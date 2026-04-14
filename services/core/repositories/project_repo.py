"""Project repository with pagination."""

from __future__ import annotations

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.models import Project


class ProjectRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_id_in_workspace(self, project_id: str, workspace_id: str) -> Project | None:
        result = await self._db.exec(
            select(Project).where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
            )
        )
        return result.first()

    async def list_by_workspace(
        self, workspace_id: str, limit: int = 20, offset: int = 0
    ) -> tuple[list[Project], int]:
        # Count
        count_result = await self._db.exec(
            select(func.count()).select_from(Project).where(Project.workspace_id == workspace_id)
        )
        total = count_result.one()

        # Items
        result = await self._db.exec(
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .offset(offset)
            .limit(limit)
            .order_by(Project.created_at.desc())
        )
        return result.all(), total

    async def create(self, workspace_id: str, name: str, description: str | None = None) -> Project:
        project = Project(workspace_id=workspace_id, name=name, description=description)
        self._db.add(project)
        await self._db.flush()
        return project

    async def update(self, project: Project, **fields) -> Project:
        for key, value in fields.items():
            if value is not None:
                setattr(project, key, value)
        self._db.add(project)
        await self._db.flush()
        return project

    async def delete(self, project: Project) -> None:
        """Delete project — cascades to services and artifacts via relationship."""
        await self._db.delete(project)
