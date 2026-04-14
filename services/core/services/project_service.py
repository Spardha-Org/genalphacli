"""Project service — CRUD with workspace ownership."""

from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.exceptions import NotFoundError
from services.core.models import Project, Workspace
from services.core.repositories.project_repo import ProjectRepository


class ProjectService:
    def __init__(self, db: AsyncSession, projects: ProjectRepository):
        self._db = db
        self._projects = projects

    async def list_projects(
        self, workspace: Workspace, limit: int = 20, offset: int = 0
    ) -> tuple[list[Project], int]:
        return await self._projects.list_by_workspace(workspace.id, limit, offset)

    async def create_project(
        self, workspace: Workspace, name: str, description: str | None = None
    ) -> Project:
        project = await self._projects.create(workspace.id, name, description)
        await self._db.commit()
        return project

    async def update_project(
        self, project_id: str, workspace: Workspace, **fields
    ) -> Project:
        project = await self._projects.find_by_id_in_workspace(project_id, workspace.id)
        if not project:
            raise NotFoundError("Project not found")
        project = await self._projects.update(project, **fields)
        await self._db.commit()
        return project

    async def delete_project(self, project_id: str, workspace: Workspace) -> None:
        """Delete project — cascades to services + artifacts via ORM relationship."""
        project = await self._projects.find_by_id_in_workspace(project_id, workspace.id)
        if not project:
            raise NotFoundError("Project not found")
        await self._projects.delete(project)
        await self._db.commit()
