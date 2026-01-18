"""
Blueprint API Endpoints
Reference: blueprint.md §3, §4, §5
"""

from datetime import datetime as dt
from typing import Any, Dict, List, Optional
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
from app.models.project_guidance import (
    ProjectGuidance,
    GuidanceSection,
    GuidanceStatus,
)
from app.services.guidance_service import (
    mark_guidance_stale,
    trigger_guidance_regeneration,
    get_guidance_status_summary,
)
from app.models.pil_job import PILJob, PILJobType, PILJobStatus
from app.models.project_spec import ProjectSpec
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
    # Blueprint v2 (Slice 2A)
    BlueprintV2CreateRequest,
    BlueprintV2Response,
    # Blueprint v2 Edit Validation (Slice 2B)
    BlueprintV2ValidationRequest,
    BlueprintV2ValidationResult,
    BlueprintV2ValidationError,
    BlueprintV2SaveRequest,
    CoreType,
    TemporalMode,
    # Project Guidance (Slice 2C)
    GuidanceSection as GuidanceSectionSchema,
    ProjectGuidanceResponse,
    ProjectGuidanceListResponse,
    TriggerGenesisRequest,
    TriggerGenesisResponse,
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

    # Re-query with eager loading to avoid DetachedInstanceError
    # The blueprint needs slots and tasks loaded for BlueprintResponse serialization
    result = await db.execute(
        select(Blueprint)
        .where(Blueprint.id == blueprint.id)
        .options(
            selectinload(Blueprint.slots),
            selectinload(Blueprint.tasks),
        )
    )
    return result.scalar_one()


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

    await db.commit()

    # Re-query with eager loading for response serialization
    result = await db.execute(
        select(Blueprint)
        .where(Blueprint.id == blueprint.id)
        .options(
            selectinload(Blueprint.slots),
            selectinload(Blueprint.tasks),
        )
    )
    return result.scalar_one()


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
    from sqlalchemy import update as sql_update
    await db.execute(
        sql_update(Blueprint)
        .where(
            Blueprint.project_id == blueprint.project_id,
            Blueprint.id != blueprint.id,
            Blueprint.is_active == True,
        )
        .values(is_active=False)
    )

    blueprint.is_draft = False
    blueprint.is_active = True

    # Slice 2C: Mark existing guidance as stale (new blueprint version)
    # This prompts users to regenerate guidance based on the updated blueprint
    stale_count = await mark_guidance_stale(db, blueprint.project_id, "blueprint_published")

    await db.commit()

    # Re-query with eager loading for response serialization
    result = await db.execute(
        select(Blueprint)
        .where(Blueprint.id == blueprint.id)
        .options(
            selectinload(Blueprint.slots),
            selectinload(Blueprint.tasks),
        )
    )
    return result.scalar_one()


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

    # Re-query with eager loading to avoid DetachedInstanceError
    result = await db.execute(
        select(Blueprint)
        .where(Blueprint.id == blueprint.id)
        .options(
            selectinload(Blueprint.slots),
            selectinload(Blueprint.tasks),
        )
    )
    return result.scalar_one()


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

    # Trigger slot pipeline jobs: validate → summarize → score → compile
    # Reference: blueprint_v2.md §5.2
    from app.models.pil_job import PILJob, PILJobStatus, PILJobType, PILJobPriority

    pipeline_jobs = [
        # 1. Validation - check data quality and schema compliance
        (PILJobType.SLOT_VALIDATION, f"Validate: {slot.slot_name}"),
        # 2. Summarization - generate AI summary of the data
        (PILJobType.SLOT_SUMMARIZATION, f"Summarize: {slot.slot_name}"),
        # 3. Alignment scoring - score fit with project goals
        (PILJobType.SLOT_ALIGNMENT_SCORING, f"Score Alignment: {slot.slot_name}"),
        # 4. Compilation - transform data for simulation use
        (PILJobType.SLOT_COMPILATION, f"Compile: {slot.slot_name}"),
    ]

    job_ids = []
    for job_type, job_name in pipeline_jobs:
        job = PILJob(
            tenant_id=current_user.id,
            project_id=blueprint.project_id,
            blueprint_id=blueprint_id,
            job_type=job_type,
            job_name=job_name,
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
        job_ids.append(str(job.id))

    await db.commit()

    # Dispatch all jobs to Celery for parallel background processing
    for job_id in job_ids:
        dispatch_pil_job.delay(job_id)

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

@router.get(
    "/project/{project_id}/active",
    response_model=BlueprintResponse,
    responses={204: {"description": "No active blueprint found"}}
)
async def get_active_blueprint(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the active blueprint for a project.
    Returns 204 No Content if no active blueprint exists.
    """
    from fastapi import Response

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
        return Response(status_code=204)

    return blueprint


@router.get(
    "/project/{project_id}/checklist",
    response_model=ProjectChecklist,
    responses={204: {"description": "No active blueprint found"}}
)
async def get_project_checklist_by_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the checklist for the active blueprint of a project.
    Returns 204 No Content if no active blueprint exists.
    """
    from fastapi import Response

    # Find active blueprint for this project
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
        return Response(status_code=204)

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


# =============================================================================
# BLUEPRINT V2 ENDPOINTS (Slice 2A)
# =============================================================================

@router.post(
    "/v2/build",
    response_model=Dict[str, Any],
    summary="Trigger Blueprint v2 Build",
    description="Triggers the final_blueprint_build PIL job to generate Blueprint v2.",
)
async def trigger_blueprint_v2_build(
    request: BlueprintV2CreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Trigger the final_blueprint_build PIL job.

    This creates a new PIL job that will:
    1. Gather all Q/A context from the project
    2. Call OpenRouter with gpt-5.2 to generate Blueprint v2
    3. Validate the JSON structure (fail if invalid)
    4. Store the result with full provenance

    Returns the job_id to poll for status.
    """
    from app.models.pil_job import PILJob, PILJobStatus, PILJobType
    from app.tasks.pil_tasks import dispatch_pil_job

    # Verify project exists and user has access
    project = await db.get(ProjectSpec, request.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.project_id} not found"
        )

    # Check tenant access
    if project.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )

    # Create PIL job for final blueprint build
    job = PILJob(
        tenant_id=current_user.tenant_id,
        project_id=request.project_id,
        job_type=PILJobType.FINAL_BLUEPRINT_BUILD,
        status=PILJobStatus.QUEUED,
        created_by_id=current_user.id,
        input_data={
            "project_id": str(request.project_id),
            "trigger_source": request.trigger_source or "manual",
            "force_rebuild": request.force_rebuild or False,
        },
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Dispatch to Celery
    dispatch_pil_job.delay(str(job.id))

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "message": "Blueprint v2 build job queued successfully",
    }


@router.get(
    "/v2/{blueprint_id}",
    response_model=BlueprintV2Response,
    summary="Get Blueprint v2",
    description="Retrieve a Blueprint v2 by its ID.",
)
async def get_blueprint_v2(
    blueprint_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BlueprintV2Response:
    """
    Get Blueprint v2 by ID.

    Returns the full Blueprint v2 data including all structured sections
    and provenance information.
    """
    from sqlalchemy import select
    from app.schemas.blueprint import BlueprintV2, BlueprintV2Provenance

    # Get blueprint with version 2
    stmt = select(Blueprint).where(
        Blueprint.id == blueprint_id,
        Blueprint.version == 2,
    )
    result = await db.execute(stmt)
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blueprint v2 {blueprint_id} not found"
        )

    # Check tenant access
    project = await db.get(ProjectSpec, blueprint.project_id)
    if project and project.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this blueprint"
        )

    # Get the v2 data from blueprint_json
    v2_data = blueprint.blueprint_json or {}

    # Build provenance from metadata
    provenance = None
    if blueprint.metadata and "provenance" in blueprint.metadata:
        prov_data = blueprint.metadata["provenance"]
        provenance = BlueprintV2Provenance(
            model=prov_data.get("model"),
            model_version=prov_data.get("model_version"),
            generated_at=prov_data.get("generated_at"),
            input_tokens=prov_data.get("input_tokens"),
            output_tokens=prov_data.get("output_tokens"),
            job_id=prov_data.get("job_id"),
        )

    # Parse the v2 data
    from app.schemas.blueprint import (
        BlueprintV2Intent,
        BlueprintV2PredictionTarget,
        BlueprintV2Horizon,
        BlueprintV2OutputFormat,
        BlueprintV2EvaluationPlan,
        BlueprintV2RequiredInput,
    )

    return BlueprintV2Response(
        id=blueprint.id,
        project_id=blueprint.project_id,
        version=blueprint.version,
        status=blueprint.status,
        intent=BlueprintV2Intent(**v2_data.get("intent", {})) if v2_data.get("intent") else None,
        prediction_target=BlueprintV2PredictionTarget(**v2_data.get("prediction_target", {})) if v2_data.get("prediction_target") else None,
        horizon=BlueprintV2Horizon(**v2_data.get("horizon", {})) if v2_data.get("horizon") else None,
        output_format=BlueprintV2OutputFormat(**v2_data.get("output_format", {})) if v2_data.get("output_format") else None,
        evaluation_plan=BlueprintV2EvaluationPlan(**v2_data.get("evaluation_plan", {})) if v2_data.get("evaluation_plan") else None,
        required_inputs=[BlueprintV2RequiredInput(**inp) for inp in v2_data.get("required_inputs", [])] if v2_data.get("required_inputs") else [],
        provenance=provenance,
        created_at=blueprint.created_at,
        updated_at=blueprint.updated_at,
    )


@router.get(
    "/v2/project/{project_id}",
    response_model=BlueprintV2Response,
    summary="Get Blueprint v2 by Project",
    description="Retrieve the latest Blueprint v2 for a project.",
)
async def get_blueprint_v2_by_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BlueprintV2Response:
    """
    Get the latest Blueprint v2 for a project.

    Returns the most recent Blueprint v2 data for the given project.
    """
    from sqlalchemy import select
    from app.schemas.blueprint import BlueprintV2, BlueprintV2Provenance

    # Verify project exists and user has access
    project = await db.get(ProjectSpec, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    if project.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )

    # Get latest blueprint v2 for project
    stmt = select(Blueprint).where(
        Blueprint.project_id == project_id,
        Blueprint.version == 2,
    ).order_by(Blueprint.created_at.desc()).limit(1)

    result = await db.execute(stmt)
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Blueprint v2 found for project {project_id}"
        )

    # Get the v2 data from blueprint_json
    v2_data = blueprint.blueprint_json or {}

    # Build provenance from metadata
    provenance = None
    if blueprint.metadata and "provenance" in blueprint.metadata:
        prov_data = blueprint.metadata["provenance"]
        provenance = BlueprintV2Provenance(
            model=prov_data.get("model"),
            model_version=prov_data.get("model_version"),
            generated_at=prov_data.get("generated_at"),
            input_tokens=prov_data.get("input_tokens"),
            output_tokens=prov_data.get("output_tokens"),
            job_id=prov_data.get("job_id"),
        )

    # Parse the v2 data
    from app.schemas.blueprint import (
        BlueprintV2Intent,
        BlueprintV2PredictionTarget,
        BlueprintV2Horizon,
        BlueprintV2OutputFormat,
        BlueprintV2EvaluationPlan,
        BlueprintV2RequiredInput,
    )

    return BlueprintV2Response(
        id=blueprint.id,
        project_id=blueprint.project_id,
        version=blueprint.version,
        status=blueprint.status,
        intent=BlueprintV2Intent(**v2_data.get("intent", {})) if v2_data.get("intent") else None,
        prediction_target=BlueprintV2PredictionTarget(**v2_data.get("prediction_target", {})) if v2_data.get("prediction_target") else None,
        horizon=BlueprintV2Horizon(**v2_data.get("horizon", {})) if v2_data.get("horizon") else None,
        output_format=BlueprintV2OutputFormat(**v2_data.get("output_format", {})) if v2_data.get("output_format") else None,
        evaluation_plan=BlueprintV2EvaluationPlan(**v2_data.get("evaluation_plan", {})) if v2_data.get("evaluation_plan") else None,
        required_inputs=[BlueprintV2RequiredInput(**inp) for inp in v2_data.get("required_inputs", [])] if v2_data.get("required_inputs") else [],
        provenance=provenance,
        created_at=blueprint.created_at,
        updated_at=blueprint.updated_at,
    )


@router.get(
    "/v2/job/{job_id}/status",
    response_model=Dict[str, Any],
    summary="Get Blueprint v2 Build Job Status",
    description="Check the status of a Blueprint v2 build job.",
)
async def get_blueprint_v2_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get the status of a Blueprint v2 build job.

    Returns the current status, progress, and any error information.
    """
    from app.models.pil_job import PILJob

    job = await db.get(PILJob, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Check tenant access
    if job.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job"
        )

    response = {
        "job_id": str(job.id),
        "status": job.status.value,
        "job_type": job.job_type.value,
        "progress": job.progress or 0,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }

    # Add error info if failed
    if job.status.value == "failed":
        response["error"] = job.error_message
        response["error_code"] = job.error_code

    # Add result info if succeeded
    if job.status.value == "succeeded" and job.output_data:
        response["blueprint_id"] = job.output_data.get("blueprint_id")
        response["blueprint_version"] = job.output_data.get("blueprint_version")

    return response


# =============================================================================
# BLUEPRINT V2 EDIT VALIDATION ENDPOINTS (Slice 2B)
# =============================================================================

# Field constraints (mirrors client-side blueprintConstraints.ts)
FIELD_CONSTRAINTS = {
    "projectName": {"minLength": 3, "maxLength": 100},
    "tags": {"maxCount": 5, "maxLength": 30},
}


def validate_core_type_conflicts(
    core_type: CoreType,
    required_inputs: list,
) -> list[BlueprintV2ValidationError]:
    """
    Validate core type conflicts based on required inputs.
    Mirrors client-side validateCoreTypeConflicts.
    """
    errors = []

    # Check if personas are required
    personas_required = any(
        inp.get("type") == "PERSONA_SET" and inp.get("required", False)
        for inp in required_inputs
    )

    # If personas are required, targeted-only is not allowed
    if personas_required and core_type == CoreType.TARGETED:
        errors.append(BlueprintV2ValidationError(
            field="coreType",
            code="CORE_REQUIRES_HYBRID",
            message='Blueprint requires personas. Use "Hybrid" mode to include both collective dynamics and targeted personas.',
            severity="error",
        ))

    # Check if events are required
    events_required = any(
        inp.get("type") == "EVENT_SCRIPT_SET" and inp.get("required", False)
        for inp in required_inputs
    )

    # If events are required, pure collective may need hybrid
    if events_required and core_type == CoreType.COLLECTIVE:
        errors.append(BlueprintV2ValidationError(
            field="coreType",
            code="CORE_MISSING_EVENTS",
            message='Blueprint includes required event simulations. Consider "Hybrid" mode for full event support.',
            severity="warning",
        ))

    return errors


def validate_temporal_settings(
    fields: "BlueprintV2EditableFields",
    recommendations: "BlueprintV2Recommendations",
) -> list[BlueprintV2ValidationError]:
    """
    Validate temporal settings.
    Mirrors client-side validateTemporalSettings.
    """
    from datetime import datetime as dt

    errors = []

    # Backtest mode requires date/time
    if fields.temporal_mode == TemporalMode.BACKTEST:
        if not fields.as_of_date:
            errors.append(BlueprintV2ValidationError(
                field="asOfDate",
                code="BACKTEST_REQUIRES_DATE",
                message="Backtest mode requires an as-of date.",
                severity="error",
            ))

        if not fields.as_of_time:
            errors.append(BlueprintV2ValidationError(
                field="asOfTime",
                code="BACKTEST_REQUIRES_TIME",
                message="Backtest mode requires an as-of time.",
                severity="error",
            ))

        # Validate date is not in future
        if fields.as_of_date and fields.as_of_time:
            try:
                as_of_datetime = dt.fromisoformat(f"{fields.as_of_date}T{fields.as_of_time}")
                if as_of_datetime > dt.now():
                    errors.append(BlueprintV2ValidationError(
                        field="asOfDate",
                        code="FUTURE_DATE_NOT_ALLOWED",
                        message="As-of date cannot be in the future for backtesting.",
                        severity="error",
                    ))
            except ValueError:
                errors.append(BlueprintV2ValidationError(
                    field="asOfDate",
                    code="INVALID_DATE_FORMAT",
                    message="Invalid date/time format. Use ISO format.",
                    severity="error",
                ))

        # Isolation level must be set for backtest
        if not fields.isolation_level:
            errors.append(BlueprintV2ValidationError(
                field="isolationLevel",
                code="BACKTEST_REQUIRES_ISOLATION",
                message="Backtest mode requires an isolation level.",
                severity="error",
            ))

    # Warn if changing from recommended temporal mode
    if fields.temporal_mode != recommendations.temporal_mode:
        rationale = recommendations.temporal_rationale or ""
        errors.append(BlueprintV2ValidationError(
            field="temporalMode",
            code="TEMPORAL_MODE_OVERRIDE",
            message=f'Blueprint recommended "{recommendations.temporal_mode.value}" mode. {rationale}',
            severity="warning",
        ))

    return errors


@router.post(
    "/v2/validate",
    response_model=BlueprintV2ValidationResult,
    summary="Validate Blueprint v2 Edits",
    description="Server-side validation of Blueprint v2 editable fields against constraints.",
)
async def validate_blueprint_v2_fields(
    request: BlueprintV2ValidationRequest,
    current_user: User = Depends(get_current_user),
) -> BlueprintV2ValidationResult:
    """
    Validate Blueprint v2 editable fields against constraints.

    This endpoint mirrors the client-side validation in blueprintConstraints.ts
    and provides server-side validation before allowing finalization.

    Returns validation errors (blocking) and warnings (non-blocking).
    """
    from app.schemas.blueprint import BlueprintV2EditableFields, BlueprintV2Recommendations

    fields = request.fields
    recommendations = request.recommendations

    errors: list[BlueprintV2ValidationError] = []
    warnings: list[BlueprintV2ValidationError] = []

    # 1. Required field validation
    required_fields = ["project_name", "core_type", "temporal_mode"]
    for field_name in required_fields:
        value = getattr(fields, field_name, None)
        if not value or (isinstance(value, str) and not value.strip()):
            errors.append(BlueprintV2ValidationError(
                field=field_name,
                code="FIELD_REQUIRED",
                message=f"{field_name} is required.",
                severity="error",
            ))

    # 2. Project name validation
    if fields.project_name:
        min_len = FIELD_CONSTRAINTS["projectName"]["minLength"]
        max_len = FIELD_CONSTRAINTS["projectName"]["maxLength"]
        if len(fields.project_name) < min_len:
            errors.append(BlueprintV2ValidationError(
                field="projectName",
                code="NAME_TOO_SHORT",
                message=f"Project name must be at least {min_len} characters.",
                severity="error",
            ))
        if len(fields.project_name) > max_len:
            errors.append(BlueprintV2ValidationError(
                field="projectName",
                code="NAME_TOO_LONG",
                message=f"Project name cannot exceed {max_len} characters.",
                severity="error",
            ))

    # 3. Tags validation
    max_tags = FIELD_CONSTRAINTS["tags"]["maxCount"]
    max_tag_len = FIELD_CONSTRAINTS["tags"]["maxLength"]
    if len(fields.tags) > max_tags:
        errors.append(BlueprintV2ValidationError(
            field="tags",
            code="TOO_MANY_TAGS",
            message=f"Maximum {max_tags} tags allowed.",
            severity="error",
        ))
    for tag in fields.tags:
        if len(tag) > max_tag_len:
            errors.append(BlueprintV2ValidationError(
                field="tags",
                code="TAG_TOO_LONG",
                message=f'Tag "{tag}" exceeds {max_tag_len} characters.',
                severity="error",
            ))

    # 4. Core type validation
    if fields.core_type and fields.core_type not in recommendations.allowed_cores:
        allowed = ", ".join(c.value for c in recommendations.allowed_cores)
        errors.append(BlueprintV2ValidationError(
            field="coreType",
            code="CORE_NOT_ALLOWED",
            message=f'"{fields.core_type.value}" is not compatible with this blueprint. Allowed: {allowed}.',
            severity="error",
        ))

    # 5. Core type conflict validation
    core_conflicts = validate_core_type_conflicts(
        fields.core_type,
        [inp for inp in recommendations.required_inputs],
    )
    for conflict in core_conflicts:
        if conflict.severity == "error":
            errors.append(conflict)
        else:
            warnings.append(conflict)

    # 6. Warn if core differs from recommendation
    if fields.core_type != recommendations.recommended_core:
        rationale = recommendations.core_rationale or ""
        warnings.append(BlueprintV2ValidationError(
            field="coreType",
            code="CORE_OVERRIDE",
            message=f'Blueprint recommended "{recommendations.recommended_core.value}". {rationale}',
            severity="warning",
        ))

    # 7. Temporal settings validation
    temporal_errors = validate_temporal_settings(fields, recommendations)
    for err in temporal_errors:
        if err.severity == "error":
            errors.append(err)
        else:
            warnings.append(err)

    return BlueprintV2ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@router.post(
    "/v2/save",
    response_model=Dict[str, Any],
    summary="Save Blueprint v2 Edits",
    description="Save Blueprint v2 edits after validation. Stores override metadata for audit.",
)
async def save_blueprint_v2_edits(
    request: BlueprintV2SaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Save Blueprint v2 edits after server-side validation.

    This endpoint:
    1. Re-validates all fields server-side
    2. Stores the edited configuration
    3. Records override metadata for audit trail
    4. Returns the updated blueprint ID

    Will reject if validation fails (errors present).
    """
    from datetime import datetime as dt

    # First, get the latest Blueprint v2 for this project to get recommendations
    from app.models.blueprint import Blueprint as BlueprintModel
    from app.schemas.blueprint import BlueprintV2Recommendations as RecsSchema

    # Get the project
    from app.models.project import ProjectSpec
    project = await db.get(ProjectSpec, request.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.project_id} not found"
        )

    # Check tenant access
    if project.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )

    # Get latest blueprint v2 for this project
    stmt = select(BlueprintModel).where(
        BlueprintModel.project_id == request.project_id,
        BlueprintModel.version == 2,
    ).order_by(BlueprintModel.created_at.desc()).limit(1)

    result = await db.execute(stmt)
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Blueprint v2 found for project {request.project_id}"
        )

    # Extract recommendations from blueprint
    v2_data = blueprint.blueprint_json or {}
    required_inputs = v2_data.get("required_inputs", [])

    # Build recommendations object for validation
    # (In production, this would come from the stored blueprint recommendations)
    recommendations = RecsSchema(
        project_name=v2_data.get("intent", {}).get("summary", "Untitled Project"),
        tags=[],  # Extract from blueprint if available
        recommended_core=CoreType.COLLECTIVE,  # Default
        allowed_cores=[CoreType.COLLECTIVE, CoreType.HYBRID, CoreType.TARGETED],
        temporal_mode=TemporalMode.LIVE,
        required_inputs=required_inputs,
    )

    # Re-run validation
    validation_request = BlueprintV2ValidationRequest(
        fields=request.fields,
        recommendations=recommendations,
    )
    validation_result = await validate_blueprint_v2_fields(
        validation_request, current_user
    )

    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Validation failed",
                "errors": [e.model_dump() for e in validation_result.errors],
            }
        )

    # Update project with editable fields
    project.name = request.fields.project_name
    # Store additional config in project metadata or blueprint
    if not blueprint.metadata:
        blueprint.metadata = {}

    blueprint.metadata["edits"] = {
        "project_name": request.fields.project_name,
        "tags": request.fields.tags,
        "core_type": request.fields.core_type.value,
        "temporal_mode": request.fields.temporal_mode.value,
        "as_of_date": request.fields.as_of_date,
        "as_of_time": request.fields.as_of_time,
        "timezone": request.fields.timezone,
        "isolation_level": request.fields.isolation_level.value if request.fields.isolation_level else None,
        "updated_at": dt.utcnow().isoformat(),
        "updated_by": str(current_user.id),
    }

    # Store override metadata
    if request.overrides:
        blueprint.metadata["overrides"] = [
            override.model_dump() for override in request.overrides
        ]

    await db.commit()
    await db.refresh(blueprint)

    return {
        "success": True,
        "blueprint_id": str(blueprint.id),
        "project_id": str(project.id),
        "warnings": [w.model_dump() for w in validation_result.warnings],
        "message": "Blueprint v2 edits saved successfully",
    }


# =============================================================================
# Project Guidance Endpoints (Slice 2C: Project Genesis)
# =============================================================================

@router.post(
    "/projects/{project_id}/genesis",
    response_model=TriggerGenesisResponse,
    summary="Trigger Project Genesis Job",
    description="Start the PROJECT_GENESIS job to generate project-specific guidance.",
)
async def trigger_project_genesis(
    project_id: UUID,
    request: TriggerGenesisRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TriggerGenesisResponse:
    """
    Trigger PROJECT_GENESIS job to generate project-specific guidance.

    This job:
    1. Reads the Blueprint v2 configuration
    2. Generates guidance for each workspace section
    3. Stores guidance in project_guidance table with provenance

    Reference: blueprint.md §7 - Section Guidance
    """
    # Validate project exists and user has access
    stmt = select(ProjectSpec).where(
        ProjectSpec.id == project_id,
        ProjectSpec.tenant_id == current_user.id,
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # Get the latest active blueprint for this project
    blueprint_stmt = select(Blueprint).where(
        Blueprint.project_id == project_id,
        Blueprint.tenant_id == current_user.id,
        Blueprint.is_active == True,
    ).order_by(Blueprint.version.desc()).limit(1)

    blueprint_result = await db.execute(blueprint_stmt)
    blueprint = blueprint_result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active blueprint found. Complete the blueprint setup first."
        )

    # Check for existing running genesis job
    running_job_stmt = select(PILJob).where(
        PILJob.project_id == project_id,
        PILJob.job_type == PILJobType.PROJECT_GENESIS.value,
        PILJob.status.in_([PILJobStatus.QUEUED.value, PILJobStatus.RUNNING.value]),
    )
    running_result = await db.execute(running_job_stmt)
    running_job = running_result.scalar_one_or_none()

    if running_job:
        # Return existing job instead of creating new one
        return TriggerGenesisResponse(
            job_id=str(running_job.id),
            status=running_job.status,
            message="Genesis job already in progress",
            project_id=str(project_id),
            blueprint_id=str(blueprint.id),
            blueprint_version=blueprint.version,
        )

    # Create new PIL job for genesis
    job = PILJob(
        tenant_id=current_user.id,
        project_id=project_id,
        blueprint_id=blueprint.id,
        job_type=PILJobType.PROJECT_GENESIS.value,
        job_name=f"Project Genesis for {project.name}",
        input_params={
            "project_id": str(project_id),
            "blueprint_id": str(blueprint.id),
            "blueprint_version": blueprint.version,
            "force_regenerate": request.force_regenerate if request else False,
        },
        created_by=current_user.id,
        status=PILJobStatus.QUEUED.value,
        stages_total=len(GuidanceSection),  # One stage per section
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Dispatch the job to Celery
    dispatch_pil_job(str(job.id))

    return TriggerGenesisResponse(
        job_id=str(job.id),
        status=job.status,
        message="Project genesis job queued successfully",
        project_id=str(project_id),
        blueprint_id=str(blueprint.id),
        blueprint_version=blueprint.version,
    )


@router.get(
    "/projects/{project_id}/guidance",
    response_model=ProjectGuidanceListResponse,
    summary="Get All Project Guidance",
    description="Get AI-generated guidance for all workspace sections.",
)
async def get_project_guidance(
    project_id: UUID,
    include_stale: bool = Query(False, description="Include stale guidance"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectGuidanceListResponse:
    """
    Get project-specific guidance for all workspace sections.

    Returns guidance generated by PROJECT_GENESIS job including:
    - what_to_input: What data to provide
    - recommended_sources: Suggested data sources
    - checklist: Actionable items
    - suggested_actions: AI-assisted actions
    - provenance: Audit trail for the guidance
    """
    # Validate project access
    stmt = select(ProjectSpec).where(
        ProjectSpec.id == project_id,
        ProjectSpec.tenant_id == current_user.id,
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # Get active blueprint for version info
    blueprint_stmt = select(Blueprint).where(
        Blueprint.project_id == project_id,
        Blueprint.is_active == True,
    ).order_by(Blueprint.version.desc()).limit(1)
    blueprint_result = await db.execute(blueprint_stmt)
    blueprint = blueprint_result.scalar_one_or_none()

    # Query guidance for all sections
    guidance_stmt = select(ProjectGuidance).where(
        ProjectGuidance.project_id == project_id,
        ProjectGuidance.tenant_id == current_user.id,
        ProjectGuidance.is_active == True,
    )

    if not include_stale:
        guidance_stmt = guidance_stmt.where(
            ProjectGuidance.status != GuidanceStatus.STALE.value
        )

    guidance_stmt = guidance_stmt.order_by(ProjectGuidance.section)
    guidance_result = await db.execute(guidance_stmt)
    guidance_records = guidance_result.scalars().all()

    # Convert to response models
    sections = []
    for record in guidance_records:
        sections.append(ProjectGuidanceResponse(
            id=str(record.id),
            project_id=str(record.project_id),
            blueprint_id=str(record.blueprint_id) if record.blueprint_id else None,
            blueprint_version=record.blueprint_version,
            guidance_version=record.guidance_version,
            section=record.section,
            status=record.status,
            section_title=record.section_title,
            section_description=record.section_description,
            what_to_input=record.what_to_input,
            recommended_sources=record.recommended_sources,
            checklist=record.checklist,
            suggested_actions=record.suggested_actions,
            tips=record.tips,
            job_id=str(record.job_id) if record.job_id else None,
            llm_call_id=record.llm_call_id,
            created_at=record.created_at.isoformat() if record.created_at else None,
            updated_at=record.updated_at.isoformat() if record.updated_at else None,
        ))

    return ProjectGuidanceListResponse(
        project_id=str(project_id),
        blueprint_id=str(blueprint.id) if blueprint else None,
        blueprint_version=blueprint.version if blueprint else None,
        sections=sections,
        total_sections=len(sections),
        ready_sections=len([s for s in sections if s.status == GuidanceStatus.READY.value]),
    )


@router.get(
    "/projects/{project_id}/guidance/{section}",
    response_model=ProjectGuidanceResponse,
    summary="Get Section Guidance",
    description="Get AI-generated guidance for a specific workspace section.",
)
async def get_section_guidance(
    project_id: UUID,
    section: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectGuidanceResponse:
    """
    Get project-specific guidance for a single workspace section.
    """
    # Validate section name
    try:
        section_enum = GuidanceSection(section)
    except ValueError:
        valid_sections = [s.value for s in GuidanceSection]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid section: {section}. Valid sections: {valid_sections}"
        )

    # Validate project access
    project_stmt = select(ProjectSpec).where(
        ProjectSpec.id == project_id,
        ProjectSpec.tenant_id == current_user.id,
    )
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # Query guidance for specific section
    guidance_stmt = select(ProjectGuidance).where(
        ProjectGuidance.project_id == project_id,
        ProjectGuidance.tenant_id == current_user.id,
        ProjectGuidance.section == section,
        ProjectGuidance.is_active == True,
    )
    guidance_result = await db.execute(guidance_stmt)
    record = guidance_result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No guidance found for section '{section}'. Run project genesis first."
        )

    return ProjectGuidanceResponse(
        id=str(record.id),
        project_id=str(record.project_id),
        blueprint_id=str(record.blueprint_id) if record.blueprint_id else None,
        blueprint_version=record.blueprint_version,
        guidance_version=record.guidance_version,
        section=record.section,
        status=record.status,
        section_title=record.section_title,
        section_description=record.section_description,
        what_to_input=record.what_to_input,
        recommended_sources=record.recommended_sources,
        checklist=record.checklist,
        suggested_actions=record.suggested_actions,
        tips=record.tips,
        job_id=str(record.job_id) if record.job_id else None,
        llm_call_id=record.llm_call_id,
        created_at=record.created_at.isoformat() if record.created_at else None,
        updated_at=record.updated_at.isoformat() if record.updated_at else None,
    )


@router.post(
    "/projects/{project_id}/guidance/regenerate",
    response_model=TriggerGenesisResponse,
    summary="Regenerate Project Guidance",
    description="Mark all guidance as stale and trigger regeneration.",
)
async def regenerate_project_guidance(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TriggerGenesisResponse:
    """
    Regenerate all project guidance.

    This endpoint:
    1. Marks all existing guidance as stale
    2. Triggers a new PROJECT_GENESIS job
    3. New guidance will have incremented guidance_version
    """
    # Validate project access
    project_stmt = select(ProjectSpec).where(
        ProjectSpec.id == project_id,
        ProjectSpec.tenant_id == current_user.id,
    )
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # Mark all existing guidance as stale
    from sqlalchemy import update
    await db.execute(
        update(ProjectGuidance)
        .where(
            ProjectGuidance.project_id == project_id,
            ProjectGuidance.is_active == True,
        )
        .values(status=GuidanceStatus.STALE.value, updated_at=dt.utcnow())
    )
    await db.commit()

    # Trigger new genesis job with force_regenerate
    request = TriggerGenesisRequest(force_regenerate=True)
    return await trigger_project_genesis(
        project_id=project_id,
        request=request,
        db=db,
        current_user=current_user,
    )


@router.get(
    "/projects/{project_id}/genesis/status",
    summary="Get Genesis Job Status",
    description="Check the status of the current or latest genesis job.",
)
async def get_genesis_job_status(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get the status of the current or latest PROJECT_GENESIS job.
    """
    # Validate project access
    project_stmt = select(ProjectSpec).where(
        ProjectSpec.id == project_id,
        ProjectSpec.tenant_id == current_user.id,
    )
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )

    # Get latest genesis job
    job_stmt = select(PILJob).where(
        PILJob.project_id == project_id,
        PILJob.job_type == PILJobType.PROJECT_GENESIS.value,
    ).order_by(PILJob.created_at.desc()).limit(1)

    job_result = await db.execute(job_stmt)
    job = job_result.scalar_one_or_none()

    if not job:
        return {
            "has_job": False,
            "message": "No genesis job found. Trigger genesis to generate guidance.",
        }

    return {
        "has_job": True,
        "job_id": str(job.id),
        "status": job.status,
        "progress_percent": job.progress_percent,
        "stage_name": job.stage_name,
        "stages_completed": job.stages_completed,
        "stages_total": job.stages_total,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
