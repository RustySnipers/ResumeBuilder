"""
API Key Management Router - Phase 4

FastAPI router for API key CRUD operations.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from backend.auth.schemas import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyInfo,
    APIKeyUpdate,
)
from backend.auth.dependencies import get_current_active_user
from backend.auth.security import generate_api_key
from backend.database.session import get_session
from backend.repositories.api_key_repository import APIKeyRepository
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.models.user import User
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/api-keys", tags=["API Keys"])


# ============================================================================
# API Key Management
# ============================================================================

@router.post("", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Generate a new API key for the current user.

    Returns the full API key (only shown once).
    """
    api_key_repo = APIKeyRepository(session)
    audit_repo = AuditLogRepository(session)

    # Check if user already has too many keys (limit to 10)
    existing_keys = await api_key_repo.get_by_user_id(current_user.id, active_only=True)
    if len(existing_keys) >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of API keys (10) reached. Please revoke unused keys.",
        )

    # Generate API key
    full_key, key_hash, prefix = generate_api_key()

    # Create API key record
    api_key = await api_key_repo.create(
        user_id=current_user.id,
        key_hash=key_hash,
        name=api_key_data.name,
        prefix=prefix,
        scopes=api_key_data.scopes,
        expires_at=api_key_data.expires_at,
    )

    await session.commit()
    await session.refresh(api_key)

    # Log API key creation
    await audit_repo.log_event(
        action="api_key_created",
        user_id=current_user.id,
        resource="api_keys",
        resource_id=api_key.id,
        metadata={"name": api_key_data.name, "scopes": api_key_data.scopes},
    )
    await session.commit()

    logger.info(f"API key created for user {current_user.email}: {api_key.name}")

    # Return response with full key (only time it's visible)
    return APIKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        key=full_key,  # Full key only returned on creation
        prefix=api_key.prefix,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get("", response_model=List[APIKeyInfo])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
    active_only: bool = True,
):
    """
    List all API keys for the current user.

    Does not return the actual keys, only metadata.
    """
    api_key_repo = APIKeyRepository(session)

    api_keys = await api_key_repo.get_by_user_id(
        current_user.id, active_only=active_only
    )

    return [
        APIKeyInfo(
            id=str(key.id),
            name=key.name,
            prefix=key.prefix,
            scopes=key.scopes,
            is_active=key.is_active,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at,
            created_at=key.created_at,
        )
        for key in api_keys
    ]


@router.get("/{key_id}", response_model=APIKeyInfo)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get details of a specific API key.

    Does not return the actual key.
    """
    api_key_repo = APIKeyRepository(session)

    # Get API key
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid API key ID format",
        )

    api_key = await api_key_repo.get_by_id(key_uuid)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Verify ownership
    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this API key",
        )

    return APIKeyInfo(
        id=str(api_key.id),
        name=api_key.name,
        prefix=api_key.prefix,
        scopes=api_key.scopes,
        is_active=api_key.is_active,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.put("/{key_id}", response_model=APIKeyInfo)
async def update_api_key(
    key_id: str,
    api_key_update: APIKeyUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update an API key (name, scopes, active status).

    Cannot change the actual key value.
    """
    api_key_repo = APIKeyRepository(session)
    audit_repo = AuditLogRepository(session)

    # Get API key
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid API key ID format",
        )

    api_key = await api_key_repo.get_by_id(key_uuid)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Verify ownership
    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this API key",
        )

    # Build update dict
    update_data = api_key_update.model_dump(exclude_unset=True)

    if not update_data:
        return APIKeyInfo(
            id=str(api_key.id),
            name=api_key.name,
            prefix=api_key.prefix,
            scopes=api_key.scopes,
            is_active=api_key.is_active,
            last_used_at=api_key.last_used_at,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
        )

    # Update API key
    updated_key = await api_key_repo.update(key_uuid, **update_data)

    await session.commit()
    await session.refresh(updated_key)

    # Log API key update
    await audit_repo.log_event(
        action="api_key_updated",
        user_id=current_user.id,
        resource="api_keys",
        resource_id=updated_key.id,
        metadata={"updated_fields": list(update_data.keys())},
    )
    await session.commit()

    logger.info(f"API key updated for user {current_user.email}: {updated_key.name}")

    return APIKeyInfo(
        id=str(updated_key.id),
        name=updated_key.name,
        prefix=updated_key.prefix,
        scopes=updated_key.scopes,
        is_active=updated_key.is_active,
        last_used_at=updated_key.last_used_at,
        expires_at=updated_key.expires_at,
        created_at=updated_key.created_at,
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Revoke (delete) an API key.

    This is permanent and cannot be undone.
    """
    api_key_repo = APIKeyRepository(session)
    audit_repo = AuditLogRepository(session)

    # Get API key
    try:
        key_uuid = uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid API key ID format",
        )

    api_key = await api_key_repo.get_by_id(key_uuid)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Verify ownership
    if api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to revoke this API key",
        )

    # Log before deletion
    await audit_repo.log_event(
        action="api_key_revoked",
        user_id=current_user.id,
        resource="api_keys",
        resource_id=api_key.id,
        metadata={"name": api_key.name},
    )

    # Delete API key
    await api_key_repo.delete(key_uuid)
    await session.commit()

    logger.info(f"API key revoked for user {current_user.email}: {api_key.name}")


@router.post("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_expired_keys(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Remove expired API keys for the current user.

    Admin endpoint (requires admin role) for cleanup.
    """
    # Check if user is admin
    user_roles = [role.name for role in current_user.roles]
    if "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for cleanup operation",
        )

    api_key_repo = APIKeyRepository(session)
    count = await api_key_repo.cleanup_expired()
    await session.commit()

    logger.info(f"Cleaned up {count} expired API keys")

    return {"deleted_count": count}
