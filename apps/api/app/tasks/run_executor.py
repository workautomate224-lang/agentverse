"""
Simulation Run Executor
Reference: project.md §4.2, §5.3, §6.5, §6.6

Executes simulation runs on-demand (C2 constraint).
Each run produces:
- Aggregated outcomes (Node)
- Telemetry blob (for replay)
- Reliability metrics

Key principles:
- FORK not MUTATE: Creates new nodes, never edits history
- Deterministic: Same seed + config = same outcome
- On-demand: Runs only when requested, no continuous simulation

STEP 1 Requirements:
- Proper state transitions: CREATED -> QUEUED -> RUNNING -> SUCCEEDED/FAILED
- Worker heartbeat with worker_id and last_seen_at
- RunSpec artifact with required fields
- RunTrace entries (at least 3) with run_id, timestamp, worker_id, execution_stage
- Outcome with real numeric results
"""

import asyncio
import hashlib
import json
import os
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import uuid

from celery import shared_task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.tasks.base import (
    TenantAwareTask,
    JobContext,
    JobStatus,
    JobResult,
)
# Import engine components
from app.engine import (
    RuleEngine,
    RuleContext,
    get_rule_engine,
    Agent,
    AgentFactory,
    AgentPool,
    AgentState as EngineAgentState,
)
# Import models
from app.models.node import (
    Node,
    Edge,
    Run,
    RunStatus,
)
from app.models.run_artifacts import (
    WorkerHeartbeat,
    RunSpec,
    RunTrace,
    ExecutionStage,
)
# STEP 3: Import PersonaSnapshot for immutable persona tracking
from app.models.persona import PersonaSnapshot
# Import services
from app.services.node_service import (
    NodeService,
    get_node_service,
    ArtifactRef,
    AggregatedOutcome,
    NodeConfidence,
)
from app.services.leakage_guard import (
    LeakageGuard,
    create_leakage_guard_from_config,
    LeakageViolationError,
)
from app.models.node import ConfidenceLevel


def get_worker_id() -> str:
    """Generate a unique worker ID for this worker instance."""
    hostname = socket.gethostname()
    pid = os.getpid()
    return f"{hostname}-{pid}"


# BUG-006 FIX: Create engine per-task to avoid event loop mismatch
# Do NOT create engine at module level - it causes "attached to a different loop" errors
# when Celery tasks create new event loops.

