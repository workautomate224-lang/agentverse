"""
STEP 7: Reliability and Calibration Models

Database models for auditable reliability infrastructure:
- CalibrationResult: Historical replay with cutoff enforcement
- StabilityTest: Multi-seed variance testing
- DriftReport: Distribution drift detection
- ReliabilityScore: Rule-based confidence computation
- ParameterVersion: Auto-tuning with versioning and rollback

Reference: STEP 7 verification requirements
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# =============================================================================
# Enums
# =============================================================================

class CalibrationMethod(str, Enum):
    """Methods for calibration."""
    BAYESIAN = "bayesian"
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    ENSEMBLE = "ensemble"
    ADAPTIVE = "adaptive"


class DriftSeverity(str, Enum):
    """Severity levels for drift detection."""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ReliabilityLevel(str, Enum):
    """Reliability confidence levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class ParameterVersionStatus(str, Enum):
    """Status of parameter versions."""
    ACTIVE = "active"
    PROPOSED = "proposed"
    SUPERSEDED = "superseded"
    ROLLED_BACK = "rolled_back"


# =============================================================================
# CalibrationResult Model (STEP 7 Requirement 1)
# =============================================================================

class CalibrationResult(Base):
    """
    STEP 7: Calibration result with historical replay.

    Stores results from calibration runs including:
    - calibration_score (Brier or ECE)
    - comparison summary (predicted vs actual)
    - references to evidence used
    - calibration_timestamp
    - data_cutoff enforcement record
    """

    __tablename__ = "calibration_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Link to Node in universe map (STEP 7 artifact linking)
    node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="STEP 7: Node used for calibration baseline",
    )

    # Link to Run(s) used for calibration
    run_ids: Mapped[List[str]] = mapped_column(
        ARRAY(String(50)),
        nullable=False,
        server_default="{}",
        comment="STEP 7: Run IDs used in calibration",
    )

    # Calibration method
    method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=CalibrationMethod.BAYESIAN.value,
        comment="STEP 7: Calibration method used",
    )

    # Data cutoff enforcement (STEP 7 Requirement 1)
    data_cutoff: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="STEP 7: Strict data cutoff - no data after this time",
    )
    leakage_guard_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="STEP 7: Whether leakage guard was enforced",
    )
    blocked_access_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="STEP 7: Number of blocked future data accesses",
    )

    # Ground truth reference
    ground_truth_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ground_truths.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="STEP 7: Ground truth used for comparison",
    )

    # Calibration Score (STEP 7 Requirement 1)
    calibration_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="STEP 7: Calibration score (Brier or ECE)",
    )
    score_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="brier",
        comment="STEP 7: Type of calibration score (brier, ece, log_loss)",
    )

    # Comparison Summary (STEP 7 Requirement 1)
    comparison_summary: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 7: Predicted vs Actual comparison",
    )
    # Structure: {
    #   "predicted": {"outcome_a": 0.45, "outcome_b": 0.35},
    #   "actual": {"outcome_a": 0.48, "outcome_b": 0.32},
    #   "differences": {"outcome_a": -0.03, "outcome_b": 0.03},
    #   "accuracy_metrics": {"mae": 0.03, "rmse": 0.04}
    # }

    # Evidence References (STEP 7 Requirement 1)
    evidence_used: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="STEP 7: References to evidence used",
    )
    # Structure: [
    #   {"type": "data_source", "id": "uuid", "name": "Census 2020", "cutoff_compliant": true},
    #   {"type": "persona_dataset", "id": "uuid", "record_count": 5000},
    #   {"type": "historical_event", "id": "uuid", "date": "2024-01-01"}
    # ]

    # Calibration Timestamp (STEP 7 Requirement 1)
    calibration_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="STEP 7: When calibration was performed",
    )

    # Additional metrics
    additional_metrics: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 7: Additional calibration metrics",
    )
    # Structure: {
    #   "kl_divergence": 0.05,
    #   "correlation": 0.92,
    #   "coverage_probability": 0.95,
    #   "ci_width": 0.08
    # }

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<CalibrationResult score={self.calibration_score:.4f} ({self.score_type})>"


# =============================================================================
# StabilityTest Model (STEP 7 Requirement 2)
# =============================================================================

