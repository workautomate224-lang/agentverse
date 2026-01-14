"""Add Temporal Knowledge Isolation schema changes

Revision ID: temporal_isolation_001
Revises: phase8_backtest_tables_001
Create Date: 2026-01-14

This migration implements Temporal Knowledge Isolation per temporal.md:

1. Extends project_specs with temporal context fields:
   - temporal_mode: 'live' or 'backtest'
   - as_of_datetime: cutoff timestamp for backtest mode
   - temporal_timezone: IANA timezone for cutoff evaluation
   - isolation_level: 1 (basic), 2 (strict), 3 (audit-first)
   - allowed_sources: JSON array of source identifiers
   - temporal_policy_version: version of source capability registry
   - temporal_lock_status: 'locked' or 'unlocked'
   - temporal_lock_history: JSONB audit trail

2. Extends run_manifests with temporal audit fields:
   - cutoff_applied_as_of_datetime: copied from project at run-time
   - data_manifest_ref: pointer to full data access manifest
   - lineage_ref: feature derivation lineage metadata
   - isolation_status: 'PASS' or 'FAIL'
   - isolation_violations: details of any violations

3. Creates source_capabilities table for DataGateway source registry

4. Creates source_capability_audits table for audit trail

Reference: temporal.md §4-5, §10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "temporal_isolation_001"
down_revision = "phase8_backtest_tables_001"
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
    """Non-destructive upgrade - adds temporal isolation schema."""

    # =========================================================================
    # 1. Extend project_specs with temporal context fields
    # =========================================================================
    if not column_exists("project_specs", "temporal_mode"):
        op.add_column(
            "project_specs",
            sa.Column(
                "temporal_mode",
                sa.String(20),
                nullable=False,
                server_default="live",
                comment="'live' or 'backtest'"
            )
        )

    if not column_exists("project_specs", "as_of_datetime"):
        op.add_column(
            "project_specs",
            sa.Column(
                "as_of_datetime",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="Cutoff timestamp for backtest mode"
            )
        )

    if not column_exists("project_specs", "temporal_timezone"):
        op.add_column(
            "project_specs",
            sa.Column(
                "temporal_timezone",
                sa.String(50),
                nullable=False,
                server_default="Asia/Kuala_Lumpur",
                comment="IANA timezone for cutoff evaluation"
            )
        )

    if not column_exists("project_specs", "isolation_level"):
        op.add_column(
            "project_specs",
            sa.Column(
                "isolation_level",
                sa.Integer(),
                nullable=False,
                server_default="1",
                comment="1=basic, 2=strict (default for backtest), 3=audit-first"
            )
        )

    if not column_exists("project_specs", "allowed_sources"):
        op.add_column(
            "project_specs",
            sa.Column(
                "allowed_sources",
                postgresql.JSONB(),
                nullable=True,
                comment="JSON array of allowed source identifiers"
            )
        )

    if not column_exists("project_specs", "temporal_policy_version"):
        op.add_column(
            "project_specs",
            sa.Column(
                "temporal_policy_version",
                sa.String(50),
                nullable=False,
                server_default="1.0.0",
                comment="Version of source capability registry at project creation"
            )
        )

    if not column_exists("project_specs", "temporal_lock_status"):
        op.add_column(
            "project_specs",
            sa.Column(
                "temporal_lock_status",
                sa.String(20),
                nullable=False,
                server_default="locked",
                comment="'locked' or 'unlocked'"
            )
        )

    if not column_exists("project_specs", "temporal_lock_history"):
        op.add_column(
            "project_specs",
            sa.Column(
                "temporal_lock_history",
                postgresql.JSONB(),
                nullable=True,
                comment="Audit trail of temporal lock changes"
            )
        )

    # =========================================================================
    # 2. Extend run_manifests with temporal audit fields
    # =========================================================================
    if not column_exists("run_manifests", "cutoff_applied_as_of_datetime"):
        op.add_column(
            "run_manifests",
            sa.Column(
                "cutoff_applied_as_of_datetime",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="Temporal cutoff applied to this run (copied from project.as_of_datetime)"
            )
        )

    if not column_exists("run_manifests", "data_manifest_ref"):
        op.add_column(
            "run_manifests",
            sa.Column(
                "data_manifest_ref",
                postgresql.JSONB(),
                nullable=True,
                comment="Full data access manifest: sources, endpoints, time windows, hashes"
            )
        )

    if not column_exists("run_manifests", "lineage_ref"):
        op.add_column(
            "run_manifests",
            sa.Column(
                "lineage_ref",
                postgresql.JSONB(),
                nullable=True,
                comment="Feature derivation lineage: what was derived from what, window boundaries"
            )
        )

    if not column_exists("run_manifests", "isolation_status"):
        op.add_column(
            "run_manifests",
            sa.Column(
                "isolation_status",
                sa.String(20),
                nullable=True,
                comment="Temporal isolation compliance: 'PASS' or 'FAIL'"
            )
        )

    if not column_exists("run_manifests", "isolation_violations"):
        op.add_column(
            "run_manifests",
            sa.Column(
                "isolation_violations",
                postgresql.JSONB(),
                nullable=True,
                comment="Details of temporal isolation violations, if any"
            )
        )

    # =========================================================================
    # 3. Create source_capabilities table
    # =========================================================================
    if not table_exists("source_capabilities"):
        op.create_table(
            "source_capabilities",
            # Identity
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                server_default=sa.text("gen_random_uuid()")
            ),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                nullable=False
            ),
            # Source identification
            sa.Column(
                "source_name",
                sa.String(100),
                nullable=False,
                comment="Unique source identifier (e.g., 'census_bureau', 'eurostat')"
            ),
            sa.Column(
                "display_name",
                sa.String(255),
                nullable=False,
                comment="Human-readable display name"
            ),
            sa.Column(
                "description",
                sa.Text(),
                nullable=True,
                comment="Description of the data source"
            ),
            sa.Column(
                "endpoint_pattern",
                sa.String(255),
                nullable=False,
                server_default="*",
                comment="Pattern for matching endpoints (e.g., '/data/*')"
            ),
            # Timestamp capabilities
            sa.Column(
                "timestamp_availability",
                sa.String(20),
                nullable=False,
                server_default="none",
                comment="'full', 'partial', or 'none'"
            ),
            sa.Column(
                "historical_query_support",
                sa.Boolean(),
                nullable=False,
                server_default="false",
                comment="Whether source supports as-of/historical queries"
            ),
            sa.Column(
                "timestamp_field",
                sa.String(100),
                nullable=True,
                comment="Name of the timestamp field in responses"
            ),
            # Cutoff enforcement
            sa.Column(
                "required_cutoff_params",
                postgresql.JSONB(),
                nullable=True,
                comment="How to pass as_of to this source: {param_name: 'time_end', format: 'iso8601'}"
            ),
            sa.Column(
                "safe_isolation_levels",
                postgresql.ARRAY(sa.Integer()),
                nullable=False,
                server_default="{1}",
                comment="Which isolation levels allow this source: [1], [1,2], [1,2,3]"
            ),
            sa.Column(
                "block_message",
                sa.String(500),
                nullable=True,
                comment="Message to show when source is blocked"
            ),
            # Governance
            sa.Column(
                "owner",
                sa.String(255),
                nullable=False,
                server_default="unassigned",
                comment="Responsible team/person for this source"
            ),
            sa.Column(
                "review_date",
                sa.Date(),
                nullable=True,
                comment="Last review date for this source capability"
            ),
            sa.Column(
                "compliance_classification",
                sa.String(50),
                nullable=False,
                server_default="pending_review",
                comment="'approved', 'restricted', 'pending_review', 'deprecated'"
            ),
            # Policy versioning
            sa.Column(
                "policy_version",
                sa.String(50),
                nullable=False,
                server_default="1.0.0",
                comment="Version increments on any change"
            ),
            # Status
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default="true",
                comment="Whether this source is currently active"
            ),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False
            ),
            # Constraints
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        )

    # Indexes for source_capabilities
    create_index_if_not_exists(
        "ix_source_capabilities_tenant_id",
        "source_capabilities",
        ["tenant_id"]
    )
    create_index_if_not_exists(
        "ix_source_capabilities_source_name",
        "source_capabilities",
        ["source_name"]
    )
    create_index_if_not_exists(
        "ix_source_capabilities_tenant_source",
        "source_capabilities",
        ["tenant_id", "source_name"],
        unique=True
    )
    create_index_if_not_exists(
        "ix_source_capabilities_active",
        "source_capabilities",
        ["tenant_id", "is_active"],
        postgresql_where=sa.text("is_active = true")
    )

    # =========================================================================
    # 4. Create source_capability_audits table
    # =========================================================================
    if not table_exists("source_capability_audits"):
        op.create_table(
            "source_capability_audits",
            # Identity
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                server_default=sa.text("gen_random_uuid()")
            ),
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                nullable=False
            ),
            sa.Column(
                "source_capability_id",
                postgresql.UUID(as_uuid=True),
                nullable=False
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                nullable=True
            ),
            # Change details
            sa.Column(
                "action",
                sa.String(50),
                nullable=False,
                comment="'create', 'update', 'deactivate'"
            ),
            sa.Column(
                "previous_version",
                sa.String(50),
                nullable=True
            ),
            sa.Column(
                "new_version",
                sa.String(50),
                nullable=False
            ),
            sa.Column(
                "changes",
                postgresql.JSONB(),
                nullable=True,
                comment="Diff of changes made"
            ),
            sa.Column(
                "reason",
                sa.Text(),
                nullable=True,
                comment="Reason for the change"
            ),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False
            ),
            # Constraints
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["source_capability_id"],
                ["source_capabilities.id"],
                ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        )

    # Indexes for source_capability_audits
    create_index_if_not_exists(
        "ix_source_capability_audits_tenant_id",
        "source_capability_audits",
        ["tenant_id"]
    )
    create_index_if_not_exists(
        "ix_source_capability_audits_source_id",
        "source_capability_audits",
        ["source_capability_id"]
    )
    create_index_if_not_exists(
        "ix_source_capability_audits_created_at",
        "source_capability_audits",
        ["tenant_id", "created_at"]
    )

    # =========================================================================
    # 5. Indexes for temporal queries on project_specs and run_manifests
    # =========================================================================
    create_index_if_not_exists(
        "ix_project_specs_temporal_mode",
        "project_specs",
        ["tenant_id", "temporal_mode"]
    )
    create_index_if_not_exists(
        "ix_project_specs_backtest",
        "project_specs",
        ["tenant_id", "as_of_datetime"],
        postgresql_where=sa.text("temporal_mode = 'backtest'")
    )
    create_index_if_not_exists(
        "ix_run_manifests_isolation_status",
        "run_manifests",
        ["tenant_id", "isolation_status"],
        postgresql_where=sa.text("isolation_status IS NOT NULL")
    )


def downgrade():
    """Rollback temporal isolation schema changes."""
    # Drop audit table first (has FK to source_capabilities)
    op.drop_table("source_capability_audits")

    # Drop source_capabilities table
    op.drop_table("source_capabilities")

    # Remove run_manifests columns
    op.drop_column("run_manifests", "isolation_violations")
    op.drop_column("run_manifests", "isolation_status")
    op.drop_column("run_manifests", "lineage_ref")
    op.drop_column("run_manifests", "data_manifest_ref")
    op.drop_column("run_manifests", "cutoff_applied_as_of_datetime")

    # Remove project_specs columns
    op.drop_column("project_specs", "temporal_lock_history")
    op.drop_column("project_specs", "temporal_lock_status")
    op.drop_column("project_specs", "temporal_policy_version")
    op.drop_column("project_specs", "allowed_sources")
    op.drop_column("project_specs", "isolation_level")
    op.drop_column("project_specs", "temporal_timezone")
    op.drop_column("project_specs", "as_of_datetime")
    op.drop_column("project_specs", "temporal_mode")
