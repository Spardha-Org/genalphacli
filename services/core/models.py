"""Core service database models (SQLModel)."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlmodel import Field, Relationship, SQLModel


def generate_cuid() -> str:
    """Generate a CUID-like ID (24 char hex)."""
    return secrets.token_hex(12)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── Users ──


class User(SQLModel, table=True):
    __tablename__ = "core_users"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str | None = None
    email_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)

    sessions: list[Session] = Relationship(back_populates="user")
    memberships: list[WorkspaceMember] = Relationship(back_populates="user")


# ── Sessions ──


class Session(SQLModel, table=True):
    __tablename__ = "core_sessions"

    session_id: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32), primary_key=True
    )
    user_id: str = Field(foreign_key="core_users.id", index=True)
    expires_at: datetime
    last_active_at: datetime = Field(default_factory=utc_now)
    user_agent: str | None = None

    user: User = Relationship(back_populates="sessions")


# ── Workspaces ──


class Workspace(SQLModel, table=True):
    __tablename__ = "core_workspaces"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    name: str
    slug: str = Field(unique=True, index=True)
    owner_id: str = Field(foreign_key="core_users.id")
    integration_id: str | None = None  # Reference to TPS integration
    created_at: datetime = Field(default_factory=utc_now)

    members: list[WorkspaceMember] = Relationship(back_populates="workspace")
    projects: list[Project] = Relationship(back_populates="workspace")


# ── Workspace Members ──


class WorkspaceMember(SQLModel, table=True):
    __tablename__ = "core_workspace_members"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    workspace_id: str = Field(foreign_key="core_workspaces.id", index=True)
    user_id: str = Field(foreign_key="core_users.id", index=True)
    role: str = Field(default="owner")
    created_at: datetime = Field(default_factory=utc_now)

    workspace: Workspace = Relationship(back_populates="members")
    user: User = Relationship(back_populates="memberships")


# ── Projects ──


class Project(SQLModel, table=True):
    __tablename__ = "core_projects"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    workspace_id: str = Field(foreign_key="core_workspaces.id", index=True)
    name: str
    description: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    workspace: Workspace = Relationship(back_populates="projects")
    services: list[Service] = Relationship(back_populates="project")


# ── Services ──


class Service(SQLModel, table=True):
    __tablename__ = "core_services"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    project_id: str = Field(foreign_key="core_projects.id", index=True)
    name: str
    repo_url: str | None = None
    framework: str | None = None
    status: str = Field(default="pending")
    route_graph: dict | None = Field(default=None, sa_type_kwargs={"astext_type": None})
    error_message: str | None = None
    parse_workflow_id: str | None = None
    generate_workflow_id: str | None = None
    download_url: str | None = None
    metadata_json: dict | None = Field(default=None, alias="metadata")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    project: Project = Relationship(back_populates="services")
