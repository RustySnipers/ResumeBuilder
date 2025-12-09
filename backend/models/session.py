"""
Session Model - Phase 4

Represents user sessions for refresh token management.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid as UUID, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from backend.database import Base


class Session(Base):
    """
    Session model for managing refresh tokens and user sessions.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to users table
        refresh_token_hash: SHA-256 hash of the refresh token
        device_info: Information about the device (e.g., browser, OS)
        ip_address: IP address where session was created
        expires_at: Timestamp when session expires
        created_at: Timestamp of session creation

    Relationships:
        user: The user who owns this session
    """

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    refresh_token_hash = Column(String(255), unique=True, nullable=False, index=True)
    device_info = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"
