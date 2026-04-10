"""TPS service dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from services.tps.config import settings

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


async def get_db():
    engine = get_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


DbDep = Annotated[AsyncSession, Depends(get_db)]


async def validate_tps_secret(
    x_tps_secret: str = Header(..., alias="X-TPS-Secret"),
) -> None:
    """Validate the shared secret header from Core/Worker."""
    if x_tps_secret != settings.tps_secret:
        raise HTTPException(status_code=403, detail="Invalid TPS secret")


TpsAuthDep = Annotated[None, Depends(validate_tps_secret)]


async def get_workspace_id(
    x_workspace_id: str = Header(..., alias="X-Workspace-ID"),
) -> str:
    """Extract workspace_id from header."""
    if not x_workspace_id:
        raise HTTPException(status_code=400, detail="X-Workspace-ID header required")
    return x_workspace_id


WorkspaceIdDep = Annotated[str, Depends(get_workspace_id)]
