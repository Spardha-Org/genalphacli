"""Integration routes — proxy to TPS service."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from services.core.deps import CurrentWorkspaceDep, DbDep
from services.core.tps_client import tps_request
from services.core.models import Workspace
from sqlmodel import select

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
    """Start OAuth flow — returns authorize URL for frontend to redirect to."""
    return await tps_request("POST", f"/integrations/{app_name}/install", workspace_id=workspace.id)


class ExchangeRequest(BaseModel):
    code: str
    state: str


@router.post("/{app_name}/exchange")
async def exchange_oauth_code(
    app_name: str,
    body: ExchangeRequest,
    workspace: CurrentWorkspaceDep,
    db: DbDep,
):
    """Exchange OAuth code+state for token. Called by frontend after GitHub redirect.

    Flow: GitHub redirects to frontend callback page → frontend POSTs code+state here
    → Core forwards to TPS → TPS validates state, exchanges code, stores encrypted token.
    """
    result = await tps_request(
        "POST",
        f"/integrations/{app_name}/exchange",
        workspace_id=workspace.id,
        json={"code": body.code, "state": body.state},
    )

    # Store integration_id on workspace
    if "integration_id" in result:
        stmt = select(Workspace).where(Workspace.id == workspace.id)
        ws_result = await db.exec(stmt)
        ws = ws_result.first()
        if ws:
            ws.integration_id = result["integration_id"]
            db.add(ws)
            await db.commit()

    return result


@router.delete("/{integration_id}")
async def delete_integration(integration_id: str, workspace: CurrentWorkspaceDep):
    """Disconnect an integration."""
    return await tps_request("DELETE", f"/integrations/{integration_id}", workspace_id=workspace.id)
