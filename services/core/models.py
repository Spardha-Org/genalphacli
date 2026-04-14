"""Core service database models (SQLModel)."""

from __future__ import annotations

import enum
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Column, LargeBinary, UniqueConstraint, event, text
from sqlmodel import Field, Relationship, SQLModel


def generate_id() -> str:
    """Generate a random 24-character hex ID."""
    return secrets.token_hex(12)


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


# ── Enums ──


class ServiceStatus(str, enum.Enum):
    PENDING = "pending"
    CLONING = "cloning"
    DOWNLOADING = "downloading"
    PARSING = "parsing"
    PARSED = "parsed"
    GENERATING = "generating"
    PACKAGING = "packaging"
    PUBLISHING = "publishing"
    COMPLETE = "complete"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class SourceType(str, enum.Enum):
    GITHUB = "github"
    PYPI = "pypi"


class ArtifactType(str, enum.Enum):
    CLI = "cli"
    MCP = "mcp"


class WorkspaceRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


# ── Users ──


class User(SQLModel, table=True):
    __tablename__ = "core_users"

    id: str = Field(default_factory=generate_id, primary_key=True)
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

    user: User | None = Relationship(back_populates="sessions")


# ── Workspaces ──


class Workspace(SQLModel, table=True):
    __tablename__ = "core_workspaces"

    id: str = Field(default_factory=generate_id, primary_key=True)
    name: str
    slug: str = Field(unique=True, index=True)
    owner_id: str = Field(foreign_key="core_users.id")
    integration_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    members: list[WorkspaceMember] = Relationship(back_populates="workspace")
    projects: list[Project] = Relationship(
        back_populates="workspace",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


# ── Workspace Members ──


class WorkspaceMember(SQLModel, table=True):
    __tablename__ = "core_workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id"),)

    id: str = Field(default_factory=generate_id, primary_key=True)
    workspace_id: str = Field(foreign_key="core_workspaces.id", index=True)
    user_id: str = Field(foreign_key="core_users.id", index=True)
    role: str = Field(default=WorkspaceRole.OWNER.value)
    created_at: datetime = Field(default_factory=utc_now)

    workspace: Workspace | None = Relationship(back_populates="members")
    user: User | None = Relationship(back_populates="memberships")


# ── Projects ──


class Project(SQLModel, table=True):
    __tablename__ = "core_projects"

    id: str = Field(default_factory=generate_id, primary_key=True)
    workspace_id: str = Field(foreign_key="core_workspaces.id", index=True)
    name: str
    description: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    workspace: Workspace | None = Relationship(back_populates="projects")
    services: list[Service] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


# ── Services ──


class Service(SQLModel, table=True):
    __tablename__ = "core_services"

    id: str = Field(default_factory=generate_id, primary_key=True)
    project_id: str = Field(foreign_key="core_projects.id", index=True)
    name: str
    repo_url: str | None = None
    source_type: str = Field(default=SourceType.GITHUB.value)
    source_version: str | None = None
    framework: str | None = None
    status: str = Field(default=ServiceStatus.PENDING.value)
    route_graph: dict | None = Field(default=None, sa_column=Column(JSON))
    error_message: str | None = None
    parse_workflow_id: str | None = None
    generate_workflow_id: str | None = None
    artifact_id: str | None = None
    metadata_json: dict | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"onupdate": utc_now},
    )

    project: Project | None = Relationship(back_populates="services")
    artifacts: list[Artifact] = Relationship(
        back_populates="service",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


# ── Artifacts ──


class Artifact(SQLModel, table=True):
    __tablename__ = "core_artifacts"

    id: str = Field(default_factory=generate_id, primary_key=True)
    service_id: str = Field(foreign_key="core_services.id", index=True)
    artifact_type: str  # ArtifactType value
    filename: str
    file_data: bytes = Field(sa_column=Column(LargeBinary))
    file_size: int = 0
    created_at: datetime = Field(default_factory=utc_now)

    service: Service | None = Relationship(back_populates="artifacts")