class StabilityTest(Base):
    """
    STEP 7: Stability test with multi-seed variance.

    Requirements:
    - Minimum 2 runs per stability test (MVP)
    - Outcome variance must be computed and stored
    """

    __tablename__ = "stability_tests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Link to Node being tested
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="STEP 7: Node being stability tested",
    )

    # Link to RunConfig being tested
    run_config_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("run_configs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="STEP 7: RunConfig used for stability test",
    )

    # Seeds used (STEP 7 Requirement 2: minimum 2)
    seeds_tested: Mapped[List[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        comment="STEP 7: Seeds used for stability runs",
    )
    run_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="STEP 7: Number of runs executed (minimum 2)",
    )

    # Run references
    run_ids: Mapped[List[str]] = mapped_column(
        ARRAY(String(50)),
        nullable=False,
        server_default="{}",
        comment="STEP 7: Run IDs from stability test",
    )

    # Outcome Variance (STEP 7 Requirement 2)
    outcome_variance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="STEP 7: Computed outcome variance across seeds",
    )
    outcome_std_dev: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="STEP 7: Standard deviation of outcomes",
    )

    # Per-outcome breakdown
    variance_by_outcome: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 7: Variance breakdown by outcome variable",
    )
    # Structure: {
    #   "primary_outcome": {"mean": 0.45, "std": 0.02, "variance": 0.0004, "cv": 0.044},
    #   "secondary_outcome": {"mean": 0.30, "std": 0.03, "variance": 0.0009, "cv": 0.10}
    # }

    # Outcomes by seed
    outcomes_by_seed: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 7: Raw outcomes for each seed",
    )
    # Structure: {
    #   "42": {"primary_outcome": 0.44, "secondary_outcome": 0.29},
    #   "123": {"primary_outcome": 0.46, "secondary_outcome": 0.31}
    # }

    # Stability assessment
    is_stable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="STEP 7: Whether variance is within acceptable threshold",
    )
    stability_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.1,
        comment="STEP 7: Threshold for stability determination",
    )
    stability_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="STEP 7: Stability score (0-1, higher is more stable)",
    )

    # Most/least stable outcomes
    most_stable_outcome: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="STEP 7: Outcome with lowest variance",
    )
    least_stable_outcome: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="STEP 7: Outcome with highest variance",
    )

    # Timestamps
    tested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<StabilityTest runs={self.run_count} variance={self.outcome_variance:.4f}>"


# =============================================================================
# DriftReport Model (STEP 7 Requirement 3)
# =============================================================================

class DriftReport(Base):
    """
    STEP 7: Drift detection report.

    Detects drift across:
    - Persona distributions
    - Data source statistics
    - Model or parameter versions

    Drift MUST affect reliability scoring.
    """

    __tablename__ = "drift_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Link to Node
    node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Drift type
    drift_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="STEP 7: Type of drift (persona, data_source, model_params)",
    )

    # Reference and comparison periods
    reference_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="STEP 7: Reference period start",
    )
    reference_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="STEP 7: Reference period end",
    )
    comparison_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="STEP 7: Comparison period start",
    )
    comparison_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="STEP 7: Comparison period end",
    )

    # Drift Detection Results
    drift_detected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="STEP 7: Whether significant drift was detected",
    )
    drift_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="STEP 7: Overall drift score (0-1)",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DriftSeverity.NONE.value,
        comment="STEP 7: Drift severity level",
    )

    # Statistical tests
    statistical_tests: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 7: Statistical test results",
    )
    # Structure: {
    #   "ks_statistic": 0.15,
    #   "ks_pvalue": 0.03,
    #   "js_divergence": 0.08,
    #   "wasserstein_distance": 0.12
    # }

    # Features that shifted
    features_shifted: Mapped[List[str]] = mapped_column(
        ARRAY(String(100)),
        nullable=False,
        server_default="{}",
        comment="STEP 7: Variables that showed significant shift",
    )

    # Shift magnitudes by feature
    shift_magnitudes: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 7: Shift magnitude for each feature",
    )
    # Structure: {
    #   "age_distribution": {"shift": 0.08, "direction": "younger"},
    #   "income_distribution": {"shift": 0.15, "direction": "higher"}
    # }

    # Reference and comparison distributions
    reference_distribution: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 7: Reference period distribution",
    )
    comparison_distribution: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 7: Comparison period distribution",
    )

    # Recommendations
    recommendations: Mapped[List[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="{}",
        comment="STEP 7: Recommended actions based on drift",
    )

    # Impact on reliability (STEP 7: drift MUST affect reliability)
    reliability_impact: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="STEP 7: How much this drift affects reliability score",
    )

    # Timestamps
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<DriftReport type={self.drift_type} severity={self.severity}>"


# =============================================================================
# ReliabilityScore Model (STEP 7 Requirement 4)
# =============================================================================

