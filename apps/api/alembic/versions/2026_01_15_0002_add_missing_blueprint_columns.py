"""Add missing columns to blueprints table

Revision ID: blueprint_columns_fix_001
Revises: blueprint_tables_001
Create Date: 2026-01-15

Adds columns that were missing from the original migration:
- input_slots (JSONB)
- section_task_map (JSONB)
- draft_expires_at (DateTime)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "blueprint_columns_fix_001"
down_revision = "blueprint_tables_001"
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
    """Add missing columns to blueprints table."""

    # Add input_slots if missing
    if not column_exists("blueprints", "input_slots"):
        op.add_column(
            "blueprints",
            sa.Column(
                "input_slots",
                postgresql.JSONB(),
                nullable=True,
                comment="List of InputSlot objects (blueprint.md §3.1.C)"
            )
        )

    # Add section_task_map if missing
    if not column_exists("blueprints", "section_task_map"):
        op.add_column(
            "blueprints",
            sa.Column(
                "section_task_map",
                postgresql.JSONB(),
                nullable=True,
                comment="Section-to-tasks mapping (blueprint.md §3.1.D)"
            )
        )

    # Add draft_expires_at if missing
    if not column_exists("blueprints", "draft_expires_at"):
        op.add_column(
            "blueprints",
            sa.Column(
                "draft_expires_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="When draft blueprint expires"
            )
        )


def downgrade():
    """Remove added columns."""
    if column_exists("blueprints", "draft_expires_at"):
        op.drop_column("blueprints", "draft_expires_at")
    if column_exists("blueprints", "section_task_map"):
        op.drop_column("blueprints", "section_task_map")
    if column_exists("blueprints", "input_slots"):
        op.drop_column("blueprints", "input_slots")
