"""
Authentication Integration Tests - Phase 4

Tests for authentication API endpoints and database integration.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import asyncio

from main import app
from backend.database.session import get_session
from backend.database import Base
from backend.models.user import User
from backend.models.role import Role
from backend.repositories.user_repository import UserRepository
from backend.repositories.role_repository import RoleRepository
from backend.auth.security import hash_password


# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def async_session():
    """Create async test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        # Create default roles
        role_repo = RoleRepository(session)
        await session.execute(
            """
            INSERT OR IGNORE INTO roles (id, name, description, permissions, created_at, updated_at)
            VALUES
                (hex(randomblob(16)), 'user', 'Standard user', '["read:own", "write:own"]', datetime('now'), datetime('now')),
                (hex(randomblob(16)), 'premium', 'Premium user', '["read:own", "write:own", "unlimited:generations"]', datetime('now'), datetime('now')),
                (hex(randomblob(16)), 'admin', 'Administrator', '["read:all", "write:all", "delete:all", "manage:users"]', datetime('now'), datetime('now'))
            """
        )
        await session.commit()

        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client(async_session):
    """Create test client with database override."""

    async def override_get_session():
        yield async_session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(async_session):
    """Create a test user."""
    user_repo = UserRepository(async_session)
    user = await user_repo.create(
        email="testuser@example.com",
        full_name="Test User",
        hashed_password=hash_password("TestP@ss123"),
    )

    # Assign default role
    role_repo = RoleRepository(async_session)
    default_role = await role_repo.get_by_name("user")
    if default_role:
        await role_repo.assign_role_to_user(user.id, default_role.id)

    await async_session.commit()
    await async_session.refresh(user)
    return user


class TestUserRegistration:
    """Test user registration endpoint."""

    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecureP@ss123",
                "full_name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["is_active"] is True
        assert data["is_verified"] is False
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email."""
        response = client.post(
            "/auth/register",
            json={
                "email": test_user.email,
                "password": "SecureP@ss123",
                "full_name": "Duplicate User",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post(
            "/auth/register",
            json={
                "email": "weakpass@example.com",
                "password": "weak",
                "full_name": "Weak Pass User",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post(
            "/auth/register",
            json={
                "email": "notanemail",
                "password": "SecureP@ss123",
                "full_name": "Invalid Email User",
            },
        )

        assert response.status_code == 422

    def test_register_missing_fields(self, client):
        """Test registration with missing required fields."""
        response = client.post(
            "/auth/register",
            json={"email": "incomplete@example.com"},
        )

        assert response.status_code == 422


class TestUserLogin:
    """Test user login endpoint."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "TestP@ss123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    def test_login_wrong_password(self, client, test_user):
        """Test login with incorrect password."""
        response = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "WrongP@ss456",
            },
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post(
            "/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "TestP@ss123",
            },
        )

        assert response.status_code == 401

    def test_login_inactive_user(self, client, async_session, test_user):
        """Test login with inactive user account."""
        # Deactivate user
        user_repo = UserRepository(async_session)
        asyncio.run(user_repo.update(test_user.id, is_active=False))
        asyncio.run(async_session.commit())

        response = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "TestP@ss123",
            },
        )

        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()


class TestTokenRefresh:
    """Test token refresh endpoint."""

    def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh."""
        # Login first
        login_response = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "TestP@ss123",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != login_response.json()["access_token"]
        assert data["refresh_token"] != refresh_token

    def test_refresh_token_invalid(self, client):
        """Test refresh with invalid token."""
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401

    def test_refresh_token_access_token(self, client, test_user):
        """Test refresh using access token (should fail)."""
        # Login first
        login_response = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "TestP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]

        # Try to refresh with access token (wrong type)
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401


class TestUserProfile:
    """Test user profile endpoints."""

    def test_get_profile_success(self, client, test_user):
        """Test getting current user profile."""
        # Login
        login_response = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "TestP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]

        # Get profile
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
        assert "password" not in data
        assert "hashed_password" not in data

    def test_get_profile_no_token(self, client):
        """Test getting profile without authentication."""
        response = client.get("/auth/me")

        assert response.status_code == 401

    def test_get_profile_invalid_token(self, client):
        """Test getting profile with invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid.token"},
        )

        assert response.status_code == 401

    def test_update_profile_success(self, client, test_user):
        """Test updating user profile."""
        # Login
        login_response = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "TestP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]

        # Update profile
        response = client.put(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"full_name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["email"] == test_user.email

    def test_update_profile_email_conflict(self, client, test_user, async_session):
        """Test updating profile with conflicting email."""
        # Create another user
        user_repo = UserRepository(async_session)
        other_user = asyncio.run(
            user_repo.create(
                email="other@example.com",
                full_name="Other User",
                hashed_password=hash_password("TestP@ss123"),
            )
        )
        asyncio.run(async_session.commit())

        # Login as test_user
        login_response = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "TestP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]

        # Try to update email to other user's email
        response = client.put(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"email": other_user.email},
        )

        assert response.status_code == 400
        assert "already in use" in response.json()["detail"].lower()


class TestPasswordManagement:
    """Test password change endpoint."""

    def test_change_password_success(self, client, test_user):
        """Test successful password change."""
        # Login
        login_response = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "TestP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]

        # Change password
        response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "TestP@ss123",
                "new_password": "NewP@ss456",
            },
        )

        assert response.status_code == 204

        # Verify can login with new password
        new_login = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "NewP@ss456",
            },
        )
        assert new_login.status_code == 200

        # Verify cannot login with old password
        old_login = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "TestP@ss123",
            },
        )
        assert old_login.status_code == 401

    def test_change_password_wrong_current(self, client, test_user):
        """Test password change with wrong current password."""
        # Login
        login_response = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "TestP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]

        # Try to change with wrong current password
        response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "WrongP@ss000",
                "new_password": "NewP@ss456",
            },
        )

        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    def test_change_password_weak_new(self, client, test_user):
        """Test password change with weak new password."""
        # Login
        login_response = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "TestP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]

        # Try to change to weak password
        response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "TestP@ss123",
                "new_password": "weak",
            },
        )

        assert response.status_code == 422  # Validation error


class TestLogout:
    """Test logout endpoint."""

    def test_logout_success(self, client, test_user):
        """Test successful logout."""
        # Login
        login_response = client.post(
            "/auth/login",
            data={
                "username": test_user.email,
                "password": "TestP@ss123",
            },
        )
        access_token = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        # Logout
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 204

        # Verify refresh token no longer works
        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 401


class TestPasswordReset:
    """Test password reset endpoints."""

    def test_forgot_password(self, client, test_user):
        """Test forgot password request (always returns success)."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": test_user.email},
        )

        assert response.status_code == 202

    def test_forgot_password_nonexistent(self, client):
        """Test forgot password with non-existent email."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )

        # Should still return success to prevent email enumeration
        assert response.status_code == 202

    def test_reset_password_not_implemented(self, client):
        """Test password reset (not fully implemented yet)."""
        response = client.post(
            "/auth/reset-password",
            json={
                "token": "some_token",
                "new_password": "NewP@ss123",
            },
        )

        assert response.status_code == 501


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
