from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.calendar_planner import build_week_plan, local_week_start, recommended_plan_size


def _fixture():
    brand = SimpleNamespace(
        id=7,
        name="ایلیا کهن آوای نو",
        primary_language="fa",
        timezone="Asia/Tehran",
    )
    dna = SimpleNamespace(
        voice_json={
            "target_audience": "مدیران کسب‌وکارهای کوچک",
            "audience_pain_points": ["بی‌نظمی در بازاریابی"],
            "desired_outcomes": ["برنامه محتوایی منظم"],
            "tone_of_voice": "شفاف و صمیمی",
            "content_pillars": ["آموزش", "اعتمادسازی", "مدیریت"],
            "value_propositions": ["صرفه‌جویی در زمان"],
            "buyer_objections": ["آیا برای تیم کوچک هم مناسب است؟"],
        },
        compliance_json={"forbidden_claims": ["نتیجه تضمینی"]},
        cta_library_json={"cta_preferences": ["برای مشاوره پیام بدهید"]},
    )
    product = SimpleNamespace(
        id=11,
        name="مشاوره مدیریت",
        metadata_json={
            "benefits": ["تصمیم‌گیری سریع‌تر"],
            "proof_points": ["فرایند مرحله‌به‌مرحله"],
        },
    )
    persona = SimpleNamespace(id=12, name="مدیر", description="مدیر کسب‌وکار کوچک")
    rule = SimpleNamespace(id=13, title="بدون اغراق", description="وعده قطعی داده نشود", is_active=True)
    return brand, dna, [product], [persona], [rule]


def test_tehran_week_start_recovers_local_monday_from_utc_iso():
    # Monday 00:00 Tehran is Sunday 20:30 UTC during Iran standard time.
    value = datetime(2026, 8, 2, 20, 30, tzinfo=timezone.utc)
    assert local_week_start(value, "Asia/Tehran").isoformat() == "2026-08-03"


def test_brand_pulse_plan_is_not_placeholder_and_uses_local_timezone():
    brand, dna, products, personas, rules = _fixture()
    week = local_week_start(datetime(2026, 8, 3), brand.timezone)
    plan = build_week_plan(
        brand=brand,
        dna=dna,
        products=products,
        personas=personas,
        rules=rules,
        channels=["instagram"],
        week_start=week,
        count=4,
    )

    assert len(plan) == 4
    assert recommended_plan_size(dna.voice_json, ["instagram"]) == 4
    assert {item["content_type"] for item in plan} == {"carousel", "reel", "story", "post"}
    assert all("Draft content idea" not in item["title"] for item in plan)
    assert any("مشاوره مدیریت" in item["title"] for item in plan)
    assert any("مدیران کسب‌وکارهای کوچک" in item["description"] for item in plan)
    assert any("نتیجه تضمینی" in item["description"] for item in plan)
    assert all(item["scheduled_at"].tzinfo is not None for item in plan)
    assert all(item["scheduled_at"].utcoffset().total_seconds() == 12600 for item in plan)
    assert plan[0]["scheduled_at"].hour == 18
    assert plan[0]["scheduled_at"].minute == 30


def test_richer_multichannel_plan_uses_five_items_and_channel_specific_types():
    brand, dna, products, personas, rules = _fixture()
    dna.voice_json["content_pillars"].append("فروش")
    assert recommended_plan_size(dna.voice_json, ["instagram", "telegram"]) == 5
    week = local_week_start(datetime(2026, 8, 3), brand.timezone)
    plan = build_week_plan(
        brand=brand,
        dna=dna,
        products=products,
        personas=personas,
        rules=rules,
        channels=["instagram", "telegram"],
        week_start=week,
        count=5,
    )
    assert [item["channel"] for item in plan] == ["instagram", "telegram", "instagram", "telegram", "instagram"]
    assert plan[1]["content_type"] == "telegram_post"
    assert plan[1]["scheduled_at"].hour == 20
