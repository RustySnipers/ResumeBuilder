# Phase 4: Authentication & Authorization - Implementation Plan

## Overview

Implement secure user authentication and authorization system with JWT tokens, role-based access control, API key management, and audit logging.

**Status:** Planning
**Priority:** High
**Estimated Time:** 2-3 days
**Dependencies:** Phase 2.1 (Database) ✅

---

## Goals

### Primary Objectives
1. **User Authentication**: Secure login with JWT tokens
2. **User Management**: Registration, profile, password reset
3. **Authorization**: Role-based access control (RBAC)
4. **API Keys**: Developer API key generation and management
5. **Rate Limiting**: Per-user rate limiting
6. **Audit Logging**: Security compliance logging

### Quality Gates
- [ ] 100% test coverage for auth flows
- [ ] Password security (bcrypt, min complexity)
- [ ] JWT token validation and refresh
- [ ] Role enforcement on all protected endpoints
- [ ] Rate limiting per user (not just global)
- [ ] Audit logs for security events

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Middleware                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │     Auth     │  │  API Keys    │  │ Rate Limit   │ │
│  │  Middleware  │  │  Middleware  │  │  Middleware  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │             Authentication Service                │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ - JWT token generation/validation                │  │
│  │ - Password hashing (bcrypt)                      │  │
│  │ - User session management                        │  │
│  │ - OAuth2 password flow                           │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │             Authorization Service                 │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ - Role-based access control (RBAC)               │  │
│  │ - Permission checking                            │  │
│  │ - Resource ownership validation                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │                Audit Service                      │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ - Login/logout tracking                          │  │
│  │ - API access logging                             │  │
│  │ - Security event logging                         │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Database Schema Updates

### New Tables

#### 1. API Keys Table
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    prefix VARCHAR(20) NOT NULL,  -- First 8 chars for identification
    scopes JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_api_keys_user_id (user_id),
    INDEX idx_api_keys_prefix (prefix),
    INDEX idx_api_keys_key_hash (key_hash)
);
```

#### 2. Roles Table
```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    permissions JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Default roles
INSERT INTO roles (name, description, permissions) VALUES
('user', 'Standard user', '["read:own", "write:own"]'),
('premium', 'Premium user', '["read:own", "write:own", "unlimited:generations"]'),
('admin', 'Administrator', '["read:all", "write:all", "delete:all", "manage:users"]');
```

#### 3. User Roles Table
```sql
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id, role_id),
    INDEX idx_user_roles_user_id (user_id)
);
```

#### 4. Audit Logs Table
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,  -- login, logout, api_access, etc.
    resource VARCHAR(100),          -- users, resumes, etc.
    resource_id UUID,
    ip_address VARCHAR(45),
    user_agent TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_audit_logs_user_id (user_id),
    INDEX idx_audit_logs_action (action),
    INDEX idx_audit_logs_created_at (created_at)
);
```

#### 5. Sessions Table (Optional - for refresh tokens)
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL UNIQUE,
    device_info TEXT,
    ip_address VARCHAR(45),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_sessions_user_id (user_id),
    INDEX idx_sessions_expires_at (expires_at)
);
```

### Model Updates

Update `User` model with new fields:
```python
class User(Base):
    # Existing fields...

    # New fields for Phase 4
    password_hash = Column(String(255), nullable=False)  # Rename from hashed_password
    email_verified_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)

    # Relationships
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
```

---

## Implementation Plan

### Step 1: Authentication Core (Day 1 Morning)

**Files to Create:**
- `backend/auth/security.py` - Password hashing, JWT utilities
- `backend/auth/dependencies.py` - FastAPI dependencies for auth
- `backend/auth/schemas.py` - Pydantic models for auth

**Key Functions:**
```python
# security.py
def hash_password(password: str) -> str
def verify_password(plain: str, hashed: str) -> bool
def create_access_token(data: dict, expires_delta: timedelta) -> str
def create_refresh_token(data: dict) -> str
def verify_token(token: str) -> dict

# dependencies.py
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User
async def get_current_active_user(user: User = Depends(get_current_user)) -> User
async def require_role(role: str)
```

### Step 2: User Management (Day 1 Afternoon)

**Files to Create:**
- `backend/auth/router.py` - Auth endpoints
- `backend/repositories/auth_repository.py` - Auth data access

**Endpoints:**
- `POST /auth/register` - User registration
- `POST /auth/login` - User login (returns JWT)
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout (invalidate tokens)
- `GET /auth/me` - Get current user profile
- `PUT /auth/me` - Update user profile
- `POST /auth/change-password` - Change password
- `POST /auth/forgot-password` - Request password reset
- `POST /auth/reset-password` - Reset password with token

### Step 3: Role-Based Access Control (Day 2 Morning)

**Files to Create:**
- `backend/auth/permissions.py` - Permission definitions
- `backend/auth/rbac.py` - RBAC enforcement
- `backend/models/role.py` - Role model
- `backend/models/user_role.py` - User-Role association

**Permission System:**
```python
class Permission(str, Enum):
    READ_OWN = "read:own"
    WRITE_OWN = "write:own"
    DELETE_OWN = "delete:own"
    READ_ALL = "read:all"
    WRITE_ALL = "write:all"
    DELETE_ALL = "delete:all"
    MANAGE_USERS = "manage:users"
    UNLIMITED_GENERATIONS = "unlimited:generations"

