"""Service repository with ownership checks and pagination."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.models import Project, Service


class ServiceRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_id(self, service_id: str) -> Service | None:
        result = await self._db.exec(select(Service).where(Service.id == service_id))
        return result.first()

    async def find_by_id_with_ownership(self, service_id: str, workspace_id: str) -> Service | None:
        """Find a service verifying it belongs to the workspace."""
        result = await self._db.exec(
            select(Service)
            .join(Project)
            .where(Service.id == service_id, Project.workspace_id == workspace_id)
        )
        return result.first()

    async def list_by_workspace(
        self, workspace_id: str, limit: int = 20, offset: int = 0
    ) -> tuple[list[Service], int]:
        base = select(Service).join(Project).where(Project.workspace_id == workspace_id)

        count_result = await self._db.exec(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.one()

        result = await self._db.exec(
            base.offset(offset).limit(limit).order_by(Service.created_at.desc())
        )
        return result.all(), total

    async def list_by_project(self, project_id: str) -> list[Service]:
        result = await self._db.exec(
            select(Service)
            .where(Service.project_id == project_id)
            .order_by(Service.created_at.desc())
        )
        return result.all()

    async def create(self, **fields) -> Service:
        service = Service(**fields)
        self._db.add(service)
        await self._db.flush()
        return service

    async def update(self, service: Service, **fields) -> Service:
        for key, value in fields.items():
            setattr(service, key, value)
        # Flag JSON columns as modified for SQLAlchemy change detection
        if "route_graph" in fields:
            flag_modified(service, "route_graph")
        if "metadata_json" in fields:
            flag_modified(service, "metadata_json")
        self._db.add(service)
        await self._db.flush()
        return service

    async def delete(self, service: Service) -> None:
        """Delete service — cascades to artifacts via relationship."""
        await self._db.delete(service)
