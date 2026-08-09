from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
from secrets import token_urlsafe
from hashlib import sha256
from typing import Any

import httpx
import redis
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import main as legacy_main
from . import models as m
from .database import ASSET_ROOT if False else get_db  # type: ignore
from .database import get_db, settings
from .production_overrides import (
    PUBLIC_BASE_URL,
    _brand_context,
    _connection_out,
    _connector_with_credentials,
    _integrations_overview,
    _provider_label,
    _report_stats,
    _structured_error,
)
from .services.ai.content_engine import generate_report_narrative
from .services.ai.providers import AIConfigurationError, AIProviderError
from .services.connectors.bale_safir import BaleSafirConnector
from .services.connectors.base import ConnectorError, ConnectorNotSupported
from .services.connectors.providers import ASSISTED_PROVIDERS, KNOWN_PROVIDERS, get_connector
from .services.connectors.secrets import decrypt_credentials, encrypt_credentials, redacted_credentials
from .tasks import celery_app, publish_scheduled_post


_INSTALLED = False


def _remove(app, path: str, method: str) -> None:
    method = method.upper()
    app.router.routes = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == path
            and method in (getattr(route, "methods", set()) or set())
        )
    ]


def _tenant_brand(db: Session, user, brand_id: int):
    _, brand = legacy_main.org_brand_or_404(db, user, brand_id)
    return brand


def _tenant_draft(db: Session, user, draft_id: int):
    draft = db.get(m.ContentDraft, draft_id)
    if not draft:
        _structured_error(404, "draft_not_found", "Draft not found.")
    _, brand = legacy_main.org_brand_or_404(db, user, draft.brand_id)
    return draft, brand


def _tenant_scheduled(db: Session, user, post_id: int):
    post = db.get(m.ScheduledPost, post_id)
    if not post:
        _structured_error(404, "scheduled_post_not_found", "Scheduled post not found.")
    draft, brand = _tenant_draft(db, user, post.draft_id)
    return post, draft, brand


def _account_for_draft(db: Session, brand: m.Brand, draft: m.ContentDraft, requested_provider: str | None = None):
    provider = str(requested_provider or draft.channel or "").strip().lower()
    if not provider:
        _structured_error(422, "channel_required", "Choose a channel before publishing or scheduling.")
    account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider=provider).first()
    if not account:
        _structured_error(422, "channel_not_configured", f"Configure {_provider_label(provider)} in Integrations first.", href="/app/integrations")
    return account


def _approval_token(db: Session, approval: m.ApprovalRequest) -> str | None:
    row = (
        db.query(m.ApprovalAction)
        .filter_by(approval_request_id=approval.id, action="created")
        .filter(m.ApprovalAction.source_message_id.is_not(None))
        .order_by(m.ApprovalAction.id.asc())
        .first()
    )
    return row.source_message_id if row else None


def _send_approval(db: Session, user, approval_id: int, provider: str):
    approval = legacy_main._approval_for_user(db, user, approval_id)
    draft = db.get(m.ContentDraft, approval.draft_id)
    if not draft:
        _structured_error(404, "draft_not_found", "Approval draft no longer exists.")
    account = db.query(m.ChannelAccount).filter_by(brand_id=draft.brand_id, provider=provider, connection_status="connected").first()
    if not account:
        _structured_error(422, "not_connected", f"{_provider_label(provider)} is not connected.", href="/app/integrations")
    token = _approval_token(db, approval)
    if not token:
        _structured_error(409, "approval_link_missing", "This approval request has no public token. Create a new approval request.")
    url = f"{PUBLIC_BASE_URL}/public/approval/{token}"
    connector, credentials = _connector_with_credentials(account)
    try:
        if provider in {"telegram", "bale"}:
            response = connector.send_message(credentials.get("chat_id"), f"{draft.title}\n\nReview and approve: {url}")
        elif provider == "brevo":
            recipient = credentials.get("approval_recipient_email") or credentials.get("test_recipient_email")
            if not recipient:
                raise ConnectorError("Brevo approval_recipient_email is missing")
            response = connector.send_message(
                recipient,
                f"{draft.title}\n\nReview and approve: {url}",
                subject=f"Approval: {draft.title}",
                sender_email=credentials.get("sender_email"),
                sender_name=credentials.get("sender_name") or "Smarbiz",
            )
        else:
            raise ConnectorNotSupported(f"Approval delivery is not implemented for {provider}")
    except ConnectorError as exc:
        _structured_error(502, "approval_delivery_failed", str(exc))
    db.add(
        m.ApprovalAction(
            approval_request_id=approval.id,
            user_id=user.id,
            action="sent",
            comment=f"Sent via {provider}",
            source_channel=provider,
            source_message_id=str((response or {}).get("message_id") or (response or {}).get("request_id") or "") or None,
            save_to_memory=False,
        )
    )
    db.commit()
    return {"sent": True, "channel": provider, "approval_url": f"/public/approval/{token}", "provider_result": response}


def _publish_direct(db: Session, user, draft_id: int, provider: str | None = None):
    draft, brand = _tenant_draft(db, user, draft_id)
    account = _account_for_draft(db, brand, draft, provider)
    connector, _ = _connector_with_credentials(account)
    if account.connection_status == "assisted" or connector.capabilities.assisted_publish and not connector.capabilities.direct_publish:
        result = connector.publish_post(draft, account=account)
        return {
            "status": "assisted",
            "result": result,
            "published_post_id": None,
            "message": "Direct publishing is unavailable for this provider; no fake PublishedPost was created.",
        }
    if account.connection_status != "connected":
        _structured_error(422, "channel_not_connected", "Run a successful live connection test before publishing.", href="/app/integrations")
    if not connector.capabilities.direct_publish:
        _structured_error(422, "direct_publish_unavailable", "This provider does not support direct publishing in this deployment.")
    try:
        result = connector.publish_post(draft, account=account)
    except ConnectorError as exc:
        _structured_error(502, "publish_failed", str(exc))
    status = str((result or {}).get("status") or "").lower()
    provider_post_id = str((result or {}).get("provider_post_id") or (result or {}).get("message_id") or "").strip()
    if status not in {"published", "sent", "success"} or not provider_post_id:
        _structured_error(502, "publish_unconfirmed", "Provider did not confirm publication with a real post/message id.", provider_result=result)
    existing = db.query(m.PublishedPost).filter_by(draft_id=draft.id, channel_account_id=account.id, provider_post_id=provider_post_id).first()
    if existing:
        return {"status": "published", "published_post_id": existing.id, "result": result}
    published = m.PublishedPost(
        draft_id=draft.id,
        channel_account_id=account.id,
        provider_post_id=provider_post_id,
        public_url=str((result or {}).get("public_url") or ""),
        status="published",
        metadata_json={"provider": account.provider, "source": "publish_now"},
    )
    db.add(published)
    draft.status = "published"
    db.commit()
    db.refresh(published)
    return {"status": "published", "published_post_id": published.id, "result": result}


