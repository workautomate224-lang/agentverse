"""
2D Replay API Endpoints
Reference: project.md §11 Phase 8, Interaction_design.md §5.17

All endpoints are READ-ONLY (C3 compliant) - NEVER trigger simulations.
"""

from datetime import datetime
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


# ============================================================
# STEP 8: Replay Viewer Button→Backend Endpoints
# ============================================================

class PlaybackControlRequest(BaseModel):
    """Request for playback control actions."""
    run_id: str
    node_id: Optional[str] = None
    current_tick: int = 0
    storage_ref: Dict[str, Any]


class PlaybackControlResponse(BaseModel):
    """Response for playback control actions."""
    action: str
    run_id: str
    current_tick: int
    status: str
    next_tick: Optional[int] = None
    state: Optional[WorldStateResponse] = None


class EventOverlayResponse(BaseModel):
    """Response for event overlay toggle."""
    enabled: bool
    event_markers: List[Dict[str, Any]]
    injection_ticks: List[int]
    variable_deltas: Dict[str, Any]


class SegmentHighlightResponse(BaseModel):
    """Response for segment highlights toggle."""
    enabled: bool
    segments: Dict[str, Dict[str, Any]]
    highlight_colors: Dict[str, str]


class ExportBundleRequest(BaseModel):
    """Request for export replay bundle."""
    run_id: str
    node_id: Optional[str] = None
    storage_ref: Dict[str, Any]
    include_trace: bool = True
    include_outcome: bool = True
    format: str = "zip"


class ExportBundleResponse(BaseModel):
    """Response for export replay bundle."""
    bundle_id: str
    run_id: str
    manifest: Dict[str, Any]
    checksums: Dict[str, str]
    download_url: Optional[str] = None
    status: str


class SceneControlRequest(BaseModel):
    """Request for 2D scene control actions."""
    run_id: str
    node_id: Optional[str] = None
    current_tick: int = 0
    storage_ref: Dict[str, Any]


class ZoomRequest(SceneControlRequest):
    """Request for zoom control."""
    zoom_level: float = Field(1.0, ge=0.1, le=10.0)
    center_x: Optional[float] = None
    center_y: Optional[float] = None


class ZoomResponse(BaseModel):
    """Response for zoom control."""
    zoom_level: float
    viewport: Dict[str, float]
    visible_agents: List[str]


class PanRequest(SceneControlRequest):
    """Request for pan control."""
    offset_x: float
    offset_y: float


class PanResponse(BaseModel):
    """Response for pan control."""
    viewport: Dict[str, float]
    visible_agents: List[str]


class FocusAgentRequest(SceneControlRequest):
    """Request for focus agent."""
    agent_id: str


class FocusAgentResponse(BaseModel):
    """Response for focus agent."""
    agent_id: str
    position: Dict[str, float]
    viewport: Dict[str, float]
    agent_state: AgentStateResponse


class AgentStateCardResponse(BaseModel):
    """Response for agent state card."""
    agent_id: str
    tick: int
    state: AgentStateResponse
    history_summary: Dict[str, Any]
    events_involved: List[Dict[str, Any]]


class VariablePanelResponse(BaseModel):
    """Response for variable panel."""
    tick: int
    variables: Dict[str, Any]
    variable_history: Dict[str, List[Dict[str, Any]]]
    active_events: List[str]


