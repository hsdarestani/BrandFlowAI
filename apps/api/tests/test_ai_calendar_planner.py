from datetime import date
from types import SimpleNamespace

from app.services.ai_calendar_planner import build_ai_week_plan, weekly_plan_schema


class FakeAI:
    is_real = True
    provider_name = "openai"
    model = "test-model"

    def __init__(self):
        self.prompts = []

    def generate_json(self, prompt, schema=None, language="en"):
        self.prompts.append(prompt)
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


def test_weekly_schema_locks_count_and_channels():
    schema = weekly_plan_schema(4, ["instagram", "linkedin"])
    assert schema["properties"]["items"]["minItems"] == 4
    assert schema["properties"]["items"]["maxItems"] == 4
    assert schema["properties"]["items"]["items"]["properties"]["channel"]["enum"] == ["instagram", "linkedin"]


def test_ai_week_plan_uses_model_output_and_brand_timezone():
    brand, dna, products, personas = _fixtures()
    fake = FakeAI()
    plan, meta = build_ai_week_plan(
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

    assert len(plan) == 2
    assert plan[0]["title"].startswith("قبل از خرید سرور")
    assert "هوک:" in plan[0]["description"]
    assert plan[0]["scheduled_at"].utcoffset().total_seconds() == 3.5 * 3600
    assert plan[0]["product_service_id"] == 11
    assert meta == {
        "strategy_summary": "هفته روی آموزش، اعتماد و تبدیل متمرکز است.",
        "provider": "openai",
        "model": "test-model",
    }
    assert "template generator" in fake.prompts[0]
    assert "توسعه‌دهنده‌ها و کسب‌وکارهای کوچک" in fake.prompts[0]
