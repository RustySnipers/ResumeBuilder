"""Daily Metrics Model for Aggregated Analytics

Stores pre-aggregated daily statistics for fast dashboard queries.
"""
from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Date, Integer, Float, String, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class DailyMetric(Base):
    """Daily aggregated metrics for analytics dashboard

    Stores pre-computed daily statistics to avoid expensive
    aggregation queries on large datasets.

    Metrics are computed daily via a background job.
    """
    __tablename__ = "daily_metrics"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # User activity counts
    total_activities: Mapped[int] = mapped_column(Integer, default=0)
    login_count: Mapped[int] = mapped_column(Integer, default=0)
    api_request_count: Mapped[int] = mapped_column(Integer, default=0)

    # Resume operations
    resumes_created: Mapped[int] = mapped_column(Integer, default=0)
    resumes_updated: Mapped[int] = mapped_column(Integer, default=0)
    resumes_analyzed: Mapped[int] = mapped_column(Integer, default=0)

    # Analysis metrics
    total_analyses: Mapped[int] = mapped_column(Integer, default=0)
    avg_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    successful_analyses: Mapped[int] = mapped_column(Integer, default=0)  # match_score >= 70

    # Export metrics
    total_exports: Mapped[int] = mapped_column(Integer, default=0)
    pdf_exports: Mapped[int] = mapped_column(Integer, default=0)
    docx_exports: Mapped[int] = mapped_column(Integer, default=0)
    html_exports: Mapped[int] = mapped_column(Integer, default=0)
    cached_exports: Mapped[int] = mapped_column(Integer, default=0)
    total_export_size_mb: Mapped[float] = mapped_column(Float, default=0.0)

    # LLM metrics
    llm_requests: Mapped[int] = mapped_column(Integer, default=0)
    llm_cached_requests: Mapped[int] = mapped_column(Integer, default=0)
    total_llm_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_llm_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Performance metrics
    avg_analysis_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_export_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Template usage (JSON for flexibility)
    template_usage: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Template usage counts: {'professional': 10, 'modern': 5, ...}"
    )

    # Additional metrics
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

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
    user: Mapped[Optional["User"]] = relationship("User", back_populates="daily_metrics")

    __table_args__ = (
        # Composite indexes for queries
        Index("idx_user_date", "user_id", "metric_date", unique=True),
        Index("idx_date_only", "metric_date"),
    )

    def __repr__(self) -> str:
        user_str = f"user_id={self.user_id}" if self.user_id else "global"
        return f"<DailyMetric({user_str}, date={self.metric_date})>"

    @classmethod
    def create_metric(
        cls,
        metric_date: date,
        user_id: Optional[UUID] = None,
    ) -> "DailyMetric":
        """Create new daily metric record

        Args:
            metric_date: Date for metrics
            user_id: User ID (None for global metrics)

        Returns:
            DailyMetric instance
        """
        return cls(
            user_id=user_id,
            metric_date=metric_date,
            template_usage={},
            metadata={},
        )

    @property
    def export_cache_rate(self) -> float:
        """Calculate export cache hit rate (0-1)"""
        if self.total_exports == 0:
            return 0.0
        return self.cached_exports / self.total_exports

    @property
    def llm_cache_rate(self) -> float:
        """Calculate LLM cache hit rate (0-1)"""
        if self.llm_requests == 0:
            return 0.0
        return self.llm_cached_requests / self.llm_requests

    @property
    def success_rate(self) -> float:
        """Calculate analysis success rate (0-1)"""
        if self.total_analyses == 0:
            return 0.0
        return self.successful_analyses / self.total_analyses

    @property
    def avg_llm_cost(self) -> float:
        """Calculate average LLM cost per request"""
        if self.llm_requests == 0:
            return 0.0
        return self.total_llm_cost / self.llm_requests
