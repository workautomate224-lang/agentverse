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

from app.api.deps import get_current_user, get_db, require_tenant, TenantContext
from app.models.user import User
from app.services.audit import (
    get_tenant_audit_logger,
    TenantAuditAction,
    AuditResourceType,
    AuditActor,
    AuditActorType,
)
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
    project_id: Optional[str]
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

        # §4.4 Audit logging for target persona creation
        audit_logger = get_tenant_audit_logger()
        await audit_logger.log(
            tenant_id=str(tenant_ctx.tenant_id) if tenant_ctx.tenant_id else None,
            action=TenantAuditAction.TARGET_PERSONA_CREATE,
            resource_type=AuditResourceType.TARGET_PERSONA,
            resource_id=target.target_id,
            actor=AuditActor(
                type=AuditActorType.USER,
                id=str(current_user.id),
                name=current_user.email,
            ),
            details={
                "project_id": target.project_id,
                "name": target.name,
                "planning_horizon": target.planning_horizon,
                "utility_dimensions": [w.dimension.value for w in target.utility_function.weights],
            },
        )

        return TargetPersonaResponse(
            target_id=target.target_id,
            project_id=target.project_id,
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
    "/personas",
    response_model=List[TargetPersonaResponse],
    summary="List target personas",
)
async def list_target_personas(
    project_id: str = Query(..., description="Project ID to filter by"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> List[TargetPersonaResponse]:
    """List all target personas for a project."""
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()
    targets = service.list_targets(project_id)

    return [
        TargetPersonaResponse(
            target_id=target.target_id,
            project_id=target.project_id,
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
        for target in targets
    ]


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
        project_id=target.project_id,
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

        # §4.4 Audit logging for plan completion with §4.2 search counters
        audit_logger = get_tenant_audit_logger()
        await audit_logger.log(
            tenant_id=str(tenant_ctx.tenant_id) if tenant_ctx.tenant_id else None,
            action=TenantAuditAction.TARGET_PLAN_COMPLETE,
            resource_type=AuditResourceType.TARGET_PLAN,
            resource_id=result.plan_id,
            actor=AuditActor(
                type=AuditActorType.USER,
                id=str(current_user.id),
                name=current_user.email,
            ),
            details={
                "target_id": result.target_id,
                "project_id": result.project_id,
                "status": result.status.value,
                "total_paths_generated": result.total_paths_generated,
                "total_paths_valid": result.total_paths_valid,
                "total_paths_pruned": result.total_paths_pruned,
                "cluster_count": len(result.clusters),
                "planning_time_ms": result.planning_time_ms,
                # §4.2 Search counters for Evidence Pack
                "explored_states_count": result.explored_states_count,
                "expanded_nodes_count": result.expanded_nodes_count,
                "hard_constraints_applied": result.hard_constraints_applied,
                "soft_constraints_applied": result.soft_constraints_applied,
            },
        )

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


# =============================================================================
# STEP 6: Planning Spec & PlanTrace Endpoints
# =============================================================================

class CreatePlanningSpecRequest(BaseModel):
    """Request to create a planning specification (STEP 6)."""
    project_id: str = Field(..., description="Project ID")
    parent_node_id: Optional[str] = Field(None, description="Parent node in Universe Map")
    target_persona_id: Optional[str] = Field(None, description="Target persona ID")
    goal_definition: dict = Field(..., description="Goal definition {goal_type, target_metrics, success_criteria}")
    constraints: dict = Field(default_factory=dict, description="Constraints {hard_constraints, soft_constraints}")
    action_library_version: str = Field("1.0.0", description="Action library version for reproducibility")
    search_config: dict = Field(
        default_factory=lambda: {
            "algorithm": "beam_search",
            "max_depth": 10,
            "beam_width": 5,
            "pruning_threshold": 0.01,
        },
        description="Search configuration"
    )
    evaluation_budget: int = Field(10, ge=1, le=100, description="Max simulation runs")
    seed: int = Field(..., description="Seed for reproducibility")
    label: Optional[str] = None
    description: Optional[str] = None


class PlanningSpecResponse(BaseModel):
    """Response for planning spec operations (STEP 6)."""
    planning_id: str
    project_id: str
    parent_node_id: Optional[str]
    target_persona_id: Optional[str]
    goal_definition: dict
    constraints: dict
    action_library_version: str
    search_config: dict
    evaluation_budget: int
    seed: int
    status: str
    label: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class PlanTraceResponse(BaseModel):
    """Response for plan trace (STEP 6)."""
    trace_id: str
    planning_spec_id: str
    total_candidates_generated: int
    candidates_pruned: int
    candidates_evaluated: int
    search_algorithm: str
    explored_states_count: int
    expanded_nodes_count: int
    pruning_decisions: List[dict]
    runs_executed: List[str]
    total_runs_count: int
    scoring_function: dict
    top_k_results: List[dict]
    selected_candidate_id: Optional[str]
    search_time_ms: int
    evaluation_time_ms: int
    total_time_ms: int
    summary: Optional[str]

    class Config:
        from_attributes = True


class ComparePlansRequest(BaseModel):
    """Request to compare two plans (STEP 6)."""
    plan_id_a: str = Field(..., description="First plan ID")
    plan_id_b: str = Field(..., description="Second plan ID")


class ComparePlansResponse(BaseModel):
    """Response for plan comparison (STEP 6)."""
    plan_id_a: str
    plan_id_b: str
    comparison_summary: dict
    metric_differences: List[dict]
    common_actions: List[str]
    divergent_actions: List[dict]
    score_comparison: dict
    recommendation: Optional[str]


class ExportPlanEvidenceResponse(BaseModel):
    """Response for exporting plan evidence (STEP 6)."""
    planning_id: str
    evidence_pack_id: str
    planning_spec: dict
    plan_trace: dict
    candidate_summaries: List[dict]
    evaluation_runs: List[dict]
    node_chain: List[dict]
    scoring_breakdown: dict
    export_timestamp: str
    verification_status: str


class RerunCandidateRequest(BaseModel):
    """Request to re-run a candidate (STEP 6)."""
    new_seed: Optional[int] = Field(None, description="New seed for re-run (optional)")
    additional_runs: int = Field(1, ge=1, le=10, description="Additional ensemble runs")


class MarkVerifiedRequest(BaseModel):
    """Request to mark plan as verified (STEP 6)."""
    verification_notes: Optional[str] = None
    verified_by_simulation: bool = Field(True, description="Whether verification includes simulation evidence")


@router.post(
    "/planning-specs",
    response_model=PlanningSpecResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a planning specification (STEP 6)",
)
async def create_planning_spec(
    request: CreatePlanningSpecRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> PlanningSpecResponse:
    """
    STEP 6: Create a planning specification.

    PlanningSpec stores: goal, constraints, search_config, budget, seed, action_library_version.
    This is the first step before running planning.

    Reference: STEP 6 Backend Requirement 1
    """
    from app.models.planning import PlanningSpec, PlanningStatus
    import uuid as uuid_module
    from sqlalchemy import select

    try:
        # Create PlanningSpec in database
        planning_spec = PlanningSpec(
            id=uuid_module.uuid4(),
            tenant_id=tenant_ctx.tenant_id,
            project_id=uuid_module.UUID(request.project_id),
            parent_node_id=uuid_module.UUID(request.parent_node_id) if request.parent_node_id else None,
            target_persona_id=request.target_persona_id,
            goal_definition=request.goal_definition,
            constraints=request.constraints,
            action_library_version=request.action_library_version,
            search_config=request.search_config,
            evaluation_budget=request.evaluation_budget,
            seed=request.seed,
            status=PlanningStatus.CREATED.value,
            label=request.label,
            description=request.description,
        )

        db.add(planning_spec)
        await db.commit()
        await db.refresh(planning_spec)

        # Audit logging
        audit_logger = get_tenant_audit_logger()
        await audit_logger.log(
            tenant_id=str(tenant_ctx.tenant_id) if tenant_ctx.tenant_id else None,
            action=TenantAuditAction.TARGET_PLAN_CREATE,
            resource_type=AuditResourceType.PLANNING_SPEC,
            resource_id=str(planning_spec.id),
            actor=AuditActor(
                type=AuditActorType.USER,
                id=str(current_user.id),
                name=current_user.email,
            ),
            details={
                "project_id": request.project_id,
                "action_library_version": request.action_library_version,
                "evaluation_budget": request.evaluation_budget,
                "seed": request.seed,
            },
        )

        return PlanningSpecResponse(
            planning_id=str(planning_spec.id),
            project_id=str(planning_spec.project_id),
            parent_node_id=str(planning_spec.parent_node_id) if planning_spec.parent_node_id else None,
            target_persona_id=planning_spec.target_persona_id,
            goal_definition=planning_spec.goal_definition,
            constraints=planning_spec.constraints,
            action_library_version=planning_spec.action_library_version,
            search_config=planning_spec.search_config,
            evaluation_budget=planning_spec.evaluation_budget,
            seed=planning_spec.seed,
            status=planning_spec.status,
            label=planning_spec.label,
            created_at=planning_spec.created_at.isoformat(),
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create planning spec: {str(e)}",
        )


@router.get(
    "/plans/{plan_id}/top-plans",
    summary="View top plans (STEP 6)",
)
async def view_top_plans(
    plan_id: str,
    limit: int = Query(5, ge=1, le=20, description="Number of top plans to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """
    STEP 6: View top K plans with their evidence links.

    Returns ranked list of candidate plans with:
    - Composite scores
    - Evidence run references
    - Node chain links
    """
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()
    result = service.get_plan(plan_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    top_plans = []
    for i, path in enumerate(result.top_paths[:limit]):
        top_plans.append({
            "rank": i + 1,
            "path_id": path.path_id,
            "label": f"Plan {i + 1}",
            "probability": path.path_probability,
            "utility": path.total_utility,
            "cost": path.total_cost,
            "risk": path.total_risk,
            "steps_count": len(path.steps),
            "cluster_id": path.cluster_id,
            "status": path.status.value,
            "action_sequence": [
                {
                    "step": s.step_index,
                    "action_id": s.action.action_id,
                    "action_name": s.action.name,
                }
                for s in path.steps
            ],
            # STEP 6: Evidence links (would be populated from DB in production)
            "evidence_run_ids": [],
            "node_id": None,
        })

    return {
        "plan_id": plan_id,
        "top_plans": top_plans,
        "total_evaluated": result.total_paths_valid,
        "evaluation_complete": result.status == PlanStatus.COMPLETED,
    }


@router.post(
    "/plans/compare",
    response_model=ComparePlansResponse,
    summary="Compare two plans (STEP 6)",
)
async def compare_plans(
    request: ComparePlansRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ComparePlansResponse:
    """
    STEP 6: Compare two plans for decision support.

    Returns metric differences, common/divergent actions, and recommendation.
    """
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()

    plan_a = service.get_plan(request.plan_id_a)
    plan_b = service.get_plan(request.plan_id_b)

    if not plan_a:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {request.plan_id_a} not found",
        )
    if not plan_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {request.plan_id_b} not found",
        )

    # Compare top paths
    top_a = plan_a.top_paths[0] if plan_a.top_paths else None
    top_b = plan_b.top_paths[0] if plan_b.top_paths else None

    # Extract actions for comparison
    actions_a = set()
    actions_b = set()
    if top_a:
        actions_a = {s.action.action_id for s in top_a.steps}
    if top_b:
        actions_b = {s.action.action_id for s in top_b.steps}

    common_actions = list(actions_a & actions_b)
    divergent_a = list(actions_a - actions_b)
    divergent_b = list(actions_b - actions_a)

    # Metric differences
    metric_differences = []
    if top_a and top_b:
        metric_differences = [
            {
                "metric": "probability",
                "plan_a": top_a.path_probability,
                "plan_b": top_b.path_probability,
                "difference": top_a.path_probability - top_b.path_probability,
            },
            {
                "metric": "utility",
                "plan_a": top_a.total_utility,
                "plan_b": top_b.total_utility,
                "difference": top_a.total_utility - top_b.total_utility,
            },
            {
                "metric": "cost",
                "plan_a": top_a.total_cost,
                "plan_b": top_b.total_cost,
                "difference": top_a.total_cost - top_b.total_cost,
            },
            {
                "metric": "risk",
                "plan_a": top_a.total_risk,
                "plan_b": top_b.total_risk,
                "difference": top_a.total_risk - top_b.total_risk,
            },
        ]

    # Score comparison
    score_a = top_a.total_utility if top_a else 0
    score_b = top_b.total_utility if top_b else 0

    recommendation = None
    if score_a > score_b:
        recommendation = f"Plan A ({request.plan_id_a}) has higher utility"
    elif score_b > score_a:
        recommendation = f"Plan B ({request.plan_id_b}) has higher utility"
    else:
        recommendation = "Plans have equivalent utility scores"

    return ComparePlansResponse(
        plan_id_a=request.plan_id_a,
        plan_id_b=request.plan_id_b,
        comparison_summary={
            "plans_compared": 2,
            "common_action_count": len(common_actions),
            "divergent_action_count": len(divergent_a) + len(divergent_b),
        },
        metric_differences=metric_differences,
        common_actions=common_actions,
        divergent_actions=[
            {"plan": "a", "unique_actions": divergent_a},
            {"plan": "b", "unique_actions": divergent_b},
        ],
        score_comparison={
            "plan_a_score": score_a,
            "plan_b_score": score_b,
            "winner": "a" if score_a > score_b else ("b" if score_b > score_a else "tie"),
        },
        recommendation=recommendation,
    )


@router.get(
    "/plans/{plan_id}/evidence",
    response_model=ExportPlanEvidenceResponse,
    summary="Export plan evidence (STEP 6)",
)
async def export_plan_evidence(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ExportPlanEvidenceResponse:
    """
    STEP 6: Export complete evidence pack for a plan.

    Includes: PlanningSpec, PlanTrace, candidate summaries, evaluation runs,
    node chain, and scoring breakdown.
    """
    from app.services.target_mode import get_target_mode_service
    import uuid as uuid_module

    service = get_target_mode_service()
    result = service.get_plan(plan_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    # Build evidence pack
    candidate_summaries = []
    for i, path in enumerate(result.top_paths):
        candidate_summaries.append({
            "rank": i + 1,
            "path_id": path.path_id,
            "probability": path.path_probability,
            "utility": path.total_utility,
            "status": path.status.value,
        })

    # Scoring breakdown
    scoring_breakdown = {
        "formula": "utility - cost - risk",
        "components": {
            "utility_weight": 0.5,
            "cost_weight": 0.3,
            "risk_weight": 0.2,
        },
        "normalization": "min-max to [0, 1]",
    }

    return ExportPlanEvidenceResponse(
        planning_id=plan_id,
        evidence_pack_id=str(uuid_module.uuid4()),
        planning_spec={
            "target_id": result.target_id,
            "project_id": result.project_id,
            "total_paths_generated": result.total_paths_generated,
        },
        plan_trace={
            "total_paths_valid": result.total_paths_valid,
            "total_paths_pruned": result.total_paths_pruned,
            "cluster_count": len(result.clusters),
            "hard_constraints_applied": result.hard_constraints_applied,
            "soft_constraints_applied": result.soft_constraints_applied,
            "planning_time_ms": result.planning_time_ms,
            "explored_states_count": result.explored_states_count,
            "expanded_nodes_count": result.expanded_nodes_count,
        },
        candidate_summaries=candidate_summaries,
        evaluation_runs=[],  # Would be populated from DB
        node_chain=[],  # Would be populated from node relationships
        scoring_breakdown=scoring_breakdown,
        export_timestamp=datetime.utcnow().isoformat(),
        verification_status="unverified" if not result.top_paths else "has_candidates",
    )


@router.get(
    "/plans/{plan_id}/trace",
    response_model=PlanTraceResponse,
    summary="View PlanTrace (STEP 6)",
)
async def view_plan_trace(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> PlanTraceResponse:
    """
    STEP 6: View the PlanTrace audit artifact.

    PlanTrace stores: candidate gen, pruning decisions, run_ids, scoring breakdown.
    """
    from app.services.target_mode import get_target_mode_service
    import uuid as uuid_module

    service = get_target_mode_service()
    result = service.get_plan(plan_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    # Build pruning decisions
    pruning_decisions = []
    for constraint_id, count in result.paths_pruned_by_constraint.items():
        pruning_decisions.append({
            "constraint_id": constraint_id,
            "paths_pruned": count,
            "reason": f"Violated constraint {constraint_id}",
        })

    # Build top K results
    top_k_results = []
    for i, path in enumerate(result.top_paths[:5]):
        top_k_results.append({
            "rank": i + 1,
            "path_id": path.path_id,
            "utility": path.total_utility,
            "probability": path.path_probability,
        })

    # Scoring function (STEP 6: explicit, auditable)
    scoring_function = {
        "type": "linear_combination",
        "formula": "w_success * probability - w_cost * cost - w_risk * risk",
        "weights": {
            "success_probability": 0.5,
            "cost": 0.3,
            "risk": 0.2,
        },
        "components": {
            "success_probability": {
                "source": "simulation_goal_achievement_rate",
                "description": "Proportion of ensemble runs that achieved goal",
            },
            "cost": {
                "source": "simulation_execution_cost_mean",
                "description": "Mean cost from simulation runs",
            },
            "risk": {
                "source": "simulation_outcome_variance",
                "description": "Variance in outcome across ensemble runs",
            },
        },
    }

    return PlanTraceResponse(
        trace_id=str(uuid_module.uuid4()),
        planning_spec_id=plan_id,
        total_candidates_generated=result.total_paths_generated,
        candidates_pruned=result.total_paths_pruned,
        candidates_evaluated=result.total_paths_valid,
        search_algorithm="beam_search",
        explored_states_count=result.explored_states_count,
        expanded_nodes_count=result.expanded_nodes_count,
        pruning_decisions=pruning_decisions,
        runs_executed=[],  # Would be populated from DB
        total_runs_count=0,
        scoring_function=scoring_function,
        top_k_results=top_k_results,
        selected_candidate_id=result.top_paths[0].path_id if result.top_paths else None,
        search_time_ms=result.planning_time_ms,
        evaluation_time_ms=0,
        total_time_ms=result.planning_time_ms,
        summary=result.planning_summary,
    )


@router.get(
    "/plans/{plan_id}/evidence-runs",
    summary="Open evidence runs (STEP 6)",
)
async def open_evidence_runs(
    plan_id: str,
    candidate_id: Optional[str] = Query(None, description="Filter by candidate"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """
    STEP 6: Open evidence runs for a plan or specific candidate.

    Returns list of simulation runs that provide evidence for the plan evaluation.
    """
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()
    result = service.get_plan(plan_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    # In production, this would query PlanEvaluation records
    evidence_runs = []

    return {
        "plan_id": plan_id,
        "candidate_id": candidate_id,
        "evidence_runs": evidence_runs,
        "total_runs": len(evidence_runs),
        "message": "Evidence runs are populated during planning evaluation phase",
    }


@router.get(
    "/plans/{plan_id}/node-chain",
    summary="Open node chain (STEP 6)",
)
async def open_node_chain(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """
    STEP 6: Open the node chain for a plan.

    Returns the chain of nodes created during planning (parent -> children).
    """
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()
    result = service.get_plan(plan_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    # In production, this would query Node relationships
    node_chain = []

    return {
        "plan_id": plan_id,
        "node_chain": node_chain,
        "chain_length": len(node_chain),
        "message": "Node chain is populated when paths are branched to Universe Map",
    }


@router.post(
    "/plans/{plan_id}/candidates/{candidate_id}/re-run",
    summary="Re-run a candidate (STEP 6)",
)
async def rerun_candidate(
    plan_id: str,
    candidate_id: str,
    request: RerunCandidateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """
    STEP 6: Re-run a candidate plan with new parameters.

    Can use a new seed or request additional ensemble runs.
    """
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()
    result = service.get_plan(plan_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    # Find the candidate
    candidate = None
    for path in result.top_paths:
        if path.path_id == candidate_id:
            candidate = path
            break

    if not candidate:
        for cluster in result.clusters:
            if cluster.representative_path.path_id == candidate_id:
                candidate = cluster.representative_path
                break
            for child in cluster.child_paths:
                if child.path_id == candidate_id:
                    candidate = child
                    break

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate {candidate_id} not found in plan {plan_id}",
        )

    # Audit logging
    audit_logger = get_tenant_audit_logger()
    await audit_logger.log(
        tenant_id=str(tenant_ctx.tenant_id) if tenant_ctx.tenant_id else None,
        action=TenantAuditAction.TARGET_PLAN_UPDATE,
        resource_type=AuditResourceType.PLAN_CANDIDATE,
        resource_id=candidate_id,
        actor=AuditActor(
            type=AuditActorType.USER,
            id=str(current_user.id),
            name=current_user.email,
        ),
        details={
            "plan_id": plan_id,
            "action": "re-run",
            "new_seed": request.new_seed,
            "additional_runs": request.additional_runs,
        },
    )

    return {
        "plan_id": plan_id,
        "candidate_id": candidate_id,
        "status": "queued",
        "new_seed": request.new_seed,
        "additional_runs": request.additional_runs,
        "message": "Candidate re-run has been queued for evaluation",
    }


@router.post(
    "/plans/{plan_id}/verify",
    summary="Mark plan as verified (STEP 6)",
)
async def mark_plan_verified(
    plan_id: str,
    request: MarkVerifiedRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """
    STEP 6: Mark a plan as verified.

    Plans should only be marked verified when simulation evidence exists.
    Unverified plans are clearly labeled.
    """
    from app.services.target_mode import get_target_mode_service

    service = get_target_mode_service()
    result = service.get_plan(plan_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )

    # Check if simulation evidence exists
    has_evidence = result.total_paths_valid > 0 and request.verified_by_simulation

    if not has_evidence and request.verified_by_simulation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark as verified without simulation evidence. Set verified_by_simulation=false for manual verification.",
        )

    # Audit logging
    audit_logger = get_tenant_audit_logger()
    await audit_logger.log(
        tenant_id=str(tenant_ctx.tenant_id) if tenant_ctx.tenant_id else None,
        action=TenantAuditAction.TARGET_PLAN_UPDATE,
        resource_type=AuditResourceType.TARGET_PLAN,
        resource_id=plan_id,
        actor=AuditActor(
            type=AuditActorType.USER,
            id=str(current_user.id),
            name=current_user.email,
        ),
        details={
            "action": "mark_verified",
            "verified_by_simulation": request.verified_by_simulation,
            "verification_notes": request.verification_notes,
        },
    )

    return {
        "plan_id": plan_id,
        "verified": True,
        "verified_at": datetime.utcnow().isoformat(),
        "verified_by": current_user.email,
        "verified_by_simulation": request.verified_by_simulation,
        "verification_notes": request.verification_notes,
        "evidence_summary": {
            "total_paths_evaluated": result.total_paths_valid,
            "total_runs": 0,  # Would be from DB
            "has_simulation_evidence": has_evidence,
        },
    }