def _normalize_webhook_secret(request: Request, telegram_secret: str | None, smarbiz_secret: str | None) -> str:
    return str(telegram_secret or smarbiz_secret or request.headers.get("x-webhook-secret") or "").strip()


def _webhook_account(db: Session, brand_id: int, provider: str):
    return db.query(m.ChannelAccount).filter_by(brand_id=brand_id, provider=provider, connection_status="connected").first()


def _store_webhook(db: Session, account: m.ChannelAccount, provider: str, payload: dict):
    credentials = decrypt_credentials(account.credentials_encrypted_json or {})
    expected = str(credentials.get("webhook_secret") or "").strip()
    if not expected:
        _structured_error(422, "webhook_secret_missing", "Configure webhook_secret on the connector before accepting webhooks.")
    event_id = str(payload.get("update_id") or payload.get("event_id") or payload.get("id") or sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest())
    existing = db.query(m.WebhookEvent).filter_by(provider=provider, event_id=event_id).first()
    if existing:
        return existing, expected, True
    event_type = "callback_query" if payload.get("callback_query") else "message" if payload.get("message") else str(payload.get("type") or "update")
    event = m.WebhookEvent(provider=provider, event_id=event_id, event_type=event_type, payload_json=payload)
    db.add(event)
    db.flush()
    db.add(m.ConnectorEvent(channel_account_id=account.id, provider=provider, event_type=f"webhook:{event_type}", payload_json={"webhook_event_id": event.id, "event_id": event_id}))
    return event, expected, False


def _health(db: Session):
    health: dict[str, str] = {"api": "healthy"}
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


