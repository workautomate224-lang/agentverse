"""
2D Replay API Endpoints
Reference: project.md §11 Phase 8, Interaction_design.md §5.17

All endpoints are READ-ONLY (C3 compliant) - NEVER trigger simulations.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_current_tenant
from app.services.replay_loader import (
    DeterministicReplayLoader,
    ReplayTimeline,
    WorldReplayState,
    ReplayChunk,
    AgentReplayState,
    create_replay_loader,
)
from app.services.storage import StorageRef
from app.models.user import User

router = APIRouter()


# ============================================================
# Response Schemas
# ============================================================

class TimelineMarkerResponse(BaseModel):
    """Timeline marker for navigation."""
    tick: int
    type: str
    label: str
    event_types: List[str] = []


class ReplayTimelineResponse(BaseModel):
    """Complete timeline metadata for replay UI."""
    run_id: str
    node_id: Optional[str] = None
    total_ticks: int
    keyframe_ticks: List[int]
    event_markers: List[TimelineMarkerResponse]
    duration_seconds: float
    tick_rate: float
    seed_used: int
    agent_count: int
    segment_distribution: Dict[str, int]
    region_distribution: Dict[str, int]
    metrics_summary: Dict[str, Any]


class AgentStateResponse(BaseModel):
    """Agent state at a specific tick."""
    agent_id: str
    tick: int
    position: Dict[str, float]
    segment: str
    region: Optional[str] = None
    stance: float
    emotion: float
    influence: float
    exposure: float
    last_action: Optional[str] = None
    last_event: Optional[str] = None
    beliefs: Dict[str, float] = {}


class EnvironmentStateResponse(BaseModel):
    """Environment state at a specific tick."""
    tick: int
    variables: Dict[str, Any]
    active_events: List[str]
    metrics: Dict[str, float]


class WorldStateResponse(BaseModel):
    """Complete world state at a specific tick."""
    tick: int
    timestamp: str
    agents: Dict[str, AgentStateResponse]
    environment: EnvironmentStateResponse
    event_log: List[Dict[str, Any]]


class ReplayChunkResponse(BaseModel):
    """A chunk of replay data."""
    start_tick: int
    end_tick: int
    keyframe_count: int
    delta_count: int
    states: List[WorldStateResponse] = []


class AgentHistoryResponse(BaseModel):
    """Agent state history for explain-on-click."""
    agent_id: str
    states: List[AgentStateResponse]
    total_states: int


class TickEventsResponse(BaseModel):
    """Events at a specific tick for explain-on-click."""
    tick: int
    events: List[Dict[str, Any]]


# ============================================================
# Request Schemas
# ============================================================

class LoadReplayRequest(BaseModel):
    """Request to load replay for a run/node."""
    storage_ref: Dict[str, Any] = Field(
        ...,
        description="Storage reference from telemetry_ref field"
    )
    preload_ticks: int = Field(
        default=100,
        ge=0,
        le=1000,
        description="Number of initial ticks to pre-reconstruct"
    )
    node_id: Optional[str] = Field(
        default=None,
        description="Node ID for reference (optional)"
    )


# ============================================================
# API Endpoints (All READ-ONLY per C3)
# ============================================================

@router.post("/load", response_model=ReplayTimelineResponse)
async def load_replay(
    request: LoadReplayRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Load telemetry and prepare for replay.

    This is READ-ONLY (C3 compliant) - does not trigger any simulation.

    Returns timeline metadata for the 2D Replay UI including:
    - Total ticks and duration
    - Keyframe positions for fast seeking
    - Event markers for timeline navigation
    - Segment/region distribution
    """
    try:
        loader = create_replay_loader()
        timeline = await loader.load_from_ref_dict(
            request.storage_ref,
            preload_ticks=request.preload_ticks,
        )

        # Set node_id if provided
        if request.node_id:
            timeline.node_id = request.node_id

        return ReplayTimelineResponse(
            run_id=timeline.run_id,
            node_id=timeline.node_id,
            total_ticks=timeline.total_ticks,
            keyframe_ticks=timeline.keyframe_ticks,
            event_markers=[
                TimelineMarkerResponse(
                    tick=m.tick,
                    type=m.marker_type,
                    label=m.label,
                    event_types=m.event_types,
                )
                for m in timeline.event_markers
            ],
            duration_seconds=timeline.duration_seconds,
            tick_rate=timeline.tick_rate,
            seed_used=timeline.seed_used,
            agent_count=timeline.agent_count,
            segment_distribution=timeline.segment_distribution,
            region_distribution=timeline.region_distribution,
            metrics_summary=timeline.metrics_summary,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load replay: {str(e)}")


@router.post("/state/{tick}", response_model=WorldStateResponse)
async def get_state_at_tick(
    tick: int,
    request: LoadReplayRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Reconstruct world state at a specific tick.

    This is DETERMINISTIC:
    - Same tick always produces identical state
    - Uses keyframe + delta reconstruction

    This is READ-ONLY (C3 compliant) - does not trigger any simulation.
    """
    try:
        loader = create_replay_loader()
        await loader.load_from_ref_dict(request.storage_ref, preload_ticks=0)

        state = await loader.get_state_at_tick(tick)

        return WorldStateResponse(
            tick=state.tick,
            timestamp=state.timestamp,
            agents={
                aid: AgentStateResponse(**a.to_dict())
                for aid, a in state.agents.items()
            },
            environment=EnvironmentStateResponse(**state.environment.to_dict()),
            event_log=state.event_log,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get state: {str(e)}")


@router.post("/chunk", response_model=ReplayChunkResponse)
async def get_replay_chunk(
    request: LoadReplayRequest,
    start_tick: int = Query(0, ge=0),
    end_tick: Optional[int] = Query(None, ge=0),
    include_states: bool = Query(False, description="Include reconstructed states"),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a chunk of replay data for streaming playback.

    For large simulations, use this to load data in batches.
    Set include_states=true to get reconstructed world states.

    This is READ-ONLY (C3 compliant) - does not trigger any simulation.
    """
    try:
        loader = create_replay_loader()
        await loader.load_from_ref_dict(request.storage_ref, preload_ticks=0)

        chunk = await loader.get_chunk(start_tick, end_tick)

        states = []
        if include_states:
            for tick in range(chunk.start_tick, chunk.end_tick + 1, 10):  # Sample every 10 ticks
                state = await loader.get_state_at_tick(tick)
                states.append(WorldStateResponse(
                    tick=state.tick,
                    timestamp=state.timestamp,
                    agents={
                        aid: AgentStateResponse(**a.to_dict())
                        for aid, a in state.agents.items()
                    },
                    environment=EnvironmentStateResponse(**state.environment.to_dict()),
                    event_log=state.event_log,
                ))

        return ReplayChunkResponse(
            start_tick=chunk.start_tick,
            end_tick=chunk.end_tick,
            keyframe_count=len(chunk.keyframes),
            delta_count=len(chunk.deltas),
            states=states,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chunk: {str(e)}")


@router.post("/agent/{agent_id}/history", response_model=AgentHistoryResponse)
async def get_agent_history(
    agent_id: str,
    request: LoadReplayRequest,
    tick_start: Optional[int] = Query(None, ge=0),
    tick_end: Optional[int] = Query(None, ge=0),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Get state history for a specific agent.

    Used for "Explain-on-Click" feature in 2D Replay.
    Shows how an agent's state changed over time.

    This is READ-ONLY (C3 compliant) - does not trigger any simulation.
    """
    try:
        loader = create_replay_loader()
        await loader.load_from_ref_dict(request.storage_ref, preload_ticks=0)

        history = await loader.get_agent_history(agent_id, tick_start, tick_end)

        return AgentHistoryResponse(
            agent_id=agent_id,
            states=[AgentStateResponse(**s.to_dict()) for s in history],
            total_states=len(history),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent history: {str(e)}")


@router.post("/events/{tick}", response_model=TickEventsResponse)
async def get_events_at_tick(
    tick: int,
    request: LoadReplayRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all events that occurred at a specific tick.

    Used for "Explain-on-Click" feature in 2D Replay.
    Shows what triggered state changes at a moment.

    This is READ-ONLY (C3 compliant) - does not trigger any simulation.
    """
    try:
        loader = create_replay_loader()
        await loader.load_from_ref_dict(request.storage_ref, preload_ticks=0)

        events = await loader.get_events_at_tick(tick)

        return TickEventsResponse(
            tick=tick,
            events=events,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get events: {str(e)}")


@router.post("/seek/{tick}", response_model=WorldStateResponse)
async def seek_to_tick(
    tick: int,
    request: LoadReplayRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Seek to a specific tick in the replay.

    Optimized for fast seeking using keyframe index.
    Equivalent to get_state_at_tick but named for UI clarity.

    This is READ-ONLY (C3 compliant) - does not trigger any simulation.
    """
    # Delegate to get_state_at_tick
    return await get_state_at_tick(tick, request, current_user, tenant_id, db)
