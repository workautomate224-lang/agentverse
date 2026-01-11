"""
Staging-only Chaos Engineering Endpoints - Step 3.2

Provides endpoints for chaos testing and Step 3.1 validation:
- POST /ops/chaos/worker-exit: Trigger real worker restart
- GET /ops/chaos/worker-status: Check worker boot info

These endpoints are ONLY available in staging environment and require
the STAGING_OPS_API_KEY header for authentication.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops/chaos", tags=["Ops - Chaos Engineering"])


# =============================================================================
# Request/Response Models
# =============================================================================

class WorkerExitRequest(BaseModel):
    """Request body for worker-exit endpoint."""
    reason: str = "chaos_test"
    max_wait_seconds: int = 120


class WorkerExitResponse(BaseModel):
    """Response from worker-exit endpoint."""
    status: str
    correlation_id: str
    before_boot_id: str | None = None
    after_boot_id: str | None = None
    time_to_restart_seconds: float | None = None
    restart_verified: bool = False
    message: str | None = None
    timestamp: str


class WorkerStatusResponse(BaseModel):
    """Response from worker-status endpoint."""
    status: str
    boot_info: dict[str, Any] | None = None
    worker_boot_id: str | None = None
    last_seen_ts: str | None = None
    redis_key_used: str = "staging:worker:boot_info"
    timestamp: str


# =============================================================================
# Auth Helper
# =============================================================================

def verify_staging_access(x_api_key: str) -> None:
    """
    Verify staging API key and environment.

    Raises:
        HTTPException: If environment is production or key is invalid
    """
    # Block in production
    if settings.ENVIRONMENT == "production":
        logger.warning("Chaos endpoint called in production - BLOCKED")
        raise HTTPException(
            status_code=403,
            detail="Chaos endpoints disabled in production"
        )

    # Verify API key
    expected_key = getattr(settings, "STAGING_OPS_API_KEY", "")
    if not expected_key:
        logger.warning("STAGING_OPS_API_KEY not configured")
        raise HTTPException(
            status_code=503,
            detail="STAGING_OPS_API_KEY not configured on server"
        )

    if x_api_key != expected_key:
        logger.warning("Invalid staging API key provided")
        raise HTTPException(
            status_code=401,
            detail="Invalid staging API key"
        )


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/worker-exit", response_model=WorkerExitResponse)
async def trigger_worker_exit(
    request: WorkerExitRequest = WorkerExitRequest(),
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> WorkerExitResponse:
    """
    Trigger real worker restart for chaos C1 validation.

    This endpoint:
    1. Records current boot_id from Redis
    2. Sends exit task to worker (calls os._exit(0))
    3. Polls for new boot_id (worker restarted by Railway)
    4. Returns before/after boot_id as proof

    Requires X-API-Key header with STAGING_OPS_API_KEY value.
    Only available in staging environment.
    """
    verify_staging_access(x_api_key)

    correlation_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info(f"Chaos worker-exit triggered: correlation_id={correlation_id}")

    before_boot_id = None
    try:
        logger.info(f"Connecting to Redis: {settings.REDIS_URL[:30]}...")
        r = redis.from_url(settings.REDIS_URL)

        # Get current boot_id
        logger.info("Fetching boot_info from Redis...")
        before_info = await r.hgetall("staging:worker:boot_info")

        if not before_info:
            await r.close()
            return WorkerExitResponse(
                status="error",
                correlation_id=correlation_id,
                message="Worker not available (no boot_info in Redis). Worker may not be running.",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        before_boot_id = before_info.get(b"boot_id", b"").decode()

        logger.info(f"Current boot_id: {before_boot_id}")

        # Close Redis connection before Celery dispatch to avoid socket conflicts
        await r.close()

        # Import task inside function to get fresh Celery connection (like debug-config)
        from app.tasks.chaos_tasks import exit_worker

        # Dispatch exit task to worker with retry
        logger.info("Dispatching exit_worker task via Celery...")
        dispatch_success = False
        dispatch_error = None
        for attempt in range(3):
            try:
                exit_worker.delay(request.reason, correlation_id)
                logger.info(f"Exit task dispatched successfully on attempt {attempt + 1}")
                dispatch_success = True
                break
            except Exception as celery_error:
                dispatch_error = celery_error
                logger.warning(f"Celery dispatch attempt {attempt + 1} failed: {celery_error}")
                await asyncio.sleep(1)

        if not dispatch_success:
            logger.error(f"All Celery dispatch attempts failed: {dispatch_error}")
            return WorkerExitResponse(
                status="error",
                correlation_id=correlation_id,
                before_boot_id=before_boot_id,
                message=f"Celery dispatch failed after 3 attempts: {dispatch_error}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        logger.info(f"Exit task dispatched, polling for restart...")

        # Reconnect to Redis for polling
        r = redis.from_url(settings.REDIS_URL)

        # Poll for boot_id change
        after_boot_id = None
        poll_start = time.time()

        while time.time() - poll_start < request.max_wait_seconds:
            await asyncio.sleep(2)

            after_info = await r.hgetall("staging:worker:boot_info")

            if after_info:
                current_boot_id = after_info.get(b"boot_id", b"").decode()
                if current_boot_id and current_boot_id != before_boot_id:
                    after_boot_id = current_boot_id
                    logger.info(f"Worker restarted! New boot_id: {after_boot_id}")
                    break

        await r.close()

        time_to_restart = time.time() - start_time

        if not after_boot_id:
            logger.warning(f"Worker did not restart within {request.max_wait_seconds}s")
            return WorkerExitResponse(
                status="timeout",
                correlation_id=correlation_id,
                before_boot_id=before_boot_id,
                after_boot_id=None,
                time_to_restart_seconds=None,
                restart_verified=False,
                message=f"Worker did not restart within {request.max_wait_seconds}s",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        return WorkerExitResponse(
            status="success",
            correlation_id=correlation_id,
            before_boot_id=before_boot_id,
            after_boot_id=after_boot_id,
            time_to_restart_seconds=round(time_to_restart, 2),
            restart_verified=True,
            message="Worker restart verified successfully",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.exception(f"Error in worker-exit: {e}")
        return WorkerExitResponse(
            status="error",
            correlation_id=correlation_id,
            before_boot_id=before_boot_id,
            message=str(e),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


@router.get("/debug-config")
async def debug_config(
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """Debug endpoint to check Redis configuration."""
    verify_staging_access(x_api_key)

    redis_url = settings.REDIS_URL
    # Mask the password if present
    if "@" in redis_url:
        # URL format: redis://[:password]@host:port/db
        parts = redis_url.split("@")
        masked_url = f"***@{parts[-1]}"
    else:
        masked_url = redis_url

    # Test Celery broker connection
    celery_broker_test = "unknown"
    try:
        from app.core.celery_app import celery_app
        # Try to connect to broker
        conn = celery_app.connection()
        conn.connect()
        celery_broker_test = "success"
        conn.release()
    except Exception as e:
        celery_broker_test = f"failed: {e}"

    # Try to send a ping task and get result
    task_test = "unknown"
    try:
        from app.tasks.maintenance import worker_heartbeat
        result = worker_heartbeat.apply_async()
        # Wait up to 10 seconds for result
        task_result = result.get(timeout=10)
        task_test = f"success: {task_result}"
    except Exception as e:
        task_test = f"failed: {e}"

    return {
        "redis_url_masked": masked_url,
        "redis_url_length": len(redis_url),
        "redis_url_starts_with_redis": redis_url.startswith("redis://") or redis_url.startswith("rediss://"),
        "celery_broker_test": celery_broker_test,
        "task_test": task_test,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/worker-status", response_model=WorkerStatusResponse)
async def get_worker_status(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> WorkerStatusResponse:
    """
    Get current worker boot info from Redis.

    Returns the worker's boot_id, boot_timestamp, hostname, pid, and environment.
    Used to verify worker is alive before triggering chaos tests.

    Requires X-API-Key header with STAGING_OPS_API_KEY value.
    Only available in staging environment.
    """
    verify_staging_access(x_api_key)

    redis_key = "staging:worker:boot_info"

    try:
        r = redis.from_url(settings.REDIS_URL)
        boot_info = await r.hgetall(redis_key)

        # Also get TTL for debugging
        ttl = await r.ttl(redis_key)
        await r.close()

        if not boot_info:
            return WorkerStatusResponse(
                status="unavailable",
                boot_info=None,
                worker_boot_id=None,
                last_seen_ts=None,
                redis_key_used=redis_key,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # Decode byte keys/values
        decoded_info = {k.decode(): v.decode() for k, v in boot_info.items()}

        # Extract worker_boot_id and timestamp
        worker_boot_id = decoded_info.get("boot_id")
        boot_timestamp = decoded_info.get("boot_timestamp")

        # Calculate last seen based on TTL (300 - ttl = seconds since last refresh)
        last_seen_ts = None
        if boot_timestamp:
            last_seen_ts = boot_timestamp  # When worker started
        decoded_info["ttl_seconds"] = ttl

        return WorkerStatusResponse(
            status="available",
            boot_info=decoded_info,
            worker_boot_id=worker_boot_id,
            last_seen_ts=last_seen_ts,
            redis_key_used=redis_key,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.exception(f"Error getting worker status: {e}")
        return WorkerStatusResponse(
            status="error",
            boot_info={"error": str(e)},
            worker_boot_id=None,
            last_seen_ts=None,
            redis_key_used=redis_key,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


@router.post("/purge-queues")
async def purge_chaos_queues(
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """
    Purge all pending chaos tasks from queues.

    Use this to clear stuck exit_worker tasks that are clogging the worker.
    """
    verify_staging_access(x_api_key)

    purged = {}
    try:
        from app.core.celery_app import celery_app

        # Purge all relevant queues
        queues_to_purge = ["maintenance", "celery", "default"]

        for queue in queues_to_purge:
            try:
                count = celery_app.control.purge()
                purged[queue] = count if count else 0
            except Exception as e:
                purged[queue] = f"error: {e}"

        # Also try to delete specific keys from Redis
        r = redis.from_url(settings.REDIS_URL)

        # Delete the chaos task keys
        deleted_keys = 0
        keys_pattern = "celery-task-meta-*"
        async for key in r.scan_iter(match=keys_pattern, count=100):
            await r.delete(key)
            deleted_keys += 1

        # Purge the maintenance queue directly
        maintenance_queue_key = "maintenance"
        maintenance_len = await r.llen(maintenance_queue_key)
        if maintenance_len > 0:
            await r.delete(maintenance_queue_key)
            purged["maintenance_direct"] = maintenance_len

        await r.close()

        return {
            "status": "success",
            "purged_queues": purged,
            "deleted_task_meta_keys": deleted_keys,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.exception(f"Error purging queues: {e}")
        return {
            "status": "error",
            "message": str(e),
            "purged_queues": purged,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.post("/force-boot-id")
async def force_register_boot_id(
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """
    Force the worker to register its boot_id in Redis.

    Use this if the boot_id TTL expired and heartbeat isn't running.
    """
    verify_staging_access(x_api_key)

    try:
        from app.tasks.maintenance import worker_heartbeat

        # Dispatch heartbeat task
        result = worker_heartbeat.apply_async()
        task_id = result.id

        # Wait for result
        try:
            hb_result = result.get(timeout=30)
            return {
                "status": "success",
                "task_id": task_id,
                "heartbeat_result": hb_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "timeout",
                "task_id": task_id,
                "message": f"Heartbeat task timed out: {e}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    except Exception as e:
        logger.exception(f"Error forcing boot_id: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
