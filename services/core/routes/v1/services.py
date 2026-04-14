"""Service routes — CRUD, auth config, download."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from services.core.deps import CurrentWorkspaceDep, DbDep, ServiceRepoDep, ArtifactRepoDep
from services.core.exceptions import NotFoundError, ValidationError
from services.core.schemas.common import OkResponse
from services.core.schemas.service import AuthConfigRequest, ServiceListItem, ServiceResponse

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=list[ServiceListItem])
async def list_all_services(workspace: CurrentWorkspaceDep, service_repo: ServiceRepoDep):
    items, _ = await service_repo.list_by_workspace(workspace.id)
    return [
        ServiceListItem(
            id=s.id, project_id=s.project_id, name=s.name, repo_url=s.repo_url,
            framework=s.framework, status=s.status, error_message=s.error_message,
            created_at=s.created_at.isoformat(),
        )
        for s in items
    ]


@router.get("/by-project/{project_id}", response_model=list[ServiceListItem])
async def list_services_by_project(project_id: str, service_repo: ServiceRepoDep):
    items = await service_repo.list_by_project(project_id)
    return [
        ServiceListItem(
            id=s.id, project_id=s.project_id, name=s.name, repo_url=s.repo_url,
            framework=s.framework, status=s.status, error_message=s.error_message,
            created_at=s.created_at.isoformat(),
        )
        for s in items
    ]


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(service_id: str, workspace: CurrentWorkspaceDep, service_repo: ServiceRepoDep):
    service = await service_repo.find_by_id_with_ownership(service_id, workspace.id)
    if not service:
        raise NotFoundError("Service not found")
    return ServiceResponse(
        id=service.id, project_id=service.project_id, name=service.name,
        repo_url=service.repo_url, source_type=service.source_type,
        source_version=service.source_version, framework=service.framework,
        status=service.status, route_graph=service.route_graph,
        error_message=service.error_message, artifact_id=service.artifact_id,
        metadata=service.metadata_json, created_at=service.created_at.isoformat(),
    )


@router.delete("/{service_id}", response_model=OkResponse)
async def delete_service(service_id: str, workspace: CurrentWorkspaceDep, service_repo: ServiceRepoDep, db: DbDep):
    service = await service_repo.find_by_id_with_ownership(service_id, workspace.id)
    if not service:
        raise NotFoundError("Service not found")
    await service_repo.delete(service)
    await db.commit()
    return OkResponse()


@router.post("/{service_id}/auth-config", response_model=OkResponse)
async def set_auth_config(
    service_id: str, body: AuthConfigRequest,
    workspace: CurrentWorkspaceDep, service_repo: ServiceRepoDep, db: DbDep,
):
    service = await service_repo.find_by_id_with_ownership(service_id, workspace.id)
    if not service:
        raise NotFoundError("Service not found")

    route_graph = dict(service.route_graph or {})
    auth = dict(route_graph.get("auth", {}))
    auth["login_endpoint"] = body.login_endpoint
    auth["login_params"] = body.login_params
    auth["refresh_endpoint"] = body.refresh_endpoint
    route_graph["auth"] = auth

    metadata = dict(service.metadata_json or {})
    metadata["auth_config"] = body.model_dump()

    await service_repo.update(service, route_graph=route_graph, metadata_json=metadata)
    await db.commit()
    return OkResponse()


@router.get("/{service_id}/download")
async def download_service(service_id: str, workspace: CurrentWorkspaceDep, service_repo: ServiceRepoDep, artifact_repo: ArtifactRepoDep):
    service = await service_repo.find_by_id_with_ownership(service_id, workspace.id)
    if not service:
        raise NotFoundError("Service not found")
    if not service.artifact_id:
        raise ValidationError("No artifact. Generate first.")

    artifact = await artifact_repo.find_by_id(service.artifact_id)
    if not artifact:
        raise NotFoundError("Artifact not found. Regenerate.")

    return Response(
        content=artifact.file_data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )
