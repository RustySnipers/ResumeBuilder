"""
APIKey Model - Phase 4

Represents API keys for programmatic access to the API.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid as UUID, JSON as JSONB, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from backend.database import Base


class APIKey(Base):
    """
    APIKey model for API key authentication.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to users table
        key_hash: SHA-256 hash of the API key (for secure storage)
        name: Human-readable name for the API key
        prefix: First 8 characters of the random token (for identification)
        scopes: JSON array of allowed scopes/permissions
        is_active: Whether the API key is active
        last_used_at: Timestamp of last API key usage
        expires_at: Optional expiration timestamp
        created_at: Timestamp of API key creation

    Relationships:
        user: The user who owns this API key
    """

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    prefix = Column(String(20), nullable=False, index=True)
    scopes = Column(JSONB, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name}, prefix={self.prefix})>"
