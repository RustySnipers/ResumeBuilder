"""
Session Repository - Phase 4

Data access layer for session (refresh token) operations.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime
import uuid

from backend.repositories.base_repository import BaseRepository
from backend.models.session import Session


class SessionRepository(BaseRepository[Session]):
    """
    Repository for session data access.

    Provides CRUD operations and session-specific queries for refresh token management.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Session, session)

    async def get_by_refresh_token_hash(
        self, refresh_token_hash: str
    ) -> Optional[Session]:
        """
        Get session by refresh token hash.

        Args:
            refresh_token_hash: SHA-256 hash of the refresh token

        Returns:
            Session instance or None if not found
        """
        result = await self.session.execute(
            select(Session).where(
                Session.refresh_token_hash == refresh_token_hash
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self, user_id: uuid.UUID, active_only: bool = True
    ) -> List[Session]:
        """
        Get all sessions for a user.

        Args:
            user_id: User UUID
            active_only: If True, only return non-expired sessions

        Returns:
            List of Session instances
        """
        query = select(Session).where(Session.user_id == user_id)

        if active_only:
            query = query.where(Session.expires_at > datetime.utcnow())

        query = query.order_by(Session.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_session(
        self,
        user_id: uuid.UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Session:
        """
        Create a new session.

        Args:
            user_id: User UUID
            refresh_token_hash: SHA-256 hash of the refresh token
            expires_at: Expiration timestamp
            device_info: Optional device information
            ip_address: Optional IP address

        Returns:
            Created Session instance
        """
        return await self.create(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            device_info=device_info,
            ip_address=ip_address,
        )

    async def revoke_session(self, session_id: uuid.UUID) -> bool:
        """
        Revoke (delete) a session.

        Args:
            session_id: Session UUID

        Returns:
            True if revoked, False if not found
        """
        return await self.delete(session_id)

    async def revoke_all_user_sessions(self, user_id: uuid.UUID) -> int:
        """
        Revoke all sessions for a user (e.g., on password change).

        Args:
            user_id: User UUID

        Returns:
            Number of sessions revoked
        """
        result = await self.session.execute(
            delete(Session).where(Session.user_id == user_id)
        )
        await self.session.flush()
        return result.rowcount

    async def cleanup_expired_sessions(self) -> int:
        """
        Delete expired sessions.

        Returns:
            Number of sessions deleted
        """
        result = await self.session.execute(
            delete(Session).where(Session.expires_at < datetime.utcnow())
        )
        await self.session.flush()
        return result.rowcount

    async def is_valid_session(
        self, refresh_token_hash: str
    ) -> bool:
        """
        Check if a session is valid (exists and not expired).

        Args:
            refresh_token_hash: SHA-256 hash of the refresh token

        Returns:
            True if valid, False otherwise
        """
        result = await self.session.execute(
            select(Session).where(
                Session.refresh_token_hash == refresh_token_hash,
                Session.expires_at > datetime.utcnow(),
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_active_session_count(self, user_id: uuid.UUID) -> int:
        """
        Get count of active sessions for a user.

        Args:
            user_id: User UUID

        Returns:
            Number of active sessions
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count())
            .select_from(Session)
            .where(
                Session.user_id == user_id,
                Session.expires_at > datetime.utcnow(),
            )
        )
        return result.scalar() or 0
