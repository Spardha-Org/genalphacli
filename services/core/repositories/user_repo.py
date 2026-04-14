"""User repository."""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from services.core.models import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_email(self, email: str) -> User | None:
        result = await self._db.exec(select(User).where(User.email == email))
        return result.first()

    async def find_by_id(self, user_id: str) -> User | None:
        result = await self._db.exec(select(User).where(User.id == user_id))
        return result.first()

    async def create(self, email: str, name: str | None = None) -> User:
        user = User(email=email, name=name)
        self._db.add(user)
        await self._db.flush()  # Get ID without committing
        return user

    async def update(self, user: User, **fields) -> User:
        for key, value in fields.items():
            setattr(user, key, value)
        self._db.add(user)
        await self._db.flush()
        return user
