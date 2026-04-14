"""Integration service — proxies to TPS via HTTP."""

from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from services.core.oauth_state import encode_state, decode_state, OAuthState
from services.core.clients.tps_client import TpsHttpClient
from services.core.config import settings
from services.core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class IntegrationService:
    def __init__(self, tps: TpsHttpClient):
        self._tps = tps

    # ── Apps ──

    async def list_apps(self) -> list[dict]:
        return await self._tps.list_apps()

    async def get_app(self, identifier: str) -> dict:
        app = await self._tps.get_app(identifier)
        if not app:
            raise NotFoundError("App not found")
        return app

    # ── Integrations ──

    async def list_integrations(self, user_id: str) -> list[dict]:
        return await self._tps.list_integrations(user_id)

    async def get_integration(self, user_id: str, identifier: str) -> dict:
        integration = await self._tps.get_integration(user_id, identifier)
        if not integration:
            raise NotFoundError("Integration not found")
        return integration

    async def delete_integration(self, user_id: str, integration_id: str) -> None:
        deleted = await self._tps.delete_integration(user_id, integration_id)
        if not deleted:
            raise NotFoundError("Integration not found")

    # ── OAuth Install ──

    async def start_install(
        self, user_id: str, app_name: str, callback_path: str = "/app-store",
        form_data: dict | None = None,
    ) -> str:
        """Build OAuth authorize URL with encrypted state."""
        state = encode_state(OAuthState(
            user_id=user_id, app_name=app_name,
            timestamp=__import__("time").time(), callback_path=callback_path,
        ))
        redirect_uri = f"{settings.app_url}/api/oauth/callback"

        result = await self._tps.install_app(user_id, app_name, state, redirect_uri)
        authorize_url = result.get("authorize_url", "")

        # Replace TPS-generated state with our encrypted state
        authorize_url = _replace_state_param(authorize_url, state)
        return authorize_url

    async def handle_oauth_callback(self, code: str, state: str) -> tuple[str, str]:
        """Exchange OAuth code. Returns (app_name, callback_path)."""
        try:
            state_data = decode_state(state)
        except ValueError:
            raise ValidationError("Invalid or expired OAuth state")

        user_id = state_data.user_id
        app_name = state_data.app_name
        callback_path = state_data.callback_path or "/app-store"

        redirect_uri = f"{settings.app_url}/api/oauth/callback"
        await self._tps.exchange_code(user_id, app_name, code, redirect_uri)

        return app_name, callback_path

    # ── Credential Connect ──

    async def connect_credentials(
        self, user_id: str, app_name: str, credentials: dict
    ) -> dict:
        return await self._tps.connect_credentials(user_id, app_name, credentials)


def _replace_state_param(url: str, new_state: str) -> str:
    """Replace the state parameter in a URL using proper URL parsing."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params["state"] = [new_state]
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))
