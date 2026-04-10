"""Base protocol for app handlers (TPS pattern)."""

from __future__ import annotations

from typing import Protocol


class AppHandler(Protocol):
    """Protocol for third-party app OAuth handlers.

    Each handler implements the OAuth flow for a specific provider.
    Follows the TPS IAppInstallHandler pattern from Atomicwork.
    """

    def get_authorize_url(self, redirect_uri: str) -> tuple[str, str]:
        """Return (authorize_url, state) for the OAuth redirect.

        The state parameter must be stored by the caller for CSRF validation.
        """
        ...

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        """Exchange an authorization code for an access token.

        Returns the full config dict to be encrypted and stored.
        """
        ...

    async def refresh_token(self, config: dict) -> dict:
        """Refresh an expired token. Returns updated config dict."""
        ...

    def is_token_expired(self, config: dict) -> bool:
        """Check if the token in the config is expired."""
        ...

    async def get_user_info(self, config: dict) -> dict:
        """Fetch the authenticated user's profile from the provider."""
        ...
