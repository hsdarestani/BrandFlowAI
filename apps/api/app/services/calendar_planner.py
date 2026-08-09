from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


CONTENT_CHANNELS = {
    "instagram",
    "telegram",
    "bale",
    "linkedin",
    "google_business",
    "tiktok",
    "youtube",
    "email",
    "blog",
    "other",
}


def safe_zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def listify(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.replace("\n", ",").split(",") if part.strip()]
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("name") or item.get("title") or item.get("label") or item.get("description")
            else:
                text = item
            if text is not None and str(text).strip():
                out.append(str(text).strip())
        return out
    return [str(value).strip()] if str(value).strip() else []


def local_week_start(value: datetime | None, timezone_name: str | None) -> date:
    tz = safe_zone(timezone_name)
    if value is None:
        today = datetime.now(tz).date()
        return today - timedelta(days=today.weekday())
    if value.tzinfo is None:
        local_date = value.date()
    else:
        local_date = value.astimezone(tz).date()
    return local_date - timedelta(days=local_date.weekday())


def recommended_plan_size(voice: dict, channels: list[str]) -> int:
    pillars = listify(voice.get("content_pillars"))
    # Four useful pieces is a better default than blindly filling every day.
    # Richer brands with several pillars/channels can support a fifth item.
    return 5 if len(pillars) >= 4 and len(channels) >= 2 else 4


def content_type_for(channel: str, index: int) -> str:
    if channel == "instagram":
        return ["carousel", "reel", "story", "post", "reel"][index % 5]
    if channel == "telegram":
        return "telegram_post"
    if channel == "bale":
        return "bale_post"
    if channel == "linkedin":
        return ["post", "carousel", "post", "post"][index % 4]
    if channel in {"tiktok", "youtube"}:
        return "short_video"
    if channel == "google_business":
        return "google_update"
    if channel == "email":
        return "email"
    if channel == "blog":
        return "blog"
    return "post"


def preferred_time(channel: str) -> time:
    return {
        "linkedin": time(9, 30),
        "email": time(10, 0),
        "blog": time(11, 0),
        "google_business": time(11, 30),
        "instagram": time(18, 30),
        "tiktok": time(19, 30),
        "youtube": time(19, 0),
        "telegram": time(20, 0),
        "bale": time(20, 0),
    }.get(channel, time(18, 0))


def _meta(product) -> dict:
    return (getattr(product, "metadata_json", None) or {}) if product else {}


def _product_value(product, key: str) -> list[str]:
    return listify(_meta(product).get(key))


def _first(values: list[str], fallback: str = "") -> str:
    return values[0] if values else fallback


def _copy_pack(language: str) -> dict[str, str]:
    if language == "fa":
        return {
            "education_title": "راهنمای {pillar} برای {audience}: چطور {outcome}؟",
            "problem_title": "{pain}؛ مسئله‌ای که {audience} نباید نادیده بگیرد",
            "proof_title": "چرا {product} برای {outcome} انتخاب قابل‌بررسی است؟",
            "value_title": "{product}: {value}",
            "objection_title": "قبل از انتخاب {product} این سؤال را جواب بدهید: {objection}",
            "conversion_title": "{product} برای {audience}؛ قدم بعدی برای {outcome}",
            "brief": "هدف: {goal}. مخاطب: {audience}. زاویه محتوا: {angle}. پیام اصلی: {message}. لحن: {tone}. قالب: {content_type}. دعوت به اقدام: {cta}.{guardrail}",
            "guardrail": " از ادعاهای ممنوع یا وعده قطعی استفاده نشود: {rules}.",
            "cta": "برای اطلاعات بیشتر پیام بدهید",
            "goals": ["آگاهی", "اعتماد", "تعامل", "تبدیل"],
        }
    if language == "de":
        return {
            "education_title": "{pillar} für {audience}: Wie gelingt {outcome}?",
            "problem_title": "{pain}: Was {audience} dabei beachten sollte",
            "proof_title": "Warum {product} für {outcome} relevant sein kann",
            "value_title": "{product}: {value}",
            "objection_title": "Vor {product}: Diese Frage zuerst klären – {objection}",
            "conversion_title": "{product} für {audience}: der nächste Schritt zu {outcome}",
            "brief": "Ziel: {goal}. Zielgruppe: {audience}. Content-Winkel: {angle}. Kernbotschaft: {message}. Ton: {tone}. Format: {content_type}. CTA: {cta}.{guardrail}",
            "guardrail": " Keine verbotenen oder garantierten Aussagen verwenden: {rules}.",
            "cta": "Mehr Informationen anfragen",
            "goals": ["Awareness", "Vertrauen", "Interaktion", "Conversion"],
        }
    return {
        "education_title": "{pillar} for {audience}: how to achieve {outcome}",
        "problem_title": "{pain}: what {audience} should know",
        "proof_title": "Why {product} can matter for {outcome}",
        "value_title": "{product}: {value}",
        "objection_title": "Before choosing {product}, answer this: {objection}",
        "conversion_title": "{product} for {audience}: the next step toward {outcome}",
        "brief": "Goal: {goal}. Audience: {audience}. Angle: {angle}. Core message: {message}. Tone: {tone}. Format: {content_type}. CTA: {cta}.{guardrail}",
        "guardrail": " Avoid prohibited or guaranteed claims: {rules}.",
        "cta": "Ask for more information",
        "goals": ["awareness", "trust", "engagement", "conversion"],
    }


