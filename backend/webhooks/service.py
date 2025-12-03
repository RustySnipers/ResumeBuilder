"""Webhook Service

Business logic for webhook management and event delivery.
"""
import hmac
import hashlib
import secrets
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.webhook import Webhook, WebhookEventType
from backend.models.webhook_event import WebhookEvent, WebhookDeliveryStatus
from backend.repositories.webhook_repository import WebhookRepository
from backend.repositories.webhook_event_repository import WebhookEventRepository


class WebhookService:
    """Service for webhook management and delivery

    Provides methods for:
    - Creating and managing webhooks
    - Triggering webhook events
    - Delivering webhooks with HMAC signatures
    - Handling retries with exponential backoff
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.webhook_repo = WebhookRepository(session)
        self.event_repo = WebhookEventRepository(session)

    # ===== Webhook Management =====

    async def create_webhook(
        self,
        user_id: UUID,
        url: str,
        events: List[str],
        description: Optional[str] = None,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ) -> Webhook:
        """Create a new webhook

        Args:
            user_id: User ID
            url: Webhook URL
            events: List of event types to subscribe to
            description: Optional description
            timeout_seconds: Request timeout
            max_retries: Maximum retry attempts

        Returns:
            Created Webhook
        """
        # Generate secure random secret for HMAC
        secret = secrets.token_urlsafe(32)

        webhook = Webhook.create_webhook(
            user_id=user_id,
            url=url,
            events=events,
            secret=secret,
            description=description,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

        self.session.add(webhook)
        await self.session.commit()
        await self.session.refresh(webhook)

        return webhook

    async def get_user_webhooks(
        self,
        user_id: UUID,
        active_only: bool = False,
    ) -> List[Webhook]:
        """Get webhooks for a user

        Args:
            user_id: User ID
            active_only: Only return active webhooks

        Returns:
            List of webhooks
        """
        return await self.webhook_repo.get_by_user(
            user_id=user_id,
            active_only=active_only,
        )

    async def get_webhook(
        self,
        user_id: UUID,
        webhook_id: UUID,
    ) -> Optional[Webhook]:
        """Get a specific webhook for a user

        Args:
            user_id: User ID
            webhook_id: Webhook ID

        Returns:
            Webhook or None
        """
        return await self.webhook_repo.get_by_user_and_id(
            user_id=user_id,
            webhook_id=webhook_id,
        )

    async def update_webhook(
        self,
        user_id: UUID,
        webhook_id: UUID,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> Optional[Webhook]:
        """Update a webhook

        Args:
            user_id: User ID
            webhook_id: Webhook ID
            url: New URL (optional)
            events: New event list (optional)
            description: New description (optional)
            is_active: New active status (optional)
            timeout_seconds: New timeout (optional)
            max_retries: New max retries (optional)

        Returns:
            Updated Webhook or None
        """
        webhook = await self.webhook_repo.get_by_user_and_id(user_id, webhook_id)
        if not webhook:
            return None

        if url is not None:
            webhook.url = url
        if events is not None:
            webhook.events = events
        if description is not None:
            webhook.description = description
        if is_active is not None:
            webhook.is_active = is_active
        if timeout_seconds is not None:
            webhook.timeout_seconds = timeout_seconds
        if max_retries is not None:
            webhook.max_retries = max_retries

        await self.session.commit()
        await self.session.refresh(webhook)

        return webhook

    async def delete_webhook(
        self,
        user_id: UUID,
        webhook_id: UUID,
    ) -> bool:
        """Delete a webhook

        Args:
            user_id: User ID
            webhook_id: Webhook ID

        Returns:
            True if deleted, False if not found
        """
        webhook = await self.webhook_repo.get_by_user_and_id(user_id, webhook_id)
        if not webhook:
            return False

        await self.session.delete(webhook)
        await self.session.commit()

        return True

    async def regenerate_secret(
        self,
        user_id: UUID,
        webhook_id: UUID,
    ) -> Optional[str]:
        """Regenerate webhook secret

        Args:
            user_id: User ID
            webhook_id: Webhook ID

        Returns:
            New secret or None
        """
        webhook = await self.webhook_repo.get_by_user_and_id(user_id, webhook_id)
        if not webhook:
            return None

        new_secret = secrets.token_urlsafe(32)
        webhook.secret = new_secret

        await self.session.commit()

        return new_secret

    # ===== Event Triggering =====

    async def trigger_event(
        self,
        event_type: WebhookEventType,
        event_id: UUID,
        payload: Dict[str, Any],
        user_id: Optional[UUID] = None,
    ) -> int:
        """Trigger a webhook event

        Creates webhook events for all active webhooks subscribed to this event type.
        Events are queued for delivery by a background worker.

        Args:
            event_type: Type of event
            event_id: ID of the entity (resume, analysis, etc.)
            payload: Event payload
            user_id: Optional user ID (if user-specific event)

        Returns:
            Number of webhook events created
        """
        # Find active webhooks subscribed to this event
        if user_id:
            webhooks = await self.webhook_repo.get_active_webhooks_for_user_and_event(
                user_id=user_id,
                event_type=event_type,
            )
        else:
            webhooks = await self.webhook_repo.get_active_webhooks_for_event(
                event_type=event_type,
            )

        # Create webhook events
        events_created = 0
        for webhook in webhooks:
            event = WebhookEvent.create_event(
                webhook_id=webhook.id,
                event_type=event_type,
                event_id=event_id,
                payload=payload,
                max_attempts=webhook.max_retries,
            )
            self.session.add(event)
            events_created += 1

        if events_created > 0:
            await self.session.commit()

        return events_created

    # ===== Event Delivery =====

    def generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature for webhook payload

        Args:
            payload: JSON payload as string
            secret: Webhook secret

        Returns:
            HMAC signature (hex)
        """
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    async def deliver_event(
        self,
        event: WebhookEvent,
        webhook: Webhook,
    ) -> bool:
        """Deliver a webhook event

        Args:
            event: WebhookEvent to deliver
            webhook: Webhook configuration

        Returns:
            True if successful, False otherwise
        """
        import json

        # Prepare payload
        payload_dict = {
            "event_id": str(event.id),
            "event_type": event.event_type.value,
            "entity_id": str(event.event_id),
            "timestamp": datetime.utcnow().isoformat(),
            "data": event.payload,
        }
        payload_json = json.dumps(payload_dict, separators=(',', ':'))

        # Generate HMAC signature
        signature = self.generate_signature(payload_json, webhook.secret)

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Event": event.event_type.value,
            "X-Webhook-Event-ID": str(event.id),
            "User-Agent": "ResumeBuilder-Webhooks/1.0",
        }

        # Attempt delivery
        start_time = time.time()
        success = False
        http_status = None
        response_body = None
        error_message = None

        try:
            async with httpx.AsyncClient(timeout=webhook.timeout_seconds) as client:
                response = await client.post(
                    webhook.url,
                    content=payload_json,
                    headers=headers,
                )

                http_status = response.status_code
                response_body = response.text[:10000]  # Truncate to 10KB

                # Consider 2xx status codes as success
                success = 200 <= http_status < 300

        except httpx.TimeoutException as e:
            error_message = f"Timeout after {webhook.timeout_seconds}s"
        except httpx.RequestError as e:
            error_message = f"Request error: {str(e)}"
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Calculate next retry time if needed
        next_retry_at = None
        if not success and event.attempt_count < event.max_attempts - 1:
            # Exponential backoff: 2^attempt_count minutes
            delay_minutes = 2 ** (event.attempt_count + 1)
            next_retry_at = datetime.utcnow() + timedelta(minutes=delay_minutes)

        # Mark attempt
        await self.event_repo.mark_attempt(
            event_id=event.id,
            success=success,
            http_status=http_status,
            response_body=response_body,
            error_message=error_message,
            response_time_ms=response_time_ms,
            next_retry_at=next_retry_at,
        )

        # Update webhook statistics
        await self.webhook_repo.update_statistics(
            webhook_id=webhook.id,
            success=success,
            delivery_time=datetime.utcnow(),
        )

        await self.session.commit()

        return success

    async def process_pending_events(self, limit: int = 100) -> int:
        """Process pending webhook events

        Args:
            limit: Maximum events to process

        Returns:
            Number of events processed
        """
        pending_events = await self.event_repo.get_pending_events(limit=limit)

        processed = 0
        for event in pending_events:
            webhook = await self.webhook_repo.get_by_id(event.webhook_id)
            if webhook and webhook.is_active:
                await self.deliver_event(event, webhook)
                processed += 1

        return processed

    async def process_retry_events(self, limit: int = 100) -> int:
        """Process events ready for retry

        Args:
            limit: Maximum events to process

        Returns:
            Number of events processed
        """
        retry_events = await self.event_repo.get_events_for_retry(limit=limit)

        processed = 0
        for event in retry_events:
            webhook = await self.webhook_repo.get_by_id(event.webhook_id)
            if webhook and webhook.is_active:
                await self.deliver_event(event, webhook)
                processed += 1

        return processed

    # ===== Event Management =====

    async def get_webhook_events(
        self,
        user_id: UUID,
        webhook_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Optional[List[WebhookEvent]]:
        """Get events for a webhook

        Args:
            user_id: User ID
            webhook_id: Webhook ID
            limit: Maximum events to return
            offset: Pagination offset

        Returns:
            List of events or None if webhook not found
        """
        # Verify webhook belongs to user
        webhook = await self.webhook_repo.get_by_user_and_id(user_id, webhook_id)
        if not webhook:
            return None

        return await self.event_repo.get_by_webhook(
            webhook_id=webhook_id,
            limit=limit,
            offset=offset,
        )

    async def get_event_statistics(
        self,
        user_id: UUID,
        webhook_id: UUID,
    ) -> Optional[Dict[str, int]]:
        """Get event statistics for a webhook

        Args:
            user_id: User ID
            webhook_id: Webhook ID

        Returns:
            Statistics dictionary or None
        """
        # Verify webhook belongs to user
        webhook = await self.webhook_repo.get_by_user_and_id(user_id, webhook_id)
        if not webhook:
            return None

        counts = await self.event_repo.count_by_status(webhook_id)

        return {
            **counts,
            "total": sum(counts.values()),
            "success_rate": (
                counts["success"] / sum(counts.values())
                if sum(counts.values()) > 0
                else 0.0
            ),
        }
