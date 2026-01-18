"""Add llm_proof to project_guidance

Revision ID: slice_2d_llm_proof_001
Revises: slice_2d_guidance_trace_001
Create Date: 2026-01-19

Slice 2D: LLM Provenance Tracking

This migration adds the llm_proof column to project_guidance table:
- llm_proof: JSONB containing provider, model, cache status, fallback flag, request_id

This column stores full LLM provenance for audit and transparency:
{
    "provider": "openrouter",
    "model": "openai/gpt-5.2",
    "cache": "hit" | "bypassed",
    "fallback": false,
    "request_id": "req_abc123",
    "job_id": "uuid"
}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'slice_2d_llm_proof_001'
down_revision: Union[str, None] = 'slice_2d_guidance_trace_001'
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
    # Add llm_proof column if not exists
    if not column_exists('project_guidance', 'llm_proof'):
        op.add_column(
            'project_guidance',
            sa.Column('llm_proof', postgresql.JSONB(), nullable=True)
        )


def downgrade() -> None:
    # Drop llm_proof column
    if column_exists('project_guidance', 'llm_proof'):
        op.drop_column('project_guidance', 'llm_proof')
