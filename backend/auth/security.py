"""
Security Utilities - Phase 4

Password hashing, JWT token generation/validation, and cryptographic utilities.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from passlib.context import CryptContext
from jose import JWTError, jwt
import logging

logger = logging.getLogger(__name__)

# Password hashing context (bcrypt with cost factor 12)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived access tokens
REFRESH_TOKEN_EXPIRE_DAYS = 7     # Long-lived refresh tokens


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary of claims to encode in token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Dictionary of claims to encode in token

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, expected_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string to verify
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Check token type
        token_type = payload.get("type")
        if token_type != expected_type:
            logger.warning(f"Invalid token type: expected {expected_type}, got {token_type}")
            return None

        # Check expiration (jose does this automatically, but we log it)
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            logger.warning("Token expired")
            return None

        return payload

    except JWTError as e:
        logger.error(f"JWT verification error: {e}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, key_hash) where:
        - full_key: The complete API key to return to user (only shown once)
        - key_hash: SHA-256 hash to store in database
    """
    import hashlib

    # Generate random token (32 bytes = 64 hex chars)
    random_token = secrets.token_urlsafe(32)

    # Create full key with prefix
    env = os.getenv("ENV", "development")
    env_prefix = "live" if env == "production" else "test"
    full_key = f"rb_{env_prefix}_{random_token}"

    # Hash for storage (SHA-256)
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    # Get prefix for identification (first 8 chars after rb_xxx_)
    prefix = random_token[:8]

    return full_key, key_hash, prefix


def verify_api_key_format(api_key: str) -> bool:
    """
    Verify API key format without checking database.

    Args:
        api_key: API key to validate

    Returns:
        True if format is valid, False otherwise
    """
    if not api_key.startswith("rb_"):
        return False

    parts = api_key.split("_")
    if len(parts) < 3:
        return False

    env_part = parts[1]
    if env_part not in ["live", "test"]:
        return False

    # Check minimum length
    if len(api_key) < 40:
        return False

    return True


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"

    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"

    # Check against common passwords (basic list)
    common_passwords = [
        "password", "12345678", "qwerty", "admin", "letmein",
        "welcome", "monkey", "dragon", "master", "sunshine"
    ]
    if password.lower() in common_passwords:
        return False, "Password is too common, please choose a stronger password"

    return True, None
