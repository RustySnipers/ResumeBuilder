"""
Authentication Router - Phase 4

FastAPI router with authentication endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
import hashlib
import logging

from backend.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from backend.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    check_account_lockout,
    handle_failed_login,
    handle_successful_login,
)
from backend.auth.schemas import (
    UserRegister,
    UserResponse,
    UserUpdate,
    Token,
    RefreshTokenRequest,
    PasswordChange,
    PasswordResetRequest,
    PasswordReset,
)
from backend.database.session import get_session
from backend.repositories.user_repository import UserRepository
from backend.repositories.session_repository import SessionRepository
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.role_repository import RoleRepository
from backend.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# User Registration
# ============================================================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Register a new user.

    Creates a new user account with hashed password and assigns default "user" role.
    """
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)
    audit_repo = AuditLogRepository(session)

    # Check if email already exists
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password
    hashed_pwd = hash_password(user_data.password)

    # Create user
    user = await user_repo.create(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_pwd,
    )

    # Assign default "user" role
    default_role = await role_repo.get_by_name("user")
    if default_role:
        await role_repo.assign_role_to_user(user.id, default_role.id)

    # Commit transaction
    await session.commit()
    await session.refresh(user)

    # Log audit event
    await audit_repo.log_event(
        action="user_registration",
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()

    logger.info(f"New user registered: {user.email}")

    return user


# ============================================================================
# User Login
# ============================================================================

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """
    Login with email and password.

    Returns JWT access token and refresh token.
    """
    user_repo = UserRepository(session)
    session_repo = SessionRepository(session)
    audit_repo = AuditLogRepository(session)

    # Get user by email
    user = await user_repo.get_by_email(form_data.username)
    if not user:
        # Log failed login attempt
        await audit_repo.log_event(
            action="failed_login",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"reason": "user_not_found", "email": form_data.username},
        )
        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check account lockout
    await check_account_lockout(user, session)

    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        # Handle failed login
        await handle_failed_login(user, session)

        # Log failed login attempt
        await audit_repo.log_event(
            action="failed_login",
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"reason": "incorrect_password"},
        )
        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Handle successful login
    await handle_successful_login(user, session)

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    # Create refresh token
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )

    # Store refresh token in session
    refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    from datetime import datetime
    await session_repo.create_session(
        user_id=user.id,
        refresh_token_hash=refresh_token_hash,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        device_info=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    # Log successful login
    await audit_repo.log_event(
        action="login",
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    await session.commit()

    logger.info(f"User logged in: {user.email}")

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ============================================================================
# Token Refresh
# ============================================================================

@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: RefreshTokenRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Refresh access token using refresh token.

    Returns new access token and refresh token.
    """
    session_repo = SessionRepository(session)
    audit_repo = AuditLogRepository(session)

    # Verify refresh token
    payload = verify_token(token_data.refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if session exists and is valid
    refresh_token_hash = hashlib.sha256(token_data.refresh_token.encode()).hexdigest()
    if not await session_repo.is_valid_session(refresh_token_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    email = payload.get("email")

    # Create new tokens
    new_access_token = create_access_token(
        data={"sub": user_id, "email": email}
    )
    new_refresh_token = create_refresh_token(
        data={"sub": user_id, "email": email}
    )

    # Revoke old session
    old_session = await session_repo.get_by_refresh_token_hash(refresh_token_hash)
    if old_session:
        await session_repo.revoke_session(old_session.id)

    # Create new session
    new_refresh_token_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
    from datetime import datetime
    await session_repo.create_session(
        user_id=user_id,
        refresh_token_hash=new_refresh_token_hash,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        device_info=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    # Log token refresh
    await audit_repo.log_event(
        action="token_refresh",
        user_id=user_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    await session.commit()

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ============================================================================
# Logout
# ============================================================================

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token_data: RefreshTokenRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Logout user by revoking refresh token.
    """
    session_repo = SessionRepository(session)
    audit_repo = AuditLogRepository(session)

    # Revoke session
    refresh_token_hash = hashlib.sha256(token_data.refresh_token.encode()).hexdigest()
    user_session = await session_repo.get_by_refresh_token_hash(refresh_token_hash)
    if user_session:
        await session_repo.revoke_session(user_session.id)

    # Log logout
    await audit_repo.log_event(
        action="logout",
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    await session.commit()

    logger.info(f"User logged out: {current_user.email}")


# ============================================================================
# User Profile
# ============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Update current user profile."""
    user_repo = UserRepository(session)
    audit_repo = AuditLogRepository(session)

    # Build update dict (only include provided fields)
    update_data = user_update.model_dump(exclude_unset=True)

    if not update_data:
        return current_user

    # Check if email is being changed and if it's already taken
    if "email" in update_data and update_data["email"] != current_user.email:
        existing_user = await user_repo.get_by_email(update_data["email"])
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )

    # Update user
    updated_user = await user_repo.update(current_user.id, **update_data)

    # Log profile update
    await audit_repo.log_event(
        action="profile_update",
        user_id=current_user.id,
        metadata={"updated_fields": list(update_data.keys())},
    )

    await session.commit()
    await session.refresh(updated_user)

    logger.info(f"User profile updated: {updated_user.email}")

    return updated_user


# ============================================================================
# Password Management
# ============================================================================

@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Change user password."""
    user_repo = UserRepository(session)
    session_repo = SessionRepository(session)
    audit_repo = AuditLogRepository(session)

    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Hash new password
    new_hashed_password = hash_password(password_data.new_password)

    # Update password
    await user_repo.update(current_user.id, hashed_password=new_hashed_password)

    # Revoke all sessions (force re-login)
    await session_repo.revoke_all_user_sessions(current_user.id)

    # Log password change
    await audit_repo.log_event(
        action="password_change",
        user_id=current_user.id,
    )

    await session.commit()

    logger.info(f"Password changed for user: {current_user.email}")


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    password_reset_request: PasswordResetRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Request password reset email.

    Note: In production, this would send an email with a reset token.
    For now, we just return success (to prevent email enumeration).
    """
    user_repo = UserRepository(session)
    audit_repo = AuditLogRepository(session)

    # Look up user (but don't reveal if they exist)
    user = await user_repo.get_by_email(password_reset_request.email)

    if user:
        # TODO: Generate reset token and send email
        # For now, just log the event
        await audit_repo.log_event(
            action="password_reset_requested",
            user_id=user.id,
        )
        await session.commit()

        logger.info(f"Password reset requested for: {user.email}")

    # Always return success (prevent email enumeration)
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    password_reset: PasswordReset,
    session: AsyncSession = Depends(get_session),
):
    """
    Reset password with token.

    Note: Token verification logic needs to be implemented.
    """
    # TODO: Verify reset token, extract user_id
    # For now, return error as this feature is not fully implemented
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset feature not fully implemented yet",
    )


# ============================================================================
# Rate Limit Status
# ============================================================================

@router.get("/rate-limit/status")
async def get_rate_limit_status(
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current rate limit status for authenticated user.

    Shows limits, usage, and remaining requests.
    """
    from backend.auth.rate_limiter import UserRateLimiter
    import os

    # Initialize rate limiter
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    rate_limiter = UserRateLimiter(redis_url=redis_url)

    # Get user roles
    user_roles = [role.name for role in current_user.roles] if current_user.roles else ["user"]

    # Get stats
    stats = await rate_limiter.get_user_stats(
        user_id=str(current_user.id),
        user_roles=user_roles,
    )

    await rate_limiter.disconnect()

    return stats
