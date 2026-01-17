"""
Project Management Endpoints

DEPRECATED: This module is deprecated as of Slice 1D-A (2026-01-17).
Use /api/v1/project-specs endpoints instead.

All endpoints in this file will be removed in a future release.
Frontend and API clients should migrate to:
- POST /api/v1/project-specs - Create project
- GET /api/v1/project-specs - List projects
- GET /api/v1/project-specs/{id} - Get project
- PATCH /api/v1/project-specs/{id} - Update project
- DELETE /api/v1/project-specs/{id} - Delete project
- PATCH /api/v1/project-specs/{id}/wizard-state - Update wizard state
- POST /api/v1/project-specs/{id}/status - Change project status
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.simulation import Project
from app.models.user import User
from app.schemas.simulation import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter()

# Deprecation date for all endpoints in this module
DEPRECATION_DATE = "2026-01-17"
SUNSET_DATE = "2026-04-01"  # 3 months from deprecation
MIGRATION_URL = "/api/v1/project-specs"


def add_deprecation_headers(response: Response) -> None:
    """Add RFC 8594 deprecation headers to response."""
    response.headers["Deprecation"] = DEPRECATION_DATE
    response.headers["Sunset"] = SUNSET_DATE
    response.headers["Link"] = f'<{MIGRATION_URL}>; rel="successor-version"'


@router.get("/", response_model=list[ProjectResponse], deprecated=True)
async def list_projects(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    domain: Optional[str] = Query(None, pattern="^(marketing|political|finance|custom)$"),
    search: Optional[str] = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Project]:
    """
    List all projects for current user.

    DEPRECATED: Use GET /api/v1/project-specs instead.
    This endpoint will be removed after 2026-04-01.
    """
    add_deprecation_headers(response)
    query = select(Project).where(Project.user_id == current_user.id)

    if domain:
        query = query.where(Project.domain == domain)

    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))

    query = query.offset(skip).limit(limit).order_by(Project.updated_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, deprecated=True)
async def create_project(
    project_in: ProjectCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    """
    Create a new project.

    DEPRECATED: Use POST /api/v1/project-specs instead.
    This endpoint will be removed after 2026-04-01.
    """
    add_deprecation_headers(response)
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


@router.get("/{project_id}", response_model=ProjectResponse, deprecated=True)
async def get_project(
    project_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    """
    Get project by ID.

    DEPRECATED: Use GET /api/v1/project-specs/{id} instead.
    This endpoint will be removed after 2026-04-01.
    """
    add_deprecation_headers(response)
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


@router.put("/{project_id}", response_model=ProjectResponse, deprecated=True)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    """
    Update project by ID.

    DEPRECATED: Use PATCH /api/v1/project-specs/{id} instead.
    This endpoint will be removed after 2026-04-01.
    """
    add_deprecation_headers(response)
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


@router.delete("/{project_id}", deprecated=True)
async def delete_project(
    project_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Delete project by ID (cascades to scenarios and runs).

    DEPRECATED: Use DELETE /api/v1/project-specs/{id} instead.
    This endpoint will be removed after 2026-04-01.
    """
    add_deprecation_headers(response)
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


@router.post("/{project_id}/duplicate", response_model=ProjectResponse, deprecated=True)
async def duplicate_project(
    project_id: UUID,
    response: Response,
    new_name: Optional[str] = Query(None, max_length=255),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    """
    Duplicate a project with all its scenarios.

    DEPRECATED: Use POST /api/v1/project-specs/{id}/duplicate instead.
    This endpoint will be removed after 2026-04-01.
    """
    add_deprecation_headers(response)
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


@router.get("/{project_id}/stats", deprecated=True)
async def get_project_stats(
    project_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get statistics for a project.

    DEPRECATED: Use GET /api/v1/project-specs/{id}/stats instead.
    This endpoint will be removed after 2026-04-01.
    """
    add_deprecation_headers(response)
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
