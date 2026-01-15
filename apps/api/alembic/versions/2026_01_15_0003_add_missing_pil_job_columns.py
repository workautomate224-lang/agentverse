"""Add missing columns to pil_jobs table

Revision ID: pil_jobs_columns_fix_001
Revises: blueprint_columns_fix_001
Create Date: 2026-01-15

Adds columns that were missing from the original migration:
- retry_delay_seconds (Integer)
- notification_sent (Boolean)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "pil_jobs_columns_fix_001"
down_revision = "blueprint_columns_fix_001"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table (idempotent)."""
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
        {"table": table_name, "column": column_name}
    )
    return result.scalar()


def upgrade():
    """Add missing columns to pil_jobs table."""

    # Add retry_delay_seconds if missing
    if not column_exists("pil_jobs", "retry_delay_seconds"):
        op.add_column(
            "pil_jobs",
            sa.Column(
                "retry_delay_seconds",
                sa.Integer(),
                nullable=False,
                server_default="60",
                comment="Delay in seconds before retrying a failed job"
            )
        )

    # Add notification_sent if missing
    if not column_exists("pil_jobs", "notification_sent"):
        op.add_column(
            "pil_jobs",
            sa.Column(
                "notification_sent",
                sa.Boolean(),
                nullable=False,
                server_default="false",
                comment="Whether notification was sent for job completion"
            )
        )


def downgrade():
    """Remove added columns."""
    if column_exists("pil_jobs", "notification_sent"):
        op.drop_column("pil_jobs", "notification_sent")
    if column_exists("pil_jobs", "retry_delay_seconds"):
        op.drop_column("pil_jobs", "retry_delay_seconds")
