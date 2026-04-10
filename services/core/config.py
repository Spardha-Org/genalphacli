"""Core service configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://genalpha:genalpha_dev@localhost:5432/genalpha"

    # Magic link
    magic_link_secret: str = "dev-secret-change-in-production"
    magic_link_max_age: int = 900  # 15 minutes
    app_url: str = "http://localhost:3000"

    # Session
    session_max_age: int = 60 * 60 * 24 * 7  # 7 days
    session_cookie_name: str = "session_id"
    session_cookie_secure: bool = False  # True in production

    # Email (Resend)
    resend_api_key: str = ""  # Get from resend.com
    email_from: str = "GenAlpha <onboarding@resend.dev>"  # Use resend.dev for testing

    # Temporal
    temporal_address: str = "localhost:7233"

    # TPS
    tps_url: str = "http://localhost:8001"
    tps_secret: str = "dev-tps-secret-change-in-production"
    tps_timeout: float = 10.0

    model_config = {"env_prefix": "CORE_"}


settings = Settings()
