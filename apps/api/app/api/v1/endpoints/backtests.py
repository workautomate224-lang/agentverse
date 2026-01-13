"""
PHASE 8: Backtest Orchestration Endpoints

Provides comprehensive backtest management:
- Create backtests with configuration
- SCOPED-SAFE reset (only deletes backtest-specific data, never global)
- Start execution (sequential or parallel)
- Get detail, runs, and report snapshots

Reference: Phase 8 specification

CRITICAL SAFETY: Reset operations are SCOPED-SAFE
- reset_backtest_data() only deletes BacktestRun and BacktestReportSnapshot
  belonging to a specific backtest_id
- NEVER deletes global runs, telemetry, or data from other backtests
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_tenant, TenantContext
from app.models.user import User
from app.schemas.backtest import (
    BacktestCreate,
    BacktestReset,
    BacktestStart,
    BacktestResponse,
    BacktestListResponse,
    BacktestRunsResponse,
    BacktestReportsResponse,
    BacktestResetResponse,
    BacktestStartResponse,
    BacktestStatusEnum,
)
from app.services.backtest_service import get_backtest_service


logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# List Backtests
# =============================================================================

@router.get(
    "/project-specs/{project_id}/backtests",
    response_model=BacktestListResponse,
    summary="List backtests for a project (PHASE 8)",
    description="""
    List all backtests for a project with optional status filter.

    Results are ordered by creation date (newest first) and paginated.

    Multi-tenant scoped.
    """,
    tags=["Backtests"],
)
async def list_backtests(
    project_id: UUID,
    status: Optional[BacktestStatusEnum] = Query(
        None,
        description="Filter by backtest status"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(require_tenant),
) -> BacktestListResponse:
    """List all backtests for a project."""
    service = get_backtest_service(db)
    # Note: status_filter not yet implemented in service
    return await service.list_backtests(
        tenant_id=tenant.tenant_id,
        project_id=project_id,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Create Backtest
# =============================================================================

@router.post(
    "/project-specs/{project_id}/backtests",
    response_model=BacktestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new backtest (PHASE 8)",
    description="""
    Create a new backtest with configuration.

    ## Configuration Options

    - **runs_per_node**: Number of runs to execute per node (default: 3)
    - **node_ids**: Specific nodes to test (empty = all nodes)
    - **seed**: Base seed for deterministic execution
    - **agent_config**: Agent sampling settings
    - **scenario_config**: Scenario execution settings

    ## Deterministic Seeding

    Each run gets a derived seed: `hash(base_seed + node_id + run_index)`
    This ensures reproducibility across identical configurations.

    Multi-tenant scoped. Creates BacktestRun records for all planned runs.
    """,
    tags=["Backtests"],
)
async def create_backtest(
    project_id: UUID,
    data: BacktestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(require_tenant),
) -> BacktestResponse:
    """Create a new backtest with planned runs."""
    service = get_backtest_service(db)
    return await service.create_backtest(
        tenant_id=tenant.tenant_id,
        project_id=project_id,
        payload=data,
    )


# =============================================================================
# Get Backtest Detail
# =============================================================================

@router.get(
    "/project-specs/{project_id}/backtests/{backtest_id}",
    response_model=BacktestResponse,
    summary="Get backtest detail (PHASE 8)",
    description="""
    Get detailed information about a specific backtest.

    Includes:
    - Status and progress
    - Configuration
    - Run counts (total, completed, failed)
    - Timestamps

    Multi-tenant scoped.
    """,
    tags=["Backtests"],
)
async def get_backtest(
    project_id: UUID,
    backtest_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(require_tenant),
) -> BacktestResponse:
    """Get backtest details."""
    service = get_backtest_service(db)
    result = await service.get_backtest(
        tenant_id=tenant.tenant_id,
        project_id=project_id,
        backtest_id=backtest_id,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest not found"
        )

    return result


# =============================================================================
# Reset Backtest Data (SCOPED-SAFE)
# =============================================================================

@router.post(
    "/project-specs/{project_id}/backtests/{backtest_id}/reset",
    response_model=BacktestResetResponse,
    summary="Reset backtest data (SCOPED-SAFE) (PHASE 8)",
    description="""
    Reset backtest data for re-execution.

    ## SCOPED-SAFE GUARANTEE

    This operation ONLY deletes:
    - BacktestRun records for THIS backtest
    - BacktestReportSnapshot records for THIS backtest

    This operation NEVER deletes:
    - Global Run records (actual simulation runs)
    - Global telemetry data
    - Data from other backtests
    - Any other tenant data

    The backtest itself is preserved and reset to 'created' status.

    ## Confirmation Required

    Set `confirm: true` in the request body to proceed.
    This prevents accidental data loss.

    Multi-tenant scoped.
    """,
    tags=["Backtests"],
)
async def reset_backtest(
    project_id: UUID,
    backtest_id: UUID,
    data: BacktestReset,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(require_tenant),
) -> BacktestResetResponse:
    """
    SCOPED-SAFE reset of backtest data.

    Only deletes BacktestRun and BacktestReportSnapshot records for this
    specific backtest. NEVER touches global data.
    """
    if not data.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set confirm=true to reset backtest data"
        )

    service = get_backtest_service(db)
    return await service.reset_backtest_data(
        tenant_id=tenant.tenant_id,
        project_id=project_id,
        backtest_id=backtest_id,
    )


# =============================================================================
# Start Backtest Execution
# =============================================================================

@router.post(
    "/project-specs/{project_id}/backtests/{backtest_id}/start",
    response_model=BacktestStartResponse,
    summary="Start backtest execution (PHASE 8)",
    description="""
    Start executing backtest runs.

    ## Execution Modes

    - **sequential** (default: true): Runs execute one at a time in-process
    - **parallel** (sequential: false): Runs are queued to Celery workers

    Sequential mode is simpler for debugging. Parallel mode is faster for
    large backtests with available workers.

    ## Run Creation

    For each pending BacktestRun, this creates an actual Run record with:
    - Derived deterministic seed
    - Link back to the BacktestRun
    - Configured scenario and agent settings

    Multi-tenant scoped.
    """,
    tags=["Backtests"],
)
async def start_backtest(
    project_id: UUID,
    backtest_id: UUID,
    data: BacktestStart,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(require_tenant),
) -> BacktestStartResponse:
    """Start executing backtest runs."""
    service = get_backtest_service(db)
    return await service.start_backtest(
        tenant_id=tenant.tenant_id,
        project_id=project_id,
        backtest_id=backtest_id,
        sequential=data.sequential,
    )


# =============================================================================
# Get Backtest Runs
# =============================================================================

@router.get(
    "/project-specs/{project_id}/backtests/{backtest_id}/runs",
    response_model=BacktestRunsResponse,
    summary="Get backtest runs (PHASE 8)",
    description="""
    Get all runs for a backtest with status breakdown.

    Returns:
    - List of BacktestRun records (linking to actual Run records when available)
    - Status counts (pending, running, succeeded, failed, skipped)

    Multi-tenant scoped.
    """,
    tags=["Backtests"],
)
async def get_backtest_runs(
    project_id: UUID,
    backtest_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(require_tenant),
) -> BacktestRunsResponse:
    """Get all runs for a backtest."""
    service = get_backtest_service(db)
    return await service.get_backtest_runs(
        tenant_id=tenant.tenant_id,
        project_id=project_id,
        backtest_id=backtest_id,
    )


# =============================================================================
# Get Backtest Reports
# =============================================================================

@router.get(
    "/project-specs/{project_id}/backtests/{backtest_id}/reports",
    response_model=BacktestReportsResponse,
    summary="Get backtest report snapshots (PHASE 8)",
    description="""
    Get cached Phase 7 report snapshots for a backtest.

    Report snapshots are created by the `snapshot_reports` operation
    after backtest completion.

    Multi-tenant scoped.
    """,
    tags=["Backtests"],
)
async def get_backtest_reports(
    project_id: UUID,
    backtest_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(require_tenant),
) -> BacktestReportsResponse:
    """Get cached report snapshots for a backtest."""
    service = get_backtest_service(db)
    return await service.get_backtest_reports(
        tenant_id=tenant.tenant_id,
        project_id=project_id,
        backtest_id=backtest_id,
    )


# =============================================================================
# Snapshot Reports
# =============================================================================

@router.post(
    "/project-specs/{project_id}/backtests/{backtest_id}/snapshot-reports",
    response_model=BacktestReportsResponse,
    summary="Snapshot Phase 7 reports (PHASE 8)",
    description="""
    Generate and cache Phase 7 reports for all nodes in the backtest.

    For each unique node in the backtest runs, this:
    1. Computes the Phase 7 aggregated report
    2. Caches the result as a BacktestReportSnapshot

    This allows comparing reports across backtest runs without
    re-computing on each view.

    Multi-tenant scoped.
    """,
    tags=["Backtests"],
)
async def snapshot_reports(
    project_id: UUID,
    backtest_id: UUID,
    metric_key: str = Query(
        ...,
        min_length=1,
        description="Metric key for reports"
    ),
    op: str = Query(
        "ge",
        description="Comparison operator (ge, gt, le, lt, eq)"
    ),
    threshold: float = Query(
        0.5,
        description="Threshold value for target probability"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(require_tenant),
) -> BacktestReportsResponse:
    """Generate and cache report snapshots for a backtest."""
    service = get_backtest_service(db)
    return await service.snapshot_reports(
        tenant_id=tenant.tenant_id,
        project_id=project_id,
        backtest_id=backtest_id,
        metric_key=metric_key,
        op=op,
        threshold=threshold,
    )
