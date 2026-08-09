from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from . import main as legacy_main
from . import models as m
from .database import get_db
from .production_overrides import _connection_out, _structured_error
from .services.connectors.secrets import decrypt_credentials, encrypt_credentials


_INSTALLED = False


def _remove(app, path: str, method: str) -> None:
    method = method.upper()
    app.router.routes = [r for r in app.router.routes if not (getattr(r, "path", None) == path and method in (getattr(r, "methods", set()) or set()))]


def _brand(db: Session, user, brand_id: int):
    _, brand = legacy_main.org_brand_or_404(db, user, brand_id)
    return brand


def install_legacy_security_overrides(app) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
    paths = {
        ("/brands/{id}/assets", "GET"), ("/brands/{id}/assets", "POST"), ("/assets/{id}", "PATCH"), ("/assets/{id}", "DELETE"),
        ("/brands/{id}/dna", "GET"), ("/brands/{id}/dna", "PATCH"),
        ("/brands/{id}/memory", "GET"), ("/brands/{id}/memory", "POST"), ("/brands/{id}/memory/{memory_id}", "PATCH"),
        ("/brands/{id}/drafts", "GET"), ("/drafts/{id}", "GET"), ("/drafts/{id}", "PATCH"),
        ("/brands/{id}/channel-accounts", "GET"), ("/channel-accounts/{id}", "PATCH"),
    }
    for path, method in paths:
        _remove(app, path, method)

    @app.get("/brands/{id}/assets", name="legacy_assets_tenant_scoped")
    def assets(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
        return db.query(m.Asset).filter_by(brand_id=brand.id).all()

    @app.post("/brands/{id}/assets", name="legacy_asset_create_real_metadata")
    def create_asset(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
        name = str(payload.get("name") or "").strip()
        if not name:
            _structured_error(422, "asset_name_required", "Asset name is required.")
        row = m.Asset(brand_id=brand.id, name=name, asset_type=payload.get("asset_type") or "reference", url=payload.get("url"), description=payload.get("description") or "", tags_json=payload.get("tags") or payload.get("tags_json") or [], metadata_json={k: v for k, v in payload.items() if k not in {"credentials", "secret", "token"}})
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @app.patch("/assets/{id}", name="legacy_asset_patch_tenant")
    def patch_asset(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, _, row = legacy_main._tenant_obj(db, user, m.Asset, id)
        mapping = {"tags": "tags_json"}
        for key, value in payload.items():
            field = mapping.get(key, key)
            if field in {"name", "asset_type", "url", "description", "tags_json"}:
                setattr(row, field, value)
        db.commit()
        return row

    @app.delete("/assets/{id}", name="legacy_asset_delete_tenant")
    def delete_asset(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, _, row = legacy_main._tenant_obj(db, user, m.Asset, id)
        db.delete(row)
        db.commit()
        return {"deleted": id}

    @app.get("/brands/{id}/dna", name="legacy_dna_tenant")
    def get_dna(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
        return db.query(m.BrandDNA).filter_by(brand_id=brand.id).first()

    @app.patch("/brands/{id}/dna", name="legacy_dna_patch_tenant")
    def patch_dna(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
        dna = db.query(m.BrandDNA).filter_by(brand_id=brand.id).first()
        if not dna:
            dna = m.BrandDNA(brand_id=brand.id)
            db.add(dna)
        for key in {"voice_json", "visual_json", "compliance_json", "channel_rules_json", "cta_library_json", "forbidden_words_json"}:
            if key in payload:
                setattr(dna, key, payload[key])
        db.commit()
        return dna

    @app.get("/brands/{id}/memory", name="legacy_memory_tenant")
    def memory(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
        return db.query(m.BrandMemoryNote).filter_by(brand_id=brand.id).all()

    @app.post("/brands/{id}/memory", name="legacy_memory_add_tenant")
    def add_memory(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
        note_text = str(payload.get("note") or "").strip()
        if not note_text:
            _structured_error(422, "memory_note_required", "Memory note cannot be empty.")
        row = m.BrandMemoryNote(brand_id=brand.id, note=note_text, source_type=payload.get("source_type") or "manual", source_id=payload.get("source_id"), accepted_by_user_id=user.id, auto_generated=False, metadata_json=payload.get("metadata") or payload.get("metadata_json") or {})
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @app.patch("/brands/{id}/memory/{memory_id}", name="legacy_memory_patch_tenant")
    def patch_memory(id: int, memory_id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
        row = db.get(m.BrandMemoryNote, memory_id)
        if not row or row.brand_id != brand.id:
            _structured_error(404, "memory_not_found", "Memory note not found.")
        for key in {"note", "confidence_score", "accepted_by_user_id", "rejected_by_user_id", "metadata_json"}:
            if key in payload:
                setattr(row, key, payload[key])
        db.commit()
        return row

    @app.get("/brands/{id}/drafts", name="legacy_drafts_tenant")
    def drafts(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
        return [legacy_main._draft_json(row, db) for row in db.query(m.ContentDraft).filter_by(brand_id=brand.id).order_by(m.ContentDraft.updated_at.desc()).all()]

    @app.get("/drafts/{id}", name="legacy_draft_get_tenant")
    def get_draft(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        row = db.get(m.ContentDraft, id)
        if not row:
            _structured_error(404, "draft_not_found", "Draft not found.")
        legacy_main.org_brand_or_404(db, user, row.brand_id)
        return legacy_main._draft_json(row, db)

    @app.patch("/drafts/{id}", name="legacy_draft_patch_tenant")
    def patch_draft(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        row = db.get(m.ContentDraft, id)
        if not row:
            _structured_error(404, "draft_not_found", "Draft not found.")
        legacy_main.org_brand_or_404(db, user, row.brand_id)
        for key, value in payload.items():
            if key in {"title", "body", "hashtags_json", "media_asset_ids_json", "status", "language", "content_type"}:
                setattr(row, key, value)
        version = m.ContentVersion(draft_id=row.id, version_number=db.query(m.ContentVersion).filter_by(draft_id=row.id).count() + 1, title=row.title, body=row.body, metadata_json={"source": "manual_edit"}, created_by_user_id=user.id, ai_generated=False)
        db.add(version)
        db.flush()
        row.current_version_id = version.id
        db.commit()
        return legacy_main._draft_json(row, db)

    @app.get("/brands/{id}/channel-accounts", name="legacy_accounts_tenant_redacted")
    def channel_accounts(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
        return [_connection_out(row) for row in db.query(m.ChannelAccount).filter_by(brand_id=brand.id).all()]

    @app.patch("/channel-accounts/{id}", name="legacy_account_patch_secure")
    def patch_account(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, _, row = legacy_main._tenant_obj(db, user, m.ChannelAccount, id)
        if "account_name" in payload:
            row.account_name = payload["account_name"]
        if "credentials" in payload or "credentials_encrypted_json" in payload:
            current = decrypt_credentials(row.credentials_encrypted_json or {})
            incoming = dict(payload.get("credentials") or payload.get("credentials_encrypted_json") or {})
            incoming = {k: v for k, v in incoming.items() if v not in {None, "", "••••••••", "********"}}
            row.credentials_encrypted_json = encrypt_credentials({**current, **incoming})
            row.connection_status = "needs_setup"
        db.commit()
        return _connection_out(row)
