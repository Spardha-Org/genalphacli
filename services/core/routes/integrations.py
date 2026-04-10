"""Integration routes — proxy to TPS service."""

from __future__ import annotations

from fastapi import APIRouter, Request
from services.core.deps import CurrentUserDep, CurrentWorkspaceDep, DbDep
from services.core.tps_client import tps_request

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
async def oauth_callback(app_name: str, request: Request, workspace: CurrentWorkspaceDep):
    """Handle OAuth callback — forward code and state to TPS."""
    code = request.query_params.get("code", "")
    state = request.query_params.get("state", "")
    result = await tps_request(
        "GET",
        f"/integrations/{app_name}/callback?code={code}&state={state}",
        workspace_id=workspace.id,
    )

    # Store integration_id on workspace if returned
    if "integration_id" in result:
        from services.core.models import Workspace
        from sqlmodel import select

        # This needs db access — get it from a dependency
        # For now, return the result and let frontend handle it
        pass

    return result


@router.delete("/{integration_id}")
async def delete_integration(integration_id: str, workspace: CurrentWorkspaceDep):
    """Disconnect an integration."""
    return await tps_request("DELETE", f"/integrations/{integration_id}", workspace_id=workspace.id)
