"""
Target Plans API Endpoints
User-defined intervention plans for Target Mode.

Provides endpoints for:
- CRUD operations on target plans
- AI-assisted plan generation
- Creating branches from plans
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_tenant, TenantContext
from app.models.user import User
from app.models.target_plan import TargetPlan, TargetPlanSource
from app.models.node import Node, InterventionType
from app.schemas.target_plan import (
    TargetPlanCreate,
    TargetPlanUpdate,
    TargetPlanResponse,
    TargetPlanListResponse,
    AIGeneratePlanRequest,
    AIGeneratePlanResponse,
    CreateBranchFromPlanRequest,
    CreateBranchFromPlanResponse,
)


router = APIRouter()


# =============================================================================
# List & Get Operations
# =============================================================================

@router.get(
    "/project-specs/{project_id}/target-plans",
    response_model=TargetPlanListResponse,
    summary="List target plans for a project"
)
async def list_target_plans(
    project_id: UUID,
    node_id: Optional[UUID] = Query(None, description="Filter by node"),
    source: Optional[str] = Query(None, description="Filter by source (manual/ai)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
    current_user: User = Depends(get_current_user),
) -> TargetPlanListResponse:
    """List all target plans for a project with optional filters."""
    # Build query
    query = select(TargetPlan).where(
        TargetPlan.tenant_id == tenant.tenant_id,
        TargetPlan.project_id == project_id,
    )

    if node_id:
        query = query.where(TargetPlan.node_id == node_id)
    if source:
        query = query.where(TargetPlan.source == source)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Get paginated results
    query = query.order_by(TargetPlan.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    plans = result.scalars().all()

    return TargetPlanListResponse(
        plans=[TargetPlanResponse.model_validate(p) for p in plans],
        total=total,
    )


@router.get(
    "/target-plans/{plan_id}",
    response_model=TargetPlanResponse,
    summary="Get a target plan by ID"
)
async def get_target_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
    current_user: User = Depends(get_current_user),
) -> TargetPlanResponse:
    """Get a specific target plan by ID."""
    query = select(TargetPlan).where(
        TargetPlan.id == plan_id,
        TargetPlan.tenant_id == tenant.tenant_id,
    )
    result = await db.execute(query)
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target plan not found"
        )

    return TargetPlanResponse.model_validate(plan)


# =============================================================================
# Create & Update Operations
# =============================================================================

@router.post(
    "/project-specs/{project_id}/target-plans",
    response_model=TargetPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new target plan"
)
async def create_target_plan(
    project_id: UUID,
    data: TargetPlanCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
    current_user: User = Depends(get_current_user),
) -> TargetPlanResponse:
    """Create a new target plan for a project."""
    # Create the plan
    plan = TargetPlan(
        tenant_id=tenant.tenant_id,
        project_id=project_id,
        node_id=data.node_id,
        name=data.name,
        description=data.description,
        target_metric=data.target_metric,
        target_value=data.target_value,
        horizon_ticks=data.horizon_ticks,
        constraints_json=data.constraints_json.model_dump() if data.constraints_json else None,
        steps_json=[s.model_dump() for s in data.steps_json] if data.steps_json else None,
        source=data.source.value,
        ai_prompt=data.ai_prompt,
    )

    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return TargetPlanResponse.model_validate(plan)


@router.put(
    "/target-plans/{plan_id}",
    response_model=TargetPlanResponse,
    summary="Update a target plan"
)
async def update_target_plan(
    plan_id: UUID,
    data: TargetPlanUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
    current_user: User = Depends(get_current_user),
) -> TargetPlanResponse:
    """Update an existing target plan."""
    query = select(TargetPlan).where(
        TargetPlan.id == plan_id,
        TargetPlan.tenant_id == tenant.tenant_id,
    )
    result = await db.execute(query)
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target plan not found"
        )

    # Update fields if provided
    if data.name is not None:
        plan.name = data.name
    if data.description is not None:
        plan.description = data.description
    if data.node_id is not None:
        plan.node_id = data.node_id
    if data.target_metric is not None:
        plan.target_metric = data.target_metric
    if data.target_value is not None:
        plan.target_value = data.target_value
    if data.horizon_ticks is not None:
        plan.horizon_ticks = data.horizon_ticks
    if data.constraints_json is not None:
        plan.constraints_json = data.constraints_json.model_dump()
    if data.steps_json is not None:
        plan.steps_json = [s.model_dump() for s in data.steps_json]

    await db.commit()
    await db.refresh(plan)

    return TargetPlanResponse.model_validate(plan)


@router.delete(
    "/target-plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a target plan"
)
async def delete_target_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
    current_user: User = Depends(get_current_user),
):
    """Delete a target plan."""
    query = select(TargetPlan).where(
        TargetPlan.id == plan_id,
        TargetPlan.tenant_id == tenant.tenant_id,
    )
    result = await db.execute(query)
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target plan not found"
        )

    await db.delete(plan)
    await db.commit()


# =============================================================================
# AI Generation (stub - will be implemented via OpenRouter in frontend)
# =============================================================================

@router.post(
    "/project-specs/{project_id}/target-plans/generate",
    response_model=AIGeneratePlanResponse,
    summary="Generate a plan using AI"
)
async def generate_plan_with_ai(
    project_id: UUID,
    data: AIGeneratePlanRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
    current_user: User = Depends(get_current_user),
) -> AIGeneratePlanResponse:
    """
    Generate intervention plan using AI.

    Note: This is a backend stub. The actual AI generation happens via
    OpenRouter in the Next.js frontend API route for better control.
    """
    # Create a placeholder plan that the frontend will update
    plan = TargetPlan(
        tenant_id=tenant.tenant_id,
        project_id=project_id,
        node_id=data.node_id,
        name=f"AI Plan: {data.prompt[:50]}...",
        description="AI-generated plan (pending)",
        target_metric=data.target_metric or "to_be_determined",
        target_value=0.0,
        horizon_ticks=data.horizon_ticks,
        constraints_json=data.constraints.model_dump() if data.constraints else None,
        steps_json=[],
        source=TargetPlanSource.AI.value,
        ai_prompt=data.prompt,
    )

    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return AIGeneratePlanResponse(
        plan=TargetPlanResponse.model_validate(plan),
        reasoning="Plan created. Use the frontend AI service to generate steps.",
        confidence=0.0,
    )


# =============================================================================
# Branch Creation
# =============================================================================

@router.post(
    "/target-plans/{plan_id}/create-branch",
    response_model=CreateBranchFromPlanResponse,
    summary="Create a branch from a target plan"
)
async def create_branch_from_plan(
    plan_id: UUID,
    data: CreateBranchFromPlanRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
    current_user: User = Depends(get_current_user),
) -> CreateBranchFromPlanResponse:
    """
    Create a new Universe Map branch from a target plan.

    Creates a Manual Fork node with the plan's intervention steps
    configured as the node's intervention_payload.
    """
    # Get the plan
    query = select(TargetPlan).where(
        TargetPlan.id == plan_id,
        TargetPlan.tenant_id == tenant.tenant_id,
    )
    result = await db.execute(query)
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target plan not found"
        )

    # Get the parent node (either specified node or project root, or create one)
    parent_node_id = plan.node_id
    if not parent_node_id:
        # Get root node from project
        from app.models.project_spec import ProjectSpec
        proj_query = select(ProjectSpec).where(ProjectSpec.id == plan.project_id)
        proj_result = await db.execute(proj_query)
        project = proj_result.scalar_one_or_none()
        if project and project.root_node_id:
            parent_node_id = project.root_node_id

    # If no parent node exists, create a baseline root node
    if not parent_node_id:
        root_node = Node(
            tenant_id=tenant.tenant_id,
            project_id=plan.project_id,
            parent_node_id=None,
            depth=0,
            label="Baseline",
            description="Auto-created baseline node",
            is_baseline=True,
            probability=1.0,
            cumulative_probability=1.0,
        )
        db.add(root_node)
        await db.flush()
        parent_node_id = root_node.id

        # Update project with root_node_id if we have access
        if project:
            project.root_node_id = root_node.id

    # Create the new branch node (without intervention fields - those go on Edge)
    branch_name = data.branch_name or f"Branch: {plan.name}"

    new_node = Node(
        tenant_id=tenant.tenant_id,
        project_id=plan.project_id,
        parent_node_id=parent_node_id,
        label=branch_name,
        description=f"Created from target plan: {plan.name}",
    )

    db.add(new_node)
    await db.flush()  # Get the new_node.id before creating Edge

    # Create Edge from parent to new node with intervention details
    from app.models.node import Edge
    edge = Edge(
        tenant_id=tenant.tenant_id,
        project_id=plan.project_id,
        from_node_id=parent_node_id,
        to_node_id=new_node.id,
        intervention={
            "intervention_type": InterventionType.MANUAL_FORK.value,
            "source_plan_id": str(plan.id),
            "target_metric": plan.target_metric,
            "target_value": plan.target_value,
            "horizon_ticks": plan.horizon_ticks,
            "steps": plan.steps_json or [],
            "constraints": plan.constraints_json or {},
        },
        explanation={
            "short_label": f"Target Plan: {plan.name}",
            "description": f"Created from target plan targeting {plan.target_metric}",
        },
    )

    db.add(edge)
    await db.commit()
    await db.refresh(new_node)

    return CreateBranchFromPlanResponse(
        node_id=new_node.id,
        plan_id=plan.id,
        message=f"Branch '{branch_name}' created successfully. Navigate to Universe Map to view.",
    )
