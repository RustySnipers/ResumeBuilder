"""
Job Description Model - Phase 2.1

Represents job descriptions for resume optimization.
"""

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Uuid as UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from backend.database import Base


class JobDescription(Base):
    """
    Job Description model for storing target job postings.

    Attributes:
        id: Unique job description identifier (UUID)
        user_id: Foreign key to User who created this job description
        company_name: Name of the hiring company (optional)
        position_title: Job title/position name
        raw_text: Original job description text
        redacted_text: PII-redacted job description text for safe processing
        created_at: Timestamp of creation

    Relationships:
        user: The user who created this job description
        analyses: All analyses performed with this job description
    """

    __tablename__ = "job_descriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_name = Column(String(255), nullable=True)
    position_title = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    redacted_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="job_descriptions")
    analyses = relationship(
        "Analysis", back_populates="job_description", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<JobDescription(id={self.id}, company={self.company_name}, position={self.position_title})>"
