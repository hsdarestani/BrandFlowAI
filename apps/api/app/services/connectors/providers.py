from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urljoin

import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from .base import (
    AssistedConnector,
    BaseConnector,
    CapabilityMatrix,
    ConnectorConfigurationError,
    ConnectorNotSupported,
    ConnectorUpstreamError,
    MockConnector,
)


def _json_response(response: httpx.Response, provider: str) -> Any:
    try:
        payload = response.json()
    except ValueError as exc:
        raise ConnectorUpstreamError(f"{provider} returned a non-JSON response ({response.status_code})") from exc
    if response.status_code >= 400:
        message = payload.get("description") or payload.get("message") or payload.get("error") or str(payload)[:500]
        raise ConnectorUpstreamError(f"{provider} rejected the request ({response.status_code}): {message}")
    return payload


class ApprovalLinkConnector(BaseConnector):
    provider_name = "approval_link"
    capabilities = CapabilityMatrix(assisted_publish=False, approval_bot=False, requires_app_review=False)

    def validate_credentials(self, credentials):
        return {"valid": True, "mode": "local", "provider": self.provider_name}


class TelegramConnector(BaseConnector):
    provider_name = "telegram"
    capabilities = CapabilityMatrix(
        direct_publish=True,
        assisted_publish=True,
        approval_bot=True,
        media_upload=False,
        schedule=True,
        requires_app_review=False,
        supports_webhook=True,
        supports_polling=True,
        supported_content_types=["text", "post"],
    )
    api_template = "https://api.telegram.org/bot{token}/{method}"

    def _token(self, credentials: dict[str, Any] | None = None) -> str:
        values = credentials or self.__dict__
        token = str(values.get("bot_token") or values.get("token") or "").strip()
        if not token:
            raise ConnectorConfigurationError("Telegram bot token is missing")
        return token

    def _call(self, method: str, payload: dict[str, Any] | None = None, credentials: dict[str, Any] | None = None):
        token = self._token(credentials)
        try:
            response = httpx.post(
                self.api_template.format(token=token, method=method),
                json=payload or {},
                timeout=20.0,
            )
        except httpx.HTTPError as exc:
            raise ConnectorUpstreamError("Telegram could not be reached") from exc
        result = _json_response(response, "Telegram")
        if not result.get("ok", False):
            raise ConnectorUpstreamError(f"Telegram API error: {result.get('description') or 'unknown error'}")
        return result

    def validate_credentials(self, credentials):
        result = self._call("getMe", credentials=credentials)
        user = result.get("result") or {}
        return {
            "valid": True,
            "mode": "bot",
            "provider": self.provider_name,
            "account_name": user.get("username") or user.get("first_name"),
            "external_account_id": str(user.get("id") or ""),
        }

    def send_message(self, chat_id, text, **kwargs):
        if not str(chat_id or "").strip():
            chat_id = getattr(self, "chat_id", None)
        if not str(chat_id or "").strip():
            raise ConnectorConfigurationError("Telegram chat_id is missing")
        payload = {"chat_id": str(chat_id), "text": str(text), "disable_web_page_preview": bool(kwargs.get("disable_web_page_preview", False))}
        if kwargs.get("reply_markup"):
            payload["reply_markup"] = kwargs["reply_markup"]
        return self._call("sendMessage", payload)

    def publish_post(self, draft, account=None):
        chat_id = getattr(self, "chat_id", None)
        if not chat_id:
            raise ConnectorConfigurationError("Telegram publishing requires a target chat_id")
        body = str(getattr(draft, "body", "") or "").strip()
        title = str(getattr(draft, "title", "") or "").strip()
        text = f"{title}\n\n{body}".strip() if title else body
        result = self.send_message(chat_id, text)
        message = result.get("result") or {}
        return {
            "status": "published",
            "provider_post_id": str(message.get("message_id") or ""),
            "message_id": message.get("message_id"),
            "public_url": None,
        }


class BaleConnector(TelegramConnector):
    provider_name = "bale"
    api_template = os.getenv("BALE_BASE_URL") or "https://tapi.bale.ai/bot{token}/{method}"
    capabilities = CapabilityMatrix(
        direct_publish=True,
        assisted_publish=True,
        analytics=False,
        comments=False,
        dm=True,
        approval_bot=True,
        media_upload=False,
        schedule=True,
        requires_app_review=False,
        supports_webhook=True,
        supports_polling=True,
        supported_content_types=["text", "post"],
    )

    def _token(self, credentials: dict[str, Any] | None = None) -> str:
        values = credentials or self.__dict__
        token = str(values.get("bot_token") or values.get("token") or os.getenv("BALE_BOT_TOKEN") or "").strip()
        if not token:
            raise ConnectorConfigurationError("Bale bot token is missing")
        return token

    def _call(self, method: str, payload: dict[str, Any] | None = None, credentials: dict[str, Any] | None = None):
        token = self._token(credentials)
        try:
            response = httpx.post(self.api_template.format(token=token, method=method), json=payload or {}, timeout=20.0)
        except httpx.HTTPError as exc:
            raise ConnectorUpstreamError("Bale could not be reached") from exc
        result = _json_response(response, "Bale")
        if result.get("ok") is False:
            raise ConnectorUpstreamError(f"Bale API error: {result.get('description') or 'unknown error'}")
        return result


