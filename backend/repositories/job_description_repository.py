"""
Job Description Repository - Phase 2.3

Handles job description-specific database operations.
"""

from typing import List
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.models.job_description import JobDescription
from backend.repositories.base_repository import BaseRepository


class JobDescriptionRepository(BaseRepository[JobDescription]):
    """Repository for JobDescription model with async operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(JobDescription, session)

    async def get_by_user(
        self, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> List[JobDescription]:
        """
        Get all job descriptions for a user, ordered by creation date (newest first).

        Args:
            user_id: User UUID
            limit: Maximum number of job descriptions to return
            offset: Number of job descriptions to skip

        Returns:
            List of job descriptions
        """
        result = await self.session.execute(
            select(JobDescription)
            .where(JobDescription.user_id == user_id)
            .order_by(JobDescription.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def search_by_company(
        self, user_id: uuid.UUID, company_name: str
    ) -> List[JobDescription]:
        """
        Search job descriptions by company name (case-insensitive partial match).

        Args:
            user_id: User UUID
            company_name: Company name to search for

        Returns:
            List of matching job descriptions
        """
        result = await self.session.execute(
            select(JobDescription)
            .where(
                JobDescription.user_id == user_id,
                JobDescription.company_name.ilike(f'%{company_name}%')
            )
            .order_by(JobDescription.created_at.desc())
        )
        return list(result.scalars().all())

    async def search_by_position(
        self, user_id: uuid.UUID, position_title: str
    ) -> List[JobDescription]:
        """
        Search job descriptions by position title (case-insensitive partial match).

        Args:
            user_id: User UUID
            position_title: Position title to search for

        Returns:
            List of matching job descriptions
        """
        result = await self.session.execute(
            select(JobDescription)
            .where(
                JobDescription.user_id == user_id,
                JobDescription.position_title.ilike(f'%{position_title}%')
            )
            .order_by(JobDescription.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        """
        Count total job descriptions for a user.

        Args:
            user_id: User UUID

        Returns:
            Total count of job descriptions
        """
        result = await self.session.execute(
            select(func.count(JobDescription.id))
            .where(JobDescription.user_id == user_id)
        )
        return result.scalar_one()
