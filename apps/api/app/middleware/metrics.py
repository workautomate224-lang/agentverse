"""
Prometheus Metrics Middleware
project.md §11 Phase 9: Production Hardening

Automatically tracks HTTP request metrics for all endpoints.
"""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.observability import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    HTTP_REQUESTS_TOTAL,
)

if TYPE_CHECKING:
    from starlette.types import ASGIApp


# Paths to exclude from metrics (reduce cardinality)
EXCLUDED_PATHS = {
    "/health",
    "/metrics",
    "/favicon.ico",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Path patterns to normalize (reduce cardinality from dynamic segments)
PATH_PATTERNS = [
    (re.compile(r"/api/v1/projects/[^/]+"), "/api/v1/projects/{project_id}"),
    (re.compile(r"/api/v1/runs/[^/]+"), "/api/v1/runs/{run_id}"),
    (re.compile(r"/api/v1/nodes/[^/]+"), "/api/v1/nodes/{node_id}"),
    (re.compile(r"/api/v1/personas/[^/]+"), "/api/v1/personas/{persona_id}"),
    (re.compile(r"/api/v1/telemetry/[^/]+"), "/api/v1/telemetry/{telemetry_id}"),
    (re.compile(r"/api/v1/event-scripts/[^/]+"), "/api/v1/event-scripts/{script_id}"),
    (re.compile(r"/api/v1/users/[^/]+"), "/api/v1/users/{user_id}"),
    (re.compile(r"/api/v1/tenants/[^/]+"), "/api/v1/tenants/{tenant_id}"),
    (re.compile(r"/api/v1/calibration/[^/]+"), "/api/v1/calibration/{calibration_id}"),
    (re.compile(r"/api/v1/reliability/[^/]+"), "/api/v1/reliability/{report_id}"),
    (re.compile(r"/api/v1/exports/[^/]+"), "/api/v1/exports/{export_id}"),
    # UUID pattern
    (re.compile(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"), "/{uuid}"),
    # Numeric ID pattern
    (re.compile(r"/\d+"), "/{id}"),
]


def normalize_path(path: str) -> str:
    """
    Normalize a path to reduce metric cardinality.

    Replaces dynamic segments (IDs, UUIDs) with placeholders.
    """
    for pattern, replacement in PATH_PATTERNS:
        path = pattern.sub(replacement, path)
    return path


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect Prometheus metrics for HTTP requests.

    Tracks:
    - Request count by method, path, status code
    - Request duration histogram
    - In-progress request gauge
    """

    def __init__(self, app: "ASGIApp", excluded_paths: set[str] | None = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or EXCLUDED_PATHS

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        # Skip excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Normalize path for metrics
        method = request.method
        path = normalize_path(request.url.path)

        # Track in-progress requests
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).inc()

        # Track request timing
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception as e:
            # Record 500 for unhandled exceptions
            status_code = "500"
            raise
        finally:
            # Record metrics
            duration = time.perf_counter() - start_time

            HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).dec()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=path).observe(duration)
            HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=path, status_code=status_code).inc()

        return response
