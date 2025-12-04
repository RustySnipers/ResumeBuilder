"""Webhook Repository

Handles data access for webhook configurations.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.webhook import Webhook, WebhookEventType
from backend.repositories.base_repository import BaseRepository


class WebhookRepository(BaseRepository[Webhook]):
    """Repository for Webhook model

    Provides methods for managing webhook configurations
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Webhook, session)

    async def get_by_user(
        self,
        user_id: UUID,
        active_only: bool = False,
    ) -> List[Webhook]:
        """Get webhooks for a specific user

        Args:
            user_id: User ID
            active_only: Only return active webhooks

        Returns:
            List of Webhook objects
        """
        stmt = select(Webhook).where(Webhook.user_id == user_id)

        if active_only:
            stmt = stmt.where(Webhook.is_active.is_(True))

        stmt = stmt.order_by(Webhook.created_at.desc())

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user_and_id(
        self,
        user_id: UUID,
        webhook_id: UUID,
    ) -> Optional[Webhook]:
        """Get a specific webhook for a user

        Args:
            user_id: User ID
            webhook_id: Webhook ID

        Returns:
            Webhook object or None
        """
        stmt = select(Webhook).where(
            and_(
                Webhook.id == webhook_id,
                Webhook.user_id == user_id,
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_webhooks_for_event(
        self,
        event_type: WebhookEventType,
    ) -> List[Webhook]:
        """Get all active webhooks subscribed to an event type

        Args:
            event_type: Event type

        Returns:
            List of active Webhook objects
        """
        # Query all active webhooks
        stmt = select(Webhook).where(Webhook.is_active.is_(True))
        result = await self.session.execute(stmt)
        webhooks = list(result.scalars().all())

        # Filter by event subscription (JSON contains check)
        subscribed_webhooks = [
            webhook for webhook in webhooks
            if webhook.is_subscribed_to(event_type)
        ]

        return subscribed_webhooks

    async def get_active_webhooks_for_user_and_event(
        self,
        user_id: UUID,
        event_type: WebhookEventType,
    ) -> List[Webhook]:
        """Get active webhooks for a user subscribed to an event type

        Args:
            user_id: User ID
            event_type: Event type

        Returns:
            List of active Webhook objects
        """
        stmt = select(Webhook).where(
            and_(
                Webhook.user_id == user_id,
                Webhook.is_active.is_(True),
            )
        )

        result = await self.session.execute(stmt)
        webhooks = list(result.scalars().all())

        # Filter by event subscription
        subscribed_webhooks = [
            webhook for webhook in webhooks
            if webhook.is_subscribed_to(event_type)
        ]

        return subscribed_webhooks

    async def update_statistics(
        self,
        webhook_id: UUID,
        success: bool,
        delivery_time: datetime,
    ) -> Optional[Webhook]:
        """Update webhook delivery statistics

        Args:
            webhook_id: Webhook ID
            success: Whether delivery was successful
            delivery_time: Time of delivery

        Returns:
            Updated Webhook object or None
        """
        webhook = await self.get_by_id(webhook_id)
        if not webhook:
            return None

        webhook.update_statistics(success=success, delivery_time=delivery_time)
        await self.session.flush()
        return webhook

    async def deactivate_webhook(
        self,
        webhook_id: UUID,
    ) -> Optional[Webhook]:
        """Deactivate a webhook

        Args:
            webhook_id: Webhook ID

        Returns:
            Updated Webhook object or None
        """
        webhook = await self.get_by_id(webhook_id)
        if not webhook:
            return None

        webhook.is_active = False
        await self.session.flush()
        return webhook

    async def activate_webhook(
        self,
        webhook_id: UUID,
    ) -> Optional[Webhook]:
        """Activate a webhook

        Args:
            webhook_id: Webhook ID

        Returns:
            Updated Webhook object or None
        """
        webhook = await self.get_by_id(webhook_id)
        if not webhook:
            return None

        webhook.is_active = True
        await self.session.flush()
        return webhook
