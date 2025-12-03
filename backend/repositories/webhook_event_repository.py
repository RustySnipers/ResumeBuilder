"""Webhook Event Repository

Handles data access for webhook delivery events.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.webhook_event import WebhookEvent, WebhookDeliveryStatus
from backend.models.webhook import WebhookEventType
from backend.repositories.base_repository import BaseRepository


class WebhookEventRepository(BaseRepository[WebhookEvent]):
    """Repository for WebhookEvent model

    Provides methods for managing webhook delivery events
    """

    def __init__(self, session: AsyncSession):
        super().__init__(WebhookEvent, session)

    async def get_by_webhook(
        self,
        webhook_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WebhookEvent]:
        """Get events for a specific webhook

        Args:
            webhook_id: Webhook ID
            limit: Maximum number of events to return
            offset: Offset for pagination

        Returns:
            List of WebhookEvent objects
        """
        stmt = (
            select(WebhookEvent)
            .where(WebhookEvent.webhook_id == webhook_id)
            .order_by(desc(WebhookEvent.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_events(
        self,
        limit: int = 100,
    ) -> List[WebhookEvent]:
        """Get pending webhook events that need to be delivered

        Args:
            limit: Maximum number of events to return

        Returns:
            List of pending WebhookEvent objects
        """
        stmt = (
            select(WebhookEvent)
            .where(WebhookEvent.status == WebhookDeliveryStatus.PENDING)
            .order_by(WebhookEvent.created_at)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_events_for_retry(
        self,
        limit: int = 100,
    ) -> List[WebhookEvent]:
        """Get events that need to be retried

        Args:
            limit: Maximum number of events to return

        Returns:
            List of WebhookEvent objects ready for retry
        """
        now = datetime.utcnow()

        stmt = (
            select(WebhookEvent)
            .where(
                and_(
                    WebhookEvent.status == WebhookDeliveryStatus.RETRYING,
                    WebhookEvent.next_retry_at <= now,
                    WebhookEvent.attempt_count < WebhookEvent.max_attempts,
                )
            )
            .order_by(WebhookEvent.next_retry_at)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_event_id(
        self,
        event_id: UUID,
        event_type: Optional[WebhookEventType] = None,
    ) -> List[WebhookEvent]:
        """Get webhook events for a specific entity

        Args:
            event_id: Entity ID (resume, analysis, export, etc.)
            event_type: Optional event type filter

        Returns:
            List of WebhookEvent objects
        """
        conditions = [WebhookEvent.event_id == event_id]

        if event_type:
            conditions.append(WebhookEvent.event_type == event_type)

        stmt = (
            select(WebhookEvent)
            .where(and_(*conditions))
            .order_by(desc(WebhookEvent.created_at))
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_failures(
        self,
        webhook_id: UUID,
        hours: int = 24,
    ) -> List[WebhookEvent]:
        """Get recent failed events for a webhook

        Args:
            webhook_id: Webhook ID
            hours: Number of hours to look back

        Returns:
            List of failed WebhookEvent objects
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        stmt = (
            select(WebhookEvent)
            .where(
                and_(
                    WebhookEvent.webhook_id == webhook_id,
                    WebhookEvent.status == WebhookDeliveryStatus.FAILED,
                    WebhookEvent.created_at >= since,
                )
            )
            .order_by(desc(WebhookEvent.created_at))
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_attempt(
        self,
        event_id: UUID,
        success: bool,
        http_status: Optional[int] = None,
        response_body: Optional[str] = None,
        error_message: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        next_retry_at: Optional[datetime] = None,
    ) -> Optional[WebhookEvent]:
        """Mark a delivery attempt for an event

        Args:
            event_id: Event ID
            success: Whether delivery was successful
            http_status: HTTP status code
            response_body: Response body
            error_message: Error message if failed
            response_time_ms: Response time in milliseconds
            next_retry_at: Time of next retry

        Returns:
            Updated WebhookEvent or None
        """
        event = await self.get_by_id(event_id)
        if not event:
            return None

        event.mark_attempt(
            success=success,
            http_status=http_status,
            response_body=response_body,
            error_message=error_message,
            response_time_ms=response_time_ms,
            next_retry_at=next_retry_at,
        )

        await self.session.flush()
        return event

    async def count_by_status(
        self,
        webhook_id: UUID,
    ) -> dict:
        """Count events by status for a webhook

        Args:
            webhook_id: Webhook ID

        Returns:
            Dictionary with counts by status
        """
        events = await self.get_by_webhook(webhook_id, limit=10000)

        counts = {
            "pending": 0,
            "success": 0,
            "failed": 0,
            "retrying": 0,
        }

        for event in events:
            counts[event.status.value] += 1

        return counts

    async def cleanup_old_events(
        self,
        days: int = 30,
        batch_size: int = 1000,
    ) -> int:
        """Delete old completed webhook events

        Args:
            days: Number of days to keep
            batch_size: Batch size for deletion

        Returns:
            Number of events deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(WebhookEvent)
            .where(
                and_(
                    WebhookEvent.completed_at < cutoff_date,
                    WebhookEvent.status.in_([
                        WebhookDeliveryStatus.SUCCESS,
                        WebhookDeliveryStatus.FAILED,
                    ]),
                )
            )
            .limit(batch_size)
        )

        result = await self.session.execute(stmt)
        events = list(result.scalars().all())

        for event in events:
            await self.session.delete(event)

        await self.session.flush()

        return len(events)
