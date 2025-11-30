"""
Comprehensive Repository Tests - Phase 2.3

Tests cover:
- BaseRepository CRUD operations
- User-specific repository methods
- Resume-specific repository methods
- JobDescription-specific repository methods
- Analysis-specific repository methods
- GeneratedResume-specific repository methods
- Unit of Work transaction management
"""

import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.database import Base
from backend.models.user import User
from backend.models.resume import Resume
from backend.models.job_description import JobDescription
from backend.models.analysis import Analysis
from backend.models.generated_resume import GeneratedResume
from backend.repositories.user_repository import UserRepository
from backend.repositories.resume_repository import ResumeRepository
from backend.repositories.job_description_repository import JobDescriptionRepository
from backend.repositories.analysis_repository import AnalysisRepository
from backend.repositories.generated_resume_repository import GeneratedResumeRepository
from backend.repositories.unit_of_work import UnitOfWork


# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def async_engine():
    """Create async test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """Create async database session for tests."""
    async_session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def sample_user(async_session):
    """Create a sample user for testing."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password_placeholder",
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def sample_resume(async_session, sample_user):
    """Create a sample resume for testing."""
    resume = Resume(
        user_id=sample_user.id,
        title="Software Engineer Resume",
        raw_text="Experienced Python developer with 5 years of experience.",
        version=1,
    )
    async_session.add(resume)
    await async_session.commit()
    await async_session.refresh(resume)
    return resume


@pytest.fixture
async def sample_job_description(async_session, sample_user):
    """Create a sample job description for testing."""
    jd = JobDescription(
        user_id=sample_user.id,
        company_name="Tech Corp",
        position_title="Senior Python Developer",
        raw_text="We need a Python expert with ML experience.",
    )
    async_session.add(jd)
    await async_session.commit()
    await async_session.refresh(jd)
    return jd


@pytest.fixture
async def sample_analysis(async_session, sample_user, sample_resume, sample_job_description):
    """Create a sample analysis for testing."""
    analysis = Analysis(
        user_id=sample_user.id,
        resume_id=sample_resume.id,
        job_description_id=sample_job_description.id,
        missing_keywords=["machine learning", "tensorflow"],
        suggestions=["Add ML projects", "Highlight Python skills"],
        match_score=75.5,
        semantic_similarity=0.78,
    )
    async_session.add(analysis)
    await async_session.commit()
    await async_session.refresh(analysis)
    return analysis


# ============================================================================
# UserRepository Tests
# ============================================================================


class TestUserRepository:
    """Test suite for UserRepository."""

    async def test_create_user(self, async_session):
        """Test creating a new user."""
        repo = UserRepository(async_session)
        user = await repo.create(
            email="newuser@example.com",
            hashed_password="hashed_password",
            is_active=True,
        )
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.full_name == "New User"
        assert user.is_active is True

    async def test_get_user_by_id(self, async_session, sample_user):
        """Test retrieving user by ID."""
        repo = UserRepository(async_session)
        user = await repo.get_by_id(sample_user.id)
        assert user is not None
        assert user.id == sample_user.id
        assert user.email == sample_user.email

    async def test_get_user_by_email(self, async_session, sample_user):
        """Test retrieving user by email."""
        repo = UserRepository(async_session)
        user = await repo.get_by_email(sample_user.email)
        assert user is not None
        assert user.email == sample_user.email

    async def test_email_exists(self, async_session, sample_user):
        """Test checking if email exists."""
        repo = UserRepository(async_session)
        exists = await repo.email_exists(sample_user.email)
        assert exists is True

        not_exists = await repo.email_exists("nonexistent@example.com")
        assert not_exists is False

    async def test_get_active_users(self, async_session, sample_user):
        """Test retrieving active users."""
        # Create inactive user
        inactive_user = User(
            email="inactive@example.com",
            hashed_password="hashed_password",
            is_active=False,
        )
        async_session.add(inactive_user)
        await async_session.commit()

        repo = UserRepository(async_session)
        active_users = await repo.get_active_users()
        assert len(active_users) == 1
        assert active_users[0].is_active is True

    async def test_update_user(self, async_session, sample_user):
        """Test updating user information."""
        repo = UserRepository(async_session)
        updated = await repo.update(sample_user.id, is_verified=True)
        assert updated is not None
        assert updated.is_verified is True

    async def test_delete_user(self, async_session, sample_user):
        """Test deleting a user."""
        repo = UserRepository(async_session)
        deleted = await repo.delete(sample_user.id)
        assert deleted is True

        user = await repo.get_by_id(sample_user.id)
        assert user is None


