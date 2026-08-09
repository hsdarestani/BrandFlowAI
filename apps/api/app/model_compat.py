from __future__ import annotations

from sqlalchemy import DateTime, Integer, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from . import models as m
from .database import Base


class WebhookEvent(Base):
    """Durable inbound webhook event with provider-level idempotency."""

    __tablename__ = "webhook_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String, index=True)
    event_id: Mapped[str] = mapped_column(String, index=True)
    event_type: Mapped[str] = mapped_column(String)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    processed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Expose the extension through the historic models module because legacy and
# override routes import `models as m`.
m.WebhookEvent = WebhookEvent


# ConnectorEvent existed before the cleanup with created_at/external_id fields.
# New code calls the same durable event log with a channel_account_id and reads
# received_at. Keep one physical schema: received_at aliases created_at and the
# channel id is preserved in external_id rather than creating duplicate columns.
if not hasattr(m.ConnectorEvent, "received_at"):
    m.ConnectorEvent.received_at = m.ConnectorEvent.created_at

_original_connector_event_init = m.ConnectorEvent.__init__


def _connector_event_init(self, **kwargs):
    channel_account_id = kwargs.pop("channel_account_id", None)
    if channel_account_id is not None and not kwargs.get("external_id"):
        kwargs["external_id"] = f"channel_account:{channel_account_id}"
    _original_connector_event_init(self, **kwargs)


m.ConnectorEvent.__init__ = _connector_event_init


# Feature flags historically stored scope and metadata. New admin UX also
# exposes rollout percentage and selected organizations. Persist those inside
# metadata_json so old databases remain compatible and no duplicate schema is
# introduced.
def _rollout_get(self):
    metadata = self.metadata_json or {}
    return int(metadata.get("rollout_percentage", 100 if self.enabled else 0))


def _rollout_set(self, value):
    metadata = dict(self.metadata_json or {})
    metadata["rollout_percentage"] = max(0, min(100, int(value or 0)))
    self.metadata_json = metadata


def _org_ids_get(self):
    metadata = self.metadata_json or {}
    value = metadata.get("organization_ids") or []
    return value if isinstance(value, list) else []


def _org_ids_set(self, value):
    metadata = dict(self.metadata_json or {})
    metadata["organization_ids"] = list(value or [])
    self.metadata_json = metadata


if not hasattr(m.FeatureFlag, "rollout_percentage"):
    m.FeatureFlag.rollout_percentage = property(_rollout_get, _rollout_set)
if not hasattr(m.FeatureFlag, "organization_ids_json"):
    m.FeatureFlag.organization_ids_json = property(_org_ids_get, _org_ids_set)
