"""
Telemetry Query API Endpoints
Reference: project.md §6.8, C3

Provides endpoints for:
- Querying telemetry data (read-only)
- Streaming telemetry for replay
- Searching events by type
- Exporting telemetry

Key constraints:
- C3: Replay is READ-ONLY - these endpoints NEVER trigger simulations
- C4: Auditable artifacts - telemetry is versioned and immutable
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.tenant import (
    TenantContext,
    require_tenant,
)
from app.models.user import User


# ============================================================================
# Response Schemas (project.md §6.8)
# ============================================================================

class AgentStateSnapshot(BaseModel):
    """Snapshot of an agent's state at a tick."""
    agent_id: str
    tick: int
    state: dict
    beliefs: Optional[dict] = None
    last_action: Optional[str] = None
    metrics: Optional[dict] = None


class KeyframeResponse(BaseModel):
    """Full state keyframe per project.md §6.8."""
    tick: int
    timestamp: str
    agent_states: dict  # agent_id -> state
    environment_state: Optional[dict] = None
    metrics: Optional[dict] = None
    event_count: int = 0


class DeltaResponse(BaseModel):
    """State delta between keyframes."""
    tick: int
    agent_updates: List[dict]
    events_triggered: List[str]
    metrics: dict


class EventResponse(BaseModel):
    """Simulation event."""
    event_id: str
    tick: int
    timestamp: str
    event_type: str
    agent_id: Optional[str]
    data: dict
    metadata: Optional[dict] = None


class TelemetrySliceResponse(BaseModel):
    """A slice of telemetry data for a tick range."""
    run_id: str
    start_tick: int
    end_tick: int
    keyframes: List[KeyframeResponse]
    deltas: List[DeltaResponse]
    events: List[EventResponse]
    total_events: int


class TelemetryIndexResponse(BaseModel):
    """Telemetry index for fast seeking."""
    run_id: str
    total_ticks: int
    keyframe_ticks: List[int]
    event_types: List[str]
    agent_ids: List[str]
    storage_ref: dict


class TelemetrySummaryResponse(BaseModel):
    """Summary statistics for telemetry."""
    run_id: str
    total_ticks: int
    total_events: int
    total_agents: int
    event_type_counts: dict
    key_metrics: dict
    duration_seconds: float


class TelemetryExportRequest(BaseModel):
    """Request to export telemetry."""
    format: str = Field(default="json", pattern="^(json|csv|parquet)$")
    tick_range: Optional[tuple] = None
    event_types: Optional[List[str]] = None
    agent_ids: Optional[List[str]] = None
    include_deltas: bool = True


# ============================================================================
# API Router
# ============================================================================

router = APIRouter()


@router.get(
    "/{run_id}",
    response_model=TelemetryIndexResponse,
    summary="Get telemetry index",
)
async def get_telemetry_index(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> TelemetryIndexResponse:
    """
    Get telemetry index for a run.

    The index provides metadata for efficient navigation:
    - Total ticks and events
    - Keyframe tick numbers (for seeking)
    - Available event types
    - Agent IDs

    This is READ-ONLY per C3.
    """
    from app.services import get_telemetry_service

    telemetry_service = get_telemetry_service()

    index = await telemetry_service.get_telemetry_index(
        run_id=run_id,
        tenant_id=tenant_ctx.tenant_id,
    )

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Telemetry not found for run {run_id}",
        )

    return TelemetryIndexResponse(
        run_id=run_id,
        total_ticks=index.total_ticks,
        keyframe_ticks=index.keyframe_ticks,
        event_types=index.event_types,
        agent_ids=index.agent_ids,
        storage_ref=index.storage_ref,
    )


@router.get(
    "/{run_id}/slice",
    response_model=TelemetrySliceResponse,
    summary="Get telemetry slice",
)
async def get_telemetry_slice(
    run_id: str,
    start_tick: int = Query(0, ge=0),
    end_tick: int = Query(100, ge=0),
    include_events: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> TelemetrySliceResponse:
    """
    Get a slice of telemetry data for a tick range.

    This is the primary endpoint for replay functionality.
    Returns keyframes, deltas, and events for the specified range.

    This is READ-ONLY per C3 - never triggers simulation.
    """
    from app.services import get_telemetry_service

    telemetry_service = get_telemetry_service()

    slice_data = await telemetry_service.get_telemetry_slice(
        run_id=run_id,
        tenant_id=tenant_ctx.tenant_id,
        start_tick=start_tick,
        end_tick=end_tick,
        include_events=include_events,
    )

    if not slice_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Telemetry not found for run {run_id}",
        )

    keyframes = [
        KeyframeResponse(
            tick=kf.tick,
            timestamp=kf.timestamp,
            agent_states=kf.agent_states,
            environment_state=kf.environment_state,
            metrics=kf.metrics,
            event_count=len(kf.agent_states),
        )
        for kf in slice_data.keyframes
    ]

    deltas = [
        DeltaResponse(
            tick=d.tick,
            agent_updates=d.agent_updates,
            events_triggered=d.events_triggered,
            metrics=d.metrics,
        )
        for d in slice_data.deltas
    ]

    events = [
        EventResponse(
            event_id=e.get("event_id", f"{run_id}_{e.get('tick', 0)}_{i}"),
            tick=e.get("tick", 0),
            timestamp=e.get("timestamp", ""),
            event_type=e.get("event_type", "unknown"),
            agent_id=e.get("agent_id"),
            data=e.get("data", {}),
            metadata=e.get("metadata"),
        )
        for i, e in enumerate(slice_data.events)
    ]

    return TelemetrySliceResponse(
        run_id=run_id,
        start_tick=start_tick,
        end_tick=end_tick,
        keyframes=keyframes,
        deltas=deltas,
        events=events,
        total_events=len(events),
    )


