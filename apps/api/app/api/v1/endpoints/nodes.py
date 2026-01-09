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


# ============================================================================
# Request/Response Schemas (project.md §6.7)
# ============================================================================

class NodeConfidenceSchema(BaseModel):
    """Node confidence per project.md §6.7."""
    mean: float = Field(ge=0.0, le=1.0)
    std: float = Field(ge=0.0)
    sample_count: int = Field(ge=0)


class AggregatedOutcomeSchema(BaseModel):
    """Aggregated outcome from simulation."""
    outcome_type: str
    primary_metric: float
    metrics: dict = Field(default_factory=dict)
    distribution: Optional[dict] = None
    top_factors: List[dict] = Field(default_factory=list)


class NodeResponse(BaseModel):
    """Node response per project.md §6.7."""
    node_id: str
    project_id: str
    parent_id: Optional[str]
    depth: int
    label: Optional[str]

    # Exploration state
    is_explored: bool
    is_pruned: bool

    # Results (if explored)
    aggregated_outcome: Optional[AggregatedOutcomeSchema] = None
    confidence: Optional[NodeConfidenceSchema] = None
    run_refs: List[str] = Field(default_factory=list)

    # Clustering
    cluster_id: Optional[str] = None
    is_cluster_rep: bool = False

    # Timestamps
    created_at: str
    explored_at: Optional[str] = None

    class Config:
        from_attributes = True


class EdgeResponse(BaseModel):
    """Edge response per project.md §6.7."""
    edge_id: str
    parent_id: str
    child_id: str

    # Intervention that caused this edge
    intervention: dict = Field(default_factory=dict)
    intervention_label: Optional[str] = None

    # Metrics
    outcome_delta: Optional[dict] = None
    significance_score: Optional[float] = None

    # Metadata
    created_at: str
    explanation: Optional[dict] = None


class ForkNodeRequest(BaseModel):
    """Request to fork a node."""
    parent_node_id: str = Field(..., description="Node to fork from")
    intervention: dict = Field(..., description="Changes for the fork")
    intervention_label: Optional[str] = Field(
        None,
        description="Human-readable description"
    )
    auto_run: bool = Field(
        default=False,
        description="Start simulation immediately"
    )


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
    root_node_id: str
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
            node_id=node.node_id,
            project_id=node.project_id,
            parent_id=node.parent_id,
            depth=node.depth,
            label=node.label,
            is_explored=node.is_explored,
            is_pruned=node.is_pruned,
            aggregated_outcome=(
                AggregatedOutcomeSchema(**node.aggregated_outcome)
                if node.aggregated_outcome else None
            ),
            confidence=(
                NodeConfidenceSchema(**node.confidence)
                if node.confidence else None
            ),
            run_refs=node.run_refs or [],
            cluster_id=node.cluster_id,
            is_cluster_rep=node.is_cluster_rep,
            created_at=node.created_at,
            explored_at=node.explored_at,
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
        node_id=node.node_id,
        project_id=node.project_id,
        parent_id=node.parent_id,
        depth=node.depth,
        label=node.label,
        is_explored=node.is_explored,
        is_pruned=node.is_pruned,
        aggregated_outcome=(
            AggregatedOutcomeSchema(**node.aggregated_outcome)
            if node.aggregated_outcome else None
        ),
        confidence=(
            NodeConfidenceSchema(**node.confidence)
            if node.confidence else None
        ),
        run_refs=node.run_refs or [],
        cluster_id=node.cluster_id,
        is_cluster_rep=node.is_cluster_rep,
        created_at=node.created_at,
        explored_at=node.explored_at,
    )


