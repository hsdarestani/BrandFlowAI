from __future__ import annotations

import base64
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from secrets import token_urlsafe
from typing import Any

from arabic_reshaper import reshape
from bidi.algorithm import get_display
from fastapi import Depends, HTTPException
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import main as legacy_main
from . import models as m
from .database import get_db
from .services.ai.content_engine import (
    generate_campaign_plan,
    generate_draft,
    generate_insight_recommendations,
    generate_report_narrative,
    normalize_hashtags,
    review_compliance,
    transform_draft,
)
from .services.ai.providers import AIConfigurationError, AIProviderError, OpenAICompatibleProvider
from .services.connectors.base import ConnectorError, ConnectorNotSupported
from .services.connectors.providers import ASSISTED_PROVIDERS, KNOWN_PROVIDERS, get_connector
from .services.connectors.secrets import decrypt_credentials, encrypt_credentials, redacted_credentials


_INSTALLED = False
PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "https://smarbiz.sbs").rstrip("/")


def _remove_route(app, path: str, method: str) -> None:
    method = method.upper()
    app.router.routes = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == path
            and method in (getattr(route, "methods", set()) or set())
        )
    ]


def _structured_error(status: int, code: str, message: str, **extra):
    detail = {"error": code, "message": message}
    detail.update(extra)
    raise HTTPException(status_code=status, detail=detail)


def _ai_error(exc: Exception):
    if isinstance(exc, AIConfigurationError):
        _structured_error(503, "ai_not_configured", "Real AI is required for this operation. Configure OPENAI_API_KEY in production.")
    _structured_error(502, "ai_generation_failed", "The AI provider could not produce a valid result. Try again.", provider_detail=str(exc)[:500])


def _tenant(db: Session, user, brand_id: int | None = None):
    return legacy_main.org_brand_or_404(db, user, brand_id)


def _brand_context(db: Session, brand: m.Brand, *, campaign: m.Campaign | None = None) -> dict[str, Any]:
    dna = db.query(m.BrandDNA).filter_by(brand_id=brand.id).first()
    voice = (dna.voice_json or {}) if dna else {}
    compliance = (dna.compliance_json or {}) if dna else {}
    visual = (dna.visual_json or {}) if dna else {}
    channel_rules = (dna.channel_rules_json or {}) if dna else {}
    cta = (dna.cta_library_json or {}) if dna else {}
    forbidden = (dna.forbidden_words_json or {}) if dna else {}
    products = db.query(m.ProductService).filter_by(brand_id=brand.id).all()
    personas = db.query(m.Persona).filter_by(brand_id=brand.id).all()
    rules = db.query(m.BrandRule).filter_by(brand_id=brand.id, is_active=True).all()
    memories = (
        db.query(m.BrandMemoryNote)
        .filter_by(brand_id=brand.id)
        .order_by(m.BrandMemoryNote.created_at.desc())
        .limit(30)
        .all()
    )
    return {
        "brand": {
            "id": brand.id,
            "name": brand.name,
            "description": brand.description,
            "industry": brand.industry,
            "country": brand.country,
            "website": brand.website_url,
            "primary_language": brand.primary_language,
            "timezone": brand.timezone,
        },
        "brand_pulse": {
            "voice": voice,
            "compliance": compliance,
            "visual": visual,
            "channel_rules": channel_rules,
            "cta_library": cta,
            "forbidden_words": forbidden,
        },
        "products_services": [
            {
                "id": row.id,
                "name": row.name,
                "type": row.type,
                "description": row.description,
                "price": str(row.price) if row.price is not None else None,
                "currency": row.currency,
                "metadata": row.metadata_json or {},
            }
            for row in products
        ],
        "personas": [
            {
                "id": row.id,
                "name": row.name,
                "segment": row.segment,
                "description": row.description,
                "pains": row.pains or [],
                "desires": row.desires or [],
                "objections": row.objections or [],
                "preferred_channels": row.preferred_channels or [],
                "language": row.language,
            }
            for row in personas
        ],
        "active_brand_rules": [
            {
                "id": row.id,
                "category": row.category,
                "title": row.title,
                "description": row.description,
                "severity": row.severity,
                "channel": row.applies_to_channel,
            }
            for row in rules
        ],
        "accepted_memory": [
            {
                "id": row.id,
                "text": row.note,
                "source": row.source_type,
                "confidence": float(row.confidence_score or 0),
                "pinned": bool((row.metadata_json or {}).get("pinned")),
            }
            for row in memories
            if not (row.metadata_json or {}).get("archived") and not row.rejected_by_user_id
        ],
        "campaign": (
            {
                "id": campaign.id,
                "name": campaign.name,
                "goal": campaign.goal,
                "description": campaign.description,
                "offer": campaign.offer,
                "target_audience": campaign.target_audience,
                "start_date": campaign.start_date,
                "end_date": campaign.end_date,
                "channels": campaign.channels_json or [],
                "content_pillars": campaign.content_pillars_json or [],
            }
            if campaign
            else None
        ),
    }


def _log_ai(db: Session, user, org: m.Organization, brand: m.Brand, provider, operation: str) -> None:
    usage = getattr(provider, "last_usage", {}) or {}
    db.add(
        m.AIUsageLog(
            organization_id=org.id,
            brand_id=brand.id,
            user_id=user.id,
            provider=getattr(provider, "provider_name", "openai"),
            model=getattr(provider, "model", ""),
            operation=operation,
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            cost_estimate=0,
        )
    )


def _draft_meta(db: Session, draft: m.ContentDraft) -> dict[str, Any]:
    if not draft.current_version_id:
        return {}
    version = db.get(m.ContentVersion, draft.current_version_id)
    return dict(version.metadata_json or {}) if version else {}


def _save_ai_version(db: Session, user, draft: m.ContentDraft, metadata: dict[str, Any]) -> None:
    number = db.query(m.ContentVersion).filter_by(draft_id=draft.id).count() + 1
    version = m.ContentVersion(
        draft_id=draft.id,
        version_number=number,
        title=draft.title,
        body=draft.body,
        metadata_json=metadata,
        created_by_user_id=user.id,
        ai_generated=True,
    )
    db.add(version)
    db.flush()
    draft.current_version_id = version.id


def _assert_draft(db: Session, user, draft_id: int):
    draft, org, brand = legacy_main._assert_draft(draft_id, user, db)
    return draft, org, brand


def _connector_with_credentials(account: m.ChannelAccount):
    connector = get_connector(account.provider)
    credentials = decrypt_credentials(account.credentials_encrypted_json or {})
    for key, value in credentials.items():
        if isinstance(key, str) and not key.startswith("_"):
            try:
                setattr(connector, key, value)
            except (AttributeError, TypeError):
                pass
    return connector, credentials


def _connection_out(account: m.ChannelAccount):
    return {
        "id": account.id,
        "provider": account.provider,
        "display_name": account.account_name,
        "category": (account.capabilities_json or {}).get("category", "other"),
        "status": account.connection_status,
        "capabilities": account.capabilities_json or {},
        "config": redacted_credentials(account.credentials_encrypted_json or {}),
        "last_test_status": (account.capabilities_json or {}).get("last_test_status"),
        "last_test_message": (account.capabilities_json or {}).get("last_test_message"),
        "last_tested_at": (account.capabilities_json or {}).get("last_tested_at"),
    }


def _provider_category(name: str) -> str:
    if name in {"ga4"}:
        return "analytics"
    if name in {"woocommerce"}:
        return "ecommerce"
    if name in {"approval_link", "bale", "telegram", "brevo"}:
        return "approval"
    return "publishing"


def _provider_label(name: str) -> str:
    labels = {
        "approval_link": "Public approval link",
        "telegram": "Telegram Bot",
        "bale": "Bale Bot",
        "brevo": "Brevo Email",
        "woocommerce": "WooCommerce",
        "ga4": "Google Analytics 4",
        "instagram": "Instagram / Meta",
        "facebook": "Facebook Page",
        "linkedin": "LinkedIn",
        "tiktok": "TikTok",
        "youtube": "YouTube",
        "google_business": "Google Business Profile",
        "mailchimp": "Mailchimp",
        "booking": "Booking",
        "eitaa": "Eitaa",
        "soroush": "Soroush",
        "aparat": "Aparat",
        "bale_safir": "Bale Safir",
    }
    return labels.get(name, name.replace("_", " ").title())


