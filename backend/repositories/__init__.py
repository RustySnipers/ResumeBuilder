"""
Repository Layer - Phase 2.3, Enhanced in Phase 4

Exports all repository classes and the Unit of Work pattern.
"""

from backend.repositories.base_repository import BaseRepository
from backend.repositories.user_repository import UserRepository
from backend.repositories.resume_repository import ResumeRepository
from backend.repositories.job_description_repository import JobDescriptionRepository
from backend.repositories.analysis_repository import AnalysisRepository
from backend.repositories.generated_resume_repository import GeneratedResumeRepository

# Phase 4: Auth repositories
from backend.repositories.api_key_repository import APIKeyRepository
from backend.repositories.role_repository import RoleRepository
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.session_repository import SessionRepository

from backend.repositories.unit_of_work import UnitOfWork

__all__ = [
    # Core repositories
    "BaseRepository",
    "UserRepository",
    "ResumeRepository",
    "JobDescriptionRepository",
    "AnalysisRepository",
    "GeneratedResumeRepository",
    # Phase 4: Auth repositories
    "APIKeyRepository",
    "RoleRepository",
    "AuditLogRepository",
    "SessionRepository",
    # Unit of Work
    "UnitOfWork",
]
