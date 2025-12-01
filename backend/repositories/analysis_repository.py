"""
Analysis Repository - Phase 2.3

Handles analysis-specific database operations.
"""

from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from backend.models.analysis import Analysis
from backend.repositories.base_repository import BaseRepository


class AnalysisRepository(BaseRepository[Analysis]):
    """Repository for Analysis model with async operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Analysis, session)

    async def get_by_user(
        self, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> List[Analysis]:
        """
        Get all analyses for a user, ordered by creation date (newest first).

        Args:
            user_id: User UUID
            limit: Maximum number of analyses to return
            offset: Number of analyses to skip

        Returns:
            List of analyses
        """
        result = await self.session.execute(
            select(Analysis)
            .where(Analysis.user_id == user_id)
            .order_by(Analysis.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_resume_and_jd(
        self, resume_id: uuid.UUID, job_description_id: uuid.UUID
    ) -> Optional[Analysis]:
        """
        Get the most recent analysis for a specific resume-JD pair.

        Args:
            resume_id: Resume UUID
            job_description_id: Job Description UUID

        Returns:
            Most recent Analysis or None
        """
        result = await self.session.execute(
            select(Analysis)
            .where(
                and_(
                    Analysis.resume_id == resume_id,
                    Analysis.job_description_id == job_description_id,
                )
            )
            .order_by(Analysis.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_recent_analyses(
        self, user_id: uuid.UUID, days: int = 7, limit: int = 20
    ) -> List[Analysis]:
        """
        Get recent analyses within specified days.

        Args:
            user_id: User UUID
            days: Number of days to look back (default 7)
            limit: Maximum number of analyses to return

        Returns:
            List of recent analyses
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            select(Analysis)
            .where(
                and_(
                    Analysis.user_id == user_id, Analysis.created_at >= cutoff_date
                )
            )
            .order_by(Analysis.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_resume(
        self, resume_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> List[Analysis]:
        """
        Get all analyses for a specific resume.

        Args:
            resume_id: Resume UUID
            limit: Maximum number of analyses to return
            offset: Number of analyses to skip

        Returns:
            List of analyses
        """
        result = await self.session.execute(
            select(Analysis)
            .where(Analysis.resume_id == resume_id)
            .order_by(Analysis.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_high_match_analyses(
        self, user_id: uuid.UUID, min_match_score: float = 80.0, limit: int = 20
    ) -> List[Analysis]:
        """
        Get analyses with high match scores for a user.

        Args:
            user_id: User UUID
            min_match_score: Minimum match score threshold (default 80.0)
            limit: Maximum number of analyses to return

        Returns:
            List of high-scoring analyses
        """
        result = await self.session.execute(
            select(Analysis)
            .where(
                and_(
                    Analysis.user_id == user_id,
                    Analysis.match_score >= min_match_score,
                )
            )
            .order_by(Analysis.match_score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
