"""Session repository with debounce pattern."""

from __future__ import annotations

import secrets
from datetime import timedelta

from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.models import Session, utc_now


class SessionRepository:
    def __init__(self, db: AsyncSession, session_max_age: int = 604800, debounce_seconds: int = 300):
        self._db = db
        self._max_age = session_max_age
        self._debounce = debounce_seconds

    async def create(self, user_id: str, user_agent: str | None = None) -> Session:
        now = utc_now()
        session = Session(
            session_id=secrets.token_urlsafe(32),
            user_id=user_id,
            expires_at=now + timedelta(seconds=self._max_age),
            last_active_at=now,
            user_agent=user_agent,
        )
        self._db.add(session)
        await self._db.flush()
        return session

    async def find_valid(self, session_id: str) -> Session | None:
        """Find a session and extend it if stale (debounce pattern)."""
        result = await self._db.exec(
            select(Session).where(Session.session_id == session_id)
        )
        session = result.first()
        if not session:
            return None

        now = utc_now()
        if session.expires_at < now:
            return None  # Expired

        # Debounce: only extend if last_active > N seconds ago
        elapsed = (now - session.last_active_at).total_seconds()
        if elapsed > self._debounce:
            session.last_active_at = now
            session.expires_at = now + timedelta(seconds=self._max_age)
            self._db.add(session)
            # No flush needed — commit happens in service layer

        return session

    async def delete(self, session_id: str) -> None:
        result = await self._db.exec(
            select(Session).where(Session.session_id == session_id)
        )
        session = result.first()
        if session:
            await self._db.delete(session)

    async def cleanup_expired(self) -> int:
        """Delete all expired sessions in a single query."""
        now = utc_now()
        stmt = delete(Session).where(Session.expires_at < now)
        result = await self._db.exec(stmt)
        return result.rowcount  # type: ignore
