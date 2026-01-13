"""
Telemetry Writer Service
Reference: project.md §6.8, §5.4, Phase 1

Handles all telemetry operations:
- Writing keyframes (world/region snapshots at intervals)
- Writing delta streams (agent segment changes, event markers)
- Query interfaces for replay (READ-ONLY per C3)

Telemetry is "playback evidence," not full world state.
Constraint C3: Replay is read-only - must NEVER trigger simulations.

Telemetry Contract (§6.8):
- Keyframes: world/region snapshots at intervals
- Delta stream:
  - agent segment changes (aggregated)
  - event markers with tick references
  - optional audio/media refs
- Query hooks:
  - by tick range
  - by region/segment
  - by event type
"""

import gzip
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import uuid

from app.services.storage import StorageService, StorageRef, get_storage_service


class TelemetryVersion(str, Enum):
    """Telemetry schema versions for forward compatibility."""
    V1_0_0 = "1.0.0"
    V1_1_0 = "1.1.0"  # Phase 5: Added capabilities and spatial normalization
    CURRENT = "1.1.0"


# ============================================================================
# PHASE 5: Spatial Normalization & Capabilities Detection
# ============================================================================

@dataclass
class NormalizedPosition:
    """Canonical position format for spatial replay."""
    agent_id: str
    x: float
    y: float
    z: Optional[float] = None
    rotation: Optional[float] = None
    scale: Optional[float] = None
    grid_cell: Optional[str] = None
    location_id: Optional[str] = None

    def to_dict(self) -> dict:
        result = {
            "agent_id": self.agent_id,
            "x": self.x,
            "y": self.y,
        }
        if self.z is not None:
            result["z"] = self.z
        if self.rotation is not None:
            result["rotation"] = self.rotation
        if self.scale is not None:
            result["scale"] = self.scale
        if self.grid_cell is not None:
            result["grid_cell"] = self.grid_cell
        if self.location_id is not None:
            result["location_id"] = self.location_id
        return result