def get_async_session():
    """Create fresh async session with new engine for current event loop."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(
    bind=True,
    base=TenantAwareTask,
    name="app.tasks.run_executor.execute_run",
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=settings.SIMULATION_TIMEOUT_SECONDS,
    time_limit=settings.SIMULATION_TIMEOUT_SECONDS + 60,
)
def execute_run(
    self,
    run_id: str,
    context: dict,
) -> dict:
    """
    Execute a simulation run.

    This is the main entry point for running simulations.
    Called when a user submits a run request.

    Args:
        run_id: UUID of the Run record
        context: JobContext as dict

    Returns:
        JobResult as dict with run outputs
    """
    ctx = JobContext.from_dict(context)
    return run_async(_execute_run(run_id, ctx))


async def _execute_run(run_id: str, context: JobContext) -> dict:
    """
    Async implementation of run execution.

    STEP 1 Compliant Phases:
    1. Worker assignment and heartbeat update
    2. Load run configuration and validate (ticks_total > 0)
    3. Create RunSpec artifact
    4. Write initial RunTrace entries
    5. Initialize deterministic RNG with seed
    6. Execute simulation ticks (with trace updates)
    7. Aggregate outcomes (real numeric results)
    8. Generate telemetry
    9. Compute reliability metrics
    10. Store results and final trace
    """
    started_at = datetime.utcnow()
    start_time = time.perf_counter()
    worker_id = get_worker_id()

    # BUG-006 FIX: Create fresh session factory for current event loop
    AsyncSessionLocal = get_async_session()
    async with AsyncSessionLocal() as db:
        try:
            # Phase 1: Worker assignment and heartbeat
            await _update_worker_heartbeat(db, worker_id, run_id)
            await _write_trace(db, run_id, context.tenant_id, worker_id,
                              ExecutionStage.WORKER_ASSIGNED,
                              "Worker assigned to run")

            # Phase 2: Load and validate
            await _write_trace(db, run_id, context.tenant_id, worker_id,
                              ExecutionStage.LOADING_CONFIG,
                              "Loading run configuration")

            run = await _load_run(db, run_id, context.tenant_id)
            if not run:
                await _write_trace(db, run_id, context.tenant_id, worker_id,
                                  ExecutionStage.RUN_FAILED,
                                  f"Run not found: {run_id}")
                await db.commit()
                return JobResult(
                    job_id=context.job_id,
                    status=JobStatus.FAILED,
                    error=f"Run not found: {run_id}",
                ).to_dict()

            # STEP 1: Validate ticks_total > 0
            config = run.get("run_config", {}) or {}
            max_ticks = config.get("max_ticks") or 100
            if not isinstance(max_ticks, int) or max_ticks < 1:
                max_ticks = 100  # Enforce minimum
            if max_ticks == 0:
                raise ValueError("STEP 1 VIOLATION: ticks_total must be > 0. 0/0 ticks is not allowed.")

            # Update run status to RUNNING with worker info
            await _update_run_status(db, run_id, "running", started_at=started_at, worker_id=worker_id)

            # Phase 3a: Create PersonaSnapshot (STEP 3: Immutable persona capture)
            personas_snapshot_id, personas_summary = await _create_persona_snapshot(
                db=db,
                tenant_id=context.tenant_id,
                project_id=run.get("project_id"),
            )

            await _write_trace(db, run_id, context.tenant_id, worker_id,
                              ExecutionStage.LOADING_AGENTS,
                              f"Created persona snapshot: {personas_summary.get('total_personas', 0) if personas_summary else 0} personas")

            # Phase 3b: Create RunSpec artifact (STEP 1: Artifact 1, STEP 3: with personas)
            primary_seed = config.get("seed_config", {}).get("primary_seed", 42)
            await _create_run_spec(
                db=db,
                run_id=run_id,
                tenant_id=context.tenant_id,
                project_id=run.get("project_id"),
                ticks_total=max_ticks,
                seed=primary_seed,
                config=config,
                personas_snapshot_id=personas_snapshot_id,
                personas_summary=personas_summary,
            )

            await _write_trace(db, run_id, context.tenant_id, worker_id,
                              ExecutionStage.INITIALIZING_RNG,
                              f"Initializing RNG with seed {primary_seed}")

            # Phase 4: Initialize RNG
            rng = DeterministicRNG(primary_seed)

            await _write_trace(db, run_id, context.tenant_id, worker_id,
                              ExecutionStage.SIMULATION_START,
                              f"Starting simulation with {max_ticks} ticks")

            # Phase 5: Execute simulation (STEP 3: with persona snapshot)
            execution_result = await _execute_simulation(
                db=db,
                run=run,
                rng=rng,
                context=context,
                worker_id=worker_id,
                personas_snapshot_id=personas_snapshot_id,  # STEP 3: immutable personas
            )

            await _write_trace(db, run_id, context.tenant_id, worker_id,
                              ExecutionStage.SIMULATION_COMPLETE,
                              f"Simulation completed: {execution_result.get('ticks_executed', 0)} ticks executed",
                              tick_number=execution_result.get("ticks_executed", 0),
                              agents_processed=execution_result.get("agent_count", 0))

            # Phase 6: Aggregate outcomes (STEP 1: Real numeric results)
            await _write_trace(db, run_id, context.tenant_id, worker_id,
                              ExecutionStage.AGGREGATING_OUTCOMES,
                              "Aggregating simulation outcomes")
            outcomes = _aggregate_outcomes(execution_result)

            # Phase 7: Generate telemetry
            await _write_trace(db, run_id, context.tenant_id, worker_id,
                              ExecutionStage.STORING_TELEMETRY,
                              "Storing telemetry data")
            telemetry_ref = await _store_telemetry(
                db=db,
                run_id=run_id,
                tenant_id=context.tenant_id,
                execution_result=execution_result,
            )

            # Phase 8: Compute reliability
            await _write_trace(db, run_id, context.tenant_id, worker_id,
                              ExecutionStage.COMPUTING_RELIABILITY,
                              "Computing reliability metrics")
            reliability = _compute_reliability(execution_result, outcomes)

            # Phase 9: Store results
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            completed_at = datetime.utcnow()

            await _update_run_complete(
                db=db,
                run_id=run_id,
                outcomes=outcomes,
                telemetry_ref=telemetry_ref,
                reliability=reliability,
                completed_at=completed_at,
                ticks_executed=execution_result.get("ticks_executed", 0),
                execution_counters=execution_result.get("execution_counters"),
            )

            # Phase 10: Update Node with run outcome
            await _update_node_outcome(
                db=db,
                run=run,
                run_id=run_id,
                outcomes=outcomes,
                reliability=reliability,
                telemetry_ref=telemetry_ref,
            )

            # Final trace entry
            await _write_trace(db, run_id, context.tenant_id, worker_id,
                              ExecutionStage.RUN_SUCCEEDED,
                              f"Run completed successfully in {elapsed_ms}ms",
                              duration_ms=elapsed_ms)

            # Update worker heartbeat to clear current run
            await _update_worker_heartbeat(db, worker_id, None, runs_executed_increment=1)

            await db.commit()

            return JobResult(
                job_id=context.job_id,
                status=JobStatus.COMPLETED,
                result={
                    "run_id": run_id,
                    "outcomes": outcomes,
                    "telemetry_ref": telemetry_ref,
                    "reliability_summary": reliability,
                    "worker_id": worker_id,
                },
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=elapsed_ms,
            ).to_dict()

        except Exception as e:
            await db.rollback()
            # Write failure trace
            try:
                await _write_trace(db, run_id, context.tenant_id, worker_id,
                                  ExecutionStage.RUN_FAILED,
                                  f"Run failed: {str(e)}")
                await _update_worker_heartbeat(db, worker_id, None, runs_failed_increment=1)
            except Exception:
                pass  # Don't fail on trace write failure
            await _update_run_status(db, run_id, "failed", error=str(e))
            await db.commit()

            return JobResult(
                job_id=context.job_id,
                status=JobStatus.FAILED,
                error=str(e),
                started_at=started_at,
                completed_at=datetime.utcnow(),
            ).to_dict()


async def _load_run(db: AsyncSession, run_id: str, tenant_id: str) -> Optional[dict]:
    """
    Load run configuration from database.
    Validates tenant ownership.
    """
    from app.models.node import Run

    # Load the Run model
    query = select(Run).where(
        Run.id == uuid.UUID(run_id),
        Run.tenant_id == uuid.UUID(tenant_id),
    )
    result = await db.execute(query)
    run = result.scalar_one_or_none()

    if not run:
        return None

    # Load associated RunConfig
    from sqlalchemy import text
    config_query = text("""
        SELECT versions, seed_config, horizon, tick_rate, scheduler_profile,
               logging_profile, scenario_patch, max_execution_time_ms, max_agents
        FROM run_configs
        WHERE id = :config_id
    """)
    config_result = await db.execute(config_query, {"config_id": run.run_config_ref})
    config_row = config_result.fetchone()

    run_config = {
        "node_id": str(run.node_id),
        "seed_config": (config_row.seed_config if config_row and config_row.seed_config else {"strategy": "single", "primary_seed": 42}),
        "max_ticks": (config_row.horizon if config_row and config_row.horizon else 100),  # Default to 100 ticks
        "tick_rate": (config_row.tick_rate if config_row and config_row.tick_rate else 1),
        "scheduler_profile": (config_row.scheduler_profile if config_row and config_row.scheduler_profile else {}),
        "logging_profile": (config_row.logging_profile if config_row and config_row.logging_profile else {}),
        "scenario_patch": (config_row.scenario_patch if config_row else None),
        "max_agents": (config_row.max_agents if config_row else 100),  # Default to 100 agents
    }

    return {
        "id": run_id,
        "tenant_id": tenant_id,
        "node_id": str(run.node_id),
        "project_id": str(run.project_id),
        "run_config": run_config,
        "actual_seed": run.actual_seed,
        "status": run.status,
    }


async def _update_run_status(
    db: AsyncSession,
    run_id: str,
    status: str,
    started_at: Optional[datetime] = None,
    error: Optional[str] = None,
    worker_id: Optional[str] = None,
):
    """Update run status in database."""
    from app.models.node import Run

    update_data = {
        "status": status,
        "updated_at": datetime.utcnow(),
    }

    if started_at:
        # Update timing with start time
        update_data["timing"] = {
            "started_at": started_at.isoformat(),
        }

    if error:
        update_data["error"] = {
            "message": error,
            "occurred_at": datetime.utcnow().isoformat(),
        }

    # STEP 1: Track worker info
    if worker_id:
        update_data["worker_id"] = worker_id
        update_data["worker_started_at"] = datetime.utcnow()
        update_data["worker_last_heartbeat_at"] = datetime.utcnow()

    stmt = (
        update(Run)
        .where(Run.id == uuid.UUID(run_id))
        .values(**update_data)
    )
    await db.execute(stmt)


async def _update_worker_heartbeat(
    db: AsyncSession,
    worker_id: str,
    current_run_id: Optional[str],
    runs_executed_increment: int = 0,
    runs_failed_increment: int = 0,
):
    """
    Update or create worker heartbeat record (STEP 1 requirement).

    Tracks:
    - worker_id
    - last_seen_at
    - current_run_id (if executing)
    - runs_executed / runs_failed counts
    """
    from sqlalchemy import text

    now = datetime.utcnow()
    hostname = socket.gethostname()
    pid = os.getpid()

    # Upsert worker heartbeat
    upsert_sql = text("""
        INSERT INTO worker_heartbeats (id, worker_id, hostname, pid, last_seen_at, status, current_run_id, runs_executed, runs_failed, created_at, updated_at)
        VALUES (:id, :worker_id, :hostname, :pid, :last_seen_at, :status, :current_run_id, :runs_executed, :runs_failed, :created_at, :updated_at)
        ON CONFLICT (worker_id)
        DO UPDATE SET
            last_seen_at = EXCLUDED.last_seen_at,
            current_run_id = EXCLUDED.current_run_id,
            runs_executed = worker_heartbeats.runs_executed + :runs_executed_inc,
            runs_failed = worker_heartbeats.runs_failed + :runs_failed_inc,
            updated_at = EXCLUDED.updated_at
    """)

    await db.execute(upsert_sql, {
        "id": uuid.uuid4(),
        "worker_id": worker_id,
        "hostname": hostname,
        "pid": pid,
        "last_seen_at": now,
        "status": "active",
        "current_run_id": uuid.UUID(current_run_id) if current_run_id else None,
        "runs_executed": runs_executed_increment,
        "runs_failed": runs_failed_increment,
        "runs_executed_inc": runs_executed_increment,
        "runs_failed_inc": runs_failed_increment,
        "created_at": now,
        "updated_at": now,
    })


async def _write_trace(
    db: AsyncSession,
    run_id: str,
    tenant_id: str,
    worker_id: str,
    execution_stage: str,
    description: str,
    tick_number: Optional[int] = None,
    agents_processed: Optional[int] = None,
    events_count: Optional[int] = None,
    duration_ms: Optional[int] = None,
    metadata: Optional[dict] = None,
):
    """
    Write a RunTrace entry (STEP 1: Artifact 2).

    Each entry includes:
    - run_id
    - timestamp
    - worker_id
    - execution_stage or brief description
    """
    from sqlalchemy import text

    trace_sql = text("""
        INSERT INTO run_traces (
            id, run_id, tenant_id, timestamp, worker_id, execution_stage,
            description, tick_number, agents_processed, events_count,
            duration_ms, metadata, created_at
        ) VALUES (
            :id, :run_id, :tenant_id, :timestamp, :worker_id, :execution_stage,
            :description, :tick_number, :agents_processed, :events_count,
            :duration_ms, :metadata, :created_at
        )
    """)

    await db.execute(trace_sql, {
        "id": uuid.uuid4(),
        "run_id": uuid.UUID(run_id),
        "tenant_id": uuid.UUID(tenant_id),
        "timestamp": datetime.utcnow(),
        "worker_id": worker_id,
        "execution_stage": execution_stage,
        "description": description,
        "tick_number": tick_number,
        "agents_processed": agents_processed,
        "events_count": events_count,
        "duration_ms": duration_ms,
        "metadata": json.dumps(metadata) if metadata else None,
        "created_at": datetime.utcnow(),
    })


async def _create_run_spec(
    db: AsyncSession,
    run_id: str,
    tenant_id: str,
    project_id: str,
    ticks_total: int,
    seed: int,
    config: dict,
    personas_snapshot_id: Optional[str] = None,
    personas_summary: Optional[dict] = None,
):
    """
    Create RunSpec artifact (STEP 1: Artifact 1, STEP 3: Personas Integration).

    Required fields:
    - run_id
    - project_id
    - ticks_total or horizon (must be > 0)
    - seed
    - model or model_config
    - environment_spec (even minimal is required)
    - created_at

    STEP 3 fields:
    - personas_snapshot_id (reference to immutable snapshot)
    - personas_summary (segment breakdown with weights)
    """
    from sqlalchemy import text

    # STEP 1: Validate ticks_total > 0
    if ticks_total < 1:
        raise ValueError(f"STEP 1 VIOLATION: ticks_total must be > 0, got {ticks_total}")

    # Build model config
    model_config = {
        "run_mode": config.get("run_mode", "society"),
        "scheduler_profile": config.get("scheduler_profile", {}),
        "logging_profile": config.get("logging_profile", {}),
        "max_agents": config.get("max_agents", 100),
    }

    # Build environment spec (even minimal is required)
    environment_spec = {
        "scenario_patch": config.get("scenario_patch"),
        "tick_rate": config.get("tick_rate", 1),
        "base_environment": {
            "time": 0,
            "market_conditions": "normal",
        },
    }

    # Extract versions
    versions = config.get("versions", {})
    engine_version = versions.get("engine", "1.0.0")
    ruleset_version = versions.get("ruleset", "1.0.0")
    dataset_version = versions.get("dataset", "1.0.0")

    # STEP 3: Include personas snapshot in RunSpec
    spec_sql = text("""
        INSERT INTO run_specs (
            id, run_id, tenant_id, project_id, ticks_total, seed,
            model_config, environment_spec, scheduler_config,
            personas_snapshot_id, personas_summary,
            engine_version, ruleset_version, dataset_version, created_at
        ) VALUES (
            :id, :run_id, :tenant_id, :project_id, :ticks_total, :seed,
            :model_config, :environment_spec, :scheduler_config,
            :personas_snapshot_id, :personas_summary,
            :engine_version, :ruleset_version, :dataset_version, :created_at
        )
    """)

    await db.execute(spec_sql, {
        "id": uuid.uuid4(),
        "run_id": uuid.UUID(run_id),
        "tenant_id": uuid.UUID(tenant_id),
        "project_id": uuid.UUID(project_id),
        "ticks_total": ticks_total,
        "seed": seed,
        "model_config": json.dumps(model_config),
        "environment_spec": json.dumps(environment_spec),
        "scheduler_config": json.dumps(config.get("scheduler_profile", {})),
        # STEP 3: Personas tracking
        "personas_snapshot_id": uuid.UUID(personas_snapshot_id) if personas_snapshot_id else None,
        "personas_summary": json.dumps(personas_summary) if personas_summary else None,
        "engine_version": engine_version,
        "ruleset_version": ruleset_version,
        "dataset_version": dataset_version,
        "created_at": datetime.utcnow(),
    })


async def _create_persona_snapshot(
    db: AsyncSession,
    tenant_id: str,
    project_id: str,
) -> Tuple[Optional[str], Optional[dict]]:
    """
    STEP 3: Create immutable PersonaSnapshot for this run.

    Creates a snapshot of all active personas in the project at the moment
    of run creation. This ensures:
    - Immutability: The snapshot cannot be changed after creation
    - Auditability: RunSpec references the exact personas used
    - Reproducibility: Same snapshot = same persona input

    Returns:
        Tuple[snapshot_id, personas_summary] or (None, None) if no personas
    """
    from sqlalchemy import text

    # Load active personas from the project
    persona_query = text("""
        SELECT id, label, demographics, preferences, perception_weights,
               bias_parameters, action_priors, uncertainty_score,
               created_at, updated_at
        FROM personas
        WHERE project_id = :project_id AND is_active = true
        ORDER BY created_at ASC
    """)
    result = await db.execute(persona_query, {"project_id": project_id})
    persona_rows = result.fetchall()

    if not persona_rows:
        # No personas found - return None
        return None, None

    # Build personas data array (immutable copy)
    personas_data = []
    segment_counts = {}  # Track segments for summary

    for row in persona_rows:
        persona_dict = {
            "persona_id": str(row.id),
            "label": row.label,
            "demographics": row.demographics or {},
            "preferences": row.preferences or {},
            "perception_weights": row.perception_weights or {},
            "bias_parameters": row.bias_parameters or {},
            "action_priors": row.action_priors or {},
            "uncertainty_score": row.uncertainty_score or 0.5,
            "original_created_at": row.created_at.isoformat() if row.created_at else None,
        }
        personas_data.append(persona_dict)

        # Extract segment from demographics for summary
        demographics = row.demographics or {}
        segment_key = demographics.get("segment", demographics.get("income_bracket", "default"))
        segment_counts[segment_key] = segment_counts.get(segment_key, 0) + 1

    # Compute data hash for integrity verification
    data_json = json.dumps(personas_data, sort_keys=True, default=str)
    data_hash = hashlib.sha256(data_json.encode()).hexdigest()

    # Build segment summary with weights
    total_personas = len(personas_data)
    segment_summary = {
        "segments": [
            {
                "name": segment,
                "count": count,
                "weight": round(count / total_personas, 4),
            }
            for segment, count in sorted(segment_counts.items())
        ],
        "total_segments": len(segment_counts),
        "total_personas": total_personas,
    }

    # Create the snapshot
    snapshot_id = uuid.uuid4()
    snapshot_sql = text("""
        INSERT INTO persona_snapshots (
            id, tenant_id, project_id, name, total_personas,
            segment_summary, personas_data, data_hash,
            confidence_score, is_locked, created_at
        ) VALUES (
            :id, :tenant_id, :project_id, :name, :total_personas,
            :segment_summary, :personas_data, :data_hash,
            :confidence_score, :is_locked, :created_at
        )
    """)

    await db.execute(snapshot_sql, {
        "id": snapshot_id,
        "tenant_id": uuid.UUID(tenant_id),
        "project_id": uuid.UUID(project_id),
        "name": f"Run Snapshot {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
        "total_personas": total_personas,
        "segment_summary": json.dumps(segment_summary),
        "personas_data": json.dumps(personas_data),
        "data_hash": data_hash,
        "confidence_score": 0.8,  # Default confidence
        "is_locked": True,  # Immutable by default
        "created_at": datetime.utcnow(),
    })

    # Return snapshot_id and summary for RunSpec
    return str(snapshot_id), segment_summary


async def _update_run_complete(
    db: AsyncSession,
    run_id: str,
    outcomes: dict,
    telemetry_ref: dict,
    reliability: dict,
    completed_at: datetime,
    ticks_executed: int,
    execution_counters: Optional[dict] = None,
):
    """Update run with completion data."""
    from app.models.node import Run

    # Build timing object
    # First get the existing timing
    query = select(Run.timing).where(Run.id == uuid.UUID(run_id))
    result = await db.execute(query)
    existing_timing = result.scalar_one_or_none() or {}

    timing = {
        **existing_timing,
        "completed_at": completed_at.isoformat(),
        "ticks_executed": ticks_executed,
    }

    if "started_at" in existing_timing:
        started = datetime.fromisoformat(existing_timing["started_at"])
        timing["duration_ms"] = int((completed_at - started).total_seconds() * 1000)

    # Build outputs with execution counters for Evidence Pack (§3.1)
    outputs_data = {
        "outcomes": outcomes,
        "telemetry_ref": telemetry_ref,
        "reliability": reliability,
    }
    if execution_counters:
        outputs_data["execution_counters"] = execution_counters

    # Update the run
    stmt = (
        update(Run)
        .where(Run.id == uuid.UUID(run_id))
        .values(
            status=RunStatus.SUCCEEDED.value,
            timing=timing,
            outputs=outputs_data,
            updated_at=datetime.utcnow(),
        )
    )
    await db.execute(stmt)


async def _update_node_outcome(
    db: AsyncSession,
    run: dict,
    run_id: str,
    outcomes: dict,
    reliability: dict,
    telemetry_ref: dict,
):
    """
    Update the Node's aggregated outcome after run completion.
    Reference: project.md §6.7 (Node.aggregated_outcome)

    This is NOT a mutation of history (C1 compliant) - we're updating
    the current outcome for the node based on completed runs.
    """
    from app.models.node import Node, ConfidenceLevel
    from sqlalchemy import select

    node_id = run.get("node_id")
    if not node_id:
        return

    # Load the node
    query = select(Node).where(Node.id == uuid.UUID(node_id))
    result = await db.execute(query)
    node = result.scalar_one_or_none()

    if not node:
        return

    # Build run reference for node
    run_ref = {
        "run_id": run_id,
        "completed_at": datetime.utcnow().isoformat(),
        "seed": outcomes.get("seed"),
        "telemetry_ref": telemetry_ref,
    }

    # Update run_refs (add this run)
    existing_run_refs = node.run_refs or []
    existing_run_refs.append(run_ref)

    # Compute confidence based on reliability
    confidence_score = reliability.get("confidence", 0.5)
    if confidence_score >= 0.8:
        confidence_level = ConfidenceLevel.HIGH
    elif confidence_score >= 0.6:
        confidence_level = ConfidenceLevel.MEDIUM
    elif confidence_score >= 0.4:
        confidence_level = ConfidenceLevel.LOW
    else:
        confidence_level = ConfidenceLevel.VERY_LOW

    # Build confidence object
    confidence_obj = {
        "level": confidence_level.value,
        "score": confidence_score,
        "factors": {
            "sample_size": outcomes.get("key_metrics", [{}])[1].get("value", 0) if len(outcomes.get("key_metrics", [])) > 1 else 0,
            "run_count": len(existing_run_refs),
        },
        "calibration": reliability.get("calibration"),
    }

    # STEP 4: Ensemble tracking - increment completed run count
    new_run_count = len(existing_run_refs)
    min_ensemble_size = node.min_ensemble_size if hasattr(node, 'min_ensemble_size') else 2
    is_ensemble_complete = new_run_count >= min_ensemble_size

    # STEP 4: Compute aggregated outcome from all runs if ensemble is complete
    aggregated_outcome = outcomes
    outcome_counts = None
    outcome_variance = None

    if is_ensemble_complete and new_run_count > 1:
        # Aggregate outcomes from all runs using mean aggregation
        aggregated_outcome, outcome_counts, outcome_variance = await _aggregate_ensemble_outcomes(
            db=db,
            node_id=node_id,
            current_outcomes=outcomes,
            aggregation_method=node.aggregation_method if hasattr(node, 'aggregation_method') else "mean",
        )

    # Update node with all ensemble tracking fields
    stmt = (
        update(Node)
        .where(Node.id == uuid.UUID(node_id))
        .values(
            aggregated_outcome=aggregated_outcome,
            run_refs=existing_run_refs,
            confidence=confidence_obj,
            is_explored=True,
            # STEP 4: Ensemble tracking fields
            completed_run_count=new_run_count,
            is_ensemble_complete=is_ensemble_complete,
            outcome_counts=outcome_counts,
            outcome_variance=outcome_variance,
            updated_at=datetime.utcnow(),
        )
    )
    await db.execute(stmt)

    # STEP 2: Update ProjectSpec.has_baseline and root_node_id if this is a baseline node
    if node.is_baseline:
        from app.models.project_spec import ProjectSpec
        project_id = run.get("project_id")
        if project_id:
            project_stmt = (
                update(ProjectSpec)
                .where(ProjectSpec.id == uuid.UUID(project_id))
                .values(
                    has_baseline=True,
                    root_node_id=uuid.UUID(node_id),
                    updated_at=datetime.utcnow(),
                )
            )
            await db.execute(project_stmt)


async def _aggregate_ensemble_outcomes(
    db: AsyncSession,
    node_id: str,
    current_outcomes: dict,
    aggregation_method: str = "mean",
) -> tuple[dict, dict, dict]:
    """
    STEP 4: Aggregate outcomes from all completed runs for a node.

    This implements proper probability aggregation from multiple ensemble runs,
    ensuring NO hardcoded probabilities. All values are computed from actual runs.

    Args:
        db: Database session
        node_id: The node ID to aggregate outcomes for
        current_outcomes: The outcomes from the current (just completed) run
        aggregation_method: Method to use - "mean", "weighted_mean", "median", "mode"

    Returns:
        Tuple of (aggregated_outcome, outcome_counts, outcome_variance)
    """
    from app.models.node import Run
    from statistics import mean, median, variance
    from collections import Counter

    # Load all succeeded runs for this node
    query = select(Run).where(
        Run.node_id == uuid.UUID(node_id),
        Run.status == RunStatus.SUCCEEDED.value,  # "succeeded" not "completed"
    )
    result = await db.execute(query)
    all_runs = result.scalars().all()

    if len(all_runs) < 2:
        # Not enough runs for aggregation - return current outcomes
        return current_outcomes, None, None

    # Collect all outcomes from all runs
    all_outcomes = []
    all_probabilities = []
    all_metrics = {}  # metric_name -> [values]

    for run in all_runs:
        run_outputs = run.outputs or {}
        run_outcomes = run_outputs.get("outcomes", {})
        all_outcomes.append(run_outcomes)

        # Collect primary outcome probability
        if "primary_outcome_probability" in run_outcomes:
            all_probabilities.append(run_outcomes["primary_outcome_probability"])

        # Collect key metrics
        for metric in run_outcomes.get("key_metrics", []):
            metric_name = metric.get("metric_name")
            value = metric.get("value")
            if metric_name and value is not None:
                if metric_name not in all_metrics:
                    all_metrics[metric_name] = []
                all_metrics[metric_name].append(value)

    # STEP 4: Compute aggregated values based on method (NO hardcoding)
    aggregated = dict(current_outcomes)

    if all_probabilities:
        if aggregation_method == "mean":
            aggregated["primary_outcome_probability"] = mean(all_probabilities)
        elif aggregation_method == "median":
            aggregated["primary_outcome_probability"] = median(all_probabilities)
        elif aggregation_method == "mode":
            counter = Counter(all_probabilities)
            aggregated["primary_outcome_probability"] = counter.most_common(1)[0][0]
        else:  # Default to mean
            aggregated["primary_outcome_probability"] = mean(all_probabilities)

    # Aggregate key metrics using same method
    aggregated_metrics = []
    for metric_name, values in all_metrics.items():
        if len(values) > 0:
            if aggregation_method == "mean":
                agg_value = mean(values)
            elif aggregation_method == "median":
                agg_value = median(values)
            else:
                agg_value = mean(values)

            aggregated_metrics.append({
                "metric_name": metric_name,
                "value": agg_value,
                "sample_size": len(values),
            })
    aggregated["key_metrics"] = aggregated_metrics

    # Compute outcome counts (for tracking distribution)
    outcome_counts = {}
    for outcomes_data in all_outcomes:
        primary = outcomes_data.get("primary_outcome", "unknown")
        outcome_counts[primary] = outcome_counts.get(primary, 0) + 1

    # Compute variance for numeric values
    outcome_variance = {}
    if len(all_probabilities) >= 2:
        outcome_variance["primary_outcome_probability"] = variance(all_probabilities)
    for metric_name, values in all_metrics.items():
        if len(values) >= 2:
            outcome_variance[metric_name] = variance(values)

    # Add ensemble metadata
    aggregated["ensemble_metadata"] = {
        "run_count": len(all_runs),
        "aggregation_method": aggregation_method,
        "aggregated_at": datetime.utcnow().isoformat(),
    }

    return aggregated, outcome_counts, outcome_variance


class DeterministicRNG:
    """
    Deterministic random number generator.
    Reference: project.md §10.1

    Ensures reproducible simulation results.
    """

    def __init__(self, seed: int):
        self.seed = seed
        self._state = seed

    def next_int(self, min_val: int = 0, max_val: int = 0xFFFFFFFF) -> int:
        """Generate next integer in range [min_val, max_val]."""
        # Simple xorshift32 for determinism
        self._state ^= (self._state << 13) & 0xFFFFFFFF
        self._state ^= (self._state >> 17) & 0xFFFFFFFF
        self._state ^= (self._state << 5) & 0xFFFFFFFF
        self._state &= 0xFFFFFFFF

        range_size = max_val - min_val + 1
        return min_val + (self._state % range_size)

    def next_float(self) -> float:
        """Generate next float in range [0, 1)."""
        return self.next_int(0, 0xFFFFFFFF - 1) / 0xFFFFFFFF

    def derive_seed(self, domain: str) -> int:
        """
        Derive a sub-seed for a specific domain.
        Used to create independent RNG streams.
        """
        combined = f"{self.seed}:{domain}"
        hash_bytes = hashlib.sha256(combined.encode()).digest()
        return int.from_bytes(hash_bytes[:4], "big")

    def create_agent_rng(self, agent_id: str, tick: int) -> "DeterministicRNG":
        """Create RNG for specific agent at specific tick."""
        derived = self.derive_seed(f"agent:{agent_id}:tick:{tick}")
        return DeterministicRNG(derived)

    def random_sample(self, items: List[Any], sample_size: int) -> List[Any]:
        """
        Deterministically sample items using Fisher-Yates shuffle.
        §3.3 Scheduler: Used for sampling policies.
        """
        if sample_size >= len(items):
            return items

        # Create a copy to avoid mutating original
        shuffled = items.copy()
        n = len(shuffled)

        # Partial Fisher-Yates shuffle (only shuffle first sample_size items)
        for i in range(min(sample_size, n)):
            # Generate random index in remaining items
            j = i + (self.next() % (n - i))
            shuffled[i], shuffled[j] = shuffled[j], shuffled[i]

        return shuffled[:sample_size]


def _stratified_sample(agents: List[Any], sampling_ratio: float, rng: DeterministicRNG) -> List[Any]:
    """
    Stratified sampling by agent segment.
    §3.3 Scheduler: Ensures representation from each segment.
    """
    # Group agents by segment
    segments: Dict[str, List[Any]] = {}
    for agent in agents:
        segment = getattr(agent, "segment", "default")
        if segment not in segments:
            segments[segment] = []
        segments[segment].append(agent)

    # Sample proportionally from each segment
    sampled = []
    for segment_name, segment_agents in segments.items():
        sample_size = max(1, int(len(segment_agents) * sampling_ratio))
        segment_rng = DeterministicRNG(rng.derive_seed(f"stratified:{segment_name}"))
        sampled.extend(segment_rng.random_sample(segment_agents, sample_size))

    return sampled


async def _execute_simulation(
    db: AsyncSession,
    run: dict,
    rng: DeterministicRNG,
    context: JobContext,
    worker_id: str = "unknown",
    personas_snapshot_id: Optional[str] = None,
) -> dict:
    """
    Execute the simulation engine.

    Uses the Rule Engine (P1-001) and Agent State Machine (P1-002).
    Produces execution trace for telemetry and outcome aggregation.

    STEP 3: Uses personas_snapshot_id to load immutable persona data.

    Returns execution trace data for telemetry and outcomes.
    """
    config = run.get("run_config", {}) or {}
    max_ticks = config.get("max_ticks") or 100  # Default to 100 ticks
    tick_rate = config.get("tick_rate") or 1

    # Safety check
    if not isinstance(max_ticks, int) or max_ticks < 1:
        max_ticks = 100

    import logging
    logging.warning(f"DEBUG: max_ticks={max_ticks}, type={type(max_ticks)}, config={config}")

    # Initialize rule engine
    rule_engine = get_rule_engine()

    # Initialize leakage guard for backtest scenarios (§1.3)
    leakage_guard = create_leakage_guard_from_config(config, strict_mode=False)

    # STEP 3: Load personas from snapshot (immutable) and create agents
    agents = await _load_agents_for_run(db, run, rng, personas_snapshot_id)

    # Create agent pool for social interactions
    agent_pool = AgentPool()
    for agent in agents:
        agent_pool.add(agent)

    # Prepare execution trace
    tick_data = []
    agent_snapshots = {}
    events_processed = []
    metrics_by_tick = []
    outcome_tracker = OutcomeTracker()
    execution_counters = ExecutionCounters()  # Evidence Pack instrumentation (§3.1)

    # Apply scenario patch if present
    scenario_patch = config.get("scenario_patch")
    environment = _apply_scenario_patch(scenario_patch)

    # §3.3 Scheduler Configuration
    scheduler_config = config.get("scheduler", {})
    batch_size = scheduler_config.get("batch_size", 100)  # Agents per batch
    backpressure_threshold_ms = scheduler_config.get("backpressure_threshold_ms", 500)  # ms per tick
    sampling_policy = scheduler_config.get("sampling_policy", "all")  # all, random, stratified
    sampling_ratio = scheduler_config.get("sampling_ratio", 1.0)  # For random/stratified

    # Track scheduler metrics for Evidence Pack (§3.3)
    execution_counters.scheduler_config = {
        "batch_size": batch_size,
        "sampling_policy": sampling_policy,
        "sampling_ratio": sampling_ratio,
        "backpressure_threshold_ms": backpressure_threshold_ms,
    }

    # Main simulation loop (Society Mode)
    for tick in range(max_ticks):
        tick_start = time.perf_counter()
        execution_counters.record_partition()  # §3.3: Each tick is a partition

        # Collect peer states for social observation
        peer_states = {
            str(a.id): a.to_snapshot()
            for a in agent_pool.get_all()
            if a.state != EngineAgentState.TERMINATED
        }

        # §3.3 Sampling Policy Application
        active_agents = agent_pool.get_active()
        if sampling_policy == "random" and sampling_ratio < 1.0:
            # Random sampling - select subset of agents
            sample_size = max(1, int(len(active_agents) * sampling_ratio))
            active_agents = rng.random_sample(active_agents, sample_size)
        elif sampling_policy == "stratified" and sampling_ratio < 1.0:
            # Stratified sampling - sample from each segment proportionally
            active_agents = _stratified_sample(active_agents, sampling_ratio, rng)
        # else: "all" policy - process all agents

        # Run each agent through the tick (in batches for §3.3)
        agent_updates = []
        num_agents = len(active_agents)
        for batch_start in range(0, num_agents, batch_size):
            batch_end = min(batch_start + batch_size, num_agents)
            batch = active_agents[batch_start:batch_end]
            execution_counters.record_batch()  # §3.3: Track batch execution

            for agent in batch:
                try:
                    # Create RNG for this agent at this tick (deterministic)
                    agent_rng = rng.create_agent_rng(str(agent.id), tick)

                    # Agent lifecycle: Observe -> Evaluate -> Decide -> Act -> Update
                    # §3.1 Evidence Pack: Record each loop stage execution
                    # BUG-007 FIX: agent.observe() expects List[Dict], not dict
                    # Convert peer_states dict values to list for observe() method
                    observation = agent.observe(environment, list(peer_states.values()))
                    execution_counters.record_observe()

                    evaluation = agent.evaluate(observation)
                    execution_counters.record_evaluate()

                    decision = agent.decide(evaluation)
                    execution_counters.record_decide()

                    action_results = []
                    if decision:
                        action_results = agent.act(decision)
                        execution_counters.record_act()
                        events_processed.extend(action_results)

                    # Apply rule engine for behavioral modifications
                    # Get peer IDs for this agent
                    peer_ids = [str(p.id) for p in agent_pool.get_peers(agent)]
                    rule_context = RuleContext(
                        agent_id=str(agent.id),
                        tick=tick,
                        rng_seed=agent_rng.seed,  # BUG-008 fix: was 'seed', should be 'rng_seed'
                        environment=environment,
                        agent_state=agent.to_full_state(),
                        peer_states=[
                            s for aid, s in peer_states.items() if aid in peer_ids
                        ],  # BUG-008b fix: RuleContext expects List, not Dict
                        metadata={"global_metrics": outcome_tracker.get_current_metrics()},
                    )

                    # Run rules for this agent
                    rule_results = rule_engine.run_agent_tick(rule_context)

                    # §3.4 Evidence Pack: Record rule applications
                    rules_applied = rule_results.get("rules_applied", [])
                    for rule_info in rules_applied:
                        execution_counters.record_rule_application(
                            rule_name=rule_info.get("rule_name", "unknown"),
                            rule_version=rule_info.get("rule_version", "1.0.0"),
                            insertion_point=rule_info.get("insertion_point", "update"),
                            agents_affected=1,
                        )

                    # Apply rule-driven state updates
                    state_updates = rule_results.get("state_updates", {})
                    agent.update(action_results, state_updates)
                    execution_counters.record_update()

                    # Record complete agent step
                    execution_counters.record_agent_step()

                    # Track updates
                    agent_updates.append({
                        "agent_id": str(agent.id),
                        "observation": _summarize_observation(observation),
                        "decision": decision.get("action_type") if decision else None,
                        "actions": len(action_results),
                        "state_delta": _compute_state_delta(rule_results),
                    })

                    # Update outcome tracker
                    outcome_tracker.record_agent_action(
                        agent_id=str(agent.id),
                        tick=tick,
                        decision=decision,
                        action_results=action_results,
                    )

                except Exception as e:
                    # Log agent error but continue simulation
                    agent_updates.append({
                        "agent_id": str(agent.id),
                        "error": str(e),
                    })

        # Compute tick metrics
        tick_metrics = outcome_tracker.compute_tick_metrics(tick, agent_pool)
        metrics_by_tick.append(tick_metrics)

        # Record tick data for telemetry
        tick_elapsed_ms = int((time.perf_counter() - tick_start) * 1000)

        # §3.3 Backpressure Detection: If tick takes too long, record it
        if tick_elapsed_ms > backpressure_threshold_ms:
            execution_counters.record_backpressure()

        tick_result = {
            "tick": tick,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_updates": agent_updates,
            "events_triggered": [e.get("event_type") for e in events_processed[-10:]],
            "metrics": tick_metrics,
            "elapsed_ms": tick_elapsed_ms,
        }
        tick_data.append(tick_result)

        # Store agent snapshots at keyframe intervals
        logging_profile = config.get("logging_profile", {})
        keyframe_interval = logging_profile.get("keyframe_interval", 100)
        if tick % keyframe_interval == 0:
            agent_snapshots[tick] = {
                str(a.id): a.to_snapshot()
                for a in agent_pool.get_all()
            }

        # Check for early termination
        if _should_terminate_early(tick_result, config):
            break

    # Final agent states
    final_agent_states = {
        str(a.id): a.to_full_state()
        for a in agent_pool.get_all()
    }

    return {
        "ticks_executed": len(tick_data),
        "ticks_configured": max_ticks,
        "tick_data": tick_data,
        "agent_snapshots": agent_snapshots,
        "final_agent_states": final_agent_states,
        "events_processed": events_processed,
        "metrics_by_tick": metrics_by_tick,
        "outcome_distribution": outcome_tracker.get_outcome_distribution(),
        "seed_used": rng.seed,
        "agent_count": len(agents),
        # §3.1 Evidence Pack: Execution counters for verification
        "execution_counters": execution_counters.to_dict(),
        # §1.3 Evidence Pack: Leakage guard stats for anti-leakage proof
        "leakage_guard_stats": leakage_guard.get_stats().to_dict() if leakage_guard.is_active() else None,
    }


async def _load_agents_for_run(
    db: AsyncSession,
    run: dict,
    rng: DeterministicRNG,
    personas_snapshot_id: Optional[str] = None,
) -> List[Agent]:
    """
    STEP 3: Load personas and compile them into agents for this run.

    Priority:
    1. Use PersonaSnapshot if available (STEP 3 compliant - immutable)
    2. Fall back to live personas table (backwards compatibility)
    3. Create default agents if no personas found

    The snapshot ensures the exact same personas are used for reproducibility.
    """
    from sqlalchemy import text

    project_id = run.get("project_id")
    config = run.get("run_config", {}) or {}
    max_agents = config.get("max_agents") or 100

    agents = []
    personas_data = []

    # STEP 3: Try to load from PersonaSnapshot first (immutable source)
    if personas_snapshot_id:
        snapshot_query = text("""
            SELECT personas_data
            FROM persona_snapshots
            WHERE id = :snapshot_id AND is_locked = true
        """)
        result = await db.execute(snapshot_query, {"snapshot_id": personas_snapshot_id})
        row = result.fetchone()
        if row and row.personas_data:
            # Parse snapshot data (stored as JSONB)
            snapshot_data = row.personas_data if isinstance(row.personas_data, list) else json.loads(row.personas_data)
            personas_data = snapshot_data[:max_agents]

    # Fallback: Load from live personas table if no snapshot data
    if not personas_data:
        persona_query = text("""
            SELECT id, label, demographics, preferences, perception_weights,
                   bias_parameters, action_priors, uncertainty_score
            FROM personas
            WHERE project_id = :project_id AND is_active = true
            LIMIT :max_agents
        """)
        result = await db.execute(persona_query, {
            "project_id": project_id,
            "max_agents": max_agents,
        })
        persona_rows = result.fetchall()

        for row in persona_rows:
            personas_data.append({
                "persona_id": str(row.id),
                "label": row.label,
                "demographics": row.demographics or {},
                "preferences": row.preferences or {},
                "perception_weights": row.perception_weights or {},
                "bias_parameters": row.bias_parameters or {},
                "action_priors": row.action_priors or {},
                "uncertainty_score": row.uncertainty_score or 0.5,
            })

    # Create agents from persona data
    for persona_dict in personas_data:
        agent = AgentFactory.create_from_persona(persona_dict)
        agents.append(agent)

    # If no personas found, create sample agents
    if not agents:
        agents = AgentFactory.create_population(
            count=min(10, max_agents),
            persona_template={
                "label": "Default Agent",
                "demographics": {"age": 35, "income": "medium"},
                "preferences": {},
                "perception_weights": {},
                "bias_parameters": {},
                "action_priors": {},
            },
            variation_factor=0.2,
            rng_seed=rng.seed,
        )

    return agents


def _apply_scenario_patch(scenario_patch: Optional[dict]) -> dict:
    """
    Apply scenario patch to create the simulation environment.
    """
    environment = {
        "time": 0,
        "market_conditions": "normal",
        "external_events": [],
        "global_modifiers": {},
    }

    if scenario_patch:
        # Apply variable changes
        for key, value in scenario_patch.get("variables", {}).items():
            environment[key] = value

        # Add events
        environment["external_events"] = scenario_patch.get("events", [])

        # Apply modifiers
        environment["global_modifiers"] = scenario_patch.get("modifiers", {})

    return environment


def _summarize_observation(observation: dict) -> dict:
    """Summarize observation for telemetry (reduce size)."""
    return {
        "environment_signals": len(observation.get("environment_signals", [])),
        "peer_count": observation.get("peer_count", 0),
        "events_observed": len(observation.get("events", [])),
    }


def _compute_state_delta(rule_results: dict) -> dict:
    """Extract state delta from rule results."""
    return {
        k: v for k, v in rule_results.get("state_updates", {}).items()
        if k not in ["timestamp"]
    }


class ExecutionCounters:
    """
    Execution counters for Evidence Pack verification (§3.1).

    Tracks loop stage executions, rule applications, and LLM calls
    to provide proof of correct engine execution.
    """

    def __init__(self):
        # Loop stage counters (§3.1)
        self.loop_stage_counters: Dict[str, int] = {
            "observe": 0,
            "evaluate": 0,
            "decide": 0,
            "act": 0,
            "update": 0,
        }

        # Rule application counts (§3.4)
        self.rule_application_counts: Dict[str, Dict[str, int]] = {}

        # LLM tracking (§1.4 / C5)
        self.llm_calls_in_tick_loop: int = 0
        self.llm_calls_in_compilation: int = 0

        # Scheduler metrics (§3.3)
        self.partitions_count: int = 0
        self.batches_count: int = 0
        self.backpressure_events: int = 0
        self.scheduler_config: Dict[str, Any] = {}  # Set by main loop

        # Total agent steps
        self.agent_steps_executed: int = 0

    def record_observe(self):
        """Record an observe() call."""
        self.loop_stage_counters["observe"] += 1

    def record_evaluate(self):
        """Record an evaluate() call."""
        self.loop_stage_counters["evaluate"] += 1

    def record_decide(self):
        """Record a decide() call."""
        self.loop_stage_counters["decide"] += 1

    def record_act(self):
        """Record an act() call."""
        self.loop_stage_counters["act"] += 1

    def record_update(self):
        """Record an update() call."""
        self.loop_stage_counters["update"] += 1

    def record_agent_step(self):
        """Record a complete agent step."""
        self.agent_steps_executed += 1

    def record_rule_application(
        self,
        rule_name: str,
        rule_version: str,
        insertion_point: str,
        agents_affected: int = 1,
    ):
        """Record a rule application."""
        key = f"{rule_name}:{rule_version}:{insertion_point}"
        if key not in self.rule_application_counts:
            self.rule_application_counts[key] = {
                "rule_name": rule_name,
                "rule_version": rule_version,
                "insertion_point": insertion_point,
                "application_count": 0,
                "agents_affected": 0,
            }
        self.rule_application_counts[key]["application_count"] += 1
        self.rule_application_counts[key]["agents_affected"] += agents_affected

    def record_batch(self):
        """Record a batch execution."""
        self.batches_count += 1

    def record_partition(self):
        """Record a partition."""
        self.partitions_count += 1

    def record_backpressure(self):
        """Record a backpressure event."""
        self.backpressure_events += 1

    def to_dict(self) -> Dict[str, Any]:
        """Export counters for Evidence Pack."""
        return {
            "loop_stage_counters": self.loop_stage_counters.copy(),
            "rule_application_counts": list(self.rule_application_counts.values()),
            "llm_calls_in_tick_loop": self.llm_calls_in_tick_loop,
            "llm_calls_in_compilation": self.llm_calls_in_compilation,
            "partitions_count": self.partitions_count,
            "batches_count": self.batches_count,
            "backpressure_events": self.backpressure_events,
            "agent_steps_executed": self.agent_steps_executed,
            "scheduler_config": self.scheduler_config,  # §3.3 scheduler policy documentation
        }


class OutcomeTracker:
    """
    Tracks simulation outcomes and metrics across ticks.
    Used for aggregating final outcomes.
    """

    def __init__(self):
        self.action_counts: Dict[str, int] = {}
        self.outcome_votes: Dict[str, float] = {}
        self.metric_series: Dict[str, List[float]] = {}
        self.agent_outcomes: Dict[str, str] = {}

    def record_agent_action(
        self,
        agent_id: str,
        tick: int,
        decision: Optional[dict],
        action_results: List[dict],
    ):
        """Record an agent's action for outcome tracking."""
        if decision:
            action_type = decision.get("action_type", "none")
            self.action_counts[action_type] = self.action_counts.get(action_type, 0) + 1

            # Track outcome votes (e.g., for adoption scenarios)
            outcome = decision.get("outcome_signal")
            if outcome:
                self.outcome_votes[outcome] = self.outcome_votes.get(outcome, 0) + 1

    def compute_tick_metrics(self, tick: int, agent_pool: AgentPool) -> dict:
        """Compute metrics for this tick."""
        active_count = len(agent_pool.get_active())
        total_count = len(agent_pool.get_all())

        metrics = {
            "active_agents": active_count,
            "total_agents": total_count,
            "activity_rate": active_count / total_count if total_count > 0 else 0,
        }

        # Track metric series
        for key, value in metrics.items():
            if key not in self.metric_series:
                self.metric_series[key] = []
            self.metric_series[key].append(value)

        return metrics

    def get_current_metrics(self) -> dict:
        """Get current aggregated metrics."""
        return {
            "action_counts": dict(self.action_counts),
            "outcome_votes": dict(self.outcome_votes),
        }

    def get_outcome_distribution(self) -> Dict[str, float]:
        """Get normalized outcome distribution."""
        total = sum(self.outcome_votes.values()) or 1
        return {
            outcome: count / total
            for outcome, count in self.outcome_votes.items()
        }


