"""
Chaos Engineering Tasks - Step 3.2

Tasks for chaos testing and validation:
- exit_worker: Intentionally exit worker process for restart testing

These tasks are used by the /ops/chaos endpoints for Step 3.1 validation.
Only enabled in staging environment.
"""

import logging
import os

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="chaos.exit_worker")
def exit_worker(reason: str, correlation_id: str) -> dict:
    """
    Intentionally exit the worker process for chaos testing.

    Railway will auto-restart the worker, which will:
    1. Generate a new WORKER_BOOT_ID
    2. Store the new boot_id in Redis
    3. Allow the chaos endpoint to verify the restart

    Args:
        reason: Why the exit is being triggered (for logging)
        correlation_id: Unique ID to track this chaos operation

    Returns:
        This task will NOT return normally - it calls os._exit(0)
    """
    from app.core.celery_app import WORKER_BOOT_ID
    from app.core.config import settings

    # Safety check - only allow in staging
    if settings.ENVIRONMENT == "production":
        logger.error("CHAOS: exit_worker called in production - BLOCKED")
        return {
            "status": "blocked",
            "reason": "Chaos tasks disabled in production",
            "correlation_id": correlation_id,
        }

    logger.warning(
        f"CHAOS_EXIT_REQUESTED: "
        f"boot_id={WORKER_BOOT_ID}, "
        f"reason={reason}, "
        f"correlation_id={correlation_id}"
    )

    # Log the exit trace
    logger.info(f"Worker {WORKER_BOOT_ID} exiting for chaos test. Goodbye!")

    # Force exit - Railway will restart the worker
    # Using os._exit(0) for immediate exit without cleanup
    # This simulates a crash/restart scenario
    os._exit(0)

    # This line is never reached
    return {"status": "exiting", "boot_id": WORKER_BOOT_ID}