def has_permission(user: User, permission: Permission, resource: Any = None) -> bool
```

### Step 4: API Key Management (Day 2 Afternoon)

**Files to Create:**
- `backend/auth/api_keys.py` - API key generation/validation
- `backend/models/api_key.py` - APIKey model
- `backend/repositories/api_key_repository.py` - API key data access

**Endpoints:**
- `POST /auth/api-keys` - Generate new API key
- `GET /auth/api-keys` - List user's API keys
- `DELETE /auth/api-keys/{key_id}` - Revoke API key
- `PUT /auth/api-keys/{key_id}` - Update API key (name, scopes)

**API Key Format:**
```
rb_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
│   │    └─────────────────────────────────────┘
│   │                    │
│   │                    └─ Random token (SHA-256 hashed in DB)
│   └─ Environment (live/test)
└─ Prefix (resumebuilder)
```

### Step 5: Rate Limiting Per User (Day 3 Morning)

**Files to Create:**
- `backend/auth/rate_limiter.py` - User-based rate limiting
- `backend/middleware/rate_limit.py` - Rate limit middleware

**Implementation:**
```python
class UserRateLimiter:
    """Rate limiter with per-user quotas based on role"""

    RATE_LIMITS = {
        "user": {"requests_per_minute": 10, "requests_per_day": 100},
        "premium": {"requests_per_minute": 50, "requests_per_day": 1000},
        "admin": {"requests_per_minute": 100, "requests_per_day": 10000},
    }

    async def check_rate_limit(self, user: User, endpoint: str) -> bool
```

### Step 6: Audit Logging (Day 3 Afternoon)

**Files to Create:**
- `backend/auth/audit.py` - Audit logging service
- `backend/models/audit_log.py` - AuditLog model
- `backend/middleware/audit.py` - Audit middleware

**Logged Events:**
- User registration
- Login/logout
- Failed login attempts
- Password changes
- API key creation/revocation
- Protected resource access
- Permission denied events
- Account lockouts

---

## Security Considerations

### Password Security
- **Hashing**: bcrypt with cost factor 12
- **Min Length**: 8 characters
- **Complexity**: Require uppercase, lowercase, number, special char
- **Validation**: Check against common password lists
- **Reset**: Time-limited tokens (1 hour expiry)

### JWT Tokens
- **Access Token**: Short-lived (15 minutes)
- **Refresh Token**: Long-lived (7 days), stored in DB
- **Algorithm**: RS256 (asymmetric) or HS256 (symmetric)
- **Claims**: user_id, email, roles, exp, iat
- **Revocation**: Store refresh tokens, allow revocation

### API Keys
- **Generation**: Cryptographically secure random tokens
- **Storage**: Hash in database (SHA-256)
- **Scopes**: Limit permissions per key
- **Expiration**: Optional expiry date
- **Rate Limiting**: Same as user rate limits

### Account Protection
- **Lockout**: 5 failed attempts → 15 minute lockout
- **Brute Force**: Rate limit login endpoint
- **Email Verification**: Required before full access
- **Session Management**: Limit concurrent sessions

---

## API Examples

### Registration
```bash
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecureP@ss123",
  "full_name": "John Doe"
}

Response: 201 Created
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "is_verified": false,
  "created_at": "2025-11-30T10:00:00Z"
}
```

### Login
```bash
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=SecureP@ss123

Response: 200 OK
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Protected Endpoint
```bash
GET /api/v1/resumes
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

Response: 200 OK
{
  "resumes": [...]
}
```

### API Key Usage
```bash
GET /api/v1/resumes
X-API-Key: rb_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

Response: 200 OK
{
  "resumes": [...]
}
```

---

## Testing Strategy

### Unit Tests
- Password hashing and verification
- JWT token generation and validation
- Permission checking
- Rate limiting logic
- API key generation and validation

### Integration Tests
- User registration flow
- Login/logout flow
- Token refresh flow
- Password reset flow
- Protected endpoint access
- Role-based authorization
- API key authentication
- Rate limit enforcement

### Security Tests
- Brute force protection
- SQL injection attempts
- XSS in user inputs
- JWT tampering
- Expired token handling
- Invalid token handling

---

## Dependencies

**New Packages:**
```txt
python-jose[cryptography]==3.3.0  # JWT handling
passlib[bcrypt]==1.7.4            # Password hashing
python-multipart==0.0.6           # Form data parsing
```

---

## Migration Plan

### Database Migrations
1. Create new tables (api_keys, roles, user_roles, audit_logs, sessions)
2. Add new columns to users table
3. Insert default roles
4. Migrate existing users to default "user" role

### API Migration
1. Add authentication to existing endpoints gradually
2. Maintain backward compatibility with optional auth
3. Deprecate unauthenticated access over 30 days
4. Full authentication required after deprecation period

---

## Success Criteria

- [ ] Users can register and login
- [ ] JWT tokens work for authentication
- [ ] Refresh tokens allow token renewal
- [ ] Role-based authorization enforced
- [ ] API keys can be generated and used
- [ ] Rate limiting works per user/role
- [ ] Audit logs capture security events
- [ ] All tests passing (>95% coverage)
- [ ] Security vulnerabilities addressed
- [ ] Documentation complete

---

## Timeline

**Day 1:**
- Morning: Authentication core (JWT, passwords)
- Afternoon: User management endpoints

**Day 2:**
- Morning: RBAC implementation
- Afternoon: API key management

**Day 3:**
- Morning: Per-user rate limiting
- Afternoon: Audit logging and testing

---

## Next Steps After Phase 4

With authentication complete, enable:
- User-specific resume storage
- Resume history per user
- Usage analytics per user
- Billing/subscription management (future)
- Team/organization support (future)

---

**Status:** Ready to implement
**Priority:** High (required for production)
**Risk:** Low (well-established patterns)
