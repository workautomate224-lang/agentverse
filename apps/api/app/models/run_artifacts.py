"""
Run Artifacts Models - STEP 1 Audit Infrastructure
Reference: Step 1 Audit Requirements

Provides models for:
1. WorkerHeartbeat - Worker health and run assignment tracking
2. RunSpec - Explicit run specification artifact
3. RunTrace - Execution trace entries for audit
4. OutcomeReport - STEP 1 Artifact 3: Outcome with numeric results
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.node import Run


class WorkerHeartbeat(Base):
    """
    Worker heartbeat tracking for STEP 1 verification.

    Tracks:
    - Which workers are active
    - Last seen timestamp for each worker
    - Current run being executed
    - Execution statistics
    """
    __tablename__ = "worker_heartbeats"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    worker_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    # Worker details
    hostname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Heartbeat tracking (STEP 1: worker_id and last_seen_at)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False
    )

    # Current run assignment
    current_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Statistics
    runs_executed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    runs_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Additional metadata (named extra_data to avoid conflict with SQLAlchemy reserved 'metadata')
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<WorkerHeartbeat {self.worker_id} status={self.status}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation."""
        return {
            "worker_id": self.worker_id,
            "hostname": self.hostname,
            "pid": self.pid,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "status": self.status,
            "current_run_id": str(self.current_run_id) if self.current_run_id else None,
            "runs_executed": self.runs_executed,
            "runs_failed": self.runs_failed,
        }


class RunSpec(Base):
    """
    RunSpec artifact for STEP 1 verification.

    STEP 1 Artifact 1 Requirements:
    - run_id
    - project_id
    - ticks_total or horizon (must be > 0)
    - seed
    - model or model configuration
    - environment_spec (even minimal is required)
    - created_at
    """
    __tablename__ = "run_specs"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Core specification fields (STEP 1: Required fields)
    ticks_total: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    model_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    environment_spec: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    scheduler_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # STEP 3: Personas Integration (Required for auditable persona influence)
    # personas_snapshot_id - Reference to immutable persona snapshot used for this run
    # personas_summary - Summary of segments and weights for quick access
    personas_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persona_snapshots.id", ondelete="SET NULL"),
        nullable=True,  # Nullable for backwards compatibility with existing runs
        index=True
    )
    personas_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
        comment="STEP 3: Summary of persona segments and weights used in this run"
    )

    # Version tracking (C4: Auditable)
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False)
    ruleset_version: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    run: Mapped["Run"] = relationship("Run", foreign_keys=[run_id])

    def __repr__(self) -> str:
        return f"<RunSpec run_id={self.run_id} ticks={self.ticks_total}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation (viewable JSON)."""
        return {
            "run_id": str(self.run_id),
            "project_id": str(self.project_id),
            "ticks_total": self.ticks_total,
            "seed": self.seed,
            "model_config": self.model_config,
            "environment_spec": self.environment_spec,
            "scheduler_config": self.scheduler_config,
            # STEP 3: Personas tracking
            "personas_snapshot_id": str(self.personas_snapshot_id) if self.personas_snapshot_id else None,
            "personas_summary": self.personas_summary,
            # Version tracking
            "engine_version": self.engine_version,
            "ruleset_version": self.ruleset_version,
            "dataset_version": self.dataset_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RunTrace(Base):
    """
    RunTrace for STEP 1 verification.

    STEP 1 Artifact 2 Requirements:
    - At least 3 real trace entries required
    - Each entry must include:
      - run_id
      - timestamp
      - worker_id
      - execution stage or brief description
    """
    __tablename__ = "run_traces"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Trace entry fields (STEP 1: Required fields)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    worker_id: Mapped[str] = mapped_column(String(255), nullable=False)
    execution_stage: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional context
    tick_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    agents_processed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    events_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    run: Mapped["Run"] = relationship("Run", foreign_keys=[run_id])

    def __repr__(self) -> str:
        return f"<RunTrace run_id={self.run_id} stage={self.execution_stage}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation."""
        return {
            "run_id": str(self.run_id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "worker_id": self.worker_id,
            "execution_stage": self.execution_stage,
            "description": self.description,
            "tick_number": self.tick_number,
            "agents_processed": self.agents_processed,
            "events_count": self.events_count,
            "duration_ms": self.duration_ms,
            "metadata": self.extra_data,
        }


# Execution stages for RunTrace
class ExecutionStage:
    """Standard execution stages for trace entries."""
    CREATED = "created"
    QUEUED = "queued"
    WORKER_ASSIGNED = "worker_assigned"
    LOADING_CONFIG = "loading_config"
    INITIALIZING_RNG = "initializing_rng"
    LOADING_AGENTS = "loading_agents"
    SIMULATION_START = "simulation_start"
    TICK_START = "tick_start"
    TICK_COMPLETE = "tick_complete"
    SIMULATION_COMPLETE = "simulation_complete"
    AGGREGATING_OUTCOMES = "aggregating_outcomes"
    STORING_TELEMETRY = "storing_telemetry"
    COMPUTING_RELIABILITY = "computing_reliability"
    RUN_SUCCEEDED = "run_succeeded"
    RUN_FAILED = "run_failed"


class OutcomeReport(Base):
    """
    OutcomeReport for STEP 1 verification.

    STEP 1 Artifact 3 Requirements:
    - run_id and/or node_id
    - distribution (outcome distribution)
    - confidence (confidence intervals)
    - drivers (key drivers)
    - evidence refs (links to artifacts)

    This is a persisted artifact ensuring outcomes are auditable (C4).
    """
    __tablename__ = "outcome_reports"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Version tracking (C4: Auditable)
    report_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    report_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    # Primary outcome (STEP 1: Real numeric results)
    primary_outcome: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_outcome_probability: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False
    )

    # Distribution (STEP 1: numeric distribution)
    outcome_distribution: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Key metrics (STEP 1: at least one real numeric result)
    key_metrics: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False)

    # Key drivers
    key_drivers: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Confidence intervals
    confidence_interval_low: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    confidence_interval_high: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=True
    )

    # Ensemble/stability metrics
    ensemble_size: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    stability_variance: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 6), nullable=True
    )

    # Evidence references
    evidence_refs: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    run: Mapped["Run"] = relationship("Run", foreign_keys=[run_id])

    def __repr__(self) -> str:
        return f"<OutcomeReport run_id={self.run_id} outcome={self.primary_outcome}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation."""
        return {
            "id": str(self.id),
            "run_id": str(self.run_id),
            "node_id": str(self.node_id),
            "report_version": self.report_version,
            "report_hash": self.report_hash,
            "primary_outcome": self.primary_outcome,
            "primary_outcome_probability": float(self.primary_outcome_probability),
            "outcome_distribution": self.outcome_distribution,
            "key_metrics": self.key_metrics,
            "key_drivers": self.key_drivers,
            "confidence_interval_low": float(self.confidence_interval_low) if self.confidence_interval_low else None,
            "confidence_interval_high": float(self.confidence_interval_high) if self.confidence_interval_high else None,
            "ensemble_size": self.ensemble_size,
            "stability_variance": float(self.stability_variance) if self.stability_variance else None,
            "evidence_refs": self.evidence_refs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
