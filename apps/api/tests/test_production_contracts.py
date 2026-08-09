import pytest

from app.entrypoint import app
from app.services.ai.providers import AIConfigurationError, get_ai_provider
from app.services.connectors.providers import get_connector


def routes(path: str, method: str):
    return [
        route for route in app.router.routes
        if getattr(route, "path", None) == path
        and method.upper() in (getattr(route, "methods", set()) or set())
    ]


def test_primary_user_actions_have_one_canonical_production_route():
    expected = {
        ("/studio/generate", "POST"): "studio_generate_real_ai",
        ("/studio/drafts/{id}/transform", "POST"): "studio_transform_real_ai",
        ("/studio/drafts/{id}/compliance-check", "POST"): "studio_compliance_real",
        ("/calendar/generate-week", "POST"): "calendar_generate_week_ai",
        ("/campaigns/{id}/generate-plan", "POST"): "campaign_generate_plan_real_ai",
        ("/reports/{id}/export", "POST"): "reports_export_real",
        ("/reports/{id}/send-email", "POST"): "reports_send_brevo_real",
        ("/integrations/connections/{id}/test", "POST"): "integration_test_live",
        ("/drafts/{id}/publish-now", "POST"): "legacy_publish_now_real",
        ("/scheduled-posts/{id}/retry", "POST"): "scheduled_retry_real_queue",
        ("/approvals/requests/{id}/send-via-telegram", "POST"): "approval_send_telegram_rotatable",
        ("/approvals/requests/{id}/send-via-bale", "POST"): "approval_send_bale_rotatable",
    }
    for (path, method), name in expected.items():
        matched = routes(path, method)
        assert len(matched) == 1, (path, method, [r.name for r in matched])
        assert matched[0].name == name


def test_assisted_social_connectors_never_claim_direct_publish():
    for provider in ("instagram", "facebook", "linkedin", "tiktok", "youtube", "google_business"):
        connector = get_connector(provider)
        assert connector.capabilities.direct_publish is False
        assert connector.capabilities.assisted_publish is True


def test_unimplemented_ai_providers_fail_instead_of_returning_mock(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    with pytest.raises(AIConfigurationError):
        get_ai_provider()


def test_mock_ai_is_explicitly_not_real(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    provider = get_ai_provider()
    assert provider.is_real is False
    assert provider.provider_name == "mock"
