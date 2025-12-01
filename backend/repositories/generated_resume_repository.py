"""
Generated Resume Repository - Phase 2.3

Handles generated resume-specific database operations.
"""

from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.generated_resume import GeneratedResume
from backend.repositories.base_repository import BaseRepository


class GeneratedResumeRepository(BaseRepository[GeneratedResume]):
    """Repository for GeneratedResume model with async operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(GeneratedResume, session)

    async def get_by_user(
        self, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> List[GeneratedResume]:
        """
        Get all generated resumes for a user, ordered by creation date (newest first).

        Args:
            user_id: User UUID
            limit: Maximum number of resumes to return
            offset: Number of resumes to skip

        Returns:
            List of generated resumes
        """
        result = await self.session.execute(
            select(GeneratedResume)
            .where(GeneratedResume.user_id == user_id)
            .order_by(GeneratedResume.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_analysis(
        self, analysis_id: uuid.UUID, limit: int = 10, offset: int = 0
    ) -> List[GeneratedResume]:
        """
        Get all generated resumes for a specific analysis.

        Args:
            analysis_id: Analysis UUID
            limit: Maximum number of resumes to return
            offset: Number of resumes to skip

        Returns:
            List of generated resumes
        """
        result = await self.session.execute(
            select(GeneratedResume)
            .where(GeneratedResume.analysis_id == analysis_id)
            .order_by(GeneratedResume.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_model(
        self, user_id: uuid.UUID, model_name: str, limit: int = 20
    ) -> List[GeneratedResume]:
        """
        Get generated resumes by specific LLM model.

        Args:
            user_id: User UUID
            model_name: Name of the LLM model (e.g., "claude-sonnet-4-20250514")
            limit: Maximum number of resumes to return

        Returns:
            List of generated resumes from specified model
        """
        result = await self.session.execute(
            select(GeneratedResume)
            .where(
                GeneratedResume.user_id == user_id,
                GeneratedResume.model_used == model_name,
            )
            .order_by(GeneratedResume.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        """
        Count total generated resumes for a user.

        Args:
            user_id: User UUID

        Returns:
            Total count of generated resumes
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count(GeneratedResume.id)).where(
                GeneratedResume.user_id == user_id
            )
        )
        return result.scalar_one()

    async def get_latest_by_analysis(
        self, analysis_id: uuid.UUID
    ) -> Optional[GeneratedResume]:
        """
        Get the most recent generated resume for an analysis.

        Args:
            analysis_id: Analysis UUID

        Returns:
            Most recent GeneratedResume or None
        """
        result = await self.session.execute(
            select(GeneratedResume)
            .where(GeneratedResume.analysis_id == analysis_id)
            .order_by(GeneratedResume.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
