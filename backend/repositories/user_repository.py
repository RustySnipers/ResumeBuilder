"""
User Repository - Phase 2.3

Handles user-specific database operations.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.user import User
from backend.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model with async operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User email address

        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """
        Check if email already exists.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        result = await self.session.execute(
            select(User.id).where(User.email == email)
        )
        return result.scalar_one_or_none() is not None

    async def get_active_users(self, limit: int = 100, offset: int = 0) -> list[User]:
        """
        Get all active users.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip

        Returns:
            List of active users
        """
        result = await self.session.execute(
            select(User)
            .where(User.is_active.is_(True))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
