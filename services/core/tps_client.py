"""TPS SDK — direct function calls to TPS service layer.

Core imports this module to interact with TPS. No HTTP overhead.
If TPS is extracted to a separate repo later, this module becomes
an HTTP client while keeping the same interface.

Usage:
    from services.core.tps_client import tps
    apps = await tps.list_apps(db)
    integration = await tps.create_integration(db, user_id, "github", config)
"""

from __future__ import annotations

import logging
from typing import Any

from sqlmodel.ext.asyncio.session import AsyncSession

from services.tps.integration_service import (
    create_integration as _create_integration,
    delete_integration as _delete_integration,
    get_or_refresh as _get_or_refresh,
)
from services.tps.models import (
    AppMarketplace,
    AuthType,
    AppCategory,
    AppProvider,
    Integration,
)
from services.tps.handlers import get_oauth_handler, get_credential_handler
from services.tps.crypto import decrypt_config

from sqlmodel import select

logger = logging.getLogger(__name__)


class TpsClient:
    """SDK interface to TPS service — direct function calls, no HTTP.

    All methods accept an AsyncSession (from Core's DB or TPS's DB).
    When TPS has its own DB, Core must pass a TPS DB session.
    """

    # ── Apps ──

    async def list_apps(
        self, db: AsyncSession, category: int | None = None
    ) -> list[dict]:
        """List all active apps in the marketplace."""
        stmt = select(AppMarketplace).where(AppMarketplace.active == True)  # noqa: E712
        if category is not None:
            stmt = stmt.where(AppMarketplace.category == category)
        result = await db.exec(stmt)
        return [self._serialize_app(app) for app in result.all()]

    async def get_app(self, db: AsyncSession, identifier: str) -> dict | None:
        """Get app by app_name or app_code."""
        if identifier.isdigit():
            stmt = select(AppMarketplace).where(AppMarketplace.app_code == int(identifier))
        else:
            stmt = select(AppMarketplace).where(AppMarketplace.app_name == identifier)
        result = await db.exec(stmt)
        app = result.first()
        return self._serialize_app(app) if app else None

    # ── Integrations ──

    async def list_integrations(self, db: AsyncSession, user_id: str) -> list[dict]:
        """List all active integrations for a user."""
        stmt = select(Integration).where(
            Integration.user_id == user_id,
            Integration.status == "active",
        )
        result = await db.exec(stmt)
        return [self._serialize_integration(i) for i in result.all()]

    async def get_integration(
        self, db: AsyncSession, user_id: str, identifier: str
    ) -> dict | None:
        """Get integration by app_name or integration_id."""
        # Try app_name first
        stmt = select(Integration).where(
            Integration.user_id == user_id,
            Integration.app_name == identifier,
            Integration.status == "active",
        )
        result = await db.exec(stmt)
        integration = result.first()

        # Fallback to integration_id
        if not integration:
            stmt = select(Integration).where(
                Integration.id == identifier,
                Integration.user_id == user_id,
                Integration.status == "active",
            )
            result = await db.exec(stmt)
            integration = result.first()

        return self._serialize_integration(integration) if integration else None

    async def create_integration(
        self,
        db: AsyncSession,
        user_id: str,
        app_name: str,
        config: dict,
        identifier: str | None = None,
        expires_at: float | None = None,
    ) -> dict:
        """Create or update an integration."""
        integration = await _create_integration(
            db, user_id=user_id, app_name=app_name,
            config=config, identifier=identifier, expires_at=expires_at,
        )
        return self._serialize_integration(integration)

    async def delete_integration(
        self, db: AsyncSession, integration_id: str, user_id: str
    ) -> bool:
        """Disconnect an integration."""
        return await _delete_integration(db, integration_id, user_id)

    async def get_or_refresh(
        self, db: AsyncSession, integration_id: str, user_id: str
    ) -> dict:
        """Get decrypted config, auto-refreshing if expired."""
        return await _get_or_refresh(db, integration_id, user_id)

    # ── OAuth ──

    async def build_oauth_url(
        self, db: AsyncSession, app_name: str,
        state: str, redirect_uri: str, form_data: dict | None = None,
    ) -> dict:
        """Build OAuth authorize URL. Core owns state — TPS is stateless."""
        # Validate app exists
        app = await self.get_app(db, app_name)
        if not app:
            raise ValueError(f"App '{app_name}' not found")
        if not app["is_install_required"]:
            raise ValueError(f"App '{app_name}' uses credential flow, not OAuth")

        handler = get_oauth_handler(app_name)
        authorize_url, _ = handler.get_authorize_url(redirect_uri, form_data)
        # Replace handler-generated state with Core's encrypted state
        authorize_url = authorize_url.replace(
            authorize_url.split("state=")[1].split("&")[0], state
        )
        return {"authorize_url": authorize_url}

    async def exchange_oauth_code(
        self, db: AsyncSession, user_id: str, app_name: str,
        code: str, redirect_uri: str,
    ) -> dict:
        """Exchange OAuth code for token, store integration. No state validation — Core owns it."""
        handler = get_oauth_handler(app_name)
        config = await handler.exchange_code(code, redirect_uri)

        try:
            user_info = await handler.get_user_info(config)
        except Exception:
            user_info = {}

        identifier = user_info.get("login") or user_info.get("email")
        expires_at = config.get("expires_at")

        integration = await _create_integration(
            db, user_id=user_id, app_name=app_name,
            config=config, identifier=identifier, expires_at=expires_at,
        )

        return {
            "integration_id": integration.id,
            "app_name": app_name,
            "identifier": identifier,
            "status": "active",
        }

    async def connect_credentials(
        self, db: AsyncSession, user_id: str, app_name: str, credentials: dict,
    ) -> dict:
        """Store credentials for a non-OAuth app."""
        # Validate required fields from app meta
        app_result = await db.exec(
            select(AppMarketplace).where(AppMarketplace.app_name == app_name)
        )
        app = app_result.first()
        if not app:
            raise ValueError(f"App '{app_name}' not found")

        form_fields = (app.meta or {}).get("form_fields", [])
        for field in form_fields:
            if field.get("required") and field["reference_key"] not in credentials:
                raise ValueError(f"Missing required field: {field['display_name']}")

        # Optional handler validation
        try:
            handler = get_credential_handler(app_name)
            if not await handler.validate_credentials(credentials):
                raise ValueError("Credentials are invalid")
        except ValueError as e:
            if "No handler" in str(e):
                pass  # No handler — store without validation
            else:
                raise

        identifier = credentials.get("email") or credentials.get("username")
        integration = await _create_integration(
            db, user_id=user_id, app_name=app_name,
            config=credentials, identifier=identifier,
        )

        return {
            "integration_id": integration.id,
            "app_name": app_name,
            "identifier": integration.identifier,
            "status": "active",
        }

    # ── Serializers ──

    @staticmethod
    def _serialize_app(app: AppMarketplace) -> dict:
        return {
            "id": app.id,
            "app_code": app.app_code,
            "app_name": app.app_name,
            "display_name": app.display_name,
            "auth_type": AuthType(app.auth_type).label,
            "category": AppCategory(app.category).label,
            "provider": AppProvider(app.provider).label,
            "meta": app.meta,
            "is_install_required": app.is_install_required,
        }

    @staticmethod
    def _serialize_integration(i: Integration) -> dict:
        return {
            "id": i.id,
            "app_name": i.app_name,
            "identifier": i.identifier,
            "status": i.status,
            "created_at": i.created_at.isoformat(),
        }


# Singleton — import and use: `from services.core.tps_client import tps`
tps = TpsClient()
