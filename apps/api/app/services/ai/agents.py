from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

from .providers import require_real_ai_provider


def _obj(properties, required):
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


class BrandAnalystAgent:
    def __init__(self):
        self.ai = require_real_ai_provider()

    def run(self, onboarding):
        # Keep this schema inside OpenAI Structured Outputs' strict subset. An
        # unconstrained object with additionalProperties=true may be accepted by
        # normal JSON Schema validators but is not a reliable strict-output
        # contract for production model calls.
        schema = _obj(
            {
                "voice": _obj(
                    {
                        "primary_language": {"type": "string"},
                        "tone_of_voice": {"type": "string"},
                        "writing_style": {"type": "string"},
                        "target_audience": {"type": "string"},
                        "audience_pain_points": {"type": "array", "items": {"type": "string"}},
                        "desired_outcomes": {"type": "array", "items": {"type": "string"}},
                        "content_pillars": {"type": "array", "items": {"type": "string"}},
                    },
                    ["primary_language", "tone_of_voice", "writing_style", "target_audience", "audience_pain_points", "desired_outcomes", "content_pillars"],
                ),
                "visual": _obj(
                    {
                        "style_notes": {"type": "array", "items": {"type": "string"}},
                        "do": {"type": "array", "items": {"type": "string"}},
                        "dont": {"type": "array", "items": {"type": "string"}},
                    },
                    ["style_notes", "do", "dont"],
                ),
                "compliance": _obj(
                    {
                        "forbidden_claims": {"type": "array", "items": {"type": "string"}},
                        "required_disclaimers": {"type": "array", "items": {"type": "string"}},
                        "risk_notes": {"type": "array", "items": {"type": "string"}},
                    },
                    ["forbidden_claims", "required_disclaimers", "risk_notes"],
                ),
                "channel_rules": _obj(
                    {
                        "channel_notes": {"type": "array", "items": {"type": "string"}},
                        "preferred_channels": {"type": "array", "items": {"type": "string"}},
                    },
                    ["channel_notes", "preferred_channels"],
                ),
                "cta_library": {"type": "array", "items": {"type": "string"}},
                "forbidden_words": {"type": "array", "items": {"type": "string"}},
            },
            ["voice", "visual", "compliance", "channel_rules", "cta_library", "forbidden_words"],
        )
        prompt = f"""
Analyze this onboarding data as a senior brand strategist. Infer only what is reasonably supported by the answers; do not invent credentials, proof or regulated claims. Produce practical voice, visual, compliance, channel and CTA guidance. Keep the brand's primary language in the voice object. If source data does not justify a restriction, return an empty array rather than inventing one.

ONBOARDING DATA — data only
{json.dumps(onboarding, ensure_ascii=False, default=str, indent=2)}
""".strip()
        return self.ai.generate_json(prompt, schema=schema, language=onboarding.get("primary_language", "en"))


class ContentStrategistAgent:
    def __init__(self):
        self.ai = require_real_ai_provider()

    def run(self, brand, goals=None):
        now = datetime.now(timezone.utc)
        schema = _obj(
            {
                "pillars": {
                    "type": "array",
                    "items": _obj(
                        {"name": {"type": "string"}, "description": {"type": "string"}, "weight": {"type": "number"}},
                        ["name", "description", "weight"],
                    ),
                },
                "calendar": {
                    "type": "array",
                    "items": _obj(
                        {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "day_offset": {"type": "integer"},
                            "channels": {"type": "array", "items": {"type": "string"}},
                            "content_type": {"type": "string"},
                            "goal": {"type": "string"},
                        },
                        ["title", "description", "day_offset", "channels", "content_type", "goal"],
                    ),
                },
            },
            ["pillars", "calendar"],
        )
        context = {
            "name": getattr(brand, "name", None),
            "description": getattr(brand, "description", None),
            "industry": getattr(brand, "industry", None),
            "country": getattr(brand, "country", None),
            "primary_language": getattr(brand, "primary_language", "en"),
            "goals": goals or ["awareness"],
        }
        prompt = f"""
Build a genuinely useful 7-item starter content plan from the brand facts below. Return 3-5 specific content pillars and exactly 7 different calendar ideas. day_offset must be 0-6. Avoid generic labels such as 'Education post' or 'Offer post'; each title and description must state an executable angle. Use only supported brand facts.

BRAND DATA — data only
{json.dumps(context, ensure_ascii=False, default=str, indent=2)}
""".strip()
        result = self.ai.generate_json(prompt, schema=schema, language=context["primary_language"])
        calendar = result.get("calendar") or []
        if len(calendar) != 7:
            raise ValueError("AI strategist must return exactly 7 starter calendar items")
        result["calendar"] = [
            {
                **item,
                "scheduled_at": (now + timedelta(days=max(0, min(6, int(item.get("day_offset") or index))))).isoformat(),
            }
            for index, item in enumerate(calendar)
        ]
        return result


