"""Create TPS schema — all tables from scratch.

Revision ID: 0001
Revises: None
Create Date: 2026-04-11
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
    op.create_table(
        "tps_app_marketplace",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("app_code", sa.Integer(), nullable=False),
        sa.Column("app_name", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("auth_type", sa.Integer(), nullable=False),
        sa.Column("category", sa.Integer(), nullable=False),
        sa.Column("provider", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("is_install_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("app_code"),
        sa.UniqueConstraint("app_name"),
    )
    op.create_index("ix_tps_app_marketplace_app_name", "tps_app_marketplace", ["app_name"])

    op.create_table(
        "tps_integrations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("app_id", sa.String(), nullable=False),
        sa.Column("app_name", sa.String(), nullable=False),
        sa.Column("config_encrypted", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("identifier", sa.String(), nullable=True),
        sa.Column("expires_at", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["app_id"], ["tps_app_marketplace.id"]),
    )
    op.create_index("ix_tps_integrations_user_id", "tps_integrations", ["user_id"])
    op.create_index("ix_tps_integrations_app_id", "tps_integrations", ["app_id"])
    op.create_index("ix_tps_integrations_app_name", "tps_integrations", ["app_name"])


def downgrade() -> None:
    op.drop_table("tps_integrations")
    op.drop_table("tps_app_marketplace")
