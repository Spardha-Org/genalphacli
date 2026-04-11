"""Base protocols for app handlers — split by auth type."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AppHandler(Protocol):
    """Base protocol — all handlers implement these."""

    def get_app_name(self) -> str:
        """Return the app slug (e.g., 'github')."""
        ...

    async def get_user_info(self, config: dict) -> dict:
        """Fetch the authenticated user's profile. Returns {} if not applicable."""
        ...


@runtime_checkable
class OAuthHandler(AppHandler, Protocol):
    """Protocol for OAuth2 and Form-based OAuth2 apps.

    These apps use a browser redirect flow:
    install → redirect → callback → exchange → store tokens
    """

    def get_authorize_url(
        self, redirect_uri: str, form_data: dict | None = None
    ) -> tuple[str, str]:
        """Return (authorize_url, state) for the OAuth redirect.

        form_data is provided for Form-based OAuth2 apps (e.g., tenant URL).
        """
        ...

    async def exchange_code(
        self, code: str, redirect_uri: str, form_data: dict | None = None
    ) -> dict:
        """Exchange an authorization code for tokens. Returns config dict to encrypt."""
        ...

    async def refresh_token(self, config: dict) -> dict:
        """Refresh an expired token. Returns updated config dict."""
        ...

    def is_token_expired(self, config: dict) -> bool:
        """Check if the token in the config is expired."""
        ...

    async def revoke_token(self, config: dict) -> None:
        """Revoke the token at the provider. Best-effort, never raises."""
        ...


@runtime_checkable
class CredentialHandler(AppHandler, Protocol):
    """Protocol for API Key, Basic Auth, and mTLS apps.

    These apps use a form submission flow:
    connect → validate → store credentials
    """

    async def validate_credentials(self, config: dict) -> bool:
        """Test if the provided credentials work. Returns True if valid."""
        ...
