"""TPS HTTP client — true microservice boundary.

Core communicates with TPS exclusively via HTTP.
No direct DB access, no shared models, no import coupling.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class TpsHttpClient:
    """Async HTTP client for the TPS (Third-Party Service)."""

    def __init__(self, base_url: str, secret: str, timeout: float = 10.0):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self._secret = secret

    # ── Apps ──

    async def list_apps(self, category: str | None = None) -> list[dict]:
        params = {"category": category} if category else None
        resp = await self._get("/apps", params=params)
        return resp.json()

    async def get_app(self, app_name: str) -> dict | None:
        resp = await self._get(f"/apps/{app_name}", raise_on_404=False)
        if resp.status_code == 404:
            return None
        return resp.json()

    # ── Integrations ──

    async def list_integrations(self, user_id: str) -> list[dict]:
        resp = await self._get("/integrations", user_id=user_id)
        return resp.json()

    async def get_integration(self, user_id: str, identifier: str) -> dict | None:
        resp = await self._get(f"/integrations/{identifier}", user_id=user_id, raise_on_404=False)
        if resp.status_code == 404:
            return None
        return resp.json()

    async def get_token(self, user_id: str, integration_id: str) -> dict | None:
        resp = await self._get(f"/integrations/{integration_id}/token", user_id=user_id, raise_on_404=False)
        if resp.status_code in (404, 400):
            return None
        return resp.json()

    async def delete_integration(self, user_id: str, integration_id: str) -> bool:
        resp = await self._request("DELETE", f"/integrations/{integration_id}", user_id=user_id)
        return resp.status_code == 200

    # ── OAuth Flow ──

    async def install_app(self, user_id: str, app_name: str, state: str, redirect_uri: str) -> dict:
        resp = await self._request(
            "POST", f"/integrations/{app_name}/install",
            user_id=user_id,
            json={"state": state, "redirect_uri": redirect_uri},
        )
        return resp.json()

    async def exchange_code(self, user_id: str, app_name: str, code: str, redirect_uri: str) -> dict:
        resp = await self._request(
            "POST", f"/integrations/{app_name}/exchange",
            user_id=user_id,
            json={"code": code, "redirect_uri": redirect_uri},
        )
        return resp.json()

    # ── Credential Flow ──

    async def connect_credentials(self, user_id: str, app_name: str, credentials: dict) -> dict:
        resp = await self._request(
            "POST", f"/integrations/{app_name}/connect",
            user_id=user_id,
            json={"credentials": credentials},
        )
        return resp.json()

    # ── Internal ──

    async def _get(self, path: str, user_id: str | None = None,
                   params: dict | None = None, raise_on_404: bool = True) -> httpx.Response:
        return await self._request("GET", path, user_id=user_id, params=params, raise_on_404=raise_on_404)

    async def _request(self, method: str, path: str, user_id: str | None = None,
                       raise_on_404: bool = True, **kwargs) -> httpx.Response:
        headers = kwargs.pop("headers", {})
        headers["X-TPS-Secret"] = self._secret
        if user_id:
            headers["X-User-ID"] = user_id

        resp = await self._client.request(method, path, headers=headers, **kwargs)

        if not raise_on_404 and resp.status_code == 404:
            return resp
        if resp.status_code >= 400 and resp.status_code != 404:
            logger.warning("TPS %s %s → %d: %s", method, path, resp.status_code, resp.text[:200])
        if resp.status_code >= 500:
            resp.raise_for_status()

        return resp

    async def close(self):
        await self._client.aclose()
