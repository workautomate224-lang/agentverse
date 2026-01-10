"""
Event Script API Endpoints
Reference: project.md §6.4, §11 Phase 3

Provides endpoints for:
- CRUD operations on event scripts
- Event bundle management
- Event execution (manual trigger)
- Event trigger logs/telemetry

Key constraints:
- C5: Events are pre-compiled from NL, executed without LLM at runtime
- C4: All events are versioned and auditable
- C6: Multi-tenant aware
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.middleware.tenant import (
    TenantContext,
    require_tenant,
    require_permission,
    get_current_tenant_id,
)
from app.models.user import User
from app.models.event_script import (
    EventScript,
    EventBundle,
    EventBundleMember,
    EventTriggerLog,
    EventType as EventTypeEnum,
)
from app.schemas.event_script import (
    EventScriptCreate,
    EventScriptUpdate,
    EventScriptResponse,
    EventScriptListResponse,
    EventBundleCreate,
    EventBundleUpdate,
    EventBundleResponse,
    EventTriggerLogCreate,
    EventTriggerLogResponse,
    EventTriggerLogListResponse,
    EventExecutionRequest,
    EventExecutionResult,
    BundleExecutionRequest,
    BundleExecutionResult,
    DeltasSchema,
)
from app.engine.event_executor import (
    get_event_executor,
    create_event_from_dict,
    ExecutionContext,
)


router = APIRouter(prefix="/event-scripts", tags=["event-scripts"])


# ============================================================================
# Helper Functions
# ============================================================================

def event_to_response(event: EventScript) -> EventScriptResponse:
    """Convert EventScript model to response schema."""
    return EventScriptResponse(
        event_id=event.id,
        project_id=event.project_id,
        event_type=event.event_type,
        label=event.label,
        description=event.description,
        scope=event.scope,
        deltas=event.deltas,
        intensity_profile=event.intensity_profile,
        uncertainty=event.uncertainty,
        provenance=event.provenance,
        event_version=event.event_version,
        schema_version=event.schema_version,
        is_active=event.is_active,
        is_validated=event.is_validated,
        tags=event.tags,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def event_to_list_response(event: EventScript) -> EventScriptListResponse:
    """Convert EventScript model to list response schema."""
    return EventScriptListResponse(
        event_id=event.id,
        project_id=event.project_id,
        event_type=event.event_type,
        label=event.label,
        is_active=event.is_active,
        is_validated=event.is_validated,
        tags=event.tags,
        created_at=event.created_at,
    )


def bundle_to_response(bundle: EventBundle) -> EventBundleResponse:
    """Convert EventBundle model to response schema."""
    event_ids = [member.event_script_id for member in bundle.members]
    return EventBundleResponse(
        bundle_id=bundle.id,
        project_id=bundle.project_id,
        label=bundle.label,
        description=bundle.description,
        event_ids=event_ids,
        execution_order=bundle.execution_order,
        joint_probability=bundle.joint_probability,
        provenance=bundle.provenance,
        is_active=bundle.is_active,
        created_at=bundle.created_at,
        updated_at=bundle.updated_at,
    )


# ============================================================================
# Event Script CRUD Endpoints
# ============================================================================

@router.post(
    "",
    response_model=EventScriptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create event script",
)
async def create_event_script(
    request: EventScriptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    Create a new event script.

    Event scripts are deterministic, executable event definitions that can be
    run without LLM involvement at runtime (C5 compliant).
    """
    # Create the event script
    event = EventScript(
        tenant_id=tenant_id,
        project_id=request.project_id,
        event_type=request.event_type.value,
        label=request.label,
        description=request.description,
        scope=request.scope.model_dump() if request.scope else {},
        deltas=request.deltas.model_dump() if request.deltas else {},
        intensity_profile=request.intensity_profile.model_dump() if request.intensity_profile else {},
        uncertainty=request.uncertainty.model_dump() if request.uncertainty else {},
        provenance=request.provenance.model_dump() if request.provenance else {},
        tags=request.tags,
        event_version="1.0.0",
        schema_version="1.0.0",
        is_active=True,
        is_validated=False,
    )

    db.add(event)
    await db.commit()
    await db.refresh(event)

    return event_to_response(event)


