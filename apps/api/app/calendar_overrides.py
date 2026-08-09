from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import re

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from . import main as legacy_main
from . import models as m
from .database import get_db
from .services.ai.providers import AIConfigurationError, AIProviderError
from .services.ai_calendar_planner import AIWeeklyPlanError, build_ai_week_plan
from .services.calendar_planner import (
    CONTENT_CHANNELS,
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
    """Serialize planned wall-clock time in the brand/item timezone."""

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
    """Resolve channels for planning, independent of publishing OAuth."""

    clean: list[str] = []
    for channel in requested or []:
        _append_channel(clean, channel)
    if clean:
        return clean

    for row in db.query(m.ChannelAccount).filter_by(brand_id=brand_id).all():
        _append_channel(clean, row.provider)

    channel_rules = (getattr(dna, "channel_rules_json", None) or {}) if dna else {}
    for note in listify(channel_rules.get("channel_notes")):
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


def _recent_titles(db: Session, brand_id: int) -> list[str]:
    rows = (
        db.query(m.CalendarItem)
        .filter_by(brand_id=brand_id)
        .order_by(m.CalendarItem.scheduled_at.desc())
        .limit(35)
        .all()
    )
    return [str(item.title).strip() for item in rows if str(item.title or "").strip()]


def install_calendar_overrides(app) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    legacy_main.calendar_item_out = _calendar_item_out_local

    for path in (
        "/calendar/generate-week",
        "/brands/{id}/calendar/generate-week",
        "/brands/{id}/calendar/regenerate-week",
    ):
        _remove_route(app, path, "POST")

    @app.post("/calendar/generate-week", name="calendar_generate_week_ai")
    def generate_week(
        data: legacy_main.CalendarGenerateIn,
        u=Depends(legacy_main.user_from_auth),
        db: Session = Depends(get_db),
    ):
        _, brand = legacy_main.org_brand_or_404(db, u, data.brand_id)
        setup = legacy_main.setup_state(db, brand)
        blocking = [
            item
            for item in setup["missing_requirements"]
            if item.get("id") in {"brand_pulse", "product_service"}
        ]
        if blocking:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Complete Brand Pulse and add an offer before generating an AI week",
                    "missing_requirements": blocking,
                    "action_links": blocking,
                },
            )

        dna = db.query(m.BrandDNA).filter_by(brand_id=brand.id).first()
        products = db.query(m.ProductService).filter_by(brand_id=brand.id).order_by(m.ProductService.id.asc()).all()
        personas = db.query(m.Persona).filter_by(brand_id=brand.id).order_by(m.Persona.id.asc()).all()
        rules = db.query(m.BrandRule).filter_by(brand_id=brand.id, is_active=True).order_by(m.BrandRule.id.asc()).all()
        memory_notes = (
            db.query(m.BrandMemoryNote)
            .filter_by(brand_id=brand.id)
            .order_by(m.BrandMemoryNote.created_at.desc())
            .limit(15)
            .all()
        )
        channels = _preferred_content_channels(db, brand.id, dna, data.channels)

        campaign = None
        if data.campaign_id:
            campaign = db.get(m.Campaign, data.campaign_id)
            if not campaign or campaign.brand_id != brand.id:
                raise HTTPException(
                    status_code=403,
                    detail={"error": "wrong_campaign", "message": "Campaign is outside this brand"},
                )

        voice = (dna.voice_json or {}) if dna else {}
        target_count = recommended_plan_size(voice, channels)
        week_date = local_week_start(data.week_start, brand.timezone)
        start_utc, end_utc = _week_bounds(week_date, brand.timezone)
        existing_all = (
            db.query(m.CalendarItem)
            .filter(
                m.CalendarItem.brand_id == brand.id,
                m.CalendarItem.scheduled_at >= start_utc,
                m.CalendarItem.scheduled_at < end_utc,
            )
            .order_by(m.CalendarItem.scheduled_at.asc())
            .all()
        )

        # Old generated junk never counts toward the real plan, but genuine user
        # edits, approvals, drafts, and published items are preserved.
        legacy_items = [item for item in existing_all if _is_legacy_placeholder(item)]
        existing = [item for item in existing_all if item not in legacy_items]
        remaining = max(0, target_count - len(existing))

        if remaining == 0:
            if legacy_items:
                for item in legacy_items:
                    db.delete(item)
                db.commit()
            return {
                "items": [_calendar_item_out_local(item, db) for item in existing],
                "created_count": 0,
                "replaced_legacy_count": len(legacy_items),
                "target_count": target_count,
                "generation_source": "ai",
                "message": "This week already has enough real planned content.",
            }

        tz = safe_zone(brand.timezone)
        used_dates = set()
        for item in existing:
            if not item.scheduled_at:
                continue
            current = item.scheduled_at
            if current.tzinfo is None:
                current = current.replace(tzinfo=timezone.utc)
            used_dates.add(current.astimezone(tz).date())
        available_dates = [week_date + timedelta(days=offset) for offset in range(7)]
        available_dates = [day for day in available_dates if day not in used_dates]

        try:
            candidates, ai_meta = build_ai_week_plan(
                brand=brand,
                dna=dna,
                products=products,
                personas=personas,
                rules=rules,
                memory_notes=memory_notes,
                campaign=campaign,
                channels=channels,
                week_start=week_date,
                count=remaining,
                available_dates=available_dates,
                existing_titles=_recent_titles(db, brand.id),
            )
        except AIConfigurationError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "ai_not_configured",
                    "message": "Real AI is required for calendar generation but the production AI provider is not configured.",
                },
            ) from exc
        except (AIProviderError, AIWeeklyPlanError) as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "ai_generation_failed",
                    "message": "AI could not produce a calendar plan that passed quality checks. Try again.",
                    "provider_detail": str(exc)[:500],
                },
            ) from exc

        # Only mutate the calendar after a valid AI plan exists. This prevents a
        # provider outage from damaging real user work.
        for item in legacy_items:
            db.delete(item)
        db.flush()

        made = []
        for candidate in candidates:
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

        db.commit()
        return {
            "items": [_calendar_item_out_local(item, db) for item in made],
            "created_count": len(made),
            "replaced_legacy_count": len(legacy_items),
            "target_count": target_count,
            "week_start": week_date.isoformat(),
            "timezone": brand.timezone,
            "channels": channels,
            "generation_source": "ai",
            "ai_provider": ai_meta.get("provider"),
            "ai_model": ai_meta.get("model"),
            "strategy_summary": ai_meta.get("strategy_summary"),
        }

    @app.post("/brands/{id}/calendar/generate-week", name="brand_calendar_generate_week_ai")
    def generate_brand_week(
        id: int,
        u=Depends(legacy_main.user_from_auth),
        db: Session = Depends(get_db),
    ):
        return generate_week(legacy_main.CalendarGenerateIn(brand_id=id), u, db)

    @app.post("/brands/{id}/calendar/regenerate-week", name="brand_calendar_regenerate_week_ai")
    def regenerate_brand_week(
        id: int,
        u=Depends(legacy_main.user_from_auth),
        db: Session = Depends(get_db),
    ):
        return generate_week(legacy_main.CalendarGenerateIn(brand_id=id), u, db)
