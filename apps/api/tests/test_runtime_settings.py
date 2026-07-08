import pytest

from app.database import Settings


def test_production_rejects_unmanaged_sqlite_and_mock_defaults():
    settings = Settings(
        app_env="production",
        database_url="sqlite:///./smarbiz.db",
        jwt_secret="dev-change-me",
        demo_mode=True,
        ai_provider="mock",
        allow_mock_connectors=True,
        connector_secret_key="",
        cors_origins="http://localhost:3000",
    )

    with pytest.raises(RuntimeError) as exc:
        settings.validate_runtime_config()

    message = str(exc.value)
    assert "SQLite is development-only" in message
    assert "JWT_SECRET" in message
    assert "DEMO_MODE" in message
    assert "AI_PROVIDER=mock" in message
    assert "ALLOW_MOCK_CONNECTORS" in message
    assert "CONNECTOR_SECRET_KEY" in message


def test_staging_allows_mock_defaults_for_demo_environments():
    settings = Settings(app_env="staging")
    settings.validate_runtime_config()
