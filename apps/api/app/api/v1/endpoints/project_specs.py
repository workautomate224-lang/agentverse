"""
Project Spec API Endpoints
Reference: project.md §6.1

Provides endpoints for:
- Managing project specifications
- Configuring personas, event scripts, rulesets
- Creating runs from projects

This is the spec-compliant replacement for the legacy projects endpoint.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.tenant import (
    TenantContext,
    require_tenant,
)
from app.models.user import User


# ============================================================================
# Request/Response Schemas (project.md §6.1)
# ============================================================================

class PersonaConfig(BaseModel):
    """Persona configuration per project.md §6.2."""
    persona_set_ref: Optional[str] = None
    demographics_distribution: Optional[dict] = None
    expansion_level: str = Field(default="standard", pattern="^(minimal|standard|full|deep)$")


class EventScriptConfig(BaseModel):
    """Event script configuration per project.md §6.4."""
    script_ref: Optional[str] = None
    events: List[dict] = Field(default_factory=list)


class RuleSetConfig(BaseModel):
    """Society mode ruleset configuration."""
    ruleset_ref: Optional[str] = None
    rules: List[dict] = Field(default_factory=list)
    parameters: dict = Field(default_factory=dict)


class ProjectSpecCreate(BaseModel):
    """Request to create a project spec."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    domain: str = Field(default="custom", pattern="^(marketing|political|finance|custom)$")

    # Data refs (project.md §6.1)
    dataset_refs: List[str] = Field(default_factory=list)
    persona_config: Optional[PersonaConfig] = None
    event_script_config: Optional[EventScriptConfig] = None
    ruleset_config: Optional[RuleSetConfig] = None

    # Versions
    schema_version: str = Field(default="1.0.0")

    # Settings
    settings: dict = Field(default_factory=dict)


