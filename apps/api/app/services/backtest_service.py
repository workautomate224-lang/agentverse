"""
Phase 8: Backtest Service

Orchestrates end-to-end backtest execution with scoped-safe reset capability.

Key Principles:
- SCOPED-SAFE RESET: reset_backtest_data() only deletes BacktestRun and
  BacktestReportSnapshot records for a specific backtest_id. NEVER deletes
  global runs, telemetry, or data from other backtests.
- FORK-NOT-MUTATE (C1): Creates new runs, never modifies existing runs.
- DETERMINISTIC: Same seed produces reproducible results.
- AUDITABLE (C4): Full provenance with manifest_hash tracking.
- MULTI-TENANT (C6): All operations scoped by tenant_id.

Reference: Phase 8 specification
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import uuid

from sqlalchemy import select, and_, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backtest import (
    Backtest,
    BacktestRun,
    BacktestReportSnapshot,
    BacktestStatus,
    BacktestRunStatus,
)
from app.models.node import Node, Run, RunStatus
from app.models.project_spec import ProjectSpec
from app.schemas.backtest import (
    BacktestCreate,
    BacktestConfig,
    BacktestResponse,
    BacktestRunResponse,
    BacktestReportSnapshotResponse,
    BacktestResetResponse,
    BacktestStartResponse,
    BacktestRunsResponse,
    BacktestReportsResponse,
    BacktestStatusEnum,
    BacktestRunStatusEnum,
)
from app.services.report_service import get_report_service
from app.schemas.report import ReportQueryParams, ReportOperator


logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_RUNS_PER_NODE = 3
DEFAULT_MAX_TICKS = 100
DEFAULT_SEED = 42


# =============================================================================
# Helper Functions
# =============================================================================

def derive_seed(base_seed: int, node_id: str, run_index: int) -> int:
    """
    Derive deterministic seed for a specific run.

    Formula: hash(base_seed + node_id + run_index) → int32
    Ensures reproducibility across backtest re-runs.
    """
    combined = f"{base_seed}:{node_id}:{run_index}"
    hash_bytes = hashlib.sha256(combined.encode()).digest()
    return int.from_bytes(hash_bytes[:4], "big") % (2**31)


def _model_to_response(backtest: Backtest) -> BacktestResponse:
    """Convert Backtest model to response schema."""
    # Compute progress
    total = backtest.total_planned_runs or 0
    completed = (backtest.completed_runs or 0) + (backtest.failed_runs or 0)
    progress = (completed / total * 100) if total > 0 else 0.0

    return BacktestResponse(
        id=str(backtest.id),
        tenant_id=str(backtest.tenant_id),
        project_id=str(backtest.project_id),
        name=backtest.name,
        topic=backtest.topic,
        status=BacktestStatusEnum(backtest.status),
        seed=backtest.seed,
        config=backtest.config or {},
        notes=backtest.notes,
        total_planned_runs=backtest.total_planned_runs,
        completed_runs=backtest.completed_runs,
        failed_runs=backtest.failed_runs,
        created_at=backtest.created_at,
        started_at=backtest.started_at,
        finished_at=backtest.finished_at,
        updated_at=backtest.updated_at,
        progress_percent=round(progress, 1),
    )


def _run_to_response(run: BacktestRun) -> BacktestRunResponse:
    """Convert BacktestRun model to response schema."""
    return BacktestRunResponse(
        id=str(run.id),
        backtest_id=str(run.backtest_id),
        run_id=str(run.run_id) if run.run_id else None,
        node_id=str(run.node_id),
        run_index=run.run_index,
        derived_seed=run.derived_seed,
        status=BacktestRunStatusEnum(run.status),
        manifest_hash=run.manifest_hash,
        error=run.error,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _snapshot_to_response(snapshot: BacktestReportSnapshot) -> BacktestReportSnapshotResponse:
    """Convert BacktestReportSnapshot model to response schema."""
    return BacktestReportSnapshotResponse(
        id=str(snapshot.id),
        backtest_id=str(snapshot.backtest_id),
        node_id=str(snapshot.node_id),
        metric_key=snapshot.metric_key,
        op=snapshot.op,
        threshold=snapshot.threshold,
        params=snapshot.params or {},
        report_json=snapshot.report_json or {},
        created_at=snapshot.created_at,
    )


# =============================================================================
# Backtest Service
# =============================================================================

class BacktestService:
    """
    Service for backtest orchestration.

    SCOPED-SAFE: All reset operations only affect data belonging to the
    specific backtest, never global data.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Create Operations
    # =========================================================================

    async def create_backtest(
        self,
        tenant_id: UUID,
        project_id: UUID,
        payload: BacktestCreate,
    ) -> BacktestResponse:
        """
        Create a new backtest with planned runs.

        1. Create Backtest record
        2. Plan BacktestRun records for each node × runs_per_node
        3. Compute derived seeds for each run

        Args:
            tenant_id: Tenant UUID (C6 multi-tenant)
            project_id: Project UUID
            payload: Backtest creation parameters

        Returns:
            BacktestResponse with created backtest
        """
        # Verify project exists and belongs to tenant
        project = await self._get_project(tenant_id, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found for tenant")

        # Get nodes to test
        config = payload.config
        node_ids = await self._resolve_node_ids(tenant_id, project_id, config.node_ids)

        if not node_ids:
            raise ValueError("No nodes found to test")

        # Calculate total planned runs
        runs_per_node = config.runs_per_node or DEFAULT_RUNS_PER_NODE
        total_planned_runs = len(node_ids) * runs_per_node

        # Create backtest record
        backtest = Backtest(
            tenant_id=tenant_id,
            project_id=project_id,
            name=payload.name,
            topic=payload.topic,
            seed=payload.seed,
            config={
                "runs_per_node": runs_per_node,
                "node_ids": [str(nid) for nid in node_ids],
                "agent_config": config.agent_config.model_dump(),
                "scenario_config": config.scenario_config.model_dump(),
            },
            notes=payload.notes,
            status=BacktestStatus.CREATED.value,
            total_planned_runs=total_planned_runs,
            completed_runs=0,
            failed_runs=0,
        )
        self.db.add(backtest)
        await self.db.flush()

        # Create planned BacktestRun records
        run_index = 0
        for node_id in node_ids:
            for i in range(runs_per_node):
                derived = derive_seed(payload.seed, str(node_id), run_index)
                backtest_run = BacktestRun(
                    backtest_id=backtest.id,
                    node_id=node_id,
                    run_index=run_index,
                    derived_seed=derived,
                    status=BacktestRunStatus.PENDING.value,
                )
                self.db.add(backtest_run)
                run_index += 1

        await self.db.commit()
        await self.db.refresh(backtest)

        logger.info(
            f"Created backtest {backtest.id} with {total_planned_runs} planned runs "
            f"across {len(node_ids)} nodes"
        )

        return _model_to_response(backtest)

    # =========================================================================
    # Reset Operations (SCOPED-SAFE)
    # =========================================================================

    async def reset_backtest_data(
        self,
        tenant_id: UUID,
        project_id: UUID,
        backtest_id: UUID,
    ) -> BacktestResetResponse:
        """
        SCOPED-SAFE reset of backtest data.

        CRITICAL: This method ONLY deletes:
        - BacktestRun records belonging to this specific backtest_id
        - BacktestReportSnapshot records belonging to this specific backtest_id

        NEVER deletes:
        - Global Run records
        - Telemetry data
        - Other backtests' data
        - Project data
        - Node data

        Args:
            tenant_id: Tenant UUID for ownership verification
            project_id: Project UUID for ownership verification
            backtest_id: Backtest UUID to reset

        Returns:
            BacktestResetResponse documenting what was deleted
        """
        # Verify ownership
        backtest = await self._get_backtest(tenant_id, project_id, backtest_id)
        if not backtest:
            raise ValueError(f"Backtest {backtest_id} not found")

        # Count records before deletion
        runs_count = await self.db.scalar(
            select(func.count(BacktestRun.id))
            .where(BacktestRun.backtest_id == backtest_id)
        )

        snapshots_count = await self.db.scalar(
            select(func.count(BacktestReportSnapshot.id))
            .where(BacktestReportSnapshot.backtest_id == backtest_id)
        )

        # SCOPED-SAFE DELETE: Only delete backtest-specific records
        # Note: We do NOT delete the actual Run records - those are global

        # Delete BacktestRun records (not the linked Run records!)
        await self.db.execute(
            delete(BacktestRun)
            .where(BacktestRun.backtest_id == backtest_id)
        )

        # Delete BacktestReportSnapshot records
        await self.db.execute(
            delete(BacktestReportSnapshot)
            .where(BacktestReportSnapshot.backtest_id == backtest_id)
        )

        # Reset backtest counters (but keep the record)
        backtest.completed_runs = 0
        backtest.failed_runs = 0
        backtest.status = BacktestStatus.CREATED.value
        backtest.started_at = None
        backtest.finished_at = None
        backtest.updated_at = datetime.utcnow()

        # Re-create planned runs with fresh state
        config = backtest.config or {}
        node_ids = config.get("node_ids", [])
        runs_per_node = config.get("runs_per_node", DEFAULT_RUNS_PER_NODE)

        run_index = 0
        for node_id_str in node_ids:
            node_id = UUID(node_id_str)
            for i in range(runs_per_node):
                derived = derive_seed(backtest.seed, node_id_str, run_index)
                backtest_run = BacktestRun(
                    backtest_id=backtest.id,
                    node_id=node_id,
                    run_index=run_index,
                    derived_seed=derived,
                    status=BacktestRunStatus.PENDING.value,
                )
                self.db.add(backtest_run)
                run_index += 1

        await self.db.commit()

        logger.info(
            f"SCOPED-SAFE RESET: Backtest {backtest_id} - "
            f"deleted {runs_count} runs, {snapshots_count} snapshots"
        )

        return BacktestResetResponse(
            backtest_id=str(backtest_id),
            runs_deleted=runs_count or 0,
            snapshots_deleted=snapshots_count or 0,
            message=f"Reset complete. Deleted {runs_count} backtest runs and {snapshots_count} report snapshots. Global data preserved.",
        )

    # =========================================================================
    # Start/Execute Operations
    # =========================================================================

    async def start_backtest(
        self,
        tenant_id: UUID,
        project_id: UUID,
        backtest_id: UUID,
        sequential: bool = True,
    ) -> BacktestStartResponse:
        """
        Start backtest execution.

        Creates actual Run records for each pending BacktestRun and queues them
        for execution via Celery worker or runs them sequentially.

        Args:
            tenant_id: Tenant UUID
            project_id: Project UUID
            backtest_id: Backtest UUID
            sequential: If True, runs execute sequentially. If False, queue to workers.

        Returns:
            BacktestStartResponse with execution status
        """
        from app.services.simulation_orchestrator import get_simulation_orchestrator
        from app.tasks.base import JobContext, JobPriority

        backtest = await self._get_backtest(tenant_id, project_id, backtest_id)
        if not backtest:
            raise ValueError(f"Backtest {backtest_id} not found")

        if backtest.status not in [BacktestStatus.CREATED.value, BacktestStatus.FAILED.value]:
            raise ValueError(f"Backtest cannot be started from status: {backtest.status}")

        # Update status to RUNNING
        backtest.status = BacktestStatus.RUNNING.value
        backtest.started_at = datetime.utcnow()
        backtest.updated_at = datetime.utcnow()

        # Get pending backtest runs
        query = select(BacktestRun).where(
            and_(
                BacktestRun.backtest_id == backtest_id,
                BacktestRun.status == BacktestRunStatus.PENDING.value,
            )
        ).order_by(BacktestRun.run_index)
        result = await self.db.execute(query)
        pending_runs = result.scalars().all()

        runs_queued = 0

        for backtest_run in pending_runs:
            try:
                # Create actual Run record (FORK-NOT-MUTATE: new run, not modifying existing)
                run = await self._create_run_for_backtest(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    backtest=backtest,
                    backtest_run=backtest_run,
                )

                # Link BacktestRun to actual Run
                backtest_run.run_id = run.id
                backtest_run.status = BacktestRunStatus.RUNNING.value
                backtest_run.started_at = datetime.utcnow()

                runs_queued += 1

                # Queue or execute run
                if sequential:
                    # Execute synchronously (for testing/debugging)
                    await self._execute_run_sync(
                        tenant_id=tenant_id,
                        run_id=run.id,
                        backtest_run=backtest_run,
                    )
                else:
                    # Queue to Celery worker
                    await self._queue_run_async(
                        tenant_id=tenant_id,
                        run_id=run.id,
                        backtest_run_id=backtest_run.id,
                    )

            except Exception as e:
                logger.error(f"Failed to start backtest run {backtest_run.id}: {e}")
                backtest_run.status = BacktestRunStatus.FAILED.value
                backtest_run.error = str(e)
                backtest_run.finished_at = datetime.utcnow()
                backtest.failed_runs += 1

        await self.db.commit()

        # Check if backtest is complete
        await self._check_backtest_completion(backtest)

        return BacktestStartResponse(
            backtest_id=str(backtest_id),
            status=BacktestStatusEnum(backtest.status),
            runs_queued=runs_queued,
            message=f"Started {runs_queued} runs {'sequentially' if sequential else 'via worker queue'}",
        )

    async def _create_run_for_backtest(
        self,
        tenant_id: UUID,
        project_id: UUID,
        backtest: Backtest,
        backtest_run: BacktestRun,
    ) -> Run:
        """Create an actual Run record for a BacktestRun."""
        from app.models.run_config import RunConfig

        config = backtest.config or {}
        scenario_config = config.get("scenario_config", {})
        agent_config = config.get("agent_config", {})

        # Create RunConfig
        run_config = RunConfig(
            tenant_id=tenant_id,
            project_id=project_id,
            name=f"Backtest Run {backtest_run.run_index}",
            seed_config={
                "strategy": "single",
                "primary_seed": backtest_run.derived_seed,
            },
            horizon=scenario_config.get("max_ticks", DEFAULT_MAX_TICKS),
            tick_rate=scenario_config.get("tick_rate", 1),
            scenario_patch=scenario_config.get("scenario_patch"),
            max_agents=agent_config.get("max_agents", 100),
        )
        self.db.add(run_config)
        await self.db.flush()

        # Create Run
        run = Run(
            tenant_id=tenant_id,
            project_id=project_id,
            node_id=backtest_run.node_id,
            run_config_ref=run_config.id,
            actual_seed=backtest_run.derived_seed,
            status=RunStatus.CREATED.value,
            timing={"created_at": datetime.utcnow().isoformat()},
        )
        self.db.add(run)
        await self.db.flush()

        return run

    async def _execute_run_sync(
        self,
        tenant_id: UUID,
        run_id: UUID,
        backtest_run: BacktestRun,
    ):
        """Execute a run synchronously (for sequential mode)."""
        from app.tasks.run_executor import _execute_run
        from app.tasks.base import JobContext, JobPriority

        context = JobContext(
            tenant_id=str(tenant_id),
            user_id="system",
            job_id=str(uuid.uuid4()),
            priority=JobPriority.NORMAL,
        )

        try:
            # Note: _execute_run is async and handles its own DB session
            result = await _execute_run(str(run_id), context)

            if result.get("status") == "completed":
                backtest_run.status = BacktestRunStatus.SUCCEEDED.value
                # Try to get manifest_hash from run result
                run_result = result.get("result", {})
                backtest_run.manifest_hash = run_result.get("manifest_hash")
            else:
                backtest_run.status = BacktestRunStatus.FAILED.value
                backtest_run.error = result.get("error", "Unknown error")

        except Exception as e:
            backtest_run.status = BacktestRunStatus.FAILED.value
            backtest_run.error = str(e)

        backtest_run.finished_at = datetime.utcnow()

    async def _queue_run_async(
        self,
        tenant_id: UUID,
        run_id: UUID,
        backtest_run_id: UUID,
    ):
        """Queue a run to Celery worker."""
        from app.tasks.run_executor import execute_run
        from app.tasks.base import JobContext, JobPriority

        context = JobContext(
            tenant_id=str(tenant_id),
            user_id="system",
            job_id=str(uuid.uuid4()),
            priority=JobPriority.NORMAL,
            metadata={"backtest_run_id": str(backtest_run_id)},
        )

        execute_run.apply_async(
            args=[str(run_id), context.to_dict()],
            priority=JobPriority.NORMAL.value,
        )

    async def _check_backtest_completion(self, backtest: Backtest):
        """Check if backtest is complete and update status."""
        # Count completed/failed runs
        completed = await self.db.scalar(
            select(func.count(BacktestRun.id))
            .where(
                and_(
                    BacktestRun.backtest_id == backtest.id,
                    BacktestRun.status == BacktestRunStatus.SUCCEEDED.value,
                )
            )
        ) or 0

        failed = await self.db.scalar(
            select(func.count(BacktestRun.id))
            .where(
                and_(
                    BacktestRun.backtest_id == backtest.id,
                    BacktestRun.status == BacktestRunStatus.FAILED.value,
                )
            )
        ) or 0

        pending = await self.db.scalar(
            select(func.count(BacktestRun.id))
            .where(
                and_(
                    BacktestRun.backtest_id == backtest.id,
                    BacktestRun.status.in_([
                        BacktestRunStatus.PENDING.value,
                        BacktestRunStatus.RUNNING.value,
                    ]),
                )
            )
        ) or 0

        backtest.completed_runs = completed
        backtest.failed_runs = failed

        if pending == 0:
            # All runs finished
            if failed > 0 and completed == 0:
                backtest.status = BacktestStatus.FAILED.value
            else:
                backtest.status = BacktestStatus.SUCCEEDED.value
            backtest.finished_at = datetime.utcnow()

        backtest.updated_at = datetime.utcnow()
        await self.db.commit()

    # =========================================================================
    # Report Snapshot Operations
    # =========================================================================

    async def snapshot_reports(
        self,
        tenant_id: UUID,
        project_id: UUID,
        backtest_id: UUID,
        metric_key: str,
        op: str,
        threshold: float,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[BacktestReportSnapshotResponse]:
        """
        Generate and cache Phase 7 report snapshots for all nodes in backtest.

        Calls the Phase 7 report service internally and caches results.

        Args:
            tenant_id: Tenant UUID
            project_id: Project UUID
            backtest_id: Backtest UUID
            metric_key: Metric to analyze
            op: Comparison operator (ge, gt, le, lt, eq)
            threshold: Threshold value
            params: Optional additional params (window_days, min_runs, etc.)

        Returns:
            List of created report snapshots
        """
        backtest = await self._get_backtest(tenant_id, project_id, backtest_id)
        if not backtest:
            raise ValueError(f"Backtest {backtest_id} not found")

        config = backtest.config or {}
        node_ids = [UUID(nid) for nid in config.get("node_ids", [])]

        report_service = get_report_service(self.db)
        snapshots = []

        for node_id in node_ids:
            try:
                # Build query params
                query_params = ReportQueryParams(
                    metric_key=metric_key,
                    op=ReportOperator(op),
                    threshold=threshold,
                    window_days=params.get("window_days", 30) if params else 30,
                    min_runs=params.get("min_runs", 3) if params else 3,
                    n_bootstrap=params.get("n_bootstrap", 200) if params else 200,
                    n_bins=params.get("n_bins", 20) if params else 20,
                )

                # Generate report
                report = await report_service.compute_report(
                    tenant_id=tenant_id,
                    node_id=node_id,
                    params=query_params,
                )

                # Create snapshot
                snapshot = BacktestReportSnapshot(
                    backtest_id=backtest_id,
                    node_id=node_id,
                    metric_key=metric_key,
                    op=op,
                    threshold=threshold,
                    params=params or {},
                    report_json=report.model_dump(),
                )
                self.db.add(snapshot)
                await self.db.flush()

                snapshots.append(_snapshot_to_response(snapshot))

            except Exception as e:
                logger.error(f"Failed to snapshot report for node {node_id}: {e}")

        await self.db.commit()
        return snapshots

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def get_backtest(
        self,
        tenant_id: UUID,
        project_id: UUID,
        backtest_id: UUID,
    ) -> Optional[BacktestResponse]:
        """Get backtest by ID."""
        backtest = await self._get_backtest(tenant_id, project_id, backtest_id)
        return _model_to_response(backtest) if backtest else None

    async def list_backtests(
        self,
        tenant_id: UUID,
        project_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[BacktestResponse], int]:
        """List backtests for a project."""
        offset = (page - 1) * page_size

        # Count total
        total = await self.db.scalar(
            select(func.count(Backtest.id))
            .where(
                and_(
                    Backtest.tenant_id == tenant_id,
                    Backtest.project_id == project_id,
                )
            )
        ) or 0

        # Query backtests
        query = (
            select(Backtest)
            .where(
                and_(
                    Backtest.tenant_id == tenant_id,
                    Backtest.project_id == project_id,
                )
            )
            .order_by(Backtest.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        backtests = result.scalars().all()

        return [_model_to_response(b) for b in backtests], total

    async def get_backtest_runs(
        self,
        tenant_id: UUID,
        project_id: UUID,
        backtest_id: UUID,
    ) -> BacktestRunsResponse:
        """Get all runs for a backtest."""
        backtest = await self._get_backtest(tenant_id, project_id, backtest_id)
        if not backtest:
            raise ValueError(f"Backtest {backtest_id} not found")

        query = (
            select(BacktestRun)
            .where(BacktestRun.backtest_id == backtest_id)
            .order_by(BacktestRun.run_index)
        )
        result = await self.db.execute(query)
        runs = result.scalars().all()

        # Count by status
        by_status: Dict[str, int] = {}
        for run in runs:
            status = run.status
            by_status[status] = by_status.get(status, 0) + 1

        return BacktestRunsResponse(
            backtest_id=str(backtest_id),
            items=[_run_to_response(r) for r in runs],
            total=len(runs),
            by_status=by_status,
        )

    async def get_backtest_reports(
        self,
        tenant_id: UUID,
        project_id: UUID,
        backtest_id: UUID,
    ) -> BacktestReportsResponse:
        """Get all report snapshots for a backtest."""
        backtest = await self._get_backtest(tenant_id, project_id, backtest_id)
        if not backtest:
            raise ValueError(f"Backtest {backtest_id} not found")

        query = (
            select(BacktestReportSnapshot)
            .where(BacktestReportSnapshot.backtest_id == backtest_id)
            .order_by(BacktestReportSnapshot.created_at.desc())
        )
        result = await self.db.execute(query)
        snapshots = result.scalars().all()

        return BacktestReportsResponse(
            backtest_id=str(backtest_id),
            items=[_snapshot_to_response(s) for s in snapshots],
            total=len(snapshots),
        )

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    async def _get_project(
        self,
        tenant_id: UUID,
        project_id: UUID,
    ) -> Optional[ProjectSpec]:
        """Get project with tenant verification."""
        query = select(ProjectSpec).where(
            and_(
                ProjectSpec.id == project_id,
                ProjectSpec.tenant_id == tenant_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_backtest(
        self,
        tenant_id: UUID,
        project_id: UUID,
        backtest_id: UUID,
    ) -> Optional[Backtest]:
        """Get backtest with tenant/project verification."""
        query = select(Backtest).where(
            and_(
                Backtest.id == backtest_id,
                Backtest.tenant_id == tenant_id,
                Backtest.project_id == project_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _resolve_node_ids(
        self,
        tenant_id: UUID,
        project_id: UUID,
        specified_ids: List[str],
    ) -> List[UUID]:
        """Resolve node IDs - use specified or get all for project."""
        if specified_ids:
            return [UUID(nid) for nid in specified_ids]

        # Get all nodes for project
        query = select(Node.id).where(
            and_(
                Node.tenant_id == tenant_id,
                Node.project_id == project_id,
            )
        )
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall()]


# =============================================================================
# Factory Function
# =============================================================================

def get_backtest_service(db: AsyncSession) -> BacktestService:
    """Factory function for BacktestService."""
    return BacktestService(db)
