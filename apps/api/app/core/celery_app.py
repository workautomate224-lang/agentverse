"""
Celery Application Configuration
Reference: project.md §5.3

Background task processing for AgentVerse.
Supports on-demand simulation execution (C2 constraint).

Queue Architecture:
- default: General purpose tasks
- runs: Simulation run execution (priority queue)
- maintenance: Cleanup, archival tasks

Step 3.2: Worker Boot ID tracking for chaos testing
- WORKER_BOOT_ID: Unique ID generated on worker startup
- Stored in Redis for real-time boot verification
"""

import logging
import os
import time
import uuid

from celery import Celery
from celery.signals import worker_ready, worker_shutdown

from app.core.config import settings

logger = logging.getLogger(__name__)

# Worker boot tracking (Step 3.2)
WORKER_BOOT_ID: str = str(uuid.uuid4())
WORKER_BOOT_TIMESTAMP: float | None = None

# Create Celery app
celery_app = Celery(
    "agentverse",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.run_executor",
        "app.tasks.maintenance",
        "app.tasks.chaos_tasks",  # Step 3.2: Chaos engineering tasks
        # Legacy tasks (to be deprecated)
        "app.tasks.world_simulation",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,

    # Result settings
    result_expires=86400,  # 24 hours

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,

    # Priority queue settings (0-9, higher = more priority)
    task_queue_max_priority=10,
    task_default_priority=5,

    # Soft time limit for tasks (seconds)
    task_soft_time_limit=settings.SIMULATION_TIMEOUT_SECONDS,
    task_time_limit=settings.SIMULATION_TIMEOUT_SECONDS + 60,

    # Beat scheduler - ON-DEMAND only (C2), no continuous simulation
    # Periodic tasks are only for maintenance, not simulation
    beat_schedule={
        # Cleanup expired job statuses (every hour)
        "cleanup-expired-job-status": {
            "task": "app.tasks.maintenance.cleanup_expired_status",
            "schedule": 3600.0,
        },
        # Archive old telemetry (daily at 3am)
        "archive-old-telemetry": {
            "task": "app.tasks.maintenance.archive_old_telemetry",
            "schedule": {
                "hour": 3,
                "minute": 0,
            },
        },
        # Worker heartbeat (Step 3.2) - refresh boot_id TTL every 30 seconds
        "worker-heartbeat": {
            "task": "app.tasks.maintenance.worker_heartbeat",
            "schedule": 30.0,
        },
    },
)

# Task routing
celery_app.conf.task_routes = {
    # Run execution tasks go to dedicated queue
    "app.tasks.run_executor.*": {
        "queue": "runs",
        "routing_key": "runs",
    },
    # Maintenance tasks
    "app.tasks.maintenance.*": {
        "queue": "maintenance",
        "routing_key": "maintenance",
    },
    # Legacy world simulation (to be deprecated)
    "app.tasks.world_simulation.*": {
        "queue": "legacy",
        "routing_key": "legacy",
    },
}

# Queue definitions with priorities
celery_app.conf.task_queues = {
    "default": {
        "exchange": "default",
        "routing_key": "default",
    },
    "runs": {
        "exchange": "runs",
        "routing_key": "runs",
        "queue_arguments": {"x-max-priority": 10},
    },
    "maintenance": {
        "exchange": "maintenance",
        "routing_key": "maintenance",
    },
    "legacy": {
        "exchange": "legacy",
        "routing_key": "legacy",
    },
}


# =============================================================================
# Step 3.2: Worker Boot ID Signal Handlers
# =============================================================================

def _store_boot_info_in_redis():
    """Store worker boot info in Redis (synchronous)."""
    global WORKER_BOOT_TIMESTAMP
    import redis

    WORKER_BOOT_TIMESTAMP = time.time()

    try:
        r = redis.from_url(settings.REDIS_URL)

        # Store boot info as hash
        boot_info = {
            "boot_id": WORKER_BOOT_ID,
            "boot_timestamp": str(WORKER_BOOT_TIMESTAMP),
            "hostname": os.environ.get("HOSTNAME", os.environ.get("RAILWAY_SERVICE_NAME", "unknown")),
            "pid": str(os.getpid()),
            "environment": settings.ENVIRONMENT,
        }

        r.hset("staging:worker:boot_info", mapping=boot_info)
        r.expire("staging:worker:boot_info", 300)  # 5 min TTL (refreshed by heartbeat)

        logger.info(f"Worker boot_id stored in Redis: {WORKER_BOOT_ID}")
        r.close()
    except Exception as e:
        logger.error(f"Failed to store boot_id in Redis: {e}")


def _clear_boot_info_from_redis():
    """Clear worker boot info from Redis on shutdown (synchronous)."""
    import redis

    try:
        r = redis.from_url(settings.REDIS_URL)
        r.delete("staging:worker:boot_info")
        logger.info(f"Worker boot_id cleared from Redis: {WORKER_BOOT_ID}")
        r.close()
    except Exception as e:
        logger.error(f"Failed to clear boot_id from Redis: {e}")


@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """
    Called when worker is ready to accept tasks.
    Stores boot_id in Redis for chaos testing verification.
    """
    logger.info(f"Worker ready signal received. Boot ID: {WORKER_BOOT_ID}")
    _store_boot_info_in_redis()


@worker_shutdown.connect
def on_worker_shutdown(sender, **kwargs):
    """
    Called when worker is shutting down.
    Clears boot_id from Redis.
    """
    logger.info(f"Worker shutdown signal received. Boot ID: {WORKER_BOOT_ID}")
    _clear_boot_info_from_redis()
