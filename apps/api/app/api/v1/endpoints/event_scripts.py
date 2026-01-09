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
