"""Seed GitHub app into marketplace.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

import json
import secrets


revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            INSERT INTO tps_app_marketplace (
                id, app_code, app_name, display_name, auth_type, category,
                provider, meta, authorize_url, token_url, scopes,
                is_install_required, active, created_at, updated_at
            ) VALUES (
                :id, :app_code, :app_name, :display_name, :auth_type, :category,
                :provider, CAST(:meta AS json), :authorize_url, :token_url, :scopes,
                :is_install_required, :active, NOW(), NOW()
            ) ON CONFLICT (app_name) DO NOTHING
        """),
        {
            "id": secrets.token_hex(12),
            "app_code": 1,
            "app_name": "github",
            "display_name": "GitHub",
            "auth_type": 1,       # AuthType.OAUTH2
            "category": 1,        # AppCategory.SOURCE_CONTROL
            "provider": 1,        # AppProvider.NATIVE
            "meta": json.dumps({
                "icon": "https://cdn.simpleicons.org/github/white",
                "description": "Connect your GitHub repositories for parsing",
            }),
            "authorize_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "scopes": "read:user user:email repo",
            "is_install_required": True,
            "active": True,
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM tps_app_marketplace WHERE app_name = 'github'"))
