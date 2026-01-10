"""
Simulation Orchestrator
Reference: project.md §5-6, Phase 1

High-level orchestrator that integrates all Phase 1 components:
- Rule Engine (P1-001)
- Agent State Machine (P1-002)
- Node/Universe Map Service (P1-003)
- Run Executor (P1-004)
- Telemetry Writer (P1-005)

This is the primary entry point for running simulations.
Enforces all constraints (C0-C6) and coordinates the simulation lifecycle.

Key Responsibilities:
1. Create/manage simulation runs
2. Coordinate node creation and forking
3. Handle run lifecycle (start, monitor, cancel)
4. Query results and telemetry
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.node import Node, Edge, Run, RunStatus, NodeCluster, TriggeredBy, InterventionType
from app.services.node_service import (
    NodeService,
    get_node_service,
    CreateNodeInput,
    ForkNodeInput,
    AggregatedOutcome,
    NodeConfidence,
    EdgeIntervention,
    EdgeExplanation,
)
from app.services.telemetry import (
    TelemetryService,
    get_telemetry_service,
    TelemetryBlob,
    TelemetryQueryParams,
    TelemetrySlice,
)
from app.services.storage import StorageRef
from app.tasks.base import JobContext, JobPriority, create_job_context


class SimulationMode(str, Enum):
    """Simulation modes per project.md."""
    SOCIETY = "society"  # Many agents interacting → emergent outcomes
    TARGET = "target"    # Work backward from desired goal
    ASK = "ask"          # Natural language query → forecasts


@dataclass
class RunConfigInput:
    """Input for creating a run configuration."""
    # Fields from runs.py endpoint
    run_mode: str = "society"  # society | individual
    max_ticks: int = 100
    agent_batch_size: int = 100
    society_mode: Optional[Dict[str, Any]] = None
    engine_version: str = "1.0.0"
    ruleset_version: str = "1.0.0"
    dataset_version: str = "1.0.0"
    # Additional internal fields
    horizon: int = 1000
    tick_rate: int = 1
    seed_strategy: str = "single"
    primary_seed: Optional[int] = None
    seed_count: int = 1
    keyframe_interval: int = 100
    scenario_patch: Optional[Dict[str, Any]] = None
    max_agents: Optional[int] = None
    max_execution_time_ms: int = 300000  # 5 minutes default


@dataclass
class CreateRunInput:
    """Input for creating a simulation run."""
    project_id: str
    tenant_id: str
    node_id: Optional[str] = None  # If None, creates root node
    config: Optional[RunConfigInput] = None
    parent_node_id: Optional[str] = None  # For forking
    scenario_patch: Optional[Dict[str, Any]] = None  # For forking
    # Fields from runs.py endpoint
    label: Optional[str] = None
    seeds: Optional[List[int]] = None
    user_id: Optional[str] = None
    triggered_by: Optional[TriggeredBy] = None


@dataclass
class SimulationResult:
    """Result of a completed simulation."""
    run_id: str
    node_id: str
    status: str
    outcome: Optional[Dict[str, Any]]
    telemetry_ref: Optional[Dict[str, Any]]
    reliability: Optional[Dict[str, Any]]
    duration_ms: Optional[int]
    ticks_executed: Optional[int]


@dataclass
class SimulationProgress:
    """Progress of a running simulation."""
    run_id: str
    status: str
    started_at: Optional[str]
    ticks_executed: Optional[int]
    estimated_completion: Optional[str]
    current_metrics: Optional[Dict[str, Any]]


class SimulationOrchestrator:
    """
    Orchestrates simulation lifecycle.

    This is the main integration point for Phase 1.
    Coordinates between RunExecutor, NodeService, and TelemetryService.

    Reference: project.md §5-6
    """

    def __init__(
        self,
        db: AsyncSession,
        node_service: Optional[NodeService] = None,
        telemetry_service: Optional[TelemetryService] = None,
    ):
        self.db = db
        self.node_service = node_service or get_node_service(db)
        self.telemetry_service = telemetry_service or get_telemetry_service()

    # ================================================================
    # RUN LIFECYCLE
    # ================================================================

    async def create_run(
        self,
        input: CreateRunInput,
        priority: JobPriority = JobPriority.NORMAL,
    ) -> Tuple[Run, Node]:
        """
        Create a new simulation run.

        If node_id is not provided, creates a root node.
        If parent_node_id is provided, forks from that node.

        Returns the Run and associated Node.
        """
        config = input.config or RunConfigInput()

        # Determine or create node
        if input.node_id:
            # Use existing node
            node = await self.node_service.get_node(uuid.UUID(input.node_id))
            if not node:
                raise ValueError(f"Node not found: {input.node_id}")
        elif input.parent_node_id:
            # Fork from parent node (C1: fork-not-mutate)
            from app.services.node_service import EdgeIntervention, InterventionType
            fork_input = ForkNodeInput(
                parent_node_id=uuid.UUID(input.parent_node_id),
                project_id=uuid.UUID(input.project_id),
                tenant_id=uuid.UUID(input.tenant_id),
                intervention=EdgeIntervention(
                    intervention_type=InterventionType.VARIABLE_DELTA,
                    variable_deltas=input.scenario_patch,
                ),
                label=input.label,
            )
            # STEP 4: fork_node now returns (Node, Edge, NodePatch)
            node, edge, node_patch = await self.node_service.fork_node(fork_input)

            # STEP 4: Generate child scenario from parent state + node_patch
            parent_node = await self.node_service.get_node(uuid.UUID(input.parent_node_id))
            if parent_node and parent_node.aggregated_outcome:
                # Get parent's environment state (from last run outcome or scenario)
                parent_env = parent_node.aggregated_outcome.get("environment_state", {})
                if not parent_env and parent_node.scenario_patch_ref:
                    parent_env = parent_node.scenario_patch_ref

                # Apply NodePatch to generate child environment
                if parent_env and node_patch:
                    config.scenario_patch = node_patch.apply_to_environment(parent_env)
                    config.scenario_patch["_derived_from_parent"] = str(parent_node.id)
                    config.scenario_patch["_patch_id"] = str(node_patch.id)
        else:
            # Create root node
            node_input = CreateNodeInput(
                project_id=uuid.UUID(input.project_id),
                tenant_id=uuid.UUID(input.tenant_id),
                is_baseline=True,
                label="Baseline",
            )
            node = await self.node_service.create_root_node(node_input)

        # Generate seed
        if config.primary_seed is None:
            import random
            config.primary_seed = random.randint(0, 2**31 - 1)

        # Create RunConfig record
        run_config_id = uuid.uuid4()
        from sqlalchemy import text
        await self.db.execute(
            text("""
                INSERT INTO run_configs (
                    id, project_id, tenant_id, versions, seed_config,
                    horizon, tick_rate, scheduler_profile, logging_profile,
                    scenario_patch, max_execution_time_ms, max_agents,
                    created_at, updated_at
                ) VALUES (
                    :id, :project_id, :tenant_id, :versions, :seed_config,
                    :horizon, :tick_rate, :scheduler_profile, :logging_profile,
                    :scenario_patch, :max_execution_time_ms, :max_agents,
                    :created_at, :updated_at
                )
            """),
            {
                "id": run_config_id,
                "project_id": uuid.UUID(input.project_id),
                "tenant_id": uuid.UUID(input.tenant_id),
                "versions": json.dumps({"engine": "1.0.0", "ruleset": "1.0.0"}),
                "seed_config": json.dumps({
                    "strategy": config.seed_strategy,
                    "primary_seed": config.primary_seed,
                    "count": config.seed_count,
                }),
                "horizon": config.horizon,
                "tick_rate": config.tick_rate,
                "scheduler_profile": json.dumps({}),
                "logging_profile": json.dumps({"keyframe_interval": config.keyframe_interval}),
                "scenario_patch": json.dumps(config.scenario_patch) if config.scenario_patch else None,
                "max_execution_time_ms": config.max_execution_time_ms,
                "max_agents": config.max_agents,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

        # Create Run record (STEP 1: Start with CREATED status)
        run = Run(
            id=uuid.uuid4(),
            project_id=uuid.UUID(input.project_id),
            tenant_id=uuid.UUID(input.tenant_id),
            node_id=node.id,
            run_config_ref=run_config_id,
            triggered_by=input.triggered_by.value if input.triggered_by else "user",
            status=RunStatus.CREATED.value,  # STEP 1: Initial state is CREATED
            actual_seed=config.primary_seed,
            timing={"created_at": datetime.utcnow().isoformat()},
        )
        self.db.add(run)
        await self.db.flush()

        return run, node

    async def queue_run(
        self,
        run: Run,
        tenant_id: str,
    ) -> Run:
        """
        Transition a run from CREATED to QUEUED status.

        STEP 1: Enforces proper state transition.
        """
        if run.status != RunStatus.CREATED.value:
            raise ValueError(
                f"STEP 1 VIOLATION: Cannot queue run with status {run.status}. "
                f"Expected status: {RunStatus.CREATED.value}"
            )

        # Update run status to QUEUED
        stmt = (
            update(Run)
            .where(Run.id == run.id)
            .values(
                status=RunStatus.QUEUED.value,
                timing={**run.timing, "queued_at": datetime.utcnow().isoformat()},
                updated_at=datetime.utcnow(),
            )
        )
        await self.db.execute(stmt)
        run.status = RunStatus.QUEUED.value
        return run

    async def start_run(
        self,
        run: Run,
        tenant_id: str,
        priority: JobPriority = JobPriority.NORMAL,
    ) -> str:
        """
        Start a simulation run by submitting to the job queue.

        STEP 1 State Transitions:
        - CREATED -> QUEUED (when submitted to queue)
        - QUEUED -> RUNNING (when worker picks it up, handled by executor)

        Returns the Celery task ID.
        """
        from app.tasks.run_executor import execute_run

        # STEP 1: Validate state transition
        if run.status not in (RunStatus.CREATED.value, RunStatus.QUEUED.value, "pending"):
            raise ValueError(
                f"STEP 1 VIOLATION: Cannot start run with status {run.status}. "
                f"Expected status: {RunStatus.CREATED.value} or {RunStatus.QUEUED.value}"
            )

        # Transition from CREATED to QUEUED
        if run.status == RunStatus.CREATED.value:
            await self.queue_run(run, tenant_id)

        # Create job context with a default user_id
        context = create_job_context(
            tenant_id=tenant_id,
            user_id=tenant_id,  # Use tenant_id as fallback for user_id
            priority=priority,
        )

        # Submit to queue
        try:
            task = execute_run.apply_async(
                args=[str(run.id), context.to_dict()],
                priority=priority.value,
            )
            return task.id
        except Exception as e:
            import logging
            logging.error(f"Failed to submit task: {e}, type(execute_run)={type(execute_run)}, priority={priority}, priority.value={priority.value}")
            raise

    async def create_and_start_run(
        self,
        input: CreateRunInput,
        priority: JobPriority = JobPriority.NORMAL,
    ) -> Tuple[Run, Node, str]:
        """
        Create and immediately start a simulation run.

        Convenience method that combines create_run and start_run.
        Returns (Run, Node, task_id).
        """
        run, node = await self.create_run(input, priority)
        await self.db.commit()

        task_id = await self.start_run(run, input.tenant_id, priority)
        return run, node, task_id

    async def cancel_run(self, run_id: str, tenant_id: str) -> bool:
        """
        Cancel a running simulation.

        Returns True if cancellation was successful.
        """
        from app.tasks.run_executor import cancel_run
        from app.tasks.base import create_job_context

        context = create_job_context(tenant_id=tenant_id)
        cancel_run.apply_async(args=[run_id, context.to_dict()])
        return True

    async def get_run_progress(
        self,
        run_id: str,
        tenant_id: str,
    ) -> Optional[SimulationProgress]:
        """
        Get the progress of a running simulation.
        """
        query = select(Run).where(
            Run.id == uuid.UUID(run_id),
            Run.tenant_id == uuid.UUID(tenant_id),
        )
        result = await self.db.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            return None

        timing = run.timing or {}
        return SimulationProgress(
            run_id=run_id,
            status=run.status,
            started_at=timing.get("started_at"),
            ticks_executed=timing.get("ticks_executed"),
            estimated_completion=None,  # Could compute from tick rate
            current_metrics=None,
        )

    async def get_run_result(
        self,
        run_id: str,
        tenant_id: str,
    ) -> Optional[SimulationResult]:
        """
        Get the result of a completed simulation.
        """
        query = select(Run).where(
            Run.id == uuid.UUID(run_id),
            Run.tenant_id == uuid.UUID(tenant_id),
        )
        result = await self.db.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            return None

        outputs = run.outputs or {}
        timing = run.timing or {}

        return SimulationResult(
            run_id=run_id,
            node_id=str(run.node_id),
            status=run.status,
            outcome=outputs.get("outcomes"),
            telemetry_ref=outputs.get("telemetry_ref"),
            reliability=outputs.get("reliability"),
            duration_ms=timing.get("duration_ms"),
            ticks_executed=timing.get("ticks_executed"),
        )

    # ================================================================
    # NODE OPERATIONS (Delegates to NodeService)
    # ================================================================

    async def create_root_node(
        self,
        project_id: str,
        tenant_id: str,
        scenario_patch: Optional[Dict[str, Any]] = None,
    ) -> Node:
        """Create a root node for a project."""
        input = CreateNodeInput(
            project_id=uuid.UUID(project_id),
            tenant_id=uuid.UUID(tenant_id),
            scenario_patch=scenario_patch,
        )
        return await self.node_service.create_root_node(input)

    async def fork_node(
        self,
        parent_node_id: str,
        tenant_id: str,
        scenario_patch: Optional[Dict[str, Any]] = None,
        intervention: Optional[Dict[str, Any]] = None,
        explanation: Optional[str] = None,
    ) -> Tuple[Node, Edge]:
        """
        Fork a node to create a new branch.

        Enforces C1: Fork-not-mutate.
        """
        # Get parent node to retrieve project_id
        parent_node = await self.node_service.get_node(
            uuid.UUID(parent_node_id),
            uuid.UUID(tenant_id),
        )
        if not parent_node:
            raise ValueError(f"Parent node {parent_node_id} not found")

        # Build EdgeIntervention from dict
        intervention_data = intervention or scenario_patch or {}
        intervention_type_str = intervention_data.get("intervention_type", "variable_delta")
        try:
            intervention_type = InterventionType(intervention_type_str)
        except ValueError:
            # Default to VARIABLE_DELTA for manual interventions
            intervention_type = InterventionType.VARIABLE_DELTA

        edge_intervention = EdgeIntervention(
            intervention_type=intervention_type,
            variable_deltas=intervention_data.get("variable_deltas") or intervention_data.get("environment_overrides"),
            nl_query=intervention_data.get("nl_query") or intervention_data.get("nl_description"),
        )

        # Build EdgeExplanation from string
        edge_explanation = None
        if explanation:
            edge_explanation = EdgeExplanation(
                short_label=explanation[:50] if len(explanation) > 50 else explanation,
                explanation_text=explanation,
            )

        input = ForkNodeInput(
            parent_node_id=uuid.UUID(parent_node_id),
            project_id=parent_node.project_id,
            tenant_id=uuid.UUID(tenant_id),
            intervention=edge_intervention,
            explanation=edge_explanation,
            label=explanation,
        )
        return await self.node_service.fork_node(input)

    async def get_node_with_runs(
        self,
        node_id: str,
        tenant_id: str,
    ) -> Optional[Tuple[Node, List[Run]]]:
        """Get a node with all its runs."""
        node = await self.node_service.get_node(
            uuid.UUID(node_id),
            include_runs=True,
        )
        if not node or str(node.tenant_id) != tenant_id:
            return None

        # Get runs for this node
        query = select(Run).where(
            Run.node_id == uuid.UUID(node_id),
            Run.tenant_id == uuid.UUID(tenant_id),
        ).order_by(Run.created_at.desc())
        result = await self.db.execute(query)
        runs = list(result.scalars().all())

        return node, runs

    async def list_runs(
        self,
        tenant_id: uuid.UUID,
        project_id: Optional[str] = None,
        node_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Run]:
        """
        List runs with optional filtering.

        Args:
            tenant_id: Tenant ID for filtering
            project_id: Optional project ID filter
            node_id: Optional node ID filter
            status: Optional status filter
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of Run objects
        """
        query = select(Run).where(Run.tenant_id == tenant_id)

        if project_id:
            query = query.where(Run.project_id == uuid.UUID(project_id))
        if node_id:
            query = query.where(Run.node_id == uuid.UUID(node_id))
        if status:
            query = query.where(Run.status == status)

        query = query.order_by(Run.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_run(
        self,
        run_id: str,
        tenant_id: uuid.UUID,
    ) -> Optional[Run]:
        """
        Get a single run by ID.

        Args:
            run_id: Run UUID string
            tenant_id: Tenant ID for filtering

        Returns:
            Run object or None if not found
        """
        query = select(Run).where(
            Run.id == uuid.UUID(run_id),
            Run.tenant_id == tenant_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_universe_map(
        self,
        project_id: str,
        tenant_id: str,
        max_depth: Optional[int] = None,
        explored_only: bool = False,
    ):
        """
        Get the Universe Map for a project.

        Returns the full node graph with node and edge objects.
        """
        return await self.node_service.get_universe_map_data(
            project_id=uuid.UUID(project_id),
            tenant_id=uuid.UUID(tenant_id),
            max_depth=max_depth,
            explored_only=explored_only,
        )

    async def compare_nodes(
        self,
        node_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Compare outcomes across multiple nodes.

        Useful for analyzing different branches.
        """
        uuids = [uuid.UUID(nid) for nid in node_ids]
        return await self.node_service.compare_nodes(uuids)

    async def get_most_likely_paths(
        self,
        project_id: str,
        tenant_id: str,
        num_paths: int = 5,
    ):
        """Get the most likely outcome paths."""
        return await self.node_service.get_most_likely_paths(
            project_id=uuid.UUID(project_id),
            tenant_id=uuid.UUID(tenant_id),
            num_paths=num_paths,
        )

    # ================================================================
    # TELEMETRY OPERATIONS (READ-ONLY per C3)
    # ================================================================

    async def get_telemetry(
        self,
        run_id: str,
        tenant_id: str,
    ) -> Optional[TelemetryBlob]:
        """
        Get full telemetry for a run.

        READ-ONLY operation (C3 compliant).
        """
        result = await self.get_run_result(run_id, tenant_id)
        if not result or not result.telemetry_ref:
            return None

        storage_ref = StorageRef.from_dict(result.telemetry_ref)
        return await self.telemetry_service.get_telemetry(storage_ref)

    async def query_telemetry(
        self,
        run_id: str,
        tenant_id: str,
        params: TelemetryQueryParams,
    ) -> Optional[TelemetrySlice]:
        """
        Query a slice of telemetry.

        READ-ONLY operation (C3 compliant).
        Supports filtering by tick range, region, segment, event type.
        """
        result = await self.get_run_result(run_id, tenant_id)
        if not result or not result.telemetry_ref:
            return None

        storage_ref = StorageRef.from_dict(result.telemetry_ref)
        return await self.telemetry_service.query_telemetry(storage_ref, params)

    async def get_telemetry_download_url(
        self,
        run_id: str,
        tenant_id: str,
        expires_in: int = 3600,
    ) -> Optional[str]:
        """
        Get a signed download URL for telemetry.

        Reference: project.md §8.4 (short-lived signed URLs).
        """
        result = await self.get_run_result(run_id, tenant_id)
        if not result or not result.telemetry_ref:
            return None

        storage_ref = StorageRef.from_dict(result.telemetry_ref)
        return await self.telemetry_service.get_signed_download_url(
            storage_ref, expires_in
        )

    # ================================================================
    # BATCH OPERATIONS
    # ================================================================

    async def run_multi_seed(
        self,
        project_id: str,
        tenant_id: str,
        node_id: Optional[str] = None,
        seed_count: int = 5,
        config: Optional[RunConfigInput] = None,
    ) -> List[Tuple[Run, str]]:
        """
        Run multiple simulations with different seeds.

        Reference: project.md §6.5 (multi strategy).
        Returns list of (Run, task_id) tuples.
        """
        import random

        base_config = config or RunConfigInput()
        results = []

        # Generate seeds
        base_seed = base_config.primary_seed or random.randint(0, 2**31 - 1)

        for i in range(seed_count):
            seed = base_seed + i
            run_config = RunConfigInput(
                horizon=base_config.horizon,
                tick_rate=base_config.tick_rate,
                seed_strategy="single",
                primary_seed=seed,
                keyframe_interval=base_config.keyframe_interval,
                scenario_patch=base_config.scenario_patch,
                max_agents=base_config.max_agents,
                max_execution_time_ms=base_config.max_execution_time_ms,
            )

            input = CreateRunInput(
                project_id=project_id,
                tenant_id=tenant_id,
                triggered_by=TriggeredBy.BATCH,
                node_id=node_id,
                config=run_config,
            )

            run, node, task_id = await self.create_and_start_run(input)
            results.append((run, task_id))

        return results

    async def aggregate_multi_seed_results(
        self,
        run_ids: List[str],
        tenant_id: str,
    ) -> Dict[str, Any]:
        """
        Aggregate outcomes across multiple seed runs.

        Useful for computing confidence intervals and variance.
        """
        outcomes = []
        for run_id in run_ids:
            result = await self.get_run_result(run_id, tenant_id)
            if result and result.outcome:
                outcomes.append(result.outcome)

        if not outcomes:
            return {"error": "No completed runs found"}

        # Compute aggregate statistics
        distributions = [o.get("outcome_distribution", {}) for o in outcomes]
        all_keys = set()
        for d in distributions:
            all_keys.update(d.keys())

        aggregated = {}
        for key in all_keys:
            values = [d.get(key, 0) for d in distributions]
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            aggregated[key] = {
                "mean": mean,
                "variance": variance,
                "min": min(values),
                "max": max(values),
                "samples": len(values),
            }

        return {
            "run_count": len(outcomes),
            "outcome_statistics": aggregated,
            "confidence": 1 - (sum(a["variance"] for a in aggregated.values()) / len(aggregated)) if aggregated else 0,
        }

    # ================================================================
    # STEP 4: Universe Map Operations
    # ================================================================

    async def queue_node_refresh(
        self,
        node_id: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """
        STEP 4: Queue a stale node for re-simulation.

        Creates a new run for the node and optionally starts it.
        Clears the staleness flag after queuing.
        """
        node_uuid = uuid.UUID(node_id)
        tenant_uuid = uuid.UUID(tenant_id)

        # Get the node
        stmt = select(Node).where(
            Node.id == node_uuid,
            Node.tenant_id == tenant_uuid,
        )
        result = await self.db.execute(stmt)
        node = result.scalar_one_or_none()

        if not node:
            raise ValueError(f"Node {node_id} not found")

        if not node.is_stale:
            return {
                "status": "skipped",
                "reason": "Node is not stale",
                "node_id": node_id,
            }

        # Create a run for this node
        input = CreateRunInput(
            project_id=str(node.project_id),
            tenant_id=tenant_id,
            node_id=node_id,
            triggered_by=TriggeredBy.BATCH,
            label=f"Refresh run for stale node",
        )

        run, _, task_id = await self.create_and_start_run(input)

        # Clear staleness flag
        node.is_stale = False
        node.stale_reason = None
        await self.db.flush()

        return {
            "status": "queued",
            "node_id": node_id,
            "run_id": str(run.id),
            "task_id": task_id,
        }

    async def run_node_ensemble(
        self,
        node_id: str,
        tenant_id: str,
        seeds: List[int],
        auto_start: bool = True,
    ) -> Dict[str, Any]:
        """
        STEP 4: Run multiple simulations for ensemble aggregation.

        Creates multiple runs with different seeds for a node.
        Updates node's min_ensemble_size.
        """
        node_uuid = uuid.UUID(node_id)
        tenant_uuid = uuid.UUID(tenant_id)

        # Get the node
        stmt = select(Node).where(
            Node.id == node_uuid,
            Node.tenant_id == tenant_uuid,
        )
        result = await self.db.execute(stmt)
        node = result.scalar_one_or_none()

        if not node:
            raise ValueError(f"Node {node_id} not found")

        # Update ensemble size requirement
        node.min_ensemble_size = max(node.min_ensemble_size, len(seeds))
        await self.db.flush()

        # Create runs for each seed
        run_ids = []
        task_ids = []

        for seed in seeds:
            run_config = RunConfigInput(
                seed_strategy="single",
                primary_seed=seed,
            )

            input = CreateRunInput(
                project_id=str(node.project_id),
                tenant_id=tenant_id,
                node_id=node_id,
                config=run_config,
                triggered_by=TriggeredBy.BATCH,
                label=f"Ensemble run (seed={seed})",
                seeds=[seed],
            )

            if auto_start:
                run, _, task_id = await self.create_and_start_run(input)
                if task_id:
                    task_ids.append(task_id)
            else:
                run, _ = await self.create_run(input)

            run_ids.append(run.id)

        return {
            "node_id": node_id,
            "run_ids": run_ids,
            "task_ids": task_ids,
            "ensemble_size": len(seeds),
        }


# Factory function
def get_simulation_orchestrator(db: AsyncSession) -> SimulationOrchestrator:
    """Get a simulation orchestrator instance."""
    return SimulationOrchestrator(db)
