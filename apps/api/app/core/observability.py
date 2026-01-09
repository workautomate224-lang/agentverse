"""
Observability Service - Prometheus Metrics & OpenTelemetry Tracing
project.md §11 Phase 9: Production Hardening
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Callable

import psutil
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
    multiprocess,
)

if TYPE_CHECKING:
    from fastapi import Request, Response

# ============================================================================
# METRIC REGISTRY
# ============================================================================

# Use a custom registry for multiprocess support
REGISTRY = CollectorRegistry()

# Try to enable multiprocess mode if available
try:
    multiprocess.MultiProcessCollector(REGISTRY)
except ValueError:
    # Not in multiprocess mode, use standard collector
    pass

# ============================================================================
# APPLICATION INFO
# ============================================================================

APP_INFO = Info(
    "agentverse_app",
    "AgentVerse application information",
    registry=REGISTRY,
)

# ============================================================================
# HTTP METRICS
# ============================================================================

HTTP_REQUESTS_TOTAL = Counter(
    "agentverse_http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "agentverse_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "agentverse_http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    ["method", "endpoint"],
    registry=REGISTRY,
)

# ============================================================================
# SIMULATION METRICS
# ============================================================================

SIMULATION_RUNS_TOTAL = Counter(
    "agentverse_simulation_runs_total",
    "Total number of simulation runs",
    ["status", "mode", "tenant_id"],
    registry=REGISTRY,
)

SIMULATION_RUN_DURATION_SECONDS = Histogram(
    "agentverse_simulation_run_duration_seconds",
    "Simulation run duration in seconds",
    ["mode"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0],
    registry=REGISTRY,
)

SIMULATION_AGENTS_TOTAL = Gauge(
    "agentverse_simulation_agents_total",
    "Total number of agents in active simulations",
    ["tenant_id", "project_id"],
    registry=REGISTRY,
)

SIMULATION_TICKS_PROCESSED = Counter(
    "agentverse_simulation_ticks_processed_total",
    "Total number of simulation ticks processed",
    ["mode"],
    registry=REGISTRY,
)

# ============================================================================
# NODE/UNIVERSE MAP METRICS
# ============================================================================

NODES_TOTAL = Gauge(
    "agentverse_nodes_total",
    "Total number of nodes in Universe Map",
    ["tenant_id", "project_id", "status"],
    registry=REGISTRY,
)

NODE_FORKS_TOTAL = Counter(
    "agentverse_node_forks_total",
    "Total number of node fork operations",
    ["tenant_id"],
    registry=REGISTRY,
)

# ============================================================================
# PERSONA METRICS
# ============================================================================

PERSONAS_TOTAL = Gauge(
    "agentverse_personas_total",
    "Total number of personas",
    ["tenant_id", "source_type"],
    registry=REGISTRY,
)

PERSONA_GENERATION_TOTAL = Counter(
    "agentverse_persona_generation_total",
    "Total number of persona generation operations",
    ["status", "method"],
    registry=REGISTRY,
)

PERSONA_GENERATION_DURATION_SECONDS = Histogram(
    "agentverse_persona_generation_duration_seconds",
    "Persona generation duration in seconds",
    ["method"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY,
)

# ============================================================================
# EVENT COMPILER METRICS
# ============================================================================

EVENT_COMPILATIONS_TOTAL = Counter(
    "agentverse_event_compilations_total",
    "Total number of event compilations (Ask feature)",
    ["status", "intent_type"],
    registry=REGISTRY,
)

EVENT_COMPILATION_DURATION_SECONDS = Histogram(
    "agentverse_event_compilation_duration_seconds",
    "Event compilation (Ask) duration in seconds",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=REGISTRY,
)

SCENARIO_CLUSTERS_GENERATED = Counter(
    "agentverse_scenario_clusters_generated_total",
    "Total number of scenario clusters generated",
    registry=REGISTRY,
)

# ============================================================================
# CALIBRATION METRICS
# ============================================================================

CALIBRATION_RUNS_TOTAL = Counter(
    "agentverse_calibration_runs_total",
    "Total number of calibration runs",
    ["status", "dataset_type"],
    registry=REGISTRY,
)

CALIBRATION_ACCURACY = Gauge(
    "agentverse_calibration_accuracy",
    "Current calibration accuracy score",
    ["tenant_id", "project_id", "metric_type"],
    registry=REGISTRY,
)

# ============================================================================
# RELIABILITY METRICS
# ============================================================================

RELIABILITY_REPORTS_GENERATED = Counter(
    "agentverse_reliability_reports_generated_total",
    "Total number of reliability reports generated",
    ["tenant_id"],
    registry=REGISTRY,
)

RELIABILITY_SCORE = Gauge(
    "agentverse_reliability_score",
    "Current reliability score",
    ["tenant_id", "project_id", "dimension"],
    registry=REGISTRY,
)

# ============================================================================
# DATABASE METRICS
# ============================================================================

DB_CONNECTIONS_ACTIVE = Gauge(
    "agentverse_db_connections_active",
    "Number of active database connections",
    registry=REGISTRY,
)

DB_CONNECTIONS_POOL_SIZE = Gauge(
    "agentverse_db_connections_pool_size",
    "Database connection pool size",
    registry=REGISTRY,
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "agentverse_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=REGISTRY,
)

# ============================================================================
# CELERY/JOB QUEUE METRICS
# ============================================================================

CELERY_TASKS_TOTAL = Counter(
    "agentverse_celery_tasks_total",
    "Total number of Celery tasks",
    ["task_name", "status"],
    registry=REGISTRY,
)

CELERY_TASK_DURATION_SECONDS = Histogram(
    "agentverse_celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0],
    registry=REGISTRY,
)

CELERY_QUEUE_LENGTH = Gauge(
    "agentverse_celery_queue_length",
    "Number of tasks in Celery queue",
    ["queue_name"],
    registry=REGISTRY,
)

# ============================================================================
# CACHE METRICS
# ============================================================================

REDIS_OPERATIONS_TOTAL = Counter(
    "agentverse_redis_operations_total",
    "Total number of Redis operations",
    ["operation", "status"],
    registry=REGISTRY,
)

REDIS_OPERATION_DURATION_SECONDS = Histogram(
    "agentverse_redis_operation_duration_seconds",
    "Redis operation duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
    registry=REGISTRY,
)

# ============================================================================
# LLM/EXTERNAL API METRICS
# ============================================================================

LLM_REQUESTS_TOTAL = Counter(
    "agentverse_llm_requests_total",
    "Total number of LLM API requests",
    ["provider", "model", "status"],
    registry=REGISTRY,
)

LLM_REQUEST_DURATION_SECONDS = Histogram(
    "agentverse_llm_request_duration_seconds",
    "LLM API request duration in seconds",
    ["provider", "model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY,
)

LLM_TOKENS_USED = Counter(
    "agentverse_llm_tokens_used_total",
    "Total number of LLM tokens used",
    ["provider", "model", "token_type"],
    registry=REGISTRY,
)

# ============================================================================
# SYSTEM METRICS
# ============================================================================

SYSTEM_CPU_USAGE = Gauge(
    "agentverse_system_cpu_usage_percent",
    "System CPU usage percentage",
    registry=REGISTRY,
)

SYSTEM_MEMORY_USAGE = Gauge(
    "agentverse_system_memory_usage_bytes",
    "System memory usage in bytes",
    ["type"],
    registry=REGISTRY,
)

SYSTEM_DISK_USAGE = Gauge(
    "agentverse_system_disk_usage_bytes",
    "System disk usage in bytes",
    ["mount", "type"],
    registry=REGISTRY,
)

# ============================================================================
# EXPORT METRICS
# ============================================================================

EXPORTS_TOTAL = Counter(
    "agentverse_exports_total",
    "Total number of data exports",
    ["format", "status", "redacted"],
    registry=REGISTRY,
)

EXPORT_DURATION_SECONDS = Histogram(
    "agentverse_export_duration_seconds",
    "Export generation duration in seconds",
    ["format"],
    buckets=[0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
    registry=REGISTRY,
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def set_app_info(version: str, engine_version: str, environment: str) -> None:
    """Set application info metrics."""
    APP_INFO.info({
        "version": version,
        "engine_version": engine_version,
        "environment": environment,
    })


def update_system_metrics() -> None:
    """Update system resource metrics."""
    # CPU
    SYSTEM_CPU_USAGE.set(psutil.cpu_percent())

    # Memory
    memory = psutil.virtual_memory()
    SYSTEM_MEMORY_USAGE.labels(type="used").set(memory.used)
    SYSTEM_MEMORY_USAGE.labels(type="available").set(memory.available)
    SYSTEM_MEMORY_USAGE.labels(type="total").set(memory.total)

    # Disk
    try:
        disk = psutil.disk_usage("/")
        SYSTEM_DISK_USAGE.labels(mount="/", type="used").set(disk.used)
        SYSTEM_DISK_USAGE.labels(mount="/", type="free").set(disk.free)
        SYSTEM_DISK_USAGE.labels(mount="/", type="total").set(disk.total)
    except OSError:
        pass


def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    update_system_metrics()
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """Get the content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST


