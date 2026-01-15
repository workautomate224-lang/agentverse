"""
Background Tasks Package
Reference: project.md §5.3

Task categories:
- run_executor: On-demand simulation execution (C2 compliant)
- maintenance: Cleanup, archival, quota computation
- world_simulation: LEGACY - to be deprecated
"""

from app.tasks.base import (
    JobStatus,
    JobPriority,
    JobContext,
    JobResult,
    TenantAwareTask,
    create_job_context,
    get_job_status,
)

from app.tasks.run_executor import (
    execute_run,
    cancel_run,
    batch_runs,
)

from app.tasks.maintenance import (
    cleanup_expired_status,
    archive_old_telemetry,
    prune_cancelled_runs,
    compute_tenant_usage,
)

# PIL (Project Intelligence Layer) tasks - blueprint.md §5
from app.tasks.pil_tasks import (
    dispatch_pil_job,
    goal_analysis_task,
    blueprint_build_task,
    slot_validation_task,
)

__all__ = [
    # Base classes
    "JobStatus",
    "JobPriority",
    "JobContext",
    "JobResult",
    "TenantAwareTask",
    "create_job_context",
    "get_job_status",
    # Run execution
    "execute_run",
    "cancel_run",
    "batch_runs",
    # Maintenance
    "cleanup_expired_status",
    "archive_old_telemetry",
    "prune_cancelled_runs",
    "compute_tenant_usage",
    # PIL (Project Intelligence Layer)
    "dispatch_pil_job",
    "goal_analysis_task",
    "blueprint_build_task",
    "slot_validation_task",
]
