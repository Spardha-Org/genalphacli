"""TPS database models (SQLModel)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def generate_cuid() -> str:
    return secrets.token_hex(12)


def utc_now() -> datetime:
    return datetime.utcnow()


# ── Enums ──


class AuthType(str, Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"
    FORM_BASED_OAUTH2 = "form_based_oauth2"
    MTLS = "mtls"


class AppCategory(str, Enum):
    SOURCE_CONTROL = "source_control"
    HOSTING = "hosting"
    DISTRIBUTION = "distribution"
    COMING_SOON = "coming_soon"


class AppProvider(str, Enum):
    NATIVE = "native"


# ── App Marketplace ──


class AppMarketplace(SQLModel, table=True):
    __tablename__ = "tps_app_marketplace"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    app_code: int = Field(unique=True)  # stable integer ID: 14=GitHub, 95=GitLab
    app_name: str = Field(unique=True, index=True)  # slug: "github", "gitlab"
    display_name: str
    auth_type: str  # AuthType value
    category: str  # AppCategory value
    provider: str = Field(default="native")  # AppProvider value
    meta: dict = Field(default_factory=dict, sa_column=Column(JSON))
    authorize_url: Optional[str] = None
    token_url: Optional[str] = None
    scopes: Optional[str] = None
    is_install_required: bool = True  # true=OAuth redirect, false=form submit
    active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ── Integrations ──


class Integration(SQLModel, table=True):
    __tablename__ = "tps_integrations"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    workspace_id: str = Field(index=True)
    app_id: str = Field(foreign_key="tps_app_marketplace.id", index=True)
    app_name: str = Field(index=True)  # denormalized for quick lookups
    config_encrypted: str  # MultiFernet ciphertext
    status: str = Field(default="active")  # active | revoked
    identifier: Optional[str] = None  # display name: github login, email, etc.
    expires_at: Optional[float] = None  # Unix timestamp, plaintext for fast expiry checks
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ── OAuth States ──


def default_state_expiry() -> datetime:
    return datetime.utcnow() + timedelta(minutes=15)


class OAuthState(SQLModel, table=True):
    """Stores OAuth state parameters for CSRF validation. DB-backed so it survives process restarts."""

    __tablename__ = "tps_oauth_states"

    state: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32), primary_key=True
    )
    workspace_id: str
    app_name: str
    meta: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # form fields for form-based OAuth
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime = Field(default_factory=default_state_expiry)
