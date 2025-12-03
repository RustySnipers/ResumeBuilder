"""User Activity Repository for Analytics

Handles data access for user activity tracking.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user_activity import UserActivity, ActivityType
from backend.repositories.base_repository import BaseRepository


class UserActivityRepository(BaseRepository[UserActivity]):
    """Repository for UserActivity model

    Provides methods for tracking and querying user activities
    for analytics and audit purposes.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(UserActivity, session)

    async def get_by_user(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[UserActivity]:
        """Get activities for a specific user

        Args:
            user_id: User ID
            limit: Maximum number of activities to return
            offset: Offset for pagination

        Returns:
            List of UserActivity objects
        """
        stmt = (
            select(UserActivity)
            .where(UserActivity.user_id == user_id)
            .order_by(desc(UserActivity.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_type(
        self,
        activity_type: ActivityType,
        limit: int = 100,
        offset: int = 0,
    ) -> List[UserActivity]:
        """Get activities by type

        Args:
            activity_type: Activity type to filter by
            limit: Maximum number of activities to return
            offset: Offset for pagination

        Returns:
            List of UserActivity objects
        """
        stmt = (
            select(UserActivity)
            .where(UserActivity.activity_type == activity_type)
            .order_by(desc(UserActivity.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user_and_type(
        self,
        user_id: UUID,
        activity_type: ActivityType,
        limit: int = 100,
        offset: int = 0,
    ) -> List[UserActivity]:
        """Get activities for a user by type

        Args:
            user_id: User ID
            activity_type: Activity type to filter by
            limit: Maximum number of activities to return
            offset: Offset for pagination

        Returns:
            List of UserActivity objects
        """
        stmt = (
            select(UserActivity)
            .where(
                and_(
                    UserActivity.user_id == user_id,
                    UserActivity.activity_type == activity_type,
                )
            )
            .order_by(desc(UserActivity.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_activities(
        self,
        user_id: Optional[UUID] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[UserActivity]:
        """Get recent activities

        Args:
            user_id: Optional user ID filter
            hours: Number of hours to look back
            limit: Maximum number of activities to return

        Returns:
            List of UserActivity objects
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        stmt = (
            select(UserActivity)
            .where(UserActivity.created_at >= since)
            .order_by(desc(UserActivity.created_at))
            .limit(limit)
        )

        if user_id:
            stmt = stmt.where(UserActivity.user_id == user_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_type(
        self,
        user_id: Optional[UUID] = None,
        since: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Count activities by type

        Args:
            user_id: Optional user ID filter
            since: Optional start date filter

        Returns:
            Dictionary mapping activity type to count
        """
        stmt = select(
            UserActivity.activity_type,
            func.count(UserActivity.id).label('count')
        ).group_by(UserActivity.activity_type)

        if user_id:
            stmt = stmt.where(UserActivity.user_id == user_id)

        if since:
            stmt = stmt.where(UserActivity.created_at >= since)

        result = await self.session.execute(stmt)
        return {row.activity_type.value: row.count for row in result}

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
            Dictionary with daily activity counts by type
        """
        since = datetime.utcnow() - timedelta(days=days)

        stmt = select(
            func.date(UserActivity.created_at).label('date'),
            UserActivity.activity_type,
            func.count(UserActivity.id).label('count')
        ).where(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.created_at >= since,
            )
        ).group_by(
            func.date(UserActivity.created_at),
            UserActivity.activity_type
        ).order_by(desc('date'))

        result = await self.session.execute(stmt)

        # Group by date
        timeline: Dict[str, List[Dict]] = {}
        for row in result:
            date_str = row.date.isoformat()
            if date_str not in timeline:
                timeline[date_str] = []
            timeline[date_str].append({
                'activity_type': row.activity_type.value,
                'count': row.count
            })

        return timeline

    async def get_average_response_time(
        self,
        endpoint: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> Optional[float]:
        """Get average response time for activities

        Args:
            endpoint: Optional endpoint filter
            since: Optional start date filter

        Returns:
            Average response time in milliseconds, or None if no data
        """
        stmt = select(func.avg(UserActivity.response_time_ms))

        conditions = []
        if endpoint:
            conditions.append(UserActivity.endpoint == endpoint)
        if since:
            conditions.append(UserActivity.created_at >= since)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return result.scalar()

    async def create_activity(
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
    ) -> UserActivity:
        """Create a new activity record

        Args:
            activity_type: Type of activity
            user_id: User ID (optional for anonymous activities)
            description: Human-readable description
            ip_address: IP address of request
            user_agent: User agent string
            endpoint: API endpoint path
            method: HTTP method
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            metadata: Additional context as JSON

        Returns:
            Created UserActivity instance
        """
        activity = UserActivity.create_activity(
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
        self.session.add(activity)
        return activity
