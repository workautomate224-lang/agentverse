"""
Node API Endpoints (Universe Map)
Reference: project.md §6.7, §5.3

Provides endpoints for:
- Viewing nodes (universe map)
- Forking nodes (creating alternative futures)
- Comparing nodes (what-if analysis)
- Path analysis

Key constraints:
- C1: Fork-not-mutate (never modify existing nodes)
- C3: Replay is read-only (nodes are immutable after creation)
- C4: Auditable artifacts (nodes versioned and persisted)
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.tenant import (
    TenantContext,
    require_tenant,
)
from app.models.user import User


def safe_parse_aggregated_outcome(data: Optional[dict]) -> Optional[dict]:
    """Safely parse aggregated outcome, handling legacy formats."""
    if not data:
        return None
    # Return as-is for flexibility - frontend handles various formats
    return data


def safe_parse_confidence(data: Optional[dict]) -> Optional[dict]:
    """Safely parse confidence data, handling legacy formats."""
    if not data:
        return None
    # Normalize to expected format while preserving all data
    result = {
        "confidence_level": data.get("confidence_level", "medium"),
        "confidence_score": data.get("confidence_score"),
        "mean": data.get("mean"),
        "std": data.get("std"),
        "sample_count": data.get("sample_count") or data.get("sample_size"),
    }
    # Include any extra fields
    for key, value in data.items():
        if key not in result:
            result[key] = value
    return result


# ============================================================================
# Request/Response Schemas (project.md §6.7)
# ============================================================================

class NodeConfidenceSchema(BaseModel):
    """Node confidence per project.md §6.7.

    Supports both:
    - Statistical metrics (mean, std, sample_count) from aggregated runs
    - Semantic metrics (confidence_level, confidence_score, factors) from initial creation

    Note: All fields are optional to handle legacy data formats.
    """
    # Statistical fields (from aggregated runs)
    mean: Optional[float] = Field(default=None)
    std: Optional[float] = Field(default=None)
    sample_count: Optional[int] = Field(default=None)

    # Semantic fields (from initial node creation)
    confidence_level: Optional[str] = Field(default="medium")
    confidence_score: Optional[float] = Field(default=None)
    factors: Optional[List[dict]] = None  # Can be list or dict in legacy data

    # Legacy fields
    run_count: Optional[int] = None
    sample_size: Optional[int] = None

    class Config:
        extra = "allow"  # Allow extra fields for forward/backward compatibility


class AggregatedOutcomeSchema(BaseModel):
    """Aggregated outcome from simulation.

    Note: All fields are optional to handle legacy data formats.
    New nodes should populate outcome_type and primary_metric.
    """
    # Required for new nodes, optional for legacy data
    outcome_type: Optional[str] = None
    primary_metric: Optional[float] = None

    # Standard fields
    metrics: dict = Field(default_factory=dict)
    distribution: Optional[dict] = None
    top_factors: List[dict] = Field(default_factory=list)

    # Legacy fields (from old simulation format)
    seed: Optional[int] = None
    key_metrics: Optional[List[dict]] = None  # List of {unit, value, name} dicts
    outcome_probability: Optional[float] = None
    outcome_distribution: Optional[dict] = None
    agent_states: Optional[List[dict]] = None

    class Config:
        extra = "allow"  # Allow extra fields for forward compatibility


class NodeResponse(BaseModel):
    """Node response per project.md §6.7."""
    node_id: str
    project_id: str
    parent_node_id: Optional[str] = None  # Match frontend's SpecNode interface
    depth: int
    label: Optional[str] = None

    # Exploration state
    is_explored: bool = False
    is_pruned: bool = False

    # Probability (for Universe Map display)
    probability: float = 1.0
    cumulative_probability: float = 1.0

    # Results (if explored) - using dict to handle legacy data formats
    aggregated_outcome: Optional[dict] = None
    confidence: Optional[dict] = None
    run_refs: List[str] = Field(default_factory=list)

    # Clustering
    cluster_id: Optional[str] = None
    is_cluster_rep: bool = False
    is_cluster_representative: bool = False  # Alias for compatibility
    is_baseline: bool = False

    # Timestamps
    created_at: str
    updated_at: Optional[str] = None
    explored_at: Optional[str] = None

    class Config:
        from_attributes = True


class EdgeResponse(BaseModel):
    """Edge response per project.md §6.7."""
    edge_id: str
    from_node_id: str  # Match frontend's SpecEdge interface
    to_node_id: str    # Match frontend's SpecEdge interface

    # Intervention that caused this edge
    intervention: dict = Field(default_factory=dict)
    intervention_label: Optional[str] = None

    # Metrics
    outcome_delta: Optional[dict] = None
    significance_score: Optional[float] = None
    weight: Optional[float] = None
    is_primary_path: bool = False

    # Metadata
    created_at: str
    updated_at: Optional[str] = None
    explanation: Optional[dict] = None


class ScenarioPatchSchema(BaseModel):
    """Scenario patch for forked nodes."""
    environment_overrides: Optional[dict] = None
    perception_deltas: Optional[dict] = None
    network_changes: Optional[dict] = None
    nl_description: Optional[str] = None
    patch_description: Optional[str] = None


class ForkNodeRequest(BaseModel):
    """Request to fork a node.

    Supports two formats:
    1. Simple: intervention dict with changes
    2. Structured: scenario_patch with typed fields
    """
    parent_node_id: str = Field(..., description="Node to fork from")

    # Option 1: Simple intervention dict
    intervention: Optional[dict] = Field(None, description="Changes for the fork")
    intervention_label: Optional[str] = Field(None, description="Human-readable description")

    # Option 2: Structured format (from frontend)
    label: Optional[str] = Field(None, description="Fork label")
    description: Optional[str] = Field(None, description="Fork description")
    scenario_patch: Optional[ScenarioPatchSchema] = Field(None, description="Structured scenario changes")
    intervention_type: Optional[str] = Field(None, description="Type: expansion, variable_delta, nl_query")
    nl_query: Optional[str] = Field(None, description="Natural language query for fork")

    auto_run: bool = Field(default=False, description="Start simulation immediately")


class ForkNodeResponse(BaseModel):
    """Response from forking a node."""
    node: NodeResponse
    edge: EdgeResponse
    run_id: Optional[str] = None
    task_id: Optional[str] = None


class UniverseMapResponse(BaseModel):
    """Complete universe map for a project."""
    project_id: str
    nodes: List[NodeResponse]
    edges: List[EdgeResponse]
    root_node_id: Optional[str] = None  # None for projects with no nodes yet
    total_nodes: int
    explored_nodes: int
    max_depth: int


class PathAnalysisRequest(BaseModel):
    """Request for path analysis between nodes."""
    start_node_id: str
    end_node_id: str
    include_siblings: bool = False


class PathAnalysisResponse(BaseModel):
    """Path analysis result."""
    path: List[NodeResponse]
    edges: List[EdgeResponse]
    total_interventions: int
    cumulative_delta: dict
    key_decision_points: List[dict]


class NodeComparisonRequest(BaseModel):
    """Request to compare two nodes."""
    node_id_a: str
    node_id_b: str
    metrics: Optional[List[str]] = None


class NodeComparisonResponse(BaseModel):
    """Comparison between two nodes."""
    node_a: NodeResponse
    node_b: NodeResponse
    common_ancestor: Optional[NodeResponse]
    divergence_depth: int
    metric_differences: dict
    key_differences: List[dict]
    statistical_significance: dict


# ============================================================================
# API Router
# ============================================================================

router = APIRouter()


@router.get(
    "/",
    response_model=List[NodeResponse],
    summary="List nodes for a project",
)
async def list_nodes(
    project_id: str = Query(..., description="Project ID"),
    explored_only: bool = Query(False, description="Only explored nodes"),
    depth: Optional[int] = Query(None, ge=0, description="Filter by depth"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> List[NodeResponse]:
    """
    List all nodes in a project's universe map.

    Nodes represent possible future states. Unexplored nodes are
    potential futures that haven't been simulated yet.
    """
    from app.services import get_node_service

    node_service = get_node_service(db)

    nodes = await node_service.list_nodes(
        project_id=project_id,
        tenant_id=tenant_ctx.tenant_id,
        explored_only=explored_only,
        depth=depth,
        skip=skip,
        limit=limit,
    )

    return [
        NodeResponse(
            node_id=str(node.id),
            project_id=str(node.project_id),
            parent_node_id=str(node.parent_node_id) if node.parent_node_id else None,
            depth=node.depth,
            label=node.label,
            is_explored=node.is_explored,
            is_pruned=False,  # Model doesn't have is_pruned yet
            probability=node.probability,
            cumulative_probability=node.cumulative_probability,
            aggregated_outcome=safe_parse_aggregated_outcome(node.aggregated_outcome),
            confidence=safe_parse_confidence(node.confidence),
            run_refs=[str(ref.get("run_id", ref)) if isinstance(ref, dict) else str(ref) for ref in (node.run_refs or [])],
            cluster_id=str(node.cluster_id) if node.cluster_id else None,
            is_cluster_rep=node.is_cluster_representative,
            is_cluster_representative=node.is_cluster_representative,
            is_baseline=node.is_baseline,
            created_at=node.created_at.isoformat() if node.created_at else "",
            updated_at=node.updated_at.isoformat() if node.updated_at else None,
            explored_at=node.updated_at.isoformat() if node.is_explored and node.updated_at else None,
        )
        for node in nodes
    ]


@router.get(
    "/{node_id}",
    response_model=NodeResponse,
    summary="Get node details",
)
async def get_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> NodeResponse:
    """Get details of a specific node."""
    from app.services import get_node_service

    node_service = get_node_service(db)

    node = await node_service.get_node(node_id, tenant_ctx.tenant_id)

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found",
        )

    return NodeResponse(
        node_id=str(node.id),
        project_id=str(node.project_id),
        parent_node_id=str(node.parent_node_id) if node.parent_node_id else None,
        depth=node.depth,
        label=node.label,
        is_explored=node.is_explored,
        is_pruned=False,
        probability=node.probability,
        cumulative_probability=node.cumulative_probability,
        aggregated_outcome=safe_parse_aggregated_outcome(node.aggregated_outcome),
        confidence=safe_parse_confidence(node.confidence),
        run_refs=[str(ref.get("run_id", ref)) if isinstance(ref, dict) else str(ref) for ref in (node.run_refs or [])],
        cluster_id=str(node.cluster_id) if node.cluster_id else None,
        is_cluster_rep=node.is_cluster_representative,
        is_cluster_representative=node.is_cluster_representative,
        is_baseline=node.is_baseline,
        created_at=node.created_at.isoformat() if node.created_at else "",
        updated_at=node.updated_at.isoformat() if node.updated_at else None,
        explored_at=node.updated_at.isoformat() if node.is_explored and node.updated_at else None,
    )


@router.post(
    "/fork/",
    response_model=ForkNodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Fork a node (create alternative future)",
)
async def fork_node(
    request: ForkNodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ForkNodeResponse:
    """
    Fork a node to create an alternative future.

    This implements C1 (fork-not-mutate): the parent node is never
    modified, and a new child node is created with the intervention
    applied.

    Reference: project.md §6.7 (Fork-not-mutate)
    """
    from app.services import get_simulation_orchestrator

    orchestrator = get_simulation_orchestrator(db)

    # Build intervention dict from either format
    intervention = request.intervention or {}

    # If scenario_patch is provided, convert to intervention
    if request.scenario_patch:
        patch = request.scenario_patch
        if patch.environment_overrides:
            intervention["environment_overrides"] = patch.environment_overrides
        if patch.perception_deltas:
            intervention["perception_deltas"] = patch.perception_deltas
        if patch.network_changes:
            intervention["network_changes"] = patch.network_changes
        if patch.nl_description:
            intervention["nl_description"] = patch.nl_description
        if patch.patch_description:
            intervention["patch_description"] = patch.patch_description

    # Add intervention type
    if request.intervention_type:
        intervention["intervention_type"] = request.intervention_type

    # Add nl_query if provided
    if request.nl_query:
        intervention["nl_query"] = request.nl_query

    # Build intervention label
    intervention_label = (
        request.intervention_label
        or request.label
        or request.description
        or None
    )

    try:
        # Fork the node - returns (Node, Edge, NodePatch) tuple
        node, edge, node_patch = await orchestrator.fork_node(
            parent_node_id=request.parent_node_id,
            tenant_id=tenant_ctx.tenant_id,
            scenario_patch=intervention if intervention else None,
            intervention=intervention,
            explanation=intervention_label,
        )

        await db.commit()

        return ForkNodeResponse(
            node=NodeResponse(
                node_id=str(node.id),
                project_id=str(node.project_id),
                parent_node_id=str(node.parent_node_id) if node.parent_node_id else None,
                depth=node.depth,
                label=node.label or intervention_label,
                is_explored=node.is_explored,
                is_pruned=False,
                run_refs=[str(ref.get("run_id", ref)) if isinstance(ref, dict) else str(ref) for ref in (node.run_refs or [])],
                created_at=node.created_at.isoformat() if node.created_at else "",
            ),
            edge=EdgeResponse(
                edge_id=str(edge.id),
                from_node_id=str(edge.from_node_id),
                to_node_id=str(edge.to_node_id),
                intervention=edge.intervention or intervention,
                intervention_label=edge.explanation.get("short_label") if edge.explanation else intervention_label,
                created_at=edge.created_at.isoformat() if edge.created_at else "",
            ),
            run_id=None,
            task_id=None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fork node: {str(e)}",
        )


@router.get(
    "/{node_id}/children",
    response_model=List[NodeResponse],
    summary="Get child nodes",
)
async def get_node_children(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> List[NodeResponse]:
    """Get all child nodes (alternative futures) of a node."""
    from app.services import get_node_service

    node_service = get_node_service(db)

    children = await node_service.get_children(node_id, tenant_ctx.tenant_id)

    return [
        NodeResponse(
            node_id=str(node.id),
            project_id=str(node.project_id),
            parent_node_id=str(node.parent_node_id) if node.parent_node_id else None,
            depth=node.depth,
            label=node.label,
            is_explored=node.is_explored,
            is_pruned=False,  # Node model doesn't have is_pruned
            aggregated_outcome=safe_parse_aggregated_outcome(node.aggregated_outcome),
            confidence=safe_parse_confidence(node.confidence),
            run_refs=[str(ref.get("run_id", ref)) if isinstance(ref, dict) else str(ref) for ref in (node.run_refs or [])],
            cluster_id=str(node.cluster_id) if node.cluster_id else None,
            is_cluster_rep=node.is_cluster_representative,
            created_at=node.created_at.isoformat() if node.created_at else "",
            explored_at=node.updated_at.isoformat() if node.is_explored and node.updated_at else None,
        )
        for node in children
    ]


@router.get(
    "/{node_id}/edges",
    response_model=List[EdgeResponse],
    summary="Get edges from a node",
)
async def get_node_edges(
    node_id: str,
    direction: str = Query("outgoing", pattern="^(incoming|outgoing|both)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> List[EdgeResponse]:
    """Get edges connected to a node."""
    from app.services import get_node_service

    node_service = get_node_service(db)

    edges = await node_service.get_edges(
        node_id=node_id,
        tenant_id=tenant_ctx.tenant_id,
        direction=direction,
    )

    return [
        EdgeResponse(
            edge_id=str(edge.id),
            from_node_id=str(edge.from_node_id),
            to_node_id=str(edge.to_node_id),
            intervention=edge.intervention or {},
            intervention_label=edge.explanation.get("short_label") if edge.explanation else None,
            outcome_delta=None,  # Edge model doesn't have outcome_delta
            significance_score=edge.weight,
            created_at=edge.created_at.isoformat() if edge.created_at else "",
            explanation=edge.explanation,
        )
        for edge in edges
    ]


@router.get(
    "/universe-map/{project_id}",
    response_model=UniverseMapResponse,
    summary="Get complete universe map",
)
async def get_universe_map(
    project_id: str,
    max_depth: Optional[int] = Query(None, ge=0),
    explored_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> UniverseMapResponse:
    """
    Get the complete universe map for a project.

    The universe map is a tree/DAG of all explored and unexplored
    possible futures. Each node represents a state; edges represent
    interventions.

    Reference: project.md §6.7 (Universe Map)
    """
    from app.services import get_simulation_orchestrator

    orchestrator = get_simulation_orchestrator(db)

    universe_map = await orchestrator.get_universe_map(
        project_id=project_id,
        tenant_id=tenant_ctx.tenant_id,
        max_depth=max_depth,
        explored_only=explored_only,
    )

    # Return empty universe map for projects with no nodes (valid state for new projects)
    if not universe_map:
        return UniverseMapResponse(
            project_id=project_id,
            nodes=[],
            edges=[],
            root_node_id=None,
            total_nodes=0,
            explored_nodes=0,
            max_depth=0,
        )

    nodes = [
        NodeResponse(
            node_id=str(node.id),
            project_id=str(node.project_id),
            parent_node_id=str(node.parent_node_id) if node.parent_node_id else None,
            depth=node.depth,
            label=node.label,
            is_explored=node.is_explored,
            is_pruned=False,  # Node model doesn't have is_pruned
            aggregated_outcome=safe_parse_aggregated_outcome(node.aggregated_outcome),
            confidence=safe_parse_confidence(node.confidence),
            run_refs=[str(ref.get("run_id", ref)) if isinstance(ref, dict) else str(ref) for ref in (node.run_refs or [])],
            cluster_id=str(node.cluster_id) if node.cluster_id else None,
            is_cluster_rep=node.is_cluster_representative,
            created_at=node.created_at.isoformat() if node.created_at else "",
            explored_at=node.updated_at.isoformat() if node.is_explored and node.updated_at else None,
        )
        for node in universe_map.nodes
    ]

    edges = [
        EdgeResponse(
            edge_id=str(edge.id),
            from_node_id=str(edge.from_node_id),
            to_node_id=str(edge.to_node_id),
            intervention=edge.intervention or {},
            intervention_label=edge.explanation.get("short_label") if edge.explanation else None,
            outcome_delta=None,  # Edge model doesn't have outcome_delta
            significance_score=edge.weight,
            created_at=edge.created_at.isoformat() if edge.created_at else "",
            explanation=edge.explanation,
        )
        for edge in universe_map.edges
    ]

    return UniverseMapResponse(
        project_id=project_id,
        nodes=nodes,
        edges=edges,
        root_node_id=universe_map.root_node_id,
        total_nodes=universe_map.total_nodes,
        explored_nodes=universe_map.explored_nodes,
        max_depth=universe_map.max_depth,
    )


@router.post(
    "/path-analysis/",
    response_model=PathAnalysisResponse,
    summary="Analyze path between nodes",
)
async def analyze_path(
    request: PathAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> PathAnalysisResponse:
    """
    Analyze the path between two nodes.

    This shows the sequence of interventions (decisions) that lead
    from one state to another, useful for understanding causality.

    Reference: project.md §6.7 (Path analysis)
    """
    from app.services import get_node_service

    node_service = get_node_service(db)

    analysis = await node_service.analyze_path(
        start_node_id=request.start_node_id,
        end_node_id=request.end_node_id,
        tenant_id=tenant_ctx.tenant_id,
        include_siblings=request.include_siblings,
    )

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Path not found between nodes",
        )

    path = [
        NodeResponse(
            node_id=str(node.id),
            project_id=str(node.project_id),
            parent_node_id=str(node.parent_node_id) if node.parent_node_id else None,
            depth=node.depth,
            label=node.label,
            is_explored=node.is_explored,
            is_pruned=False,
            aggregated_outcome=safe_parse_aggregated_outcome(node.aggregated_outcome),
            confidence=safe_parse_confidence(node.confidence),
            run_refs=[str(ref.get("run_id", ref)) if isinstance(ref, dict) else str(ref) for ref in (node.run_refs or [])],
            cluster_id=str(node.cluster_id) if node.cluster_id else None,
            is_cluster_rep=node.is_cluster_representative,
            created_at=node.created_at.isoformat() if node.created_at else "",
            explored_at=node.updated_at.isoformat() if node.is_explored and node.updated_at else None,
        )
        for node in analysis.path
    ]

    edges = [
        EdgeResponse(
            edge_id=str(edge.id),
            from_node_id=str(edge.from_node_id),
            to_node_id=str(edge.to_node_id),
            intervention=edge.intervention or {},
            intervention_label=edge.explanation.get("short_label") if edge.explanation else None,
            outcome_delta=None,
            significance_score=edge.weight,
            created_at=edge.created_at.isoformat() if edge.created_at else "",
            explanation=edge.explanation,
        )
        for edge in analysis.edges
    ]

    return PathAnalysisResponse(
        path=path,
        edges=edges,
        total_interventions=analysis.total_interventions,
        cumulative_delta=analysis.cumulative_delta,
        key_decision_points=analysis.key_decision_points,
    )


@router.post(
    "/compare/",
    response_model=NodeComparisonResponse,
    summary="Compare two nodes",
)
async def compare_nodes(
    request: NodeComparisonRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> NodeComparisonResponse:
    """
    Compare two nodes to understand outcome differences.

    This is the core of what-if analysis: understanding how different
    decisions (interventions) lead to different outcomes.

    Reference: project.md §5.3 (What-if analysis)
    """
    from app.services import get_simulation_orchestrator

    orchestrator = get_simulation_orchestrator(db)

    comparison = await orchestrator.compare_nodes(
        node_id_a=request.node_id_a,
        node_id_b=request.node_id_b,
        tenant_id=tenant_ctx.tenant_id,
        metrics=request.metrics,
    )

    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both nodes not found",
        )

    def node_to_response(node) -> NodeResponse:
        return NodeResponse(
            node_id=str(node.id),
            project_id=str(node.project_id),
            parent_node_id=str(node.parent_node_id) if node.parent_node_id else None,
            depth=node.depth,
            label=node.label,
            is_explored=node.is_explored,
            is_pruned=False,
            aggregated_outcome=safe_parse_aggregated_outcome(node.aggregated_outcome),
            confidence=safe_parse_confidence(node.confidence),
            run_refs=[str(ref.get("run_id", ref)) if isinstance(ref, dict) else str(ref) for ref in (node.run_refs or [])],
            cluster_id=str(node.cluster_id) if node.cluster_id else None,
            is_cluster_rep=node.is_cluster_representative,
            created_at=node.created_at.isoformat() if node.created_at else "",
            explored_at=node.updated_at.isoformat() if node.is_explored and node.updated_at else None,
        )

    return NodeComparisonResponse(
        node_a=node_to_response(comparison["node_a"]),
        node_b=node_to_response(comparison["node_b"]),
        common_ancestor=(
            node_to_response(comparison["common_ancestor"])
            if comparison.get("common_ancestor") else None
        ),
        divergence_depth=comparison["divergence_depth"],
        metric_differences=comparison["metric_differences"],
        key_differences=comparison["key_differences"],
        statistical_significance=comparison["statistical_significance"],
    )


@router.post(
    "/{node_id}/prune",
    response_model=NodeResponse,
    summary="Prune a node",
)
async def prune_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> NodeResponse:
    """
    Mark a node as pruned (excluded from analysis).

    Pruned nodes are kept for audit purposes but excluded from
    aggregations and comparisons. This follows C1 (never delete).
    """
    from app.services import get_node_service

    node_service = get_node_service(db)

    node = await node_service.prune_node(node_id, tenant_ctx.tenant_id)

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found",
        )

    await db.commit()

    return NodeResponse(
        node_id=str(node.id),
        project_id=str(node.project_id),
        parent_node_id=str(node.parent_node_id) if node.parent_node_id else None,
        depth=node.depth,
        label=node.label,
        is_explored=node.is_explored,
        is_pruned=False,
        run_refs=[str(ref.get("run_id", ref)) if isinstance(ref, dict) else str(ref) for ref in (node.run_refs or [])],
        cluster_id=str(node.cluster_id) if node.cluster_id else None,
        is_cluster_rep=node.is_cluster_representative,
        created_at=node.created_at.isoformat() if node.created_at else "",
        explored_at=node.updated_at.isoformat() if node.is_explored and node.updated_at else None,
    )


# =============================================================================
# Probability Verification Endpoints (§2.4)
# Reference: verification_checklist_v2.md §2.4 (Conditional Probability Correctness)
# =============================================================================


class ProbabilityConsistencyResponse(BaseModel):
    """Response for probability consistency verification."""
    is_consistent: bool
    tolerance: float
    stats: dict
    issues: Optional[List[dict]] = None


class SiblingProbabilityResponse(BaseModel):
    """Response for sibling probability report."""
    parent: dict
    children: List[dict]
    children_count: int
    children_sum: float
    is_normalized: bool
    difference: float


class NormalizationResponse(BaseModel):
    """Response for probability normalization."""
    status: str
    parent_probability: float
    before_sum: Optional[float] = None
    after_sum: Optional[float] = None
    children_count: int
    before: Optional[List[dict]] = None
    after: Optional[List[dict]] = None


@router.get(
    "/project/{project_id}/verify-probabilities",
    response_model=ProbabilityConsistencyResponse,
    summary="Verify probability consistency (§2.4)",
)
async def verify_probability_consistency(
    project_id: str,
    tolerance: float = Query(default=0.001, ge=0, le=0.1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ProbabilityConsistencyResponse:
    """
    Verify probability consistency across all nodes in a project.

    Reference: verification_checklist_v2.md §2.4 (Conditional Probability Correctness)

    Checks:
    1. Root node probability is 1.0
    2. Children probabilities sum to parent probability (within tolerance)
    3. Cumulative probabilities are correctly computed

    Returns verification report with any issues found.
    """
    from app.services import get_node_service

    node_service = get_node_service(db)

    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format",
        )

    result = await node_service.verify_probability_consistency(
        project_id=project_uuid,
        tenant_id=tenant_ctx.tenant_id,
        tolerance=tolerance,
    )

    return ProbabilityConsistencyResponse(
        is_consistent=result["is_consistent"],
        tolerance=result["tolerance"],
        stats=result["stats"],
        issues=result.get("issues"),
    )


@router.get(
    "/{node_id}/sibling-probabilities",
    response_model=SiblingProbabilityResponse,
    summary="Get sibling probability report (§2.4)",
)
async def get_sibling_probabilities(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> SiblingProbabilityResponse:
    """
    Get probability report for children under a parent node.

    Reference: verification_checklist_v2.md §2.4

    Returns parent probability, children probabilities, and validation status.
    """
    from app.services import get_node_service

    node_service = get_node_service(db)

    try:
        node_uuid = UUID(node_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid node ID format",
        )

    try:
        result = await node_service.get_sibling_probability_report(node_uuid)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return SiblingProbabilityResponse(
        parent=result["parent"],
        children=result["children"],
        children_count=result["children_count"],
        children_sum=result["children_sum"],
        is_normalized=result["is_normalized"],
        difference=result["difference"],
    )


@router.post(
    "/{node_id}/normalize-children",
    response_model=NormalizationResponse,
    summary="Normalize child probabilities (§2.4)",
)
async def normalize_child_probabilities(
    node_id: str,
    tolerance: float = Query(default=0.001, ge=0, le=0.1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> NormalizationResponse:
    """
    Normalize child node probabilities to sum to parent's probability.

    Reference: verification_checklist_v2.md §2.4 (Conditional Probability Correctness)

    When a parent node is forked into multiple children, this ensures:
    P(child_1 | parent) + P(child_2 | parent) + ... = P(parent)

    Returns normalization report with before/after state.
    """
    from app.services import get_node_service

    node_service = get_node_service(db)

    try:
        node_uuid = UUID(node_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid node ID format",
        )

    try:
        result = await node_service.normalize_sibling_probabilities(
            parent_node_id=node_uuid,
            tolerance=tolerance,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    await db.commit()

    return NormalizationResponse(
        status=result["status"],
        parent_probability=result["parent_probability"],
        before_sum=result.get("before_sum"),
        after_sum=result.get("after_sum"),
        children_count=result["children_count"],
        before=result.get("before"),
        after=result.get("after"),
    )


# =============================================================================
# STEP 4: Universe Map & Node Details Endpoints
# Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md STEP 4
# =============================================================================


class NodePatchResponse(BaseModel):
    """Response for viewing a node's patch (STEP 4)."""
    patch_id: str
    node_id: str
    patch_type: str
    change_description: dict
    parameters: dict
    affected_variables: List[str]
    environment_overrides: Optional[dict] = None
    event_script_id: Optional[str] = None
    nl_description: Optional[str] = None
    created_at: str


