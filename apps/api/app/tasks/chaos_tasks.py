"""
Chaos Engineering Tasks - Step 3.2

Tasks for chaos testing and validation:
- exit_worker: Intentionally exit worker process for restart testing

These tasks are used by the /ops/chaos endpoints for Step 3.1 validation.
Only enabled in staging environment.
"""

import logging
import os
import signal

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="chaos.exit_worker", acks_late=False)
def exit_worker(reason: str, correlation_id: str) -> dict:
    """
    Intentionally exit the MAIN worker process for chaos testing.

    This kills the main Celery process (not just the fork worker)
    so Railway will restart it with a new WORKER_BOOT_ID.

    IMPORTANT: acks_late=False ensures the task is acknowledged immediately
    when received, preventing it from being redelivered when the worker exits.

    Args:
        reason: Why the exit is being triggered (for logging)
        correlation_id: Unique ID to track this chaos operation

    Returns:
        This task will NOT return normally - it kills the main process
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
    logger.info(f"Worker {WORKER_BOOT_ID} main process exiting for chaos test. Goodbye!")

    # Get the main Celery process PID (parent of this fork worker)
    main_pid = os.getppid()
    logger.warning(f"CHAOS: Killing main Celery process PID={main_pid}")

    # Send SIGTERM to the main Celery process to trigger a clean shutdown
    # Railway will then restart the entire container
    try:
        os.kill(main_pid, signal.SIGTERM)
    except OSError as e:
        logger.error(f"Failed to kill main process: {e}")
        # Fallback: exit this fork worker
        os._exit(1)

    # Also exit this fork worker
    os._exit(0)

    # This line is never reached
    return {"status": "exiting", "boot_id": WORKER_BOOT_ID}
