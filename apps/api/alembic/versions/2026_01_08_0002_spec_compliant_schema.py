"""Spec-compliant schema - Core data contracts

Revision ID: spec_compliant_001
Revises: predictive_sim_001
Create Date: 2026-01-08 00:00:00.000000

This migration creates the spec-compliant schema as defined in project.md §6.
It implements multi-tenancy, Universe Map (Nodes/Edges), and all core contracts.

Reference: project.md §6 (Data contracts)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'spec_compliant_001'
down_revision: Union[str, None] = 'predictive_sim_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # Tenants Table (Multi-tenancy foundation - project.md §8.1)
    # =========================================================================
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),
        sa.Column('tier', sa.String(50), nullable=False, server_default='free'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_tenants_slug', 'tenants', ['slug'])

    # Add tenant_id to existing users table
    op.add_column('users', sa.Column(
        'tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_users_tenant_id', 'users', 'tenants',
        ['tenant_id'], ['id'], ondelete='SET NULL'
    )
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])

    # =========================================================================
    # Project Specs Table (project.md §6.1)
    # =========================================================================
    op.create_table(
        'project_specs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Core configuration
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('goal_nl', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Prediction configuration
        sa.Column('prediction_core', sa.String(50), nullable=False),
        sa.Column('domain_template', sa.String(50), nullable=True),

        # Simulation defaults
        sa.Column('default_horizon', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('default_output_metrics', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Access control
        sa.Column('privacy_level', sa.String(20), nullable=False, server_default='private'),
        sa.Column('policy_flags', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Status
        sa.Column('has_baseline', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('root_node_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_project_specs_tenant_id', 'project_specs', ['tenant_id'])
    op.create_index('ix_project_specs_owner_id', 'project_specs', ['owner_id'])

    # =========================================================================
    # Personas Table (project.md §6.2)
    # =========================================================================
    op.create_table(
        'personas',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Identity
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),  # uploaded/generated/deep_search

        # Demographics (structured, normalized)
        sa.Column('demographics', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Preferences vector
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Perception weights
        sa.Column('perception_weights', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Bias parameters
        sa.Column('bias_parameters', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Action priors
        sa.Column('action_priors', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Uncertainty
        sa.Column('uncertainty_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('evidence_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Versioning
        sa.Column('persona_version', sa.String(20), nullable=False, server_default='1.0.0'),
        sa.Column('schema_version', sa.String(20), nullable=False, server_default='1.0.0'),

        # Segments
        sa.Column('segment_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_personas_tenant_id', 'personas', ['tenant_id'])
    op.create_index('ix_personas_project_id', 'personas', ['project_id'])

    # =========================================================================
    # Persona Segments Table
    # =========================================================================
    op.create_table(
        'persona_segments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('filter_criteria', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),
        sa.Column('persona_count', sa.Integer(), nullable=False, server_default='0'),

        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_persona_segments_project_id', 'persona_segments', ['project_id'])

    # =========================================================================
    # Event Scripts Table (project.md §6.4)
    # =========================================================================
    op.create_table(
        'event_scripts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Classification
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Scope, Deltas, Intensity, Uncertainty, Provenance (all JSONB)
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),
        sa.Column('deltas', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),
        sa.Column('intensity_profile', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),
        sa.Column('uncertainty', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),
        sa.Column('provenance', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Versioning
        sa.Column('event_version', sa.String(20), nullable=False, server_default='1.0.0'),
        sa.Column('schema_version', sa.String(20), nullable=False, server_default='1.0.0'),

        # Status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_validated', sa.Boolean(), nullable=False, server_default='false'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_event_scripts_project_id', 'event_scripts', ['project_id'])

    # =========================================================================
    # Event Bundles Table
    # =========================================================================
    op.create_table(
        'event_bundles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
                  nullable=False, server_default='{}'),
        sa.Column('execution_order', postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
                  nullable=True),
        sa.Column('joint_probability', sa.Float(), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_event_bundles_project_id', 'event_bundles', ['project_id'])

    # =========================================================================
    # Run Configs Table (project.md §6.5)
    # =========================================================================
    op.create_table(
        'run_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Versioning (critical for reproducibility)
        sa.Column('versions', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Seed configuration
        sa.Column('seed_config', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Execution parameters
        sa.Column('horizon', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('tick_rate', sa.Integer(), nullable=False, server_default='1'),

        # Scheduling and logging
        sa.Column('scheduler_profile', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),
        sa.Column('logging_profile', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Scenario modifications
        sa.Column('scenario_patch', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),

        # Resource limits
        sa.Column('max_execution_time_ms', sa.BigInteger(), nullable=True),
        sa.Column('max_agents', sa.Integer(), nullable=True),

        # Metadata
        sa.Column('label', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_template', sa.Boolean(), nullable=False, server_default='false'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_run_configs_project_id', 'run_configs', ['project_id'])
    op.create_index('ix_run_configs_is_template', 'run_configs', ['is_template'])

    # =========================================================================
    # Nodes Table (project.md §6.7) - Universe Map
    # =========================================================================
    op.create_table(
        'nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Tree structure
        sa.Column('parent_node_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('depth', sa.Integer(), nullable=False, server_default='0'),

        # Scenario
        sa.Column('scenario_patch_ref', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),

        # Run references
        sa.Column('run_refs', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='[]'),

        # Outcomes
        sa.Column('aggregated_outcome', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),

        # Probability
        sa.Column('probability', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('cumulative_probability', sa.Float(), nullable=False, server_default='1.0'),

        # Confidence
        sa.Column('confidence', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Telemetry reference
        sa.Column('telemetry_ref', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),

        # Clustering
        sa.Column('cluster_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_cluster_representative', sa.Boolean(), nullable=False,
                  server_default='false'),

        # UI state hints
        sa.Column('ui_position', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_collapsed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),

        # Metadata
        sa.Column('label', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(100)), nullable=True),

        # Status
        sa.Column('is_baseline', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_explored', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('child_count', sa.Integer(), nullable=False, server_default='0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_node_id'], ['nodes.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_nodes_project_id', 'nodes', ['project_id'])
    op.create_index('ix_nodes_parent_node_id', 'nodes', ['parent_node_id'])
    op.create_index('ix_nodes_is_baseline', 'nodes', ['is_baseline'])
    op.create_index('ix_nodes_cluster_id', 'nodes', ['cluster_id'])

    # Add FK from project_specs to nodes for root_node_id (now that nodes exists)
    op.create_foreign_key(
        'fk_project_specs_root_node_id', 'project_specs', 'nodes',
        ['root_node_id'], ['id'], ondelete='SET NULL'
    )

    # =========================================================================
    # Edges Table (project.md §6.7) - Universe Map
    # =========================================================================
    op.create_table(
        'edges',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Connections
        sa.Column('from_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('to_node_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Intervention details
        sa.Column('intervention', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Explanation
        sa.Column('explanation', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Metadata
        sa.Column('is_primary_path', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('weight', sa.Float(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_node_id'], ['nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_node_id'], ['nodes.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_edges_project_id', 'edges', ['project_id'])
    op.create_index('ix_edges_from_node_id', 'edges', ['from_node_id'])
    op.create_index('ix_edges_to_node_id', 'edges', ['to_node_id'])

    # =========================================================================
    # Node Clusters Table
    # =========================================================================
    op.create_table(
        'node_clusters',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        sa.Column('member_node_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
                  nullable=False, server_default='{}'),
        sa.Column('representative_node_id', postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column('cluster_outcome', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),
        sa.Column('cluster_probability', sa.Float(), nullable=False, server_default='1.0'),

        sa.Column('is_expanded', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('expandable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ui_position', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['representative_node_id'], ['nodes.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_node_clusters_project_id', 'node_clusters', ['project_id'])

    # =========================================================================
    # Runs Table (project.md §6.6)
    # =========================================================================
    op.create_table(
        'runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Config reference
        sa.Column('run_config_ref', postgresql.UUID(as_uuid=True), nullable=False),

        # Status
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),

        # Timing
        sa.Column('timing', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Outputs (populated when succeeded)
        sa.Column('outputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Error (populated when failed)
        sa.Column('error', postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        # Seed used
        sa.Column('actual_seed', sa.BigInteger(), nullable=False),

        # Worker info
        sa.Column('worker_id', sa.String(100), nullable=True),

        # Metadata
        sa.Column('label', sa.String(255), nullable=True),
        sa.Column('triggered_by', sa.String(20), nullable=False, server_default='user'),
        sa.Column('triggered_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_config_ref'], ['run_configs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['triggered_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_runs_project_id', 'runs', ['project_id'])
    op.create_index('ix_runs_node_id', 'runs', ['node_id'])
    op.create_index('ix_runs_status', 'runs', ['status'])

    # =========================================================================
    # Telemetry Table (project.md §6.8) - Metadata only, blobs in object storage
    # =========================================================================
    op.create_table(
        'telemetry',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Storage reference (actual data in object storage)
        sa.Column('storage_ref', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('compression', sa.String(20), nullable=False, server_default='gzip'),

        # Index metadata (for efficient queries)
        sa.Column('index_metadata', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Summary stats
        sa.Column('tick_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('keyframe_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('delta_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tracked_agents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('available_metrics', postgresql.ARRAY(sa.String(100)), nullable=True),

        # Versioning
        sa.Column('schema_version', sa.String(20), nullable=False, server_default='1.0.0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_telemetry_run_id', 'telemetry', ['run_id'])
    op.create_index('ix_telemetry_node_id', 'telemetry', ['node_id'])

    # =========================================================================
    # Reliability Reports Table (project.md §7.1)
    # =========================================================================
    op.create_table(
        'reliability_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Reliability metrics
        sa.Column('calibration', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),
        sa.Column('stability', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),
        sa.Column('sensitivity', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),
        sa.Column('drift', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),
        sa.Column('data_gaps', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),
        sa.Column('confidence', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Versioning
        sa.Column('methodology_version', sa.String(20), nullable=False, server_default='1.0.0'),
        sa.Column('schema_version', sa.String(20), nullable=False, server_default='1.0.0'),

        # Computation metadata
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('computation_time_ms', sa.Integer(), nullable=False, server_default='0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_reliability_reports_project_id', 'reliability_reports', ['project_id'])
    op.create_index('ix_reliability_reports_node_id', 'reliability_reports', ['node_id'])
    op.create_index('ix_reliability_reports_run_id', 'reliability_reports', ['run_id'])

    # =========================================================================
    # Audit Logs Table (project.md §8.5) - Enhanced for spec compliance
    # =========================================================================
    op.create_table(
        'spec_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Action details
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Context
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default='{}'),

        # Request metadata
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),

        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_spec_audit_logs_tenant_id', 'spec_audit_logs', ['tenant_id'])
    op.create_index('ix_spec_audit_logs_user_id', 'spec_audit_logs', ['user_id'])
    op.create_index('ix_spec_audit_logs_resource_type', 'spec_audit_logs', ['resource_type'])
    op.create_index('ix_spec_audit_logs_created_at', 'spec_audit_logs', ['created_at'])


def downgrade() -> None:
    # Drop tables in reverse order of creation (respecting FKs)
    op.drop_table('spec_audit_logs')
    op.drop_table('reliability_reports')
    op.drop_table('telemetry')
    op.drop_table('runs')
    op.drop_table('node_clusters')
    op.drop_table('edges')

    # Drop FK from project_specs before dropping nodes
    op.drop_constraint('fk_project_specs_root_node_id', 'project_specs', type_='foreignkey')

    op.drop_table('nodes')
    op.drop_table('run_configs')
    op.drop_table('event_bundles')
    op.drop_table('event_scripts')
    op.drop_table('persona_segments')
    op.drop_table('personas')
    op.drop_table('project_specs')

    # Remove tenant_id from users
    op.drop_constraint('fk_users_tenant_id', 'users', type_='foreignkey')
    op.drop_index('ix_users_tenant_id', table_name='users')
    op.drop_column('users', 'tenant_id')

    op.drop_table('tenants')
