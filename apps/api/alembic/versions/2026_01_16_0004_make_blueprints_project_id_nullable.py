"""Make blueprints.project_id nullable for Blueprint v2 draft creation

Revision ID: blueprints_nullable_001
Revises: pil_jobs_jsonb_001
Create Date: 2026-01-16

Blueprint v2 requires creating draft blueprints BEFORE a project exists.
The goal analysis phase creates a blueprint with project_id=NULL, which
is then linked to a project after the user confirms the blueprint.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'blueprints_nullable_001'
down_revision = 'pil_jobs_jsonb_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make project_id nullable to allow draft blueprints (Blueprint v2)
    op.alter_column(
        'blueprints',
        'project_id',
        existing_type=sa.UUID(),
        nullable=True
    )


def downgrade() -> None:
    # Revert to NOT NULL (will fail if any rows have NULL project_id)
    op.alter_column(
        'blueprints',
        'project_id',
        existing_type=sa.UUID(),
        nullable=False
    )