@router.get(
    "",
    response_model=List[EventScriptListResponse],
    summary="List event scripts",
)
async def list_event_scripts(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_validated: Optional[bool] = Query(None, description="Filter by validated status"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags (any match)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """List event scripts with optional filters."""
    query = select(EventScript).where(EventScript.tenant_id == tenant_id)

    if project_id:
        query = query.where(EventScript.project_id == project_id)
    if event_type:
        query = query.where(EventScript.event_type == event_type)
    if is_active is not None:
        query = query.where(EventScript.is_active == is_active)
    if is_validated is not None:
        query = query.where(EventScript.is_validated == is_validated)
    if tags:
        # PostgreSQL ARRAY overlap operator
        query = query.where(EventScript.tags.overlap(tags))

    query = query.order_by(EventScript.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    events = result.scalars().all()

    return [event_to_list_response(e) for e in events]


@router.get(
    "/{event_id}",
    response_model=EventScriptResponse,
    summary="Get event script",
)
async def get_event_script(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get an event script by ID."""
    result = await db.execute(
        select(EventScript).where(
            and_(
                EventScript.id == event_id,
                EventScript.tenant_id == tenant_id,
            )
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event script {event_id} not found",
        )

    return event_to_response(event)


@router.patch(
    "/{event_id}",
    response_model=EventScriptResponse,
    summary="Update event script",
)
async def update_event_script(
    event_id: UUID,
    request: EventScriptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    Update an event script.

    Note: Updating an event creates a new version (P3-004).
    """
    result = await db.execute(
        select(EventScript).where(
            and_(
                EventScript.id == event_id,
                EventScript.tenant_id == tenant_id,
            )
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event script {event_id} not found",
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "event_type" and value:
            setattr(event, field, value.value)
        elif field in ("scope", "deltas", "intensity_profile", "uncertainty", "provenance"):
            if value:
                setattr(event, field, value.model_dump())
        else:
            setattr(event, field, value)

    # Bump version (P3-004)
    parts = event.event_version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    event.event_version = ".".join(parts)

    # Mark provenance as manually edited
    if event.provenance:
        event.provenance["manually_edited"] = True

    await db.commit()
    await db.refresh(event)

    return event_to_response(event)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete event script",
)
async def delete_event_script(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    Delete an event script.

    Note: Soft delete by setting is_active=False is recommended.
    Hard delete removes the event permanently.
    """
    result = await db.execute(
        select(EventScript).where(
            and_(
                EventScript.id == event_id,
                EventScript.tenant_id == tenant_id,
            )
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event script {event_id} not found",
        )

    await db.delete(event)
    await db.commit()


@router.post(
    "/{event_id}/validate",
    response_model=EventScriptResponse,
    summary="Validate event script",
)
async def validate_event_script(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    Validate an event script for execution readiness.

    Checks:
    - Required fields are present
    - Deltas have valid structure
    - Scope is well-formed
    """
    result = await db.execute(
        select(EventScript).where(
            and_(
                EventScript.id == event_id,
                EventScript.tenant_id == tenant_id,
            )
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event script {event_id} not found",
        )

    # Validation checks
    errors = []

    if not event.label:
        errors.append("Label is required")

    deltas = event.deltas or {}
    if not any([
        deltas.get("environment_deltas"),
        deltas.get("perception_deltas"),
        deltas.get("custom_deltas"),
    ]):
        errors.append("At least one delta (environment, perception, or custom) is required")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": errors},
        )

    event.is_validated = True
    await db.commit()
    await db.refresh(event)

    return event_to_response(event)


# ============================================================================
# Event Bundle Endpoints (P3-002)
# ============================================================================

@router.post(
    "/bundles",
    response_model=EventBundleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create event bundle",
)
async def create_event_bundle(
    request: EventBundleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    Create an event bundle (group of related events).

    Bundles allow multiple events from a single natural language question
    to be applied atomically with the scenario patch.
    """
    # Verify all event IDs exist
    result = await db.execute(
        select(EventScript).where(
            and_(
                EventScript.id.in_(request.event_ids),
                EventScript.tenant_id == tenant_id,
            )
        )
    )
    events = result.scalars().all()

    if len(events) != len(request.event_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more event IDs not found",
        )

    # Create bundle
    bundle = EventBundle(
        tenant_id=tenant_id,
        project_id=request.project_id,
        label=request.label,
        description=request.description,
        execution_order=request.execution_order,
        joint_probability=request.joint_probability,
        provenance=request.provenance.model_dump() if request.provenance else {},
        is_active=True,
    )

    db.add(bundle)
    await db.flush()

    # Add members
    for idx, event_id in enumerate(request.event_ids):
        member = EventBundleMember(
            bundle_id=bundle.id,
            event_script_id=event_id,
            order_index=idx,
        )
        db.add(member)

    await db.commit()
    await db.refresh(bundle, ["members"])

    return bundle_to_response(bundle)


@router.get(
    "/bundles",
    response_model=List[EventBundleResponse],
    summary="List event bundles",
)
async def list_event_bundles(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """List event bundles with optional filters."""
    query = (
        select(EventBundle)
        .where(EventBundle.tenant_id == tenant_id)
        .options(selectinload(EventBundle.members))
    )

    if project_id:
        query = query.where(EventBundle.project_id == project_id)
    if is_active is not None:
        query = query.where(EventBundle.is_active == is_active)

    query = query.order_by(EventBundle.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    bundles = result.scalars().all()

    return [bundle_to_response(b) for b in bundles]


@router.get(
    "/bundles/{bundle_id}",
    response_model=EventBundleResponse,
    summary="Get event bundle",
)
async def get_event_bundle(
    bundle_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get an event bundle by ID."""
    result = await db.execute(
        select(EventBundle)
        .where(
            and_(
                EventBundle.id == bundle_id,
                EventBundle.tenant_id == tenant_id,
            )
        )
        .options(selectinload(EventBundle.members))
    )
    bundle = result.scalar_one_or_none()

    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event bundle {bundle_id} not found",
        )

    return bundle_to_response(bundle)


@router.delete(
    "/bundles/{bundle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete event bundle",
)
async def delete_event_bundle(
    bundle_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Delete an event bundle."""
    result = await db.execute(
        select(EventBundle).where(
            and_(
                EventBundle.id == bundle_id,
                EventBundle.tenant_id == tenant_id,
            )
        )
    )
    bundle = result.scalar_one_or_none()

    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event bundle {bundle_id} not found",
        )

    await db.delete(bundle)
    await db.commit()


# ============================================================================
# Event Execution Endpoints
# ============================================================================

@router.post(
    "/{event_id}/execute",
    response_model=EventExecutionResult,
    summary="Execute event script",
)
async def execute_event_script(
    event_id: UUID,
    request: EventExecutionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    Manually execute an event script.

    This is for testing/debugging. In production, events are triggered
    by the simulation scheduler based on tick and conditions.
    """
    # Fetch event
    result = await db.execute(
        select(EventScript).where(
            and_(
                EventScript.id == event_id,
                EventScript.tenant_id == tenant_id,
            )
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event script {event_id} not found",
        )

    if not event.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event script is not active",
        )

    # Convert to executor format
    event_data = event.to_dict()
    executable_event = create_event_from_dict(event_data)

    # Create execution context
    # Note: In production, this would be populated from the run's world state
    context = ExecutionContext(
        run_id=str(request.run_id),
        current_tick=request.current_tick,
        rng_seed=42,  # Would come from run config
        environment_state={},  # Would come from world state
        agent_states={},  # Would come from agent pool
    )

    # Execute
    executor = get_event_executor()
    exec_result = executor.execute(
        executable_event,
        context,
        intensity_override=request.intensity_override,
    )

    # Log trigger (P3-003)
    trigger_log = EventTriggerLog(
        tenant_id=tenant_id,
        run_id=request.run_id,
        event_script_id=event_id,
        triggered_at_tick=request.current_tick,
        trigger_source="manual",
        affected_agent_count=exec_result.affected_agent_count,
        affected_segment_count=exec_result.affected_segment_count,
        affected_region_count=exec_result.affected_region_count,
        applied_deltas={
            "environment_deltas": [
                {
                    "variable": d.variable,
                    "operation": d.operation.value,
                    "old_value": d.old_value,
                    "new_value": d.new_value,
                }
                for d in exec_result.environment_deltas_applied
            ],
            "agent_deltas": {
                agent_id: [
                    {
                        "variable": d.variable,
                        "operation": d.operation.value,
                        "old_value": d.old_value,
                        "new_value": d.new_value,
                    }
                    for d in deltas
                ]
                for agent_id, deltas in exec_result.agent_deltas_applied.items()
            },
        },
        applied_intensity=exec_result.applied_intensity,
        effect_summary={
            "occurred": exec_result.occurred,
            "affected_regions": list(exec_result.affected_regions),
            "affected_segments": list(exec_result.affected_segments),
        },
    )
    db.add(trigger_log)
    await db.commit()
    await db.refresh(trigger_log)

    return EventExecutionResult(
        event_id=event_id,
        run_id=request.run_id,
        executed_at_tick=request.current_tick,
        affected_agent_count=exec_result.affected_agent_count,
        affected_segment_count=exec_result.affected_segment_count,
        affected_region_count=exec_result.affected_region_count,
        applied_intensity=exec_result.applied_intensity,
        deltas_applied=DeltasSchema(
            environment_deltas=[],
            perception_deltas=[],
            custom_deltas=[],
        ),
        effect_summary={
            "occurred": exec_result.occurred,
            "affected_regions": list(exec_result.affected_regions),
        },
        trigger_log_id=trigger_log.id,
    )


# ============================================================================
# Event Trigger Log Endpoints (P3-003)
# ============================================================================

@router.get(
    "/trigger-logs",
    response_model=List[EventTriggerLogListResponse],
    summary="List event trigger logs",
)
async def list_trigger_logs(
    run_id: Optional[UUID] = Query(None, description="Filter by run"),
    event_id: Optional[UUID] = Query(None, description="Filter by event"),
    min_tick: Optional[int] = Query(None, description="Minimum tick"),
    max_tick: Optional[int] = Query(None, description="Maximum tick"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    List event trigger logs for telemetry and debugging.

    Logs track when events were triggered, what was affected, and
    the actual deltas applied.
    """
    query = select(EventTriggerLog).where(EventTriggerLog.tenant_id == tenant_id)

    if run_id:
        query = query.where(EventTriggerLog.run_id == run_id)
    if event_id:
        query = query.where(EventTriggerLog.event_script_id == event_id)
    if min_tick is not None:
        query = query.where(EventTriggerLog.triggered_at_tick >= min_tick)
    if max_tick is not None:
        query = query.where(EventTriggerLog.triggered_at_tick <= max_tick)

    query = query.order_by(EventTriggerLog.triggered_at_tick.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        EventTriggerLogListResponse(
            log_id=log.id,
            run_id=log.run_id,
            event_id=log.event_script_id,
            triggered_at_tick=log.triggered_at_tick,
            trigger_source=log.trigger_source,
            affected_agent_count=log.affected_agent_count,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get(
    "/trigger-logs/{log_id}",
    response_model=EventTriggerLogResponse,
    summary="Get event trigger log",
)
async def get_trigger_log(
    log_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get a specific trigger log entry."""
    result = await db.execute(
        select(EventTriggerLog).where(
            and_(
                EventTriggerLog.id == log_id,
                EventTriggerLog.tenant_id == tenant_id,
            )
        )
    )
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trigger log {log_id} not found",
        )

    return EventTriggerLogResponse(
        log_id=log.id,
        run_id=log.run_id,
        event_id=log.event_script_id,
        triggered_at_tick=log.triggered_at_tick,
        trigger_source=log.trigger_source,
        affected_agent_count=log.affected_agent_count,
        affected_segment_count=log.affected_segment_count,
        affected_region_count=log.affected_region_count,
        applied_deltas=log.applied_deltas,
        applied_intensity=log.applied_intensity,
        effect_summary=log.effect_summary,
        created_at=log.created_at,
    )


# ============================================================================
# Statistics Endpoints
# ============================================================================

@router.get(
    "/stats",
    summary="Get event script statistics",
)
async def get_event_stats(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """Get statistics about event scripts."""
    base_filter = EventScript.tenant_id == tenant_id
    if project_id:
        base_filter = and_(base_filter, EventScript.project_id == project_id)

    # Total count
    total_result = await db.execute(
        select(func.count(EventScript.id)).where(base_filter)
    )
    total = total_result.scalar() or 0

    # Active count
    active_result = await db.execute(
        select(func.count(EventScript.id)).where(
            and_(base_filter, EventScript.is_active == True)
        )
    )
    active = active_result.scalar() or 0

    # Validated count
    validated_result = await db.execute(
        select(func.count(EventScript.id)).where(
            and_(base_filter, EventScript.is_validated == True)
        )
    )
    validated = validated_result.scalar() or 0

    # By type
    type_result = await db.execute(
        select(EventScript.event_type, func.count(EventScript.id))
        .where(base_filter)
        .group_by(EventScript.event_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    # Bundle count
    bundle_filter = EventBundle.tenant_id == tenant_id
    if project_id:
        bundle_filter = and_(bundle_filter, EventBundle.project_id == project_id)

    bundle_result = await db.execute(
        select(func.count(EventBundle.id)).where(bundle_filter)
    )
    bundle_count = bundle_result.scalar() or 0

    return {
        "total_events": total,
        "active_events": active,
        "validated_events": validated,
        "events_by_type": by_type,
        "total_bundles": bundle_count,
    }


# ============================================================================
# STEP 5: Event Candidate Endpoints
# ============================================================================

class EventCandidateListResponse(BaseModel):
    """Response for listing event candidates."""
    candidate_id: str
    compilation_id: str
    source_text: str
    label: str
    candidate_index: int
    probability: float
    confidence_score: float
    status: str
    created_at: datetime


class EventCandidateDetailResponse(BaseModel):
    """Detailed response for an event candidate."""
    candidate_id: str
    compilation_id: str
    source_text: str
    candidate_index: int
    label: str
    description: Optional[str]
    parsed_intent: Dict[str, Any]
    proposed_deltas: Dict[str, Any]
    proposed_scope: Dict[str, Any]
    affected_variables: List[str]
    probability: float
    confidence_score: float
    cluster_id: Optional[str]
    status: str
    committed_event_id: Optional[str]
    compiler_version: str
    model_used: Optional[str]
    created_at: datetime
    selected_at: Optional[datetime]


class SelectCandidateRequest(BaseModel):
    """Request to select an event candidate."""
    pass  # Selection just requires the candidate_id in path


class SelectCandidateResponse(BaseModel):
    """Response from selecting a candidate."""
    candidate_id: str
    status: str
    selected_at: datetime


class EditCandidateParametersRequest(BaseModel):
    """Request to edit candidate parameters."""
    label: Optional[str] = None
    description: Optional[str] = None
    proposed_deltas: Optional[Dict[str, Any]] = None
    proposed_scope: Optional[Dict[str, Any]] = None
    probability: Optional[float] = Field(None, ge=0.0, le=1.0)


class ApplyToNodeRequest(BaseModel):
    """Request to apply a candidate to a node (creates fork)."""
    parent_node_id: UUID = Field(..., description="Parent node to fork from")
    label: Optional[str] = Field(None, description="Optional label for the new node")
    auto_run: bool = Field(default=False, description="Auto-start simulation run")


class ApplyToNodeResponse(BaseModel):
    """Response from applying candidate to node."""
    candidate_id: str
    committed_event_id: str
    node_id: str
    edge_id: str
    patch_id: str
    patch_hash: str


class MissingFieldsResponse(BaseModel):
    """Response showing missing fields for a candidate."""
    candidate_id: str
    missing_required: List[Dict[str, Any]]
    missing_recommended: List[Dict[str, Any]]
    completeness_score: float


class AffectedVariablesResponse(BaseModel):
    """Response showing affected variables for a candidate."""
    candidate_id: str
    affected_variables: List[str]
    variable_details: List[Dict[str, Any]]
    impact_summary: Dict[str, Any]


class ScopePreviewResponse(BaseModel):
    """Response showing scope preview for a candidate."""
    candidate_id: str
    scope: Dict[str, Any]
    affected_regions: List[str]
    affected_segments: List[str]
    time_window: Optional[Dict[str, int]]
    estimated_agent_count: int


class SaveAsTemplateRequest(BaseModel):
    """Request to save an event as a template."""
    template_name: str = Field(..., min_length=1, max_length=255)
    template_description: Optional[str] = None
    tags: Optional[List[str]] = None


class SaveAsTemplateResponse(BaseModel):
    """Response from saving event as template."""
    original_event_id: str
    template_event_id: str
    template_name: str


@router.get(
    "/candidates",
    response_model=List[EventCandidateListResponse],
    summary="List event candidates (STEP 5)",
)
async def list_event_candidates(
    compilation_id: Optional[str] = Query(None, description="Filter by compilation ID"),
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, selected, rejected, committed"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    STEP 5: List event candidates from NL compilation.

    Candidates are parsed but uncommitted event interpretations from natural
    language input. Use this endpoint to review candidates before committing.
    """
    from app.models.event_script import EventCandidate

    query = select(EventCandidate).where(EventCandidate.tenant_id == tenant_id)

    if compilation_id:
        query = query.where(EventCandidate.compilation_id == compilation_id)
    if project_id:
        query = query.where(EventCandidate.project_id == project_id)
    if status_filter:
        query = query.where(EventCandidate.status == status_filter)

    query = query.order_by(EventCandidate.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    candidates = result.scalars().all()

    return [
        EventCandidateListResponse(
            candidate_id=str(c.id),
            compilation_id=c.compilation_id,
            source_text=c.source_text[:100] + "..." if len(c.source_text) > 100 else c.source_text,
            label=c.label,
            candidate_index=c.candidate_index,
            probability=c.probability,
            confidence_score=c.confidence_score,
            status=c.status,
            created_at=c.created_at,
        )
        for c in candidates
    ]


@router.get(
    "/candidates/{candidate_id}",
    response_model=EventCandidateDetailResponse,
    summary="Get event candidate details (STEP 5)",
)
async def get_event_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """STEP 5: Get detailed information about an event candidate."""
    from app.models.event_script import EventCandidate

    result = await db.execute(
        select(EventCandidate).where(
            and_(
                EventCandidate.id == candidate_id,
                EventCandidate.tenant_id == tenant_id,
            )
        )
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event candidate {candidate_id} not found",
        )

    return EventCandidateDetailResponse(
        candidate_id=str(candidate.id),
        compilation_id=candidate.compilation_id,
        source_text=candidate.source_text,
        candidate_index=candidate.candidate_index,
        label=candidate.label,
        description=candidate.description,
        parsed_intent=candidate.parsed_intent,
        proposed_deltas=candidate.proposed_deltas,
        proposed_scope=candidate.proposed_scope,
        affected_variables=candidate.affected_variables,
        probability=candidate.probability,
        confidence_score=candidate.confidence_score,
        cluster_id=candidate.cluster_id,
        status=candidate.status,
        committed_event_id=str(candidate.committed_event_id) if candidate.committed_event_id else None,
        compiler_version=candidate.compiler_version,
        model_used=candidate.model_used,
        created_at=candidate.created_at,
        selected_at=candidate.selected_at,
    )


@router.post(
    "/candidates/{candidate_id}/select",
    response_model=SelectCandidateResponse,
    summary="Select an event candidate (STEP 5)",
)
async def select_event_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    STEP 5: Select an event candidate for further use.

    Marking a candidate as selected indicates user intent to use this
    interpretation. The candidate can then be applied to a node.
    """
    from app.models.event_script import EventCandidate, EventCandidateStatus

    result = await db.execute(
        select(EventCandidate).where(
            and_(
                EventCandidate.id == candidate_id,
                EventCandidate.tenant_id == tenant_id,
            )
        )
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event candidate {candidate_id} not found",
        )

    if candidate.status == EventCandidateStatus.COMMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate has already been committed",
        )

    # Mark as selected
    candidate.status = EventCandidateStatus.SELECTED.value
    candidate.selected_at = datetime.utcnow()

    await db.commit()
    await db.refresh(candidate)

    return SelectCandidateResponse(
        candidate_id=str(candidate.id),
        status=candidate.status,
        selected_at=candidate.selected_at,
    )


@router.patch(
    "/candidates/{candidate_id}/parameters",
    response_model=EventCandidateDetailResponse,
    summary="Edit candidate parameters (STEP 5)",
)
async def edit_candidate_parameters(
    candidate_id: UUID,
    request: EditCandidateParametersRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    STEP 5: Edit parameters of an event candidate.

    Allows fine-tuning the candidate's deltas, scope, and metadata
    before applying it to a node.
    """
    from app.models.event_script import EventCandidate, EventCandidateStatus

    result = await db.execute(
        select(EventCandidate).where(
            and_(
                EventCandidate.id == candidate_id,
                EventCandidate.tenant_id == tenant_id,
            )
        )
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event candidate {candidate_id} not found",
        )

    if candidate.status == EventCandidateStatus.COMMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit committed candidate",
        )

    # Update fields
    if request.label is not None:
        candidate.label = request.label
    if request.description is not None:
        candidate.description = request.description
    if request.proposed_deltas is not None:
        candidate.proposed_deltas = request.proposed_deltas
        # Update affected_variables based on deltas
        affected = set()
        for delta in request.proposed_deltas.get("environment_deltas", []):
            if isinstance(delta, dict) and "variable" in delta:
                affected.add(delta["variable"])
        for delta in request.proposed_deltas.get("perception_deltas", []):
            if isinstance(delta, dict) and "variable" in delta:
                affected.add(delta["variable"])
        candidate.affected_variables = list(affected)
    if request.proposed_scope is not None:
        candidate.proposed_scope = request.proposed_scope
    if request.probability is not None:
        candidate.probability = request.probability

    await db.commit()
    await db.refresh(candidate)

    return EventCandidateDetailResponse(
        candidate_id=str(candidate.id),
        compilation_id=candidate.compilation_id,
        source_text=candidate.source_text,
        candidate_index=candidate.candidate_index,
        label=candidate.label,
        description=candidate.description,
        parsed_intent=candidate.parsed_intent,
        proposed_deltas=candidate.proposed_deltas,
        proposed_scope=candidate.proposed_scope,
        affected_variables=candidate.affected_variables,
        probability=candidate.probability,
        confidence_score=candidate.confidence_score,
        cluster_id=candidate.cluster_id,
        status=candidate.status,
        committed_event_id=str(candidate.committed_event_id) if candidate.committed_event_id else None,
        compiler_version=candidate.compiler_version,
        model_used=candidate.model_used,
        created_at=candidate.created_at,
        selected_at=candidate.selected_at,
    )


@router.post(
    "/candidates/{candidate_id}/apply-to-node",
    response_model=ApplyToNodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply candidate to node (STEP 5)",
)
async def apply_candidate_to_node(
    candidate_id: UUID,
    request: ApplyToNodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    STEP 5: Apply an event candidate to a node.

    This creates:
    1. An EventScript from the candidate (committed)
    2. A NodePatch describing the change
    3. A child Node forked from the parent
    4. An Edge linking parent to child

    The candidate's patch_hash ensures reproducibility.
    """
    import hashlib
    import json
    from app.models.event_script import EventCandidate, EventCandidateStatus
    from app.models.node import Node, Edge, NodePatch

    # Get the candidate
    result = await db.execute(
        select(EventCandidate).where(
            and_(
                EventCandidate.id == candidate_id,
                EventCandidate.tenant_id == tenant_id,
            )
        )
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event candidate {candidate_id} not found",
        )

    if candidate.status == EventCandidateStatus.COMMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate has already been committed",
        )

    # Get the parent node
    parent_result = await db.execute(
        select(Node).where(
            and_(
                Node.id == request.parent_node_id,
                Node.tenant_id == tenant_id,
            )
        )
    )
    parent_node = parent_result.scalar_one_or_none()

    if not parent_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent node {request.parent_node_id} not found",
        )

    # Create deterministic patch_hash from candidate content
    hash_content = json.dumps({
        "source_text": candidate.source_text,
        "proposed_deltas": candidate.proposed_deltas,
        "proposed_scope": candidate.proposed_scope,
        "parent_node_id": str(request.parent_node_id),
    }, sort_keys=True)
    patch_hash = hashlib.sha256(hash_content.encode()).hexdigest()[:16]

    # 1. Create EventScript from candidate
    event_script = EventScript(
        tenant_id=tenant_id,
        project_id=parent_node.project_id,
        event_type="custom",
        label=candidate.label,
        description=candidate.description,
        scope=candidate.proposed_scope,
        deltas=candidate.proposed_deltas,
        intensity_profile={},
        uncertainty={
            "occurrence_probability": candidate.probability,
            "compilation_confidence": candidate.confidence_score,
        },
        provenance={
            "compiled_from": candidate.source_text,
            "compiler_version": candidate.compiler_version,
            "compilation_id": candidate.compilation_id,
            "candidate_id": str(candidate.id),
            "model_used": candidate.model_used,
        },
        source_text=candidate.source_text,
        affected_variables=candidate.affected_variables,
        confidence_score=candidate.confidence_score,
        is_validated=False,
    )
    db.add(event_script)
    await db.flush()

    # 2. Create NodePatch
    node_patch = NodePatch(
        tenant_id=tenant_id,
        patch_type="event_injection",
        change_description={
            "type": "event_candidate_applied",
            "candidate_id": str(candidate.id),
            "source_text": candidate.source_text,
        },
        parameters=candidate.proposed_deltas,
        affected_variables=candidate.affected_variables,
        environment_overrides=candidate.proposed_scope.get("environment_overrides"),
        event_script_id=event_script.id,
        nl_description=candidate.source_text,
    )
    db.add(node_patch)
    await db.flush()

    # 3. Create child Node
    child_node = Node(
        tenant_id=tenant_id,
        project_id=parent_node.project_id,
        parent_node_id=parent_node.id,
        depth=parent_node.depth + 1,
        label=request.label or candidate.label,
        environment_spec=parent_node.environment_spec,  # Inherit from parent
        is_explored=False,
        is_baseline=False,
        probability=candidate.probability,
        cumulative_probability=parent_node.cumulative_probability * candidate.probability,
        min_ensemble_size=2,
        completed_run_count=0,
        is_ensemble_complete=False,
    )
    db.add(child_node)
    await db.flush()

    # Update NodePatch with node_id
    node_patch.node_id = child_node.id

    # 4. Create Edge
    edge = Edge(
        tenant_id=tenant_id,
        from_node_id=parent_node.id,
        to_node_id=child_node.id,
        intervention=candidate.proposed_deltas,
        explanation=candidate.description or candidate.source_text,
    )
    db.add(edge)

    # 5. Update candidate as committed
    candidate.status = EventCandidateStatus.COMMITTED.value
    candidate.committed_event_id = event_script.id

    await db.commit()

    return ApplyToNodeResponse(
        candidate_id=str(candidate.id),
        committed_event_id=str(event_script.id),
        node_id=str(child_node.id),
        edge_id=str(edge.id),
        patch_id=str(node_patch.id),
        patch_hash=patch_hash,
    )


@router.get(
    "/candidates/{candidate_id}/missing-fields",
    response_model=MissingFieldsResponse,
    summary="Show missing fields for candidate (STEP 5)",
)
async def show_candidate_missing_fields(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    STEP 5: Show which fields are missing or incomplete for a candidate.

    Helps users understand what additional information might be needed
    before applying the candidate to a node.
    """
    from app.models.event_script import EventCandidate

    result = await db.execute(
        select(EventCandidate).where(
            and_(
                EventCandidate.id == candidate_id,
                EventCandidate.tenant_id == tenant_id,
            )
        )
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event candidate {candidate_id} not found",
        )

    missing_required = []
    missing_recommended = []

    # Required fields
    if not candidate.label:
        missing_required.append({"field": "label", "message": "Label is required"})
    if not candidate.proposed_deltas:
        missing_required.append({"field": "proposed_deltas", "message": "At least one delta is required"})
    elif not any([
        candidate.proposed_deltas.get("environment_deltas"),
        candidate.proposed_deltas.get("perception_deltas"),
    ]):
        missing_required.append({
            "field": "proposed_deltas",
            "message": "At least one environment or perception delta is required"
        })

    # Recommended fields
    if not candidate.description:
        missing_recommended.append({"field": "description", "message": "Description is recommended"})
    if not candidate.proposed_scope:
        missing_recommended.append({"field": "proposed_scope", "message": "Scope is recommended for targeting"})
    if candidate.probability == 0.0:
        missing_recommended.append({"field": "probability", "message": "Probability should be > 0"})

    # Calculate completeness score
    total_fields = 5
    complete_fields = total_fields - len(missing_required)
    completeness_score = complete_fields / total_fields

    return MissingFieldsResponse(
        candidate_id=str(candidate.id),
        missing_required=missing_required,
        missing_recommended=missing_recommended,
        completeness_score=completeness_score,
    )


@router.get(
    "/candidates/{candidate_id}/affected-variables",
    response_model=AffectedVariablesResponse,
    summary="Show affected variables for candidate (STEP 5)",
)
async def show_candidate_affected_variables(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    STEP 5: Show which simulation variables would be affected by this candidate.

    Provides detailed information about each affected variable including
    the operation and value to be applied.
    """
    from app.models.event_script import EventCandidate

    result = await db.execute(
        select(EventCandidate).where(
            and_(
                EventCandidate.id == candidate_id,
                EventCandidate.tenant_id == tenant_id,
            )
        )
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event candidate {candidate_id} not found",
        )

    variable_details = []

    # Extract from environment_deltas
    env_deltas = candidate.proposed_deltas.get("environment_deltas", [])
    for delta in env_deltas:
        if isinstance(delta, dict):
            variable_details.append({
                "variable": delta.get("variable"),
                "category": "environment",
                "operation": delta.get("operation", "add"),
                "value": delta.get("value"),
                "impact_type": "direct",
            })

    # Extract from perception_deltas
    perception_deltas = candidate.proposed_deltas.get("perception_deltas", [])
    for delta in perception_deltas:
        if isinstance(delta, dict):
            variable_details.append({
                "variable": delta.get("variable"),
                "category": "perception",
                "operation": delta.get("operation", "add"),
                "value": delta.get("value"),
                "impact_type": "indirect",
            })

    # Impact summary
    impact_summary = {
        "total_variables": len(candidate.affected_variables),
        "environment_count": len(env_deltas),
        "perception_count": len(perception_deltas),
        "estimated_impact": "medium" if len(candidate.affected_variables) < 5 else "high",
    }

    return AffectedVariablesResponse(
        candidate_id=str(candidate.id),
        affected_variables=candidate.affected_variables,
        variable_details=variable_details,
        impact_summary=impact_summary,
    )


@router.get(
    "/candidates/{candidate_id}/scope-preview",
    response_model=ScopePreviewResponse,
    summary="Show scope preview for candidate (STEP 5)",
)
async def show_candidate_scope_preview(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    STEP 5: Preview the scope of effect for this candidate.

    Shows which regions, segments, and time window would be affected
    if this candidate is applied.
    """
    from app.models.event_script import EventCandidate

    result = await db.execute(
        select(EventCandidate).where(
            and_(
                EventCandidate.id == candidate_id,
                EventCandidate.tenant_id == tenant_id,
            )
        )
    )
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event candidate {candidate_id} not found",
        )

    scope = candidate.proposed_scope or {}
    affected_regions = scope.get("affected_regions", ["global"])
    affected_segments = scope.get("affected_segments", ["all"])
    time_window = scope.get("time_window")

    # Estimate affected agent count based on scope
    # In production, this would query the project's persona pool
    if "global" in affected_regions or not affected_regions:
        estimated_agent_count = 1000  # Full simulation
    else:
        estimated_agent_count = len(affected_regions) * 200  # Rough estimate

    if "all" not in affected_segments and affected_segments:
        estimated_agent_count = int(estimated_agent_count * 0.3)  # Segment subset

    return ScopePreviewResponse(
        candidate_id=str(candidate.id),
        scope=scope,
        affected_regions=affected_regions,
        affected_segments=affected_segments,
        time_window=time_window,
        estimated_agent_count=estimated_agent_count,
    )


@router.post(
    "/{event_id}/save-as-template",
    response_model=SaveAsTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save event as template (STEP 5)",
)
async def save_event_as_template(
    event_id: UUID,
    request: SaveAsTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    STEP 5: Save an event script as a reusable template.

    Creates a copy of the event with template metadata, allowing
    it to be reused across projects.
    """
    # Get original event
    result = await db.execute(
        select(EventScript).where(
            and_(
                EventScript.id == event_id,
                EventScript.tenant_id == tenant_id,
            )
        )
    )
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event script {event_id} not found",
        )

    # Create template copy
    template = EventScript(
        tenant_id=tenant_id,
        project_id=original.project_id,  # Templates can be moved later
        event_type=original.event_type,
        label=request.template_name,
        description=request.template_description or original.description,
        scope=original.scope,
        deltas=original.deltas,
        intensity_profile=original.intensity_profile,
        uncertainty=original.uncertainty,
        provenance={
            "template_source": str(original.id),
            "original_label": original.label,
            "templated_at": datetime.utcnow().isoformat(),
            "templated_by": str(current_user.id),
        },
        source_text=original.source_text,
        affected_variables=original.affected_variables,
        confidence_score=original.confidence_score,
        tags=(request.tags or []) + ["template"],
        is_active=True,
        is_validated=original.is_validated,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return SaveAsTemplateResponse(
        original_event_id=str(original.id),
        template_event_id=str(template.id),
        template_name=request.template_name,
    )
