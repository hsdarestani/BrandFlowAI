from datetime import date
from types import SimpleNamespace

import pytest

from app.services.ai_calendar_planner import AIWeeklyPlanError, build_ai_week_plan, weekly_plan_schema


def approved_critique(score=94):
    return {
        "approved": True,
        "overall_score": score,
        "specificity_score": 93,
        "brand_fit_score": 95,
        "platform_fit_score": 92,
        "strategic_diversity_score": 91,
        "factual_grounding_score": 98,
        "execution_quality_score": 94,
        "strengths": ["Specific and executable"],
        "issues": [],
    }


def sample_plan():
    return {
        "strategy_summary": "هفته روی آموزش، اعتماد و تبدیل متمرکز است.",
        "items": [
            {
                "date": "2026-08-10",
                "time": "18:30",
                "channel": "instagram",
                "content_type": "carousel",
                "title": "قبل از خرید سرور، این ۳ هزینه پنهان را حساب کن",
                "hook": "قیمت ماهانه فقط بخشی از هزینه واقعی زیرساخت است.",
                "brief": "سه هزینه‌ای را که تیم‌های کوچک معمولاً دیر متوجه می‌شوند توضیح بده و برای هرکدام یک راه بررسی عملی قبل از خرید ارائه کن.",
                "creative_direction": "کاروسل ۵ اسلایدی با یک هزینه در هر اسلاید و چک‌لیست جمع‌بندی در اسلاید آخر.",
                "goal": "awareness",
                "funnel_stage": "top",
                "cta": "برای مقایسه پلن مناسب پیام بده.",
                "product_service_id": 11,
                "persona_id": 21,
            },
            {
                "date": "2026-08-12",
                "time": "20:00",
                "channel": "instagram",
                "content_type": "reel",
                "title": "چه زمانی سرور ارزان واقعاً گران تمام می‌شود؟",
                "hook": "اگر هر قطعی برایت فروش یا زمان تیم را می‌سوزاند، فقط قیمت را مقایسه نکن.",
                "brief": "با یک سناریوی واقعی اما بدون عددسازی نشان بده چه معیارهایی برای انتخاب زیرساخت مهم‌تر از کمترین قیمت هستند و مزیت سرویس را فقط از داده‌های برند توضیح بده.",
                "creative_direction": "ویدیوی talking-head با سه کات سریع، نمایش داشبورد و متن کوتاه روی تصویر برای هر معیار.",
                "goal": "trust",
                "funnel_stage": "middle",
                "cta": "نیازت را بگو تا گزینه مناسب را بررسی کنیم.",
                "product_service_id": 11,
                "persona_id": 21,
            },
        ],
    }


class FakeAI:
    is_real = True
    provider_name = "openai"
    model = "test-model"

    def __init__(self):
        self.prompts = []

    def generate_json(self, prompt, schema=None, language="en"):
        self.prompts.append(prompt)
        if "independent, skeptical senior content director" in prompt:
            return approved_critique()
        return sample_plan()


class WrongCountAI(FakeAI):
    def generate_json(self, prompt, schema=None, language="en"):
        self.prompts.append(prompt)
        result = sample_plan()
        result["items"] = result["items"][:1]
        return result


class CriticRetryAI(FakeAI):
    def __init__(self):
        super().__init__()
        self.critic_calls = 0

    def generate_json(self, prompt, schema=None, language="en"):
        self.prompts.append(prompt)
        if "independent, skeptical senior content director" in prompt:
            self.critic_calls += 1
            if self.critic_calls == 1:
                return {
                    "approved": False,
                    "overall_score": 73,
                    "specificity_score": 68,
                    "brand_fit_score": 75,
                    "platform_fit_score": 82,
                    "strategic_diversity_score": 70,
                    "factual_grounding_score": 96,
                    "execution_quality_score": 72,
                    "strengths": ["Grounded"],
                    "issues": ["Use more specific audience pains and make the two angles less similar."],
                }
            return approved_critique(91)
        return sample_plan()


