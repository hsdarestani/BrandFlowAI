from __future__ import annotations

from typing import Any

from .services.connectors.secrets import decrypt_credentials


SENSITIVE_MARKERS = (
    "secret",
    "token",
    "password",
    "private_key",
    "privatekey",
    "api_key",
    "apikey",
    "consumer_key",
    "service_account",
    "credential",
    "authorization",
)


def _sensitive(key: str) -> bool:
    normalized = str(key or "").strip().lower().replace("-", "_")
    return any(marker in normalized for marker in SENSITIVE_MARKERS)


def _mask(value: Any) -> Any:
    if value in (None, "", {}, []):
        return value
    return "••••••••"


def _redact(value: Any, parent_key: str = "") -> Any:
    if _sensitive(parent_key):
        return _mask(value)
    if isinstance(value, dict):
        return {key: (_mask(item) if _sensitive(key) else _redact(item, key)) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item, parent_key) for item in value]
    return value


def hardened_redacted_credentials(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Decrypt internally, then return a display-only configuration with all secrets masked.

    In particular, whole service-account JSON blobs are sensitive even when the
    top-level field name does not literally contain `secret`.
    """
    decrypted = decrypt_credentials(payload or {})
    return _redact(decrypted)


def install_secret_redaction_guard() -> None:
    # `production_overrides._connection_out()` resolves this module global at
    # request time, so replacing it here hardens every route that reuses that
    # serializer without duplicating route registrations.
    from . import production_overrides

    production_overrides.redacted_credentials = hardened_redacted_credentials
