"""GitHub OAuth handler — implements the OAuthHandler protocol."""

from __future__ import annotations

import logging

import httpx

from services.tps.config import settings

logger = logging.getLogger(__name__)


class GithubHandler:
    """GitHub OAuth2 handler.

    GitHub tokens don't expire by default, so refresh is a no-op.
    """

    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_URL = "https://api.github.com/user"
    USER_EMAILS_URL = "https://api.github.com/user/emails"

    def get_app_name(self) -> str:
        return "github"

    def get_authorize_url(
        self, redirect_uri: str, form_data: dict | None = None
    ) -> tuple[str, str]:
        """Generate GitHub OAuth authorization URL."""
        import secrets

        state = secrets.token_urlsafe(32)
        url = (
            f"{self.AUTHORIZE_URL}"
            f"?client_id={settings.github_client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={settings.github_scopes}"
            f"&state={state}"
        )
        return url, state

    async def exchange_code(
        self, code: str, redirect_uri: str, form_data: dict | None = None
    ) -> dict:
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
        """GitHub tokens don't expire — return config as-is."""
        return config

    def is_token_expired(self, config: dict) -> bool:
        """GitHub tokens don't expire."""
        return False

    async def revoke_token(self, config: dict) -> None:
        """Best-effort token revocation at GitHub."""
        access_token = config.get("access_token")
        if not access_token or not settings.github_client_id:
            return
        try:
            async with httpx.AsyncClient() as client:
                await client.delete(
                    f"https://api.github.com/applications/{settings.github_client_id}/token",
                    auth=(settings.github_client_id, settings.github_client_secret),
                    json={"access_token": access_token},
                    headers={"Accept": "application/vnd.github+json"},
                    timeout=5.0,
                )
        except (httpx.HTTPError, httpx.TimeoutException):
            logger.warning("Failed to revoke GitHub token — continuing with local cleanup")

    async def get_user_info(self, config: dict) -> dict:
        """Fetch GitHub user profile."""
        access_token = config["access_token"]

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            user = response.json()

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
