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
        # Only check if S3 is configured
        if not getattr(settings, "S3_BUCKET", None):
            return DependencyHealth(
                name="storage",
                status=HealthStatus.HEALTHY,
                message="Using local storage",
            )

        import boto3
        from botocore.config import Config

        config = Config(
            connect_timeout=5,
            read_timeout=5,
            retries={"max_attempts": 1},
        )

        s3 = boto3.client(
            "s3",
            endpoint_url=getattr(settings, "S3_ENDPOINT_URL", None),
            aws_access_key_id=getattr(settings, "S3_ACCESS_KEY", None),
            aws_secret_access_key=getattr(settings, "S3_SECRET_KEY", None),
            config=config,
        )

        # List buckets to verify connectivity
        s3.list_buckets()
        latency = (time.perf_counter() - start) * 1000

        return DependencyHealth(
            name="storage",
            status=HealthStatus.HEALTHY,
            latency_ms=round(latency, 2),
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
