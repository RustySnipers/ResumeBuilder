"""
Repository Layer - Phase 2.3

Exports all repository classes and the Unit of Work pattern.
"""

from backend.repositories.base_repository import BaseRepository
from backend.repositories.user_repository import UserRepository
from backend.repositories.resume_repository import ResumeRepository
from backend.repositories.job_description_repository import JobDescriptionRepository
from backend.repositories.analysis_repository import AnalysisRepository
from backend.repositories.generated_resume_repository import GeneratedResumeRepository
from backend.repositories.unit_of_work import UnitOfWork

__all__ = [
    "BaseRepository",
    "UserRepository",
    "ResumeRepository",
    "JobDescriptionRepository",
    "AnalysisRepository",
    "GeneratedResumeRepository",
    "UnitOfWork",
]