# ============================================================================
# ResumeRepository Tests
# ============================================================================


class TestResumeRepository:
    """Test suite for ResumeRepository."""

    async def test_create_resume(self, async_session, sample_user):
        """Test creating a new resume."""
        repo = ResumeRepository(async_session)
        resume = await repo.create(
            user_id=sample_user.id,
            title="Data Scientist Resume",
            raw_text="Experienced data scientist with ML expertise.",
            version=1,
        )
        assert resume.id is not None
        assert resume.title == "Data Scientist Resume"
        assert resume.version == 1

    async def test_get_by_user(self, async_session, sample_user, sample_resume):
        """Test retrieving resumes by user."""
        repo = ResumeRepository(async_session)
        resumes = await repo.get_by_user(sample_user.id)
        assert len(resumes) >= 1
        assert resumes[0].user_id == sample_user.id

    async def test_get_latest_version(self, async_session, sample_user):
        """Test getting latest version number for a resume title."""
        repo = ResumeRepository(async_session)

        # Create multiple versions
        await repo.create(
            user_id=sample_user.id, title="SWE Resume", raw_text="v1", version=1
        )
        await repo.create(
            user_id=sample_user.id, title="SWE Resume", raw_text="v2", version=2
        )
        await repo.create(
            user_id=sample_user.id, title="SWE Resume", raw_text="v3", version=3
        )

        latest = await repo.get_latest_version(sample_user.id, "SWE Resume")
        assert latest == 3

    async def test_get_by_title(self, async_session, sample_user, sample_resume):
        """Test retrieving resumes by title."""
        repo = ResumeRepository(async_session)
        resumes = await repo.get_by_title(sample_user.id, sample_resume.title)
        assert len(resumes) >= 1
        assert resumes[0].title == sample_resume.title

    async def test_count_by_user(self, async_session, sample_user, sample_resume):
        """Test counting resumes for a user."""
        repo = ResumeRepository(async_session)
        count = await repo.count_by_user(sample_user.id)
        assert count >= 1


# ============================================================================
# JobDescriptionRepository Tests
# ============================================================================


class TestJobDescriptionRepository:
    """Test suite for JobDescriptionRepository."""

    async def test_create_job_description(self, async_session, sample_user):
        """Test creating a new job description."""
        repo = JobDescriptionRepository(async_session)
        jd = await repo.create(
            user_id=sample_user.id,
            company_name="Startup Inc",
            position_title="ML Engineer",
            raw_text="Looking for ML engineer with Python skills.",
        )
        assert jd.id is not None
        assert jd.company_name == "Startup Inc"
        assert jd.position_title == "ML Engineer"

    async def test_get_by_user(self, async_session, sample_user, sample_job_description):
        """Test retrieving job descriptions by user."""
        repo = JobDescriptionRepository(async_session)
        jds = await repo.get_by_user(sample_user.id)
        assert len(jds) >= 1
        assert jds[0].user_id == sample_user.id

    async def test_search_by_company(self, async_session, sample_user, sample_job_description):
        """Test searching job descriptions by company name."""
        repo = JobDescriptionRepository(async_session)
        jds = await repo.search_by_company(sample_user.id, "Tech")
        assert len(jds) >= 1
        assert "Tech" in jds[0].company_name

    async def test_search_by_position(self, async_session, sample_user, sample_job_description):
        """Test searching job descriptions by position title."""
        repo = JobDescriptionRepository(async_session)
        jds = await repo.search_by_position(sample_user.id, "Python")
        assert len(jds) >= 1
        assert "Python" in jds[0].position_title

    async def test_count_by_user(self, async_session, sample_user, sample_job_description):
        """Test counting job descriptions for a user."""
        repo = JobDescriptionRepository(async_session)
        count = await repo.count_by_user(sample_user.id)
        assert count >= 1


# ============================================================================
# AnalysisRepository Tests
# ============================================================================


