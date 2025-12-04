"""Analytics Service

Main service for collecting and aggregating analytics data.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user_activity import ActivityType
from backend.models.export_metric import ExportFormat
from backend.repositories.user_activity_repository import UserActivityRepository
from backend.repositories.analysis_metric_repository import AnalysisMetricRepository
from backend.repositories.export_metric_repository import ExportMetricRepository
from backend.repositories.daily_metric_repository import DailyMetricRepository


class AnalyticsService:
    """Service for collecting and managing analytics data

    Provides methods for:
    - Tracking user activities
    - Recording analysis metrics
    - Recording export metrics
    - Aggregating daily statistics
    - Generating dashboard data
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.activity_repo = UserActivityRepository(session)
        self.analysis_repo = AnalysisMetricRepository(session)
        self.export_repo = ExportMetricRepository(session)
        self.daily_repo = DailyMetricRepository(session)

    # ===== User Activity Tracking =====

    async def track_activity(
        self,
        activity_type: ActivityType,
        user_id: Optional[UUID] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Track a user activity

        Args:
            activity_type: Type of activity
            user_id: User ID (optional)
            description: Description of activity
            ip_address: IP address
            user_agent: User agent string
            endpoint: API endpoint
            method: HTTP method
            status_code: HTTP status code
            response_time_ms: Response time in ms
            metadata: Additional metadata
        """
        await self.activity_repo.create_activity(
            activity_type=activity_type,
            user_id=user_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            metadata=metadata,
        )
        await self.session.commit()

    async def get_user_activities(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """Get recent activities for a user

        Args:
            user_id: User ID
            limit: Maximum activities to return
            offset: Pagination offset

        Returns:
            List of activity dictionaries
        """
        activities = await self.activity_repo.get_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

        return [
            {
                'id': str(activity.id),
                'activity_type': activity.activity_type.value,
                'description': activity.description,
                'endpoint': activity.endpoint,
                'method': activity.method,
                'status_code': activity.status_code,
                'created_at': activity.created_at.isoformat(),
            }
            for activity in activities
        ]

    async def get_activity_timeline(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> Dict[str, List[Dict]]:
        """Get activity timeline for a user

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Timeline dictionary with daily activity counts
        """
        return await self.activity_repo.get_activity_timeline(
            user_id=user_id,
            days=days,
        )

    # ===== Analysis Metrics =====

    async def record_analysis_metric(
        self,
        user_id: UUID,
        analysis_id: UUID,
        resume_id: Optional[UUID],
        job_description_id: Optional[UUID],
        match_score: float,
        semantic_similarity: Optional[float],
        keyword_count: int,
        matched_keywords: int,
        missing_keywords: int,
        gap_count: int,
        processing_time_ms: int,
        llm_used: bool = False,
        llm_cost: Optional[float] = None,
        llm_tokens: Optional[int] = None,
        llm_cached: bool = False,
        metadata: Optional[dict] = None,
    ) -> None:
        """Record an analysis metric

        Args:
            user_id: User ID
            analysis_id: Analysis ID
            resume_id: Resume ID
            job_description_id: Job description ID
            match_score: Match score (0-100)
            semantic_similarity: Semantic similarity (0-1)
            keyword_count: Total keywords
            matched_keywords: Matched keywords
            missing_keywords: Missing keywords
            gap_count: Number of gaps
            processing_time_ms: Processing time in ms
            llm_used: Whether LLM was used
            llm_cost: LLM cost
            llm_tokens: LLM tokens used
            llm_cached: Whether LLM response was cached
            metadata: Additional metadata
        """
        from backend.models.analysis_metric import AnalysisMetric

        metric = AnalysisMetric.create_from_analysis(
            user_id=user_id,
            analysis_id=analysis_id,
            resume_id=resume_id,
            job_description_id=job_description_id,
            match_score=match_score,
            semantic_similarity=semantic_similarity,
            keyword_count=keyword_count,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            gap_count=gap_count,
            processing_time_ms=processing_time_ms,
            llm_used=llm_used,
            llm_cost=llm_cost,
            llm_tokens=llm_tokens,
            llm_cached=llm_cached,
            metadata=metadata,
        )
        self.session.add(metric)
        await self.session.commit()

    async def get_match_score_trends(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> List[Dict]:
        """Get match score trends for a user

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            List of trend data points
        """
        return await self.analysis_repo.get_match_score_trends(
            user_id=user_id,
            days=days,
        )

    async def get_success_rate(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> Dict:
        """Get success rate for user's analyses

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Success rate statistics
        """
        return await self.analysis_repo.get_success_rate(
            user_id=user_id,
            days=days,
        )

    # ===== Export Metrics =====

    async def record_export_metric(
        self,
        user_id: UUID,
        export_format: ExportFormat,
        template_name: str,
        file_size_bytes: int,
        generation_time_ms: int,
        resume_id: Optional[UUID] = None,
        generated_resume_id: Optional[UUID] = None,
        page_count: Optional[int] = None,
        cached: bool = False,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Record an export metric

        Args:
            user_id: User ID
            export_format: Export format
            template_name: Template name
            file_size_bytes: File size in bytes
            generation_time_ms: Generation time in ms
            resume_id: Resume ID
            generated_resume_id: Generated resume ID
            page_count: Page count
            cached: Whether cached
            success: Whether successful
            error_message: Error message if failed
            ip_address: IP address
            user_agent: User agent
        """
        from backend.models.export_metric import ExportMetric

        metric = ExportMetric.create_export_metric(
            user_id=user_id,
            export_format=export_format,
            template_name=template_name,
            file_size_bytes=file_size_bytes,
            generation_time_ms=generation_time_ms,
            resume_id=resume_id,
            generated_resume_id=generated_resume_id,
            page_count=page_count,
            cached=cached,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(metric)
        await self.session.commit()

    async def get_template_usage(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> List[Dict]:
        """Get template usage statistics

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Template usage statistics
        """
        return await self.export_repo.get_template_usage(
            user_id=user_id,
            days=days,
        )

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
            Export trend data
        """
        return await self.export_repo.get_export_trends(
            user_id=user_id,
            days=days,
        )

    # ===== Dashboard Statistics =====

    async def get_dashboard_stats(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> Dict:
        """Get comprehensive dashboard statistics

        Args:
            user_id: User ID
            days: Number of days to aggregate

        Returns:
            Dashboard statistics dictionary
        """
        # Get activity statistics
        activity_counts = await self.activity_repo.count_by_type(
            user_id=user_id,
            since=datetime.utcnow() - timedelta(days=days),
        )

        # Get analysis statistics
        success_rate_data = await self.analysis_repo.get_success_rate(
            user_id=user_id,
            days=days,
        )
        keyword_stats = await self.analysis_repo.get_keyword_stats(
            user_id=user_id,
            days=days,
        )
        llm_stats = await self.analysis_repo.get_llm_usage_stats(
            user_id=user_id,
            days=days,
        )
        analysis_perf = await self.analysis_repo.get_performance_stats(
            user_id=user_id,
            days=days,
        )

        # Get export statistics
        template_usage = await self.export_repo.get_template_usage(
            user_id=user_id,
            days=days,
        )
        format_usage = await self.export_repo.get_format_usage(
            user_id=user_id,
            days=days,
        )
        cache_effectiveness = await self.export_repo.get_cache_effectiveness(
            user_id=user_id,
            days=days,
        )

        return {
            'period_days': days,
            'activity_counts': activity_counts,
            'analysis': {
                'success_rate': success_rate_data,
                'keyword_stats': keyword_stats,
                'llm_usage': llm_stats,
                'performance': analysis_perf,
            },
            'exports': {
                'template_usage': template_usage,
                'format_usage': format_usage,
                'cache_effectiveness': cache_effectiveness,
            },
        }

    async def get_user_summary(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> Dict:
        """Get summary statistics from daily metrics

        Args:
            user_id: User ID
            days: Number of days to aggregate

        Returns:
            Summary statistics
        """
        return await self.daily_repo.get_summary_stats(
            user_id=user_id,
            days=days,
        )
