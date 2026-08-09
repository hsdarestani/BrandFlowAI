from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from ...database import settings


MARKER = "_smarbiz_encrypted"


def _fernet() -> Fernet:
    raw = str(settings.connector_secret_key or "").encode("utf-8")
    if len(raw) < 16:
        raise RuntimeError("CONNECTOR_SECRET_KEY is not configured")
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt_credentials(credentials: dict[str, Any] | None) -> dict[str, Any]:
    data = dict(credentials or {})
    if not data:
        return {}
    if data.get(MARKER) and data.get("ciphertext"):
        return data
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {MARKER: True, "version": 1, "ciphertext": _fernet().encrypt(payload).decode("ascii")}


def decrypt_credentials(stored: dict[str, Any] | None) -> dict[str, Any]:
    data = dict(stored or {})
    if not data:
        return {}
    # Backward-compatible read path for credentials saved before encryption was
    # introduced. Any subsequent update/test route rewrites them encrypted.
    if not data.get(MARKER):
        return data
    token = str(data.get("ciphertext") or "")
    if not token:
        return {}
    try:
        raw = _fernet().decrypt(token.encode("ascii"))
    except InvalidToken as exc:
        raise RuntimeError("Stored connector credentials could not be decrypted") from exc
    decoded = json.loads(raw.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise RuntimeError("Stored connector credentials have an invalid format")
    return decoded


def redacted_credentials(stored: dict[str, Any] | None) -> dict[str, Any]:
    credentials = decrypt_credentials(stored)
    redacted: dict[str, Any] = {}
    secret_keys = {"token", "bot_token", "api_key", "secret", "consumer_secret", "client_secret", "access_token", "refresh_token", "password"}
    for key, value in credentials.items():
        if key.lower() in secret_keys or any(part in key.lower() for part in ("secret", "token", "password", "key")):
            redacted[key] = "••••••••" if value else ""
        else:
            redacted[key] = value
    return redacted
