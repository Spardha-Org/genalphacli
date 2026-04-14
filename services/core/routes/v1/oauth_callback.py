"""OAuth callback — browser redirect target after provider authorization."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from services.core.config import settings
from services.core.deps import IntegrationServiceDep

logger = logging.getLogger(__name__)

router = APIRouter(tags=["oauth"])


@router.get("/oauth/callback")
async def oauth_callback(code: str, state: str, integration_service: IntegrationServiceDep):
    """Handle OAuth provider redirect. Exchanges code for token via TPS."""
    try:
        app_name, callback_path = await integration_service.handle_oauth_callback(code, state)

        # Validate callback_path to prevent open redirects
        if not callback_path.startswith("/"):
            callback_path = "/app-store"

        return RedirectResponse(
            url=f"{settings.app_url}{callback_path}?connected={app_name}",
            status_code=302,
        )
    except Exception as e:
        logger.error("OAuth callback failed: %s", e)
        return RedirectResponse(
            url=f"{settings.app_url}/app-store?error=oauth_failed",
            status_code=302,
        )