class BrevoConnector(BaseConnector):
    provider_name = "brevo"
    capabilities = CapabilityMatrix(dm=True, requires_app_review=False, supported_content_types=["email"])
    base_url = "https://api.brevo.com/v3/"

    @staticmethod
    def _api_key(credentials: dict[str, Any] | None = None, obj: Any = None) -> str:
        values = credentials or (getattr(obj, "__dict__", {}) if obj is not None else {})
        key = str(values.get("api_key") or "").strip()
        if not key:
            raise ConnectorConfigurationError("Brevo API key is missing")
        return key

    def _request(self, method: str, path: str, *, credentials=None, json_body=None):
        key = self._api_key(credentials, self)
        try:
            response = httpx.request(
                method,
                urljoin(self.base_url, path.lstrip("/")),
                headers={"api-key": key, "accept": "application/json", "content-type": "application/json"},
                json=json_body,
                timeout=20.0,
            )
        except httpx.HTTPError as exc:
            raise ConnectorUpstreamError("Brevo could not be reached") from exc
        return _json_response(response, "Brevo")

    def validate_credentials(self, credentials):
        payload = self._request("GET", "account", credentials=credentials)
        return {
            "valid": True,
            "mode": "api_key",
            "provider": self.provider_name,
            "account_name": payload.get("companyName") or payload.get("email"),
            "external_account_id": str(payload.get("organization_id") or payload.get("user_id") or ""),
        }

    def send_message(self, recipient_email, text, **kwargs):
        sender_email = str(kwargs.get("sender_email") or getattr(self, "sender_email", "")).strip()
        sender_name = str(kwargs.get("sender_name") or getattr(self, "sender_name", "Smarbiz")).strip()
        if not sender_email:
            raise ConnectorConfigurationError("Brevo sender_email is missing")
        subject = str(kwargs.get("subject") or "Smarbiz message")
        payload = self._request(
            "POST",
            "smtp/email",
            json_body={
                "sender": {"name": sender_name, "email": sender_email},
                "to": [{"email": str(recipient_email)}],
                "subject": subject,
                "textContent": str(text),
            },
        )
        return {"sent": True, "status": "sent", "message_id": payload.get("messageId")}


class WooCommerceConnector(BaseConnector):
    provider_name = "woocommerce"
    capabilities = CapabilityMatrix(analytics=True, requires_app_review=False, supports_polling=True, supported_content_types=[])

    @staticmethod
    def _config(credentials: dict[str, Any] | None = None, obj: Any = None):
        values = credentials or (getattr(obj, "__dict__", {}) if obj is not None else {})
        site_url = str(values.get("site_url") or values.get("url") or "").strip().rstrip("/")
        key = str(values.get("consumer_key") or "").strip()
        secret = str(values.get("consumer_secret") or "").strip()
        if not site_url or not key or not secret:
            raise ConnectorConfigurationError("WooCommerce site_url, consumer_key and consumer_secret are required")
        if not site_url.startswith(("https://", "http://")):
            raise ConnectorConfigurationError("WooCommerce site_url must be an absolute URL")
        return site_url, key, secret

    def _get(self, path: str, *, credentials=None, params=None):
        site_url, key, secret = self._config(credentials, self)
        url = f"{site_url}/wp-json/wc/v3/{path.lstrip('/')}"
        try:
            response = httpx.get(url, auth=(key, secret), params=params or {}, timeout=25.0, follow_redirects=True)
        except httpx.HTTPError as exc:
            raise ConnectorUpstreamError("WooCommerce could not be reached") from exc
        return _json_response(response, "WooCommerce")

    def validate_credentials(self, credentials):
        payload = self._get("system_status", credentials=credentials)
        env = payload.get("environment") or {}
        return {
            "valid": True,
            "mode": "rest_api",
            "provider": self.provider_name,
            "account_name": env.get("site_url") or env.get("home_url"),
            "external_account_id": env.get("site_url") or env.get("home_url"),
            "woocommerce_version": env.get("version"),
        }

    def fetch_analytics(self, provider_post_id=None, **kwargs):
        start_date = kwargs.get("start_date") or (date.today() - timedelta(days=30)).isoformat()
        end_date = kwargs.get("end_date") or date.today().isoformat()
        orders = self._get(
            "orders",
            params={
                "after": f"{start_date}T00:00:00",
                "before": f"{end_date}T23:59:59",
                "per_page": 100,
                "status": "any",
            },
        )
        if not isinstance(orders, list):
            raise ConnectorUpstreamError("WooCommerce orders response was invalid")
        completed = [row for row in orders if row.get("status") in {"completed", "processing"}]
        revenue = 0.0
        for row in completed:
            try:
                revenue += float(row.get("total") or 0)
            except (TypeError, ValueError):
                pass
        return {
            "orders": len(orders),
            "fulfilled_or_processing_orders": len(completed),
            "revenue": round(revenue, 2),
            "currency": next((row.get("currency") for row in completed if row.get("currency")), None),
            "source_period": {"start": start_date, "end": end_date},
        }


