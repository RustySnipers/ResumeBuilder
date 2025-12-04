"""Resume API Schemas

Pydantic models for resume API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class ResumeCreate(BaseModel):
    """Schema for creating a new resume."""
    title: str = Field(..., min_length=1, max_length=255, description="Resume title")
    raw_text: str = Field(..., min_length=10, description="Resume content")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Senior Python Developer Resume",
                "raw_text": "John Doe\\nSenior Python Developer\\n\\nExperience:\\n- Led development team..."
            }
        }


class ResumeUpdate(BaseModel):
    """Schema for updating a resume."""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Resume title")
    raw_text: Optional[str] = Field(None, min_length=10, description="Resume content")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Lead Python Developer Resume",
                "raw_text": "John Doe\\nLead Python Developer\\n\\nExperience:\\n- Led development team..."
            }
        }


class ResumeResponse(BaseModel):
    """Schema for resume response."""
    id: UUID
    user_id: UUID
    title: str
    raw_text: str
    redacted_text: Optional[str] = None
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResumeListResponse(BaseModel):
    """Schema for list of resumes response."""
    resumes: list[ResumeResponse]
    total: int
    limit: int
    offset: int


class ResumeDeleteResponse(BaseModel):
    """Schema for resume deletion response."""
    message: str
    resume_id: UUID