@dataclass
class TelemetryCapabilities:
    """
    Capabilities flags for telemetry data.
    Enables UI to conditionally render features.
    """
    has_spatial: bool = False
    has_events: bool = False
    has_metrics: bool = False

    def to_dict(self) -> dict:
        return {
            "has_spatial": self.has_spatial,
            "has_events": self.has_events,
            "has_metrics": self.has_metrics,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TelemetryCapabilities":
        return cls(
            has_spatial=data.get("has_spatial", False),
            has_events=data.get("has_events", False),
            has_metrics=data.get("has_metrics", False),
        )


# Spatial field aliases for normalization
SPATIAL_X_ALIASES = ["x", "position_x", "pos_x", "coord_x", "loc_x"]
SPATIAL_Y_ALIASES = ["y", "position_y", "pos_y", "coord_y", "loc_y"]
SPATIAL_Z_ALIASES = ["z", "position_z", "pos_z", "coord_z", "loc_z"]


def extract_spatial_value(
    state: Dict[str, Any],
    aliases: List[str],
    default: Optional[float] = None,
) -> Optional[float]:
    """
    Extract spatial value from agent state using alias list.
    Checks both top-level and nested 'variables' dict.
    """
    # Check top-level fields first
    for alias in aliases:
        if alias in state:
            val = state[alias]
            if isinstance(val, (int, float)):
                return float(val)

    # Check nested variables dict
    variables = state.get("variables", {})
    if isinstance(variables, dict):
        for alias in aliases:
            if alias in variables:
                val = variables[alias]
                if isinstance(val, (int, float)):
                    return float(val)

    return default


def normalize_agent_position(
    agent_id: str,
    agent_state: Dict[str, Any],
) -> Optional[NormalizedPosition]:
    """
    Extract normalized position from agent state.
    Returns None if no spatial data found.

    Supports detection of:
    - x/y, position_x/position_y, pos_x/pos_y, coord_x/coord_y, loc_x/loc_y
    - grid_cell, location_id as fallback
    """
    x = extract_spatial_value(agent_state, SPATIAL_X_ALIASES)
    y = extract_spatial_value(agent_state, SPATIAL_Y_ALIASES)

    # Check for grid_cell or location_id fallback
    variables = agent_state.get("variables", {})
    if not isinstance(variables, dict):
        variables = {}

    grid_cell = agent_state.get("grid_cell") or variables.get("grid_cell")
    location_id = agent_state.get("location_id") or variables.get("location_id")

    # Must have x and y, or grid_cell/location_id
    if x is not None and y is not None:
        z = extract_spatial_value(agent_state, SPATIAL_Z_ALIASES)
        rotation = agent_state.get("rotation") or variables.get("rotation")
        scale = agent_state.get("scale") or variables.get("scale")

        return NormalizedPosition(
            agent_id=agent_id,
            x=x,
            y=y,
            z=z,
            rotation=float(rotation) if isinstance(rotation, (int, float)) else None,
            scale=float(scale) if isinstance(scale, (int, float)) else None,
            grid_cell=str(grid_cell) if grid_cell else None,
            location_id=str(location_id) if location_id else None,
        )
    elif grid_cell or location_id:
        # Fallback: create position with 0,0 if we only have grid/location
        return NormalizedPosition(
            agent_id=agent_id,
            x=0.0,
            y=0.0,
            grid_cell=str(grid_cell) if grid_cell else None,
            location_id=str(location_id) if location_id else None,
        )

    return None


def extract_normalized_positions(
    agent_states: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Extract normalized positions from all agent states.
    Returns list of position dicts for agents with spatial data.
    """
    positions = []
    for agent_id, state in agent_states.items():
        if isinstance(state, dict):
            pos = normalize_agent_position(agent_id, state)
            if pos:
                positions.append(pos.to_dict())
    return positions


def detect_capabilities(blob_dict: Dict[str, Any]) -> TelemetryCapabilities:
    """
    Detect capabilities from telemetry blob.

    Checks for:
    - has_spatial: Agent states contain position data
    - has_events: Any events were triggered during simulation
    - has_metrics: Metrics were recorded
    """
    capabilities = TelemetryCapabilities()

    # Check deltas for events and metrics
    deltas = blob_dict.get("deltas", [])
    for delta in deltas:
        if isinstance(delta, dict):
            events = delta.get("events", [])
            if events:
                capabilities.has_events = True

            metrics = delta.get("metrics", {})
            if metrics and isinstance(metrics, dict) and len(metrics) > 0:
                capabilities.has_metrics = True

    # Check keyframes for spatial data
    keyframes = blob_dict.get("keyframes", [])
    for keyframe in keyframes:
        if isinstance(keyframe, dict):
            agent_states = keyframe.get("agent_states", {})
            for agent_id, agent_state in agent_states.items():
                if isinstance(agent_state, dict):
                    if _has_spatial_fields(agent_state):
                        capabilities.has_spatial = True
                        break
            if capabilities.has_spatial:
                break

    # Also check final states for spatial data
    if not capabilities.has_spatial:
        final_states = blob_dict.get("final_states", {})
        for agent_id, agent_state in final_states.items():
            if isinstance(agent_state, dict):
                if _has_spatial_fields(agent_state):
                    capabilities.has_spatial = True
                    break

    return capabilities


def _has_spatial_fields(agent_state: Dict[str, Any]) -> bool:
    """Check if agent state contains spatial position fields."""
    variables = agent_state.get("variables", {})
    if not isinstance(variables, dict):
        variables = {}

    # Merge top-level fields with variables for checking
    fields_to_check = {**agent_state, **variables}

    has_x = any(field in fields_to_check for field in SPATIAL_X_ALIASES)
    has_y = any(field in fields_to_check for field in SPATIAL_Y_ALIASES)

    # Both x and y must be present
    if has_x and has_y:
        return True

    # Fallback: grid_cell or location_id
    if "grid_cell" in fields_to_check or "location_id" in fields_to_check:
        return True

    return False


@dataclass
class TelemetryKeyframe:
    """
    A keyframe snapshot for timeline seeking.
    Stored at regular intervals for efficient playback.
    """
    tick: int
    timestamp: str
    agent_states: Dict[str, Any]  # agent_id -> snapshot
    environment_state: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, float]] = None

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "timestamp": self.timestamp,
            "agent_states": self.agent_states,
            "environment_state": self.environment_state,
            "metrics": self.metrics,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TelemetryKeyframe":
        return cls(
            tick=data["tick"],
            timestamp=data["timestamp"],
            agent_states=data.get("agent_states", {}),
            environment_state=data.get("environment_state"),
            metrics=data.get("metrics"),
        )


@dataclass
class TelemetryDelta:
    """
    A delta entry between keyframes.
    Captures changes only, not full state.
    """
    tick: int
    agent_updates: List[Dict[str, Any]]  # List of agent changes
    events_triggered: List[str]  # Event type markers
    metrics: Dict[str, float]  # Tick metrics

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "updates": self.agent_updates,
            "events": self.events_triggered,
            "metrics": self.metrics,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TelemetryDelta":
        return cls(
            tick=data["tick"],
            agent_updates=data.get("updates", []),
            events_triggered=data.get("events", []),
            metrics=data.get("metrics", {}),
        )


@dataclass
class TelemetryIndex:
    """
    Index for fast telemetry queries.
    Enables efficient seeking and filtering.
    """
    tick_count: int
    keyframe_ticks: List[int]  # Ticks where keyframes exist
    event_index: List[Dict[str, Any]]  # [{tick, events}]
    region_index: Optional[Dict[str, List[int]]] = None  # region -> ticks
    segment_index: Optional[Dict[str, List[int]]] = None  # segment -> ticks

    def to_dict(self) -> dict:
        return {
            "tick_count": self.tick_count,
            "keyframe_ticks": self.keyframe_ticks,
            "event_timestamps": self.event_index,
            "region_index": self.region_index,
            "segment_index": self.segment_index,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TelemetryIndex":
        return cls(
            tick_count=data.get("tick_count", 0),
            keyframe_ticks=data.get("keyframe_ticks", []),
            event_index=data.get("event_timestamps", []),
            region_index=data.get("region_index"),
            segment_index=data.get("segment_index"),
        )


@dataclass
class TelemetryBlob:
    """
    Complete telemetry data for a run.
    Stored in object storage for replay.
    """
    run_id: str
    schema_version: str
    created_at: str
    ticks_executed: int
    seed_used: int
    agent_count: int
    keyframes: List[TelemetryKeyframe]
    deltas: List[TelemetryDelta]
    final_states: Dict[str, Any]
    index: TelemetryIndex
    metrics_summary: Dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "ticks_executed": self.ticks_executed,
            "seed_used": self.seed_used,
            "agent_count": self.agent_count,
            "keyframes": [k.to_dict() for k in self.keyframes],
            "deltas": [d.to_dict() for d in self.deltas],
            "final_states": self.final_states,
            "index": self.index.to_dict(),
            "metrics_summary": self.metrics_summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TelemetryBlob":
        return cls(
            run_id=data["run_id"],
            schema_version=data.get("schema_version", TelemetryVersion.V1_0_0.value),
            created_at=data["created_at"],
            ticks_executed=data.get("ticks_executed", 0),
            seed_used=data.get("seed_used", 0),
            agent_count=data.get("agent_count", 0),
            keyframes=[TelemetryKeyframe.from_dict(k) for k in data.get("keyframes", [])],
            deltas=[TelemetryDelta.from_dict(d) for d in data.get("deltas", [])],
            final_states=data.get("final_states", {}),
            index=TelemetryIndex.from_dict(data.get("index", {})),
            metrics_summary=data.get("metrics_summary", {}),
        )


@dataclass
class TelemetryQueryParams:
    """Parameters for telemetry queries."""
    tick_start: Optional[int] = None
    tick_end: Optional[int] = None
    regions: Optional[List[str]] = None
    segments: Optional[List[str]] = None
    event_types: Optional[List[str]] = None
    agent_ids: Optional[List[str]] = None
    include_keyframes: bool = True
    include_deltas: bool = True


@dataclass
class TelemetrySlice:
    """
    A slice of telemetry data for replay.
    Returned by query operations.
    """
    tick_start: int
    tick_end: int
    keyframes: List[TelemetryKeyframe]
    deltas: List[TelemetryDelta]
    total_ticks: int


@dataclass
class TelemetryIndexResult:
    """
    Result of telemetry index query for API.
    Phase 5: Added capabilities, telemetry_schema_version, total_agents, metric_keys.
    """
    total_ticks: int
    keyframe_ticks: List[int]
    event_types: List[str]
    agent_ids: List[str]
    storage_ref: Dict[str, Any]
    # Phase 5 additions
    capabilities: TelemetryCapabilities = field(default_factory=TelemetryCapabilities)
    telemetry_schema_version: str = TelemetryVersion.CURRENT.value
    total_agents: int = 0
    total_events: int = 0
    metric_keys: List[str] = field(default_factory=list)


@dataclass
class TelemetrySliceResult:
    """
    Result of telemetry slice query for API.
    Phase 5: Added normalized_positions, capabilities, telemetry_schema_version.
    """
    keyframes: List[TelemetryKeyframe]
    deltas: List[TelemetryDelta]
    events: List[Dict[str, Any]]
    # Phase 5 additions
    normalized_positions: List[Dict[str, Any]] = field(default_factory=list)
    capabilities: TelemetryCapabilities = field(default_factory=TelemetryCapabilities)
    telemetry_schema_version: str = TelemetryVersion.CURRENT.value


class TelemetryWriter:
    """
    Writes telemetry data during simulation execution.
    Used by RunExecutor to accumulate telemetry.
    """

    def __init__(self, run_id: str, keyframe_interval: int = 100):
        self.run_id = run_id
        self.keyframe_interval = keyframe_interval
        self.keyframes: List[TelemetryKeyframe] = []
        self.deltas: List[TelemetryDelta] = []
        self.event_index: List[Dict[str, Any]] = []
        self.region_ticks: Dict[str, List[int]] = {}
        self.segment_ticks: Dict[str, List[int]] = {}
        self.seed_used: int = 0
        self.agent_count: int = 0
        self.final_states: Dict[str, Any] = {}

    def set_metadata(self, seed: int, agent_count: int):
        """Set run metadata."""
        self.seed_used = seed
        self.agent_count = agent_count

    def write_keyframe(
        self,
        tick: int,
        agent_states: Dict[str, Any],
        environment_state: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None,
    ):
        """
        Write a keyframe snapshot.
        Called at keyframe intervals for efficient seeking.
        """
        keyframe = TelemetryKeyframe(
            tick=tick,
            timestamp=datetime.utcnow().isoformat(),
            agent_states=agent_states,
            environment_state=environment_state,
            metrics=metrics,
        )
        self.keyframes.append(keyframe)

    def write_delta(
        self,
        tick: int,
        agent_updates: List[Dict[str, Any]],
        events_triggered: List[str],
        metrics: Dict[str, float],
    ):
        """
        Write a delta entry for this tick.
        Captures changes since last tick.
        """
        delta = TelemetryDelta(
            tick=tick,
            agent_updates=agent_updates,
            events_triggered=events_triggered,
            metrics=metrics,
        )
        self.deltas.append(delta)

        # Update event index
        if events_triggered:
            self.event_index.append({
                "tick": tick,
                "events": events_triggered,
            })

    def write_region_tick(self, region: str, tick: int):
        """Track which ticks affected which regions."""
        if region not in self.region_ticks:
            self.region_ticks[region] = []
        self.region_ticks[region].append(tick)

    def write_segment_tick(self, segment: str, tick: int):
        """Track which ticks affected which segments."""
        if segment not in self.segment_ticks:
            self.segment_ticks[segment] = []
        self.segment_ticks[segment].append(tick)

    def set_final_states(self, states: Dict[str, Any]):
        """Set final agent states."""
        self.final_states = states

    def should_write_keyframe(self, tick: int) -> bool:
        """Check if we should write a keyframe at this tick."""
        return tick % self.keyframe_interval == 0

    def build_blob(self, metrics_summary: Optional[Dict[str, Any]] = None) -> TelemetryBlob:
        """
        Build the complete telemetry blob for storage.
        Called at end of simulation.
        """
        index = TelemetryIndex(
            tick_count=len(self.deltas),
            keyframe_ticks=[k.tick for k in self.keyframes],
            event_index=self.event_index,
            region_index=self.region_ticks if self.region_ticks else None,
            segment_index=self.segment_ticks if self.segment_ticks else None,
        )

        return TelemetryBlob(
            run_id=self.run_id,
            schema_version=TelemetryVersion.CURRENT.value,
            created_at=datetime.utcnow().isoformat(),
            ticks_executed=len(self.deltas),
            seed_used=self.seed_used,
            agent_count=self.agent_count,
            keyframes=self.keyframes,
            deltas=self.deltas,
            final_states=self.final_states,
            index=index,
            metrics_summary=metrics_summary or {},
        )


class TelemetryService:
    """
    Service for telemetry operations.
    Handles storage and read-only queries (C3 compliant).

    Reference: project.md §6.8
    """

    def __init__(self, storage: Optional[StorageService] = None):
        self.storage = storage or get_storage_service()

    # ================================================================
    # RUN-BASED LOOKUP METHODS (used by API endpoints)
    # These look up the telemetry_ref from Run.outputs, then delegate
    # to the storage-based methods below.
    # ================================================================

    async def _get_telemetry_ref_for_run(
        self,
        run_id: str,
        tenant_id: str,
    ) -> Optional[StorageRef]:
        """
        Look up the telemetry StorageRef for a run from the database.
        Returns None if run not found or no telemetry exists.
        """
        from sqlalchemy import select, text
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from app.core.config import settings

        # Create a fresh session for this lookup
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with AsyncSessionLocal() as db:
            query = text("""
                SELECT outputs
                FROM runs
                WHERE id = :run_id AND tenant_id = :tenant_id
            """)
            result = await db.execute(query, {
                "run_id": run_id,
                "tenant_id": tenant_id,
            })
            row = result.fetchone()

            if not row or not row.outputs:
                return None

            outputs = row.outputs
            telemetry_ref_dict = outputs.get("telemetry_ref")
            if not telemetry_ref_dict:
                return None

            return StorageRef.from_dict(telemetry_ref_dict)

    async def get_telemetry_index(
        self,
        run_id: str,
        tenant_id: str,
    ) -> Optional["TelemetryIndexResult"]:
        """
        Get telemetry index for a run by looking up its storage ref.
        Used by API endpoints.

        Phase 5: Now includes capabilities, telemetry_schema_version, total_agents, metric_keys.
        """
        storage_ref = await self._get_telemetry_ref_for_run(run_id, tenant_id)
        if not storage_ref:
            return None

        try:
            blob = await self.get_telemetry(storage_ref)
            blob_dict = blob.to_dict()

            # Phase 5: Detect capabilities from blob
            capabilities = detect_capabilities(blob_dict)

            # Collect event types
            event_types = list(set(
                evt for d in blob.deltas for evt in d.events_triggered
            ))

            # Collect metric keys
            metric_keys: List[str] = []
            if blob.metrics_summary:
                metric_keys.extend(blob.metrics_summary.keys())
            for delta in blob.deltas:
                for key in delta.metrics.keys():
                    if key not in metric_keys:
                        metric_keys.append(key)

            # Count total events
            total_events = sum(len(d.events_triggered) for d in blob.deltas)

            return TelemetryIndexResult(
                total_ticks=blob.ticks_executed,
                keyframe_ticks=[k.tick for k in blob.keyframes],
                event_types=event_types,
                agent_ids=list(blob.final_states.keys()) if blob.final_states else [],
                storage_ref=storage_ref.to_dict(),
                # Phase 5 additions
                capabilities=capabilities,
                telemetry_schema_version=blob.schema_version,
                total_agents=blob.agent_count,
                total_events=total_events,
                metric_keys=metric_keys,
            )
        except Exception:
            return None

    async def get_telemetry_slice(
        self,
        run_id: str,
        tenant_id: str,
        start_tick: int,
        end_tick: int,
        include_events: bool = True,
    ) -> Optional["TelemetrySliceResult"]:
        """
        Get a slice of telemetry data for a run.
        Used by API endpoints.

        Phase 5: Now includes normalized_positions, capabilities, telemetry_schema_version.
        """
        storage_ref = await self._get_telemetry_ref_for_run(run_id, tenant_id)
        if not storage_ref:
            return None

        try:
            blob = await self.get_telemetry(storage_ref)
            blob_dict = blob.to_dict()

            # Phase 5: Detect capabilities from blob
            capabilities = detect_capabilities(blob_dict)

            # Filter keyframes in range
            keyframes = [k for k in blob.keyframes if start_tick <= k.tick <= end_tick]

            # Filter deltas in range
            deltas = [d for d in blob.deltas if start_tick <= d.tick <= end_tick]

            # Phase 5: Extract normalized positions from keyframes
            normalized_positions: List[Dict[str, Any]] = []
            if capabilities.has_spatial and keyframes:
                # Use the last keyframe's agent states for positions
                last_keyframe = keyframes[-1] if keyframes else None
                if last_keyframe:
                    normalized_positions = extract_normalized_positions(
                        last_keyframe.agent_states
                    )

            # Extract events from deltas
            events = []
            if include_events:
                for delta in deltas:
                    for evt_type in delta.events_triggered:
                        events.append({
                            "tick": delta.tick,
                            "event_type": evt_type,
                            "timestamp": "",
                            "agent_id": None,
                            "data": {},
                        })

            return TelemetrySliceResult(
                keyframes=keyframes,
                deltas=deltas,
                events=events,
                # Phase 5 additions
                normalized_positions=normalized_positions,
                capabilities=capabilities,
                telemetry_schema_version=blob.schema_version,
            )
        except Exception:
            return None

    async def get_keyframe_at_tick_by_run(
        self,
        run_id: str,
        tick: int,
        tenant_id: str,
    ) -> Optional[TelemetryKeyframe]:
        """
        Get the closest keyframe at or before a tick for a run.
        Used by API endpoints.
        """
        storage_ref = await self._get_telemetry_ref_for_run(run_id, tenant_id)
        if not storage_ref:
            return None

        return await self.get_keyframe_at_tick(storage_ref, tick)

    async def get_telemetry_summary(
        self,
        run_id: str,
        tenant_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get telemetry summary for a run.
        Used by API endpoints.

        Phase 5: Now includes capabilities and telemetry_schema_version.
        """
        storage_ref = await self._get_telemetry_ref_for_run(run_id, tenant_id)
        if not storage_ref:
            return None

        try:
            blob = await self.get_telemetry(storage_ref)
            blob_dict = blob.to_dict()

            # Phase 5: Detect capabilities
            capabilities = detect_capabilities(blob_dict)

            # Count events by type
            event_type_counts: Dict[str, int] = {}
            total_events = 0
            for delta in blob.deltas:
                for evt_type in delta.events_triggered:
                    event_type_counts[evt_type] = event_type_counts.get(evt_type, 0) + 1
                    total_events += 1

            return {
                "total_ticks": blob.ticks_executed,
                "total_events": total_events,
                "total_agents": blob.agent_count,
                "event_type_counts": event_type_counts,
                "key_metrics": blob.metrics_summary,
                "duration_seconds": 0.0,  # Would need timing data
                # Phase 5 additions
                "capabilities": capabilities.to_dict(),
                "telemetry_schema_version": blob.schema_version,
            }
        except Exception:
            return None

    async def get_telemetry_by_run(
        self,
        run_id: str,
        tenant_id: str,
    ) -> Optional[TelemetryBlob]:
        """
        Get full telemetry blob for a run.
        Used by API endpoints.
        """
        storage_ref = await self._get_telemetry_ref_for_run(run_id, tenant_id)
        if not storage_ref:
            return None

        try:
            return await self.get_telemetry(storage_ref)
        except Exception:
            return None

    async def get_agent_history(
        self,
        run_id: str,
        agent_id: str,
        tenant_id: str,
        start_tick: int = 0,
        end_tick: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get state history for a specific agent.
        Used by API endpoints.
        """
        storage_ref = await self._get_telemetry_ref_for_run(run_id, tenant_id)
        if not storage_ref:
            return []

        try:
            blob = await self.get_telemetry(storage_ref)

            history = []
            for keyframe in blob.keyframes:
                if keyframe.tick < start_tick:
                    continue
                if end_tick is not None and keyframe.tick > end_tick:
                    break
                if agent_id in keyframe.agent_states:
                    history.append({
                        "tick": keyframe.tick,
                        "state": keyframe.agent_states[agent_id],
                        "beliefs": None,
                        "last_action": None,
                        "metrics": keyframe.metrics,
                    })

            return history
        except Exception:
            return []

    async def get_events_by_type(
        self,
        run_id: str,
        tenant_id: str,
        event_type: Optional[str] = None,
        agent_id: Optional[str] = None,
        start_tick: int = 0,
        end_tick: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get events filtered by type and other criteria.
        Used by API endpoints.
        """
        storage_ref = await self._get_telemetry_ref_for_run(run_id, tenant_id)
        if not storage_ref:
            return []

        try:
            blob = await self.get_telemetry(storage_ref)

            events = []
            for delta in blob.deltas:
                if delta.tick < start_tick:
                    continue
                if end_tick is not None and delta.tick > end_tick:
                    break

                for evt_type in delta.events_triggered:
                    if event_type and evt_type != event_type:
                        continue

                    events.append({
                        "tick": delta.tick,
                        "event_type": evt_type,
                        "timestamp": "",
                        "agent_id": agent_id,
                        "data": {},
                    })

                    if len(events) >= limit:
                        return events

            return events
        except Exception:
            return []

    async def get_aggregated_metrics(
        self,
        run_id: str,
        tenant_id: str,
        metric_names: Optional[List[str]] = None,
        aggregation: str = "mean",
        group_by_tick: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Get aggregated metrics from telemetry.
        Used by API endpoints.
        """
        storage_ref = await self._get_telemetry_ref_for_run(run_id, tenant_id)
        if not storage_ref:
            return None

        try:
            blob = await self.get_telemetry(storage_ref)

            if group_by_tick:
                # Return metrics per tick
                return {
                    "by_tick": [
                        {"tick": d.tick, "metrics": d.metrics}
                        for d in blob.deltas
                    ]
                }

            # Aggregate across all ticks
            all_metrics: Dict[str, List[float]] = {}
            for delta in blob.deltas:
                for key, value in delta.metrics.items():
                    if metric_names and key not in metric_names:
                        continue
                    if key not in all_metrics:
                        all_metrics[key] = []
                    if isinstance(value, (int, float)):
                        all_metrics[key].append(float(value))

            # Apply aggregation
            result = {}
            for key, values in all_metrics.items():
                if not values:
                    continue
                if aggregation == "mean":
                    result[key] = sum(values) / len(values)
                elif aggregation == "sum":
                    result[key] = sum(values)
                elif aggregation == "min":
                    result[key] = min(values)
                elif aggregation == "max":
                    result[key] = max(values)
                elif aggregation == "std":
                    mean = sum(values) / len(values)
                    variance = sum((v - mean) ** 2 for v in values) / len(values)
                    result[key] = variance ** 0.5

            return result
        except Exception:
            return None

    # ================================================================
    # WRITE OPERATIONS (used by RunExecutor)
    # ================================================================

    async def store_telemetry(
        self,
        tenant_id: str,
        run_id: str,
        telemetry: TelemetryBlob,
        compress: bool = True,
    ) -> StorageRef:
        """
        Store complete telemetry blob to object storage.
        Called at end of simulation run.
        """
        return await self.storage.store_telemetry(
            tenant_id=tenant_id,
            telemetry_id=run_id,
            data=telemetry.to_dict(),
            compress=compress,
        )

    async def store_from_execution_result(
        self,
        tenant_id: str,
        run_id: str,
        execution_result: dict,
        compress: bool = True,
    ) -> StorageRef:
        """
        Convert execution result to telemetry blob and store.
        Used by run_executor for backward compatibility.
        """
        # Build keyframes from agent snapshots
        keyframes = []
        agent_snapshots = execution_result.get("agent_snapshots", {})
        for tick_str, snapshot in sorted(agent_snapshots.items(), key=lambda x: int(x[0])):
            keyframes.append(TelemetryKeyframe(
                tick=int(tick_str),
                timestamp=datetime.utcnow().isoformat(),
                agent_states=snapshot,
            ))

        # Build deltas from tick data
        deltas = []
        event_index = []
        tick_data = execution_result.get("tick_data", [])
        for entry in tick_data:
            tick = entry.get("tick", 0)
            events = entry.get("events_triggered", [])
            deltas.append(TelemetryDelta(
                tick=tick,
                agent_updates=entry.get("agent_updates", []),
                events_triggered=events,
                metrics=entry.get("metrics", {}),
            ))
            if events:
                event_index.append({"tick": tick, "events": events})

        # Build index
        index = TelemetryIndex(
            tick_count=execution_result.get("ticks_executed", 0),
            keyframe_ticks=list(agent_snapshots.keys()),
            event_index=event_index,
        )

        # Build blob
        blob = TelemetryBlob(
            run_id=run_id,
            schema_version=TelemetryVersion.CURRENT.value,
            created_at=datetime.utcnow().isoformat(),
            ticks_executed=execution_result.get("ticks_executed", 0),
            seed_used=execution_result.get("seed_used", 0),
            agent_count=execution_result.get("agent_count", 0),
            keyframes=keyframes,
            deltas=deltas,
            final_states=execution_result.get("final_agent_states", {}),
            index=index,
            metrics_summary={
                "by_tick": execution_result.get("metrics_by_tick", []),
                "outcome_distribution": execution_result.get("outcome_distribution", {}),
            },
        )

        return await self.store_telemetry(tenant_id, run_id, blob, compress)

    # ================================================================
    # READ OPERATIONS (READ-ONLY per C3 - NEVER triggers simulation)
    # ================================================================

    async def get_telemetry(
        self,
        storage_ref: StorageRef,
    ) -> TelemetryBlob:
        """
        Retrieve complete telemetry blob.
        READ-ONLY operation (C3 compliant).
        """
        data = await self.storage.get_telemetry(storage_ref)
        return TelemetryBlob.from_dict(data)

    async def get_telemetry_by_ref_dict(
        self,
        ref_dict: dict,
    ) -> TelemetryBlob:
        """
        Retrieve telemetry using reference dictionary.
        READ-ONLY operation (C3 compliant).
        """
        storage_ref = StorageRef.from_dict(ref_dict)
        return await self.get_telemetry(storage_ref)

    async def query_telemetry(
        self,
        storage_ref: StorageRef,
        params: TelemetryQueryParams,
    ) -> TelemetrySlice:
        """
        Query a slice of telemetry data.
        READ-ONLY operation (C3 compliant).

        Supports:
        - Tick range filtering
        - Event type filtering
        - Agent ID filtering

        Reference: project.md §6.8 (Query hooks)
        """
        blob = await self.get_telemetry(storage_ref)

        # Apply tick range filter
        tick_start = params.tick_start or 0
        tick_end = params.tick_end or blob.ticks_executed

        # Filter keyframes
        keyframes = []
        if params.include_keyframes:
            for kf in blob.keyframes:
                if tick_start <= kf.tick <= tick_end:
                    # Filter by agent IDs if specified
                    if params.agent_ids:
                        filtered_states = {
                            aid: state for aid, state in kf.agent_states.items()
                            if aid in params.agent_ids
                        }
                        keyframes.append(TelemetryKeyframe(
                            tick=kf.tick,
                            timestamp=kf.timestamp,
                            agent_states=filtered_states,
                            environment_state=kf.environment_state,
                            metrics=kf.metrics,
                        ))
                    else:
                        keyframes.append(kf)

        # Filter deltas
        deltas = []
        if params.include_deltas:
            for delta in blob.deltas:
                if tick_start <= delta.tick <= tick_end:
                    # Filter by event types if specified
                    if params.event_types:
                        matching_events = [
                            e for e in delta.events_triggered
                            if e in params.event_types
                        ]
                        if matching_events or not params.event_types:
                            deltas.append(TelemetryDelta(
                                tick=delta.tick,
                                agent_updates=delta.agent_updates,
                                events_triggered=matching_events,
                                metrics=delta.metrics,
                            ))
                    else:
                        deltas.append(delta)

        return TelemetrySlice(
            tick_start=tick_start,
            tick_end=tick_end,
            keyframes=keyframes,
            deltas=deltas,
            total_ticks=blob.ticks_executed,
        )

    async def get_keyframe_at_tick(
        self,
        storage_ref: StorageRef,
        tick: int,
    ) -> Optional[TelemetryKeyframe]:
        """
        Get the closest keyframe at or before the specified tick.
        Useful for seeking in replay.
        READ-ONLY operation (C3 compliant).
        """
        blob = await self.get_telemetry(storage_ref)

        # Find closest keyframe at or before tick
        closest: Optional[TelemetryKeyframe] = None
        for kf in blob.keyframes:
            if kf.tick <= tick:
                if closest is None or kf.tick > closest.tick:
                    closest = kf
            else:
                break

        return closest

    async def get_deltas_in_range(
        self,
        storage_ref: StorageRef,
        tick_start: int,
        tick_end: int,
    ) -> List[TelemetryDelta]:
        """
        Get all deltas in a tick range.
        Used for replaying from a keyframe.
        READ-ONLY operation (C3 compliant).
        """
        blob = await self.get_telemetry(storage_ref)
        return [
            d for d in blob.deltas
            if tick_start <= d.tick <= tick_end
        ]

    async def get_events_by_type(
        self,
        storage_ref: StorageRef,
        event_types: List[str],
    ) -> List[Tuple[int, List[str]]]:
        """
        Find all ticks where specific event types occurred.
        READ-ONLY operation (C3 compliant).
        """
        blob = await self.get_telemetry(storage_ref)
        results = []

        for entry in blob.index.event_index:
            matching = [e for e in entry.get("events", []) if e in event_types]
            if matching:
                results.append((entry["tick"], matching))

        return results

    async def get_metrics_summary(
        self,
        storage_ref: StorageRef,
    ) -> Dict[str, Any]:
        """
        Get metrics summary for quick overview.
        READ-ONLY operation (C3 compliant).
        """
        blob = await self.get_telemetry(storage_ref)
        return blob.metrics_summary

    async def get_final_states(
        self,
        storage_ref: StorageRef,
        agent_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get final agent states.
        Optionally filtered by agent IDs.
        READ-ONLY operation (C3 compliant).
        """
        blob = await self.get_telemetry(storage_ref)

        if agent_ids:
            return {
                aid: state for aid, state in blob.final_states.items()
                if aid in agent_ids
            }
        return blob.final_states

    async def get_signed_download_url(
        self,
        storage_ref: StorageRef,
        expires_in: int = 3600,
    ) -> str:
        """
        Get a signed URL for downloading telemetry.
        Reference: project.md §8.4 (short-lived signed URLs)
        READ-ONLY operation (C3 compliant).
        """
        return await self.storage.get_signed_download_url(storage_ref, expires_in)

    # ================================================================
    # INTEGRITY OPERATIONS (§6.2 Telemetry Sufficiency & Integrity)
    # ================================================================

    def compute_telemetry_hash(self, blob: TelemetryBlob) -> str:
        """
        Compute SHA256 hash of telemetry data for integrity verification.
        §6.2: telemetry_hash must be stable across queries.

        Hash is computed from:
        - run_id
        - ticks_executed
        - seed_used
        - agent_count
        - sorted keyframe ticks
        - sorted delta metrics
        - final_states hash

        This ensures deterministic hash without including timestamps.
        """
        import hashlib
        import json

        # Build canonical representation (excluding timestamps for stability)
        canonical = {
            "run_id": blob.run_id,
            "schema_version": blob.schema_version,
            "ticks_executed": blob.ticks_executed,
            "seed_used": blob.seed_used,
            "agent_count": blob.agent_count,
            "keyframe_ticks": sorted(k.tick for k in blob.keyframes),
            "delta_count": len(blob.deltas),
            "final_states_keys": sorted(blob.final_states.keys()),
            "metrics_summary_keys": sorted(blob.metrics_summary.keys()) if blob.metrics_summary else [],
        }

        # Add aggregated metrics from deltas for verification
        total_events = sum(len(d.events_triggered) for d in blob.deltas)
        total_updates = sum(len(d.agent_updates) for d in blob.deltas)
        canonical["total_events_triggered"] = total_events
        canonical["total_agent_updates"] = total_updates

        # Compute hash
        canonical_json = json.dumps(canonical, sort_keys=True)
        return hashlib.sha256(canonical_json.encode()).hexdigest()

    def check_replay_integrity(
        self,
        blob: TelemetryBlob,
        expected_ticks: int,
    ) -> Tuple[str, bool, List[str]]:
        """
        Check telemetry integrity and completeness for replay.
        §6.2: replay_degraded flag if telemetry is incomplete.

        Args:
            blob: The telemetry blob to check
            expected_ticks: Expected number of ticks from RunConfig

        Returns:
            Tuple of (telemetry_hash, replay_degraded, issues)
        """
        issues = []
        replay_degraded = False

        # Check tick count matches expected
        if blob.ticks_executed < expected_ticks:
            issues.append(f"Incomplete: executed {blob.ticks_executed}/{expected_ticks} ticks")
            replay_degraded = True

        # Check keyframes exist for seeking
        if not blob.keyframes:
            issues.append("No keyframes available for seeking")
            replay_degraded = True
        else:
            # Check keyframe coverage (should have at least start and near-end)
            keyframe_ticks = [k.tick for k in blob.keyframes]
            if 0 not in keyframe_ticks and min(keyframe_ticks) > 10:
                issues.append("Missing early keyframe for replay start")
                replay_degraded = True

        # Check deltas exist
        if not blob.deltas:
            issues.append("No deltas available for replay")
            replay_degraded = True

        # Check delta continuity (no gaps)
        delta_ticks = sorted(d.tick for d in blob.deltas)
        if delta_ticks:
            expected_sequence = list(range(delta_ticks[0], delta_ticks[-1] + 1))
            if delta_ticks != expected_sequence:
                missing = set(expected_sequence) - set(delta_ticks)
                if len(missing) > 5:
                    issues.append(f"Delta gaps detected: {len(missing)} missing ticks")
                    replay_degraded = True

        # Check final states exist
        if not blob.final_states:
            issues.append("No final states recorded")
            # Not critical for replay, just noting

        # Compute hash
        telemetry_hash = self.compute_telemetry_hash(blob)

        return telemetry_hash, replay_degraded, issues

    async def get_telemetry_proof(
        self,
        storage_ref: StorageRef,
        expected_ticks: int,
    ) -> "TelemetryProofData":
        """
        Generate telemetry proof data for Evidence Pack.
        §6.2: Telemetry Sufficiency & Integrity proof.

        Returns:
            TelemetryProofData with hash, integrity status, and metrics
        """
        blob = await self.get_telemetry(storage_ref)
        telemetry_hash, replay_degraded, issues = self.check_replay_integrity(
            blob, expected_ticks
        )

        return TelemetryProofData(
            telemetry_ref=storage_ref.to_dict(),
            keyframe_count=len(blob.keyframes),
            delta_count=len(blob.deltas),
            total_events=sum(len(d.events_triggered) for d in blob.deltas),
            telemetry_hash=telemetry_hash,
            is_complete=not replay_degraded,
            replay_degraded=replay_degraded,
            integrity_issues=issues,
        )


@dataclass
class TelemetryProofData:
    """
    §6.2 Telemetry proof data for Evidence Pack.
    Proves telemetry integrity and replay capability.
    """
    telemetry_ref: Dict[str, Any]
    keyframe_count: int
    delta_count: int
    total_events: int
    telemetry_hash: str
    is_complete: bool
    replay_degraded: bool
    integrity_issues: List[str] = field(default_factory=list)


# Singleton instance
_telemetry_service: Optional[TelemetryService] = None


def get_telemetry_service() -> TelemetryService:
    """Get the telemetry service instance."""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
    return _telemetry_service


def create_telemetry_writer(run_id: str, keyframe_interval: int = 100) -> TelemetryWriter:
    """Create a new telemetry writer for a run."""
    return TelemetryWriter(run_id=run_id, keyframe_interval=keyframe_interval)
