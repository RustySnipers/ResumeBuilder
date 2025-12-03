"""Email verification and password reset tokens

Revision ID: b3c4d5e6f7g8
Revises: a8b9c0d1e2f3
Create Date: 2025-12-02 14:30:00

Adds verification_tokens table for:
- Email verification tokens
- Password reset tokens
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7g8'
down_revision: Union[str, None] = 'a8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add verification_tokens table."""

    # Create token_type enum
    op.execute("""
        CREATE TYPE tokentype AS ENUM ('email_verification', 'password_reset')
    """)

    # Create verification_tokens table
    op.create_table(
        'verification_tokens',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(64), unique=True, nullable=False),
        sa.Column('token_type', sa.Enum('email_verification', 'password_reset', name='tokentype'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('ix_verification_tokens_id', 'verification_tokens', ['id'])
    op.create_index('ix_verification_tokens_user_id', 'verification_tokens', ['user_id'])
    op.create_index('ix_verification_tokens_token', 'verification_tokens', ['token'])
    op.create_index('ix_verification_tokens_expires_at', 'verification_tokens', ['expires_at'])


def downgrade() -> None:
    """Remove verification_tokens table."""

    # Drop indexes
    op.drop_index('ix_verification_tokens_expires_at', table_name='verification_tokens')
    op.drop_index('ix_verification_tokens_token', table_name='verification_tokens')
    op.drop_index('ix_verification_tokens_user_id', table_name='verification_tokens')
    op.drop_index('ix_verification_tokens_id', table_name='verification_tokens')

    # Drop table
    op.drop_table('verification_tokens')

    # Drop enum
    op.execute('DROP TYPE tokentype')