def install_legacy_cleanup_overrides(app) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    cleanup_routes = {
        ("/brands/{id}/connectors/{provider}/connect", "POST"),
        ("/connectors/{provider}/callback", "GET"),
        ("/drafts/{id}/publish-now", "POST"),
        ("/drafts/{id}/schedule", "POST"),
        ("/scheduled-posts/{id}/retry", "POST"),
        ("/scheduled-posts/{id}/mark-manual-published", "POST"),
        ("/webhooks/telegram/{brand_id}", "POST"),
        ("/webhooks/bale/{brand_id}", "POST"),
        ("/webhooks/bale-safir/{brand_id}", "POST"),
        ("/connectors/telegram/poll", "POST"),
        ("/connectors/bale/poll", "POST"),
        ("/brands/{id}/connectors/bale/test-message", "POST"),
        ("/brands/{id}/connectors/bale/set-webhook", "POST"),
        ("/brands/{id}/connectors/bale/delete-webhook", "POST"),
        ("/brands/{id}/connectors/bale/get-updates", "POST"),
        ("/drafts/{id}/publish-bale", "POST"),
        ("/approvals/{id}/send-bale", "POST"),
        ("/brands/{id}/connectors/bale-safir/connect", "POST"),
        ("/brands/{id}/connectors/bale-safir/test-message", "POST"),
        ("/messages/bale-safir/send", "POST"),
        ("/messages/bale-safir/{message_id}", "GET"),
        ("/published-posts/{id}/fetch-insights", "POST"),
        ("/brands/{id}/analytics/overview", "GET"),
        ("/brands/{id}/reports/generate-weekly", "POST"),
        ("/brands/{id}/assets", "GET"),
        ("/brands/{id}/assets", "POST"),
        ("/assets/{id}", "PATCH"),
        ("/assets/{id}", "DELETE"),
        ("/brands/{id}/dna", "GET"),
        ("/brands/{id}/dna", "PATCH"),
        ("/brands/{id}/memory", "GET"),
        ("/brands/{id}/memory", "POST"),
        ("/brands/{id}/memory/{memory_id}", "PATCH"),
        ("/brands/{id}/drafts", "GET"),
        ("/drafts/{id}", "GET"),
        ("/drafts/{id}", "PATCH"),
        ("/brands/{id}/channel-accounts", "GET"),
        ("/channel-accounts/{id}", "PATCH"),
        ("/approvals/requests/{id}/send-via-telegram", "POST"),
        ("/approvals/requests/{id}/send-via-bale", "POST"),
        ("/admin/overview", "GET"),
        ("/admin/control-tower/overview", "GET"),
        ("/admin/organizations", "GET"),
        ("/admin/organizations/{id}", "PATCH"),
        ("/admin/organizations/{id}/suspend", "POST"),
        ("/admin/organizations/{id}/unsuspend", "POST"),
        ("/admin/users", "GET"),
        ("/admin/users/{id}", "PATCH"),
        ("/admin/users/{id}/disable", "POST"),
        ("/admin/users/{id}/enable", "POST"),
        ("/admin/brands", "GET"),
        ("/admin/ai-usage", "GET"),
        ("/admin/jobs", "GET"),
        ("/admin/jobs/{id}/retry", "POST"),
        ("/admin/jobs/{id}/cancel", "POST"),
        ("/admin/connectors", "GET"),
        ("/admin/connectors/{provider}", "PATCH"),
        ("/admin/audit-logs", "GET"),
        ("/admin/plans", "GET"),
        ("/admin/plans", "POST"),
        ("/admin/plans/{id}", "PATCH"),
        ("/admin/feature-flags", "GET"),
        ("/admin/feature-flags/{id}", "PATCH"),
        ("/admin/feature-flags/{key}", "PATCH"),
        ("/admin/compliance", "GET"),
        ("/admin/system-settings", "GET"),
        ("/admin/system-settings", "PATCH"),
    }
    for path, method in cleanup_routes:
        _remove(app, path, method)

    @app.post("/brands/{id}/connectors/{provider}/connect", name="legacy_connector_connect_secure")
    def legacy_connector_connect(id: int, provider: str, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        provider = provider.strip().lower()
        if provider == "mock":
            _structured_error(422, "mock_disabled", "Mock connectors cannot be created through production API routes.")
        if provider not in KNOWN_PROVIDERS and provider != "bale_safir":
            _structured_error(422, "unknown_provider", "Unknown connector provider.")
        credentials = dict(payload.get("credentials") or payload)
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider=provider).first() or m.ChannelAccount(brand_id=brand.id, provider=provider, account_name=payload.get("account_name") or _provider_label(provider), account_identifier=provider)
        if provider in ASSISTED_PROVIDERS and provider != "bale_safir":
            account.connection_status = "assisted"
            account.credentials_encrypted_json = {}
            account.capabilities_json = get_connector(provider).capabilities.__dict__
        elif provider == "bale_safir":
            account.connection_status = "needs_setup"
            account.credentials_encrypted_json = encrypt_credentials(credentials)
            account.capabilities_json = BaleSafirConnector().capabilities.__dict__
        else:
            account.connection_status = "needs_setup"
            account.credentials_encrypted_json = encrypt_credentials(credentials)
            account.capabilities_json = get_connector(provider).capabilities.__dict__
        db.add(account)
        db.commit()
        return _connection_out(account)

    @app.get("/connectors/{provider}/callback", name="legacy_oauth_callback_truthful")
    def legacy_callback(provider: str):
        _structured_error(409, "oauth_not_enabled", f"Direct OAuth callback for {_provider_label(provider)} is not enabled in this deployment.")

    @app.post("/drafts/{id}/publish-now", name="legacy_publish_now_real")
    def legacy_publish_now(id: int, payload: dict | None = None, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _publish_direct(db, user, id, (payload or {}).get("provider"))

    @app.post("/drafts/{id}/publish-bale", name="legacy_publish_bale_real")
    def legacy_publish_bale(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _publish_direct(db, user, id, "bale")

    @app.post("/drafts/{id}/schedule", name="legacy_schedule_real_time")
    def legacy_schedule(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        draft, brand = _tenant_draft(db, user, id)
        account = _account_for_draft(db, brand, draft, payload.get("provider"))
        raw = payload.get("scheduled_at")
        if not raw:
            _structured_error(422, "scheduled_at_required", "scheduled_at is required; Smarbiz will not silently schedule for now.")
        try:
            scheduled_at = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
            scheduled_at = scheduled_at.astimezone(timezone.utc)
        except ValueError:
            _structured_error(422, "invalid_scheduled_at", "scheduled_at must be an ISO-8601 datetime.")
        post = m.ScheduledPost(draft_id=draft.id, channel_account_id=account.id, scheduled_at=scheduled_at, status="scheduled")
        db.add(post)
        draft.status = "scheduled"
        db.commit()
        return {"id": post.id, "status": post.status, "scheduled_at": post.scheduled_at.isoformat(), "provider": account.provider}

    @app.post("/scheduled-posts/{id}/retry", name="scheduled_retry_real_queue")
    def scheduled_retry(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        post, _, _ = _tenant_scheduled(db, user, id)
        if post.status not in {"failed", "retry", "scheduled"}:
            _structured_error(409, "retry_not_allowed", f"Post cannot be retried from status {post.status}.")
        post.status = "retry"
        post.error_message = None
        post.scheduled_at = datetime.now(timezone.utc)
        db.commit()
        try:
            task = publish_scheduled_post.delay(post.id)
        except Exception as exc:
            post.status = "failed"
            post.error_message = f"Queue unavailable: {exc}"[:2000]
            db.commit()
            _structured_error(503, "queue_unavailable", "Publishing worker queue is unavailable.")
        return {"status": "retry_queued", "task_id": task.id, "scheduled_post_id": post.id}

    @app.post("/scheduled-posts/{id}/mark-manual-published", name="scheduled_manual_publish_evidence")
    def scheduled_manual(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        post, draft, _ = _tenant_scheduled(db, user, id)
        provider_post_id = str(payload.get("provider_post_id") or "").strip()
        public_url = str(payload.get("public_url") or "").strip()
        if not provider_post_id and not public_url:
            _structured_error(422, "publication_evidence_required", "Enter a provider post id or public URL before marking manually published.")
        published = db.query(m.PublishedPost).filter_by(draft_id=draft.id, channel_account_id=post.channel_account_id).first()
        if not published:
            published = m.PublishedPost(draft_id=draft.id, channel_account_id=post.channel_account_id, provider_post_id=provider_post_id or f"manual:{sha256(public_url.encode()).hexdigest()[:20]}", public_url=public_url, status="published", metadata_json={"source": "manual_confirmation", "confirmed_by_user_id": user.id})
            db.add(published)
        post.status = "published"
        post.provider_post_id = published.provider_post_id
        draft.status = "published"
        db.commit()
        return {"status": "published", "published_post_id": published.id, "provider_post_id": published.provider_post_id, "public_url": published.public_url}

    def webhook(provider: str, brand_id: int, payload: dict, request: Request, telegram_secret: str | None, smarbiz_secret: str | None, db: Session):
        account = _webhook_account(db, brand_id, provider)
        if not account:
            _structured_error(404, "connector_not_found", "No connected webhook connector exists for this brand.")
        event, expected, duplicate = _store_webhook(db, account, provider, payload)
        received = _normalize_webhook_secret(request, telegram_secret, smarbiz_secret)
        if not received or received != expected:
            db.rollback()
            _structured_error(401, "invalid_webhook_secret", "Webhook secret is invalid.")
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return {"accepted": True, "duplicate": duplicate, "event_id": event.event_id, "event_type": event.event_type}

    @app.post("/webhooks/telegram/{brand_id}", name="telegram_webhook_verified")
    def telegram_webhook(brand_id: int, payload: dict, request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None), x_smarbiz_webhook_secret: str | None = Header(default=None), db: Session = Depends(get_db)):
        return webhook("telegram", brand_id, payload, request, x_telegram_bot_api_secret_token, x_smarbiz_webhook_secret, db)

    @app.post("/webhooks/bale/{brand_id}", name="bale_webhook_verified")
    def bale_webhook(brand_id: int, payload: dict, request: Request, x_smarbiz_webhook_secret: str | None = Header(default=None), db: Session = Depends(get_db)):
        return webhook("bale", brand_id, payload, request, None, x_smarbiz_webhook_secret, db)

    @app.post("/webhooks/bale-safir/{brand_id}", name="safir_webhook_unavailable")
    def safir_webhook(brand_id: int, payload: dict):
        _structured_error(409, "safir_webhook_not_configured", "Bale Safir message sending is supported, but inbound webhook/status handling is not configured. Smarbiz will not report fake delivery events.")

    def poll_provider(provider: str, user, db: Session):
        _, brand = legacy_main.org_brand_or_404(db, user)
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider=provider, connection_status="connected").first()
        if not account:
            _structured_error(422, "not_connected", f"{_provider_label(provider)} is not connected.")
        connector, _ = _connector_with_credentials(account)
        try:
            result = connector._call("getUpdates", {"timeout": 0, "limit": 100})  # Bot APIs expose this method.
        except (ConnectorError, AttributeError) as exc:
            _structured_error(502, "poll_failed", str(exc))
        return {"updates": result.get("result") or [], "provider": provider}

    @app.post("/connectors/telegram/poll", name="telegram_poll_real")
    def telegram_poll(user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return poll_provider("telegram", user, db)

    @app.post("/connectors/bale/poll", name="bale_poll_real")
    def bale_poll(user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return poll_provider("bale", user, db)

    @app.post("/brands/{id}/connectors/bale/test-message", name="bale_test_message_real")
    def bale_test(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider="bale", connection_status="connected").first()
        if not account:
            _structured_error(422, "not_connected", "Bale is not connected.")
        connector, credentials = _connector_with_credentials(account)
        try:
            result = connector.send_message(payload.get("chat_id") or credentials.get("chat_id"), payload.get("text") or "Smarbiz connection test")
        except ConnectorError as exc:
            _structured_error(502, "bale_send_failed", str(exc))
        return {"sent": True, "provider_result": result}

    @app.post("/brands/{id}/connectors/bale/set-webhook", name="bale_set_webhook_real")
    def bale_set_webhook(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider="bale", connection_status="connected").first()
        if not account:
            _structured_error(422, "not_connected", "Bale is not connected.")
        connector, credentials = _connector_with_credentials(account)
        secret = str(payload.get("webhook_secret") or credentials.get("webhook_secret") or token_urlsafe(24))
        url = str(payload.get("url") or f"{PUBLIC_BASE_URL}/api/webhooks/bale/{brand.id}")
        try:
            result = connector._call("setWebhook", {"url": url})
        except ConnectorError as exc:
            _structured_error(502, "webhook_setup_failed", str(exc))
        account.credentials_encrypted_json = encrypt_credentials({**credentials, "webhook_secret": secret})
        db.commit()
        return {"webhook_set": True, "url": url, "provider_result": result, "secret_generated": "webhook_secret" not in credentials and not payload.get("webhook_secret")}

    @app.post("/brands/{id}/connectors/bale/delete-webhook", name="bale_delete_webhook_real")
    def bale_delete_webhook(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider="bale", connection_status="connected").first()
        if not account:
            _structured_error(422, "not_connected", "Bale is not connected.")
        connector, _ = _connector_with_credentials(account)
        try:
            result = connector._call("deleteWebhook", {})
        except ConnectorError as exc:
            _structured_error(502, "webhook_delete_failed", str(exc))
        return {"webhook_deleted": True, "provider_result": result}

    @app.post("/brands/{id}/connectors/bale/get-updates", name="bale_get_updates_real")
    def bale_get_updates(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _tenant_brand(db, user, id)
        return poll_provider("bale", user, db)

    @app.post("/approvals/requests/{id}/send-via-telegram", name="approval_send_telegram_real")
    def approval_send_telegram(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _send_approval(db, user, id, "telegram")

    @app.post("/approvals/requests/{id}/send-via-bale", name="approval_send_bale_real")
    def approval_send_bale(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _send_approval(db, user, id, "bale")

    @app.post("/approvals/{id}/send-bale", name="legacy_approval_send_bale_real")
    def legacy_approval_send_bale(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _send_approval(db, user, id, "bale")

    @app.post("/brands/{id}/connectors/bale-safir/connect", name="safir_connect_secure")
    def safir_connect(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        credentials = dict(payload.get("credentials") or payload)
        connector = BaleSafirConnector()
        # Safir has no harmless identity endpoint in this integration; connection
        # stays needs_setup until an explicit consented test message succeeds.
        connector._config(credentials)
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider="bale_safir").first() or m.ChannelAccount(brand_id=brand.id, provider="bale_safir", account_name="Bale Safir", account_identifier=str(credentials.get("bot_id") or "bale_safir"))
        account.connection_status = "needs_setup"
        account.capabilities_json = connector.capabilities.__dict__
        account.credentials_encrypted_json = encrypt_credentials(credentials)
        db.add(account)
        db.commit()
        return _connection_out(account)

    @app.post("/brands/{id}/connectors/bale-safir/test-message", name="safir_test_message_real")
    def safir_test(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider="bale_safir").first()
        if not account:
            _structured_error(422, "not_configured", "Configure Bale Safir credentials first.")
        credentials = decrypt_credentials(account.credentials_encrypted_json or {})
        try:
            result = BaleSafirConnector().send_message(payload.get("phone_number"), {"text": payload.get("text") or "Smarbiz connection test"}, credentials, consent=bool(payload.get("consent")))
        except (ConnectorError, ValueError) as exc:
            account.connection_status = "error"
            db.commit()
            _structured_error(502, "safir_send_failed", str(exc))
        account.connection_status = "connected"
        account.last_sync_at = datetime.now(timezone.utc)
        db.commit()
        return {"sent": True, "provider_result": result, "connection": _connection_out(account)}

    @app.post("/messages/bale-safir/send", name="safir_send_real")
    def safir_send(payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, brand = legacy_main.org_brand_or_404(db, user)
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider="bale_safir", connection_status="connected").first()
        if not account:
            _structured_error(422, "not_connected", "Connect and test Bale Safir first.")
        credentials = decrypt_credentials(account.credentials_encrypted_json or {})
        try:
            result = BaleSafirConnector().send_message(payload.get("phone_number"), payload.get("message_data") or {"text": payload.get("text") or ""}, credentials, consent=bool(payload.get("consent")))
        except (ConnectorError, ValueError) as exc:
            _structured_error(502, "safir_send_failed", str(exc))
        db.add(m.ConnectorEvent(channel_account_id=account.id, provider="bale_safir", event_type="message_sent", payload_json={"request_id": result.get("request_id"), "message_id": result.get("message_id"), "phone_number": result.get("phone_number")}))
        db.commit()
        return result

    @app.get("/messages/bale-safir/{message_id}", name="safir_status_truthful")
    def safir_status(message_id: str, user=Depends(legacy_main.user_from_auth)):
        _structured_error(409, "safir_status_unavailable", "This Safir integration can send messages but has no configured delivery-status endpoint. Smarbiz will not return a fake delivered status.", message_id=message_id)

    @app.post("/published-posts/{id}/fetch-insights", name="published_insights_measured_only")
    def published_insights(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        published = db.get(m.PublishedPost, id)
        if not published:
            _structured_error(404, "published_post_not_found", "Published post not found.")
        draft, _ = _tenant_draft(db, user, published.draft_id)
        matched = []
        for row in db.query(m.ManualMetric).filter_by(brand_id=draft.brand_id).all():
            data = row.metrics_json or {}
            if str(data.get("published_post_id") or "") == str(id) or str(data.get("provider_post_id") or "") == str(published.provider_post_id):
                matched.append({"date": row.metric_date, "source": row.source, **data})
        if not matched:
            _structured_error(422, "post_metrics_unavailable", "No measured metrics are linked to this published post. Connect a supported source or add a manual metric with published_post_id/provider_post_id.")
        latest = matched[-1]
        numeric = {key: value for key, value in latest.items() if isinstance(value, (int, float))}
        snapshot = m.InsightSnapshot(published_post_id=id, metrics_json=latest, normalized_scores_json={"source": "measured", "numeric_metrics": numeric})
        db.add(snapshot)
        db.commit()
        return {"id": snapshot.id, "published_post_id": id, "metrics": latest, "source": "measured"}

    @app.get("/brands/{id}/analytics/overview", name="legacy_analytics_measured")
    def legacy_analytics(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        rows = db.query(m.ManualMetric).filter_by(brand_id=brand.id).order_by(m.ManualMetric.metric_date.asc()).all()
        return {"brand_id": brand.id, "measured_records": len(rows), "trends": [{"date": row.metric_date, "source": row.source, "metrics": row.metrics_json or {}} for row in rows], "message": "Only measured connector/manual metrics are returned; no synthetic KPI scores are generated."}

    @app.post("/brands/{id}/reports/generate-weekly", name="legacy_report_factual")
    def legacy_report_generate(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        org = db.get(m.Organization, brand.organization_id)
        today = date.today()
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        stats = _report_stats(db, brand, start.isoformat(), end.isoformat())
        context = _brand_context(db, brand)
        context["workflow_and_performance_data"] = stats
        context["report_period"] = {"start": start.isoformat(), "end": end.isoformat()}
        narrative = None
        try:
            narrative, provider = generate_report_narrative(context)
        except AIConfigurationError:
            provider = None
        except AIProviderError as exc:
            _structured_error(502, "ai_report_failed", "AI report analysis failed.", provider_detail=str(exc)[:500])
        summary = narrative["summary"] if narrative else f"{start.isoformat()}–{end.isoformat()}: {stats['drafts_created']} drafts, {stats['approval_requests']} approval requests, {stats['published_posts']} published posts, {len(stats['measured_metrics'])} measured metric records."
        report = m.WeeklyReport(brand_id=brand.id, week_start=start.isoformat(), week_end=end.isoformat(), summary=summary, insights_json={"highlights": (narrative or {}).get("highlights", []), "metrics": stats, "risks": (narrative or {}).get("risks", []), "analysis_source": "ai" if narrative else "factual"}, recommendations_json={"items": (narrative or {}).get("recommendations", []), "next_week": (narrative or {}).get("next_week_focus", [])})
        db.add(report)
        if provider:
            usage = getattr(provider, "last_usage", {}) or {}
            db.add(m.AIUsageLog(organization_id=org.id, brand_id=brand.id, user_id=user.id, provider=provider.provider_name, model=provider.model, operation="legacy_weekly_report", input_tokens=int(usage.get("input_tokens") or 0), output_tokens=int(usage.get("output_tokens") or 0), cost_estimate=0))
        db.commit()
        db.refresh(report)
        return report

    @app.get("/brands/{id}/assets", name="legacy_assets_tenant_scoped")
    def assets(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        return db.query(m.Asset).filter_by(brand_id=brand.id).all()

    @app.post("/brands/{id}/assets", name="legacy_asset_create_real_metadata")
    def create_asset(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        name = str(payload.get("name") or "").strip()
        if not name:
            _structured_error(422, "asset_name_required", "Asset name is required.")
        row = m.Asset(brand_id=brand.id, name=name, asset_type=payload.get("asset_type") or "reference", url=payload.get("url"), description=payload.get("description") or "", tags_json=payload.get("tags") or [], metadata_json={key: value for key, value in payload.items() if key not in {"credentials", "secret", "token"}})
        db.add(row)
        db.commit()
        return row

    @app.patch("/assets/{id}", name="legacy_asset_patch_tenant")
    def patch_asset(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, _, row = legacy_main._tenant_obj(db, user, m.Asset, id)
        for key in {"name", "asset_type", "url", "description", "tags_json"}:
            if key in payload:
                setattr(row, key, payload[key])
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
        brand = _tenant_brand(db, user, id)
        return db.query(m.BrandDNA).filter_by(brand_id=brand.id).first()

    @app.patch("/brands/{id}/dna", name="legacy_dna_patch_tenant")
    def patch_dna(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
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
        brand = _tenant_brand(db, user, id)
        return db.query(m.BrandMemoryNote).filter_by(brand_id=brand.id).all()

    @app.post("/brands/{id}/memory", name="legacy_memory_add_tenant")
    def add_memory(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        text_value = str(payload.get("note") or "").strip()
        if not text_value:
            _structured_error(422, "memory_note_required", "Memory note cannot be empty.")
        note = m.BrandMemoryNote(brand_id=brand.id, note=text_value, source_type=payload.get("source_type") or "manual", source_id=payload.get("source_id"), accepted_by_user_id=user.id, auto_generated=False, metadata_json=payload.get("metadata") or {})
        db.add(note)
        db.commit()
        return note

    @app.patch("/brands/{id}/memory/{memory_id}", name="legacy_memory_patch_tenant")
    def patch_memory(id: int, memory_id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        note = db.get(m.BrandMemoryNote, memory_id)
        if not note or note.brand_id != brand.id:
            _structured_error(404, "memory_not_found", "Memory note not found.")
        for key in {"note", "confidence_score", "accepted_by_user_id", "rejected_by_user_id", "metadata_json"}:
            if key in payload:
                setattr(note, key, payload[key])
        db.commit()
        return note

    @app.get("/brands/{id}/drafts", name="legacy_drafts_tenant")
    def drafts(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        return db.query(m.ContentDraft).filter_by(brand_id=brand.id).all()

    @app.get("/drafts/{id}", name="legacy_draft_get_tenant")
    def draft_get(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        draft, _ = _tenant_draft(db, user, id)
        return legacy_main._draft_json(draft, db)

    @app.patch("/drafts/{id}", name="legacy_draft_patch_tenant")
    def draft_patch(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        draft, _ = _tenant_draft(db, user, id)
        allowed = {"title", "body", "hashtags_json", "media_asset_ids_json", "status", "language", "content_type"}
        for key, value in payload.items():
            if key in allowed:
                setattr(draft, key, value)
        version = m.ContentVersion(draft_id=draft.id, version_number=db.query(m.ContentVersion).filter_by(draft_id=draft.id).count() + 1, title=draft.title, body=draft.body, metadata_json={"source": "manual_edit"}, created_by_user_id=user.id, ai_generated=False)
        db.add(version)
        db.flush()
        draft.current_version_id = version.id
        db.commit()
        return legacy_main._draft_json(draft, db)

    @app.get("/brands/{id}/channel-accounts", name="legacy_accounts_tenant_redacted")
    def channel_accounts(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _tenant_brand(db, user, id)
        return [_connection_out(row) for row in db.query(m.ChannelAccount).filter_by(brand_id=brand.id).all()]

    @app.patch("/channel-accounts/{id}", name="legacy_account_patch_secure")
    def channel_account_patch(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _, _, account = legacy_main._tenant_obj(db, user, m.ChannelAccount, id)
        if "account_name" in payload:
            account.account_name = payload["account_name"]
        if "credentials" in payload or "credentials_encrypted_json" in payload:
            current = decrypt_credentials(account.credentials_encrypted_json or {})
            incoming = dict(payload.get("credentials") or payload.get("credentials_encrypted_json") or {})
            incoming = {key: value for key, value in incoming.items() if value not in {None, "", "••••••••", "********"}}
            account.credentials_encrypted_json = encrypt_credentials({**current, **incoming})
            account.connection_status = "needs_setup"
        db.commit()
        return _connection_out(account)

    # ----- Super-admin: remove every legacy unprotected duplicate and register one secure surface. -----
    def superadmin(user=Depends(legacy_main.require_super_admin)):
        return user

    def admin_overview(db: Session, user):
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        health = _health(db)
        connector_error_rows = db.query(m.ConnectorEvent).filter(m.ConnectorEvent.event_type.in_(["error", "failed"])).count()
        failed_jobs = db.query(m.JobLog).filter(m.JobLog.status == "failed").count()
        suspended = db.query(m.Organization).filter(m.Organization.suspended_at.is_not(None)).count()
        incidents = []
        if failed_jobs:
            incidents.append({"id": "failed_jobs", "title": "Failed jobs detected", "severity": "warning", "count": failed_jobs, "href": "/app/admin?tab=Jobs"})
        if connector_error_rows:
            incidents.append({"id": "connector_errors", "title": "Connector errors detected", "severity": "warning", "count": connector_error_rows, "href": "/app/admin?tab=Connectors"})
        for service, status in health.items():
            if status in {"error", "unreachable"}:
                incidents.append({"id": f"health_{service}", "title": f"{service} is {status}", "severity": "danger", "count": 1, "href": "/app/admin"})
        orgs = db.query(m.Organization).order_by(m.Organization.created_at.desc()).limit(100).all()
        jobs = db.query(m.JobLog).order_by(m.JobLog.created_at.desc()).limit(100).all()
        return {
            "user": {"id": user.id, "name": user.name, "email": user.email, "is_super_admin": True},
            "system_health": {**health, "connector_errors": "error" if connector_error_rows else "healthy"},
            "summary": {"organizations": db.query(m.Organization).count(), "users": db.query(m.User).count(), "brands": db.query(m.Brand).count(), "active_trials": db.query(m.Organization).filter_by(billing_status="trial").count(), "suspended_orgs": suspended, "ai_requests_24h": db.query(m.AIUsageLog).filter(m.AIUsageLog.created_at >= yesterday).count(), "failed_jobs_24h": db.query(m.JobLog).filter(m.JobLog.status == "failed", m.JobLog.created_at >= yesterday).count(), "connector_errors_24h": db.query(m.ConnectorEvent).filter(m.ConnectorEvent.received_at >= yesterday, m.ConnectorEvent.event_type.in_(["error", "failed"])).count()},
            "incidents": incidents,
            "organizations": [{"id": org.id, "name": org.name, "owner_email": (db.get(m.User, org.owner_user_id).email if org.owner_user_id and db.get(m.User, org.owner_user_id) else None), "status": "suspended" if org.suspended_at else org.billing_status, "plan": (db.get(m.Plan, org.plan_id).name if org.plan_id and db.get(m.Plan, org.plan_id) else None), "created_at": org.created_at.isoformat() if hasattr(org.created_at, "isoformat") else None, "last_event": None} for org in orgs],
            "jobs": [{"id": row.id, "type": row.job_type, "status": row.status, "organization_name": (db.get(m.Organization, row.organization_id).name if row.organization_id and db.get(m.Organization, row.organization_id) else None), "last_error": row.error_message, "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else None, "updated_at": row.finished_at.isoformat() if hasattr(row.finished_at, "isoformat") else None} for row in jobs],
            "connector_errors": [{"id": row.id, "provider": row.provider, "event_type": row.event_type, "received_at": row.received_at.isoformat() if hasattr(row.received_at, "isoformat") else None} for row in db.query(m.ConnectorEvent).filter(m.ConnectorEvent.event_type.in_(["error", "failed"])).order_by(m.ConnectorEvent.received_at.desc()).limit(100).all()],
        }

    @app.get("/admin/overview", name="admin_overview_secure")
    @app.get("/admin/control-tower/overview", name="admin_control_overview_secure")
    def admin_overview_route(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return admin_overview(db, user)

    @app.get("/admin/organizations", name="admin_orgs_secure")
    def admin_orgs(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return admin_overview(db, user)["organizations"]

    @app.post("/admin/organizations/{id}/suspend", name="admin_org_suspend_secure")
    def admin_suspend(id: int, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        org = db.get(m.Organization, id)
        if not org:
            _structured_error(404, "organization_not_found", "Organization not found.")
        org.suspended_at = datetime.now(timezone.utc)
        db.add(m.AuditLog(organization_id=org.id, user_id=user.id, action="organization_suspended", target_type="organization", target_id=str(org.id), metadata_json={}))
        db.commit()
        return {"ok": True, "status": "suspended"}

    @app.post("/admin/organizations/{id}/unsuspend", name="admin_org_unsuspend_secure")
    def admin_unsuspend(id: int, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        org = db.get(m.Organization, id)
        if not org:
            _structured_error(404, "organization_not_found", "Organization not found.")
        org.suspended_at = None
        db.add(m.AuditLog(organization_id=org.id, user_id=user.id, action="organization_unsuspended", target_type="organization", target_id=str(org.id), metadata_json={}))
        db.commit()
        return {"ok": True, "status": "active"}

    @app.patch("/admin/organizations/{id}", name="admin_org_patch_secure")
    def admin_org_patch(id: int, payload: dict, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        org = db.get(m.Organization, id)
        if not org:
            _structured_error(404, "organization_not_found", "Organization not found.")
        for key in {"name", "mode", "billing_status", "plan_id"}:
            if key in payload:
                setattr(org, key, payload[key])
        db.commit()
        return {"id": org.id, "name": org.name, "mode": org.mode, "billing_status": org.billing_status, "plan_id": org.plan_id}

    @app.get("/admin/users", name="admin_users_secure")
    def admin_users(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "email": row.email, "name": row.name, "status": "active" if row.is_active else "disabled", "is_super_admin": row.is_super_admin, "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else None} for row in db.query(m.User).order_by(m.User.created_at.desc()).limit(500).all()]

    @app.patch("/admin/users/{id}", name="admin_user_patch_secure")
    def admin_user_patch(id: int, payload: dict, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        row = db.get(m.User, id)
        if not row:
            _structured_error(404, "user_not_found", "User not found.")
        for key in {"name", "locale", "timezone", "is_active", "is_super_admin"}:
            if key in payload:
                setattr(row, key, payload[key])
        db.commit()
        return {"id": row.id, "email": row.email, "name": row.name, "is_active": row.is_active, "is_super_admin": row.is_super_admin}

    @app.post("/admin/users/{id}/disable", name="admin_user_disable_secure")
    def admin_user_disable(id: int, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return admin_user_patch(id, {"is_active": False}, user, db)

    @app.post("/admin/users/{id}/enable", name="admin_user_enable_secure")
    def admin_user_enable(id: int, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return admin_user_patch(id, {"is_active": True}, user, db)

    @app.get("/admin/brands", name="admin_brands_secure")
    def admin_brands(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "name": row.name, "organization_id": row.organization_id, "industry": row.industry, "country": row.country, "status": row.status, "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else None} for row in db.query(m.Brand).order_by(m.Brand.created_at.desc()).limit(500).all()]

    @app.get("/admin/ai-usage", name="admin_ai_usage_secure")
    def admin_ai_usage(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "organization_id": row.organization_id, "brand_id": row.brand_id, "user_id": row.user_id, "provider": row.provider, "model": row.model, "operation": row.operation, "input_tokens": row.input_tokens, "output_tokens": row.output_tokens, "cost_estimate": float(row.cost_estimate or 0), "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else None} for row in db.query(m.AIUsageLog).order_by(m.AIUsageLog.created_at.desc()).limit(1000).all()]

    @app.get("/admin/connectors", name="admin_connectors_secure")
    def admin_connectors(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "brand_id": row.brand_id, "provider": row.provider, "status": row.connection_status, "account_name": row.account_name, "last_sync_at": row.last_sync_at.isoformat() if hasattr(row.last_sync_at, "isoformat") else None, "last_test_status": (row.capabilities_json or {}).get("last_test_status"), "last_test_message": (row.capabilities_json or {}).get("last_test_message")} for row in db.query(m.ChannelAccount).order_by(m.ChannelAccount.updated_at.desc()).limit(1000).all()]

    @app.patch("/admin/connectors/{provider}", name="admin_connector_patch_truthful")
    def admin_connector_patch(provider: str, payload: dict, user=Depends(legacy_main.require_super_admin)):
        _structured_error(409, "tenant_credentials_managed_in_workspace", "Connector credentials are tenant-scoped. Configure them in the workspace Integrations page rather than a global admin toggle.")

    @app.get("/admin/jobs", name="admin_jobs_secure")
    def admin_jobs(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return admin_overview(db, user)["jobs"]

    @app.post("/admin/jobs/{id}/retry", name="admin_job_retry_real")
    def admin_job_retry(id: int, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
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
    def admin_job_cancel(id: int, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
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
    def admin_compliance(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        drafts = db.query(m.ContentDraft).filter(m.ContentDraft.compliance_score < 0.8).order_by(m.ContentDraft.updated_at.desc()).limit(200).all()
        rules = db.query(m.BrandRule).filter_by(is_active=True).count()
        events = []
        for draft in drafts:
            metadata = {}
            if draft.current_version_id:
                version = db.get(m.ContentVersion, draft.current_version_id)
                metadata = version.metadata_json or {} if version else {}
            events.append({"id": draft.id, "brand_id": draft.brand_id, "title": draft.title, "compliance_score": round(float(draft.compliance_score or 0) * 100), "status": draft.status, "warnings": metadata.get("warnings") or (metadata.get("compliance_result") or {}).get("warnings") or []})
        return {"active_brand_rules": rules, "flagged_drafts": events, "flagged_count": len(events)}

    @app.get("/admin/plans", name="admin_plans_secure")
    def admin_plans(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "name": row.name, "price_monthly": float(row.price_monthly or 0), "currency": row.currency, "active": row.active, "limits": row.limits_json or {}, "features": row.features_json or {}} for row in db.query(m.Plan).all()]

    @app.post("/admin/plans", name="admin_plan_create_secure")
    def admin_plan_create(payload: dict, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        if not str(payload.get("name") or "").strip():
            _structured_error(422, "plan_name_required", "Plan name is required.")
        row = m.Plan(name=payload["name"], price_monthly=payload.get("price_monthly", 0), currency=payload.get("currency", "EUR"), limits_json=payload.get("limits_json") or {}, features_json=payload.get("features_json") or {}, active=payload.get("active", True))
        db.add(row)
        db.commit()
        return admin_plans(user, db)[-1]

    @app.patch("/admin/plans/{id}", name="admin_plan_patch_secure")
    def admin_plan_patch(id: int, payload: dict, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        row = db.get(m.Plan, id)
        if not row:
            _structured_error(404, "plan_not_found", "Plan not found.")
        for key in {"name", "price_monthly", "currency", "limits_json", "features_json", "active"}:
            if key in payload:
                setattr(row, key, payload[key])
        db.commit()
        return {"id": row.id, "name": row.name, "price_monthly": float(row.price_monthly or 0), "currency": row.currency, "active": row.active, "limits": row.limits_json or {}, "features": row.features_json or {}}

    @app.get("/admin/feature-flags", name="admin_flags_secure")
    def admin_flags(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "key": row.key, "enabled": row.enabled, "rollout_percentage": row.rollout_percentage, "organization_ids": row.organization_ids_json or [], "metadata": row.metadata_json or {}} for row in db.query(m.FeatureFlag).order_by(m.FeatureFlag.key.asc()).all()]

    @app.patch("/admin/feature-flags/{key}", name="admin_flag_patch_secure")
    def admin_flag_patch(key: str, payload: dict, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        row = db.query(m.FeatureFlag).filter_by(key=key).first() or m.FeatureFlag(key=key)
        for field in {"enabled", "rollout_percentage", "organization_ids_json", "metadata_json"}:
            if field in payload:
                setattr(row, field, payload[field])
        row.rollout_percentage = max(0, min(100, int(row.rollout_percentage or 0)))
        db.add(row)
        db.commit()
        return {"id": row.id, "key": row.key, "enabled": row.enabled, "rollout_percentage": row.rollout_percentage, "organization_ids": row.organization_ids_json or [], "metadata": row.metadata_json or {}}

    @app.patch("/admin/feature-flags/{id}", name="admin_flag_patch_id_secure")
    def admin_flag_patch_id(id: int, payload: dict, user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        row = db.get(m.FeatureFlag, id)
        if not row:
            _structured_error(404, "feature_flag_not_found", "Feature flag not found.")
        return admin_flag_patch(row.key, payload, user, db)

    @app.get("/admin/audit-logs", name="admin_audit_secure")
    def admin_audit(user=Depends(legacy_main.require_super_admin), db: Session = Depends(get_db)):
        return [{"id": row.id, "organization_id": row.organization_id, "brand_id": row.brand_id, "user_id": row.user_id, "action": row.action, "target_type": row.target_type, "target_id": row.target_id, "metadata": row.metadata_json or {}, "created_at": row.created_at.isoformat() if hasattr(row.created_at, "isoformat") else None} for row in db.query(m.AuditLog).order_by(m.AuditLog.created_at.desc()).limit(1000).all()]

    @app.get("/admin/system-settings", name="admin_system_settings_truthful")
    def admin_system_settings(user=Depends(legacy_main.require_super_admin)):
        return {"platform_mode": "demo" if legacy_main.DEMO_MODE else "production", "cors_origins": legacy_main.cors_origins, "signup_enabled": True, "maintenance_mode": False, "default_ai_provider": os.getenv("AI_PROVIDER") or "mock", "ai_model": os.getenv("OPENAI_MODEL") or "gpt-5.6-sol", "environment_managed": True}

    @app.patch("/admin/system-settings", name="admin_system_settings_env_managed")
    def admin_system_settings_patch(payload: dict, user=Depends(legacy_main.require_super_admin)):
        _structured_error(409, "environment_managed", "System settings are deployment environment values and cannot be changed by an API acknowledgement-only route.")