def _should_terminate_early(tick_result: dict, config: dict) -> bool:
    """Check if simulation should terminate early."""
    # Could check for:
    # - All agents inactive
    # - Target reached (in Target Mode)
    # - Stability achieved
    return False


def _aggregate_outcomes(execution_result: dict) -> dict:
    """
    Aggregate simulation results into outcomes.
    Reference: project.md §6.7 (AggregatedOutcome)

    Returns metrics suitable for Node storage.
    """
    ticks = execution_result.get("ticks_executed", 0)
    outcome_distribution = execution_result.get("outcome_distribution", {})
    metrics_by_tick = execution_result.get("metrics_by_tick", [])

    # Determine primary outcome
    if outcome_distribution:
        primary_outcome = max(outcome_distribution.keys(), key=lambda k: outcome_distribution[k])
        primary_probability = outcome_distribution[primary_outcome]
    else:
        primary_outcome = "simulation_complete"
        primary_probability = 1.0

    # Compute key metrics from final tick
    final_metrics = metrics_by_tick[-1] if metrics_by_tick else {}
    key_metrics = [
        {
            "metric_name": "ticks_executed",
            "value": ticks,
            "unit": "ticks",
        },
        {
            "metric_name": "agents_simulated",
            "value": execution_result.get("agent_count", 0),
            "unit": "agents",
        },
        {
            "metric_name": "events_processed",
            "value": len(execution_result.get("events_processed", [])),
            "unit": "events",
        },
        {
            "metric_name": "final_activity_rate",
            "value": final_metrics.get("activity_rate", 0),
            "unit": "ratio",
        },
    ]

    # Compute variance if we have metric series
    variance_metrics = {}
    if metrics_by_tick:
        for key in ["activity_rate"]:
            values = [m.get(key, 0) for m in metrics_by_tick if key in m]
            if len(values) > 1:
                mean = sum(values) / len(values)
                variance = sum((v - mean) ** 2 for v in values) / len(values)
                variance_metrics[key] = variance

    # Generate summary text
    summary_text = (
        f"Simulation completed after {ticks} ticks with {execution_result.get('agent_count', 0)} agents. "
        f"Primary outcome: {primary_outcome} ({primary_probability:.1%} probability)."
    )

    return {
        "primary_outcome": primary_outcome,
        "primary_outcome_probability": primary_probability,
        "outcome_distribution": outcome_distribution,
        "key_metrics": key_metrics,
        "variance_metrics": variance_metrics if variance_metrics else None,
        "summary_text": summary_text,
        "seed": execution_result.get("seed_used"),
    }


