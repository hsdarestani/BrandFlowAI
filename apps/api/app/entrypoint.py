"""Production API entrypoint.

The legacy module still owns the broad route surface while this entrypoint
removes placeholder/fake behavior and installs production implementations before
serving requests.
"""

import os
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import models as m
from . import model_compat as _model_compat  # noqa: F401 - registers durable compatibility models/properties
from .admin_overrides import install_admin_overrides
from .approval_delivery_overrides import install_approval_delivery_overrides
from .calendar_overrides import install_calendar_overrides
from .database import get_db
from .legacy_security_overrides import install_legacy_security_overrides
from .main import (
    ASSET_ROOT,
    _tenant_obj,
    active_brand,
    app,
    build_home_overview,
    current_org,
    org_brand_or_404,
    user_from_auth,
)
from .production_overrides import install_production_overrides
from .publishing_overrides import install_publishing_overrides


def _remove_route(path: str, method: str) -> None:
    method = method.upper()
    app.router.routes = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == path
            and method in (getattr(route, "methods", set()) or set())
        )
    ]


# Remove duplicate/unsafe legacy handlers before registering canonical routes.
_remove_route("/assets/{id}/download", "GET")
_remove_route("/environment", "GET")
_remove_route("/workspace/current", "GET")
_remove_route("/brands/{id}/drafts", "POST")
install_calendar_overrides(app)


@app.get("/environment", name="environment_canonical")
def environment_canonical():
    demo_mode = os.getenv("DEMO_MODE", "false").strip().lower() == "true"
    return {
        "demo_mode": demo_mode,
        "mode": "Demo mode" if demo_mode else "Production mode",
    }


@app.get("/workspace/current", name="workspace_current_canonical")
def workspace_current_canonical(u=Depends(user_from_auth), db: Session = Depends(get_db)):
    org = current_org(db, u)
    brand = active_brand(db, org)
    return {
        "user": {"id": u.id, "name": u.name or "User", "email": u.email},
        "organization": ({"id": org.id, "name": org.name, "mode": org.mode} if org else None),
        "brand": (
            {
                "id": brand.id,
                "name": brand.name,
                "primary_language": brand.primary_language,
                "timezone": brand.timezone,
            }
            if brand
            else None
        ),
        "recommended_action": (
            build_home_overview(db, u).get("recommended_action")
            if org and brand
            else None
        ),
    }


@app.post("/brands/{id}/drafts", name="draft_create_canonical")
def draft_create_canonical(id: int, payload: dict, u=Depends(user_from_auth), db: Session = Depends(get_db)):
    _, brand = org_brand_or_404(db, u, id)
    calendar_item_id = payload.get("calendar_item_id")
    if calendar_item_id is not None:
        item = db.get(m.CalendarItem, calendar_item_id)
        if not item or item.brand_id != brand.id:
            raise HTTPException(
                status_code=422,
                detail={"error": "calendar_item_invalid", "message": "Calendar item does not belong to this brand."},
            )
    draft = m.ContentDraft(
        brand_id=brand.id,
        calendar_item_id=calendar_item_id,
        channel=str(payload.get("channel") or "assisted"),
        content_type=str(payload.get("content_type") or "post"),
        language=str(payload.get("language") or brand.primary_language or "en"),
        title=str(payload.get("title") or "Untitled draft"),
        body=str(payload.get("body") or ""),
        status=str(payload.get("status") or "draft"),
        created_by_user_id=u.id,
    )
    db.add(draft)
    db.flush()
    version = m.ContentVersion(
        draft_id=draft.id,
        version_number=1,
        title=draft.title,
        body=draft.body,
        metadata_json=dict(payload.get("metadata") or {}),
        created_by_user_id=u.id,
        ai_generated=bool(payload.get("ai_generated", False)),
    )
    db.add(version)
    db.flush()
    draft.current_version_id = version.id
    db.commit()
    db.refresh(draft)
    return {
        "id": draft.id,
        "brand_id": draft.brand_id,
        "calendar_item_id": draft.calendar_item_id,
        "channel": draft.channel,
        "content_type": draft.content_type,
        "language": draft.language,
        "title": draft.title,
        "body": draft.body,
        "status": draft.status,
        "current_version_id": draft.current_version_id,
    }


@app.post("/onboarding/activate", name="onboarding_activate_safe")
def onboarding_activate_safe(u=Depends(user_from_auth), db: Session = Depends(get_db)):
    """Activate a completed chat onboarding without deleting existing records."""
    _, brand = org_brand_or_404(db, u)
    dna = db.query(m.BrandDNA).filter_by(brand_id=brand.id).first()
    voice = (dna.voice_json or {}) if dna else {}
    pillars = voice.get("content_pillars") or []
    if isinstance(pillars, str):
        pillars = [item.strip() for item in pillars.split(",") if item.strip()]
    required = {
        "brand_name": bool(str(brand.name or "").strip()),
        "brand_summary": bool(str(voice.get("brand_summary") or brand.description or "").strip()),
        "target_audience": bool(str(voice.get("target_audience") or "").strip()),
        "tone_of_voice": bool(str(voice.get("tone_of_voice") or "").strip()),
        "content_pillars": len(pillars) >= 2,
        "product_service": db.query(m.ProductService).filter_by(brand_id=brand.id).count() > 0,
    }
    missing = [key for key, complete in required.items() if not complete]
    if missing:
        raise HTTPException(status_code=422, detail={"error": "onboarding_incomplete", "message": "Complete the required onboarding answers before opening the workspace.", "missing": missing})
    brand.status = "active"
    for key, label in (("profile", "Brand profile"), ("dna", "Brand voice")):
        row = db.query(m.SetupChecklistItem).filter_by(brand_id=brand.id, key=key).first()
        if not row:
            row = m.SetupChecklistItem(brand_id=brand.id, key=key, label=label)
        row.status = "done"
        db.add(row)
    db.commit()
    return {"completed": True, "brand_id": brand.id, "status": brand.status}


@app.get("/assets/{id}/download", name="asset_download_file")
def asset_download_file(id: int, u=Depends(user_from_auth), db: Session = Depends(get_db)):
    """Stream an authenticated tenant-scoped asset from local storage."""
    _, _, asset = _tenant_obj(db, u, m.Asset, id)
    metadata = asset.metadata_json or {}
    raw_path = metadata.get("storage_path")
    if not raw_path:
        raise HTTPException(status_code=404, detail={"error": "asset_file_missing", "message": "This asset has no stored file."})
    root = Path(ASSET_ROOT).resolve()
    path = Path(raw_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail={"error": "invalid_asset_path", "message": "Asset path is outside the storage root."}) from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail={"error": "asset_file_missing", "message": "The stored asset file could not be found."})
    filename = metadata.get("original_filename") or path.name
    media_type = metadata.get("mime_type") or "application/octet-stream"
    return FileResponse(path=path, media_type=media_type, filename=filename)


# Install in increasing specificity. The last layers intentionally remove any
# duplicate legacy routes left behind by the compatibility module.
install_production_overrides(app)
install_publishing_overrides(app)
install_approval_delivery_overrides(app)
install_legacy_security_overrides(app)
install_admin_overrides(app)
