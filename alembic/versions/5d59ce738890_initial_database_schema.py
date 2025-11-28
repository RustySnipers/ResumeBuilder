"""Initial database schema

Revision ID: 5d59ce738890
Revises:
Create Date: 2025-11-28 22:02:05.072163

Creates tables for:
- users: User authentication and management
- resumes: Resume storage with versioning
- job_descriptions: Job description storage
- analyses: Gap analysis results
- generated_resumes: LLM-generated optimized resumes
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '5d59ce738890'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('is_verified', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'])

    # Create resumes table
    op.create_table(
        'resumes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('redacted_text', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), default=1, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_resumes_id', 'resumes', ['id'])
    op.create_index('ix_resumes_user_id', 'resumes', ['user_id'])
    op.create_index('ix_user_resumes', 'resumes', ['user_id', 'created_at'])

    # Create job_descriptions table
    op.create_table(
        'job_descriptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('position_title', sa.String(255), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('redacted_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_job_descriptions_id', 'job_descriptions', ['id'])
    op.create_index('ix_job_descriptions_user_id', 'job_descriptions', ['user_id'])

    # Create analyses table
    op.create_table(
        'analyses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('resume_id', UUID(as_uuid=True), nullable=False),
        sa.Column('job_description_id', UUID(as_uuid=True), nullable=False),
        sa.Column('missing_keywords', JSONB, nullable=True),
        sa.Column('suggestions', JSONB, nullable=True),
        sa.Column('match_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('semantic_similarity', sa.Numeric(5, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_description_id'], ['job_descriptions.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_analyses_id', 'analyses', ['id'])
    op.create_index('ix_analyses_user_id', 'analyses', ['user_id'])
    op.create_index('ix_analyses_resume_id', 'analyses', ['resume_id'])
    op.create_index('ix_analyses_job_description_id', 'analyses', ['job_description_id'])
    op.create_index('ix_analyses_created_at', 'analyses', ['created_at'])

    # Create generated_resumes table
    op.create_table(
        'generated_resumes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('analysis_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('optimized_text', sa.Text(), nullable=False),
        sa.Column('model_used', sa.String(50), nullable=True),
        sa.Column('generation_metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_generated_resumes_id', 'generated_resumes', ['id'])
    op.create_index('ix_generated_resumes_analysis_id', 'generated_resumes', ['analysis_id'])
    op.create_index('ix_generated_resumes_user_id', 'generated_resumes', ['user_id'])
    op.create_index('ix_generated_resumes_created_at', 'generated_resumes', ['created_at'])


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table('generated_resumes')
    op.drop_table('analyses')
    op.drop_table('job_descriptions')
    op.drop_table('resumes')
    op.drop_table('users')
