"""Daily Metric Repository

Handles data access for aggregated daily analytics.
"""
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.daily_metric import DailyMetric
from backend.repositories.base_repository import BaseRepository


class DailyMetricRepository(BaseRepository[DailyMetric]):
    """Repository for DailyMetric model

    Provides methods for managing and querying pre-aggregated daily statistics.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(DailyMetric, session)

    async def get_or_create_daily_metric(
        self,
        metric_date: date,
        user_id: Optional[UUID] = None,
    ) -> DailyMetric:
        """Get or create a daily metric record

        Args:
            metric_date: Date for metrics
            user_id: User ID (None for global metrics)

        Returns:
            DailyMetric instance
        """
        stmt = select(DailyMetric).where(
            and_(
                DailyMetric.metric_date == metric_date,
                DailyMetric.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        metric = result.scalar_one_or_none()

        if not metric:
            metric = DailyMetric.create_metric(
                metric_date=metric_date,
                user_id=user_id,
            )
            self.session.add(metric)
            await self.session.flush()

        return metric

    async def get_by_user(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> List[DailyMetric]:
        """Get daily metrics for a specific user

        Args:
            user_id: User ID
            days: Number of days to retrieve

        Returns:
            List of DailyMetric objects
        """
        since = date.today() - timedelta(days=days)

        stmt = (
            select(DailyMetric)
            .where(
                and_(
                    DailyMetric.user_id == user_id,
                    DailyMetric.metric_date >= since,
                )
            )
            .order_by(desc(DailyMetric.metric_date))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_global_metrics(
        self,
        days: int = 30,
    ) -> List[DailyMetric]:
        """Get global (system-wide) daily metrics

        Args:
            days: Number of days to retrieve

        Returns:
            List of DailyMetric objects for global metrics
        """
        since = date.today() - timedelta(days=days)

        stmt = (
            select(DailyMetric)
            .where(
                and_(
                    DailyMetric.user_id.is_(None),
                    DailyMetric.metric_date >= since,
                )
            )
            .order_by(desc(DailyMetric.metric_date))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_date_range(
        self,
        start_date: date,
        end_date: date,
        user_id: Optional[UUID] = None,
    ) -> List[DailyMetric]:
        """Get daily metrics for a date range

        Args:
            start_date: Start date
            end_date: End date
            user_id: Optional user ID filter (None for global)

        Returns:
            List of DailyMetric objects
        """
        conditions = [
            DailyMetric.metric_date >= start_date,
            DailyMetric.metric_date <= end_date,
        ]

        if user_id is not None:
            conditions.append(DailyMetric.user_id == user_id)
        else:
            conditions.append(DailyMetric.user_id.is_(None))

        stmt = (
            select(DailyMetric)
            .where(and_(*conditions))
            .order_by(DailyMetric.metric_date)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_summary_stats(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> Dict:
        """Get summary statistics for a user

        Args:
            user_id: User ID
            days: Number of days to aggregate

        Returns:
            Dictionary with summary statistics
        """
        metrics = await self.get_by_user(user_id, days)

        if not metrics:
            return {
                'total_activities': 0,
                'total_analyses': 0,
                'avg_match_score': 0.0,
                'total_exports': 0,
                'total_llm_cost': 0.0,
                'success_rate': 0.0,
                'cache_rate': 0.0,
            }

        total_activities = sum(m.total_activities for m in metrics)
        total_analyses = sum(m.total_analyses for m in metrics)
        total_exports = sum(m.total_exports for m in metrics)
        total_llm_cost = sum(m.total_llm_cost for m in metrics)

        # Calculate weighted average match score
        total_match_score_sum = sum(
            (m.avg_match_score or 0) * m.total_analyses
            for m in metrics
            if m.avg_match_score is not None
        )
        avg_match_score = (
            total_match_score_sum / total_analyses
            if total_analyses > 0
            else 0.0
        )

        # Calculate success rate
        total_successful = sum(m.successful_analyses for m in metrics)
        success_rate = (
            total_successful / total_analyses
            if total_analyses > 0
            else 0.0
        )

        # Calculate cache rates
        total_cached_exports = sum(m.cached_exports for m in metrics)
        export_cache_rate = (
            total_cached_exports / total_exports
            if total_exports > 0
            else 0.0
        )

        total_llm_requests = sum(m.llm_requests for m in metrics)
        total_llm_cached = sum(m.llm_cached_requests for m in metrics)
        llm_cache_rate = (
            total_llm_cached / total_llm_requests
            if total_llm_requests > 0
            else 0.0
        )

        return {
            'total_activities': total_activities,
            'total_analyses': total_analyses,
            'avg_match_score': round(avg_match_score, 2),
            'total_exports': total_exports,
            'total_llm_cost': round(total_llm_cost, 4),
            'success_rate': round(success_rate, 4),
            'export_cache_rate': round(export_cache_rate, 4),
            'llm_cache_rate': round(llm_cache_rate, 4),
        }

    async def get_template_usage_summary(
        self,
        user_id: Optional[UUID] = None,
        days: int = 30,
    ) -> Dict[str, int]:
        """Get template usage summary from daily metrics

        Args:
            user_id: Optional user ID filter
            days: Number of days to aggregate

        Returns:
            Dictionary mapping template name to total usage count
        """
        if user_id:
            metrics = await self.get_by_user(user_id, days)
        else:
            metrics = await self.get_global_metrics(days)

        template_totals: Dict[str, int] = {}

        for metric in metrics:
            if metric.template_usage:
                for template_name, count in metric.template_usage.items():
                    template_totals[template_name] = (
                        template_totals.get(template_name, 0) + count
                    )

        return template_totals
