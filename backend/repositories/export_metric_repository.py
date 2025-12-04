"""Export Metric Repository

Handles data access for export metrics and template usage.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.export_metric import ExportMetric, ExportFormat
from backend.repositories.base_repository import BaseRepository


class ExportMetricRepository(BaseRepository[ExportMetric]):
    """Repository for ExportMetric model

    Provides methods for tracking and analyzing resume export operations,
    template usage, and export performance.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(ExportMetric, session)

    async def get_by_user(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ExportMetric]:
        """Get export metrics for a specific user

        Args:
            user_id: User ID
            limit: Maximum number of metrics to return
            offset: Offset for pagination

        Returns:
            List of ExportMetric objects
        """
        stmt = (
            select(ExportMetric)
            .where(ExportMetric.user_id == user_id)
            .order_by(desc(ExportMetric.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_template_usage(
        self,
        user_id: Optional[UUID] = None,
        days: Optional[int] = None,
    ) -> List[Dict]:
        """Get template usage statistics

        Args:
            user_id: Optional user ID filter
            days: Optional number of days to look back

        Returns:
            List of dictionaries with template usage counts
        """
        stmt = select(
            ExportMetric.template_name,
            func.count(ExportMetric.id).label('count'),
            func.sum(
                func.cast(ExportMetric.success, func.Integer())
            ).label('successful'),
        ).group_by(ExportMetric.template_name)

        conditions = []
        if user_id:
            conditions.append(ExportMetric.user_id == user_id)
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            conditions.append(ExportMetric.created_at >= since)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(desc('count'))

        result = await self.session.execute(stmt)

        return [
            {
                'template_name': row.template_name,
                'total_exports': row.count,
                'successful_exports': row.successful or 0,
                'success_rate': round((row.successful or 0) / row.count, 4),
            }
            for row in result
        ]

    async def get_format_usage(
        self,
        user_id: Optional[UUID] = None,
        days: Optional[int] = None,
    ) -> Dict[str, int]:
        """Get export format usage statistics

        Args:
            user_id: Optional user ID filter
            days: Optional number of days to look back

        Returns:
            Dictionary mapping format to count
        """
        stmt = select(
            ExportMetric.export_format,
            func.count(ExportMetric.id).label('count')
        ).group_by(ExportMetric.export_format)

        conditions = []
        if user_id:
            conditions.append(ExportMetric.user_id == user_id)
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            conditions.append(ExportMetric.created_at >= since)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return {row.export_format.value: row.count for row in result}

    async def get_cache_effectiveness(
        self,
        user_id: Optional[UUID] = None,
        days: Optional[int] = None,
    ) -> Dict:
        """Get export cache effectiveness statistics

        Args:
            user_id: Optional user ID filter
            days: Optional number of days to look back

        Returns:
            Dictionary with cache statistics
        """
        stmt = select(
            func.count(ExportMetric.id).label('total_exports'),
            func.sum(
                func.cast(ExportMetric.cached, func.Integer())
            ).label('cached_exports'),
            func.avg(
                func.case(
                    (ExportMetric.cached.is_(True), ExportMetric.generation_time_ms),
                    else_=None
                )
            ).label('avg_cached_time'),
            func.avg(
                func.case(
                    (ExportMetric.cached.is_(False), ExportMetric.generation_time_ms),
                    else_=None
                )
            ).label('avg_uncached_time'),
        )

        conditions = []
        if user_id:
            conditions.append(ExportMetric.user_id == user_id)
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            conditions.append(ExportMetric.created_at >= since)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        row = result.first()

        if not row or row.total_exports == 0:
            return {
                'total_exports': 0,
                'cached_exports': 0,
                'cache_hit_rate': 0.0,
                'avg_cached_time_ms': 0,
                'avg_uncached_time_ms': 0,
                'time_savings_ms': 0,
            }

        cached = row.cached_exports or 0
        avg_cached_time = int(row.avg_cached_time or 0)
        avg_uncached_time = int(row.avg_uncached_time or 0)

        return {
            'total_exports': row.total_exports,
            'cached_exports': cached,
            'cache_hit_rate': round(cached / row.total_exports, 4),
            'avg_cached_time_ms': avg_cached_time,
            'avg_uncached_time_ms': avg_uncached_time,
            'time_savings_ms': avg_uncached_time - avg_cached_time,
        }

    async def get_export_trends(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> List[Dict]:
        """Get export trends over time

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            List of dictionaries with daily export statistics
        """
        since = datetime.utcnow() - timedelta(days=days)

        stmt = select(
            func.date(ExportMetric.created_at).label('date'),
            func.count(ExportMetric.id).label('total_exports'),
            func.sum(
                func.cast(ExportMetric.cached, func.Integer())
            ).label('cached_exports'),
            func.avg(ExportMetric.generation_time_ms).label('avg_time'),
            func.sum(ExportMetric.file_size_bytes).label('total_size'),
        ).where(
            and_(
                ExportMetric.user_id == user_id,
                ExportMetric.created_at >= since,
            )
        ).group_by(
            func.date(ExportMetric.created_at)
        ).order_by(desc('date'))

        result = await self.session.execute(stmt)

        return [
            {
                'date': row.date.isoformat(),
                'total_exports': row.total_exports,
                'cached_exports': row.cached_exports or 0,
                'cache_rate': round((row.cached_exports or 0) / row.total_exports, 4),
                'avg_generation_time_ms': int(row.avg_time or 0),
                'total_size_mb': round((row.total_size or 0) / (1024 * 1024), 2),
            }
            for row in result
        ]

    async def get_file_size_stats(
        self,
        user_id: Optional[UUID] = None,
        export_format: Optional[ExportFormat] = None,
        days: Optional[int] = None,
    ) -> Dict:
        """Get file size statistics

        Args:
            user_id: Optional user ID filter
            export_format: Optional format filter
            days: Optional number of days to look back

        Returns:
            Dictionary with file size statistics
        """
        stmt = select(
            func.avg(ExportMetric.file_size_bytes).label('avg_size'),
            func.min(ExportMetric.file_size_bytes).label('min_size'),
            func.max(ExportMetric.file_size_bytes).label('max_size'),
            func.sum(ExportMetric.file_size_bytes).label('total_size'),
            func.count(ExportMetric.id).label('count'),
        )

        conditions = []
        if user_id:
            conditions.append(ExportMetric.user_id == user_id)
        if export_format:
            conditions.append(ExportMetric.export_format == export_format)
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            conditions.append(ExportMetric.created_at >= since)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        row = result.first()

        if not row or row.count == 0:
            return {
                'avg_size_kb': 0.0,
                'min_size_kb': 0.0,
                'max_size_kb': 0.0,
                'total_size_mb': 0.0,
                'count': 0,
            }

        return {
            'avg_size_kb': round((row.avg_size or 0) / 1024, 2),
            'min_size_kb': round((row.min_size or 0) / 1024, 2),
            'max_size_kb': round((row.max_size or 0) / 1024, 2),
            'total_size_mb': round((row.total_size or 0) / (1024 * 1024), 2),
            'count': row.count,
        }

    async def get_performance_by_template(
        self,
        days: Optional[int] = None,
    ) -> List[Dict]:
        """Get export performance statistics by template

        Args:
            days: Optional number of days to look back

        Returns:
            List of dictionaries with template performance metrics
        """
        stmt = select(
            ExportMetric.template_name,
            ExportMetric.export_format,
            func.count(ExportMetric.id).label('count'),
            func.avg(ExportMetric.generation_time_ms).label('avg_time'),
            func.avg(ExportMetric.file_size_bytes).label('avg_size'),
        ).group_by(
            ExportMetric.template_name,
            ExportMetric.export_format
        )

        if days:
            since = datetime.utcnow() - timedelta(days=days)
            stmt = stmt.where(ExportMetric.created_at >= since)

        stmt = stmt.order_by(ExportMetric.template_name, ExportMetric.export_format)

        result = await self.session.execute(stmt)

        return [
            {
                'template_name': row.template_name,
                'export_format': row.export_format.value,
                'count': row.count,
                'avg_generation_time_ms': int(row.avg_time or 0),
                'avg_file_size_kb': round((row.avg_size or 0) / 1024, 2),
            }
            for row in result
        ]
