"""Core service database models (SQLModel)."""

import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Column, LargeBinary
from sqlmodel import Field, Relationship, SQLModel


def generate_cuid() -> str:
    return secrets.token_hex(12)


def utc_now() -> datetime:
    return datetime.utcnow()


# ── Users ──


class User(SQLModel, table=True):
    __tablename__ = "core_users"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: Optional[str] = None
    email_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)

    sessions: list["Session"] = Relationship(back_populates="user")
    memberships: list["WorkspaceMember"] = Relationship(back_populates="user")


# ── Sessions ──


class Session(SQLModel, table=True):
    __tablename__ = "core_sessions"

    session_id: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32), primary_key=True
    )
    user_id: str = Field(foreign_key="core_users.id", index=True)
    expires_at: datetime
    last_active_at: datetime = Field(default_factory=utc_now)
    user_agent: Optional[str] = None

    user: Optional["User"] = Relationship(back_populates="sessions")


# ── Workspaces ──


class Workspace(SQLModel, table=True):
    __tablename__ = "core_workspaces"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    name: str
    slug: str = Field(unique=True, index=True)
    owner_id: str = Field(foreign_key="core_users.id")
    integration_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)

    members: list["WorkspaceMember"] = Relationship(back_populates="workspace")
    projects: list["Project"] = Relationship(back_populates="workspace")


# ── Workspace Members ──


class WorkspaceMember(SQLModel, table=True):
    __tablename__ = "core_workspace_members"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    workspace_id: str = Field(foreign_key="core_workspaces.id", index=True)
    user_id: str = Field(foreign_key="core_users.id", index=True)
    role: str = Field(default="owner")
    created_at: datetime = Field(default_factory=utc_now)

    workspace: Optional["Workspace"] = Relationship(back_populates="members")
    user: Optional["User"] = Relationship(back_populates="memberships")


# ── Projects ──


class Project(SQLModel, table=True):
    __tablename__ = "core_projects"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    workspace_id: str = Field(foreign_key="core_workspaces.id", index=True)
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)

    workspace: Optional["Workspace"] = Relationship(back_populates="projects")
    services: list["Service"] = Relationship(back_populates="project")


# ── Services ──


class Service(SQLModel, table=True):
    __tablename__ = "core_services"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    project_id: str = Field(foreign_key="core_projects.id", index=True)
    name: str
    repo_url: Optional[str] = None
    source_type: str = Field(default="github")  # "github" | "pypi"
    source_version: Optional[str] = None  # PyPI version parsed
    framework: Optional[str] = None
    status: str = Field(default="pending")
    route_graph: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    error_message: Optional[str] = None
    parse_workflow_id: Optional[str] = None
    generate_workflow_id: Optional[str] = None
    artifact_id: Optional[str] = None
    metadata_json: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    project: Optional["Project"] = Relationship(back_populates="services")


# ── Artifacts ──


class Artifact(SQLModel, table=True):
    __tablename__ = "core_artifacts"

    id: str = Field(default_factory=generate_cuid, primary_key=True)
    service_id: str = Field(foreign_key="core_services.id", index=True)
    artifact_type: str  # "cli" or "mcp"
    filename: str
    file_data: bytes = Field(sa_column=Column(LargeBinary))
    file_size: int = 0
    created_at: datetime = Field(default_factory=utc_now)
