from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central runtime configuration.

    Production must fail fast when a deployment is still using development
    defaults.  This keeps mock/demo behavior from silently leaking into a real
    customer workspace.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    database_url: str = "sqlite:///./smarbiz.db"
    jwt_secret: str = "dev-change-me"
    jwt_expires_minutes: int = 60 * 24 * 7
    jwt_issuer: str = "smarbiz-api"

    ai_provider: str = "mock"
    demo_mode: bool = True
    allow_mock_connectors: bool = False
    allow_unsafe_dev_defaults: bool = False

    cors_origins: str = "http://localhost:3000,https://smarbiz.sbs,https://www.smarbiz.sbs"
    redis_url: str = "redis://redis:6379/0"
    connector_secret_key: str | None = None

    bale_base_url: str = "https://tapi.bale.ai/bot{token}/{method}"

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"prod", "production"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_runtime_config(self) -> None:
        if not self.is_production or self.allow_unsafe_dev_defaults:
            return

        errors: list[str] = []
        if self.database_url.startswith("sqlite"):
            errors.append("DATABASE_URL must point to Postgres in production; SQLite is development-only.")
        if self.jwt_secret in {"", "dev-change-me", "replace-with-strong-secret"} or len(self.jwt_secret) < 32:
            errors.append("JWT_SECRET must be a unique high-entropy value of at least 32 characters.")
        if self.demo_mode:
            errors.append("DEMO_MODE must be false in production.")
        if self.ai_provider.lower() == "mock":
            errors.append("AI_PROVIDER=mock is not allowed in production; configure a real provider or set APP_ENV=staging.")
        if self.allow_mock_connectors:
            errors.append("ALLOW_MOCK_CONNECTORS must be false in production.")
        if not self.connector_secret_key or len(self.connector_secret_key) < 32:
            errors.append("CONNECTOR_SECRET_KEY is required in production for encrypted connector credentials.")
        if "*" in self.cors_origin_list:
            errors.append("CORS_ORIGINS must not contain '*' in production.")
        if any("localhost" in origin or "127.0.0.1" in origin for origin in self.cors_origin_list):
            errors.append("CORS_ORIGINS must not contain localhost origins in production.")

        if errors:
            raise RuntimeError("Production configuration is not safe:\n- " + "\n- ".join(errors))


settings = Settings()
settings.validate_runtime_config()

engine_kwargs = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