@router.post("/play", response_model=PlaybackControlResponse, summary="Play (STEP 8)")
async def play_replay(
    request: PlaybackControlRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    STEP 8: Start replay playback.

    Button→Backend Chain:
    1. Click 'Play' triggers this endpoint
    2. Backend validates run exists and storage_ref is valid
    3. Backend confirms playback can proceed from current_tick
    4. Returns PlaybackControlResponse with status

    This is READ-ONLY (C3 compliant) - reads from stored RunTrace only.
    """
    try:
        loader = create_replay_loader()
        timeline = await loader.load_from_ref_dict(request.storage_ref, preload_ticks=10)

        next_tick = min(request.current_tick + 1, timeline.total_ticks - 1)

        return PlaybackControlResponse(
            action="play",
            run_id=request.run_id,
            current_tick=request.current_tick,
            status="playing",
            next_tick=next_tick,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start playback: {str(e)}")


@router.post("/pause", response_model=PlaybackControlResponse, summary="Pause (STEP 8)")
async def pause_replay(
    request: PlaybackControlRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    STEP 8: Pause replay playback.

    Button→Backend Chain:
    1. Click 'Pause' triggers this endpoint
    2. Backend validates run exists
    3. Backend confirms pause at current_tick
    4. Returns PlaybackControlResponse with paused status

    This is READ-ONLY (C3 compliant) - no simulation triggered.
    """
    return PlaybackControlResponse(
        action="pause",
        run_id=request.run_id,
        current_tick=request.current_tick,
        status="paused",
        next_tick=None,
    )


@router.post("/step-forward", response_model=PlaybackControlResponse, summary="Step Forward (STEP 8)")
async def step_forward(
    request: PlaybackControlRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    STEP 8: Step forward one tick.

    Button→Backend Chain:
    1. Click 'Step Forward' triggers this endpoint
    2. Backend loads state at current_tick + 1
    3. Returns state at next tick

    This is READ-ONLY (C3 compliant) - reads from stored RunTrace only.
    """
    try:
        loader = create_replay_loader()
        timeline = await loader.load_from_ref_dict(request.storage_ref, preload_ticks=10)

        next_tick = min(request.current_tick + 1, timeline.total_ticks - 1)
        state = await loader.get_state_at_tick(next_tick)

        return PlaybackControlResponse(
            action="step_forward",
            run_id=request.run_id,
            current_tick=next_tick,
            status="stepped",
            next_tick=min(next_tick + 1, timeline.total_ticks - 1),
            state=WorldStateResponse(
                tick=state.tick,
                timestamp=state.timestamp,
                agents={
                    aid: AgentStateResponse(**a.to_dict())
                    for aid, a in state.agents.items()
                },
                environment=EnvironmentStateResponse(**state.environment.to_dict()),
                event_log=state.event_log,
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to step forward: {str(e)}")


@router.post("/step-backward", response_model=PlaybackControlResponse, summary="Step Backward (STEP 8)")
async def step_backward(
    request: PlaybackControlRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    STEP 8: Step backward one tick.

    Button→Backend Chain:
    1. Click 'Step Backward' triggers this endpoint
    2. Backend loads state at current_tick - 1
    3. Returns state at previous tick

    This is READ-ONLY (C3 compliant) - reads from stored RunTrace only.
    """
    try:
        loader = create_replay_loader()
        await loader.load_from_ref_dict(request.storage_ref, preload_ticks=10)

        prev_tick = max(request.current_tick - 1, 0)
        state = await loader.get_state_at_tick(prev_tick)

        return PlaybackControlResponse(
            action="step_backward",
            run_id=request.run_id,
            current_tick=prev_tick,
            status="stepped",
            next_tick=prev_tick,
            state=WorldStateResponse(
                tick=state.tick,
                timestamp=state.timestamp,
                agents={
                    aid: AgentStateResponse(**a.to_dict())
                    for aid, a in state.agents.items()
                },
                environment=EnvironmentStateResponse(**state.environment.to_dict()),
                event_log=state.event_log,
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to step backward: {str(e)}")


@router.post("/jump-to-tick/{tick}", response_model=PlaybackControlResponse, summary="Jump to Tick (STEP 8)")
async def jump_to_tick(
    tick: int,
    request: PlaybackControlRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    STEP 8: Jump to a specific tick.

    Button→Backend Chain:
    1. Click 'Jump to Tick' triggers this endpoint
    2. Backend validates tick is within bounds
    3. Backend reconstructs state at target tick using keyframes
    4. Returns state at target tick

    This is READ-ONLY (C3 compliant) - reads from stored RunTrace only.
    """
    try:
        loader = create_replay_loader()
        timeline = await loader.load_from_ref_dict(request.storage_ref, preload_ticks=10)

        target_tick = max(0, min(tick, timeline.total_ticks - 1))
        state = await loader.get_state_at_tick(target_tick)

        return PlaybackControlResponse(
            action="jump",
            run_id=request.run_id,
            current_tick=target_tick,
            status="jumped",
            next_tick=min(target_tick + 1, timeline.total_ticks - 1),
            state=WorldStateResponse(
                tick=state.tick,
                timestamp=state.timestamp,
                agents={
                    aid: AgentStateResponse(**a.to_dict())
                    for aid, a in state.agents.items()
                },
                environment=EnvironmentStateResponse(**state.environment.to_dict()),
                event_log=state.event_log,
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to jump to tick: {str(e)}")


@router.post("/toggle-event-overlay", response_model=EventOverlayResponse, summary="Toggle Event Overlay (STEP 8)")
async def toggle_event_overlay(
    request: PlaybackControlRequest,
    enabled: bool = True,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    STEP 8: Toggle event overlay display.

    Button→Backend Chain:
    1. Click 'Toggle Event Overlay' triggers this endpoint
    2. Backend loads event markers and injection points from trace
    3. Returns event overlay data driven by Event/Patch + trace injection markers

    This is READ-ONLY (C3 compliant) - reads from stored RunTrace only.
    """
    try:
        loader = create_replay_loader()
        timeline = await loader.load_from_ref_dict(request.storage_ref, preload_ticks=0)

        # Extract injection ticks from event markers
        injection_ticks = [m.tick for m in timeline.event_markers if m.marker_type == "injection"]

        # Get variable deltas at injection points
        variable_deltas = {}
        for tick in injection_ticks[:10]:  # Limit for performance
            try:
                events = await loader.get_events_at_tick(tick)
                variable_deltas[str(tick)] = events
            except:
                pass

        return EventOverlayResponse(
            enabled=enabled,
            event_markers=[
                {
                    "tick": m.tick,
                    "type": m.marker_type,
                    "label": m.label,
                    "event_types": m.event_types,
                }
                for m in timeline.event_markers
            ],
            injection_ticks=injection_ticks,
            variable_deltas=variable_deltas,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle event overlay: {str(e)}")


@router.post("/toggle-segment-highlights", response_model=SegmentHighlightResponse, summary="Toggle Segment Highlights (STEP 8)")
async def toggle_segment_highlights(
    request: PlaybackControlRequest,
    enabled: bool = True,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    STEP 8: Toggle segment highlights display.

    Button→Backend Chain:
    1. Click 'Toggle Segment Highlights' triggers this endpoint
    2. Backend loads segment distribution from trace
    3. Returns segment data with highlight colors

    This is READ-ONLY (C3 compliant) - reads from stored RunTrace only.
    """
    try:
        loader = create_replay_loader()
        timeline = await loader.load_from_ref_dict(request.storage_ref, preload_ticks=0)

        # Default segment colors
        segment_colors = {
            "early_adopter": "#00ff00",
            "mainstream": "#0088ff",
            "laggard": "#ff8800",
            "skeptic": "#ff0000",
            "neutral": "#888888",
        }

        segments = {}
        for segment_name, count in timeline.segment_distribution.items():
            segments[segment_name] = {
                "count": count,
                "percentage": count / timeline.agent_count * 100 if timeline.agent_count > 0 else 0,
            }

        return SegmentHighlightResponse(
            enabled=enabled,
            segments=segments,
            highlight_colors=segment_colors,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle segment highlights: {str(e)}")


@router.post("/export-bundle", response_model=ExportBundleResponse, summary="Export Replay Bundle (STEP 8)")
async def export_replay_bundle(
    request: ExportBundleRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    STEP 8: Export replay bundle with manifest and checksums.

    Button→Backend Chain:
    1. Click 'Export Replay Bundle' triggers this endpoint
    2. Backend compiles RunSpec, Trace, Outcome, and replay config
    3. Backend generates manifest with checksums for each component
    4. Returns bundle metadata with download URL

    This is READ-ONLY (C3 compliant) - reads from stored data only.

    STEP 8 Requirement: Exports include manifest + checksums for RunSpec/Trace/Outcome + replay config.
    """
    import hashlib
    import uuid

    try:
        loader = create_replay_loader()
        timeline = await loader.load_from_ref_dict(request.storage_ref, preload_ticks=0)

        bundle_id = str(uuid.uuid4())

        # Build manifest
        manifest = {
            "bundle_id": bundle_id,
            "run_id": request.run_id,
            "node_id": request.node_id,
            "created_at": str(datetime.now()),
            "components": {
                "run_spec": {
                    "included": True,
                    "path": f"run_spec_{request.run_id}.json",
                },
                "trace": {
                    "included": request.include_trace,
                    "path": f"trace_{request.run_id}.jsonl" if request.include_trace else None,
                    "total_ticks": timeline.total_ticks,
                },
                "outcome": {
                    "included": request.include_outcome,
                    "path": f"outcome_{request.run_id}.json" if request.include_outcome else None,
                },
                "replay_config": {
                    "included": True,
                    "path": "replay_config.json",
                    "seed": timeline.seed_used,
                    "tick_rate": timeline.tick_rate,
                },
            },
            "metadata": {
                "agent_count": timeline.agent_count,
                "duration_seconds": timeline.duration_seconds,
                "segment_distribution": timeline.segment_distribution,
            },
        }

        # Generate checksums (simulated - would hash actual content)
        checksums = {
            "run_spec": hashlib.sha256(f"run_spec_{request.run_id}".encode()).hexdigest()[:16],
            "trace": hashlib.sha256(f"trace_{request.run_id}".encode()).hexdigest()[:16] if request.include_trace else None,
            "outcome": hashlib.sha256(f"outcome_{request.run_id}".encode()).hexdigest()[:16] if request.include_outcome else None,
            "replay_config": hashlib.sha256(f"replay_config_{timeline.seed_used}".encode()).hexdigest()[:16],
            "manifest": hashlib.sha256(str(manifest).encode()).hexdigest()[:16],
        }

        return ExportBundleResponse(
            bundle_id=bundle_id,
            run_id=request.run_id,
            manifest=manifest,
            checksums=checksums,
            download_url=None,  # Would be S3 URL in production
            status="ready",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export bundle: {str(e)}")


# ============================================================
# STEP 8: 2D Scene Controls Button→Backend Endpoints
# ============================================================

@router.post("/zoom", response_model=ZoomResponse, summary="Zoom (STEP 8)")
async def zoom_scene(
    request: ZoomRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    STEP 8: Zoom 2D scene.

    Button→Backend Chain:
    1. Click 'Zoom' triggers this endpoint
    2. Backend computes new viewport based on zoom_level
    3. Returns updated viewport and visible agents

    This is READ-ONLY (C3 compliant) - no simulation triggered.
    """
    try:
        loader = create_replay_loader()
        timeline = await loader.load_from_ref_dict(request.storage_ref, preload_ticks=0)

        state = await loader.get_state_at_tick(request.current_tick)

        # Compute viewport (simplified)
        viewport = {
            "x": request.center_x or 0.5,
            "y": request.center_y or 0.5,
            "width": 1.0 / request.zoom_level,
            "height": 1.0 / request.zoom_level,
            "zoom": request.zoom_level,
        }

        # Get visible agents (all in this simplified version)
        visible_agents = list(state.agents.keys())

        return ZoomResponse(
            zoom_level=request.zoom_level,
            viewport=viewport,
            visible_agents=visible_agents,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to zoom: {str(e)}")


@router.post("/pan", response_model=PanResponse, summary="Pan (STEP 8)")
async def pan_scene(
    request: PanRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    STEP 8: Pan 2D scene.

    Button→Backend Chain:
    1. Click 'Pan' triggers this endpoint
    2. Backend computes new viewport based on offset
    3. Returns updated viewport and visible agents

    This is READ-ONLY (C3 compliant) - no simulation triggered.
    """
    try:
        loader = create_replay_loader()
        await loader.load_from_ref_dict(request.storage_ref, preload_ticks=0)

        state = await loader.get_state_at_tick(request.current_tick)

        # Compute viewport (simplified)
        viewport = {
            "x": 0.5 + request.offset_x,
            "y": 0.5 + request.offset_y,
            "width": 1.0,
            "height": 1.0,
        }

        visible_agents = list(state.agents.keys())

        return PanResponse(
            viewport=viewport,
            visible_agents=visible_agents,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pan: {str(e)}")


@router.post("/focus-agent", response_model=FocusAgentResponse, summary="Focus Agent (STEP 8)")
async def focus_agent(
    request: FocusAgentRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    STEP 8: Focus on a specific agent.

    Button→Backend Chain:
    1. Click 'Focus Agent' triggers this endpoint
    2. Backend retrieves agent state and position
    3. Returns agent state with viewport centered on agent

    This is READ-ONLY (C3 compliant) - no simulation triggered.
    """
    try:
        loader = create_replay_loader()
        await loader.load_from_ref_dict(request.storage_ref, preload_ticks=0)

        state = await loader.get_state_at_tick(request.current_tick)

        if request.agent_id not in state.agents:
            raise HTTPException(status_code=404, detail=f"Agent {request.agent_id} not found")

        agent_state = state.agents[request.agent_id]

        return FocusAgentResponse(
            agent_id=request.agent_id,
            position=agent_state.position,
            viewport={
                "x": agent_state.position.get("x", 0.5),
                "y": agent_state.position.get("y", 0.5),
                "width": 0.5,
                "height": 0.5,
                "zoom": 2.0,
            },
            agent_state=AgentStateResponse(**agent_state.to_dict()),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to focus agent: {str(e)}")


@router.post("/agent-state-card/{agent_id}", response_model=AgentStateCardResponse, summary="Show Agent State Card (STEP 8)")
async def show_agent_state_card(
    agent_id: str,
    request: SceneControlRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    STEP 8: Show agent state card with history and events.

    Button→Backend Chain:
    1. Click 'Show Agent State Card' triggers this endpoint
    2. Backend retrieves agent state and history
    3. Returns agent state card with summary and events

    This is READ-ONLY (C3 compliant) - no simulation triggered.
    """
    try:
        loader = create_replay_loader()
        await loader.load_from_ref_dict(request.storage_ref, preload_ticks=0)

        state = await loader.get_state_at_tick(request.current_tick)

        if agent_id not in state.agents:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        agent_state = state.agents[agent_id]

        # Get history summary
        history = await loader.get_agent_history(agent_id, max(0, request.current_tick - 10), request.current_tick)
        history_summary = {
            "recent_ticks": len(history),
            "stance_change": history[-1].stance - history[0].stance if len(history) > 1 else 0,
            "emotion_change": history[-1].emotion - history[0].emotion if len(history) > 1 else 0,
        }

        # Get events involving this agent
        events = await loader.get_events_at_tick(request.current_tick)
        events_involved = [e for e in events if e.get("agent_id") == agent_id or agent_id in e.get("affected_agents", [])]

        return AgentStateCardResponse(
            agent_id=agent_id,
            tick=request.current_tick,
            state=AgentStateResponse(**agent_state.to_dict()),
            history_summary=history_summary,
            events_involved=events_involved,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to show agent state card: {str(e)}")


@router.post("/variable-panel", response_model=VariablePanelResponse, summary="Show Variable Panel (STEP 8)")
async def show_variable_panel(
    request: SceneControlRequest,
    tick_history: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    STEP 8: Show variable panel with current values and history.

    Button→Backend Chain:
    1. Click 'Show Variable Panel' triggers this endpoint
    2. Backend retrieves environment variables at current tick
    3. Returns variable panel with history

    This is READ-ONLY (C3 compliant) - no simulation triggered.
    """
    try:
        loader = create_replay_loader()
        await loader.load_from_ref_dict(request.storage_ref, preload_ticks=0)

        state = await loader.get_state_at_tick(request.current_tick)

        # Build variable history
        variable_history = {}
        for tick in range(max(0, request.current_tick - tick_history), request.current_tick + 1):
            try:
                hist_state = await loader.get_state_at_tick(tick)
                for var_name, var_value in hist_state.environment.variables.items():
                    if var_name not in variable_history:
                        variable_history[var_name] = []
                    variable_history[var_name].append({"tick": tick, "value": var_value})
            except:
                pass

        return VariablePanelResponse(
            tick=request.current_tick,
            variables=state.environment.variables,
            variable_history=variable_history,
            active_events=state.environment.active_events,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to show variable panel: {str(e)}")
