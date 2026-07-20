"""Production API entrypoint.

This module keeps the mature route surface in ``app.main`` while replacing a
small number of legacy placeholder endpoints with production-capable handlers.
"""

from html import escape
from pathlib import Path
import re

import httpx
from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import models as m
from .database import get_db
from .main import (
    ASSET_ROOT,
    _tenant_obj,
    app,
    org_brand_or_404,
    report_get,
    user_from_auth,
)


def _remove_route(path: str, method: str) -> None:
    """Remove one legacy route before registering its replacement."""

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
_remove_route("/reports/{id}/send-email", "POST")


@app.get("/assets/{id}/download", name="asset_download_file")
def asset_download_file(
    id: int,
    u=Depends(user_from_auth),
    db: Session = Depends(get_db),
):
    """Stream an authenticated tenant-scoped asset from local storage."""

    _, _, asset = _tenant_obj(db, u, m.Asset, id)
    metadata = asset.metadata_json or {}
    raw_path = metadata.get("storage_path")
    if not raw_path:
        raise HTTPException(
            status_code=404,
            detail={"error": "asset_file_missing", "message": "This asset has no stored file."},
        )

    root = Path(ASSET_ROOT).resolve()
    path = Path(raw_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail={"error": "invalid_asset_path", "message": "Asset path is outside the storage root."},
        ) from exc

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail={"error": "asset_file_missing", "message": "The stored asset file could not be found."},
        )

    filename = metadata.get("original_filename") or path.name
    media_type = metadata.get("mime_type") or "application/octet-stream"
    return FileResponse(path=path, media_type=media_type, filename=filename)


_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@app.post("/reports/{id}/send-email", name="report_send_email_brevo")
def report_send_email_brevo(
    id: int,
    payload: dict | None = None,
    u=Depends(user_from_auth),
    db: Session = Depends(get_db),
):
    """Send a report through a configured Brevo transactional-email connector."""

    payload = payload or {}
    recipient = str(payload.get("recipient_email") or "").strip().lower()
    if not _EMAIL_PATTERN.match(recipient):
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_recipient", "message": "A valid recipient email is required."},
        )

    _, brand = org_brand_or_404(db, u)
    report = db.get(m.WeeklyReport, id)
    if not report:
        raise HTTPException(status_code=404, detail={"error": "report_not_found", "message": "Report not found."})
    if report.brand_id != brand.id:
        raise HTTPException(status_code=403, detail={"error": "wrong_tenant", "message": "Report is outside your workspace."})

    account = (
        db.query(m.ChannelAccount)
        .filter_by(brand_id=brand.id, provider="brevo", connection_status="connected")
        .first()
    )
    if not account:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "email_not_connected",
                "message": "Connect and test a Brevo email integration before sending reports.",
                "href": "/app/integrations?type=email&provider=brevo",
            },
        )

    config = account.credentials_encrypted_json or {}
    api_key = str(config.get("api_key") or "").strip()
    sender_email = str(config.get("sender_email") or "").strip().lower()
    sender_name = str(config.get("sender_name") or brand.name or "Smarbiz").strip()
    if not api_key or not _EMAIL_PATTERN.match(sender_email):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "email_configuration_incomplete",
                "message": "Brevo API key and a valid sender email are required.",
                "href": f"/app/integrations?provider=brevo",
            },
        )

    rendered = report_get(id, u, db)
    recommendations = (rendered.get("recommendations") or {}).get("items", [])
    highlights = rendered.get("highlights") or []
    html = [
        f"<h1>{escape(rendered['title'])}</h1>",
        f"<p><strong>{escape(rendered['period_start'])}</strong> – <strong>{escape(rendered['period_end'])}</strong></p>",
        f"<p>{escape(rendered.get('summary') or '').replace(chr(10), '<br>')}</p>",
    ]
    if highlights:
        html.append("<h2>Highlights</h2><ul>" + "".join(f"<li>{escape(str(item))}</li>" for item in highlights) + "</ul>")
    if recommendations:
        html.append("<h2>Recommendations</h2><ul>" + "".join(f"<li>{escape(str(item))}</li>" for item in recommendations) + "</ul>")
    html.append("<p style='color:#64748b'>Generated by Smarbiz.</p>")

    request_body = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": recipient, "name": str(payload.get("recipient_name") or recipient)}],
        "subject": str(payload.get("subject") or rendered["title"]),
        "htmlContent": "".join(html),
    }
    try:
        response = httpx.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": api_key, "accept": "application/json", "content-type": "application/json"},
            json=request_body,
            timeout=20.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "email_provider_unreachable", "message": "Brevo could not be reached. Try again later."},
        ) from exc

    if response.status_code not in {200, 201, 202}:
        try:
            provider_detail = response.json()
        except ValueError:
            provider_detail = {"message": response.text[:500]}
        raise HTTPException(
            status_code=502,
            detail={
                "error": "email_provider_rejected",
                "message": provider_detail.get("message") or "Brevo rejected the email request.",
                "provider_status": response.status_code,
            },
        )

    metadata = report.insights_json or {}
    metadata.update(
        {
            "status": "sent",
            "sent_to": recipient,
            "email_provider": "brevo",
            "email_message_id": response.json().get("messageId") if response.content else None,
        }
    )
    report.insights_json = metadata
    db.commit()
    return {
        "sent": True,
        "report_id": id,
        "provider": "brevo",
        "recipient_email": recipient,
        "message_id": metadata.get("email_message_id"),
    }
