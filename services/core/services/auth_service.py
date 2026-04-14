"""Auth service — magic link, session management, OAuth."""

from __future__ import annotations

import logging
import re

from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.auth.magic_link import create_magic_token, verify_magic_token
from services.core.clients.email_client import EmailClient
from services.core.config import settings
from services.core.exceptions import NotFoundError, UnauthorizedError
from services.core.models import Project, User, Workspace
from services.core.repositories.session_repo import SessionRepository
from services.core.repositories.user_repo import UserRepository
from services.core.repositories.workspace_repo import WorkspaceRepository

logger = logging.getLogger(__name__)


class LoginResult:
    def __init__(self, user: User, session_id: str, workspace: Workspace | None, is_new_user: bool):
        self.user = user
        self.session_id = session_id
        self.workspace = workspace
        self.is_new_user = is_new_user


class AuthService:
    def __init__(
        self,
        db: AsyncSession,
        users: UserRepository,
        sessions: SessionRepository,
        workspaces: WorkspaceRepository,
        email_client: EmailClient,
    ):
        self._db = db
        self._users = users
        self._sessions = sessions
        self._workspaces = workspaces
        self._email = email_client

    async def request_magic_link(self, email: str) -> None:
        """Send a magic link email. Always succeeds (prevents email enumeration)."""
        token = create_magic_token(email)
        link = f"{settings.app_url}/auth/verify?token={token}"
        await self._email.send_magic_link(email, link)

    async def verify_and_login(self, token: str, user_agent: str | None = None) -> LoginResult:
        """Verify a magic link token and create a session.

        Single transaction: find/create user → ensure workspace → create session.
        """
        email = verify_magic_token(token)
        if not email:
            raise UnauthorizedError("Invalid or expired magic link")

        # Find or create user
        user = await self._users.find_by_email(email)
        is_new_user = user is None

        if not user:
            user = await self._users.create(email=email)

        if not user.email_verified:
            await self._users.update(user, email_verified=True)

        # Ensure default workspace
        workspace = await self._workspaces.find_first_for_user(user.id)
        if not workspace:
            slug = _generate_slug(email, user.id)
            workspace = await self._workspaces.create_with_member(
                name=f"{slug}'s workspace",
                slug=slug,
                owner_id=user.id,
            )
            # Create default project for new workspaces
            project = Project(workspace_id=workspace.id, name="Default", description="Your first project")
            self._db.add(project)

        # Create session
        session = await self._sessions.create(user.id, user_agent)

        # Single commit for entire operation
        await self._db.commit()

        return LoginResult(
            user=user,
            session_id=session.session_id,
            workspace=workspace,
            is_new_user=is_new_user,
        )

    async def get_session(self, session_id: str) -> tuple[User, Workspace | None]:
        """Validate session and return user + workspace."""
        session = await self._sessions.find_valid(session_id)
        if not session:
            raise UnauthorizedError("Session expired or invalid")

        user = await self._users.find_by_id(session.user_id)
        if not user:
            raise UnauthorizedError("User not found")

        workspace = await self._workspaces.find_first_for_user(user.id)

        await self._db.commit()  # Persist debounced session extension
        return user, workspace

    async def logout(self, session_id: str) -> None:
        """Delete a session."""
        await self._sessions.delete(session_id)
        await self._db.commit()


def _generate_slug(email: str, user_id: str) -> str:
    """Generate a workspace slug from email + user ID suffix."""
    local = email.split("@")[0]
    slug = re.sub(r"[^a-z0-9-]", "-", local.lower())[:20]
    return f"{slug}-{user_id[:6]}"