class CollapseBranchesRequest(BaseModel):
    """Request to collapse branches under a parent node (STEP 4)."""
    parent_node_id: str = Field(..., description="Parent node whose children to collapse")
    cluster_label: Optional[str] = Field(None, description="Label for the collapsed cluster")


class CollapseBranchesResponse(BaseModel):
    """Response from collapsing branches (STEP 4)."""
    cluster_id: str
    parent_node_id: str
    collapsed_count: int
    representative_node_id: str
    cluster_label: Optional[str] = None


class BulkPruneRequest(BaseModel):
    """Request for bulk pruning nodes (STEP 4)."""
    project_id: str = Field(..., description="Project ID")
    threshold: float = Field(..., description="Threshold value for pruning")


class BulkPruneResponse(BaseModel):
    """Response from bulk pruning operation (STEP 4)."""
    pruned_count: int
    threshold_used: float
    pruned_node_ids: List[str]


class RefreshStaleRequest(BaseModel):
    """Request to refresh stale nodes (STEP 4)."""
    project_id: str = Field(..., description="Project ID")
    max_nodes: Optional[int] = Field(default=10, description="Max nodes to refresh")


class RefreshStaleResponse(BaseModel):
    """Response from refreshing stale nodes (STEP 4)."""
    queued_count: int
    queued_node_ids: List[str]
    task_ids: List[str]


