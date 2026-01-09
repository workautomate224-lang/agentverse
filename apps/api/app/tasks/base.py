"""
Base Task Configuration
Reference: project.md §5.3, §8

Provides base task classes with:
- Tenant isolation
- Job status tracking
- Rate limiting hooks
- Error handling
- Retry policies
"""

import abc
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, TypeVar, Generic
from dataclasses import dataclass, field

from celery import Task
from celery.exceptions import MaxRetriesExceededError

from app.core.config import settings


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class JobPriority(int, Enum):
    """Job priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class JobContext:
    """
    Context passed to every job execution.
    Provides tenant isolation and tracking.
    """
    job_id: str
    tenant_id: str
    user_id: str
    priority: JobPriority = JobPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: int = 60
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize context for Celery."""
        return {
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobContext":
        """Deserialize context from Celery."""
        return cls(
            job_id=data["job_id"],
            tenant_id=data["tenant_id"],
            user_id=data["user_id"],
            priority=JobPriority(data.get("priority", JobPriority.NORMAL.value)),
            created_at=datetime.fromisoformat(data["created_at"]),
            timeout_seconds=data.get("timeout_seconds", 300),
            max_retries=data.get("max_retries", 3),
            retry_delay_seconds=data.get("retry_delay_seconds", 60),
            metadata=data.get("metadata", {}),
        )


@dataclass
class JobResult:
    """
    Result of a job execution.
    """
    job_id: str
    status: JobStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    retries: int = 0

    def to_dict(self) -> dict:
        """Serialize result."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "retries": self.retries,
        }


class TenantAwareTask(Task):
    """
    Base Celery task with tenant awareness and job tracking.

    Features:
    - Tenant isolation via context
    - Automatic status tracking
    - Configurable retries
    - Timeout handling
    - Error reporting
    """

    abstract = True

    # Default settings
    autoretry_for = (Exception,)
    max_retries = 3
    default_retry_delay = 60

    # Bind to get access to self
    bind = True

    def before_start(self, task_id: str, args: tuple, kwargs: dict):
        """Called before task execution."""
        context = kwargs.get("context")
        if context and isinstance(context, dict):
            context = JobContext.from_dict(context)
            self._update_job_status(context.job_id, JobStatus.RUNNING)

    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict):
        """Called on successful completion."""
        context = kwargs.get("context")
        if context and isinstance(context, dict):
            context = JobContext.from_dict(context)
            self._update_job_status(context.job_id, JobStatus.COMPLETED, result=retval)

    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo):
        """Called on task failure."""
        context = kwargs.get("context")
        if context and isinstance(context, dict):
            context = JobContext.from_dict(context)

            # Check if we've exceeded retries
            if isinstance(exc, MaxRetriesExceededError):
                status = JobStatus.FAILED
            else:
                status = JobStatus.FAILED

            self._update_job_status(
                context.job_id,
                status,
                error=str(exc)
            )

    def on_retry(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo):
        """Called when task is retried."""
        context = kwargs.get("context")
        if context and isinstance(context, dict):
            context = JobContext.from_dict(context)
            # Keep status as RUNNING during retries
            self._update_job_status(
                context.job_id,
                JobStatus.RUNNING,
                metadata={"retry_reason": str(exc)}
            )

    def _update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        result: Any = None,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """
        Update job status in Redis for real-time tracking.
        This is a lightweight status update - full results go to the database.
        """
        from app.core.celery_app import celery_app

        status_key = f"job_status:{job_id}"
        status_data = {
            "job_id": job_id,
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat(),
        }

        if error:
            status_data["error"] = error
        if metadata:
            status_data["metadata"] = metadata

        # Store in Redis with 24h expiry
        try:
            redis = celery_app.backend.client
            import json
            redis.setex(
                status_key,
                timedelta(hours=24),
                json.dumps(status_data)
            )
        except Exception:
            # Non-critical - status tracking is best-effort
            pass


def create_job_context(
    tenant_id: str,
    user_id: str,
    priority: JobPriority = JobPriority.NORMAL,
    timeout_seconds: int = 300,
    metadata: Optional[dict] = None,
) -> JobContext:
    """
    Factory function to create a job context.
    """
    return JobContext(
        job_id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        priority=priority,
        timeout_seconds=timeout_seconds,
        metadata=metadata or {},
    )


def get_job_status(job_id: str) -> Optional[dict]:
    """
    Get current job status from Redis.
    For full job details, query the database.
    """
    from app.core.celery_app import celery_app

    try:
        redis = celery_app.backend.client
        import json
        status_key = f"job_status:{job_id}"
        data = redis.get(status_key)
        if data:
            return json.loads(data)
    except Exception:
        pass

    return None
