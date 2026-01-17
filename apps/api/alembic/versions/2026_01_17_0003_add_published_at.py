"""Add published_at column to project_specs for Slice 1D-B

Revision ID: slice_1d_b_published_at_001
Revises: slice_1c_wizard_state_001
Create Date: 2026-01-17

This migration adds the published_at timestamp field for Slice 1D-B:

1. Adds published_at column to project_specs:
   - Set when DRAFT is promoted to ACTIVE via /publish endpoint
   - NULL for projects created before this feature
   - Enables tracking of when drafts became active projects

Reference: Slice 1D-B specification (Blueprint Ready + Publish)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'slice_1d_b_published_at_001'
down_revision: Union[str, None] = 'slice_1c_wizard_state_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add published_at column for tracking when drafts are published
    op.add_column(
        'project_specs',
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True)
    )
    # Index for efficient queries on published projects
    op.create_index('ix_project_specs_published_at', 'project_specs', ['published_at'])


def downgrade() -> None:
    op.drop_index('ix_project_specs_published_at', table_name='project_specs')
    op.drop_column('project_specs', 'published_at')
