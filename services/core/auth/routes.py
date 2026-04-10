"""Auth routes: magic link login, session management."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, EmailStr

from services.core.auth.magic_link import create_magic_token, verify_magic_token
from services.core.auth.session import create_session, delete_session
from services.core.config import settings
from services.core.deps import CurrentUserDep, DbDep
from services.core.models import (
    Project,
    User,
    Workspace,
    WorkspaceMember,
    generate_cuid,
)
from sqlmodel import select

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkResponse(BaseModel):
    message: str


@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(body: MagicLinkRequest, db: DbDep):
    """Send a magic link to the user's email.

    Always returns 200 regardless of whether the email exists (prevents enumeration).
    For MVP: logs the link to console instead of sending email.
    """
    token = create_magic_token(body.email)
    link = f"{settings.app_url}/auth/verify?token={token}"

    # MVP: log to console instead of sending email
    logger.info("=== MAGIC LINK ===")
    logger.info("Email: %s", body.email)
    logger.info("Link: %s", link)
    logger.info("==================")

    # TODO: Replace with actual email sending (Resend, SES, etc.)

    return MagicLinkResponse(message="If that email exists, a login link was sent.")


@router.get("/verify")
async def verify_magic_link(
    response: Response,
    request: Request,
    db: DbDep,
    token: Annotated[str, Query()],
):
    """Verify a magic link token, create/find user, set session cookie."""
    email = verify_magic_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired magic link")

    # Get or create user
    stmt = select(User).where(User.email == email)
    result = await db.exec(stmt)
    user = result.first()

    is_new_user = user is None

    if not user:
        user = User(email=email, email_verified=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.email_verified:
        user.email_verified = True
        db.add(user)
        await db.commit()

    # Auto-create workspace + project for new users
    if is_new_user:
        slug = email.split("@")[0].lower().replace(".", "-").replace("+", "-")
        slug = f"{slug}-{user.id[:6]}"

        workspace = Workspace(
            name=f"{slug}'s workspace",
            slug=slug,
            owner_id=user.id,
        )
        db.add(workspace)
        await db.commit()
        await db.refresh(workspace)

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner",
        )
        db.add(member)

        project = Project(
            workspace_id=workspace.id,
            name="Default Project",
            description="Your first project — add services by pasting a GitHub URL.",
        )
        db.add(project)
        await db.commit()

    # Create session
    user_agent = request.headers.get("user-agent")
    session_id = await create_session(db, user.id, user_agent)

    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_max_age,
    )

    return {
        "message": "Logged in",
        "user": {"id": user.id, "email": user.email, "name": user.name},
        "is_new_user": is_new_user,
    }


@router.get("/session")
async def get_session(user: CurrentUserDep, db: DbDep):
    """Get the current user's session info including workspace."""
    stmt = (
        select(WorkspaceMember)
        .where(WorkspaceMember.user_id == user.id)
    )
    result = await db.exec(stmt)
    membership = result.first()

    workspace = None
    if membership:
        ws_stmt = select(Workspace).where(Workspace.id == membership.workspace_id)
        ws_result = await db.exec(ws_stmt)
        workspace = ws_result.first()

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "email_verified": user.email_verified,
        },
        "workspace": {
            "id": workspace.id,
            "name": workspace.name,
            "slug": workspace.slug,
            "integration_id": workspace.integration_id,
        } if workspace else None,
    }


@router.post("/logout")
async def logout(
    response: Response,
    db: DbDep,
    session_id: str | None = Query(default=None, include_in_schema=False),
):
    """Log out by deleting the session."""
    from fastapi import Cookie as CookieParam
    # Get session from cookie
    if session_id:
        await delete_session(db, session_id)

    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )

    return {"message": "Logged out"}