def _catalog(db: Session, brand: m.Brand):
    existing = {row.provider: row for row in db.query(m.ChannelAccount).filter_by(brand_id=brand.id).all()}
    rows = []
    for provider in KNOWN_PROVIDERS:
        connector = get_connector(provider)
        caps = connector.capabilities.__dict__.copy()
        category = _provider_category(provider)
        caps.update(
            {
                "category": category,
                "can_publish": bool(connector.capabilities.direct_publish),
                "can_schedule": bool(connector.capabilities.schedule),
                "can_approve": bool(connector.capabilities.approval_bot or provider in {"approval_link", "brevo"}),
                "can_send_message": bool(connector.capabilities.dm or connector.capabilities.approval_bot or provider == "brevo"),
                "can_fetch_analytics": bool(connector.capabilities.analytics),
                "can_import_orders": provider == "woocommerce",
            }
        )
        account = existing.get(provider)
        assisted = provider in ASSISTED_PROVIDERS
        status = account.connection_status if account else ("assisted" if assisted else "not_configured")
        rows.append(
            {
                "provider": provider,
                "label": _provider_label(provider),
                "category": category,
                "purpose": (
                    "Direct API connection"
                    if provider in {"telegram", "bale", "brevo", "woocommerce", "ga4", "approval_link"}
                    else "Assisted workflow; direct API/OAuth is not enabled in this deployment"
                ),
                "status": status,
                "publishing": "Yes" if caps["can_publish"] else ("Assisted" if assisted and category == "publishing" else "No"),
                "approval": "Yes" if caps["can_approve"] else "No",
                "analytics": "Yes" if caps["can_fetch_analytics"] else "No",
                "difficulty": "Easy" if provider == "approval_link" else "Medium" if provider in {"telegram", "bale", "brevo", "woocommerce", "ga4"} else "Assisted",
                "capabilities": caps,
                "is_available": provider in {"approval_link", "telegram", "bale", "brevo", "woocommerce", "ga4"},
                "is_mock": False,
                "is_assisted": assisted,
                "connection_id": account.id if account else None,
                "auth_method": "local" if provider == "approval_link" else "credentials" if provider in {"telegram", "bale", "brevo", "woocommerce", "ga4"} else "assisted",
                "setup_requirements": "No credentials" if provider == "approval_link" else "Provider credentials" if provider in {"telegram", "bale", "brevo", "woocommerce", "ga4"} else "No direct API credentials accepted",
                "docs": "Test connection performs a real provider request for direct integrations.",
            }
        )
    return rows


def _integrations_overview(db: Session, user):
    org, brand = _tenant(db, user)
    catalog = _catalog(db, brand)
    connected = [row for row in catalog if row["status"] == "connected"]
    alerts = []
    if not any(row["status"] == "connected" and row["capabilities"].get("can_approve") for row in catalog):
        alerts.append({"id": "no_approval", "title": "No approval method connected", "description": "Enable a public approval link or connect Telegram, Bale, or Brevo.", "severity": "warning", "href": "/app/integrations"})
    if not any(row["status"] == "connected" and row["capabilities"].get("can_fetch_analytics") for row in catalog):
        alerts.append({"id": "no_analytics", "title": "No analytics source connected", "description": "Connect GA4 or WooCommerce, or add manual metrics.", "severity": "info", "href": "/app/integrations"})
    path = ["approval_link", "telegram", "bale", "brevo", "woocommerce", "ga4"]
    return {
        "user": {"id": user.id, "name": user.name or "User", "email": user.email},
        "organization": {"id": org.id, "name": org.name},
        "brand": {"id": brand.id, "name": brand.name},
        "summary": {
            "total_available": sum(bool(row["is_available"]) for row in catalog),
            "connected_count": len(connected),
            "publishing_connected": sum(row["status"] == "connected" and row["capabilities"].get("can_publish") for row in catalog),
            "approval_connected": sum(row["status"] == "connected" and row["capabilities"].get("can_approve") for row in catalog),
            "analytics_connected": sum(row["status"] == "connected" and row["capabilities"].get("can_fetch_analytics") for row in catalog),
            "error_count": sum(row["status"] == "error" for row in catalog),
        },
        "recommended_path": [
            {
                "step": index + 1,
                "provider": provider,
                "label": next(row["label"] for row in catalog if row["provider"] == provider),
                "purpose": next(row["purpose"] for row in catalog if row["provider"] == provider),
                "status": next(row["status"] for row in catalog if row["provider"] == provider),
                "action_label": "Configure",
                "action_type": "connect",
            }
            for index, provider in enumerate(path)
        ],
        "catalog": catalog,
        "alerts": alerts,
    }


def _report_stats(db: Session, brand: m.Brand, start: str, end: str) -> dict[str, Any]:
    start_dt = datetime.combine(date.fromisoformat(start), time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(date.fromisoformat(end) + timedelta(days=1), time.min, tzinfo=timezone.utc)
    draft_q = db.query(m.ContentDraft).filter(m.ContentDraft.brand_id == brand.id, m.ContentDraft.created_at >= start_dt, m.ContentDraft.created_at < end_dt)
    approval_q = (
        db.query(m.ApprovalRequest)
        .join(m.ContentDraft, m.ContentDraft.id == m.ApprovalRequest.draft_id)
        .filter(m.ContentDraft.brand_id == brand.id, m.ApprovalRequest.created_at >= start_dt, m.ApprovalRequest.created_at < end_dt)
    )
    campaign_q = db.query(m.Campaign).filter(m.Campaign.brand_id == brand.id, m.Campaign.created_at >= start_dt, m.Campaign.created_at < end_dt)
    published_q = (
        db.query(m.PublishedPost)
        .join(m.ContentDraft, m.ContentDraft.id == m.PublishedPost.draft_id)
        .filter(m.ContentDraft.brand_id == brand.id, m.PublishedPost.published_at >= start_dt, m.PublishedPost.published_at < end_dt)
    )
    metrics = db.query(m.ManualMetric).filter(m.ManualMetric.brand_id == brand.id, m.ManualMetric.metric_date >= start, m.ManualMetric.metric_date <= end).all()
    approvals = approval_q.all()
    return {
        "drafts_created": draft_q.count(),
        "approval_requests": len(approvals),
        "approved": sum(row.status == "approved" for row in approvals),
        "rejected_or_revision": sum(row.status in {"rejected", "revision_requested"} for row in approvals),
        "campaigns_created": campaign_q.count(),
        "published_posts": published_q.count(),
        "measured_metrics": [
            {"date": row.metric_date, "source": row.source, **(row.metrics_json or {})}
            for row in metrics
        ],
    }


def _render_pdf(report: dict[str, Any]) -> bytes:
    stream = BytesIO()
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_name = "DejaVuSans"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font_name, font_path))
    pdf = canvas.Canvas(stream, pagesize=A4)
    width, height = A4
    y = height - 48
    rtl = any("\u0600" <= ch <= "\u06ff" for ch in (report.get("summary") or ""))

    def visual(text: str) -> str:
        value = str(text or "")
        return get_display(reshape(value)) if rtl else value

    def line(text: str, size: int = 10, gap: int = 16):
        nonlocal y
        pdf.setFont(font_name, size)
        max_chars = 86 if size <= 10 else 64
        words = str(text or "").replace("\n", " \n ").split(" ")
        current = ""
        chunks = []
        for word in words:
            if word == "\n":
                chunks.append(current)
                current = ""
                continue
            candidate = (current + " " + word).strip()
            if len(candidate) > max_chars and current:
                chunks.append(current)
                current = word
            else:
                current = candidate
        if current:
            chunks.append(current)
        for chunk in chunks or [""]:
            if y < 60:
                pdf.showPage()
                y = height - 48
                pdf.setFont(font_name, size)
            text_value = visual(chunk)
            if rtl:
                pdf.drawRightString(width - 48, y, text_value)
            else:
                pdf.drawString(48, y, text_value)
            y -= gap

    line(report.get("title") or "Smarbiz report", 16, 22)
    line(f"{report.get('period_start')} — {report.get('period_end')}", 9, 18)
    y -= 4
    line(report.get("summary") or "", 10, 16)
    y -= 8
    for heading, values in (("Highlights", report.get("highlights") or []), ("Recommendations", (report.get("recommendations") or {}).get("items") or [])):
        line(heading, 13, 20)
        for item in values:
            line("• " + str(item), 10, 16)
        y -= 6
    pdf.save()
    return stream.getvalue()


