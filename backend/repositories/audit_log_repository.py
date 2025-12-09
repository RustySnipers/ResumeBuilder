"""
AuditLog Repository - Phase 4

Data access layer for audit log operations.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import uuid

from backend.repositories.base_repository import BaseRepository
from backend.models.audit_log import AuditLog


class AuditLogRepository(BaseRepository[AuditLog]):
    """
    Repository for audit log data access.

    Provides CRUD operations and audit log-specific queries.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    async def log_event(
        self,
        action: str,
        user_id: Optional[uuid.UUID] = None,
        resource: Optional[str] = None,
        resource_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        meta_data: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: Action performed (e.g., "login", "api_access")
            user_id: Optional user UUID
            resource: Optional resource type
            resource_id: Optional resource UUID
            ip_address: Optional IP address
            user_agent: Optional user agent string
            meta_data: Optional additional context

        Returns:
            Created AuditLog instance
        """
        return await self.create(
            action=action,
            user_id=user_id,
            resource=resource,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            meta_data=meta_data,
        )

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific user.

        Args:
            user_id: User UUID
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of AuditLog instances
        """
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_action(
        self,
        action: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific action.

        Args:
            action: Action name
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of AuditLog instances
        """
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_resource(
        self,
        resource: str,
        resource_id: Optional[uuid.UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific resource.

        Args:
            resource: Resource type
            resource_id: Optional specific resource UUID
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of AuditLog instances
        """
        query = select(AuditLog).where(AuditLog.resource == resource)

        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)

        query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_recent(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> List[AuditLog]:
        """
        Get recent audit logs.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of records

        Returns:
            List of AuditLog instances
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.created_at >= since)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_failed_login_attempts(
        self, user_id: uuid.UUID, hours: int = 1
    ) -> int:
        """
        Count failed login attempts for a user in recent hours.

        Args:
            user_id: User UUID
            hours: Number of hours to look back

        Returns:
            Number of failed login attempts
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        result = await self.session.execute(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.user_id == user_id,
                AuditLog.action == "failed_login",
                AuditLog.created_at >= since,
            )
        )
        return result.scalar() or 0

    async def cleanup_old_logs(self, days: int = 90) -> int:
        """
        Delete audit logs older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Number of logs deleted
        """
        from sqlalchemy import delete

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            delete(AuditLog).where(AuditLog.created_at < cutoff_date)
        )
        await self.session.flush()
        return result.rowcount

    async def get_action_statistics(
        self, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get statistics of actions performed in recent hours.

        Args:
            hours: Number of hours to analyze

        Returns:
            List of dicts with action and count
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        result = await self.session.execute(
            select(AuditLog.action, func.count().label("count"))
            .where(AuditLog.created_at >= since)
            .group_by(AuditLog.action)
            .order_by(func.count().desc())
        )

        return [
            {"action": row.action, "count": row.count} for row in result.all()
        ]