@router.get(
    "/{run_id}/keyframe/{tick}",
    response_model=KeyframeResponse,
    summary="Get keyframe at tick",
)
async def get_keyframe_at_tick(
    run_id: str,
    tick: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> KeyframeResponse:
    """
    Get the nearest keyframe at or before a specific tick.

    Use this for seeking to a specific point in the simulation.
    The response includes the full state at that keyframe.

    This is READ-ONLY per C3.
    """
    from app.services import get_telemetry_service

    telemetry_service = get_telemetry_service()

    keyframe = await telemetry_service.get_keyframe_at_tick_by_run(
        run_id=run_id,
        tick=tick,
        tenant_id=tenant_ctx.tenant_id,
    )

    if not keyframe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Keyframe not found at tick {tick} for run {run_id}",
        )

    return KeyframeResponse(
        tick=keyframe.tick,
        timestamp=keyframe.timestamp,
        agent_states=keyframe.agent_states,
        environment_state=keyframe.environment_state,
        metrics=keyframe.metrics,
        event_count=len(keyframe.agent_states),
    )


@router.get(
    "/{run_id}/agent/{agent_id}",
    response_model=List[AgentStateSnapshot],
    summary="Get agent history",
)
async def get_agent_history(
    run_id: str,
    agent_id: str,
    start_tick: int = Query(0, ge=0),
    end_tick: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> List[AgentStateSnapshot]:
    """
    Get state history for a specific agent.

    Returns the agent's state snapshots across the specified tick range.
    Useful for analyzing individual agent behavior.

    This is READ-ONLY per C3.
    """
    from app.services import get_telemetry_service

    telemetry_service = get_telemetry_service()

    history = await telemetry_service.get_agent_history(
        run_id=run_id,
        agent_id=agent_id,
        tenant_id=tenant_ctx.tenant_id,
        start_tick=start_tick,
        end_tick=end_tick,
    )

    return [
        AgentStateSnapshot(
            agent_id=agent_id,
            tick=state.get("tick", 0),
            state=state.get("state", {}),
            beliefs=state.get("beliefs"),
            last_action=state.get("last_action"),
            metrics=state.get("metrics"),
        )
        for state in history
    ]


@router.get(
    "/{run_id}/events",
    response_model=List[EventResponse],
    summary="Search events",
)
async def search_events(
    run_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    start_tick: int = Query(0, ge=0),
    end_tick: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> List[EventResponse]:
    """
    Search events within telemetry.

    Filter by event type, agent, or tick range.
    Returns matching events up to the specified limit.

    This is READ-ONLY per C3.
    """
    from app.services import get_telemetry_service

    telemetry_service = get_telemetry_service()

    events = await telemetry_service.get_events_by_type(
        run_id=run_id,
        tenant_id=tenant_ctx.tenant_id,
        event_type=event_type,
        agent_id=agent_id,
        start_tick=start_tick,
        end_tick=end_tick,
        limit=limit,
    )

    return [
        EventResponse(
            event_id=e.get("event_id", f"{run_id}_{e.get('tick', 0)}_{i}"),
            tick=e.get("tick", 0),
            timestamp=e.get("timestamp", ""),
            event_type=e.get("event_type", "unknown"),
            agent_id=e.get("agent_id"),
            data=e.get("data", {}),
            metadata=e.get("metadata"),
        )
        for i, e in enumerate(events)
    ]


@router.get(
    "/{run_id}/summary",
    response_model=TelemetrySummaryResponse,
    summary="Get telemetry summary",
)
async def get_telemetry_summary(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> TelemetrySummaryResponse:
    """
    Get summary statistics for telemetry.

    Returns aggregate metrics without loading full telemetry.
    Useful for dashboards and quick overviews.

    This is READ-ONLY per C3.
    """
    from app.services import get_telemetry_service

    telemetry_service = get_telemetry_service()

    summary = await telemetry_service.get_telemetry_summary(
        run_id=run_id,
        tenant_id=tenant_ctx.tenant_id,
    )

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Telemetry not found for run {run_id}",
        )

    return TelemetrySummaryResponse(
        run_id=run_id,
        total_ticks=summary.get("total_ticks", 0),
        total_events=summary.get("total_events", 0),
        total_agents=summary.get("total_agents", 0),
        event_type_counts=summary.get("event_type_counts", {}),
        key_metrics=summary.get("key_metrics", {}),
        duration_seconds=summary.get("duration_seconds", 0.0),
    )


@router.get(
    "/{run_id}/stream",
    summary="Stream telemetry (SSE)",
)
async def stream_telemetry(
    run_id: str,
    start_tick: int = Query(0, ge=0),
    speed: float = Query(1.0, ge=0.1, le=10.0, description="Playback speed"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
):
    """
    Stream telemetry as Server-Sent Events for replay.

    This provides real-time playback of historical simulation data.
    The speed parameter controls playback rate (1.0 = real-time).

    This is READ-ONLY per C3 - streams historical data only.
    """
    from app.services import get_telemetry_service

    telemetry_service = get_telemetry_service()

    # Verify run exists
    index = await telemetry_service.get_telemetry_index(
        run_id=run_id,
        tenant_id=tenant_ctx.tenant_id,
    )

    if not index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Telemetry not found for run {run_id}",
        )

    async def event_generator():
        import asyncio
        import json

        tick = start_tick
        tick_interval = 1.0 / speed  # Seconds per tick

        while tick <= index.total_ticks:
            # Get slice for this tick
            slice_data = await telemetry_service.get_telemetry_slice(
                run_id=run_id,
                tenant_id=tenant_ctx.tenant_id,
                start_tick=tick,
                end_tick=tick + 1,
                include_events=True,
            )

            if slice_data:
                tick_data = {
                    "tick": tick,
                    "total_ticks": index.total_ticks,
                    "keyframes": [
                        {
                            "tick": kf.tick,
                            "agent_count": len(kf.agent_states),
                            "metrics": kf.metrics,
                        }
                        for kf in slice_data.keyframes
                    ],
                    "events": [
                        {
                            "event_type": e.get("event_type"),
                            "agent_id": e.get("agent_id"),
                            "data": e.get("data", {}),
                        }
                        for e in slice_data.events
                    ],
                }

                yield f"event: tick\ndata: {json.dumps(tick_data)}\n\n"

            tick += 1
            await asyncio.sleep(tick_interval)

        # Send completion event
        yield f"event: complete\ndata: {json.dumps({'final_tick': tick - 1})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/{run_id}/export",
    summary="Export telemetry",
)
async def export_telemetry(
    run_id: str,
    request: TelemetryExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
):
    """
    Export telemetry data in various formats.

    Supported formats:
    - json: Full structured data
    - csv: Flattened event log
    - parquet: Columnar format for analytics

    This is READ-ONLY per C3.
    """
    from app.services import get_telemetry_service

    telemetry_service = get_telemetry_service()

    # Get telemetry data
    telemetry = await telemetry_service.get_telemetry_by_run(
        run_id=run_id,
        tenant_id=tenant_ctx.tenant_id,
    )

    if not telemetry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Telemetry not found for run {run_id}",
        )

    if request.format == "json":
        import json
        from fastapi.responses import Response

        export_data = {
            "run_id": run_id,
            "version": telemetry.version.to_dict() if hasattr(telemetry, 'version') else {},
            "index": {
                "total_ticks": telemetry.index.total_ticks,
                "keyframe_ticks": telemetry.index.keyframe_ticks,
                "event_types": telemetry.index.event_types,
            },
            "keyframes": [
                {
                    "tick": kf.tick,
                    "timestamp": kf.timestamp,
                    "agent_states": kf.agent_states,
                    "metrics": kf.metrics,
                }
                for kf in telemetry.keyframes
            ],
            "events": telemetry.events,
        }

        return Response(
            content=json.dumps(export_data, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="telemetry_{run_id}.json"'
            },
        )

    elif request.format == "csv":
        import csv
        import io
        from fastapi.responses import Response

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "tick", "timestamp", "event_type", "agent_id", "data"
        ])

        # Events
        for event in telemetry.events:
            writer.writerow([
                event.get("tick", ""),
                event.get("timestamp", ""),
                event.get("event_type", ""),
                event.get("agent_id", ""),
                json.dumps(event.get("data", {})),
            ])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="telemetry_{run_id}.csv"'
            },
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export format '{request.format}' not yet implemented",
        )


@router.get(
    "/{run_id}/metrics",
    summary="Get aggregated metrics",
)
async def get_aggregated_metrics(
    run_id: str,
    metric_names: Optional[List[str]] = Query(None),
    aggregation: str = Query("mean", pattern="^(mean|sum|min|max|std)$"),
    group_by_tick: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """
    Get aggregated metrics from telemetry.

    Provides summary statistics for simulation metrics.
    Can aggregate across all ticks or group by tick.

    This is READ-ONLY per C3.
    """
    from app.services import get_telemetry_service

    telemetry_service = get_telemetry_service()

    metrics = await telemetry_service.get_aggregated_metrics(
        run_id=run_id,
        tenant_id=tenant_ctx.tenant_id,
        metric_names=metric_names,
        aggregation=aggregation,
        group_by_tick=group_by_tick,
    )

    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metrics not found for run {run_id}",
        )

    return {
        "run_id": run_id,
        "aggregation": aggregation,
        "metrics": metrics,
    }
