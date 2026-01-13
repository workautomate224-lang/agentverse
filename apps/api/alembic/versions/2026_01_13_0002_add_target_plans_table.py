"""Add target_plans table for Target Planner UI

Revision ID: add_target_plans_001
Revises: add_has_results_001
Create Date: 2026-01-13

This migration creates the target_plans table for the Target Planner UI.
This is a simpler model for user-created intervention plans, separate from
the PlanningSpec model used for simulation-based evaluation.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "add_target_plans_001"
down_revision = "add_has_results_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create target_plans table."""
    op.create_table(
        "target_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_specs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="Optional starting node for this plan",
        ),
        # Plan definition
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        # Target specification
        sa.Column(
            "target_metric",
            sa.String(100),
            nullable=False,
            comment="Metric to optimize (e.g., 'market_share', 'revenue')",
        ),
        sa.Column(
            "target_value",
            sa.Float,
            nullable=False,
            comment="Target value to achieve",
        ),
        sa.Column(
            "horizon_ticks",
            sa.Integer,
            nullable=False,
            server_default="100",
            comment="Time horizon in simulation ticks",
        ),
        # Constraints and steps (JSONB for flexibility)
        sa.Column(
            "constraints_json",
            postgresql.JSONB,
            nullable=True,
            comment="Constraints for the plan (budget, timing, etc.)",
        ),
        sa.Column(
            "steps_json",
            postgresql.JSONB,
            nullable=True,
            comment="Intervention steps array",
        ),
        # Metadata
        sa.Column(
            "source",
            sa.String(20),
            nullable=False,
            server_default="manual",
            comment="How the plan was created: manual or ai",
        ),
        sa.Column(
            "ai_prompt",
            sa.Text,
            nullable=True,
            comment="Original prompt if AI-generated",
        ),
        # Timestamps
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
            nullable=False,
        ),
    )

    # Create indexes for common queries
    op.create_index(
        "ix_target_plans_project_updated",
        "target_plans",
        ["project_id", "updated_at"],
    )
    op.create_index(
        "ix_target_plans_source",
        "target_plans",
        ["tenant_id", "source"],
    )


def downgrade() -> None:
    """Drop target_plans table."""
    op.drop_index("ix_target_plans_source", table_name="target_plans")
    op.drop_index("ix_target_plans_project_updated", table_name="target_plans")
    op.drop_table("target_plans")
