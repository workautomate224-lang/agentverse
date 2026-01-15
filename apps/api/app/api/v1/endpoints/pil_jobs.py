"""
PIL Job API Endpoints
Reference: blueprint.md §5
Project Intelligence Layer job management for background AI processing.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.pil_job import (
    PILJob,
    PILArtifact,
    PILJobStatus,
    PILJobType,
    ArtifactType,
)
from app.schemas.blueprint import (
    PILJobCreate,
    PILJobUpdate,
    PILJobResponse,
    PILArtifactCreate,
    PILArtifactResponse,
    JobNotification,
)
from app.tasks.pil_tasks import dispatch_pil_job

router = APIRouter()


# =============================================================================
# Job Endpoints
# =============================================================================

@router.get("/", response_model=list[PILJobResponse])
async def list_jobs(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    blueprint_id: Optional[UUID] = Query(None, description="Filter by blueprint ID"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PILJob]:
    """
    List PIL jobs for the current tenant.
    Reference: blueprint.md §5.3
    """
    query = select(PILJob).where(PILJob.tenant_id == current_user.tenant_id)

    if project_id:
        query = query.where(PILJob.project_id == project_id)
    if blueprint_id:
        query = query.where(PILJob.blueprint_id == blueprint_id)
    if job_type:
        query = query.where(PILJob.job_type == job_type)
    if status_filter:
        query = query.where(PILJob.status == status_filter)

    query = query.offset(skip).limit(limit).order_by(PILJob.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/active", response_model=list[PILJobResponse])
async def list_active_jobs(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PILJob]:
    """
    List active (queued or running) jobs.
    Useful for showing in-progress operations in the UI.
    """
    query = select(PILJob).where(
        PILJob.tenant_id == current_user.tenant_id,
        PILJob.status.in_([PILJobStatus.QUEUED.value, PILJobStatus.RUNNING.value]),
    )

    if project_id:
        query = query.where(PILJob.project_id == project_id)

    query = query.order_by(PILJob.created_at.asc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{job_id}", response_model=PILJobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PILJob:
    """
    Get a specific job by ID.
    """
    result = await db.execute(
        select(PILJob).where(
            PILJob.id == job_id,
            PILJob.tenant_id == current_user.tenant_id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return job


@router.post("/", response_model=PILJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: PILJobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PILJob:
    """
    Create a new PIL job.
    Jobs are queued and processed asynchronously by Celery workers.
    """
    job = PILJob(
        tenant_id=current_user.tenant_id,
        project_id=job_in.project_id,
        blueprint_id=job_in.blueprint_id,
        job_type=job_in.job_type,
        job_name=job_in.job_name,
        priority=job_in.priority or "normal",
        status=PILJobStatus.QUEUED,
        input_params=job_in.input_params,
        slot_id=job_in.slot_id,
        task_id=job_in.task_id,
        created_by=str(current_user.id),
    )

    db.add(job)
    await db.flush()
    await db.refresh(job)
    await db.commit()

    # Dispatch to Celery for background processing
    dispatch_pil_job.delay(str(job.id))

    return job


@router.put("/{job_id}", response_model=PILJobResponse)
async def update_job(
    job_id: UUID,
    job_update: PILJobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PILJob:
    """
    Update a job (typically for progress updates from workers).
    """
    result = await db.execute(
        select(PILJob).where(
            PILJob.id == job_id,
            PILJob.tenant_id == current_user.tenant_id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    update_data = job_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    await db.flush()
    await db.refresh(job)

    return job


@router.post("/{job_id}/cancel", response_model=PILJobResponse)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PILJob:
    """
    Cancel a queued or running job.
    """
    result = await db.execute(
        select(PILJob).where(
            PILJob.id == job_id,
            PILJob.tenant_id == current_user.tenant_id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status not in [PILJobStatus.QUEUED.value, PILJobStatus.RUNNING.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status}",
        )

    job.status = PILJobStatus.CANCELLED

    # Cancel Celery task if running
    if job.celery_task_id:
        from celery import current_app
        current_app.control.revoke(job.celery_task_id, terminate=True)

    await db.flush()
    await db.refresh(job)
    await db.commit()

    return job


@router.post("/{job_id}/retry", response_model=PILJobResponse)
async def retry_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PILJob:
    """
    Retry a failed job.
    """
    result = await db.execute(
        select(PILJob).where(
            PILJob.id == job_id,
            PILJob.tenant_id == current_user.tenant_id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status != PILJobStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retry failed jobs",
        )

    if job.retry_count >= job.max_retries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum retries ({job.max_retries}) exceeded",
        )

    job.status = PILJobStatus.QUEUED
    job.retry_count += 1
    job.error_message = None
    job.progress_percent = 0
    job.stage_name = None

    await db.flush()
    await db.refresh(job)
    await db.commit()

    # Dispatch to Celery again for retry
    dispatch_pil_job.delay(str(job.id))

    return job


# =============================================================================
# Artifact Endpoints
# =============================================================================

@router.get("/artifacts/", response_model=list[PILArtifactResponse])
async def list_artifacts(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    blueprint_id: Optional[UUID] = Query(None, description="Filter by blueprint ID"),
    artifact_type: Optional[str] = Query(None, description="Filter by artifact type"),
    slot_id: Optional[str] = Query(None, description="Filter by slot ID"),
    job_id: Optional[UUID] = Query(None, description="Filter by job ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PILArtifact]:
    """
    List PIL artifacts.
    Reference: blueprint.md §5.6
    """
    query = select(PILArtifact).where(PILArtifact.tenant_id == current_user.tenant_id)

    if project_id:
        query = query.where(PILArtifact.project_id == project_id)
    if blueprint_id:
        query = query.where(PILArtifact.blueprint_id == blueprint_id)
    if artifact_type:
        query = query.where(PILArtifact.artifact_type == artifact_type)
    if slot_id:
        query = query.where(PILArtifact.slot_id == slot_id)
    if job_id:
        query = query.where(PILArtifact.job_id == job_id)

    query = query.offset(skip).limit(limit).order_by(PILArtifact.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/artifacts/{artifact_id}", response_model=PILArtifactResponse)
async def get_artifact(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PILArtifact:
    """
    Get a specific artifact by ID.
    """
    result = await db.execute(
        select(PILArtifact).where(
            PILArtifact.id == artifact_id,
            PILArtifact.tenant_id == current_user.tenant_id,
        )
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    return artifact


@router.post("/artifacts/", response_model=PILArtifactResponse, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    artifact_in: PILArtifactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PILArtifact:
    """
    Create a new PIL artifact.
    Typically called by job workers when producing output.
    """
    artifact = PILArtifact(
        tenant_id=current_user.tenant_id,
        project_id=artifact_in.project_id,
        blueprint_id=artifact_in.blueprint_id,
        blueprint_version=artifact_in.blueprint_version,
        artifact_type=artifact_in.artifact_type,
        artifact_name=artifact_in.artifact_name,
        job_id=artifact_in.job_id,
        slot_id=artifact_in.slot_id,
        task_id=artifact_in.task_id,
        content=artifact_in.content,
        content_text=artifact_in.content_text,
        alignment_score=artifact_in.alignment_score,
        quality_score=artifact_in.quality_score,
        validation_passed=artifact_in.validation_passed,
    )

    db.add(artifact)
    await db.flush()
    await db.refresh(artifact)

    return artifact


# =============================================================================
# Statistics & Dashboard
# =============================================================================

@router.get("/stats")
async def get_job_stats(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get job statistics for the Job Center dashboard.
    """
    base_query = select(PILJob).where(PILJob.tenant_id == current_user.tenant_id)

    if project_id:
        base_query = base_query.where(PILJob.project_id == project_id)

    # Count by status
    status_counts = {}
    for status_val in PILJobStatus:
        count_result = await db.execute(
            select(func.count(PILJob.id)).where(
                PILJob.tenant_id == current_user.tenant_id,
                PILJob.status == status_val.value,
                *([PILJob.project_id == project_id] if project_id else []),
            )
        )
        status_counts[status_val.value] = count_result.scalar() or 0

    # Count by type
    type_counts = {}
    for type_val in PILJobType:
        count_result = await db.execute(
            select(func.count(PILJob.id)).where(
                PILJob.tenant_id == current_user.tenant_id,
                PILJob.job_type == type_val.value,
                *([PILJob.project_id == project_id] if project_id else []),
            )
        )
        type_counts[type_val.value] = count_result.scalar() or 0

    # Total counts
    total_result = await db.execute(
        select(func.count(PILJob.id)).where(
            PILJob.tenant_id == current_user.tenant_id,
            *([PILJob.project_id == project_id] if project_id else []),
        )
    )
    total = total_result.scalar() or 0

    # Artifact count
    artifact_result = await db.execute(
        select(func.count(PILArtifact.id)).where(
            PILArtifact.tenant_id == current_user.tenant_id,
            *([PILArtifact.project_id == project_id] if project_id else []),
        )
    )
    artifact_count = artifact_result.scalar() or 0

    return {
        "total_jobs": total,
        "by_status": status_counts,
        "by_type": type_counts,
        "total_artifacts": artifact_count,
        "active_jobs": status_counts.get("queued", 0) + status_counts.get("running", 0),
        "failed_jobs": status_counts.get("failed", 0),
        "success_rate": round(
            status_counts.get("succeeded", 0) / total * 100 if total > 0 else 0,
            2
        ),
    }


@router.get("/{job_id}/artifacts", response_model=list[PILArtifactResponse])
async def get_job_artifacts(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PILArtifact]:
    """
    Get all artifacts produced by a specific job.
    """
    # Verify job access
    job_result = await db.execute(
        select(PILJob).where(
            PILJob.id == job_id,
            PILJob.tenant_id == current_user.tenant_id,
        )
    )
    if not job_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found")

    result = await db.execute(
        select(PILArtifact).where(PILArtifact.job_id == job_id)
    )
    return result.scalars().all()
