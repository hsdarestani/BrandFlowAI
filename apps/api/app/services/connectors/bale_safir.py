from __future__ import annotations

import os
import re
import uuid
from typing import Any

import httpx

from .base import BaseConnector, CapabilityMatrix, ConnectorConfigurationError, ConnectorUpstreamError

ERROR_MAP = {
    "InternalServerError": "Provider internal error",
    "RateLimitExceeded": "Rate limit exceeded",
    "InvalidInput": "Invalid request payload",
    "InvalidPhone": "Invalid Iranian mobile number",
    "NotBaleUser": "Recipient is not a Bale user",
    "PaymentRequired": "Safir account requires payment",
    "MaximumContactLimitReached": "Contact limit reached",
}


def normalize_iran_phone(phone: str, plus: bool = True) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("0098"):
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = "98" + digits[1:]
    if digits.startswith("9") and len(digits) == 10:
        digits = "98" + digits
    if not (digits.startswith("98") and len(digits) == 12 and digits[2] == "9"):
        raise ValueError("InvalidPhone")
    return ("+" if plus else "") + digits


class BaleSafirConnector(BaseConnector):
    provider_name = "bale_safir"
    capabilities = CapabilityMatrix(
        direct_publish=False,
        assisted_publish=False,
        dm=True,
        approval_bot=True,
        requires_app_review=False,
        supports_webhook=False,
        supported_content_types=["text", "document", "image"],
    )

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("BALE_SAFIR_BASE_URL") or "https://safir.bale.ai/api/v3").rstrip("/")

    @staticmethod
    def _config(credentials: dict[str, Any] | None):
        values = credentials or {}
        access_key = str(values.get("api_access_key") or values.get("access_key") or os.getenv("BALE_SAFIR_API_ACCESS_KEY") or "").strip()
        bot_id = values.get("bot_id") or os.getenv("BALE_SAFIR_BOT_ID")
        if not access_key:
            raise ConnectorConfigurationError("Bale Safir api_access_key is missing")
        try:
            bot_id = int(bot_id)
        except (TypeError, ValueError) as exc:
            raise ConnectorConfigurationError("Bale Safir bot_id is missing or invalid") from exc
        if bot_id <= 0:
            raise ConnectorConfigurationError("Bale Safir bot_id must be positive")
        return access_key, bot_id

    def send_message(self, phone_number, message_data, credentials=None, consent=False):
        if not consent:
            raise ConnectorConfigurationError("Explicit recipient consent is required for Bale Safir messaging")
        access_key, bot_id = self._config(credentials)
        phone = normalize_iran_phone(phone_number, plus=False)
        request_id = str(uuid.uuid4())
        payload = {
            "bot_id": bot_id,
            "request_id": request_id,
            "phone_number": phone,
            "message_data": message_data,
        }
        try:
            response = httpx.post(
                f"{self.base_url}/send_message",
                headers={"api-access-key": access_key, "Content-Type": "application/json"},
                json=payload,
                timeout=25.0,
            )
        except httpx.HTTPError as exc:
            raise ConnectorUpstreamError("Bale Safir could not be reached") from exc
        try:
            result = response.json()
        except ValueError as exc:
            raise ConnectorUpstreamError(f"Bale Safir returned a non-JSON response ({response.status_code})") from exc
        if response.status_code >= 400 or result.get("ok") is False:
            error = result.get("error") or result.get("error_code") or result.get("description") or result.get("message") or str(result)[:500]
            mapped = self.map_error(str(error))
            raise ConnectorUpstreamError(f"Bale Safir rejected the request ({response.status_code}): {mapped if mapped != 'Unknown API error' else error}")
        provider_message_id = result.get("message_id") or result.get("id") or (result.get("result") or {}).get("message_id")
        return {
            "sent": True,
            "status": "sent",
            "request_id": result.get("request_id") or request_id,
            "message_id": str(provider_message_id or ""),
            "phone_number": phone,
            "provider_response": result,
        }

    def map_error(self, code):
        return ERROR_MAP.get(code, "Unknown API error")
