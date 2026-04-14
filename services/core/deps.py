"""FastAPI dependency injection — wires repos, services, clients, and auth guards."""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.config import settings
from services.core.exceptions import UnauthorizedError, NotFoundError
from services.core.models import User, Workspace

# ── Database ──

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database.url, echo=False)
    return _engine


async def get_db():
    engine = get_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


DbDep = Annotated[AsyncSession, Depends(get_db)]


# ── Clients (read from app.state, set in lifespan) ──

def get_tps_client(request: Request):
    from services.core.clients.tps_client import TpsHttpClient
    client: TpsHttpClient = request.app.state.tps
    return client


def get_temporal_client(request: Request):
    from services.core.clients.temporal_client import TemporalClient
    client: TemporalClient = request.app.state.temporal
    return client


def get_email_client(request: Request):
    from services.core.clients.email_client import EmailClient
    client: EmailClient = request.app.state.email
    return client


TpsClientDep = Annotated[object, Depends(get_tps_client)]
TemporalClientDep = Annotated[object, Depends(get_temporal_client)]
EmailClientDep = Annotated[object, Depends(get_email_client)]


# ── Repositories ──

def get_user_repo(db: DbDep):
    from services.core.repositories.user_repo import UserRepository
    return UserRepository(db)


def get_session_repo(db: DbDep):
    from services.core.repositories.session_repo import SessionRepository
    return SessionRepository(db, settings.auth.session_max_age, settings.auth.session_debounce_seconds)


def get_workspace_repo(db: DbDep):
    from services.core.repositories.workspace_repo import WorkspaceRepository
    return WorkspaceRepository(db)


def get_project_repo(db: DbDep):
    from services.core.repositories.project_repo import ProjectRepository
    return ProjectRepository(db)


def get_service_repo(db: DbDep):
    from services.core.repositories.service_repo import ServiceRepository
    return ServiceRepository(db)


def get_artifact_repo(db: DbDep):
    from services.core.repositories.artifact_repo import ArtifactRepository
    return ArtifactRepository(db)


# ── Services ──

def get_auth_service(
    db: DbDep,
    users=Depends(get_user_repo),
    sessions=Depends(get_session_repo),
    workspaces=Depends(get_workspace_repo),
    email=Depends(get_email_client),
):
    from services.core.services.auth_service import AuthService
    return AuthService(db, users, sessions, workspaces, email)


def get_project_service(db: DbDep, projects=Depends(get_project_repo)):
    from services.core.services.project_service import ProjectService
    return ProjectService(db, projects)


def get_parse_service(
    db: DbDep,
    services=Depends(get_service_repo),
    projects=Depends(get_project_repo),
    tps=Depends(get_tps_client),
    temporal=Depends(get_temporal_client),
):
    from services.core.services.parse_service import ParseService
    return ParseService(db, services, projects, tps, temporal)


def get_generate_service(
    db: DbDep,
    services=Depends(get_service_repo),
    tps=Depends(get_tps_client),
    temporal=Depends(get_temporal_client),
):
    from services.core.services.generate_service import GenerateService
    return GenerateService(db, services, tps, temporal)


def get_integration_service(tps=Depends(get_tps_client)):
    from services.core.services.integration_service import IntegrationService
    return IntegrationService(tps)


AuthServiceDep = Annotated[object, Depends(get_auth_service)]
ProjectServiceDep = Annotated[object, Depends(get_project_service)]
ParseServiceDep = Annotated[object, Depends(get_parse_service)]
GenerateServiceDep = Annotated[object, Depends(get_generate_service)]
IntegrationServiceDep = Annotated[object, Depends(get_integration_service)]
ServiceRepoDep = Annotated[object, Depends(get_service_repo)]
ArtifactRepoDep = Annotated[object, Depends(get_artifact_repo)]


# ── Auth Guards ──

async def get_current_user(
    db: DbDep,
    session_id: str | None = Cookie(default=None),
) -> User:
    """Guard: requires valid session cookie."""
    if not session_id:
        raise UnauthorizedError()

    from services.core.repositories.session_repo import SessionRepository
    from services.core.repositories.user_repo import UserRepository

    sessions = SessionRepository(db, settings.auth.session_max_age, settings.auth.session_debounce_seconds)
    session = await sessions.find_valid(session_id)
    if not session:
        raise UnauthorizedError("Session expired or invalid")

    users = UserRepository(db)
    user = await users.find_by_id(session.user_id)
    if not user:
        raise UnauthorizedError("User not found")

    await db.commit()  # Persist debounced session extension
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_current_workspace(
    db: DbDep,
    user: CurrentUserDep,
) -> Workspace:
    """Guard: requires workspace membership."""
    from services.core.repositories.workspace_repo import WorkspaceRepository

    workspaces = WorkspaceRepository(db)
    workspace = await workspaces.find_first_for_user(user.id)
    if not workspace:
        raise NotFoundError("No workspace found")

    return workspace


CurrentWorkspaceDep = Annotated[Workspace, Depends(get_current_workspace)]


async def verify_worker_secret(
    x_worker_secret: str = Header(...),
) -> None:
    """Guard: validates X-Worker-Secret header for internal routes."""
    if x_worker_secret != settings.worker.secret:
        raise UnauthorizedError("Invalid worker secret")


WorkerSecretDep = Annotated[None, Depends(verify_worker_secret)]
