"""
Project Spec API Endpoints
Reference: project.md §6.1, temporal.md §4

Provides endpoints for:
- Managing project specifications
- Configuring personas, event scripts, rulesets
- Creating runs from projects
- Temporal Knowledge Isolation context (backtest mode)

This is the spec-compliant replacement for the legacy projects endpoint.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_tenant, TenantContext
from app.models.user import User


# ============================================================================
# Request/Response Schemas (project.md §6.1, temporal.md §4)
# ============================================================================


class TemporalContextCreate(BaseModel):
    """
    Temporal Knowledge Isolation context for project creation.
    Reference: temporal.md §4

    Required for backtest mode to enforce temporal cutoffs and prevent
    future data leakage.
    """
    mode: Literal['live', 'backtest'] = Field(
        default='live',
        description="Temporal mode: 'live' for real-time, 'backtest' for historical simulation"
    )
    as_of_datetime: Optional[str] = Field(
        default=None,
        description="ISO 8601 datetime string for backtest cutoff (required if mode='backtest')"
    )
    timezone: str = Field(
        default='Asia/Kuala_Lumpur',
        description="IANA timezone for cutoff evaluation"
    )
    isolation_level: int = Field(
        default=2,
        ge=1,
        le=3,
        description="Isolation strictness: 1=Basic, 2=Strict (recommended), 3=Audit-First"
    )
    allowed_sources: Optional[List[str]] = Field(
        default=None,
        description="List of allowed source identifiers (null = all sources allowed)"
    )

    @field_validator('as_of_datetime')
    @classmethod
    def validate_as_of_datetime(cls, v: Optional[str], info) -> Optional[str]:
        """Validate as_of_datetime is not in the future."""
        if v is None:
            return v
        try:
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            if dt > datetime.now(dt.tzinfo if dt.tzinfo else None):
                raise ValueError("as_of_datetime cannot be in the future")
            return v
        except ValueError as e:
            if "as_of_datetime cannot be" in str(e):
                raise
            raise ValueError(f"Invalid ISO 8601 datetime: {v}")


class TemporalContextResponse(BaseModel):
    """Temporal context in API responses."""
    mode: str
    as_of_datetime: Optional[str]
    timezone: str
    isolation_level: int
    allowed_sources: Optional[List[str]]
    policy_version: str
    lock_status: str


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

    # Temporal Knowledge Isolation (temporal.md §4)
    temporal_context: Optional[TemporalContextCreate] = Field(
        default=None,
        description="Temporal isolation context. Required for backtest mode."
    )

    # Slice 1C: Draft / Resume - allow creating projects as DRAFT
    status: Literal['DRAFT', 'ACTIVE'] = Field(
        default='ACTIVE',
        description="Project status. Use DRAFT when starting wizard flow."
    )
    wizard_state: Optional[dict] = Field(
        default=None,
        description="Initial wizard state for DRAFT projects."
    )

    # Versions
    schema_version: str = Field(default="1.0.0")

    # Settings
    settings: dict = Field(default_factory=dict)

    @field_validator('temporal_context')
    @classmethod
    def validate_backtest_has_datetime(cls, v: Optional[TemporalContextCreate]) -> Optional[TemporalContextCreate]:
        """Validate backtest mode has as_of_datetime."""
        if v is not None and v.mode == 'backtest' and not v.as_of_datetime:
            raise ValueError("as_of_datetime is required for backtest mode")
        return v


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


# ============================================================================
# Slice 1C: Draft / Resume Schemas
# ============================================================================


class WizardLLMProvenance(BaseModel):
    """LLM provenance tracking per Slice 1A invariants."""
    provider: str
    model: str
    cache_hit: bool = False
    fallback_used: bool = False
    fallback_attempts: int = 0
    call_id: Optional[str] = None
    cost_usd: Optional[float] = None
    timestamp: Optional[str] = None
    profile_key: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class WizardClarifyingQuestion(BaseModel):
    """Clarifying question from goal analysis."""
    id: str
    question: str
    options: List[str] = Field(default_factory=list)
    rationale: str = ""
    required: bool = False


class WizardGoalAnalysisResult(BaseModel):
    """Goal analysis result stored in wizard_state."""
    domain_guess: Optional[str] = None
    output_type: Optional[str] = None
    horizon_guess: Optional[str] = None
    scope_guess: Optional[str] = None
    goal_summary: Optional[str] = None
    clarifying_questions: List[WizardClarifyingQuestion] = Field(default_factory=list)
    llm_proof: Optional[dict] = None  # Contains LLM provenance for each step


class WizardState(BaseModel):
    """
    Wizard state schema for Slice 1C Draft/Resume.

    This mirrors the frontend WizardPersistedState but is the server-side
    source of truth.

    Slice 1D-A: Added user_did_skip_clarify for BlueprintInput assembly.
    Slice 1D-B: Added BLUEPRINT_READY as valid step for publish validation.
    """
    # Schema metadata
    schema_version: int = Field(default=1, description="Schema version for migrations")

    # Current step in wizard flow
    # Slice 1D-B: 'blueprint_ready' is the server-side canonical step for publish validation
    step: Literal[
        'goal', 'analyzing', 'clarify', 'generating', 'blueprint_preview', 'blueprint_ready', 'complete'
    ] = Field(default='goal')

    # Goal input
    goal_text: str = Field(default="", description="Natural language goal")

    # Goal analysis results (with LLM provenance)
    goal_analysis_result: Optional[WizardGoalAnalysisResult] = None
    goal_analysis_job_id: Optional[str] = None

    # Clarification answers
    clarification_answers: dict = Field(default_factory=dict)

    # Slice 1D-A: Track if user skipped clarification step
    user_did_skip_clarify: bool = Field(default=False, description="True if user skipped clarification")

    # Blueprint draft
    blueprint_draft: Optional[dict] = None
    blueprint_job_id: Optional[str] = None

    # Timestamps
    last_saved_at: str = Field(default="", description="ISO timestamp of last save")


class WizardStatePatch(BaseModel):
    """
    PATCH request for wizard state updates with optimistic concurrency.

    Client must provide expected_version to prevent overwrites from stale clients.
    Server returns 409 Conflict if version mismatch.
    """
    wizard_state: WizardState
    expected_version: int = Field(
        ...,
        ge=0,
        description="Expected current version (for optimistic concurrency)"
    )


class WizardStateResponse(BaseModel):
    """Response containing wizard state with version."""
    wizard_state: Optional[WizardState] = None
    wizard_state_version: int = 0
    status: str = "ACTIVE"


class ProjectStatusUpdate(BaseModel):
    """Request to promote draft to active or archive a project."""
    status: Literal['DRAFT', 'ACTIVE', 'ARCHIVED']


class ProjectSpecResponse(BaseModel):
    """Project spec response per project.md §6.1, temporal.md §4."""
    id: str  # Changed from project_id to match frontend interface
    tenant_id: str
    name: str
    description: Optional[str]
    domain: str

    # Data refs
    dataset_refs: List[str]
    persona_set_ref: Optional[str]
    event_script_ref: Optional[str]
    ruleset_ref: Optional[str]

    # Temporal Knowledge Isolation (temporal.md §4)
    temporal_context: Optional[TemporalContextResponse] = None

    # Slice 1C: Draft / Resume
    status: str = Field(default="ACTIVE", description="Project status: DRAFT, ACTIVE, ARCHIVED")
    wizard_state_version: int = Field(default=0, description="Optimistic concurrency version")

    # Slice 1D-B: Published timestamp
    published_at: Optional[str] = Field(default=None, description="ISO timestamp when DRAFT was promoted to ACTIVE")

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
    temporal_mode: Optional[str] = Query(None, pattern="^(live|backtest)$"),
    project_status: Optional[str] = Query(
        None,
        pattern="^(DRAFT|ACTIVE|ARCHIVED)$",
        description="Filter by project status (Slice 1C)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> List[ProjectSpecResponse]:
    """
    List all project specs for the current tenant.

    Projects are the top-level container for simulations.
    They hold references to datasets, personas, and event scripts.

    Optionally filter by temporal_mode ('live' or 'backtest').
    Optionally filter by project_status ('DRAFT', 'ACTIVE', 'ARCHIVED') per Slice 1C.
    """
    import json
    # Query project_specs table
    from sqlalchemy import text

    # Build dynamic query to avoid parameter type issues with NULL values
    # PostgreSQL asyncpg can't infer types for NULL parameters
    where_clauses = ["tenant_id = :tenant_id"]
    params = {
        "tenant_id": str(tenant_ctx.tenant_id),
        "skip": skip,
        "limit": limit,
    }

    if domain:
        where_clauses.append("domain_template = :domain")
        params["domain"] = domain

    if search:
        where_clauses.append("title ILIKE :search_pattern")
        params["search_pattern"] = f"%{search}%"

    if temporal_mode:
        where_clauses.append("temporal_mode = :temporal_mode")
        params["temporal_mode"] = temporal_mode

    # Slice 1C: Filter by project status
    if project_status:
        where_clauses.append("status = :project_status")
        params["project_status"] = project_status

    query = text(f"""
        SELECT
            id, tenant_id, title, goal_nl, description, domain_template,
            prediction_core, default_horizon, default_output_metrics,
            privacy_level, policy_flags, has_baseline,
            temporal_mode, as_of_datetime, temporal_timezone,
            isolation_level, allowed_sources, temporal_policy_version,
            temporal_lock_status,
            status, wizard_state_version, published_at,
            created_at, updated_at
        FROM project_specs
        WHERE {" AND ".join(where_clauses)}
        ORDER BY updated_at DESC
        OFFSET :skip LIMIT :limit
    """)

    result = await db.execute(query, params)

    rows = result.fetchall()

    # Map spec-compliant columns to response model
    responses = []
    for row in rows:
        # Parse allowed_sources if present
        allowed_sources_parsed = None
        if row.allowed_sources:
            if isinstance(row.allowed_sources, str):
                allowed_sources_parsed = json.loads(row.allowed_sources)
            else:
                allowed_sources_parsed = row.allowed_sources

        # Build temporal context response
        temporal_context_response = TemporalContextResponse(
            mode=row.temporal_mode or "live",
            as_of_datetime=row.as_of_datetime.isoformat() if row.as_of_datetime else None,
            timezone=row.temporal_timezone or "Asia/Kuala_Lumpur",
            isolation_level=row.isolation_level or 1,
            allowed_sources=allowed_sources_parsed,
            policy_version=row.temporal_policy_version or "1.0.0",
            lock_status=row.temporal_lock_status or "unlocked",
        )

        responses.append(ProjectSpecResponse(
            id=str(row.id),
            tenant_id=str(row.tenant_id),
            name=row.title,
            description=row.description,
            domain=row.domain_template,
            dataset_refs=[],  # Not stored in spec schema - derived from data sources
            persona_set_ref=None,  # Not stored in spec schema
            event_script_ref=None,  # Not stored in spec schema
            ruleset_ref=None,  # Not stored in spec schema
            temporal_context=temporal_context_response,
            # Slice 1C: Draft / Resume fields
            status=row.status or "ACTIVE",
            wizard_state_version=row.wizard_state_version or 0,
            # Slice 1D-B: Published timestamp
            published_at=row.published_at.isoformat() if row.published_at else None,
            schema_version="1.0.0",  # Default version
            project_version="1.0.0",  # Not stored in spec schema
            settings={
                "default_horizon": row.default_horizon,
                "output_metrics": row.default_output_metrics or {},
                "prediction_core": row.prediction_core,
                "privacy_level": row.privacy_level,
                "has_baseline": row.has_baseline,
            },
            created_at=row.created_at.isoformat() if row.created_at else "",
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
        ))

    return responses


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
    import json
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

    # Extract temporal context (default to live mode if not provided)
    temporal_mode = "live"
    as_of_datetime_val = None
    temporal_timezone = "Asia/Kuala_Lumpur"
    isolation_level = 1  # Default for live mode
    allowed_sources_val = None
    temporal_policy_version = "1.0.0"
    temporal_lock_status = "unlocked"  # Live mode doesn't need locking
    temporal_lock_history = None

    if request.temporal_context:
        tc = request.temporal_context
        temporal_mode = tc.mode

        if tc.mode == "backtest":
            # Backtest mode requires locking and has stricter defaults
            as_of_datetime_val = tc.as_of_datetime
            temporal_timezone = tc.timezone
            isolation_level = tc.isolation_level
            allowed_sources_val = tc.allowed_sources
            temporal_lock_status = "locked"  # Lock immediately for backtest
            temporal_lock_history = [{
                "action": "locked",
                "timestamp": now.isoformat(),
                "user_id": str(current_user.id),
                "reason": "Project created in backtest mode"
            }]
        else:
            # Live mode uses provided values or defaults
            temporal_timezone = tc.timezone
            isolation_level = tc.isolation_level
            allowed_sources_val = tc.allowed_sources

    # Insert project spec (using spec-compliant schema from migration)
    # Includes temporal fields per temporal.md §4 and Slice 1C fields
    insert_query = text("""
        INSERT INTO project_specs (
            id, tenant_id, owner_id, title, goal_nl, description,
            prediction_core, domain_template, default_horizon,
            default_output_metrics, privacy_level, policy_flags,
            temporal_mode, as_of_datetime, temporal_timezone,
            isolation_level, allowed_sources, temporal_policy_version,
            temporal_lock_status, temporal_lock_history,
            status, wizard_state, wizard_state_version,
            has_baseline, created_at, updated_at
        ) VALUES (
            :id, :tenant_id, :owner_id, :title, :goal_nl, :description,
            :prediction_core, :domain_template, :default_horizon,
            :default_output_metrics, :privacy_level, :policy_flags,
            :temporal_mode, :as_of_datetime, :temporal_timezone,
            :isolation_level, :allowed_sources, :temporal_policy_version,
            :temporal_lock_status, :temporal_lock_history,
            :status, :wizard_state, :wizard_state_version,
            :has_baseline, :created_at, :updated_at
        )
    """)

    await db.execute(
        insert_query,
        {
            "id": project_id,
            "tenant_id": tenant_ctx.tenant_id,
            "owner_id": str(current_user.id),
            "title": request.name,
            "goal_nl": request.description or "",
            "description": request.description,
            "prediction_core": "hybrid",  # Default prediction core
            "domain_template": request.domain,
            "default_horizon": request.settings.get("default_horizon", 100),
            "default_output_metrics": json.dumps(request.settings.get("output_metrics", {})),
            "privacy_level": "private" if request.settings.get("allow_public_templates", True) else "public",
            "policy_flags": json.dumps({}),
            # Temporal Knowledge Isolation fields
            "temporal_mode": temporal_mode,
            "as_of_datetime": as_of_datetime_val,
            "temporal_timezone": temporal_timezone,
            "isolation_level": isolation_level,
            "allowed_sources": json.dumps(allowed_sources_val) if allowed_sources_val else None,
            "temporal_policy_version": temporal_policy_version,
            "temporal_lock_status": temporal_lock_status,
            "temporal_lock_history": json.dumps(temporal_lock_history) if temporal_lock_history else None,
            # Slice 1C: Draft / Resume fields
            "status": request.status,
            "wizard_state": json.dumps(request.wizard_state) if request.wizard_state else None,
            "wizard_state_version": 0,
            "has_baseline": False,
            "created_at": now,
            "updated_at": now,
        },
    )

    await db.commit()

    # Build temporal context response
    temporal_context_response = TemporalContextResponse(
        mode=temporal_mode,
        as_of_datetime=as_of_datetime_val,
        timezone=temporal_timezone,
        isolation_level=isolation_level,
        allowed_sources=allowed_sources_val,
        policy_version=temporal_policy_version,
        lock_status=temporal_lock_status,
    )

    return ProjectSpecResponse(
        id=str(project_id),
        tenant_id=str(tenant_ctx.tenant_id),
        name=request.name,
        description=request.description,
        domain=request.domain,
        dataset_refs=request.dataset_refs,
        persona_set_ref=persona_set_ref,
        event_script_ref=event_script_ref,
        ruleset_ref=ruleset_ref,
        temporal_context=temporal_context_response,
        # Slice 1C: Draft / Resume fields
        status=request.status,
        wizard_state_version=0,
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
    import json
    from sqlalchemy import text

    # Query using spec-compliant schema columns including temporal, Slice 1C, and Slice 1D-B fields
    query = text("""
        SELECT
            id, tenant_id, title, goal_nl, description, domain_template,
            prediction_core, default_horizon, default_output_metrics,
            privacy_level, policy_flags, has_baseline,
            temporal_mode, as_of_datetime, temporal_timezone,
            isolation_level, allowed_sources, temporal_policy_version,
            temporal_lock_status,
            status, wizard_state_version, published_at,
            created_at, updated_at
        FROM project_specs
        WHERE id = :project_id AND tenant_id = :tenant_id
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

    # Build temporal context response
    allowed_sources_parsed = None
    if row.allowed_sources:
        if isinstance(row.allowed_sources, str):
            allowed_sources_parsed = json.loads(row.allowed_sources)
        else:
            allowed_sources_parsed = row.allowed_sources

    temporal_context_response = TemporalContextResponse(
        mode=row.temporal_mode or "live",
        as_of_datetime=row.as_of_datetime.isoformat() if row.as_of_datetime else None,
        timezone=row.temporal_timezone or "Asia/Kuala_Lumpur",
        isolation_level=row.isolation_level or 1,
        allowed_sources=allowed_sources_parsed,
        policy_version=row.temporal_policy_version or "1.0.0",
        lock_status=row.temporal_lock_status or "unlocked",
    )

    # Map spec-compliant columns to response model
    return ProjectSpecResponse(
        id=str(row.id),
        tenant_id=str(row.tenant_id),
        name=row.title,
        description=row.description,
        domain=row.domain_template,
        dataset_refs=[],  # Not stored in spec schema
        persona_set_ref=None,
        event_script_ref=None,
        ruleset_ref=None,
        temporal_context=temporal_context_response,
        # Slice 1C: Draft / Resume fields
        status=row.status or "ACTIVE",
        wizard_state_version=row.wizard_state_version or 0,
        # Slice 1D-B: Published timestamp
        published_at=row.published_at.isoformat() if row.published_at else None,
        schema_version="1.0.0",
        project_version="1.0.0",
        settings={
            "default_horizon": row.default_horizon,
            "output_metrics": row.default_output_metrics or {},
            "prediction_core": row.prediction_core,
            "privacy_level": row.privacy_level,
            "has_baseline": row.has_baseline,
        },
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

    Updates the spec and sets updated_at timestamp.
    """
    import json
    from datetime import datetime
    from sqlalchemy import text

    # First check if project exists (using spec-compliant schema)
    check_query = text("""
        SELECT id FROM project_specs
        WHERE id = :project_id AND tenant_id = :tenant_id
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

    # Build update fields using spec-compliant column names
    update_fields = []
    params = {
        "project_id": project_id,
        "tenant_id": tenant_ctx.tenant_id,
        "updated_at": datetime.utcnow(),
    }

    if request.name is not None:
        update_fields.append("title = :title")
        params["title"] = request.name

    if request.description is not None:
        update_fields.append("description = :description")
        update_fields.append("goal_nl = :goal_nl")
        params["description"] = request.description
        params["goal_nl"] = request.description

    if request.domain is not None:
        update_fields.append("domain_template = :domain_template")
        params["domain_template"] = request.domain

    if request.settings is not None:
        if "default_horizon" in request.settings:
            update_fields.append("default_horizon = :default_horizon")
            params["default_horizon"] = request.settings["default_horizon"]
        if "output_metrics" in request.settings:
            update_fields.append("default_output_metrics = :default_output_metrics")
            params["default_output_metrics"] = json.dumps(request.settings["output_metrics"])
        if "prediction_core" in request.settings:
            update_fields.append("prediction_core = :prediction_core")
            params["prediction_core"] = request.settings["prediction_core"]

    update_fields.append("updated_at = :updated_at")

    update_query = text(f"""
        UPDATE project_specs
        SET {', '.join(update_fields)}
        WHERE id = :project_id AND tenant_id = :tenant_id
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

    # First check if project exists (using spec-compliant schema)
    check_query = text("""
        SELECT id FROM project_specs
        WHERE id = :project_id AND tenant_id = :tenant_id
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
        WHERE id = :project_id AND tenant_id = :tenant_id
    """)

    await db.execute(
        delete_query,
        {"project_id": project_id, "tenant_id": tenant_ctx.tenant_id},
    )

    await db.commit()

    return {"message": f"Project {project_id} deleted successfully"}


# ============================================================================
# Slice 1C: Draft / Resume Endpoints
# ============================================================================


@router.get(
    "/{project_id}/wizard-state",
    response_model=WizardStateResponse,
    summary="Get wizard state for a project (Slice 1C)",
)
async def get_wizard_state(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> WizardStateResponse:
    """
    Get the wizard state for a DRAFT project.

    Returns the current wizard state including step, goal_text, goal_analysis_result,
    clarification_answers, and blueprint_draft.

    Used by the frontend to resume wizard progress after page refresh or navigation.
    """
    import json
    from sqlalchemy import text

    query = text("""
        SELECT status, wizard_state, wizard_state_version
        FROM project_specs
        WHERE id = :project_id AND tenant_id = :tenant_id
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

    # Parse wizard_state if present
    wizard_state_data = None
    if row.wizard_state:
        ws = row.wizard_state
        if isinstance(ws, str):
            ws = json.loads(ws)
        wizard_state_data = WizardState(**ws)

    return WizardStateResponse(
        wizard_state=wizard_state_data,
        wizard_state_version=row.wizard_state_version or 0,
        status=row.status or "ACTIVE",
    )


@router.patch(
    "/{project_id}/wizard-state",
    response_model=WizardStateResponse,
    summary="Update wizard state with optimistic concurrency (Slice 1C)",
)
async def patch_wizard_state(
    project_id: str,
    request: WizardStatePatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> WizardStateResponse:
    """
    Update the wizard state for a DRAFT project with optimistic concurrency.

    The client must provide the expected_version. If the server's current version
    doesn't match, a 409 Conflict is returned to prevent overwrites from stale clients.

    On success, the server increments wizard_state_version and returns the new version.

    This endpoint is used for autosave during wizard flow.
    """
    import json
    from datetime import datetime
    from sqlalchemy import text

    # Get current version
    check_query = text("""
        SELECT status, wizard_state_version
        FROM project_specs
        WHERE id = :project_id AND tenant_id = :tenant_id
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

    current_version = row.wizard_state_version or 0

    # Optimistic concurrency check
    if request.expected_version != current_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version mismatch. Expected {request.expected_version}, but server has {current_version}. Fetch latest state and retry.",
        )

    # Compute new version
    new_version = current_version + 1

    # Update wizard state and timestamp
    now = datetime.utcnow()
    wizard_state_dict = request.wizard_state.model_dump()
    wizard_state_dict["last_saved_at"] = now.isoformat()

    update_query = text("""
        UPDATE project_specs
        SET wizard_state = :wizard_state,
            wizard_state_version = :new_version,
            updated_at = :updated_at
        WHERE id = :project_id AND tenant_id = :tenant_id
    """)

    await db.execute(
        update_query,
        {
            "project_id": project_id,
            "tenant_id": tenant_ctx.tenant_id,
            "wizard_state": json.dumps(wizard_state_dict),
            "new_version": new_version,
            "updated_at": now,
        },
    )

    await db.commit()

    return WizardStateResponse(
        wizard_state=WizardState(**wizard_state_dict),
        wizard_state_version=new_version,
        status=row.status or "ACTIVE",
    )


@router.patch(
    "/{project_id}/status",
    response_model=ProjectSpecResponse,
    summary="Update project status (Slice 1C)",
)
async def patch_project_status(
    project_id: str,
    request: ProjectStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ProjectSpecResponse:
    """
    Update project status (DRAFT -> ACTIVE or ACTIVE -> ARCHIVED).

    Used to:
    - Promote a DRAFT project to ACTIVE when wizard completes
    - Archive a project (soft delete)

    When promoting DRAFT to ACTIVE, the wizard_state is preserved for reference
    but the project is considered complete.
    """
    from datetime import datetime
    from sqlalchemy import text

    # Check project exists
    check_query = text("""
        SELECT id, status FROM project_specs
        WHERE id = :project_id AND tenant_id = :tenant_id
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

    # Validate status transitions
    current_status = row.status or "ACTIVE"
    new_status = request.status

    # Allowed transitions:
    # DRAFT -> ACTIVE (wizard complete)
    # DRAFT -> ARCHIVED (cancel wizard)
    # ACTIVE -> ARCHIVED (archive project)
    # ARCHIVED -> ACTIVE (restore project)
    valid_transitions = {
        ("DRAFT", "ACTIVE"),
        ("DRAFT", "ARCHIVED"),
        ("ACTIVE", "ARCHIVED"),
        ("ARCHIVED", "ACTIVE"),
    }

    if current_status == new_status:
        # No change needed, return current state
        return await get_project_spec(project_id, db, current_user, tenant_ctx)

    if (current_status, new_status) not in valid_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition: {current_status} -> {new_status}",
        )

    # Update status
    now = datetime.utcnow()
    update_query = text("""
        UPDATE project_specs
        SET status = :status, updated_at = :updated_at
        WHERE id = :project_id AND tenant_id = :tenant_id
    """)

    await db.execute(
        update_query,
        {
            "project_id": project_id,
            "tenant_id": tenant_ctx.tenant_id,
            "status": new_status,
            "updated_at": now,
        },
    )

    await db.commit()

    return await get_project_spec(project_id, db, current_user, tenant_ctx)


# =============================================================================
# Slice 1D-B: Publish Endpoint
# =============================================================================

class PublishResponse(BaseModel):
    """Response from publishing a draft project."""
    id: str
    status: str
    published_at: str
    message: str


@router.post(
    "/{project_id}/publish",
    response_model=PublishResponse,
    summary="Publish a draft project (Slice 1D-B)",
    responses={
        200: {"description": "Project successfully published"},
        400: {"description": "Invalid state for publishing"},
        404: {"description": "Project not found"},
    },
)
async def publish_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> PublishResponse:
    """
    Publish a DRAFT project to make it ACTIVE.

    Slice 1D-B: This endpoint validates that:
    1. Project status is DRAFT
    2. wizard_state.step is 'blueprint_preview' or 'blueprint_ready'

    On success:
    - Sets status = 'ACTIVE'
    - Sets published_at = current timestamp
    - Sets wizard_state.step = 'complete'

    Returns 400 if validation fails (wrong status or wizard step).
    """
    from datetime import datetime
    from sqlalchemy import text
    import json

    # Check project exists and get current state
    check_query = text("""
        SELECT id, status, wizard_state FROM project_specs
        WHERE id = :project_id AND tenant_id = :tenant_id
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

    current_status = row.status or "ACTIVE"

    # Validate status is DRAFT
    if current_status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish: project status is '{current_status}', expected 'DRAFT'",
        )

    # Validate wizard_state.step is blueprint_preview or blueprint_ready
    wizard_state = row.wizard_state
    if not wizard_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish: wizard_state is missing",
        )

    # Parse wizard_state if it's a string
    if isinstance(wizard_state, str):
        wizard_state = json.loads(wizard_state)

    current_step = wizard_state.get("step", "goal")

    # Allow publish from blueprint_preview or blueprint_ready
    valid_steps = ("blueprint_preview", "blueprint_ready")
    if current_step not in valid_steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish: wizard step is '{current_step}', expected one of {valid_steps}",
        )

    # Update to ACTIVE with published_at and set wizard step to complete
    now = datetime.utcnow()

    # Update wizard_state.step to 'complete'
    wizard_state["step"] = "complete"

    update_query = text("""
        UPDATE project_specs
        SET status = 'ACTIVE',
            published_at = :published_at,
            wizard_state = :wizard_state,
            updated_at = :updated_at
        WHERE id = :project_id AND tenant_id = :tenant_id
    """)

    await db.execute(
        update_query,
        {
            "project_id": project_id,
            "tenant_id": tenant_ctx.tenant_id,
            "published_at": now,
            "wizard_state": json.dumps(wizard_state),
            "updated_at": now,
        },
    )

    await db.commit()

    # Slice 2C: Trigger PROJECT_GENESIS job to generate project-specific guidance
    # This is done after publish to avoid generating guidance for unpublished projects
    try:
        from app.models.pil_job import PILJob, PILJobStatus, PILJobType, PILJobPriority
        from app.tasks.pil_tasks import dispatch_pil_job
        from uuid import UUID as UUIDType

        # Get the blueprint for this project
        blueprint_query = text("""
            SELECT id, version FROM blueprint_v2
            WHERE project_id = :project_id AND is_active = true
            ORDER BY version DESC LIMIT 1
        """)
        blueprint_result = await db.execute(
            blueprint_query,
            {"project_id": project_id},
        )
        blueprint_row = blueprint_result.fetchone()

        if blueprint_row:
            # Create PROJECT_GENESIS job
            genesis_job = PILJob(
                tenant_id=UUIDType(str(tenant_ctx.tenant_id)),
                project_id=UUIDType(project_id),
                blueprint_id=blueprint_row.id,
                job_type=PILJobType.PROJECT_GENESIS.value,
                job_name=f"Project Genesis (auto-triggered on publish)",
                status=PILJobStatus.QUEUED.value,
                priority=PILJobPriority.HIGH.value,
                input_params={
                    "project_id": project_id,
                    "blueprint_id": str(blueprint_row.id),
                    "blueprint_version": blueprint_row.version,
                    "trigger": "publish",
                },
            )
            db.add(genesis_job)
            await db.commit()
            await db.refresh(genesis_job)

            # Dispatch to Celery worker
            dispatch_pil_job.delay(str(genesis_job.id))
    except Exception as e:
        # Log but don't fail the publish - genesis can be triggered manually
        import logging
        logging.getLogger(__name__).warning(f"Failed to trigger PROJECT_GENESIS on publish: {e}")

    return PublishResponse(
        id=project_id,
        status="ACTIVE",
        published_at=now.isoformat(),
        message="Project published successfully",
    )


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

    # Check project exists (using spec-compliant schema)
    check_query = text("""
        SELECT id FROM project_specs
        WHERE id = :project_id AND tenant_id = :tenant_id
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
    # Note: agents_processed and ticks_completed are stored in outputs JSONB
    run_query = text("""
        SELECT
            COUNT(*) as run_count,
            COUNT(*) FILTER (WHERE status = 'completed') as completed_runs,
            COALESCE(SUM((outputs->>'total_agents')::int), 0) as total_agents,
            COALESCE(SUM((outputs->>'total_ticks')::int), 0) as total_ticks
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
    import json
    import uuid
    from datetime import datetime
    from sqlalchemy import text

    # Get original project (using spec-compliant schema)
    original_query = text("""
        SELECT
            title, goal_nl, description, domain_template,
            prediction_core, default_horizon, default_output_metrics,
            privacy_level, policy_flags
        FROM project_specs
        WHERE id = :project_id AND tenant_id = :tenant_id
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

    # Insert duplicate (using spec-compliant schema)
    insert_query = text("""
        INSERT INTO project_specs (
            id, tenant_id, owner_id, title, goal_nl, description,
            prediction_core, domain_template, default_horizon,
            default_output_metrics, privacy_level, policy_flags,
            has_baseline, created_at, updated_at
        ) VALUES (
            :id, :tenant_id, :owner_id, :title, :goal_nl, :description,
            :prediction_core, :domain_template, :default_horizon,
            :default_output_metrics, :privacy_level, :policy_flags,
            :has_baseline, :created_at, :updated_at
        )
    """)

    await db.execute(
        insert_query,
        {
            "id": new_project_id,
            "tenant_id": tenant_ctx.tenant_id,
            "owner_id": str(current_user.id),
            "title": new_name or f"{original.title} (Copy)",
            "goal_nl": original.goal_nl,
            "description": original.description,
            "prediction_core": original.prediction_core,
            "domain_template": original.domain_template,
            "default_horizon": original.default_horizon,
            "default_output_metrics": json.dumps(original.default_output_metrics or {}),
            "privacy_level": original.privacy_level,
            "policy_flags": json.dumps(original.policy_flags or {}),
            "has_baseline": False,  # New project starts without baseline
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

    # Verify project exists (using spec-compliant schema)
    from sqlalchemy import text

    check_query = text("""
        SELECT id FROM project_specs
        WHERE id = :project_id AND tenant_id = :tenant_id
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
        tenant_id=str(tenant_ctx.tenant_id),
    )

    try:
        if auto_start:
            run, node, task_id = await orchestrator.create_and_start_run(run_input)
        else:
            run, node = await orchestrator.create_run(run_input)
            task_id = None

        await db.commit()

        return {
            "run_id": str(run.id),
            "node_id": str(run.node_id),
            "project_id": str(run.project_id),
            "status": run.status,
            "task_id": task_id,
        }
    except Exception as e:
        await db.rollback()
        import traceback
        print(f"ERROR creating run: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create run: {str(e)}",
        )


# ============================================================================
# STEP 2: ProjectSnapshot API (Aggregated Project Overview)
# ============================================================================

class BaselineNodeSummary(BaseModel):
    """Summary of baseline node for ProjectSnapshot."""
    node_id: str
    label: Optional[str]
    is_baseline: bool
    has_outcome: bool
    created_at: str


class BaselineRunSummary(BaseModel):
    """Summary of baseline run for ProjectSnapshot."""
    run_id: str
    status: str
    ticks_executed: Optional[int]
    seed: Optional[int]
    worker_id: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]


class OutcomeSummary(BaseModel):
    """Summary of baseline outcome for ProjectSnapshot."""
    primary_outcome: str
    primary_outcome_probability: float
    key_metrics: List[dict]
    summary_text: Optional[str]


class ReliabilitySummary(BaseModel):
    """Reliability summary for ProjectSnapshot."""
    confidence_level: str
    confidence_score: float
    run_count: int


class ProjectSnapshotResponse(BaseModel):
    """
    STEP 2: ProjectSnapshot - Single backend aggregation endpoint.

    Provides truthful project overview including:
    - Baseline node summary
    - Baseline run summary (with status=SUCCEEDED verification)
    - Outcome summary (real numeric values)
    - Reliability summary

    UI should ONLY show "Baseline Complete" if:
    - baseline_node exists AND
    - baseline_run exists AND baseline_run.status == "succeeded" AND
    - outcome exists
    """
    project_id: str
    project_name: str
    has_baseline: bool
    baseline_complete: bool  # True ONLY if node + run + outcome all exist

    # Baseline data (null if no baseline)
    baseline_node: Optional[BaselineNodeSummary]
    baseline_run: Optional[BaselineRunSummary]
    outcome: Optional[OutcomeSummary]
    reliability: Optional[ReliabilitySummary]

    # Latest node (may differ from baseline)
    latest_node: Optional[BaselineNodeSummary]

    # Stats
    total_nodes: int
    total_runs: int
    total_completed_runs: int

    # Timestamps
    created_at: str
    updated_at: str


@router.get(
    "/{project_id}/snapshot",
    response_model=ProjectSnapshotResponse,
    summary="Get project snapshot (STEP 2: Aggregated overview)",
)
async def get_project_snapshot(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ProjectSnapshotResponse:
    """
    STEP 2: ProjectSnapshot API - Single backend aggregation endpoint.

    Returns a complete snapshot of the project state including:
    - Baseline node (if exists)
    - Baseline run (if exists, with status)
    - Outcome data (real numeric values)
    - Reliability metrics

    The `baseline_complete` field is TRUE only when ALL of:
    - Baseline node exists
    - Baseline run exists with status=succeeded
    - Outcome data exists

    This replaces frontend logic assembly for truthful project overview.
    """
    from sqlalchemy import text
    import json

    # 1. Load project
    project_query = text("""
        SELECT id, title, has_baseline, root_node_id, created_at, updated_at
        FROM project_specs
        WHERE id = :project_id AND tenant_id = :tenant_id
    """)
    project_result = await db.execute(
        project_query,
        {"project_id": project_id, "tenant_id": tenant_ctx.tenant_id}
    )
    project = project_result.fetchone()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # 2. Load baseline node (is_baseline=true)
    baseline_node_query = text("""
        SELECT id, label, is_baseline, aggregated_outcome, confidence, created_at
        FROM nodes
        WHERE project_id = :project_id AND tenant_id = :tenant_id AND is_baseline = true
        LIMIT 1
    """)
    baseline_node_result = await db.execute(
        baseline_node_query,
        {"project_id": project_id, "tenant_id": tenant_ctx.tenant_id}
    )
    baseline_node_row = baseline_node_result.fetchone()

    baseline_node = None
    outcome = None
    reliability = None

    if baseline_node_row:
        has_outcome = baseline_node_row.aggregated_outcome is not None
        baseline_node = BaselineNodeSummary(
            node_id=str(baseline_node_row.id),
            label=baseline_node_row.label,
            is_baseline=baseline_node_row.is_baseline,
            has_outcome=has_outcome,
            created_at=baseline_node_row.created_at.isoformat() if baseline_node_row.created_at else "",
        )

        # Extract outcome if exists
        if has_outcome:
            outcome_data = baseline_node_row.aggregated_outcome
            if isinstance(outcome_data, str):
                outcome_data = json.loads(outcome_data)

            outcome = OutcomeSummary(
                primary_outcome=outcome_data.get("primary_outcome", "unknown"),
                primary_outcome_probability=outcome_data.get("primary_outcome_probability", 0.0),
                key_metrics=outcome_data.get("key_metrics", []),
                summary_text=outcome_data.get("summary_text"),
            )

        # Extract reliability from node confidence
        if baseline_node_row.confidence:
            confidence_data = baseline_node_row.confidence
            if isinstance(confidence_data, str):
                confidence_data = json.loads(confidence_data)

            reliability = ReliabilitySummary(
                confidence_level=confidence_data.get("level", "medium"),
                confidence_score=confidence_data.get("score", 0.5),
                run_count=confidence_data.get("factors", {}).get("run_count", 0),
            )

    # 3. Load baseline run (run associated with baseline node)
    baseline_run = None
    if baseline_node:
        run_query = text("""
            SELECT id, status, timing, actual_seed, worker_id
            FROM runs
            WHERE node_id = :node_id AND tenant_id = :tenant_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        run_result = await db.execute(
            run_query,
            {"node_id": baseline_node.node_id, "tenant_id": tenant_ctx.tenant_id}
        )
        run_row = run_result.fetchone()

        if run_row:
            timing = run_row.timing or {}
            if isinstance(timing, str):
                timing = json.loads(timing)

            baseline_run = BaselineRunSummary(
                run_id=str(run_row.id),
                status=run_row.status,
                ticks_executed=timing.get("ticks_executed"),
                seed=run_row.actual_seed,
                worker_id=run_row.worker_id,
                started_at=timing.get("started_at"),
                completed_at=timing.get("completed_at"),
            )

    # 4. Load latest node (most recently updated)
    latest_node_query = text("""
        SELECT id, label, is_baseline, aggregated_outcome, created_at
        FROM nodes
        WHERE project_id = :project_id AND tenant_id = :tenant_id
        ORDER BY updated_at DESC
        LIMIT 1
    """)
    latest_node_result = await db.execute(
        latest_node_query,
        {"project_id": project_id, "tenant_id": tenant_ctx.tenant_id}
    )
    latest_node_row = latest_node_result.fetchone()

    latest_node = None
    if latest_node_row:
        latest_node = BaselineNodeSummary(
            node_id=str(latest_node_row.id),
            label=latest_node_row.label,
            is_baseline=latest_node_row.is_baseline,
            has_outcome=latest_node_row.aggregated_outcome is not None,
            created_at=latest_node_row.created_at.isoformat() if latest_node_row.created_at else "",
        )

    # 5. Load stats
    stats_query = text("""
        SELECT
            (SELECT COUNT(*) FROM nodes WHERE project_id = :project_id AND tenant_id = :tenant_id) as total_nodes,
            (SELECT COUNT(*) FROM runs WHERE project_id = :project_id AND tenant_id = :tenant_id) as total_runs,
            (SELECT COUNT(*) FROM runs WHERE project_id = :project_id AND tenant_id = :tenant_id AND status = 'succeeded') as completed_runs
    """)
    stats_result = await db.execute(
        stats_query,
        {"project_id": project_id, "tenant_id": tenant_ctx.tenant_id}
    )
    stats = stats_result.fetchone()

    # 6. Compute baseline_complete flag (STEP 2 requirement)
    # TRUE only if ALL conditions are met:
    # - baseline_node exists
    # - baseline_run exists with status=succeeded
    # - outcome exists (aggregated_outcome is not null)
    baseline_complete = (
        baseline_node is not None and
        baseline_run is not None and
        baseline_run.status == "succeeded" and
        outcome is not None
    )

    return ProjectSnapshotResponse(
        project_id=str(project.id),
        project_name=project.title,
        has_baseline=project.has_baseline,
        baseline_complete=baseline_complete,
        baseline_node=baseline_node,
        baseline_run=baseline_run,
        outcome=outcome,
        reliability=reliability,
        latest_node=latest_node,
        total_nodes=stats.total_nodes if stats else 0,
        total_runs=stats.total_runs if stats else 0,
        total_completed_runs=stats.completed_runs if stats else 0,
        created_at=project.created_at.isoformat() if project.created_at else "",
        updated_at=project.updated_at.isoformat() if project.updated_at else "",
    )


@router.get(
    "/{project_id}/snapshot/download",
    summary="Download project snapshot as JSON file (STEP 2)",
)
async def download_project_snapshot(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> Response:
    """
    STEP 2: Download Project Snapshot as JSON file.

    Returns the same data as GET /snapshot but as a downloadable file
    with proper Content-Disposition header for browser download.

    Use this endpoint for:
    - Archiving project state
    - Sharing snapshot with team members
    - Evidence preservation for audits
    """
    import json

    # Get the snapshot data
    snapshot = await get_project_snapshot(project_id, db, current_user, tenant_ctx)

    # Convert to JSON with proper formatting
    json_content = json.dumps(snapshot.model_dump(), indent=2, default=str)

    # Generate filename
    safe_name = snapshot.project_name.replace(" ", "_").replace("/", "-")[:50]
    filename = f"snapshot_{safe_name}_{project_id[:8]}.json"

    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Snapshot-Project-Id": project_id,
            "X-Snapshot-Baseline-Complete": str(snapshot.baseline_complete).lower(),
        },
    )
