"""STEP 3: Persona Snapshot Audit Infrastructure

Revision ID: step3_persona_snapshot_001
Revises: step1_run_audit_001
Create Date: 2026-01-10

This migration adds the infrastructure required for Step 3 verification:
1. PersonaValidationReport table (validation analysis for persona sets)
2. PersonaSnapshot table (immutable capture of personas used for runs)
3. New columns in run_specs for personas tracking (personas_snapshot_id, personas_summary)

STEP 3 Goal: Make Personas a real causal input to simulations,
not a decorative UI list. Personas must be immutable per run,
auditable, and provably influential on outcomes.

Reference: Step 3 Audit Requirements
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'step3_persona_snapshot_001'
down_revision = 'step1_run_audit_001'
branch_labels = None
depends_on = None


def upgrade():
    # ==========================================================================
    # 1. PersonaValidationReport Table
    # Must be created first because PersonaSnapshot references it
    # ==========================================================================
    op.create_table(
        'persona_validation_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('snapshot_id', postgresql.UUID(as_uuid=True), nullable=True),  # Will be linked after snapshot creation
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('persona_templates.id', ondelete='SET NULL'), nullable=True),

        # Report status
        sa.Column('status', sa.String(50), default='pending', nullable=False),

        # Validation scores and analysis (JSONB for flexibility)
        sa.Column('overall_score', sa.Float, nullable=False),
        sa.Column('coverage_gaps', postgresql.JSONB, nullable=False, default={}),
        sa.Column('duplication_analysis', postgresql.JSONB, nullable=False, default={}),
        sa.Column('bias_risk', postgresql.JSONB, nullable=False, default={}),
        sa.Column('uncertainty_warnings', postgresql.JSONB, nullable=False, default={}),

        # Statistics and recommendations
        sa.Column('statistics', postgresql.JSONB, nullable=False, default={}),
        sa.Column('recommendations', postgresql.JSONB, nullable=False, default=[]),

        # Confidence impact for outcome calculations
        sa.Column('confidence_impact', sa.Float, default=0.0, nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ==========================================================================
    # 2. PersonaSnapshot Table
    # Immutable capture of personas used for a simulation run
    # ==========================================================================
    op.create_table(
        'persona_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_specs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('source_template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('persona_templates.id', ondelete='SET NULL'), nullable=True),

        # Snapshot identification
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('total_personas', sa.Integer, nullable=False),

        # Segment summary with weights (STEP 3 requirement)
        sa.Column('segment_summary', postgresql.JSONB, nullable=False, default={}),

        # Full immutable copy of all persona data
        sa.Column('personas_data', postgresql.JSONB, nullable=False, default=[]),

        # Data integrity hash
        sa.Column('data_hash', sa.String(64), nullable=False),

        # Link to validation report (optional)
        sa.Column('validation_report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('persona_validation_reports.id', ondelete='SET NULL'), nullable=True),

        # Confidence score based on persona quality
        sa.Column('confidence_score', sa.Float, default=0.8, nullable=False),

        # Immutability flag
        sa.Column('is_locked', sa.Boolean, default=True, nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create index for efficient snapshot queries
    op.create_index('ix_persona_snapshots_project_created', 'persona_snapshots', ['project_id', 'created_at'])

    # ==========================================================================
    # 3. Add personas tracking columns to run_specs table
    # ==========================================================================
    op.add_column(
        'run_specs',
        sa.Column(
            'personas_snapshot_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('persona_snapshots.id', ondelete='SET NULL'),
            nullable=True,
            index=True
        )
    )
    op.add_column(
        'run_specs',
        sa.Column(
            'personas_summary',
            postgresql.JSONB,
            nullable=True,
            comment='STEP 3: Summary of persona segments and weights used in this run'
        )
    )


def downgrade():
    # Remove columns from run_specs
    op.drop_column('run_specs', 'personas_summary')
    op.drop_column('run_specs', 'personas_snapshot_id')

    # Drop index
    op.drop_index('ix_persona_snapshots_project_created', table_name='persona_snapshots')

    # Drop tables (order matters for foreign keys)
    op.drop_table('persona_snapshots')
    op.drop_table('persona_validation_reports')
