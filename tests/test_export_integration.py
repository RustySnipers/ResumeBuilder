"""
Integration Tests for Phase 5 Export API Endpoints

Tests for export router endpoints with authentication and database.
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import uuid
from datetime import datetime

from main import app
from backend.database.session import Base, get_session
from backend.models.user import User
from backend.models.resume import Resume
from backend.models.role import Role
from backend.models.user_role import UserRole
from backend.auth.security import hash_password, create_access_token


# ============================================================================
# Test Database Setup
# ============================================================================

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create test database tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def test_session(test_db):
    """Get test database session."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def override_get_session(test_db):
    """Override FastAPI dependency for database session."""
    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    yield
    app.dependency_overrides.clear()


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def test_user(test_session: AsyncSession):
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password=hash_password("TestPassword123!"),
        full_name="Test User",
        is_active=True,
        is_verified=False,
        failed_login_attempts=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    # Create user role
    role = Role(
        id=uuid.uuid4(),
        name="user",
        description="Standard user role",
        permissions=["read:own", "write:own"],
        created_at=datetime.utcnow()
    )

    test_session.add(role)
    await test_session.flush()

    user_role = UserRole(
        user_id=user.id,
        role_id=role.id,
        created_at=datetime.utcnow()
    )

    test_session.add(user)
    test_session.add(user_role)
    await test_session.commit()
    await test_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def test_resume(test_session: AsyncSession, test_user: User):
    """Create a test resume."""
    resume = Resume(
        id=uuid.uuid4(),
        user_id=test_user.id,
        title="Software Engineer Resume",
        raw_text="Experienced software engineer with 5 years of experience.",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    test_session.add(resume)
    await test_session.commit()
    await test_session.refresh(resume)

    return resume


@pytest_asyncio.fixture
def auth_headers(test_user: User):
    """Create authentication headers."""
    access_token = create_access_token(
        data={"sub": test_user.email, "user_id": str(test_user.id)}
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
def client(override_get_session):
    """Create test client."""
    with TestClient(app) as c:
        yield c


# ============================================================================
# Export PDF Endpoint Tests
# ============================================================================

class TestExportPDFEndpoint:
    """Test PDF export endpoint."""

    @pytest.mark.asyncio
    async def test_export_pdf_success(self, client, auth_headers, test_resume):
        """Test successful PDF export."""
        response = client.post(
            "/api/v1/export/pdf",
            json={
                "resume_id": str(test_resume.id),
                "template": "professional",
                "format": "pdf"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["Content-Disposition"]
        assert len(response.content) > 0
        assert response.content[:4] == b'%PDF'

    @pytest.mark.asyncio
    async def test_export_pdf_without_auth(self, client, test_resume):
        """Test PDF export without authentication."""
        response = client.post(
            "/api/v1/export/pdf",
            json={
                "resume_id": str(test_resume.id),
                "template": "professional"
            }
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_pdf_invalid_resume_id(self, client, auth_headers):
        """Test PDF export with invalid resume ID."""
        response = client.post(
            "/api/v1/export/pdf",
            json={
                "resume_id": "invalid-uuid",
                "template": "professional"
            },
            headers=auth_headers
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_export_pdf_nonexistent_resume(self, client, auth_headers):
        """Test PDF export with nonexistent resume."""
        fake_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/export/pdf",
            json={
                "resume_id": fake_id,
                "template": "professional"
            },
            headers=auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_pdf_modern_template(self, client, auth_headers, test_resume):
        """Test PDF export with modern template."""
        response = client.post(
            "/api/v1/export/pdf",
            json={
                "resume_id": str(test_resume.id),
                "template": "modern"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"


# ============================================================================
# Export DOCX Endpoint Tests
# ============================================================================

class TestExportDOCXEndpoint:
    """Test DOCX export endpoint."""

    @pytest.mark.asyncio
    async def test_export_docx_success(self, client, auth_headers, test_resume):
        """Test successful DOCX export."""
        response = client.post(
            "/api/v1/export/docx",
            json={
                "resume_id": str(test_resume.id),
                "template": "professional",
                "format": "docx"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in response.headers["content-type"]
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["Content-Disposition"]
        assert len(response.content) > 0
        assert response.content[:2] == b'PK'  # ZIP/DOCX magic number

    @pytest.mark.asyncio
    async def test_export_docx_without_auth(self, client, test_resume):
        """Test DOCX export without authentication."""
        response = client.post(
            "/api/v1/export/docx",
            json={
                "resume_id": str(test_resume.id),
                "template": "professional"
            }
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_docx_invalid_resume_id(self, client, auth_headers):
        """Test DOCX export with invalid resume ID."""
        response = client.post(
            "/api/v1/export/docx",
            json={
                "resume_id": "invalid-uuid",
                "template": "professional"
            },
            headers=auth_headers
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_export_docx_nonexistent_resume(self, client, auth_headers):
        """Test DOCX export with nonexistent resume."""
        fake_id = str(uuid.uuid4())
        response = client.post(
            "/api/v1/export/docx",
            json={
                "resume_id": fake_id,
                "template": "professional"
            },
            headers=auth_headers
        )

        assert response.status_code == 404


# ============================================================================
# HTML Preview Endpoint Tests
# ============================================================================

class TestPreviewEndpoint:
    """Test HTML preview endpoint."""

    @pytest.mark.asyncio
    async def test_preview_success(self, client, auth_headers, test_resume):
        """Test successful HTML preview generation."""
        response = client.post(
            "/api/v1/export/preview",
            json={
                "resume_id": str(test_resume.id),
                "template": "professional"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert len(response.content) > 0

        # Check HTML structure
        html = response.text
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    @pytest.mark.asyncio
    async def test_preview_without_auth(self, client, test_resume):
        """Test preview without authentication."""
        response = client.post(
            "/api/v1/export/preview",
            json={
                "resume_id": str(test_resume.id),
                "template": "professional"
            }
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_preview_invalid_resume_id(self, client, auth_headers):
        """Test preview with invalid resume ID."""
        response = client.post(
            "/api/v1/export/preview",
            json={
                "resume_id": "invalid-uuid",
                "template": "professional"
            },
            headers=auth_headers
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_preview_modern_template(self, client, auth_headers, test_resume):
        """Test preview with modern template."""
        response = client.post(
            "/api/v1/export/preview",
            json={
                "resume_id": str(test_resume.id),
                "template": "modern"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


# ============================================================================
# Template Management Endpoint Tests
# ============================================================================

class TestTemplateEndpoints:
    """Test template management endpoints."""

    @pytest.mark.asyncio
    async def test_list_templates(self, client, auth_headers):
        """Test listing available templates."""
        response = client.get(
            "/api/v1/export/templates",
            headers=auth_headers
        )

        assert response.status_code == 200
        templates = response.json()

        assert isinstance(templates, list)
        assert len(templates) > 0

        # Check template structure
        for template in templates:
            assert "id" in template
            assert "name" in template
            assert "description" in template
            assert "category" in template
            assert "preview_url" in template

    @pytest.mark.asyncio
    async def test_list_templates_without_auth(self, client):
        """Test listing templates without authentication."""
        response = client.get("/api/v1/export/templates")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_template_details(self, client, auth_headers):
        """Test getting template details."""
        response = client.get(
            "/api/v1/export/templates/professional",
            headers=auth_headers
        )

        assert response.status_code == 200
        template = response.json()

        assert template["id"] == "professional"
        assert template["name"] == "Professional"
        assert "description" in template

    @pytest.mark.asyncio
    async def test_get_template_details_modern(self, client, auth_headers):
        """Test getting modern template details."""
        response = client.get(
            "/api/v1/export/templates/modern",
            headers=auth_headers
        )

        assert response.status_code == 200
        template = response.json()

        assert template["id"] == "modern"
        assert template["name"] == "Modern Professional"

    @pytest.mark.asyncio
    async def test_get_nonexistent_template(self, client, auth_headers):
        """Test getting details of nonexistent template."""
        response = client.get(
            "/api/v1/export/templates/nonexistent",
            headers=auth_headers
        )

        assert response.status_code == 404


# ============================================================================
# Authorization Tests
# ============================================================================

class TestExportAuthorization:
    """Test authorization for export endpoints."""

    @pytest_asyncio.fixture
    async def other_user(self, test_session: AsyncSession):
        """Create another test user."""
        user = User(
            id=uuid.uuid4(),
            email="other@example.com",
            hashed_password=hash_password("TestPassword123!"),
            full_name="Other User",
            is_active=True,
            is_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Create user role
        role = Role(
            id=uuid.uuid4(),
            name="user",
            description="Standard user role",
            permissions=["read:own", "write:own"],
            created_at=datetime.utcnow()
        )

        test_session.add(role)
        await test_session.flush()

        user_role = UserRole(
            user_id=user.id,
            role_id=role.id,
            created_at=datetime.utcnow()
        )

        test_session.add(user)
        test_session.add(user_role)
        await test_session.commit()
        await test_session.refresh(user)

        return user

    @pytest_asyncio.fixture
    def other_user_headers(self, other_user: User):
        """Create authentication headers for other user."""
        access_token = create_access_token(
            data={"sub": other_user.email, "user_id": str(other_user.id)}
        )
        return {"Authorization": f"Bearer {access_token}"}

    @pytest.mark.asyncio
    async def test_export_pdf_unauthorized_user(self, client, other_user_headers, test_resume):
        """Test that user cannot export another user's resume."""
        response = client.post(
            "/api/v1/export/pdf",
            json={
                "resume_id": str(test_resume.id),
                "template": "professional"
            },
            headers=other_user_headers
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_export_docx_unauthorized_user(self, client, other_user_headers, test_resume):
        """Test that user cannot export another user's resume as DOCX."""
        response = client.post(
            "/api/v1/export/docx",
            json={
                "resume_id": str(test_resume.id),
                "template": "professional"
            },
            headers=other_user_headers
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_preview_unauthorized_user(self, client, other_user_headers, test_resume):
        """Test that user cannot preview another user's resume."""
        response = client.post(
            "/api/v1/export/preview",
            json={
                "resume_id": str(test_resume.id),
                "template": "professional"
            },
            headers=other_user_headers
        )

        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
