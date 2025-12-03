"""phase_6_analytics_tables

Revision ID: c4d5e6f7g8h9
Revises: b3c4d5e6f7g8
Create Date: 2025-12-03

Phase 6: Analytics Dashboard
- Create user_activities table for activity tracking
- Create analysis_metrics table for analysis result tracking
- Create export_metrics table for export operation tracking
- Create daily_metrics table for aggregated statistics
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = 'c4d5e6f7g8h9'
down_revision = 'b3c4d5e6f7g8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create analytics tables"""

    # Create activity_type_enum
    activity_type_enum = sa.Enum(
        'login', 'logout', 'register', 'password_change', 'password_reset', 'email_verified',
        'resume_created', 'resume_updated', 'resume_deleted', 'resume_analyzed',
        'generation_started', 'generation_completed', 'generation_failed', 'generation_stream_started',
        'export_pdf', 'export_docx', 'export_html',
        'job_description_created', 'job_description_updated', 'job_description_deleted',
        'api_request', 'api_key_created', 'api_key_revoked',
        name='activity_type_enum',
        create_type=True
    )
    activity_type_enum.create(op.get_bind())

    # Create export_format_enum
    export_format_enum = sa.Enum(
        'pdf', 'docx', 'html',
        name='export_format_enum',
        create_type=True
    )
    export_format_enum.create(op.get_bind())

    # Create user_activities table
    op.create_table(
        'user_activities',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('activity_type', sa.Enum(name='activity_type_enum'), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('endpoint', sa.String(200), nullable=True),
        sa.Column('method', sa.String(10), nullable=True),
        sa.Column('status_code', sa.Integer, nullable=True),
        sa.Column('response_time_ms', sa.Integer, nullable=True),
        sa.Column('metadata', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes for user_activities
    op.create_index('idx_user_activity_type', 'user_activities', ['user_id', 'activity_type'])
    op.create_index('idx_user_created_at', 'user_activities', ['user_id', 'created_at'])
    op.create_index('idx_activity_created_at', 'user_activities', ['activity_type', 'created_at'])
    op.create_index('idx_ua_user_id', 'user_activities', ['user_id'])
    op.create_index('idx_ua_activity_type', 'user_activities', ['activity_type'])
    op.create_index('idx_ua_created_at', 'user_activities', ['created_at'])

    # Create analysis_metrics table
    op.create_table(
        'analysis_metrics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('analysis_id', UUID(as_uuid=True), sa.ForeignKey('analyses.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resume_id', UUID(as_uuid=True), sa.ForeignKey('resumes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('job_description_id', UUID(as_uuid=True), sa.ForeignKey('job_descriptions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('match_score', sa.Float, nullable=False),
        sa.Column('semantic_similarity', sa.Float, nullable=True),
        sa.Column('keyword_count', sa.Integer, default=0),
        sa.Column('matched_keywords', sa.Integer, default=0),
        sa.Column('missing_keywords', sa.Integer, default=0),
        sa.Column('gap_count', sa.Integer, default=0),
        sa.Column('processing_time_ms', sa.Integer, nullable=False),
        sa.Column('llm_used', sa.Boolean, default=False),
        sa.Column('llm_cost', sa.Float, nullable=True),
        sa.Column('llm_tokens', sa.Integer, nullable=True),
        sa.Column('llm_cached', sa.Boolean, default=False),
        sa.Column('metadata', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes for analysis_metrics
    op.create_index('idx_user_created_match', 'analysis_metrics', ['user_id', 'created_at', 'match_score'])
    op.create_index('idx_created_match_score', 'analysis_metrics', ['created_at', 'match_score'])
    op.create_index('idx_am_user_id', 'analysis_metrics', ['user_id'])
    op.create_index('idx_am_analysis_id', 'analysis_metrics', ['analysis_id'])
    op.create_index('idx_am_resume_id', 'analysis_metrics', ['resume_id'])
    op.create_index('idx_am_created_at', 'analysis_metrics', ['created_at'])

    # Create export_metrics table
    op.create_table(
        'export_metrics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('resume_id', UUID(as_uuid=True), sa.ForeignKey('resumes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('generated_resume_id', UUID(as_uuid=True), sa.ForeignKey('generated_resumes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('export_format', sa.Enum(name='export_format_enum'), nullable=False),
        sa.Column('template_name', sa.String(100), nullable=False),
        sa.Column('file_size_bytes', sa.Integer, nullable=False),
        sa.Column('page_count', sa.Integer, nullable=True),
        sa.Column('generation_time_ms', sa.Integer, nullable=False),
        sa.Column('cached', sa.Boolean, default=False),
        sa.Column('success', sa.Boolean, default=True),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes for export_metrics
    op.create_index('idx_user_format_created', 'export_metrics', ['user_id', 'export_format', 'created_at'])
    op.create_index('idx_template_created', 'export_metrics', ['template_name', 'created_at'])
    op.create_index('idx_format_created', 'export_metrics', ['export_format', 'created_at'])
    op.create_index('idx_created_success', 'export_metrics', ['created_at', 'success'])
    op.create_index('idx_em_user_id', 'export_metrics', ['user_id'])
    op.create_index('idx_em_resume_id', 'export_metrics', ['resume_id'])
    op.create_index('idx_em_export_format', 'export_metrics', ['export_format'])
    op.create_index('idx_em_template_name', 'export_metrics', ['template_name'])
    op.create_index('idx_em_cached', 'export_metrics', ['cached'])
    op.create_index('idx_em_created_at', 'export_metrics', ['created_at'])

    # Create daily_metrics table
    op.create_table(
        'daily_metrics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('metric_date', sa.Date, nullable=False),
        sa.Column('total_activities', sa.Integer, default=0),
        sa.Column('login_count', sa.Integer, default=0),
        sa.Column('api_request_count', sa.Integer, default=0),
        sa.Column('resumes_created', sa.Integer, default=0),
        sa.Column('resumes_updated', sa.Integer, default=0),
        sa.Column('resumes_analyzed', sa.Integer, default=0),
        sa.Column('total_analyses', sa.Integer, default=0),
        sa.Column('avg_match_score', sa.Float, nullable=True),
        sa.Column('max_match_score', sa.Float, nullable=True),
        sa.Column('min_match_score', sa.Float, nullable=True),
        sa.Column('successful_analyses', sa.Integer, default=0),
        sa.Column('total_exports', sa.Integer, default=0),
        sa.Column('pdf_exports', sa.Integer, default=0),
        sa.Column('docx_exports', sa.Integer, default=0),
        sa.Column('html_exports', sa.Integer, default=0),
        sa.Column('cached_exports', sa.Integer, default=0),
        sa.Column('total_export_size_mb', sa.Float, default=0.0),
        sa.Column('llm_requests', sa.Integer, default=0),
        sa.Column('llm_cached_requests', sa.Integer, default=0),
        sa.Column('total_llm_cost', sa.Float, default=0.0),
        sa.Column('total_llm_tokens', sa.Integer, default=0),
        sa.Column('avg_analysis_time_ms', sa.Integer, nullable=True),
        sa.Column('avg_export_time_ms', sa.Integer, nullable=True),
        sa.Column('template_usage', JSON, nullable=True),
        sa.Column('metadata', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for daily_metrics
    op.create_index('idx_user_date', 'daily_metrics', ['user_id', 'metric_date'], unique=True)
    op.create_index('idx_date_only', 'daily_metrics', ['metric_date'])


def downgrade() -> None:
    """Drop analytics tables"""

    # Drop tables
    op.drop_table('daily_metrics')
    op.drop_table('export_metrics')
    op.drop_table('analysis_metrics')
    op.drop_table('user_activities')

    # Drop enums
    sa.Enum(name='export_format_enum').drop(op.get_bind())
    sa.Enum(name='activity_type_enum').drop(op.get_bind())
