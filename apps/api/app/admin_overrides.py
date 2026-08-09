from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import os

import httpx
import redis
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import main as legacy_main
from . import models as m
from .database import get_db, settings
from .production_overrides import _structured_error
from .services.connectors.providers import KNOWN_PROVIDERS, get_connector
from .tasks import celery_app, publish_scheduled_post


_INSTALLED = False


def _remove(app, path: str, method: str) -> None:
    method = method.upper()
    app.router.routes = [r for r in app.router.routes if not (getattr(r, "path", None) == path and method in (getattr(r, "methods", set()) or set()))]


def _health(db: Session):
    health = {"api": "healthy"}
    try:
        db.execute(text("SELECT 1"))
        health["postgres"] = "healthy"
    except Exception:
        health["postgres"] = "error"
    try:
        client = redis.Redis.from_url(settings.redis_url, socket_timeout=1, socket_connect_timeout=1)
        health["redis"] = "healthy" if client.ping() else "error"
    except Exception:
        health["redis"] = "error"
    try:
        root = Path(legacy_main.ASSET_ROOT)
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".health-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        health["storage"] = "healthy"
    except Exception:
        health["storage"] = "error"
    try:
        response = httpx.get("http://web:3000/en", timeout=1.5)
        health["web"] = "healthy" if response.status_code < 500 else "error"
    except Exception:
        health["web"] = "unreachable"
    try:
        ping = celery_app.control.inspect(timeout=1.0).ping() or {}
        health["worker"] = "healthy" if ping else "unreachable"
    except Exception:
        health["worker"] = "unreachable"
    health["scheduler"] = "configured" if "publish-due-posts-every-minute" in (celery_app.conf.beat_schedule or {}) else "not_configured"
    return health


def _overview(db: Session, user):
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    health = _health(db)
    connector_errors = db.query(m.ConnectorEvent).filter(m.ConnectorEvent.event_type.in_(["error", "failed"])).count()
    failed_jobs = db.query(m.JobLog).filter_by(status="failed").count()
    incidents = []
    if failed_jobs:
        incidents.append({"id": "failed_jobs", "title": "Failed jobs detected", "severity": "warning", "count": failed_jobs})
    if connector_errors:
        incidents.append({"id": "connector_errors", "title": "Connector errors detected", "severity": "warning", "count": connector_errors})
    for service, status in health.items():
        if status in {"error", "unreachable"}:
            incidents.append({"id": f"health_{service}", "title": f"{service} is {status}", "severity": "danger", "count": 1})
    orgs = db.query(m.Organization).order_by(m.Organization.created_at.desc()).limit(100).all()
    jobs = db.query(m.JobLog).order_by(m.JobLog.created_at.desc()).limit(100).all()
    return {
        "user": {"id": user.id, "name": user.name, "email": user.email, "is_super_admin": True},
        "system_health": {**health, "connector_errors": "error" if connector_errors else "healthy"},
        "summary": {
            "organizations": db.query(m.Organization).count(),
            "users": db.query(m.User).count(),
            "brands": db.query(m.Brand).count(),
            "active_trials": db.query(m.Organization).filter_by(billing_status="trial").count(),
            "suspended_orgs": db.query(m.Organization).filter(m.Organization.suspended_at.is_not(None)).count(),
            "ai_requests_24h": db.query(m.AIUsageLog).filter(m.AIUsageLog.created_at >= yesterday).count(),
            "failed_jobs_24h": db.query(m.JobLog).filter(m.JobLog.status == "failed", m.JobLog.created_at >= yesterday).count(),
            "connector_errors_24h": db.query(m.ConnectorEvent).filter(m.ConnectorEvent.received_at >= yesterday, m.ConnectorEvent.event_type.in_(["error", "failed"])).count(),
        },
        "incidents": incidents,
        "organizations": [
            {
                "id": org.id,
                "name": org.name,
                "owner_email": (db.get(m.User, org.owner_user_id).email if org.owner_user_id and db.get(m.User, org.owner_user_id) else None),
                "status": "suspended" if org.suspended_at else org.billing_status,
                "plan": (db.get(m.Plan, org.plan_id).name if org.plan_id and db.get(m.Plan, org.plan_id) else None),
                "created_at": org.created_at.isoformat() if hasattr(org.created_at, "isoformat") else None,
            }
            for org in orgs
        ],
        "jobs": [
            {
                "id": row.id,
                "type": row.job_type,
                "status": row.status,
                "organization_name": (db.get(m.Organization, row.organization_id).name if row.organization_id and db.get(m.Organization, row.organization_id) else None),
                "last_error": row.error_message,
                "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else None,
            }
            for row in jobs
        ],
    }


