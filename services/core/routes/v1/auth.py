"""Auth routes — magic link login, session, logout."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Response

from services.core.config import settings
from services.core.deps import AuthServiceDep, CurrentUserDep, CurrentWorkspaceDep, DbDep
from services.core.schemas.auth import (
    MagicLinkRequest,
    MagicLinkResponse,
    SessionResponse,
    UserResponse,
    VerifyResponse,
    WorkspaceResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(body: MagicLinkRequest, auth_service: AuthServiceDep):
    await auth_service.request_magic_link(body.email)
    return MagicLinkResponse()


@router.get("/verify", response_model=VerifyResponse)
async def verify_magic_link(token: str, auth_service: AuthServiceDep, response: Response):
    result = await auth_service.verify_and_login(token)

    response.set_cookie(
        key=settings.auth.session_cookie_name,
        value=result.session_id,
        httponly=True,
        secure=settings.auth.session_cookie_secure,
        samesite="lax",
        max_age=settings.auth.session_max_age,
        path="/",
    )

    return VerifyResponse(
        message="Logged in",
        user=UserResponse(
            id=result.user.id, email=result.user.email,
            name=result.user.name, email_verified=result.user.email_verified,
        ),
        is_new_user=result.is_new_user,
    )


@router.get("/session", response_model=SessionResponse)
async def get_session(user: CurrentUserDep, workspace: CurrentWorkspaceDep):
    return SessionResponse(
        user=UserResponse(
            id=user.id, email=user.email, name=user.name, email_verified=user.email_verified,
        ),
        workspace=WorkspaceResponse(
            id=workspace.id, name=workspace.name, slug=workspace.slug,
            integration_id=workspace.integration_id,
        ),
    )


@router.post("/logout")
async def logout(auth_service: AuthServiceDep, response: Response, session_id: str | None = Cookie(default=None)):
    if session_id:
        await auth_service.logout(session_id)
    response.delete_cookie(settings.auth.session_cookie_name, path="/")
    return {"message": "Logged out"}
