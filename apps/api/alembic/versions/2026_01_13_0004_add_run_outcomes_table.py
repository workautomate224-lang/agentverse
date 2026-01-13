"""Add run_outcomes table for PHASE 3 Probability Source Compliance

Revision ID: add_run_outcomes_001
Revises: add_run_manifests_001
Create Date: 2026-01-13

This migration creates the run_outcomes table for PHASE 3:
Probability Source Compliance for empirical distribution computation.

The run_outcomes table stores:
- Normalized numeric metrics per run for aggregation
- Quality flags for filtering low-quality data
- Link to manifest_hash for version-based filtering
- Status (SUCCEEDED by default)

This enables auditable, evidence-based probability calculations
derived from empirical distributions across multiple runs.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "add_run_outcomes_001"
down_revision = "add_run_manifests_001"
branch_labels = None
depends_on = None


def index_exists(index_name: str) -> bool:
    """Check if an index exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = :index)"
        ),
        {"index": index_name}
    )
    return result.scalar()


def create_index_if_not_exists(index_name: str, table_name: str, columns: list, **kwargs):
    """Create index only if it doesn't already exist."""
    if not index_exists(index_name):
        op.create_index(index_name, table_name, columns, **kwargs)


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table)"
        ),
        {"table": table_name}
    )
    return result.scalar()


def upgrade() -> None:
    """Create run_outcomes table."""
    if not table_exists("run_outcomes"):
        op.create_table(
            "run_outcomes",
            # Primary key
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            # Multi-tenancy
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
            ),
            # Foreign keys
            sa.Column(
                "project_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "node_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("nodes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "run_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("runs.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            # Link to Phase 2 manifest for version filtering
            sa.Column(
                "manifest_hash",
                sa.String(64),
                nullable=True,
            ),
            # Normalized numeric outcomes (JSONB)
            sa.Column(
                "metrics_json",
                postgresql.JSONB,
                nullable=False,
                server_default="{}",
            ),
            # Data quality flags (JSONB)
            sa.Column(
                "quality_flags",
                postgresql.JSONB,
                nullable=False,
                server_default="{}",
            ),
            # Run status (only SUCCEEDED by default)
            sa.Column(
                "status",
                sa.String(32),
                nullable=False,
                server_default="succeeded",
            ),
        )

    # Create indexes (idempotent)
    # Primary query pattern: get all outcomes for a node within time range
    create_index_if_not_exists(
        "ix_run_outcomes_project_node_created",
        "run_outcomes",
        ["project_id", "node_id", "created_at"],
    )

    # Filter by manifest version
    create_index_if_not_exists(
        "ix_run_outcomes_node_manifest",
        "run_outcomes",
        ["node_id", "manifest_hash"],
    )

    # Tenant scoping
    create_index_if_not_exists(
        "ix_run_outcomes_tenant_project",
        "run_outcomes",
        ["tenant_id", "project_id"],
    )

    # Individual column indexes
    create_index_if_not_exists(
        "ix_run_outcomes_run_id",
        "run_outcomes",
        ["run_id"],
        unique=True,
    )

    create_index_if_not_exists(
        "ix_run_outcomes_manifest_hash",
        "run_outcomes",
        ["manifest_hash"],
    )

    create_index_if_not_exists(
        "ix_run_outcomes_tenant_id",
        "run_outcomes",
        ["tenant_id"],
    )

    create_index_if_not_exists(
        "ix_run_outcomes_project_id",
        "run_outcomes",
        ["project_id"],
    )

    create_index_if_not_exists(
        "ix_run_outcomes_node_id",
        "run_outcomes",
        ["node_id"],
    )


def downgrade() -> None:
    """Drop run_outcomes table."""
    # Drop indexes
    op.drop_index("ix_run_outcomes_node_id", table_name="run_outcomes")
    op.drop_index("ix_run_outcomes_project_id", table_name="run_outcomes")
    op.drop_index("ix_run_outcomes_tenant_id", table_name="run_outcomes")
    op.drop_index("ix_run_outcomes_manifest_hash", table_name="run_outcomes")
    op.drop_index("ix_run_outcomes_run_id", table_name="run_outcomes")
    op.drop_index("ix_run_outcomes_tenant_project", table_name="run_outcomes")
    op.drop_index("ix_run_outcomes_node_manifest", table_name="run_outcomes")
    op.drop_index("ix_run_outcomes_project_node_created", table_name="run_outcomes")

    # Drop table
    op.drop_table("run_outcomes")
