"""
Report Service - PHASE 7: Aggregated Report Endpoint

Aggregates prediction (distribution + target probability), reliability
(sensitivity, stability, drift), calibration, and provenance into a
single unified report response.

Key Principles:
- NEVER return HTTP 500 for missing data - return 200 with insufficient_data=true
- DETERMINISTIC: same inputs produce same outputs (seeded bootstrap)
- AUDITABLE: full provenance metadata included
- REUSES existing Phase 3-6 services

Reference: Phase 7 specification
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import numpy as np
from scipy import stats
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run_outcome import RunOutcome, OutcomeStatus
from app.models.calibration import CalibrationJob, CalibrationJobStatus
from app.schemas.report import (
    ReportResponse,
    ReportQueryParams,
    ReportOperator,
    TargetSpec,
    ReportFilters,
    ReportProvenance,
    DistributionData,
    PredictionResult,
    CalibrationCurve,
    CalibrationResult,
    SensitivityData,
    StabilityData,
    DriftData,
    DriftStatus,
    ReliabilityResult,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_MIN_RUNS = 3
DEFAULT_MAX_RUNS = 500
DEFAULT_WINDOW_DAYS = 30
DEFAULT_N_BINS = 20
DEFAULT_N_SENSITIVITY_GRID = 20
DEFAULT_N_BOOTSTRAP = 200


# =============================================================================
# Helper Functions (Reused from Phase 6)
# =============================================================================

def compute_deterministic_seed(
    tenant_id: str,
    node_id: str,
    metric_key: str,
    threshold: float,
    manifest_hash: Optional[str],
) -> str:
    """
    Compute deterministic seed from (tenant_id, node_id, metric_key, threshold, manifest_hash).
    Ensures reproducible bootstrap sampling.
    """
    seed_input = f"{tenant_id}:{node_id}:{metric_key}:{threshold}:{manifest_hash}"
    return hashlib.sha256(seed_input.encode()).hexdigest()[:16]


def _op_to_string(op: ReportOperator) -> str:
    """Convert ReportOperator enum to comparison string."""
    mapping = {
        ReportOperator.GE: "gte",
        ReportOperator.GT: "gt",
        ReportOperator.LE: "lte",
        ReportOperator.LT: "lt",
        ReportOperator.EQ: "eq",
    }
    return mapping.get(op, "gte")


def _compute_target_probability(
    values: List[float],
    op: ReportOperator,
    threshold: float,
) -> float:
    """Compute P(metric op threshold) from empirical data."""
    if not values:
        return 0.0

    arr = np.array(values)

    if op == ReportOperator.GE:
        return float(np.mean(arr >= threshold))
    elif op == ReportOperator.GT:
        return float(np.mean(arr > threshold))
    elif op == ReportOperator.LE:
        return float(np.mean(arr <= threshold))
    elif op == ReportOperator.LT:
        return float(np.mean(arr < threshold))
    elif op == ReportOperator.EQ:
        epsilon = 1e-9
        return float(np.mean(np.abs(arr - threshold) < epsilon))
    else:
        return float(np.mean(arr >= threshold))


def _compute_histogram(
    values: List[float],
    n_bins: int = DEFAULT_N_BINS,
) -> DistributionData:
    """Compute histogram data from values using numpy for deterministic binning."""
    if not values:
        return DistributionData(
            bins=[],
            counts=[],
            min=0.0,
            max=0.0,
        )

    arr = np.array(values)
    counts, bin_edges = np.histogram(arr, bins=n_bins)

    return DistributionData(
        bins=[float(x) for x in bin_edges],
        counts=[int(x) for x in counts],
        min=float(np.min(arr)),
        max=float(np.max(arr)),
    )


def _compute_sensitivity(
    values: List[float],
    op: ReportOperator,
    threshold: float,
    n_grid: int = DEFAULT_N_SENSITIVITY_GRID,
) -> SensitivityData:
    """
    Compute sensitivity: P(metric op threshold) across threshold grid.
    Grid is centered around the provided threshold.
    """
    if not values:
        return SensitivityData(thresholds=[], probabilities=[])

    arr = np.array(values)
    min_val, max_val = float(np.min(arr)), float(np.max(arr))

    # Generate grid centered around threshold with reasonable margin
    margin = (max_val - min_val) * 0.2 if max_val > min_val else abs(threshold) * 0.2 + 0.1
    grid_min = min(min_val - margin, threshold - margin)
    grid_max = max(max_val + margin, threshold + margin)

    threshold_grid = np.linspace(grid_min, grid_max, n_grid).tolist()

    probabilities = []
    for t in threshold_grid:
        prob = _compute_target_probability(values, op, t)
        probabilities.append(prob)

    return SensitivityData(
        thresholds=threshold_grid,
        probabilities=probabilities,
    )


def _compute_stability(
    values: List[float],
    op: ReportOperator,
    threshold: float,
    seed_hash: str,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
) -> StabilityData:
    """
    Compute stability via bootstrap resampling of target probability.
    Uses deterministic seed for reproducibility.
    """
    if not values or len(values) < 2:
        return StabilityData(
            mean=0.0,
            ci_low=0.0,
            ci_high=0.0,
            bootstrap_samples=n_bootstrap,
        )

    arr = np.array(values)
    n = len(arr)

    # Convert seed_hash to integer seed
    seed_int = int(seed_hash, 16) % (2**32)
    rng = np.random.default_rng(seed_int)

    # Bootstrap resampling - compute P(metric op threshold) for each sample
    bootstrap_probs = []
    for _ in range(n_bootstrap):
        sample = rng.choice(arr, size=n, replace=True)
        prob = _compute_target_probability(sample.tolist(), op, threshold)
        bootstrap_probs.append(prob)

    bootstrap_arr = np.array(bootstrap_probs)

    return StabilityData(
        mean=float(np.mean(bootstrap_arr)),
        ci_low=float(np.percentile(bootstrap_arr, 2.5)),
        ci_high=float(np.percentile(bootstrap_arr, 97.5)),
        bootstrap_samples=n_bootstrap,
    )


def _compute_drift(
    baseline_values: List[float],
    recent_values: List[float],
    n_bins: int = 10,
) -> DriftData:
    """
    Compute drift using KS statistic and PSI.

    Args:
        baseline_values: Values from baseline period (older half)
        recent_values: Values from recent period (newer half)
    """
    if not baseline_values or not recent_values:
        return DriftData(
            status=DriftStatus.STABLE,
            ks=None,
            psi=None,
        )

    baseline_arr = np.array(baseline_values)
    recent_arr = np.array(recent_values)

    # KS test
    ks_stat, ks_pvalue = stats.ks_2samp(baseline_arr, recent_arr)

    # PSI calculation
    combined = np.concatenate([baseline_arr, recent_arr])
    bin_edges = np.percentile(combined, np.linspace(0, 100, n_bins + 1))
    bin_edges = np.unique(bin_edges)

    if len(bin_edges) < 2:
        psi = 0.0
    else:
        baseline_hist, _ = np.histogram(baseline_arr, bins=bin_edges, density=True)
        recent_hist, _ = np.histogram(recent_arr, bins=bin_edges, density=True)

        eps = 1e-10
        baseline_hist = baseline_hist + eps
        recent_hist = recent_hist + eps

        baseline_prop = baseline_hist / np.sum(baseline_hist)
        recent_prop = recent_hist / np.sum(recent_hist)

        psi = float(np.sum((recent_prop - baseline_prop) * np.log(recent_prop / baseline_prop)))

    # Determine drift status
    if psi > 0.25 or ks_pvalue < 0.01:
        drift_status = DriftStatus.DRIFTING
    elif psi > 0.10 or ks_pvalue < 0.05:
        drift_status = DriftStatus.WARNING
    else:
        drift_status = DriftStatus.STABLE

    return DriftData(
        status=drift_status,
        ks=float(ks_stat),
        psi=float(psi),
    )


# =============================================================================
# Report Service
# =============================================================================

class ReportService:
    """
    Service for computing aggregated report data.

    Merges Phase 3 (Probability Source) + Phase 6 (Reliability) + Phase 4 (Calibration)
    into a single comprehensive report response.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_report(
        self,
        tenant_id: UUID,
        node_id: UUID,
        params: ReportQueryParams,
    ) -> ReportResponse:
        """
        Compute full aggregated report for a node.

        NEVER raises HTTP 500 for missing data - always returns structured response
        with insufficient_data=true when data is insufficient.

        Args:
            tenant_id: Tenant ID for multi-tenant scoping
            node_id: Node ID to compute report for
            params: Query parameters (metric_key, op, threshold, etc.)

        Returns:
            ReportResponse with prediction, reliability, calibration, provenance
        """
        errors: List[str] = []

        # Compute deterministic seed
        seed_hash = compute_deterministic_seed(
            tenant_id=str(tenant_id),
            node_id=str(node_id),
            metric_key=params.metric_key,
            threshold=params.threshold,
            manifest_hash=params.manifest_hash,
        )

        # Fetch run outcomes
        values, run_ids, updated_at = await self._fetch_metric_values(
            tenant_id=tenant_id,
            node_id=node_id,
            metric_key=params.metric_key,
            manifest_hash=params.manifest_hash,
            window_days=params.window_days,
        )

        n_runs = len(values)
        insufficient_data = n_runs < params.min_runs

        if insufficient_data:
            errors.append(
                f"Insufficient data: {n_runs} runs found, minimum {params.min_runs} required"
            )

        # Build provenance (always present)
        provenance = ReportProvenance(
            manifest_hash=params.manifest_hash,
            filters=ReportFilters(
                manifest_hash=params.manifest_hash,
                window_days=params.window_days,
                min_runs=params.min_runs,
            ),
            n_runs=n_runs,
            updated_at=updated_at or datetime.utcnow(),
        )

        # Build target spec
        target = TargetSpec(op=params.op, threshold=params.threshold)

        # Compute prediction (distribution + target probability)
        if insufficient_data:
            prediction = PredictionResult(
                distribution=DistributionData(bins=[], counts=[], min=0.0, max=0.0),
                target_probability=0.0,
            )
        else:
            distribution = _compute_histogram(values, n_bins=params.n_bins)
            target_prob = _compute_target_probability(values, params.op, params.threshold)
            prediction = PredictionResult(
                distribution=distribution,
                target_probability=target_prob,
            )

        # Compute reliability (sensitivity, stability, drift)
        if insufficient_data:
            reliability = ReliabilityResult(
                sensitivity=SensitivityData(thresholds=[], probabilities=[]),
                stability=StabilityData(mean=0.0, ci_low=0.0, ci_high=0.0, bootstrap_samples=params.n_bootstrap),
                drift=DriftData(status=DriftStatus.STABLE, ks=None, psi=None),
            )
        else:
            # Sensitivity analysis across threshold grid
            sensitivity = _compute_sensitivity(
                values=values,
                op=params.op,
                threshold=params.threshold,
                n_grid=params.n_sensitivity_grid,
            )

            # Stability via bootstrap
            stability = _compute_stability(
                values=values,
                op=params.op,
                threshold=params.threshold,
                seed_hash=seed_hash,
                n_bootstrap=params.n_bootstrap,
            )

            # Drift detection (split into baseline vs recent)
            mid_point = n_runs // 2
            # values are ordered desc by created_at, so:
            # values[:mid_point] = recent, values[mid_point:] = baseline
            recent_values = values[:mid_point]
            baseline_values = values[mid_point:]
            drift = _compute_drift(baseline_values, recent_values)

            reliability = ReliabilityResult(
                sensitivity=sensitivity,
                stability=stability,
                drift=drift,
            )

        # Fetch calibration summary from latest CalibrationJob
        calibration = await self._get_calibration_result(tenant_id, node_id)

        return ReportResponse(
            node_id=str(node_id),
            metric_key=params.metric_key,
            target=target,
            provenance=provenance,
            prediction=prediction,
            calibration=calibration,
            reliability=reliability,
            insufficient_data=insufficient_data,
            errors=errors,
        )

    async def _fetch_metric_values(
        self,
        tenant_id: UUID,
        node_id: UUID,
        metric_key: str,
        manifest_hash: Optional[str],
        window_days: int,
    ) -> Tuple[List[float], List[str], Optional[datetime]]:
        """
        Fetch metric values from run outcomes.

        Returns:
            Tuple of (values, run_ids, updated_at)
        """
        cutoff_date = datetime.utcnow() - timedelta(days=window_days)

        conditions = [
            RunOutcome.tenant_id == tenant_id,
            RunOutcome.node_id == node_id,
            RunOutcome.created_at >= cutoff_date,
            RunOutcome.status == OutcomeStatus.SUCCEEDED,
        ]

        if manifest_hash:
            conditions.append(RunOutcome.manifest_hash == manifest_hash)

        query = (
            select(RunOutcome)
            .where(and_(*conditions))
            .order_by(RunOutcome.created_at.desc())
            .limit(DEFAULT_MAX_RUNS)
        )

        result = await self.db.execute(query)
        outcomes = result.scalars().all()

        values: List[float] = []
        run_ids: List[str] = []
        updated_at: Optional[datetime] = None

        for outcome in outcomes:
            metrics = outcome.metrics_json or {}
            if metric_key in metrics:
                val = metrics[metric_key]
                if isinstance(val, (int, float)):
                    values.append(float(val))
                    run_ids.append(str(outcome.run_id))
                    if updated_at is None:
                        updated_at = outcome.created_at

        return values, run_ids, updated_at

    async def _get_calibration_result(
        self,
        tenant_id: UUID,
        node_id: UUID,
    ) -> CalibrationResult:
        """
        Fetch latest calibration metrics from CalibrationJob.

        Returns CalibrationResult with available=false if no calibration exists.
        """
        query = (
            select(CalibrationJob)
            .where(
                and_(
                    CalibrationJob.tenant_id == tenant_id,
                    CalibrationJob.node_id == node_id,
                    CalibrationJob.status == CalibrationJobStatus.SUCCEEDED.value,
                )
            )
            .order_by(CalibrationJob.finished_at.desc())
            .limit(1)
        )

        result = await self.db.execute(query)
        job = result.scalar_one_or_none()

        if not job:
            return CalibrationResult(
                available=False,
                latest_job_id=None,
                brier=None,
                ece=None,
                curve=None,
            )

        # Extract metrics from result_json
        metrics = job.result_json.get("metrics", {}) if job.result_json else {}

        # Extract calibration curve if available
        curve_data = job.result_json.get("curve", {}) if job.result_json else {}
        curve = None
        if curve_data and all(k in curve_data for k in ["p_pred", "p_true", "counts"]):
            curve = CalibrationCurve(
                p_pred=curve_data["p_pred"],
                p_true=curve_data["p_true"],
                counts=curve_data["counts"],
            )

        return CalibrationResult(
            available=True,
            latest_job_id=str(job.id),
            brier=metrics.get("brier_score"),
            ece=metrics.get("ece"),
            curve=curve,
        )


def get_report_service(db: AsyncSession) -> ReportService:
    """Factory function for ReportService."""
    return ReportService(db)
