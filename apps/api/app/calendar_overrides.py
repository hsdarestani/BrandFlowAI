from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import re

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from . import main as legacy_main
from . import models as m
from .database import get_db
from .services.calendar_planner import (
    CONTENT_CHANNELS,
    build_week_plan,
    listify,
    local_week_start,
    recommended_plan_size,
    safe_zone,
)


_ORIGINAL_CALENDAR_ITEM_OUT = legacy_main.calendar_item_out
_INSTALLED = False
_LEGACY_TITLE = re.compile(r"^Draft content idea \d+$", re.IGNORECASE)


def _remove_route(app, path: str, method: str) -> None:
    method = method.upper()
    app.router.routes = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == path
            and method in (getattr(route, "methods", set()) or set())
        )
    ]


def _calendar_item_out_local(item, db: Session):
    """Serialize planned wall-clock time in the brand/item timezone.

    PostgreSQL stores timestamptz instants and normally returns UTC. Returning an
    ISO timestamp with the configured offset keeps the calendar drawer from
    showing raw UTC (for example 06:30 instead of the intended local time).
    """

    out = _ORIGINAL_CALENDAR_ITEM_OUT(item, db)
    if item.scheduled_at:
        dt = item.scheduled_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        timezone_name = item.timezone
        if not timezone_name and item.brand_id:
            brand = db.get(m.Brand, item.brand_id)
            timezone_name = brand.timezone if brand else "UTC"
        out["scheduled_at"] = dt.astimezone(safe_zone(timezone_name)).isoformat()
    return out


def _append_channel(target: list[str], value) -> None:
    channel = str(value or "").strip().lower().replace(" ", "_")
    if channel in CONTENT_CHANNELS and channel not in target:
        target.append(channel)


def _preferred_content_channels(
    db: Session,
    brand_id: int,
    dna,
    requested: list[str] | None,
) -> list[str]:
    """Resolve channels for planning, independent of publishing OAuth.

    A content idea can be planned before a provider is connected. Publishing and
    scheduling continue to enforce the actual connector requirement elsewhere.
    """

    clean: list[str] = []
    for channel in requested or []:
        _append_channel(clean, channel)
    if clean:
        return clean

    # A saved account is a strong preference even when its OAuth connection is
    # not complete yet.
    for row in db.query(m.ChannelAccount).filter_by(brand_id=brand_id).all():
        _append_channel(clean, row.provider)

    channel_rules = (getattr(dna, "channel_rules_json", None) or {}) if dna else {}
    for note in listify(channel_rules.get("channel_notes")):
        # Onboarding normally stores bare provider ids, but tolerate a short note
        # containing one of the known provider names.
        normalized = note.strip().lower().replace(" ", "_")
        _append_channel(clean, normalized)
        for candidate in CONTENT_CHANNELS:
            if candidate in normalized:
                _append_channel(clean, candidate)

    return clean or ["instagram"]


def _week_bounds(week_date, timezone_name: str):
    tz = safe_zone(timezone_name)
    local_start = datetime.combine(week_date, time.min, tzinfo=tz)
    local_end = local_start + timedelta(days=7)
    return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)


def _is_legacy_placeholder(item) -> bool:
    """Identify only the unmistakable items created by the old hard-coded loop."""

    title = str(item.title or "").strip()
    description = str(item.description or "").strip()
    return bool(
        _LEGACY_TITLE.fullmatch(title)
        and description.startswith("Draft weekly plan for ")
        and "Review before publishing" in description
        and (item.status or "") in {"draft", "idea", "planned"}
    )


