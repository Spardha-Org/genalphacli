"""Test fixtures for Core service API tests.

Uses SQLite in-memory DB to avoid needing PostgreSQL for tests.
Overrides auth dependencies to bypass session/cookie checks.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.models import (
    Artifact,
    Project,
    Service,
    User,
    Workspace,
    WorkspaceMember,
)


@pytest_asyncio.fixture
async def engine():
    """Create an in-memory SQLite async engine."""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with eng.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    """Yield a fresh async session."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


@pytest_asyncio.fixture
async def seed_data(db):
    """Seed a user, workspace, project, and service for testing."""
    user = User(id="test-user", email="test@example.com", name="Test User", email_verified=True)
    db.add(user)
    await db.flush()

    workspace = Workspace(id="test-ws", name="Test Workspace", slug="test-ws", owner_id=user.id)
    db.add(workspace)
    await db.flush()

    member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner")
    db.add(member)
    await db.flush()

    project = Project(id="test-proj", workspace_id=workspace.id, name="Test Project")
    db.add(project)
    await db.flush()

    service = Service(
        id="test-svc",
        project_id=project.id,
        name="test-api",
        repo_url="https://github.com/test/test-api",
        status="complete",
    )
    db.add(service)
    await db.commit()

    return {
        "user": user,
        "workspace": workspace,
        "project": project,
        "service": service,
    }


@pytest_asyncio.fixture
async def client(engine, seed_data):
    """Create an async test client with dependency overrides."""
    from services.core.main import app
    from services.core.deps import get_db, get_current_user, get_current_workspace

    async def override_get_db():
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    async def override_get_current_user():
        return seed_data["user"]

    async def override_get_current_workspace():
        return seed_data["workspace"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_workspace] = override_get_current_workspace

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
