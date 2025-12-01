"""
Export Router - Phase 5

FastAPI endpoints for resume export functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel, Field
import logging

from backend.export.pdf_generator import PDFGenerator
from backend.export.docx_generator import DOCXGenerator
from backend.export.template_engine import TemplateEngine
from backend.auth.dependencies import get_current_active_user
from backend.database.session import get_session
from backend.repositories.resume_repository import ResumeRepository
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.models.user import User
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/export", tags=["Export"])


# ============================================================================
# Schemas
# ============================================================================

class ExportRequest(BaseModel):
    """Request to export a resume."""
    resume_id: str = Field(..., description="Resume UUID to export")
    template: str = Field(default="professional", description="Template to use")
    format: str = Field(default="pdf", description="Export format: pdf or docx")


class TemplateInfo(BaseModel):
    """Template metadata."""
    id: str
    name: str
    description: str
    category: str
    preview_url: str


# ============================================================================
# Export Endpoints
# ============================================================================

@router.post("/pdf")
async def export_pdf(
    export_request: ExportRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Export resume as PDF.

    Returns a PDF file download.
    """
    resume_repo = ResumeRepository(session)
    audit_repo = AuditLogRepository(session)

    # Get resume
    try:
        resume_uuid = uuid.UUID(export_request.resume_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resume ID format",
        )

    resume = await resume_repo.get_by_id(resume_uuid)

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    # Verify ownership
    if resume.user_id != current_user.id:
        # Check if user is admin
        user_roles = [role.name for role in current_user.roles]
        if "admin" not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to export this resume",
            )

    # Prepare resume data
    resume_data = {
        "name": current_user.full_name,
        "email": current_user.email,
        "title": resume.title,
        "raw_text": resume.raw_text,
        # Add more fields as needed from resume object
    }

    # Generate PDF
    try:
        pdf_generator = PDFGenerator()
        pdf_bytes = pdf_generator.generate(
            resume_data=resume_data,
            template=export_request.template,
        )

        # Log export
        await audit_repo.log_event(
            action="resume_exported",
            user_id=current_user.id,
            resource="resumes",
            resource_id=resume.id,
            metadata={"format": "pdf", "template": export_request.template},
        )
        await session.commit()

        logger.info(f"Exported resume {resume.id} as PDF for user {current_user.email}")

        # Return PDF file
        filename = f"resume_{resume.title.replace(' ', '_')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes)),
            },
        )

    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {str(e)}",
        )


@router.post("/docx")
async def export_docx(
    export_request: ExportRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Export resume as DOCX (Microsoft Word).

    Returns a DOCX file download.
    """
    resume_repo = ResumeRepository(session)
    audit_repo = AuditLogRepository(session)

    # Get resume
    try:
        resume_uuid = uuid.UUID(export_request.resume_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resume ID format",
        )

    resume = await resume_repo.get_by_id(resume_uuid)

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    # Verify ownership
    if resume.user_id != current_user.id:
        # Check if user is admin
        user_roles = [role.name for role in current_user.roles]
        if "admin" not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to export this resume",
            )

    # Prepare resume data
    resume_data = {
        "name": current_user.full_name,
        "email": current_user.email,
        "title": resume.title,
        "raw_text": resume.raw_text,
        # Add more fields as needed
    }

    # Generate DOCX
    try:
        docx_generator = DOCXGenerator()
        docx_bytes = docx_generator.generate(
            resume_data=resume_data,
            template=export_request.template,
        )

        # Log export
        await audit_repo.log_event(
            action="resume_exported",
            user_id=current_user.id,
            resource="resumes",
            resource_id=resume.id,
            metadata={"format": "docx", "template": export_request.template},
        )
        await session.commit()

        logger.info(f"Exported resume {resume.id} as DOCX for user {current_user.email}")

        # Return DOCX file
        filename = f"resume_{resume.title.replace(' ', '_')}.docx"
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(docx_bytes)),
            },
        )

    except Exception as e:
        logger.error(f"DOCX generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DOCX generation failed: {str(e)}",
        )


@router.post("/preview")
async def generate_preview(
    export_request: ExportRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Generate HTML preview of resume.

    Returns HTML for preview in browser.
    """
    resume_repo = ResumeRepository(session)

    # Get resume
    try:
        resume_uuid = uuid.UUID(export_request.resume_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resume ID format",
        )

    resume = await resume_repo.get_by_id(resume_uuid)

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    # Verify ownership
    if resume.user_id != current_user.id:
        user_roles = [role.name for role in current_user.roles]
        if "admin" not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to preview this resume",
            )

    # Prepare resume data
    resume_data = {
        "name": current_user.full_name,
        "email": current_user.email,
        "title": resume.title,
        "raw_text": resume.raw_text,
    }

    # Generate HTML preview
    try:
        template_engine = TemplateEngine()
        html = template_engine.render(
            template_name=export_request.template,
            resume_data=resume_data,
        )

        return Response(
            content=html,
            media_type="text/html",
        )

    except Exception as e:
        logger.error(f"Preview generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Preview generation failed: {str(e)}",
        )


# ============================================================================
# Template Management
# ============================================================================

@router.get("/templates", response_model=list[TemplateInfo])
async def list_templates(
    current_user: User = Depends(get_current_active_user),
):
    """
    List available resume templates.

    Returns metadata for all available templates.
    """
    template_engine = TemplateEngine()
    templates = template_engine.list_templates()

    return [TemplateInfo(**t) for t in templates]


@router.get("/templates/{template_id}", response_model=TemplateInfo)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get details of a specific template.

    Returns template metadata including preview URL.
    """
    try:
        template_engine = TemplateEngine()
        template_info = template_engine.get_template_info(template_id)

        return TemplateInfo(**template_info)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