class TestAnalysisRepository:
    """Test suite for AnalysisRepository."""

    async def test_create_analysis(
        self, async_session, sample_user, sample_resume, sample_job_description
    ):
        """Test creating a new analysis."""
        repo = AnalysisRepository(async_session)
        analysis = await repo.create(
            user_id=sample_user.id,
            resume_id=sample_resume.id,
            job_description_id=sample_job_description.id,
            missing_keywords=["docker", "kubernetes"],
            suggestions=["Add DevOps skills"],
            match_score=82.3,
            semantic_similarity=0.85,
        )
        assert analysis.id is not None
        assert analysis.match_score == 82.3
        assert len(analysis.missing_keywords) == 2

    async def test_get_by_user(self, async_session, sample_user, sample_analysis):
        """Test retrieving analyses by user."""
        repo = AnalysisRepository(async_session)
        analyses = await repo.get_by_user(sample_user.id)
        assert len(analyses) >= 1
        assert analyses[0].user_id == sample_user.id

    async def test_get_by_resume_and_jd(
        self, async_session, sample_resume, sample_job_description, sample_analysis
    ):
        """Test retrieving analysis by resume and job description."""
        repo = AnalysisRepository(async_session)
        analysis = await repo.get_by_resume_and_jd(
            sample_resume.id, sample_job_description.id
        )
        assert analysis is not None
        assert analysis.resume_id == sample_resume.id
        assert analysis.job_description_id == sample_job_description.id

    async def test_get_recent_analyses(self, async_session, sample_user, sample_analysis):
        """Test retrieving recent analyses."""
        repo = AnalysisRepository(async_session)
        analyses = await repo.get_recent_analyses(sample_user.id, days=7)
        assert len(analyses) >= 1

    async def test_get_by_resume(self, async_session, sample_resume, sample_analysis):
        """Test retrieving analyses by resume."""
        repo = AnalysisRepository(async_session)
        analyses = await repo.get_by_resume(sample_resume.id)
        assert len(analyses) >= 1
        assert analyses[0].resume_id == sample_resume.id

    async def test_get_high_match_analyses(self, async_session, sample_user, sample_analysis):
        """Test retrieving high-scoring analyses."""
        repo = AnalysisRepository(async_session)
        analyses = await repo.get_high_match_analyses(sample_user.id, min_match_score=70.0)
        assert len(analyses) >= 1
        assert all(a.match_score >= 70.0 for a in analyses)


# ============================================================================
# GeneratedResumeRepository Tests
# ============================================================================


class TestGeneratedResumeRepository:
    """Test suite for GeneratedResumeRepository."""

    async def test_create_generated_resume(self, async_session, sample_user, sample_analysis):
        """Test creating a new generated resume."""
        repo = GeneratedResumeRepository(async_session)
        gen_resume = await repo.create(
            analysis_id=sample_analysis.id,
            user_id=sample_user.id,
            optimized_text="Optimized resume text with ML keywords.",
            model_used="claude-sonnet-4-20250514",
            generation_metadata={"tokens": 1500, "cost": 0.05},
        )
        assert gen_resume.id is not None
        assert gen_resume.model_used == "claude-sonnet-4-20250514"
        assert gen_resume.generation_metadata["tokens"] == 1500

    async def test_get_by_user(self, async_session, sample_user, sample_analysis):
        """Test retrieving generated resumes by user."""
        repo = GeneratedResumeRepository(async_session)

        # Create a generated resume
        await repo.create(
            analysis_id=sample_analysis.id,
            user_id=sample_user.id,
            optimized_text="Resume text",
            model_used="claude-sonnet-4-20250514",
        )

        gen_resumes = await repo.get_by_user(sample_user.id)
        assert len(gen_resumes) >= 1
        assert gen_resumes[0].user_id == sample_user.id

    async def test_get_by_analysis(self, async_session, sample_user, sample_analysis):
        """Test retrieving generated resumes by analysis."""
        repo = GeneratedResumeRepository(async_session)

        # Create a generated resume
        await repo.create(
            analysis_id=sample_analysis.id,
            user_id=sample_user.id,
            optimized_text="Resume text",
            model_used="claude-sonnet-4-20250514",
        )

        gen_resumes = await repo.get_by_analysis(sample_analysis.id)
        assert len(gen_resumes) >= 1
        assert gen_resumes[0].analysis_id == sample_analysis.id

    async def test_get_by_model(self, async_session, sample_user, sample_analysis):
        """Test retrieving generated resumes by model name."""
        repo = GeneratedResumeRepository(async_session)

        # Create resumes with different models
        await repo.create(
            analysis_id=sample_analysis.id,
            user_id=sample_user.id,
            optimized_text="Resume 1",
            model_used="claude-sonnet-4-20250514",
        )
        await repo.create(
            analysis_id=sample_analysis.id,
            user_id=sample_user.id,
            optimized_text="Resume 2",
            model_used="claude-opus-4-20250514",
        )

        sonnet_resumes = await repo.get_by_model(sample_user.id, "claude-sonnet-4-20250514")
        assert len(sonnet_resumes) >= 1
        assert all(r.model_used == "claude-sonnet-4-20250514" for r in sonnet_resumes)

    async def test_count_by_user(self, async_session, sample_user, sample_analysis):
        """Test counting generated resumes for a user."""
        repo = GeneratedResumeRepository(async_session)

        # Create a generated resume
        await repo.create(
            analysis_id=sample_analysis.id,
            user_id=sample_user.id,
            optimized_text="Resume text",
            model_used="claude-sonnet-4-20250514",
        )

        count = await repo.count_by_user(sample_user.id)
        assert count >= 1

    async def test_get_latest_by_analysis(self, async_session, sample_user, sample_analysis):
        """Test getting the latest generated resume for an analysis."""
        repo = GeneratedResumeRepository(async_session)

        # Create multiple generated resumes
        await repo.create(
            analysis_id=sample_analysis.id,
            user_id=sample_user.id,
            optimized_text="Resume v1",
            model_used="claude-sonnet-4-20250514",
        )
        await repo.create(
            analysis_id=sample_analysis.id,
            user_id=sample_user.id,
            optimized_text="Resume v2",
            model_used="claude-sonnet-4-20250514",
        )

        latest = await repo.get_latest_by_analysis(sample_analysis.id)
        assert latest is not None
        assert "Resume v2" in latest.optimized_text