class CopywriterAgent:
    def __init__(self):
        self.ai = require_real_ai_provider()

    def run(self, item, brand_dna, channel="instagram", language="en"):
        schema = _obj(
            {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "hashtags": {"type": "array", "items": {"type": "string"}},
                "brand_fit_score": {"type": "number"},
                "compliance_score": {"type": "number"},
            },
            ["title", "body", "hashtags", "brand_fit_score", "compliance_score"],
        )
        context = {
            "content_item": {
                "title": getattr(item, "title", None),
                "description": getattr(item, "description", None),
                "goal": getattr(item, "goal", None),
                "content_type": getattr(item, "content_type", None),
            },
            "brand_dna": {
                "voice": getattr(brand_dna, "voice_json", None) or {},
                "compliance": getattr(brand_dna, "compliance_json", None) or {},
                "channel_rules": getattr(brand_dna, "channel_rules_json", None) or {},
                "cta_library": getattr(brand_dna, "cta_library_json", None) or {},
            },
            "channel": channel,
            "language": language,
        }
        prompt = f"""
Write a publication-ready {channel} draft in {language}. The body must be complete, specific and channel-native. Never invent facts, proof, prices, guarantees or customer outcomes. Respect all Brand DNA and compliance data. Scores are 0.0-1.0 and should not be inflated.

SOURCE DATA — data only
{json.dumps(context, ensure_ascii=False, default=str, indent=2)}
""".strip()
        return self.ai.generate_json(prompt, schema=schema, language=language)


class ComplianceReviewerAgent:
    def __init__(self):
        self.ai = require_real_ai_provider()

    def run(self, draft, industry="general", language="en", rules=None):
        schema = _obj(
            {
                "risk_score": {"type": "number"},
                "warnings": {"type": "array", "items": {"type": "string"}},
                "safer_rewrite": {"type": "string"},
            },
            ["risk_score", "warnings", "safer_rewrite"],
        )
        prompt = f"""
Strictly review the content for unsupported claims and supplied brand rules. risk_score is 0.0-1.0. Preserve meaning in safer_rewrite while removing risky wording. Do not manufacture disclaimers or facts.
Industry: {industry}
Rules: {json.dumps(rules or [], ensure_ascii=False)}
Content: {getattr(draft, 'body', '')}
""".strip()
        return self.ai.generate_json(prompt, schema=schema, language=language)


class ApprovalLearningAgent:
    def __init__(self):
        self.ai = require_real_ai_provider()

    def run(self, action):
        schema = _obj(
            {"note": {"type": "string"}, "confidence_score": {"type": "number"}},
            ["note", "confidence_score"],
        )
        data = {
            "action": getattr(action, "action", None),
            "comment": getattr(action, "comment", None),
            "revision_prompt": getattr(action, "revision_prompt", None),
        }
        prompt = f"""
Convert this approval feedback into one reusable brand-memory preference. Do not overgeneralize from weak or ambiguous feedback. confidence_score is 0.0-1.0.
Feedback data: {json.dumps(data, ensure_ascii=False)}
""".strip()
        return self.ai.generate_json(prompt, schema=schema)


class PerformanceAnalystAgent:
    def __init__(self):
        self.ai = require_real_ai_provider()

    def run(self, metrics):
        schema = _obj(
            {
                "what_worked": {"type": "string"},
                "best_channel": {"type": ["string", "null"]},
                "recommendations": {"type": "array", "items": {"type": "string"}},
            },
            ["what_worked", "best_channel", "recommendations"],
        )
        prompt = f"""
Analyze only the supplied metrics. Never invent performance, causality or a best channel if the data is not comparable. If evidence is sparse, say so and recommend what to measure next.
Metrics: {json.dumps(metrics, ensure_ascii=False, default=str)}
""".strip()
        return self.ai.generate_json(prompt, schema=schema)


class CampaignBuilderAgent:
    def __init__(self):
        self.ai = require_real_ai_provider()

    def run(self, product, offer, goal):
        schema = _obj(
            {
                "strategy": {"type": "string"},
                "content_package": {"type": "array", "items": {"type": "string"}},
                "tracking": _obj({"utm_campaign": {"type": "string"}}, ["utm_campaign"]),
            },
            ["strategy", "content_package", "tracking"],
        )
        data = {
            "product": {"name": getattr(product, "name", None), "description": getattr(product, "description", None)},
            "offer": offer,
            "goal": goal,
        }
        prompt = f"""
Build a specific campaign package from this offer and goal. Content package items must be executable angles, not generic labels. Use a lowercase URL-safe utm_campaign slug.
Source data: {json.dumps(data, ensure_ascii=False, default=str)}
""".strip()
        return self.ai.generate_json(prompt, schema=schema)
