"""FastAPI dependencies for the Core service."""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.config import settings
from services.core.auth.session import validate_session
from services.core.models import User, WorkspaceMember, Workspace

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


async def get_db():
    """Yield an async database session."""
    engine = get_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbDep,
    session_id: str | None = Cookie(default=None),
) -> User:
    """Get the current authenticated user from session cookie."""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await validate_session(db, session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    stmt = select(User).where(User.id == session.user_id)
    result = await db.exec(stmt)
    user = result.first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_current_workspace(
    db: DbDep,
    user: CurrentUserDep,
) -> Workspace:
    """Get the current user's workspace."""
    stmt = (
        select(Workspace)
        .join(WorkspaceMember)
        .where(WorkspaceMember.user_id == user.id)
    )
    result = await db.exec(stmt)
    workspace = result.first()

    if not workspace:
        raise HTTPException(status_code=404, detail="No workspace found")

    return workspace


CurrentWorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]
