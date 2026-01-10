"""STEP 10: Production Readiness Infrastructure

Revision ID: step10_production_001
Revises: step9_universe_map_001
Create Date: 2026-01-10

This migration adds infrastructure required for STEP 10 verification:
1. Cost Tracking tables (run_cost_records, planning_cost_records, project_cost_summaries)
2. Quota/Budget tables (tenant_quota_configs, quota_usage_records, quota_violations)
3. Feature Flag tables (feature_flags, tenant_feature_overrides)
4. Safety Guardrail tables (safety_rules, safety_incidents)
5. Governance Audit table (governance_audit_logs)
6. Export Integrity table (export_bundles)

STEP 10 Goal: Make the platform production-ready with controllable cost,
access control, safety guardrails, and full auditability.

Key Requirements:
1. Cost Tracking: Every run must have cost record (LLM tokens, compute, queue)
2. Budgets and Quotas: Server-side enforcement, block or degrade when exceeded
3. Feature Flags: Tier-based gating, server-side checks (not UI-only)
4. Rate Limiting: Already exists in middleware
5. Safety Guardrails: Risk classification, block/degrade high-risk
6. Governance Audit: Immutable logs with actor, timestamp, entity ids, spec_hash
7. Export Integrity: Spec hashes, artifact ids, checksums
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'step10_production_001'
down_revision = 'step9_universe_map_001'
branch_labels = None
depends_on = None


def upgrade():
    # ==========================================================================
    # 1. Cost Tracking Tables (STEP 10 Requirement 1)
    # ==========================================================================

    # Run Cost Records
    op.create_table(
        'run_cost_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('runs.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('project_specs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('nodes.id', ondelete='SET NULL'), nullable=True),

        # LLM Token Usage
        sa.Column('llm_input_tokens', sa.BigInteger(), default=0, nullable=False),
        sa.Column('llm_output_tokens', sa.BigInteger(), default=0, nullable=False),
        sa.Column('llm_total_tokens', sa.BigInteger(), default=0, nullable=False),
        sa.Column('llm_cost_usd', sa.Numeric(12, 6), default=0, nullable=False),
        sa.Column('llm_call_count', sa.Integer(), default=0, nullable=False),

        # Compute Time
        sa.Column('compute_time_ms', sa.BigInteger(), default=0, nullable=False),
        sa.Column('worker_time_ms', sa.BigInteger(), default=0, nullable=False),
        sa.Column('queue_latency_ms', sa.BigInteger(), default=0, nullable=False),

        # Ensemble tracking
        sa.Column('ensemble_index', sa.Integer(), default=0, nullable=False),
        sa.Column('ensemble_size', sa.Integer(), default=1, nullable=False),

        # Simulation specifics
        sa.Column('tick_count', sa.Integer(), default=0, nullable=False),
        sa.Column('agent_count', sa.Integer(), default=0, nullable=False),

        # Total cost
        sa.Column('total_cost_usd', sa.Numeric(12, 6), default=0, nullable=False),

        # Timestamps
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    op.create_index('ix_run_cost_tenant_id', 'run_cost_records', ['tenant_id'])
    op.create_index('ix_run_cost_run_id', 'run_cost_records', ['run_id'], unique=True)
    op.create_index('ix_run_cost_project_id', 'run_cost_records', ['project_id'])
    op.create_index('ix_run_cost_node_id', 'run_cost_records', ['node_id'])

    # Planning Cost Records
    op.create_table(
        'planning_cost_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('planning_spec_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('planning_specs.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('project_specs.id', ondelete='CASCADE'), nullable=False),

        # LLM costs
        sa.Column('llm_input_tokens', sa.BigInteger(), default=0, nullable=False),
        sa.Column('llm_output_tokens', sa.BigInteger(), default=0, nullable=False),
        sa.Column('llm_cost_usd', sa.Numeric(12, 6), default=0, nullable=False),

        # Evaluation costs
        sa.Column('evaluation_run_count', sa.Integer(), default=0, nullable=False),
        sa.Column('evaluation_run_cost_usd', sa.Numeric(12, 6), default=0, nullable=False),

        # Candidates
        sa.Column('candidates_generated', sa.Integer(), default=0, nullable=False),
        sa.Column('candidates_evaluated', sa.Integer(), default=0, nullable=False),
        sa.Column('candidates_pruned', sa.Integer(), default=0, nullable=False),

        # Timing
        sa.Column('total_time_ms', sa.BigInteger(), default=0, nullable=False),

        # Total
        sa.Column('total_cost_usd', sa.Numeric(12, 6), default=0, nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    op.create_index('ix_planning_cost_tenant_id', 'planning_cost_records', ['tenant_id'])
    op.create_index('ix_planning_cost_planning_id', 'planning_cost_records', ['planning_spec_id'], unique=True)
    op.create_index('ix_planning_cost_project_id', 'planning_cost_records', ['project_id'])

    # Project Cost Summaries
    op.create_table(
        'project_cost_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('project_specs.id', ondelete='CASCADE'), nullable=False),

        # Period
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),

        # Run costs
        sa.Column('run_count', sa.Integer(), default=0, nullable=False),
        sa.Column('run_cost_usd', sa.Numeric(12, 6), default=0, nullable=False),

        # Planning costs
        sa.Column('planning_count', sa.Integer(), default=0, nullable=False),
        sa.Column('planning_cost_usd', sa.Numeric(12, 6), default=0, nullable=False),

        # LLM costs
        sa.Column('llm_tokens_total', sa.BigInteger(), default=0, nullable=False),
        sa.Column('llm_cost_usd', sa.Numeric(12, 6), default=0, nullable=False),

        # Totals
        sa.Column('total_cost_usd', sa.Numeric(12, 6), default=0, nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.UniqueConstraint('project_id', 'period_type', 'period_start', name='uq_project_cost_period'),
    )

    op.create_index('ix_project_cost_tenant_id', 'project_cost_summaries', ['tenant_id'])
    op.create_index('ix_project_cost_project_id', 'project_cost_summaries', ['project_id'])
    op.create_index('ix_project_cost_tenant_period', 'project_cost_summaries',
                    ['tenant_id', 'period_type', 'period_start'])

    # ==========================================================================
    # 2. Quota/Budget Tables (STEP 10 Requirement 2)
    # ==========================================================================

    # Tenant Quota Configurations
    op.create_table(
        'tenant_quota_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),

        # Plan tier
        sa.Column('plan_tier', sa.String(50), default='free', nullable=False),

        # Run limits
        sa.Column('daily_run_limit', sa.Integer(), default=10, nullable=False),
        sa.Column('monthly_run_limit', sa.Integer(), default=100, nullable=False),
        sa.Column('concurrent_run_limit', sa.Integer(), default=2, nullable=False),

        # Planning limits
        sa.Column('daily_planning_limit', sa.Integer(), default=5, nullable=False),
        sa.Column('planning_evaluation_budget', sa.Integer(), default=10, nullable=False),

        # Simulation limits
        sa.Column('max_ensemble_size', sa.Integer(), default=3, nullable=False),
        sa.Column('max_agents_per_run', sa.Integer(), default=100, nullable=False),
        sa.Column('max_ticks_per_run', sa.Integer(), default=1000, nullable=False),

        # Token limits
        sa.Column('daily_llm_token_limit', sa.BigInteger(), default=100000, nullable=False),
        sa.Column('monthly_llm_token_limit', sa.BigInteger(), default=1000000, nullable=False),

        # Storage
        sa.Column('storage_limit_mb', sa.Integer(), default=1024, nullable=False),

        # Cost limits
        sa.Column('daily_cost_limit_usd', sa.Numeric(12, 2), nullable=True),
        sa.Column('monthly_cost_limit_usd', sa.Numeric(12, 2), nullable=True),

        # Enforcement action
        sa.Column('exceeded_action', sa.String(20), default='block', nullable=False),

        # Active status
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.UniqueConstraint('tenant_id', name='uq_tenant_quota_tenant'),
    )

    op.create_index('ix_tenant_quota_tenant_id', 'tenant_quota_configs', ['tenant_id'])

    # Quota Usage Records
    op.create_table(
        'quota_usage_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),

        # Period
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),

        # Usage counters
        sa.Column('runs_used', sa.Integer(), default=0, nullable=False),
        sa.Column('concurrent_runs', sa.Integer(), default=0, nullable=False),
        sa.Column('planning_used', sa.Integer(), default=0, nullable=False),
        sa.Column('llm_tokens_used', sa.BigInteger(), default=0, nullable=False),
        sa.Column('storage_used_mb', sa.Integer(), default=0, nullable=False),
        sa.Column('cost_used_usd', sa.Numeric(12, 6), default=0, nullable=False),

        # Timestamps
        sa.Column('last_updated', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.UniqueConstraint('tenant_id', 'period_type', 'period_start', name='uq_quota_usage_period'),
    )

    op.create_index('ix_quota_usage_tenant_id', 'quota_usage_records', ['tenant_id'])
    op.create_index('ix_quota_usage_tenant_period', 'quota_usage_records',
                    ['tenant_id', 'period_type', 'period_start'])

    # Quota Violations
    op.create_table(
        'quota_violations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Violation details
        sa.Column('quota_type', sa.String(50), nullable=False),
        sa.Column('limit_value', sa.BigInteger(), nullable=False),
        sa.Column('current_value', sa.BigInteger(), nullable=False),
        sa.Column('requested_value', sa.BigInteger(), nullable=False),

        # Action taken
        sa.Column('action_taken', sa.String(20), nullable=False),

        # Request context
        sa.Column('request_type', sa.String(50), nullable=False),
        sa.Column('request_id', sa.String(100), nullable=True),

        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    op.create_index('ix_quota_violation_tenant_id', 'quota_violations', ['tenant_id'])
    op.create_index('ix_quota_violation_user_id', 'quota_violations', ['user_id'])
    op.create_index('ix_quota_violation_created_at', 'quota_violations', ['created_at'])

    # ==========================================================================
    # 3. Feature Flag Tables (STEP 10 Requirement 3)
    # ==========================================================================

    # Feature Flags
    op.create_table(
        'feature_flags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),

        # Flag identification
        sa.Column('flag_key', sa.String(100), nullable=False, unique=True),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Default state
        sa.Column('is_enabled_by_default', sa.Boolean(), default=False, nullable=False),

        # Tier-based access
        sa.Column('enabled_tiers', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),

        # Percentage rollout
        sa.Column('rollout_percentage', sa.Integer(), default=100, nullable=False),

        # Override settings
        sa.Column('allow_tenant_override', sa.Boolean(), default=True, nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index('ix_feature_flags_flag_key', 'feature_flags', ['flag_key'], unique=True)

    # Tenant Feature Overrides
    op.create_table(
        'tenant_feature_overrides',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('feature_flag_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('feature_flags.id', ondelete='CASCADE'), nullable=False),

        # Override
        sa.Column('is_enabled', sa.Boolean(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),

        sa.UniqueConstraint('tenant_id', 'feature_flag_id', name='uq_tenant_feature_override'),
    )

    op.create_index('ix_tenant_feature_tenant_id', 'tenant_feature_overrides', ['tenant_id'])
    op.create_index('ix_tenant_feature_flag_id', 'tenant_feature_overrides', ['feature_flag_id'])

    # ==========================================================================
    # 4. Safety Guardrail Tables (STEP 10 Requirement 5)
    # ==========================================================================

    # Safety Rules
    op.create_table(
        'safety_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),

        # Rule identification
        sa.Column('rule_key', sa.String(100), nullable=False, unique=True),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Rule configuration
        sa.Column('risk_level', sa.String(20), default='medium', nullable=False),
        sa.Column('action_on_match', sa.String(20), default='blocked', nullable=False),

        # Detection patterns
        sa.Column('detection_patterns', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('detection_type', sa.String(20), default='keyword', nullable=False),

        # Applies to
        sa.Column('applies_to', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),

        # Active status
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index('ix_safety_rules_rule_key', 'safety_rules', ['rule_key'], unique=True)
    op.create_index('ix_safety_rules_is_active', 'safety_rules', ['is_active'])

    # Safety Incidents
    op.create_table(
        'safety_incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Incident details
        sa.Column('rule_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('safety_rules.id', ondelete='SET NULL'), nullable=True),
        sa.Column('rule_key', sa.String(100), nullable=False),

        # Risk assessment
        sa.Column('risk_level', sa.String(20), nullable=False),
        sa.Column('action_taken', sa.String(20), nullable=False),

        # Request context
        sa.Column('request_type', sa.String(50), nullable=False),
        sa.Column('request_hash', sa.String(64), nullable=False),

        # Additional context
        sa.Column('context', postgresql.JSONB(), nullable=True),

        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    op.create_index('ix_safety_incidents_tenant_id', 'safety_incidents', ['tenant_id'])
    op.create_index('ix_safety_incidents_user_id', 'safety_incidents', ['user_id'])
    op.create_index('ix_safety_incidents_created_at', 'safety_incidents', ['created_at'])

    # ==========================================================================
    # 5. Governance Audit Log Table (STEP 10 Requirement 6)
    # ==========================================================================

    op.create_table(
        'governance_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),

        # Actor
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_type', sa.String(20), nullable=False),
        sa.Column('actor_ip', sa.String(45), nullable=True),

        # Action
        sa.Column('action_type', sa.String(50), nullable=False),

        # Entity references
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('planning_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_script_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('persona_snapshot_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Version/hash for reproducibility
        sa.Column('spec_hash', sa.String(64), nullable=True),
        sa.Column('version', sa.String(50), nullable=True),

        # Additional details
        sa.Column('details', postgresql.JSONB(), nullable=True),

        # Result
        sa.Column('success', sa.Boolean(), default=True, nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Timestamp (immutable)
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    op.create_index('ix_governance_audit_tenant_id', 'governance_audit_logs', ['tenant_id'])
    op.create_index('ix_governance_audit_user_id', 'governance_audit_logs', ['user_id'])
    op.create_index('ix_governance_audit_action_type', 'governance_audit_logs', ['action_type'])
    op.create_index('ix_governance_audit_created_at', 'governance_audit_logs', ['created_at'])
    op.create_index('ix_governance_audit_project_id', 'governance_audit_logs', ['project_id'])
    op.create_index('ix_governance_audit_action_time', 'governance_audit_logs',
                    ['action_type', 'created_at'])
    op.create_index('ix_governance_audit_project_time', 'governance_audit_logs',
                    ['project_id', 'created_at'])
    op.create_index('ix_governance_audit_user_time', 'governance_audit_logs',
                    ['user_id', 'created_at'])

    # ==========================================================================
    # 6. Export Integrity Table (STEP 10 Requirement 7)
    # ==========================================================================

    op.create_table(
        'export_bundles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Export type
        sa.Column('export_type', sa.String(50), nullable=False),

        # Source references
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('planning_id', postgresql.UUID(as_uuid=True), nullable=True),

        # Artifact IDs
        sa.Column('artifact_ids', postgresql.JSONB(), nullable=False),

        # Integrity hashes
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('spec_hashes', postgresql.JSONB(), nullable=False),

        # File info
        sa.Column('file_format', sa.String(20), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=True),

        # Export metadata
        sa.Column('export_version', sa.String(20), nullable=False, server_default='1.0.0'),
        sa.Column('included_components', postgresql.ARRAY(sa.String(50)), nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('downloaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('download_count', sa.Integer(), default=0, nullable=False),
    )

    op.create_index('ix_export_bundles_tenant_id', 'export_bundles', ['tenant_id'])
    op.create_index('ix_export_bundles_user_id', 'export_bundles', ['user_id'])
    op.create_index('ix_export_bundles_content_hash', 'export_bundles', ['content_hash'])
    op.create_index('ix_export_bundles_created_at', 'export_bundles', ['created_at'])

    # ==========================================================================
    # 7. Seed Default Feature Flags
    # ==========================================================================

    # Insert default feature flags
    op.execute("""
        INSERT INTO feature_flags (id, flag_key, label, description, is_enabled_by_default, enabled_tiers, rollout_percentage, allow_tenant_override)
        VALUES
            (gen_random_uuid(), 'ensemble_large', 'Large Ensemble', 'Allow ensemble size > 5', false, ARRAY['professional', 'enterprise'], 100, true),
            (gen_random_uuid(), 'ensemble_unlimited', 'Unlimited Ensemble', 'Allow unlimited ensemble size', false, ARRAY['enterprise'], 100, true),
            (gen_random_uuid(), 'calibration_basic', 'Basic Calibration', 'Basic calibration features', true, ARRAY['starter', 'professional', 'enterprise'], 100, true),
            (gen_random_uuid(), 'calibration_advanced', 'Advanced Calibration', 'Advanced calibration features', false, ARRAY['professional', 'enterprise'], 100, true),
            (gen_random_uuid(), 'autotune', 'Autotune', 'Automatic parameter tuning', false, ARRAY['professional', 'enterprise'], 100, true),
            (gen_random_uuid(), 'replay_basic', 'Basic Replay', 'Basic replay functionality', true, ARRAY['free', 'starter', 'professional', 'enterprise'], 100, true),
            (gen_random_uuid(), 'replay_full_telemetry', 'Full Telemetry Replay', 'Replay with full telemetry', false, ARRAY['starter', 'professional', 'enterprise'], 100, true),
            (gen_random_uuid(), 'replay_export', 'Replay Export', 'Export replay data', false, ARRAY['professional', 'enterprise'], 100, true),
            (gen_random_uuid(), 'export_json', 'JSON Export', 'Export to JSON format', true, ARRAY['free', 'starter', 'professional', 'enterprise'], 100, true),
            (gen_random_uuid(), 'export_csv', 'CSV Export', 'Export to CSV format', false, ARRAY['starter', 'professional', 'enterprise'], 100, true),
            (gen_random_uuid(), 'export_full_bundle', 'Full Export Bundle', 'Complete export with all artifacts', false, ARRAY['professional', 'enterprise'], 100, true),
            (gen_random_uuid(), 'planning_basic', 'Basic Planning', 'Basic planning features', false, ARRAY['starter', 'professional', 'enterprise'], 100, true),
            (gen_random_uuid(), 'planning_deep', 'Deep Planning', 'Planning with depth > 3', false, ARRAY['professional', 'enterprise'], 100, true),
            (gen_random_uuid(), 'planning_unlimited', 'Unlimited Planning', 'Unlimited planning depth', false, ARRAY['enterprise'], 100, true),
            (gen_random_uuid(), 'safety_override', 'Safety Override', 'Override safety guardrails', false, ARRAY['enterprise'], 100, false)
        ON CONFLICT (flag_key) DO NOTHING
    """)


def downgrade():
    # ==========================================================================
    # Drop tables in reverse order
    # ==========================================================================

    # Export bundles
    op.drop_index('ix_export_bundles_created_at', table_name='export_bundles')
    op.drop_index('ix_export_bundles_content_hash', table_name='export_bundles')
    op.drop_index('ix_export_bundles_user_id', table_name='export_bundles')
    op.drop_index('ix_export_bundles_tenant_id', table_name='export_bundles')
    op.drop_table('export_bundles')

    # Governance audit logs
    op.drop_index('ix_governance_audit_user_time', table_name='governance_audit_logs')
    op.drop_index('ix_governance_audit_project_time', table_name='governance_audit_logs')
    op.drop_index('ix_governance_audit_action_time', table_name='governance_audit_logs')
    op.drop_index('ix_governance_audit_project_id', table_name='governance_audit_logs')
    op.drop_index('ix_governance_audit_created_at', table_name='governance_audit_logs')
    op.drop_index('ix_governance_audit_action_type', table_name='governance_audit_logs')
    op.drop_index('ix_governance_audit_user_id', table_name='governance_audit_logs')
    op.drop_index('ix_governance_audit_tenant_id', table_name='governance_audit_logs')
    op.drop_table('governance_audit_logs')

    # Safety incidents
    op.drop_index('ix_safety_incidents_created_at', table_name='safety_incidents')
    op.drop_index('ix_safety_incidents_user_id', table_name='safety_incidents')
    op.drop_index('ix_safety_incidents_tenant_id', table_name='safety_incidents')
    op.drop_table('safety_incidents')

    # Safety rules
    op.drop_index('ix_safety_rules_is_active', table_name='safety_rules')
    op.drop_index('ix_safety_rules_rule_key', table_name='safety_rules')
    op.drop_table('safety_rules')

    # Tenant feature overrides
    op.drop_index('ix_tenant_feature_flag_id', table_name='tenant_feature_overrides')
    op.drop_index('ix_tenant_feature_tenant_id', table_name='tenant_feature_overrides')
    op.drop_table('tenant_feature_overrides')

    # Feature flags
    op.drop_index('ix_feature_flags_flag_key', table_name='feature_flags')
    op.drop_table('feature_flags')

    # Quota violations
    op.drop_index('ix_quota_violation_created_at', table_name='quota_violations')
    op.drop_index('ix_quota_violation_user_id', table_name='quota_violations')
    op.drop_index('ix_quota_violation_tenant_id', table_name='quota_violations')
    op.drop_table('quota_violations')

    # Quota usage records
    op.drop_index('ix_quota_usage_tenant_period', table_name='quota_usage_records')
    op.drop_index('ix_quota_usage_tenant_id', table_name='quota_usage_records')
    op.drop_table('quota_usage_records')

    # Tenant quota configs
    op.drop_index('ix_tenant_quota_tenant_id', table_name='tenant_quota_configs')
    op.drop_table('tenant_quota_configs')

    # Project cost summaries
    op.drop_index('ix_project_cost_tenant_period', table_name='project_cost_summaries')
    op.drop_index('ix_project_cost_project_id', table_name='project_cost_summaries')
    op.drop_index('ix_project_cost_tenant_id', table_name='project_cost_summaries')
    op.drop_table('project_cost_summaries')

    # Planning cost records
    op.drop_index('ix_planning_cost_project_id', table_name='planning_cost_records')
    op.drop_index('ix_planning_cost_planning_id', table_name='planning_cost_records')
    op.drop_index('ix_planning_cost_tenant_id', table_name='planning_cost_records')
    op.drop_table('planning_cost_records')

    # Run cost records
    op.drop_index('ix_run_cost_node_id', table_name='run_cost_records')
    op.drop_index('ix_run_cost_project_id', table_name='run_cost_records')
    op.drop_index('ix_run_cost_run_id', table_name='run_cost_records')
    op.drop_index('ix_run_cost_tenant_id', table_name='run_cost_records')
    op.drop_table('run_cost_records')