class ReliabilityScore(Base):
    """
    STEP 7: Reliability/confidence score.

    Must be computed from:
    - Calibration results
    - Stability results
    - Data gaps
    - Drift signals

    Score MUST be rule-based or explicitly defined.
    A constant or unexplained number is a FAIL.
    """

    __tablename__ = "reliability_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Link to Run (artifact linking)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
        comment="STEP 7: Run this reliability score applies to",
    )

    # Link to Node
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="STEP 7: Node this reliability score applies to",
    )

    # Component scores (STEP 7: explicit rule-based)
    calibration_component: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="STEP 7: Calibration contribution to score (0-1)",
    )
    stability_component: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="STEP 7: Stability contribution to score (0-1)",
    )
    data_gap_component: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="STEP 7: Data gap penalty (0-1, 1=no gaps)",
    )
    drift_component: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="STEP 7: Drift penalty (0-1, 1=no drift)",
    )

    # Component references
    calibration_result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calibration_results.id", ondelete="SET NULL"),
        nullable=True,
        comment="STEP 7: Calibration result used",
    )
    stability_test_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stability_tests.id", ondelete="SET NULL"),
        nullable=True,
        comment="STEP 7: Stability test used",
    )
    drift_report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drift_reports.id", ondelete="SET NULL"),
        nullable=True,
        comment="STEP 7: Drift report used",
    )

    # Weights (STEP 7: explicit, non-black-box)
    weights: Mapped[Dict[str, float]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 7: Weights for each component",
    )
    # Structure: {
    #   "calibration": 0.30,
    #   "stability": 0.25,
    #   "data_gap": 0.25,
    #   "drift": 0.20
    # }

    # Scoring formula (STEP 7: explicit, auditable)
    scoring_formula: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="STEP 7: Explicit formula for score computation",
    )
    # Example: "score = w_cal * calibration + w_stab * stability + w_gap * (1 - gap_penalty) + w_drift * (1 - drift_penalty)"

    # Final Score (STEP 7: NOT a constant)
    reliability_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="STEP 7: Final reliability score (0-1)",
    )
    reliability_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReliabilityLevel.MEDIUM.value,
        comment="STEP 7: Reliability level classification",
    )

    # Data gaps detail
    data_gaps: Mapped[List[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="{}",
        comment="STEP 7: List of identified data gaps",
    )
    data_gap_severity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="STEP 7: Severity of data gaps (0-1)",
    )

    # Computation trace (STEP 7: auditable)
    computation_trace: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 7: Full computation trace for audit",
    )
    # Structure: {
    #   "step_1": {"name": "calibration_lookup", "value": 0.85},
    #   "step_2": {"name": "stability_lookup", "value": 0.92},
    #   "step_3": {"name": "gap_penalty", "value": 0.05},
    #   "step_4": {"name": "drift_penalty", "value": 0.10},
    #   "step_5": {"name": "weighted_sum", "intermediate": 0.78},
    #   "final": 0.78
    # }

    # Timestamps
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ReliabilityScore {self.reliability_score:.2f} ({self.reliability_level})>"


# =============================================================================
# ParameterVersion Model (STEP 7 Requirement 5)
# =============================================================================

class ParameterVersion(Base):
    """
    STEP 7: Parameter versioning for auto-tuning.

    Requirements:
    - Run calibration to evaluate changes
    - Store each parameter set with versioning
    - Support rollback
    - Never silently modify baseline outcomes
    """

    __tablename__ = "parameter_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Version identification
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="STEP 7: Monotonically increasing version number",
    )
    version_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        comment="STEP 7: SHA-256 hash of parameter set",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ParameterVersionStatus.PROPOSED.value,
        index=True,
        comment="STEP 7: Version status",
    )

    # Parameters (STEP 7: stored with versioning)
    parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="STEP 7: Complete parameter set",
    )
    # Structure: {
    #   "loss_aversion": 2.25,
    #   "probability_weight": 0.61,
    #   "status_quo_bias": 0.15,
    #   "social_influence": 0.30
    # }

    # Parameter bounds
    parameter_bounds: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 7: Bounds for each parameter",
    )
    # Structure: {
    #   "loss_aversion": {"min": 1.0, "max": 3.0},
    #   "probability_weight": {"min": 0.4, "max": 0.8}
    # }

    # Calibration evaluation (STEP 7: must run calibration)
    calibration_result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calibration_results.id", ondelete="SET NULL"),
        nullable=True,
        comment="STEP 7: Calibration result for this version",
    )
    calibration_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="STEP 7: Calibration score achieved",
    )

    # Previous version (for rollback)
    previous_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parameter_versions.id", ondelete="SET NULL"),
        nullable=True,
        comment="STEP 7: Previous version for rollback chain",
    )

    # Change description
    change_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="STEP 7: Description of changes from previous version",
    )
    change_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="STEP 7: Reason for parameter change",
    )

    # Auto-tune metadata
    auto_tuned: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="STEP 7: Whether this was auto-tuned",
    )
    auto_tune_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="STEP 7: Auto-tune method used",
    )

    # Approval (STEP 7: never silently modify)
    requires_approval: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="STEP 7: Whether this version requires approval",
    )
    approved_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="STEP 7: Who approved this version",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="STEP 7: When this version was approved",
    )

    # Rollback info (STEP 7: support rollback)
    rolled_back_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parameter_versions.id", ondelete="SET NULL"),
        nullable=True,
        comment="STEP 7: If rolled back, which version was restored",
    )
    rollback_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="STEP 7: Reason for rollback",
    )
    rollback_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="STEP 7: When rollback occurred",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="STEP 7: When this version became active",
    )

    def __repr__(self) -> str:
        return f"<ParameterVersion v{self.version_number} ({self.status})>"


