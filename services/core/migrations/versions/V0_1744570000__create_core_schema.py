"""Create Core schema — all tables from scratch.

This migration defines the full Core schema. For existing databases
(created by SQLModel.metadata.create_all), run: alembic stamp 0001
to mark this migration as applied without running it.

Revision ID: 0001
Revises: None
Create Date: 2026-04-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Users ──
    op.create_table(
        "core_users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_core_users_email", "core_users", ["email"])

    # ── Sessions ──
    op.create_table(
        "core_sessions",
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(), nullable=False),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("session_id"),
        sa.ForeignKeyConstraint(["user_id"], ["core_users.id"]),
    )
    op.create_index("ix_core_sessions_user_id", "core_sessions", ["user_id"])

    # ── Workspaces ──
    op.create_table(
        "core_workspaces",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("integration_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.ForeignKeyConstraint(["owner_id"], ["core_users.id"]),
    )
    op.create_index("ix_core_workspaces_slug", "core_workspaces", ["slug"])

    # ── Workspace Members ──
    op.create_table(
        "core_workspace_members",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="owner"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["core_workspaces.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["core_users.id"]),
    )
    op.create_index("ix_core_workspace_members_workspace_id", "core_workspace_members", ["workspace_id"])
    op.create_index("ix_core_workspace_members_user_id", "core_workspace_members", ["user_id"])

    # ── Projects ──
    op.create_table(
        "core_projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["core_workspaces.id"]),
    )
    op.create_index("ix_core_projects_workspace_id", "core_projects", ["workspace_id"])

    # ── Services ──
    op.create_table(
        "core_services",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("repo_url", sa.String(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=False, server_default="github"),
        sa.Column("source_version", sa.String(), nullable=True),
        sa.Column("framework", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("route_graph", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("parse_workflow_id", sa.String(), nullable=True),
        sa.Column("generate_workflow_id", sa.String(), nullable=True),
        sa.Column("artifact_id", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["core_projects.id"]),
    )
    op.create_index("ix_core_services_project_id", "core_services", ["project_id"])

    # ── Artifacts ──
    op.create_table(
        "core_artifacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("service_id", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_data", sa.LargeBinary(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["service_id"], ["core_services.id"]),
    )
    op.create_index("ix_core_artifacts_service_id", "core_artifacts", ["service_id"])


def downgrade() -> None:
    op.drop_table("core_artifacts")
    op.drop_table("core_services")
    op.drop_table("core_projects")
    op.drop_table("core_workspace_members")
    op.drop_table("core_workspaces")
    op.drop_table("core_sessions")
    op.drop_table("core_users")
