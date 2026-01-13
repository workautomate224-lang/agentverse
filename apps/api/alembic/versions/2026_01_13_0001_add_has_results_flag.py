"""Add has_results flag to runs table

Revision ID: 2026_01_13_0001
Revises: 2026_01_10_0008
Create Date: 2026-01-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_has_results_001"
down_revision = "step10_production_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add has_results column to runs table."""
    op.add_column(
        "runs",
        sa.Column("has_results", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Remove has_results column from runs table."""
    op.drop_column("runs", "has_results")
