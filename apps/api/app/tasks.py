"""Background jobs for scheduled Smarbiz operations.

Scheduled posts are published only when a real connector confirms success. The
worker never treats assisted or test responses as direct publication in
production.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from celery import Celery
from sqlalchemy import update

from . import models as m
from .database import SessionLocal, settings
from .services.connectors.providers import get_connector
from .services.connectors.secrets import decrypt_credentials


celery_app = Celery(
    "smarbiz",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    result_expires=60 * 60 * 24,
    beat_schedule={
        "publish-due-posts-every-minute": {
            "task": "smarbiz.publish_due_posts",
            "schedule": 60.0,
        },
    },
)

MAX_PUBLISH_RETRIES = 5
REAL_SUCCESS_STATUSES = {"published", "success", "sent"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _configure_connector(connector: Any, credentials: dict[str, Any]) -> Any:
    for key, value in credentials.items():
        if not isinstance(key, str) or key.startswith("_"):
            continue
        if isinstance(value, (str, int, float, bool, dict, list)) or value is None:
            try:
                setattr(connector, key, value)
            except (AttributeError, TypeError):
                pass
    return connector


def _publish_with_compat(connector: Any, draft: m.ContentDraft, account: m.ChannelAccount):
    """Support older/custom connector implementations that accept only draft.

    The fallback is intentionally limited to Python signature compatibility. It
    does not alter the response validation rules below, so production still
    requires a provider-confirmed success/id.
    """
    try:
        return connector.publish_post(draft, account=account)
    except TypeError as exc:
        message = str(exc)
        if "unexpected keyword argument 'account'" not in message and 'unexpected keyword argument "account"' not in message:
            raise
        return connector.publish_post(draft)


def _claim_scheduled_post(post_id: int) -> bool:
    with SessionLocal() as db:
        result = db.execute(
            update(m.ScheduledPost)
            .where(
                m.ScheduledPost.id == post_id,
                m.ScheduledPost.status.in_(["scheduled", "retry"]),
            )
            .values(status="processing", error_message=None)
        )
        db.commit()
        return bool(result.rowcount)


def _fail(post_id: int, message: str) -> dict[str, Any]:
    with SessionLocal() as db:
        post = db.get(m.ScheduledPost, post_id)
        if not post:
            return {"ok": False, "post_id": post_id, "error": "not_found"}
        post.retry_count = int(post.retry_count or 0) + 1
        post.error_message = message[:2000]
        if post.retry_count >= MAX_PUBLISH_RETRIES:
            post.status = "failed"
        else:
            post.status = "retry"
            delay_minutes = min(60, 2 ** post.retry_count)
            post.scheduled_at = _now() + timedelta(minutes=delay_minutes)
        db.commit()
        return {
            "ok": False,
            "post_id": post_id,
            "status": post.status,
            "retry_count": post.retry_count,
            "error": post.error_message,
        }


@celery_app.task(name="smarbiz.publish_due_posts")
def publish_due_posts(batch_size: int = 100) -> dict[str, Any]:
    now = _now()
    with SessionLocal() as db:
        rows = (
            db.query(m.ScheduledPost.id)
            .filter(
                m.ScheduledPost.status.in_(["scheduled", "retry"]),
                m.ScheduledPost.scheduled_at.is_not(None),
                m.ScheduledPost.scheduled_at <= now,
            )
            .order_by(m.ScheduledPost.scheduled_at.asc())
            .limit(max(1, min(int(batch_size), 500)))
            .all()
        )
    ids = [row[0] for row in rows]
    for post_id in ids:
        publish_scheduled_post.delay(post_id)
    return {"ok": True, "queued": len(ids), "post_ids": ids}


@celery_app.task(name="smarbiz.publish_scheduled_post", bind=True, autoretry_for=())
def publish_scheduled_post(self, post_id: int) -> dict[str, Any]:
    if not _claim_scheduled_post(post_id):
        return {"ok": True, "post_id": post_id, "status": "already_claimed"}

    try:
        with SessionLocal() as db:
            post = db.get(m.ScheduledPost, post_id)
            if not post:
                raise RuntimeError("Scheduled post not found")
            draft = db.get(m.ContentDraft, post.draft_id)
            account = db.get(m.ChannelAccount, post.channel_account_id)
            if not draft:
                raise RuntimeError("Linked content draft no longer exists")
            if not account:
                raise RuntimeError("Linked channel connection no longer exists")

            existing = db.query(m.PublishedPost).filter_by(draft_id=draft.id, channel_account_id=account.id).first()
            if existing:
                post.status = "published"
                post.provider_post_id = existing.provider_post_id
                draft.status = "published"
                db.commit()
                return {"ok": True, "post_id": post_id, "status": "already_published", "published_post_id": existing.id}

            if account.connection_status != "connected":
                raise RuntimeError(f"Connector {account.provider} is not connected (status={account.connection_status})")
            if account.provider == "mock" and not settings.allow_mock_connectors:
                raise RuntimeError("Mock publishing is disabled in this environment")
            if account.provider in {"approval_link", "ga4", "woocommerce", "brevo"}:
                raise RuntimeError(f"Connector {account.provider} cannot publish social content")

            credentials = decrypt_credentials(account.credentials_encrypted_json or {})
            connector = _configure_connector(get_connector(account.provider), credentials)
            response = _publish_with_compat(connector, draft, account)
            if not isinstance(response, dict):
                raise RuntimeError("Connector returned an invalid response")

            response_status = str(response.get("status") or "").lower()
            is_mock = bool(response.get("mock")) or response_status.startswith("mock")
            is_assisted = response_status in {"assisted", "prepared", "manual", "needs_manual_action"}
            if is_mock and not settings.allow_mock_connectors:
                raise RuntimeError("Connector returned a mock publishing result")
            if is_assisted:
                post.status = "assisted"
                post.assisted_publish_url = response.get("url") or response.get("assisted_publish_url")
                post.error_message = "Direct publishing is unavailable; an assisted publishing kit was prepared."
                db.commit()
                return {"ok": True, "post_id": post_id, "status": "assisted", "assisted_publish_url": post.assisted_publish_url}

            # Explicit test/dev environments may exercise MockConnector. It is
            # accepted there only; production has already rejected it above.
            confirmed_status = response_status in REAL_SUCCESS_STATUSES or (is_mock and settings.allow_mock_connectors and response_status == "mock_published")
            if not confirmed_status:
                message = response.get("error") or response.get("message") or f"Connector did not confirm publication (status={response_status or 'missing'})"
                raise RuntimeError(str(message))

            provider_post_id = str(response.get("provider_post_id") or response.get("message_id") or response.get("id") or "")
            if not provider_post_id:
                raise RuntimeError("Provider confirmed success without a provider post/message id")
            public_url = str(response.get("public_url") or response.get("url") or response.get("permalink") or "")
            published = m.PublishedPost(
                draft_id=draft.id,
                channel_account_id=account.id,
                provider_post_id=provider_post_id,
                public_url=public_url,
                status="published",
                metadata_json={
                    "scheduled_post_id": post.id,
                    "provider": account.provider,
                    "connector_response": {
                        key: value
                        for key, value in response.items()
                        if key not in {"token", "api_key", "secret", "credentials", "consumer_secret"}
                    },
                },
            )
            db.add(published)
            post.status = "published"
            post.provider_post_id = provider_post_id
            post.error_message = None
            draft.status = "published"
            db.commit()
            db.refresh(published)
            return {
                "ok": True,
                "post_id": post_id,
                "status": "published",
                "published_post_id": published.id,
                "provider_post_id": provider_post_id,
                "public_url": public_url,
            }
    except Exception as exc:
        return _fail(post_id, str(exc))
