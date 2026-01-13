"""
Calibration Schemas - PHASE 4: Calibration Minimal Closed Loop

Pydantic v2 schemas for calibration API endpoints.
Includes ground truth datasets, labels, calibration jobs, and results.

Reference: project.md Phase 4 - Calibration Lab Backend
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Enums
# =============================================================================

class CalibrationJobStatus(str, Enum):
    """Status values for calibration jobs."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class ComparisonOperator(str, Enum):
    """Comparison operators for threshold conditions."""
    GTE = ">="
    LTE = "<="
    GT = ">"
    LT = "<"
    EQ = "=="


class WeightingMethod(str, Enum):
    """Weighting methods for sample aggregation."""
    UNIFORM = "uniform"
    RECENT_DECAY = "recent_decay"


# =============================================================================
# Ground Truth Dataset Schemas
# =============================================================================

class GroundTruthDatasetCreate(BaseModel):
    """Request schema for creating a ground truth dataset."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the dataset",
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description",
    )


class GroundTruthDatasetResponse(BaseModel):
    """Response schema for ground truth dataset."""
    id: UUID
    tenant_id: UUID
    project_id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    label_count: int = Field(
        default=0,
        description="Number of labels in this dataset",
    )

    model_config = {"from_attributes": True}


class GroundTruthDatasetListResponse(BaseModel):
    """Response for listing datasets."""
    datasets: List[GroundTruthDatasetResponse]
    total: int


# =============================================================================
# Ground Truth Label Schemas
# =============================================================================

class GroundTruthLabelInput(BaseModel):
    """Input schema for a single ground truth label."""
    run_id: UUID = Field(..., description="Run ID to label")
    node_id: UUID = Field(..., description="Node ID the run belongs to")
    label: int = Field(
        ...,
        ge=0,
        le=1,
        description="Ground truth label (0 or 1)",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional notes about this label",
    )
    json_meta: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata",
    )


class BulkUpsertLabelsRequest(BaseModel):
    """Request for bulk upserting labels."""
    labels: List[GroundTruthLabelInput] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Labels to upsert (max 1000)",
    )


class BulkUpsertLabelsResponse(BaseModel):
    """Response for bulk upsert operation."""
    created: int = Field(..., description="Number of labels created")
    updated: int = Field(..., description="Number of labels updated")
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Any errors encountered",
    )


class GroundTruthLabelResponse(BaseModel):
    """Response schema for a ground truth label."""
    id: UUID
    tenant_id: UUID
    project_id: UUID
    dataset_id: UUID
    node_id: UUID
    run_id: UUID
    label: int
    notes: Optional[str]
    json_meta: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class GroundTruthLabelListResponse(BaseModel):
    """Response for listing labels."""
    labels: List[GroundTruthLabelResponse]
    total: int
    limit: int
    offset: int


# =============================================================================
# Calibration Job Schemas
# =============================================================================

class CalibrationStartRequest(BaseModel):
    """Request schema for starting a calibration job."""
    node_id: UUID = Field(..., description="Node to calibrate")
    dataset_id: UUID = Field(..., description="Ground truth dataset to use")
    target_accuracy: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Target accuracy threshold for early stopping",
    )
    max_iterations: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of iterations",
    )
    metric_key: str = Field(
        default="outcome_value",
        description="Metric key to use from RunOutcome.metrics_json",
    )
    op: Optional[ComparisonOperator] = Field(
        default=None,
        description="Comparison operator for threshold condition",
    )
    threshold: Optional[float] = Field(
        default=None,
        description="Threshold value for condition",
    )
    time_window_days: Optional[int] = Field(
        default=30,
        ge=1,
        le=365,
        description="Time window for selecting run outcomes",
    )
    weighting: WeightingMethod = Field(
        default=WeightingMethod.UNIFORM,
        description="Weighting method for samples",
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducibility",
    )

    @field_validator("threshold")
    @classmethod
    def validate_threshold_with_op(cls, v, info):
        """Validate that threshold is provided if op is provided."""
        if info.data.get("op") and v is None:
            raise ValueError("threshold is required when op is provided")
        return v


class CalibrationStartResponse(BaseModel):
    """Response for starting a calibration job."""
    job_id: UUID
    status: CalibrationJobStatus
    message: str


class CalibrationJobResponse(BaseModel):
    """Response schema for calibration job status."""
    id: UUID
    tenant_id: UUID
    project_id: UUID
    node_id: UUID
    dataset_id: UUID
    status: CalibrationJobStatus
    config_json: Dict[str, Any]
    progress: int
    total_iterations: int
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]
    # Latest metrics summary (if available)
    latest_metrics: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class CalibrationIterationResponse(BaseModel):
    """Response schema for a calibration iteration."""
    id: UUID
    job_id: UUID
    iter_index: int
    params_json: Dict[str, Any]
    metrics_json: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class CalibrationIterationsResponse(BaseModel):
    """Response for listing iterations."""
    job_id: UUID
    iterations: List[CalibrationIterationResponse]
    total: int


# =============================================================================
# Calibration Result Schemas
# =============================================================================

class CalibrationBin(BaseModel):
    """A single calibration bin."""
    bin_start: float
    bin_end: float
    calibrated_prob: float
    n_samples: int
    empirical_rate: float


class CalibrationMetrics(BaseModel):
    """Calibration quality metrics."""
    accuracy: float = Field(..., ge=0, le=1, description="Classification accuracy")
    brier_score: float = Field(..., ge=0, description="Brier score (lower is better)")
    ece: float = Field(..., ge=0, description="Expected Calibration Error")
    n_samples: int = Field(..., ge=0, description="Number of samples used")


class CalibrationResultResponse(BaseModel):
    """Response schema for calibration results."""
    job_id: UUID
    status: CalibrationJobStatus

    # Best result (None if job not completed)
    best_mapping: Optional[List[CalibrationBin]] = Field(
        default=None,
        description="Best calibration mapping found",
    )
    best_bin_count: Optional[int] = Field(
        default=None,
        description="Number of bins in best mapping",
    )
    best_iteration: Optional[int] = Field(
        default=None,
        description="Iteration index that produced best result",
    )
    metrics: Optional[CalibrationMetrics] = Field(
        default=None,
        description="Metrics for best mapping",
    )

    # Audit information
    audit: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Audit summary (runs matched, missing, etc.)",
    )
    selected_run_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Run IDs used in calibration (sample)",
    )

    # Timing
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Error if failed
    error_message: Optional[str] = None


class CalibrationCancelResponse(BaseModel):
    """Response for canceling a calibration job."""
    job_id: UUID
    status: CalibrationJobStatus
    message: str


# =============================================================================
# Internal/Service Schemas
# =============================================================================

class CalibrationSample(BaseModel):
    """Internal schema for a calibration sample."""
    run_id: UUID
    predicted_value: float
    label: int
    weight: float = 1.0


class CalibrationConfig(BaseModel):
    """Internal schema for calibration configuration."""
    node_id: UUID
    dataset_id: UUID
    target_accuracy: float
    max_iterations: int
    metric_key: str
    op: Optional[ComparisonOperator] = None
    threshold: Optional[float] = None
    time_window_days: Optional[int] = None
    weighting: WeightingMethod = WeightingMethod.UNIFORM
    seed: Optional[int] = None
