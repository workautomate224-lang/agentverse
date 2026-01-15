"""Add more missing columns to pil_jobs table

Revision ID: pil_jobs_columns_fix_002
Revises: pil_jobs_columns_fix_001
Create Date: 2026-01-15

Adds additional columns that were missing:
- error_details (JSONB)
- artifact_ids (JSONB)
- eta_hint (String)
- stages_completed (Integer)
- stages_total (Integer)
- stage_name (String)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "pil_jobs_columns_fix_002"
down_revision = "pil_jobs_columns_fix_001"
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

    # Add error_details if missing
    if not column_exists("pil_jobs", "error_details"):
        op.add_column(
            "pil_jobs",
            sa.Column(
                "error_details",
                postgresql.JSONB(),
                nullable=True,
                comment="Detailed error information (stack trace, etc.)"
            )
        )

    # Add artifact_ids if missing
    if not column_exists("pil_jobs", "artifact_ids"):
        op.add_column(
            "pil_jobs",
            sa.Column(
                "artifact_ids",
                postgresql.JSONB(),
                nullable=True,
                comment="List of artifact UUIDs created by this job"
            )
        )

    # Add eta_hint if missing
    if not column_exists("pil_jobs", "eta_hint"):
        op.add_column(
            "pil_jobs",
            sa.Column(
                "eta_hint",
                sa.String(100),
                nullable=True,
                comment="Estimated time to completion hint"
            )
        )

    # Add stages_completed if missing
    if not column_exists("pil_jobs", "stages_completed"):
        op.add_column(
            "pil_jobs",
            sa.Column(
                "stages_completed",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="Number of stages completed"
            )
        )

    # Add stages_total if missing
    if not column_exists("pil_jobs", "stages_total"):
        op.add_column(
            "pil_jobs",
            sa.Column(
                "stages_total",
                sa.Integer(),
                nullable=False,
                server_default="1",
                comment="Total number of stages"
            )
        )

    # Add stage_name if missing
    if not column_exists("pil_jobs", "stage_name"):
        op.add_column(
            "pil_jobs",
            sa.Column(
                "stage_name",
                sa.String(255),
                nullable=True,
                comment="Current stage name"
            )
        )


def downgrade():
    """Remove added columns."""
    if column_exists("pil_jobs", "stage_name"):
        op.drop_column("pil_jobs", "stage_name")
    if column_exists("pil_jobs", "stages_total"):
        op.drop_column("pil_jobs", "stages_total")
    if column_exists("pil_jobs", "stages_completed"):
        op.drop_column("pil_jobs", "stages_completed")
    if column_exists("pil_jobs", "eta_hint"):
        op.drop_column("pil_jobs", "eta_hint")
    if column_exists("pil_jobs", "artifact_ids"):
        op.drop_column("pil_jobs", "artifact_ids")
    if column_exists("pil_jobs", "error_details"):
        op.drop_column("pil_jobs", "error_details")
