"""Webhook Router

API endpoints for webhook management.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.models.webhook import WebhookEventType
from backend.webhooks.service import WebhookService
from backend.webhooks.schemas import (
    WebhookCreate,
    WebhookUpdate,
    WebhookResponse,
    WebhookListResponse,
    WebhookEventListResponse,
    WebhookStatisticsResponse,
    WebhookSecretResponse,
    WebhookEventTypesResponse,
)


router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook_data: WebhookCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new webhook

    Creates a webhook configuration for receiving event notifications.
    A secure HMAC secret is automatically generated for signature verification.

    **Required Permissions:** Authenticated user

    Args:
        webhook_data: Webhook configuration
        current_user: Authenticated user
        session: Database session

    Returns:
        Created webhook with secret
    """
    webhook_service = WebhookService(session)

    webhook = await webhook_service.create_webhook(
        user_id=current_user.id,
        url=webhook_data.url,
        events=webhook_data.events,
        description=webhook_data.description,
        timeout_seconds=webhook_data.timeout_seconds,
        max_retries=webhook_data.max_retries,
    )

    return webhook


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    active_only: bool = Query(False, description="Only return active webhooks"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all webhooks for the authenticated user

    **Required Permissions:** Authenticated user

    Args:
        active_only: Filter for active webhooks only
        current_user: Authenticated user
        session: Database session

    Returns:
        List of webhooks
    """
    webhook_service = WebhookService(session)

    webhooks = await webhook_service.get_user_webhooks(
        user_id=current_user.id,
        active_only=active_only,
    )

    return WebhookListResponse(
        webhooks=webhooks,
        total=len(webhooks),
    )


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific webhook

    **Required Permissions:** Webhook owner

    Args:
        webhook_id: Webhook ID
        current_user: Authenticated user
        session: Database session

    Returns:
        Webhook details
    """
    webhook_service = WebhookService(session)

    webhook = await webhook_service.get_webhook(
        user_id=current_user.id,
        webhook_id=webhook_id,
    )

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    return webhook


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: UUID,
    webhook_data: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update a webhook

    **Required Permissions:** Webhook owner

    Args:
        webhook_id: Webhook ID
        webhook_data: Updated webhook data
        current_user: Authenticated user
        session: Database session

    Returns:
        Updated webhook
    """
    webhook_service = WebhookService(session)

    webhook = await webhook_service.update_webhook(
        user_id=current_user.id,
        webhook_id=webhook_id,
        url=webhook_data.url,
        events=webhook_data.events,
        description=webhook_data.description,
        is_active=webhook_data.is_active,
        timeout_seconds=webhook_data.timeout_seconds,
        max_retries=webhook_data.max_retries,
    )

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    return webhook


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete a webhook

    **Required Permissions:** Webhook owner

    Args:
        webhook_id: Webhook ID
        current_user: Authenticated user
        session: Database session
    """
    webhook_service = WebhookService(session)

    deleted = await webhook_service.delete_webhook(
        user_id=current_user.id,
        webhook_id=webhook_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )


@router.post("/{webhook_id}/regenerate-secret", response_model=WebhookSecretResponse)
async def regenerate_webhook_secret(
    webhook_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Regenerate webhook secret

    Generates a new HMAC secret for the webhook. The old secret will be
    invalidated immediately.

    **Required Permissions:** Webhook owner

    Args:
        webhook_id: Webhook ID
        current_user: Authenticated user
        session: Database session

    Returns:
        New secret
    """
    webhook_service = WebhookService(session)

    new_secret = await webhook_service.regenerate_secret(
        user_id=current_user.id,
        webhook_id=webhook_id,
    )

    if not new_secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    return WebhookSecretResponse(
        webhook_id=webhook_id,
        secret=new_secret,
    )


@router.get("/{webhook_id}/events", response_model=WebhookEventListResponse)
async def list_webhook_events(
    webhook_id: UUID,
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List webhook delivery events

    **Required Permissions:** Webhook owner

    Args:
        webhook_id: Webhook ID
        limit: Maximum events to return
        offset: Pagination offset
        current_user: Authenticated user
        session: Database session

    Returns:
        List of webhook events
    """
    webhook_service = WebhookService(session)

    events = await webhook_service.get_webhook_events(
        user_id=current_user.id,
        webhook_id=webhook_id,
        limit=limit,
        offset=offset,
    )

    if events is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    return WebhookEventListResponse(
        events=events,
        total=len(events),
    )


@router.get("/{webhook_id}/statistics", response_model=WebhookStatisticsResponse)
async def get_webhook_statistics(
    webhook_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get webhook delivery statistics

    **Required Permissions:** Webhook owner

    Args:
        webhook_id: Webhook ID
        current_user: Authenticated user
        session: Database session

    Returns:
        Webhook statistics
    """
    webhook_service = WebhookService(session)

    stats = await webhook_service.get_event_statistics(
        user_id=current_user.id,
        webhook_id=webhook_id,
    )

    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    return WebhookStatisticsResponse(**stats)


@router.get("/event-types/available", response_model=WebhookEventTypesResponse)
async def get_available_event_types(
    current_user: User = Depends(get_current_user),
):
    """Get available webhook event types

    Returns a list of all available event types that can be subscribed to.

    **Required Permissions:** Authenticated user

    Returns:
        List of available event types with descriptions
    """
    event_types = [
        {
            "type": event_type.value,
            "description": _get_event_description(event_type),
        }
        for event_type in WebhookEventType
    ]

    return WebhookEventTypesResponse(event_types=event_types)


def _get_event_description(event_type: WebhookEventType) -> str:
    """Get description for an event type"""
    descriptions = {
        WebhookEventType.RESUME_CREATED: "Triggered when a resume is created",
        WebhookEventType.RESUME_UPDATED: "Triggered when a resume is updated",
        WebhookEventType.RESUME_DELETED: "Triggered when a resume is deleted",
        WebhookEventType.ANALYSIS_COMPLETED: "Triggered when resume analysis completes",
        WebhookEventType.ANALYSIS_FAILED: "Triggered when resume analysis fails",
        WebhookEventType.GENERATION_COMPLETED: "Triggered when AI generation completes",
        WebhookEventType.GENERATION_FAILED: "Triggered when AI generation fails",
        WebhookEventType.EXPORT_COMPLETED: "Triggered when resume export completes",
        WebhookEventType.EXPORT_FAILED: "Triggered when resume export fails",
        WebhookEventType.USER_EMAIL_VERIFIED: "Triggered when user verifies their email",
        WebhookEventType.USER_PASSWORD_CHANGED: "Triggered when user changes password",
    }
    return descriptions.get(event_type, "")
