"""
Node & Edge Models (Universe Map)
Reference: project.md §6.7

Nodes are parallel-universe snapshots. Edges are transformations.
Fork-not-mutate: Changes create new nodes, never edit existing ones.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.project_spec import ProjectSpec
    from app.models.run_config import RunConfig


class InterventionType(str, Enum):
    """Types of interventions that create edges."""
    EVENT_SCRIPT = "event_script"
    VARIABLE_DELTA = "variable_delta"
    NL_QUERY = "nl_query"
    EXPANSION = "expansion"


class ExpansionStrategy(str, Enum):
    """Strategies for auto-expansion of nodes."""
    USER_ASK = "user_ask"
    AUTO_EXPLORE = "auto_explore"
    SENSITIVITY = "sensitivity"


class ConfidenceLevel(str, Enum):
    """Confidence levels for node outcomes."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# Node Model (project.md §6.7)
# =============================================================================

class Node(Base):
    """
    A node in the Universe Map - represents a parallel-universe snapshot.

    Nodes are IMMUTABLE after creation (fork-not-mutate principle C1).
    To change outcomes, fork a new node from the parent.
    """
    __tablename__ = "nodes"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Tree structure (fork-not-mutate)
    parent_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Scenario definition
    scenario_patch_ref: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Run references (1+ runs aggregated)
    run_refs: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    # Aggregated outcomes
    aggregated_outcome: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Probability (conditional to parent)
    probability: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    cumulative_probability: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )

    # Confidence/reliability
    confidence: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Telemetry reference for replay
    telemetry_ref: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Clustering
    cluster_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    is_cluster_representative: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # UI state hints (not authoritative)
    ui_position: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    is_collapsed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Metadata
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(100)), nullable=True)

    # Status flags
    is_baseline: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    is_explored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    child_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    parent: Mapped[Optional["Node"]] = relationship(
        "Node",
        remote_side=[id],
        back_populates="children",
        foreign_keys=[parent_node_id]
    )
    children: Mapped[List["Node"]] = relationship(
        "Node",
        back_populates="parent",
        foreign_keys=[parent_node_id]
    )
    outgoing_edges: Mapped[List["Edge"]] = relationship(
        "Edge",
        back_populates="from_node",
        foreign_keys="Edge.from_node_id"
    )
    incoming_edges: Mapped[List["Edge"]] = relationship(
        "Edge",
        back_populates="to_node",
        foreign_keys="Edge.to_node_id"
    )
    runs: Mapped[List["Run"]] = relationship(
        "Run",
        back_populates="node"
    )
    project: Mapped["ProjectSpec"] = relationship(
        "ProjectSpec",
        back_populates="nodes",
        foreign_keys=[project_id]
    )

    def __repr__(self) -> str:
        return f"<Node {self.id} depth={self.depth} label={self.label}>"

    def to_summary(self) -> Dict[str, Any]:
        """Return a lightweight summary for list views."""
        return {
            "node_id": str(self.id),
            "parent_node_id": str(self.parent_node_id) if self.parent_node_id else None,
            "label": self.label,
            "probability": self.probability,
            "confidence_level": self.confidence.get("confidence_level", "medium"),
            "is_baseline": self.is_baseline,
            "has_outcome": self.aggregated_outcome is not None,
            "child_count": self.child_count,
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# Edge Model (project.md §6.7)
# =============================================================================

class Edge(Base):
    """
    An edge in the Universe Map - represents a transformation from one node to another.

    Edges explain WHY a branch exists and WHAT intervention created it.
    """
    __tablename__ = "edges"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Connections
    from_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    to_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Intervention details
    intervention: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Explanation
    explanation: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Metadata
    is_primary_path: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    from_node: Mapped["Node"] = relationship(
        "Node",
        back_populates="outgoing_edges",
        foreign_keys=[from_node_id]
    )
    to_node: Mapped["Node"] = relationship(
        "Node",
        back_populates="incoming_edges",
        foreign_keys=[to_node_id]
    )

    def __repr__(self) -> str:
        return f"<Edge {self.id} {self.from_node_id} -> {self.to_node_id}>"

    def to_summary(self) -> Dict[str, Any]:
        """Return a lightweight summary for list views."""
        return {
            "edge_id": str(self.id),
            "from_node_id": str(self.from_node_id),
            "to_node_id": str(self.to_node_id),
            "short_label": self.explanation.get("short_label", ""),
            "intervention_type": self.intervention.get("intervention_type", "unknown"),
        }


# =============================================================================
# Node Cluster Model
# =============================================================================

class NodeCluster(Base):
    """
    A cluster of similar nodes for progressive expansion.

    Clustering prevents the UI from being overwhelmed by thousands of nodes.
    """
    __tablename__ = "node_clusters"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Cluster properties
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Member nodes
    member_node_ids: Mapped[List[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    representative_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False
    )

    # Aggregated cluster outcome
    cluster_outcome: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    cluster_probability: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )

    # Expansion state
    is_expanded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expandable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # UI position
    ui_position: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    representative_node: Mapped["Node"] = relationship("Node")

    def __repr__(self) -> str:
        return f"<NodeCluster {self.id} label={self.label}>"


# =============================================================================
# Run Model (project.md §6.6)
# =============================================================================

class RunStatus(str, Enum):
    """Status of a simulation run."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggeredBy(str, Enum):
    """Who/what triggered the run."""
    USER = "user"
    SYSTEM = "system"
    SCHEDULE = "schedule"
    API = "api"


class Run(Base):
    """
    A simulation run - the actual execution of a simulation.

    Runs are associated with nodes and produce telemetry for replay.
    """
    __tablename__ = "runs"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Config reference
    run_config_ref: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("run_configs.id", ondelete="CASCADE"),
        nullable=False
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default=RunStatus.QUEUED.value, nullable=False, index=True
    )

    # Timing
    timing: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Outputs (populated when succeeded)
    outputs: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Error (populated when failed)
    error: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Seed used (for reproducibility)
    actual_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Worker info
    worker_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Metadata
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    triggered_by: Mapped[str] = mapped_column(
        String(20), default=TriggeredBy.USER.value, nullable=False
    )
    triggered_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    node: Mapped["Node"] = relationship("Node", back_populates="runs")
    project: Mapped["ProjectSpec"] = relationship(
        "ProjectSpec",
        back_populates="runs",
        foreign_keys=[project_id]
    )
    run_config: Mapped["RunConfig"] = relationship(
        "RunConfig",
        back_populates="runs",
        foreign_keys=[run_config_ref]
    )

    def __repr__(self) -> str:
        return f"<Run {self.id} status={self.status}>"
