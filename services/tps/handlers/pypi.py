"""PyPI handler — API key auth for package uploads."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class PyPIHandler:
    """Handler for PyPI — validates API tokens via upload endpoint probe."""

    def get_app_name(self) -> str:
        return "pypi"

    async def get_user_info(self, config: dict) -> dict:
        # PyPI has no /whoami endpoint — cannot fetch user info from token
        return {}

    async def validate_credentials(self, config: dict) -> bool:
        """Validate PyPI API token by probing the upload endpoint.

        POST to upload.pypi.org/legacy/ with auth but no file:
        - 400 = token is valid (auth passed, body validation failed as expected)
        - 403 = token is invalid or revoked
        """
        token = config.get("api_token", "")
        if not token or not token.startswith("pypi-"):
            return False

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://upload.pypi.org/legacy/",
                    auth=("__token__", token),
                    data={":action": "file_upload"},
                )
            return resp.status_code == 400  # 400 = auth passed, no file
        except httpx.HTTPError:
            logger.warning("Failed to validate PyPI token: network error")
            return False
