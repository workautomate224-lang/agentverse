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

    # Log process info for debugging
    current_pid = os.getpid()
    parent_pid = os.getppid()
    logger.warning(f"CHAOS: Current PID={current_pid}, Parent PID={parent_pid}")

    # Log the exit trace
    logger.info(f"Worker {WORKER_BOOT_ID} exiting for chaos test. Goodbye!")

    # Method 1: Use Celery control to broadcast shutdown to all workers
    # This is more reliable than trying to kill PID 1 in Docker
    try:
        from app.core.celery_app import celery_app
        logger.warning("CHAOS: Broadcasting shutdown via Celery control...")
        celery_app.control.shutdown()
    except Exception as e:
        logger.error(f"Celery control.shutdown() failed: {e}")

    # Method 2: Kill the process tree from this fork worker
    # Try to terminate the parent process group
    try:
        logger.warning(f"CHAOS: Killing process group {parent_pid}...")
        os.killpg(parent_pid, signal.SIGKILL)
    except (OSError, ProcessLookupError) as e:
        logger.warning(f"killpg failed (expected in some setups): {e}")

    # Method 3: Direct SIGKILL to parent
    try:
        logger.warning(f"CHAOS: Sending SIGKILL to parent PID {parent_pid}...")
        os.kill(parent_pid, signal.SIGKILL)
    except OSError as e:
        logger.error(f"Failed to kill parent: {e}")

    # Method 4: Exit this fork worker - Celery's prefork pool will handle it
    # If Celery is using --pool=prefork, the worker will restart this process
    # If using --pool=solo, this will exit the entire worker
    import time
    time.sleep(1)  # Give control commands time to propagate

    logger.warning("CHAOS: Force exiting this worker process...")
    os._exit(137)  # 128 + 9 (SIGKILL signal number)

    # This line is never reached
    return {"status": "exiting", "boot_id": WORKER_BOOT_ID}
