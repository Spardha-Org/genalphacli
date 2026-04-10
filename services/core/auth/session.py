"""Server-side session management backed by PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.config import settings
from services.core.models import Session, utc_now


async def create_session(
    db: AsyncSession,
    user_id: str,
    user_agent: str | None = None,
) -> str:
    """Create a new session and return the session_id (for the cookie)."""
    session = Session(
        user_id=user_id,
        expires_at=utc_now() + timedelta(seconds=settings.session_max_age),
        user_agent=user_agent,
    )
    db.add(session)
    await db.commit()
    return session.session_id


async def validate_session(db: AsyncSession, session_id: str) -> Session | None:
    """Validate a session_id. Returns Session if valid, None if expired/missing."""
    stmt = select(Session).where(
        Session.session_id == session_id,
        Session.expires_at > utc_now(),
    )
    result = await db.exec(stmt)
    session = result.first()

    if session:
        # Rolling window: extend expiry on activity
        session.last_active_at = utc_now()
        session.expires_at = utc_now() + timedelta(seconds=settings.session_max_age)
        db.add(session)
        await db.commit()

    return session


async def delete_session(db: AsyncSession, session_id: str) -> None:
    """Delete a session (logout)."""
    stmt = select(Session).where(Session.session_id == session_id)
    result = await db.exec(stmt)
    session = result.first()
    if session:
        await db.delete(session)
        await db.commit()


async def cleanup_expired_sessions(db: AsyncSession) -> int:
    """Delete all expired sessions. Returns count of deleted sessions."""
    stmt = select(Session).where(Session.expires_at < utc_now())
    result = await db.exec(stmt)
    sessions = result.all()
    for s in sessions:
        await db.delete(s)
    await db.commit()
    return len(sessions)
