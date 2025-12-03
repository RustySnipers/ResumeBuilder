"""Analysis Metrics Model for Tracking Resume Analysis Results

Stores analysis results over time for trend analysis and success tracking.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, Integer, String, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class AnalysisMetric(Base):
    """Analysis metrics for tracking resume optimization results

    Stores key metrics from resume analysis to enable:
    - Match score trends over time
    - Success rate tracking
    - Keyword effectiveness analysis
    - Performance monitoring
    """
    __tablename__ = "analysis_metrics"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    analysis_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    resume_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    job_description_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="SET NULL"),
        nullable=True
    )

    # Match score metrics
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    semantic_similarity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Keyword metrics
    keyword_count: Mapped[int] = mapped_column(Integer, default=0)
    matched_keywords: Mapped[int] = mapped_column(Integer, default=0)
    missing_keywords: Mapped[int] = mapped_column(Integer, default=0)

    # Gap analysis
    gap_count: Mapped[int] = mapped_column(Integer, default=0)

    # Performance metrics
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # LLM metrics (if AI optimization was used)
    llm_used: Mapped[bool] = mapped_column(default=False)
    llm_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    llm_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_cached: Mapped[bool] = mapped_column(default=False)

    # Additional metrics
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="analysis_metrics")
    analysis: Mapped[Optional["Analysis"]] = relationship("Analysis")

    __table_args__ = (
        # Composite indexes for trend queries
        Index("idx_user_created_match", "user_id", "created_at", "match_score"),
        Index("idx_created_match_score", "created_at", "match_score"),
    )

    def __repr__(self) -> str:
        return f"<AnalysisMetric(id={self.id}, user_id={self.user_id}, match_score={self.match_score}, created_at={self.created_at})>"

    @classmethod
    def create_from_analysis(
        cls,
        user_id: UUID,
        analysis_id: UUID,
        resume_id: Optional[UUID],
        job_description_id: Optional[UUID],
        match_score: float,
        semantic_similarity: Optional[float],
        keyword_count: int,
        matched_keywords: int,
        missing_keywords: int,
        gap_count: int,
        processing_time_ms: int,
        llm_used: bool = False,
        llm_cost: Optional[float] = None,
        llm_tokens: Optional[int] = None,
        llm_cached: bool = False,
        metadata: Optional[dict] = None,
    ) -> "AnalysisMetric":
        """Create analysis metric from analysis results

        Args:
            user_id: User ID
            analysis_id: Analysis ID
            resume_id: Resume ID
            job_description_id: Job description ID
            match_score: Overall match score (0-100)
            semantic_similarity: Semantic similarity score (0-1)
            keyword_count: Total keywords in job description
            matched_keywords: Number of matched keywords
            missing_keywords: Number of missing keywords
            gap_count: Number of gaps identified
            processing_time_ms: Processing time in milliseconds
            llm_used: Whether LLM was used
            llm_cost: LLM cost in dollars
            llm_tokens: LLM tokens used
            llm_cached: Whether LLM response was cached
            metadata: Additional metadata

        Returns:
            AnalysisMetric instance
        """
        return cls(
            user_id=user_id,
            analysis_id=analysis_id,
            resume_id=resume_id,
            job_description_id=job_description_id,
            match_score=match_score,
            semantic_similarity=semantic_similarity,
            keyword_count=keyword_count,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            gap_count=gap_count,
            processing_time_ms=processing_time_ms,
            llm_used=llm_used,
            llm_cost=llm_cost,
            llm_tokens=llm_tokens,
            llm_cached=llm_cached,
            metadata=metadata or {},
        )

    @property
    def keyword_match_rate(self) -> float:
        """Calculate keyword match rate (0-1)"""
        if self.keyword_count == 0:
            return 0.0
        return self.matched_keywords / self.keyword_count

    @property
    def is_successful(self) -> bool:
        """Determine if analysis is considered successful (>70% match)"""
        return self.match_score >= 70.0
