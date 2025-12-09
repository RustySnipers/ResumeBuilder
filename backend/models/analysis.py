"""
Analysis Model - Phase 2.1

Represents gap analysis results between resumes and job descriptions.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Uuid as UUID, JSON as JSONB, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from backend.database import Base


class Analysis(Base):
    """
    Analysis model for storing gap analysis results.

    Attributes:
        id: Unique analysis identifier (UUID)
        user_id: Foreign key to User who requested the analysis
        resume_id: Foreign key to Resume being analyzed
        job_description_id: Foreign key to JobDescription being compared
        missing_keywords: JSON array of keywords missing from resume
        suggestions: JSON array of improvement suggestions
        match_score: Overall match score (0-100)
        semantic_similarity: Semantic similarity score (0-1)
        created_at: Timestamp of analysis creation

    Relationships:
        user: The user who requested this analysis
        resume: The resume being analyzed
        job_description: The job description being compared against
        generated_resumes: All resumes generated from this analysis
    """

    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id = Column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_description_id = Column(
        UUID(as_uuid=True),
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    missing_keywords = Column(JSONB, nullable=True)
    suggestions = Column(JSONB, nullable=True)
    match_score = Column(Numeric(5, 2), nullable=True)
    semantic_similarity = Column(Numeric(5, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="analyses")
    resume = relationship("Resume", back_populates="analyses")
    job_description = relationship("JobDescription", back_populates="analyses")
    generated_resumes = relationship(
        "GeneratedResume", back_populates="analysis", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Analysis(id={self.id}, match_score={self.match_score}, created_at={self.created_at})>"
