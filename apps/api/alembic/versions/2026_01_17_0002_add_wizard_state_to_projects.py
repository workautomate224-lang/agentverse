"""Add wizard_state and status to project_specs for Slice 1C

Revision ID: slice_1c_wizard_state_001
Revises: temporal_isolation_001
Create Date: 2026-01-17

This migration adds Draft/Resume functionality per Slice 1C:

1. Adds status column to project_specs:
   - 'DRAFT' (default for new projects from wizard)
   - 'ACTIVE' (promoted when wizard completes)
   - 'ARCHIVED' (soft-deleted projects)

2. Adds wizard_state JSONB column to store wizard progress:
   - step: current wizard step ('goal' | 'clarify' | 'blueprint_preview' | ...)
   - goal_text: the natural language goal
   - goal_analysis_result: LLM analysis output (with provenance)
   - clarifying_questions: questions from goal analysis
   - clarification_answers: user's answers
   - blueprint_draft: partial blueprint if generated
   - last_saved_at: timestamp of last autosave

3. Adds wizard_state_version for optimistic concurrency control
   - Prevents overwrites from stale clients
   - Server increments on each update
   - Client must provide current version to update

Reference: slice_1c_spec (Draft/Resume feature)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "slice_1c_wizard_state_001"
down_revision = "pil_llm_profiles_001"
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


def index_exists(index_name: str) -> bool:
    """Check if an index exists (idempotent)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = :index)"
        ),
        {"index": index_name}
    )
    return result.scalar()


def create_index_if_not_exists(index_name: str, table_name: str, columns: list, **kwargs):
    """Create index only if it doesn't already exist (idempotent)."""
    if not index_exists(index_name):
        op.create_index(index_name, table_name, columns, **kwargs)


def upgrade():
    """Non-destructive upgrade - adds wizard state columns to project_specs."""

    # =========================================================================
    # 1. Add status column (DRAFT, ACTIVE, ARCHIVED)
    # =========================================================================
    if not column_exists("project_specs", "status"):
        op.add_column(
            "project_specs",
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="ACTIVE",  # Existing projects are ACTIVE
                comment="Project status: DRAFT, ACTIVE, ARCHIVED"
            )
        )

    # =========================================================================
    # 2. Add wizard_state JSONB column
    # =========================================================================
    if not column_exists("project_specs", "wizard_state"):
        op.add_column(
            "project_specs",
            sa.Column(
                "wizard_state",
                postgresql.JSONB(),
                nullable=True,
                comment="Wizard state for Draft projects (step, goal_text, answers, etc.)"
            )
        )

    # =========================================================================
    # 3. Add wizard_state_version for optimistic concurrency
    # =========================================================================
    if not column_exists("project_specs", "wizard_state_version"):
        op.add_column(
            "project_specs",
            sa.Column(
                "wizard_state_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="Optimistic concurrency version for wizard_state updates"
            )
        )

    # =========================================================================
    # 4. Add indexes for efficient queries
    # =========================================================================
    # Index for filtering by status (drafts appear in project list)
    create_index_if_not_exists(
        "ix_project_specs_tenant_status",
        "project_specs",
        ["tenant_id", "status"]
    )

    # Partial index for DRAFT projects (most common query)
    create_index_if_not_exists(
        "ix_project_specs_drafts",
        "project_specs",
        ["tenant_id", "updated_at"],
        postgresql_where=sa.text("status = 'DRAFT'")
    )


def downgrade():
    """Rollback wizard state columns."""
    # Drop indexes
    op.drop_index("ix_project_specs_drafts", table_name="project_specs")
    op.drop_index("ix_project_specs_tenant_status", table_name="project_specs")

    # Drop columns
    op.drop_column("project_specs", "wizard_state_version")
    op.drop_column("project_specs", "wizard_state")
    op.drop_column("project_specs", "status")
