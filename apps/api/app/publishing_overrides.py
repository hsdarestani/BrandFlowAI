from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from secrets import token_urlsafe

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from . import main as legacy_main
from . import models as m
from .database import get_db
from .production_overrides import PUBLIC_BASE_URL, _brand_context, _connector_with_credentials, _provider_label, _report_stats, _structured_error
from .services.ai.content_engine import generate_report_narrative
from .services.ai.providers import AIConfigurationError, AIProviderError
from .services.connectors.bale_safir import BaleSafirConnector
from .services.connectors.base import ConnectorError, ConnectorNotSupported
from .services.connectors.providers import ASSISTED_PROVIDERS, KNOWN_PROVIDERS, get_connector
from .services.connectors.secrets import decrypt_credentials, encrypt_credentials
from .tasks import publish_scheduled_post


_INSTALLED = False


def _remove(app, path: str, method: str) -> None:
    method = method.upper()
    app.router.routes = [r for r in app.router.routes if not (getattr(r, "path", None) == path and method in (getattr(r, "methods", set()) or set()))]


def _brand(db: Session, user, brand_id: int):
    _, brand = legacy_main.org_brand_or_404(db, user, brand_id)
    return brand


def _draft(db: Session, user, draft_id: int):
    row = db.get(m.ContentDraft, draft_id)
    if not row:
        _structured_error(404, "draft_not_found", "Draft not found.")
    _, brand = legacy_main.org_brand_or_404(db, user, row.brand_id)
    return row, brand


def _scheduled(db: Session, user, post_id: int):
    row = db.get(m.ScheduledPost, post_id)
    if not row:
        _structured_error(404, "scheduled_post_not_found", "Scheduled post not found.")
    draft, brand = _draft(db, user, row.draft_id)
    return row, draft, brand


def _account(db: Session, brand: m.Brand, draft: m.ContentDraft, requested: str | None = None):
    provider = str(requested or draft.channel or "").strip().lower()
    if not provider:
        _structured_error(422, "channel_required", "Choose a channel first.")
    account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider=provider).first()
    if not account:
        _structured_error(422, "channel_not_configured", f"Configure {_provider_label(provider)} in Integrations first.", href="/app/integrations")
    return account


def _approval_token(db: Session, approval_id: int) -> str | None:
    action = (
        db.query(m.ApprovalAction)
        .filter_by(approval_request_id=approval_id, action="created")
        .filter(m.ApprovalAction.source_message_id.is_not(None))
        .order_by(m.ApprovalAction.id.asc())
        .first()
    )
    return action.source_message_id if action else None


def _send_approval(db: Session, user, approval_id: int, provider: str):
    approval = legacy_main._approval_for_user(db, user, approval_id)
    draft = db.get(m.ContentDraft, approval.draft_id)
    if not draft:
        _structured_error(404, "draft_not_found", "Approval draft no longer exists.")
    account = db.query(m.ChannelAccount).filter_by(brand_id=draft.brand_id, provider=provider, connection_status="connected").first()
    if not account:
        _structured_error(422, "not_connected", f"{_provider_label(provider)} is not connected.", href="/app/integrations")
    token = _approval_token(db, approval.id)
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
            response = connector.send_message(recipient, f"{draft.title}\n\nReview and approve: {url}", subject=f"Approval: {draft.title}", sender_email=credentials.get("sender_email"), sender_name=credentials.get("sender_name") or "Smarbiz")
        else:
            raise ConnectorNotSupported(f"Approval delivery is not implemented for {provider}")
    except ConnectorError as exc:
        _structured_error(502, "approval_delivery_failed", str(exc))
    db.add(m.ApprovalAction(approval_request_id=approval.id, user_id=user.id, action="sent", comment=f"Sent via {provider}", source_channel=provider, source_message_id=str((response or {}).get("message_id") or (response or {}).get("request_id") or "") or None, save_to_memory=False))
    db.commit()
    return {"sent": True, "channel": provider, "approval_url": f"/public/approval/{token}", "provider_result": response}