def install_calendar_overrides(app) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    # Improve timestamps for every existing calendar endpoint, not only newly
    # generated items.
    legacy_main.calendar_item_out = _calendar_item_out_local

    for path in (
        "/calendar/generate-week",
        "/brands/{id}/calendar/generate-week",
        "/brands/{id}/calendar/regenerate-week",
    ):
        _remove_route(app, path, "POST")

    @app.post("/calendar/generate-week", name="calendar_generate_week_brand_aware")
    def generate_week(
        data: legacy_main.CalendarGenerateIn,
        u=Depends(legacy_main.user_from_auth),
        db: Session = Depends(get_db),
    ):
        _, brand = legacy_main.org_brand_or_404(db, u, data.brand_id)
        setup = legacy_main.setup_state(db, brand)
        # Planning content only requires real brand knowledge and an offer.
        # Publishing-channel OAuth and approval integrations are enforced later,
        # when the user schedules/sends content.
        blocking = [
            item
            for item in setup["missing_requirements"]
            if item.get("id") in {"brand_pulse", "product_service"}
        ]
        if blocking:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Complete Brand Pulse and add an offer before generating a week",
                    "missing_requirements": blocking,
                    "action_links": blocking,
                },
            )

        dna = db.query(m.BrandDNA).filter_by(brand_id=brand.id).first()
        products = db.query(m.ProductService).filter_by(brand_id=brand.id).order_by(m.ProductService.id.asc()).all()
        personas = db.query(m.Persona).filter_by(brand_id=brand.id).order_by(m.Persona.id.asc()).all()
        rules = db.query(m.BrandRule).filter_by(brand_id=brand.id, is_active=True).order_by(m.BrandRule.id.asc()).all()
        channels = _preferred_content_channels(db, brand.id, dna, data.channels)

        voice = (dna.voice_json or {}) if dna else {}
        target_count = recommended_plan_size(voice, channels)
        week_date = local_week_start(data.week_start, brand.timezone)
        start_utc, end_utc = _week_bounds(week_date, brand.timezone)
        existing = (
            db.query(m.CalendarItem)
            .filter(
                m.CalendarItem.brand_id == brand.id,
                m.CalendarItem.scheduled_at >= start_utc,
                m.CalendarItem.scheduled_at < end_utc,
            )
            .order_by(m.CalendarItem.scheduled_at.asc())
            .all()
        )

        # The previous implementation created seven unmistakable English
        # placeholders. On the next Generate action, replace only those legacy
        # records, while preserving every manually edited/real calendar item.
        legacy_items = [item for item in existing if _is_legacy_placeholder(item)]
        if legacy_items:
            for item in legacy_items:
                db.delete(item)
            db.flush()
            existing = [item for item in existing if item not in legacy_items]

        remaining = max(0, target_count - len(existing))
        if remaining == 0:
            if legacy_items:
                db.commit()
            return {
                "items": [_calendar_item_out_local(item, db) for item in existing],
                "created_count": 0,
                "replaced_legacy_count": len(legacy_items),
                "target_count": target_count,
                "message": "This week already has enough planned content.",
            }

        # Build seven spread-out candidates, then fill only unused days until the
        # week reaches the recommended 4–5 items. This prevents duplicate floods
        # when the button is clicked more than once.
        candidates = build_week_plan(
            brand=brand,
            dna=dna,
            products=products,
            personas=personas,
            rules=rules,
            channels=channels,
            week_start=week_date,
            count=7,
        )
        tz = safe_zone(brand.timezone)
        used_dates = set()
        for item in existing:
            if not item.scheduled_at:
                continue
            current = item.scheduled_at
            if current.tzinfo is None:
                current = current.replace(tzinfo=timezone.utc)
            used_dates.add(current.astimezone(tz).date())

        made = []
        for candidate in candidates:
            if len(made) >= remaining:
                break
            if candidate["scheduled_at"].date() in used_dates:
                continue
            item = m.CalendarItem(
                brand_id=brand.id,
                campaign_id=data.campaign_id,
                title=candidate["title"],
                description=candidate["description"],
                channels_json=[candidate["channel"]],
                content_type=candidate["content_type"],
                status="idea",
                scheduled_at=candidate["scheduled_at"],
                timezone=candidate["timezone"],
                language=candidate["language"],
                goal=candidate["goal"],
                funnel_stage=candidate["funnel_stage"],
                persona_id=candidate["persona_id"],
                product_service_id=candidate["product_service_id"],
                cta=candidate["cta"],
                created_by_user_id=u.id,
                assigned_user_id=u.id,
            )
            db.add(item)
            db.flush()
            made.append(item)
            used_dates.add(candidate["scheduled_at"].date())

        db.commit()
        return {
            "items": [_calendar_item_out_local(item, db) for item in made],
            "created_count": len(made),
            "replaced_legacy_count": len(legacy_items),
            "target_count": target_count,
            "week_start": week_date.isoformat(),
            "timezone": brand.timezone,
            "channels": channels,
        }

    @app.post("/brands/{id}/calendar/generate-week", name="brand_calendar_generate_week_brand_aware")
    def generate_brand_week(
        id: int,
        u=Depends(legacy_main.user_from_auth),
        db: Session = Depends(get_db),
    ):
        return generate_week(legacy_main.CalendarGenerateIn(brand_id=id), u, db)

    @app.post("/brands/{id}/calendar/regenerate-week", name="brand_calendar_regenerate_week_brand_aware")
    def regenerate_brand_week(
        id: int,
        u=Depends(legacy_main.user_from_auth),
        db: Session = Depends(get_db),
    ):
        # Non-destructive by design: legacy placeholders may be replaced, while
        # real user edits, approvals, drafts, and published history are preserved.
        return generate_week(legacy_main.CalendarGenerateIn(brand_id=id), u, db)
