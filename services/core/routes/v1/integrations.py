"""Integration routes — app store, OAuth, credentials."""

from __future__ import annotations

from fastapi import APIRouter

from services.core.deps import CurrentWorkspaceDep, IntegrationServiceDep
from services.core.schemas.common import OkResponse
from services.core.schemas.integration import ConnectRequest, InstallRequest

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/apps")
async def list_apps(integration_service: IntegrationServiceDep):
    return await integration_service.list_apps()


@router.get("/apps/{identifier}")
async def get_app(identifier: str, integration_service: IntegrationServiceDep):
    return await integration_service.get_app(identifier)


@router.get("")
async def list_integrations(workspace: CurrentWorkspaceDep, integration_service: IntegrationServiceDep):
    return await integration_service.list_integrations(workspace.owner_id)


@router.get("/{identifier}")
async def get_integration(identifier: str, workspace: CurrentWorkspaceDep, integration_service: IntegrationServiceDep):
    return await integration_service.get_integration(workspace.owner_id, identifier)


@router.post("/{app_name}/install")
async def install_app(app_name: str, body: InstallRequest, workspace: CurrentWorkspaceDep, integration_service: IntegrationServiceDep):
    authorize_url = await integration_service.start_install(
        workspace.owner_id, app_name, body.callback_path, body.form_data,
    )
    return {"authorize_url": authorize_url}


@router.post("/{app_name}/connect")
async def connect_app(app_name: str, body: ConnectRequest, workspace: CurrentWorkspaceDep, integration_service: IntegrationServiceDep):
    return await integration_service.connect_credentials(workspace.owner_id, app_name, body.credentials)


@router.delete("/{integration_id}", response_model=OkResponse)
async def delete_integration(integration_id: str, workspace: CurrentWorkspaceDep, integration_service: IntegrationServiceDep):
    await integration_service.delete_integration(workspace.owner_id, integration_id)
    return OkResponse()