def _fixtures():
    brand = SimpleNamespace(
        name="HamoonCloud",
        description="Hetzner servers with local payment and support",
        industry="cloud hosting",
        country="IR",
        website_url="https://example.com",
        primary_language="fa",
        timezone="Asia/Tehran",
    )
    dna = SimpleNamespace(
        voice_json={
            "target_audience": "توسعه‌دهنده‌ها و کسب‌وکارهای کوچک",
            "audience_pain_points": ["هزینه ارزی", "پیچیدگی خرید سرور خارجی"],
            "desired_outcomes": ["راه‌اندازی سریع و قابل اتکا"],
            "tone_of_voice": "مستقیم و فنی",
            "content_pillars": ["آموزش", "اعتماد", "مقایسه", "پیشنهاد"],
        },
        compliance_json={"forbidden_claims": ["تضمین بدون قطعی"]},
        visual_json={},
        channel_rules_json={},
        cta_library_json={"cta_preferences": ["برای انتخاب پلن پیام بده"]},
    )
    product = SimpleNamespace(
        id=11,
        type="service",
        name="Hetzner Cloud",
        description="سرور ابری",
        metadata_json={
            "benefits": ["پرداخت ریالی", "فعال‌سازی سریع"],
            "objections": ["نگرانی از پشتیبانی"],
            "proof_points": ["سرور اصلی Hetzner"],
        },
    )
    persona = SimpleNamespace(
        id=21,
        name="Developer",
        segment="SMB",
        description="توسعه‌دهنده فارسی‌زبان",
        pains=["پرداخت خارجی"],
        desires=["راه‌اندازی سریع"],
        objections=["پشتیبانی"],
        preferred_channels=["instagram"],
        language="fa",
    )
    return brand, dna, [product], [persona]


def _build(fake):
    brand, dna, products, personas = _fixtures()
    return build_ai_week_plan(
        brand=brand,
        dna=dna,
        products=products,
        personas=personas,
        rules=[],
        memory_notes=[],
        campaign=None,
        channels=["instagram"],
        week_start=date(2026, 8, 10),
        count=2,
        available_dates=[date(2026, 8, 10), date(2026, 8, 12), date(2026, 8, 14)],
        existing_titles=["یک عنوان قدیمی"],
        provider=fake,
    )


def test_weekly_schema_locks_channels_without_risky_array_keywords():
    schema = weekly_plan_schema(4, ["instagram", "linkedin"])
    items = schema["properties"]["items"]
    assert items["type"] == "array"
    assert "minItems" not in items
    assert "maxItems" not in items
    assert items["items"]["properties"]["channel"]["enum"] == ["instagram", "linkedin"]


def test_ai_week_plan_uses_model_output_brand_timezone_and_critic():
    fake = FakeAI()
    plan, meta = _build(fake)

    assert len(plan) == 2
    assert plan[0]["title"].startswith("قبل از خرید سرور")
    assert "هوک:" in plan[0]["description"]
    assert plan[0]["scheduled_at"].utcoffset().total_seconds() == 3.5 * 3600
    assert plan[0]["product_service_id"] == 11
    assert meta["strategy_summary"] == "هفته روی آموزش، اعتماد و تبدیل متمرکز است."
    assert meta["provider"] == "openai"
    assert meta["model"] == "test-model"
    assert meta["quality_score"] == 94
    assert meta["quality_scores"]["factual_grounding"] == 98
    assert len(fake.prompts) == 2
    assert "template generator" in fake.prompts[0]
    assert "توسعه‌دهنده‌ها و کسب‌وکارهای کوچک" in fake.prompts[0]
    assert "independent, skeptical senior content director" in fake.prompts[1]


def test_ai_week_plan_retries_then_rejects_wrong_item_count():
    fake = WrongCountAI()
    with pytest.raises(AIWeeklyPlanError, match="expected exactly 2 items"):
        _build(fake)
    assert len(fake.prompts) == 2
    assert "previous candidate plan was rejected" in fake.prompts[1]


def test_ai_critic_rejects_mediocre_plan_and_forces_full_regeneration():
    fake = CriticRetryAI()
    plan, meta = _build(fake)
    assert len(plan) == 2
    assert meta["quality_score"] == 91
    assert fake.critic_calls == 2
    assert len(fake.prompts) == 4
    second_planner_prompt = fake.prompts[2]
    assert "AI quality critic rejected the plan" in second_planner_prompt
    assert "Use more specific audience pains" in second_planner_prompt
