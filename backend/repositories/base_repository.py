"""
Base Repository Pattern - Phase 2.3

Provides generic CRUD operations for all repositories using async SQLAlchemy.
"""

from typing import TypeVar, Generic, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from backend.database import Base
import uuid

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """
    Base repository with async CRUD operations for all models.

    Type Parameters:
        T: SQLAlchemy model class

    Args:
        model: The SQLAlchemy model class
        session: Async database session
    """

    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def create(self, **kwargs) -> T:
        """
        Create a new record.

        Args:
            **kwargs: Model field values

        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(self, id: uuid.UUID) -> Optional[T]:
        """
        Get record by ID.

        Args:
            id: Record UUID

        Returns:
            Model instance or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Get all records with pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of model instances
        """
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def update(self, id: uuid.UUID, **kwargs) -> Optional[T]:
        """
        Update a record by ID.

        Args:
            id: Record UUID
            **kwargs: Fields to update

        Returns:
            Updated model instance or None if not found
        """
        instance = await self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            await self.session.flush()
            await self.session.refresh(instance)
        return instance

    async def delete(self, id: uuid.UUID) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Record UUID

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        return result.rowcount > 0

    async def exists(self, id: uuid.UUID) -> bool:
        """
        Check if record exists by ID.

        Args:
            id: Record UUID

        Returns:
            True if exists, False otherwise
        """
        result = await self.session.execute(
            select(self.model.id).where(self.model.id == id)
        )
        return result.scalar_one_or_none() is not None
