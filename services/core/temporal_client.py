"""Temporal client for starting workflows from Core service."""

from __future__ import annotations

import logging
from temporalio.client import Client

from services.core.config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None


async def get_temporal_client() -> Client:
    """Get or create the shared Temporal client."""
    global _client
    if _client is None:
        _client = await Client.connect(settings.temporal_address)
        logger.info("Connected to Temporal at %s", settings.temporal_address)
    return _client