class RunEnsembleRequest(BaseModel):
    """Request to run ensemble simulations for a node (STEP 4)."""
    seeds: List[int] = Field(default=[42, 123, 456], description="Seeds for ensemble runs")
    auto_start: bool = Field(default=True, description="Auto-start the runs")


class RunEnsembleResponse(BaseModel):
    """Response from running ensemble (STEP 4)."""
    node_id: str
    run_ids: List[str]
    task_ids: List[str]
    ensemble_size: int


@router.get(
    "/{node_id}/patch",
    response_model=NodePatchResponse,
    summary="View node patch (STEP 4)",
)
async def get_node_patch(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> NodePatchResponse:
    """
    Get the NodePatch for a specific node.

    STEP 4 Requirement: View Patch button shows the structured patch
    describing what changed from the parent node.

    Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md STEP 4
    """
    from app.services import get_node_service

    node_service = get_node_service(db)

    try:
        node_uuid = UUID(node_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid node ID format",
        )

    patch = await node_service.get_node_patch(node_uuid, tenant_ctx.tenant_id)

    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No patch found for node {node_id}. Root/baseline nodes have no patch.",
        )

    return NodePatchResponse(
        patch_id=str(patch.id),
        node_id=str(patch.node_id),
        patch_type=patch.patch_type or "unknown",
        change_description=patch.change_description or {},
        parameters=patch.parameters or {},
        affected_variables=patch.affected_variables or [],
        environment_overrides=patch.environment_overrides,
        event_script_id=str(patch.event_script_id) if patch.event_script_id else None,
        nl_description=patch.nl_description,
        created_at=patch.created_at.isoformat() if patch.created_at else "",
    )


