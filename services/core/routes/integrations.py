"""Integration routes — proxy to TPS service."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from services.core.deps import CurrentWorkspaceDep
from services.core.tps_client import tps_request
from services.core.config import settings

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/apps")
async def list_apps(workspace: CurrentWorkspaceDep):
    """List available apps from TPS marketplace."""
    return await tps_request("GET", "/apps", workspace_id=workspace.id)


@router.get("")
async def list_integrations(workspace: CurrentWorkspaceDep):
    """List connected integrations for this workspace."""
    return await tps_request("GET", "/integrations", workspace_id=workspace.id)


@router.post("/{app_name}/install")
async def install_app(app_name: str, workspace: CurrentWorkspaceDep):
    """Start OAuth flow for an app."""
    return await tps_request("POST", f"/integrations/{app_name}/install", workspace_id=workspace.id)


@router.get("/{app_name}/callback")
async def oauth_callback(app_name: str, request: Request):
    """Handle OAuth callback from GitHub.

    This is a browser redirect — no session cookie available.
    We forward to TPS which validates via the stored OAuth state (DB-backed).
    Then redirect the user back to the integrations settings page.
    """
    code = request.query_params.get("code", "")
    state = request.query_params.get("state", "")

    # Call TPS directly — no workspace_id header needed,
    # TPS gets it from the stored OAuth state
    tps_url = settings.tps_url
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{tps_url}/integrations/{app_name}/callback",
                params={"code": code, "state": state},
                headers={"X-TPS-Secret": settings.tps_secret},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # Redirect to settings with error
        return RedirectResponse(
            url=f"{settings.app_url}/settings/integrations?error=oauth_failed",
            status_code=302,
        )
    except Exception:
        return RedirectResponse(
            url=f"{settings.app_url}/settings/integrations?error=service_unavailable",
            status_code=302,
        )

    # Success — redirect to integrations page
    return RedirectResponse(
        url=f"{settings.app_url}/settings/integrations?connected={app_name}",
        status_code=302,
    )


@router.delete("/{integration_id}")
async def delete_integration(integration_id: str, workspace: CurrentWorkspaceDep):
    """Disconnect an integration."""
    return await tps_request("DELETE", f"/integrations/{integration_id}", workspace_id=workspace.id)
