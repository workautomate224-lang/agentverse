"""
Project Management Endpoints
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.simulation import Project
from app.models.user import User
from app.schemas.simulation import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter()


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    domain: Optional[str] = Query(None, pattern="^(marketing|political|finance|custom)$"),
    search: Optional[str] = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Project]:
    """
    List all projects for current user.
    """
    query = select(Project).where(Project.user_id == current_user.id)

    if domain:
        query = query.where(Project.domain == domain)

    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))

    query = query.offset(skip).limit(limit).order_by(Project.updated_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    """
    Create a new project.
    """
    project = Project(
        user_id=current_user.id,
        name=project_in.name,
        description=project_in.description,
        domain=project_in.domain,
        settings=project_in.settings,
    )

    db.add(project)
    await db.flush()
    await db.refresh(project)

    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    """
    Get project by ID.
    """
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    """
    Update project by ID.
    """
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    update_data = project_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    await db.refresh(project)

    return project


@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Delete project by ID (cascades to scenarios and runs).
    """
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await db.delete(project)

    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/duplicate", response_model=ProjectResponse)
async def duplicate_project(
    project_id: UUID,
    new_name: Optional[str] = Query(None, max_length=255),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    """
    Duplicate a project with all its scenarios.
    """
    result = await db.execute(
        select(Project)
        .where(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
        .options(selectinload(Project.scenarios))
    )
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Create duplicate project
    duplicate = Project(
        user_id=current_user.id,
        name=new_name or f"{original.name} (Copy)",
        description=original.description,
        domain=original.domain,
        settings=original.settings.copy() if original.settings else {},
    )

    db.add(duplicate)
    await db.flush()
    await db.refresh(duplicate)

    return duplicate


@router.get("/{project_id}/stats")
async def get_project_stats(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get statistics for a project.
    """
    from app.models.simulation import Scenario, SimulationRun

    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Count scenarios
    scenario_result = await db.execute(
        select(func.count(Scenario.id)).where(Scenario.project_id == project_id)
    )
    scenario_count = scenario_result.scalar()

    # Count simulation runs through scenarios
    run_result = await db.execute(
        select(func.count(SimulationRun.id))
        .join(Scenario, SimulationRun.scenario_id == Scenario.id)
        .where(Scenario.project_id == project_id)
    )
    run_count = run_result.scalar()

    # Calculate total costs
    cost_result = await db.execute(
        select(func.sum(SimulationRun.cost_usd))
        .join(Scenario, SimulationRun.scenario_id == Scenario.id)
        .where(Scenario.project_id == project_id)
    )
    total_cost = cost_result.scalar() or 0.0

    return {
        "project_id": str(project_id),
        "scenario_count": scenario_count,
        "simulation_count": run_count,
        "total_cost_usd": round(total_cost, 4),
    }
