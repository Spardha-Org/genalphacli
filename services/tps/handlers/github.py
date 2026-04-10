"""GitHub OAuth handler — implements the AppHandler protocol."""

from __future__ import annotations

import secrets
import logging

import httpx

from services.tps.config import settings

logger = logging.getLogger(__name__)


class GithubHandler:
    """GitHub OAuth handler.

    Implements the full OAuth web flow:
    1. Generate authorize URL with state
    2. Exchange code for access token
    3. Token refresh (GitHub tokens don't expire by default)
    4. Fetch user info
    """

    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_URL = "https://api.github.com/user"
    USER_EMAILS_URL = "https://api.github.com/user/emails"

    def get_authorize_url(self, redirect_uri: str) -> tuple[str, str]:
        """Generate GitHub OAuth authorization URL."""
        state = secrets.token_urlsafe(32)
        url = (
            f"{self.AUTHORIZE_URL}"
            f"?client_id={settings.github_client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={settings.github_scopes}"
            f"&state={state}"
        )
        return url, state

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise ValueError(
                    f"GitHub OAuth error: {data.get('error_description', data['error'])}"
                )

            return {
                "access_token": data["access_token"],
                "token_type": data.get("token_type", "bearer"),
                "scope": data.get("scope", ""),
            }

    async def refresh_token(self, config: dict) -> dict:
        """GitHub tokens don't expire by default — return config as-is."""
        return config

    def is_token_expired(self, config: dict) -> bool:
        """GitHub tokens don't expire by default."""
        return False

    async def get_user_info(self, config: dict) -> dict:
        """Fetch GitHub user profile."""
        access_token = config["access_token"]

        async with httpx.AsyncClient() as client:
            # Get user profile
            response = await client.get(
                self.USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            user = response.json()

            # Get email if not public
            email = user.get("email")
            if not email:
                email_response = await client.get(
                    self.USER_EMAILS_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github+json",
                    },
                )
                email_response.raise_for_status()
                for e in email_response.json():
                    if e.get("primary") and e.get("verified"):
                        email = e["email"]
                        break

            return {
                "id": user["id"],
                "login": user["login"],
                "name": user.get("name"),
                "email": email,
                "avatar_url": user.get("avatar_url"),
            }
