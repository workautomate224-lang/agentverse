"""
Telemetry Index Model - PHASE 5: Telemetry Standardization

Stores metadata about telemetry for efficient querying without loading full blob.
Enables capabilities-based UI rendering and schema version tracking.

Reference: Phase 5 - Telemetry Standardization + Spatial Replay Enablement
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TelemetryCapabilities:
    """Capability flags for telemetry data."""

    @staticmethod
    def default() -> Dict[str, bool]:
        return {
            "has_spatial": False,
            "has_events": False,
            "has_metrics": False,
        }


class TelemetryIndex(Base):
    """
    Stores metadata about telemetry for efficient querying.

    Purpose:
    - Schema versioning for forward compatibility
    - Capabilities flags (has_spatial, has_events, has_metrics) for UI enablement
    - Quick access to index data without loading full telemetry blob
    - Storage reference tracking

    Key Properties:
    - One TelemetryIndex per Run (unique run_id)
    - Capabilities computed from telemetry data
    - Links to storage via storage_ref JSON
    - Immutable once created (C1 compliant)
    """

    __tablename__ = "telemetry_index"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Multi-tenancy
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Foreign key to run
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Schema version
    schema_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="v1",
    )

    # Storage reference (points to S3/object storage)
    storage_ref: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Index data (for quick access)
    total_ticks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    keyframe_ticks: Mapped[List[int]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    agent_ids: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Capabilities flags (critical for UI enablement)
    capabilities: Mapped[Dict[str, bool]] = mapped_column(
        JSONB,
        nullable=False,
        default=TelemetryCapabilities.default,
    )

    # Summary stats
    total_agents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    total_events: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    metric_keys: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Integrity
    telemetry_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )

    is_complete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Indexes
    __table_args__ = (
        Index("ix_telemetry_index_tenant_id", "tenant_id"),
        Index("ix_telemetry_index_run_id", "run_id"),
        Index("ix_telemetry_index_tenant_run", "tenant_id", "run_id"),
        UniqueConstraint("run_id", name="uq_telemetry_index_run_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<TelemetryIndex(id={self.id}, run_id={self.run_id}, "
            f"total_ticks={self.total_ticks}, capabilities={self.capabilities})>"
        )

    @classmethod
    def from_telemetry_blob(
        cls,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        blob_dict: Dict[str, Any],
        storage_ref: Optional[Dict[str, Any]] = None,
        telemetry_hash: Optional[str] = None,
    ) -> "TelemetryIndex":
        """
        Create a TelemetryIndex from a telemetry blob.

        Args:
            tenant_id: Tenant ID
            run_id: Run ID
            blob_dict: Telemetry blob as dictionary
            storage_ref: Optional storage reference
            telemetry_hash: Optional integrity hash

        Returns:
            New TelemetryIndex instance
        """
        # Extract basic info
        total_ticks = blob_dict.get("ticks_executed", 0)
        agent_count = blob_dict.get("agent_count", 0)

        # Extract keyframe ticks
        keyframes = blob_dict.get("keyframes", [])
        keyframe_ticks = [kf.get("tick", 0) for kf in keyframes if isinstance(kf, dict)]

        # Extract agent IDs from final states
        final_states = blob_dict.get("final_states", {})
        agent_ids = list(final_states.keys()) if final_states else []

        # Detect capabilities
        capabilities = cls._detect_capabilities(blob_dict)

        # Count events
        deltas = blob_dict.get("deltas", [])
        total_events = sum(
            len(d.get("events", [])) for d in deltas if isinstance(d, dict)
        )

        # Extract metric keys
        metrics_summary = blob_dict.get("metrics_summary", {})
        metric_keys = list(metrics_summary.keys()) if isinstance(metrics_summary, dict) else []

        # Add metric keys from deltas
        for delta in deltas:
            if isinstance(delta, dict) and "metrics" in delta:
                delta_metrics = delta.get("metrics", {})
                if isinstance(delta_metrics, dict):
                    for key in delta_metrics.keys():
                        if key not in metric_keys:
                            metric_keys.append(key)

        return cls(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            run_id=run_id,
            schema_version=blob_dict.get("schema_version", "v1"),
            storage_ref=storage_ref,
            total_ticks=total_ticks,
            keyframe_ticks=keyframe_ticks,
            agent_ids=agent_ids,
            capabilities=capabilities,
            total_agents=agent_count or len(agent_ids),
            total_events=total_events,
            metric_keys=metric_keys,
            telemetry_hash=telemetry_hash,
            is_complete=True,
            created_at=datetime.utcnow(),
        )

    @staticmethod
    def _detect_capabilities(blob_dict: Dict[str, Any]) -> Dict[str, bool]:
        """
        Detect capabilities from telemetry blob.

        Checks for:
        - has_spatial: Agent states contain position data (x, y, position_x, etc.)
        - has_events: Any events were triggered during simulation
        - has_metrics: Metrics were recorded
        """
        capabilities = TelemetryCapabilities.default()

        # Check for events
        deltas = blob_dict.get("deltas", [])
        for delta in deltas:
            if isinstance(delta, dict):
                events = delta.get("events", [])
                if events:
                    capabilities["has_events"] = True

                metrics = delta.get("metrics", {})
                if metrics and isinstance(metrics, dict) and len(metrics) > 0:
                    capabilities["has_metrics"] = True

        # Check for spatial data in keyframes
        keyframes = blob_dict.get("keyframes", [])
        for keyframe in keyframes:
            if isinstance(keyframe, dict):
                agent_states = keyframe.get("agent_states", {})
                for agent_id, agent_state in agent_states.items():
                    if isinstance(agent_state, dict):
                        if TelemetryIndex._has_spatial_fields(agent_state):
                            capabilities["has_spatial"] = True
                            break
                if capabilities["has_spatial"]:
                    break

        # Also check final states for spatial data
        if not capabilities["has_spatial"]:
            final_states = blob_dict.get("final_states", {})
            for agent_id, agent_state in final_states.items():
                if isinstance(agent_state, dict):
                    if TelemetryIndex._has_spatial_fields(agent_state):
                        capabilities["has_spatial"] = True
                        break

        return capabilities

    @staticmethod
    def _has_spatial_fields(agent_state: Dict[str, Any]) -> bool:
        """
        Check if agent state contains spatial position fields.

        Supports detection of:
        - x, y
        - position_x, position_y
        - pos_x, pos_y
        - coord_x, coord_y
        - loc_x, loc_y
        - grid_cell
        - location_id
        """
        # Check variables dict if present
        variables = agent_state.get("variables", {})
        if not isinstance(variables, dict):
            variables = {}

        # Merge top-level fields with variables for checking
        fields_to_check = {**agent_state, **variables}

        # X-field patterns
        x_fields = ["x", "position_x", "pos_x", "coord_x", "loc_x"]
        # Y-field patterns
        y_fields = ["y", "position_y", "pos_y", "coord_y", "loc_y"]

        has_x = any(field in fields_to_check for field in x_fields)
        has_y = any(field in fields_to_check for field in y_fields)

        # Both x and y must be present
        if has_x and has_y:
            return True

        # Fallback: grid_cell or location_id
        if "grid_cell" in fields_to_check or "location_id" in fields_to_check:
            return True

        return False

    def to_api_response(self) -> Dict[str, Any]:
        """
        Convert to API response format matching TelemetryIndexResponse.
        """
        return {
            "run_id": str(self.run_id),
            "total_ticks": self.total_ticks,
            "keyframe_ticks": self.keyframe_ticks,
            "agent_ids": self.agent_ids,
            "storage_ref": self.storage_ref or {},
            "telemetry_schema_version": self.schema_version,
            "capabilities": self.capabilities,
            "total_agents": self.total_agents,
            "total_events": self.total_events,
            "metric_keys": self.metric_keys,
        }
