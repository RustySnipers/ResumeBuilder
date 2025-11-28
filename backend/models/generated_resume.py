"""
Generated Resume Model - Phase 2.1

Represents AI-generated optimized resumes.
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from backend.database import Base


class GeneratedResume(Base):
    """
    Generated Resume model for storing LLM-optimized resume versions.

    Attributes:
        id: Unique generated resume identifier (UUID)
        analysis_id: Foreign key to Analysis that generated this resume
        user_id: Foreign key to User who owns this resume
        optimized_text: The LLM-generated optimized resume text
        model_used: Name of the LLM model used (e.g., "claude-sonnet-4-20250514")
        generation_metadata: JSONB field for storing metadata (tokens, cost, etc.)
        created_at: Timestamp of generation

    Relationships:
        analysis: The analysis that generated this resume
        user: The user who owns this resume
    """

    __tablename__ = "generated_resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    analysis_id = Column(
        UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    optimized_text = Column(Text, nullable=False)
    model_used = Column(String(50), nullable=True)
    generation_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    analysis = relationship("Analysis", back_populates="generated_resumes")
    user = relationship("User", back_populates="generated_resumes")

    def __repr__(self) -> str:
        return f"<GeneratedResume(id={self.id}, model={self.model_used}, created_at={self.created_at})>"
