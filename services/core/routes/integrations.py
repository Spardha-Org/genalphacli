"""Integration routes — proxy to TPS service."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from services.core.deps import CurrentWorkspaceDep, DbDep
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
async def install_app(
    app_name: str,
    workspace: CurrentWorkspaceDep,
    body: dict | None = None,
):
    """Start OAuth flow — returns authorize URL for frontend to redirect to."""
    return await tps_request(
        "POST",
        f"/integrations/{app_name}/install",
        workspace_id=workspace.id,
        json=body,
    )


class ExchangeRequest(BaseModel):
    code: str
    state: str


@router.post("/{app_name}/exchange")
async def exchange_oauth_code(
    app_name: str,
    body: ExchangeRequest,
    workspace: CurrentWorkspaceDep,
):
    """Exchange OAuth code+state for token.

    No longer writes to Workspace.integration_id — multi-app support
    means integrations are looked up by (workspace_id, app_name) via TPS.
    """
    return await tps_request(
        "POST",
        f"/integrations/{app_name}/exchange",
        workspace_id=workspace.id,
        json={"code": body.code, "state": body.state},
    )


class ConnectRequest(BaseModel):
    credentials: dict


@router.post("/{app_name}/connect")
async def connect_app(
    app_name: str,
    body: ConnectRequest,
    workspace: CurrentWorkspaceDep,
):
    """Connect a credential-based app (API Key, Basic Auth, mTLS)."""
    return await tps_request(
        "POST",
        f"/integrations/{app_name}/connect",
        workspace_id=workspace.id,
        json={"credentials": body.credentials},
    )


@router.delete("/{integration_id}")
async def delete_integration(integration_id: str, workspace: CurrentWorkspaceDep):
    """Disconnect an integration."""
    return await tps_request("DELETE", f"/integrations/{integration_id}", workspace_id=workspace.id)