def build_week_plan(
    *,
    brand,
    dna,
    products: list,
    personas: list,
    rules: list,
    channels: list[str],
    week_start: date,
    count: int,
) -> list[dict]:
    voice = (getattr(dna, "voice_json", None) or {}) if dna else {}
    compliance = (getattr(dna, "compliance_json", None) or {}) if dna else {}
    cta_data = (getattr(dna, "cta_library_json", None) or {}) if dna else {}
    language = getattr(brand, "primary_language", None) or "en"
    pack = _copy_pack(language)
    tz = safe_zone(getattr(brand, "timezone", None))

    clean_channels = [c for c in channels if c in CONTENT_CHANNELS] or ["instagram"]
    pillars = listify(voice.get("content_pillars")) or [
        {"fa": "آموزش", "de": "Wissen", "en": "Education"}.get(language, "Education")
    ]
    audience = str(voice.get("target_audience") or "").strip()
    if not audience and personas:
        audience = str(getattr(personas[0], "description", None) or getattr(personas[0], "name", "")).strip()
    audience = audience or {"fa": "مخاطبان هدف", "de": "die Zielgruppe", "en": "the target audience"}.get(language, "the target audience")
    pains = listify(voice.get("audience_pain_points"))
    outcomes = listify(voice.get("desired_outcomes"))
    values = listify(voice.get("value_propositions"))
    proof = listify(voice.get("proof_points"))
    objections = listify(voice.get("buyer_objections"))
    tone = str(voice.get("tone_of_voice") or voice.get("writing_style") or "").strip() or {
        "fa": "شفاف و طبیعی",
        "de": "klar und natürlich",
        "en": "clear and natural",
    }.get(language, "clear and natural")
    ctas = listify(cta_data.get("cta_preferences"))
    cta = _first(ctas, pack["cta"])

    forbidden = listify(compliance.get("forbidden_claims"))
    active_rule_text = [
        str(getattr(rule, "description", None) or getattr(rule, "title", "")).strip()
        for rule in rules
        if getattr(rule, "is_active", True)
    ]
    guardrails = [x for x in forbidden + active_rule_text if x][:3]

    day_offsets = [0, 2, 4, 6, 1, 3, 5]
    plan: list[dict] = []
    for index in range(count):
        channel = clean_channels[index % len(clean_channels)]
        content_type = content_type_for(channel, index)
        product = products[index % len(products)] if products else None
        product_name = str(getattr(product, "name", None) or getattr(brand, "name", "Brand")).strip()
        product_benefits = _product_value(product, "benefits")
        product_objections = _product_value(product, "objections")
        product_proof = _product_value(product, "proof_points")

        pillar = pillars[index % len(pillars)]
        pain = _first(pains, {"fa": "انتخاب و تصمیم‌گیری سخت", "de": "eine schwierige Entscheidung", "en": "a difficult decision"}.get(language, "a difficult decision"))
        outcome = _first(outcomes, _first(product_benefits, {"fa": "نتیجه بهتر", "de": "ein besseres Ergebnis", "en": "a better outcome"}.get(language, "a better outcome")))
        value = _first(product_benefits, _first(values, str(voice.get("differentiation") or outcome)))
        objection = _first(product_objections, _first(objections, pain))
        proof_point = _first(product_proof, _first(proof, value))

        angle_index = index % 4
        if angle_index == 0:
            template = "problem_title" if pains else "education_title"
            title = pack[template].format(pillar=pillar, audience=audience, outcome=outcome, pain=pain)
            angle = f"{pillar} · {pain}"
            message = f"{outcome}; {value}"
            goal = "awareness"
            funnel = "top"
        elif angle_index == 1:
            title = pack["proof_title"].format(product=product_name, outcome=outcome)
            angle = proof_point
            message = f"{value}; {proof_point}"
            goal = "trust"
            funnel = "middle"
        elif angle_index == 2:
            title = pack["objection_title"].format(product=product_name, objection=objection)
            angle = objection
            message = f"{value}; {outcome}"
            goal = "engagement"
            funnel = "middle"
        else:
            title = pack["conversion_title"].format(product=product_name, audience=audience, outcome=outcome)
            angle = value
            message = f"{product_name}: {value}"
            goal = "conversion"
            funnel = "bottom"

        guardrail = pack["guardrail"].format(rules="؛ ".join(guardrails)) if guardrails else ""
        description = pack["brief"].format(
            goal=pack["goals"][angle_index],
            audience=audience,
            angle=angle,
            message=message,
            tone=tone,
            content_type=content_type,
            cta=cta,
            guardrail=guardrail,
        )
        local_day = week_start + timedelta(days=day_offsets[index % len(day_offsets)])
        scheduled_at = datetime.combine(local_day, preferred_time(channel), tzinfo=tz)
        plan.append(
            {
                "title": title[:240],
                "description": description,
                "channel": channel,
                "content_type": content_type,
                "goal": goal,
                "funnel_stage": funnel,
                "scheduled_at": scheduled_at,
                "timezone": getattr(brand, "timezone", None) or "UTC",
                "language": language,
                "product_service_id": getattr(product, "id", None),
                "persona_id": getattr(personas[index % len(personas)], "id", None) if personas else None,
                "cta": cta,
            }
        )
    return plan
