"""STEP 4: Universe Map Audit Infrastructure

Revision ID: step4_universe_map_001
Revises: step3_persona_snapshot_001
Create Date: 2026-01-10

This migration adds the infrastructure required for Step 4 verification:
1. NodePatch table (structured delta from parent node)
2. Ensemble tracking columns in nodes table
3. Probability aggregation tracking columns in nodes table

STEP 4 Goal: Make the Universe Map a real versioned world graph,
not a UI-only diagram. Each Node represents a world state with:
- Structured NodePatch describing what changed from parent
- Ensemble runs (minimum 2) with different seeds
- Aggregated probabilities computed from runs (NO hardcoding)
- Immutable configuration after runs complete

Reference: Step 4 Audit Requirements
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'step4_universe_map_001'
down_revision = 'step3_persona_snapshot_001'
branch_labels = None
depends_on = None


def upgrade():
    # ==========================================================================
    # 1. NodePatch Table
    # Structured patch describing what changed from parent node
    # ==========================================================================
    op.create_table(
        'node_patches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),

        # What was changed
        sa.Column('patch_type', sa.String(50), nullable=False,
                  comment='Type of change: event_injection, variable_delta, environment_override, agent_modification'),

        # Structured change description (JSONB for flexibility)
        sa.Column('change_description', postgresql.JSONB, nullable=False, server_default='{}',
                  comment='STEP 4: Structured description of what changed'),

        # Parameters for the change
        sa.Column('parameters', postgresql.JSONB, nullable=False, server_default='{}',
                  comment='STEP 4: Parameters like variable_deltas, expansion_strategy'),

        # List of affected variables
        sa.Column('affected_variables', postgresql.ARRAY(sa.String(100)), nullable=False, server_default='{}',
                  comment='STEP 4: Variables impacted by this patch'),

        # Environment overrides (for apply_to_environment)
        sa.Column('environment_overrides', postgresql.JSONB, nullable=True,
                  comment='STEP 4: Direct environment variable overrides'),

        # Event script for event injections
        sa.Column('event_script', postgresql.JSONB, nullable=True,
                  comment='STEP 4: Event script ref for event-based patches'),

        # Natural language description
        sa.Column('nl_description', sa.Text, nullable=True,
                  comment='STEP 4: Human-readable description of the change'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create index for efficient node patch lookups
    op.create_index('ix_node_patches_tenant_created', 'node_patches', ['tenant_id', 'created_at'])

    # ==========================================================================
    # 2. Add STEP 4 Ensemble Tracking columns to nodes table
    # ==========================================================================
    op.add_column(
        'nodes',
        sa.Column(
            'min_ensemble_size',
            sa.Integer,
            nullable=False,
            server_default='2',
            comment='STEP 4: Minimum number of runs required for ensemble (default=2)'
        )
    )
    op.add_column(
        'nodes',
        sa.Column(
            'completed_run_count',
            sa.Integer,
            nullable=False,
            server_default='0',
            comment='STEP 4: Number of completed runs for this node'
        )
    )
    op.add_column(
        'nodes',
        sa.Column(
            'is_ensemble_complete',
            sa.Boolean,
            nullable=False,
            server_default='false',
            comment='STEP 4: True when completed_run_count >= min_ensemble_size'
        )
    )

    # ==========================================================================
    # 3. Add STEP 4 Probability Aggregation columns to nodes table
    # ==========================================================================
    op.add_column(
        'nodes',
        sa.Column(
            'aggregation_method',
            sa.String(50),
            nullable=True,
            server_default='mean',
            comment='STEP 4: Method used: mean, weighted_mean, median, mode'
        )
    )
    op.add_column(
        'nodes',
        sa.Column(
            'outcome_counts',
            postgresql.JSONB,
            nullable=True,
            comment='STEP 4: Count of each outcome across runs {outcome: count}'
        )
    )
    op.add_column(
        'nodes',
        sa.Column(
            'outcome_variance',
            postgresql.JSONB,
            nullable=True,
            comment='STEP 4: Variance of numeric outcomes across runs'
        )
    )


def downgrade():
    # Remove columns from nodes table (reverse order)
    op.drop_column('nodes', 'outcome_variance')
    op.drop_column('nodes', 'outcome_counts')
    op.drop_column('nodes', 'aggregation_method')
    op.drop_column('nodes', 'is_ensemble_complete')
    op.drop_column('nodes', 'completed_run_count')
    op.drop_column('nodes', 'min_ensemble_size')

    # Drop index
    op.drop_index('ix_node_patches_tenant_created', table_name='node_patches')

    # Drop node_patches table
    op.drop_table('node_patches')
