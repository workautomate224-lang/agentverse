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
from app.tasks.chaos_tasks import exit_worker

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

        # Dispatch exit task to worker
        logger.info("Dispatching exit_worker task via Celery...")
        try:
            exit_worker.delay(request.reason, correlation_id)
            logger.info("Exit task dispatched successfully")
        except Exception as celery_error:
            logger.error(f"Celery dispatch failed: {celery_error}")
            await r.close()
            return WorkerExitResponse(
                status="error",
                correlation_id=correlation_id,
                before_boot_id=before_boot_id,
                message=f"Celery dispatch failed: {celery_error}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        logger.info(f"Exit task dispatched, polling for restart...")

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

    try:
        r = redis.from_url(settings.REDIS_URL)
        boot_info = await r.hgetall("staging:worker:boot_info")
        await r.close()

        if not boot_info:
            return WorkerStatusResponse(
                status="unavailable",
                boot_info=None,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # Decode byte keys/values
        decoded_info = {k.decode(): v.decode() for k, v in boot_info.items()}

        return WorkerStatusResponse(
            status="available",
            boot_info=decoded_info,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.exception(f"Error getting worker status: {e}")
        return WorkerStatusResponse(
            status="error",
            boot_info={"error": str(e)},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
