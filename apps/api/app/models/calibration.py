"""
Calibration Models - PHASE 4: Calibration Minimal Closed Loop

Models for ground truth datasets, labels, calibration jobs, and iterations.
Enables a production-usable calibration loop with:
1) Ground truth label management
2) Background calibration jobs via Celery
3) Deterministic calibration algorithm with auditable results

Reference: project.md Phase 4 - Calibration Lab Backend
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


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


# =============================================================================
# Ground Truth Dataset Model
# =============================================================================

class GroundTruthDataset(Base):
    """
    A named collection of ground truth labels for calibration.

    Datasets allow users to organize ground truth labels into logical groups
    (e.g., "Q4 2025 Historical Data", "Toy Test Dataset").
    """

    __tablename__ = "ground_truth_datasets"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Multi-tenancy
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Project association
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Dataset metadata
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    labels: Mapped[List["GroundTruthLabel"]] = relationship(
        "GroundTruthLabel",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index(
            "ix_ground_truth_datasets_tenant_project",
            "tenant_id",
            "project_id",
        ),
    )

    def __repr__(self) -> str:
        return f"<GroundTruthDataset(id={self.id}, name={self.name})>"


# =============================================================================
# Ground Truth Label Model
# =============================================================================

class GroundTruthLabel(Base):
    """
    Individual ground truth label for a specific run.

    Links a run to its known outcome (label=True/False or 1/0).
    Used for calibration against historical data.

    Constraints:
    - UNIQUE(dataset_id, run_id) for idempotent upsert
    - Labels are immutable once created (fork-not-mutate spirit)
    """

    __tablename__ = "ground_truth_labels"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Multi-tenancy
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Project association
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Dataset association
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ground_truth_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Node association (for filtering)
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Run association
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # The ground truth label (0 or 1)
    label: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Optional metadata
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    json_meta: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    dataset: Mapped["GroundTruthDataset"] = relationship(
        "GroundTruthDataset",
        back_populates="labels",
    )

    # Indexes and constraints
    __table_args__ = (
        # Unique constraint: one label per run per dataset
        UniqueConstraint(
            "dataset_id",
            "run_id",
            name="uq_ground_truth_labels_dataset_run",
        ),
        Index(
            "ix_ground_truth_labels_tenant_project",
            "tenant_id",
            "project_id",
        ),
        Index(
            "ix_ground_truth_labels_dataset_node",
            "dataset_id",
            "node_id",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<GroundTruthLabel(id={self.id}, run_id={self.run_id}, "
            f"label={self.label})>"
        )


# =============================================================================
# Calibration Job Model
# =============================================================================

class CalibrationJob(Base):
    """
    A calibration job that runs in the background via Celery.

    Stores:
    - Configuration (target_accuracy, max_iterations, etc.)
    - Status tracking
    - Results (best_mapping, metrics, audit summary)

    Jobs are deterministic: same config + same data = same results.
    """

    __tablename__ = "calibration_jobs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Multi-tenancy
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Project association
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Node being calibrated
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Ground truth dataset
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ground_truth_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Job status
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CalibrationJobStatus.QUEUED.value,
    )

    # Configuration
    # Example:
    # {
    #   "target_accuracy": 0.85,
    #   "max_iterations": 10,
    #   "metric_key": "outcome_value",
    #   "op": ">=",
    #   "threshold": 0.5,
    #   "time_window_days": 30,
    #   "weighting": "uniform",
    #   "seed": 42
    # }
    config_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Results
    # Example:
    # {
    #   "best_mapping": [[0.0, 0.2, 0.1], [0.2, 0.4, 0.3], ...],
    #   "best_bin_count": 10,
    #   "best_iteration": 5,
    #   "metrics": {
    #     "accuracy": 0.87,
    #     "brier_score": 0.12,
    #     "ece": 0.05
    #   },
    #   "n_samples": 42,
    #   "selected_run_ids": [...],
    #   "audit": {
    #     "runs_matched": 42,
    #     "runs_missing_labels": 5,
    #     "runs_missing_metric": 2
    #   }
    # }
    result_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Progress tracking
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    total_iterations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Created by user
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Celery task ID for tracking
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Relationships
    iterations: Mapped[List["CalibrationIteration"]] = relationship(
        "CalibrationIteration",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="CalibrationIteration.iter_index",
    )

    # Indexes
    __table_args__ = (
        Index(
            "ix_calibration_jobs_tenant_project",
            "tenant_id",
            "project_id",
        ),
        Index(
            "ix_calibration_jobs_node_status",
            "node_id",
            "status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CalibrationJob(id={self.id}, node_id={self.node_id}, "
            f"status={self.status})>"
        )

    def is_terminal(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in (
            CalibrationJobStatus.SUCCEEDED.value,
            CalibrationJobStatus.FAILED.value,
            CalibrationJobStatus.CANCELED.value,
        )


# =============================================================================
# Calibration Iteration Model
# =============================================================================

class CalibrationIteration(Base):
    """
    A single iteration of a calibration job.

    Stores the parameters tried and resulting metrics.
    Useful for UI progress display and debugging.
    """

    __tablename__ = "calibration_iterations"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Job association
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calibration_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Iteration index (0-based)
    iter_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Parameters for this iteration
    # Example: {"bin_count": 10}
    params_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Metrics from this iteration
    # Example: {"accuracy": 0.85, "brier_score": 0.12, "ece": 0.05}
    metrics_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # The calibration mapping produced
    # List of [bin_start, bin_end, calibrated_prob]
    mapping_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    job: Mapped["CalibrationJob"] = relationship(
        "CalibrationJob",
        back_populates="iterations",
    )

    # Indexes
    __table_args__ = (
        Index(
            "ix_calibration_iterations_job_index",
            "job_id",
            "iter_index",
        ),
        UniqueConstraint(
            "job_id",
            "iter_index",
            name="uq_calibration_iterations_job_index",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CalibrationIteration(id={self.id}, job_id={self.job_id}, "
            f"iter_index={self.iter_index})>"
        )
