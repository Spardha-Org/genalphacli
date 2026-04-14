"""Core service configuration via environment variables.

Uses nested settings with CORE_ prefix and __ delimiter.
Example: CORE_DATABASE__URL, CORE_AUTH__MAGIC_LINK_SECRET
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    url: str = "postgresql+asyncpg://esd:esd@localhost:11432/core"


class AuthSettings(BaseModel):
    magic_link_secret: str = "dev-secret-change-in-production"
    magic_link_max_age: int = 900  # 15 minutes
    session_max_age: int = 60 * 60 * 24 * 7  # 7 days
    session_cookie_name: str = "session_id"
    session_cookie_secure: bool = False  # True in production
    session_debounce_seconds: int = 300  # Only extend session if stale > 5 min


class EmailSettings(BaseModel):
    resend_api_key: str = ""
    from_address: str = "GenAlpha <onboarding@resend.dev>"


class TpsSettings(BaseModel):
    url: str = "http://localhost:8001"
    secret: str = "dev-tps-shared-secret"
    timeout: float = 10.0


class WorkerSettings(BaseModel):
    secret: str = "dev-worker-shared-secret"  # X-Worker-Secret for internal routes


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CORE_",
        env_nested_delimiter="__",
    )

    environment: str = "local"  # local | staging | production
    app_url: str = "http://localhost:3000"
    temporal_address: str = "localhost:7233"

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    tps: TpsSettings = Field(default_factory=TpsSettings)
    worker: WorkerSettings = Field(default_factory=WorkerSettings)

    # Backward compatibility — flat access for code that hasn't been refactored yet
    @property
    def database_url(self) -> str:
        return self.database.url

    @property
    def magic_link_secret(self) -> str:
        return self.auth.magic_link_secret

    @property
    def magic_link_max_age(self) -> int:
        return self.auth.magic_link_max_age

    @property
    def session_max_age(self) -> int:
        return self.auth.session_max_age

    @property
    def session_cookie_name(self) -> str:
        return self.auth.session_cookie_name

    @property
    def session_cookie_secure(self) -> bool:
        return self.auth.session_cookie_secure

    @property
    def resend_api_key(self) -> str:
        return self.email.resend_api_key

    @property
    def email_from(self) -> str:
        return self.email.from_address

    @property
    def tps_url(self) -> str:
        return self.tps.url

    @property
    def tps_secret(self) -> str:
        return self.tps.secret

    @property
    def tps_timeout(self) -> float:
        return self.tps.timeout


settings = Settings()
