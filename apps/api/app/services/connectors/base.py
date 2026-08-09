from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ConnectorError(RuntimeError):
    pass


class ConnectorNotSupported(ConnectorError):
    pass


class ConnectorConfigurationError(ConnectorError):
    pass


class ConnectorUpstreamError(ConnectorError):
    pass


@dataclass
class CapabilityMatrix:
    direct_publish: bool = False
    assisted_publish: bool = False
    analytics: bool = False
    comments: bool = False
    dm: bool = False
    approval_bot: bool = False
    media_upload: bool = False
    schedule: bool = False
    requires_app_review: bool = True
    supports_webhook: bool = False
    supports_polling: bool = False
    supported_content_types: list[str] = field(default_factory=lambda: ["text"])


class BaseConnector:
    provider_name = "base"
    capabilities = CapabilityMatrix()

    def connect_url(self):
        return None

    def oauth_callback(self, payload):
        raise ConnectorNotSupported(f"OAuth is not implemented for {self.provider_name}")

    def refresh_token(self, credentials):
        raise ConnectorNotSupported(f"Token refresh is not implemented for {self.provider_name}")

    def validate_credentials(self, credentials: dict[str, Any]):
        raise ConnectorNotSupported(f"Credential validation is not implemented for {self.provider_name}")

    def publish_post(self, draft, account=None):
        raise ConnectorNotSupported(f"Direct publishing is not supported by {self.provider_name}")

    def schedule_post(self, draft, when, account=None):
        raise ConnectorNotSupported(f"Provider-side scheduling is not supported by {self.provider_name}")

    def get_post_status(self, provider_post_id):
        raise ConnectorNotSupported(f"Post status lookup is not supported by {self.provider_name}")

    def fetch_analytics(self, provider_post_id=None, **kwargs):
        raise ConnectorNotSupported(f"Analytics are not supported by {self.provider_name}")

    def fetch_comments(self, provider_post_id):
        raise ConnectorNotSupported(f"Comments are not supported by {self.provider_name}")

    def send_message(self, *args, **kwargs):
        raise ConnectorNotSupported(f"Messaging is not supported by {self.provider_name}")

    def revoke_connection(self, *args, **kwargs):
        return {"revoked": True, "provider": self.provider_name, "remote_revocation": False}


class AssistedConnector(BaseConnector):
    """A truthful connector for providers where Smarbiz prepares a manual kit."""

    capabilities = CapabilityMatrix(
        direct_publish=False,
        assisted_publish=True,
        requires_app_review=True,
        supported_content_types=["text", "image", "video", "carousel"],
    )

    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    def validate_credentials(self, credentials):
        return {
            "valid": False,
            "mode": "assisted",
            "provider": self.provider_name,
            "message": "Direct API connection is not configured; assisted publishing is available.",
        }

    def publish_post(self, draft, account=None):
        return {
            "status": "assisted",
            "provider": self.provider_name,
            "assisted_publish_url": f"/app/content-studio?draft={getattr(draft, 'id', '')}&publish={self.provider_name}",
        }


class MockConnector(BaseConnector):
    """Explicit test-only connector. Production code must never auto-select it."""

    provider_name = "mock"
    capabilities = CapabilityMatrix(
        direct_publish=True,
        assisted_publish=True,
        analytics=True,
        comments=True,
        dm=True,
        approval_bot=True,
        media_upload=True,
        schedule=True,
        requires_app_review=False,
        supports_webhook=True,
        supports_polling=True,
        supported_content_types=["text", "image", "video", "carousel", "document"],
    )

    def validate_credentials(self, credentials):
        return {"valid": True, "mode": "test", "mock": True}

    def publish_post(self, draft, account=None):
        return {
            "status": "mock_published",
            "mock": True,
            "provider_post_id": f"mock_{getattr(draft, 'id', 1)}",
            "public_url": None,
        }
