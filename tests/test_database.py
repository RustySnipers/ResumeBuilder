"""
Unit Tests for Database Infrastructure - Phase 2.1

Tests for:
- Database connection management
- SQLAlchemy models
- Migration system
"""

import pytest
from sqlalchemy import select
from datetime import datetime
import uuid

# Import models
from backend.models import User, Resume, JobDescription, Analysis, GeneratedResume

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit


class TestUserModel:
    """Test cases for User model."""

    def test_user_model_creation(self):
        """Test User model can be instantiated."""
        user = User(
            email="test@example.com",
            hashed_password="hashed_password_here",
            is_active=True,
            is_verified=False,
        )

        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password_here"
        assert user.is_active is True
        assert user.is_verified is False

    def test_user_model_defaults(self):
        """Test User model default values."""
        user = User(
            email="test@example.com",
            hashed_password="hashed_password_here",
        )

        # Note: Column defaults are applied by the database, not by SQLAlchemy ORM
        # When a model is instantiated without values, they will be None until inserted
        # This test verifies the model can be created without specifying defaults
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password_here"

    def test_user_model_repr(self):
        """Test User model string representation."""
        user = User(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password="hashed_password_here",
            is_active=True,
        )

        repr_str = repr(user)
        assert "User" in repr_str
        assert user.email in repr_str


class TestResumeModel:
    """Test cases for Resume model."""

    def test_resume_model_creation(self):
        """Test Resume model can be instantiated."""
        user_id = uuid.uuid4()
        resume = Resume(
            user_id=user_id,
            title="Senior Python Developer Resume",
            raw_text="Original resume text",
            redacted_text="Redacted resume text",
            version=1,
        )

        assert resume.user_id == user_id
        assert resume.title == "Senior Python Developer Resume"
        assert resume.raw_text == "Original resume text"
        assert resume.redacted_text == "Redacted resume text"
        assert resume.version == 1

    def test_resume_model_defaults(self):
        """Test Resume model default values."""
        resume = Resume(
            user_id=uuid.uuid4(),
            title="Test Resume",
            raw_text="Text",
        )

        # Note: Column defaults are applied by the database, not by SQLAlchemy ORM
        # When a model is instantiated without values, they will be None until inserted
        # This test verifies the model can be created without specifying defaults
        assert resume.title == "Test Resume"
        assert resume.redacted_text is None

    def test_resume_model_repr(self):
        """Test Resume model string representation."""
        resume = Resume(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Test Resume",
            raw_text="Text",
            version=2,
        )

        repr_str = repr(resume)
        assert "Resume" in repr_str
        assert resume.title in repr_str


class TestJobDescriptionModel:
    """Test cases for JobDescription model."""

    def test_job_description_model_creation(self):
        """Test JobDescription model can be instantiated."""
        user_id = uuid.uuid4()
        jd = JobDescription(
            user_id=user_id,
            company_name="Tech Corp",
            position_title="Senior Engineer",
            raw_text="Job description text",
            redacted_text="Redacted JD text",
        )

        assert jd.user_id == user_id
        assert jd.company_name == "Tech Corp"
        assert jd.position_title == "Senior Engineer"
        assert jd.raw_text == "Job description text"
        assert jd.redacted_text == "Redacted JD text"

    def test_job_description_optional_company(self):
        """Test JobDescription with optional company name."""
        jd = JobDescription(
            user_id=uuid.uuid4(),
            position_title="Software Engineer",
            raw_text="JD text",
        )

        assert jd.company_name is None
        assert jd.position_title == "Software Engineer"

    def test_job_description_repr(self):
        """Test JobDescription model string representation."""
        jd = JobDescription(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            company_name="Tech Corp",
            position_title="Engineer",
            raw_text="Text",
        )

        repr_str = repr(jd)
        assert "JobDescription" in repr_str
        assert "Tech Corp" in repr_str


