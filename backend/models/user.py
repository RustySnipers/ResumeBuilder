"""
User Model - Phase 2.1

Represents users of the resume builder application with authentication fields.
"""

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from backend.database import Base


class User(Base):
    """
    User model for authentication and user management.

    Attributes:
        id: Unique user identifier (UUID)
        email: User email address (unique, used for login)
        hashed_password: Bcrypt hashed password
        is_active: Whether the user account is active
        is_verified: Whether the user email has been verified
        created_at: Timestamp of account creation
        updated_at: Timestamp of last account update

    Relationships:
        resumes: All resumes created by this user
        job_descriptions: All job descriptions created by this user
        analyses: All analyses created by this user
        generated_resumes: All generated resumes for this user
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships (cascade delete to remove all user data when user is deleted)
    resumes = relationship(
        "Resume", back_populates="user", cascade="all, delete-orphan"
    )
    job_descriptions = relationship(
        "JobDescription", back_populates="user", cascade="all, delete-orphan"
    )
    analyses = relationship(
        "Analysis", back_populates="user", cascade="all, delete-orphan"
    )
    generated_resumes = relationship(
        "GeneratedResume", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, is_active={self.is_active})>"
