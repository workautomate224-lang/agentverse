"""
Node/Universe Map Service
Reference: project.md §6.7, §9.1

Manages the Universe Map: nodes, edges, clusters, and path analysis.
Enforces fork-not-mutate invariant (C1): changes create new nodes, never edit existing.
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.node import (
    Node,
    Edge,
    NodeCluster,
    Run,
    InterventionType,
    ExpansionStrategy,
    ConfidenceLevel,
)


# =============================================================================
# Data Transfer Objects
# =============================================================================

@dataclass
class ArtifactRef:
    """Reference to an artifact in object storage."""
    ref_type: str
    storage_key: str
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ref_type": self.ref_type,
            "storage_key": self.storage_key,
            "version": self.version,
        }


@dataclass
class AggregatedOutcome:
    """Summary of run results for a node."""
    primary_outcome: str
    primary_outcome_probability: float
    outcome_distribution: Dict[str, float] = field(default_factory=dict)
    key_metrics: List[Dict[str, Any]] = field(default_factory=list)
    variance_metrics: Optional[Dict[str, float]] = None
    summary_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_outcome": self.primary_outcome,
            "primary_outcome_probability": self.primary_outcome_probability,
            "outcome_distribution": self.outcome_distribution,
            "key_metrics": self.key_metrics,
            "variance_metrics": self.variance_metrics,
            "summary_text": self.summary_text,
        }


@dataclass
class NodeConfidence:
    """Confidence information for a node."""
    confidence_level: ConfidenceLevel
    confidence_score: float
    factors: List[Dict[str, Any]] = field(default_factory=list)
    reliability_ref: Optional[ArtifactRef] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_level": self.confidence_level.value,
            "confidence_score": self.confidence_score,
            "factors": self.factors,
            "reliability_ref": self.reliability_ref.to_dict() if self.reliability_ref else None,
        }


@dataclass
class EdgeIntervention:
    """What created an edge."""
    intervention_type: InterventionType
    event_script_ref: Optional[ArtifactRef] = None
    variable_deltas: Optional[Dict[str, Any]] = None
    nl_query: Optional[str] = None
    expansion_strategy: Optional[ExpansionStrategy] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intervention_type": self.intervention_type.value,
            "event_script_ref": self.event_script_ref.to_dict() if self.event_script_ref else None,
            "variable_deltas": self.variable_deltas,
            "nl_query": self.nl_query,
            "expansion_strategy": self.expansion_strategy.value if self.expansion_strategy else None,
        }


@dataclass
class EdgeExplanation:
    """Why an edge exists."""
    short_label: str
    explanation_text: str
    key_differentiators: List[str] = field(default_factory=list)
    generated_by: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "short_label": self.short_label,
            "explanation_text": self.explanation_text,
            "key_differentiators": self.key_differentiators,
            "generated_by": self.generated_by,
        }


@dataclass
class PathAnalysis:
    """Analysis of a path through the Universe Map."""
    path_id: str
    node_sequence: List[str]
    path_probability: float
    summary: str
    key_events: List[str]
    final_outcome: Optional[AggregatedOutcome] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "node_sequence": self.node_sequence,
            "path_probability": self.path_probability,
            "summary": self.summary,
            "key_events": self.key_events,
            "final_outcome": self.final_outcome.to_dict() if self.final_outcome else None,
        }


@dataclass
class UniverseMapState:
    """Current state of the Universe Map for frontend rendering."""
    project_id: str
    root_node_id: str
    visible_nodes: List[str] = field(default_factory=list)
    visible_edges: List[str] = field(default_factory=list)
    visible_clusters: List[str] = field(default_factory=list)
    selected_node_id: Optional[str] = None
    compared_node_ids: Optional[List[str]] = None
    zoom_level: float = 1.0
    viewport_center: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    probability_threshold: float = 0.0
    show_low_confidence: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "root_node_id": self.root_node_id,
            "visible_nodes": self.visible_nodes,
            "visible_edges": self.visible_edges,
            "visible_clusters": self.visible_clusters,
            "selected_node_id": self.selected_node_id,
            "compared_node_ids": self.compared_node_ids,
            "zoom_level": self.zoom_level,
            "viewport_center": self.viewport_center,
            "probability_threshold": self.probability_threshold,
            "show_low_confidence": self.show_low_confidence,
        }


@dataclass
class UniverseMapData:
    """Full universe map data for API responses."""
    project_id: str
    root_node_id: str
    nodes: List[Any]  # List of Node SQLAlchemy objects
    edges: List[Any]  # List of Edge SQLAlchemy objects
    total_nodes: int
    explored_nodes: int
    max_depth: int


# =============================================================================
# Create/Fork Input DTOs
# =============================================================================

@dataclass
class CreateNodeInput:
    """Input for creating a new node (root or forked)."""
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    parent_node_id: Optional[uuid.UUID] = None
    scenario_patch_ref: Optional[ArtifactRef] = None
    label: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_baseline: bool = False


@dataclass
class CreateEdgeInput:
    """Input for creating an edge between nodes."""
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    from_node_id: uuid.UUID
    to_node_id: uuid.UUID
    intervention: EdgeIntervention
    explanation: Optional[EdgeExplanation] = None


@dataclass
class ForkNodeInput:
    """Input for forking a node (creates both node and edge)."""
    parent_node_id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    intervention: EdgeIntervention
    explanation: Optional[EdgeExplanation] = None
    scenario_patch_ref: Optional[ArtifactRef] = None
    label: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


# =============================================================================
# Node Service
# =============================================================================

class NodeService:
    """
    Service for managing the Universe Map.

    Core invariant (C1): Fork-not-mutate. Changes create new nodes, never edit existing.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Node Operations
    # -------------------------------------------------------------------------

    async def create_root_node(
        self,
        input: CreateNodeInput,
    ) -> Node:
        """
        Create a root node (baseline) for a project.

        This is the starting point of the Universe Map.
        """
        node = Node(
            id=uuid.uuid4(),
            tenant_id=input.tenant_id,
            project_id=input.project_id,
            parent_node_id=None,
            depth=0,
            scenario_patch_ref=input.scenario_patch_ref.to_dict() if input.scenario_patch_ref else None,
            run_refs=[],
            probability=1.0,
            cumulative_probability=1.0,
            confidence={
                "confidence_level": ConfidenceLevel.MEDIUM.value,
                "confidence_score": 0.5,
                "factors": [],
            },
            label=input.label or "Baseline",
            description=input.description,
            tags=input.tags,
            is_baseline=True,
            is_explored=False,
            child_count=0,
        )

        self.db.add(node)
        await self.db.flush()
        return node

    async def fork_node(
        self,
        input: ForkNodeInput,
    ) -> Tuple[Node, Edge]:
        """
        Fork a new node from an existing parent.

        This is the ONLY way to create non-root nodes.
        Enforces fork-not-mutate invariant.
        """
        # Get parent node
        parent = await self.get_node(input.parent_node_id)
        if not parent:
            raise ValueError(f"Parent node {input.parent_node_id} not found")

        # Create child node
        child_node = Node(
            id=uuid.uuid4(),
            tenant_id=input.tenant_id,
            project_id=input.project_id,
            parent_node_id=parent.id,
            depth=parent.depth + 1,
            scenario_patch_ref=input.scenario_patch_ref.to_dict() if input.scenario_patch_ref else None,
            run_refs=[],
            probability=1.0,  # Will be updated when runs complete
            cumulative_probability=parent.cumulative_probability,  # Updated with runs
            confidence={
                "confidence_level": ConfidenceLevel.LOW.value,
                "confidence_score": 0.0,
                "factors": [],
            },
            label=input.label,
            description=input.description,
            tags=input.tags,
            is_baseline=False,
            is_explored=False,
            child_count=0,
        )

        # Create edge from parent to child
        explanation = input.explanation or EdgeExplanation(
            short_label="Fork",
            explanation_text="Forked from parent node",
            generated_by="system",
        )

        edge = Edge(
            id=uuid.uuid4(),
            tenant_id=input.tenant_id,
            project_id=input.project_id,
            from_node_id=parent.id,
            to_node_id=child_node.id,
            intervention=input.intervention.to_dict(),
            explanation=explanation.to_dict(),
            is_primary_path=False,
        )

        # Update parent child count (allowed meta update, not outcome mutation)
        parent.child_count += 1

        self.db.add(child_node)
        self.db.add(edge)
        await self.db.flush()

        return child_node, edge

    async def get_node(
        self,
        node_id: str | uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
        include_children: bool = False,
        include_runs: bool = False,
    ) -> Optional[Node]:
        """Get a node by ID with optional relationships and tenant filtering."""
        # Handle string or UUID input
        try:
            node_uuid = uuid.UUID(str(node_id)) if isinstance(node_id, str) else node_id
        except ValueError:
            return None

        query = select(Node).where(Node.id == node_uuid)

        # Filter by tenant if provided (for multi-tenancy)
        if tenant_id:
            query = query.where(Node.tenant_id == tenant_id)

        if include_children:
            query = query.options(selectinload(Node.children))
        if include_runs:
            query = query.options(selectinload(Node.runs))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_nodes_by_project(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
        include_clustered: bool = True,
        probability_threshold: float = 0.0,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Node]:
        """Get nodes for a project with filtering."""
        query = select(Node).where(
            and_(
                Node.project_id == project_id,
                Node.tenant_id == tenant_id,
                Node.probability >= probability_threshold,
            )
        )

        if not include_clustered:
            query = query.where(Node.cluster_id.is_(None))

        query = query.order_by(Node.depth, Node.created_at).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_nodes(
        self,
        project_id: str,
        tenant_id: uuid.UUID,
        explored_only: bool = False,
        depth: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Node]:
        """
        List nodes for a project with filtering options.

        This method is called by the API endpoint and provides
        filtering by explored state and depth.
        """
        try:
            project_uuid = uuid.UUID(project_id)
        except ValueError:
            return []

        conditions = [
            Node.project_id == project_uuid,
            Node.tenant_id == tenant_id,
        ]

        if explored_only:
            conditions.append(Node.is_explored == True)

        if depth is not None:
            conditions.append(Node.depth == depth)

        query = select(Node).where(and_(*conditions))
        query = query.order_by(Node.depth, Node.created_at).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_root_node(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[Node]:
        """Get the root (baseline) node for a project.

        If multiple baseline nodes exist (e.g., from testing), returns the
        most recently explored one, or the earliest created if none explored.
        """
        query = select(Node).where(
            and_(
                Node.project_id == project_id,
                Node.tenant_id == tenant_id,
                Node.is_baseline == True,
            )
        ).order_by(
            # Prefer explored nodes first, then most recently created
            Node.is_explored.desc(),
            Node.created_at.desc(),
        ).limit(1)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_node_outcome(
        self,
        node_id: uuid.UUID,
        outcome: AggregatedOutcome,
        confidence: NodeConfidence,
    ) -> Node:
        """
        Update a node's outcome after runs complete.

        Note: This is the ONLY allowed mutation of node content.
        It's setting the result, not changing history.
        """
        node = await self.get_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        node.aggregated_outcome = outcome.to_dict()
        node.confidence = confidence.to_dict()
        node.probability = outcome.primary_outcome_probability

        # Recalculate cumulative probability
        if node.parent_node_id:
            parent = await self.get_node(node.parent_node_id)
            if parent:
                node.cumulative_probability = parent.cumulative_probability * node.probability
        else:
            node.cumulative_probability = node.probability

        await self.db.flush()
        return node

    async def add_run_ref(
        self,
        node_id: uuid.UUID,
        run_ref: ArtifactRef,
    ) -> Node:
        """Add a run reference to a node."""
        node = await self.get_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        refs = list(node.run_refs or [])
        refs.append(run_ref.to_dict())
        node.run_refs = refs

        await self.db.flush()
        return node

    async def mark_explored(self, node_id: uuid.UUID) -> Node:
        """Mark a node as explored (user has examined it)."""
        node = await self.get_node(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        node.is_explored = True
        await self.db.flush()
        return node

    # -------------------------------------------------------------------------
    # Edge Operations
    # -------------------------------------------------------------------------

    async def get_edge(self, edge_id: uuid.UUID) -> Optional[Edge]:
        """Get an edge by ID."""
        query = select(Edge).where(Edge.id == edge_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_edges_by_project(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> List[Edge]:
        """Get all edges for a project."""
        query = select(Edge).where(
            and_(
                Edge.project_id == project_id,
                Edge.tenant_id == tenant_id,
            )
        ).order_by(Edge.created_at)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_outgoing_edges(self, node_id: uuid.UUID) -> List[Edge]:
        """Get edges going out from a node."""
        query = select(Edge).where(Edge.from_node_id == node_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_incoming_edges(self, node_id: uuid.UUID) -> List[Edge]:
        """Get edges coming into a node."""
        query = select(Edge).where(Edge.to_node_id == node_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_edges(
        self,
        node_id: str,
        tenant_id: uuid.UUID,
        direction: str = "outgoing",
    ) -> List[Edge]:
        """Get edges connected to a node with direction filtering."""
        try:
            node_uuid = uuid.UUID(node_id)
        except ValueError:
            return []

        if direction == "outgoing":
            query = select(Edge).where(
                and_(
                    Edge.from_node_id == node_uuid,
                    Edge.tenant_id == tenant_id,
                )
            )
        elif direction == "incoming":
            query = select(Edge).where(
                and_(
                    Edge.to_node_id == node_uuid,
                    Edge.tenant_id == tenant_id,
                )
            )
        else:  # both
            query = select(Edge).where(
                and_(
                    (Edge.from_node_id == node_uuid) | (Edge.to_node_id == node_uuid),
                    Edge.tenant_id == tenant_id,
                )
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_children(
        self,
        node_id: str,
        tenant_id: uuid.UUID,
    ) -> List[Node]:
        """Get all child nodes of a given node."""
        try:
            node_uuid = uuid.UUID(node_id)
        except ValueError:
            return []

        query = select(Node).where(
            and_(
                Node.parent_node_id == node_uuid,
                Node.tenant_id == tenant_id,
            )
        ).order_by(Node.created_at)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def set_primary_path(
        self,
        edge_ids: List[uuid.UUID],
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        """Set the primary path through the Universe Map."""
        # First, clear all primary flags for this project
        all_edges = await self.get_edges_by_project(project_id, tenant_id)
        for edge in all_edges:
            edge.is_primary_path = edge.id in edge_ids

        await self.db.flush()

    # -------------------------------------------------------------------------
    # Cluster Operations
    # -------------------------------------------------------------------------

    async def create_cluster(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
        node_ids: List[uuid.UUID],
        label: str,
        description: Optional[str] = None,
    ) -> NodeCluster:
        """
        Create a cluster of similar nodes.

        Clustering prevents UI overload with too many nodes (project.md §9.1).
        """
        if not node_ids:
            raise ValueError("Cluster must contain at least one node")

        # Get nodes
        nodes = []
        for nid in node_ids:
            node = await self.get_node(nid)
            if node:
                nodes.append(node)

        if not nodes:
            raise ValueError("No valid nodes found for cluster")

        # Select representative (highest probability)
        representative = max(nodes, key=lambda n: n.probability)

        # Compute cluster probability (average of members)
        cluster_prob = sum(n.probability for n in nodes) / len(nodes)

        cluster = NodeCluster(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            label=label,
            description=description,
            member_node_ids=node_ids,
            representative_node_id=representative.id,
            cluster_probability=cluster_prob,
            is_expanded=False,
            expandable=True,
        )

        # Update nodes with cluster assignment
        for node in nodes:
            node.cluster_id = cluster.id
            node.is_cluster_representative = (node.id == representative.id)

        self.db.add(cluster)
        await self.db.flush()
        return cluster

    async def expand_cluster(self, cluster_id: uuid.UUID) -> NodeCluster:
        """Mark a cluster as expanded (show individual nodes)."""
        query = select(NodeCluster).where(NodeCluster.id == cluster_id)
        result = await self.db.execute(query)
        cluster = result.scalar_one_or_none()

        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        cluster.is_expanded = True
        await self.db.flush()
        return cluster

    async def collapse_cluster(self, cluster_id: uuid.UUID) -> NodeCluster:
        """Mark a cluster as collapsed (show representative only)."""
        query = select(NodeCluster).where(NodeCluster.id == cluster_id)
        result = await self.db.execute(query)
        cluster = result.scalar_one_or_none()

        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        cluster.is_expanded = False
        await self.db.flush()
        return cluster

    async def get_clusters_by_project(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> List[NodeCluster]:
        """Get all clusters for a project."""
        query = select(NodeCluster).where(
            and_(
                NodeCluster.project_id == project_id,
                NodeCluster.tenant_id == tenant_id,
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Path Analysis
    # -------------------------------------------------------------------------

    async def get_path_to_root(self, node_id: uuid.UUID) -> List[Node]:
        """Get the path from a node to the root (ancestry chain)."""
        path = []
        current = await self.get_node(node_id)

        while current:
            path.append(current)
            if current.parent_node_id:
                current = await self.get_node(current.parent_node_id)
            else:
                break

        return list(reversed(path))  # Root to leaf order

    async def get_most_likely_paths(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
        num_paths: int = 5,
    ) -> List[PathAnalysis]:
        """
        Get the N most likely paths through the Universe Map.

        A path is a sequence of nodes from root to a leaf.
        """
        # Get all leaf nodes (nodes with no children)
        leaves = await self._get_leaf_nodes(project_id, tenant_id)

        # For each leaf, compute path to root with probability
        paths = []
        for leaf in leaves:
            path_nodes = await self.get_path_to_root(leaf.id)
            if path_nodes:
                path_prob = path_nodes[-1].cumulative_probability

                # Collect key events from edges along the path
                key_events = []
                for i in range(len(path_nodes) - 1):
                    edges = await self.get_outgoing_edges(path_nodes[i].id)
                    for edge in edges:
                        if edge.to_node_id == path_nodes[i + 1].id:
                            short_label = edge.explanation.get("short_label", "")
                            if short_label:
                                key_events.append(short_label)

                # Create path analysis
                final_outcome = None
                if leaf.aggregated_outcome:
                    final_outcome = AggregatedOutcome(
                        primary_outcome=leaf.aggregated_outcome.get("primary_outcome", ""),
                        primary_outcome_probability=leaf.aggregated_outcome.get(
                            "primary_outcome_probability", 0
                        ),
                        outcome_distribution=leaf.aggregated_outcome.get(
                            "outcome_distribution", {}
                        ),
                        key_metrics=leaf.aggregated_outcome.get("key_metrics", []),
                        summary_text=leaf.aggregated_outcome.get("summary_text"),
                    )

                path_id = hashlib.md5(
                    "-".join(str(n.id) for n in path_nodes).encode()
                ).hexdigest()[:12]

                paths.append(PathAnalysis(
                    path_id=path_id,
                    node_sequence=[str(n.id) for n in path_nodes],
                    path_probability=path_prob,
                    summary=leaf.label or f"Path to {leaf.id}",
                    key_events=key_events,
                    final_outcome=final_outcome,
                ))

        # Sort by probability and return top N
        paths.sort(key=lambda p: p.path_probability, reverse=True)
        return paths[:num_paths]

    async def _get_leaf_nodes(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> List[Node]:
        """Get all leaf nodes (nodes with no children)."""
        query = select(Node).where(
            and_(
                Node.project_id == project_id,
                Node.tenant_id == tenant_id,
                Node.child_count == 0,
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Universe Map State
    # -------------------------------------------------------------------------

    async def get_universe_map_state(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
        probability_threshold: float = 0.0,
        show_low_confidence: bool = True,
    ) -> UniverseMapState:
        """
        Get the current state of the Universe Map for frontend rendering.

        Respects node collapse state and cluster expansion.
        """
        root = await self.get_root_node(project_id, tenant_id)
        if not root:
            raise ValueError(f"No root node found for project {project_id}")

        # Get all nodes
        all_nodes = await self.get_nodes_by_project(
            project_id, tenant_id,
            include_clustered=True,
            probability_threshold=probability_threshold,
        )

        # Filter by confidence if needed
        if not show_low_confidence:
            all_nodes = [
                n for n in all_nodes
                if n.confidence.get("confidence_level") != ConfidenceLevel.LOW.value
            ]

        # Get all clusters
        clusters = await self.get_clusters_by_project(project_id, tenant_id)
        expanded_cluster_ids = {c.id for c in clusters if c.is_expanded}

        # Build visible nodes list (respecting clusters)
        visible_nodes = []
        for node in all_nodes:
            if node.cluster_id:
                # Node is in a cluster
                if node.cluster_id in expanded_cluster_ids:
                    # Cluster is expanded, show all nodes
                    visible_nodes.append(str(node.id))
                elif node.is_cluster_representative:
                    # Show only representative for collapsed clusters
                    visible_nodes.append(str(node.id))
            else:
                # Not in a cluster
                if not node.is_collapsed:
                    visible_nodes.append(str(node.id))

        # Get all edges
        all_edges = await self.get_edges_by_project(project_id, tenant_id)

        # Filter edges to only those between visible nodes
        visible_node_set = set(visible_nodes)
        visible_edges = [
            str(e.id) for e in all_edges
            if str(e.from_node_id) in visible_node_set
            and str(e.to_node_id) in visible_node_set
        ]

        # Visible clusters (collapsed ones)
        visible_clusters = [
            str(c.id) for c in clusters
            if not c.is_expanded
        ]

        return UniverseMapState(
            project_id=str(project_id),
            root_node_id=str(root.id),
            visible_nodes=visible_nodes,
            visible_edges=visible_edges,
            visible_clusters=visible_clusters,
            probability_threshold=probability_threshold,
            show_low_confidence=show_low_confidence,
        )

    async def get_universe_map_data(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
        max_depth: Optional[int] = None,
        explored_only: bool = False,
    ) -> Optional[UniverseMapData]:
        """
        Get full universe map data with node and edge objects for API responses.

        Returns None if project has no nodes.
        """
        # Get root node
        root = await self.get_root_node(project_id, tenant_id)
        if not root:
            return None

        # Get all nodes
        all_nodes = await self.get_nodes_by_project(
            project_id, tenant_id,
            include_clustered=True,
            limit=10000,  # Large limit to get all nodes
        )

        # Filter by max_depth if specified
        if max_depth is not None:
            all_nodes = [n for n in all_nodes if n.depth <= max_depth]

        # Filter to explored only if requested
        if explored_only:
            all_nodes = [n for n in all_nodes if n.is_explored]

        # Get all edges
        all_edges = await self.get_edges_by_project(project_id, tenant_id)

        # Calculate stats
        total_nodes = len(all_nodes)
        explored_nodes = sum(1 for n in all_nodes if n.is_explored)
        max_depth_actual = max((n.depth for n in all_nodes), default=0)

        return UniverseMapData(
            project_id=str(project_id),
            root_node_id=str(root.id),
            nodes=all_nodes,
            edges=all_edges,
            total_nodes=total_nodes,
            explored_nodes=explored_nodes,
            max_depth=max_depth_actual,
        )

    # -------------------------------------------------------------------------
    # Comparison Operations
    # -------------------------------------------------------------------------

    async def compare_nodes(
        self,
        node_ids: List[uuid.UUID],
    ) -> Dict[str, Any]:
        """
        Compare multiple nodes side by side.

        Returns comparison data for outcomes, probabilities, and key metrics.
        """
        nodes = []
        for nid in node_ids:
            node = await self.get_node(nid)
            if node:
                nodes.append(node)

        if len(nodes) < 2:
            raise ValueError("Need at least 2 nodes to compare")

        comparison = {
            "nodes": [],
            "metric_comparison": {},
            "outcome_comparison": {},
        }

        all_metrics = set()

        for node in nodes:
            node_data = {
                "node_id": str(node.id),
                "label": node.label,
                "probability": node.probability,
                "cumulative_probability": node.cumulative_probability,
                "confidence_level": node.confidence.get("confidence_level"),
            }

            if node.aggregated_outcome:
                node_data["primary_outcome"] = node.aggregated_outcome.get("primary_outcome")
                node_data["primary_outcome_probability"] = node.aggregated_outcome.get(
                    "primary_outcome_probability"
                )

                # Track metrics
                for metric in node.aggregated_outcome.get("key_metrics", []):
                    metric_name = metric.get("metric_name")
                    if metric_name:
                        all_metrics.add(metric_name)
                        if metric_name not in comparison["metric_comparison"]:
                            comparison["metric_comparison"][metric_name] = {}
                        comparison["metric_comparison"][metric_name][str(node.id)] = metric.get("value")

                # Track outcome distribution
                for outcome, prob in node.aggregated_outcome.get("outcome_distribution", {}).items():
                    if outcome not in comparison["outcome_comparison"]:
                        comparison["outcome_comparison"][outcome] = {}
                    comparison["outcome_comparison"][outcome][str(node.id)] = prob

            comparison["nodes"].append(node_data)

        return comparison

    # -------------------------------------------------------------------------
    # Probability Normalization & Verification (§2.4)
    # -------------------------------------------------------------------------

    async def normalize_sibling_probabilities(
        self,
        parent_node_id: uuid.UUID,
        tolerance: float = 0.001,
    ) -> Dict[str, Any]:
        """
        Normalize child node probabilities to sum to parent's probability.
        Reference: verification_checklist_v2.md §2.4 (Conditional Probability Correctness)

        When a parent node is forked into multiple children, this ensures:
        P(child_1 | parent) + P(child_2 | parent) + ... = P(parent)

        Returns normalization report with before/after state.
        """
        parent = await self.get_node(parent_node_id)
        if not parent:
            raise ValueError(f"Parent node {parent_node_id} not found")

        # Get all children
        children = await self.get_child_nodes(parent.id)
        if not children:
            return {
                "status": "no_children",
                "parent_probability": parent.probability,
                "children_count": 0,
            }

        # Calculate current sum
        current_sum = sum(c.probability for c in children)

        # Check if normalization needed
        if abs(current_sum - parent.probability) <= tolerance:
            return {
                "status": "already_normalized",
                "parent_probability": parent.probability,
                "children_sum": current_sum,
                "children_count": len(children),
            }

        # Normalize each child
        before_state = []
        after_state = []

        for child in children:
            before_state.append({
                "node_id": str(child.id),
                "probability": child.probability,
            })

            # Proportional normalization
            if current_sum > 0:
                normalized_prob = (child.probability / current_sum) * parent.probability
            else:
                # Equal distribution if all zeros
                normalized_prob = parent.probability / len(children)

            child.probability = normalized_prob
            child.cumulative_probability = parent.cumulative_probability * normalized_prob

            after_state.append({
                "node_id": str(child.id),
                "probability": normalized_prob,
                "cumulative_probability": child.cumulative_probability,
            })

        await self.db.flush()

        return {
            "status": "normalized",
            "parent_probability": parent.probability,
            "before_sum": current_sum,
            "after_sum": sum(c["probability"] for c in after_state),
            "children_count": len(children),
            "before": before_state,
            "after": after_state,
        }

    async def verify_probability_consistency(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
        tolerance: float = 0.001,
    ) -> Dict[str, Any]:
        """
        Verify probability consistency across all nodes in a project.
        Reference: verification_checklist_v2.md §2.4 (Conditional Probability Correctness)

        Checks:
        1. Root node probability is 1.0
        2. Children probabilities sum to parent probability (within tolerance)
        3. Cumulative probabilities are correctly computed

        Returns verification report.
        """
        all_nodes = await self.get_nodes_by_project(project_id, tenant_id)

        issues = []
        stats = {
            "total_nodes": len(all_nodes),
            "verified_ok": 0,
            "issues_found": 0,
        }

        # Build parent -> children mapping
        nodes_by_id = {n.id: n for n in all_nodes}
        children_by_parent = {}
        root_nodes = []

        for node in all_nodes:
            if node.parent_node_id:
                if node.parent_node_id not in children_by_parent:
                    children_by_parent[node.parent_node_id] = []
                children_by_parent[node.parent_node_id].append(node)
            else:
                root_nodes.append(node)

        # Check 1: Root node probability should be 1.0
        for root in root_nodes:
            if abs(root.probability - 1.0) > tolerance:
                issues.append({
                    "type": "root_probability_not_one",
                    "node_id": str(root.id),
                    "expected": 1.0,
                    "actual": root.probability,
                })
            else:
                stats["verified_ok"] += 1

        # Check 2: Children sum to parent probability
        for parent_id, children in children_by_parent.items():
            parent = nodes_by_id.get(parent_id)
            if not parent:
                continue

            children_sum = sum(c.probability for c in children)
            if abs(children_sum - parent.probability) > tolerance:
                issues.append({
                    "type": "children_sum_mismatch",
                    "parent_node_id": str(parent_id),
                    "parent_probability": parent.probability,
                    "children_sum": children_sum,
                    "difference": abs(children_sum - parent.probability),
                    "children_count": len(children),
                })
            else:
                stats["verified_ok"] += 1

        # Check 3: Cumulative probability correctness
        for node in all_nodes:
            if node.parent_node_id:
                parent = nodes_by_id.get(node.parent_node_id)
                if parent:
                    expected_cumulative = parent.cumulative_probability * node.probability
                    if abs(node.cumulative_probability - expected_cumulative) > tolerance:
                        issues.append({
                            "type": "cumulative_probability_mismatch",
                            "node_id": str(node.id),
                            "expected": expected_cumulative,
                            "actual": node.cumulative_probability,
                        })
            else:
                # Root node: cumulative should equal probability
                if abs(node.cumulative_probability - node.probability) > tolerance:
                    issues.append({
                        "type": "root_cumulative_mismatch",
                        "node_id": str(node.id),
                        "expected": node.probability,
                        "actual": node.cumulative_probability,
                    })

        stats["issues_found"] = len(issues)
        is_consistent = len(issues) == 0

        return {
            "is_consistent": is_consistent,
            "tolerance": tolerance,
            "stats": stats,
            "issues": issues if issues else None,
        }

    async def get_sibling_probability_report(
        self,
        parent_node_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Get probability report for siblings under a parent node.
        Reference: verification_checklist_v2.md §2.4

        Returns:
            Dict with parent probability, children probabilities, and sum validation.
        """
        parent = await self.get_node(parent_node_id)
        if not parent:
            raise ValueError(f"Parent node {parent_node_id} not found")

        children = await self.get_child_nodes(parent.id)

        children_data = [
            {
                "node_id": str(c.id),
                "label": c.label,
                "probability": c.probability,
                "cumulative_probability": c.cumulative_probability,
                "is_explored": c.is_explored,
            }
            for c in children
        ]

        children_sum = sum(c.probability for c in children)
        is_normalized = abs(children_sum - parent.probability) <= 0.001

        return {
            "parent": {
                "node_id": str(parent.id),
                "probability": parent.probability,
            },
            "children": children_data,
            "children_count": len(children),
            "children_sum": children_sum,
            "is_normalized": is_normalized,
            "difference": abs(children_sum - parent.probability),
        }


# =============================================================================
# Service Factory
# =============================================================================

def get_node_service(db: AsyncSession) -> NodeService:
    """Get a NodeService instance."""
    return NodeService(db)
