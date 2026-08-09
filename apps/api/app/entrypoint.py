"""Production API entrypoint.

The legacy module still owns the broad route surface while this entrypoint
replaces placeholder behavior with production implementations before serving.
"""

from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import models as m
from .calendar_overrides import install_calendar_overrides
from .database import get_db
from .main import ASSET_ROOT, _tenant_obj, app, org_brand_or_404, user_from_auth
from .production_overrides import install_production_overrides


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


_remove_route("/assets/{id}/download", "GET")
install_calendar_overrides(app)


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
        raise HTTPException(
            status_code=422,
            detail={
                "error": "onboarding_incomplete",
                "message": "Complete the required onboarding answers before opening the workspace.",
                "missing": missing,
            },
        )
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


# Must be installed last so every legacy placeholder (including any route added
# above by compatibility code) is removed before its production replacement is
# registered.
install_production_overrides(app)
