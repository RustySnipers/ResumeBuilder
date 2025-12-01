"""
Role Model - Phase 4

Represents user roles for role-based access control (RBAC).
"""

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from backend.database import Base


class Role(Base):
    """
    Role model for role-based access control.

    Attributes:
        id: Unique role identifier (UUID)
        name: Role name (unique, e.g., "user", "premium", "admin")
        description: Human-readable description of the role
        permissions: JSON array of permission strings (e.g., ["read:own", "write:own"])
        created_at: Timestamp of role creation
        updated_at: Timestamp of last role update

    Relationships:
        users: All users with this role (many-to-many via user_roles)
    """

    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    permissions = Column(JSONB, default=list, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    users = relationship("User", secondary="user_roles", back_populates="roles")

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"
