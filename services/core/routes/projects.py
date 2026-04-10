"""Project CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from services.core.deps import CurrentUserDep, CurrentWorkspaceDep, DbDep
from services.core.models import Project

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    description: str | None = None


@router.get("")
async def list_projects(db: DbDep, workspace: CurrentWorkspaceDep):
    """List all projects in the current workspace."""
    stmt = select(Project).where(Project.workspace_id == workspace.id)
    result = await db.exec(stmt)
    projects = result.all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "created_at": p.created_at.isoformat(),
        }
        for p in projects
    ]


@router.post("")
async def create_project(
    body: CreateProjectRequest,
    db: DbDep,
    workspace: CurrentWorkspaceDep,
):
    """Create a new project in the current workspace."""
    project = Project(
        workspace_id=workspace.id,
        name=body.name.strip(),
        description=body.description,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at.isoformat(),
    }


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: DbDep,
    workspace: CurrentWorkspaceDep,
):
    """Delete a project (cascade deletes services)."""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.workspace_id == workspace.id,
    )
    result = await db.exec(stmt)
    project = result.first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()

    return {"ok": True}