@router.post(
    "/collapse-branches",
    response_model=CollapseBranchesResponse,
    summary="Collapse branches under a parent (STEP 4)",
)
async def collapse_branches(
    request: CollapseBranchesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> CollapseBranchesResponse:
    """
    Collapse all child branches under a parent node into a cluster.

    STEP 4 Requirement: Collapse Branches button groups similar nodes
    for easier visualization without deleting them.

    Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md STEP 4
    """
    from app.services import get_node_service

    node_service = get_node_service(db)

    try:
        parent_uuid = UUID(request.parent_node_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid parent node ID format",
        )

    try:
        result = await node_service.collapse_branches(
            parent_node_id=parent_uuid,
            tenant_id=tenant_ctx.tenant_id,
            cluster_label=request.cluster_label,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    await db.commit()

    return CollapseBranchesResponse(
        cluster_id=str(result["cluster_id"]),
        parent_node_id=str(result["parent_node_id"]),
        collapsed_count=result["collapsed_count"],
        representative_node_id=str(result["representative_node_id"]),
        cluster_label=result.get("cluster_label"),
    )


@router.post(
    "/prune/low-probability",
    response_model=BulkPruneResponse,
    summary="Prune nodes below probability threshold (STEP 4)",
)
async def prune_low_probability(
    request: BulkPruneRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> BulkPruneResponse:
    """
    Prune all nodes in a project below a probability threshold.

    STEP 4 Requirement: Prune Low Probability button removes
    unlikely futures from the active view (keeps for audit).

    Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md STEP 4
    """
    from app.services import get_node_service

    node_service = get_node_service(db)

    try:
        project_uuid = UUID(request.project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format",
        )

    if not 0 <= request.threshold <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Threshold must be between 0 and 1",
        )

    result = await node_service.prune_by_probability(
        project_id=project_uuid,
        tenant_id=tenant_ctx.tenant_id,
        threshold=request.threshold,
    )

    await db.commit()

    return BulkPruneResponse(
        pruned_count=result["pruned_count"],
        threshold_used=result["threshold_used"],
        pruned_node_ids=[str(nid) for nid in result["pruned_node_ids"]],
    )


@router.post(
    "/prune/low-reliability",
    response_model=BulkPruneResponse,
    summary="Prune nodes below reliability threshold (STEP 4)",
)
async def prune_low_reliability(
    request: BulkPruneRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> BulkPruneResponse:
    """
    Prune all nodes in a project below a reliability threshold.

    STEP 4 Requirement: Prune Low Reliability button removes
    unreliable nodes from the active view (keeps for audit).

    Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md STEP 4
    """
    from app.services import get_node_service

    node_service = get_node_service(db)

    try:
        project_uuid = UUID(request.project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format",
        )

    if not 0 <= request.threshold <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Threshold must be between 0 and 1",
        )

    result = await node_service.prune_by_reliability(
        project_id=project_uuid,
        tenant_id=tenant_ctx.tenant_id,
        threshold=request.threshold,
    )

    await db.commit()

    return BulkPruneResponse(
        pruned_count=result["pruned_count"],
        threshold_used=result["threshold_used"],
        pruned_node_ids=[str(nid) for nid in result["pruned_node_ids"]],
    )


@router.post(
    "/refresh-stale",
    response_model=RefreshStaleResponse,
    summary="Refresh stale nodes (STEP 4)",
)
async def refresh_stale_nodes(
    request: RefreshStaleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> RefreshStaleResponse:
    """
    Queue stale nodes for re-simulation.

    STEP 4 Requirement: Refresh Stale Nodes button triggers
    re-runs for nodes that are marked as stale due to upstream changes.

    Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md STEP 4
    """
    from app.services import get_node_service, get_simulation_orchestrator

    node_service = get_node_service(db)
    orchestrator = get_simulation_orchestrator(db)

    try:
        project_uuid = UUID(request.project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format",
        )

    # Get stale nodes (ordered by depth to process ancestors first)
    stale_nodes = await node_service.get_stale_nodes(
        project_id=project_uuid,
        tenant_id=tenant_ctx.tenant_id,
    )

    # Limit to max_nodes
    nodes_to_refresh = stale_nodes[:request.max_nodes]

    # Queue runs for each stale node
    queued_node_ids = []
    task_ids = []

    for node in nodes_to_refresh:
        try:
            result = await orchestrator.queue_node_refresh(
                node_id=str(node.id),
                tenant_id=str(tenant_ctx.tenant_id),
            )
            queued_node_ids.append(str(node.id))
            if result.get("task_id"):
                task_ids.append(result["task_id"])
        except Exception:
            # Skip nodes that fail to queue
            continue

    await db.commit()

    return RefreshStaleResponse(
        queued_count=len(queued_node_ids),
        queued_node_ids=queued_node_ids,
        task_ids=task_ids,
    )


@router.post(
    "/{node_id}/run-ensemble",
    response_model=RunEnsembleResponse,
    summary="Run ensemble simulations for a node (STEP 4)",
)
async def run_node_ensemble(
    node_id: str,
    request: RunEnsembleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> RunEnsembleResponse:
    """
    Run multiple simulations with different seeds for ensemble aggregation.

    STEP 4 Requirement: Run Node Ensemble button creates multiple runs
    with different seeds to compute aggregated outcome statistics.

    Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md STEP 4
    """
    from app.services import get_simulation_orchestrator

    orchestrator = get_simulation_orchestrator(db)

    try:
        node_uuid = UUID(node_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid node ID format",
        )

    if len(request.seeds) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ensemble requires at least 2 seeds",
        )

    try:
        result = await orchestrator.run_node_ensemble(
            node_id=str(node_uuid),
            tenant_id=str(tenant_ctx.tenant_id),
            seeds=request.seeds,
            auto_start=request.auto_start,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    await db.commit()

    return RunEnsembleResponse(
        node_id=str(node_uuid),
        run_ids=[str(rid) for rid in result["run_ids"]],
        task_ids=result.get("task_ids", []),
        ensemble_size=len(request.seeds),
    )
