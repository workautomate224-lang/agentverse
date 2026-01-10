"""STEP 7: Reliability and Calibration Models

Revision ID: step7_reliability_001
Revises: step6_planning_001
Create Date: 2026-01-10

This migration adds infrastructure required for STEP 7 verification:
1. Create calibration_results table for historical replay with cutoff
2. Create stability_tests table for multi-seed variance testing
3. Create drift_reports table for distribution drift detection
4. Create reliability_scores table for rule-based confidence computation
5. Create parameter_versions table for auto-tuning with versioning/rollback

STEP 7 Goal: Implement Calibration and Reliability so predictions are
auditable, self-aware, and trustworthy.

Key Requirements:
- Calibration: Historical replay with strict data_cutoff enforcement
- Stability: Minimum 2 runs per test, outcome variance stored
- Drift: Detection across personas, data sources, model params; affects reliability
- Reliability: Rule-based score from calibration + stability + data gaps + drift
- Auto-Tuning: Parameter versioning with rollback support
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'step7_reliability_001'
down_revision = 'step6_planning_001'
branch_labels = None
depends_on = None


def upgrade():
    # ==========================================================================
    # 1. Create calibration_results table (STEP 7 Requirement 1)
    # ==========================================================================
    op.create_table(
        'calibration_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('project_specs.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('node_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('nodes.id', ondelete='SET NULL'),
                  nullable=True, index=True,
                  comment='STEP 7: Node used for calibration baseline'),
        sa.Column('run_ids', postgresql.ARRAY(sa.String(50)),
                  nullable=False, server_default='{}',
                  comment='STEP 7: Run IDs used in calibration'),
        sa.Column('method', sa.String(50), nullable=False, default='bayesian',
                  comment='STEP 7: Calibration method used'),

        # Data cutoff enforcement (STEP 7 Requirement 1)
        sa.Column('data_cutoff', sa.DateTime(timezone=True), nullable=False,
                  comment='STEP 7: Strict data cutoff - no data after this time'),
        sa.Column('leakage_guard_enabled', sa.Boolean, nullable=False, default=True,
                  comment='STEP 7: Whether leakage guard was enforced'),
        sa.Column('blocked_access_count', sa.Integer, nullable=False, default=0,
                  comment='STEP 7: Number of blocked future data accesses'),

        # Ground truth reference
        sa.Column('ground_truth_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('ground_truths.id', ondelete='SET NULL'),
                  nullable=True, index=True,
                  comment='STEP 7: Ground truth used for comparison'),

        # Calibration Score (STEP 7 Requirement 1)
        sa.Column('calibration_score', sa.Float, nullable=False,
                  comment='STEP 7: Calibration score (Brier or ECE)'),
        sa.Column('score_type', sa.String(50), nullable=False, default='brier',
                  comment='STEP 7: Type of calibration score (brier, ece, log_loss)'),

        # Comparison Summary (STEP 7 Requirement 1)
        sa.Column('comparison_summary', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 7: Predicted vs Actual comparison'),

        # Evidence References (STEP 7 Requirement 1)
        sa.Column('evidence_used', postgresql.JSONB, nullable=False, default=list,
                  comment='STEP 7: References to evidence used'),

        # Calibration Timestamp (STEP 7 Requirement 1)
        sa.Column('calibration_timestamp', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False,
                  comment='STEP 7: When calibration was performed'),

        # Additional metrics
        sa.Column('additional_metrics', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 7: Additional calibration metrics'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_calibration_results_project_time
        ON calibration_results (project_id, calibration_timestamp)
    """)

    # ==========================================================================
    # 2. Create stability_tests table (STEP 7 Requirement 2)
    # ==========================================================================
    op.create_table(
        'stability_tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('project_specs.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('node_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('nodes.id', ondelete='CASCADE'),
                  nullable=False, index=True,
                  comment='STEP 7: Node being stability tested'),
        sa.Column('run_config_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('run_configs.id', ondelete='SET NULL'),
                  nullable=True, index=True,
                  comment='STEP 7: RunConfig used for stability test'),

        # Seeds used (STEP 7 Requirement 2: minimum 2)
        sa.Column('seeds_tested', postgresql.ARRAY(sa.Integer), nullable=False,
                  comment='STEP 7: Seeds used for stability runs'),
        sa.Column('run_count', sa.Integer, nullable=False,
                  comment='STEP 7: Number of runs executed (minimum 2)'),

        # Run references
        sa.Column('run_ids', postgresql.ARRAY(sa.String(50)),
                  nullable=False, server_default='{}',
                  comment='STEP 7: Run IDs from stability test'),

        # Outcome Variance (STEP 7 Requirement 2)
        sa.Column('outcome_variance', sa.Float, nullable=False,
                  comment='STEP 7: Computed outcome variance across seeds'),
        sa.Column('outcome_std_dev', sa.Float, nullable=False,
                  comment='STEP 7: Standard deviation of outcomes'),

        # Per-outcome breakdown
        sa.Column('variance_by_outcome', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 7: Variance breakdown by outcome variable'),
        sa.Column('outcomes_by_seed', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 7: Raw outcomes for each seed'),

        # Stability assessment
        sa.Column('is_stable', sa.Boolean, nullable=False,
                  comment='STEP 7: Whether variance is within acceptable threshold'),
        sa.Column('stability_threshold', sa.Float, nullable=False, default=0.1,
                  comment='STEP 7: Threshold for stability determination'),
        sa.Column('stability_score', sa.Float, nullable=False,
                  comment='STEP 7: Stability score (0-1, higher is more stable)'),

        # Most/least stable outcomes
        sa.Column('most_stable_outcome', sa.String(100), nullable=True,
                  comment='STEP 7: Outcome with lowest variance'),
        sa.Column('least_stable_outcome', sa.String(100), nullable=True,
                  comment='STEP 7: Outcome with highest variance'),

        # Timestamps
        sa.Column('tested_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_stability_tests_node
        ON stability_tests (node_id, tested_at)
    """)

    # ==========================================================================
    # 3. Create drift_reports table (STEP 7 Requirement 3)
    # ==========================================================================
    op.create_table(
        'drift_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('project_specs.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('node_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('nodes.id', ondelete='SET NULL'),
                  nullable=True, index=True),

        # Drift type
        sa.Column('drift_type', sa.String(50), nullable=False,
                  comment='STEP 7: Type of drift (persona, data_source, model_params)'),

        # Reference and comparison periods
        sa.Column('reference_period_start', sa.DateTime(timezone=True), nullable=False,
                  comment='STEP 7: Reference period start'),
        sa.Column('reference_period_end', sa.DateTime(timezone=True), nullable=False,
                  comment='STEP 7: Reference period end'),
        sa.Column('comparison_period_start', sa.DateTime(timezone=True), nullable=False,
                  comment='STEP 7: Comparison period start'),
        sa.Column('comparison_period_end', sa.DateTime(timezone=True), nullable=False,
                  comment='STEP 7: Comparison period end'),

        # Drift Detection Results
        sa.Column('drift_detected', sa.Boolean, nullable=False,
                  comment='STEP 7: Whether significant drift was detected'),
        sa.Column('drift_score', sa.Float, nullable=False,
                  comment='STEP 7: Overall drift score (0-1)'),
        sa.Column('severity', sa.String(20), nullable=False, default='none',
                  comment='STEP 7: Drift severity level'),

        # Statistical tests
        sa.Column('statistical_tests', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 7: Statistical test results'),

        # Features that shifted
        sa.Column('features_shifted', postgresql.ARRAY(sa.String(100)),
                  nullable=False, server_default='{}',
                  comment='STEP 7: Variables that showed significant shift'),

        # Shift magnitudes by feature
        sa.Column('shift_magnitudes', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 7: Shift magnitude for each feature'),

        # Reference and comparison distributions
        sa.Column('reference_distribution', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 7: Reference period distribution'),
        sa.Column('comparison_distribution', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 7: Comparison period distribution'),

        # Recommendations
        sa.Column('recommendations', postgresql.ARRAY(sa.Text),
                  nullable=False, server_default='{}',
                  comment='STEP 7: Recommended actions based on drift'),

        # Impact on reliability (STEP 7: drift MUST affect reliability)
        sa.Column('reliability_impact', sa.Float, nullable=False,
                  comment='STEP 7: How much this drift affects reliability score'),

        # Timestamps
        sa.Column('detected_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_drift_reports_project_type
        ON drift_reports (project_id, drift_type, detected_at)
    """)

    # ==========================================================================
    # 4. Create parameter_versions table (STEP 7 Requirement 5)
    # Must be created before reliability_scores due to FK reference
    # ==========================================================================
    op.create_table(
        'parameter_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('project_specs.id', ondelete='CASCADE'),
                  nullable=False, index=True),

        # Version identification
        sa.Column('version_number', sa.Integer, nullable=False,
                  comment='STEP 7: Monotonically increasing version number'),
        sa.Column('version_hash', sa.String(64), nullable=False, unique=True,
                  comment='STEP 7: SHA-256 hash of parameter set'),

        # Status
        sa.Column('status', sa.String(20), nullable=False, default='proposed', index=True,
                  comment='STEP 7: Version status'),

        # Parameters (STEP 7: stored with versioning)
        sa.Column('parameters', postgresql.JSONB, nullable=False,
                  comment='STEP 7: Complete parameter set'),

        # Parameter bounds
        sa.Column('parameter_bounds', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 7: Bounds for each parameter'),

        # Calibration evaluation - FK added later to avoid circular dependency
        sa.Column('calibration_result_id', postgresql.UUID(as_uuid=True),
                  nullable=True,
                  comment='STEP 7: Calibration result for this version'),
        sa.Column('calibration_score', sa.Float, nullable=True,
                  comment='STEP 7: Calibration score achieved'),

        # Previous version (for rollback) - self-referential FK added later
        sa.Column('previous_version_id', postgresql.UUID(as_uuid=True),
                  nullable=True,
                  comment='STEP 7: Previous version for rollback chain'),

        # Change description
        sa.Column('change_description', sa.Text, nullable=True,
                  comment='STEP 7: Description of changes from previous version'),
        sa.Column('change_reason', sa.Text, nullable=True,
                  comment='STEP 7: Reason for parameter change'),

        # Auto-tune metadata
        sa.Column('auto_tuned', sa.Boolean, nullable=False, default=False,
                  comment='STEP 7: Whether this was auto-tuned'),
        sa.Column('auto_tune_method', sa.String(50), nullable=True,
                  comment='STEP 7: Auto-tune method used'),

        # Approval (STEP 7: never silently modify)
        sa.Column('requires_approval', sa.Boolean, nullable=False, default=True,
                  comment='STEP 7: Whether this version requires approval'),
        sa.Column('approved_by', sa.String(100), nullable=True,
                  comment='STEP 7: Who approved this version'),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True,
                  comment='STEP 7: When this version was approved'),

        # Rollback info (STEP 7: support rollback)
        sa.Column('rolled_back_to_id', postgresql.UUID(as_uuid=True),
                  nullable=True,
                  comment='STEP 7: If rolled back, which version was restored'),
        sa.Column('rollback_reason', sa.Text, nullable=True,
                  comment='STEP 7: Reason for rollback'),
        sa.Column('rollback_at', sa.DateTime(timezone=True), nullable=True,
                  comment='STEP 7: When rollback occurred'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True,
                  comment='STEP 7: When this version became active'),
    )

    # Add self-referential FKs for parameter_versions
    op.execute("""
        ALTER TABLE parameter_versions
        ADD CONSTRAINT fk_parameter_versions_previous
        FOREIGN KEY (previous_version_id)
        REFERENCES parameter_versions(id)
        ON DELETE SET NULL
    """)

    op.execute("""
        ALTER TABLE parameter_versions
        ADD CONSTRAINT fk_parameter_versions_rollback
        FOREIGN KEY (rolled_back_to_id)
        REFERENCES parameter_versions(id)
        ON DELETE SET NULL
    """)

    # Add FK to calibration_results
    op.execute("""
        ALTER TABLE parameter_versions
        ADD CONSTRAINT fk_parameter_versions_calibration
        FOREIGN KEY (calibration_result_id)
        REFERENCES calibration_results(id)
        ON DELETE SET NULL
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_parameter_versions_project_status
        ON parameter_versions (project_id, status)
    """)

    # ==========================================================================
    # 5. Create reliability_scores table (STEP 7 Requirement 4)
    # ==========================================================================
    op.create_table(
        'reliability_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('project_specs.id', ondelete='CASCADE'),
                  nullable=False, index=True),

        # Link to Run (artifact linking)
        sa.Column('run_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('runs.id', ondelete='CASCADE'),
                  nullable=False, index=True, unique=True,
                  comment='STEP 7: Run this reliability score applies to'),

        # Link to Node
        sa.Column('node_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('nodes.id', ondelete='CASCADE'),
                  nullable=False, index=True,
                  comment='STEP 7: Node this reliability score applies to'),

        # Component scores (STEP 7: explicit rule-based)
        sa.Column('calibration_component', sa.Float, nullable=True,
                  comment='STEP 7: Calibration contribution to score (0-1)'),
        sa.Column('stability_component', sa.Float, nullable=True,
                  comment='STEP 7: Stability contribution to score (0-1)'),
        sa.Column('data_gap_component', sa.Float, nullable=True,
                  comment='STEP 7: Data gap penalty (0-1, 1=no gaps)'),
        sa.Column('drift_component', sa.Float, nullable=True,
                  comment='STEP 7: Drift penalty (0-1, 1=no drift)'),

        # Component references
        sa.Column('calibration_result_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('calibration_results.id', ondelete='SET NULL'),
                  nullable=True,
                  comment='STEP 7: Calibration result used'),
        sa.Column('stability_test_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('stability_tests.id', ondelete='SET NULL'),
                  nullable=True,
                  comment='STEP 7: Stability test used'),
        sa.Column('drift_report_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('drift_reports.id', ondelete='SET NULL'),
                  nullable=True,
                  comment='STEP 7: Drift report used'),

        # Weights (STEP 7: explicit, non-black-box)
        sa.Column('weights', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 7: Weights for each component'),

        # Scoring formula (STEP 7: explicit, auditable)
        sa.Column('scoring_formula', sa.Text, nullable=False,
                  comment='STEP 7: Explicit formula for score computation'),

        # Final Score (STEP 7: NOT a constant)
        sa.Column('reliability_score', sa.Float, nullable=False,
                  comment='STEP 7: Final reliability score (0-1)'),
        sa.Column('reliability_level', sa.String(20), nullable=False, default='medium',
                  comment='STEP 7: Reliability level classification'),

        # Data gaps detail
        sa.Column('data_gaps', postgresql.ARRAY(sa.Text),
                  nullable=False, server_default='{}',
                  comment='STEP 7: List of identified data gaps'),
        sa.Column('data_gap_severity', sa.Float, nullable=False, default=0.0,
                  comment='STEP 7: Severity of data gaps (0-1)'),

        # Computation trace (STEP 7: auditable)
        sa.Column('computation_trace', postgresql.JSONB, nullable=False, default=dict,
                  comment='STEP 7: Full computation trace for audit'),

        # Timestamps
        sa.Column('computed_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_reliability_scores_node
        ON reliability_scores (node_id, computed_at)
    """)


def downgrade():
    # Drop tables in reverse order (respecting FK constraints)
    op.execute("DROP INDEX IF EXISTS ix_reliability_scores_node")
    op.execute("DROP TABLE IF EXISTS reliability_scores CASCADE")

    op.execute("DROP INDEX IF EXISTS ix_parameter_versions_project_status")
    op.execute("DROP TABLE IF EXISTS parameter_versions CASCADE")

    op.execute("DROP INDEX IF EXISTS ix_drift_reports_project_type")
    op.execute("DROP TABLE IF EXISTS drift_reports CASCADE")

    op.execute("DROP INDEX IF EXISTS ix_stability_tests_node")
    op.execute("DROP TABLE IF EXISTS stability_tests CASCADE")

    op.execute("DROP INDEX IF EXISTS ix_calibration_results_project_time")
    op.execute("DROP TABLE IF EXISTS calibration_results CASCADE")
