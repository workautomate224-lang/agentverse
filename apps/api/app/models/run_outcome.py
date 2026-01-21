"""
Run Outcome Model - PHASE 3: Probability Source Compliance

Stores normalized numeric outcomes per run for empirical distribution computation.
This enables auditable, evidence-based probability calculations.

Reference: project.md Phase 3 - Probability Source Compliance
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OutcomeStatus(str):
    """Status values for run outcomes."""
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RunOutcome(Base):
    """
    Stores normalized numeric outcomes per completed run.

    Used for computing empirical probability distributions across multiple runs.
    Only SUCCEEDED runs should be stored here by default.

    Key Properties:
    - One RunOutcome per Run (unique run_id)
    - Contains normalized metrics in metrics_json
    - Tracks data quality via quality_flags
    - Links to manifest via manifest_hash for version filtering
    """

    __tablename__ = "run_outcomes"

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

    # Foreign keys (references project_specs, not legacy projects table)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
    )

    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One outcome per run
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Link to Phase 2 manifest for version filtering
    manifest_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    # Normalized numeric outcomes
    # Example:
    # {
    #   "ticks_executed": 1000,
    #   "total_agents": 100,
    #   "score": 0.73,
    #   "cost": 12.5,
    #   "success": 1,
    #   "primary_outcome_probability": 0.65,
    #   "adoption_rate": 0.42,
    #   "custom": {...}
    # }
    metrics_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Data quality flags
    # Example:
    # {
    #   "partial_telemetry": false,
    #   "errors": 0,
    #   "warnings": [],
    #   "execution_duration_ms": 5000
    # }
    quality_flags: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Run status (only SUCCEEDED by default)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=OutcomeStatus.SUCCEEDED,
    )

    # Composite indexes for efficient queries
    __table_args__ = (
        # Primary query pattern: get all outcomes for a node
        Index(
            "ix_run_outcomes_project_node_created",
            "project_id",
            "node_id",
            "created_at",
        ),
        # Filter by manifest version
        Index(
            "ix_run_outcomes_node_manifest",
            "node_id",
            "manifest_hash",
        ),
        # Tenant scoping
        Index(
            "ix_run_outcomes_tenant_project",
            "tenant_id",
            "project_id",
        ),
        # Unique constraint on run_id
        UniqueConstraint("run_id", name="uq_run_outcomes_run_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<RunOutcome(id={self.id}, run_id={self.run_id}, "
            f"node_id={self.node_id}, status={self.status})>"
        )

    @classmethod
    def from_run_completion(
        cls,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        node_id: uuid.UUID,
        run_id: uuid.UUID,
        outcomes: Dict[str, Any],
        timing: Dict[str, Any],
        reliability: Optional[Dict[str, Any]] = None,
        execution_counters: Optional[Dict[str, Any]] = None,
        manifest_hash: Optional[str] = None,
    ) -> "RunOutcome":
        """
        Create a RunOutcome from run completion data.

        Extracts and normalizes numeric metrics from the various outcome sources.

        Args:
            tenant_id: Tenant ID
            project_id: Project ID
            node_id: Node ID the run belongs to
            run_id: Run ID
            outcomes: AggregatedOutcome dict from run completion
            timing: Run timing dict with duration, ticks_executed
            reliability: Optional reliability metrics
            execution_counters: Optional execution counters from Evidence Pack
            manifest_hash: Optional manifest hash from Phase 2

        Returns:
            New RunOutcome instance (not yet added to session)
        """
        # Extract normalized metrics
        metrics = cls._extract_metrics(outcomes, timing, execution_counters)

        # Extract quality flags
        quality = cls._extract_quality_flags(
            outcomes, timing, reliability, execution_counters
        )

        return cls(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            node_id=node_id,
            run_id=run_id,
            manifest_hash=manifest_hash,
            metrics_json=metrics,
            quality_flags=quality,
            status=OutcomeStatus.SUCCEEDED,
            created_at=datetime.utcnow(),
        )

    @staticmethod
    def _extract_metrics(
        outcomes: Dict[str, Any],
        timing: Dict[str, Any],
        execution_counters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Extract and normalize numeric metrics from outcome data.

        Ensures all values are numeric (int, float) for distribution computation.
        """
        metrics: Dict[str, Any] = {}

        # From timing
        if timing:
            if "ticks_executed" in timing:
                metrics["ticks_executed"] = int(timing["ticks_executed"])
            if "duration_ms" in timing:
                metrics["duration_ms"] = int(timing["duration_ms"])

        # From outcomes
        if outcomes:
            # Primary outcome probability
            if "primary_outcome_probability" in outcomes:
                metrics["primary_outcome_probability"] = float(
                    outcomes["primary_outcome_probability"]
                )

            # Outcome distribution (convert to individual metrics)
            if "outcome_distribution" in outcomes:
                for key, value in outcomes["outcome_distribution"].items():
                    if isinstance(value, (int, float)):
                        metrics[f"outcome_{key}"] = float(value)

            # Key metrics (numbered list in current format)
            if "key_metrics" in outcomes:
                for km in outcomes["key_metrics"]:
                    if isinstance(km, dict) and "name" in km and "value" in km:
                        name = km["name"].lower().replace(" ", "_")
                        value = km["value"]
                        if isinstance(value, (int, float)):
                            metrics[name] = float(value)

            # Variance metrics
            if "variance_metrics" in outcomes:
                for key, value in outcomes["variance_metrics"].items():
                    if isinstance(value, (int, float)):
                        metrics[f"variance_{key}"] = float(value)

            # Seed (for reproducibility tracking)
            if "seed" in outcomes:
                metrics["seed"] = int(outcomes["seed"])

        # From execution counters (Evidence Pack)
        if execution_counters:
            if "agent_steps_executed" in execution_counters:
                metrics["agent_steps_executed"] = int(
                    execution_counters["agent_steps_executed"]
                )

            # Loop stage counters
            if "loop_stage_counters" in execution_counters:
                for stage, count in execution_counters["loop_stage_counters"].items():
                    if isinstance(count, (int, float)):
                        metrics[f"loop_{stage}"] = int(count)

        return metrics

    @staticmethod
    def _extract_quality_flags(
        outcomes: Dict[str, Any],
        timing: Dict[str, Any],
        reliability: Optional[Dict[str, Any]] = None,
        execution_counters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Extract data quality flags from outcome data.

        These flags help filter low-quality runs from aggregation.
        """
        flags: Dict[str, Any] = {
            "partial_telemetry": False,
            "errors": 0,
            "warnings": [],
        }

        # Check for execution duration
        if timing and "duration_ms" in timing:
            flags["execution_duration_ms"] = int(timing["duration_ms"])

        # Check reliability data gaps
        if reliability:
            data_gaps = reliability.get("data_gaps", [])
            if data_gaps:
                flags["partial_telemetry"] = True
                flags["warnings"].append("data_gaps_detected")

            # Store confidence for filtering
            if "confidence" in reliability:
                flags["confidence"] = float(reliability["confidence"])

        # Check execution counters for issues
        if execution_counters:
            backpressure = execution_counters.get("backpressure_events", 0)
            if backpressure > 0:
                flags["warnings"].append(f"backpressure_events:{backpressure}")

        return flags

    def get_metric_keys(self) -> List[str]:
        """Get list of available metric keys."""
        return list(self.metrics_json.keys())

    def get_metric(self, key: str, default: Any = None) -> Any:
        """Get a specific metric value."""
        return self.metrics_json.get(key, default)
