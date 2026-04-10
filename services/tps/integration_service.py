"""Integration service — CRUD + token lifecycle management."""

from __future__ import annotations

import logging
import time

import sqlalchemy as sa
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.tps.crypto import decrypt_config, encrypt_config
from services.tps.handlers import get_handler
from services.tps.handlers.base import OAuthHandler
from services.tps.models import AppMarketplace, Integration, OAuthState, utc_now

logger = logging.getLogger(__name__)

REFRESH_BUFFER_SECONDS = 120  # refresh 2 minutes before actual expiry


async def get_or_refresh(
    db: AsyncSession,
    integration_id: str,
    workspace_id: str,
) -> dict:
    """Get an integration's decrypted config, refreshing the token if expired.

    Uses SELECT FOR UPDATE to prevent concurrent refresh race conditions.
    """
    # Lock the row to prevent concurrent refresh
    stmt = (
        select(Integration)
        .where(
            Integration.id == integration_id,
            Integration.workspace_id == workspace_id,
            Integration.status == "active",
        )
        .with_for_update()
    )
    result = await db.exec(stmt)
    integration = result.first()

    if not integration:
        raise ValueError(f"Integration {integration_id} not found for workspace {workspace_id}")

    config = decrypt_config(integration.config_encrypted)
    handler = get_handler(integration.app_name)

    # Check expiry — use plaintext expires_at column for fast check
    needs_refresh = False
    if isinstance(handler, OAuthHandler):
        if integration.expires_at and time.time() >= (integration.expires_at - REFRESH_BUFFER_SECONDS):
            needs_refresh = True
        elif handler.is_token_expired(config):
            needs_refresh = True

    if needs_refresh:
        logger.info("Token expired for integration %s, refreshing", integration_id)
        config = await handler.refresh_token(config)
        integration.config_encrypted = encrypt_config(config)
        integration.expires_at = config.get("expires_at")
        integration.updated_at = utc_now()
        db.add(integration)
        await db.commit()

    return config


async def create_integration(
    db: AsyncSession,
    workspace_id: str,
    app_name: str,
    config: dict,
    identifier: str | None = None,
    expires_at: float | None = None,
) -> Integration:
    """Create or update an integration with encrypted config.

    Upserts: if an active integration exists for workspace+app, updates it.
    """
    # Look up the app to get app_id
    app_result = await db.exec(
        select(AppMarketplace).where(AppMarketplace.app_name == app_name)
    )
    app = app_result.first()
    if not app:
        raise ValueError(f"App '{app_name}' not found in marketplace")

    # Check for existing active integration
    stmt = select(Integration).where(
        Integration.workspace_id == workspace_id,
        Integration.app_name == app_name,
        Integration.status == "active",
    )
    result = await db.exec(stmt)
    existing = result.first()

    if existing:
        existing.config_encrypted = encrypt_config(config)
        existing.identifier = identifier
        existing.expires_at = expires_at
        existing.updated_at = utc_now()
        existing.status = "active"
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        return existing

    integration = Integration(
        workspace_id=workspace_id,
        app_id=app.id,
        app_name=app_name,
        config_encrypted=encrypt_config(config),
        identifier=identifier,
        expires_at=expires_at,
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return integration


async def delete_integration(
    db: AsyncSession,
    integration_id: str,
    workspace_id: str,
) -> bool:
    """Revoke an integration — wipes credentials, calls provider revocation."""
    stmt = select(Integration).where(
        Integration.id == integration_id,
        Integration.workspace_id == workspace_id,
    )
    result = await db.exec(stmt)
    integration = result.first()

    if not integration:
        return False

    # Best-effort token revocation at the provider
    try:
        handler = get_handler(integration.app_name)
        if isinstance(handler, OAuthHandler):
            config = decrypt_config(integration.config_encrypted)
            await handler.revoke_token(config)
    except Exception as e:
        logger.warning("Token revocation failed for %s: %s", integration.app_name, e)

    integration.status = "revoked"
    integration.config_encrypted = encrypt_config({})
    integration.expires_at = None
    integration.updated_at = utc_now()
    db.add(integration)
    await db.commit()
    return True


async def cleanup_expired_states(db: AsyncSession) -> int:
    """Delete OAuth states older than their expiry. Returns count deleted."""
    now = utc_now()
    stmt = select(OAuthState).where(OAuthState.expires_at < now)
    result = await db.exec(stmt)
    expired = result.all()
    for s in expired:
        await db.delete(s)
    if expired:
        await db.commit()
    return len(expired)
