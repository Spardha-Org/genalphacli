"""Integration service — CRUD + token lifecycle management."""

from __future__ import annotations

import logging

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.tps.crypto import decrypt_config, encrypt_config
from services.tps.handlers import get_handler
from services.tps.models import Integration, utc_now

logger = logging.getLogger(__name__)


async def get_or_refresh(
    db: AsyncSession,
    integration_id: str,
    workspace_id: str,
) -> dict:
    """Get an integration's decrypted config, refreshing the token if expired.

    This is the TPS equivalent of ClientConfigResolver.getOrRefresh().
    """
    stmt = select(Integration).where(
        Integration.id == integration_id,
        Integration.workspace_id == workspace_id,
        Integration.status == "active",
    )
    result = await db.exec(stmt)
    integration = result.first()

    if not integration:
        raise ValueError(f"Integration {integration_id} not found for workspace {workspace_id}")

    config = decrypt_config(integration.config_encrypted)
    handler = get_handler(integration.app_name)

    if handler.is_token_expired(config):
        logger.info("Token expired for integration %s, refreshing", integration_id)
        config = await handler.refresh_token(config)
        integration.config_encrypted = encrypt_config(config)
        integration.updated_at = utc_now()
        db.add(integration)
        await db.commit()

    return config


async def create_integration(
    db: AsyncSession,
    workspace_id: str,
    app_name: str,
    config: dict,
    github_username: str | None = None,
) -> Integration:
    """Create a new integration with encrypted config."""
    # Check for existing integration for this workspace + app
    stmt = select(Integration).where(
        Integration.workspace_id == workspace_id,
        Integration.app_name == app_name,
        Integration.status == "active",
    )
    result = await db.exec(stmt)
    existing = result.first()

    if existing:
        # Update existing integration
        existing.config_encrypted = encrypt_config(config)
        existing.github_username = github_username
        existing.updated_at = utc_now()
        existing.status = "active"
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        return existing

    # Create new
    integration = Integration(
        workspace_id=workspace_id,
        app_name=app_name,
        config_encrypted=encrypt_config(config),
        github_username=github_username,
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
    """Delete (revoke) an integration."""
    stmt = select(Integration).where(
        Integration.id == integration_id,
        Integration.workspace_id == workspace_id,
    )
    result = await db.exec(stmt)
    integration = result.first()

    if not integration:
        return False

    integration.status = "revoked"
    integration.config_encrypted = encrypt_config({})  # Clear tokens
    integration.updated_at = utc_now()
    db.add(integration)
    await db.commit()
    return True
