"""
Phase 8: Backtest Schemas

Pydantic v2 schemas for backtest orchestration endpoints.
Supports create, reset, start, detail, runs, and report operations.

Reference: Phase 8 specification
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Enums (mirror model enums)
# =============================================================================

class BacktestStatusEnum(str, Enum):
    """Status states for backtest lifecycle."""
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class BacktestRunStatusEnum(str, Enum):
    """Status states for individual backtest runs."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# Configuration Schemas
# =============================================================================

class BacktestAgentConfig(BaseModel):
    """Agent configuration for backtest runs."""
    max_agents: int = Field(default=100, ge=1, le=10000, description="Maximum agents per run")
    sampling_policy: str = Field(default="all", description="Agent sampling policy: all, random, stratified")
    sampling_ratio: float = Field(default=1.0, ge=0.0, le=1.0, description="Sampling ratio for random/stratified")


class BacktestScenarioConfig(BaseModel):
    """Scenario configuration for backtest runs."""
    max_ticks: int = Field(default=100, ge=1, le=10000, description="Maximum ticks per run")
    tick_rate: int = Field(default=1, ge=1, description="Tick rate")
    scenario_patch: Optional[Dict[str, Any]] = Field(None, description="Optional scenario patch to apply")


class BacktestConfig(BaseModel):
    """Full backtest configuration."""
    runs_per_node: int = Field(default=3, ge=1, le=100, description="Number of runs per node")
    node_ids: List[str] = Field(default_factory=list, description="Specific node IDs to test (empty = all)")
    agent_config: BacktestAgentConfig = Field(default_factory=BacktestAgentConfig)
    scenario_config: BacktestScenarioConfig = Field(default_factory=BacktestScenarioConfig)


# =============================================================================
# Request Schemas
# =============================================================================

class BacktestCreate(BaseModel):
    """Request schema for creating a new backtest."""
    name: str = Field(..., min_length=1, max_length=255, description="Backtest name")
    topic: str = Field(..., min_length=1, max_length=500, description="Scenario topic/description")
    seed: int = Field(default=42, description="Base seed for deterministic execution")
    config: BacktestConfig = Field(default_factory=BacktestConfig)
    notes: Optional[str] = Field(None, description="Optional notes")


class BacktestReset(BaseModel):
    """Request schema for resetting backtest data.

    SCOPED-SAFE: Only resets data for THIS backtest, never global data.
    """
    confirm: bool = Field(
        ...,
        description="Must be true to confirm reset. Prevents accidental resets."
    )


class BacktestStart(BaseModel):
    """Request schema for starting a backtest."""
    sequential: bool = Field(
        default=True,
        description="Run sequentially (true) or in parallel via worker queue (false)"
    )


# =============================================================================
# Response Schemas
# =============================================================================

class BacktestRunResponse(BaseModel):
    """Response schema for a single backtest run."""
    id: str = Field(..., description="BacktestRun UUID")
    backtest_id: str = Field(..., description="Parent backtest UUID")
    run_id: Optional[str] = Field(None, description="Actual Run UUID (null until created)")
    node_id: str = Field(..., description="Node UUID being tested")
    run_index: int = Field(..., description="Run index within backtest")
    derived_seed: int = Field(..., description="Derived seed for this run")
    status: BacktestRunStatusEnum = Field(..., description="Run status")
    manifest_hash: Optional[str] = Field(None, description="SHA256 hash of run manifest")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    finished_at: Optional[datetime] = Field(None, description="Completion timestamp")

    class Config:
        from_attributes = True


class BacktestReportSnapshotResponse(BaseModel):
    """Response schema for a backtest report snapshot."""
    id: str = Field(..., description="Snapshot UUID")
    backtest_id: str = Field(..., description="Parent backtest UUID")
    node_id: str = Field(..., description="Node UUID")
    metric_key: str = Field(..., description="Metric key analyzed")
    op: str = Field(..., description="Comparison operator")
    threshold: float = Field(..., description="Threshold value")
    params: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")
    report_json: Dict[str, Any] = Field(default_factory=dict, description="Cached report JSON")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class BacktestResponse(BaseModel):
    """Response schema for backtest detail."""
    id: str = Field(..., description="Backtest UUID")
    tenant_id: str = Field(..., description="Tenant UUID")
    project_id: str = Field(..., description="Project UUID")
    name: str = Field(..., description="Backtest name")
    topic: str = Field(..., description="Scenario topic/description")
    status: BacktestStatusEnum = Field(..., description="Backtest status")
    seed: int = Field(..., description="Base seed")
    config: Dict[str, Any] = Field(default_factory=dict, description="Full configuration")
    notes: Optional[str] = Field(None, description="Optional notes")
    total_planned_runs: int = Field(..., description="Total planned runs")
    completed_runs: int = Field(..., description="Completed runs count")
    failed_runs: int = Field(..., description="Failed runs count")
    created_at: datetime = Field(..., description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    finished_at: Optional[datetime] = Field(None, description="Completion timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Progress computed fields
    progress_percent: float = Field(
        default=0.0,
        description="Completion progress as percentage"
    )

    class Config:
        from_attributes = True


class BacktestListResponse(BaseModel):
    """Response schema for listing backtests."""
    items: List[BacktestResponse] = Field(default_factory=list, description="List of backtests")
    total: int = Field(..., description="Total count")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=20, description="Page size")


class BacktestRunsResponse(BaseModel):
    """Response schema for backtest runs listing."""
    backtest_id: str = Field(..., description="Parent backtest UUID")
    items: List[BacktestRunResponse] = Field(default_factory=list, description="List of runs")
    total: int = Field(..., description="Total count")
    by_status: Dict[str, int] = Field(default_factory=dict, description="Counts by status")


class BacktestReportsResponse(BaseModel):
    """Response schema for backtest report snapshots."""
    backtest_id: str = Field(..., description="Parent backtest UUID")
    items: List[BacktestReportSnapshotResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total count")


# =============================================================================
# Action Response Schemas
# =============================================================================

class BacktestResetResponse(BaseModel):
    """Response schema for backtest reset operation.

    SCOPED-SAFE: Documents what was deleted.
    """
    backtest_id: str = Field(..., description="Backtest UUID")
    runs_deleted: int = Field(..., description="Number of BacktestRun records deleted")
    snapshots_deleted: int = Field(..., description="Number of BacktestReportSnapshot records deleted")
    message: str = Field(..., description="Human-readable message")


class BacktestStartResponse(BaseModel):
    """Response schema for backtest start operation."""
    backtest_id: str = Field(..., description="Backtest UUID")
    status: BacktestStatusEnum = Field(..., description="New status")
    runs_queued: int = Field(..., description="Number of runs queued")
    message: str = Field(..., description="Human-readable message")
