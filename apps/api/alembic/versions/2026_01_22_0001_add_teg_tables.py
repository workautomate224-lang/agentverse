"""Add TEG (Thought Expansion Graph) tables

Revision ID: teg_universe_map_001
Revises: fix_run_outcomes_fk_001
Create Date: 2026-01-22

This migration adds tables for the Thought Expansion Graph (TEG),
which replaces the old Universe Map with a mind-map style scenario explorer.

Tables:
- teg_graphs: Root container for each project's TEG
- teg_nodes: Individual scenario nodes (OUTCOME_VERIFIED, SCENARIO_DRAFT, EVIDENCE)
- teg_edges: Relationships between nodes (EXPANDS_TO, RUNS_TO, etc.)

Reference: docs/TEG_UNIVERSE_MAP_EXECUTION.md
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'teg_universe_map_001'
down_revision: Union[str, None] = 'fix_run_outcomes_fk_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists (for idempotency)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = :table
            )
            """
        ),
        {"table": table_name},
    )
    return result.scalar()


def enum_exists(enum_name: str) -> bool:
    """Check if an enum type exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT FROM pg_type
                WHERE typname = :enum
            )
            """
        ),
        {"enum": enum_name},
    )
    return result.scalar()


def upgrade() -> None:
    # Create enum types if they don't exist
    if not enum_exists('teg_node_type'):
        op.execute("""
            CREATE TYPE teg_node_type AS ENUM (
                'OUTCOME_VERIFIED',
                'SCENARIO_DRAFT',
                'EVIDENCE'
            )
        """)

    if not enum_exists('teg_node_status'):
        op.execute("""
            CREATE TYPE teg_node_status AS ENUM (
                'DRAFT',
                'QUEUED',
                'RUNNING',
                'DONE',
                'FAILED'
            )
        """)

    if not enum_exists('teg_edge_relation'):
        op.execute("""
            CREATE TYPE teg_edge_relation AS ENUM (
                'EXPANDS_TO',
                'RUNS_TO',
                'FORKS_FROM',
                'SUPPORTS',
                'CONFLICTS'
            )
        """)

    # =========================================================================
    # teg_graphs table
    # =========================================================================
    if not table_exists('teg_graphs'):
        op.create_table(
            'teg_graphs',
            # Primary key
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),

            # Multi-tenancy
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),

            # Foreign key to project_specs
            sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),

            # Active baseline node for comparisons
            sa.Column('active_baseline_node_id', postgresql.UUID(as_uuid=True), nullable=True),

            # Graph metadata
            sa.Column('metadata_json', postgresql.JSONB(), nullable=False,
                      server_default='{}'),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),

            # Foreign keys
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),

            # One TEG per project
            sa.UniqueConstraint('project_id', name='uq_teg_graphs_project'),
        )

        # Indexes
        op.create_index('ix_teg_graphs_tenant_id', 'teg_graphs', ['tenant_id'])
        op.create_index('ix_teg_graphs_tenant_project', 'teg_graphs',
                        ['tenant_id', 'project_id'])

    # =========================================================================
    # teg_nodes table
    # =========================================================================
    if not table_exists('teg_nodes'):
        op.create_table(
            'teg_nodes',
            # Primary key
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),

            # Multi-tenancy
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),

            # Parent references
            sa.Column('graph_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),

            # Parent node for tree structure
            sa.Column('parent_node_id', postgresql.UUID(as_uuid=True), nullable=True),

            # Node type and status (using the enums)
            sa.Column('node_type',
                      postgresql.ENUM('OUTCOME_VERIFIED', 'SCENARIO_DRAFT', 'EVIDENCE',
                                      name='teg_node_type', create_type=False),
                      nullable=False),
            sa.Column('status',
                      postgresql.ENUM('DRAFT', 'QUEUED', 'RUNNING', 'DONE', 'FAILED',
                                      name='teg_node_status', create_type=False),
                      nullable=False, server_default='DRAFT'),

            # Display info
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('summary', sa.Text(), nullable=True),

            # Payload (JSONB for type-specific data)
            sa.Column('payload', postgresql.JSONB(), nullable=False, server_default='{}'),

            # Links to existing infrastructure
            sa.Column('links', postgresql.JSONB(), nullable=False, server_default='{}'),

            # Position for graph rendering
            sa.Column('position', postgresql.JSONB(), nullable=True),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),

            # Foreign keys
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['graph_id'], ['teg_graphs.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['project_specs.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['parent_node_id'], ['teg_nodes.id'], ondelete='SET NULL'),
        )

        # Indexes
        op.create_index('ix_teg_nodes_tenant_id', 'teg_nodes', ['tenant_id'])
        op.create_index('ix_teg_nodes_graph_id', 'teg_nodes', ['graph_id'])
        op.create_index('ix_teg_nodes_project_id', 'teg_nodes', ['project_id'])
        op.create_index('ix_teg_nodes_tenant_project', 'teg_nodes',
                        ['tenant_id', 'project_id'])
        op.create_index('ix_teg_nodes_parent', 'teg_nodes', ['parent_node_id'])
        op.create_index('ix_teg_nodes_type_status', 'teg_nodes', ['node_type', 'status'])

    # =========================================================================
    # teg_edges table
    # =========================================================================
    if not table_exists('teg_edges'):
        op.create_table(
            'teg_edges',
            # Primary key
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),

            # Multi-tenancy
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),

            # Graph reference
            sa.Column('graph_id', postgresql.UUID(as_uuid=True), nullable=False),

            # Edge endpoints
            sa.Column('from_node_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('to_node_id', postgresql.UUID(as_uuid=True), nullable=False),

            # Relationship type
            sa.Column('relation',
                      postgresql.ENUM('EXPANDS_TO', 'RUNS_TO', 'FORKS_FROM',
                                      'SUPPORTS', 'CONFLICTS',
                                      name='teg_edge_relation', create_type=False),
                      nullable=False),

            # Optional metadata
            sa.Column('metadata_json', postgresql.JSONB(), nullable=False,
                      server_default='{}'),

            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),

            # Foreign keys
            sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['graph_id'], ['teg_graphs.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['from_node_id'], ['teg_nodes.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['to_node_id'], ['teg_nodes.id'], ondelete='CASCADE'),
        )

        # Indexes
        op.create_index('ix_teg_edges_tenant_id', 'teg_edges', ['tenant_id'])
        op.create_index('ix_teg_edges_graph_id', 'teg_edges', ['graph_id'])
        op.create_index('ix_teg_edges_from_node', 'teg_edges', ['from_node_id'])
        op.create_index('ix_teg_edges_to_node', 'teg_edges', ['to_node_id'])
        op.create_index('ix_teg_edges_relation', 'teg_edges', ['relation'])

    # =========================================================================
    # Add self-referential FK constraint to teg_graphs.active_baseline_node_id
    # (done separately since teg_nodes table must exist first)
    # =========================================================================
    # Note: We can't add FK constraint for active_baseline_node_id because
    # it creates a circular dependency. The application layer handles validation.


