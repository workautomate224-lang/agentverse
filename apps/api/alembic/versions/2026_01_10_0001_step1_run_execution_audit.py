"""STEP 1: Run Execution Audit Infrastructure

Revision ID: step1_run_audit_001
Revises: llm_phase_001
Create Date: 2026-01-10

This migration adds the infrastructure required for Step 1 verification:
1. CREATED status in run lifecycle (CREATED -> QUEUED -> RUNNING -> SUCCEEDED/FAILED)
2. Worker heartbeat tracking (worker_id, last_seen_at)
3. RunSpec artifact table (explicit specification storage)
4. RunTrace table (execution trace entries)

Reference: Step 1 Audit Requirements
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'step1_run_audit_001'
down_revision = 'llm_phase_001'
branch_labels = None
depends_on = None


def upgrade():
    # ==========================================================================
    # 1. Worker Heartbeat Table
    # ==========================================================================
    op.create_table(
        'worker_heartbeats',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('worker_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('hostname', sa.String(255), nullable=True),
        sa.Column('pid', sa.Integer, nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(50), default='active', nullable=False),
        sa.Column('current_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('runs_executed', sa.Integer, default=0, nullable=False),
        sa.Column('runs_failed', sa.Integer, default=0, nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ==========================================================================
    # 2. RunSpec Artifact Table
    # ==========================================================================
    op.create_table(
        'run_specs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('runs.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_specs.id', ondelete='CASCADE'), nullable=False, index=True),

        # Core specification fields
        sa.Column('ticks_total', sa.Integer, nullable=False),
        sa.Column('seed', sa.BigInteger, nullable=False),
        sa.Column('model_config', postgresql.JSONB, nullable=False),
        sa.Column('environment_spec', postgresql.JSONB, nullable=False),
        sa.Column('scheduler_config', postgresql.JSONB, nullable=True),

        # Version tracking (C4: Auditable)
        sa.Column('engine_version', sa.String(50), nullable=False),
        sa.Column('ruleset_version', sa.String(50), nullable=False),
        sa.Column('dataset_version', sa.String(50), nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ==========================================================================
    # 3. RunTrace Table
    # ==========================================================================
    op.create_table(
        'run_traces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('runs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),

        # Trace entry fields
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('worker_id', sa.String(255), nullable=False),
        sa.Column('execution_stage', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),

        # Additional context
        sa.Column('tick_number', sa.Integer, nullable=True),
        sa.Column('agents_processed', sa.Integer, nullable=True),
        sa.Column('events_count', sa.Integer, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create index for efficient trace queries
    op.create_index('ix_run_traces_run_timestamp', 'run_traces', ['run_id', 'timestamp'])

    # ==========================================================================
    # 4. Add worker tracking fields to runs table
    # ==========================================================================
    # Add worker_started_at and worker_last_heartbeat_at columns
    op.add_column('runs', sa.Column('worker_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('runs', sa.Column('worker_last_heartbeat_at', sa.DateTime(timezone=True), nullable=True))

    # ==========================================================================
    # 5. Update runs status check constraint to include 'created'
    # ==========================================================================
    # Note: The status column already exists, we need to ensure 'created' is a valid value
    # This is handled in the model code, not at DB level since status is a String


def downgrade():
    # Remove columns from runs
    op.drop_column('runs', 'worker_last_heartbeat_at')
    op.drop_column('runs', 'worker_started_at')

    # Drop index
    op.drop_index('ix_run_traces_run_timestamp', table_name='run_traces')

    # Drop tables
    op.drop_table('run_traces')
    op.drop_table('run_specs')
    op.drop_table('worker_heartbeats')
