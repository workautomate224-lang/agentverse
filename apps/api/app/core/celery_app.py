"""
Celery Application Configuration
Reference: project.md §5.3

Background task processing for AgentVerse.
Supports on-demand simulation execution (C2 constraint).

Queue Architecture:
- default: General purpose tasks
- runs: Simulation run execution (priority queue)
- maintenance: Cleanup, archival tasks
"""

from celery import Celery

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "agentverse",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.run_executor",
        "app.tasks.maintenance",
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
