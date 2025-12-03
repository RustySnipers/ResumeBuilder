"""
Authentication Unit Tests - Phase 4

Tests for core authentication utilities (password hashing, JWT tokens, API keys).
"""

import pytest
from datetime import datetime, timedelta
from backend.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_api_key,
    verify_api_key_format,
    validate_password_strength,
)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing produces different hashes."""
        password = "SecureP@ss123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Same password should produce different hashes (bcrypt salt)
        assert hash1 != hash2
        assert len(hash1) > 0
        assert hash1.startswith("$2b$")  # Bcrypt prefix

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "SecureP@ss123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "SecureP@ss123"
        wrong_password = "WrongP@ss456"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """Test password verification with empty password."""
        password = "SecureP@ss123"
        hashed = hash_password(password)

        assert verify_password("", hashed) is False


class TestPasswordStrength:
    """Test password strength validation."""

    def test_valid_strong_password(self):
        """Test validation of strong password."""
        passwords = [
            "SecureP@ss123",
            "MyP@ssw0rd!",
            "Test1234!@#$",
            "Str0ng!Pass",
        ]
        for password in passwords:
            is_valid, error = validate_password_strength(password)
            assert is_valid is True
            assert error is None

    def test_password_too_short(self):
        """Test password that's too short."""
        is_valid, error = validate_password_strength("Short1!")
        assert is_valid is False
        assert "at least 8 characters" in error

    def test_password_no_uppercase(self):
        """Test password without uppercase letter."""
        is_valid, error = validate_password_strength("password123!")
        assert is_valid is False
        assert "uppercase letter" in error

    def test_password_no_lowercase(self):
        """Test password without lowercase letter."""
        is_valid, error = validate_password_strength("PASSWORD123!")
        assert is_valid is False
        assert "lowercase letter" in error

    def test_password_no_number(self):
        """Test password without number."""
        is_valid, error = validate_password_strength("Password!")
        assert is_valid is False
        assert "number" in error

    def test_password_no_special_char(self):
        """Test password without special character."""
        is_valid, error = validate_password_strength("Password123")
        assert is_valid is False
        assert "special character" in error

    def test_common_password(self):
        """Test detection of common passwords."""
        common_passwords = ["Password123!", "Admin123!", "Welcome123!"]
        for password in common_passwords:
            is_valid, error = validate_password_strength(password)
            assert is_valid is False
            assert "common password" in error


class TestJWTTokens:
    """Test JWT token generation and verification."""

    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_refresh_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_access_token(self):
        """Test access token verification."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        payload = verify_token(token, expected_type="access")

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_refresh_token(self):
        """Test refresh token verification."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_refresh_token(data)
        payload = verify_token(token, expected_type="refresh")

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "refresh"

    def test_verify_token_wrong_type(self):
        """Test token verification with wrong type."""
        data = {"sub": "user123", "email": "test@example.com"}
        access_token = create_access_token(data)

        # Try to verify access token as refresh token
        payload = verify_token(access_token, expected_type="refresh")
        assert payload is None

    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)

        assert payload is None

    def test_verify_expired_token(self):
        """Test verification of expired token."""
        data = {"sub": "user123", "email": "test@example.com"}
        # Create token with negative expiry (already expired)
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        import time
        time.sleep(2)  # Wait to ensure expiry

        payload = verify_token(token)
        assert payload is None

    def test_token_contains_custom_data(self):
        """Test that custom data is preserved in token."""
        data = {
            "sub": "user123",
            "email": "test@example.com",
            "custom_field": "custom_value",
        }
        token = create_access_token(data)
        payload = verify_token(token, expected_type="access")

        assert payload["custom_field"] == "custom_value"


class TestAPIKeys:
    """Test API key generation and validation."""

    def test_generate_api_key(self):
        """Test API key generation."""
        full_key, key_hash, prefix = generate_api_key()

        # Check full key format
        assert full_key.startswith("rb_")
        assert len(full_key) > 20

        # Check key hash (SHA-256 produces 64 hex chars)
        assert len(key_hash) == 64
        assert all(c in "0123456789abcdef" for c in key_hash)

        # Check prefix (first 8 chars of random token)
        assert len(prefix) == 8

    def test_generate_unique_keys(self):
        """Test that generated keys are unique."""
        key1_full, key1_hash, key1_prefix = generate_api_key()
        key2_full, key2_hash, key2_prefix = generate_api_key()

        assert key1_full != key2_full
        assert key1_hash != key2_hash
        # Prefixes might collide but very unlikely

    def test_verify_api_key_format_valid(self):
        """Test API key format validation with valid keys."""
        full_key, _, _ = generate_api_key()
        assert verify_api_key_format(full_key) is True

    def test_verify_api_key_format_invalid(self):
        """Test API key format validation with invalid keys."""
        invalid_keys = [
            "invalid_key",
            "rb_",
            "rb_short",
            "",
            "notstartwithprefix",
            "rb_test_toolong" + "x" * 100,
        ]
        for key in invalid_keys:
            assert verify_api_key_format(key) is False

    def test_api_key_hash_consistency(self):
        """Test that hashing the same key produces same hash."""
        import hashlib

        full_key, key_hash, _ = generate_api_key()

        # Re-hash the full key
        rehashed = hashlib.sha256(full_key.encode()).hexdigest()

        assert rehashed == key_hash


class TestSecurityEdgeCases:
    """Test edge cases and security scenarios."""

    def test_empty_password_hash(self):
        """Test hashing empty password."""
        with pytest.raises(Exception):
            hash_password("")

    def test_very_long_password(self):
        """Test hashing very long password."""
        long_password = "A1!" + "x" * 1000
        hashed = hash_password(long_password)
        assert verify_password(long_password, hashed) is True

    def test_unicode_password(self):
        """Test password with unicode characters."""
        unicode_password = "Pāssw0rd!🔒"
        hashed = hash_password(unicode_password)
        assert verify_password(unicode_password, hashed) is True

    def test_token_without_sub(self):
        """Test token creation without 'sub' field."""
        data = {"email": "test@example.com"}
        token = create_access_token(data)
        payload = verify_token(token)

        # Should still create token, but sub will be None
        assert payload is not None
        assert "sub" not in payload or payload.get("sub") is None

    def test_sql_injection_in_password(self):
        """Test that SQL injection attempts in passwords are safely handled."""
        malicious_password = "'; DROP TABLE users; --"
        hashed = hash_password(malicious_password)

        # Should hash safely without executing SQL
        assert verify_password(malicious_password, hashed) is True
        assert "DROP TABLE" in malicious_password  # Original is preserved


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
