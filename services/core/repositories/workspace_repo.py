"""Workspace repository."""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.models import Workspace, WorkspaceMember, WorkspaceRole


class WorkspaceRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_owner(self, owner_id: str) -> Workspace | None:
        result = await self._db.exec(
            select(Workspace).where(Workspace.owner_id == owner_id)
        )
        return result.first()

    async def find_first_for_user(self, user_id: str) -> Workspace | None:
        """Find the first workspace a user belongs to."""
        result = await self._db.exec(
            select(Workspace)
            .join(WorkspaceMember)
            .where(WorkspaceMember.user_id == user_id)
        )
        return result.first()

    async def create_with_member(
        self, name: str, slug: str, owner_id: str
    ) -> Workspace:
        workspace = Workspace(name=name, slug=slug, owner_id=owner_id)
        self._db.add(workspace)
        await self._db.flush()

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner_id,
            role=WorkspaceRole.OWNER.value,
        )
        self._db.add(member)
        await self._db.flush()

        return workspace
