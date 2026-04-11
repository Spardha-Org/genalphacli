"""Seed PyPI app into marketplace.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

import json
import secrets


revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            INSERT INTO tps_app_marketplace (
                id, app_code, app_name, display_name, auth_type, category,
                provider, meta, is_install_required, active, created_at, updated_at
            ) VALUES (
                :id, :app_code, :app_name, :display_name, :auth_type, :category,
                :provider, CAST(:meta AS json), :is_install_required, :active, NOW(), NOW()
            ) ON CONFLICT (app_name) DO NOTHING
        """),
        {
            "id": secrets.token_hex(12),
            "app_code": 20,
            "app_name": "pypi",
            "display_name": "PyPI",
            "auth_type": 2,       # AuthType.API_KEY
            "category": 3,        # AppCategory.DISTRIBUTION
            "provider": 1,        # AppProvider.NATIVE
            "meta": json.dumps({
                "icon": "https://cdn.simpleicons.org/pypi/white",
                "description": "Publish and distribute Python packages to PyPI",
                "keywords": "PyPI, Python, packages, sdist, upload",
                "form_fields": [
                    {
                        "reference_key": "api_token",
                        "type": "password",
                        "display_name": "PyPI API Token",
                        "required": True,
                        "placeholder": "pypi-...",
                    },
                ],
            }),
            "is_install_required": False,
            "active": True,
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM tps_app_marketplace WHERE app_name = 'pypi'"))
