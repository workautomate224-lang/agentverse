"""
Target Mode API Endpoints
Single-target, many possible futures.
Reference: project.md §11 Phase 5, Interaction_design.md §5.13

Provides endpoints for:
- Creating target personas
- Running path planner
- Expanding path clusters
- Branching paths to Universe Map nodes

Key constraints:
- C1: Fork-not-mutate (branching creates new nodes)
- C5: LLMs compile personas, not tick-by-tick simulation
"""

from datetime import datetime
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
from app.schemas.target_mode import (
    TargetPersona,
    TargetPersonaCreate,
    UtilityFunction,
    ActionDefinition,
    Constraint,
    PlanResult,
    PlanStatus,
    PathCluster,
    TargetPlanRequest,
    ExpandClusterRequest,
    BranchToNodeRequest,
    TargetPlanListItem,
)


# ============================================================================
# Request/Response Schemas
# ============================================================================

class TargetPersonaResponse(BaseModel):
    """Response for target persona operations."""
    target_id: str
    persona_id: Optional[str]
    name: str
    description: Optional[str]
    domain: Optional[str]
    planning_horizon: int
    discount_factor: float
    exploration_rate: float
    utility_dimensions: List[str]
    action_count: int
    constraint_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PlanResultResponse(BaseModel):
    """Response for planning operations."""
    plan_id: str
    target_id: str
    project_id: str
    status: str
    error_message: Optional[str]
    total_paths_generated: int
    total_paths_valid: int
    total_paths_pruned: int
    cluster_count: int
    top_path_utility: Optional[float]
    planning_summary: Optional[str]
    planning_time_ms: int
    created_at: str
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class ClusterResponse(BaseModel):
    """Response for cluster expansion."""
    cluster_id: str
    label: str
    description: Optional[str]
    aggregated_probability: float
    avg_utility: float
    utility_min: float
    utility_max: float
    is_expanded: bool
    expansion_depth: int
    path_count: int
    common_actions: Optional[List[str]]

    class Config:
        from_attributes = True


class BranchResponse(BaseModel):
    """Response for branching path to node."""
    node_id: str
    path_id: str
    parent_node_id: str
    label: str
    probability: float
    utility: float
    action_sequence: List[dict]
    variable_deltas: dict

    class Config:
        from_attributes = True


# ============================================================================
# API Router
# ============================================================================

router = APIRouter()


