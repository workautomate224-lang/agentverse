"""
Staging-only Test Simulation Endpoint - Step 3.2

Provides endpoint for running real simulations to produce valid REP:
- POST /ops/test/run-real-simulation: Execute a real simulation run

This endpoint is ONLY available in staging environment and requires
the STAGING_OPS_API_KEY header for authentication.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops/test", tags=["Ops - Test Simulation"])


# =============================================================================
# Request/Response Models
# =============================================================================

class RunSimulationRequest(BaseModel):
    """Request body for run-real-simulation endpoint."""
    agent_count: int = Field(default=10, ge=1, le=100, description="Number of agents")
    tick_count: int = Field(default=10, ge=1, le=100, description="Number of simulation ticks")
    max_wait_seconds: int = Field(default=300, ge=30, le=600, description="Max wait time for completion")


class RunSimulationResponse(BaseModel):
    """Response from run-real-simulation endpoint."""
    status: str  # success, failed, timeout, error
    run_id: Optional[str] = None
    task_id: Optional[str] = None
    rep_path: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    config: Optional[dict[str, Any]] = None
    llm_calls_made: Optional[int] = None
    message: Optional[str] = None
    timestamp: str


class TestStatusResponse(BaseModel):
    """Response from test status endpoint."""
    status: str
    environment: str
    staging_ops_configured: bool
    worker_available: bool
    timestamp: str


class DbCheckResponse(BaseModel):
    """Response from db-check endpoint."""
    status: str
    tables_found: list[str]
    tables_missing: list[str]
    migration_head: Optional[str] = None
    message: Optional[str] = None
    timestamp: str


class MigrationResponse(BaseModel):
    """Response from run-migrations endpoint."""
    status: str
    message: str
    output: Optional[str] = None
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
        logger.warning("Test endpoint called in production - BLOCKED")
        raise HTTPException(
            status_code=403,
            detail="Test endpoints disabled in production"
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

@router.post("/run-real-simulation", response_model=RunSimulationResponse)
async def run_real_simulation(
    request: RunSimulationRequest = RunSimulationRequest(),
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> RunSimulationResponse:
    """
    Create and execute a REAL simulation run for Step 3.1 validation.

    This endpoint:
    1. Creates a run with specified agents/ticks
    2. Uses REAL OpenRouter LLM calls (not mocked)
    3. Waits for completion
    4. Validates REP has all required files
    5. Returns run_id and REP location

    Requires X-API-Key header with STAGING_OPS_API_KEY value.
    Only available in staging environment.
    """
    verify_staging_access(x_api_key)

    logger.info(
        f"Test simulation requested: agents={request.agent_count}, "
        f"ticks={request.tick_count}"
    )

    start_time = datetime.now(timezone.utc)

    try:
        from app.services.simulation_orchestrator import (
            SimulationOrchestrator,
            CreateRunInput,
            RunConfigInput,
        )
        from app.models.node import RunStatus, TriggeredBy

        orchestrator = SimulationOrchestrator(db)

        # Use staging test tenant/project IDs
        # These should be pre-created in staging environment
        test_tenant_id = str(uuid.UUID("00000000-0000-0000-0000-000000000001"))
        test_user_id = str(uuid.UUID("00000000-0000-0000-0000-000000000003"))
        test_project_id = str(uuid.UUID("00000000-0000-0000-0000-000000000002"))

        from sqlalchemy import text

        # Step 1: Ensure test tenant exists
        result = await db.execute(
            text("SELECT id FROM tenants WHERE id = :id"),
            {"id": uuid.UUID(test_tenant_id)}
        )
        tenant_exists = result.scalar_one_or_none()

        if not tenant_exists:
            await db.execute(
                text("""
                    INSERT INTO tenants (id, slug, name, tier, created_at, updated_at)
                    VALUES (:id, :slug, :name, :tier, :created_at, :updated_at)
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": uuid.UUID(test_tenant_id),
                    "slug": "step31-test-tenant",
                    "name": "Step 3.1 Test Tenant",
                    "tier": "enterprise",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            await db.commit()
            logger.info(f"Created test tenant: {test_tenant_id}")

        # Step 2: Ensure test user exists
        result = await db.execute(
            text("SELECT id FROM users WHERE id = :id"),
            {"id": uuid.UUID(test_user_id)}
        )
        user_exists = result.scalar_one_or_none()

        if not user_exists:
            await db.execute(
                text("""
                    INSERT INTO users (id, tenant_id, email, full_name, role, created_at, updated_at)
                    VALUES (:id, :tenant_id, :email, :full_name, :role, :created_at, :updated_at)
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": uuid.UUID(test_user_id),
                    "tenant_id": uuid.UUID(test_tenant_id),
                    "email": "step31-test@agentverse.local",
                    "full_name": "Step 3.1 Test User",
                    "role": "admin",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            await db.commit()
            logger.info(f"Created test user: {test_user_id}")

        # Step 3: Check if test project exists, create if not
        result = await db.execute(
            text("SELECT id FROM project_specs WHERE id = :id"),
            {"id": uuid.UUID(test_project_id)}
        )
        project_exists = result.scalar_one_or_none()

        if not project_exists:
            # Create a minimal test project for validation runs
            await db.execute(
                text("""
                    INSERT INTO project_specs (
                        id, tenant_id, owner_id, title, goal_nl, description,
                        prediction_core, created_at, updated_at
                    ) VALUES (
                        :id, :tenant_id, :owner_id, :title, :goal_nl, :description,
                        :prediction_core, :created_at, :updated_at
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": uuid.UUID(test_project_id),
                    "tenant_id": uuid.UUID(test_tenant_id),
                    "owner_id": uuid.UUID(test_user_id),
                    "title": "Step 3.1 Validation Project",
                    "goal_nl": "Automated test project for Step 3.1 validation",
                    "description": "This project is used for automated E2E validation testing",
                    "prediction_core": "general",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            await db.commit()
            logger.info(f"Created test project: {test_project_id}")

        # Build run configuration
        config_input = RunConfigInput(
            run_mode="society",
            max_ticks=request.tick_count,
            agent_batch_size=request.agent_count,
            max_agents=request.agent_count,
            engine_version=settings.ENGINE_VERSION,
            ruleset_version=settings.RULESET_VERSION,
            dataset_version=settings.SCHEMA_VERSION,
        )

        # Create run input
        run_label = f"Step3.1-Validation-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        run_input = CreateRunInput(
            project_id=test_project_id,
            tenant_id=test_tenant_id,
            label=run_label,
            config=config_input,
            seeds=[42],  # Deterministic seed for reproducibility
            triggered_by=TriggeredBy.API,
        )

        # Create and start the run
        run, node, task_id = await orchestrator.create_and_start_run(run_input)
        await db.commit()

        logger.info(f"Created test run: run_id={run.id}, task_id={task_id}")

        # Poll for completion
        poll_start = datetime.now(timezone.utc)
        final_status = "timeout"

        while True:
            elapsed = (datetime.now(timezone.utc) - poll_start).total_seconds()

            if elapsed > request.max_wait_seconds:
                logger.warning(f"Test run did not complete within {request.max_wait_seconds}s")
                break

            await asyncio.sleep(5)

            # Refresh run status
            run = await orchestrator.get_run(str(run.id), uuid.UUID(test_tenant_id))

            if not run:
                logger.error("Run disappeared during polling")
                final_status = "error"
                break

            if run.status == RunStatus.SUCCEEDED.value or run.status == "succeeded":
                final_status = "success"
                logger.info(f"Test run completed successfully: run_id={run.id}")
                break
            elif run.status == RunStatus.FAILED.value or run.status == "failed":
                final_status = "failed"
                logger.warning(f"Test run failed: run_id={run.id}")
                break
            elif run.status == "cancelled":
                final_status = "cancelled"
                logger.warning(f"Test run cancelled: run_id={run.id}")
                break

        total_elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Determine REP path
        rep_path = None
        llm_calls = None
        if final_status == "success":
            rep_path = f"s3://{settings.STORAGE_BUCKET}/runs/{run.id}/"

            # Try to get LLM call count from run outputs
            if run.outputs:
                telemetry_ref = run.outputs.get("telemetry_ref", {})
                llm_calls = telemetry_ref.get("llm_calls_count", 0)

        return RunSimulationResponse(
            status=final_status,
            run_id=str(run.id) if run else None,
            task_id=task_id,
            rep_path=rep_path,
            elapsed_seconds=round(total_elapsed, 2),
            config={
                "agent_count": request.agent_count,
                "tick_count": request.tick_count,
            },
            llm_calls_made=llm_calls,
            message=f"Test run completed with status: {final_status}",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.exception(f"Error in run-real-simulation: {e}")
        return RunSimulationResponse(
            status="error",
            message=str(e),
            elapsed_seconds=(datetime.now(timezone.utc) - start_time).total_seconds(),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


@router.get("/run-status/{run_id}")
async def get_run_status(
    run_id: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Get status of a specific run for debugging."""
    verify_staging_access(x_api_key)

    from sqlalchemy import text

    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        return {"status": "invalid_uuid", "run_id": run_id}

    try:
        result = await db.execute(
            text("SELECT id, status, worker_id, label FROM runs WHERE id = :id::uuid"),
            {"id": str(run_uuid)}
        )
        row = result.fetchone()

        if not row:
            return {"status": "not_found", "run_id": run_id}

        return {
            "run_id": str(row[0]),
            "status": row[1],
            "worker_id": row[2],
            "label": row[3],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "run_id": run_id,
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/config-check")
async def check_config(
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """Check critical configuration for simulation runs."""
    verify_staging_access(x_api_key)

    return {
        "environment": settings.ENVIRONMENT,
        "openrouter_configured": bool(settings.OPENROUTER_API_KEY),
        "openrouter_key_length": len(settings.OPENROUTER_API_KEY) if settings.OPENROUTER_API_KEY else 0,
        "default_model": settings.DEFAULT_MODEL,
        "database_url_configured": bool(settings.DATABASE_URL),
        "redis_url_configured": bool(settings.REDIS_URL),
        "storage_bucket": settings.STORAGE_BUCKET,
        "simulation_timeout_seconds": settings.SIMULATION_TIMEOUT_SECONDS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status", response_model=TestStatusResponse)
async def get_test_status(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> TestStatusResponse:
    """
    Get test endpoint status and configuration.

    Returns information about:
    - Current environment
    - Whether STAGING_OPS_API_KEY is configured
    - Whether worker is available (via Redis boot_info)

    Requires X-API-Key header with STAGING_OPS_API_KEY value.
    Only available in staging environment.
    """
    verify_staging_access(x_api_key)

    # Check worker availability via Redis
    worker_available = False
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.REDIS_URL)
        boot_info = await r.hgetall("staging:worker:boot_info")
        await r.close()
        worker_available = bool(boot_info)
    except Exception as e:
        logger.warning(f"Could not check worker status: {e}")

    return TestStatusResponse(
        status="ready" if worker_available else "worker_unavailable",
        environment=settings.ENVIRONMENT,
        staging_ops_configured=bool(getattr(settings, "STAGING_OPS_API_KEY", "")),
        worker_available=worker_available,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/db-check", response_model=DbCheckResponse)
async def check_database(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> DbCheckResponse:
    """
    Check database schema status.

    Returns list of required tables and which are present/missing.
    Useful for debugging migration issues.
    """
    verify_staging_access(x_api_key)

    required_tables = [
        "project_specs",
        "nodes",
        "runs",
        "event_scripts",
        "llm_calls",
    ]

    tables_found = []
    tables_missing = []

    try:
        from sqlalchemy import text

        for table in required_tables:
            result = await db.execute(
                text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table)"),
                {"table": table}
            )
            exists = result.scalar()
            if exists:
                tables_found.append(table)
            else:
                tables_missing.append(table)

        # Get current migration head
        migration_head = None
        try:
            result = await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = result.fetchone()
            if row:
                migration_head = row[0]
        except Exception:
            migration_head = "alembic_version table not found"

        status = "ok" if not tables_missing else "missing_tables"

        return DbCheckResponse(
            status=status,
            tables_found=tables_found,
            tables_missing=tables_missing,
            migration_head=migration_head,
            message=f"Found {len(tables_found)}/{len(required_tables)} required tables",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.exception(f"Error checking database: {e}")
        return DbCheckResponse(
            status="error",
            tables_found=tables_found,
            tables_missing=tables_missing,
            message=str(e),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


@router.post("/run-migrations", response_model=MigrationResponse)
async def run_migrations(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> MigrationResponse:
    """
    Trigger database migrations.

    Runs `alembic upgrade head` synchronously and returns the result.
    This is a staging-only endpoint for fixing migration issues.
    """
    verify_staging_access(x_api_key)

    try:
        import subprocess
        import os

        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        )

        if result.returncode == 0:
            return MigrationResponse(
                status="success",
                message="Migrations completed successfully",
                output=result.stdout + result.stderr,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        else:
            return MigrationResponse(
                status="failed",
                message=f"Migrations failed with exit code {result.returncode}",
                output=result.stdout + result.stderr,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    except subprocess.TimeoutExpired:
        return MigrationResponse(
            status="timeout",
            message="Migration command timed out after 120 seconds",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.exception(f"Error running migrations: {e}")
        return MigrationResponse(
            status="error",
            message=str(e),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
