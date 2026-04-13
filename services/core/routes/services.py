"""Service CRUD and status routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import select

from services.core.deps import CurrentUserDep, CurrentWorkspaceDep, DbDep
from services.core.models import Artifact, Project, Service

router = APIRouter(prefix="/services", tags=["services"])


class CreateServiceRequest(BaseModel):
    repo_url: str
    project_id: str


@router.get("")
async def list_all_services(
    db: DbDep,
    workspace: CurrentWorkspaceDep,
):
    """List all services across all projects for the current workspace."""
    result = await db.exec(
        select(Service)
        .join(Project)
        .where(Project.workspace_id == workspace.id)
    )
    services = result.all()

    return [
        {
            "id": s.id,
            "project_id": s.project_id,
            "name": s.name,
            "repo_url": s.repo_url,
            "framework": s.framework,
            "status": s.status,
            "error_message": s.error_message,
            "created_at": s.created_at.isoformat(),
        }
        for s in services
    ]


@router.get("/by-project/{project_id}")
async def list_services_by_project(
    project_id: str,
    db: DbDep,
    workspace: CurrentWorkspaceDep,
):
    """List all services for a project (excludes route_graph for performance)."""
    # Verify project belongs to workspace
    project_result = await db.exec(
        select(Project).where(Project.id == project_id, Project.workspace_id == workspace.id)
    )
    if not project_result.first():
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.exec(
        select(Service).where(Service.project_id == project_id)
    )
    services = result.all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "repo_url": s.repo_url,
            "framework": s.framework,
            "status": s.status,
            "error_message": s.error_message,
            "created_at": s.created_at.isoformat(),
        }
        for s in services
    ]


@router.get("/{service_id}")
async def get_service(
    service_id: str,
    db: DbDep,
    workspace: CurrentWorkspaceDep,
):
    """Get a service with ownership check."""
    stmt = (
        select(Service)
        .join(Project)
        .where(Service.id == service_id, Project.workspace_id == workspace.id)
    )
    result = await db.exec(stmt)
    service = result.first()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    return {
        "id": service.id,
        "project_id": service.project_id,
        "name": service.name,
        "repo_url": service.repo_url,
        "framework": service.framework,
        "status": service.status,
        "route_graph": service.route_graph,
        "error_message": service.error_message,
        "artifact_id": service.artifact_id,
        "download_url": service.download_url,  # deprecated
        "metadata": service.metadata_json,
        "created_at": service.created_at.isoformat(),
    }


@router.delete("/{service_id}")
async def delete_service(
    service_id: str,
    db: DbDep,
    workspace: CurrentWorkspaceDep,
):
    """Delete a service with ownership check."""
    stmt = (
        select(Service)
        .join(Project)
        .where(Service.id == service_id, Project.workspace_id == workspace.id)
    )
    result = await db.exec(stmt)
    service = result.first()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Delete associated artifacts first
    artifact_result = await db.exec(
        select(Artifact).where(Artifact.service_id == service_id)
    )
    for artifact in artifact_result.all():
        await db.delete(artifact)

    await db.delete(service)
    await db.commit()

    return {"ok": True}


class AuthConfigRequest(BaseModel):
    login_endpoint: str = ""
    login_params: list[str] = []
    refresh_endpoint: str = ""
    auth_type: str = "bearer"


@router.post("/{service_id}/auth-config")
async def set_auth_config(
    service_id: str,
    body: AuthConfigRequest,
    db: DbDep,
    workspace: CurrentWorkspaceDep,
):
    """Save user-confirmed auth config. Merges into route_graph.auth for generators."""
    stmt = (
        select(Service)
        .join(Project)
        .where(Service.id == service_id, Project.workspace_id == workspace.id)
    )
    result = await db.exec(stmt)
    service = result.first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Merge into route_graph.auth so generators read from established path
    # Must reassign the whole dict — SQLAlchemy doesn't detect in-place JSON mutations
    route_graph = dict(service.route_graph or {})
    auth = dict(route_graph.get("auth", {}))
    auth["login_endpoint"] = body.login_endpoint
    auth["login_params"] = body.login_params
    auth["refresh_endpoint"] = body.refresh_endpoint
    route_graph["auth"] = auth
    service.route_graph = route_graph

    # Also store in metadata for frontend reference
    metadata = dict(service.metadata_json or {})
    metadata["auth_config"] = body.model_dump()
    service.metadata_json = metadata

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(service, "route_graph")
    flag_modified(service, "metadata_json")

    db.add(service)
    await db.commit()

    return {"ok": True}


@router.get("/{service_id}/download")
async def download_service(
    service_id: str,
    db: DbDep,
    workspace: CurrentWorkspaceDep,
):
    """Download the generated zip for a service (redirects to artifact)."""
    stmt = (
        select(Service)
        .join(Project)
        .where(Service.id == service_id, Project.workspace_id == workspace.id)
    )
    result = await db.exec(stmt)
    service = result.first()

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    if service.status != "complete" or not service.artifact_id:
        raise HTTPException(status_code=400, detail="Download not available. Generate first.")

    # Serve from DB artifact
    artifact_result = await db.exec(
        select(Artifact).where(Artifact.id == service.artifact_id)
    )
    artifact = artifact_result.first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found. Please regenerate.")

    return Response(
        content=artifact.file_data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )
