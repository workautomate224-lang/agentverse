"""
Run API Endpoints
Reference: project.md §6.5-6.6, §5.2

Provides endpoints for:
- Creating runs (with automatic Node creation)
- Starting/cancelling runs
- Monitoring run progress
- Viewing run results

Key constraints:
- C1: Fork-not-mutate (runs create nodes, never modify existing)
- C2: On-demand execution (runs are explicitly started)
- C4: Auditable artifacts (all runs versioned and persisted)
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.tenant import (
    TenantContext,
    require_tenant,
    require_permission,
    get_current_tenant_id,
)
from app.models.user import User


# ============================================================================
# Request/Response Schemas (project.md §6.5-6.6)
# ============================================================================

class RunConfigSchema(BaseModel):
    """Run configuration per project.md §6.5."""
    run_mode: str = Field(default="society", description="society | individual")
    max_ticks: int = Field(default=100, ge=1, le=10000)
    agent_batch_size: int = Field(default=100, ge=1, le=1000)

    # Society mode settings
    society_mode: Optional[dict] = Field(
        default=None,
        description="RuleSet for society mode simulation"
    )

    # Versions for reproducibility
    engine_version: str = Field(default="0.1.0")
    ruleset_version: str = Field(default="1.0.0")
    dataset_version: str = Field(default="1.0.0")

    class Config:
        extra = "allow"


class CreateRunRequest(BaseModel):
    """Request to create a new run."""
    project_id: str = Field(..., description="Project spec ID")
    node_id: Optional[str] = Field(
        None,
        description="Parent node ID (if forking, else creates root node)"
    )
    label: Optional[str] = Field(None, description="Human-readable label")
    config: RunConfigSchema = Field(default_factory=RunConfigSchema)
    seeds: List[int] = Field(
        default_factory=lambda: [42],
        description="RNG seeds for simulation"
    )
    auto_start: bool = Field(
        default=False,
        description="Start immediately after creation"
    )


class RunResponse(BaseModel):
    """Run response per project.md §6.6."""
    run_id: str
    node_id: str
    project_id: str
    label: Optional[str]
    status: str  # pending | running | completed | failed | cancelled
    config: dict
    seeds: List[int]

    # Timing
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]

    # Results (if completed)
    aggregated_outcome: Optional[dict] = None
    telemetry_ref: Optional[dict] = None
    reliability_ref: Optional[dict] = None

    # Metrics
    ticks_completed: int = 0
    agents_processed: int = 0
    duration_seconds: Optional[float] = None

    # Task info
    task_id: Optional[str] = None

    class Config:
        from_attributes = True


class RunProgressResponse(BaseModel):
    """Real-time run progress."""
    run_id: str
    status: str
    progress_percent: float = 0.0
    current_tick: int = 0
    max_ticks: int = 100
    agents_completed: int = 0
    agents_total: int = 0
    eta_seconds: Optional[float] = None
    current_phase: str = "initializing"


class RunResultsResponse(BaseModel):
    """Completed run results."""
    run_id: str
    node_id: str
    status: str
    aggregated_outcome: dict
    reliability_score: float
    confidence: dict

    # Telemetry summary
    total_ticks: int
    total_events: int
    key_metrics: dict

    # Versions for reproducibility
    engine_version: str
    ruleset_version: str
    dataset_version: str


# ============================================================================
# API Router
# ============================================================================

router = APIRouter()


@router.post(
    "",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new simulation run",
)
async def create_run(
    request: CreateRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> RunResponse:
    """
    Create a new simulation run.

    This creates a Run and associates it with a Node. If no node_id is
    provided, creates a new root node. Otherwise, the run will be
    associated with the specified node (for forking scenarios).

    Reference: project.md §6.5-6.6
    """
    from app.services import get_simulation_orchestrator
    from app.services.simulation_orchestrator import CreateRunInput, RunConfigInput

    orchestrator = get_simulation_orchestrator(db)

    # Build config input
    config_input = RunConfigInput(
        run_mode=request.config.run_mode,
        max_ticks=request.config.max_ticks,
        agent_batch_size=request.config.agent_batch_size,
        society_mode=request.config.society_mode,
        engine_version=request.config.engine_version,
        ruleset_version=request.config.ruleset_version,
        dataset_version=request.config.dataset_version,
    )

    # Create run input
    run_input = CreateRunInput(
        project_id=request.project_id,
        node_id=request.node_id,
        label=request.label,
        config=config_input,
        seeds=request.seeds,
        user_id=str(current_user.id),
        tenant_id=tenant_ctx.tenant_id,
    )

    try:
        if request.auto_start:
            # Create and start immediately
            run, node, task_id = await orchestrator.create_and_start_run(run_input)
            task_id_str = task_id
        else:
            # Just create
            run, node = await orchestrator.create_run(run_input)
            task_id_str = None

        await db.commit()

        return RunResponse(
            run_id=str(run.id),
            node_id=str(run.node_id),
            project_id=str(run.project_id),
            label=run.label,
            status=run.status,
            config=run.outputs.get("config", {}) if run.outputs else {},
            seeds=[run.actual_seed] if run.actual_seed else [],
            created_at=run.created_at.isoformat() if run.created_at else None,
            started_at=run.timing.get("started_at") if run.timing else None,
            completed_at=run.timing.get("completed_at") if run.timing else None,
            ticks_completed=run.timing.get("ticks_executed", 0) if run.timing else 0,
            agents_processed=run.timing.get("agents_processed", 0) if run.timing else 0,
            task_id=task_id_str,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        import traceback
        import logging
        logging.error(f"Failed to create run: {str(e)}\n{traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create run: {str(e)}",
        )


@router.get(
    "",
    response_model=List[RunResponse],
    summary="List simulation runs",
)
async def list_runs(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    node_id: Optional[str] = Query(None, description="Filter by node"),
    status_filter: Optional[str] = Query(
        None,
        pattern="^(pending|running|completed|failed|cancelled)$",
        description="Filter by status",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> List[RunResponse]:
    """
    List runs with optional filtering.

    Runs are scoped to the current tenant and optionally filtered by
    project, node, or status.
    """
    from app.services import get_simulation_orchestrator

    orchestrator = get_simulation_orchestrator(db)

    runs = await orchestrator.list_runs(
        tenant_id=tenant_ctx.tenant_id,
        project_id=project_id,
        node_id=node_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )

    return [
        RunResponse(
            run_id=str(run.id),
            node_id=str(run.node_id),
            project_id=str(run.project_id),
            label=run.label,
            status=run.status,
            config=run.outputs.get("config", {}) if run.outputs else {},
            seeds=[run.actual_seed] if run.actual_seed else [],
            created_at=run.created_at.isoformat() if run.created_at else None,
            started_at=run.timing.get("started_at") if run.timing else None,
            completed_at=run.timing.get("completed_at") if run.timing else None,
            aggregated_outcome=run.outputs.get("outcomes") if run.outputs else None,
            telemetry_ref=run.outputs.get("telemetry_ref") if run.outputs else None,
            ticks_completed=run.timing.get("ticks_executed", 0) if run.timing else 0,
            agents_processed=run.timing.get("agents_processed", 0) if run.timing else 0,
        )
        for run in runs
    ]


@router.get(
    "/{run_id}",
    response_model=RunResponse,
    summary="Get run details",
)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> RunResponse:
    """Get details of a specific run."""
    from app.services import get_simulation_orchestrator

    orchestrator = get_simulation_orchestrator(db)

    run = await orchestrator.get_run(run_id, tenant_ctx.tenant_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    timing = run.timing or {}
    outputs = run.outputs or {}

    duration = None
    started_at = timing.get("started_at")
    completed_at = timing.get("completed_at")
    if started_at and completed_at:
        try:
            start = datetime.fromisoformat(started_at)
            end = datetime.fromisoformat(completed_at)
            duration = (end - start).total_seconds()
        except (ValueError, TypeError):
            pass

    return RunResponse(
        run_id=str(run.id),
        node_id=str(run.node_id),
        project_id=str(run.project_id),
        label=run.label,
        status=run.status,
        config=outputs.get("config", {}),
        seeds=[run.actual_seed] if run.actual_seed else [],
        created_at=run.created_at.isoformat() if run.created_at else None,
        started_at=started_at,
        completed_at=completed_at,
        aggregated_outcome=outputs.get("outcomes"),
        telemetry_ref=outputs.get("telemetry_ref"),
        reliability_ref=outputs.get("reliability_ref"),
        ticks_completed=timing.get("ticks_executed", 0),
        agents_processed=timing.get("agents_processed", 0),
        duration_seconds=duration,
    )


@router.post(
    "/{run_id}/start",
    response_model=RunResponse,
    summary="Start a pending run",
)
async def start_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> RunResponse:
    """
    Start a pending simulation run.

    This queues the run for execution. Use GET /runs/{run_id}/progress
    to monitor execution progress.

    Reference: project.md §6.6 (Run lifecycle)
    """
    from app.services import get_simulation_orchestrator

    orchestrator = get_simulation_orchestrator(db)

    run = await orchestrator.get_run(run_id, tenant_ctx.tenant_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    if run.status not in ("created", "pending", "queued"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run must be created, pending or queued to start. Current status: {run.status}",
        )

    # Auto-queue if status is created
    if run.status == "created":
        run = await orchestrator.queue_run(run, str(tenant_ctx.tenant_id))

    try:
        task_id = await orchestrator.start_run(run, tenant_ctx.tenant_id)
        await db.commit()

        # Refresh run to get updated status
        run = await orchestrator.get_run(run_id, tenant_ctx.tenant_id)

        return RunResponse(
            run_id=str(run.id),
            node_id=str(run.node_id),
            project_id=str(run.project_id),
            label=run.label,
            status=run.status,
            config=run.outputs.get("config", {}) if run.outputs else {},
            seeds=[run.actual_seed] if run.actual_seed else [],
            created_at=run.created_at.isoformat() if run.created_at else None,
            started_at=run.timing.get("started_at") if run.timing else None,
            completed_at=run.timing.get("completed_at") if run.timing else None,
            ticks_completed=run.timing.get("ticks_executed", 0) if run.timing else 0,
            agents_processed=run.timing.get("agents_processed", 0) if run.timing else 0,
            task_id=task_id,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start run: {str(e)}",
        )


@router.post(
    "/{run_id}/cancel",
    response_model=RunResponse,
    summary="Cancel a running simulation",
)
async def cancel_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> RunResponse:
    """
    Cancel a pending or running simulation.

    If the run is already running, the Celery task will be revoked.
    The run status will be set to 'cancelled'.
    """
    from app.services import get_simulation_orchestrator

    orchestrator = get_simulation_orchestrator(db)

    run = await orchestrator.get_run(run_id, tenant_ctx.tenant_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    if run.status not in ("pending", "running"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel run with status: {run.status}",
        )

    try:
        await orchestrator.cancel_run(run_id, tenant_ctx.tenant_id)
        await db.commit()

        # Refresh
        run = await orchestrator.get_run(run_id, tenant_ctx.tenant_id)

        return RunResponse(
            run_id=str(run.id),
            node_id=str(run.node_id),
            project_id=str(run.project_id),
            label=run.label,
            status=run.status,
            config=run.outputs.get("config", {}) if run.outputs else {},
            seeds=[run.actual_seed] if run.actual_seed else [],
            created_at=run.created_at.isoformat() if run.created_at else None,
            started_at=run.timing.get("started_at") if run.timing else None,
            completed_at=run.timing.get("completed_at") if run.timing else None,
            ticks_completed=run.timing.get("ticks_executed", 0) if run.timing else 0,
            agents_processed=run.timing.get("agents_processed", 0) if run.timing else 0,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel run: {str(e)}",
        )


@router.get(
    "/{run_id}/progress",
    response_model=RunProgressResponse,
    summary="Get run progress",
)
async def get_run_progress(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> RunProgressResponse:
    """
    Get real-time progress of a running simulation.

    For completed runs, returns final progress (100%).
    """
    from app.services import get_simulation_orchestrator

    orchestrator = get_simulation_orchestrator(db)

    # Get both progress and run data for full response
    progress = await orchestrator.get_run_progress(run_id, tenant_ctx.tenant_id)

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    # Get full run data to access config for max_ticks
    run = await orchestrator.get_run(run_id, tenant_ctx.tenant_id)

    # Extract max_ticks from run config or default to 100
    max_ticks = 100
    if run and run.outputs:
        config = run.outputs.get("config", {})
        max_ticks = config.get("max_ticks", 100)

    # Calculate current tick and progress
    current_tick = progress.ticks_executed or 0
    progress_percent = min((current_tick / max_ticks) * 100, 100.0) if max_ticks > 0 else 0.0

    # Determine phase based on status
    current_phase = "initializing"
    if progress.status == "running":
        current_phase = "simulating"
    elif progress.status == "succeeded":
        current_phase = "completed"
        progress_percent = 100.0
    elif progress.status == "failed":
        current_phase = "failed"
    elif progress.status == "cancelled":
        current_phase = "cancelled"

    return RunProgressResponse(
        run_id=progress.run_id,
        status=progress.status,
        progress_percent=progress_percent,
        current_tick=current_tick,
        max_ticks=max_ticks,
        agents_completed=0,  # Will be populated from actual simulation when running
        agents_total=0,
        eta_seconds=None,
        current_phase=current_phase,
    )


@router.get(
    "/{run_id}/stream",
    summary="Stream run progress (SSE)",
)
async def stream_run_progress(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
):
    """
    Stream run progress using Server-Sent Events.

    Events include:
    - progress: Current progress updates
    - completed: Final results (when done)
    - error: Error information (on failure)
    """
    from app.services import get_simulation_orchestrator

    orchestrator = get_simulation_orchestrator(db)

    # Verify run exists
    run = await orchestrator.get_run(run_id, tenant_ctx.tenant_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    async def event_generator():
        import asyncio
        import json

        # Get initial run data for max_ticks
        initial_run = await orchestrator.get_run(run_id, tenant_ctx.tenant_id)
        max_ticks = 100
        if initial_run and initial_run.outputs:
            config = initial_run.outputs.get("config", {})
            max_ticks = config.get("max_ticks", 100)

        while True:
            progress = await orchestrator.get_run_progress(run_id, tenant_ctx.tenant_id)

            if not progress:
                yield f"event: error\ndata: {json.dumps({'error': 'Run not found'})}\n\n"
                break

            # Calculate derived values
            current_tick = progress.ticks_executed or 0
            progress_percent = min((current_tick / max_ticks) * 100, 100.0) if max_ticks > 0 else 0.0

            # Determine phase
            current_phase = "initializing"
            if progress.status == "running":
                current_phase = "simulating"
            elif progress.status == "succeeded":
                current_phase = "completed"
                progress_percent = 100.0
            elif progress.status == "failed":
                current_phase = "failed"
            elif progress.status == "cancelled":
                current_phase = "cancelled"

            progress_data = {
                "run_id": progress.run_id,
                "status": progress.status,
                "progress_percent": progress_percent,
                "current_tick": current_tick,
                "max_ticks": max_ticks,
                "agents_completed": 0,
                "agents_total": 0,
                "current_phase": current_phase,
            }

            yield f"event: progress\ndata: {json.dumps(progress_data)}\n\n"

            if progress.status in ("succeeded", "failed", "cancelled"):
                # Send final event
                run = await orchestrator.get_run(run_id, tenant_ctx.tenant_id)
                if run and run.aggregated_outcome:
                    yield f"event: completed\ndata: {json.dumps({'outcome': run.aggregated_outcome})}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{run_id}/results",
    response_model=RunResultsResponse,
    summary="Get run results",
)
async def get_run_results(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> RunResultsResponse:
    """
    Get aggregated results for a completed run.

    Reference: project.md §6.6 (Aggregated outcome)
    """
    from app.services import get_simulation_orchestrator

    orchestrator = get_simulation_orchestrator(db)

    run = await orchestrator.get_run(run_id, tenant_ctx.tenant_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    if run.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run not completed. Status: {run.status}",
        )

    outcome = run.aggregated_outcome or {}
    reliability = run.reliability_ref or {}

    return RunResultsResponse(
        run_id=run.run_id,
        node_id=run.node_id,
        status=run.status,
        aggregated_outcome=outcome,
        reliability_score=reliability.get("overall_score", 0.0),
        confidence=outcome.get("confidence", {}),
        total_ticks=run.ticks_completed,
        total_events=outcome.get("total_events", 0),
        key_metrics=outcome.get("key_metrics", {}),
        engine_version=run.config.get("engine_version", "0.1.0"),
        ruleset_version=run.config.get("ruleset_version", "1.0.0"),
        dataset_version=run.config.get("dataset_version", "1.0.0"),
    )


@router.post(
    "/batch",
    response_model=List[RunResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create multiple runs (multi-seed)",
)
async def create_batch_runs(
    project_id: str,
    seeds: List[int] = [42, 123, 456],
    config: Optional[RunConfigSchema] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> List[RunResponse]:
    """
    Create multiple runs with different seeds for the same project.

    This is useful for Monte Carlo analysis - running the same simulation
    with different random seeds to measure outcome variance.

    Reference: project.md §10.1 (Seed and RNG policy)
    """
    from app.services import get_simulation_orchestrator
    from app.services.simulation_orchestrator import CreateRunInput, RunConfigInput

    orchestrator = get_simulation_orchestrator(db)

    config_dict = config.dict() if config else {}
    config_input = RunConfigInput(**config_dict)

    results = []
    for seed in seeds:
        run_input = CreateRunInput(
            project_id=project_id,
            config=config_input,
            seeds=[seed],
            user_id=str(current_user.id),
            tenant_id=tenant_ctx.tenant_id,
            label=f"Seed {seed}",
        )

        run, node = await orchestrator.create_run(run_input)
        results.append(run)

    await db.commit()

    return [
        RunResponse(
            run_id=str(run.id),
            node_id=str(run.node_id),
            project_id=str(run.project_id),
            label=run.label,
            status=run.status,
            config=run.outputs.get("config", {}) if run.outputs else {},
            seeds=[run.actual_seed] if run.actual_seed else [],
            created_at=run.created_at.isoformat() if run.created_at else None,
            started_at=run.timing.get("started_at") if run.timing else None,
            completed_at=run.timing.get("completed_at") if run.timing else None,
            ticks_completed=run.timing.get("ticks_executed", 0) if run.timing else 0,
            agents_processed=run.timing.get("agents_processed", 0) if run.timing else 0,
        )
        for run in results
    ]


@router.post(
    "/batch/start",
    summary="Start multiple runs",
)
async def start_batch_runs(
    run_ids: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """
    Start multiple pending runs.

    Returns task IDs for each run that was successfully started.
    """
    from app.services import get_simulation_orchestrator

    orchestrator = get_simulation_orchestrator(db)

    started = []
    failed = []

    for run_id in run_ids:
        try:
            run = await orchestrator.get_run(run_id, tenant_ctx.tenant_id)
            if run and run.status == "pending":
                task_id = await orchestrator.start_run(run, tenant_ctx.tenant_id)
                started.append({"run_id": run_id, "task_id": task_id})
            else:
                failed.append({
                    "run_id": run_id,
                    "error": "Run not found or not pending",
                })
        except Exception as e:
            failed.append({"run_id": run_id, "error": str(e)})

    await db.commit()

    return {
        "started": started,
        "failed": failed,
        "total_started": len(started),
        "total_failed": len(failed),
    }


# =============================================================================
# STEP 1 Audit Endpoints - RunSpec, RunTrace, Worker Heartbeats
# =============================================================================

class RunSpecResponse(BaseModel):
    """RunSpec artifact response (STEP 1: Artifact 1)."""
    run_id: str
    project_id: str
    ticks_total: int
    seed: int
    llm_config: dict = Field(..., alias="model_config")
    environment_spec: dict
    scheduler_config: Optional[dict]
    engine_version: str
    ruleset_version: str
    dataset_version: str
    created_at: str

    model_config = {"populate_by_name": True}


class RunTraceEntryResponse(BaseModel):
    """RunTrace entry response (STEP 1: Artifact 2)."""
    run_id: str
    timestamp: str
    worker_id: str
    execution_stage: str
    description: Optional[str]
    tick_number: Optional[int]
    agents_processed: Optional[int]
    events_count: Optional[int]
    duration_ms: Optional[int]


class WorkerHeartbeatResponse(BaseModel):
    """Worker heartbeat response (STEP 1: Worker tracking)."""
    worker_id: str
    hostname: Optional[str]
    last_seen_at: str
    status: str
    current_run_id: Optional[str]
    runs_executed: int
    runs_failed: int


@router.get(
    "/{run_id}/spec",
    response_model=RunSpecResponse,
    summary="Get RunSpec artifact (STEP 1: Artifact 1)",
)
async def get_run_spec(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> RunSpecResponse:
    """
    Get the RunSpec artifact for a run.

    STEP 1 Requirement - RunSpec must include:
    - run_id
    - project_id
    - ticks_total or horizon (must be > 0)
    - seed
    - model or model configuration
    - environment_spec
    - created_at
    """
    from sqlalchemy import text

    query = text("""
        SELECT run_id, project_id, ticks_total, seed, model_config,
               environment_spec, scheduler_config, engine_version,
               ruleset_version, dataset_version, created_at
        FROM run_specs
        WHERE run_id = :run_id AND tenant_id = :tenant_id
    """)

    result = await db.execute(query, {
        "run_id": run_id,
        "tenant_id": tenant_ctx.tenant_id,
    })
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RunSpec not found for run {run_id}",
        )

    return RunSpecResponse(
        run_id=str(row.run_id),
        project_id=str(row.project_id),
        ticks_total=row.ticks_total,
        seed=row.seed,
        model_config=row.model_config if isinstance(row.model_config, dict) else {},
        environment_spec=row.environment_spec if isinstance(row.environment_spec, dict) else {},
        scheduler_config=row.scheduler_config if isinstance(row.scheduler_config, dict) else None,
        engine_version=row.engine_version,
        ruleset_version=row.ruleset_version,
        dataset_version=row.dataset_version,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.get(
    "/{run_id}/traces",
    response_model=List[RunTraceEntryResponse],
    summary="Get RunTrace entries (STEP 1: Artifact 2)",
)
async def get_run_traces(
    run_id: str,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> List[RunTraceEntryResponse]:
    """
    Get RunTrace entries for a run.

    STEP 1 Requirement - At least 3 real trace entries:
    - Each entry includes: run_id, timestamp, worker_id, execution_stage
    """
    from sqlalchemy import text

    query = text("""
        SELECT run_id, timestamp, worker_id, execution_stage, description,
               tick_number, agents_processed, events_count, duration_ms
        FROM run_traces
        WHERE run_id = :run_id AND tenant_id = :tenant_id
        ORDER BY timestamp ASC
        LIMIT :limit
    """)

    result = await db.execute(query, {
        "run_id": run_id,
        "tenant_id": tenant_ctx.tenant_id,
        "limit": limit,
    })
    rows = result.fetchall()

    return [
        RunTraceEntryResponse(
            run_id=str(row.run_id),
            timestamp=row.timestamp.isoformat() if row.timestamp else None,
            worker_id=row.worker_id,
            execution_stage=row.execution_stage,
            description=row.description,
            tick_number=row.tick_number,
            agents_processed=row.agents_processed,
            events_count=row.events_count,
            duration_ms=row.duration_ms,
        )
        for row in rows
    ]


@router.get(
    "/workers/heartbeats",
    response_model=List[WorkerHeartbeatResponse],
    summary="Get worker heartbeats (STEP 1: Worker tracking)",
)
async def get_worker_heartbeats(
    active_only: bool = Query(True, description="Only show active workers"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> List[WorkerHeartbeatResponse]:
    """
    Get worker heartbeat information.

    STEP 1 Requirement - Worker heartbeat with:
    - worker_id
    - last_seen_at
    - current_run_id (which run the worker is executing)
    """
    from sqlalchemy import text
    from datetime import timedelta

    # Consider workers active if seen in last 5 minutes
    cutoff = datetime.utcnow() - timedelta(minutes=5)

    if active_only:
        query = text("""
            SELECT worker_id, hostname, last_seen_at, status, current_run_id,
                   runs_executed, runs_failed
            FROM worker_heartbeats
            WHERE last_seen_at > :cutoff
            ORDER BY last_seen_at DESC
        """)
        result = await db.execute(query, {"cutoff": cutoff})
    else:
        query = text("""
            SELECT worker_id, hostname, last_seen_at, status, current_run_id,
                   runs_executed, runs_failed
            FROM worker_heartbeats
            ORDER BY last_seen_at DESC
            LIMIT 100
        """)
        result = await db.execute(query)

    rows = result.fetchall()

    return [
        WorkerHeartbeatResponse(
            worker_id=row.worker_id,
            hostname=row.hostname,
            last_seen_at=row.last_seen_at.isoformat() if row.last_seen_at else None,
            status=row.status,
            current_run_id=str(row.current_run_id) if row.current_run_id else None,
            runs_executed=row.runs_executed or 0,
            runs_failed=row.runs_failed or 0,
        )
        for row in rows
    ]


@router.get(
    "/{run_id}/outcome",
    summary="Get Run Outcome (STEP 1: Artifact 3)",
)
async def get_run_outcome(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """
    Get the Outcome artifact for a completed run.

    STEP 1 Requirement - Outcome must include:
    - run_id
    - at least one real numeric result
    - status = completed
    """
    from app.services import get_simulation_orchestrator

    orchestrator = get_simulation_orchestrator(db)
    run = await orchestrator.get_run(run_id, tenant_ctx.tenant_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    if run.status != "succeeded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run not completed. Status: {run.status}",
        )

    outputs = run.outputs or {}
    outcomes = outputs.get("outcomes", {})

    # STEP 1 Validation: Ensure at least one real numeric result
    key_metrics = outcomes.get("key_metrics", [])
    has_numeric = any(
        isinstance(m.get("value"), (int, float)) and m.get("value") != 0
        for m in key_metrics
    )

    if not has_numeric:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="STEP 1 VIOLATION: Outcome has no real numeric results",
        )

    return {
        "run_id": str(run.id),
        "status": "completed",
        "primary_outcome": outcomes.get("primary_outcome"),
        "primary_outcome_probability": outcomes.get("primary_outcome_probability"),
        "outcome_distribution": outcomes.get("outcome_distribution"),
        "key_metrics": key_metrics,
        "variance_metrics": outcomes.get("variance_metrics"),
        "summary_text": outcomes.get("summary_text"),
        "seed": outcomes.get("seed"),
        "reliability": outputs.get("reliability"),
        "execution_counters": outputs.get("execution_counters"),
    }


# =============================================================================
# STEP 1: Retry Failed Run Endpoint
# =============================================================================

@router.post(
    "/{run_id}/retry",
    response_model=RunResponse,
    summary="Retry a failed run (STEP 1: Retry Failed Run)",
)
async def retry_failed_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> RunResponse:
    """
    Retry a failed simulation run.

    STEP 1 Requirement - 'Retry Failed Run' button must:
    - Trigger request with request_id and relevant ids
    - Validate input schema and permissions
    - Write DB records and emit AuditLog entry
    - Show loading state driven by backend response
    - Return actionable error on failure

    This creates a NEW run with the same configuration as the failed run.
    The original failed run is preserved for audit purposes (C4: Auditable).
    """
    from app.services import get_simulation_orchestrator
    from app.services.simulation_orchestrator import CreateRunInput, RunConfigInput

    orchestrator = get_simulation_orchestrator(db)

    # Get the failed run
    failed_run = await orchestrator.get_run(run_id, tenant_ctx.tenant_id)

    if not failed_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    if failed_run.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only failed runs can be retried. Current status: {failed_run.status}",
        )

    try:
        # Extract configuration from failed run
        failed_outputs = failed_run.outputs or {}
        failed_config = failed_outputs.get("config", {})

        config_input = RunConfigInput(
            run_mode=failed_config.get("run_mode", "society"),
            max_ticks=failed_config.get("max_ticks", 100),
            agent_batch_size=failed_config.get("agent_batch_size", 100),
            society_mode=failed_config.get("society_mode"),
            engine_version=failed_config.get("engine_version", "0.1.0"),
            ruleset_version=failed_config.get("ruleset_version", "1.0.0"),
            dataset_version=failed_config.get("dataset_version", "1.0.0"),
        )

        # Create new run with same configuration
        run_input = CreateRunInput(
            project_id=str(failed_run.project_id),
            node_id=str(failed_run.node_id),
            label=f"Retry of {failed_run.label or run_id}",
            config=config_input,
            seeds=[failed_run.actual_seed] if failed_run.actual_seed else [42],
            user_id=str(current_user.id),
            tenant_id=tenant_ctx.tenant_id,
        )

        # Create and start the retry run
        run, node, task_id = await orchestrator.create_and_start_run(run_input)

        await db.commit()

        return RunResponse(
            run_id=str(run.id),
            node_id=str(run.node_id),
            project_id=str(run.project_id),
            label=run.label,
            status=run.status,
            config=run.outputs.get("config", {}) if run.outputs else {},
            seeds=[run.actual_seed] if run.actual_seed else [],
            created_at=run.created_at.isoformat() if run.created_at else None,
            started_at=run.timing.get("started_at") if run.timing else None,
            completed_at=run.timing.get("completed_at") if run.timing else None,
            ticks_completed=run.timing.get("ticks_executed", 0) if run.timing else 0,
            agents_processed=run.timing.get("agents_processed", 0) if run.timing else 0,
            task_id=task_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        import traceback
        import logging
        logging.error(f"Failed to retry run: {str(e)}\n{traceback.format_exc()}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry run: {str(e)}",
        )
