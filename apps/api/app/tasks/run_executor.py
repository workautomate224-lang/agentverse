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
"""

import asyncio
import hashlib
import json
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
# Import services
from app.services.node_service import (
    NodeService,
    get_node_service,
    ArtifactRef,
    AggregatedOutcome,
    NodeConfidence,
)
from app.models.node import ConfidenceLevel


# Async database session for background tasks
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


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

    Phases:
    1. Load run configuration and validate
    2. Initialize deterministic RNG with seed
    3. Execute simulation ticks
    4. Aggregate outcomes
    5. Generate telemetry
    6. Compute reliability metrics
    7. Store results
    """
    started_at = datetime.utcnow()
    start_time = time.perf_counter()

    async with AsyncSessionLocal() as db:
        try:
            # Phase 1: Load and validate
            run = await _load_run(db, run_id, context.tenant_id)
            if not run:
                return JobResult(
                    job_id=context.job_id,
                    status=JobStatus.FAILED,
                    error=f"Run not found: {run_id}",
                ).to_dict()

            # Update run status to RUNNING
            await _update_run_status(db, run_id, "running", started_at=started_at)

            # Phase 2: Initialize RNG
            primary_seed = run.get("run_config", {}).get("seed_config", {}).get("primary_seed", 42)
            rng = DeterministicRNG(primary_seed)

            # Phase 3: Execute simulation
            execution_result = await _execute_simulation(
                db=db,
                run=run,
                rng=rng,
                context=context,
            )

            # Phase 4: Aggregate outcomes
            outcomes = _aggregate_outcomes(execution_result)

            # Phase 5: Generate telemetry
            telemetry_ref = await _store_telemetry(
                db=db,
                run_id=run_id,
                tenant_id=context.tenant_id,
                execution_result=execution_result,
            )

            # Phase 6: Compute reliability (placeholder)
            reliability = _compute_reliability(execution_result, outcomes)

            # Phase 7: Store results
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
            )

            # Phase 8: Update Node with run outcome (C1: fork-not-mutate applies to history, outcomes update is OK)
            await _update_node_outcome(
                db=db,
                run=run,
                run_id=run_id,
                outcomes=outcomes,
                reliability=reliability,
                telemetry_ref=telemetry_ref,
            )

            await db.commit()

            return JobResult(
                job_id=context.job_id,
                status=JobStatus.COMPLETED,
                result={
                    "run_id": run_id,
                    "outcomes": outcomes,
                    "telemetry_ref": telemetry_ref,
                    "reliability_summary": reliability,
                },
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=elapsed_ms,
            ).to_dict()

        except Exception as e:
            await db.rollback()
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
        "seed_config": config_row.seed_config if config_row else {"strategy": "single", "primary_seed": 42},
        "max_ticks": config_row.horizon if config_row else 1000,
        "tick_rate": config_row.tick_rate if config_row else 1,
        "scheduler_profile": config_row.scheduler_profile if config_row else {},
        "logging_profile": config_row.logging_profile if config_row else {},
        "scenario_patch": config_row.scenario_patch if config_row else None,
        "max_agents": config_row.max_agents if config_row else None,
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

    stmt = (
        update(Run)
        .where(Run.id == uuid.UUID(run_id))
        .values(**update_data)
    )
    await db.execute(stmt)


