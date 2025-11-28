"""
Resume Model - Phase 2.1

Represents user resumes with versioning and PII redaction.
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from backend.database import Base


class Resume(Base):
    """
    Resume model for storing user resumes with version tracking.

    Attributes:
        id: Unique resume identifier (UUID)
        user_id: Foreign key to User who owns this resume
        title: Human-readable title for the resume (e.g., "Senior Python Developer Resume")
        raw_text: Original resume text (with PII)
        redacted_text: PII-redacted resume text for safe processing
        version: Version number for tracking resume iterations
        created_at: Timestamp of resume creation
        updated_at: Timestamp of last resume update

    Relationships:
        user: The user who owns this resume
        analyses: All analyses performed with this resume
    """

    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    redacted_text = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="resumes")
    analyses = relationship(
        "Analysis", back_populates="resume", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, title={self.title}, version={self.version})>"
