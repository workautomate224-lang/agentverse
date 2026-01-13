"""Add calibration tables for PHASE 4 Calibration Minimal Closed Loop

Revision ID: add_calibration_tables_001
Revises: add_run_outcomes_001
Create Date: 2026-01-13

This migration creates tables for PHASE 4: Calibration Minimal Closed Loop:
- ground_truth_datasets: Named collections of ground truth labels
- ground_truth_labels: Individual labels linking runs to known outcomes
- calibration_jobs: Background calibration job tracking
- calibration_iterations: Per-iteration results for auditability

Key features:
- Deterministic calibration (no LLM in loop - C5 compliance)
- Fork-not-mutate: Labels are immutable once created (C1 spirit)
- Auditable: All iterations stored for debugging (C4 compliance)
- Multi-tenant: All tables scoped by tenant_id (C6 compliance)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import ProgrammingError


# revision identifiers, used by Alembic.
revision = "add_calibration_tables_001"
down_revision = "add_run_outcomes_001"
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


def constraint_exists(constraint_name: str) -> bool:
    """Check if a constraint exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.table_constraints WHERE constraint_name = :name)"
        ),
        {"name": constraint_name}
    )
    return result.scalar()


def upgrade():
    # =========================================================================
    # Ground Truth Datasets Table
    # =========================================================================
    if not table_exists("ground_truth_datasets"):
        op.create_table(
            "ground_truth_datasets",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["project_id"],
                ["projects.id"],
                ondelete="CASCADE",
            ),
        )

    create_index_if_not_exists(
        "ix_ground_truth_datasets_tenant_id",
        "ground_truth_datasets",
        ["tenant_id"],
    )
    create_index_if_not_exists(
        "ix_ground_truth_datasets_tenant_project",
        "ground_truth_datasets",
        ["tenant_id", "project_id"],
    )

    # =========================================================================
    # Ground Truth Labels Table
    # =========================================================================
    if not table_exists("ground_truth_labels"):
        op.create_table(
            "ground_truth_labels",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("label", sa.Integer(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "json_meta",
                postgresql.JSONB(),
                nullable=False,
                server_default="{}",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["project_id"],
                ["projects.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["dataset_id"],
                ["ground_truth_datasets.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["node_id"],
                ["nodes.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["run_id"],
                ["runs.id"],
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "dataset_id",
                "run_id",
                name="uq_ground_truth_labels_dataset_run",
            ),
        )

    create_index_if_not_exists(
        "ix_ground_truth_labels_tenant_id",
        "ground_truth_labels",
        ["tenant_id"],
    )
    create_index_if_not_exists(
        "ix_ground_truth_labels_tenant_project",
        "ground_truth_labels",
        ["tenant_id", "project_id"],
    )
    create_index_if_not_exists(
        "ix_ground_truth_labels_dataset_node",
        "ground_truth_labels",
        ["dataset_id", "node_id"],
    )

    # =========================================================================
    # Calibration Jobs Table
    # =========================================================================
    if not table_exists("calibration_jobs"):
        op.create_table(
            "calibration_jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "status",
                sa.String(32),
                nullable=False,
                server_default="queued",
            ),
            sa.Column(
                "config_json",
                postgresql.JSONB(),
                nullable=False,
                server_default="{}",
            ),
            sa.Column("result_json", postgresql.JSONB(), nullable=True),
            sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_iterations", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("celery_task_id", sa.String(255), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["project_id"],
                ["projects.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["node_id"],
                ["nodes.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["dataset_id"],
                ["ground_truth_datasets.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["created_by_user_id"],
                ["users.id"],
                ondelete="SET NULL",
            ),
        )

    create_index_if_not_exists(
        "ix_calibration_jobs_tenant_id",
        "calibration_jobs",
        ["tenant_id"],
    )
    create_index_if_not_exists(
        "ix_calibration_jobs_tenant_project",
        "calibration_jobs",
        ["tenant_id", "project_id"],
    )
    create_index_if_not_exists(
        "ix_calibration_jobs_node_status",
        "calibration_jobs",
        ["node_id", "status"],
    )

    # =========================================================================
    # Calibration Iterations Table
    # =========================================================================
    if not table_exists("calibration_iterations"):
        op.create_table(
            "calibration_iterations",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("iter_index", sa.Integer(), nullable=False),
            sa.Column(
                "params_json",
                postgresql.JSONB(),
                nullable=False,
                server_default="{}",
            ),
            sa.Column(
                "metrics_json",
                postgresql.JSONB(),
                nullable=False,
                server_default="{}",
            ),
            sa.Column("mapping_json", postgresql.JSONB(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["job_id"],
                ["calibration_jobs.id"],
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "job_id",
                "iter_index",
                name="uq_calibration_iterations_job_index",
            ),
        )

    create_index_if_not_exists(
        "ix_calibration_iterations_job_index",
        "calibration_iterations",
        ["job_id", "iter_index"],
    )


def downgrade():
    # Drop tables in reverse order (due to foreign keys)
    op.drop_table("calibration_iterations")
    op.drop_table("calibration_jobs")
    op.drop_table("ground_truth_labels")
    op.drop_table("ground_truth_datasets")
