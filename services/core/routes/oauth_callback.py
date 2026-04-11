"""Public OAuth callback endpoint — handles provider redirects.

This is the redirect_uri registered with OAuth providers. It:
1. Receives code + encrypted state from the provider
2. Decrypts state to recover user/app context
3. Calls TPS to exchange code for token
4. Redirects browser to the frontend callback_path

No session cookie required — context is in the encrypted state.
Pattern copied from: Atomicwork ESD ExternalOAuthController + ExternalOauthApiFilter
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from services.core.config import settings
from services.core.deps import DbDep
from services.core.oauth_state import decode_state
from services.core.tps_client import tps

logger = logging.getLogger(__name__)
router = APIRouter(tags=["oauth"])


@router.get("/oauth/callback")
async def oauth_callback(
    db: DbDep,
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = Query(None),
):
    """Public OAuth callback — provider redirects here after user authorizes.

    No auth required. Context is recovered from the encrypted state blob.
    """
    # Handle provider-side errors (e.g., user denied access)
    if error:
        logger.warning("OAuth provider returned error: %s", error)
        return RedirectResponse(
            url=f"{settings.app_url}/integrations?error=oauth_denied",
            status_code=302,
        )

    # Decrypt state to recover context
    try:
        oauth_state = decode_state(state)
    except ValueError as e:
        logger.error("OAuth state decode failed: %s", e)
        return RedirectResponse(
            url=f"{settings.app_url}/integrations?error=invalid_state",
            status_code=302,
        )

    # Exchange code for token via TPS SDK
    redirect_uri = f"{settings.app_url}/api/oauth/callback"
    try:
        result = await tps.exchange_oauth_code(
            db,
            user_id=oauth_state.user_id,
            app_name=oauth_state.app_name,
            code=code,
            redirect_uri=redirect_uri,
        )
        logger.info(
            "OAuth exchange successful for %s (user: %s)",
            oauth_state.app_name, oauth_state.user_id,
        )
    except Exception as e:
        logger.error("OAuth exchange failed for %s: %s", oauth_state.app_name, e)
        return RedirectResponse(
            url=f"{settings.app_url}{oauth_state.callback_path}?error=oauth_failed",
            status_code=302,
        )

    # Redirect browser to frontend
    return RedirectResponse(
        url=f"{settings.app_url}{oauth_state.callback_path}?connected={oauth_state.app_name}",
        status_code=302,
    )
