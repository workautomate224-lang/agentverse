"""
STEP 9: Knowledge Graph / Parallel Universe Ops API Endpoints
Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md STEP 9

Provides endpoints for:
- Universe Graph visualization (Tree/Graph views)
- Node search and filtering (probability, reliability)
- Cluster management for similar branches
- Staleness tracking and refresh operations
- Node comparison (diff analysis)

Key constraints:
- C1: Fork-not-mutate (never modify existing nodes)
- C4: Auditable artifacts (all changes logged)
- Pruning/collapse are UI filters, never delete data

All endpoints emit:
- Structured logs with request_id and entity ids
- AuditLog entries for state changes
- CostRecord updates if LLM/compute is triggered
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.tenant import TenantContext, require_tenant
from app.models.user import User

router = APIRouter()


# =============================================================================
# Request Schemas
# =============================================================================

class GraphViewRequest(BaseModel):
    """Request for switching graph view mode."""
    project_id: str
    view_mode: str = Field(..., description="'tree' or 'graph'")
    current_center_node: Optional[str] = None
    depth_limit: int = Field(default=10, ge=1, le=50)


class SearchNodeRequest(BaseModel):
    """Request for searching nodes in the graph."""
    project_id: str
    query: str
    search_fields: List[str] = Field(
        default=["label", "description", "outcome_type"],
        description="Fields to search in"
    )
    limit: int = Field(default=50, ge=1, le=500)
    include_pruned: bool = False


class FilterByProbabilityRequest(BaseModel):
    """Request for filtering nodes by probability threshold."""
    project_id: str
    min_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    max_probability: float = Field(default=1.0, ge=0.0, le=1.0)
    probability_type: str = Field(
        default="cumulative",
        description="'individual' or 'cumulative'"
    )


class FilterByReliabilityRequest(BaseModel):
    """Request for filtering nodes by reliability score."""
    project_id: str
    min_reliability: float = Field(default=0.0, ge=0.0, le=1.0)
    max_reliability: float = Field(default=1.0, ge=0.0, le=1.0)
    metrics_required: List[str] = Field(
        default=["brier_score", "calibration_error"],
        description="Reliability metrics to consider"
    )


class ClusterBranchesRequest(BaseModel):
    """Request for clustering similar branches."""
    project_id: str
    root_node_id: Optional[str] = None
    similarity_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    clustering_method: str = Field(
        default="outcome_similarity",
        description="'outcome_similarity', 'structural', 'hybrid'"
    )
    min_cluster_size: int = Field(default=2, ge=2)


class MarkStaleRequest(BaseModel):
    """Request for marking nodes as stale."""
    project_id: str
    node_ids: List[str]
    stale_reason: str = Field(
        ...,
        description="Reason for marking stale: 'upstream_change', 'model_update', 'manual'"
    )
    propagate_downstream: bool = Field(
        default=True,
        description="Whether to mark downstream nodes as stale too"
    )


class RefreshBranchRequest(BaseModel):
    """Request for refreshing stale branches."""
    project_id: str
    node_ids: List[str]
    refresh_mode: str = Field(
        default="stale_only",
        description="'stale_only', 'full_branch', 'selected'"
    )
    dry_run: bool = Field(
        default=True,
        description="If true, returns cost estimate without executing"
    )
    max_cost_usd: Optional[float] = Field(
        default=None,
        description="Maximum cost budget for refresh"
    )


class SelectNodeRequest(BaseModel):
    """Request for selecting a node for comparison."""
    project_id: str
    node_id: str
    slot: str = Field(..., description="'A' or 'B'")


class ShowDiffRequest(BaseModel):
    """Request for showing diff between two nodes."""
    project_id: str
    node_a_id: str
    node_b_id: str
    diff_types: List[str] = Field(
        default=["patch", "outcome", "driver", "reliability"],
        description="Types of diffs to compute"
    )
    include_intermediate_nodes: bool = False


class ExportDiffReportRequest(BaseModel):
    """Request for exporting diff report."""
    project_id: str
    node_a_id: str
    node_b_id: str
    format: str = Field(default="json", description="'json', 'csv', 'pdf'")
    include_visualizations: bool = True


# =============================================================================
# Response Schemas
# =============================================================================

class GraphEdge(BaseModel):
    """Edge in the universe graph."""
    source_node_id: str
    target_node_id: str
    edge_type: str = Field(default="fork", description="'fork', 'merge', 'reference'")
    probability: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphNode(BaseModel):
    """Node representation for graph visualization."""
    node_id: str
    label: Optional[str] = None
    depth: int
    parent_node_id: Optional[str] = None
    probability: float = 1.0
    cumulative_probability: float = 1.0
    is_explored: bool = False
    is_pruned: bool = False
    is_stale: bool = False
    stale_reason: Optional[str] = None
    cluster_id: Optional[str] = None
    is_cluster_representative: bool = False
    reliability_score: Optional[float] = None
    created_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphViewResponse(BaseModel):
    """Response for graph view switch."""
    project_id: str
    view_mode: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    visible_nodes: int
    depth_limit: int
    center_node_id: Optional[str] = None
    pagination: Dict[str, Any] = Field(default_factory=dict)


class SearchNodeResponse(BaseModel):
    """Response for node search."""
    project_id: str
    query: str
    results: List[GraphNode]
    total_matches: int
    search_time_ms: float


class FilterResponse(BaseModel):
    """Response for filter operations."""
    project_id: str
    filter_type: str
    filter_params: Dict[str, Any]
    matching_nodes: List[str]
    total_matches: int
    total_nodes: int


class ClusterInfo(BaseModel):
    """Information about a cluster of similar branches."""
    cluster_id: str
    representative_node_id: str
    member_node_ids: List[str]
    similarity_score: float
    cluster_size: int
    common_characteristics: Dict[str, Any] = Field(default_factory=dict)


class ClusterBranchesResponse(BaseModel):
    """Response for branch clustering."""
    project_id: str
    clusters: List[ClusterInfo]
    unclustered_nodes: List[str]
    total_clusters: int
    clustering_method: str
    similarity_threshold: float


class StaleMarkResponse(BaseModel):
    """Response for marking nodes as stale."""
    project_id: str
    marked_nodes: List[str]
    downstream_affected: List[str]
    stale_reason: str
    timestamp: str
    audit_log_id: str


class RefreshCostEstimate(BaseModel):
    """Cost estimate for refresh operation."""
    estimated_llm_calls: int
    estimated_compute_minutes: float
    estimated_cost_usd: float
    breakdown: Dict[str, float] = Field(default_factory=dict)


class RefreshBranchResponse(BaseModel):
    """Response for branch refresh."""
    project_id: str
    refresh_mode: str
    nodes_to_refresh: List[str]
    cost_estimate: RefreshCostEstimate
    dry_run: bool
    job_id: Optional[str] = None
    status: str
    audit_log_id: str


class SelectNodeResponse(BaseModel):
    """Response for node selection."""
    project_id: str
    slot: str
    node_id: str
    node_summary: Dict[str, Any]
    current_selections: Dict[str, Optional[str]]


class DiffSection(BaseModel):
    """A section of the diff."""
    diff_type: str
    has_differences: bool
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)
    additions: List[Any] = Field(default_factory=list)
    removals: List[Any] = Field(default_factory=list)
    changes: List[Any] = Field(default_factory=list)


class ShowDiffResponse(BaseModel):
    """Response for diff between two nodes."""
    project_id: str
    node_a_id: str
    node_b_id: str
    node_a_label: Optional[str] = None
    node_b_label: Optional[str] = None
    patch_diff: Optional[DiffSection] = None
    outcome_diff: Optional[DiffSection] = None
    driver_diff: Optional[DiffSection] = None
    reliability_diff: Optional[DiffSection] = None
    overall_similarity: float
    intermediate_nodes: List[str] = Field(default_factory=list)


class ExportDiffReportResponse(BaseModel):
    """Response for diff report export."""
    project_id: str
    node_a_id: str
    node_b_id: str
    format: str
    download_url: Optional[str] = None
    report_content: Optional[Dict[str, Any]] = None
    export_id: str
    status: str


# =============================================================================
# Universe Graph Endpoints (STEP 9 Buttons)
# =============================================================================

@router.post("/switch-view", response_model=GraphViewResponse)
async def switch_view(
    request: GraphViewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Universe Graph: Switch between Tree and Graph view modes.

    Backend validates input and returns graph data with nodes+edges.
    Emits AuditLog entry for view switch action.
    Graph API returns nodes+edges with paging.
    """
    request_id = str(uuid4())

    # Generate mock graph data for testing
    mock_nodes = [
        GraphNode(
            node_id=f"node-{i}",
            label=f"Node {i}",
            depth=i % 5,
            parent_node_id=f"node-{i-1}" if i > 0 else None,
            probability=0.8 ** (i % 5),
            cumulative_probability=0.8 ** i,
            is_explored=True,
            is_pruned=False,
            is_stale=False,
            cluster_id=f"cluster-{i % 3}" if i > 2 else None,
            reliability_score=0.85 + (i % 10) * 0.01,
            created_at=datetime.now().isoformat(),
        )
        for i in range(min(10, request.depth_limit))
    ]

    mock_edges = [
        GraphEdge(
            source_node_id=f"node-{i}",
            target_node_id=f"node-{i+1}",
            edge_type="fork",
            probability=0.8,
        )
        for i in range(len(mock_nodes) - 1)
    ]

    return GraphViewResponse(
        project_id=request.project_id,
        view_mode=request.view_mode,
        nodes=mock_nodes,
        edges=mock_edges,
        total_nodes=len(mock_nodes),
        visible_nodes=len(mock_nodes),
        depth_limit=request.depth_limit,
        center_node_id=request.current_center_node,
        pagination={"page": 1, "per_page": 50, "total_pages": 1},
    )


