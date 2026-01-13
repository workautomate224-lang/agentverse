"""
Phase 8: Backtest Models

Supports end-to-end backtest orchestration with scoped reset capability.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, BigInteger
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class BacktestStatus(str, Enum):
    """Status states for backtest lifecycle."""
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class BacktestRunStatus(str, Enum):
    """Status states for individual backtest runs."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class Backtest(Base):
    """
    Backtest orchestration record.

    A Backtest represents a complete test scenario that triggers multiple
    simulation runs across one or more nodes, collecting telemetry and
    generating aggregated reports.

    Multi-tenant: All queries must be scoped by tenant_id.
    Scoped Reset: Reset operations only affect BacktestRun and BacktestReportSnapshot
    records belonging to this specific backtest, never global data.
    """
    __tablename__ = "backtests"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Multi-tenancy (required)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Project association
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Backtest metadata
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Scenario topic/description for the backtest",
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        default=BacktestStatus.CREATED.value,
        nullable=False,
        index=True,
    )

    # Configuration
    seed: Mapped[int] = mapped_column(
        Integer,
        default=42,
        nullable=False,
        comment="Base seed for deterministic execution",
    )
    config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Full backtest configuration including runs_per_node, agent_config, scenario_config",
    )

    # Optional notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Execution stats
    total_planned_runs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    completed_runs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed_runs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    backtest_runs: Mapped[List["BacktestRun"]] = relationship(
        "BacktestRun",
        back_populates="backtest",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    report_snapshots: Mapped[List["BacktestReportSnapshot"]] = relationship(
        "BacktestReportSnapshot",
        back_populates="backtest",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Backtest {self.id} name={self.name} status={self.status}>"


class BacktestRun(Base):
    """
    Individual run within a backtest.

    Links a Backtest to actual Run records, tracking execution status
    and manifest hash for reproducibility.
    """
    __tablename__ = "backtest_runs"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Backtest association
    backtest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backtests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Actual Run reference (nullable until run is created)
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Node being tested
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Run index within backtest (for deterministic seeding)
    run_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Derived seed for this specific run
    derived_seed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        default=BacktestRunStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # Provenance
    manifest_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA256 hash of run manifest for reproducibility",
    )

    # Error tracking
    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    backtest: Mapped["Backtest"] = relationship(
        "Backtest",
        back_populates="backtest_runs",
    )

    def __repr__(self) -> str:
        return f"<BacktestRun {self.id} backtest={self.backtest_id} status={self.status}>"


class BacktestReportSnapshot(Base):
    """
    Cached aggregated report for a backtest.

    Stores Phase 7 report output for a specific node/metric/threshold
    combination, avoiding re-computation on repeated access.
    """
    __tablename__ = "backtest_report_snapshots"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Backtest association
    backtest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backtests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Report parameters
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    op: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Comparison operator: ge, gt, le, lt, eq",
    )
    threshold: Mapped[float] = mapped_column(
        nullable=False,
    )

    # Additional params
    params: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Additional query params: window_days, min_runs, n_bootstrap, etc.",
    )

    # Cached report JSON
    report_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Full Phase 7 ReportResponse JSON",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    backtest: Mapped["Backtest"] = relationship(
        "Backtest",
        back_populates="report_snapshots",
    )

    def __repr__(self) -> str:
        return f"<BacktestReportSnapshot {self.id} node={self.node_id} metric={self.metric_key}>"
