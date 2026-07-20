"""Runtime security guardrails for the MVP API.

The original API was built quickly in a single module and a few early routes only
checked that a user was authenticated.  This module adds a central protection
layer while those routes are gradually moved to explicit service-level RBAC.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict, deque
from typing import Any

import fastapi
from sqlalchemy import event
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import JSONResponse

_INSTALLED = False
_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_AUTH_LIMIT = int(os.getenv("AUTH_RATE_LIMIT_PER_MINUTE", "12"))


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


def _rate_limited(request: Request) -> bool:
    key = f"{_client_ip(request)}:{request.url.path}"
    now = time.monotonic()
    bucket = _RATE_BUCKETS[key]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= _AUTH_LIMIT:
        return True
    bucket.append(now)
    return False


def _json_error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": {"error": code, "message": message}})


def _restore_body(request: Request, body: bytes) -> None:
    sent = False

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    request._receive = receive  # Starlette-compatible replay for downstream parsing.


def _install_sqlalchemy_guard() -> None:
    bootstrap_email = os.getenv("BOOTSTRAP_SUPERADMIN_EMAIL", "").strip().lower()

    @event.listens_for(Session, "before_flush")
    def prevent_public_superadmin(session: Session, _flush_context: Any, _instances: Any) -> None:
        for obj in set(session.new).union(session.dirty):
            if obj.__class__.__name__ != "User" or not getattr(obj, "is_super_admin", False):
                continue
            email = str(getattr(obj, "email", "")).strip().lower()
            if not bootstrap_email or email != bootstrap_email:
                obj.is_super_admin = False


def _install_fastapi_guard() -> None:
    original_fastapi = fastapi.FastAPI

    async def security_middleware(request: Request, call_next):
        path = request.url.path.rstrip("/") or "/"

        if path in {"/auth/login", "/auth/signup"} and request.method == "POST":
            if _rate_limited(request):
                return _json_error(429, "rate_limited", "Too many authentication attempts. Try again in a minute.")

        authorization = request.headers.get("authorization", "")
        if not authorization.lower().startswith("bearer "):
            return await call_next(request)

        try:
            from . import models as m
            from .database import SessionLocal
            from .security import decode_token

            token = authorization.split(" ", 1)[1].strip()
            email = str(decode_token(token).get("sub", "")).strip().lower()
            db = SessionLocal()
            try:
                user = db.query(m.User).filter(m.User.email == email).first()
                if not user:
                    return _json_error(401, "unknown_user", "The authenticated user no longer exists.")
                if user.is_super_admin:
                    return await call_next(request)

                memberships = (
                    db.query(m.OrganizationMember)
                    .filter_by(user_id=user.id, status="active")
                    .all()
                )
                roles_by_org = {row.organization_id: row.role for row in memberships}
                owned_org_ids = {
                    row.id for row in db.query(m.Organization).filter_by(owner_user_id=user.id).all()
                }
                org_ids = set(roles_by_org).union(owned_org_ids)
                brand_rows = db.query(m.Brand).filter(m.Brand.organization_id.in_(org_ids)).all() if org_ids else []
                brand_org = {row.id: row.organization_id for row in brand_rows}

                if path.startswith("/admin"):
                    return _json_error(403, "superadmin_required", "Super Admin access is required.")

                org_match = re.match(r"^/organizations/(\d+)(?:/|$)", path)
                if org_match:
                    org_id = int(org_match.group(1))
                    if org_id not in org_ids:
                        return _json_error(403, "wrong_tenant", "Organization is outside your workspace.")
                    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
                        role = roles_by_org.get(org_id)
                        if org_id not in owned_org_ids and role not in {"org_owner", "admin"}:
                            return _json_error(403, "insufficient_role", "Organization admin access is required.")

                brand_match = re.match(r"^/brands/(\d+)(?:/|$)", path)
                if brand_match:
                    brand_id = int(brand_match.group(1))
                    if brand_id not in brand_org:
                        return _json_error(403, "wrong_tenant", "Brand is outside your workspace.")
                    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
                        org_id = brand_org[brand_id]
                        role = roles_by_org.get(org_id)
                        if org_id not in owned_org_ids and role not in {"org_owner", "admin", "editor"}:
                            return _json_error(403, "insufficient_role", "Brand editor access is required.")

                if request.method in {"POST", "PATCH", "PUT"} and "application/json" in request.headers.get("content-type", ""):
                    body = await request.body()
                    _restore_body(request, body)
                    try:
                        payload = json.loads(body or b"{}")
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        payload = {}
                    if isinstance(payload, dict):
                        requested_org = payload.get("organization_id")
                        requested_brand = payload.get("brand_id")
                        if requested_org is not None and int(requested_org) not in org_ids:
                            return _json_error(403, "wrong_tenant", "Organization is outside your workspace.")
                        if requested_brand is not None and int(requested_brand) not in brand_org:
                            return _json_error(403, "wrong_tenant", "Brand is outside your workspace.")
                        protected_fields = {"owner_user_id", "is_super_admin", "suspended_at"}
                        if protected_fields.intersection(payload) and path.startswith(("/organizations/", "/brands/")):
                            return _json_error(403, "protected_field", "This field can only be changed by a Super Admin.")
            finally:
                db.close()
        except Exception:
            # Authentication and request validation remain enforced by the endpoint.
            # Never turn an internal guard failure into a public outage.
            pass

        return await call_next(request)

    class GuardedFastAPI(original_fastapi):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.middleware("http")(security_middleware)

    fastapi.FastAPI = GuardedFastAPI


def install_security_guards() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
    _install_sqlalchemy_guard()
    _install_fastapi_guard()
