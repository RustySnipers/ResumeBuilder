"""
APIKey Repository - Phase 4

Data access layer for API key operations.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
import uuid

from backend.repositories.base_repository import BaseRepository
from backend.models.api_key import APIKey


class APIKeyRepository(BaseRepository[APIKey]):
    """
    Repository for API key data access.

    Provides CRUD operations and API key-specific queries.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(APIKey, session)

    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """
        Get API key by its hash.

        Args:
            key_hash: SHA-256 hash of the API key

        Returns:
            APIKey instance or None if not found
        """
        result = await self.session.execute(
            select(APIKey).where(APIKey.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_prefix(self, prefix: str) -> List[APIKey]:
        """
        Get API keys by prefix (for identification).

        Args:
            prefix: First 8 characters of the random token

        Returns:
            List of APIKey instances
        """
        result = await self.session.execute(
            select(APIKey).where(APIKey.prefix == prefix)
        )
        return list(result.scalars().all())

    async def get_by_user_id(
        self, user_id: uuid.UUID, active_only: bool = False
    ) -> List[APIKey]:
        """
        Get all API keys for a user.

        Args:
            user_id: User UUID
            active_only: If True, only return active keys

        Returns:
            List of APIKey instances
        """
        query = select(APIKey).where(APIKey.user_id == user_id)

        if active_only:
            query = query.where(APIKey.is_active == True)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_last_used(self, api_key_id: uuid.UUID) -> None:
        """
        Update the last_used_at timestamp for an API key.

        Args:
            api_key_id: API key UUID
        """
        await self.session.execute(
            update(APIKey)
            .where(APIKey.id == api_key_id)
            .values(last_used_at=datetime.utcnow())
        )
        await self.session.flush()

    async def deactivate(self, api_key_id: uuid.UUID) -> bool:
        """
        Deactivate an API key.

        Args:
            api_key_id: API key UUID

        Returns:
            True if deactivated, False if not found
        """
        result = await self.session.execute(
            update(APIKey)
            .where(APIKey.id == api_key_id)
            .values(is_active=False)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def cleanup_expired(self) -> int:
        """
        Delete expired API keys.

        Returns:
            Number of keys deleted
        """
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(APIKey).where(
                APIKey.expires_at.isnot(None),
                APIKey.expires_at < datetime.utcnow(),
            )
        )
        await self.session.flush()
        return result.rowcount
