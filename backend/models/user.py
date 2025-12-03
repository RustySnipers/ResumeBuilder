"""
User Model - Phase 2.1, Enhanced in Phase 4

Represents users of the resume builder application with authentication fields.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer
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
        full_name: User's full name
        hashed_password: Bcrypt hashed password
        is_active: Whether the user account is active
        is_verified: Whether the user email has been verified
        email_verified_at: Timestamp when email was verified (Phase 4)
        last_login_at: Timestamp of last successful login (Phase 4)
        failed_login_attempts: Number of consecutive failed login attempts (Phase 4)
        locked_until: Timestamp until which account is locked (Phase 4)
        created_at: Timestamp of account creation
        updated_at: Timestamp of last account update

    Relationships:
        resumes: All resumes created by this user
        job_descriptions: All job descriptions created by this user
        analyses: All analyses created by this user
        generated_resumes: All generated resumes for this user
        roles: User's roles (many-to-many via user_roles)
        api_keys: User's API keys
        audit_logs: User's audit log entries
        sessions: User's active sessions
        verification_tokens: User's email verification tokens (Phase 5.2)
        activities: User's activity log (Phase 6)
        analysis_metrics: User's analysis metrics (Phase 6)
        export_metrics: User's export metrics (Phase 6)
        daily_metrics: User's daily aggregated metrics (Phase 6)
        webhooks: User's configured webhooks (Phase 7)
    """

    __tablename__ = "users"

    # Core fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Phase 4: Enhanced auth fields
    email_verified_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    # Timestamps
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

    # Phase 4: Auth relationships
    roles = relationship(
        "Role", secondary="user_roles", back_populates="users"
    )
    api_keys = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    verification_tokens = relationship(
        "VerificationToken", back_populates="user", cascade="all, delete-orphan"
    )

    # Phase 6: Analytics relationships
    activities = relationship(
        "UserActivity", back_populates="user", cascade="all, delete-orphan"
    )
    analysis_metrics = relationship(
        "AnalysisMetric", back_populates="user", cascade="all, delete-orphan"
    )
    export_metrics = relationship(
        "ExportMetric", back_populates="user", cascade="all, delete-orphan"
    )
    daily_metrics = relationship(
        "DailyMetric", back_populates="user", cascade="all, delete-orphan"
    )

    # Phase 7: Webhook relationships
    webhooks = relationship(
        "Webhook", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, is_active={self.is_active})>"
