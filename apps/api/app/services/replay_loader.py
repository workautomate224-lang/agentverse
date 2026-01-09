"""
Deterministic Replay Loader Service
Reference: project.md §11 Phase 8

Loads telemetry and produces timeline for playback.
Constraint C3: This is READ-ONLY - NEVER triggers simulations.

Features:
- Loads keyframes + deltas from telemetry storage
- Reconstructs world state at any tick (deterministic)
- Same node always replays same storyline
- Efficient seeking using keyframe index
- Timeline generation for 2D Replay UI
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from copy import deepcopy

from app.services.telemetry import (
    TelemetryService,
    TelemetryBlob,
    TelemetryKeyframe,
    TelemetryDelta,
    TelemetrySlice,
    TelemetryQueryParams,
    get_telemetry_service,
)
from app.services.storage import StorageRef, get_storage_service


class ReplayState(str, Enum):
    """Replay loading states."""
    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    SEEKING = "seeking"
    ERROR = "error"


@dataclass
class AgentReplayState:
    """
    Agent state at a specific tick for replay visualization.
    Contains all visual-relevant properties.
    """
    agent_id: str
    tick: int
    position: Dict[str, float]  # x, y coordinates for 2D layout
    segment: str
    region: Optional[str]
    stance: float  # -1 to 1 (opinion/preference)
    emotion: float  # 0 to 1 (arousal/engagement)
    influence: float  # 0 to 1 (social influence level)
    exposure: float  # 0 to 1 (media/information exposure)
    last_action: Optional[str]
    last_event: Optional[str]
    beliefs: Dict[str, float]

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "tick": self.tick,
            "position": self.position,
            "segment": self.segment,
            "region": self.region,
            "stance": self.stance,
            "emotion": self.emotion,
            "influence": self.influence,
            "exposure": self.exposure,
            "last_action": self.last_action,
            "last_event": self.last_event,
            "beliefs": self.beliefs,
        }

    @classmethod
    def from_dict(cls, data: dict, tick: int) -> "AgentReplayState":
        """Create from telemetry agent state data."""
        return cls(
            agent_id=data.get("agent_id", data.get("id", "")),
            tick=tick,
            position=data.get("position", {"x": 0.0, "y": 0.0}),
            segment=data.get("segment", "default"),
            region=data.get("region"),
            stance=data.get("stance", data.get("opinion", 0.0)),
            emotion=data.get("emotion", data.get("arousal", 0.5)),
            influence=data.get("influence", 0.5),
            exposure=data.get("exposure", 0.0),
            last_action=data.get("last_action"),
            last_event=data.get("last_event"),
            beliefs=data.get("beliefs", {}),
        )


@dataclass
class EnvironmentReplayState:
    """
    Environment state at a specific tick.
    Contains global variables and events.
    """
    tick: int
    variables: Dict[str, Any]
    active_events: List[str]
    metrics: Dict[str, float]

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "variables": self.variables,
            "active_events": self.active_events,
            "metrics": self.metrics,
        }


@dataclass
class WorldReplayState:
    """
    Complete world state at a specific tick.
    This is the primary structure for 2D visualization.
    """
    tick: int
    timestamp: str
    agents: Dict[str, AgentReplayState]
    environment: EnvironmentReplayState
    event_log: List[Dict[str, Any]]  # Events triggered at this tick

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "timestamp": self.timestamp,
            "agents": {aid: a.to_dict() for aid, a in self.agents.items()},
            "environment": self.environment.to_dict(),
            "event_log": self.event_log,
        }


@dataclass
class TimelineMarker:
    """
    A marker on the timeline for navigation.
    Used for event highlights and keyframe positions.
    """
    tick: int
    marker_type: str  # "keyframe", "event", "segment_change"
    label: str
    event_types: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "type": self.marker_type,
            "label": self.label,
            "event_types": self.event_types,
        }


@dataclass
class ReplayTimeline:
    """
    Complete timeline structure for the 2D Replay UI.
    Provides navigation and seeking capabilities.
    """
    run_id: str
    node_id: Optional[str]
    total_ticks: int
    keyframe_ticks: List[int]
    event_markers: List[TimelineMarker]
    duration_seconds: float
    tick_rate: float  # Ticks per second in real-time
    seed_used: int
    agent_count: int
    segment_distribution: Dict[str, int]  # segment -> agent count
    region_distribution: Dict[str, int]   # region -> agent count
    metrics_summary: Dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "node_id": self.node_id,
            "total_ticks": self.total_ticks,
            "keyframe_ticks": self.keyframe_ticks,
            "event_markers": [m.to_dict() for m in self.event_markers],
            "duration_seconds": self.duration_seconds,
            "tick_rate": self.tick_rate,
            "seed_used": self.seed_used,
            "agent_count": self.agent_count,
            "segment_distribution": self.segment_distribution,
            "region_distribution": self.region_distribution,
            "metrics_summary": self.metrics_summary,
        }


@dataclass
class ReplayChunk:
    """
    A chunk of replay data for streaming.
    Used for efficient loading of large simulations.
    """
    start_tick: int
    end_tick: int
    keyframes: List[TelemetryKeyframe]
    deltas: List[TelemetryDelta]

    def to_dict(self) -> dict:
        return {
            "start_tick": self.start_tick,
            "end_tick": self.end_tick,
            "keyframe_count": len(self.keyframes),
            "delta_count": len(self.deltas),
        }


class DeterministicReplayLoader:
    """
    Loads telemetry and reconstructs world state for replay.

    Key features:
    - Deterministic: Same node always produces same replay
    - Efficient: Uses keyframe index for fast seeking
    - Read-only: NEVER triggers simulations (C3 compliant)

    Reference: project.md §11 Phase 8
    """

    DEFAULT_CHUNK_SIZE = 1000  # Ticks per chunk
    DEFAULT_TICK_RATE = 10.0   # Ticks per second for playback

    def __init__(
        self,
        telemetry_service: Optional[TelemetryService] = None,
    ):
        self.telemetry = telemetry_service or get_telemetry_service()
        self._loaded_blob: Optional[TelemetryBlob] = None
        self._storage_ref: Optional[StorageRef] = None
        self._reconstructed_states: Dict[int, WorldReplayState] = {}
        self._state = ReplayState.IDLE

    @property
    def state(self) -> ReplayState:
        return self._state

    @property
    def is_loaded(self) -> bool:
        return self._loaded_blob is not None

    async def load(
        self,
        storage_ref: StorageRef,
        preload_ticks: int = 100,
    ) -> ReplayTimeline:
        """
        Load telemetry and prepare for replay.

        Args:
            storage_ref: Reference to telemetry in object storage
            preload_ticks: Number of initial ticks to pre-reconstruct

        Returns:
            ReplayTimeline with navigation metadata

        This is READ-ONLY - does not trigger any simulation.
        """
        self._state = ReplayState.LOADING

        try:
            # Load telemetry blob
            self._loaded_blob = await self.telemetry.get_telemetry(storage_ref)
            self._storage_ref = storage_ref

            # Build timeline
            timeline = self._build_timeline()

            # Pre-reconstruct initial states for fast start
            if preload_ticks > 0:
                for tick in range(min(preload_ticks, self._loaded_blob.ticks_executed)):
                    await self.get_state_at_tick(tick)

            self._state = ReplayState.READY
            return timeline

        except Exception as e:
            self._state = ReplayState.ERROR
            raise RuntimeError(f"Failed to load replay: {e}")

    async def load_from_ref_dict(
        self,
        ref_dict: dict,
        preload_ticks: int = 100,
    ) -> ReplayTimeline:
        """Load using a reference dictionary."""
        storage_ref = StorageRef.from_dict(ref_dict)
        return await self.load(storage_ref, preload_ticks)

    def _build_timeline(self) -> ReplayTimeline:
        """Build the timeline structure from loaded telemetry."""
        if not self._loaded_blob:
            raise RuntimeError("No telemetry loaded")

        blob = self._loaded_blob

        # Build event markers from index
        event_markers = []

        # Add keyframe markers
        for tick in blob.index.keyframe_ticks:
            event_markers.append(TimelineMarker(
                tick=int(tick) if isinstance(tick, str) else tick,
                marker_type="keyframe",
                label=f"Keyframe {tick}",
            ))

        # Add event markers
        for entry in blob.index.event_index:
            tick = entry.get("tick", 0)
            events = entry.get("events", [])
            if events:
                event_markers.append(TimelineMarker(
                    tick=tick,
                    marker_type="event",
                    label=", ".join(events[:2]) + ("..." if len(events) > 2 else ""),
                    event_types=events,
                ))

        # Sort markers by tick
        event_markers.sort(key=lambda m: m.tick)

        # Calculate segment/region distribution from final states
        segment_dist: Dict[str, int] = {}
        region_dist: Dict[str, int] = {}

        for agent_id, state in blob.final_states.items():
            segment = state.get("segment", "default")
            region = state.get("region", "unknown")
            segment_dist[segment] = segment_dist.get(segment, 0) + 1
            region_dist[region] = region_dist.get(region, 0) + 1

        # Estimate duration (assuming 1 second = 10 ticks by default)
        duration = blob.ticks_executed / self.DEFAULT_TICK_RATE

        return ReplayTimeline(
            run_id=blob.run_id,
            node_id=None,  # Will be set by caller if available
            total_ticks=blob.ticks_executed,
            keyframe_ticks=[int(t) if isinstance(t, str) else t for t in blob.index.keyframe_ticks],
            event_markers=event_markers,
            duration_seconds=duration,
            tick_rate=self.DEFAULT_TICK_RATE,
            seed_used=blob.seed_used,
            agent_count=blob.agent_count,
            segment_distribution=segment_dist,
            region_distribution=region_dist,
            metrics_summary=blob.metrics_summary,
        )

    async def get_state_at_tick(self, tick: int) -> WorldReplayState:
        """
        Reconstruct the world state at a specific tick.

        This is DETERMINISTIC:
        - Same tick always produces identical state
        - Uses keyframe + delta reconstruction

        This is READ-ONLY (C3 compliant):
        - Does not trigger any simulation
        - Pure state reconstruction from stored telemetry
        """
        if not self._loaded_blob:
            raise RuntimeError("No telemetry loaded - call load() first")

        # Check cache
        if tick in self._reconstructed_states:
            return self._reconstructed_states[tick]

        self._state = ReplayState.SEEKING

        try:
            # Find nearest keyframe at or before tick
            keyframe = self._find_keyframe_before(tick)

            if keyframe is None:
                # No keyframe before tick - reconstruct from start
                state = self._create_initial_state()
                start_tick = 0
            else:
                # Start from keyframe
                state = self._keyframe_to_world_state(keyframe)
                start_tick = keyframe.tick

            # Apply deltas from keyframe to target tick
            if start_tick < tick:
                deltas = self._get_deltas_in_range(start_tick, tick)
                for delta in deltas:
                    state = self._apply_delta(state, delta)

            # Cache reconstructed state
            self._reconstructed_states[tick] = state

            self._state = ReplayState.READY
            return state

        except Exception as e:
            self._state = ReplayState.ERROR
            raise RuntimeError(f"Failed to reconstruct state at tick {tick}: {e}")

    def _find_keyframe_before(self, tick: int) -> Optional[TelemetryKeyframe]:
        """Find the closest keyframe at or before the given tick."""
        if not self._loaded_blob:
            return None

        closest: Optional[TelemetryKeyframe] = None
        for kf in self._loaded_blob.keyframes:
            if kf.tick <= tick:
                if closest is None or kf.tick > closest.tick:
                    closest = kf
            else:
                break  # Keyframes are sorted by tick

        return closest

    def _get_deltas_in_range(
        self,
        start_tick: int,
        end_tick: int,
    ) -> List[TelemetryDelta]:
        """Get all deltas in a tick range (exclusive start, inclusive end)."""
        if not self._loaded_blob:
            return []

        return [
            d for d in self._loaded_blob.deltas
            if start_tick < d.tick <= end_tick
        ]

    def _create_initial_state(self) -> WorldReplayState:
        """Create initial world state (tick 0)."""
        return WorldReplayState(
            tick=0,
            timestamp=datetime.utcnow().isoformat(),
            agents={},
            environment=EnvironmentReplayState(
                tick=0,
                variables={},
                active_events=[],
                metrics={},
            ),
            event_log=[],
        )

    def _keyframe_to_world_state(
        self,
        keyframe: TelemetryKeyframe,
    ) -> WorldReplayState:
        """Convert a keyframe to a WorldReplayState."""
        agents: Dict[str, AgentReplayState] = {}

        for agent_id, agent_data in keyframe.agent_states.items():
            agents[agent_id] = AgentReplayState.from_dict(agent_data, keyframe.tick)

        environment = EnvironmentReplayState(
            tick=keyframe.tick,
            variables=keyframe.environment_state or {},
            active_events=[],
            metrics=keyframe.metrics or {},
        )

        return WorldReplayState(
            tick=keyframe.tick,
            timestamp=keyframe.timestamp,
            agents=agents,
            environment=environment,
            event_log=[],
        )

    def _apply_delta(
        self,
        state: WorldReplayState,
        delta: TelemetryDelta,
    ) -> WorldReplayState:
        """
        Apply a delta to the world state.
        Returns a new state (immutable update).
        """
        # Deep copy to ensure immutability
        new_agents = deepcopy(state.agents)
        new_env = deepcopy(state.environment)

        # Apply agent updates
        for update in delta.agent_updates:
            agent_id = update.get("agent_id", update.get("id"))
            if not agent_id:
                continue

            if agent_id in new_agents:
                # Update existing agent
                agent = new_agents[agent_id]
                self._apply_agent_update(agent, update, delta.tick)
            else:
                # New agent (shouldn't normally happen mid-simulation)
                new_agents[agent_id] = AgentReplayState.from_dict(update, delta.tick)

        # Update environment
        new_env.tick = delta.tick
        new_env.metrics = {**new_env.metrics, **delta.metrics}
        new_env.active_events = delta.events_triggered

        # Build event log
        event_log = [
            {
                "tick": delta.tick,
                "type": event_type,
            }
            for event_type in delta.events_triggered
        ]

        return WorldReplayState(
            tick=delta.tick,
            timestamp=datetime.utcnow().isoformat(),
            agents=new_agents,
            environment=new_env,
            event_log=event_log,
        )

    def _apply_agent_update(
        self,
        agent: AgentReplayState,
        update: Dict[str, Any],
        tick: int,
    ):
        """Apply an update to an agent state (in place)."""
        agent.tick = tick

        if "position" in update:
            agent.position = update["position"]
        if "segment" in update:
            agent.segment = update["segment"]
        if "region" in update:
            agent.region = update["region"]
        if "stance" in update or "opinion" in update:
            agent.stance = update.get("stance", update.get("opinion", agent.stance))
        if "emotion" in update or "arousal" in update:
            agent.emotion = update.get("emotion", update.get("arousal", agent.emotion))
        if "influence" in update:
            agent.influence = update["influence"]
        if "exposure" in update:
            agent.exposure = update["exposure"]
        if "last_action" in update:
            agent.last_action = update["last_action"]
        if "last_event" in update:
            agent.last_event = update["last_event"]
        if "beliefs" in update:
            agent.beliefs = {**agent.beliefs, **update["beliefs"]}

    async def get_chunk(
        self,
        start_tick: int,
        end_tick: Optional[int] = None,
    ) -> ReplayChunk:
        """
        Get a chunk of replay data for streaming.

        Args:
            start_tick: Start of chunk
            end_tick: End of chunk (defaults to start_tick + CHUNK_SIZE)

        Returns:
            ReplayChunk with keyframes and deltas in range

        This is READ-ONLY (C3 compliant).
        """
        if not self._loaded_blob:
            raise RuntimeError("No telemetry loaded - call load() first")

        if end_tick is None:
            end_tick = start_tick + self.DEFAULT_CHUNK_SIZE

        end_tick = min(end_tick, self._loaded_blob.ticks_executed)

        # Get keyframes in range
        keyframes = [
            kf for kf in self._loaded_blob.keyframes
            if start_tick <= kf.tick <= end_tick
        ]

        # Get deltas in range
        deltas = [
            d for d in self._loaded_blob.deltas
            if start_tick <= d.tick <= end_tick
        ]

        return ReplayChunk(
            start_tick=start_tick,
            end_tick=end_tick,
            keyframes=keyframes,
            deltas=deltas,
        )

    async def get_agent_history(
        self,
        agent_id: str,
        tick_start: Optional[int] = None,
        tick_end: Optional[int] = None,
    ) -> List[AgentReplayState]:
        """
        Get the state history for a specific agent.
        Used for "Explain-on-Click" feature.

        This is READ-ONLY (C3 compliant).
        """
        if not self._loaded_blob:
            raise RuntimeError("No telemetry loaded - call load() first")

        tick_start = tick_start or 0
        tick_end = tick_end or self._loaded_blob.ticks_executed

        history: List[AgentReplayState] = []

        # Get states from keyframes
        for kf in self._loaded_blob.keyframes:
            if tick_start <= kf.tick <= tick_end:
                if agent_id in kf.agent_states:
                    history.append(
                        AgentReplayState.from_dict(kf.agent_states[agent_id], kf.tick)
                    )

        # Fill in from deltas
        for delta in self._loaded_blob.deltas:
            if tick_start <= delta.tick <= tick_end:
                for update in delta.agent_updates:
                    if update.get("agent_id") == agent_id or update.get("id") == agent_id:
                        # Apply update to last known state
                        if history:
                            last_state = deepcopy(history[-1])
                            self._apply_agent_update(last_state, update, delta.tick)
                            history.append(last_state)

        # Sort by tick
        history.sort(key=lambda s: s.tick)
        return history

    async def get_events_at_tick(
        self,
        tick: int,
    ) -> List[Dict[str, Any]]:
        """
        Get all events that occurred at a specific tick.
        Used for "Explain-on-Click" feature.

        This is READ-ONLY (C3 compliant).
        """
        if not self._loaded_blob:
            raise RuntimeError("No telemetry loaded - call load() first")

        events = []

        for delta in self._loaded_blob.deltas:
            if delta.tick == tick:
                for event_type in delta.events_triggered:
                    events.append({
                        "tick": tick,
                        "type": event_type,
                        "metrics": delta.metrics,
                    })
                break

        return events

    def clear(self):
        """Clear loaded telemetry and cached states."""
        self._loaded_blob = None
        self._storage_ref = None
        self._reconstructed_states.clear()
        self._state = ReplayState.IDLE


# Factory function
def create_replay_loader(
    telemetry_service: Optional[TelemetryService] = None,
) -> DeterministicReplayLoader:
    """Create a new replay loader instance."""
    return DeterministicReplayLoader(telemetry_service)


# Singleton instance (for shared use)
_replay_loader: Optional[DeterministicReplayLoader] = None


def get_replay_loader() -> DeterministicReplayLoader:
    """Get the shared replay loader instance."""
    global _replay_loader
    if _replay_loader is None:
        _replay_loader = DeterministicReplayLoader()
    return _replay_loader
