"""Phase 8: End-to-End Backtest Loop - Add backtest tables

Revision ID: phase8_backtest_tables_001
Revises: phase5_telemetry_index_001
Create Date: 2026-01-14

Adds three new tables for backtest orchestration:
- backtests: Main backtest records with status, config, progress tracking
- backtest_runs: Links backtests to individual simulation runs
- backtest_report_snapshots: Cached Phase 7 report outputs

Constraints:
- C1: Fork-not-mutate - Backtests create new runs, never modify existing
- C4: Auditable - Full provenance with manifest_hash tracking
- C6: Multi-tenant - All tables include tenant_id for scoping

IMPORTANT: Reset operations are SCOPED-SAFE.
- reset_backtest_data() only deletes backtest_runs and backtest_report_snapshots
  belonging to a specific backtest_id
- NEVER deletes global runs, telemetry, or data from other backtests
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "phase8_backtest_tables_001"
down_revision = "phase5_telemetry_index_001"
branch_labels = None
depends_on = None


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


def table_exists(table_name: str) -> bool:
    """Check if a table exists (idempotent)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table)"
        ),
        {"table": table_name}
    )
    return result.scalar()


def upgrade():
    """Non-destructive upgrade path - only adds new tables."""

    # =========================================================================
    # Table: backtests
    # =========================================================================
    if not table_exists("backtests"):
        op.create_table(
            "backtests",
            # Primary Key
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False,
                     server_default=sa.text("gen_random_uuid()")),

            # Multi-tenancy (required)
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),

            # Project association
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),

            # Backtest metadata
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("topic", sa.String(500), nullable=False),

            # Status tracking
            sa.Column("status", sa.String(20), nullable=False, server_default="created"),

            # Configuration
            sa.Column("seed", sa.Integer(), nullable=False, server_default="42"),
            sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),

            # Notes
            sa.Column("notes", sa.Text(), nullable=True),

            # Execution stats
            sa.Column("total_planned_runs", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completed_runs", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_runs", sa.Integer(), nullable=False, server_default="0"),

            # Timestamps
            sa.Column("created_at", sa.DateTime(timezone=True),
                     server_default=sa.func.now(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True),
                     server_default=sa.func.now(), nullable=False),

            # Constraints
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["project_id"], ["project_specs.id"], ondelete="CASCADE"),
        )

    # Indexes for backtests
    create_index_if_not_exists("ix_backtests_tenant_id", "backtests", ["tenant_id"])
    create_index_if_not_exists("ix_backtests_project_id", "backtests", ["project_id"])
    create_index_if_not_exists("ix_backtests_status", "backtests", ["status"])
    create_index_if_not_exists("ix_backtests_tenant_project", "backtests", ["tenant_id", "project_id"])

    # =========================================================================
    # Table: backtest_runs
    # =========================================================================
    if not table_exists("backtest_runs"):
        op.create_table(
            "backtest_runs",
            # Primary Key
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False,
                     server_default=sa.text("gen_random_uuid()")),

            # Backtest association
            sa.Column("backtest_id", postgresql.UUID(as_uuid=True), nullable=False),

            # Actual Run reference (nullable until run is created)
            sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),

            # Node being tested
            sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),

            # Run index within backtest (for deterministic seeding)
            sa.Column("run_index", sa.Integer(), nullable=False, server_default="0"),

            # Derived seed for this specific run
            sa.Column("derived_seed", sa.Integer(), nullable=False, server_default="0"),

            # Status tracking
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),

            # Provenance
            sa.Column("manifest_hash", sa.String(64), nullable=True),

            # Error tracking
            sa.Column("error", sa.Text(), nullable=True),

            # Timestamps
            sa.Column("created_at", sa.DateTime(timezone=True),
                     server_default=sa.func.now(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),

            # Constraints
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["backtest_id"], ["backtests.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        )

    # Indexes for backtest_runs
    create_index_if_not_exists("ix_backtest_runs_backtest_id", "backtest_runs", ["backtest_id"])
    create_index_if_not_exists("ix_backtest_runs_run_id", "backtest_runs", ["run_id"])
    create_index_if_not_exists("ix_backtest_runs_node_id", "backtest_runs", ["node_id"])
    create_index_if_not_exists("ix_backtest_runs_status", "backtest_runs", ["status"])
    create_index_if_not_exists("ix_backtest_runs_backtest_node", "backtest_runs", ["backtest_id", "node_id"])

    # =========================================================================
    # Table: backtest_report_snapshots
    # =========================================================================
    if not table_exists("backtest_report_snapshots"):
        op.create_table(
            "backtest_report_snapshots",
            # Primary Key
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False,
                     server_default=sa.text("gen_random_uuid()")),

            # Backtest association
            sa.Column("backtest_id", postgresql.UUID(as_uuid=True), nullable=False),

            # Report parameters
            sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("metric_key", sa.String(100), nullable=False),
            sa.Column("op", sa.String(10), nullable=False),
            sa.Column("threshold", sa.Float(), nullable=False),

            # Additional params
            sa.Column("params", postgresql.JSONB(), nullable=False, server_default="{}"),

            # Cached report JSON
            sa.Column("report_json", postgresql.JSONB(), nullable=False, server_default="{}"),

            # Timestamps
            sa.Column("created_at", sa.DateTime(timezone=True),
                     server_default=sa.func.now(), nullable=False),

            # Constraints
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["backtest_id"], ["backtests.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        )

    # Indexes for backtest_report_snapshots
    create_index_if_not_exists("ix_backtest_report_snapshots_backtest_id",
                               "backtest_report_snapshots", ["backtest_id"])
    create_index_if_not_exists("ix_backtest_report_snapshots_node_id",
                               "backtest_report_snapshots", ["node_id"])
    create_index_if_not_exists("ix_backtest_report_snapshots_backtest_node",
                               "backtest_report_snapshots", ["backtest_id", "node_id"])


def downgrade():
    """Rollback - drops all Phase 8 tables."""
    op.drop_table("backtest_report_snapshots")
    op.drop_table("backtest_runs")
    op.drop_table("backtests")
