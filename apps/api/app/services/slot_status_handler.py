"""
Slot Status Handler Service (blueprint.md §7.2, blueprint_v3.md §4.5)
Reference: blueprint.md §7.2 Checklist With Alerts

This service handles post-job status updates for BlueprintSlot and BlueprintTask.
After each PIL job completes, the status handler determines the new status based on:
- Job success/failure
- Validation results
- Alignment scores
- Compilation status

Status Transitions:
- NOT_STARTED → PROCESSING (when job starts)
- PROCESSING → READY (job succeeds with good scores)
- PROCESSING → NEEDS_ATTENTION (job succeeds with low scores or warnings)
- PROCESSING → BLOCKED (job fails or critical error)
- Any → NOT_STARTED (if data is removed)
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blueprint import (
    Blueprint,
    BlueprintSlot,
    BlueprintTask,
    AlertState,
)
from app.models.pil_job import (
    PILJob,
    PILJobStatus,
    PILJobType,
    PILArtifact,
)


# =============================================================================
# Slot Status Thresholds (configurable)
# =============================================================================

# Alignment score thresholds
ALIGNMENT_READY_THRESHOLD = 80.0  # >= 80 is READY
ALIGNMENT_WARNING_THRESHOLD = 60.0  # 60-79 is not great but acceptable
# < 60 is NEEDS_ATTENTION

# Quality score thresholds
QUALITY_READY_THRESHOLD = 0.8  # >= 0.8 is READY
QUALITY_WARNING_THRESHOLD = 0.5  # 0.5-0.79 is acceptable


# =============================================================================
# Status Update Functions
# =============================================================================

async def update_slot_status_from_job(
    session: AsyncSession,
    job: PILJob,
    result: Optional[Dict[str, Any]] = None,
) -> Optional[AlertState]:
    """
    Update BlueprintSlot status based on completed job.

    Called after PIL job completion to update the slot status.
    Returns the new AlertState or None if no slot was updated.

    Logic:
    - SLOT_VALIDATION: Check validation_passed and quality_score
    - SLOT_ALIGNMENT_SCORING: Check alignment_score
    - SLOT_COMPILATION: Mark fulfilled if successful
    """
    if not job.slot_id or not job.blueprint_id:
        return None

    try:
        slot_uuid = UUID(job.slot_id)
    except (ValueError, TypeError):
        return None

    # Get the slot
    slot_result = await session.execute(
        select(BlueprintSlot).where(BlueprintSlot.id == slot_uuid)
    )
    slot = slot_result.scalar_one_or_none()

    if not slot:
        return None

    new_status: Optional[AlertState] = None
    status_reason: Optional[str] = None
    fulfilled = slot.fulfilled

    job_type = job.job_type
    job_status = job.status
    job_result = result or job.result or {}

    # Handle job failure
    if job_status == PILJobStatus.FAILED.value:
        new_status = AlertState.BLOCKED
        status_reason = f"Job failed: {job.error_message or 'Unknown error'}"

    # Handle job success based on job type
    elif job_status == PILJobStatus.SUCCEEDED.value:

        if job_type == PILJobType.SLOT_VALIDATION.value:
            new_status, status_reason = _evaluate_validation_result(job_result)

        elif job_type == PILJobType.SLOT_ALIGNMENT_SCORING.value:
            new_status, status_reason = _evaluate_alignment_result(job_result)

        elif job_type == PILJobType.SLOT_COMPILATION.value:
            # Successful compilation means the slot is fulfilled and ready
            new_status = AlertState.READY
            fulfilled = True
            status_reason = "Data compiled and ready for simulation"

        elif job_type == PILJobType.SLOT_SUMMARIZATION.value:
            # Summarization doesn't change status, just adds metadata
            pass

    # Update the slot if we determined a new status
    if new_status:
        update_data = {
            "status": new_status.value,
            "updated_at": datetime.utcnow(),
        }
        if status_reason:
            update_data["status_reason"] = status_reason
        if fulfilled != slot.fulfilled:
            update_data["fulfilled"] = fulfilled

        await session.execute(
            update(BlueprintSlot)
            .where(BlueprintSlot.id == slot_uuid)
            .values(**update_data)
        )
        await session.commit()

    # After slot status update, update linked tasks
    if new_status:
        await update_linked_tasks_status(session, slot)

    return new_status


def _evaluate_validation_result(result: Dict[str, Any]) -> tuple[AlertState, str]:
    """
    Evaluate validation job result and determine status.
    """
    schema_valid = result.get("schema_valid", False)
    quality_score = result.get("quality_score", 0.0)
    issues = result.get("issues", [])

    if not schema_valid:
        return (
            AlertState.BLOCKED,
            f"Schema validation failed. {len(issues)} issue(s) found."
        )

    if quality_score >= QUALITY_READY_THRESHOLD:
        if issues:
            return (
                AlertState.NEEDS_ATTENTION,
                f"Data quality good ({quality_score:.0%}) but {len(issues)} minor issue(s)"
            )
        return (AlertState.READY, f"Validation passed. Quality score: {quality_score:.0%}")

    if quality_score >= QUALITY_WARNING_THRESHOLD:
        return (
            AlertState.NEEDS_ATTENTION,
            f"Data quality acceptable ({quality_score:.0%}). Consider improvements."
        )

    return (
        AlertState.NEEDS_ATTENTION,
        f"Low data quality ({quality_score:.0%}). Review data source."
    )


def _evaluate_alignment_result(result: Dict[str, Any]) -> tuple[AlertState, str]:
    """
    Evaluate alignment scoring job result and determine status.
    """
    alignment_score = result.get("alignment_score", 0.0)
    goal_relevance = result.get("goal_relevance", "unknown")
    recommendations = result.get("recommendations", [])

    if alignment_score >= ALIGNMENT_READY_THRESHOLD:
        return (
            AlertState.READY,
            f"Excellent alignment ({alignment_score:.0f}%). Data well-suited for project."
        )

    if alignment_score >= ALIGNMENT_WARNING_THRESHOLD:
        rec_text = f" Recommendations: {len(recommendations)}" if recommendations else ""
        return (
            AlertState.NEEDS_ATTENTION,
            f"Moderate alignment ({alignment_score:.0f}%).{rec_text}"
        )

    return (
        AlertState.NEEDS_ATTENTION,
        f"Low alignment ({alignment_score:.0f}%). Consider alternative data sources."
    )


async def update_linked_tasks_status(
    session: AsyncSession,
    slot: BlueprintSlot,
) -> None:
    """
    Update status of tasks linked to this slot.

    A task's status is derived from its linked slots:
    - If ALL linked slots are READY → task is READY
    - If ANY linked slot is BLOCKED → task is BLOCKED
    - If ANY linked slot is NEEDS_ATTENTION → task is NEEDS_ATTENTION
    - Otherwise → NOT_STARTED
    """
    # Get tasks linked to this slot
    tasks_result = await session.execute(
        select(BlueprintTask).where(
            BlueprintTask.blueprint_id == slot.blueprint_id
        )
    )
    tasks = tasks_result.scalars().all()

    slot_id_str = str(slot.id)

    for task in tasks:
        if not task.linked_slot_ids:
            continue

        if slot_id_str not in task.linked_slot_ids:
            continue

        # Get all linked slots for this task
        linked_slots_result = await session.execute(
            select(BlueprintSlot).where(
                BlueprintSlot.blueprint_id == task.blueprint_id,
                BlueprintSlot.id.in_([UUID(sid) for sid in task.linked_slot_ids if sid])
            )
        )
        linked_slots = linked_slots_result.scalars().all()

        if not linked_slots:
            continue

        # Determine task status based on linked slots
        new_task_status, task_status_reason = _aggregate_slot_statuses(linked_slots)

        await session.execute(
            update(BlueprintTask)
            .where(BlueprintTask.id == task.id)
            .values(
                status=new_task_status.value,
                status_reason=task_status_reason,
                updated_at=datetime.utcnow(),
            )
        )

    await session.commit()


def _aggregate_slot_statuses(slots: list[BlueprintSlot]) -> tuple[AlertState, str]:
    """
    Aggregate statuses of multiple slots into a single task status.
    """
    if not slots:
        return (AlertState.NOT_STARTED, "No linked slots")

    statuses = [slot.status for slot in slots]

    # Check for blocked
    blocked_count = sum(1 for s in statuses if s == AlertState.BLOCKED.value)
    if blocked_count > 0:
        return (
            AlertState.BLOCKED,
            f"{blocked_count} of {len(slots)} slot(s) blocked"
        )

    # Check for needs_attention
    attention_count = sum(1 for s in statuses if s == AlertState.NEEDS_ATTENTION.value)
    if attention_count > 0:
        return (
            AlertState.NEEDS_ATTENTION,
            f"{attention_count} of {len(slots)} slot(s) need attention"
        )

    # Check for all ready
    ready_count = sum(1 for s in statuses if s == AlertState.READY.value)
    if ready_count == len(slots):
        return (
            AlertState.READY,
            "All linked slots are ready"
        )

    # Some not started
    not_started_count = sum(1 for s in statuses if s == AlertState.NOT_STARTED.value)
    return (
        AlertState.NOT_STARTED,
        f"{not_started_count} of {len(slots)} slot(s) not started"
    )


async def mark_slot_processing(
    session: AsyncSession,
    slot_id: str,
    job_type: str,
) -> None:
    """
    Mark a slot as processing when a job starts.
    Called when a slot-related job begins execution.
    """
    try:
        slot_uuid = UUID(slot_id)
    except (ValueError, TypeError):
        return

    # Only transition from NOT_STARTED to effectively "processing"
    # We keep the same status but add a status_reason indicating processing
    result = await session.execute(
        select(BlueprintSlot).where(BlueprintSlot.id == slot_uuid)
    )
    slot = result.scalar_one_or_none()

    if slot and slot.status == AlertState.NOT_STARTED.value:
        await session.execute(
            update(BlueprintSlot)
            .where(BlueprintSlot.id == slot_uuid)
            .values(
                status_reason=f"Processing: {job_type}",
                updated_at=datetime.utcnow(),
            )
        )
        await session.commit()


async def reset_slot_status(
    session: AsyncSession,
    slot_id: str,
) -> None:
    """
    Reset slot status to NOT_STARTED.
    Called when data is removed from a slot.
    """
    try:
        slot_uuid = UUID(slot_id)
    except (ValueError, TypeError):
        return

    await session.execute(
        update(BlueprintSlot)
        .where(BlueprintSlot.id == slot_uuid)
        .values(
            status=AlertState.NOT_STARTED.value,
            status_reason=None,
            fulfilled=False,
            fulfilled_by=None,
            fulfillment_method=None,
            alignment_score=None,
            alignment_reasons=None,
            updated_at=datetime.utcnow(),
        )
    )
    await session.commit()


# =============================================================================
# High-level Pipeline Integration
# =============================================================================

async def process_slot_pipeline_completion(
    session: AsyncSession,
    job: PILJob,
) -> Dict[str, Any]:
    """
    Process completion of a slot pipeline job and return status update info.

    This is the main entry point called from pil_tasks.py after job completion.
    Returns a dict with:
    - slot_id: The slot that was updated
    - previous_status: Status before update
    - new_status: Status after update
    - status_reason: Reason for the new status
    """
    if not job.slot_id:
        return {"error": "No slot_id in job"}

    # Get current slot status
    try:
        slot_uuid = UUID(job.slot_id)
    except (ValueError, TypeError):
        return {"error": f"Invalid slot_id: {job.slot_id}"}

    slot_result = await session.execute(
        select(BlueprintSlot).where(BlueprintSlot.id == slot_uuid)
    )
    slot = slot_result.scalar_one_or_none()

    if not slot:
        return {"error": f"Slot not found: {job.slot_id}"}

    previous_status = slot.status

    # Update status based on job result
    new_status = await update_slot_status_from_job(session, job)

    # Refresh slot to get updated values
    await session.refresh(slot)

    return {
        "slot_id": str(slot.id),
        "slot_name": slot.slot_name,
        "previous_status": previous_status,
        "new_status": slot.status,
        "status_reason": slot.status_reason,
        "fulfilled": slot.fulfilled,
        "alignment_score": slot.alignment_score,
    }