# ============================================================================
# INSTRUMENTATION DECORATORS
# ============================================================================


def track_simulation_run(mode: str = "society"):
    """Decorator to track simulation run metrics."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tenant_id = kwargs.get("tenant_id", "unknown")
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                SIMULATION_RUNS_TOTAL.labels(
                    status="success", mode=mode, tenant_id=tenant_id
                ).inc()
                return result
            except Exception as e:
                SIMULATION_RUNS_TOTAL.labels(
                    status="error", mode=mode, tenant_id=tenant_id
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                SIMULATION_RUN_DURATION_SECONDS.labels(mode=mode).observe(duration)
        return wrapper
    return decorator


def track_llm_request(provider: str = "openrouter", model: str = "default"):
    """Decorator to track LLM API request metrics."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                LLM_REQUESTS_TOTAL.labels(
                    provider=provider, model=model, status="success"
                ).inc()
                return result
            except Exception:
                LLM_REQUESTS_TOTAL.labels(
                    provider=provider, model=model, status="error"
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                LLM_REQUEST_DURATION_SECONDS.labels(
                    provider=provider, model=model
                ).observe(duration)
        return wrapper
    return decorator


def track_db_query(operation: str = "query"):
    """Decorator to track database query metrics."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                DB_QUERY_DURATION_SECONDS.labels(operation=operation).observe(duration)
        return wrapper
    return decorator


def track_celery_task(task_name: str):
    """Decorator to track Celery task metrics."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                CELERY_TASKS_TOTAL.labels(
                    task_name=task_name, status="success"
                ).inc()
                return result
            except Exception:
                CELERY_TASKS_TOTAL.labels(
                    task_name=task_name, status="error"
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                CELERY_TASK_DURATION_SECONDS.labels(task_name=task_name).observe(duration)
        return wrapper
    return decorator


# ============================================================================
# CONTEXT MANAGERS
# ============================================================================


@asynccontextmanager
async def track_http_request(method: str, endpoint: str):
    """Context manager to track HTTP request metrics."""
    HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
    start_time = time.time()
    status_code = "500"
    try:
        yield lambda code: nonlocal_set("status_code", code)
    finally:
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
        duration = time.time() - start_time
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration)
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=status_code).inc()


def nonlocal_set(var_name: str, value: Any) -> None:
    """Helper for setting nonlocal variables in context managers."""
    pass  # Placeholder - actual implementation uses closure


class RequestMetricsTracker:
    """Class-based request metrics tracker for cleaner usage."""

    def __init__(self, method: str, endpoint: str):
        self.method = method
        self.endpoint = endpoint
        self.start_time = 0.0
        self.status_code = "500"

    def __enter__(self) -> "RequestMetricsTracker":
        HTTP_REQUESTS_IN_PROGRESS.labels(
            method=self.method, endpoint=self.endpoint
        ).inc()
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        HTTP_REQUESTS_IN_PROGRESS.labels(
            method=self.method, endpoint=self.endpoint
        ).dec()
        duration = time.time() - self.start_time
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=self.method, endpoint=self.endpoint
        ).observe(duration)
        HTTP_REQUESTS_TOTAL.labels(
            method=self.method,
            endpoint=self.endpoint,
            status_code=self.status_code,
        ).inc()

    def set_status(self, code: int) -> None:
        """Set the response status code."""
        self.status_code = str(code)
