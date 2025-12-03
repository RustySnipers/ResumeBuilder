"""
UserRole Model - Phase 4

Association table for many-to-many relationship between users and roles.
"""

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from backend.database import Base


class UserRole(Base):
    """
    UserRole association table for user-role many-to-many relationship.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to users table
        role_id: Foreign key to roles table
        created_at: Timestamp when role was assigned to user

    Constraints:
        unique_user_role: Each user can only have a role once
    """

    __tablename__ = "user_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "role_id", name="unique_user_role"),)

    def __repr__(self) -> str:
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"
