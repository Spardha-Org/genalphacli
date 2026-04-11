"""TPS database models (SQLModel)."""

from __future__ import annotations

import secrets
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def generate_cuid() -> str:
    return secrets.token_hex(12)


def utc_now() -> datetime:
    return datetime.utcnow()


# ── Enums ──


class AuthType(int, Enum):
    OAUTH2 = 1
    API_KEY = 2
    BASIC_AUTH = 3
    FORM_BASED_OAUTH2 = 4
    MTLS = 5

    @property
    def label(self) -> str:
        return _AUTH_TYPE_LABELS[self]


_AUTH_TYPE_LABELS = {
    AuthType.OAUTH2: "oauth2",
    AuthType.API_KEY: "api_key",
    AuthType.BASIC_AUTH: "basic_auth",
    AuthType.FORM_BASED_OAUTH2: "form_based_oauth2",
    AuthType.MTLS: "mtls",
}


class AppCategory(int, Enum):
    SOURCE_CONTROL = 1
    HOSTING = 2
    DISTRIBUTION = 3
    COMING_SOON = 4

    @property
    def label(self) -> str:
        return _CATEGORY_LABELS[self]


_CATEGORY_LABELS = {
    AppCategory.SOURCE_CONTROL: "source_control",
    AppCategory.HOSTING: "hosting",
    AppCategory.DISTRIBUTION: "distribution",
    AppCategory.COMING_SOON: "coming_soon",
}


class AppProvider(int, Enum):
    NATIVE = 1

    @property
    def label(self) -> str:
        return _PROVIDER_LABELS[self]


_PROVIDER_LABELS = {
    AppProvider.NATIVE: "native",
}


# ── App Marketplace ──


class AppMarketplace(SQLModel, table=True):
    __tablename__ = "tps_app_marketplace"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    app_code: int = Field(unique=True)  # stable integer ID: 14=GitHub, 95=GitLab
    app_name: str = Field(unique=True, index=True)  # slug: "github", "gitlab"
    display_name: str
    auth_type: int  # AuthType enum value (1=oauth2, 2=api_key, etc.)
    category: int  # AppCategory enum value (1=source_control, 2=hosting, etc.)
    provider: int = Field(default=1)  # AppProvider enum value (1=native)
    meta: dict = Field(default_factory=dict, sa_column=Column(JSON))  # icon, description, fields, keywords
    is_install_required: bool = True  # true=OAuth redirect, false=form submit
    active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ── Integrations ──


class Integration(SQLModel, table=True):
    __tablename__ = "tps_integrations"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    user_id: str = Field(index=True)
    app_id: str = Field(foreign_key="tps_app_marketplace.id", index=True)
    app_name: str = Field(index=True)  # denormalized for quick lookups
    config_encrypted: str  # MultiFernet ciphertext
    status: str = Field(default="active")  # active | revoked
    identifier: Optional[str] = None  # display name: github login, email, etc.
    expires_at: Optional[float] = None  # Unix timestamp, plaintext for fast expiry checks
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
