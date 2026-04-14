"""Artifact repository."""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.models import Artifact, Project, Service


class ArtifactRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_id(self, artifact_id: str) -> Artifact | None:
        result = await self._db.exec(select(Artifact).where(Artifact.id == artifact_id))
        return result.first()

    async def find_by_id_with_ownership(self, artifact_id: str, workspace_id: str) -> Artifact | None:
        """Find an artifact verifying it belongs to the workspace."""
        result = await self._db.exec(
            select(Artifact)
            .join(Service)
            .join(Project)
            .where(Artifact.id == artifact_id, Project.workspace_id == workspace_id)
        )
        return result.first()

    async def upsert_for_service(
        self, service_id: str, artifact_type: str, filename: str,
        file_data: bytes, file_size: int,
    ) -> Artifact:
        """Create or replace an artifact for a service."""
        # Delete existing artifacts for this service
        result = await self._db.exec(
            select(Artifact).where(Artifact.service_id == service_id)
        )
        for old in result.all():
            await self._db.delete(old)

        artifact = Artifact(
            service_id=service_id,
            artifact_type=artifact_type,
            filename=filename,
            file_data=file_data,
            file_size=file_size,
        )
        self._db.add(artifact)
        await self._db.flush()
        return artifact
