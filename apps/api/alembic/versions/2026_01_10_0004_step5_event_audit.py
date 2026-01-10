"""STEP 5: Event Audit Infrastructure

Revision ID: step5_event_audit_001
Revises: step4_universe_map_001
Create Date: 2026-01-10

This migration adds infrastructure required for STEP 5 verification:
1. Add source_text, affected_variables, confidence_score to event_scripts
2. Add event_script_id FK to node_patches for proper audit trail
3. Create event_candidates table for parsed but uncommitted interpretations
4. Add validation_result column to event_scripts

STEP 5 Goal: Turn natural-language "What-if" inputs into real, auditable,
and reproducible world changes.

Key Principle: An Event must modify the world configuration, not directly
produce an outcome. Events compile to NodePatches which generate RunSpecs.

Reference: Step 5 Audit Requirements
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'step5_event_audit_001'
down_revision = 'step4_universe_map_001'
branch_labels = None
depends_on = None


def upgrade():
    # ==========================================================================
    # 1. Add STEP 5 Event Audit columns to event_scripts table
    # ==========================================================================

    # Source text: explicit field for original NL input (was buried in provenance)
    op.add_column(
        'event_scripts',
        sa.Column(
            'source_text',
            sa.Text,
            nullable=True,
            comment='STEP 5: Original natural language input that was compiled'
        )
    )

    # Affected variables: explicit array field (was derived from deltas)
    op.add_column(
        'event_scripts',
        sa.Column(
            'affected_variables',
            postgresql.ARRAY(sa.String(100)),
            nullable=True,
            server_default='{}',
            comment='STEP 5: List of variables this event affects'
        )
    )

    # Confidence score: how confident is the compiler in this interpretation
    op.add_column(
        'event_scripts',
        sa.Column(
            'confidence_score',
            sa.Float,
            nullable=True,
            comment='STEP 5: Compiler confidence in this interpretation (0.0-1.0)'
        )
    )

    # Ambiguity score: how ambiguous was the original input
    op.add_column(
        'event_scripts',
        sa.Column(
            'ambiguity_score',
            sa.Float,
            nullable=True,
            comment='STEP 5: Ambiguity level of the original input (0.0-1.0)'
        )
    )

    # Validation result: detailed validation status
    op.add_column(
        'event_scripts',
        sa.Column(
            'validation_result',
            postgresql.JSONB,
            nullable=True,
            comment='STEP 5: Detailed validation result {passed, errors, warnings}'
        )
    )

    # ==========================================================================
    # 2. Add event_script_id FK to node_patches for proper audit trail
    # This replaces the JSONB event_script field with a proper FK reference
    # ==========================================================================
    op.add_column(
        'node_patches',
        sa.Column(
            'event_script_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='STEP 5: FK reference to EventScript (replaces JSONB copy)'
        )
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_node_patches_event_script_id',
        'node_patches',
        'event_scripts',
        ['event_script_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Create index for efficient lookups (if not exists - idempotent)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_node_patches_event_script_id
        ON node_patches (event_script_id)
    """)

    # ==========================================================================
    # 3. Create EventCandidate table for parsed but uncommitted interpretations
    # Users can review multiple interpretations before committing to EventScript
    # ==========================================================================
    op.create_table(
        'event_candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('project_specs.id', ondelete='CASCADE'),
                  nullable=False, index=True),

        # Compilation reference
        sa.Column('compilation_id', sa.String(100), nullable=False, index=True,
                  comment='STEP 5: ID of the compilation session'),

        # Original input
        sa.Column('source_text', sa.Text, nullable=False,
                  comment='STEP 5: Original natural language input'),

        # Candidate details
        sa.Column('candidate_index', sa.Integer, nullable=False,
                  comment='STEP 5: Index of this candidate in the compilation result'),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),

        # Parsed interpretation
        sa.Column('parsed_intent', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 5: Structured intent extracted from NL input'),
        sa.Column('proposed_deltas', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 5: Proposed deltas to apply'),
        sa.Column('proposed_scope', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 5: Proposed scope of the event'),
        sa.Column('affected_variables', postgresql.ARRAY(sa.String(100)),
                  nullable=False, server_default='{}',
                  comment='STEP 5: Variables this candidate would affect'),

        # Scoring
        sa.Column('probability', sa.Float, nullable=False, default=0.0,
                  comment='STEP 5: Probability assigned to this interpretation'),
        sa.Column('confidence_score', sa.Float, nullable=False, default=0.0,
                  comment='STEP 5: Compiler confidence in this interpretation'),
        sa.Column('cluster_id', sa.String(100), nullable=True,
                  comment='STEP 5: ID of the scenario cluster this belongs to'),

        # Status
        sa.Column('status', sa.String(50), nullable=False, default='pending',
                  comment='STEP 5: pending, selected, rejected, committed'),
        sa.Column('committed_event_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('event_scripts.id', ondelete='SET NULL'),
                  nullable=True,
                  comment='STEP 5: EventScript ID if this candidate was committed'),

        # Provenance
        sa.Column('compiler_version', sa.String(50), nullable=False),
        sa.Column('model_used', sa.String(100), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column('selected_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Index for efficient lookups
    op.create_index('ix_event_candidates_compilation', 'event_candidates',
                    ['compilation_id', 'tenant_id'])
    op.create_index('ix_event_candidates_status', 'event_candidates',
                    ['tenant_id', 'status'])

    # ==========================================================================
    # 4. Create EventValidation table for tracking validation history
    # ==========================================================================
    op.create_table(
        'event_validations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('event_script_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('event_scripts.id', ondelete='CASCADE'),
                  nullable=False, index=True),

        # Validation context
        sa.Column('validation_type', sa.String(50), nullable=False,
                  comment='STEP 5: Type: parameter_range, variable_existence, conflict_detection'),
        sa.Column('context_node_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('nodes.id', ondelete='SET NULL'),
                  nullable=True,
                  comment='STEP 5: Node context for conflict detection'),

        # Results
        sa.Column('passed', sa.Boolean, nullable=False),
        sa.Column('errors', postgresql.JSONB, nullable=False, default=list,
                  comment='STEP 5: List of validation errors'),
        sa.Column('warnings', postgresql.JSONB, nullable=False, default=list,
                  comment='STEP 5: List of validation warnings'),
        sa.Column('details', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 5: Detailed validation output'),

        # Timestamp
        sa.Column('validated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    op.create_index('ix_event_validations_event', 'event_validations',
                    ['event_script_id', 'validated_at'])


def downgrade():
    # Drop event_validations table
    op.drop_index('ix_event_validations_event', table_name='event_validations')
    op.drop_table('event_validations')

    # Drop event_candidates table
    op.drop_index('ix_event_candidates_status', table_name='event_candidates')
    op.drop_index('ix_event_candidates_compilation', table_name='event_candidates')
    op.drop_table('event_candidates')

    # Drop index, FK and column from node_patches
    op.drop_index('ix_node_patches_event_script_id', table_name='node_patches')
    op.drop_constraint('fk_node_patches_event_script_id', 'node_patches', type_='foreignkey')
    op.drop_column('node_patches', 'event_script_id')

    # Drop columns from event_scripts
    op.drop_column('event_scripts', 'validation_result')
    op.drop_column('event_scripts', 'ambiguity_score')
    op.drop_column('event_scripts', 'confidence_score')
    op.drop_column('event_scripts', 'affected_variables')
    op.drop_column('event_scripts', 'source_text')
