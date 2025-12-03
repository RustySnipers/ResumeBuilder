"""
Authentication & Authorization Module - Phase 4

Provides secure authentication with JWT tokens, role-based access control,
API key management, and audit logging.
"""

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
from backend.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    get_optional_user,
    get_user_from_api_key,
    get_current_user_or_api_key,
    require_role,
    require_permission,
    verify_resource_ownership,
    oauth2_scheme,
)
from backend.auth.schemas import (
    UserRegister,
    UserLogin,
    UserResponse,
    UserUpdate,
    Token,
    TokenPayload,
    RefreshTokenRequest,
    PasswordChange,
    PasswordResetRequest,
    PasswordReset,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyInfo,
    APIKeyUpdate,
    RoleResponse,
    AuditLogResponse,
)

__all__ = [
    # Security utilities
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "generate_api_key",
    "verify_api_key_format",
    "validate_password_strength",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_optional_user",
    "get_user_from_api_key",
    "get_current_user_or_api_key",
    "require_role",
    "require_permission",
    "verify_resource_ownership",
    "oauth2_scheme",
    # Schemas
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
    "Token",
    "TokenPayload",
    "RefreshTokenRequest",
    "PasswordChange",
    "PasswordResetRequest",
    "PasswordReset",
    "APIKeyCreate",
    "APIKeyResponse",
    "APIKeyInfo",
    "APIKeyUpdate",
    "RoleResponse",
    "AuditLogResponse",
]
