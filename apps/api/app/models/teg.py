"""
Thought Expansion Graph (TEG) Models

Data model for the TEG presentation layer over existing simulation infrastructure.
TEG is a mind-map style view of scenarios (nodes) and their relationships (edges).

Reference: docs/TEG_UNIVERSE_MAP_EXECUTION.md

Architecture:
- TEGGraph: Root container per project
- TEGNode: Individual scenario nodes (OUTCOME_VERIFIED, SCENARIO_DRAFT, EVIDENCE)
- TEGEdge: Relationships between nodes (EXPANDS_TO, RUNS_TO, etc.)

IMPORTANT: This is a presentation layer. The actual simulation execution uses
the existing Node, Run, and RunOutcome infrastructure. TEG provides a unified
view for exploring "what-if" scenarios.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# =============================================================================
# Enums
# =============================================================================

class TEGNodeType(str, Enum):
    """Type of TEG node."""
    OUTCOME_VERIFIED = "OUTCOME_VERIFIED"  # From actual run with verified result
    SCENARIO_DRAFT = "SCENARIO_DRAFT"      # LLM-estimated scenario (not executed)
    EVIDENCE = "EVIDENCE"                  # Supporting evidence node


class TEGNodeStatus(str, Enum):
    """Status of TEG node."""
    DRAFT = "DRAFT"       # Created but not scheduled
    QUEUED = "QUEUED"     # Scheduled for execution
    RUNNING = "RUNNING"   # Currently executing
    DONE = "DONE"         # Completed successfully
    FAILED = "FAILED"     # Execution failed


class TEGEdgeRelation(str, Enum):
    """Relationship type between TEG nodes."""
    EXPANDS_TO = "EXPANDS_TO"    # Parent expands to child scenarios
    RUNS_TO = "RUNS_TO"          # Draft node executed to verified node
    FORKS_FROM = "FORKS_FROM"    # Alternative branch from parent
    SUPPORTS = "SUPPORTS"        # Evidence supports outcome
    CONFLICTS = "CONFLICTS"      # Evidence conflicts with outcome


# =============================================================================
# TEG Graph Model
# =============================================================================

class TEGGraph(Base):
    """
    Root container for a project's Thought Expansion Graph.

    Each project has exactly one TEGGraph instance that tracks:
    - All nodes in the graph
    - The active baseline node for comparisons
    - Graph metadata and settings
    """

    __tablename__ = "teg_graphs"

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

    # Foreign key to project_specs (one graph per project)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One TEG per project
    )

    # Active baseline node for comparisons
    active_baseline_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    # Graph metadata
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    nodes: Mapped[List["TEGNode"]] = relationship(
        "TEGNode",
        back_populates="graph",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_teg_graphs_tenant_project", "tenant_id", "project_id"),
    )

    def __repr__(self) -> str:
        return f"<TEGGraph(id={self.id}, project_id={self.project_id})>"


# =============================================================================
# TEG Node Model
# =============================================================================

class TEGNode(Base):
    """
    Individual node in the Thought Expansion Graph.

    Represents either:
    - OUTCOME_VERIFIED: Result from an actual simulation run
    - SCENARIO_DRAFT: LLM-estimated scenario not yet executed
    - EVIDENCE: Supporting evidence for outcomes

    Links to existing infrastructure:
    - node_id: Links to nodes table (simulation node)
    - run_id: Links to runs table (if from actual run)
    - run_outcome_id: Links to run_outcomes table (verified metrics)
    """

    __tablename__ = "teg_nodes"

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

    # Parent references
    graph_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teg_graphs.id", ondelete="CASCADE"),
        nullable=False,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Parent node for tree structure
    parent_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teg_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Node type and status
    node_type: Mapped[TEGNodeType] = mapped_column(
        SAEnum(TEGNodeType, name="teg_node_type"),
        nullable=False,
    )

    status: Mapped[TEGNodeStatus] = mapped_column(
        SAEnum(TEGNodeStatus, name="teg_node_status"),
        nullable=False,
        default=TEGNodeStatus.DRAFT,
    )

    # Display info
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Payload varies by node type
    # OUTCOME_VERIFIED: { primary_outcome_probability, confidence, metrics, ... }
    # SCENARIO_DRAFT: { estimated_delta, scenario_description, suggested_changes, ... }
    # EVIDENCE: { evidence_type, source, relevance, ... }
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Links to existing infrastructure
    links: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        # Structure:
        # {
        #   "run_ids": ["uuid1", "uuid2"],  # Associated run IDs
        #   "node_id": "uuid",              # Link to nodes table
        #   "run_outcome_id": "uuid",       # Link to run_outcomes table
        #   "manifest_hash": "sha256...",   # For reproducibility
        #   "persona_version": "v1.2.3",    # Persona snapshot version
        #   "evidence_ids": ["uuid1", ...]  # Evidence references
        # }
    )

    # Position for graph rendering (optional, can be computed)
    position: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        # { "x": 100, "y": 200 }
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    graph: Mapped["TEGGraph"] = relationship(
        "TEGGraph",
        back_populates="nodes",
    )

    # Self-referential relationship for tree structure
    children: Mapped[List["TEGNode"]] = relationship(
        "TEGNode",
        back_populates="parent",
        remote_side=[id],
    )
    parent: Mapped[Optional["TEGNode"]] = relationship(
        "TEGNode",
        back_populates="children",
        remote_side=[parent_node_id],
    )

    # Edges where this node is the source
    outgoing_edges: Mapped[List["TEGEdge"]] = relationship(
        "TEGEdge",
        foreign_keys="TEGEdge.from_node_id",
        back_populates="from_node",
        cascade="all, delete-orphan",
    )

    # Edges where this node is the target
    incoming_edges: Mapped[List["TEGEdge"]] = relationship(
        "TEGEdge",
        foreign_keys="TEGEdge.to_node_id",
        back_populates="to_node",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_teg_nodes_graph_id", "graph_id"),
        Index("ix_teg_nodes_project_id", "project_id"),
        Index("ix_teg_nodes_tenant_project", "tenant_id", "project_id"),
        Index("ix_teg_nodes_parent", "parent_node_id"),
        Index("ix_teg_nodes_type_status", "node_type", "status"),
    )

    def __repr__(self) -> str:
        return f"<TEGNode(id={self.id}, type={self.node_type}, title='{self.title[:30]}...')>"


# =============================================================================
# TEG Edge Model
# =============================================================================

class TEGEdge(Base):
    """
    Edge representing relationship between TEG nodes.

    Relations:
    - EXPANDS_TO: Parent scenario expands to child scenarios
    - RUNS_TO: Draft scenario was executed to produce verified outcome
    - FORKS_FROM: Alternative branch exploring different parameters
    - SUPPORTS: Evidence supports an outcome
    - CONFLICTS: Evidence conflicts with an outcome
    """

    __tablename__ = "teg_edges"

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

    # Graph reference
    graph_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teg_graphs.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Edge endpoints
    from_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teg_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )

    to_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teg_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationship type
    relation: Mapped[TEGEdgeRelation] = mapped_column(
        SAEnum(TEGEdgeRelation, name="teg_edge_relation"),
        nullable=False,
    )

    # Optional metadata for the edge
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        # Could include:
        # {
        #   "delta": 0.15,           # Probability change
        #   "intervention_type": "event_injection",
        #   "description": "What if...",
        # }
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    from_node: Mapped["TEGNode"] = relationship(
        "TEGNode",
        foreign_keys=[from_node_id],
        back_populates="outgoing_edges",
    )

    to_node: Mapped["TEGNode"] = relationship(
        "TEGNode",
        foreign_keys=[to_node_id],
        back_populates="incoming_edges",
    )

    __table_args__ = (
        Index("ix_teg_edges_graph_id", "graph_id"),
        Index("ix_teg_edges_from_node", "from_node_id"),
        Index("ix_teg_edges_to_node", "to_node_id"),
        Index("ix_teg_edges_relation", "relation"),
    )

    def __repr__(self) -> str:
        return f"<TEGEdge(id={self.id}, {self.relation}: {self.from_node_id} -> {self.to_node_id})>"
