"""Webhook Model for Event Notifications

Allows users to subscribe to events and receive HTTP callbacks.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Boolean, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.user import User
    from backend.models.webhook_event import WebhookEvent


class WebhookEventType(str, Enum):
    """Types of webhook events"""
    # Resume events
    RESUME_CREATED = "resume.created"
    RESUME_UPDATED = "resume.updated"
    RESUME_DELETED = "resume.deleted"

    # Analysis events
    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_FAILED = "analysis.failed"

    # Generation events
    GENERATION_COMPLETED = "generation.completed"
    GENERATION_FAILED = "generation.failed"

    # Export events
    EXPORT_COMPLETED = "export.completed"
    EXPORT_FAILED = "export.failed"

    # User events
    USER_EMAIL_VERIFIED = "user.email_verified"
    USER_PASSWORD_CHANGED = "user.password_changed"


class Webhook(Base):
    """Webhook configuration for event notifications

    Allows users to subscribe to specific events and receive
    HTTP POST callbacks when those events occur.
    """
    __tablename__ = "webhooks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Webhook configuration
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Event subscriptions (JSON array of event types)
    events: Mapped[List[str]] = mapped_column(JSON, nullable=False)

    # Secret for HMAC signature verification
    secret: Mapped[str] = mapped_column(String(64), nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Delivery settings
    timeout_seconds: Mapped[int] = mapped_column(default=30, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)

    # Statistics
    total_deliveries: Mapped[int] = mapped_column(default=0, nullable=False)
    successful_deliveries: Mapped[int] = mapped_column(default=0, nullable=False)
    failed_deliveries: Mapped[int] = mapped_column(default=0, nullable=False)
    last_delivery_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="webhooks")
    events_log: Mapped[List["WebhookEvent"]] = relationship(
        "WebhookEvent",
        back_populates="webhook",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_webhook_user_active", "user_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Webhook(id={self.id}, user_id={self.user_id}, url={self.url}, active={self.is_active})>"

    @classmethod
    def create_webhook(
        cls,
        user_id: UUID,
        url: str,
        events: List[str],
        secret: str,
        description: Optional[str] = None,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ) -> "Webhook":
        """Create a new webhook

        Args:
            user_id: User ID
            url: Webhook URL
            events: List of event types to subscribe to
            secret: Secret for HMAC signature
            description: Optional description
            timeout_seconds: Request timeout in seconds
            max_retries: Maximum retry attempts

        Returns:
            Webhook instance
        """
        return cls(
            user_id=user_id,
            url=url,
            events=events,
            secret=secret,
            description=description,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    def update_statistics(
        self,
        success: bool,
        delivery_time: datetime,
    ) -> None:
        """Update webhook delivery statistics

        Args:
            success: Whether delivery was successful
            delivery_time: Time of delivery attempt
        """
        self.total_deliveries += 1
        self.last_delivery_at = delivery_time

        if success:
            self.successful_deliveries += 1
            self.last_success_at = delivery_time
        else:
            self.failed_deliveries += 1
            self.last_failure_at = delivery_time

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0-1)"""
        if self.total_deliveries == 0:
            return 0.0
        return self.successful_deliveries / self.total_deliveries

    def is_subscribed_to(self, event_type: WebhookEventType) -> bool:
        """Check if webhook is subscribed to an event type

        Args:
            event_type: Event type to check

        Returns:
            True if subscribed
        """
        return event_type.value in self.events