def downgrade() -> None:
    # Drop teg_edges first (depends on teg_nodes)
    if table_exists('teg_edges'):
        op.drop_index('ix_teg_edges_relation', table_name='teg_edges')
        op.drop_index('ix_teg_edges_to_node', table_name='teg_edges')
        op.drop_index('ix_teg_edges_from_node', table_name='teg_edges')
        op.drop_index('ix_teg_edges_graph_id', table_name='teg_edges')
        op.drop_index('ix_teg_edges_tenant_id', table_name='teg_edges')
        op.drop_table('teg_edges')

    # Drop teg_nodes (depends on teg_graphs)
    if table_exists('teg_nodes'):
        op.drop_index('ix_teg_nodes_type_status', table_name='teg_nodes')
        op.drop_index('ix_teg_nodes_parent', table_name='teg_nodes')
        op.drop_index('ix_teg_nodes_tenant_project', table_name='teg_nodes')
        op.drop_index('ix_teg_nodes_project_id', table_name='teg_nodes')
        op.drop_index('ix_teg_nodes_graph_id', table_name='teg_nodes')
        op.drop_index('ix_teg_nodes_tenant_id', table_name='teg_nodes')
        op.drop_table('teg_nodes')

    # Drop teg_graphs
    if table_exists('teg_graphs'):
        op.drop_index('ix_teg_graphs_tenant_project', table_name='teg_graphs')
        op.drop_index('ix_teg_graphs_tenant_id', table_name='teg_graphs')
        op.drop_table('teg_graphs')

    # Drop enum types
    if enum_exists('teg_edge_relation'):
        op.execute('DROP TYPE teg_edge_relation')
    if enum_exists('teg_node_status'):
        op.execute('DROP TYPE teg_node_status')
    if enum_exists('teg_node_type'):
        op.execute('DROP TYPE teg_node_type')