def _ai_status() -> dict[str, Any]:
    provider = (os.getenv("AI_PROVIDER") or "").strip().lower() or ("openai" if os.getenv("OPENAI_API_KEY") else "mock")
    model = (os.getenv("OPENAI_MODEL") or "gpt-5.6-sol") if provider == "openai" else None
    configured = provider == "openai" and bool((os.getenv("OPENAI_API_KEY") or "").strip())
    return {
        "provider": provider,
        "model": model,
        "status": "configured" if configured else "test_only" if provider == "mock" else "missing_credentials",
        "real_ai": configured,
        "last_test_message": None,
    }


def _settings_payload(db: Session, user):
    original = legacy_main._original_settings_overview_payload(db, user) if hasattr(legacy_main, "_original_settings_overview_payload") else legacy_main.settings_overview_payload(db, user)
    org = legacy_main.current_org(db, user)
    brand = legacy_main.active_brand(db, org) if org else None
    if org:
        prefs = dict(org.settings_json or {})
        original["preferences"] = {
            "default_language": prefs.get("default_language", user.locale or "en"),
            "default_timezone": prefs.get("default_timezone", user.timezone or (brand.timezone if brand else "UTC")),
            "approval_required_before_publish": prefs.get("approval_required_before_publish", True),
            "assisted_publishing_mode": prefs.get("assisted_publishing_mode", True),
        }
        usage_rows = db.query(m.AIUsageLog).filter_by(organization_id=org.id).all()
        original["usage"]["ai_requests"] = len(usage_rows)
        original["usage"]["ai_input_tokens"] = sum(int(row.input_tokens or 0) for row in usage_rows)
        original["usage"]["ai_output_tokens"] = sum(int(row.output_tokens or 0) for row in usage_rows)
        original["usage"]["storage_used_bytes"] = sum(int((asset.metadata_json or {}).get("size_bytes") or 0) for asset in (db.query(m.Asset).filter_by(brand_id=brand.id).all() if brand else []))
    original["ai_provider"] = _ai_status()
    return original


