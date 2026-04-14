"""Project routes — CRUD with workspace ownership."""

from __future__ import annotations

from fastapi import APIRouter, Query

from services.core.deps import CurrentWorkspaceDep, ProjectServiceDep
from services.core.schemas.common import OkResponse
from services.core.schemas.project import CreateProjectRequest, ProjectResponse, UpdateProjectRequest

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    workspace: CurrentWorkspaceDep,
    project_service: ProjectServiceDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    items, total = await project_service.list_projects(workspace, limit, offset)
    return [
        ProjectResponse(id=p.id, name=p.name, description=p.description, created_at=p.created_at.isoformat())
        for p in items
    ]


@router.post("", response_model=ProjectResponse)
async def create_project(body: CreateProjectRequest, workspace: CurrentWorkspaceDep, project_service: ProjectServiceDep):
    project = await project_service.create_project(workspace, body.name, body.description)
    return ProjectResponse(id=project.id, name=project.name, description=project.description, created_at=project.created_at.isoformat())


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, body: UpdateProjectRequest, workspace: CurrentWorkspaceDep, project_service: ProjectServiceDep):
    project = await project_service.update_project(project_id, workspace, name=body.name, description=body.description)
    return ProjectResponse(id=project.id, name=project.name, description=project.description, created_at=project.created_at.isoformat())


@router.delete("/{project_id}", response_model=OkResponse)
async def delete_project(project_id: str, workspace: CurrentWorkspaceDep, project_service: ProjectServiceDep):
    await project_service.delete_project(project_id, workspace)
    return OkResponse()
