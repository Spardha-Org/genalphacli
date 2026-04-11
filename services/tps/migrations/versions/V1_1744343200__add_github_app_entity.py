"""seed GitHub app

Revision ID: 984827bf34bf
Revises: 9368bcc484ad
Create Date: 2026-04-11 03:07:03.575407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '984827bf34bf'
down_revision: Union[str, Sequence[str], None] = '9368bcc484ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


import json
import secrets


def upgrade() -> None:
    """Seed GitHub as the first app in the marketplace."""
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            INSERT INTO tps_app_marketplace (
                id, app_code, app_name, display_name, auth_type, category,
                provider, meta, authorize_url, token_url, scopes,
                is_install_required, active, created_at, updated_at
            ) VALUES (
                :id, :app_code, :app_name, :display_name, :auth_type, :category,
                :provider, :meta, :authorize_url, :token_url, :scopes,
                :is_install_required, :active, NOW(), NOW()
            ) ON CONFLICT (app_name) DO NOTHING
        """),
        {
            "id": secrets.token_hex(12),
            "app_code": 1,
            "app_name": "github",
            "display_name": "GitHub",
            "auth_type": "oauth2",
            "category": "source_control",
            "provider": "native",
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
    """Remove GitHub seed."""
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM tps_app_marketplace WHERE app_name = 'github'"))
