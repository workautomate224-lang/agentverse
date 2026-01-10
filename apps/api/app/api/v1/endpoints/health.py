"""
Health Check Endpoints with Dependency Probes
project.md §11 Phase 9: Production Hardening

Provides:
- /health: Basic liveness check
- /health/ready: Readiness check with dependency probes
- /health/live: Kubernetes liveness probe
- /metrics: Prometheus metrics endpoint
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.observability import get_metrics, get_metrics_content_type
from app.db.session import get_db

router = APIRouter(tags=["Health"])


class HealthStatus(str, Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DependencyHealth(BaseModel):
    """Health status of a single dependency."""
    name: str
    status: HealthStatus
    latency_ms: float | None = None
    message: str | None = None
    details: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    """Full health check response."""
    status: HealthStatus
    version: str
    environment: str
    timestamp: str
    uptime_seconds: float
    dependencies: list[DependencyHealth] | None = None


# Track service start time for uptime calculation
_start_time = time.time()


async def check_database(db: AsyncSession) -> DependencyHealth:
    """Check database connectivity."""
    start = time.perf_counter()
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        latency = (time.perf_counter() - start) * 1000
        return DependencyHealth(
            name="postgresql",
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return DependencyHealth(
            name="postgresql",
            status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 2),
            message=str(e)[:100],
        )


async def check_redis() -> DependencyHealth:
    """Check Redis connectivity."""
    start = time.perf_counter()
    try:
        import redis.asyncio as redis

        client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        await client.ping()
        await client.close()
        latency = (time.perf_counter() - start) * 1000
        return DependencyHealth(
            name="redis",
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return DependencyHealth(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 2),
            message=str(e)[:100],
        )


async def check_celery() -> DependencyHealth:
    """Check Celery worker connectivity via Redis broker."""
    start = time.perf_counter()
    try:
        # Check if Celery broker (Redis) is accessible
        # We can't easily check worker status without Flower
        import redis.asyncio as redis

        # Parse celery broker URL from settings
        broker_url = getattr(settings, "CELERY_BROKER_URL", settings.REDIS_URL)
        client = redis.from_url(broker_url)

        # Check if the celery queue exists
        queue_length = await client.llen("celery")
        await client.close()

        latency = (time.perf_counter() - start) * 1000
        return DependencyHealth(
            name="celery",
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
            details={"queue_length": queue_length},
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return DependencyHealth(
            name="celery",
            status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 2),
            message=str(e)[:100],
        )


async def check_storage() -> DependencyHealth:
    """Check object storage (S3) connectivity."""
    start = time.perf_counter()
    try:
        # Check if using local storage
        backend = getattr(settings, "STORAGE_BACKEND", "local")
        if backend == "local":
            return DependencyHealth(
                name="storage",
                status=HealthStatus.HEALTHY,
                message="Using local storage",
            )

        # Check S3-compatible storage
        bucket = getattr(settings, "STORAGE_BUCKET", None)
        if not bucket:
            return DependencyHealth(
                name="storage",
                status=HealthStatus.HEALTHY,
                message="No bucket configured",
            )

        import boto3
        from botocore.config import Config

        config = Config(
            connect_timeout=5,
            read_timeout=5,
            retries={"max_attempts": 1},
            signature_version="s3v4",
        )

        s3 = boto3.client(
            "s3",
            region_name=getattr(settings, "STORAGE_REGION", "us-east-1"),
            endpoint_url=getattr(settings, "STORAGE_ENDPOINT_URL", None),
            aws_access_key_id=getattr(settings, "STORAGE_ACCESS_KEY", None),
            aws_secret_access_key=getattr(settings, "STORAGE_SECRET_KEY", None),
            use_ssl=getattr(settings, "STORAGE_USE_SSL", True),
            config=config,
        )

        # List buckets to verify connectivity
        s3.list_buckets()
        latency = (time.perf_counter() - start) * 1000

        return DependencyHealth(
            name="storage",
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
            details={"bucket": bucket, "backend": backend},
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return DependencyHealth(
            name="storage",
            status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 2),
            message=str(e)[:100],
        )


def determine_overall_status(dependencies: list[DependencyHealth]) -> HealthStatus:
    """Determine overall health status from dependency checks."""
    statuses = [d.status for d in dependencies]

    # If any critical dependency is unhealthy, overall is unhealthy
    critical = ["postgresql", "redis"]
    for dep in dependencies:
        if dep.name in critical and dep.status == HealthStatus.UNHEALTHY:
            return HealthStatus.UNHEALTHY

    # If any dependency is degraded, overall is degraded
    if HealthStatus.DEGRADED in statuses:
        return HealthStatus.DEGRADED

    # If any dependency is unhealthy (non-critical), overall is degraded
    if HealthStatus.UNHEALTHY in statuses:
        return HealthStatus.DEGRADED

    return HealthStatus.HEALTHY


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check (liveness probe).

    Returns basic status without checking dependencies.
    Use /health/ready for full readiness check.
    """
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        version=settings.VERSION,
        environment=getattr(settings, "ENVIRONMENT", "development"),
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(time.time() - _start_time, 2),
    )


