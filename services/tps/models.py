"""TPS service database models."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def generate_cuid() -> str:
    return secrets.token_hex(12)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AppMarketplace(SQLModel, table=True):
    __tablename__ = "tps_app_marketplace"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    app_name: str = Field(unique=True, index=True)  # github, gitlab, bitbucket
    display_name: str
    auth_type: str  # oauth2, api_key
    authorize_url: str | None = None
    token_url: str | None = None
    scopes: str | None = None
    icon_url: str | None = None
    active: bool = Field(default=True)


class Integration(SQLModel, table=True):
    __tablename__ = "tps_integrations"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    workspace_id: str = Field(index=True)  # From X-Workspace-ID header, not FK
    app_name: str = Field(index=True)
    config_encrypted: str  # Fernet-encrypted JSON
    status: str = Field(default="active")  # active, expired, revoked
    github_username: str | None = None  # Convenience field for display
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