@router.post(
    "/fork",
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

    try:
        result = await orchestrator.fork_node(
            parent_node_id=request.parent_node_id,
            intervention=request.intervention,
            intervention_label=request.intervention_label,
            tenant_id=tenant_ctx.tenant_id,
            user_id=str(current_user.id),
            auto_run=request.auto_run,
        )

        await db.commit()

        node, edge = result["node"], result["edge"]
        run_id = result.get("run_id")
        task_id = result.get("task_id")

        return ForkNodeResponse(
            node=NodeResponse(
                node_id=node.node_id,
                project_id=node.project_id,
                parent_id=node.parent_id,
                depth=node.depth,
                label=node.label,
                is_explored=node.is_explored,
                is_pruned=node.is_pruned,
                run_refs=node.run_refs or [],
                created_at=node.created_at,
            ),
            edge=EdgeResponse(
                edge_id=edge.edge_id,
                parent_id=edge.parent_id,
                child_id=edge.child_id,
                intervention=edge.intervention,
                intervention_label=edge.intervention_label,
                created_at=edge.created_at,
            ),
            run_id=run_id,
            task_id=task_id,
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
            node_id=node.node_id,
            project_id=node.project_id,
            parent_id=node.parent_id,
            depth=node.depth,
            label=node.label,
            is_explored=node.is_explored,
            is_pruned=node.is_pruned,
            aggregated_outcome=(
                AggregatedOutcomeSchema(**node.aggregated_outcome)
                if node.aggregated_outcome else None
            ),
            confidence=(
                NodeConfidenceSchema(**node.confidence)
                if node.confidence else None
            ),
            run_refs=node.run_refs or [],
            created_at=node.created_at,
            explored_at=node.explored_at,
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
            edge_id=edge.edge_id,
            parent_id=edge.parent_id,
            child_id=edge.child_id,
            intervention=edge.intervention,
            intervention_label=edge.intervention_label,
            outcome_delta=edge.outcome_delta,
            significance_score=edge.significance_score,
            created_at=edge.created_at,
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

    if not universe_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found or has no nodes",
        )

    nodes = [
        NodeResponse(
            node_id=node.node_id,
            project_id=node.project_id,
            parent_id=node.parent_id,
            depth=node.depth,
            label=node.label,
            is_explored=node.is_explored,
            is_pruned=node.is_pruned,
            aggregated_outcome=(
                AggregatedOutcomeSchema(**node.aggregated_outcome)
                if node.aggregated_outcome else None
            ),
            confidence=(
                NodeConfidenceSchema(**node.confidence)
                if node.confidence else None
            ),
            run_refs=node.run_refs or [],
            cluster_id=node.cluster_id,
            is_cluster_rep=node.is_cluster_rep,
            created_at=node.created_at,
            explored_at=node.explored_at,
        )
        for node in universe_map.nodes
    ]

    edges = [
        EdgeResponse(
            edge_id=edge.edge_id,
            parent_id=edge.parent_id,
            child_id=edge.child_id,
            intervention=edge.intervention,
            intervention_label=edge.intervention_label,
            outcome_delta=edge.outcome_delta,
            significance_score=edge.significance_score,
            created_at=edge.created_at,
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
    "/path-analysis",
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
            node_id=node.node_id,
            project_id=node.project_id,
            parent_id=node.parent_id,
            depth=node.depth,
            label=node.label,
            is_explored=node.is_explored,
            is_pruned=node.is_pruned,
            aggregated_outcome=(
                AggregatedOutcomeSchema(**node.aggregated_outcome)
                if node.aggregated_outcome else None
            ),
            run_refs=node.run_refs or [],
            created_at=node.created_at,
        )
        for node in analysis.path
    ]

    edges = [
        EdgeResponse(
            edge_id=edge.edge_id,
            parent_id=edge.parent_id,
            child_id=edge.child_id,
            intervention=edge.intervention,
            intervention_label=edge.intervention_label,
            outcome_delta=edge.outcome_delta,
            created_at=edge.created_at,
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
    "/compare",
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
            node_id=node.node_id,
            project_id=node.project_id,
            parent_id=node.parent_id,
            depth=node.depth,
            label=node.label,
            is_explored=node.is_explored,
            is_pruned=node.is_pruned,
            aggregated_outcome=(
                AggregatedOutcomeSchema(**node.aggregated_outcome)
                if node.aggregated_outcome else None
            ),
            confidence=(
                NodeConfidenceSchema(**node.confidence)
                if node.confidence else None
            ),
            run_refs=node.run_refs or [],
            created_at=node.created_at,
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
        node_id=node.node_id,
        project_id=node.project_id,
        parent_id=node.parent_id,
        depth=node.depth,
        label=node.label,
        is_explored=node.is_explored,
        is_pruned=node.is_pruned,
        run_refs=node.run_refs or [],
        created_at=node.created_at,
    )
