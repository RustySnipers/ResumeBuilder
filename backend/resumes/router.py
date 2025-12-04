"""Resume Router

FastAPI endpoints for resume CRUD operations with webhook triggers.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime
import logging

from backend.resumes.schemas import (
    ResumeCreate,
    ResumeUpdate,
    ResumeResponse,
    ResumeListResponse,
    ResumeDeleteResponse,
)
from backend.auth.dependencies import get_current_active_user
from backend.database.session import get_session
from backend.repositories.resume_repository import ResumeRepository
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.models.user import User
from backend.models.webhook import WebhookEventType
from backend.webhooks.service import WebhookService
from backend.nlp.pii_detector import PIIDetector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/resumes", tags=["Resumes"])

# Initialize PII detector for redaction
pii_detector = PIIDetector()


@router.post("", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def create_resume(
    resume_data: ResumeCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new resume with PII redaction.

    Automatically redacts PII from the resume text before storage.
    Triggers webhook event: resume.created
    """
    resume_repo = ResumeRepository(session)
    audit_repo = AuditLogRepository(session)

    try:
        # Redact PII from resume text
        redacted_text = pii_detector.redact_pii(resume_data.raw_text)

        # Get next version number for this title
        latest_version = await resume_repo.get_latest_version(
            user_id=current_user.id,
            title=resume_data.title
        )

        # Create resume
        from backend.models.resume import Resume
        resume = Resume(
            user_id=current_user.id,
            title=resume_data.title,
            raw_text=resume_data.raw_text,
            redacted_text=redacted_text,
            version=latest_version + 1,
        )

        session.add(resume)
        await session.flush()

        # Log audit event
        await audit_repo.log_event(
            action="resume_created",
            user_id=current_user.id,
            resource="resumes",
            resource_id=resume.id,
            metadata={"title": resume.title, "version": resume.version},
        )

        await session.commit()
        await session.refresh(resume)

        logger.info(f"Resume created: {resume.id} by user {current_user.email}")

        # Trigger webhook event
        try:
            webhook_service = WebhookService(session)
            await webhook_service.trigger_event(
                event_type=WebhookEventType.RESUME_CREATED,
                event_id=resume.id,
                payload={
                    "resume_id": str(resume.id),
                    "user_id": str(current_user.id),
                    "title": resume.title,
                    "version": resume.version,
                    "created_at": resume.created_at.isoformat(),
                },
                user_id=current_user.id,
            )
            await session.commit()
        except Exception as webhook_error:
            logger.error(f"Failed to trigger webhook for resume creation: {webhook_error}")

        return resume

    except Exception as e:
        logger.error(f"Failed to create resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create resume: {str(e)}"
        )


@router.get("", response_model=ResumeListResponse)
async def list_resumes(
    limit: int = Query(50, ge=1, le=100, description="Maximum resumes to return"),
    offset: int = Query(0, ge=0, description="Number of resumes to skip"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    List all resumes for the current user.

    Returns paginated list of resumes ordered by creation date (newest first).
    """
    resume_repo = ResumeRepository(session)

    try:
        resumes = await resume_repo.get_by_user(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )

        total = await resume_repo.count_by_user(user_id=current_user.id)

        return ResumeListResponse(
            resumes=resumes,
            total=total,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Failed to list resumes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list resumes: {str(e)}"
        )


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get a specific resume by ID.

    Returns the resume if it belongs to the current user.
    """
    resume_repo = ResumeRepository(session)

    try:
        resume = await resume_repo.get_by_id(resume_id)

        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Verify ownership
        if resume.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this resume"
            )

        return resume

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get resume: {str(e)}"
        )


@router.put("/{resume_id}", response_model=ResumeResponse)
async def update_resume(
    resume_id: UUID,
    resume_data: ResumeUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update an existing resume.

    Updates title and/or content. Redacts PII if content is updated.
    Triggers webhook event: resume.updated
    """
    resume_repo = ResumeRepository(session)
    audit_repo = AuditLogRepository(session)

    try:
        resume = await resume_repo.get_by_id(resume_id)

        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Verify ownership
        if resume.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this resume"
            )

        # Update fields
        if resume_data.title is not None:
            resume.title = resume_data.title

        if resume_data.raw_text is not None:
            resume.raw_text = resume_data.raw_text
            # Redact PII from new content
            resume.redacted_text = pii_detector.redact_pii(resume_data.raw_text)

        # Log audit event
        await audit_repo.log_event(
            action="resume_updated",
            user_id=current_user.id,
            resource="resumes",
            resource_id=resume.id,
            metadata={"title": resume.title, "version": resume.version},
        )

        await session.commit()
        await session.refresh(resume)

        logger.info(f"Resume updated: {resume.id} by user {current_user.email}")

        # Trigger webhook event
        try:
            webhook_service = WebhookService(session)
            await webhook_service.trigger_event(
                event_type=WebhookEventType.RESUME_UPDATED,
                event_id=resume.id,
                payload={
                    "resume_id": str(resume.id),
                    "user_id": str(current_user.id),
                    "title": resume.title,
                    "version": resume.version,
                    "updated_at": resume.updated_at.isoformat(),
                },
                user_id=current_user.id,
            )
            await session.commit()
        except Exception as webhook_error:
            logger.error(f"Failed to trigger webhook for resume update: {webhook_error}")

        return resume

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update resume: {str(e)}"
        )


@router.delete("/{resume_id}", response_model=ResumeDeleteResponse)
async def delete_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a resume.

    Permanently deletes the resume and all associated data.
    Triggers webhook event: resume.deleted
    """
    resume_repo = ResumeRepository(session)
    audit_repo = AuditLogRepository(session)

    try:
        resume = await resume_repo.get_by_id(resume_id)

        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )

        # Verify ownership
        if resume.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this resume"
            )

        # Store resume info for webhook
        resume_info = {
            "resume_id": str(resume.id),
            "user_id": str(current_user.id),
            "title": resume.title,
            "version": resume.version,
            "deleted_at": datetime.utcnow().isoformat(),
        }

        # Log audit event
        await audit_repo.log_event(
            action="resume_deleted",
            user_id=current_user.id,
            resource="resumes",
            resource_id=resume.id,
            metadata={"title": resume.title, "version": resume.version},
        )

        # Delete resume
        await session.delete(resume)
        await session.commit()

        logger.info(f"Resume deleted: {resume_id} by user {current_user.email}")

        # Trigger webhook event
        try:
            webhook_service = WebhookService(session)
            await webhook_service.trigger_event(
                event_type=WebhookEventType.RESUME_DELETED,
                event_id=resume_id,
                payload=resume_info,
                user_id=current_user.id,
            )
            await session.commit()
        except Exception as webhook_error:
            logger.error(f"Failed to trigger webhook for resume deletion: {webhook_error}")

        return ResumeDeleteResponse(
            message="Resume deleted successfully",
            resume_id=resume_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete resume: {str(e)}"
        )