async def _store_telemetry(
    db: AsyncSession,
    run_id: str,
    tenant_id: str,
    execution_result: dict,
) -> dict:
    """
    Store telemetry data in object storage.
    Reference: project.md §6.8

    Uses TelemetryService for proper telemetry structure:
    - keyframes: Full agent snapshots at intervals (for seeking)
    - deltas: Changes between ticks (for playback)
    - index: Quick lookup for events and ticks

    Returns storage reference.
    """
    from app.services.telemetry import get_telemetry_service

    telemetry_service = get_telemetry_service()

    # Use TelemetryService to convert and store
    ref = await telemetry_service.store_from_execution_result(
        tenant_id=tenant_id,
        run_id=run_id,
        execution_result=execution_result,
        compress=True,
    )

    return ref.to_dict()


def _compute_reliability(execution_result: dict, outcomes: dict) -> dict:
    """
    Compute basic reliability metrics.
    Reference: project.md §7.1

    Full reliability computation is in P2-001.
    """
    return {
        "confidence": 0.5,  # Placeholder
        "calibration": None,
        "stability": None,
        "data_gaps": [],
    }


@shared_task(
    bind=True,
    base=TenantAwareTask,
    name="app.tasks.run_executor.cancel_run",
)
def cancel_run(self, run_id: str, context: dict) -> dict:
    """
    Cancel a running simulation.
    """
    ctx = JobContext.from_dict(context)
    return run_async(_cancel_run(run_id, ctx))


