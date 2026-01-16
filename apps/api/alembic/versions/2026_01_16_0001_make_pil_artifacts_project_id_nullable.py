"""Make pil_artifacts.project_id nullable for pre-project goal analysis

Revision ID: 20260116_0001
Revises: 20260115_0004
Create Date: 2026-01-16

Blueprint v2 requires artifacts to be created BEFORE a project exists,
during the goal analysis phase. The model already has nullable=True,
but the database schema was never updated.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260116_0001'
down_revision = '20260115_0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make project_id nullable to allow pre-project artifacts (Blueprint v2)
    op.alter_column(
        'pil_artifacts',
        'project_id',
        existing_type=sa.UUID(),
        nullable=True
    )


def downgrade() -> None:
    # Revert to NOT NULL (will fail if any rows have NULL project_id)
    op.alter_column(
        'pil_artifacts',
        'project_id',
        existing_type=sa.UUID(),
        nullable=False
    )
