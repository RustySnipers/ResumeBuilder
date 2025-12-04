"""Export Metrics Model for Tracking Resume Export Operations

Tracks export operations for analytics and optimization.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Enum as SQLEnum, ForeignKey, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.user import User


class ExportFormat(str, Enum):
    """Export format types"""
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"


class ExportMetric(Base):
    """Export metrics for tracking resume export operations

    Stores metrics from export operations to enable:
    - Template usage analysis
    - Export performance monitoring
    - File size tracking
    - Cache effectiveness
    - User preferences analysis
    """
    __tablename__ = "export_metrics"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    resume_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    generated_resume_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("generated_resumes.id", ondelete="SET NULL"),
        nullable=True
    )

    # Export details
    export_format: Mapped[ExportFormat] = mapped_column(
        SQLEnum(ExportFormat, name="export_format_enum"),
        nullable=False,
        index=True
    )
    template_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # File metrics
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Performance metrics
    generation_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    cached: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Success tracking
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Request metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="export_metrics")

    __table_args__ = (
        # Composite indexes for analytics queries
        Index("idx_user_format_created", "user_id", "export_format", "created_at"),
        Index("idx_template_created", "template_name", "created_at"),
        Index("idx_format_created", "export_format", "created_at"),
        Index("idx_created_success", "created_at", "success"),
    )

    def __repr__(self) -> str:
        return f"<ExportMetric(id={self.id}, user_id={self.user_id}, format={self.export_format}, template={self.template_name}, created_at={self.created_at})>"

    @classmethod
    def create_export_metric(
        cls,
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
    ) -> "ExportMetric":
        """Create export metric record

        Args:
            user_id: User ID
            export_format: Export format (PDF, DOCX, HTML)
            template_name: Template used
            file_size_bytes: File size in bytes
            generation_time_ms: Generation time in milliseconds
            resume_id: Resume ID (optional)
            generated_resume_id: Generated resume ID (optional)
            page_count: Number of pages (optional)
            cached: Whether result was cached
            success: Whether export was successful
            error_message: Error message if failed
            ip_address: IP address of request
            user_agent: User agent string

        Returns:
            ExportMetric instance
        """
        return cls(
            user_id=user_id,
            resume_id=resume_id,
            generated_resume_id=generated_resume_id,
            export_format=export_format,
            template_name=template_name,
            file_size_bytes=file_size_bytes,
            page_count=page_count,
            generation_time_ms=generation_time_ms,
            cached=cached,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @property
    def file_size_kb(self) -> float:
        """Get file size in kilobytes"""
        return self.file_size_bytes / 1024

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes"""
        return self.file_size_bytes / (1024 * 1024)

    @property
    def generation_time_s(self) -> float:
        """Get generation time in seconds"""
        return self.generation_time_ms / 1000
