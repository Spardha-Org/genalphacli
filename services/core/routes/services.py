"""Service CRUD and status routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select, func

from services.core.deps import CurrentUserDep, CurrentWorkspaceDep, DbDep
from services.core.models import Project, Service

router = APIRouter(prefix="/services", tags=["services"])

ACTIVE_STATUSES = ["parsed", "generating", "packaging", "complete"]
MAX_SERVICES_PER_WORKSPACE = 2


class CreateServiceRequest(BaseModel):
    repo_url: str
    project_id: str


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
        "download_url": service.download_url,
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

    await db.delete(service)
    await db.commit()

    return {"ok": True}