# =============================================================================
# Reliability Score Computation (STEP 7 Requirement 4)
# =============================================================================

class ReliabilityScoreComputer:
    """
    STEP 7: Rule-based reliability score computation.

    This class provides the EXPLICIT, NON-BLACK-BOX scoring formula.
    """

    DEFAULT_WEIGHTS = {
        "calibration": 0.30,
        "stability": 0.25,
        "data_gap": 0.25,
        "drift": 0.20,
    }

    FORMULA = (
        "reliability_score = "
        "w_calibration * calibration_component + "
        "w_stability * stability_component + "
        "w_data_gap * (1 - data_gap_penalty) + "
        "w_drift * (1 - drift_penalty)"
    )

    @staticmethod
    def compute(
        calibration_score: Optional[float] = None,
        stability_score: Optional[float] = None,
        data_gap_penalty: float = 0.0,
        drift_penalty: float = 0.0,
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Compute reliability score using explicit formula.

        STEP 7: This is NOT a black box. The formula is:
        score = w_cal * calibration + w_stab * stability + w_gap * (1 - gap) + w_drift * (1 - drift)

        Args:
            calibration_score: Score from calibration (0-1, 1=perfectly calibrated)
            stability_score: Score from stability test (0-1, 1=perfectly stable)
            data_gap_penalty: Penalty for missing data (0-1, 0=no gaps)
            drift_penalty: Penalty for detected drift (0-1, 0=no drift)
            weights: Custom weights for each component

        Returns:
            Dict with score, level, components, and computation trace
        """
        w = weights or ReliabilityScoreComputer.DEFAULT_WEIGHTS

        # Normalize weights
        total_weight = sum(w.values())
        w = {k: v / total_weight for k, v in w.items()}

        # Handle missing components with neutral values
        cal = calibration_score if calibration_score is not None else 0.5
        stab = stability_score if stability_score is not None else 0.5
        gap_component = 1.0 - min(1.0, max(0.0, data_gap_penalty))
        drift_component = 1.0 - min(1.0, max(0.0, drift_penalty))

        # Computation trace (STEP 7: auditable)
        trace = {
            "step_1_calibration": {
                "raw_value": calibration_score,
                "used_value": cal,
                "weight": w["calibration"],
                "contribution": w["calibration"] * cal,
            },
            "step_2_stability": {
                "raw_value": stability_score,
                "used_value": stab,
                "weight": w["stability"],
                "contribution": w["stability"] * stab,
            },
            "step_3_data_gap": {
                "penalty": data_gap_penalty,
                "component": gap_component,
                "weight": w["data_gap"],
                "contribution": w["data_gap"] * gap_component,
            },
            "step_4_drift": {
                "penalty": drift_penalty,
                "component": drift_component,
                "weight": w["drift"],
                "contribution": w["drift"] * drift_component,
            },
        }

        # Apply formula (STEP 7: explicit)
        score = (
            w["calibration"] * cal
            + w["stability"] * stab
            + w["data_gap"] * gap_component
            + w["drift"] * drift_component
        )

        # Clamp to [0, 1]
        score = min(1.0, max(0.0, score))

        trace["step_5_weighted_sum"] = score
        trace["final_score"] = score

        # Determine level
        if score >= 0.8:
            level = ReliabilityLevel.HIGH.value
        elif score >= 0.6:
            level = ReliabilityLevel.MEDIUM.value
        elif score >= 0.4:
            level = ReliabilityLevel.LOW.value
        else:
            level = ReliabilityLevel.VERY_LOW.value

        return {
            "reliability_score": score,
            "reliability_level": level,
            "calibration_component": cal,
            "stability_component": stab,
            "data_gap_component": gap_component,
            "drift_component": drift_component,
            "weights": w,
            "scoring_formula": ReliabilityScoreComputer.FORMULA,
            "computation_trace": trace,
        }
