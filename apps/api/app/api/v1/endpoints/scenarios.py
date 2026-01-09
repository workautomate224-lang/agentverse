"""
Scenario Management Endpoints
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.simulation import Project, Scenario
from app.models.user import User
from app.schemas.simulation import ScenarioCreate, ScenarioResponse, ScenarioUpdate

router = APIRouter()


async def verify_project_access(
    project_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> Project:
    """Verify user has access to the project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == user_id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


@router.get("/", response_model=list[ScenarioResponse])
async def list_scenarios(
    project_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(
        None, pattern="^(draft|ready|running|completed)$"
    ),
    scenario_type: Optional[str] = Query(
        None, pattern="^(survey|election|product_launch|policy|custom)$"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Scenario]:
    """
    List scenarios, optionally filtered by project.
    """
    query = (
        select(Scenario)
        .join(Project)
        .where(Project.user_id == current_user.id)
    )

    if project_id:
        query = query.where(Scenario.project_id == project_id)

    if status_filter:
        query = query.where(Scenario.status == status_filter)

    if scenario_type:
        query = query.where(Scenario.scenario_type == scenario_type)

    query = query.offset(skip).limit(limit).order_by(Scenario.updated_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    scenario_in: ScenarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Scenario:
    """
    Create a new scenario.
    """
    # Verify project access
    await verify_project_access(scenario_in.project_id, current_user.id, db)

    scenario = Scenario(
        project_id=scenario_in.project_id,
        name=scenario_in.name,
        description=scenario_in.description,
        scenario_type=scenario_in.scenario_type,
        context=scenario_in.context,
        questions=scenario_in.questions,
        variables=scenario_in.variables,
        population_size=scenario_in.population_size,
        demographics=scenario_in.demographics,
        persona_template=scenario_in.persona_template,
        model_config_json=scenario_in.model_config_json,
        simulation_mode=scenario_in.simulation_mode,
    )

    db.add(scenario)
    await db.flush()
    await db.refresh(scenario)

    return scenario


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Scenario:
    """
    Get scenario by ID.
    """
    result = await db.execute(
        select(Scenario)
        .join(Project)
        .where(
            Scenario.id == scenario_id,
            Project.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    return scenario


@router.put("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: UUID,
    scenario_update: ScenarioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Scenario:
    """
    Update scenario by ID.
    """
    result = await db.execute(
        select(Scenario)
        .join(Project)
        .where(
            Scenario.id == scenario_id,
            Project.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    # Cannot update running scenarios
    if scenario.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a running scenario",
        )

    update_data = scenario_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(scenario, field, value)

    await db.flush()
    await db.refresh(scenario)

    return scenario


@router.delete("/{scenario_id}")
async def delete_scenario(
    scenario_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Delete scenario by ID.
    """
    result = await db.execute(
        select(Scenario)
        .join(Project)
        .where(
            Scenario.id == scenario_id,
            Project.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    # Cannot delete running scenarios
    if scenario.status == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running scenario",
        )

    await db.delete(scenario)

    return {"message": "Scenario deleted successfully"}


@router.post("/{scenario_id}/duplicate", response_model=ScenarioResponse)
async def duplicate_scenario(
    scenario_id: UUID,
    new_name: Optional[str] = Query(None, max_length=255),
    target_project_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Scenario:
    """
    Duplicate a scenario.
    """
    result = await db.execute(
        select(Scenario)
        .join(Project)
        .where(
            Scenario.id == scenario_id,
            Project.user_id == current_user.id,
        )
    )
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    # If target project specified, verify access
    project_id = target_project_id or original.project_id
    if target_project_id:
        await verify_project_access(target_project_id, current_user.id, db)

    duplicate = Scenario(
        project_id=project_id,
        name=new_name or f"{original.name} (Copy)",
        description=original.description,
        scenario_type=original.scenario_type,
        context=original.context,
        questions=original.questions.copy() if original.questions else [],
        variables=original.variables.copy() if original.variables else {},
        population_size=original.population_size,
        demographics=original.demographics.copy() if original.demographics else {},
        persona_template=original.persona_template.copy() if original.persona_template else None,
        model_config_json=original.model_config_json.copy() if original.model_config_json else {},
        simulation_mode=original.simulation_mode,
        status="draft",
    )

    db.add(duplicate)
    await db.flush()
    await db.refresh(duplicate)

    return duplicate


@router.post("/{scenario_id}/validate")
async def validate_scenario(
    scenario_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Validate scenario configuration before running.
    """
    result = await db.execute(
        select(Scenario)
        .join(Project)
        .where(
            Scenario.id == scenario_id,
            Project.user_id == current_user.id,
        )
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    errors = []
    warnings = []

    # Validate context
    if not scenario.context or len(scenario.context) < 50:
        errors.append("Context must be at least 50 characters")

    # Validate questions
    if not scenario.questions or len(scenario.questions) == 0:
        errors.append("At least one question is required")

    # Validate demographics
    if not scenario.demographics:
        errors.append("Demographics configuration is required")

    # Validate population size against tier limits
    if scenario.population_size > 10000:
        warnings.append("Large population size may increase costs significantly")

    # Check if ready to run
    is_valid = len(errors) == 0

    if is_valid and scenario.status == "draft":
        scenario.status = "ready"
        await db.flush()

    return {
        "scenario_id": str(scenario_id),
        "is_valid": is_valid,
        "status": scenario.status,
        "errors": errors,
        "warnings": warnings,
    }
