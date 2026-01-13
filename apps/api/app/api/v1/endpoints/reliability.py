"""
PHASE 6: Reliability Integration Endpoints

Integrates Sensitivity / Stability / Drift into the Reliability module.
Computes aggregate reliability metrics across multiple runs for a node.

Reference: Phase 6 specification
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from scipy import stats
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.tenant import TenantContext, get_tenant_context
from app.models.user import User
from app.models.run_outcome import RunOutcome
from app.models.calibration import CalibrationJob, CalibrationJobStatus

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# PHASE 6: Pydantic Response Schemas
# =============================================================================

class SensitivityResult(BaseModel):
    """Sensitivity analysis result - P(metric op threshold) across threshold grid."""
    threshold_grid: List[float] = Field(..., description="Array of threshold values")
    probabilities: List[float] = Field(..., description="P(metric op threshold) for each threshold")
    op: str = Field(..., description="Comparison operator used")
    metric_key: str = Field(..., description="Metric key analyzed")


class StabilityResult(BaseModel):
    """Stability analysis result from bootstrap resampling."""
    bootstrap_mean: float = Field(..., description="Mean of bootstrap estimates")
    bootstrap_std: float = Field(..., description="Std of bootstrap estimates")
    ci_95_lower: float = Field(..., description="95% CI lower bound")
    ci_95_upper: float = Field(..., description="95% CI upper bound")
    n_bootstrap: int = Field(default=200, description="Number of bootstrap samples")
    seed_hash: str = Field(..., description="Deterministic seed hash for reproducibility")


class DriftResult(BaseModel):
    """Drift detection result using KS statistic and PSI."""
    ks_statistic: float = Field(..., description="Kolmogorov-Smirnov statistic")
    ks_pvalue: float = Field(..., description="KS test p-value")
    psi: float = Field(..., description="Population Stability Index")
    drift_status: str = Field(..., description="stable | warning | drifting")
    baseline_n: int = Field(..., description="Number of baseline runs")
    recent_n: int = Field(..., description="Number of recent runs")
    baseline_histogram: Optional[List[float]] = Field(None, description="Baseline distribution histogram")
    recent_histogram: Optional[List[float]] = Field(None, description="Recent distribution histogram")
    histogram_bins: Optional[List[float]] = Field(None, description="Histogram bin edges")


class CalibrationSummary(BaseModel):
    """Calibration metrics summary from latest calibration job."""
    brier_score: Optional[float] = Field(None, description="Brier score (lower is better)")
    ece: Optional[float] = Field(None, description="Expected Calibration Error")
    method: Optional[str] = Field(None, description="Calibration method used")
    calibration_job_id: Optional[str] = Field(None, description="Reference to CalibrationJob")


class AuditMetadata(BaseModel):
    """Audit metadata for reproducibility."""
    computed_at: datetime = Field(..., description="Computation timestamp")
    run_ids_used: List[str] = Field(..., description="Run IDs included in computation")
    filters_applied: Dict[str, Any] = Field(..., description="Filters used")
    deterministic_seed: str = Field(..., description="Seed for reproducibility")


class ReliabilitySummaryResponse(BaseModel):
    """Response for GET /nodes/{node_id}/reliability/summary"""
    status: str = Field(..., description="ok | insufficient_data")
    n_runs_total: int = Field(..., description="Total runs found")
    n_runs_used: int = Field(..., description="Runs used after filtering")

    # Core metrics (null if insufficient_data)
    sensitivity: Optional[SensitivityResult] = None
    stability: Optional[StabilityResult] = None
    drift: Optional[DriftResult] = None
    calibration: Optional[CalibrationSummary] = None

    # Audit trail
    audit: AuditMetadata


class ReliabilityDetailResponse(BaseModel):
    """Response for GET /nodes/{node_id}/reliability/detail - richer curves."""
    status: str = Field(..., description="ok | insufficient_data")
    n_runs_total: int = Field(..., description="Total runs found")
    n_runs_used: int = Field(..., description="Runs used after filtering")

    # Core metrics
    sensitivity: Optional[SensitivityResult] = None
    stability: Optional[StabilityResult] = None
    drift: Optional[DriftResult] = None
    calibration: Optional[CalibrationSummary] = None

    # Extended detail
    raw_values: Optional[List[float]] = Field(None, description="Raw metric values for custom analysis")
    percentiles: Optional[Dict[str, float]] = Field(None, description="Percentile breakdown")
    bootstrap_samples: Optional[List[float]] = Field(None, description="Bootstrap sample estimates")

    # Audit trail
    audit: AuditMetadata


# =============================================================================
# PHASE 6: Computation Helpers
# =============================================================================

def compute_deterministic_seed(
    tenant_id: str,
    node_id: str,
    metric_key: str,
    threshold: Optional[float],
    manifest_hash: Optional[str],
) -> str:
    """
    Compute deterministic seed from (tenant_id, node_id, metric_key, threshold, manifest_hash).
    Returns a hash string that can be used as seed.
    """
    seed_input = f"{tenant_id}:{node_id}:{metric_key}:{threshold}:{manifest_hash}"
    return hashlib.sha256(seed_input.encode()).hexdigest()[:16]


def compute_sensitivity(
    values: List[float],
    op: str,
    threshold_grid: Optional[List[float]] = None,
    n_grid: int = 20,
) -> SensitivityResult:
    """
    Compute sensitivity: empirical P(metric op threshold) across threshold grid.

    Args:
        values: Raw metric values from runs
        op: Comparison operator (gte, lte, gt, lt, eq)
        threshold_grid: Optional explicit grid, else auto-generate
        n_grid: Number of grid points if auto-generating
    """
    if not values:
        return SensitivityResult(
            threshold_grid=[],
            probabilities=[],
            op=op,
            metric_key="",
        )

    arr = np.array(values)

    # Auto-generate threshold grid if not provided
    if threshold_grid is None:
        min_val, max_val = np.min(arr), np.max(arr)
        # Add small margin
        margin = (max_val - min_val) * 0.1 if max_val > min_val else 0.1
        threshold_grid = np.linspace(min_val - margin, max_val + margin, n_grid).tolist()

    # Compute P(metric op threshold) for each threshold
    probabilities = []
    for t in threshold_grid:
        if op == "gte":
            prob = np.mean(arr >= t)
        elif op == "gt":
            prob = np.mean(arr > t)
        elif op == "lte":
            prob = np.mean(arr <= t)
        elif op == "lt":
            prob = np.mean(arr < t)
        elif op == "eq":
            prob = np.mean(arr == t)
        else:
            prob = np.mean(arr >= t)  # Default to gte
        probabilities.append(float(prob))

    return SensitivityResult(
        threshold_grid=threshold_grid,
        probabilities=probabilities,
        op=op,
        metric_key="",  # Will be set by caller
    )


def compute_stability(
    values: List[float],
    seed_hash: str,
    n_bootstrap: int = 200,
) -> StabilityResult:
    """
    Compute stability via bootstrap resampling with deterministic seed.

    Args:
        values: Raw metric values from runs
        seed_hash: Deterministic seed hash
        n_bootstrap: Number of bootstrap samples
    """
    if not values or len(values) < 2:
        return StabilityResult(
            bootstrap_mean=0.0,
            bootstrap_std=0.0,
            ci_95_lower=0.0,
            ci_95_upper=0.0,
            n_bootstrap=n_bootstrap,
            seed_hash=seed_hash,
        )

    arr = np.array(values)
    n = len(arr)

    # Convert seed_hash to integer seed
    seed_int = int(seed_hash, 16) % (2**32)
    rng = np.random.default_rng(seed_int)

    # Bootstrap resampling
    bootstrap_estimates = []
    for _ in range(n_bootstrap):
        sample = rng.choice(arr, size=n, replace=True)
        bootstrap_estimates.append(np.mean(sample))

    bootstrap_arr = np.array(bootstrap_estimates)

    return StabilityResult(
        bootstrap_mean=float(np.mean(bootstrap_arr)),
        bootstrap_std=float(np.std(bootstrap_arr)),
        ci_95_lower=float(np.percentile(bootstrap_arr, 2.5)),
        ci_95_upper=float(np.percentile(bootstrap_arr, 97.5)),
        n_bootstrap=n_bootstrap,
        seed_hash=seed_hash,
    )


def compute_drift(
    baseline_values: List[float],
    recent_values: List[float],
    n_bins: int = 10,
) -> DriftResult:
    """
    Compute drift using KS statistic and PSI.

    Args:
        baseline_values: Values from baseline period
        recent_values: Values from recent period
        n_bins: Number of bins for PSI calculation
    """
    if not baseline_values or not recent_values:
        return DriftResult(
            ks_statistic=0.0,
            ks_pvalue=1.0,
            psi=0.0,
            drift_status="stable",
            baseline_n=len(baseline_values),
            recent_n=len(recent_values),
        )

    baseline_arr = np.array(baseline_values)
    recent_arr = np.array(recent_values)

    # KS test
    ks_stat, ks_pvalue = stats.ks_2samp(baseline_arr, recent_arr)

    # PSI calculation
    # Define bins based on combined data
    combined = np.concatenate([baseline_arr, recent_arr])
    bin_edges = np.percentile(combined, np.linspace(0, 100, n_bins + 1))
    bin_edges = np.unique(bin_edges)  # Remove duplicates

    if len(bin_edges) < 2:
        # Not enough variation for PSI
        psi = 0.0
        baseline_hist = []
        recent_hist = []
    else:
        baseline_hist, _ = np.histogram(baseline_arr, bins=bin_edges, density=True)
        recent_hist, _ = np.histogram(recent_arr, bins=bin_edges, density=True)

        # Add small epsilon to avoid division by zero
        eps = 1e-10
        baseline_hist = baseline_hist + eps
        recent_hist = recent_hist + eps

        # Normalize to proportions
        baseline_prop = baseline_hist / np.sum(baseline_hist)
        recent_prop = recent_hist / np.sum(recent_hist)

        # PSI = sum((recent - baseline) * ln(recent / baseline))
        psi = float(np.sum((recent_prop - baseline_prop) * np.log(recent_prop / baseline_prop)))

    # Determine drift status
    if psi > 0.25 or ks_pvalue < 0.01:
        drift_status = "drifting"
    elif psi > 0.10 or ks_pvalue < 0.05:
        drift_status = "warning"
    else:
        drift_status = "stable"

    return DriftResult(
        ks_statistic=float(ks_stat),
        ks_pvalue=float(ks_pvalue),
        psi=float(psi),
        drift_status=drift_status,
        baseline_n=len(baseline_values),
        recent_n=len(recent_values),
        baseline_histogram=[float(x) for x in baseline_hist] if len(baseline_hist) > 0 else None,
        recent_histogram=[float(x) for x in recent_hist] if len(recent_hist) > 0 else None,
        histogram_bins=[float(x) for x in bin_edges] if len(bin_edges) > 0 else None,
    )


async def get_calibration_summary(
    db: AsyncSession,
    tenant_id: UUID,
    node_id: UUID,
) -> Optional[CalibrationSummary]:
    """Fetch latest calibration metrics for a node."""
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

    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        return None

    # Extract metrics from result_json
    metrics = job.result_json.get("metrics", {}) if job.result_json else {}

    return CalibrationSummary(
        brier_score=metrics.get("brier_score"),
        ece=metrics.get("ece"),
        method=job.config_json.get("method") if job.config_json else None,
        calibration_job_id=str(job.id),
    )


# =============================================================================
# PHASE 6: Endpoints
# =============================================================================

@router.get(
    "/nodes/{node_id}/reliability/summary",
    response_model=ReliabilitySummaryResponse,
    summary="Get Reliability Summary (PHASE 6)",
    tags=["Reliability"],
)
async def get_reliability_summary(
    node_id: UUID,
    metric_key: str = Query(..., description="Metric key to analyze (required)"),
    op: str = Query("gte", description="Comparison operator: gte, lte, gt, lt, eq"),
    threshold: Optional[float] = Query(None, description="Threshold for sensitivity at specific point"),
    manifest_hash: Optional[str] = Query(None, description="Filter by manifest hash"),
    window_days: int = Query(30, ge=1, le=365, description="Time window in days"),
    min_runs: int = Query(30, ge=1, le=1000, description="Minimum runs required"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_tenant_context),
) -> ReliabilitySummaryResponse:
    """
    PHASE 6: Get reliability summary for a node.

    Computes sensitivity, stability, and drift metrics from run outcomes.
    Returns `status: insufficient_data` if n_runs < min_runs.

    Multi-tenant scoped. All computations are deterministic and auditable.
    """
    tenant_id = UUID(tenant.tenant_id)
    computed_at = datetime.utcnow()

    # Compute deterministic seed
    seed_hash = compute_deterministic_seed(
        tenant_id=str(tenant_id),
        node_id=str(node_id),
        metric_key=metric_key,
        threshold=threshold,
        manifest_hash=manifest_hash,
    )

    # Build query for run outcomes
    cutoff_date = datetime.utcnow() - timedelta(days=window_days)

    query = (
        select(RunOutcome)
        .where(
            and_(
                RunOutcome.tenant_id == tenant_id,
                RunOutcome.node_id == node_id,
                RunOutcome.created_at >= cutoff_date,
            )
        )
        .order_by(RunOutcome.created_at.desc())
    )

    # Add manifest_hash filter if provided
    if manifest_hash:
        query = query.where(RunOutcome.manifest_hash == manifest_hash)

    result = await db.execute(query)
    outcomes = result.scalars().all()

    n_runs_total = len(outcomes)

    # Extract metric values
    values = []
    run_ids_used = []
    for outcome in outcomes:
        metrics = outcome.metrics_json or {}
        if metric_key in metrics:
            val = metrics[metric_key]
            if isinstance(val, (int, float)):
                values.append(float(val))
                run_ids_used.append(str(outcome.run_id))

    n_runs_used = len(values)

    # Build audit metadata
    audit = AuditMetadata(
        computed_at=computed_at,
        run_ids_used=run_ids_used,
        filters_applied={
            "node_id": str(node_id),
            "metric_key": metric_key,
            "manifest_hash": manifest_hash,
            "window_days": window_days,
            "op": op,
            "threshold": threshold,
        },
        deterministic_seed=seed_hash,
    )

    # Check for insufficient data
    if n_runs_used < min_runs:
        return ReliabilitySummaryResponse(
            status="insufficient_data",
            n_runs_total=n_runs_total,
            n_runs_used=n_runs_used,
            sensitivity=None,
            stability=None,
            drift=None,
            calibration=None,
            audit=audit,
        )

    # Compute sensitivity
    sensitivity = compute_sensitivity(values, op)
    sensitivity.metric_key = metric_key

    # Compute stability
    stability = compute_stability(values, seed_hash)

    # Compute drift (split into baseline vs recent)
    # Baseline: older half, Recent: newer half
    mid_point = n_runs_used // 2
    baseline_values = values[mid_point:]  # Older runs (later in sorted list)
    recent_values = values[:mid_point]    # Newer runs
    drift = compute_drift(baseline_values, recent_values)

    # Get calibration summary
    calibration = await get_calibration_summary(db, tenant_id, node_id)

    return ReliabilitySummaryResponse(
        status="ok",
        n_runs_total=n_runs_total,
        n_runs_used=n_runs_used,
        sensitivity=sensitivity,
        stability=stability,
        drift=drift,
        calibration=calibration,
        audit=audit,
    )


@router.get(
    "/nodes/{node_id}/reliability/detail",
    response_model=ReliabilityDetailResponse,
    summary="Get Reliability Detail (PHASE 6)",
    tags=["Reliability"],
)
async def get_reliability_detail(
    node_id: UUID,
    metric_key: str = Query(..., description="Metric key to analyze (required)"),
    op: str = Query("gte", description="Comparison operator: gte, lte, gt, lt, eq"),
    threshold: Optional[float] = Query(None, description="Threshold for sensitivity at specific point"),
    manifest_hash: Optional[str] = Query(None, description="Filter by manifest hash"),
    window_days: int = Query(30, ge=1, le=365, description="Time window in days"),
    min_runs: int = Query(30, ge=1, le=1000, description="Minimum runs required"),
    n_grid: int = Query(20, ge=5, le=100, description="Number of threshold grid points"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(get_tenant_context),
) -> ReliabilityDetailResponse:
    """
    PHASE 6: Get detailed reliability analysis for a node.

    Same as summary but includes:
    - raw_values: Raw metric values for custom analysis
    - percentiles: Percentile breakdown (p5, p25, p50, p75, p95)
    - bootstrap_samples: Full bootstrap sample estimates
    - Richer histogram data for drift visualization

    Multi-tenant scoped. All computations are deterministic and auditable.
    """
    tenant_id = UUID(tenant.tenant_id)
    computed_at = datetime.utcnow()

    # Compute deterministic seed
    seed_hash = compute_deterministic_seed(
        tenant_id=str(tenant_id),
        node_id=str(node_id),
        metric_key=metric_key,
        threshold=threshold,
        manifest_hash=manifest_hash,
    )

    # Build query for run outcomes
    cutoff_date = datetime.utcnow() - timedelta(days=window_days)

    query = (
        select(RunOutcome)
        .where(
            and_(
                RunOutcome.tenant_id == tenant_id,
                RunOutcome.node_id == node_id,
                RunOutcome.created_at >= cutoff_date,
            )
        )
        .order_by(RunOutcome.created_at.desc())
    )

    # Add manifest_hash filter if provided
    if manifest_hash:
        query = query.where(RunOutcome.manifest_hash == manifest_hash)

    result = await db.execute(query)
    outcomes = result.scalars().all()

    n_runs_total = len(outcomes)

    # Extract metric values
    values = []
    run_ids_used = []
    for outcome in outcomes:
        metrics = outcome.metrics_json or {}
        if metric_key in metrics:
            val = metrics[metric_key]
            if isinstance(val, (int, float)):
                values.append(float(val))
                run_ids_used.append(str(outcome.run_id))

    n_runs_used = len(values)

    # Build audit metadata
    audit = AuditMetadata(
        computed_at=computed_at,
        run_ids_used=run_ids_used,
        filters_applied={
            "node_id": str(node_id),
            "metric_key": metric_key,
            "manifest_hash": manifest_hash,
            "window_days": window_days,
            "op": op,
            "threshold": threshold,
            "n_grid": n_grid,
        },
        deterministic_seed=seed_hash,
    )

    # Check for insufficient data
    if n_runs_used < min_runs:
        return ReliabilityDetailResponse(
            status="insufficient_data",
            n_runs_total=n_runs_total,
            n_runs_used=n_runs_used,
            sensitivity=None,
            stability=None,
            drift=None,
            calibration=None,
            raw_values=None,
            percentiles=None,
            bootstrap_samples=None,
            audit=audit,
        )

    arr = np.array(values)

    # Compute sensitivity with configurable grid
    sensitivity = compute_sensitivity(values, op, n_grid=n_grid)
    sensitivity.metric_key = metric_key

    # Compute stability and capture bootstrap samples
    seed_int = int(seed_hash, 16) % (2**32)
    rng = np.random.default_rng(seed_int)
    n_bootstrap = 200
    bootstrap_samples = []
    n = len(arr)
    for _ in range(n_bootstrap):
        sample = rng.choice(arr, size=n, replace=True)
        bootstrap_samples.append(float(np.mean(sample)))

    bootstrap_arr = np.array(bootstrap_samples)
    stability = StabilityResult(
        bootstrap_mean=float(np.mean(bootstrap_arr)),
        bootstrap_std=float(np.std(bootstrap_arr)),
        ci_95_lower=float(np.percentile(bootstrap_arr, 2.5)),
        ci_95_upper=float(np.percentile(bootstrap_arr, 97.5)),
        n_bootstrap=n_bootstrap,
        seed_hash=seed_hash,
    )

    # Compute drift
    mid_point = n_runs_used // 2
    baseline_values = values[mid_point:]
    recent_values = values[:mid_point]
    drift = compute_drift(baseline_values, recent_values)

    # Get calibration summary
    calibration = await get_calibration_summary(db, tenant_id, node_id)

    # Compute percentiles
    percentiles = {
        "p5": float(np.percentile(arr, 5)),
        "p25": float(np.percentile(arr, 25)),
        "p50": float(np.percentile(arr, 50)),
        "p75": float(np.percentile(arr, 75)),
        "p95": float(np.percentile(arr, 95)),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }

    return ReliabilityDetailResponse(
        status="ok",
        n_runs_total=n_runs_total,
        n_runs_used=n_runs_used,
        sensitivity=sensitivity,
        stability=stability,
        drift=drift,
        calibration=calibration,
        raw_values=values,
        percentiles=percentiles,
        bootstrap_samples=bootstrap_samples,
        audit=audit,
    )
