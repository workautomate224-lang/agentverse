"""Add Blueprint-Driven Orchestration tables

Revision ID: blueprint_tables_001
Revises: temporal_isolation_001
Create Date: 2026-01-15

This migration implements Blueprint-Driven Project Orchestration per blueprint.md:

1. Creates blueprints table - versioned project construction plans
2. Creates blueprint_slots table - input requirements for blueprints
3. Creates blueprint_tasks table - section tasks driven by blueprint
4. Creates pil_jobs table - Project Intelligence Layer background jobs
5. Creates pil_artifacts table - outputs from PIL jobs
6. Extends runs table with blueprint_id and blueprint_version

Reference: blueprint.md §3, §5, §6
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "blueprint_tables_001"
down_revision = "temporal_isolation_001"
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
    """Non-destructive upgrade - adds blueprint orchestration schema."""

    # =========================================================================
    # 1. Create blueprints table (blueprint.md §3)
    # =========================================================================
    if not table_exists("blueprints"):
        op.create_table(
            "blueprints",
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
                "project_id",
                postgresql.UUID(as_uuid=True),
                nullable=False
            ),
            # Versioning
            sa.Column(
                "version",
                sa.Integer(),
                nullable=False,
                server_default="1",
                comment="Blueprint version number (increments on changes)"
            ),
            sa.Column(
                "policy_version",
                sa.String(50),
                nullable=False,
                server_default="1.0.0",
                comment="Policy version used for this blueprint"
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default="false",
                comment="Whether this is the active blueprint for the project"
            ),
            sa.Column(
                "is_draft",
                sa.Boolean(),
                nullable=False,
                server_default="true",
                comment="Draft blueprints can be edited"
            ),
            sa.Column(
                "draft_expires_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="When draft blueprint expires"
            ),
            # A) Project Profile (blueprint.md §3.1.A)
            sa.Column(
                "goal_text",
                sa.Text(),
                nullable=False,
                comment="Original user goal text"
            ),
            sa.Column(
                "goal_summary",
                sa.Text(),
                nullable=True,
                comment="AI-generated goal summary"
            ),
            sa.Column(
                "domain_guess",
                sa.String(50),
                nullable=True,
                comment="election, market_demand, production_forecast, policy_impact, perception_risk, crime_route, personal_decision, generic"
            ),
            sa.Column(
                "target_outputs",
                postgresql.ARRAY(sa.String(50)),
                nullable=True,
                comment="distribution, point_estimate, ranked_outcomes, paths, recommendations"
            ),
            sa.Column(
                "horizon",
                postgresql.JSONB(),
                nullable=True,
                comment="Time horizon: {range, granularity}"
            ),
            sa.Column(
                "scope",
                postgresql.JSONB(),
                nullable=True,
                comment="Scope: {geography, entity}"
            ),
            sa.Column(
                "success_metrics",
                postgresql.JSONB(),
                nullable=True,
                comment="Success criteria: {description, evaluation_metrics[]}"
            ),
            # B) Strategy (blueprint.md §3.1.B)
            sa.Column(
                "recommended_core",
                sa.String(20),
                nullable=True,
                comment="collective, targeted, hybrid"
            ),
            sa.Column(
                "primary_drivers",
                postgresql.ARRAY(sa.String(50)),
                nullable=True,
                comment="population, timeseries, network, constraints, events, sentiment, mixed"
            ),
            sa.Column(
                "required_modules",
                postgresql.ARRAY(sa.String(100)),
                nullable=True,
                comment="List of required simulation modules"
            ),
            # C) Input Slots (Contract) - stored as JSON array (blueprint.md §3.1.C)
            sa.Column(
                "input_slots",
                postgresql.JSONB(),
                nullable=True,
                comment="List of InputSlot objects"
            ),
            # D) Section Task Map - stored as JSON object (blueprint.md §3.1.D)
            sa.Column(
                "section_task_map",
                postgresql.JSONB(),
                nullable=True,
                comment="{section_id: [tasks]}"
            ),
            # E) Calibration Plan (blueprint.md §3.1.E)
            sa.Column(
                "calibration_plan",
                postgresql.JSONB(),
                nullable=True,
                comment="Calibration configuration"
            ),
            # F) Branching Plan (blueprint.md §3.1.F)
            sa.Column(
                "branching_plan",
                postgresql.JSONB(),
                nullable=True,
                comment="Universe Map branching configuration"
            ),
            # G) Policy & Audit Metadata
            sa.Column(
                "clarification_answers",
                postgresql.JSONB(),
                nullable=True,
                comment="User answers to clarifying questions"
            ),
            sa.Column(
                "constraints_applied",
                postgresql.ARRAY(sa.String(100)),
                nullable=True,
                comment="Policy constraints applied"
            ),
            sa.Column(
                "risk_notes",
                postgresql.ARRAY(sa.Text()),
                nullable=True,
                comment="Risk notes generated during analysis"
            ),
            sa.Column(
                "created_by",
                sa.String(50),
                nullable=True,
                comment="User ID who created this blueprint"
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

    # Indexes for blueprints
    create_index_if_not_exists("ix_blueprints_tenant_id", "blueprints", ["tenant_id"])
    create_index_if_not_exists("ix_blueprints_project_id", "blueprints", ["project_id"])
    create_index_if_not_exists(
        "ix_blueprints_project_active",
        "blueprints",
        ["project_id", "is_active"],
        postgresql_where=sa.text("is_active = true")
    )
    create_index_if_not_exists(
        "ix_blueprints_project_version",
        "blueprints",
        ["project_id", "version"],
        unique=True
    )

    # =========================================================================
    # 2. Create blueprint_slots table (blueprint.md §3.1.C)
    # =========================================================================
    if not table_exists("blueprint_slots"):
        op.create_table(
            "blueprint_slots",
            # Identity
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                server_default=sa.text("gen_random_uuid()")
            ),
            sa.Column(
                "blueprint_id",
                postgresql.UUID(as_uuid=True),
                nullable=False
            ),
            sa.Column(
                "sort_order",
                sa.Integer(),
                nullable=False,
                server_default="0"
            ),
            # Slot definition
            sa.Column(
                "slot_name",
                sa.String(255),
                nullable=False,
                comment="Human-readable slot name"
            ),
            sa.Column(
                "slot_type",
                sa.String(50),
                nullable=False,
                comment="TimeSeries, Table, EntitySet, Graph, TextCorpus, Labels, Ruleset, AssumptionSet, PersonaSet, EventScriptSet"
            ),
            sa.Column(
                "required_level",
                sa.String(20),
                nullable=False,
                server_default="recommended",
                comment="required, recommended, optional"
            ),
            sa.Column(
                "description",
                sa.Text(),
                nullable=True,
                comment="Slot description and purpose"
            ),
            # Requirements
            sa.Column(
                "schema_requirements",
                postgresql.JSONB(),
                nullable=True,
                comment="Schema constraints: min_fields, types, allowed_values"
            ),
            sa.Column(
                "temporal_requirements",
                postgresql.JSONB(),
                nullable=True,
                comment="Temporal constraints: must_have_timestamps, must_be_before_cutoff, required_window"
            ),
            sa.Column(
                "quality_requirements",
                postgresql.JSONB(),
                nullable=True,
                comment="Quality constraints: missing_threshold, dedupe_rules, min_coverage"
            ),
            sa.Column(
                "allowed_acquisition_methods",
                postgresql.ARRAY(sa.String(50)),
                nullable=False,
                server_default="{}",
                comment="manual_upload, connect_api, ai_research, ai_generation, snapshot_import"
            ),
            sa.Column(
                "validation_plan",
                postgresql.JSONB(),
                nullable=True,
                comment="Validation: ai_checks[], programmatic_checks[]"
            ),
            sa.Column(
                "derived_artifacts",
                postgresql.ARRAY(sa.String(100)),
                nullable=True,
                comment="Artifacts derived from this slot"
            ),
            # Status tracking
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="not_started",
                comment="ready, needs_attention, blocked, not_started"
            ),
            sa.Column(
                "status_reason",
                sa.Text(),
                nullable=True,
                comment="Reason for current status"
            ),
            # Fulfillment
            sa.Column(
                "fulfilled",
                sa.Boolean(),
                nullable=False,
                server_default="false"
            ),
            sa.Column(
                "fulfilled_by",
                postgresql.JSONB(),
                nullable=True,
                comment="Artifact that fulfills this slot: {type, id, name}"
            ),
            sa.Column(
                "fulfillment_method",
                sa.String(50),
                nullable=True,
                comment="How the slot was fulfilled"
            ),
            # AI artifacts
            sa.Column(
                "alignment_score",
                sa.Float(),
                nullable=True,
                comment="0-1 alignment score from AI validation"
            ),
            sa.Column(
                "alignment_reasons",
                postgresql.ARRAY(sa.Text()),
                nullable=True,
                comment="Reasons for alignment score"
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
            sa.ForeignKeyConstraint(
                ["blueprint_id"],
                ["blueprints.id"],
                ondelete="CASCADE"
            ),
        )

    # Indexes for blueprint_slots
    create_index_if_not_exists("ix_blueprint_slots_blueprint_id", "blueprint_slots", ["blueprint_id"])
    create_index_if_not_exists("ix_blueprint_slots_status", "blueprint_slots", ["blueprint_id", "status"])
    create_index_if_not_exists("ix_blueprint_slots_required", "blueprint_slots", ["blueprint_id", "required_level"])

    # =========================================================================
    # 3. Create blueprint_tasks table (blueprint.md §3.1.D)
    # =========================================================================
    if not table_exists("blueprint_tasks"):
        op.create_table(
            "blueprint_tasks",
            # Identity
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                server_default=sa.text("gen_random_uuid()")
            ),
            sa.Column(
                "blueprint_id",
                postgresql.UUID(as_uuid=True),
                nullable=False
            ),
            sa.Column(
                "section_id",
                sa.String(50),
                nullable=False,
                comment="Platform section this task belongs to"
            ),
            sa.Column(
                "sort_order",
                sa.Integer(),
                nullable=False,
                server_default="0"
            ),
            # Task content
            sa.Column(
                "title",
                sa.String(255),
                nullable=False
            ),
            sa.Column(
                "description",
                sa.Text(),
                nullable=True
            ),
            sa.Column(
                "why_it_matters",
                sa.Text(),
                nullable=True,
                comment="Explanation of task importance"
            ),
            # Links
            sa.Column(
                "linked_slot_ids",
                postgresql.ARRAY(sa.String(50)),
                nullable=True,
                comment="Slots linked to this task"
            ),
            sa.Column(
                "available_actions",
                postgresql.ARRAY(sa.String(50)),
                nullable=False,
                server_default="{}",
                comment="ai_generate, ai_research, manual_add, connect_source"
            ),
            # Completion criteria
            sa.Column(
                "completion_criteria",
                postgresql.JSONB(),
                nullable=True,
                comment="Criteria for task completion: {artifact_type, artifact_exists}"
            ),
            sa.Column(
                "alert_config",
                postgresql.JSONB(),
                nullable=True,
                comment="Alert configuration: {warn_if_incomplete, warn_if_low_quality, quality_threshold}"
            ),
            # Status
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="not_started",
                comment="ready, needs_attention, blocked, not_started"
            ),
            sa.Column(
                "status_reason",
                sa.Text(),
                nullable=True
            ),
            sa.Column(
                "last_summary_ref",
                sa.String(100),
                nullable=True,
                comment="Reference to latest summary artifact"
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
            sa.ForeignKeyConstraint(
                ["blueprint_id"],
                ["blueprints.id"],
                ondelete="CASCADE"
            ),
        )

    # Indexes for blueprint_tasks
    create_index_if_not_exists("ix_blueprint_tasks_blueprint_id", "blueprint_tasks", ["blueprint_id"])
    create_index_if_not_exists("ix_blueprint_tasks_section", "blueprint_tasks", ["blueprint_id", "section_id"])
    create_index_if_not_exists("ix_blueprint_tasks_status", "blueprint_tasks", ["blueprint_id", "status"])

    # =========================================================================
    # 4. Create pil_jobs table (blueprint.md §5)
    # =========================================================================
    if not table_exists("pil_jobs"):
        op.create_table(
            "pil_jobs",
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
                "project_id",
                postgresql.UUID(as_uuid=True),
                nullable=True
            ),
            sa.Column(
                "blueprint_id",
                postgresql.UUID(as_uuid=True),
                nullable=True
            ),
            # Job identification
            sa.Column(
                "job_type",
                sa.String(50),
                nullable=False,
                comment="goal_analysis, clarification_generate, blueprint_build, slot_validation, etc."
            ),
            sa.Column(
                "job_name",
                sa.String(255),
                nullable=False
            ),
            sa.Column(
                "priority",
                sa.String(20),
                nullable=False,
                server_default="normal",
                comment="low, normal, high, critical"
            ),
            sa.Column(
                "celery_task_id",
                sa.String(255),
                nullable=True,
                comment="Celery task ID for tracking"
            ),
            # Status
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="queued",
                comment="queued, running, succeeded, failed, cancelled, partial"
            ),
            # Progress (blueprint.md §5.4)
            sa.Column(
                "progress_percent",
                sa.Integer(),
                nullable=False,
                server_default="0"
            ),
            sa.Column(
                "stage_name",
                sa.String(100),
                nullable=True,
                comment="Current stage name"
            ),
            sa.Column(
                "eta_hint",
                sa.String(100),
                nullable=True,
                comment="Estimated time remaining"
            ),
            sa.Column(
                "stages_completed",
                sa.Integer(),
                nullable=False,
                server_default="0"
            ),
            sa.Column(
                "stages_total",
                sa.Integer(),
                nullable=False,
                server_default="1"
            ),
            # Input/Output
            sa.Column(
                "input_params",
                postgresql.JSONB(),
                nullable=True,
                comment="Job input parameters"
            ),
            sa.Column(
                "result",
                postgresql.JSONB(),
                nullable=True,
                comment="Job result data"
            ),
            sa.Column(
                "error_message",
                sa.Text(),
                nullable=True
            ),
            # Artifact references
            sa.Column(
                "artifact_ids",
                postgresql.ARRAY(sa.String(50)),
                nullable=True,
                comment="IDs of artifacts produced by this job"
            ),
            sa.Column(
                "slot_id",
                sa.String(50),
                nullable=True,
                comment="Target slot for slot-specific jobs"
            ),
            sa.Column(
                "task_id",
                sa.String(50),
                nullable=True,
                comment="Target task for task-specific jobs"
            ),
            # Retry
            sa.Column(
                "retry_count",
                sa.Integer(),
                nullable=False,
                server_default="0"
            ),
            sa.Column(
                "max_retries",
                sa.Integer(),
                nullable=False,
                server_default="3"
            ),
            # Tracking
            sa.Column(
                "created_by",
                sa.String(50),
                nullable=True
            ),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                nullable=True
            ),
            sa.Column(
                "completed_at",
                sa.DateTime(timezone=True),
                nullable=True
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
            sa.ForeignKeyConstraint(
                ["blueprint_id"],
                ["blueprints.id"],
                ondelete="SET NULL"
            ),
        )

    # Indexes for pil_jobs
    create_index_if_not_exists("ix_pil_jobs_tenant_id", "pil_jobs", ["tenant_id"])
    create_index_if_not_exists("ix_pil_jobs_project_id", "pil_jobs", ["project_id"])
    create_index_if_not_exists("ix_pil_jobs_blueprint_id", "pil_jobs", ["blueprint_id"])
    create_index_if_not_exists("ix_pil_jobs_status", "pil_jobs", ["tenant_id", "status"])
    create_index_if_not_exists("ix_pil_jobs_type", "pil_jobs", ["tenant_id", "job_type"])
    create_index_if_not_exists(
        "ix_pil_jobs_active",
        "pil_jobs",
        ["tenant_id", "status"],
        postgresql_where=sa.text("status IN ('queued', 'running')")
    )
    create_index_if_not_exists("ix_pil_jobs_celery", "pil_jobs", ["celery_task_id"])

    # =========================================================================
    # 5. Create pil_artifacts table (blueprint.md §5.6)
    # =========================================================================
    if not table_exists("pil_artifacts"):
        op.create_table(
            "pil_artifacts",
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
                "project_id",
                postgresql.UUID(as_uuid=True),
                nullable=False
            ),
            sa.Column(
                "blueprint_id",
                postgresql.UUID(as_uuid=True),
                nullable=True
            ),
            sa.Column(
                "blueprint_version",
                sa.Integer(),
                nullable=True
            ),
            # Artifact type
            sa.Column(
                "artifact_type",
                sa.String(50),
                nullable=False,
                comment="goal_summary, clarification_questions, blueprint_preview, slot_validation_report, etc."
            ),
            sa.Column(
                "artifact_name",
                sa.String(255),
                nullable=False
            ),
            # References
            sa.Column(
                "job_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
                comment="Job that produced this artifact"
            ),
            sa.Column(
                "slot_id",
                sa.String(50),
                nullable=True,
                comment="Associated slot"
            ),
            sa.Column(
                "task_id",
                sa.String(50),
                nullable=True,
                comment="Associated task"
            ),
            # Content
            sa.Column(
                "content",
                postgresql.JSONB(),
                nullable=True,
                comment="Structured artifact content"
            ),
            sa.Column(
                "content_text",
                sa.Text(),
                nullable=True,
                comment="Text content for full-text search"
            ),
            # Scoring
            sa.Column(
                "alignment_score",
                sa.Float(),
                nullable=True,
                comment="0-1 alignment score"
            ),
            sa.Column(
                "quality_score",
                sa.Float(),
                nullable=True,
                comment="0-1 quality score"
            ),
            sa.Column(
                "validation_passed",
                sa.Boolean(),
                nullable=True,
                comment="Whether artifact passed validation"
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
                ["blueprint_id"],
                ["blueprints.id"],
                ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["job_id"],
                ["pil_jobs.id"],
                ondelete="SET NULL"
            ),
        )

    # Indexes for pil_artifacts
    create_index_if_not_exists("ix_pil_artifacts_tenant_id", "pil_artifacts", ["tenant_id"])
    create_index_if_not_exists("ix_pil_artifacts_project_id", "pil_artifacts", ["project_id"])
    create_index_if_not_exists("ix_pil_artifacts_blueprint_id", "pil_artifacts", ["blueprint_id"])
    create_index_if_not_exists("ix_pil_artifacts_job_id", "pil_artifacts", ["job_id"])
    create_index_if_not_exists("ix_pil_artifacts_type", "pil_artifacts", ["tenant_id", "artifact_type"])
    create_index_if_not_exists("ix_pil_artifacts_slot", "pil_artifacts", ["slot_id"])

    # =========================================================================
    # 6. Extend runs table with blueprint reference (blueprint.md §1.1)
    # =========================================================================
    if not column_exists("runs", "blueprint_id"):
        op.add_column(
            "runs",
            sa.Column(
                "blueprint_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
                comment="Blueprint used for this run (blueprint.md §1.1)"
            )
        )

    if not column_exists("runs", "blueprint_version"):
        op.add_column(
            "runs",
            sa.Column(
                "blueprint_version",
                sa.Integer(),
                nullable=True,
                comment="Blueprint version at time of run creation"
            )
        )

    # Index for runs.blueprint_id
    create_index_if_not_exists("ix_runs_blueprint_id", "runs", ["blueprint_id"])

    # Foreign key constraint for runs.blueprint_id (if runs table exists)
    if table_exists("runs") and column_exists("runs", "blueprint_id"):
        try:
            op.create_foreign_key(
                "fk_runs_blueprint_id",
                "runs",
                "blueprints",
                ["blueprint_id"],
                ["id"],
                ondelete="SET NULL"
            )
        except Exception:
            pass  # FK may already exist


def downgrade():
    """Rollback blueprint orchestration schema changes."""
    # Drop foreign key from runs
    try:
        op.drop_constraint("fk_runs_blueprint_id", "runs", type_="foreignkey")
    except Exception:
        pass

    # Remove runs columns
    if column_exists("runs", "blueprint_version"):
        op.drop_column("runs", "blueprint_version")
    if column_exists("runs", "blueprint_id"):
        op.drop_column("runs", "blueprint_id")

    # Drop tables in reverse dependency order
    op.drop_table("pil_artifacts")
    op.drop_table("pil_jobs")
    op.drop_table("blueprint_tasks")
    op.drop_table("blueprint_slots")
    op.drop_table("blueprints")
