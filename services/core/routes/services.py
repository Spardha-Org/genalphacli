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
