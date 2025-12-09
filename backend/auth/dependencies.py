"""
Authentication Dependencies - Phase 4

FastAPI dependencies for JWT authentication, authorization, and user access.
"""

from typing import Optional, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import verify_token, verify_api_key_format
from backend.database import get_db as get_session
from backend.models.user import User
from backend.repositories.user_repository import UserRepository
import logging

logger = logging.getLogger(__name__)

# OAuth2 password bearer for JWT authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    auto_error=False  # Allow endpoints to handle missing tokens
)

# API key header authentication
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False
)


# ============================================================================
# JWT Authentication
# ============================================================================

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Get current user from JWT token.

    Args:
        token: JWT access token from Authorization header
        session: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    # Verify and decode token
    payload = verify_token(token, expected_type="access")
    if not payload:
        raise credentials_exception

    # Extract user ID from token
    user_id_str: str = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        import uuid
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        # Invalid UUID format
        raise credentials_exception

    # Fetch user from database
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (ensure user is not disabled).

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Active user object

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return current_user


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> Optional[User]:
    """
    Get current user if token is provided, otherwise return None.
    Useful for endpoints that work both with and without authentication.

    Args:
        token: Optional JWT access token
        session: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if not token:
        return None

    try:
        return await get_current_user(token, session)
    except HTTPException:
        return None


# ============================================================================
# API Key Authentication
# ============================================================================

async def get_user_from_api_key(
    api_key: Optional[str] = Depends(api_key_header),
    session: AsyncSession = Depends(get_session)
) -> Optional[User]:
    """
    Get user from API key.

    Args:
        api_key: API key from X-API-Key header
        session: Database session

    Returns:
        User object if API key is valid, None otherwise

    Raises:
        HTTPException: If API key is invalid or expired
    """
    if not api_key:
        return None

    # Validate format
    if not verify_api_key_format(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format"
        )

    # Hash the API key for lookup
    import hashlib
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Lookup API key in database
    from backend.repositories.api_key_repository import APIKeyRepository
    api_key_repo = APIKeyRepository(session)
    api_key_obj = await api_key_repo.get_by_hash(key_hash)

    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    # Check if key is active
    if not api_key_obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is inactive"
        )

    # Check if key is expired
    from datetime import datetime
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired"
        )

    # Update last used timestamp
    await api_key_repo.update_last_used(api_key_obj.id)

    # Fetch user
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(api_key_obj.user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return user


async def get_current_user_or_api_key(
    user_from_jwt: Optional[User] = Depends(get_optional_user),
    user_from_api_key: Optional[User] = Depends(get_user_from_api_key)
) -> User:
    """
    Get current user from either JWT token or API key.
    Tries JWT first, then API key.

    Args:
        user_from_jwt: User from JWT token (if provided)
        user_from_api_key: User from API key (if provided)

    Returns:
        User object

    Raises:
        HTTPException: If neither authentication method succeeds
    """
    user = user_from_jwt or user_from_api_key

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ============================================================================
# Role-Based Access Control (RBAC)
# ============================================================================

def require_role(required_role: str) -> Callable:
    """
    Dependency factory for role-based authorization.

    Usage:
        @app.get("/admin/users", dependencies=[Depends(require_role("admin"))])
        async def list_all_users():
            ...

    Args:
        required_role: Required role name (e.g., "admin", "premium")

    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """Check if user has required role"""
        # Get user roles
        user_roles = [role.name for role in current_user.roles]

        if required_role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )

        return current_user

    return role_checker


def require_permission(required_permission: str) -> Callable:
    """
    Dependency factory for permission-based authorization.

    Usage:
        @app.delete("/resumes/{id}", dependencies=[Depends(require_permission("delete:own"))])
        async def delete_resume(id: str):
            ...

    Args:
        required_permission: Required permission (e.g., "read:own", "write:all")

    Returns:
        Dependency function
    """
    async def permission_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """Check if user has required permission"""
        # Collect all permissions from user's roles
        user_permissions = []
        for role in current_user.roles:
            if hasattr(role, 'permissions'):
                user_permissions.extend(role.permissions)

        if required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required"
            )

        return current_user

    return permission_checker


# ============================================================================
# Resource Ownership
# ============================================================================

async def verify_resource_ownership(
    resource_user_id: str,
    current_user: User = Depends(get_current_active_user)
) -> bool:
    """
    Verify that current user owns the resource.

    Args:
        resource_user_id: User ID that owns the resource
        current_user: Current authenticated user

    Returns:
        True if user owns resource or is admin

    Raises:
        HTTPException: If user doesn't own resource and is not admin
    """
    # Admins can access all resources
    user_roles = [role.name for role in current_user.roles]
    if "admin" in user_roles:
        return True

    # Check ownership
    if str(current_user.id) != str(resource_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource"
        )

    return True


# ============================================================================
# Account Lockout Protection
# ============================================================================

async def check_account_lockout(
    user: User,
    session: AsyncSession
) -> None:
    """
    Check if user account is locked due to failed login attempts.

    Args:
        user: User to check
        session: Database session

    Raises:
        HTTPException: If account is locked
    """
    from datetime import datetime

    if user.locked_until and user.locked_until > datetime.utcnow():
        time_remaining = (user.locked_until - datetime.utcnow()).seconds // 60
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked due to multiple failed login attempts. Try again in {time_remaining} minutes."
        )


async def handle_failed_login(
    user: User,
    session: AsyncSession
) -> None:
    """
    Handle failed login attempt (increment counter, lock if needed).

    Args:
        user: User who failed login
        session: Database session
    """
    from datetime import datetime, timedelta

    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15

    user.failed_login_attempts += 1

    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        logger.warning(f"User {user.email} locked out due to {MAX_FAILED_ATTEMPTS} failed login attempts")

    session.add(user)
    await session.commit()


async def handle_successful_login(
    user: User,
    session: AsyncSession
) -> None:
    """
    Handle successful login (reset failed attempts, update last login).

    Args:
        user: User who logged in successfully
        session: Database session
    """
    from datetime import datetime

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()

    session.add(user)
    await session.commit()