@router.post(
    "/personas",
    response_model=TargetPersonaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a target persona",
)
async def create_target_persona(
    request: TargetPersonaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> TargetPersonaResponse:
    """
    Create a new target persona for Target Mode simulation.

    Target personas include:
    - Utility function (what the target optimizes for)
    - Action priors (behavioral tendencies)
    - Initial state vector
    - Personal constraints

    Reference: project.md §11 Phase 5
    """
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()

    try:
        target = service.create_target(request)

        return TargetPersonaResponse(
            target_id=target.target_id,
            persona_id=target.persona_id,
            name=target.name,
            description=target.description,
            domain=target.domain,
            planning_horizon=target.planning_horizon,
            discount_factor=target.discount_factor,
            exploration_rate=target.exploration_rate,
            utility_dimensions=[w.dimension.value for w in target.utility_function.weights],
            action_count=len(target.custom_actions) if target.custom_actions else 0,
            constraint_count=len(target.personal_constraints) if target.personal_constraints else 0,
            created_at=target.created_at.isoformat(),
            updated_at=target.updated_at.isoformat(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create target persona: {str(e)}",
        )


@router.get(
    "/personas/{target_id}",
    response_model=TargetPersonaResponse,
    summary="Get a target persona",
)
async def get_target_persona(
    target_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> TargetPersonaResponse:
    """Get details of a specific target persona."""
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()
    target = service.get_target(target_id)

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target persona {target_id} not found",
        )

    return TargetPersonaResponse(
        target_id=target.target_id,
        persona_id=target.persona_id,
        name=target.name,
        description=target.description,
        domain=target.domain,
        planning_horizon=target.planning_horizon,
        discount_factor=target.discount_factor,
        exploration_rate=target.exploration_rate,
        utility_dimensions=[w.dimension.value for w in target.utility_function.weights],
        action_count=len(target.custom_actions) if target.custom_actions else 0,
        constraint_count=len(target.personal_constraints) if target.personal_constraints else 0,
        created_at=target.created_at.isoformat(),
        updated_at=target.updated_at.isoformat(),
    )


@router.post(
    "/plans",
    response_model=PlanResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run the path planner",
)
async def run_planner(
    request: TargetPlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> PlanResultResponse:
    """
    Run the Target Mode path planner.

    Generates possible action sequences (paths) for the target,
    pruning by constraints and clustering by outcome similarity.

    Reference: project.md §11 Phase 5
    """
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()

    try:
        result = service.run_planner(request)

        top_utility = None
        if result.top_paths:
            top_utility = result.top_paths[0].total_utility

        return PlanResultResponse(
            plan_id=result.plan_id,
            target_id=result.target_id,
            project_id=result.project_id,
            status=result.status.value,
            error_message=result.error_message,
            total_paths_generated=result.total_paths_generated,
            total_paths_valid=result.total_paths_valid,
            total_paths_pruned=result.total_paths_pruned,
            cluster_count=len(result.clusters),
            top_path_utility=top_utility,
            planning_summary=result.planning_summary,
            planning_time_ms=result.planning_time_ms,
            created_at=result.created_at.isoformat(),
            completed_at=result.completed_at.isoformat() if result.completed_at else None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Planning failed: {str(e)}",
        )


@router.get(
    "/plans/{plan_id}",
    response_model=PlanResultResponse,
    summary="Get plan result",
)
async def get_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> PlanResultResponse:
    """Get details of a completed planning run."""
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()
    result = service.get_plan(plan_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    top_utility = None
    if result.top_paths:
        top_utility = result.top_paths[0].total_utility

    return PlanResultResponse(
        plan_id=result.plan_id,
        target_id=result.target_id,
        project_id=result.project_id,
        status=result.status.value,
        error_message=result.error_message,
        total_paths_generated=result.total_paths_generated,
        total_paths_valid=result.total_paths_valid,
        total_paths_pruned=result.total_paths_pruned,
        cluster_count=len(result.clusters),
        top_path_utility=top_utility,
        planning_summary=result.planning_summary,
        planning_time_ms=result.planning_time_ms,
        created_at=result.created_at.isoformat(),
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
    )


@router.get(
    "/plans/{plan_id}/clusters",
    response_model=List[ClusterResponse],
    summary="Get plan clusters",
)
async def get_plan_clusters(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> List[ClusterResponse]:
    """Get all clusters for a plan."""
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()
    result = service.get_plan(plan_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    return [
        ClusterResponse(
            cluster_id=cluster.cluster_id,
            label=cluster.label,
            description=cluster.description,
            aggregated_probability=cluster.aggregated_probability,
            avg_utility=cluster.avg_utility,
            utility_min=cluster.utility_range[0],
            utility_max=cluster.utility_range[1],
            is_expanded=cluster.is_expanded,
            expansion_depth=cluster.expansion_depth,
            path_count=1 + len(cluster.child_paths),
            common_actions=cluster.common_actions,
        )
        for cluster in result.clusters
    ]


@router.post(
    "/plans/{plan_id}/expand-cluster",
    response_model=ClusterResponse,
    summary="Expand a path cluster",
)
async def expand_cluster(
    plan_id: str,
    request: ExpandClusterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ClusterResponse:
    """
    Expand a path cluster to reveal child paths.

    Supports progressive disclosure - clusters can be expanded
    multiple times to reveal deeper variations.

    Reference: Interaction_design.md G5 (no hard caps on futures)
    """
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()

    # Ensure plan_id matches
    request.plan_id = plan_id

    cluster = service.expand_cluster(request)

    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster {request.cluster_id} not found in plan {plan_id}",
        )

    return ClusterResponse(
        cluster_id=cluster.cluster_id,
        label=cluster.label,
        description=cluster.description,
        aggregated_probability=cluster.aggregated_probability,
        avg_utility=cluster.avg_utility,
        utility_min=cluster.utility_range[0],
        utility_max=cluster.utility_range[1],
        is_expanded=cluster.is_expanded,
        expansion_depth=cluster.expansion_depth,
        path_count=1 + len(cluster.child_paths),
        common_actions=cluster.common_actions,
    )


@router.get(
    "/plans/{plan_id}/paths",
    summary="Get paths from a plan",
)
async def get_plan_paths(
    plan_id: str,
    cluster_id: Optional[str] = Query(None, description="Filter by cluster"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """Get paths from a plan, optionally filtered by cluster."""
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()
    result = service.get_plan(plan_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    paths = []

    if cluster_id:
        # Get paths from specific cluster
        for cluster in result.clusters:
            if cluster.cluster_id == cluster_id:
                paths.append(cluster.representative_path)
                paths.extend(cluster.child_paths[:limit - 1])
                break
    else:
        # Get top paths
        paths = result.top_paths[:limit]

    return {
        "plan_id": plan_id,
        "paths": [
            {
                "path_id": p.path_id,
                "probability": p.path_probability,
                "utility": p.total_utility,
                "steps": len(p.steps),
                "status": p.status.value,
                "cluster_id": p.cluster_id,
                "is_representative": p.is_representative,
                "action_sequence": [
                    {
                        "step": s.step_index,
                        "action_id": s.action.action_id,
                        "action_name": s.action.name,
                        "probability": s.probability,
                    }
                    for s in p.steps
                ],
            }
            for p in paths
        ],
        "total": len(paths),
    }


@router.post(
    "/plans/{plan_id}/branch",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Branch path to Universe Map node",
)
async def branch_to_node(
    plan_id: str,
    request: BranchToNodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> BranchResponse:
    """
    Create a Universe Map node from a selected path.

    This bridges Target Mode to the Universe Map, allowing
    selected futures to become simulation starting points.

    Reference: project.md C1 (fork-not-mutate)
    """
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()

    # Ensure plan_id matches
    request.plan_id = plan_id

    node_data = service.branch_to_node(request)

    if not node_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path {request.path_id} not found in plan {plan_id}",
        )

    target_data = node_data.get("target_mode_data", {})

    return BranchResponse(
        node_id=node_data["node_id"],
        path_id=request.path_id,
        parent_node_id=request.parent_node_id,
        label=node_data["label"],
        probability=node_data["probability"],
        utility=node_data["predicted_outcome"]["utility"],
        action_sequence=target_data.get("action_sequence", []),
        variable_deltas=target_data.get("variable_deltas", {}),
    )


@router.get(
    "/plans/{plan_id}/telemetry",
    summary="Get plan telemetry logs",
)
async def get_plan_telemetry(
    plan_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """Get telemetry logs for a planning run."""
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()
    logs = service.get_telemetry(plan_id)

    if event_type:
        logs = [log for log in logs if log.get("event_type") == event_type]

    return {
        "plan_id": plan_id,
        "logs": logs,
        "total": len(logs),
    }


@router.get(
    "/action-catalogs",
    summary="List available action catalogs",
)
async def list_action_catalogs(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """List available action catalogs for Target Mode."""
    from app.services.target_mode import ActionSpace

    catalogs = []
    for domain_name, actions in ActionSpace.DEFAULT_CATALOGS.items():
        if domain and domain != domain_name:
            continue

        catalogs.append({
            "domain": domain_name,
            "action_count": len(actions),
            "actions": [
                {
                    "action_id": a.action_id,
                    "name": a.name,
                    "category": a.category.value,
                    "risk_level": a.risk_level,
                }
                for a in actions
            ],
        })

    return {
        "catalogs": catalogs,
        "total": len(catalogs),
    }
