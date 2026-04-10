"""TPS service database models."""

import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def generate_cuid() -> str:
    return secrets.token_hex(12)


def utc_now() -> datetime:
    return datetime.utcnow()


class AppMarketplace(SQLModel, table=True):
    __tablename__ = "tps_app_marketplace"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    app_name: str = Field(unique=True, index=True)
    display_name: str
    auth_type: str
    authorize_url: Optional[str] = None
    token_url: Optional[str] = None
    scopes: Optional[str] = None
    icon_url: Optional[str] = None
    active: bool = Field(default=True)


class OAuthState(SQLModel, table=True):
    """Stores OAuth state parameters for CSRF validation. DB-backed so it survives process restarts."""

    __tablename__ = "tps_oauth_states"

    state: str = Field(primary_key=True)
    workspace_id: str
    app_name: str
    created_at: datetime = Field(default_factory=utc_now)


class Integration(SQLModel, table=True):
    __tablename__ = "tps_integrations"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    workspace_id: str = Field(index=True)
    app_name: str = Field(index=True)
    config_encrypted: str
    status: str = Field(default="active")
    github_username: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