async def _cancel_run(run_id: str, context: JobContext) -> dict:
    """Cancel a run and clean up resources."""
    # BUG-006 FIX: Create fresh session factory for current event loop
    AsyncSessionLocal = get_async_session()
    async with AsyncSessionLocal() as db:
        await _update_run_status(db, run_id, "cancelled")
        await db.commit()

    return JobResult(
        job_id=context.job_id,
        status=JobStatus.CANCELLED,
        result={"run_id": run_id, "cancelled_at": datetime.utcnow().isoformat()},
    ).to_dict()


@shared_task(
    bind=True,
    base=TenantAwareTask,
    name="app.tasks.run_executor.batch_runs",
)
def batch_runs(self, run_ids: list[str], context: dict) -> dict:
    """
    Execute multiple runs in parallel (for multi-seed scenarios).
    Reference: project.md §6.5 (multi strategy)
    """
    ctx = JobContext.from_dict(context)

    # Submit each run as a separate task
    from app.tasks.run_executor import execute_run

    tasks = []
    for run_id in run_ids:
        task = execute_run.apply_async(
            args=[run_id, ctx.to_dict()],
            priority=ctx.priority.value,
        )
        tasks.append({"run_id": run_id, "task_id": task.id})

    return {
        "job_id": ctx.job_id,
        "batch_size": len(run_ids),
        "tasks": tasks,
        "status": "submitted",
    }
