"""
Verification Token Repository

Data access layer for verification tokens.
"""

from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from backend.repositories.base_repository import BaseRepository
from backend.models.verification_token import VerificationToken, TokenType


class VerificationTokenRepository(BaseRepository[VerificationToken]):
    """Repository for managing verification tokens."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository.

        Args:
            session: Database session
        """
        super().__init__(VerificationToken, session)

    async def get_by_token(self, token: str) -> Optional[VerificationToken]:
        """
        Get token by token string.

        Args:
            token: Token string

        Returns:
            VerificationToken if found, None otherwise
        """
        result = await self.session.execute(
            select(VerificationToken).where(VerificationToken.token == token)
        )
        return result.scalars().first()

    async def get_valid_token(self, token: str, token_type: TokenType) -> Optional[VerificationToken]:
        """
        Get valid (unused and not expired) token by token string and type.

        Args:
            token: Token string
            token_type: Type of token

        Returns:
            VerificationToken if valid, None otherwise
        """
        result = await self.session.execute(
            select(VerificationToken).where(
                and_(
                    VerificationToken.token == token,
                    VerificationToken.token_type == token_type,
                    VerificationToken.used == False,
                    VerificationToken.expires_at > datetime.utcnow()
                )
            )
        )
        return result.scalars().first()

    async def get_user_tokens(
        self,
        user_id: int,
        token_type: Optional[TokenType] = None,
        include_used: bool = False
    ) -> list[VerificationToken]:
        """
        Get all tokens for a user.

        Args:
            user_id: User ID
            token_type: Optional filter by token type
            include_used: Whether to include used tokens

        Returns:
            List of tokens
        """
        conditions = [VerificationToken.user_id == user_id]

        if token_type:
            conditions.append(VerificationToken.token_type == token_type)

        if not include_used:
            conditions.append(VerificationToken.used == False)

        result = await self.session.execute(
            select(VerificationToken)
            .where(and_(*conditions))
            .order_by(VerificationToken.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_token(
        self,
        user_id: int,
        token_type: TokenType
    ) -> Optional[VerificationToken]:
        """
        Get the most recent active (unused and not expired) token for a user.

        Args:
            user_id: User ID
            token_type: Type of token

        Returns:
            VerificationToken if found, None otherwise
        """
        result = await self.session.execute(
            select(VerificationToken)
            .where(
                and_(
                    VerificationToken.user_id == user_id,
                    VerificationToken.token_type == token_type,
                    VerificationToken.used == False,
                    VerificationToken.expires_at > datetime.utcnow()
                )
            )
            .order_by(VerificationToken.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def invalidate_user_tokens(
        self,
        user_id: int,
        token_type: Optional[TokenType] = None
    ) -> int:
        """
        Mark all user tokens as used (invalidate them).

        Args:
            user_id: User ID
            token_type: Optional filter by token type

        Returns:
            Number of tokens invalidated
        """
        tokens = await self.get_user_tokens(user_id, token_type, include_used=False)

        count = 0
        for token in tokens:
            if not token.used:
                token.mark_as_used()
                count += 1

        await self.session.flush()
        return count

    async def cleanup_expired_tokens(self) -> int:
        """
        Delete expired tokens (cleanup operation).

        Returns:
            Number of tokens deleted
        """
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(VerificationToken).where(
                VerificationToken.expires_at < datetime.utcnow()
            )
        )
        await self.session.commit()
        return result.rowcount