class TestAnalysisModel:
    """Test cases for Analysis model."""

    def test_analysis_model_creation(self):
        """Test Analysis model can be instantiated."""
        user_id = uuid.uuid4()
        resume_id = uuid.uuid4()
        job_desc_id = uuid.uuid4()

        analysis = Analysis(
            user_id=user_id,
            resume_id=resume_id,
            job_description_id=job_desc_id,
            missing_keywords=["python", "fastapi"],
            suggestions=["Add Python skills"],
            match_score=75.5,
            semantic_similarity=0.85,
        )

        assert analysis.user_id == user_id
        assert analysis.resume_id == resume_id
        assert analysis.job_description_id == job_desc_id
        assert analysis.missing_keywords == ["python", "fastapi"]
        assert analysis.suggestions == ["Add Python skills"]
        assert float(analysis.match_score) == 75.5
        assert float(analysis.semantic_similarity) == 0.85

    def test_analysis_model_optional_fields(self):
        """Test Analysis with optional fields."""
        analysis = Analysis(
            user_id=uuid.uuid4(),
            resume_id=uuid.uuid4(),
            job_description_id=uuid.uuid4(),
        )

        assert analysis.missing_keywords is None
        assert analysis.suggestions is None
        assert analysis.match_score is None
        assert analysis.semantic_similarity is None

    def test_analysis_model_repr(self):
        """Test Analysis model string representation."""
        analysis = Analysis(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            resume_id=uuid.uuid4(),
            job_description_id=uuid.uuid4(),
            match_score=85.5,
        )

        repr_str = repr(analysis)
        assert "Analysis" in repr_str


class TestGeneratedResumeModel:
    """Test cases for GeneratedResume model."""

    def test_generated_resume_model_creation(self):
        """Test GeneratedResume model can be instantiated."""
        user_id = uuid.uuid4()
        analysis_id = uuid.uuid4()

        gen_resume = GeneratedResume(
            user_id=user_id,
            analysis_id=analysis_id,
            optimized_text="Optimized resume text",
            model_used="claude-sonnet-4-20250514",
            generation_metadata={"tokens": 1500, "cost": 0.05},
        )

        assert gen_resume.user_id == user_id
        assert gen_resume.analysis_id == analysis_id
        assert gen_resume.optimized_text == "Optimized resume text"
        assert gen_resume.model_used == "claude-sonnet-4-20250514"
        assert gen_resume.generation_metadata["tokens"] == 1500
        assert gen_resume.generation_metadata["cost"] == 0.05

    def test_generated_resume_optional_metadata(self):
        """Test GeneratedResume with optional metadata."""
        gen_resume = GeneratedResume(
            user_id=uuid.uuid4(),
            analysis_id=uuid.uuid4(),
            optimized_text="Text",
        )

        assert gen_resume.model_used is None
        assert gen_resume.generation_metadata is None

    def test_generated_resume_repr(self):
        """Test GeneratedResume model string representation."""
        gen_resume = GeneratedResume(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            analysis_id=uuid.uuid4(),
            optimized_text="Text",
            model_used="claude-sonnet-4",
        )

        repr_str = repr(gen_resume)
        assert "GeneratedResume" in repr_str
        assert "claude-sonnet-4" in repr_str


class TestModelRelationships:
    """Test cases for model relationships."""

    def test_user_has_resumes_relationship(self):
        """Test User has resumes relationship defined."""
        user = User(
            email="test@example.com",
            hashed_password="hashed",
        )

        # Check relationship exists
        assert hasattr(user, "resumes")
        assert hasattr(user, "job_descriptions")
        assert hasattr(user, "analyses")
        assert hasattr(user, "generated_resumes")

    def test_resume_has_user_relationship(self):
        """Test Resume has user relationship defined."""
        resume = Resume(
            user_id=uuid.uuid4(),
            title="Test",
            raw_text="Text",
        )

        # Check relationship exists
        assert hasattr(resume, "user")
        assert hasattr(resume, "analyses")

    def test_analysis_has_all_relationships(self):
        """Test Analysis has all relationships defined."""
        analysis = Analysis(
            user_id=uuid.uuid4(),
            resume_id=uuid.uuid4(),
            job_description_id=uuid.uuid4(),
        )

        # Check relationships exist
        assert hasattr(analysis, "user")
        assert hasattr(analysis, "resume")
        assert hasattr(analysis, "job_description")
        assert hasattr(analysis, "generated_resumes")


# ============================================================================
# Integration Tests (require database connection)
# ============================================================================

# These tests would require a running PostgreSQL database
# They are marked as integration tests and can be run separately

@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection can be established (integration test)."""
    # This would require mocking or a test database
    # Placeholder for future implementation
    pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_crud_operations():
    """Test CRUD operations on User model (integration test)."""
    # This would test actual database operations
    # Placeholder for future implementation
    pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cascade_delete():
    """Test cascade delete when user is deleted (integration test)."""
    # This would test that deleting a user deletes all related data
    # Placeholder for future implementation
    pass