@router.get("/health/live", response_model=HealthResponse)
async def liveness_probe() -> HealthResponse:
    """
    Kubernetes liveness probe.

    Simple check that the service is running.
    """
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        version=settings.VERSION,
        environment=getattr(settings, "ENVIRONMENT", "development"),
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(time.time() - _start_time, 2),
    )


@router.get("/health/ready", response_model=HealthResponse)
async def readiness_probe(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """
    Kubernetes readiness probe.

    Checks all dependencies and returns detailed status.
    Service is ready only if all critical dependencies are healthy.
    """
    # Run all dependency checks concurrently
    dependencies = await asyncio.gather(
        check_database(db),
        check_redis(),
        check_celery(),
        check_storage(),
    )

    overall_status = determine_overall_status(list(dependencies))

    return HealthResponse(
        status=overall_status,
        version=settings.VERSION,
        environment=getattr(settings, "ENVIRONMENT", "development"),
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(time.time() - _start_time, 2),
        dependencies=list(dependencies),
    )


@router.get("/debug/celery-test")
async def debug_celery_test() -> dict:
    """
    Debug endpoint to test Celery task submission.
    """
    from app.core.celery_app import celery_app
    from app.core.config import settings

    result = {
        "settings_redis_url": settings.REDIS_URL,
        "celery_broker_url": celery_app.conf.broker_url,
        "celery_backend_url": celery_app.conf.result_backend,
    }

    # Try to connect
    try:
        with celery_app.connection() as conn:
            conn.connect()
            result["connection_test"] = "success"
            result["connected"] = conn.connected
    except Exception as e:
        result["connection_test"] = f"failed: {str(e)}"

    # Try to submit a simple task
    try:
        from app.tasks.run_executor import execute_run
        # Don't actually run, just test if apply_async works
        task = execute_run.apply_async(
            args=["debug-test-id", {"tenant_id": "debug"}],
            countdown=3600,  # Delay by 1 hour so it doesn't run
        )
        result["task_submit_test"] = f"success: {task.id}"
        task.revoke()  # Cancel immediately
    except Exception as e:
        import traceback
        result["task_submit_test"] = f"failed: {str(e)}"
        result["traceback"] = traceback.format_exc()

    return result


@router.get("/health/storage-test")
async def storage_smoke_test() -> dict:
    """
    Storage write/read smoke test.

    Performs a full write-read cycle to verify S3-compatible storage is working.
    Returns the test object key and confirmation.
    """
    import uuid
    from datetime import datetime, timezone

    result: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": getattr(settings, "ENVIRONMENT", "development"),
    }

    backend = getattr(settings, "STORAGE_BACKEND", "local")
    bucket = getattr(settings, "STORAGE_BUCKET", None)

    result["storage_backend"] = backend
    result["storage_bucket"] = bucket

    if backend == "local":
        result["status"] = "skipped"
        result["message"] = "Local storage backend - S3 test not applicable"
        return result

    if not bucket:
        result["status"] = "error"
        result["message"] = "No bucket configured"
        return result

    try:
        import boto3
        from botocore.config import Config

        config = Config(
            connect_timeout=10,
            read_timeout=10,
            retries={"max_attempts": 2},
            signature_version="s3v4",
        )

        s3 = boto3.client(
            "s3",
            region_name=getattr(settings, "STORAGE_REGION", "us-east-1"),
            endpoint_url=getattr(settings, "STORAGE_ENDPOINT_URL", None),
            aws_access_key_id=getattr(settings, "STORAGE_ACCESS_KEY", None),
            aws_secret_access_key=getattr(settings, "STORAGE_SECRET_KEY", None),
            use_ssl=getattr(settings, "STORAGE_USE_SSL", True),
            config=config,
        )

        # Generate test object
        test_id = str(uuid.uuid4())[:8]
        test_key = f"smoke-tests/storage-test-{test_id}.txt"
        test_content = f"AgentVerse Storage Smoke Test\nTimestamp: {result['timestamp']}\nEnvironment: {result['environment']}\nTest ID: {test_id}"

        # Write test
        start = time.perf_counter()
        s3.put_object(
            Bucket=bucket,
            Key=test_key,
            Body=test_content.encode("utf-8"),
            ContentType="text/plain",
        )
        write_latency = (time.perf_counter() - start) * 1000

        # Read test
        start = time.perf_counter()
        response = s3.get_object(Bucket=bucket, Key=test_key)
        read_content = response["Body"].read().decode("utf-8")
        read_latency = (time.perf_counter() - start) * 1000

        # Verify content
        if read_content == test_content:
            result["status"] = "success"
            result["test_object_key"] = test_key
            result["write_latency_ms"] = round(write_latency, 2)
            result["read_latency_ms"] = round(read_latency, 2)
            result["content_verified"] = True
        else:
            result["status"] = "error"
            result["message"] = "Content mismatch after read"

    except Exception as e:
        import traceback
        result["status"] = "error"
        result["message"] = str(e)
        result["traceback"] = traceback.format_exc()

    return result


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint.

    Returns all collected metrics in Prometheus format.
    """
    metrics_output = get_metrics()
    return Response(
        content=metrics_output,
        media_type=get_metrics_content_type(),
    )


@router.get("/health/llm-canary")
async def llm_canary_test(db: AsyncSession = Depends(get_db)) -> dict:
    """
    LLM Canary Test - Makes a REAL OpenRouter API call.

    This endpoint is used for Step 3.1 validation to prove that:
    1. The LLM integration is working (spends real tokens)
    2. OpenRouter API key is valid
    3. The system can make actual LLM calls

    Returns detailed evidence of the real LLM call including:
    - OpenRouter request_id (from response headers or body)
    - Model used
    - Token counts (input/output)
    - Cost in USD
    - Response time
    - Actual LLM response content

    Staging-only endpoint for validation purposes.
    """
    import json
    import uuid
    from datetime import datetime, timezone

    import httpx

    result: dict[str, Any] = {
        "test_id": f"llm-canary-{str(uuid.uuid4())[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": getattr(settings, "ENVIRONMENT", "development"),
        "purpose": "Step 3.1 E2E Validation - Real LLM Call Proof",
    }

    # Only allow in staging/development
    env = getattr(settings, "ENVIRONMENT", "development")
    if env == "production":
        result["status"] = "skipped"
        result["message"] = "LLM canary disabled in production"
        return result

    try:
        # Get OpenRouter credentials
        api_key = getattr(settings, "OPENROUTER_API_KEY", None)
        base_url = getattr(settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        if not api_key:
            result["status"] = "error"
            result["message"] = "OPENROUTER_API_KEY not configured"
            return result

        # Make a minimal LLM call (fewest tokens possible)
        canary_prompt = "Reply with exactly: CANARY_OK"
        model = "openai/gpt-4o-mini"  # Fast, cheap model

        start_time = time.perf_counter()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://agentverse.ai",
                    "X-Title": "AgentVerse LLM Canary Test",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": canary_prompt}],
                    "temperature": 0,
                    "max_tokens": 10,
                },
                timeout=30.0,
            )

            response.raise_for_status()
            response_data = response.json()
            response_headers = dict(response.headers)

        response_time_ms = (time.perf_counter() - start_time) * 1000

        # Extract usage info
        usage = response_data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

        # Extract request ID from response
        openrouter_id = response_data.get("id", "unknown")

        # Calculate cost (GPT-4o-mini pricing)
        cost_per_1k_input = 0.00015
        cost_per_1k_output = 0.0006
        cost_usd = (
            (input_tokens / 1000) * cost_per_1k_input +
            (output_tokens / 1000) * cost_per_1k_output
        )

        # Extract actual response content
        content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Build comprehensive result
        result["status"] = "success"
        result["llm_call"] = {
            "openrouter_request_id": openrouter_id,
            "model_requested": model,
            "model_used": response_data.get("model", model),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": round(cost_usd, 8),
            "response_time_ms": round(response_time_ms, 2),
            "response_content": content,
            "canary_verified": "canary" in content.lower() or "ok" in content.lower(),
        }
        result["evidence"] = {
            "api_endpoint": f"{base_url}/chat/completions",
            "http_status": response.status_code,
            "response_id_header": response_headers.get("x-request-id", "not_present"),
        }

        # Create llm_ledger entry for validation
        ledger_entry = {
            "timestamp": result["timestamp"],
            "test_id": result["test_id"],
            "request_id": openrouter_id,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost_usd,
            "response_time_ms": response_time_ms,
            "status": "success",
            "content_preview": content[:100],
        }
        result["llm_ledger_entry"] = ledger_entry

    except httpx.HTTPStatusError as e:
        result["status"] = "error"
        result["error_type"] = "http_error"
        result["message"] = f"HTTP {e.response.status_code}: {str(e)}"
        result["response_body"] = e.response.text[:500] if e.response else None
    except httpx.RequestError as e:
        result["status"] = "error"
        result["error_type"] = "request_error"
        result["message"] = str(e)
    except Exception as e:
        import traceback
        result["status"] = "error"
        result["error_type"] = "unexpected_error"
        result["message"] = str(e)
        result["traceback"] = traceback.format_exc()

    return result
