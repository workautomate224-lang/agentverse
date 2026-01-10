"""STEP 9: Universe Map / Knowledge Graph Enhancements

Revision ID: step9_universe_map_001
Revises: step7_reliability_001
Create Date: 2026-01-10

This migration adds infrastructure required for STEP 9 verification:
1. Add STEP 9 columns to nodes table (reliability_score_id, staleness, pruning, annotations)
2. Add STEP 9 columns to edges table (event_script_id, node_patch_id, outcome_delta)
3. Create necessary indexes for efficient querying

STEP 9 Goal: Implement Universe Map / Knowledge Graph that organizes simulations
into a navigable, forkable, and auditable parallel-world structure.

Key Requirements:
1. Universe Node Model: Complete with all snapshot references and reliability link
2. Edge/Causal Link: Explicit FK references to EventScript/NodePatch
3. Probability Aggregation: Already exists from STEP 4 (min 2 runs)
4. Unlimited Branching: Already exists with pruning rules, aggregation views
5. Dependency Tracking: is_stale, stale_reason for downstream node staleness
6. Node Operations: is_pruned, pruned_at, annotations for prune/annotate ops
7. UI + API Exposure: Handled at service/endpoint layer
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'step9_universe_map_001'
down_revision = 'step7_reliability_001'
branch_labels = None
depends_on = None


def upgrade():
    # ==========================================================================
    # 1. Add STEP 9 columns to nodes table
    # ==========================================================================

    # STEP 9 Req 1: Snapshot references for audit trail
    op.add_column('nodes', sa.Column(
        'personas_snapshot_id',
        postgresql.UUID(as_uuid=True),
        nullable=True,
        comment='STEP 9: Reference to personas snapshot used for this node'
    ))
    op.add_column('nodes', sa.Column(
        'rules_version',
        sa.String(100),
        nullable=True,
        comment='STEP 9: Version of rules used for this node (for audit)'
    ))
    op.add_column('nodes', sa.Column(
        'parameters_version',
        sa.String(100),
        nullable=True,
        comment='STEP 9: Version of simulation parameters (for audit)'
    ))

    # STEP 9 Req 1: Reliability score FK
    op.add_column('nodes', sa.Column(
        'reliability_score_id',
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey('reliability_scores.id', ondelete='SET NULL'),
        nullable=True,
        comment='STEP 9: FK to ReliabilityScore from STEP 7'
    ))

    # STEP 9 Req 5: Dependency tracking - staleness
    op.add_column('nodes', sa.Column(
        'is_stale',
        sa.Boolean(),
        nullable=False,
        server_default='false',
        comment='STEP 9: True if this node depends on stale parent or modified ancestor'
    ))
    op.add_column('nodes', sa.Column(
        'stale_reason',
        postgresql.JSONB(),
        nullable=True,
        comment='STEP 9: Reason for staleness {ancestor_node_id, change_type, changed_at}'
    ))

    # STEP 9 Req 6: Pruning support
    op.add_column('nodes', sa.Column(
        'is_pruned',
        sa.Boolean(),
        nullable=False,
        server_default='false',
        comment='STEP 9: True if node has been pruned (hidden from default views)'
    ))
    op.add_column('nodes', sa.Column(
        'pruned_at',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='STEP 9: Timestamp when node was pruned'
    ))
    op.add_column('nodes', sa.Column(
        'pruned_reason',
        sa.Text(),
        nullable=True,
        comment='STEP 9: Reason for pruning (for audit trail)'
    ))

    # STEP 9 Req 6: Annotations for human notes
    op.add_column('nodes', sa.Column(
        'annotations',
        postgresql.JSONB(),
        nullable=True,
        server_default='{}',
        comment='STEP 9: Human annotations/notes for this node {notes, tags, bookmarked, custom_labels}'
    ))

    # Create indexes for new columns
    op.create_index(
        'ix_nodes_personas_snapshot_id',
        'nodes',
        ['personas_snapshot_id'],
        unique=False
    )
    op.create_index(
        'ix_nodes_reliability_score_id',
        'nodes',
        ['reliability_score_id'],
        unique=False
    )
    op.create_index(
        'ix_nodes_is_pruned',
        'nodes',
        ['is_pruned'],
        unique=False
    )
    op.create_index(
        'ix_nodes_is_stale',
        'nodes',
        ['is_stale'],
        unique=False
    )

    # ==========================================================================
    # 2. Add STEP 9 columns to edges table
    # ==========================================================================

    # STEP 9 Req 2: Explicit FK to EventScript
    op.add_column('edges', sa.Column(
        'event_script_id',
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey('event_scripts.id', ondelete='SET NULL'),
        nullable=True,
        comment='STEP 9: FK reference to EventScript that caused this edge'
    ))

    # STEP 9 Req 2: Explicit FK to NodePatch
    op.add_column('edges', sa.Column(
        'node_patch_id',
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey('node_patches.id', ondelete='SET NULL'),
        nullable=True,
        comment='STEP 9: FK reference to NodePatch describing the transformation'
    ))

    # STEP 9 Req 2: Outcome delta
    op.add_column('edges', sa.Column(
        'outcome_delta',
        postgresql.JSONB(),
        nullable=True,
        comment='STEP 9: Delta between parent and child aggregated_outcome {metric: {before, after, change_pct}}'
    ))

    # Create indexes for new columns
    op.create_index(
        'ix_edges_event_script_id',
        'edges',
        ['event_script_id'],
        unique=False
    )
    op.create_index(
        'ix_edges_node_patch_id',
        'edges',
        ['node_patch_id'],
        unique=False
    )

    # ==========================================================================
    # 3. Create composite indexes for common query patterns
    # ==========================================================================

    # Index for finding stale nodes in a project
    op.create_index(
        'ix_nodes_project_stale',
        'nodes',
        ['project_id', 'is_stale'],
        unique=False,
        postgresql_where=sa.text('is_stale = true')
    )

    # Index for finding pruned nodes in a project
    op.create_index(
        'ix_nodes_project_pruned',
        'nodes',
        ['project_id', 'is_pruned'],
        unique=False,
        postgresql_where=sa.text('is_pruned = true')
    )


def downgrade():
    # ==========================================================================
    # Drop indexes
    # ==========================================================================
    op.drop_index('ix_nodes_project_pruned', table_name='nodes')
    op.drop_index('ix_nodes_project_stale', table_name='nodes')
    op.drop_index('ix_edges_node_patch_id', table_name='edges')
    op.drop_index('ix_edges_event_script_id', table_name='edges')
    op.drop_index('ix_nodes_is_stale', table_name='nodes')
    op.drop_index('ix_nodes_is_pruned', table_name='nodes')
    op.drop_index('ix_nodes_reliability_score_id', table_name='nodes')
    op.drop_index('ix_nodes_personas_snapshot_id', table_name='nodes')

    # ==========================================================================
    # Drop columns from edges table
    # ==========================================================================
    op.drop_column('edges', 'outcome_delta')
    op.drop_column('edges', 'node_patch_id')
    op.drop_column('edges', 'event_script_id')

    # ==========================================================================
    # Drop columns from nodes table
    # ==========================================================================
    op.drop_column('nodes', 'annotations')
    op.drop_column('nodes', 'pruned_reason')
    op.drop_column('nodes', 'pruned_at')
    op.drop_column('nodes', 'is_pruned')
    op.drop_column('nodes', 'stale_reason')
    op.drop_column('nodes', 'is_stale')
    op.drop_column('nodes', 'reliability_score_id')
    op.drop_column('nodes', 'parameters_version')
    op.drop_column('nodes', 'rules_version')
    op.drop_column('nodes', 'personas_snapshot_id')
