"""
AuditLog Model - Phase 4

Represents audit log entries for security and compliance tracking.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from backend.database import Base


class AuditLog(Base):
    """
    AuditLog model for security and compliance logging.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to users table (nullable for system events)
        action: Action performed (e.g., "login", "logout", "api_access", "password_change")
        resource: Type of resource accessed (e.g., "users", "resumes", "api_keys")
        resource_id: ID of the specific resource accessed
        ip_address: IP address of the request
        user_agent: User agent string from the request
        metadata: Additional context as JSON (e.g., error details, request parameters)
        created_at: Timestamp of the event

    Relationships:
        user: The user who performed the action (if applicable)
    """

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action = Column(String(100), nullable=False, index=True)
    resource = Column(String(100), nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"