def _publish(db: Session, user, draft_id: int, requested_provider: str | None = None):
    draft, brand = _draft(db, user, draft_id)
    account = _account(db, brand, draft, requested_provider)
    connector, _ = _connector_with_credentials(account)
    if account.connection_status == "assisted" or (connector.capabilities.assisted_publish and not connector.capabilities.direct_publish):
        result = connector.publish_post(draft, account=account)
        return {"status": "assisted", "result": result, "published_post_id": None, "message": "Direct publishing is unavailable; no fake PublishedPost was created."}
    if account.connection_status != "connected":
        _structured_error(422, "channel_not_connected", "Run a successful live connection test before publishing.", href="/app/integrations")
    if not connector.capabilities.direct_publish:
        _structured_error(422, "direct_publish_unavailable", "This provider is not configured for direct publishing.")
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
    published = m.PublishedPost(draft_id=draft.id, channel_account_id=account.id, provider_post_id=provider_post_id, public_url=str((result or {}).get("public_url") or ""), status="published", metadata_json={"provider": account.provider, "source": "publish_now"})
    db.add(published)
    draft.status = "published"
    db.commit()
    db.refresh(published)
    return {"status": "published", "published_post_id": published.id, "result": result}


def install_publishing_overrides(app) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    paths = {
        ("/brands/{id}/connectors/{provider}/connect", "POST"),
        ("/connectors/{provider}/callback", "GET"),
        ("/drafts/{id}/publish-now", "POST"),
        ("/drafts/{id}/publish-bale", "POST"),
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
        ("/approvals/requests/{id}/send-via-telegram", "POST"),
        ("/approvals/requests/{id}/send-via-bale", "POST"),
        ("/approvals/{id}/send-bale", "POST"),
        ("/brands/{id}/connectors/bale-safir/connect", "POST"),
        ("/brands/{id}/connectors/bale-safir/test-message", "POST"),
        ("/messages/bale-safir/send", "POST"),
        ("/messages/bale-safir/{message_id}", "GET"),
        ("/published-posts/{id}/fetch-insights", "POST"),
        ("/brands/{id}/analytics/overview", "GET"),
        ("/brands/{id}/reports/generate-weekly", "POST"),
    }
    for path, method in paths:
        _remove(app, path, method)

    @app.post("/brands/{id}/connectors/{provider}/connect", name="legacy_connector_connect_secure")
    def connect(id: int, provider: str, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
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
            BaleSafirConnector()._config(credentials)
            account.connection_status = "needs_setup"
            account.credentials_encrypted_json = encrypt_credentials(credentials)
            account.capabilities_json = BaleSafirConnector().capabilities.__dict__
        else:
            account.connection_status = "needs_setup"
            account.credentials_encrypted_json = encrypt_credentials(credentials)
            account.capabilities_json = get_connector(provider).capabilities.__dict__
        db.add(account)
        db.commit()
        return {"id": account.id, "provider": account.provider, "status": account.connection_status, "account_name": account.account_name}

    @app.get("/connectors/{provider}/callback", name="legacy_oauth_callback_truthful")
    def callback(provider: str):
        _structured_error(409, "oauth_not_enabled", f"Direct OAuth callback for {_provider_label(provider)} is not enabled in this deployment.")

    @app.post("/drafts/{id}/publish-now", name="legacy_publish_now_real")
    def publish_now(id: int, payload: dict | None = None, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _publish(db, user, id, (payload or {}).get("provider"))

    @app.post("/drafts/{id}/publish-bale", name="legacy_publish_bale_real")
    def publish_bale(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _publish(db, user, id, "bale")

    @app.post("/drafts/{id}/schedule", name="legacy_schedule_real_time")
    def schedule(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        draft, brand = _draft(db, user, id)
        account = _account(db, brand, draft, payload.get("provider"))
        raw = payload.get("scheduled_at")
        if not raw:
            _structured_error(422, "scheduled_at_required", "scheduled_at is required; Smarbiz will not silently schedule for the current time.")
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
    def retry(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        post, _, _ = _scheduled(db, user, id)
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
    def manual(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        post, draft, _ = _scheduled(db, user, id)
        provider_post_id = str(payload.get("provider_post_id") or "").strip()
        public_url = str(payload.get("public_url") or "").strip()
        if not provider_post_id and not public_url:
            _structured_error(422, "publication_evidence_required", "Enter a provider post id or public URL before marking manually published.")
        published = db.query(m.PublishedPost).filter_by(draft_id=draft.id, channel_account_id=post.channel_account_id).first()
        if not published:
            published = m.PublishedPost(draft_id=draft.id, channel_account_id=post.channel_account_id, provider_post_id=provider_post_id or f"manual:{sha256(public_url.encode()).hexdigest()[:20]}", public_url=public_url, status="published", metadata_json={"source": "manual_confirmation", "confirmed_by_user_id": user.id})
            db.add(published)
            db.flush()
        post.status = "published"
        post.provider_post_id = published.provider_post_id
        draft.status = "published"
        db.commit()
        return {"status": "published", "published_post_id": published.id, "provider_post_id": published.provider_post_id, "public_url": published.public_url}

    def poll(provider: str, user, db: Session):
        _, brand = legacy_main.org_brand_or_404(db, user)
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider=provider, connection_status="connected").first()
        if not account:
            _structured_error(422, "not_connected", f"{_provider_label(provider)} is not connected.")
        connector, _ = _connector_with_credentials(account)
        try:
            result = connector._call("getUpdates", {"timeout": 0, "limit": 100})
        except (ConnectorError, AttributeError) as exc:
            _structured_error(502, "poll_failed", str(exc))
        return {"updates": result.get("result") or [], "provider": provider}

    @app.post("/connectors/telegram/poll", name="telegram_poll_real")
    def telegram_poll(user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return poll("telegram", user, db)

    @app.post("/connectors/bale/poll", name="bale_poll_real")
    def bale_poll(user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return poll("bale", user, db)

    def verified_webhook(provider: str, brand_id: int, payload: dict, received_secret: str, db: Session):
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand_id, provider=provider, connection_status="connected").first()
        if not account:
            _structured_error(404, "connector_not_found", "No connected webhook connector exists for this brand.")
        credentials = decrypt_credentials(account.credentials_encrypted_json or {})
        expected = str(credentials.get("webhook_secret") or "").strip()
        if not expected:
            _structured_error(422, "webhook_secret_missing", "Configure webhook_secret before accepting webhooks.")
        if not received_secret or received_secret != expected:
            _structured_error(401, "invalid_webhook_secret", "Webhook secret is invalid.")
        event_id = str(payload.get("update_id") or payload.get("event_id") or payload.get("id") or sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest())
        existing = db.query(m.WebhookEvent).filter_by(provider=provider, event_id=event_id).first()
        if existing:
            return {"accepted": True, "duplicate": True, "event_id": event_id}
        event_type = "callback_query" if payload.get("callback_query") else "message" if payload.get("message") else str(payload.get("type") or "update")
        event = m.WebhookEvent(provider=provider, event_id=event_id, event_type=event_type, payload_json=payload, processed_at=datetime.now(timezone.utc))
        db.add(event)
        db.flush()
        db.add(m.ConnectorEvent(channel_account_id=account.id, provider=provider, event_type=f"webhook:{event_type}", payload_json={"webhook_event_id": event.id, "event_id": event_id}))
        db.commit()
        return {"accepted": True, "duplicate": False, "event_id": event_id, "event_type": event_type}

    @app.post("/webhooks/telegram/{brand_id}", name="telegram_webhook_verified")
    def telegram_webhook(brand_id: int, payload: dict, request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None), x_smarbiz_webhook_secret: str | None = Header(default=None), db: Session = Depends(get_db)):
        secret = str(x_telegram_bot_api_secret_token or x_smarbiz_webhook_secret or request.headers.get("x-webhook-secret") or "")
        return verified_webhook("telegram", brand_id, payload, secret, db)

    @app.post("/webhooks/bale/{brand_id}", name="bale_webhook_verified")
    def bale_webhook(brand_id: int, payload: dict, request: Request, x_smarbiz_webhook_secret: str | None = Header(default=None), db: Session = Depends(get_db)):
        secret = str(x_smarbiz_webhook_secret or request.headers.get("x-webhook-secret") or "")
        return verified_webhook("bale", brand_id, payload, secret, db)

    @app.post("/webhooks/bale-safir/{brand_id}", name="safir_webhook_truthful")
    def safir_webhook(brand_id: int, payload: dict):
        _structured_error(409, "safir_webhook_not_configured", "Bale Safir sending is supported, but inbound status/webhook handling is not configured. Smarbiz will not report fake delivery events.")

    @app.post("/brands/{id}/connectors/bale/test-message", name="bale_test_message_real")
    def bale_test(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
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
        brand = _brand(db, user, id)
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
        brand = _brand(db, user, id)
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
    def bale_updates(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        _brand(db, user, id)
        return poll("bale", user, db)

    @app.post("/approvals/requests/{id}/send-via-telegram", name="approval_send_telegram_real")
    def approval_send_telegram(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _send_approval(db, user, id, "telegram")

    @app.post("/approvals/requests/{id}/send-via-bale", name="approval_send_bale_real")
    def approval_send_bale(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _send_approval(db, user, id, "bale")

    @app.post("/approvals/{id}/send-bale", name="legacy_approval_send_bale_real")
    def approval_send_bale_legacy(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _send_approval(db, user, id, "bale")

    @app.post("/brands/{id}/connectors/bale-safir/connect", name="safir_connect_secure")
    def safir_connect(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
        credentials = dict(payload.get("credentials") or payload)
        connector = BaleSafirConnector()
        connector._config(credentials)
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider="bale_safir").first() or m.ChannelAccount(brand_id=brand.id, provider="bale_safir", account_name="Bale Safir", account_identifier=str(credentials.get("bot_id") or "bale_safir"))
        account.connection_status = "needs_setup"
        account.capabilities_json = connector.capabilities.__dict__
        account.credentials_encrypted_json = encrypt_credentials(credentials)
        db.add(account)
        db.commit()
        return {"id": account.id, "provider": "bale_safir", "status": account.connection_status}

    @app.post("/brands/{id}/connectors/bale-safir/test-message", name="safir_test_message_real")
    def safir_test(id: int, payload: dict, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
        account = db.query(m.ChannelAccount).filter_by(brand_id=brand.id, provider="bale_safir").first()
        if not account:
            _structured_error(422, "not_configured", "Configure Bale Safir first.")
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
        return {"sent": True, "provider_result": result, "status": "connected"}

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
        db.add(m.ConnectorEvent(channel_account_id=account.id, provider="bale_safir", event_type="message_sent", payload_json={"request_id": result.get("request_id"), "message_id": result.get("message_id")}))
        db.commit()
        return result

    @app.get("/messages/bale-safir/{message_id}", name="safir_status_truthful")
    def safir_status(message_id: str, user=Depends(legacy_main.user_from_auth)):
        _structured_error(409, "safir_status_unavailable", "This Safir integration has no configured delivery-status endpoint. Smarbiz will not return a fake delivered status.", message_id=message_id)

    @app.post("/published-posts/{id}/fetch-insights", name="published_insights_measured_only")
    def fetch_post_insights(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        published = db.get(m.PublishedPost, id)
        if not published:
            _structured_error(404, "published_post_not_found", "Published post not found.")
        draft, _ = _draft(db, user, published.draft_id)
        matches = []
        for row in db.query(m.ManualMetric).filter_by(brand_id=draft.brand_id).all():
            data = row.metrics_json or {}
            if str(data.get("published_post_id") or "") == str(id) or str(data.get("provider_post_id") or "") == str(published.provider_post_id):
                matches.append({"date": row.metric_date, "source": row.source, **data})
        if not matches:
            _structured_error(422, "post_metrics_unavailable", "No measured metrics are linked to this post. Smarbiz will not fabricate insight scores.")
        latest = matches[-1]
        numeric = {k: v for k, v in latest.items() if isinstance(v, (int, float))}
        snapshot = m.InsightSnapshot(published_post_id=id, metrics_json=latest, normalized_scores_json={"source": "measured", "numeric_metrics": numeric})
        db.add(snapshot)
        db.commit()
        return {"id": snapshot.id, "published_post_id": id, "metrics": latest, "source": "measured"}

    @app.get("/brands/{id}/analytics/overview", name="legacy_analytics_measured")
    def analytics(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
        rows = db.query(m.ManualMetric).filter_by(brand_id=brand.id).order_by(m.ManualMetric.metric_date.asc()).all()
        return {"brand_id": brand.id, "measured_records": len(rows), "trends": [{"date": row.metric_date, "source": row.source, "metrics": row.metrics_json or {}} for row in rows], "message": "Only measured connector/manual metrics are returned; no synthetic KPI scores are generated."}

    @app.post("/brands/{id}/reports/generate-weekly", name="legacy_report_factual")
    def report(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        brand = _brand(db, user, id)
        today = date.today()
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        stats = _report_stats(db, brand, start.isoformat(), end.isoformat())
        context = _brand_context(db, brand)
        context["workflow_and_performance_data"] = stats
        context["report_period"] = {"start": start.isoformat(), "end": end.isoformat()}
        narrative = None
        try:
            narrative, _provider = generate_report_narrative(context)
        except AIConfigurationError:
            pass
        except AIProviderError as exc:
            _structured_error(502, "ai_report_failed", "AI report analysis failed.", provider_detail=str(exc)[:500])
        summary = narrative["summary"] if narrative else f"{start.isoformat()}–{end.isoformat()}: {stats['drafts_created']} drafts, {stats['approval_requests']} approval requests, {stats['published_posts']} published posts, {len(stats['measured_metrics'])} measured metric records."
        row = m.WeeklyReport(brand_id=brand.id, week_start=start.isoformat(), week_end=end.isoformat(), summary=summary, insights_json={"highlights": (narrative or {}).get("highlights", []), "metrics": stats, "risks": (narrative or {}).get("risks", []), "analysis_source": "ai" if narrative else "factual"}, recommendations_json={"items": (narrative or {}).get("recommendations", []), "next_week": (narrative or {}).get("next_week_focus", [])})
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
