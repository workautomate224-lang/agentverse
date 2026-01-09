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
    CURRENT = "1.0.0"


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
