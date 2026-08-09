from __future__ import annotations

from hashlib import sha256
from secrets import token_urlsafe

from fastapi import Depends
from sqlalchemy.orm import Session

from . import main as legacy_main
from . import models as m
from .database import get_db
from .production_overrides import PUBLIC_BASE_URL, _connector_with_credentials, _provider_label, _structured_error
from .services.connectors.base import ConnectorError, ConnectorNotSupported


_INSTALLED = False


def _remove(app, path: str, method: str) -> None:
    method = method.upper()
    app.router.routes = [
        route for route in app.router.routes
        if not (
            getattr(route, "path", None) == path
            and method in (getattr(route, "methods", set()) or set())
        )
    ]


def _usable_token(db: Session, approval: m.ApprovalRequest, user_id: int) -> str:
    actions = (
        db.query(m.ApprovalAction)
        .filter(
            m.ApprovalAction.approval_request_id == approval.id,
            m.ApprovalAction.source_message_id.is_not(None),
            m.ApprovalAction.action.in_(["created", "link_rotated"]),
        )
        .order_by(m.ApprovalAction.id.desc())
        .all()
    )
    for action in actions:
        token = str(action.source_message_id or "").strip()
        if token and sha256(token.encode()).hexdigest() == approval.public_token_hash:
            return token

    # Existing approvals created before clear-token persistence cannot recover a
    # one-way hash. Rotate to a new valid token rather than falsely reporting
    # that the approval link is missing forever.
    token = token_urlsafe(24)
    approval.public_token_hash = sha256(token.encode()).hexdigest()
    db.add(
        m.ApprovalAction(
            approval_request_id=approval.id,
            user_id=user_id,
            action="link_rotated",
            comment="Approval link rotated for external delivery",
            source_channel="system",
            source_message_id=token,
            save_to_memory=False,
        )
    )
    db.flush()
    return token


def _send(db: Session, user, approval_id: int, provider: str):
    approval = legacy_main._approval_for_user(db, user, approval_id)
    draft = db.get(m.ContentDraft, approval.draft_id)
    if not draft:
        _structured_error(404, "draft_not_found", "Approval draft no longer exists.")
    account = (
        db.query(m.ChannelAccount)
        .filter_by(brand_id=draft.brand_id, provider=provider, connection_status="connected")
        .first()
    )
    if not account:
        _structured_error(
            422,
            "not_connected",
            f"{_provider_label(provider)} is not connected.",
            href="/app/integrations",
        )

    token = _usable_token(db, approval, user.id)
    url = f"{PUBLIC_BASE_URL}/public/approval/{token}"
    connector, credentials = _connector_with_credentials(account)
    try:
        if provider in {"telegram", "bale"}:
            response = connector.send_message(
                credentials.get("chat_id"),
                f"{draft.title}\n\nReview and approve: {url}",
            )
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
        db.rollback()
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
    return {
        "sent": True,
        "channel": provider,
        "approval_url": f"/public/approval/{token}",
        "provider_result": response,
    }


def install_approval_delivery_overrides(app) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    for path in (
        "/approvals/requests/{id}/send-via-telegram",
        "/approvals/requests/{id}/send-via-bale",
        "/approvals/{id}/send-bale",
    ):
        _remove(app, path, "POST")

    @app.post("/approvals/requests/{id}/send-via-telegram", name="approval_send_telegram_rotatable")
    def send_telegram(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _send(db, user, id, "telegram")

    @app.post("/approvals/requests/{id}/send-via-bale", name="approval_send_bale_rotatable")
    def send_bale(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _send(db, user, id, "bale")

    @app.post("/approvals/{id}/send-bale", name="legacy_approval_send_bale_rotatable")
    def legacy_send_bale(id: int, user=Depends(legacy_main.user_from_auth), db: Session = Depends(get_db)):
        return _send(db, user, id, "bale")