def install_admin_overrides(app) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
    paths = {
        ("/admin/overview", "GET"), ("/admin/control-tower/overview", "GET"),
        ("/admin/organizations", "GET"), ("/admin/organizations/{id}", "PATCH"),
        ("/admin/organizations/{id}/suspend", "POST"), ("/admin/organizations/{id}/unsuspend", "POST"),
        ("/admin/users", "GET"), ("/admin/users/{id}", "PATCH"), ("/admin/users/{id}/disable", "POST"), ("/admin/users/{id}/enable", "POST"),
        ("/admin/brands", "GET"), ("/admin/ai-usage", "GET"), ("/admin/jobs", "GET"), ("/admin/jobs/{id}/retry", "POST"), ("/admin/jobs/{id}/cancel", "POST"),
        ("/admin/connectors", "GET"), ("/admin/connectors/{provider}", "PATCH"), ("/admin/audit-logs", "GET"),
        ("/admin/plans", "GET"), ("/admin/plans", "POST"), ("/admin/plans/{id}", "PATCH"),
        ("/admin/feature-flags", "GET"), ("/admin/feature-flags/{id}", "PATCH"), ("/admin/feature-flags/{key}", "PATCH"),
        ("/admin/compliance", "GET"), ("/admin/system-settings", "GET"), ("/admin/system-settings", "PATCH"),
    }
    for path, method in paths:
        _remove(app, path, method)

    @app.get("/admin/overview", name="admin_overview_secure")
    @app.get("/admin/control-tower/overview", name="admin_control_overview_secure")
    def overview(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return _overview(db, user)

    @app.get("/admin/organizations", name="admin_orgs_secure")
    def orgs(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return _overview(db, user)["organizations"]

    @app.post("/admin/organizations/{id}/suspend", name="admin_org_suspend_secure")
    def suspend(id: int, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        org = db.get(m.Organization, id)
        if not org:
            _structured_error(404, "organization_not_found", "Organization not found.")
        org.suspended_at = datetime.now(timezone.utc)
        db.add(m.AuditLog(organization_id=org.id, user_id=user.id, action="organization_suspended", target_type="organization", target_id=str(org.id), metadata_json={}))
        db.commit()
        return {"ok": True, "status": "suspended"}

    @app.post("/admin/organizations/{id}/unsuspend", name="admin_org_unsuspend_secure")
    def unsuspend(id: int, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        org = db.get(m.Organization, id)
        if not org:
            _structured_error(404, "organization_not_found", "Organization not found.")
        org.suspended_at = None
        db.add(m.AuditLog(organization_id=org.id, user_id=user.id, action="organization_unsuspended", target_type="organization", target_id=str(org.id), metadata_json={}))
        db.commit()
        return {"ok": True, "status": "active"}

    @app.patch("/admin/organizations/{id}", name="admin_org_patch_secure")
    def patch_org(id: int, payload: dict, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        org = db.get(m.Organization, id)
        if not org:
            _structured_error(404, "organization_not_found", "Organization not found.")
        for key in {"name", "mode", "billing_status", "plan_id"}:
            if key in payload:
                setattr(org, key, payload[key])
        db.commit()
        return {"id": org.id, "name": org.name, "mode": org.mode, "billing_status": org.billing_status, "plan_id": org.plan_id}

    @app.get("/admin/users", name="admin_users_secure")
    def users(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "email": row.email, "name": row.name, "status": "active" if row.is_active else "disabled", "is_super_admin": row.is_super_admin, "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else None} for row in db.query(m.User).order_by(m.User.created_at.desc()).limit(500).all()]

    @app.patch("/admin/users/{id}", name="admin_user_patch_secure")
    def patch_user(id: int, payload: dict, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        row = db.get(m.User, id)
        if not row:
            _structured_error(404, "user_not_found", "User not found.")
        for key in {"name", "locale", "timezone", "is_active", "is_super_admin"}:
            if key in payload:
                setattr(row, key, payload[key])
        db.commit()
        return {"id": row.id, "email": row.email, "name": row.name, "is_active": row.is_active, "is_super_admin": row.is_super_admin}

    @app.post("/admin/users/{id}/disable", name="admin_user_disable_secure")
    def disable(id: int, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return patch_user(id, {"is_active": False}, user, db)

    @app.post("/admin/users/{id}/enable", name="admin_user_enable_secure")
    def enable(id: int, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return patch_user(id, {"is_active": True}, user, db)

    @app.get("/admin/brands", name="admin_brands_secure")
    def brands(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "name": row.name, "organization_id": row.organization_id, "industry": row.industry, "country": row.country, "status": row.status, "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else None} for row in db.query(m.Brand).order_by(m.Brand.created_at.desc()).limit(500).all()]

    @app.get("/admin/ai-usage", name="admin_ai_usage_secure")
    def ai_usage(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "organization_id": row.organization_id, "brand_id": row.brand_id, "user_id": row.user_id, "provider": row.provider, "model": row.model, "operation": row.operation, "input_tokens": row.input_tokens, "output_tokens": row.output_tokens, "cost_estimate": float(row.cost_estimate or 0), "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else None} for row in db.query(m.AIUsageLog).order_by(m.AIUsageLog.created_at.desc()).limit(1000).all()]

    @app.get("/admin/connectors", name="admin_connectors_secure")
    def connectors(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "brand_id": row.brand_id, "provider": row.provider, "status": row.connection_status, "account_name": row.account_name, "last_sync_at": row.last_sync_at.isoformat() if hasattr(row.last_sync_at, "isoformat") else None, "last_test_status": (row.capabilities_json or {}).get("last_test_status"), "last_test_message": (row.capabilities_json or {}).get("last_test_message")} for row in db.query(m.ChannelAccount).order_by(m.ChannelAccount.updated_at.desc()).limit(1000).all()]

    @app.patch("/admin/connectors/{provider}", name="admin_connector_patch_truthful")
    def patch_connector(provider: str, payload: dict, user=Depends(legacy_main.require_super_admin)):
        _structured_error(409, "tenant_credentials_managed_in_workspace", "Connector credentials are tenant-scoped. Configure them in each workspace Integrations page.")

    @app.get("/admin/jobs", name="admin_jobs_secure")
    def jobs(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return _overview(db, user)["jobs"]

    @app.post("/admin/jobs/{id}/retry", name="admin_job_retry_real")
    def retry_job(id: int, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        job = db.get(m.JobLog, id)
        if not job:
            _structured_error(404, "job_not_found", "Job not found.")
        payload = job.payload_json or {}
        if job.job_type in {"publish_scheduled_post", "scheduled_publish"} and payload.get("post_id"):
            try:
                task = publish_scheduled_post.delay(int(payload["post_id"]))
            except Exception:
                _structured_error(503, "queue_unavailable", "Publishing worker queue is unavailable.")
            job.status = "queued"
            job.error_message = None
            db.commit()
            return {"ok": True, "status": "queued", "task_id": task.id}
        _structured_error(409, "job_retry_unsupported", f"No executable retry handler is registered for job_type={job.job_type}.")

    @app.post("/admin/jobs/{id}/cancel", name="admin_job_cancel_secure")
    def cancel_job(id: int, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        job = db.get(m.JobLog, id)
        if not job:
            _structured_error(404, "job_not_found", "Job not found.")
        if job.status not in {"queued", "running", "retry"}:
            _structured_error(409, "job_not_cancellable", f"Job cannot be cancelled from status {job.status}.")
        job.status = "cancelled"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        return {"ok": True, "status": "cancelled"}

    @app.get("/admin/compliance", name="admin_compliance_real")
    def compliance(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        drafts = db.query(m.ContentDraft).filter(m.ContentDraft.compliance_score < 0.8).order_by(m.ContentDraft.updated_at.desc()).limit(200).all()
        events = []
        for draft in drafts:
            metadata = {}
            if draft.current_version_id:
                version = db.get(m.ContentVersion, draft.current_version_id)
                metadata = (version.metadata_json or {}) if version else {}
            events.append({"id": draft.id, "brand_id": draft.brand_id, "title": draft.title, "compliance_score": round(float(draft.compliance_score or 0) * 100), "status": draft.status, "warnings": metadata.get("warnings") or (metadata.get("compliance_result") or {}).get("warnings") or []})
        return {"active_brand_rules": db.query(m.BrandRule).filter_by(is_active=True).count(), "flagged_drafts": events, "flagged_count": len(events)}

    @app.get("/admin/plans", name="admin_plans_secure")
    def plans(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "name": row.name, "price_monthly": float(row.price_monthly or 0), "currency": row.currency, "active": row.active, "limits": row.limits_json or {}, "features": row.features_json or {}} for row in db.query(m.Plan).all()]

    @app.post("/admin/plans", name="admin_plan_create_secure")
    def create_plan(payload: dict, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        if not str(payload.get("name") or "").strip():
            _structured_error(422, "plan_name_required", "Plan name is required.")
        row = m.Plan(name=payload["name"], price_monthly=payload.get("price_monthly", 0), currency=payload.get("currency", "EUR"), limits_json=payload.get("limits_json") or {}, features_json=payload.get("features_json") or {}, active=payload.get("active", True))
        db.add(row)
        db.commit()
        return {"id": row.id, "name": row.name, "price_monthly": float(row.price_monthly or 0), "currency": row.currency, "active": row.active}

    @app.patch("/admin/plans/{id}", name="admin_plan_patch_secure")
    def patch_plan(id: int, payload: dict, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        row = db.get(m.Plan, id)
        if not row:
            _structured_error(404, "plan_not_found", "Plan not found.")
        for key in {"name", "price_monthly", "currency", "limits_json", "features_json", "active"}:
            if key in payload:
                setattr(row, key, payload[key])
        db.commit()
        return {"id": row.id, "name": row.name, "price_monthly": float(row.price_monthly or 0), "currency": row.currency, "active": row.active}

    @app.get("/admin/feature-flags", name="admin_flags_secure")
    def flags(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "key": row.key, "enabled": row.enabled, "rollout_percentage": row.rollout_percentage, "organization_ids": row.organization_ids_json or [], "metadata": row.metadata_json or {}} for row in db.query(m.FeatureFlag).order_by(m.FeatureFlag.key.asc()).all()]

    @app.patch("/admin/feature-flags/{key}", name="admin_flag_patch_secure")
    def patch_flag(key: str, payload: dict, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        row = db.query(m.FeatureFlag).filter_by(key=key).first() or m.FeatureFlag(key=key)
        for field in {"enabled", "rollout_percentage", "organization_ids_json", "metadata_json"}:
            if field in payload:
                setattr(row, field, payload[field])
        row.rollout_percentage = max(0, min(100, int(row.rollout_percentage or 0)))
        db.add(row)
        db.commit()
        return {"id": row.id, "key": row.key, "enabled": row.enabled, "rollout_percentage": row.rollout_percentage, "organization_ids": row.organization_ids_json or [], "metadata": row.metadata_json or {}}

    @app.patch("/admin/feature-flags/{id}", name="admin_flag_patch_id_secure")
    def patch_flag_id(id: int, payload: dict, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        row = db.get(m.FeatureFlag, id)
        if not row:
            _structured_error(404, "feature_flag_not_found", "Feature flag not found.")
        return patch_flag(row.key, payload, user, db)

    @app.get("/admin/audit-logs", name="admin_audit_secure")
    def audit(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "organization_id": row.organization_id, "brand_id": row.brand_id, "user_id": row.user_id, "action": row.action, "target_type": row.target_type, "target_id": row.target_id, "metadata": row.metadata_json or {}, "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else None} for row in db.query(m.AuditLog).order_by(m.AuditLog.created_at.desc()).limit(1000).all()]

    @app.get("/admin/system-settings", name="admin_system_settings_truthful")
    def system_settings(user=Depends(legacy_main.require_super_admin)):
        return {"platform_mode": "demo" if legacy_main.DEMO_MODE else "production", "cors_origins": legacy_main.cors_origins, "signup_enabled": True, "maintenance_mode": False, "default_ai_provider": os.getenv("AI_PROVIDER") or "mock", "ai_model": os.getenv("OPENAI_MODEL") or "gpt-5.6-sol", "environment_managed": True}

    @app.patch("/admin/system-settings", name="admin_system_settings_env_managed")
    def patch_system_settings(payload: dict, user=Depends(legacy_main.require_super_admin)):
        _structured_error(409, "environment_managed", "System settings are deployment environment values and cannot be changed by an acknowledgement-only route.")
