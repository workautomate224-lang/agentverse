"""Add focus group tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-01-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create focus_group_sessions table
    op.create_table(
        'focus_group_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('session_type', sa.String(50), nullable=False, server_default='individual_interview'),
        sa.Column('topic', sa.Text(), nullable=True),
        sa.Column('objectives', postgresql.JSONB(), nullable=True),
        sa.Column('agent_ids', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('agent_contexts', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('discussion_guide', postgresql.JSONB(), nullable=True),
        sa.Column('model_preset', sa.String(50), nullable=False, server_default='balanced'),
        sa.Column('temperature', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('moderator_style', sa.String(50), nullable=False, server_default='neutral'),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('sentiment_trajectory', postgresql.JSONB(), nullable=True),
        sa.Column('key_themes', postgresql.JSONB(), nullable=True),
        sa.Column('insights_summary', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['product_runs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for focus_group_sessions
    op.create_index('ix_focus_group_sessions_product_id', 'focus_group_sessions', ['product_id'])
    op.create_index('ix_focus_group_sessions_user_id', 'focus_group_sessions', ['user_id'])
    op.create_index('ix_focus_group_sessions_status', 'focus_group_sessions', ['status'])
    op.create_index('ix_focus_group_sessions_created_at', 'focus_group_sessions', ['created_at'])

    # Create focus_group_messages table
    op.create_table(
        'focus_group_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('agent_id', sa.String(100), nullable=True),
        sa.Column('agent_name', sa.String(255), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_group_response', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('responding_agents', postgresql.JSONB(), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('emotion', sa.String(50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('key_points', postgresql.JSONB(), nullable=True),
        sa.Column('themes', postgresql.JSONB(), nullable=True),
        sa.Column('quotes', postgresql.JSONB(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('response_time_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['session_id'], ['focus_group_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for focus_group_messages
    op.create_index('ix_focus_group_messages_session_id', 'focus_group_messages', ['session_id'])
    op.create_index('ix_focus_group_messages_sequence', 'focus_group_messages', ['session_id', 'sequence_number'])
    op.create_index('ix_focus_group_messages_role', 'focus_group_messages', ['role'])
    op.create_index('ix_focus_group_messages_agent_id', 'focus_group_messages', ['agent_id'])


def downgrade() -> None:
    # Drop focus_group_messages table and indexes
    op.drop_index('ix_focus_group_messages_agent_id', table_name='focus_group_messages')
    op.drop_index('ix_focus_group_messages_role', table_name='focus_group_messages')
    op.drop_index('ix_focus_group_messages_sequence', table_name='focus_group_messages')
    op.drop_index('ix_focus_group_messages_session_id', table_name='focus_group_messages')
    op.drop_table('focus_group_messages')

    # Drop focus_group_sessions table and indexes
    op.drop_index('ix_focus_group_sessions_created_at', table_name='focus_group_sessions')
    op.drop_index('ix_focus_group_sessions_status', table_name='focus_group_sessions')
    op.drop_index('ix_focus_group_sessions_user_id', table_name='focus_group_sessions')
    op.drop_index('ix_focus_group_sessions_product_id', table_name='focus_group_sessions')
    op.drop_table('focus_group_sessions')
