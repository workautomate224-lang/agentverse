"""
OpenTelemetry Tracing Service
project.md §11 Phase 9: Production Hardening

Distributed tracing for request flows across:
- HTTP requests
- Database queries
- Celery tasks
- External API calls (LLM providers)
- Simulation execution
"""

from __future__ import annotations

import os
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy.engine import Engine

# Type variable for generic function decoration
F = TypeVar("F", bound=Callable[..., Any])

# ============================================================================
# TRACER PROVIDER SETUP
# ============================================================================

_tracer_provider: TracerProvider | None = None
_tracer: trace.Tracer | None = None


def init_tracing(
    service_name: str = "agentverse-api",
    environment: str = "development",
    version: str = "0.1.0",
    otlp_endpoint: str | None = None,
) -> TracerProvider:
    """
    Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service for tracing
        environment: Deployment environment (development, staging, production)
        version: Service version
        otlp_endpoint: OTLP exporter endpoint (e.g., "http://jaeger:4317")

    Returns:
        Configured TracerProvider
    """
    global _tracer_provider, _tracer

    # Create resource with service metadata
    resource = Resource.create({
        "service.name": service_name,
        "service.version": version,
        "deployment.environment": environment,
        "service.namespace": "agentverse",
    })

    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)

    # Configure exporters based on environment
    if otlp_endpoint:
        # Production: send to OTLP collector (Jaeger, Tempo, etc.)
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=environment != "production",
        )
        _tracer_provider.add_span_processor(
            BatchSpanProcessor(otlp_exporter)
        )
    elif environment == "development":
        # Development: log to console
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(
            BatchSpanProcessor(console_exporter)
        )

    # Set global tracer provider
    trace.set_tracer_provider(_tracer_provider)

    # Create tracer for this module
    _tracer = trace.get_tracer(service_name, version)

    return _tracer_provider


def get_tracer() -> trace.Tracer:
    """Get the configured tracer instance."""
    global _tracer
    if _tracer is None:
        # Lazy initialization with defaults
        init_tracing()
        _tracer = trace.get_tracer("agentverse-api")
    return _tracer


def shutdown_tracing() -> None:
    """Shutdown tracing and flush pending spans."""
    global _tracer_provider
    if _tracer_provider:
        _tracer_provider.shutdown()


# ============================================================================
# AUTO-INSTRUMENTATION
# ============================================================================


def instrument_fastapi(app: "FastAPI") -> None:
    """
    Instrument FastAPI application for automatic tracing.

    This will automatically create spans for:
    - All HTTP requests
    - Request/response headers
    - Status codes and errors
    """
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="health,metrics,favicon.ico",
        tracer_provider=_tracer_provider,
    )


def instrument_sqlalchemy(engine: "Engine") -> None:
    """
    Instrument SQLAlchemy for automatic query tracing.

    This will automatically create spans for:
    - All database queries
    - Query parameters (sanitized)
    - Query duration
    """
    SQLAlchemyInstrumentor().instrument(
        engine=engine,
        tracer_provider=_tracer_provider,
    )


def instrument_redis() -> None:
    """
    Instrument Redis for automatic operation tracing.

    This will automatically create spans for:
    - All Redis commands
    - Key names (configurable)
    - Operation duration
    """
    RedisInstrumentor().instrument(
        tracer_provider=_tracer_provider,
    )


def instrument_celery() -> None:
    """
    Instrument Celery for automatic task tracing.

    This will automatically create spans for:
    - Task execution
    - Task routing
    - Task retries
    """
    CeleryInstrumentor().instrument(
        tracer_provider=_tracer_provider,
    )


def instrument_all(app: "FastAPI", engine: "Engine" | None = None) -> None:
    """
    Apply all auto-instrumentation.

    Args:
        app: FastAPI application instance
        engine: SQLAlchemy engine (optional)
    """
    instrument_fastapi(app)
    instrument_redis()
    instrument_celery()
    if engine:
        instrument_sqlalchemy(engine)


# ============================================================================
# MANUAL INSTRUMENTATION DECORATORS
# ============================================================================