def install_production_overrides(app) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    # Capture legacy helper before replacing it; the existing routes resolve the
    # module global at request time and therefore automatically gain real status.
    if not hasattr(legacy_main, "_original_settings_overview_payload"):
        legacy_main._original_settings_overview_payload = legacy_main.settings_overview_payload
    legacy_main.settings_overview_payload = _settings_payload

    routes = {
        ("/studio/generate", "POST"),
        ("/studio/drafts/{id}/transform", "POST"),
        ("/studio/drafts/{id}/compliance-check", "POST"),
        ("/studio/drafts/{id}/send-for-approval", "POST"),
        ("/studio/drafts/{id}/schedule", "POST"),
        ("/campaigns/{id}/generate-plan", "POST"),
        ("/campaigns/{id}/create-drafts", "POST"),
        ("/insights/overview", "GET"),
        ("/insights/refresh", "POST"),
        ("/insights/generate-recommendations", "POST"),
        ("/reports/generate-weekly", "POST"),
        ("/reports/{id}/regenerate", "POST"),
        ("/reports/{id}/export", "POST"),
        ("/reports/{id}/send-email", "POST"),
        ("/integrations/overview", "GET"),
        ("/integrations/catalog", "GET"),
        ("/integrations/connections", "GET"),
        ("/integrations/connections/{id}", "GET"),
        ("/integrations/connections", "POST"),
        ("/integrations/connections/{id}", "PATCH"),
        ("/integrations/connections/{id}/test", "POST"),
        ("/integrations/connections/{id}/refresh", "POST"),
        ("/integrations/connections/{id}/send-test", "POST"),
        ("/integrations/oauth/{provider}/start", "GET"),
        ("/integrations/oauth/{provider}/callback", "GET"),
        ("/brand-pulse/memory/{id}/pin", "POST"),
        ("/brand-pulse/memory/{id}/archive", "POST"),
        ("/settings/ai-provider", "PATCH"),
        ("/settings/ai-provider/test", "POST"),
        ("/settings/billing", "GET"),
        ("/settings/setup-preferences", "PATCH"),
        ("/settings/security", "PATCH"),
        ("/settings/export-data", "POST"),
        ("/settings/delete-workspace-request", "POST"),
        ("/drafts/{id}/revise", "POST"),
        ("/drafts/{id}/translate", "POST"),
        ("/drafts/{id}/compliance-check", "POST"),
        ("/calendar/items/{id}/generate-drafts", "POST"),
    }
    for path, method in routes:
        _remove_route(app, path, method)

    @app.post("/studio/generate", name="studio_generate_real_ai")
    def studio_generate(payload: legacy_main.StudioGenerateIn, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        org, brand = _tenant(db, user)
        context = _brand_context(db, brand)
        try:
            result, provider = generate_draft(
                context,
                channel=payload.channel,
                content_type=payload.content_type,
                language=payload.language or brand.primary_language,
                user_prompt=f"Goal: {payload.goal}\nOffer: {payload.product_or_offer}\nTone: {payload.tone}\nRequest: {payload.prompt}",
            )
        except (AIProviderError, ValueError) as exc:
            _ai_error(exc)
        draft = m.ContentDraft(
            brand_id=brand.id,
            channel=payload.channel,
            content_type=payload.content_type,
            language=payload.language or brand.primary_language,
            title=result["title"],
            body=result["body"],
            hashtags_json=normalize_hashtags(result.get("hashtags") or []),
            status="draft_ready",
            brand_fit_score=float(result.get("brand_fit_score") or 0) / 100,
            compliance_score=float(result.get("compliance_score") or 0) / 100,
            ai_provider=provider.provider_name,
            ai_model=provider.model,
            created_by_user_id=user.id,
        )
        db.add(draft)
        db.flush()
        metadata = {
            "hook": result.get("hook"),
            "cta": result.get("cta"),
            "hashtags": draft.hashtags_json,
            "creative_direction": result.get("creative_direction"),
            "warnings": result.get("warnings") or [],
            "source_facts_used": result.get("source_facts_used") or [],
            "goal": payload.goal,
            "product_or_offer": payload.product_or_offer,
            "tone": payload.tone,
            "prompt": payload.prompt,
        }
        _save_ai_version(db, user, draft, metadata)
        _log_ai(db, user, org, brand, provider, "studio_generate")
        db.commit()
        return {"draft": legacy_main._draft_json(draft, db), "provider": provider.provider_name, "model": provider.model, "warnings": metadata["warnings"]}

    @app.post("/studio/drafts/{id}/transform", name="studio_transform_real_ai")
    def studio_transform(id: int, payload: legacy_main.StudioTransformIn, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        draft, org, brand = _assert_draft(db, user, id)
        context = _brand_context(db, brand)
        metadata = _draft_meta(db, draft)
        try:
            result, provider = transform_draft(
                context,
                title=draft.title,
                body=draft.body,
                cta=str(metadata.get("cta") or ""),
                action=payload.action,
                target_language=payload.target_language,
            )
        except (AIProviderError, ValueError) as exc:
            _ai_error(exc)
        draft.title = result.get("title") or draft.title
        draft.body = result.get("body") or draft.body
        if payload.action == "translate" and payload.target_language:
            draft.language = payload.target_language
        metadata.update({"cta": result.get("cta") or metadata.get("cta", ""), "editor_notes": result.get("notes"), "last_transform": payload.action})
        draft.ai_provider = provider.provider_name
        draft.ai_model = provider.model
        _save_ai_version(db, user, draft, metadata)
        _log_ai(db, user, org, brand, provider, f"studio_transform:{payload.action}")
        db.commit()
        return legacy_main._draft_json(draft, db)

    @app.post("/studio/drafts/{id}/compliance-check", name="studio_compliance_real")
    def studio_compliance(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        draft, org, brand = _assert_draft(db, user, id)
        context = _brand_context(db, brand)
        metadata = _draft_meta(db, draft)
        result, provider = review_compliance(context, text=f"{draft.title}\n\n{draft.body}\n\n{metadata.get('cta','')}")
        warnings = [
            {"id": f"compliance-{index}", "title": "Compliance warning", "description": text, "severity": "danger" if result.get("risk_level") in {"high", "blocked"} else "warning"}
            for index, text in enumerate(result.get("warnings") or [])
        ]
        status = "passed" if result.get("safe") and not warnings else "blocked" if result.get("risk_level") == "blocked" else "warnings"
        compliance_result = {
            "status": status,
            "summary": "Compliance review completed against saved brand rules and source facts.",
            "warnings": warnings,
            "suggestions": result.get("required_changes") or [],
            "unsupported_claims": result.get("unsupported_claims") or [],
            "score": int(result.get("score") or 0),
        }
        metadata["compliance_result"] = compliance_result
        metadata["warnings"] = warnings
        draft.compliance_score = int(result.get("score") or 0) / 100
        _save_ai_version(db, user, draft, metadata)
        if provider:
            _log_ai(db, user, org, brand, provider, "studio_compliance")
        db.commit()
        return {"draft": legacy_main._draft_json(draft, db), "compliance_result": compliance_result}

    @app.post("/studio/drafts/{id}/send-for-approval", name="studio_send_approval_real")
    def studio_send_approval(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        draft, _, brand = _assert_draft(db, user, id)
        accounts = db.query(m.ChannelAccount).filter(m.ChannelAccount.brand_id == brand.id, m.ChannelAccount.connection_status == "connected").all()
        account = next((row for row in accounts if row.provider in {"telegram", "bale", "brevo", "approval_link"}), None)
        if not account:
            _structured_error(422, "missing_approval_method", "Connect a public approval link, Telegram, Bale, or Brevo before sending.", action_href="/app/integrations")
        token = token_urlsafe(24)
        request = m.ApprovalRequest(draft_id=id, requested_by_user_id=user.id, public_token_hash=sha256(token.encode()).hexdigest())
        db.add(request)
        db.flush()
        approval_path = f"/public/approval/{token}"
        approval_url = f"{PUBLIC_BASE_URL}{approval_path}"
        delivered = account.provider == "approval_link"
        delivery = {"provider": account.provider, "mode": "public_link" if delivered else "external_message"}
        if account.provider in {"telegram", "bale", "brevo"}:
            connector, credentials = _connector_with_credentials(account)
            try:
                if account.provider in {"telegram", "bale"}:
                    chat_id = credentials.get("chat_id")
                    response = connector.send_message(chat_id, f"{draft.title}\n\nApproval: {approval_url}")
                else:
                    recipient = credentials.get("approval_recipient_email") or credentials.get("test_recipient_email")
                    if not recipient:
                        raise ConnectorError("Brevo approval_recipient_email is missing")
                    response = connector.send_message(recipient, f"{draft.title}\n\nReview and approve: {approval_url}", subject=f"Approval: {draft.title}", sender_email=credentials.get("sender_email"), sender_name=credentials.get("sender_name") or brand.name)
                delivered = True
                delivery["provider_response_id"] = response.get("message_id") if isinstance(response, dict) else None
            except ConnectorError as exc:
                db.rollback()
                _structured_error(502, "approval_delivery_failed", str(exc))
        draft.status = "in_review"
        db.add(m.ConnectorEvent(channel_account_id=account.id, provider=account.provider, event_type="approval_sent", payload_json={"approval_request_id": request.id, "delivered": delivered}))
        db.commit()
        return {"approval_request_id": request.id, "status": request.status, "approval_url": approval_path, "delivered": delivered, "delivery": delivery, "draft": legacy_main._draft_json(draft, db)}

    @app.post("/studio/drafts/{id}/schedule", name="studio_schedule_real")
    def studio_schedule(id: int, payload: legacy_main.StudioScheduleIn, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        draft, _, brand = _assert_draft(db, user, id)
        provider = payload.channel or draft.channel
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider=provider).first()
        if not account:
            _structured_error(422, "channel_not_configured", f"Configure {provider} in Integrations before scheduling.", action_href="/app/integrations")
        if account.connection_status not in {"connected", "assisted"}:
            _structured_error(422, "channel_not_ready", f"{provider} is not ready. Test the connection or use an assisted integration.", action_href="/app/integrations")
        try:
            zone = legacy_main.ZoneInfo(payload.timezone or brand.timezone or "UTC")
            local = datetime.fromisoformat(f"{payload.date}T{payload.time}:00").replace(tzinfo=zone)
            scheduled_at = local.astimezone(timezone.utc)
        except Exception as exc:
            _structured_error(422, "invalid_schedule", f"Invalid date/time/timezone: {exc}")
        post = m.ScheduledPost(draft_id=id, channel_account_id=account.id, scheduled_at=scheduled_at, status="scheduled")
        db.add(post)
        draft.status = "scheduled"
        db.commit()
        return {"scheduled_post_id": post.id, "status": post.status, "warning": "This provider uses assisted publishing at the scheduled time." if account.connection_status == "assisted" else None, "draft": legacy_main._draft_json(draft, db)}

    @app.post("/campaigns/{id}/generate-plan", name="campaign_generate_plan_real_ai")
    def campaign_generate_plan_route(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        campaign, org, brand = legacy_main._campaign(db, user, id)
        missing = legacy_main.setup_state(db, brand)["missing_requirements"]
        if missing:
            _structured_error(422, "missing_setup", "Complete Brand Pulse before generating a campaign plan.", missing_requirements=missing)
        channels = campaign.channels_json or [row.provider for row in db.query(m.ChannelAccount).filter_by(brand_id=brand.id).all() if row.provider not in {"ga4", "woocommerce", "brevo", "approval_link"}] or ["instagram"]
        try:
            start = date.fromisoformat(campaign.start_date) if campaign.start_date else date.today()
            end = date.fromisoformat(campaign.end_date) if campaign.end_date else start + timedelta(days=13)
        except ValueError:
            _structured_error(422, "invalid_campaign_dates", "Campaign dates are invalid.")
        duration = max(1, (end - start).days + 1)
        item_count = max(4, min(12, round(duration / 2)))
        context = _brand_context(db, brand, campaign=campaign)
        try:
            result, provider = generate_campaign_plan(context, duration_days=duration, channels=channels, item_count=item_count)
        except (AIProviderError, ValueError) as exc:
            _ai_error(exc)
        product_ids = {row.id for row in db.query(m.ProductService).filter_by(brand_id=brand.id).all()}
        persona_ids = {row.id for row in db.query(m.Persona).filter_by(brand_id=brand.id).all()}
        for item in result.get("items") or []:
            if item.get("product_service_id") is not None and item["product_service_id"] not in product_ids:
                _structured_error(502, "ai_invalid_reference", "AI returned an unknown product/service reference.")
            if item.get("persona_id") is not None and item["persona_id"] not in persona_ids:
                _structured_error(502, "ai_invalid_reference", "AI returned an unknown persona reference.")
        db.query(m.CampaignPlanItem).filter_by(campaign_id=campaign.id).delete()
        for item in result["items"]:
            suggested = (start + timedelta(days=int(item.get("day_offset") or 0))).isoformat()
            brief = f"Hook: {item.get('hook','')}\n\nBrief: {item.get('brief','')}\n\nCTA: {item.get('cta','')}\n\nGoal: {item.get('goal','')} · Funnel: {item.get('funnel_stage','')}"
            db.add(m.CampaignPlanItem(campaign_id=campaign.id, title=item["title"], channel=item["channel"], content_type=item["content_type"], brief=brief, suggested_date=suggested, status="idea"))
        campaign.status = "planned" if campaign.status == "draft" else campaign.status
        _log_ai(db, user, org, brand, provider, "campaign_generate_plan")
        db.add(m.AuditLog(organization_id=org.id, brand_id=brand.id, user_id=user.id, action="campaign_plan_generated", target_type="campaign", target_id=str(campaign.id), metadata_json={"strategy": result.get("strategy"), "success_definition": result.get("success_definition"), "item_count": item_count}))
        db.commit()
        return legacy_main.get_campaign_new(id, user, db)

    @app.post("/campaigns/{id}/create-drafts", name="campaign_create_drafts_real_ai")
    def campaign_create_drafts_route(id: int, payload: dict = {}, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        campaign, org, brand = legacy_main._campaign(db, user, id)
        ids = payload.get("plan_item_ids") or [row.id for row in db.query(m.CampaignPlanItem).filter_by(campaign_id=campaign.id).all()]
        rows = db.query(m.CampaignPlanItem).filter(m.CampaignPlanItem.campaign_id == campaign.id, m.CampaignPlanItem.id.in_(ids)).all()
        context = _brand_context(db, brand, campaign=campaign)
        made = []
        for row in rows:
            if row.linked_content_draft_id:
                made.append(row.linked_content_draft_id)
                continue
            try:
                result, provider = generate_draft(context, channel=row.channel, content_type=row.content_type, language=brand.primary_language, user_prompt=f"Campaign plan item: {row.title}\n{row.brief}")
            except (AIProviderError, ValueError) as exc:
                db.rollback()
                _ai_error(exc)
            draft = m.ContentDraft(
                brand_id=brand.id,
                channel=row.channel,
                content_type=row.content_type,
                language=brand.primary_language,
                title=result["title"],
                body=result["body"],
                hashtags_json=normalize_hashtags(result.get("hashtags") or []),
                status="draft_ready",
                brand_fit_score=int(result.get("brand_fit_score") or 0) / 100,
                compliance_score=int(result.get("compliance_score") or 0) / 100,
                ai_provider=provider.provider_name,
                ai_model=provider.model,
                created_by_user_id=user.id,
            )
            db.add(draft)
            db.flush()
            _save_ai_version(db, user, draft, {"hook": result.get("hook"), "cta": result.get("cta"), "creative_direction": result.get("creative_direction"), "warnings": result.get("warnings") or [], "campaign_id": campaign.id, "campaign_plan_item_id": row.id})
            row.linked_content_draft_id = draft.id
            row.status = "draft"
            _log_ai(db, user, org, brand, provider, "campaign_create_draft")
            made.append(draft.id)
        db.commit()
        return {"created_draft_ids": made, "href": "/app/content-studio"}

    def insights_payload(user, db: Session):
        org, brand = _tenant(db, user)
        metrics = db.query(m.ManualMetric).filter_by(brand_id=brand.id).order_by(m.ManualMetric.metric_date.asc()).all()
        accounts = db.query(m.ChannelAccount).filter_by(brand_id=brand.id).all()
        published_rows = db.query(m.PublishedPost).join(m.ContentDraft, m.ContentDraft.id == m.PublishedPost.draft_id).filter(m.ContentDraft.brand_id == brand.id).all()
        approvals = db.query(m.ApprovalRequest).join(m.ContentDraft, m.ContentDraft.id == m.ApprovalRequest.draft_id).filter(m.ContentDraft.brand_id == brand.id).all()
        approved = sum(row.status == "approved" for row in approvals)
        analytics_connected = any(row.connection_status == "connected" and get_connector(row.provider).capabilities.analytics for row in accounts if row.provider in KNOWN_PROVIDERS)
        priority = ["revenue", "conversions", "orders", "clicks", "sessions", "reach", "impressions"]
        by_metric: dict[str, dict[str, float]] = {name: {} for name in priority}
        for metric in metrics:
            data = metric.metrics_json or {}
            channel = str(data.get("channel") or metric.source or "manual")
            if data.get("metric_name") in priority:
                key = data["metric_name"]
                by_metric[key][channel] = by_metric[key].get(channel, 0) + float(data.get("metric_value") or 0)
            for key in priority:
                if isinstance(data.get(key), (int, float)):
                    by_metric[key][channel] = by_metric[key].get(channel, 0) + float(data[key])
        best_channel = None
        best_metric = None
        for key in priority:
            comparable = by_metric[key]
            if len(comparable) >= 2:
                best_channel = max(comparable, key=comparable.get)
                best_metric = key
                break
        type_counts: dict[str, int] = {}
        for post in published_rows:
            draft = db.get(m.ContentDraft, post.draft_id)
            if draft:
                type_counts[draft.content_type] = type_counts.get(draft.content_type, 0) + 1
        top_type = max(type_counts, key=type_counts.get) if type_counts else None
        recommendations = []
        if not analytics_connected:
            recommendations.append({"id": "connect_analytics", "title": "Connect analytics", "description": "Connect GA4 or WooCommerce, or continue adding measured manual metrics.", "action_label": "Connect analytics", "action_href": "/app/integrations", "severity": "warning"})
        if not published_rows:
            recommendations.append({"id": "publish_first", "title": "Publish first content", "description": "Performance recommendations need published content or measured outcomes.", "action_label": "Open Studio", "action_href": "/app/content-studio", "severity": "info"})
        top = []
        for metric in metrics[-8:]:
            data = metric.metrics_json or {}
            top.append({"id": metric.id, "title": data.get("notes") or data.get("metric_name") or metric.source, "channel": data.get("channel", metric.source), "content_type": data.get("content_type") or "metric", "metric_label": data.get("metric_name") or "measured data", "metric_value": data.get("metric_value") if "metric_value" in data else next((data.get(key) for key in priority if data.get(key) is not None), None), "status": "measured", "href": "/app/analytics"})
        return {
            "user": {"id": user.id, "name": user.name or "User", "email": user.email},
            "organization": {"id": org.id, "name": org.name},
            "brand": {"id": brand.id, "name": brand.name, "primary_language": brand.primary_language},
            "connection_status": {"analytics_connected": analytics_connected, "connected_sources": [{"id": provider, "label": _provider_label(provider), "status": "connected" if any(row.provider == provider and row.connection_status == "connected" for row in accounts) else "missing", "href": "/app/integrations"} for provider in ["ga4", "woocommerce", "instagram", "linkedin", "youtube", "google_business"]]},
            "summary": {"published_posts": len(published_rows), "total_approvals": len(approvals), "approval_rate": round(approved / len(approvals) * 100) if approvals else None, "best_channel": best_channel, "best_channel_metric": best_metric, "top_content_type": top_type, "content_with_data_count": len(metrics), "warnings_count": 0 if metrics else 1},
            "trends": [{"date": row.metric_date, "source": row.source, "metrics": row.metrics_json or {}} for row in metrics],
            "top_content": top,
            "recommendations": recommendations,
            "memory_candidates": [{"id": row["id"], "text": row["description"], "source": "deterministic", "action_label": "Save to memory"} for row in recommendations],
            "alerts": [] if metrics else [{"id": "no_insights", "title": "No measured insights yet", "description": "Connect analytics or add manual metrics. Smarbiz will not invent performance data.", "severity": "warning", "href": "/app/analytics"}],
        }

    @app.get("/insights/overview", name="insights_overview_real")
    def insights_overview_route(user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return insights_payload(user, db)

    @app.post("/insights/refresh", name="insights_refresh_real_connectors")
    def insights_refresh_route(user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        org, brand = _tenant(db, user)
        today = date.today().isoformat()
        start = (date.today() - timedelta(days=29)).isoformat()
        accounts = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, connection_status="connected").all()
        refreshed = []
        errors = []
        for account in accounts:
            try:
                connector, _ = _connector_with_credentials(account)
                if not connector.capabilities.analytics:
                    continue
                data = connector.fetch_analytics(start_date=start, end_date=today)
                existing = db.query(m.ManualMetric).filter_by(brand_id=brand.id, source=f"connector:{account.provider}", metric_date=today).first()
                row = existing or m.ManualMetric(brand_id=brand.id, source=f"connector:{account.provider}", metric_date=today, metrics_json={})
                row.metrics_json = {"channel": account.provider, "sync_period_start": start, "sync_period_end": today, **data}
                db.add(row)
                account.last_sync_at = datetime.now(timezone.utc)
                refreshed.append(account.provider)
            except (ConnectorError, ValueError, RuntimeError) as exc:
                account.connection_status = "error"
                account.capabilities_json = {**(account.capabilities_json or {}), "last_test_status": "error", "last_test_message": str(exc)[:500]}
                errors.append({"provider": account.provider, "message": str(exc)[:500]})
        db.commit()
        return {"refreshed": True, "sources": refreshed, "errors": errors, "overview": insights_payload(user, db)}

    @app.post("/insights/generate-recommendations", name="insights_recommendations_real_ai")
    def insights_recommendations_route(user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        org, brand = _tenant(db, user)
        overview = insights_payload(user, db)
        context = _brand_context(db, brand)
        context["measured_insights"] = {"summary": overview["summary"], "trends": overview["trends"], "top_content": overview["top_content"]}
        try:
            result, provider = generate_insight_recommendations(context)
        except (AIProviderError, ValueError) as exc:
            _ai_error(exc)
        _log_ai(db, user, org, brand, provider, "insights_recommendations")
        db.commit()
        return result

    @app.post("/reports/generate-weekly", name="reports_generate_factual")
    def report_generate_route(data: legacy_main.ReportGenerateIn, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        org, brand = _tenant(db, user, data.brand_id)
        now = date.today()
        start = data.period_start or (now - timedelta(days=now.weekday())).isoformat()
        end = data.period_end or (date.fromisoformat(start) + timedelta(days=6)).isoformat()
        if end < start:
            _structured_error(422, "invalid_period", "End date cannot be before start date.")
        stats = _report_stats(db, brand, start, end)
        context = _brand_context(db, brand)
        context["report_period"] = {"start": start, "end": end, "audience": data.audience, "language": data.language}
        context["workflow_and_performance_data"] = stats
        provider = None
        narrative = None
        try:
            narrative, provider = generate_report_narrative(context)
        except AIConfigurationError:
            narrative = None
        except AIProviderError as exc:
            _structured_error(502, "ai_report_failed", "AI report analysis failed. No fabricated narrative was saved.", provider_detail=str(exc)[:500])
        if narrative:
            summary = narrative["summary"]
            highlights = narrative.get("highlights") or []
            recommendations = narrative.get("recommendations") or []
            risks = narrative.get("risks") or []
            next_week = narrative.get("next_week_focus") or []
            source = "ai"
        else:
            summary = f"{start}–{end}: {stats['drafts_created']} drafts created, {stats['approval_requests']} approval requests, {stats['published_posts']} published posts, and {len(stats['measured_metrics'])} measured metric records."
            if not stats["measured_metrics"]:
                summary += " No performance metrics were available, so this report does not claim marketing results."
            highlights = [f"{stats['drafts_created']} drafts created", f"{stats['published_posts']} posts published", f"{stats['approved']} approvals accepted"]
            recommendations = ["Connect or refresh analytics before making performance conclusions"] if not stats["measured_metrics"] else ["Review measured metrics by comparable unit before changing the content mix"]
            risks = ["No measured performance data"] if not stats["measured_metrics"] else []
            next_week = []
            source = "factual"
        report = m.WeeklyReport(
            brand_id=brand.id,
            week_start=start,
            week_end=end,
            summary=summary,
            insights_json={"title": f"Weekly report {start}", "status": "generated", "highlights": highlights, "metrics": stats, "risks": risks, "language": data.language, "audience": data.audience, "analysis_source": source},
            recommendations_json={"items": recommendations, "next_week": next_week},
        )
        db.add(report)
        if provider:
            _log_ai(db, user, org, brand, provider, "weekly_report")
        db.commit()
        db.refresh(report)
        return legacy_main.report_get(report.id, user, db)

    @app.post("/reports/{id}/regenerate", name="reports_regenerate_real")
    def report_regenerate_route(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        old = legacy_main.report_get(id, user, db)
        payload = legacy_main.ReportGenerateIn(period_start=old["period_start"], period_end=old["period_end"], language=(db.get(m.WeeklyReport, id).insights_json or {}).get("language", "en"), audience=(db.get(m.WeeklyReport, id).insights_json or {}).get("audience", "internal"))
        return report_generate_route(payload, user, db)

    @app.post("/reports/{id}/export", name="reports_export_real")
    def report_export_route(id: int, payload: dict = {}, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        report = legacy_main.report_get(id, user, db)
        fmt = str(payload.get("format") or "markdown").lower()
        recommendations = (report.get("recommendations") or {}).get("items") or []
        text = f"# {report['title']}\n\n{report['period_start']} – {report['period_end']}\n\n{report['summary']}\n\n## Highlights\n" + "\n".join(f"- {item}" for item in report.get("highlights") or []) + "\n\n## Recommendations\n" + "\n".join(f"- {item}" for item in recommendations)
        if fmt == "pdf":
            raw = _render_pdf(report)
            return {"available": True, "format": "pdf", "content_base64": base64.b64encode(raw).decode("ascii"), "filename": f"smarbiz-report-{id}.pdf"}
        if fmt == "html":
            safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            return {"available": True, "format": "html", "content": f"<!doctype html><meta charset='utf-8'><body>{safe}</body>", "filename": f"smarbiz-report-{id}.html"}
        return {"available": True, "format": "markdown", "content": text, "filename": f"smarbiz-report-{id}.md"}

    @app.post("/reports/{id}/send-email", name="reports_send_brevo_real")
    def report_send_email_route(id: int, payload: dict = {}, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, brand = _tenant(db, user)
        report = legacy_main.report_get(id, user, db)
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider="brevo", connection_status="connected").first()
        if not account:
            _structured_error(422, "email_not_connected", "Connect and test Brevo before sending reports.", href="/app/integrations")
        recipient = str(payload.get("recipient_email") or "").strip()
        if not recipient or "@" not in recipient:
            _structured_error(422, "invalid_recipient", "Enter a valid recipient email address.")
        connector, credentials = _connector_with_credentials(account)
        text = f"{report['title']}\n{report['period_start']} – {report['period_end']}\n\n{report['summary']}\n\nRecommendations:\n" + "\n".join(f"- {item}" for item in (report.get("recommendations") or {}).get("items", []))
        try:
            result = connector.send_message(recipient, text, subject=report["title"], sender_email=credentials.get("sender_email"), sender_name=credentials.get("sender_name") or brand.name)
        except ConnectorError as exc:
            _structured_error(502, "email_send_failed", str(exc))
        row = db.get(m.WeeklyReport, id)
        row.insights_json = {**(row.insights_json or {}), "status": "sent", "sent_to": recipient, "sent_at": datetime.now(timezone.utc).isoformat(), "provider_message_id": result.get("message_id")}
        db.commit()
        return {"sent": True, "report_id": id, "message_id": result.get("message_id")}

    @app.get("/integrations/overview", name="integrations_overview_truthful")
    def integrations_overview_route(user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _integrations_overview(db, user)

    @app.get("/integrations/catalog", name="integrations_catalog_truthful")
    def integrations_catalog_route(user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, brand = _tenant(db, user)
        return _catalog(db, brand)

    @app.get("/integrations/connections", name="integrations_connections_secure")
    def integrations_connections_route(user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, brand = _tenant(db, user)
        return [_connection_out(row) for row in db.query(m.ChannelAccount).filter_by(brand_id=brand.id).all()]

    @app.get("/integrations/connections/{id}", name="integration_connection_secure")
    def integration_connection_route(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, _, account = legacy_main._tenant_obj(db, user, m.ChannelAccount, id)
        return _connection_out(account)

    @app.post("/integrations/connections", name="integration_create_secure")
    def integration_create_route(payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, brand = _tenant(db, user)
        provider = str(payload.get("provider") or "").strip().lower()
        if provider not in KNOWN_PROVIDERS:
            _structured_error(422, "unknown_provider", "Unknown connector provider.")
        connector = get_connector(provider)
        category = _provider_category(provider)
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider=provider).first() or m.ChannelAccount(brand_id=brand.id, provider=provider, account_name=payload.get("display_name") or _provider_label(provider), account_identifier=provider)
        account.account_name = payload.get("display_name") or account.account_name
        account.capabilities_json = {**connector.capabilities.__dict__, "category": category, "can_publish": connector.capabilities.direct_publish, "can_schedule": connector.capabilities.schedule, "can_approve": connector.capabilities.approval_bot or provider in {"approval_link", "brevo"}, "can_send_message": connector.capabilities.dm or connector.capabilities.approval_bot or provider == "brevo", "can_fetch_analytics": connector.capabilities.analytics, "can_import_orders": provider == "woocommerce"}
        config = dict(payload.get("config") or {})
        if provider == "approval_link":
            account.connection_status = "connected"
            account.credentials_encrypted_json = {}
        elif provider in ASSISTED_PROVIDERS:
            account.connection_status = "assisted"
            account.credentials_encrypted_json = {}
        else:
            account.connection_status = "needs_setup"
            account.credentials_encrypted_json = encrypt_credentials(config)
        db.add(account)
        db.commit()
        return _connection_out(account)

    @app.patch("/integrations/connections/{id}", name="integration_patch_secure")
    def integration_patch_route(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, _, account = legacy_main._tenant_obj(db, user, m.ChannelAccount, id)
        if payload.get("display_name"):
            account.account_name = payload["display_name"]
        if "config" in payload:
            current = decrypt_credentials(account.credentials_encrypted_json or {})
            incoming = {key: value for key, value in dict(payload.get("config") or {}).items() if value not in {None, "", "••••••••"}}
            account.credentials_encrypted_json = encrypt_credentials({**current, **incoming})
            if account.provider not in ASSISTED_PROVIDERS and account.provider != "approval_link":
                account.connection_status = "needs_setup"
        db.commit()
        return _connection_out(account)

    def test_connection(id: int, user, db: Session):
        _, _, account = legacy_main._tenant_obj(db, user, m.ChannelAccount, id)
        connector, credentials = _connector_with_credentials(account)
        try:
            result = connector.validate_credentials(credentials)
            valid = bool(result.get("valid")) if isinstance(result, dict) else False
            if not valid and account.provider in ASSISTED_PROVIDERS:
                account.connection_status = "assisted"
            elif valid:
                account.connection_status = "connected"
                account.account_name = result.get("account_name") or account.account_name
                account.account_identifier = result.get("external_account_id") or account.account_identifier
                account.last_sync_at = datetime.now(timezone.utc)
            else:
                account.connection_status = "error"
            account.capabilities_json = {**(account.capabilities_json or {}), "last_test_status": "ok" if valid else "assisted", "last_test_message": result.get("message") if isinstance(result, dict) else None, "last_tested_at": datetime.now(timezone.utc).isoformat()}
            # Rewrite legacy plaintext credentials encrypted after first test.
            account.credentials_encrypted_json = encrypt_credentials(credentials)
            db.commit()
            return {"status": "ok" if valid else "assisted", "message": result.get("message") or "Live provider validation passed." if isinstance(result, dict) else "Validation completed.", "connection": _connection_out(account), "provider_result": {key: value for key, value in (result or {}).items() if key not in {"token", "api_key", "secret"}}}
        except (ConnectorError, RuntimeError) as exc:
            account.connection_status = "error"
            account.capabilities_json = {**(account.capabilities_json or {}), "last_test_status": "error", "last_test_message": str(exc)[:500], "last_tested_at": datetime.now(timezone.utc).isoformat()}
            db.commit()
            _structured_error(422, "connection_test_failed", str(exc))

    @app.post("/integrations/connections/{id}/test", name="integration_test_live")
    def integration_test_route(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return test_connection(id, user, db)

    @app.post("/integrations/connections/{id}/refresh", name="integration_refresh_live")
    def integration_refresh_route(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return test_connection(id, user, db)

    @app.post("/integrations/connections/{id}/send-test", name="integration_send_test_live")
    def integration_send_test_route(id: int, payload: dict | None = None, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, _, account = legacy_main._tenant_obj(db, user, m.ChannelAccount, id)
        if account.connection_status != "connected":
            _structured_error(422, "not_connected", "Run a successful live connection test first.")
        connector, credentials = _connector_with_credentials(account)
        data = payload or {}
        try:
            if account.provider in {"telegram", "bale"}:
                result = connector.send_message(data.get("chat_id") or credentials.get("chat_id"), data.get("text") or "Smarbiz connection test")
            elif account.provider == "brevo":
                recipient = data.get("recipient_email") or credentials.get("test_recipient_email")
                if not recipient:
                    raise ConnectorError("Set test_recipient_email or provide recipient_email")
                result = connector.send_message(recipient, data.get("text") or "Smarbiz connection test", subject="Smarbiz connection test", sender_email=credentials.get("sender_email"), sender_name=credentials.get("sender_name") or "Smarbiz")
            elif account.provider in {"ga4", "woocommerce", "approval_link"}:
                return test_connection(id, user, db)
            else:
                _structured_error(422, "assisted_only", "This integration is assisted-only; there is no external test message to send.")
        except ConnectorError as exc:
            _structured_error(502, "test_message_failed", str(exc))
        return {"status": "sent", "message": "Provider confirmed the test request.", "provider_result": result}

    @app.get("/integrations/oauth/{provider}/start", name="integration_oauth_truthful")
    def oauth_start_route(provider: str, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        if provider in ASSISTED_PROVIDERS:
            _structured_error(409, "assisted_only", f"{_provider_label(provider)} direct OAuth is not enabled in this deployment. Use assisted publishing instead.", assisted=True)
        _structured_error(404, "oauth_not_used", "This provider is configured with credentials in Integrations, not OAuth.")

    @app.get("/integrations/oauth/{provider}/callback", name="integration_oauth_callback_truthful")
    def oauth_callback_route(provider: str, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _structured_error(409, "oauth_not_enabled", f"OAuth callback is not enabled for {_provider_label(provider)} in this deployment.")

    @app.post("/brand-pulse/memory/{id}/pin", name="memory_pin_persisted")
    def memory_pin_route(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, _, note = legacy_main._tenant_obj(db, user, m.BrandMemoryNote, id)
        metadata = dict(note.metadata_json or {})
        metadata["pinned"] = not bool(metadata.get("pinned"))
        note.metadata_json = metadata
        db.commit()
        return {"id": id, "pinned": metadata["pinned"]}

    @app.post("/brand-pulse/memory/{id}/archive", name="memory_archive_persisted")
    def memory_archive_route(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, _, note = legacy_main._tenant_obj(db, user, m.BrandMemoryNote, id)
        metadata = dict(note.metadata_json or {})
        metadata["archived"] = True
        note.metadata_json = metadata
        db.commit()
        return {"id": id, "archived": True}

    @app.patch("/settings/ai-provider", name="settings_ai_server_managed")
    def settings_ai_provider_route(payload: dict, user=Depends(legacy_main.user_from_auth)):
        requested = str(payload.get("provider") or "openai").lower()
        current = _ai_status()
        if requested != current["provider"] or (payload.get("model") and payload.get("model") != current.get("model")):
            _structured_error(409, "server_managed_ai", "Production AI provider/model are server-managed. Change deployment secrets/environment, then run Test provider.", current=current)
        return current

    @app.post("/settings/ai-provider/test", name="settings_ai_live_test")
    def settings_ai_test_route(payload: dict | None = None, user=Depends(legacy_main.user_from_auth)):
        data = payload or {}
        api_key = str(data.get("api_key") or os.getenv("OPENAI_API_KEY") or "").strip()
        if not api_key:
            _structured_error(422, "missing_credentials", "OPENAI_API_KEY is not configured.")
        model = str(data.get("model") or os.getenv("OPENAI_MODEL") or "gpt-5.6-sol")
        try:
            provider = OpenAICompatibleProvider(api_key=api_key, model=model, timeout_seconds=30)
            result = provider.generate_json("Production configuration test. Return ok=true.", schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False})
        except AIProviderError as exc:
            _structured_error(422, "ai_test_failed", str(exc))
        if result.get("ok") is not True:
            _structured_error(502, "ai_test_invalid", "The provider responded but the structured test did not pass.")
        return {"status": "success", "message": "Live OpenAI Responses API test passed.", "provider": provider.provider_name, "model": provider.model}

    @app.get("/settings/billing", name="settings_billing_truthful")
    def settings_billing_route(user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        org = legacy_main.current_org(db, user)
        plan = db.get(m.Plan, org.plan_id) if org and org.plan_id else None
        return {"status": org.billing_status if org else "unavailable", "billing_provider_connected": False, "plan": ({"id": plan.id, "name": plan.name, "price_monthly": float(plan.price_monthly or 0), "currency": plan.currency} if plan else None), "message": "No external payment processor is connected. Smarbiz does not display invented invoices or subscription state."}

    @app.patch("/settings/setup-preferences", name="settings_preferences_persisted")
    def settings_preferences_route(payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        org = legacy_main.current_org(db, user)
        if not org:
            _structured_error(404, "workspace_not_found", "Workspace not found.")
        allowed = {"default_language", "default_timezone", "approval_required_before_publish", "assisted_publishing_mode"}
        current = dict(org.settings_json or {})
        current.update({key: value for key, value in payload.items() if key in allowed})
        org.settings_json = current
        db.commit()
        return _settings_payload(db, user)["preferences"]

    @app.patch("/settings/security", name="settings_security_truthful")
    def settings_security_route(payload: dict, user=Depends(legacy_main.user_from_auth)):
        unsupported = [key for key in payload if key not in {"current_password", "new_password"}]
        if unsupported:
            _structured_error(422, "unsupported_security_setting", "These security controls are not implemented as toggles. Use Change password for the currently supported account security action.", fields=unsupported)
        return {"ok": True, "supported_actions": ["change_password"]}

    @app.post("/settings/export-data", name="settings_export_real")
    def settings_export_route(user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        org, brand = _tenant(db, user)
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "user": {"id": user.id, "email": user.email, "name": user.name, "locale": user.locale, "timezone": user.timezone},
            "organization": {"id": org.id, "name": org.name, "mode": org.mode, "billing_status": org.billing_status, "settings": org.settings_json or {}},
            "brand_pulse": legacy_main._brand_pulse_overview(db, user),
            "campaigns": [legacy_main.campaign_row(db, row) for row in db.query(m.Campaign).filter_by(brand_id=brand.id).all()],
            "calendar": [legacy_main.calendar_item_out(row, db) for row in db.query(m.CalendarItem).filter_by(brand_id=brand.id).all()],
            "drafts": [legacy_main._draft_json(row, db) for row in db.query(m.ContentDraft).filter_by(brand_id=brand.id).all()],
            "reports": [legacy_main.report_get(row.id, user, db) for row in db.query(m.WeeklyReport).filter_by(brand_id=brand.id).all()],
            "integrations": [_connection_out(row) for row in db.query(m.ChannelAccount).filter_by(brand_id=brand.id).all()],
        }
        content = json.dumps(payload, ensure_ascii=False, default=str, indent=2)
        return {"available": True, "filename": f"smarbiz-data-{brand.id}-{date.today().isoformat()}.json", "content": content, "content_type": "application/json"}

    @app.post("/settings/delete-workspace-request", name="settings_delete_request_persisted")
    def settings_delete_workspace_route(payload: dict | None = None, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        org = legacy_main.current_org(db, user)
        if not org:
            _structured_error(404, "workspace_not_found", "Workspace not found.")
        if not legacy_main.can_manage_team(db, user, org):
            _structured_error(403, "forbidden", "Only the workspace owner/admin can request deletion.")
        confirmation = str((payload or {}).get("confirmation") or "").strip()
        if confirmation != org.name:
            _structured_error(422, "confirmation_required", "Type the exact organization name to record a deletion request.")
        settings_data = dict(org.settings_json or {})
        requested_at = datetime.now(timezone.utc).isoformat()
        settings_data["deletion_request"] = {"requested_at": requested_at, "requested_by_user_id": user.id, "status": "requested"}
        org.settings_json = settings_data
        org.billing_status = "deletion_requested"
        db.add(m.AuditLog(organization_id=org.id, user_id=user.id, action="workspace_deletion_requested", target_type="organization", target_id=str(org.id), metadata_json={"requested_at": requested_at}))
        db.commit()
        return {"status": "requested", "requested_at": requested_at, "organization_id": org.id}

    def legacy_transform(id: int, action: str, target_language: str | None, user, db: Session):
        draft, org, brand = _assert_draft(db, user, id)
        context = _brand_context(db, brand)
        metadata = _draft_meta(db, draft)
        try:
            result, provider = transform_draft(context, title=draft.title, body=draft.body, cta=str(metadata.get("cta") or ""), action=action, target_language=target_language)
        except (AIProviderError, ValueError) as exc:
            _ai_error(exc)
        draft.title = result.get("title") or draft.title
        draft.body = result.get("body") or draft.body
        if target_language:
            draft.language = target_language
        metadata.update({"cta": result.get("cta") or metadata.get("cta", ""), "editor_notes": result.get("notes"), "last_transform": action})
        draft.ai_provider = provider.provider_name
        draft.ai_model = provider.model
        _save_ai_version(db, user, draft, metadata)
        _log_ai(db, user, org, brand, provider, f"legacy_transform:{action}")
        db.commit()
        return draft

    @app.post("/drafts/{id}/revise", name="legacy_revise_real_ai")
    def draft_revise_route(id: int, payload: dict = {}, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        action = str(payload.get("instruction") or payload.get("prompt") or "rewrite for clarity")
        draft = legacy_transform(id, action, None, user, db)
        return legacy_main._draft_json(draft, db)

    @app.post("/drafts/{id}/translate", name="legacy_translate_real_ai")
    def draft_translate_route(id: int, payload: dict = {}, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        language = str(payload.get("target_language") or payload.get("language") or "").strip()
        if not language:
            _structured_error(422, "target_language_required", "Choose a target language.")
        draft = legacy_transform(id, "translate", language, user, db)
        return legacy_main._draft_json(draft, db)

    @app.post("/drafts/{id}/compliance-check", name="legacy_compliance_real")
    def draft_compliance_route(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return studio_compliance(id, user, db)

    @app.post("/calendar/items/{id}/generate-drafts", name="calendar_generate_drafts_real_ai")
    def calendar_generate_drafts_route(id: int, payload: dict = {}, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        org, brand = _tenant(db, user)
        item = db.get(m.CalendarItem, id)
        if not item or item.brand_id != brand.id:
            _structured_error(404, "calendar_item_not_found", "Calendar item not found in this workspace.")
        channels = payload.get("channels") or item.channels_json or ["instagram"]
        context = _brand_context(db, brand)
        made = []
        for channel in channels:
            try:
                result, provider = generate_draft(context, channel=channel, content_type=item.content_type, language=item.language or brand.primary_language, user_prompt=f"Calendar item: {item.title}\n{item.description}\nGoal: {item.goal}\nCTA: {item.cta}")
            except (AIProviderError, ValueError) as exc:
                db.rollback()
                _ai_error(exc)
            draft = m.ContentDraft(brand_id=brand.id, calendar_item_id=item.id, channel=channel, content_type=item.content_type, language=item.language or brand.primary_language, title=result["title"], body=result["body"], hashtags_json=normalize_hashtags(result.get("hashtags") or []), status="draft_ready", brand_fit_score=int(result.get("brand_fit_score") or 0) / 100, compliance_score=int(result.get("compliance_score") or 0) / 100, ai_provider=provider.provider_name, ai_model=provider.model, created_by_user_id=user.id)
            db.add(draft)
            db.flush()
            _save_ai_version(db, user, draft, {"hook": result.get("hook"), "cta": result.get("cta"), "creative_direction": result.get("creative_direction"), "warnings": result.get("warnings") or [], "calendar_item_id": item.id})
            _log_ai(db, user, org, brand, provider, "calendar_generate_draft")
            made.append(draft)
        item.status = "drafted"
        db.commit()
        return {"drafts": [legacy_main._draft_json(row, db) for row in made], "created_count": len(made)}