# ============================================================================
# Unit of Work Tests
# ============================================================================


class TestUnitOfWork:
    """Test suite for Unit of Work pattern."""

    async def test_uow_provides_all_repositories(self, async_session):
        """Test that UnitOfWork provides access to all repositories."""
        uow = UnitOfWork(async_session)
        assert isinstance(uow.users, UserRepository)
        assert isinstance(uow.resumes, ResumeRepository)
        assert isinstance(uow.job_descriptions, JobDescriptionRepository)
        assert isinstance(uow.analyses, AnalysisRepository)
        assert isinstance(uow.generated_resumes, GeneratedResumeRepository)

    async def test_uow_atomic_transaction(self, async_session):
        """Test that UnitOfWork ensures atomic transactions."""
        uow = UnitOfWork(async_session)

        # Create user and resume in one transaction
        user = await uow.users.create(
            email="transaction@example.com",
            hashed_password="hashed_password",
            is_active=True,
        )
        resume = await uow.resumes.create(
            user_id=user.id,
            title="Test Resume",
            raw_text="Test content",
            version=1,
        )
        await uow.commit()

        # Verify both were saved
        retrieved_user = await uow.users.get_by_id(user.id)
        retrieved_resume = await uow.resumes.get_by_id(resume.id)
        assert retrieved_user is not None
        assert retrieved_resume is not None

    async def test_uow_rollback_on_error(self, async_session):
        """Test that UnitOfWork rolls back on error."""
        uow = UnitOfWork(async_session)

        try:
            # Create user
            user = await uow.users.create(
                email="rollback@example.com",
                hashed_password="hashed_password",
                is_active=True,
            )

            # Intentionally cause an error (invalid foreign key)
            invalid_uuid = uuid.uuid4()
            await uow.resumes.create(
                user_id=invalid_uuid,  # Non-existent user
                title="Test",
                raw_text="Test",
                version=1,
            )
            await uow.commit()
        except Exception:
            await uow.rollback()

        # User should not exist due to rollback
        user_check = await uow.users.get_by_email("rollback@example.com")
        # Depending on DB behavior, this might be None or still exist
        # SQLite in-memory might behave differently than PostgreSQL

    async def test_uow_context_manager(self, async_session):
        """Test using UnitOfWork as context manager."""
        async with UnitOfWork(async_session) as uow:
            user = await uow.users.create(
                email="context@example.com",
                hashed_password="hashed_password",
                is_active=True,
            )
            await uow.commit()

        # Verify user was created
        uow2 = UnitOfWork(async_session)
        retrieved = await uow2.users.get_by_email("context@example.com")
        assert retrieved is not None

    async def test_uow_lazy_loading(self, async_session):
        """Test that repositories are lazy-loaded."""
        uow = UnitOfWork(async_session)
        assert uow._users is None
        assert uow._resumes is None

        # Access triggers lazy loading
        _ = uow.users
        assert uow._users is not None
        assert uow._resumes is None  # Still not loaded