class GA4Connector(BaseConnector):
    provider_name = "ga4"
    capabilities = CapabilityMatrix(analytics=True, requires_app_review=False, supports_polling=True, supported_content_types=[])
    scope = "https://www.googleapis.com/auth/analytics.readonly"

    @staticmethod
    def _credentials(values: dict[str, Any]):
        property_id = str(values.get("property_id") or "").strip()
        raw_sa = values.get("service_account_json") or values.get("service_account")
        if isinstance(raw_sa, str):
            try:
                raw_sa = json.loads(raw_sa)
            except json.JSONDecodeError as exc:
                raise ConnectorConfigurationError("GA4 service_account_json is not valid JSON") from exc
        if not property_id or not isinstance(raw_sa, dict):
            raise ConnectorConfigurationError("GA4 property_id and service_account_json are required")
        try:
            credentials = service_account.Credentials.from_service_account_info(raw_sa, scopes=[GA4Connector.scope])
            credentials.refresh(GoogleAuthRequest())
        except Exception as exc:
            raise ConnectorConfigurationError(f"GA4 service account authentication failed: {exc}") from exc
        return property_id, credentials

    def validate_credentials(self, credentials):
        property_id, creds = self._credentials(credentials)
        payload = self._run_report(property_id, creds, start_date="7daysAgo", end_date="today", metrics=["sessions"])
        return {
            "valid": True,
            "mode": "service_account",
            "provider": self.provider_name,
            "account_name": f"GA4 property {property_id}",
            "external_account_id": property_id,
            "rows": int(payload.get("rowCount") or 0),
        }

    @staticmethod
    def _run_report(property_id, credentials, *, start_date, end_date, metrics, dimensions=None):
        body = {
            "dateRanges": [{"startDate": start_date, "endDate": end_date}],
            "metrics": [{"name": metric} for metric in metrics],
        }
        if dimensions:
            body["dimensions"] = [{"name": dimension} for dimension in dimensions]
        try:
            response = httpx.post(
                f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
                headers={"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"},
                json=body,
                timeout=25.0,
            )
        except httpx.HTTPError as exc:
            raise ConnectorUpstreamError("Google Analytics Data API could not be reached") from exc
        return _json_response(response, "GA4")

    def fetch_analytics(self, provider_post_id=None, **kwargs):
        values = self.__dict__
        property_id, creds = self._credentials(values)
        start_date = kwargs.get("start_date") or "30daysAgo"
        end_date = kwargs.get("end_date") or "today"
        metrics = ["sessions", "activeUsers", "screenPageViews", "conversions"]
        payload = self._run_report(property_id, creds, start_date=start_date, end_date=end_date, metrics=metrics)
        totals = (payload.get("totals") or [{}])[0].get("metricValues") or []
        if not totals and payload.get("rows"):
            totals = (payload["rows"][0].get("metricValues") or [])
        parsed: dict[str, float] = {}
        for metric, value in zip(metrics, totals):
            try:
                parsed[metric] = float(value.get("value") or 0)
            except (TypeError, ValueError):
                parsed[metric] = 0.0
        parsed["source_period"] = {"start": start_date, "end": end_date}
        return parsed


ASSISTED_PROVIDERS = {
    "instagram",
    "facebook",
    "tiktok",
    "linkedin",
    "google_business",
    "youtube",
    "mailchimp",
    "booking",
    "eitaa",
    "soroush",
    "aparat",
    "bale_safir",
}

CONNECTORS: dict[str, BaseConnector] = {
    "mock": MockConnector(),
    "approval_link": ApprovalLinkConnector(),
    "telegram": TelegramConnector(),
    "bale": BaleConnector(),
    "brevo": BrevoConnector(),
    "woocommerce": WooCommerceConnector(),
    "ga4": GA4Connector(),
}
for name in ASSISTED_PROVIDERS:
    CONNECTORS[name] = AssistedConnector(name)


def get_connector(provider: str) -> BaseConnector:
    name = str(provider or "").strip().lower()
    connector = CONNECTORS.get(name)
    if not connector:
        raise ConnectorNotSupported(f"Unknown connector provider '{name or provider}'")
    return connector


def connector_catalog():
    return [{"provider": key, "capabilities": value.capabilities.__dict__} for key, value in CONNECTORS.items()]
