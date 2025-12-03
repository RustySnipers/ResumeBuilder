"""phase_7_webhook_tables

Revision ID: d5e6f7g8h9i0
Revises: c4d5e6f7g8h9
Create Date: 2025-12-03

Phase 7: Webhook System
- Create webhooks table for webhook configurations
- Create webhook_events table for delivery logs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = 'd5e6f7g8h9i0'
down_revision = 'c4d5e6f7g8h9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create webhook tables"""

    # Create webhook_event_type_enum
    webhook_event_type_enum = sa.Enum(
        'resume.created', 'resume.updated', 'resume.deleted',
        'analysis.completed', 'analysis.failed',
        'generation.completed', 'generation.failed',
        'export.completed', 'export.failed',
        'user.email_verified', 'user.password_changed',
        name='webhook_event_type_enum',
        create_type=True
    )
    webhook_event_type_enum.create(op.get_bind())

    # Create webhook_delivery_status_enum
    webhook_delivery_status_enum = sa.Enum(
        'pending', 'success', 'failed', 'retrying',
        name='webhook_delivery_status_enum',
        create_type=True
    )
    webhook_delivery_status_enum.create(op.get_bind())

    # Create webhooks table
    op.create_table(
        'webhooks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.String(2000), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('events', JSON, nullable=False),
        sa.Column('secret', sa.String(64), nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('timeout_seconds', sa.Integer, default=30, nullable=False),
        sa.Column('max_retries', sa.Integer, default=3, nullable=False),
        sa.Column('total_deliveries', sa.Integer, default=0, nullable=False),
        sa.Column('successful_deliveries', sa.Integer, default=0, nullable=False),
        sa.Column('failed_deliveries', sa.Integer, default=0, nullable=False),
        sa.Column('last_delivery_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for webhooks
    op.create_index('idx_webhook_user_active', 'webhooks', ['user_id', 'is_active'])
    op.create_index('idx_webhooks_user_id', 'webhooks', ['user_id'])

    # Create webhook_events table
    op.create_table(
        'webhook_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('webhook_id', UUID(as_uuid=True), sa.ForeignKey('webhooks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.Enum(name='webhook_event_type_enum'), nullable=False),
        sa.Column('event_id', UUID(as_uuid=True), nullable=False),
        sa.Column('payload', JSON, nullable=False),
        sa.Column('status', sa.Enum(name='webhook_delivery_status_enum'), default='pending', nullable=False),
        sa.Column('attempt_count', sa.Integer, default=0, nullable=False),
        sa.Column('max_attempts', sa.Integer, default=3, nullable=False),
        sa.Column('http_status', sa.Integer, nullable=True),
        sa.Column('response_body', sa.Text, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('response_time_ms', sa.Integer, nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for webhook_events
    op.create_index('idx_webhook_event_status', 'webhook_events', ['webhook_id', 'status'])
    op.create_index('idx_webhook_event_created', 'webhook_events', ['webhook_id', 'created_at'])
    op.create_index('idx_webhook_event_retry', 'webhook_events', ['status', 'next_retry_at'])
    op.create_index('idx_webhook_events_webhook_id', 'webhook_events', ['webhook_id'])
    op.create_index('idx_webhook_events_event_type', 'webhook_events', ['event_type'])
    op.create_index('idx_webhook_events_event_id', 'webhook_events', ['event_id'])
    op.create_index('idx_webhook_events_status', 'webhook_events', ['status'])
    op.create_index('idx_webhook_events_created_at', 'webhook_events', ['created_at'])
    op.create_index('idx_webhook_events_next_retry_at', 'webhook_events', ['next_retry_at'])


def downgrade() -> None:
    """Drop webhook tables"""

    # Drop tables
    op.drop_table('webhook_events')
    op.drop_table('webhooks')

    # Drop enums
    sa.Enum(name='webhook_delivery_status_enum').drop(op.get_bind())
    sa.Enum(name='webhook_event_type_enum').drop(op.get_bind())
