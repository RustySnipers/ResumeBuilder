"""Analytics Router

API endpoints for analytics and dashboard data.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.analytics.service import AnalyticsService
from backend.analytics.schemas import (
    DashboardResponse,
    ActivityTimelineResponse,
    MatchScoreTrendsResponse,
    TemplateUsageResponse,
    ExportTrendsResponse,
    SuccessRateResponse,
    UserSummaryResponse,
)


router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    days: int = Query(30, ge=1, le=365, description="Number of days to aggregate"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get comprehensive dashboard statistics

    Returns analytics data for the authenticated user including:
    - Activity counts by type
    - Analysis statistics (success rate, keyword stats, LLM usage)
    - Export statistics (template usage, format usage, cache effectiveness)

    **Required Permissions:** Authenticated user

    Args:
        days: Number of days to aggregate (1-365)
        current_user: Authenticated user
        session: Database session

    Returns:
        DashboardResponse with comprehensive statistics
    """
    analytics_service = AnalyticsService(session)

    stats = await analytics_service.get_dashboard_stats(
        user_id=current_user.id,
        days=days,
    )

    return DashboardResponse(**stats)


@router.get("/activities", response_model=ActivityTimelineResponse)
async def get_activity_timeline(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get activity timeline for the authenticated user

    Returns a timeline of user activities grouped by date and type.

    **Required Permissions:** Authenticated user

    Args:
        days: Number of days to look back (1-365)
        current_user: Authenticated user
        session: Database session

    Returns:
        ActivityTimelineResponse with timeline data
    """
    analytics_service = AnalyticsService(session)

    timeline = await analytics_service.get_activity_timeline(
        user_id=current_user.id,
        days=days,
    )

    return ActivityTimelineResponse(
        user_id=current_user.id,
        days=days,
        timeline=timeline,
    )


@router.get("/match-scores", response_model=MatchScoreTrendsResponse)
async def get_match_score_trends(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get match score trends over time

    Returns daily match score statistics including averages, min, max, and counts.

    **Required Permissions:** Authenticated user

    Args:
        days: Number of days to look back (1-365)
        current_user: Authenticated user
        session: Database session

    Returns:
        MatchScoreTrendsResponse with trend data
    """
    analytics_service = AnalyticsService(session)

    trends = await analytics_service.get_match_score_trends(
        user_id=current_user.id,
        days=days,
    )

    return MatchScoreTrendsResponse(
        user_id=current_user.id,
        days=days,
        trends=trends,
    )


@router.get("/templates", response_model=TemplateUsageResponse)
async def get_template_usage(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get template usage statistics

    Returns statistics for resume template usage including total exports,
    successful exports, and success rates for each template.

    **Required Permissions:** Authenticated user

    Args:
        days: Number of days to look back (1-365)
        current_user: Authenticated user
        session: Database session

    Returns:
        TemplateUsageResponse with template statistics
    """
    analytics_service = AnalyticsService(session)

    usage = await analytics_service.get_template_usage(
        user_id=current_user.id,
        days=days,
    )

    return TemplateUsageResponse(
        user_id=current_user.id,
        days=days,
        templates=usage,
    )


@router.get("/exports", response_model=ExportTrendsResponse)
async def get_export_trends(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get export trends over time

    Returns daily export statistics including counts, cache rates,
    generation times, and total file sizes.

    **Required Permissions:** Authenticated user

    Args:
        days: Number of days to look back (1-365)
        current_user: Authenticated user
        session: Database session

    Returns:
        ExportTrendsResponse with export trend data
    """
    analytics_service = AnalyticsService(session)

    trends = await analytics_service.get_export_trends(
        user_id=current_user.id,
        days=days,
    )

    return ExportTrendsResponse(
        user_id=current_user.id,
        days=days,
        trends=trends,
    )


@router.get("/success-rate", response_model=SuccessRateResponse)
async def get_success_rate(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get analysis success rate

    Returns success rate for resume analyses (match score >= 70%).

    **Required Permissions:** Authenticated user

    Args:
        days: Number of days to look back (1-365)
        current_user: Authenticated user
        session: Database session

    Returns:
        SuccessRateResponse with success rate statistics
    """
    analytics_service = AnalyticsService(session)

    success_rate = await analytics_service.get_success_rate(
        user_id=current_user.id,
        days=days,
    )

    return SuccessRateResponse(
        user_id=current_user.id,
        days=days,
        **success_rate,
    )


@router.get("/summary", response_model=UserSummaryResponse)
async def get_user_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to aggregate"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get summary statistics from daily metrics

    Returns aggregated summary statistics for the user from pre-computed
    daily metrics. This is faster than the full dashboard endpoint.

    **Required Permissions:** Authenticated user

    Args:
        days: Number of days to aggregate (1-365)
        current_user: Authenticated user
        session: Database session

    Returns:
        UserSummaryResponse with summary statistics
    """
    analytics_service = AnalyticsService(session)

    summary = await analytics_service.get_user_summary(
        user_id=current_user.id,
        days=days,
    )

    return UserSummaryResponse(
        user_id=current_user.id,
        days=days,
        **summary,
    )