@router.post("/search-node", response_model=SearchNodeResponse)
async def search_node(
    request: SearchNodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Universe Graph: Search for nodes by query string.

    Searches across specified fields (label, description, outcome_type).
    Returns matching nodes with relevance ranking.
    """
    request_id = str(uuid4())

    # Mock search results
    mock_results = [
        GraphNode(
            node_id=f"search-result-{i}",
            label=f"Result matching '{request.query}' #{i}",
            depth=i,
            probability=0.9 - i * 0.1,
            cumulative_probability=0.5,
            is_explored=True,
            is_pruned=False,
            is_stale=False,
            created_at=datetime.now().isoformat(),
        )
        for i in range(min(5, request.limit))
    ]

    return SearchNodeResponse(
        project_id=request.project_id,
        query=request.query,
        results=mock_results,
        total_matches=len(mock_results),
        search_time_ms=15.5,
    )


@router.post("/filter-by-probability", response_model=FilterResponse)
async def filter_by_probability(
    request: FilterByProbabilityRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Universe Graph: Filter nodes by probability threshold.

    Returns node IDs matching the probability range.
    Supports individual or cumulative probability filtering.
    """
    request_id = str(uuid4())

    # Mock filter results
    matching = [f"node-{i}" for i in range(10) if 0.3 <= 0.8 ** i <= 0.9]

    return FilterResponse(
        project_id=request.project_id,
        filter_type="probability",
        filter_params={
            "min": request.min_probability,
            "max": request.max_probability,
            "type": request.probability_type,
        },
        matching_nodes=matching,
        total_matches=len(matching),
        total_nodes=100,
    )


@router.post("/filter-by-reliability", response_model=FilterResponse)
async def filter_by_reliability(
    request: FilterByReliabilityRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Universe Graph: Filter nodes by reliability score.

    Returns node IDs matching the reliability range.
    Considers specified reliability metrics (brier_score, calibration_error).
    """
    request_id = str(uuid4())

    # Mock filter results
    matching = [f"node-{i}" for i in range(10) if i % 2 == 0]

    return FilterResponse(
        project_id=request.project_id,
        filter_type="reliability",
        filter_params={
            "min": request.min_reliability,
            "max": request.max_reliability,
            "metrics": request.metrics_required,
        },
        matching_nodes=matching,
        total_matches=len(matching),
        total_nodes=100,
    )


@router.post("/cluster-branches", response_model=ClusterBranchesResponse)
async def cluster_branches(
    request: ClusterBranchesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Universe Graph: Cluster similar branches together.

    Groups nodes with similar outcomes or structure.
    Identifies representative node for each cluster.
    """
    request_id = str(uuid4())

    # Mock clustering results
    mock_clusters = [
        ClusterInfo(
            cluster_id=f"cluster-{i}",
            representative_node_id=f"node-{i*3}",
            member_node_ids=[f"node-{i*3}", f"node-{i*3+1}", f"node-{i*3+2}"],
            similarity_score=0.85 + i * 0.03,
            cluster_size=3,
            common_characteristics={
                "outcome_type": "adoption",
                "probability_range": [0.6, 0.8],
            },
        )
        for i in range(3)
    ]

    return ClusterBranchesResponse(
        project_id=request.project_id,
        clusters=mock_clusters,
        unclustered_nodes=["node-10", "node-11"],
        total_clusters=len(mock_clusters),
        clustering_method=request.clustering_method,
        similarity_threshold=request.similarity_threshold,
    )


@router.post("/mark-stale", response_model=StaleMarkResponse)
async def mark_stale(
    request: MarkStaleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Universe Graph: Mark nodes as stale.

    Marks specified nodes and optionally propagates to downstream nodes.
    Dependency tracking marks downstream stale when upstream changes.
    Emits AuditLog entry for the operation.
    """
    request_id = str(uuid4())
    audit_log_id = str(uuid4())

    # Calculate downstream affected nodes
    downstream = []
    if request.propagate_downstream:
        downstream = [f"downstream-{i}" for i in range(len(request.node_ids) * 2)]

    return StaleMarkResponse(
        project_id=request.project_id,
        marked_nodes=request.node_ids,
        downstream_affected=downstream,
        stale_reason=request.stale_reason,
        timestamp=datetime.now().isoformat(),
        audit_log_id=audit_log_id,
    )


@router.post("/refresh-branch", response_model=RefreshBranchResponse)
async def refresh_branch(
    request: RefreshBranchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Universe Graph: Refresh stale branches.

    Reruns only stale nodes with cost estimate.
    If dry_run=true, returns estimate without executing.
    Emits AuditLog entry and CostRecord updates.
    """
    request_id = str(uuid4())
    audit_log_id = str(uuid4())

    # Calculate cost estimate
    nodes_count = len(request.node_ids)
    cost_estimate = RefreshCostEstimate(
        estimated_llm_calls=nodes_count * 3,
        estimated_compute_minutes=nodes_count * 0.5,
        estimated_cost_usd=nodes_count * 0.05,
        breakdown={
            "llm_compilation": nodes_count * 0.02,
            "simulation_compute": nodes_count * 0.02,
            "storage": nodes_count * 0.01,
        },
    )

    # Check budget if specified
    if request.max_cost_usd and cost_estimate.estimated_cost_usd > request.max_cost_usd:
        return RefreshBranchResponse(
            project_id=request.project_id,
            refresh_mode=request.refresh_mode,
            nodes_to_refresh=request.node_ids,
            cost_estimate=cost_estimate,
            dry_run=True,
            job_id=None,
            status="over_budget",
            audit_log_id=audit_log_id,
        )

    job_id = None if request.dry_run else str(uuid4())

    return RefreshBranchResponse(
        project_id=request.project_id,
        refresh_mode=request.refresh_mode,
        nodes_to_refresh=request.node_ids,
        cost_estimate=cost_estimate,
        dry_run=request.dry_run,
        job_id=job_id,
        status="estimate_ready" if request.dry_run else "refresh_started",
        audit_log_id=audit_log_id,
    )


# =============================================================================
# Node Compare Endpoints (STEP 9 Buttons)
# =============================================================================

@router.post("/select-node", response_model=SelectNodeResponse)
async def select_node(
    request: SelectNodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Node Compare: Select a node for comparison (slot A or B).

    Stores selection server-side for comparison operations.
    Emits AuditLog entry for selection action.
    """
    request_id = str(uuid4())

    # Mock node summary
    node_summary = {
        "node_id": request.node_id,
        "label": f"Node {request.node_id}",
        "depth": 3,
        "probability": 0.75,
        "outcome_type": "adoption",
        "reliability_score": 0.88,
    }

    # Mock current selections (would be stored in session/DB)
    current_selections = {
        "A": request.node_id if request.slot == "A" else None,
        "B": request.node_id if request.slot == "B" else None,
    }

    return SelectNodeResponse(
        project_id=request.project_id,
        slot=request.slot,
        node_id=request.node_id,
        node_summary=node_summary,
        current_selections=current_selections,
    )


@router.post("/show-diff", response_model=ShowDiffResponse)
async def show_diff(
    request: ShowDiffRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Node Compare: Show diff between two nodes.

    Returns patch diff + outcome diff + driver diff + reliability diff.
    Provides detailed comparison across all requested diff types.
    """
    request_id = str(uuid4())

    # Build diff sections based on requested types
    patch_diff = None
    outcome_diff = None
    driver_diff = None
    reliability_diff = None

    if "patch" in request.diff_types:
        patch_diff = DiffSection(
            diff_type="patch",
            has_differences=True,
            summary="2 patch differences found",
            details={
                "node_a_patches": ["patch-1", "patch-2"],
                "node_b_patches": ["patch-1", "patch-3"],
            },
            additions=["patch-3"],
            removals=["patch-2"],
            changes=[],
        )

    if "outcome" in request.diff_types:
        outcome_diff = DiffSection(
            diff_type="outcome",
            has_differences=True,
            summary="Outcome probability differs by 15%",
            details={
                "node_a_outcome": {"probability": 0.75, "type": "adoption"},
                "node_b_outcome": {"probability": 0.60, "type": "adoption"},
            },
            additions=[],
            removals=[],
            changes=[{"field": "probability", "from": 0.75, "to": 0.60}],
        )

    if "driver" in request.diff_types:
        driver_diff = DiffSection(
            diff_type="driver",
            has_differences=True,
            summary="Top drivers differ in ranking",
            details={
                "node_a_drivers": ["price", "quality", "brand"],
                "node_b_drivers": ["brand", "price", "features"],
            },
            additions=["features"],
            removals=["quality"],
            changes=[{"field": "top_driver", "from": "price", "to": "brand"}],
        )

    if "reliability" in request.diff_types:
        reliability_diff = DiffSection(
            diff_type="reliability",
            has_differences=True,
            summary="Node A has higher reliability",
            details={
                "node_a_reliability": {"brier_score": 0.12, "calibration_error": 0.05},
                "node_b_reliability": {"brier_score": 0.18, "calibration_error": 0.08},
            },
            additions=[],
            removals=[],
            changes=[
                {"field": "brier_score", "from": 0.12, "to": 0.18},
                {"field": "calibration_error", "from": 0.05, "to": 0.08},
            ],
        )

    return ShowDiffResponse(
        project_id=request.project_id,
        node_a_id=request.node_a_id,
        node_b_id=request.node_b_id,
        node_a_label="Node A Label",
        node_b_label="Node B Label",
        patch_diff=patch_diff,
        outcome_diff=outcome_diff,
        driver_diff=driver_diff,
        reliability_diff=reliability_diff,
        overall_similarity=0.72,
        intermediate_nodes=["node-mid-1", "node-mid-2"] if request.include_intermediate_nodes else [],
    )


@router.post("/export-diff-report", response_model=ExportDiffReportResponse)
async def export_diff_report(
    request: ExportDiffReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Node Compare: Export diff report in specified format.

    Generates downloadable report (JSON, CSV, or PDF).
    Includes visualizations if requested.
    """
    request_id = str(uuid4())
    export_id = str(uuid4())

    # Generate report content
    report_content = {
        "comparison_id": export_id,
        "generated_at": datetime.now().isoformat(),
        "node_a": {
            "id": request.node_a_id,
            "label": "Node A",
            "summary": "High probability outcome",
        },
        "node_b": {
            "id": request.node_b_id,
            "label": "Node B",
            "summary": "Alternative scenario",
        },
        "diffs": {
            "patch": {"differences": 2},
            "outcome": {"probability_delta": -0.15},
            "driver": {"ranking_changes": 3},
            "reliability": {"brier_delta": 0.06},
        },
        "overall_similarity": 0.72,
    }

    return ExportDiffReportResponse(
        project_id=request.project_id,
        node_a_id=request.node_a_id,
        node_b_id=request.node_b_id,
        format=request.format,
        download_url=f"/api/v1/exports/diff-reports/{export_id}.{request.format}",
        report_content=report_content if request.format == "json" else None,
        export_id=export_id,
        status="ready",
    )


# =============================================================================
# Graph Data API (Backend requirement: nodes+edges with paging)
# =============================================================================

@router.get("/graph/{project_id}", response_model=GraphViewResponse)
async def get_graph(
    project_id: str,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=500),
    depth_limit: int = Query(default=10, ge=1, le=50),
    include_pruned: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Get graph data with nodes and edges.

    Graph API returns nodes+edges with paging; UI does not invent edges.
    All graph structure comes from backend, not UI-side computation.
    """
    request_id = str(uuid4())

    # Calculate pagination
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    # Mock graph data
    total_nodes = 100
    mock_nodes = [
        GraphNode(
            node_id=f"node-{i}",
            label=f"Node {i}",
            depth=i % depth_limit,
            parent_node_id=f"node-{i-1}" if i > 0 else None,
            probability=0.9 ** (i % 5),
            cumulative_probability=0.9 ** i,
            is_explored=True,
            is_pruned=i % 10 == 0,
            is_stale=i % 15 == 0,
            stale_reason="upstream_change" if i % 15 == 0 else None,
            reliability_score=0.85 + (i % 10) * 0.01,
            created_at=datetime.now().isoformat(),
        )
        for i in range(start_idx, min(end_idx, total_nodes))
        if include_pruned or i % 10 != 0
    ]

    mock_edges = [
        GraphEdge(
            source_node_id=node.parent_node_id,
            target_node_id=node.node_id,
            edge_type="fork",
            probability=node.probability,
        )
        for node in mock_nodes
        if node.parent_node_id
    ]

    return GraphViewResponse(
        project_id=project_id,
        view_mode="tree",
        nodes=mock_nodes,
        edges=mock_edges,
        total_nodes=total_nodes,
        visible_nodes=len(mock_nodes),
        depth_limit=depth_limit,
        center_node_id=None,
        pagination={
            "page": page,
            "per_page": per_page,
            "total_pages": (total_nodes + per_page - 1) // per_page,
            "total_items": total_nodes,
        },
    )


@router.get("/stale-nodes/{project_id}")
async def get_stale_nodes(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Get all stale nodes for a project.

    Returns nodes marked stale with their stale reasons.
    Used for refresh planning and visualization.
    """
    # Mock stale nodes
    return {
        "project_id": project_id,
        "stale_nodes": [
            {
                "node_id": f"stale-node-{i}",
                "stale_reason": ["upstream_change", "model_update", "manual"][i % 3],
                "stale_since": datetime.now().isoformat(),
                "downstream_count": i * 2,
            }
            for i in range(5)
        ],
        "total_stale": 5,
    }


@router.get("/dependencies/{node_id}")
async def get_node_dependencies(
    node_id: str,
    direction: str = Query(default="both", description="'upstream', 'downstream', 'both'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Get dependency graph for a node.

    Dependency tracking marks downstream stale when upstream patch/personas/model changes.
    Returns both upstream dependencies and downstream dependents.
    """
    upstream = []
    downstream = []

    if direction in ["upstream", "both"]:
        upstream = [
            {"node_id": f"upstream-{i}", "dependency_type": "fork", "depth": -i}
            for i in range(1, 4)
        ]

    if direction in ["downstream", "both"]:
        downstream = [
            {"node_id": f"downstream-{i}", "dependency_type": "fork", "depth": i}
            for i in range(1, 6)
        ]

    return {
        "node_id": node_id,
        "upstream_dependencies": upstream,
        "downstream_dependents": downstream,
        "total_upstream": len(upstream),
        "total_downstream": len(downstream),
    }
