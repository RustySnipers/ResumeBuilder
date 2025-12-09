"""
Authentication Schemas - Phase 4

Pydantic models for authentication requests and responses.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============================================================================
# User Registration & Login
# ============================================================================

class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=100)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        from backend.auth.security import validate_password_strength

        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


class UserLogin(BaseModel):
    """User login request (OAuth2 password flow)"""
    username: EmailStr  # OAuth2 spec uses 'username' field
    password: str


class UserResponse(BaseModel):
    """User profile response"""
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User profile update"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None


# ============================================================================
# JWT Tokens
# ============================================================================

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until access token expires


class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str  # Subject (user_id)
    email: str
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    type: str  # "access" or "refresh"


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


# ============================================================================
# Password Management
# ============================================================================

class PasswordChange(BaseModel):
    """Password change request"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str, info) -> str:
        """Validate new password strength"""
        from backend.auth.security import validate_password_strength

        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)

        # Ensure new password is different from current
        if 'current_password' in info.data and v == info.data['current_password']:
            raise ValueError("New password must be different from current password")

        return v


class PasswordResetRequest(BaseModel):
    """Request password reset"""
    email: EmailStr


class PasswordReset(BaseModel):
    """Reset password with token"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate password strength"""
        from backend.auth.security import validate_password_strength

        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


# ============================================================================
# Email Verification
# ============================================================================

class EmailVerificationRequest(BaseModel):
    """Request email verification"""
    email: EmailStr


class EmailVerificationConfirm(BaseModel):
    """Confirm email with token"""
    token: str


class EmailVerificationResponse(BaseModel):
    """Email verification response"""
    message: str
    email_verified: bool = False


# ============================================================================
# API Keys
# ============================================================================

class APIKeyCreate(BaseModel):
    """Create API key request"""
    name: str = Field(..., min_length=1, max_length=100)
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    """API key response (only shown once on creation)"""
    id: UUID
    name: str
    key: str  # Full key (only returned on creation)
    prefix: str
    scopes: List[str]
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyInfo(BaseModel):
    """API key info (without the actual key)"""
    id: UUID
    name: str
    prefix: str
    scopes: List[str]
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyUpdate(BaseModel):
    """Update API key"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    scopes: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ============================================================================
# Roles & Permissions
# ============================================================================

class RoleResponse(BaseModel):
    """Role response"""
    id: UUID
    name: str
    description: Optional[str]
    permissions: List[str]

    class Config:
        from_attributes = True


# ============================================================================
# Audit Logs
# ============================================================================

class AuditLogResponse(BaseModel):
    """Audit log entry"""
    id: UUID
    user_id: Optional[UUID]
    action: str
    resource: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    meta_data: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True
