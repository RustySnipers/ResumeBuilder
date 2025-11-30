"""
Unit of Work Pattern - Phase 2.3

Manages database transactions across multiple repositories.
Ensures atomic operations and proper session lifecycle management.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.repositories.user_repository import UserRepository
from backend.repositories.resume_repository import ResumeRepository
from backend.repositories.job_description_repository import JobDescriptionRepository
from backend.repositories.analysis_repository import AnalysisRepository
from backend.repositories.generated_resume_repository import GeneratedResumeRepository


class UnitOfWork:
    """
    Unit of Work pattern for managing database transactions.

    Provides a single point of access to all repositories and ensures
    that all operations within a unit of work are committed or rolled back together.

    Usage:
        async with UnitOfWork(session) as uow:
            user = await uow.users.create(email="test@example.com", ...)
            resume = await uow.resumes.create(user_id=user.id, ...)
            await uow.commit()

    Attributes:
        users: UserRepository instance
        resumes: ResumeRepository instance
        job_descriptions: JobDescriptionRepository instance
        analyses: AnalysisRepository instance
        generated_resumes: GeneratedResumeRepository instance
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize Unit of Work with a database session.

        Args:
            session: AsyncSession from database.get_db()
        """
        self.session = session
        self._users: Optional[UserRepository] = None
        self._resumes: Optional[ResumeRepository] = None
        self._job_descriptions: Optional[JobDescriptionRepository] = None
        self._analyses: Optional[AnalysisRepository] = None
        self._generated_resumes: Optional[GeneratedResumeRepository] = None

    @property
    def users(self) -> UserRepository:
        """Lazy-loaded UserRepository."""
        if self._users is None:
            self._users = UserRepository(self.session)
        return self._users

    @property
    def resumes(self) -> ResumeRepository:
        """Lazy-loaded ResumeRepository."""
        if self._resumes is None:
            self._resumes = ResumeRepository(self.session)
        return self._resumes

    @property
    def job_descriptions(self) -> JobDescriptionRepository:
        """Lazy-loaded JobDescriptionRepository."""
        if self._job_descriptions is None:
            self._job_descriptions = JobDescriptionRepository(self.session)
        return self._job_descriptions

    @property
    def analyses(self) -> AnalysisRepository:
        """Lazy-loaded AnalysisRepository."""
        if self._analyses is None:
            self._analyses = AnalysisRepository(self.session)
        return self._analyses

    @property
    def generated_resumes(self) -> GeneratedResumeRepository:
        """Lazy-loaded GeneratedResumeRepository."""
        if self._generated_resumes is None:
            self._generated_resumes = GeneratedResumeRepository(self.session)
        return self._generated_resumes

    async def commit(self) -> None:
        """
        Commit the current transaction.

        This should be called after all operations in the unit of work
        have been performed successfully.
        """
        await self.session.commit()

    async def rollback(self) -> None:
        """
        Rollback the current transaction.

        This should be called if an error occurs during the unit of work
        to ensure data consistency.
        """
        await self.session.rollback()

    async def refresh(self, instance) -> None:
        """
        Refresh an instance from the database.

        Args:
            instance: SQLAlchemy model instance to refresh
        """
        await self.session.refresh(instance)

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit.

        Automatically rolls back on exception, commits on success.
        """
        if exc_type is not None:
            await self.rollback()
        # Note: get_db() already handles commit/rollback, so we don't commit here
        # to avoid double-committing. If using UnitOfWork outside get_db(),
        # manually call commit().
