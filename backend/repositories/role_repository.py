"""
Role Repository - Phase 4

Data access layer for role operations.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import uuid

from backend.repositories.base_repository import BaseRepository
from backend.models.role import Role
from backend.models.user_role import UserRole


class RoleRepository(BaseRepository[Role]):
    """
    Repository for role data access.

    Provides CRUD operations and role-specific queries.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Role, session)

    async def get_by_name(self, name: str) -> Optional[Role]:
        """
        Get role by name.

        Args:
            name: Role name (e.g., "user", "premium", "admin")

        Returns:
            Role instance or None if not found
        """
        result = await self.session.execute(
            select(Role).where(Role.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_names(self, names: List[str]) -> List[Role]:
        """
        Get multiple roles by their names.

        Args:
            names: List of role names

        Returns:
            List of Role instances
        """
        result = await self.session.execute(
            select(Role).where(Role.name.in_(names))
        )
        return list(result.scalars().all())

    async def get_user_roles(self, user_id: uuid.UUID) -> List[Role]:
        """
        Get all roles for a user.

        Args:
            user_id: User UUID

        Returns:
            List of Role instances
        """
        result = await self.session.execute(
            select(Role)
            .join(UserRole)
            .where(UserRole.user_id == user_id)
        )
        return list(result.scalars().all())

    async def assign_role_to_user(
        self, user_id: uuid.UUID, role_id: uuid.UUID
    ) -> UserRole:
        """
        Assign a role to a user.

        Args:
            user_id: User UUID
            role_id: Role UUID

        Returns:
            Created UserRole instance
        """
        user_role = UserRole(user_id=user_id, role_id=role_id)
        self.session.add(user_role)
        await self.session.flush()
        await self.session.refresh(user_role)
        return user_role

    async def remove_role_from_user(
        self, user_id: uuid.UUID, role_id: uuid.UUID
    ) -> bool:
        """
        Remove a role from a user.

        Args:
            user_id: User UUID
            role_id: Role UUID

        Returns:
            True if removed, False if not found
        """
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(UserRole).where(
                UserRole.user_id == user_id, UserRole.role_id == role_id
            )
        )
        await self.session.flush()
        return result.rowcount > 0

    async def get_users_with_role(self, role_name: str) -> List[uuid.UUID]:
        """
        Get all user IDs with a specific role.

        Args:
            role_name: Role name

        Returns:
            List of user UUIDs
        """
        result = await self.session.execute(
            select(UserRole.user_id)
            .join(Role)
            .where(Role.name == role_name)
        )
        return list(result.scalars().all())

    async def has_permission(
        self, user_id: uuid.UUID, permission: str
    ) -> bool:
        """
        Check if user has a specific permission through their roles.

        Args:
            user_id: User UUID
            permission: Permission string (e.g., "read:own", "write:all")

        Returns:
            True if user has permission, False otherwise
        """
        result = await self.session.execute(
            select(Role)
            .join(UserRole)
            .where(UserRole.user_id == user_id)
        )
        roles = result.scalars().all()

        # Check if any role has the permission
        for role in roles:
            if permission in role.permissions:
                return True

        return False
