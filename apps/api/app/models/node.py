"""
Node & Edge Models (Universe Map)
Reference: project.md §6.7

Nodes are parallel-universe snapshots. Edges are transformations.
Fork-not-mutate: Changes create new nodes, never edit existing ones.

STEP 4: Universe Map as Real Versioned World Graph
- Each Node must be backed by multiple runs (ensemble)
- NodePatch stores structured delta from parent
- Aggregated outcomes computed from all runs
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


class AggregationMethod(str, Enum):
    """STEP 4: Methods for aggregating multiple run outcomes."""
    MEAN = "mean"
    WEIGHTED_MEAN = "weighted_mean"
    MEDIAN = "median"
    MODE = "mode"


# =============================================================================
# NodePatch Model (STEP 4: Structured delta from parent)
# =============================================================================

class NodePatch(Base):
    """
    STEP 4: Structured patch describing what changed from parent node.

    This is NOT a UI-only concept - it's a real data object that:
    1. Describes what was changed (event / variable)
    2. Stores magnitude and parameters
    3. Lists affected variables
    4. Is used to generate RunSpec from parent state
    """
    __tablename__ = "node_patches"

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
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # What was changed
    patch_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Type of change: event_injection, variable_delta, environment_override, agent_modification"
    )

    # Structured change description
    change_description: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="STEP 4: Structured description of what changed"
    )

    # Magnitude and parameters
    parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="STEP 4: Magnitude, timing, and other parameters of the change"
    )

    # Affected variables (for dependency tracking)
    affected_variables: Mapped[List[str]] = mapped_column(
        ARRAY(String(100)), nullable=False, default=list,
        comment="STEP 4: List of variables affected by this patch"
    )

    # Environment overrides (applied to parent environment_spec)
    environment_overrides: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
        comment="STEP 4: Overrides to apply to parent environment_spec"
    )

    # Event injection (if patch_type is event_injection)
    event_script: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
        comment="STEP 4: Event script to inject at specified tick (DEPRECATED: use event_script_id)"
    )

    # STEP 5: Proper FK reference to EventScript for audit trail
    event_script_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_scripts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="STEP 5: FK reference to EventScript (replaces JSONB copy)"
    )

    # Natural language description for audit trail
    nl_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Human-readable description of the change"
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    node: Mapped["Node"] = relationship("Node", back_populates="node_patch")

    def __repr__(self) -> str:
        return f"<NodePatch {self.id} type={self.patch_type}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation for RunSpec generation."""
        return {
            "id": str(self.id),
            "node_id": str(self.node_id),
            "patch_type": self.patch_type,
            "change_description": self.change_description,
            "parameters": self.parameters,
            "affected_variables": self.affected_variables,
            "environment_overrides": self.environment_overrides,
            "event_script": self.event_script,
            # STEP 5: Include FK reference
            "event_script_id": str(self.event_script_id) if self.event_script_id else None,
            "nl_description": self.nl_description,
        }

    def apply_to_environment(self, parent_env: Dict[str, Any]) -> Dict[str, Any]:
        """
        STEP 4: Apply this patch to parent environment to generate child environment.

        This is how RunSpec is generated from parent state + patch.
        """
        import copy
        child_env = copy.deepcopy(parent_env)

        # Apply environment overrides
        if self.environment_overrides:
            for key, value in self.environment_overrides.items():
                if isinstance(value, dict) and isinstance(child_env.get(key), dict):
                    # Merge nested dicts
                    child_env[key] = {**child_env.get(key, {}), **value}
                else:
                    child_env[key] = value

        # Apply variable deltas from parameters
        if self.parameters.get("variable_deltas"):
            for var_name, delta in self.parameters["variable_deltas"].items():
                if var_name in child_env:
                    if isinstance(delta, dict) and delta.get("operation") == "multiply":
                        child_env[var_name] = child_env[var_name] * delta.get("factor", 1.0)
                    elif isinstance(delta, dict) and delta.get("operation") == "add":
                        child_env[var_name] = child_env[var_name] + delta.get("value", 0)
                    elif isinstance(delta, dict) and delta.get("operation") == "set":
                        child_env[var_name] = delta.get("value")
                    else:
                        # Direct replacement
                        child_env[var_name] = delta

        return child_env


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

    # ==========================================================================
    # STEP 4: Ensemble Run Tracking
    # Each node must be backed by multiple runs (at least 2 for MVP)
    # ==========================================================================
    min_ensemble_size: Mapped[int] = mapped_column(
        Integer, default=2, nullable=False,
        comment="STEP 4: Minimum number of runs required for this node"
    )
    completed_run_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="STEP 4: Number of completed runs for this node"
    )
    is_ensemble_complete: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="STEP 4: True when completed_run_count >= min_ensemble_size"
    )

    # STEP 4: Aggregation tracking
    aggregation_method: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default="mean",
        comment="STEP 4: Method used for outcome aggregation (mean, weighted_mean, median, mode)"
    )
    outcome_counts: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
        comment="STEP 4: Count/weight of each outcome across ensemble runs"
    )
    outcome_variance: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
        comment="STEP 4: Variance metrics for aggregated outcomes"
    )

    # ==========================================================================
    # STEP 9: Universe Map / Knowledge Graph Requirements
    # ==========================================================================

    # STEP 9 Req 1: Snapshot references for auditable persona/rules/parameters
    personas_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="STEP 9: Reference to personas snapshot used for this node"
    )
    rules_version: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="STEP 9: Version of rules used for this node (for audit)"
    )
    parameters_version: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="STEP 9: Version of simulation parameters (for audit)"
    )

    # STEP 9 Req 1: Reliability score FK (links to STEP 7 reliability infrastructure)
    reliability_score_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reliability_scores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="STEP 9: FK to ReliabilityScore from STEP 7"
    )

    # STEP 9 Req 5: Dependency tracking - staleness propagation
    is_stale: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="STEP 9: True if this node depends on stale parent or modified ancestor"
    )
    stale_reason: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
        comment="STEP 9: Reason for staleness {ancestor_node_id, change_type, changed_at}"
    )

    # STEP 9 Req 6: Node operations - pruning flag
    is_pruned: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True,
        comment="STEP 9: True if node has been pruned (hidden from default views)"
    )
    pruned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="STEP 9: Timestamp when node was pruned"
    )
    pruned_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="STEP 9: Reason for pruning (for audit trail)"
    )

    # STEP 9 Req 6: Node operations - annotations for human notes
    annotations: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict,
        comment="STEP 9: Human annotations/notes for this node {notes, tags, bookmarked, custom_labels}"
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
    # STEP 4: Relationship to structured NodePatch
    node_patch: Mapped[Optional["NodePatch"]] = relationship(
        "NodePatch",
        back_populates="node",
        uselist=False  # One-to-one relationship
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
            # STEP 4: Ensemble status
            "completed_run_count": self.completed_run_count,
            "min_ensemble_size": self.min_ensemble_size,
            "is_ensemble_complete": self.is_ensemble_complete,
            # STEP 9: Staleness and pruning status
            "is_stale": self.is_stale,
            "is_pruned": self.is_pruned,
            "has_annotations": bool(self.annotations),
            "reliability_score_id": str(self.reliability_score_id) if self.reliability_score_id else None,
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

    # ==========================================================================
    # STEP 9 Req 2: Explicit FK references for audit trail
    # ==========================================================================

    # STEP 9: Explicit FK to EventScript (replaces reliance on intervention JSONB)
    event_script_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_scripts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="STEP 9: FK reference to EventScript that caused this edge"
    )

    # STEP 9: Explicit FK to NodePatch for structured change tracking
    node_patch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("node_patches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="STEP 9: FK reference to NodePatch describing the transformation"
    )

    # STEP 9: Outcome delta between parent and child nodes
    outcome_delta: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
        comment="STEP 9: Delta between parent and child aggregated_outcome {metric: {before, after, change_pct}}"
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
            # STEP 9: Explicit FK references
            "event_script_id": str(self.event_script_id) if self.event_script_id else None,
            "node_patch_id": str(self.node_patch_id) if self.node_patch_id else None,
            "has_outcome_delta": self.outcome_delta is not None,
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
    """Status of a simulation run.

    State transitions (STEP 1 requirement):
    CREATED -> QUEUED -> RUNNING -> SUCCEEDED | FAILED

    CANCELLED can be reached from CREATED, QUEUED, or RUNNING states.
    """
    CREATED = "created"      # Initial state when run record is created
    QUEUED = "queued"        # Run is queued for worker pickup
    RUNNING = "running"      # Worker is actively executing the run
    SUCCEEDED = "succeeded"  # Run completed successfully
    FAILED = "failed"        # Run failed with error
    CANCELLED = "cancelled"  # Run was cancelled by user/system


class TriggeredBy(str, Enum):
    """Who/what triggered the run."""
    USER = "user"
    SYSTEM = "system"
    SCHEDULE = "schedule"
    API = "api"
    BATCH = "batch"  # For multi-seed / ensemble runs


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

    # Status (STEP 1: Start with CREATED, then transition to QUEUED when submitted)
    status: Mapped[str] = mapped_column(
        String(20), default=RunStatus.CREATED.value, nullable=False, index=True
    )

    # Timing
    timing: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Outputs (populated when succeeded)
    outputs: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Has results flag (set to True when telemetry is successfully stored)
    has_results: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )

    # Error (populated when failed)
    error: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Seed used (for reproducibility)
    actual_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Worker info (STEP 1: Worker heartbeat tracking)
    worker_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    worker_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    worker_last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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
