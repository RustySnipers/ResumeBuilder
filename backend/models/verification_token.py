"""
Verification Token Model

Handles email verification and password reset tokens.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Enum as SQLEnum, ForeignKey, Uuid as UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import secrets
import enum
import uuid

from backend.database import Base


class TokenType(enum.Enum):
    """Token type enumeration."""
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"


class VerificationToken(Base):
    """
    Verification Token Model

    Stores tokens for email verification and password reset.
    Tokens are automatically expired after a set time period.
    """

    __tablename__ = "verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    token_type = Column(SQLEnum(TokenType), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address = Column(String(45), nullable=True)  # Supports IPv6

    # Relationship
    user = relationship("User", back_populates="verification_tokens")

    @staticmethod
    def generate_token() -> str:
        """
        Generate a secure random token.

        Returns:
            64-character hex token
        """
        return secrets.token_urlsafe(48)  # 48 bytes = 64 chars in base64

    @classmethod
    def create_email_verification_token(
        cls,
        user_id: uuid.UUID,
        expires_hours: int = 24,
        ip_address: str = None
    ) -> "VerificationToken":
        """
        Create an email verification token.

        Args:
            user_id: User ID
            expires_hours: Expiration time in hours (default: 24)
            ip_address: IP address of requester

        Returns:
            VerificationToken instance
        """
        return cls(
            user_id=user_id,
            token=cls.generate_token(),
            token_type=TokenType.EMAIL_VERIFICATION,
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
            ip_address=ip_address
        )

    @classmethod
    def create_password_reset_token(
        cls,
        user_id: uuid.UUID,
        expires_hours: int = 1,
        ip_address: str = None
    ) -> "VerificationToken":
        """
        Create a password reset token.

        Args:
            user_id: User ID
            expires_hours: Expiration time in hours (default: 1)
            ip_address: IP address of requester

        Returns:
            VerificationToken instance
        """
        return cls(
            user_id=user_id,
            token=cls.generate_token(),
            token_type=TokenType.PASSWORD_RESET,
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
            ip_address=ip_address
        )

    def is_valid(self) -> bool:
        """
        Check if token is valid (not used and not expired).

        Returns:
            True if token is valid
        """
        if self.used:
            return False

        if datetime.utcnow() > self.expires_at:
            return False

        return True

    def mark_as_used(self) -> None:
        """Mark token as used."""
        self.used = True
        self.used_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<VerificationToken(id={self.id}, type={self.token_type.value}, user_id={self.user_id}, valid={self.is_valid()})>"
