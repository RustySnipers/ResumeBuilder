"""Phase 4: Authentication & Authorization Tables

Revision ID: a8b9c0d1e2f3
Revises: 5d59ce738890
Create Date: 2025-12-01 11:20:49

Adds tables and columns for Phase 4:
- roles: User roles for RBAC
- user_roles: Many-to-many user-role association
- api_keys: API key authentication
- audit_logs: Security and compliance logging
- sessions: Refresh token management
- Updates users table with new auth fields
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = '5d59ce738890'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Phase 4 authentication tables and update users table."""

    # Add new columns to users table
    op.add_column('users', sa.Column('full_name', sa.String(100), nullable=False, server_default=''))
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))

    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', JSONB, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_roles_id', 'roles', ['id'])
    op.create_index('ix_roles_name', 'roles', ['name'])

    # Insert default roles
    op.execute("""
        INSERT INTO roles (id, name, description, permissions, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'user', 'Standard user', '["read:own", "write:own"]'::jsonb, NOW(), NOW()),
            (gen_random_uuid(), 'premium', 'Premium user', '["read:own", "write:own", "unlimited:generations"]'::jsonb, NOW(), NOW()),
            (gen_random_uuid(), 'admin', 'Administrator', '["read:all", "write:all", "delete:all", "manage:users"]'::jsonb, NOW(), NOW())
    """)

    # Create user_roles table (many-to-many)
    op.create_table(
        'user_roles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'role_id', name='unique_user_role'),
    )
    op.create_index('ix_user_roles_id', 'user_roles', ['id'])
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'])
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'])

    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('key_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('prefix', sa.String(20), nullable=False),
        sa.Column('scopes', JSONB, nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_api_keys_id', 'api_keys', ['id'])
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'])
    op.create_index('ix_api_keys_prefix', 'api_keys', ['prefix'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource', sa.String(100), nullable=True),
        sa.Column('resource_id', UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('refresh_token_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('device_info', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_sessions_id', 'sessions', ['id'])
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('ix_sessions_refresh_token_hash', 'sessions', ['refresh_token_hash'])
    op.create_index('ix_sessions_expires_at', 'sessions', ['expires_at'])


def downgrade() -> None:
    """Remove Phase 4 authentication tables and columns."""

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('sessions')
    op.drop_table('audit_logs')
    op.drop_table('api_keys')
    op.drop_table('user_roles')
    op.drop_table('roles')

    # Remove columns from users table
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'full_name')