class ProjectSpecUpdate(BaseModel):
    """Request to update a project spec."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    domain: Optional[str] = Field(None, pattern="^(marketing|political|finance|custom)$")
    dataset_refs: Optional[List[str]] = None
    persona_config: Optional[PersonaConfig] = None
    event_script_config: Optional[EventScriptConfig] = None
    ruleset_config: Optional[RuleSetConfig] = None
    settings: Optional[dict] = None


class ProjectSpecResponse(BaseModel):
    """Project spec response per project.md §6.1."""
    project_id: str
    tenant_id: str
    name: str
    description: Optional[str]
    domain: str

    # Data refs
    dataset_refs: List[str]
    persona_set_ref: Optional[str]
    event_script_ref: Optional[str]
    ruleset_ref: Optional[str]

    # Versions
    schema_version: str
    project_version: str

    # Stats
    node_count: int = 0
    run_count: int = 0

    # Settings
    settings: dict

    # Timestamps
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProjectStatsResponse(BaseModel):
    """Project statistics."""
    project_id: str
    node_count: int
    explored_nodes: int
    run_count: int
    completed_runs: int
    total_agents_simulated: int
    total_ticks_simulated: int
    max_depth: int


# ============================================================================
# API Router
# ============================================================================

router = APIRouter()


@router.get(
    "/",
    response_model=List[ProjectSpecResponse],
    summary="List project specs",
)
async def list_project_specs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    domain: Optional[str] = Query(None, pattern="^(marketing|political|finance|custom)$"),
    search: Optional[str] = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> List[ProjectSpecResponse]:
    """
    List all project specs for the current tenant.

    Projects are the top-level container for simulations.
    They hold references to datasets, personas, and event scripts.
    """
    # Query project_specs table
    from sqlalchemy import text

    query = text("""
        SELECT
            project_id, tenant_id, name, description, domain,
            dataset_refs, persona_set_ref, event_script_ref, ruleset_ref,
            schema_version, project_version, settings,
            created_at, updated_at
        FROM project_specs
        WHERE tenant_id = :tenant_id
        AND (:domain IS NULL OR domain = :domain)
        AND (:search IS NULL OR name ILIKE :search_pattern)
        ORDER BY updated_at DESC
        OFFSET :skip LIMIT :limit
    """)

    result = await db.execute(
        query,
        {
            "tenant_id": tenant_ctx.tenant_id,
            "domain": domain,
            "search": search,
            "search_pattern": f"%{search}%" if search else None,
            "skip": skip,
            "limit": limit,
        },
    )

    rows = result.fetchall()

    return [
        ProjectSpecResponse(
            project_id=str(row.project_id),
            tenant_id=str(row.tenant_id),
            name=row.name,
            description=row.description,
            domain=row.domain,
            dataset_refs=row.dataset_refs or [],
            persona_set_ref=row.persona_set_ref,
            event_script_ref=row.event_script_ref,
            ruleset_ref=row.ruleset_ref,
            schema_version=row.schema_version,
            project_version=row.project_version,
            settings=row.settings or {},
            created_at=row.created_at.isoformat() if row.created_at else "",
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
        )
        for row in rows
    ]


@router.post(
    "/",
    response_model=ProjectSpecResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project spec",
)
async def create_project_spec(
    request: ProjectSpecCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ProjectSpecResponse:
    """
    Create a new project spec.

    A project is the top-level container for simulations.
    It defines the personas, events, and rules for the simulation.
    """
    import uuid
    from datetime import datetime
    from sqlalchemy import text

    project_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # Extract refs from configs
    persona_set_ref = None
    if request.persona_config:
        persona_set_ref = request.persona_config.persona_set_ref

    event_script_ref = None
    if request.event_script_config:
        event_script_ref = request.event_script_config.script_ref

    ruleset_ref = None
    if request.ruleset_config:
        ruleset_ref = request.ruleset_config.ruleset_ref

    # Insert project spec
    insert_query = text("""
        INSERT INTO project_specs (
            project_id, tenant_id, name, description, domain,
            dataset_refs, persona_set_ref, event_script_ref, ruleset_ref,
            schema_version, project_version, settings,
            created_at, updated_at
        ) VALUES (
            :project_id, :tenant_id, :name, :description, :domain,
            :dataset_refs, :persona_set_ref, :event_script_ref, :ruleset_ref,
            :schema_version, :project_version, :settings,
            :created_at, :updated_at
        )
    """)

    await db.execute(
        insert_query,
        {
            "project_id": project_id,
            "tenant_id": tenant_ctx.tenant_id,
            "name": request.name,
            "description": request.description,
            "domain": request.domain,
            "dataset_refs": request.dataset_refs,
            "persona_set_ref": persona_set_ref,
            "event_script_ref": event_script_ref,
            "ruleset_ref": ruleset_ref,
            "schema_version": request.schema_version,
            "project_version": "1.0.0",
            "settings": request.settings,
            "created_at": now,
            "updated_at": now,
        },
    )

    await db.commit()

    return ProjectSpecResponse(
        project_id=project_id,
        tenant_id=tenant_ctx.tenant_id,
        name=request.name,
        description=request.description,
        domain=request.domain,
        dataset_refs=request.dataset_refs,
        persona_set_ref=persona_set_ref,
        event_script_ref=event_script_ref,
        ruleset_ref=ruleset_ref,
        schema_version=request.schema_version,
        project_version="1.0.0",
        settings=request.settings,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
    )


@router.get(
    "/{project_id}",
    response_model=ProjectSpecResponse,
    summary="Get project spec",
)
async def get_project_spec(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ProjectSpecResponse:
    """Get a project spec by ID."""
    from sqlalchemy import text

    query = text("""
        SELECT
            project_id, tenant_id, name, description, domain,
            dataset_refs, persona_set_ref, event_script_ref, ruleset_ref,
            schema_version, project_version, settings,
            created_at, updated_at
        FROM project_specs
        WHERE project_id = :project_id AND tenant_id = :tenant_id
    """)

    result = await db.execute(
        query,
        {"project_id": project_id, "tenant_id": tenant_ctx.tenant_id},
    )

    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    return ProjectSpecResponse(
        project_id=str(row.project_id),
        tenant_id=str(row.tenant_id),
        name=row.name,
        description=row.description,
        domain=row.domain,
        dataset_refs=row.dataset_refs or [],
        persona_set_ref=row.persona_set_ref,
        event_script_ref=row.event_script_ref,
        ruleset_ref=row.ruleset_ref,
        schema_version=row.schema_version,
        project_version=row.project_version,
        settings=row.settings or {},
        created_at=row.created_at.isoformat() if row.created_at else "",
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


@router.put(
    "/{project_id}",
    response_model=ProjectSpecResponse,
    summary="Update project spec",
)
async def update_project_spec(
    project_id: str,
    request: ProjectSpecUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ProjectSpecResponse:
    """
    Update a project spec.

    Note: This increments the project_version for tracking.
    """
    from datetime import datetime
    from sqlalchemy import text

    # First check if project exists
    check_query = text("""
        SELECT project_version FROM project_specs
        WHERE project_id = :project_id AND tenant_id = :tenant_id
    """)

    result = await db.execute(
        check_query,
        {"project_id": project_id, "tenant_id": tenant_ctx.tenant_id},
    )

    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # Increment version
    current_version = row.project_version
    parts = current_version.split(".")
    new_version = f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"

    # Build update fields
    update_fields = []
    params = {
        "project_id": project_id,
        "tenant_id": tenant_ctx.tenant_id,
        "updated_at": datetime.utcnow(),
        "project_version": new_version,
    }

    if request.name is not None:
        update_fields.append("name = :name")
        params["name"] = request.name

    if request.description is not None:
        update_fields.append("description = :description")
        params["description"] = request.description

    if request.domain is not None:
        update_fields.append("domain = :domain")
        params["domain"] = request.domain

    if request.dataset_refs is not None:
        update_fields.append("dataset_refs = :dataset_refs")
        params["dataset_refs"] = request.dataset_refs

    if request.persona_config is not None:
        update_fields.append("persona_set_ref = :persona_set_ref")
        params["persona_set_ref"] = request.persona_config.persona_set_ref

    if request.event_script_config is not None:
        update_fields.append("event_script_ref = :event_script_ref")
        params["event_script_ref"] = request.event_script_config.script_ref

    if request.ruleset_config is not None:
        update_fields.append("ruleset_ref = :ruleset_ref")
        params["ruleset_ref"] = request.ruleset_config.ruleset_ref

    if request.settings is not None:
        update_fields.append("settings = :settings")
        params["settings"] = request.settings

    update_fields.append("updated_at = :updated_at")
    update_fields.append("project_version = :project_version")

    update_query = text(f"""
        UPDATE project_specs
        SET {', '.join(update_fields)}
        WHERE project_id = :project_id AND tenant_id = :tenant_id
    """)

    await db.execute(update_query, params)
    await db.commit()

    # Return updated project
    return await get_project_spec(project_id, db, current_user, tenant_ctx)


@router.delete(
    "/{project_id}",
    summary="Delete project spec",
)
async def delete_project_spec(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """
    Delete a project spec.

    Warning: This also deletes all associated nodes and runs.
    """
    from sqlalchemy import text

    # First check if project exists
    check_query = text("""
        SELECT project_id FROM project_specs
        WHERE project_id = :project_id AND tenant_id = :tenant_id
    """)

    result = await db.execute(
        check_query,
        {"project_id": project_id, "tenant_id": tenant_ctx.tenant_id},
    )

    if not result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # Delete associated data (cascade should handle most of this)
    delete_query = text("""
        DELETE FROM project_specs
        WHERE project_id = :project_id AND tenant_id = :tenant_id
    """)

    await db.execute(
        delete_query,
        {"project_id": project_id, "tenant_id": tenant_ctx.tenant_id},
    )

    await db.commit()

    return {"message": f"Project {project_id} deleted successfully"}


@router.get(
    "/{project_id}/stats",
    response_model=ProjectStatsResponse,
    summary="Get project statistics",
)
async def get_project_stats(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ProjectStatsResponse:
    """
    Get statistics for a project.

    Returns node count, run count, and simulation metrics.
    """
    from sqlalchemy import text

    # Check project exists
    check_query = text("""
        SELECT project_id FROM project_specs
        WHERE project_id = :project_id AND tenant_id = :tenant_id
    """)

    result = await db.execute(
        check_query,
        {"project_id": project_id, "tenant_id": tenant_ctx.tenant_id},
    )

    if not result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # Get node stats
    node_query = text("""
        SELECT
            COUNT(*) as node_count,
            COUNT(*) FILTER (WHERE is_explored = true) as explored_nodes,
            COALESCE(MAX(depth), 0) as max_depth
        FROM nodes
        WHERE project_id = :project_id
    """)

    node_result = await db.execute(node_query, {"project_id": project_id})
    node_row = node_result.fetchone()

    # Get run stats
    run_query = text("""
        SELECT
            COUNT(*) as run_count,
            COUNT(*) FILTER (WHERE status = 'completed') as completed_runs,
            COALESCE(SUM(agents_processed), 0) as total_agents,
            COALESCE(SUM(ticks_completed), 0) as total_ticks
        FROM runs
        WHERE project_id = :project_id
    """)

    run_result = await db.execute(run_query, {"project_id": project_id})
    run_row = run_result.fetchone()

    return ProjectStatsResponse(
        project_id=project_id,
        node_count=node_row.node_count if node_row else 0,
        explored_nodes=node_row.explored_nodes if node_row else 0,
        run_count=run_row.run_count if run_row else 0,
        completed_runs=run_row.completed_runs if run_row else 0,
        total_agents_simulated=run_row.total_agents if run_row else 0,
        total_ticks_simulated=run_row.total_ticks if run_row else 0,
        max_depth=node_row.max_depth if node_row else 0,
    )


@router.post(
    "/{project_id}/duplicate",
    response_model=ProjectSpecResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate project spec",
)
async def duplicate_project_spec(
    project_id: str,
    new_name: Optional[str] = Query(None, max_length=255),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ProjectSpecResponse:
    """
    Duplicate a project spec.

    Creates a new project with the same configuration.
    Does NOT copy nodes or runs (starts fresh).
    """
    import uuid
    from datetime import datetime
    from sqlalchemy import text

    # Get original project
    original_query = text("""
        SELECT
            name, description, domain,
            dataset_refs, persona_set_ref, event_script_ref, ruleset_ref,
            schema_version, settings
        FROM project_specs
        WHERE project_id = :project_id AND tenant_id = :tenant_id
    """)

    result = await db.execute(
        original_query,
        {"project_id": project_id, "tenant_id": tenant_ctx.tenant_id},
    )

    original = result.fetchone()

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    new_project_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # Insert duplicate
    insert_query = text("""
        INSERT INTO project_specs (
            project_id, tenant_id, name, description, domain,
            dataset_refs, persona_set_ref, event_script_ref, ruleset_ref,
            schema_version, project_version, settings,
            created_at, updated_at
        ) VALUES (
            :project_id, :tenant_id, :name, :description, :domain,
            :dataset_refs, :persona_set_ref, :event_script_ref, :ruleset_ref,
            :schema_version, :project_version, :settings,
            :created_at, :updated_at
        )
    """)

    await db.execute(
        insert_query,
        {
            "project_id": new_project_id,
            "tenant_id": tenant_ctx.tenant_id,
            "name": new_name or f"{original.name} (Copy)",
            "description": original.description,
            "domain": original.domain,
            "dataset_refs": original.dataset_refs,
            "persona_set_ref": original.persona_set_ref,
            "event_script_ref": original.event_script_ref,
            "ruleset_ref": original.ruleset_ref,
            "schema_version": original.schema_version,
            "project_version": "1.0.0",
            "settings": original.settings or {},
            "created_at": now,
            "updated_at": now,
        },
    )

    await db.commit()

    return await get_project_spec(new_project_id, db, current_user, tenant_ctx)


@router.post(
    "/{project_id}/create-run",
    summary="Create a run from project",
)
async def create_run_from_project(
    project_id: str,
    seeds: List[int] = Query(default=[42]),
    auto_start: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> dict:
    """
    Create a simulation run from a project spec.

    This is a convenience endpoint that creates a run with
    default configuration from the project spec.
    """
    from app.services import get_simulation_orchestrator
    from app.services.simulation_orchestrator import CreateRunInput, RunConfigInput

    orchestrator = get_simulation_orchestrator(db)

    # Verify project exists
    from sqlalchemy import text

    check_query = text("""
        SELECT project_id FROM project_specs
        WHERE project_id = :project_id AND tenant_id = :tenant_id
    """)

    result = await db.execute(
        check_query,
        {"project_id": project_id, "tenant_id": tenant_ctx.tenant_id},
    )

    if not result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # Create run
    config_input = RunConfigInput()
    run_input = CreateRunInput(
        project_id=project_id,
        config=config_input,
        seeds=seeds,
        user_id=str(current_user.id),
        tenant_id=tenant_ctx.tenant_id,
    )

    try:
        if auto_start:
            run, node, task_id = await orchestrator.create_and_start_run(run_input)
        else:
            run, node = await orchestrator.create_run(run_input)
            task_id = None

        await db.commit()

        return {
            "run_id": run.run_id,
            "node_id": run.node_id,
            "project_id": run.project_id,
            "status": run.status,
            "task_id": task_id,
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create run: {str(e)}",
        )
