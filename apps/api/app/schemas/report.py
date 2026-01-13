"""
Report Schemas - PHASE 7: Reports (Prediction + Reliability Output Page)

Pydantic v2 schemas for the aggregated report endpoint that merges:
- Prediction (empirical distribution + target probability)
- Reliability (sensitivity, stability CI, drift status)
- Calibration summary (Brier/ECE + optional curve)
- Provenance (manifest hash, filters, run counts)

Reference: Phase 7 specification
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class ReportOperator(str, Enum):
    """Comparison operators for target probability."""
    GE = "ge"
    GT = "gt"
    LE = "le"
    LT = "lt"
    EQ = "eq"


class DriftStatus(str, Enum):
    """Drift detection status."""
    STABLE = "stable"
    WARNING = "warning"
    DRIFTING = "drifting"


# =============================================================================
# Target Schema
# =============================================================================

class TargetSpec(BaseModel):
    """Target specification for report computation."""
    op: ReportOperator = Field(..., description="Comparison operator")
    threshold: float = Field(..., description="Threshold value")


# =============================================================================
# Provenance Schema
# =============================================================================

class ReportFilters(BaseModel):
    """Filters applied to the report computation."""
    manifest_hash: Optional[str] = Field(None, description="Manifest hash filter if applied")
    window_days: int = Field(default=30, description="Time window in days")
    min_runs: int = Field(default=3, description="Minimum runs required")


class ReportProvenance(BaseModel):
    """Provenance information for auditability."""
    manifest_hash: Optional[str] = Field(None, description="Manifest hash used (if filtered)")
    filters: ReportFilters = Field(..., description="Filters applied")
    n_runs: int = Field(..., ge=0, description="Number of runs used in computation")
    updated_at: datetime = Field(..., description="Timestamp of most recent run in dataset")


# =============================================================================
# Prediction Schema
# =============================================================================

class DistributionData(BaseModel):
    """Histogram data for prediction distribution."""
    bins: List[float] = Field(default_factory=list, description="Bin edges (N+1 values for N bins)")
    counts: List[int] = Field(default_factory=list, description="Counts per bin (N values)")
    min: float = Field(default=0.0, description="Minimum value in data")
    max: float = Field(default=0.0, description="Maximum value in data")


class PredictionResult(BaseModel):
    """Prediction section of the report."""
    distribution: DistributionData = Field(..., description="Empirical distribution histogram")
    target_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="P(metric op threshold) - probability of meeting target"
    )


# =============================================================================
# Calibration Schema
# =============================================================================

class CalibrationCurve(BaseModel):
    """Reliability diagram curve data."""
    p_pred: List[float] = Field(default_factory=list, description="Predicted probabilities (bin centers)")
    p_true: List[float] = Field(default_factory=list, description="Observed frequencies")
    counts: List[int] = Field(default_factory=list, description="Sample counts per bin")


class CalibrationResult(BaseModel):
    """Calibration section of the report."""
    available: bool = Field(..., description="Whether calibration data is available")
    latest_job_id: Optional[str] = Field(None, description="UUID of latest calibration job")
    brier: Optional[float] = Field(None, ge=0.0, description="Brier score (lower is better)")
    ece: Optional[float] = Field(None, ge=0.0, description="Expected Calibration Error")
    curve: Optional[CalibrationCurve] = Field(None, description="Calibration curve for visualization")


# =============================================================================
# Reliability Schema
# =============================================================================

class SensitivityData(BaseModel):
    """Sensitivity analysis data: P(metric op threshold) across threshold grid."""
    thresholds: List[float] = Field(default_factory=list, description="Threshold grid values")
    probabilities: List[float] = Field(default_factory=list, description="Probabilities at each threshold")


class StabilityData(BaseModel):
    """Stability analysis via bootstrap resampling."""
    mean: float = Field(..., description="Bootstrap mean estimate")
    ci_low: float = Field(..., description="95% CI lower bound")
    ci_high: float = Field(..., description="95% CI upper bound")
    bootstrap_samples: int = Field(default=200, description="Number of bootstrap samples used")


class DriftData(BaseModel):
    """Drift detection results."""
    status: DriftStatus = Field(..., description="Drift status: stable, warning, or drifting")
    ks: Optional[float] = Field(None, ge=0.0, description="Kolmogorov-Smirnov statistic")
    psi: Optional[float] = Field(None, description="Population Stability Index")


class ReliabilityResult(BaseModel):
    """Reliability section of the report."""
    sensitivity: SensitivityData = Field(..., description="Sensitivity analysis")
    stability: StabilityData = Field(..., description="Stability analysis with CI")
    drift: DriftData = Field(..., description="Drift detection results")


# =============================================================================
# Main Report Response Schema
# =============================================================================

class ReportResponse(BaseModel):
    """
    Complete report response - aggregates all prediction and reliability data.

    Returns HTTP 200 with insufficient_data=true when data is insufficient,
    never returns HTTP 500 for missing data.
    """
    # Identifiers
    node_id: str = Field(..., description="UUID of the node")
    metric_key: str = Field(..., description="Metric key analyzed")

    # Target specification
    target: TargetSpec = Field(..., description="Target specification (op + threshold)")

    # Provenance (always present)
    provenance: ReportProvenance = Field(..., description="Audit trail and data source info")

    # Core report sections (present but may have minimal data if insufficient_data)
    prediction: PredictionResult = Field(..., description="Prediction distribution and target probability")
    calibration: CalibrationResult = Field(..., description="Calibration metrics from latest job")
    reliability: ReliabilityResult = Field(..., description="Sensitivity, stability, and drift")

    # Status flags
    insufficient_data: bool = Field(
        default=False,
        description="True if n_runs < min_runs required"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Error messages explaining what is missing"
    )


# =============================================================================
# Request Schema (for query parameter validation)
# =============================================================================

class ReportQueryParams(BaseModel):
    """Query parameters for report endpoint."""
    metric_key: str = Field(..., min_length=1, description="Metric key (required)")
    op: ReportOperator = Field(..., description="Comparison operator (required)")
    threshold: float = Field(..., description="Threshold value (required)")
    manifest_hash: Optional[str] = Field(None, description="Optional manifest hash filter")
    min_runs: int = Field(default=3, ge=1, le=1000, description="Minimum runs required")
    window_days: int = Field(default=30, ge=1, le=365, description="Time window in days")
    n_sensitivity_grid: int = Field(default=20, ge=5, le=100, description="Number of sensitivity grid points")
    n_bootstrap: int = Field(default=200, ge=50, le=1000, description="Number of bootstrap samples")
    n_bins: int = Field(default=20, ge=5, le=100, description="Number of histogram bins")
