"""
Calibration Background Tasks - PHASE 4: Calibration Minimal Closed Loop
Reference: project.md Phase 4 - Calibration Lab Backend

Background Celery tasks for running calibration jobs.
Executes deterministic calibration algorithm in async mode.

Key principles:
- Deterministic: Same data + same config = same results (no LLM)
- Fork-not-mutate (C1): Never modify historical RunOutcome rows
- Auditable: All iterations stored for debugging
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
import uuid

from celery import shared_task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.tasks.base import (
    TenantAwareTask,
    JobContext,
    JobStatus,
    JobResult,
)
from app.models.calibration import (
    CalibrationJob,
    CalibrationIteration,
    CalibrationJobStatus,
)

logger = logging.getLogger(__name__)


def get_async_session():
    """Create fresh async session with new engine for current event loop."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(
    bind=True,
    base=TenantAwareTask,
    name="app.tasks.calibration.run_calibration_job",
    max_retries=1,  # Calibration jobs should not retry (deterministic)
    default_retry_delay=60,
    soft_time_limit=3600,  # 1 hour max
    time_limit=3660,
)
def run_calibration_job(
    self,
    job_id: str,
    context: dict,
) -> dict:
    """
    Execute a calibration job in the background.

    This is the main entry point for background calibration execution.
    Called when a user starts a calibration job via the API.

    Args:
        job_id: UUID of the CalibrationJob record
        context: JobContext as dict

    Returns:
        JobResult as dict with calibration results
    """
    ctx = JobContext.from_dict(context)
    return run_async(_run_calibration_job(job_id, ctx))


async def _run_calibration_job(job_id: str, context: JobContext) -> dict:
    """
    Async implementation of calibration job execution.

    Phases:
    1. Load job configuration
    2. Update status to RUNNING
    3. Load calibration samples from RunOutcome data
    4. Run deterministic calibration algorithm
    5. Store results and update job status
    """
    started_at = datetime.utcnow()
    start_time = time.perf_counter()

    AsyncSessionLocal = get_async_session()
    async with AsyncSessionLocal() as db:
        try:
            # Phase 1: Load job
            job = await _load_job(db, job_id)
            if not job:
                return JobResult(
                    job_id=context.job_id,
                    status=JobStatus.FAILED,
                    error=f"Calibration job not found: {job_id}",
                ).to_dict()

            # Check if job was canceled
            if job.status == CalibrationJobStatus.CANCELED.value:
                return JobResult(
                    job_id=context.job_id,
                    status=JobStatus.CANCELLED,
                    result={"job_id": job_id, "message": "Job was canceled"},
                ).to_dict()

            # Phase 2: Update to RUNNING
            await _update_job_status(
                db, job_id, CalibrationJobStatus.RUNNING, started_at=started_at
            )
            await db.commit()

            # Phase 3: Run calibration using the service
            from app.services.calibration_service import CalibrationService
            from app.schemas.calibration import CalibrationJobStatus as CalibrationJobStatusEnum

            service = CalibrationService(db)
            result = await service.run_calibration(job=job)

            # Phase 4: Compute final timing
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            completed_at = datetime.utcnow()

            # Check result status (result is a Pydantic model)
            if result.status == CalibrationJobStatusEnum.SUCCEEDED:
                return JobResult(
                    job_id=context.job_id,
                    status=JobStatus.COMPLETED,
                    result={
                        "job_id": job_id,
                        "best_accuracy": result.metrics.accuracy if result.metrics else None,
                        "best_bin_count": result.best_bin_count,
                        "n_samples": result.metrics.n_samples if result.metrics else None,
                        "duration_ms": elapsed_ms,
                    },
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=elapsed_ms,
                ).to_dict()
            else:
                return JobResult(
                    job_id=context.job_id,
                    status=JobStatus.FAILED,
                    error=result.error_message or "Unknown error",
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=elapsed_ms,
                ).to_dict()

        except Exception as e:
            logger.exception(f"Calibration job {job_id} failed: {e}")
            await db.rollback()

            # Update job status to FAILED
            try:
                await _update_job_status(
                    db,
                    job_id,
                    CalibrationJobStatus.FAILED,
                    error_message=str(e),
                    finished_at=datetime.utcnow(),
                )
                await db.commit()
            except Exception:
                pass  # Don't fail on status update

            return JobResult(
                job_id=context.job_id,
                status=JobStatus.FAILED,
                error=str(e),
                started_at=started_at,
                completed_at=datetime.utcnow(),
            ).to_dict()


async def _load_job(db: AsyncSession, job_id: str) -> Optional[CalibrationJob]:
    """Load calibration job from database."""
    query = select(CalibrationJob).where(CalibrationJob.id == uuid.UUID(job_id))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def _update_job_status(
    db: AsyncSession,
    job_id: str,
    status: CalibrationJobStatus,
    started_at: Optional[datetime] = None,
    finished_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
):
    """Update calibration job status."""
    update_data = {
        "status": status.value,
    }

    if started_at:
        update_data["started_at"] = started_at
    if finished_at:
        update_data["finished_at"] = finished_at
    if error_message:
        update_data["error_message"] = error_message

    stmt = (
        update(CalibrationJob)
        .where(CalibrationJob.id == uuid.UUID(job_id))
        .values(**update_data)
    )
    await db.execute(stmt)


@shared_task(
    bind=True,
    base=TenantAwareTask,
    name="app.tasks.calibration.cancel_calibration_job",
)
def cancel_calibration_job(self, job_id: str, context: dict) -> dict:
    """
    Cancel a running calibration job.

    Sets status to CANCELED so the running task will check and exit.
    """
    ctx = JobContext.from_dict(context)
    return run_async(_cancel_calibration_job(job_id, ctx))


async def _cancel_calibration_job(job_id: str, context: JobContext) -> dict:
    """Cancel a calibration job."""
    AsyncSessionLocal = get_async_session()
    async with AsyncSessionLocal() as db:
        # Load job
        job = await _load_job(db, job_id)
        if not job:
            return JobResult(
                job_id=context.job_id,
                status=JobStatus.FAILED,
                error=f"Job not found: {job_id}",
            ).to_dict()

        # Check if job is in a cancelable state
        if job.status in (
            CalibrationJobStatus.SUCCEEDED.value,
            CalibrationJobStatus.FAILED.value,
            CalibrationJobStatus.CANCELED.value,
        ):
            return JobResult(
                job_id=context.job_id,
                status=JobStatus.COMPLETED,
                result={
                    "job_id": job_id,
                    "message": f"Job already in terminal state: {job.status}",
                },
            ).to_dict()

        # Update to CANCELED
        await _update_job_status(
            db,
            job_id,
            CalibrationJobStatus.CANCELED,
            finished_at=datetime.utcnow(),
        )
        await db.commit()

        return JobResult(
            job_id=context.job_id,
            status=JobStatus.COMPLETED,
            result={
                "job_id": job_id,
                "status": CalibrationJobStatus.CANCELED.value,
                "message": "Job canceled successfully",
            },
        ).to_dict()
