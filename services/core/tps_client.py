"""HTTP client for calling the TPS service."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import HTTPException

from services.core.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def get_tps_client() -> httpx.AsyncClient:
    """Get or create the shared TPS HTTP client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.tps_url,
            timeout=httpx.Timeout(settings.tps_timeout, connect=5.0),
            headers={"X-TPS-Secret": settings.tps_secret},
        )
    return _client


async def tps_request(
    method: str,
    path: str,
    workspace_id: str,
    **kwargs: Any,
) -> dict:
    """Make an authenticated request to TPS.

    Adds workspace_id header and TPS secret automatically.
    Converts TPS errors to 502 for the caller.
    """
    client = get_tps_client()

    try:
        response = await client.request(
            method,
            path,
            headers={"X-Workspace-ID": workspace_id},
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    except httpx.TimeoutException:
        logger.error("TPS timeout: %s %s", method, path)
        raise HTTPException(status_code=502, detail="Integration service timed out")

    except httpx.ConnectError:
        logger.error("TPS unreachable: %s %s", method, path)
        raise HTTPException(status_code=502, detail="Integration service unavailable")

    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        logger.error("TPS error %d: %s %s", status, method, path)

        # Map TPS errors to user-friendly messages
        if status == 401:
            raise HTTPException(status_code=502, detail="Integration token expired. Please reconnect.")
        elif status == 404:
            raise HTTPException(status_code=404, detail="Integration not found")
        elif status == 429:
            raise HTTPException(status_code=429, detail="Rate limit reached. Try again later.")
        else:
            raise HTTPException(status_code=502, detail=f"Integration service error ({status})")
