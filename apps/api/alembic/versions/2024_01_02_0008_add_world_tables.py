"""Add Vi World tables for persistent world states

Revision ID: 0008
Revises: 0007
Create Date: 2026-01-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create world_states table
    op.create_table(
        'world_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        # World configuration
        sa.Column('seed', sa.Integer(), nullable=False),
        sa.Column('world_width', sa.Integer(), nullable=False, server_default='150'),
        sa.Column('world_height', sa.Integer(), nullable=False, server_default='114'),
        sa.Column('tile_size', sa.Integer(), nullable=False, server_default='16'),
        # Simulation status
        sa.Column('status', sa.String(50), nullable=False, server_default='inactive'),
        sa.Column('is_continuous', sa.Boolean(), nullable=False, server_default='true'),
        # NPC states - flexible JSONB storage
        sa.Column('npc_states', postgresql.JSONB(), nullable=False, server_default='{}'),
        # Chat history - JSONB array
        sa.Column('chat_history', postgresql.JSONB(), nullable=False, server_default='[]'),
        # Statistics
        sa.Column('total_messages', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_simulation_time', sa.Integer(), nullable=False, server_default='0'),
        # Simulation timing
        sa.Column('simulation_speed', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('last_tick_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ticks_processed', sa.Integer(), nullable=False, server_default='0'),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        # Foreign keys and constraints
        sa.ForeignKeyConstraint(['template_id'], ['persona_templates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_id', name='uq_world_state_template'),
    )

    # Create indexes for world_states
    op.create_index('ix_world_states_template_id', 'world_states', ['template_id'])
    op.create_index('ix_world_states_status', 'world_states', ['status'])
    op.create_index('ix_world_states_updated_at', 'world_states', ['updated_at'])

    # Create world_events table for event logging and replay
    op.create_table(
        'world_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('world_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Event details
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('actor_id', sa.String(255), nullable=True),
        sa.Column('target_id', sa.String(255), nullable=True),
        # Event data - flexible JSONB storage
        sa.Column('data', postgresql.JSONB(), nullable=False, server_default='{}'),
        # Timing
        sa.Column('tick', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Foreign keys
        sa.ForeignKeyConstraint(['world_id'], ['world_states.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for world_events
    op.create_index('ix_world_events_world_id', 'world_events', ['world_id'])
    op.create_index('ix_world_events_tick', 'world_events', ['world_id', 'tick'])
    op.create_index('ix_world_events_event_type', 'world_events', ['event_type'])
    op.create_index('ix_world_events_actor', 'world_events', ['world_id', 'actor_id'])


def downgrade() -> None:
    # Drop world_events table and indexes
    op.drop_index('ix_world_events_actor', table_name='world_events')
    op.drop_index('ix_world_events_event_type', table_name='world_events')
    op.drop_index('ix_world_events_tick', table_name='world_events')
    op.drop_index('ix_world_events_world_id', table_name='world_events')
    op.drop_table('world_events')

    # Drop world_states table and indexes
    op.drop_index('ix_world_states_updated_at', table_name='world_states')
    op.drop_index('ix_world_states_status', table_name='world_states')
    op.drop_index('ix_world_states_template_id', table_name='world_states')
    op.drop_table('world_states')