async def _update_run_complete(
    db: AsyncSession,
    run_id: str,
    outcomes: dict,
    telemetry_ref: dict,
    reliability: dict,
    completed_at: datetime,
    ticks_executed: int,
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

    # Update the run
    stmt = (
        update(Run)
        .where(Run.id == uuid.UUID(run_id))
        .values(
            status=RunStatus.SUCCEEDED.value,
            timing=timing,
            outputs={
                "outcomes": outcomes,
                "telemetry_ref": telemetry_ref,
                "reliability": reliability,
            },
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

    # Update node
    stmt = (
        update(Node)
        .where(Node.id == uuid.UUID(node_id))
        .values(
            aggregated_outcome=outcomes,
            run_refs=existing_run_refs,
            confidence=confidence_obj,
            is_explored=True,
            updated_at=datetime.utcnow(),
        )
    )
    await db.execute(stmt)


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


async def _execute_simulation(
    db: AsyncSession,
    run: dict,
    rng: DeterministicRNG,
    context: JobContext,
) -> dict:
    """
    Execute the simulation engine.

    Uses the Rule Engine (P1-001) and Agent State Machine (P1-002).
    Produces execution trace for telemetry and outcome aggregation.

    Returns execution trace data for telemetry and outcomes.
    """
    config = run.get("run_config", {})
    max_ticks = config.get("max_ticks", 1000)
    tick_rate = config.get("tick_rate", 1)

    # Initialize rule engine
    rule_engine = get_rule_engine()

    # Load personas and create agents
    # TODO: Load actual personas from database based on project
    agents = await _load_agents_for_run(db, run, rng)

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

    # Apply scenario patch if present
    scenario_patch = config.get("scenario_patch")
    environment = _apply_scenario_patch(scenario_patch)

    # Main simulation loop (Society Mode)
    for tick in range(max_ticks):
        tick_start = time.perf_counter()

        # Collect peer states for social observation
        peer_states = {
            str(a.id): a.to_snapshot()
            for a in agent_pool.get_all()
            if a.state != EngineAgentState.TERMINATED
        }

        # Run each agent through the tick
        agent_updates = []
        for agent in agent_pool.get_active():
            try:
                # Create RNG for this agent at this tick (deterministic)
                agent_rng = rng.create_agent_rng(str(agent.id), tick)

                # Agent lifecycle: Observe -> Evaluate -> Decide -> Act -> Update
                observation = agent.observe(environment, peer_states)
                evaluation = agent.evaluate(observation)
                decision = agent.decide(evaluation)

                action_results = []
                if decision:
                    action_results = agent.act(decision)
                    events_processed.extend(action_results)

                # Apply rule engine for behavioral modifications
                rule_context = RuleContext(
                    agent_id=str(agent.id),
                    tick=tick,
                    seed=agent_rng.seed,
                    environment=environment,
                    agent_state=agent.to_full_state(),
                    peer_states={
                        aid: s for aid, s in peer_states.items()
                        if aid in [str(p.id) for p in agent_pool.get_peers(agent)]
                    },
                    global_metrics=outcome_tracker.get_current_metrics(),
                )

                # Run rules for this agent
                rule_results = rule_engine.run_agent_tick(rule_context)

                # Apply rule-driven state updates
                state_updates = rule_results.get("state_updates", {})
                agent.update(action_results, state_updates)

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
        "tick_data": tick_data,
        "agent_snapshots": agent_snapshots,
        "final_agent_states": final_agent_states,
        "events_processed": events_processed,
        "metrics_by_tick": metrics_by_tick,
        "outcome_distribution": outcome_tracker.get_outcome_distribution(),
        "seed_used": rng.seed,
        "agent_count": len(agents),
    }


async def _load_agents_for_run(
    db: AsyncSession,
    run: dict,
    rng: DeterministicRNG,
) -> List[Agent]:
    """
    Load personas and compile them into agents for this run.
    """
    from sqlalchemy import text

    project_id = run.get("project_id")
    config = run.get("run_config", {})
    max_agents = config.get("max_agents", 100)

    # Load personas from database
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

    agents = []
    for row in persona_rows:
        # Create agent from persona using factory
        persona_dict = {
            "persona_id": str(row.id),
            "label": row.label,
            "demographics": row.demographics or {},
            "preferences": row.preferences or {},
            "perception_weights": row.perception_weights or {},
            "bias_parameters": row.bias_parameters or {},
            "action_priors": row.action_priors or {},
            "uncertainty_score": row.uncertainty_score or 0.5,
        }

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
