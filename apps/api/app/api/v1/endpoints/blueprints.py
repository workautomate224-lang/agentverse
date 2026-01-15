"""
Blueprint API Endpoints
Reference: blueprint.md §3, §4, §5
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.blueprint import (
    Blueprint,
    BlueprintSlot,
    BlueprintTask,
    DomainGuess,
    AlertState,
    PLATFORM_SECTIONS,
)
from app.schemas.blueprint import (
    # Blueprint schemas
    BlueprintCreate,
    BlueprintUpdate,
    BlueprintResponse,
    BlueprintSummary,
    # Slot schemas
    BlueprintSlotCreate,
    BlueprintSlotUpdate,
    BlueprintSlotResponse,
    # Task schemas
    BlueprintTaskCreate,
    BlueprintTaskUpdate,
    BlueprintTaskResponse,
    # Goal analysis
    GoalAnalysisResult,
    SubmitClarificationAnswers,
    # Checklist
    ProjectChecklist,
    ChecklistItem,
    # Guidance
    GuidancePanel,
)
from app.tasks.pil_tasks import dispatch_pil_job

router = APIRouter()


# =============================================================================
# Blueprint CRUD Endpoints
# =============================================================================

@router.get("/", response_model=list[BlueprintSummary])
async def list_blueprints(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_draft: Optional[bool] = Query(None, description="Filter by draft status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BlueprintSummary]:
    """
    List blueprints for the current user's tenant.
    """
    query = select(Blueprint).where(Blueprint.tenant_id == current_user.id)

    if project_id:
        query = query.where(Blueprint.project_id == project_id)
    if is_active is not None:
        query = query.where(Blueprint.is_active == is_active)
    if is_draft is not None:
        query = query.where(Blueprint.is_draft == is_draft)

    query = query.offset(skip).limit(limit).order_by(Blueprint.created_at.desc())

    result = await db.execute(query)
    blueprints = result.scalars().all()

    # Convert to summaries with slot/task counts
    summaries = []
    for bp in blueprints:
        # Count slots
        slot_result = await db.execute(
            select(func.count(BlueprintSlot.id)).where(BlueprintSlot.blueprint_id == bp.id)
        )
        slots_total = slot_result.scalar() or 0

        ready_slots_result = await db.execute(
            select(func.count(BlueprintSlot.id)).where(
                BlueprintSlot.blueprint_id == bp.id,
                BlueprintSlot.fulfilled == True
            )
        )
        slots_ready = ready_slots_result.scalar() or 0

        # Count tasks
        task_result = await db.execute(
            select(func.count(BlueprintTask.id)).where(BlueprintTask.blueprint_id == bp.id)
        )
        tasks_total = task_result.scalar() or 0

        ready_tasks_result = await db.execute(
            select(func.count(BlueprintTask.id)).where(
                BlueprintTask.blueprint_id == bp.id,
                BlueprintTask.status == AlertState.READY.value
            )
        )
        tasks_ready = ready_tasks_result.scalar() or 0

        summaries.append(BlueprintSummary(
            id=bp.id,
            project_id=bp.project_id,
            version=bp.version,
            is_active=bp.is_active,
            goal_summary=bp.goal_summary,
            domain_guess=bp.domain_guess.value if bp.domain_guess else None,
            is_draft=bp.is_draft,
            created_at=bp.created_at.isoformat() if bp.created_at else None,
            slots_ready=slots_ready,
            slots_total=slots_total,
            tasks_ready=tasks_ready,
            tasks_total=tasks_total,
        ))

    return summaries


@router.post("/", response_model=BlueprintResponse, status_code=status.HTTP_201_CREATED)
async def create_blueprint(
    blueprint_in: BlueprintCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Blueprint:
    """
    Create a new blueprint for a project.
    This creates a draft blueprint and optionally triggers goal analysis.
    Reference: blueprint.md §4.1
    """
    # Check for existing active blueprint and get next version
    existing_result = await db.execute(
        select(Blueprint)
        .where(Blueprint.project_id == blueprint_in.project_id)
        .order_by(Blueprint.version.desc())
        .limit(1)
    )
    existing = existing_result.scalar_one_or_none()
    next_version = (existing.version + 1) if existing else 1

    # Deactivate existing active blueprint
    if existing and existing.is_active:
        existing.is_active = False

    blueprint = Blueprint(
        tenant_id=current_user.id,
        project_id=blueprint_in.project_id,
        version=next_version,
        is_active=True,
        is_draft=True,
        goal_text=blueprint_in.goal_text,
        created_by=str(current_user.id),
    )

    db.add(blueprint)
    await db.flush()
    await db.refresh(blueprint)

    # If not skipping clarification, trigger goal analysis job
    if not blueprint_in.skip_clarification:
        # Import here to avoid circular dependency
        from app.models.pil_job import PILJob, PILJobStatus, PILJobType, PILJobPriority
        import logging
        logger = logging.getLogger(__name__)

        job = PILJob(
            tenant_id=current_user.id,
            project_id=blueprint_in.project_id,
            blueprint_id=blueprint.id,
            job_type=PILJobType.GOAL_ANALYSIS,
            job_name=f"Goal Analysis for Blueprint v{next_version}",
            priority=PILJobPriority.HIGH,
            status=PILJobStatus.QUEUED,
            input_params={"goal_text": blueprint_in.goal_text},
            created_by=str(current_user.id),
        )
        db.add(job)
        await db.flush()
        await db.refresh(job)
        await db.commit()

        # Dispatch to Celery for background processing
        # Handle dispatch failure gracefully - blueprint still gets created
        try:
            dispatch_pil_job.delay(str(job.id))
        except Exception as e:
            logger.error(f"Failed to dispatch PIL job {job.id}: {e}")
            # Update job status to FAILED so UI can show the error
            job.status = PILJobStatus.FAILED
            job.error_message = f"Failed to dispatch job: {str(e)}"
            await db.commit()
    else:
        await db.commit()

    await db.refresh(blueprint)

    return blueprint


@router.get("/{blueprint_id}", response_model=BlueprintResponse)
async def get_blueprint(
    blueprint_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Blueprint:
    """
    Get blueprint by ID with all slots and tasks.
    """
    result = await db.execute(
        select(Blueprint)
        .where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == current_user.id,
        )
        .options(
            selectinload(Blueprint.slots),
            selectinload(Blueprint.tasks),
        )
    )
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blueprint not found",
        )

    return blueprint


@router.put("/{blueprint_id}", response_model=BlueprintResponse)
async def update_blueprint(
    blueprint_id: UUID,
    blueprint_update: BlueprintUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Blueprint:
    """
    Update a blueprint. Creates a new version if non-draft blueprint.
    Reference: blueprint.md §3 - fork-not-mutate
    """
    result = await db.execute(
        select(Blueprint).where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == current_user.id,
        )
    )
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blueprint not found",
        )

    # If not a draft, we should create a new version (fork-not-mutate)
    if not blueprint.is_draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify non-draft blueprint. Create a new version instead.",
        )

    update_data = blueprint_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(blueprint, field, value)

    await db.flush()
    await db.refresh(blueprint)

    return blueprint


@router.post("/{blueprint_id}/publish", response_model=BlueprintResponse)
async def publish_blueprint(
    blueprint_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Blueprint:
    """
    Publish a draft blueprint, making it the active version.
    Reference: blueprint.md §4.3
    """
    result = await db.execute(
        select(Blueprint).where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == current_user.id,
        )
    )
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blueprint not found",
        )

    if not blueprint.is_draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Blueprint is already published",
        )

    # Deactivate other blueprints for this project
    await db.execute(
        select(Blueprint).where(
            Blueprint.project_id == blueprint.project_id,
            Blueprint.id != blueprint.id,
            Blueprint.is_active == True,
        )
    )

    blueprint.is_draft = False
    blueprint.is_active = True

    await db.flush()
    await db.refresh(blueprint)

    return blueprint


@router.post("/{blueprint_id}/clarify", response_model=BlueprintResponse)
async def submit_clarification_answers(
    blueprint_id: UUID,
    answers: SubmitClarificationAnswers,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Blueprint:
    """
    Submit clarification answers to refine the blueprint.
    Reference: blueprint.md §4.2.2
    """
    result = await db.execute(
        select(Blueprint).where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == current_user.id,
        )
    )
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blueprint not found",
        )

    if not blueprint.is_draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify published blueprint",
        )

    # Store answers
    existing_answers = blueprint.clarification_answers or {}
    existing_answers.update(answers.clarification_answers)
    blueprint.clarification_answers = existing_answers

    # Trigger blueprint build job
    from app.models.pil_job import PILJob, PILJobStatus, PILJobType, PILJobPriority

    job = PILJob(
        tenant_id=current_user.id,
        project_id=blueprint.project_id,
        blueprint_id=blueprint.id,
        job_type=PILJobType.BLUEPRINT_BUILD,
        job_name=f"Build Blueprint v{blueprint.version}",
        priority=PILJobPriority.HIGH,
        status=PILJobStatus.QUEUED,
        input_params={
            "goal_text": blueprint.goal_text,
            "clarification_answers": existing_answers,
        },
        created_by=str(current_user.id),
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    await db.commit()

    # Dispatch to Celery for background processing
    dispatch_pil_job.delay(str(job.id))

    await db.refresh(blueprint)

    return blueprint


# =============================================================================
# Slot Endpoints
# =============================================================================

@router.get("/{blueprint_id}/slots", response_model=list[BlueprintSlotResponse])
async def list_blueprint_slots(
    blueprint_id: UUID,
    required_level: Optional[str] = Query(None, pattern="^(required|recommended|optional)$"),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BlueprintSlot]:
    """
    List all slots for a blueprint.
    """
    # Verify blueprint access
    bp_result = await db.execute(
        select(Blueprint).where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == current_user.id,
        )
    )
    if not bp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Blueprint not found")

    query = select(BlueprintSlot).where(BlueprintSlot.blueprint_id == blueprint_id)

    if required_level:
        query = query.where(BlueprintSlot.required_level == required_level)
    if status_filter:
        query = query.where(BlueprintSlot.status == status_filter)

    query = query.order_by(BlueprintSlot.sort_order)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{blueprint_id}/slots", response_model=BlueprintSlotResponse)
async def create_slot(
    blueprint_id: UUID,
    slot_in: BlueprintSlotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BlueprintSlot:
    """
    Add a slot to a blueprint.
    """
    # Verify blueprint access and is draft
    bp_result = await db.execute(
        select(Blueprint).where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == current_user.id,
        )
    )
    blueprint = bp_result.scalar_one_or_none()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    if not blueprint.is_draft:
        raise HTTPException(status_code=400, detail="Cannot modify published blueprint")

    # Get next sort order
    max_order_result = await db.execute(
        select(func.max(BlueprintSlot.sort_order)).where(
            BlueprintSlot.blueprint_id == blueprint_id
        )
    )
    max_order = max_order_result.scalar() or 0

    slot = BlueprintSlot(
        blueprint_id=blueprint_id,
        sort_order=max_order + 1,
        **slot_in.model_dump(),
    )

    db.add(slot)
    await db.flush()
    await db.refresh(slot)

    return slot


@router.put("/{blueprint_id}/slots/{slot_id}", response_model=BlueprintSlotResponse)
async def update_slot(
    blueprint_id: UUID,
    slot_id: UUID,
    slot_update: BlueprintSlotUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BlueprintSlot:
    """
    Update a slot.
    """
    # Verify access
    bp_result = await db.execute(
        select(Blueprint).where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == current_user.id,
        )
    )
    blueprint = bp_result.scalar_one_or_none()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    if not blueprint.is_draft:
        raise HTTPException(status_code=400, detail="Cannot modify published blueprint")

    slot_result = await db.execute(
        select(BlueprintSlot).where(
            BlueprintSlot.id == slot_id,
            BlueprintSlot.blueprint_id == blueprint_id,
        )
    )
    slot = slot_result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    update_data = slot_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(slot, field, value)

    await db.flush()
    await db.refresh(slot)

    return slot


@router.post("/{blueprint_id}/slots/{slot_id}/fulfill")
async def fulfill_slot(
    blueprint_id: UUID,
    slot_id: UUID,
    fulfilled_by_type: str = Query(..., description="Type of artifact fulfilling slot"),
    fulfilled_by_id: str = Query(..., description="ID of artifact"),
    fulfilled_by_name: str = Query(..., description="Name of artifact"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BlueprintSlotResponse:
    """
    Mark a slot as fulfilled by an artifact.
    Reference: blueprint.md §6.3
    """
    # Verify access and get blueprint
    bp_result = await db.execute(
        select(Blueprint).where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == current_user.id,
        )
    )
    blueprint = bp_result.scalar_one_or_none()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    slot_result = await db.execute(
        select(BlueprintSlot).where(
            BlueprintSlot.id == slot_id,
            BlueprintSlot.blueprint_id == blueprint_id,
        )
    )
    slot = slot_result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    slot.fulfilled = True
    slot.fulfilled_by = {
        "type": fulfilled_by_type,
        "id": fulfilled_by_id,
        "name": fulfilled_by_name,
    }
    slot.status = AlertState.READY

    # Trigger slot validation job
    from app.models.pil_job import PILJob, PILJobStatus, PILJobType, PILJobPriority

    job = PILJob(
        tenant_id=current_user.id,
        project_id=blueprint.project_id,
        blueprint_id=blueprint_id,
        job_type=PILJobType.SLOT_VALIDATION,
        job_name=f"Validate Slot: {slot.slot_name}",
        priority=PILJobPriority.NORMAL,
        status=PILJobStatus.QUEUED,
        slot_id=str(slot_id),
        input_params={
            "slot_id": str(slot_id),
            "fulfilled_by": slot.fulfilled_by,
        },
        created_by=str(current_user.id),
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    await db.commit()

    # Dispatch to Celery for background processing
    dispatch_pil_job.delay(str(job.id))

    await db.refresh(slot)

    return slot


# =============================================================================
# Task Endpoints
# =============================================================================

@router.get("/{blueprint_id}/tasks", response_model=list[BlueprintTaskResponse])
async def list_blueprint_tasks(
    blueprint_id: UUID,
    section_id: Optional[str] = Query(None, description="Filter by section ID"),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BlueprintTask]:
    """
    List all tasks for a blueprint.
    """
    # Verify blueprint access
    bp_result = await db.execute(
        select(Blueprint).where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == current_user.id,
        )
    )
    if not bp_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Blueprint not found")

    query = select(BlueprintTask).where(BlueprintTask.blueprint_id == blueprint_id)

    if section_id:
        query = query.where(BlueprintTask.section_id == section_id)
    if status_filter:
        query = query.where(BlueprintTask.status == status_filter)

    query = query.order_by(BlueprintTask.section_id, BlueprintTask.sort_order)

    result = await db.execute(query)
    return result.scalars().all()


@router.put("/{blueprint_id}/tasks/{task_id}", response_model=BlueprintTaskResponse)
async def update_task(
    blueprint_id: UUID,
    task_id: UUID,
    task_update: BlueprintTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BlueprintTask:
    """
    Update a task.
    """
    # Verify access
    bp_result = await db.execute(
        select(Blueprint).where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == current_user.id,
        )
    )
    blueprint = bp_result.scalar_one_or_none()
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    if not blueprint.is_draft:
        raise HTTPException(status_code=400, detail="Cannot modify published blueprint")

    task_result = await db.execute(
        select(BlueprintTask).where(
            BlueprintTask.id == task_id,
            BlueprintTask.blueprint_id == blueprint_id,
        )
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.flush()
    await db.refresh(task)

    return task


# =============================================================================
# Checklist & Guidance Endpoints
# =============================================================================

@router.get("/{blueprint_id}/checklist", response_model=ProjectChecklist)
async def get_project_checklist(
    blueprint_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectChecklist:
    """
    Get the project checklist with alert states.
    Reference: blueprint.md §7
    """
    result = await db.execute(
        select(Blueprint)
        .where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == current_user.id,
        )
        .options(
            selectinload(Blueprint.slots),
            selectinload(Blueprint.tasks),
        )
    )
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    # Build checklist items from slots and tasks
    items = []

    # Add slot-based items
    for slot in blueprint.slots or []:
        items.append(ChecklistItem(
            id=str(slot.id),
            title=slot.slot_name,
            section_id="inputs",  # Slots are in inputs section
            status=slot.status or "not_started",
            status_reason=slot.status_reason,
            why_it_matters=slot.description,
            missing_items=[slot.slot_name] if not slot.fulfilled else None,
            match_score=slot.alignment_score,
        ))

    # Add task-based items
    for task in blueprint.tasks or []:
        items.append(ChecklistItem(
            id=str(task.id),
            title=task.title,
            section_id=task.section_id,
            status=task.status or "not_started",
            status_reason=task.status_reason,
            why_it_matters=task.why_it_matters,
            latest_summary=task.last_summary_ref,
        ))

    # Count by status
    ready = sum(1 for i in items if i.status == "ready")
    needs_attention = sum(1 for i in items if i.status == "needs_attention")
    blocked = sum(1 for i in items if i.status == "blocked")
    not_started = sum(1 for i in items if i.status == "not_started")

    # Determine overall readiness
    if blocked > 0:
        overall = "blocked"
    elif needs_attention > 0 or not_started > 0:
        overall = "needs_work"
    else:
        overall = "ready"

    return ProjectChecklist(
        project_id=str(blueprint.project_id),
        blueprint_id=str(blueprint.id),
        blueprint_version=blueprint.version,
        items=items,
        ready_count=ready,
        needs_attention_count=needs_attention,
        blocked_count=blocked,
        not_started_count=not_started,
        overall_readiness=overall,
    )


@router.get("/{blueprint_id}/guidance/{section_id}", response_model=GuidancePanel)
async def get_section_guidance(
    blueprint_id: UUID,
    section_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GuidancePanel:
    """
    Get the guidance panel for a specific section.
    Reference: blueprint.md §8
    """
    if section_id not in PLATFORM_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section_id. Must be one of: {', '.join(PLATFORM_SECTIONS)}",
        )

    result = await db.execute(
        select(Blueprint)
        .where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == current_user.id,
        )
        .options(
            selectinload(Blueprint.slots),
            selectinload(Blueprint.tasks),
        )
    )
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    # Filter tasks for this section
    section_tasks = [t for t in (blueprint.tasks or []) if t.section_id == section_id]

    # Get linked slots for tasks in this section
    linked_slot_ids = set()
    for task in section_tasks:
        if task.linked_slot_ids:
            linked_slot_ids.update(task.linked_slot_ids)

    # Separate required vs recommended slots
    required_slots = []
    recommended_slots = []
    for slot in blueprint.slots or []:
        if str(slot.id) in linked_slot_ids:
            if slot.required_level == "required":
                required_slots.append(slot)
            else:
                recommended_slots.append(slot)

    # Determine overall status
    statuses = [t.status for t in section_tasks] + [s.status for s in required_slots]
    if any(s == "blocked" for s in statuses):
        overall_status = "blocked"
    elif any(s == "needs_attention" for s in statuses):
        overall_status = "needs_attention"
    elif any(s == "not_started" for s in statuses):
        overall_status = "not_started"
    else:
        overall_status = "ready"

    # Suggest next action
    next_action = None
    for task in section_tasks:
        if task.status != "ready":
            next_action = {
                "action": task.available_actions[0] if task.available_actions else "manual_add",
                "target_task_id": str(task.id),
                "reason": task.status_reason or f"Complete: {task.title}",
            }
            break

    if not next_action:
        for slot in required_slots:
            if not slot.fulfilled:
                next_action = {
                    "action": slot.allowed_acquisition_methods[0] if slot.allowed_acquisition_methods else "manual_upload",
                    "target_slot_id": str(slot.id),
                    "reason": f"Fulfill slot: {slot.slot_name}",
                }
                break

    return GuidancePanel(
        section_id=section_id,
        project_id=str(blueprint.project_id),
        blueprint_version=blueprint.version,
        tasks=[BlueprintTaskResponse.model_validate(t) for t in section_tasks],
        required_slots=[BlueprintSlotResponse.model_validate(s) for s in required_slots],
        recommended_slots=[BlueprintSlotResponse.model_validate(s) for s in recommended_slots],
        overall_status=overall_status,
        next_suggested_action=next_action,
    )


# =============================================================================
# Active Blueprint Shortcut
# =============================================================================

@router.get("/project/{project_id}/active", response_model=BlueprintResponse)
async def get_active_blueprint(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Blueprint:
    """
    Get the active blueprint for a project.
    """
    result = await db.execute(
        select(Blueprint)
        .where(
            Blueprint.project_id == project_id,
            Blueprint.tenant_id == current_user.id,
            Blueprint.is_active == True,
        )
        .options(
            selectinload(Blueprint.slots),
            selectinload(Blueprint.tasks),
        )
    )
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active blueprint found for this project",
        )

    return blueprint
