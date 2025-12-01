"""
Database Models - Phase 2.1, Enhanced in Phase 4

This module exports all SQLAlchemy ORM models for the Resume Builder application.
"""

from backend.models.user import User
from backend.models.resume import Resume
from backend.models.job_description import JobDescription
from backend.models.analysis import Analysis
from backend.models.generated_resume import GeneratedResume

# Phase 4: Authentication & Authorization Models
from backend.models.role import Role
from backend.models.user_role import UserRole
from backend.models.api_key import APIKey
from backend.models.audit_log import AuditLog
from backend.models.session import Session

__all__ = [
    # Core models
    "User",
    "Resume",
    "JobDescription",
    "Analysis",
    "GeneratedResume",
    # Phase 4: Auth models
    "Role",
    "UserRole",
    "APIKey",
    "AuditLog",
    "Session",
]
