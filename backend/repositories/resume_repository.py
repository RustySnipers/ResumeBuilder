"""
Resume Repository - Phase 2.3

Handles resume-specific database operations.
"""

from typing import List
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.models.resume import Resume
from backend.repositories.base_repository import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    """Repository for Resume model with async operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Resume, session)

    async def get_by_user(
        self, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> List[Resume]:
        """
        Get all resumes for a user, ordered by creation date (newest first).

        Args:
            user_id: User UUID
            limit: Maximum number of resumes to return
            offset: Number of resumes to skip

        Returns:
            List of resumes
        """
        result = await self.session.execute(
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_latest_version(self, user_id: uuid.UUID, title: str) -> int:
        """
        Get the latest version number for a resume title.

        Args:
            user_id: User UUID
            title: Resume title

        Returns:
            Latest version number (0 if no versions exist)
        """
        result = await self.session.execute(
            select(func.max(Resume.version))
            .where(Resume.user_id == user_id, Resume.title == title)
        )
        max_version = result.scalar_one_or_none()
        return max_version if max_version is not None else 0

    async def get_by_title(
        self, user_id: uuid.UUID, title: str
    ) -> List[Resume]:
        """
        Get all versions of a resume by title.

        Args:
            user_id: User UUID
            title: Resume title

        Returns:
            List of resume versions ordered by version number
        """
        result = await self.session.execute(
            select(Resume)
            .where(Resume.user_id == user_id, Resume.title == title)
            .order_by(Resume.version.desc())
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        """
        Count total resumes for a user.

        Args:
            user_id: User UUID

        Returns:
            Total count of resumes
        """
        result = await self.session.execute(
            select(func.count(Resume.id)).where(Resume.user_id == user_id)
        )
        return result.scalar_one()
