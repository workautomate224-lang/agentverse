"""Add phase column to llm_calls for C5 compliance tracking

Revision ID: llm_phase_001
Revises: llm_router_001
Create Date: 2026-01-09 12:00:00.000000

This migration adds the 'phase' column to llm_calls to track
whether LLM calls occur during compilation or tick loop.

Reference: verification_checklist_v2.md §1.4 (LLM Usage Tracking)
- "compilation" = LLM calls during scenario/event compilation
- "tick_loop" = LLM calls during agent execution loop (should be 0 for C5)

C5 constraint: LLMs are compilers/planners - NOT tick-by-tick brains in agent loops
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'llm_phase_001'
down_revision: Union[str, None] = 'llm_router_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add phase column for C5 compliance tracking
    op.add_column(
        'llm_calls',
        sa.Column('phase', sa.String(50), nullable=True)
    )
    # Index for efficient phase-based queries
    op.create_index('ix_llm_calls_phase', 'llm_calls', ['phase'])
    # Composite index for run + phase queries (Evidence Pack generation)
    op.create_index(
        'ix_llm_calls_run_phase',
        'llm_calls',
        ['run_id', 'phase']
    )


def downgrade() -> None:
    op.drop_index('ix_llm_calls_run_phase', table_name='llm_calls')
    op.drop_index('ix_llm_calls_phase', table_name='llm_calls')
    op.drop_column('llm_calls', 'phase')