def traced(
    name: str | None = None,
    attributes: dict[str, Any] | None = None,
    record_exception: bool = True,
) -> Callable[[F], F]:
    """
    Decorator to create a span for a function.

    Args:
        name: Span name (defaults to function name)
        attributes: Additional span attributes
        record_exception: Whether to record exceptions in the span

    Example:
        @traced("process_simulation")
        async def run_simulation(config):
            ...
    """
    def decorator(func: F) -> F:
        span_name = name or func.__name__

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def traced_llm(
    provider: str = "openrouter",
    model: str = "default",
) -> Callable[[F], F]:
    """
    Decorator specifically for LLM API calls.

    Adds LLM-specific attributes to the span.

    Example:
        @traced_llm(provider="openrouter", model="gpt-4")
        async def call_llm(prompt):
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(f"llm.{provider}.{model}") as span:
                span.set_attribute("llm.provider", provider)
                span.set_attribute("llm.model", model)
                span.set_attribute("llm.request_type", func.__name__)

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))

                    # Record token usage if available
                    if hasattr(result, "usage"):
                        usage = result.usage
                        span.set_attribute("llm.prompt_tokens", getattr(usage, "prompt_tokens", 0))
                        span.set_attribute("llm.completion_tokens", getattr(usage, "completion_tokens", 0))
                        span.set_attribute("llm.total_tokens", getattr(usage, "total_tokens", 0))

                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        return wrapper  # type: ignore

    return decorator


def traced_simulation(mode: str = "society") -> Callable[[F], F]:
    """
    Decorator specifically for simulation execution.

    Adds simulation-specific attributes and creates child spans for phases.

    Example:
        @traced_simulation(mode="society")
        async def execute_run(run_config):
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(f"simulation.{mode}") as span:
                span.set_attribute("simulation.mode", mode)

                # Extract common kwargs
                if "run_id" in kwargs:
                    span.set_attribute("simulation.run_id", str(kwargs["run_id"]))
                if "project_id" in kwargs:
                    span.set_attribute("simulation.project_id", str(kwargs["project_id"]))
                if "tenant_id" in kwargs:
                    span.set_attribute("simulation.tenant_id", str(kwargs["tenant_id"]))
                if "num_agents" in kwargs:
                    span.set_attribute("simulation.num_agents", kwargs["num_agents"])
                if "num_ticks" in kwargs:
                    span.set_attribute("simulation.num_ticks", kwargs["num_ticks"])

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        return wrapper  # type: ignore

    return decorator


def traced_db_operation(operation: str = "query") -> Callable[[F], F]:
    """
    Decorator for database operations.

    Example:
        @traced_db_operation("insert")
        async def create_node(data):
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(f"db.{operation}") as span:
                span.set_attribute("db.operation", operation)
                span.set_attribute("db.function", func.__name__)

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(f"db.{operation}") as span:
                span.set_attribute("db.operation", operation)
                span.set_attribute("db.function", func.__name__)

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


# ============================================================================
# SPAN CONTEXT HELPERS
# ============================================================================


def get_current_span() -> Span:
    """Get the current active span."""
    return trace.get_current_span()


def add_span_attribute(key: str, value: Any) -> None:
    """Add an attribute to the current span."""
    span = get_current_span()
    if span.is_recording():
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: dict[str, Any] | None = None) -> None:
    """Add an event to the current span."""
    span = get_current_span()
    if span.is_recording():
        span.add_event(name, attributes=attributes or {})


def record_exception(exception: Exception) -> None:
    """Record an exception in the current span."""
    span = get_current_span()
    if span.is_recording():
        span.record_exception(exception)


def set_span_status_error(message: str) -> None:
    """Set the current span status to error."""
    span = get_current_span()
    if span.is_recording():
        span.set_status(Status(StatusCode.ERROR, message))


def set_span_status_ok() -> None:
    """Set the current span status to OK."""
    span = get_current_span()
    if span.is_recording():
        span.set_status(Status(StatusCode.OK))


# ============================================================================
# TRACE CONTEXT PROPAGATION
# ============================================================================

propagator = TraceContextTextMapPropagator()


def inject_trace_context(carrier: dict[str, str]) -> None:
    """
    Inject trace context into a carrier dict for propagation.

    Use when making outbound HTTP calls to propagate trace context.

    Example:
        headers = {}
        inject_trace_context(headers)
        response = await client.get(url, headers=headers)
    """
    propagator.inject(carrier)


def extract_trace_context(carrier: dict[str, str]) -> trace.Context:
    """
    Extract trace context from a carrier dict.

    Use when receiving inbound requests to continue a trace.

    Example:
        context = extract_trace_context(request.headers)
        with tracer.start_as_current_span("handler", context=context):
            ...
    """
    return propagator.extract(carrier)


# ============================================================================
# BAGGAGE HELPERS (for cross-service context)
# ============================================================================


def set_baggage(key: str, value: str) -> None:
    """
    Set a baggage item that propagates across service boundaries.

    Useful for propagating tenant_id, user_id, etc.
    """
    from opentelemetry import baggage
    baggage.set_baggage(key, value)


def get_baggage(key: str) -> str | None:
    """Get a baggage item value."""
    from opentelemetry import baggage
    return baggage.get_baggage(key)
