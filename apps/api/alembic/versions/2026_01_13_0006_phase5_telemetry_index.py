"""Phase 5: Telemetry Standardization - Add telemetry_index table

Revision ID: phase5_telemetry_index_001
Revises: add_calibration_tables_001
Create Date: 2026-01-13

This migration adds metadata storage for telemetry to enable:
1. Schema versioning for forward compatibility
2. Capabilities flags (has_spatial, has_events, has_metrics) for UI enablement
3. Quick access to index data without loading full telemetry blob
4. Storage reference tracking

Key constraints compliance:
- C1 (Fork-not-mutate): Telemetry index is immutable once created
- C3 (Replay read-only): Index enables efficient read-only queries
- C4 (Auditable): Schema version tracked for reproducibility
- C6 (Multi-tenant): All data scoped by tenant_id

NON-DESTRUCTIVE: This migration only adds new table, does not modify existing data.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import ProgrammingError


# revision identifiers, used by Alembic.
revision = "phase5_telemetry_index_001"
down_revision = "add_calibration_tables_001"
branch_labels = None
depends_on = None


def create_index_if_not_exists(index_name: str, table_name: str, columns: list, **kwargs):
    """Create index only if it doesn't already exist."""
    try:
        op.create_index(index_name, table_name, columns, **kwargs)
    except ProgrammingError as e:
        if "already exists" in str(e):
            pass  # Index already exists, skip
        else:
            raise


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


def upgrade():
    # =========================================================================
    # Telemetry Index Table
    # Stores metadata about telemetry for efficient querying
    # =========================================================================
    if not table_exists("telemetry_index"):
        op.create_table(
            "telemetry_index",
            # Identity
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),

            # Schema & Version
            sa.Column(
                "schema_version",
                sa.String(32),
                nullable=False,
                server_default="v1",
            ),

            # Storage reference (points to S3/object storage)
            sa.Column(
                "storage_ref",
                postgresql.JSONB(),
                nullable=True,
            ),

            # Index data (for quick access without loading full blob)
            sa.Column("total_ticks", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "keyframe_ticks",
                postgresql.JSONB(),
                nullable=False,
                server_default="[]",
            ),
            sa.Column(
                "agent_ids",
                postgresql.JSONB(),
                nullable=False,
                server_default="[]",
            ),

            # Capabilities flags (critical for UI enablement)
            sa.Column(
                "capabilities",
                postgresql.JSONB(),
                nullable=False,
                server_default='{"has_spatial": false, "has_events": false, "has_metrics": false}',
            ),

            # Summary stats
            sa.Column("total_agents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_events", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "metric_keys",
                postgresql.JSONB(),
                nullable=False,
                server_default="[]",
            ),

            # Integrity
            sa.Column("telemetry_hash", sa.String(64), nullable=True),
            sa.Column("is_complete", sa.Boolean(), nullable=False, server_default="true"),

            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),

            # Constraints
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["run_id"],
                ["runs.id"],
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "run_id",
                name="uq_telemetry_index_run_id",
            ),
        )

    # Indexes for efficient queries (idempotent)
    create_index_if_not_exists(
        "ix_telemetry_index_tenant_id",
        "telemetry_index",
        ["tenant_id"],
    )
    create_index_if_not_exists(
        "ix_telemetry_index_run_id",
        "telemetry_index",
        ["run_id"],
    )
    create_index_if_not_exists(
        "ix_telemetry_index_tenant_run",
        "telemetry_index",
        ["tenant_id", "run_id"],
    )


def downgrade():
    op.drop_table("telemetry_index")
