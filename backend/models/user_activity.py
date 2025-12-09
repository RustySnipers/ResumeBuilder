"""User Activity Model for Analytics Tracking

Tracks all user actions for analytics and audit purposes.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, JSON, Integer, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.user import User


class ActivityType(str, Enum):
    """Types of user activities tracked"""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFIED = "email_verified"

    # Resume Operations
    RESUME_CREATED = "resume_created"
    RESUME_UPDATED = "resume_updated"
    RESUME_DELETED = "resume_deleted"
    RESUME_ANALYZED = "resume_analyzed"

    # AI Generation
    GENERATION_STARTED = "generation_started"
    GENERATION_COMPLETED = "generation_completed"
    GENERATION_FAILED = "generation_failed"
    GENERATION_STREAM_STARTED = "generation_stream_started"

    # Export Operations
    EXPORT_PDF = "export_pdf"
    EXPORT_DOCX = "export_docx"
    EXPORT_HTML = "export_html"

    # Job Description
    JOB_DESCRIPTION_CREATED = "job_description_created"
    JOB_DESCRIPTION_UPDATED = "job_description_updated"
    JOB_DESCRIPTION_DELETED = "job_description_deleted"

    # API Usage
    API_REQUEST = "api_request"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"


class UserActivity(Base):
    """User activity tracking for analytics

    Records all significant user actions with metadata for analytics.
    Enables tracking of user behavior, feature usage, and success metrics.
    """
    __tablename__ = "user_activities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Activity details
    activity_type: Mapped[ActivityType] = mapped_column(
        SQLEnum(ActivityType, name="activity_type_enum"),
        nullable=False,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Request metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    endpoint: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Response metadata
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Additional context (JSON for flexibility)
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="activities")

    __table_args__ = (
        # Composite indexes for common queries
        Index("idx_user_activity_type", "user_id", "activity_type"),
        Index("idx_user_created_at", "user_id", "created_at"),
        Index("idx_activity_created_at", "activity_type", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<UserActivity(id={self.id}, user_id={self.user_id}, type={self.activity_type}, created_at={self.created_at})>"

    @classmethod
    def create_activity(
        cls,
        activity_type: ActivityType,
        user_id: Optional[UUID] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        meta_data: Optional[dict] = None,
    ) -> "UserActivity":
        """Create a new user activity record

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
            meta_data: Additional context as JSON

        Returns:
            UserActivity instance
        """
        return cls(
            activity_type=activity_type,
            user_id=user_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            meta_data=meta_data or {},
        )
