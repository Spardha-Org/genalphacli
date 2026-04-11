"""npm credential handler."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class NpmHandler:
    """API key handler for npm."""

    def get_app_name(self) -> str:
        return "npm"

    async def get_user_info(self, config: dict) -> dict:
        """Fetch username from npm whoami endpoint."""
        token = config.get("access_token", "")
        if not token:
            return {}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://registry.npmjs.org/-/whoami",
                    headers={"Authorization": f"Bearer {token}"},
                )
            if not resp.is_success:
                return {}
            data = resp.json()
            return {"login": data.get("username")}
        except httpx.HTTPError:
            logger.warning("Failed to fetch npm user info")
            return {}

    async def validate_credentials(self, config: dict) -> bool:
        """Validate npm token by calling the whoami endpoint.

        GET https://registry.npmjs.org/-/whoami with Bearer token:
        - 200 {"username": "..."} = valid
        - 401 = invalid or revoked
        """
        token = config.get("access_token", "")
        if not token or not token.startswith("npm_"):
            return False

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://registry.npmjs.org/-/whoami",
                    headers={"Authorization": f"Bearer {token}"},
                )
            return resp.is_success
        except httpx.HTTPError:
            logger.warning("Failed to validate npm token: network error")
            return False
