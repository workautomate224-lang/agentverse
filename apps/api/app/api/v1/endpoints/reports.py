"""
PHASE 7: Aggregated Report Endpoints

Provides unified report endpoint that merges:
- Prediction (distribution + target probability)
- Reliability (sensitivity, stability, drift)
- Calibration (latest job metrics)
- Provenance (audit trail)

Reference: Phase 7 specification
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_tenant, TenantContext
from app.models.user import User
from app.schemas.report import (
    ReportResponse,
    ReportQueryParams,
    ReportOperator,
)
from app.services.report_service import get_report_service


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/nodes/{node_id}",
    response_model=ReportResponse,
    summary="Get Aggregated Report (PHASE 7)",
    description="""
    Get complete aggregated report for a node, including:

    - **Prediction**: Distribution histogram and P(metric op threshold)
    - **Reliability**: Sensitivity analysis, bootstrap stability CI, drift detection
    - **Calibration**: Latest calibration job metrics (Brier, ECE, curve)
    - **Provenance**: Filters applied, run counts, timestamps

    ## Key Behaviors

    - **NEVER returns 500** for missing data - returns 200 with `insufficient_data: true`
    - **Deterministic**: Same inputs produce identical outputs (seeded bootstrap)
    - **Multi-tenant**: All data scoped by tenant_id

    ## Query Parameters

    - `metric_key` (required): Metric key to analyze
    - `op` (required): Comparison operator (ge, gt, le, lt, eq)
    - `threshold` (required): Threshold value for target probability
    - `manifest_hash` (optional): Filter by manifest hash
    - `min_runs`: Minimum runs required (default: 3)
    - `window_days`: Time window in days (default: 30)
    - `n_sensitivity_grid`: Sensitivity grid points (default: 20)
    - `n_bootstrap`: Bootstrap samples for stability (default: 200)
    - `n_bins`: Histogram bins (default: 20)
    """,
    responses={
        200: {
            "description": "Report computed successfully (or insufficient_data=true if not enough runs)",
            "content": {
                "application/json": {
                    "example": {
                        "node_id": "550e8400-e29b-41d4-a716-446655440000",
                        "metric_key": "score",
                        "target": {"op": "ge", "threshold": 0.8},
                        "provenance": {
                            "manifest_hash": None,
                            "filters": {"window_days": 30, "min_runs": 3},
                            "n_runs": 50,
                            "updated_at": "2024-01-15T10:30:00Z"
                        },
                        "prediction": {
                            "distribution": {"bins": [], "counts": [], "min": 0.0, "max": 1.0},
                            "target_probability": 0.72
                        },
                        "calibration": {"available": True, "brier": 0.15, "ece": 0.08},
                        "reliability": {
                            "sensitivity": {"thresholds": [], "probabilities": []},
                            "stability": {"mean": 0.72, "ci_low": 0.68, "ci_high": 0.76},
                            "drift": {"status": "stable", "ks": 0.12, "psi": 0.05}
                        },
                        "insufficient_data": False,
                        "errors": []
                    }
                }
            }
        },
        401: {"description": "Not authenticated"},
        404: {"description": "Node not found"},
    },
    tags=["Reports"],
)
async def get_node_report(
    node_id: UUID,
    metric_key: str = Query(
        ...,
        min_length=1,
        description="Metric key to analyze (required)"
    ),
    op: ReportOperator = Query(
        ...,
        description="Comparison operator: ge (>=), gt (>), le (<=), lt (<), eq (==)"
    ),
    threshold: float = Query(
        ...,
        description="Threshold value for target probability"
    ),
    manifest_hash: Optional[str] = Query(
        None,
        description="Optional manifest hash filter"
    ),
    min_runs: int = Query(
        3,
        ge=1,
        le=1000,
        description="Minimum runs required for valid results"
    ),
    window_days: int = Query(
        30,
        ge=1,
        le=365,
        description="Time window in days"
    ),
    n_sensitivity_grid: int = Query(
        20,
        ge=5,
        le=100,
        description="Number of sensitivity grid points"
    ),
    n_bootstrap: int = Query(
        200,
        ge=50,
        le=1000,
        description="Number of bootstrap samples for stability"
    ),
    n_bins: int = Query(
        20,
        ge=5,
        le=100,
        description="Number of histogram bins"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(require_tenant),
) -> ReportResponse:
    """
    PHASE 7: Get aggregated report for a node.

    This endpoint aggregates all prediction and reliability data into a single
    response suitable for the Reports page. It NEVER returns HTTP 500 for
    missing data - instead returns HTTP 200 with insufficient_data=true.

    Multi-tenant scoped. All computations are deterministic and auditable.
    """
    # Build query params
    params = ReportQueryParams(
        metric_key=metric_key,
        op=op,
        threshold=threshold,
        manifest_hash=manifest_hash,
        min_runs=min_runs,
        window_days=window_days,
        n_sensitivity_grid=n_sensitivity_grid,
        n_bootstrap=n_bootstrap,
        n_bins=n_bins,
    )

    # Get service and compute report
    service = get_report_service(db)
    report = await service.compute_report(
        tenant_id=tenant.tenant_id,
        node_id=node_id,
        params=params,
    )

    return report


@router.get(
    "/nodes/{node_id}/export",
    response_model=ReportResponse,
    summary="Export Report as JSON (PHASE 7)",
    description="""
    Same as GET /nodes/{node_id} but with Content-Disposition header
    for file download. Use this endpoint for "Export JSON" functionality.
    """,
    tags=["Reports"],
)
async def export_node_report(
    node_id: UUID,
    metric_key: str = Query(..., min_length=1),
    op: ReportOperator = Query(...),
    threshold: float = Query(...),
    manifest_hash: Optional[str] = Query(None),
    min_runs: int = Query(3, ge=1, le=1000),
    window_days: int = Query(30, ge=1, le=365),
    n_sensitivity_grid: int = Query(20, ge=5, le=100),
    n_bootstrap: int = Query(200, ge=50, le=1000),
    n_bins: int = Query(20, ge=5, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(require_tenant),
) -> ReportResponse:
    """
    Export report as JSON file.

    This is identical to get_node_report but intended for download.
    Frontend should add Content-Disposition header for file download UX.
    """
    params = ReportQueryParams(
        metric_key=metric_key,
        op=op,
        threshold=threshold,
        manifest_hash=manifest_hash,
        min_runs=min_runs,
        window_days=window_days,
        n_sensitivity_grid=n_sensitivity_grid,
        n_bootstrap=n_bootstrap,
        n_bins=n_bins,
    )

    service = get_report_service(db)
    return await service.compute_report(
        tenant_id=tenant.tenant_id,
        node_id=node_id,
        params=params,
    )
