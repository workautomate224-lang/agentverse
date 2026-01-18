"""Add project_fingerprint and source_refs to project_guidance

Revision ID: slice_2d_guidance_trace_001
Revises: slice_2c_project_guidance_001
Create Date: 2026-01-18

Slice 2D: Blueprint Traceability

This migration adds two columns to project_guidance table:
- project_fingerprint: JSONB containing goal_hash, domain, core_strategy, blueprint_version
- source_refs: JSONB array of blueprint fields used to generate this guidance

These columns prove that guidance is derived from the specific blueprint,
not generic/static content.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'slice_2d_guidance_trace_001'
down_revision: Union[str, None] = 'slice_2c_project_guidance_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists (for idempotency)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_name = :table AND column_name = :column
            )
            """
        ),
        {"table": table_name, "column": column_name},
    )
    return result.scalar()


def upgrade() -> None:
    # Add project_fingerprint column if not exists
    if not column_exists('project_guidance', 'project_fingerprint'):
        op.add_column(
            'project_guidance',
            sa.Column('project_fingerprint', postgresql.JSONB(), nullable=True)
        )

    # Add source_refs column if not exists
    if not column_exists('project_guidance', 'source_refs'):
        op.add_column(
            'project_guidance',
            sa.Column('source_refs', postgresql.JSONB(), nullable=True)
        )


def downgrade() -> None:
    # Drop source_refs column
    if column_exists('project_guidance', 'source_refs'):
        op.drop_column('project_guidance', 'source_refs')

    # Drop project_fingerprint column
    if column_exists('project_guidance', 'project_fingerprint'):
        op.drop_column('project_guidance', 'project_fingerprint')
