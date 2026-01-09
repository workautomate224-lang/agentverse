"""
AgentVerse API - AI Agent Simulation Platform
Main FastAPI application entry point
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import sentry_sdk
import structlog
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.api.v1.endpoints.health import router as health_router
from app.core.config import settings
from app.core.websocket import websocket_endpoint
from app.db.session import engine
from app.middleware.tenant import TenantMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.metrics import PrometheusMetricsMiddleware
from app.core.observability import set_app_info
from app.core.tracing import (
    init_tracing,
    instrument_fastapi,
    instrument_redis,
    instrument_celery,
    shutdown_tracing,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    logger.info("Starting AgentVerse API", version=settings.VERSION)

    # Initialize OpenTelemetry tracing (project.md §11 Phase 9)
    otlp_endpoint = getattr(settings, "OTLP_ENDPOINT", None)
    init_tracing(
        service_name="agentverse-api",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
        otlp_endpoint=otlp_endpoint,
    )
    instrument_redis()
    instrument_celery()
    logger.info("OpenTelemetry tracing initialized")

    # Set Prometheus app info (project.md §11 Phase 9)
    engine_version = getattr(settings, "ENGINE_VERSION", "1.0.0")
    set_app_info(
        version=settings.VERSION,
        engine_version=engine_version,
        environment=settings.ENVIRONMENT,
    )
    logger.info("Prometheus metrics initialized")

    # Initialize Sentry if configured
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=0.1,
        )
        logger.info("Sentry initialized")

    # Initialize audit logger with database session factory (project.md §8)
    from app.services.audit import get_tenant_audit_logger
    from app.db.session import async_session_maker
    audit_logger = get_tenant_audit_logger()
    audit_logger.set_db_session_factory(async_session_maker)
    await audit_logger.start_background_flush()
    logger.info("Audit logger initialized")

    yield

    # Shutdown
    logger.info("Shutting down AgentVerse API")

    # Stop audit logger and flush remaining logs
    await audit_logger.stop()

    # Shutdown tracing
    shutdown_tracing()

    await engine.dispose()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="AI Agent Simulation Platform - Simulate human decisions at scale",
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.ENVIRONMENT != "production" else None,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Prometheus metrics middleware (project.md §11 Phase 9)
    application.add_middleware(PrometheusMetricsMiddleware)

    # Tenant isolation middleware (C6: multi-tenancy from day 1)
    application.add_middleware(TenantMiddleware)

    # Rate limiting middleware (C6: rate limits mandatory)
    # Skip rate limiting in test environment to avoid async Redis issues during testing
    if settings.ENVIRONMENT != "test":
        application.add_middleware(RateLimitMiddleware)

    # Include API router
    application.include_router(api_router, prefix=settings.API_V1_STR)

    # Include health and metrics endpoints at root level (project.md §11 Phase 9)
    application.include_router(health_router)

    # Instrument FastAPI for OpenTelemetry (after all middleware added)
    instrument_fastapi(application)

    # Mount static files for test page
    static_path = Path(__file__).parent.parent / "static"
    if static_path.exists():
        application.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    # Root endpoint
    @application.get("/")
    async def root() -> dict[str, str]:
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics",
        }

    # WebSocket endpoint for real-time simulation updates
    @application.websocket("/ws")
    async def websocket_general(websocket: WebSocket):
        """General WebSocket connection."""
        await websocket_endpoint(websocket)

    @application.websocket("/ws/{run_id}")
    async def websocket_run(websocket: WebSocket, run_id: str):
        """WebSocket connection for a specific run."""
        await websocket_endpoint(websocket, run_id)

    return application


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
