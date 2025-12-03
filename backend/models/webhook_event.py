"""Webhook Event Model for Delivery Logging

Tracks webhook delivery attempts and their results.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Integer, Enum as SQLEnum, ForeignKey, Index, JSON, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base
from backend.models.webhook import WebhookEventType


class WebhookDeliveryStatus(str, Enum):
    """Webhook delivery status"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class WebhookEvent(Base):
    """Webhook event delivery log

    Records each webhook delivery attempt including
    request/response data and retry information.
    """
    __tablename__ = "webhook_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    webhook_id: Mapped[UUID] = mapped_column(
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Event details
    event_type: Mapped[WebhookEventType] = mapped_column(
        SQLEnum(WebhookEventType, name="webhook_event_type_enum"),
        nullable=False,
        index=True
    )
    event_id: Mapped[UUID] = mapped_column(nullable=False, index=True)  # ID of the related entity

    # Payload
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Delivery information
    status: Mapped[WebhookDeliveryStatus] = mapped_column(
        SQLEnum(WebhookDeliveryStatus, name="webhook_delivery_status_enum"),
        default=WebhookDeliveryStatus.PENDING,
        nullable=False,
        index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Response details
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Retry information
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    webhook: Mapped["Webhook"] = relationship("Webhook", back_populates="events_log")

    __table_args__ = (
        Index("idx_webhook_event_status", "webhook_id", "status"),
        Index("idx_webhook_event_created", "webhook_id", "created_at"),
        Index("idx_webhook_event_retry", "status", "next_retry_at"),
    )

    def __repr__(self) -> str:
        return f"<WebhookEvent(id={self.id}, webhook_id={self.webhook_id}, type={self.event_type}, status={self.status})>"

    @classmethod
    def create_event(
        cls,
        webhook_id: UUID,
        event_type: WebhookEventType,
        event_id: UUID,
        payload: dict,
        max_attempts: int = 3,
    ) -> "WebhookEvent":
        """Create a new webhook event

        Args:
            webhook_id: Webhook ID
            event_type: Type of event
            event_id: ID of the related entity
            payload: Event payload
            max_attempts: Maximum delivery attempts

        Returns:
            WebhookEvent instance
        """
        return cls(
            webhook_id=webhook_id,
            event_type=event_type,
            event_id=event_id,
            payload=payload,
            max_attempts=max_attempts,
            status=WebhookDeliveryStatus.PENDING,
        )

    def mark_attempt(
        self,
        success: bool,
        http_status: Optional[int] = None,
        response_body: Optional[str] = None,
        error_message: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        next_retry_at: Optional[datetime] = None,
    ) -> None:
        """Record a delivery attempt

        Args:
            success: Whether delivery was successful
            http_status: HTTP status code
            response_body: Response body (truncated)
            error_message: Error message if failed
            response_time_ms: Response time in milliseconds
            next_retry_at: Time of next retry (if applicable)
        """
        self.attempt_count += 1
        self.last_attempt_at = datetime.utcnow()
        self.http_status = http_status
        self.response_time_ms = response_time_ms

        # Truncate response body to 10KB
        if response_body and len(response_body) > 10000:
            self.response_body = response_body[:10000] + "... (truncated)"
        else:
            self.response_body = response_body

        # Truncate error message to 5KB
        if error_message and len(error_message) > 5000:
            self.error_message = error_message[:5000] + "... (truncated)"
        else:
            self.error_message = error_message

        if success:
            self.status = WebhookDeliveryStatus.SUCCESS
            self.completed_at = datetime.utcnow()
            self.next_retry_at = None
        elif self.attempt_count >= self.max_attempts:
            self.status = WebhookDeliveryStatus.FAILED
            self.completed_at = datetime.utcnow()
            self.next_retry_at = None
        else:
            self.status = WebhookDeliveryStatus.RETRYING
            self.next_retry_at = next_retry_at

    @property
    def is_pending(self) -> bool:
        """Check if event is pending delivery"""
        return self.status in (WebhookDeliveryStatus.PENDING, WebhookDeliveryStatus.RETRYING)

    @property
    def should_retry(self) -> bool:
        """Check if event should be retried"""
        return (
            self.status == WebhookDeliveryStatus.RETRYING
            and self.attempt_count < self.max_attempts
            and self.next_retry_at is not None
            and self.next_retry_at <= datetime.utcnow()
        )
