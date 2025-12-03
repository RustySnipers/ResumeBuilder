"""Analysis Metric Repository

Handles data access for analysis metrics and trends.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.analysis_metric import AnalysisMetric
from backend.repositories.base_repository import BaseRepository


class AnalysisMetricRepository(BaseRepository[AnalysisMetric]):
    """Repository for AnalysisMetric model

    Provides methods for tracking and analyzing resume analysis metrics,
    match score trends, and success rates.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(AnalysisMetric, session)

    async def get_by_user(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AnalysisMetric]:
        """Get analysis metrics for a specific user

        Args:
            user_id: User ID
            limit: Maximum number of metrics to return
            offset: Offset for pagination

        Returns:
            List of AnalysisMetric objects
        """
        stmt = (
            select(AnalysisMetric)
            .where(AnalysisMetric.user_id == user_id)
            .order_by(desc(AnalysisMetric.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_match_score_trends(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> List[Dict]:
        """Get match score trends over time

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            List of dictionaries with date and average match score
        """
        since = datetime.utcnow() - timedelta(days=days)

        stmt = select(
            func.date(AnalysisMetric.created_at).label('date'),
            func.avg(AnalysisMetric.match_score).label('avg_match_score'),
            func.max(AnalysisMetric.match_score).label('max_match_score'),
            func.min(AnalysisMetric.match_score).label('min_match_score'),
            func.count(AnalysisMetric.id).label('count')
        ).where(
            and_(
                AnalysisMetric.user_id == user_id,
                AnalysisMetric.created_at >= since,
            )
        ).group_by(
            func.date(AnalysisMetric.created_at)
        ).order_by(desc('date'))

        result = await self.session.execute(stmt)

        return [
            {
                'date': row.date.isoformat(),
                'avg_match_score': round(row.avg_match_score, 2),
                'max_match_score': row.max_match_score,
                'min_match_score': row.min_match_score,
                'count': row.count,
            }
            for row in result
        ]

    async def get_success_rate(
        self,
        user_id: Optional[UUID] = None,
        days: Optional[int] = None,
    ) -> Dict[str, float]:
        """Get analysis success rate (match_score >= 70%)

        Args:
            user_id: Optional user ID filter
            days: Optional number of days to look back

        Returns:
            Dictionary with success rate and counts
        """
        stmt = select(
            func.count(AnalysisMetric.id).label('total'),
            func.sum(
                func.cast(AnalysisMetric.match_score >= 70.0, func.Integer())
            ).label('successful')
        )

        conditions = []
        if user_id:
            conditions.append(AnalysisMetric.user_id == user_id)
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            conditions.append(AnalysisMetric.created_at >= since)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        row = result.first()

        if not row or row.total == 0:
            return {'total': 0, 'successful': 0, 'success_rate': 0.0}

        return {
            'total': row.total,
            'successful': row.successful or 0,
            'success_rate': round((row.successful or 0) / row.total, 4),
        }

    async def get_keyword_stats(
        self,
        user_id: UUID,
        days: Optional[int] = None,
    ) -> Dict[str, float]:
        """Get keyword match statistics

        Args:
            user_id: User ID
            days: Optional number of days to look back

        Returns:
            Dictionary with keyword statistics
        """
        stmt = select(
            func.avg(AnalysisMetric.keyword_count).label('avg_total_keywords'),
            func.avg(AnalysisMetric.matched_keywords).label('avg_matched'),
            func.avg(AnalysisMetric.missing_keywords).label('avg_missing'),
        ).where(AnalysisMetric.user_id == user_id)

        if days:
            since = datetime.utcnow() - timedelta(days=days)
            stmt = stmt.where(AnalysisMetric.created_at >= since)

        result = await self.session.execute(stmt)
        row = result.first()

        if not row:
            return {
                'avg_total_keywords': 0.0,
                'avg_matched_keywords': 0.0,
                'avg_missing_keywords': 0.0,
                'avg_match_rate': 0.0,
            }

        avg_total = row.avg_total_keywords or 0.0
        avg_matched = row.avg_matched or 0.0

        return {
            'avg_total_keywords': round(avg_total, 2),
            'avg_matched_keywords': round(avg_matched, 2),
            'avg_missing_keywords': round(row.avg_missing or 0.0, 2),
            'avg_match_rate': round(avg_matched / avg_total, 4) if avg_total > 0 else 0.0,
        }

    async def get_llm_usage_stats(
        self,
        user_id: Optional[UUID] = None,
        days: Optional[int] = None,
    ) -> Dict:
        """Get LLM usage statistics

        Args:
            user_id: Optional user ID filter
            days: Optional number of days to look back

        Returns:
            Dictionary with LLM usage statistics
        """
        stmt = select(
            func.count(AnalysisMetric.id).label('total_analyses'),
            func.sum(
                func.cast(AnalysisMetric.llm_used, func.Integer())
            ).label('llm_analyses'),
            func.sum(
                func.cast(AnalysisMetric.llm_cached, func.Integer())
            ).label('cached_analyses'),
            func.sum(AnalysisMetric.llm_cost).label('total_cost'),
            func.sum(AnalysisMetric.llm_tokens).label('total_tokens'),
        )

        conditions = []
        if user_id:
            conditions.append(AnalysisMetric.user_id == user_id)
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            conditions.append(AnalysisMetric.created_at >= since)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        row = result.first()

        if not row or row.total_analyses == 0:
            return {
                'total_analyses': 0,
                'llm_analyses': 0,
                'cached_analyses': 0,
                'total_cost': 0.0,
                'total_tokens': 0,
                'cache_rate': 0.0,
                'avg_cost': 0.0,
            }

        llm_analyses = row.llm_analyses or 0
        cached = row.cached_analyses or 0

        return {
            'total_analyses': row.total_analyses,
            'llm_analyses': llm_analyses,
            'cached_analyses': cached,
            'total_cost': round(row.total_cost or 0.0, 4),
            'total_tokens': row.total_tokens or 0,
            'cache_rate': round(cached / llm_analyses, 4) if llm_analyses > 0 else 0.0,
            'avg_cost': round((row.total_cost or 0.0) / llm_analyses, 6) if llm_analyses > 0 else 0.0,
        }

    async def get_performance_stats(
        self,
        user_id: Optional[UUID] = None,
        days: Optional[int] = None,
    ) -> Dict:
        """Get processing performance statistics

        Args:
            user_id: Optional user ID filter
            days: Optional number of days to look back

        Returns:
            Dictionary with performance statistics
        """
        stmt = select(
            func.avg(AnalysisMetric.processing_time_ms).label('avg_time'),
            func.min(AnalysisMetric.processing_time_ms).label('min_time'),
            func.max(AnalysisMetric.processing_time_ms).label('max_time'),
        )

        conditions = []
        if user_id:
            conditions.append(AnalysisMetric.user_id == user_id)
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            conditions.append(AnalysisMetric.created_at >= since)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        row = result.first()

        if not row:
            return {'avg_time_ms': 0, 'min_time_ms': 0, 'max_time_ms': 0}

        return {
            'avg_time_ms': int(row.avg_time or 0),
            'min_time_ms': row.min_time or 0,
            'max_time_ms': row.max_time or 0,
        }
