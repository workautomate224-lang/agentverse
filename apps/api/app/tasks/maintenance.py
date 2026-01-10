"""
Maintenance Tasks
Reference: project.md §8.4

Background maintenance operations:
- Cleanup expired job status
- Archive old telemetry
- Prune stale data
"""

from datetime import datetime, timedelta
from celery import shared_task

from app.core.config import settings


@shared_task(name="app.tasks.maintenance.cleanup_expired_status")
def cleanup_expired_status() -> dict:
    """
    Clean up expired job status entries from Redis.
    Job statuses older than 24 hours are automatically expired by Redis TTL,
    but this task ensures consistency.
    """
    from app.core.celery_app import celery_app

    try:
        redis = celery_app.backend.client
        # Pattern match job_status:* keys
        pattern = "job_status:*"
        cursor = 0
        cleaned = 0

        while True:
            cursor, keys = redis.scan(cursor, match=pattern, count=100)
            # Keys are already expired by TTL, this is just for logging
            cleaned += len(keys)
            if cursor == 0:
                break

        return {
            "status": "completed",
            "scanned": cleaned,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(name="app.tasks.maintenance.archive_old_telemetry")
def archive_old_telemetry() -> dict:
    """
    Archive telemetry older than retention period.
    Reference: project.md §8.4

    This task:
    1. Identifies telemetry older than retention period
    2. Moves to cold storage tier (if configured)
    3. Updates database references
    """
    # Retention period (default 90 days)
    retention_days = 90
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    # TODO: Implement actual archival logic
    # This requires:
    # 1. Query telemetry records older than cutoff
    # 2. Move from hot to cold storage
    # 3. Update storage_ref in database

    return {
        "status": "completed",
        "cutoff_date": cutoff_date.isoformat(),
        "archived_count": 0,  # Placeholder
        "timestamp": datetime.utcnow().isoformat(),
    }


@shared_task(name="app.tasks.maintenance.prune_cancelled_runs")
def prune_cancelled_runs() -> dict:
    """
    Remove data from cancelled runs that never completed.
    Cleans up partial telemetry and temporary data.
    """
    # Runs that were cancelled more than 7 days ago
    cutoff = datetime.utcnow() - timedelta(days=7)

    # TODO: Implement cleanup logic
    return {
        "status": "completed",
        "cutoff_date": cutoff.isoformat(),
        "pruned_count": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }


@shared_task(name="app.tasks.maintenance.compute_tenant_usage")
def compute_tenant_usage(tenant_id: str) -> dict:
    """
    Compute storage and compute usage for a tenant.
    Used for quota enforcement and billing.
    """
    # TODO: Implement usage computation
    return {
        "tenant_id": tenant_id,
        "storage_bytes": 0,
        "runs_this_month": 0,
        "agents_active": 0,
        "computed_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# Step 3.2: Worker Heartbeat
# =============================================================================

@shared_task(name="app.tasks.maintenance.worker_heartbeat")
def worker_heartbeat() -> dict:
    """
    Refresh worker boot_id TTL in Redis.

    This task runs every 30 seconds (via Celery Beat) to keep the
    worker's boot_info alive in Redis. If the worker dies, the TTL
    will expire and the boot_info will disappear.

    Used by chaos testing to verify worker is alive.
    """
    import redis
    from app.core.celery_app import WORKER_BOOT_ID, WORKER_BOOT_TIMESTAMP
    from app.core.config import settings

    try:
        r = redis.from_url(settings.REDIS_URL)

        # Check if boot_info exists
        exists = r.exists("staging:worker:boot_info")

        if exists:
            # Refresh TTL
            r.expire("staging:worker:boot_info", 300)  # 5 min TTL
            r.close()
            return {
                "status": "alive",
                "boot_id": WORKER_BOOT_ID,
                "boot_timestamp": WORKER_BOOT_TIMESTAMP,
                "heartbeat_at": datetime.utcnow().isoformat(),
            }
        else:
            # Re-store boot info (might have expired)
            boot_info = {
                "boot_id": WORKER_BOOT_ID,
                "boot_timestamp": str(WORKER_BOOT_TIMESTAMP or datetime.utcnow().timestamp()),
                "hostname": "unknown",
                "pid": "unknown",
                "environment": settings.ENVIRONMENT,
            }
            r.hset("staging:worker:boot_info", mapping=boot_info)
            r.expire("staging:worker:boot_info", 300)
            r.close()
            return {
                "status": "restored",
                "boot_id": WORKER_BOOT_ID,
                "heartbeat_at": datetime.utcnow().isoformat(),
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "boot_id": WORKER_BOOT_ID,
            "heartbeat_at": datetime.utcnow().isoformat(),
        }
