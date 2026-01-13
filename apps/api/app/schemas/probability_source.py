"""
Probability Source Schemas - PHASE 3: Probability Source Compliance

Pydantic v2 schemas for probability source API endpoints.
Ensures all probability outputs include auditable source metadata.

Reference: project.md Phase 3 - Probability Source Compliance
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Enums
# =============================================================================

class WeightingMethod(str, Enum):
    """Weighting methods for aggregation."""
    UNIFORM = "uniform"
    RECENT_DECAY = "recent_decay"


class ProbabilityStatus(str, Enum):
    """Status of probability computation."""
    OK = "ok"
    INSUFFICIENT_DATA = "insufficient_data"


class ComparisonOperator(str, Enum):
    """Comparison operators for target probability."""
    GTE = ">="
    LTE = "<="
    GT = ">"
    LT = "<"
    EQ = "=="


# =============================================================================
# Source Metadata Schemas
# =============================================================================

class DataQuality(BaseModel):
    """Data quality information for probability source."""
    partial_telemetry_runs: int = Field(
        default=0,
        description="Number of runs with partial telemetry",
    )
    failed_runs_excluded: int = Field(
        default=0,
        description="Number of failed runs excluded from aggregation",
    )
    low_confidence_runs: int = Field(
        default=0,
        description="Number of runs with low confidence scores",
    )
    average_confidence: Optional[float] = Field(
        default=None,
        description="Average confidence across included runs",
    )


class FiltersApplied(BaseModel):
    """Filters applied to the probability source query."""
    manifest_hash: Optional[str] = Field(
        default=None,
        description="Manifest hash filter (Phase 2)",
    )
    rules_version: Optional[str] = Field(
        default=None,
        description="Rules version filter",
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Model version filter",
    )
    time_window_days: Optional[int] = Field(
        default=None,
        description="Time window in days",
    )
    status: str = Field(
        default="succeeded",
        description="Run status filter",
    )


class ProbabilitySourceMetadata(BaseModel):
    """
    Metadata explaining the source of a probability estimate.

    This is required for all probability outputs to ensure auditability.
    """
    source_type: str = Field(
        default="empirical_runs",
        description="Type of probability source",
    )
    project_id: UUID = Field(
        ...,
        description="Project ID",
    )
    node_id: UUID = Field(
        ...,
        description="Node ID the probability is computed for",
    )
    metric_key: str = Field(
        ...,
        description="Metric key used for computation",
    )
    filters_applied: FiltersApplied = Field(
        default_factory=FiltersApplied,
        description="Filters applied to the data",
    )
    n_runs: int = Field(
        ...,
        ge=0,
        description="Number of runs used in computation",
    )
    min_runs_required: int = Field(
        default=3,
        description="Minimum runs required for valid probability",
    )
    max_runs_used: int = Field(
        default=200,
        description="Maximum runs considered",
    )
    time_window_days: Optional[int] = Field(
        default=None,
        description="Time window in days (None = all time)",
    )
    weighting: WeightingMethod = Field(
        default=WeightingMethod.UNIFORM,
        description="Weighting method used",
    )
    data_quality: DataQuality = Field(
        default_factory=DataQuality,
        description="Data quality flags",
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp of most recent run in dataset",
    )


# =============================================================================
# Distribution Schemas
# =============================================================================

class HistogramBucket(BaseModel):
    """A single histogram bucket."""
    bin_start: float = Field(..., description="Start of bin (inclusive)")
    bin_end: float = Field(..., description="End of bin (exclusive)")
    count: int = Field(..., ge=0, description="Number of values in bucket")
    frequency: float = Field(..., ge=0, le=1, description="Relative frequency")


class DistributionSummary(BaseModel):
    """
    Summary statistics for a distribution.

    Includes central tendency, spread, and percentiles.
    """
    mean: float = Field(..., description="Arithmetic mean")
    std: float = Field(..., ge=0, description="Standard deviation")
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")

    # Percentiles
    p5: float = Field(..., description="5th percentile")
    p25: float = Field(..., description="25th percentile (Q1)")
    p50: float = Field(..., description="50th percentile (median)")
    p75: float = Field(..., description="75th percentile (Q3)")
    p95: float = Field(..., description="95th percentile")

    # Histogram
    histogram: List[HistogramBucket] = Field(
        default_factory=list,
        description="Histogram buckets for visualization",
    )


# =============================================================================
# API Request/Response Schemas
# =============================================================================

class AvailableMetricsResponse(BaseModel):
    """Response for GET /nodes/{node_id}/metrics endpoint."""
    node_id: UUID = Field(..., description="Node ID")
    project_id: UUID = Field(..., description="Project ID")
    metric_keys: List[str] = Field(
        default_factory=list,
        description="Available metric keys for this node",
    )
    n_runs: int = Field(..., ge=0, description="Total runs with outcomes")
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of most recent outcome",
    )


class ProbabilitySourceRequest(BaseModel):
    """Query parameters for probability source endpoint."""
    metric: str = Field(
        ...,
        min_length=1,
        description="Metric key to compute distribution for",
    )
    manifest_hash: Optional[str] = Field(
        default=None,
        description="Filter by manifest hash (Phase 2)",
    )
    time_window_days: Optional[int] = Field(
        default=30,
        ge=1,
        le=365,
        description="Time window in days (default 30)",
    )
    weighting: WeightingMethod = Field(
        default=WeightingMethod.UNIFORM,
        description="Weighting method",
    )
    min_runs: int = Field(
        default=3,
        ge=1,
        le=100,
        description="Minimum runs required",
    )
    max_runs: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum runs to consider",
    )


class ProbabilitySourceResponse(BaseModel):
    """Response for GET /nodes/{node_id}/probability-source endpoint."""
    status: ProbabilityStatus = Field(
        ...,
        description="Status of probability computation",
    )
    probability_source: ProbabilitySourceMetadata = Field(
        ...,
        description="Source metadata for auditability",
    )
    distribution: Optional[DistributionSummary] = Field(
        default=None,
        description="Distribution summary (None if insufficient_data)",
    )
    sample_run_ids: List[UUID] = Field(
        default_factory=list,
        max_length=10,
        description="Sample run IDs for audit (up to 10)",
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable message (especially for insufficient_data)",
    )


class TargetProbabilityRequest(BaseModel):
    """Query parameters for target probability endpoint."""
    metric: str = Field(
        ...,
        min_length=1,
        description="Metric key to evaluate",
    )
    op: ComparisonOperator = Field(
        ...,
        description="Comparison operator",
    )
    threshold: float = Field(
        ...,
        description="Threshold value to compare against",
    )
    manifest_hash: Optional[str] = Field(
        default=None,
        description="Filter by manifest hash",
    )
    time_window_days: Optional[int] = Field(
        default=30,
        ge=1,
        le=365,
        description="Time window in days",
    )
    weighting: WeightingMethod = Field(
        default=WeightingMethod.UNIFORM,
        description="Weighting method",
    )


class TargetProbabilityResponse(BaseModel):
    """Response for GET /nodes/{node_id}/target-probability endpoint."""
    status: ProbabilityStatus = Field(
        ...,
        description="Status of probability computation",
    )
    probability: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Probability of meeting threshold (None if insufficient_data)",
    )
    condition: str = Field(
        ...,
        description="Human-readable condition, e.g., 'score >= 0.8'",
    )
    probability_source: ProbabilitySourceMetadata = Field(
        ...,
        description="Source metadata for auditability",
    )
    sample_run_ids: List[UUID] = Field(
        default_factory=list,
        max_length=10,
        description="Sample run IDs for audit",
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable message",
    )


# =============================================================================
# Internal/Service Schemas
# =============================================================================

class RunOutcomeCreate(BaseModel):
    """Schema for creating a run outcome record."""
    tenant_id: UUID
    project_id: UUID
    node_id: UUID
    run_id: UUID
    manifest_hash: Optional[str] = None
    metrics_json: Dict[str, Any] = Field(default_factory=dict)
    quality_flags: Dict[str, Any] = Field(default_factory=dict)
    status: str = "succeeded"


class RunOutcomeResponse(BaseModel):
    """Response schema for run outcome queries."""
    id: UUID
    tenant_id: UUID
    project_id: UUID
    node_id: UUID
    run_id: UUID
    created_at: datetime
    manifest_hash: Optional[str] = None
    metrics_json: Dict[str, Any]
    quality_flags: Dict[str, Any]
    status: str

    class Config:
        from_attributes = True


class AggregationResult(BaseModel):
    """Internal result of aggregation computation."""
    status: ProbabilityStatus
    n_runs: int
    values: List[float] = Field(default_factory=list)
    weights: List[float] = Field(default_factory=list)
    run_ids: List[UUID] = Field(default_factory=list)
    created_ats: List[datetime] = Field(default_factory=list)
    quality_summary: DataQuality = Field(default_factory=DataQuality)
