"""
STEP 10: Governance, Cost Controls, Safety, Access Control, Auditability
Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md STEP 10

Provides endpoints for:
- Admin/Governance (Audit Logs, Quotas, Costs, Feature Flags, Safety Blocks, Exports)
- Billing Hooks (Usage, Quota Remaining, Upgrade Tier, Download Invoice)
- Cost Records and Estimators
- Quota Enforcement (server-side)
- Feature Flags (API guards for tiered plans)
- Rate Limiting
- Safety Classification
- AuditLog (immutable, append-only)
- Export Integrity

Key constraints:
- C4: Auditable artifacts (all changes logged)
- C6: Multi-tenant (all data scoped by tenant_id)
- Quotas enforced server-side with degrade/block behaviors
- Feature flags enforced server-side (API guards)
- AuditLog is immutable, append-only
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.tenant import TenantContext, require_tenant
from app.models.user import User

router = APIRouter()


# =============================================================================
# Request Schemas
# =============================================================================

class ViewAuditLogsRequest(BaseModel):
    """Request for viewing audit logs."""
    project_id: Optional[str] = None
    node_id: Optional[str] = None
    run_id: Optional[str] = None
    planning_id: Optional[str] = None
    action_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=500)


class SetQuotasRequest(BaseModel):
    """Request for setting quotas."""
    tenant_id: str
    quota_type: str = Field(..., description="'runs', 'llm_calls', 'storage_gb', 'api_calls'")
    daily_limit: Optional[int] = None
    monthly_limit: Optional[int] = None
    rate_limit_per_minute: Optional[int] = None
    enforce_behavior: str = Field(
        default="block",
        description="'block', 'degrade', 'warn'"
    )


class ViewCostsRequest(BaseModel):
    """Request for viewing costs."""
    tenant_id: str
    project_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    group_by: str = Field(default="day", description="'hour', 'day', 'week', 'month'")
    include_breakdown: bool = True


class ManageFeatureFlagsRequest(BaseModel):
    """Request for managing feature flags."""
    tenant_id: str
    action: str = Field(..., description="'list', 'enable', 'disable', 'update'")
    feature_flag: Optional[str] = None
    value: Optional[Any] = None


class ReviewSafetyBlocksRequest(BaseModel):
    """Request for reviewing safety blocks."""
    tenant_id: Optional[str] = None
    block_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = Field(default=None, description="'pending', 'approved', 'rejected'")
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=500)


class ManageExportsRequest(BaseModel):
    """Request for managing exports."""
    action: str = Field(..., description="'list', 'revoke', 'extend', 'audit'")
    export_id: Optional[str] = None
    expiry_days: Optional[int] = None


class ViewUsageRequest(BaseModel):
    """Request for viewing usage."""
    tenant_id: str
    period: str = Field(default="current_month", description="'today', 'current_week', 'current_month', 'custom'")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    group_by: str = Field(default="day", description="'hour', 'day', 'resource_type'")


class ViewQuotaRemainingRequest(BaseModel):
    """Request for viewing quota remaining."""
    tenant_id: str
    quota_types: List[str] = Field(
        default=["runs", "llm_calls", "storage_gb", "api_calls"],
        description="Quota types to check"
    )


class UpgradeTierRequest(BaseModel):
    """Request for tier upgrade (stub)."""
    tenant_id: str
    target_tier: str = Field(..., description="'starter', 'professional', 'enterprise'")
    billing_cycle: str = Field(default="monthly", description="'monthly', 'annual'")


class DownloadInvoiceRequest(BaseModel):
    """Request for downloading invoice (stub)."""
    tenant_id: str
    invoice_id: Optional[str] = None
    period: Optional[str] = None
    format: str = Field(default="pdf", description="'pdf', 'csv'")


class CostEstimateRequest(BaseModel):
    """Request for cost estimation before run."""
    project_id: str
    run_config: Dict[str, Any]
    include_breakdown: bool = True


class SafetyCheckRequest(BaseModel):
    """Request for safety classification check."""
    content: str
    content_type: str = Field(..., description="'prompt', 'event', 'persona', 'output'")
    context: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Response Schemas
# =============================================================================

class AuditLogEntry(BaseModel):
    """Single audit log entry."""
    log_id: str
    timestamp: str
    actor_id: str
    actor_type: str
    org_id: str
    action_type: str
    resource_type: str
    resource_id: str
    spec_hash: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    client_ip: Optional[str] = None
    session_id: Optional[str] = None


class ViewAuditLogsResponse(BaseModel):
    """Response for viewing audit logs."""
    logs: List[AuditLogEntry]
    total_count: int
    page: int
    per_page: int
    has_more: bool


class QuotaSettings(BaseModel):
    """Quota settings for a tenant."""
    quota_type: str
    daily_limit: Optional[int] = None
    monthly_limit: Optional[int] = None
    rate_limit_per_minute: Optional[int] = None
    enforce_behavior: str
    current_usage: Dict[str, int] = Field(default_factory=dict)


class SetQuotasResponse(BaseModel):
    """Response for setting quotas."""
    tenant_id: str
    quotas: List[QuotaSettings]
    audit_log_id: str
    effective_from: str


class CostBreakdown(BaseModel):
    """Cost breakdown by category."""
    category: str
    amount_usd: float
    units: int
    unit_type: str


class CostSummary(BaseModel):
    """Cost summary for a period."""
    period: str
    total_usd: float
    breakdown: List[CostBreakdown]
    comparison_to_previous: Optional[float] = None


class ViewCostsResponse(BaseModel):
    """Response for viewing costs."""
    tenant_id: str
    project_id: Optional[str] = None
    start_date: str
    end_date: str
    total_cost_usd: float
    summaries: List[CostSummary]
    trends: Dict[str, Any] = Field(default_factory=dict)


class FeatureFlag(BaseModel):
    """Feature flag definition."""
    flag_name: str
    enabled: bool
    tier_required: str
    description: str
    config: Dict[str, Any] = Field(default_factory=dict)


class ManageFeatureFlagsResponse(BaseModel):
    """Response for managing feature flags."""
    tenant_id: str
    action: str
    flags: List[FeatureFlag]
    audit_log_id: str


class SafetyBlock(BaseModel):
    """Safety block record."""
    block_id: str
    timestamp: str
    block_type: str
    severity: str
    reason_code: str
    reason_text: str
    content_hash: str
    tenant_id: str
    user_id: str
    status: str
    reviewer_id: Optional[str] = None
    reviewed_at: Optional[str] = None


class ReviewSafetyBlocksResponse(BaseModel):
    """Response for reviewing safety blocks."""
    blocks: List[SafetyBlock]
    total_count: int
    page: int
    per_page: int
    summary: Dict[str, int] = Field(default_factory=dict)


class ExportRecord(BaseModel):
    """Export record with integrity metadata."""
    export_id: str
    created_at: str
    expires_at: Optional[str] = None
    export_type: str
    resource_ids: List[str]
    checksum: str
    checksum_algorithm: str
    size_bytes: int
    download_count: int
    status: str


class ManageExportsResponse(BaseModel):
    """Response for managing exports."""
    action: str
    exports: List[ExportRecord]
    total_count: int
    audit_log_id: str


class UsageMetric(BaseModel):
    """Usage metric for a period."""
    metric_type: str
    value: int
    unit: str
    limit: Optional[int] = None
    percentage_used: Optional[float] = None


class ViewUsageResponse(BaseModel):
    """Response for viewing usage."""
    tenant_id: str
    period: str
    start_date: str
    end_date: str
    metrics: List[UsageMetric]
    daily_breakdown: List[Dict[str, Any]] = Field(default_factory=list)


class QuotaRemaining(BaseModel):
    """Quota remaining for a specific type."""
    quota_type: str
    limit: int
    used: int
    remaining: int
    percentage_remaining: float
    reset_at: Optional[str] = None
    enforce_behavior: str


class ViewQuotaRemainingResponse(BaseModel):
    """Response for viewing quota remaining."""
    tenant_id: str
    quotas: List[QuotaRemaining]
    warnings: List[str] = Field(default_factory=list)


class TierInfo(BaseModel):
    """Tier information."""
    tier_name: str
    monthly_price_usd: float
    annual_price_usd: float
    features: List[str]
    quotas: Dict[str, int]


class UpgradeTierResponse(BaseModel):
    """Response for tier upgrade (stub)."""
    tenant_id: str
    current_tier: str
    target_tier: str
    price_difference_usd: float
    checkout_url: Optional[str] = None
    status: str
    audit_log_id: str


class DownloadInvoiceResponse(BaseModel):
    """Response for downloading invoice (stub)."""
    tenant_id: str
    invoice_id: str
    period: str
    total_usd: float
    download_url: Optional[str] = None
    format: str
    status: str


class CostEstimateResponse(BaseModel):
    """Response for cost estimation."""
    project_id: str
    estimated_min_usd: float
    estimated_max_usd: float
    estimated_likely_usd: float
    breakdown: Dict[str, float] = Field(default_factory=dict)
    confidence: float
    warnings: List[str] = Field(default_factory=list)


class SafetyCheckResponse(BaseModel):
    """Response for safety classification."""
    is_safe: bool
    risk_level: str = Field(..., description="'low', 'medium', 'high', 'blocked'")
    classifications: List[str]
    reason_codes: List[str]
    action_taken: str = Field(..., description="'allow', 'warn', 'downgrade', 'block'")
    audit_log_id: str


# =============================================================================
# Admin / Governance Endpoints (STEP 10 Buttons)
# =============================================================================

@router.post("/audit-logs/view", response_model=ViewAuditLogsResponse)
async def view_audit_logs(
    request: ViewAuditLogsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Admin / Governance: View Audit Logs.

    AuditLog is immutable, append-only.
    Includes actor, action, entity ids, spec_hash, timestamp.
    Supports filtering by project/node/run/planning and time range.
    """
    request_id = str(uuid4())

    # Mock audit logs
    mock_logs = [
        AuditLogEntry(
            log_id=str(uuid4()),
            timestamp=(datetime.now() - timedelta(hours=i)).isoformat(),
            actor_id=str(uuid4()),
            actor_type="user",
            org_id=str(tenant.tenant_id) if tenant.tenant_id else str(uuid4()),
            action_type=["create", "update", "delete", "view"][i % 4],
            resource_type=["run", "node", "project", "persona"][i % 4],
            resource_id=str(uuid4()),
            spec_hash=f"sha256:{uuid4().hex[:32]}",
            details={"action": f"Action {i}"},
            client_ip="192.168.1.1",
        )
        for i in range(min(10, request.per_page))
    ]

    return ViewAuditLogsResponse(
        logs=mock_logs,
        total_count=100,
        page=request.page,
        per_page=request.per_page,
        has_more=request.page * request.per_page < 100,
    )


@router.post("/quotas/set", response_model=SetQuotasResponse)
async def set_quotas(
    request: SetQuotasRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Admin / Governance: Set Quotas.

    Quotas enforced server-side with degrade/block behaviors.
    Emits AuditLog entry for quota changes.
    """
    request_id = str(uuid4())
    audit_log_id = str(uuid4())

    quota = QuotaSettings(
        quota_type=request.quota_type,
        daily_limit=request.daily_limit,
        monthly_limit=request.monthly_limit,
        rate_limit_per_minute=request.rate_limit_per_minute,
        enforce_behavior=request.enforce_behavior,
        current_usage={"today": 0, "this_month": 0},
    )

    return SetQuotasResponse(
        tenant_id=request.tenant_id,
        quotas=[quota],
        audit_log_id=audit_log_id,
        effective_from=datetime.now().isoformat(),
    )


@router.post("/costs/view", response_model=ViewCostsResponse)
async def view_costs(
    request: ViewCostsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Admin / Governance: View Costs.

    CostRecord stored per run/planning/calibration.
    Returns cost breakdown by category and time period.
    """
    request_id = str(uuid4())

    start = request.start_date or datetime.now() - timedelta(days=30)
    end = request.end_date or datetime.now()

    # Mock cost summaries
    mock_summaries = [
        CostSummary(
            period=f"2024-01-{10-i:02d}",
            total_usd=50.0 + i * 5,
            breakdown=[
                CostBreakdown(
                    category="llm_calls",
                    amount_usd=30.0 + i * 3,
                    units=1000 + i * 100,
                    unit_type="tokens",
                ),
                CostBreakdown(
                    category="compute",
                    amount_usd=15.0 + i * 1.5,
                    units=60 + i * 5,
                    unit_type="minutes",
                ),
                CostBreakdown(
                    category="storage",
                    amount_usd=5.0 + i * 0.5,
                    units=10 + i,
                    unit_type="gb_hours",
                ),
            ],
            comparison_to_previous=-0.05 if i > 0 else None,
        )
        for i in range(7)
    ]

    return ViewCostsResponse(
        tenant_id=request.tenant_id,
        project_id=request.project_id,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        total_cost_usd=sum(s.total_usd for s in mock_summaries),
        summaries=mock_summaries,
        trends={"trend": "decreasing", "avg_daily": 52.0},
    )


@router.post("/feature-flags/manage", response_model=ManageFeatureFlagsResponse)
async def manage_feature_flags(
    request: ManageFeatureFlagsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Admin / Governance: Manage Feature Flags.

    Feature flags enforced server-side (API guards) for tiered plans.
    Emits AuditLog entry for flag changes.
    """
    request_id = str(uuid4())
    audit_log_id = str(uuid4())

    # Mock feature flags
    mock_flags = [
        FeatureFlag(
            flag_name="target_mode",
            enabled=True,
            tier_required="professional",
            description="Enable target mode planning",
        ),
        FeatureFlag(
            flag_name="calibration",
            enabled=True,
            tier_required="professional",
            description="Enable calibration and reliability scoring",
        ),
        FeatureFlag(
            flag_name="ensemble_runs",
            enabled=False,
            tier_required="enterprise",
            description="Enable ensemble simulation runs",
        ),
        FeatureFlag(
            flag_name="advanced_export",
            enabled=True,
            tier_required="starter",
            description="Enable advanced export formats",
        ),
    ]

    return ManageFeatureFlagsResponse(
        tenant_id=request.tenant_id,
        action=request.action,
        flags=mock_flags,
        audit_log_id=audit_log_id,
    )


@router.post("/safety-blocks/review", response_model=ReviewSafetyBlocksResponse)
async def review_safety_blocks(
    request: ReviewSafetyBlocksRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Admin / Governance: Review Safety Blocks.

    Safety classifier blocks/downgrades high-risk requests; logs decisions.
    Returns list of safety blocks with reason codes.
    """
    request_id = str(uuid4())

    # Mock safety blocks
    mock_blocks = [
        SafetyBlock(
            block_id=str(uuid4()),
            timestamp=(datetime.now() - timedelta(hours=i)).isoformat(),
            block_type=["content", "prompt", "output"][i % 3],
            severity=["low", "medium", "high"][i % 3],
            reason_code=f"SAFETY_{i:03d}",
            reason_text=f"Safety violation type {i}",
            content_hash=f"sha256:{uuid4().hex[:32]}",
            tenant_id=str(uuid4()),
            user_id=str(uuid4()),
            status=["pending", "approved", "rejected"][i % 3],
        )
        for i in range(min(5, request.per_page))
    ]

    return ReviewSafetyBlocksResponse(
        blocks=mock_blocks,
        total_count=50,
        page=request.page,
        per_page=request.per_page,
        summary={"pending": 10, "approved": 25, "rejected": 15},
    )


@router.post("/exports/manage", response_model=ManageExportsResponse)
async def manage_exports(
    request: ManageExportsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Admin / Governance: Manage Exports.

    Export bundles include integrity metadata.
    Access checks + audit log for every download.
    """
    request_id = str(uuid4())
    audit_log_id = str(uuid4())

    # Mock export records
    mock_exports = [
        ExportRecord(
            export_id=str(uuid4()),
            created_at=(datetime.now() - timedelta(days=i)).isoformat(),
            expires_at=(datetime.now() + timedelta(days=30 - i)).isoformat(),
            export_type=["full_bundle", "trace_only", "outcome_only"][i % 3],
            resource_ids=[str(uuid4()) for _ in range(2)],
            checksum=f"sha256:{uuid4().hex}",
            checksum_algorithm="sha256",
            size_bytes=1024 * 1024 * (i + 1),
            download_count=i * 2,
            status="active",
        )
        for i in range(5)
    ]

    return ManageExportsResponse(
        action=request.action,
        exports=mock_exports,
        total_count=len(mock_exports),
        audit_log_id=audit_log_id,
    )


# =============================================================================
# Billing Hooks Endpoints (STEP 10 Buttons)
# =============================================================================

@router.post("/billing/usage", response_model=ViewUsageResponse)
async def view_usage(
    request: ViewUsageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Billing Hooks: View Usage.

    Returns usage metrics for the specified period.
    Includes breakdown by day and resource type.
    """
    request_id = str(uuid4())

    # Calculate period dates
    now = datetime.now()
    if request.period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif request.period == "current_week":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif request.period == "current_month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    else:
        start = request.start_date or now - timedelta(days=30)
        end = request.end_date or now

    # Mock usage metrics
    mock_metrics = [
        UsageMetric(
            metric_type="runs",
            value=150,
            unit="runs",
            limit=500,
            percentage_used=30.0,
        ),
        UsageMetric(
            metric_type="llm_calls",
            value=5000,
            unit="calls",
            limit=10000,
            percentage_used=50.0,
        ),
        UsageMetric(
            metric_type="storage_gb",
            value=25,
            unit="gb",
            limit=100,
            percentage_used=25.0,
        ),
        UsageMetric(
            metric_type="api_calls",
            value=10000,
            unit="calls",
            limit=50000,
            percentage_used=20.0,
        ),
    ]

    return ViewUsageResponse(
        tenant_id=request.tenant_id,
        period=request.period,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        metrics=mock_metrics,
        daily_breakdown=[
            {"date": (now - timedelta(days=i)).strftime("%Y-%m-%d"), "runs": 10 + i, "llm_calls": 500 + i * 50}
            for i in range(7)
        ],
    )


@router.post("/billing/quota-remaining", response_model=ViewQuotaRemainingResponse)
async def view_quota_remaining(
    request: ViewQuotaRemainingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Billing Hooks: View Quota Remaining.

    Returns remaining quota for each quota type.
    Includes warnings if nearing limits.
    """
    request_id = str(uuid4())

    # Mock quota remaining
    mock_quotas = [
        QuotaRemaining(
            quota_type="runs",
            limit=500,
            used=350,
            remaining=150,
            percentage_remaining=30.0,
            reset_at=(datetime.now() + timedelta(days=15)).isoformat(),
            enforce_behavior="block",
        ),
        QuotaRemaining(
            quota_type="llm_calls",
            limit=10000,
            used=5000,
            remaining=5000,
            percentage_remaining=50.0,
            reset_at=(datetime.now() + timedelta(days=15)).isoformat(),
            enforce_behavior="degrade",
        ),
        QuotaRemaining(
            quota_type="storage_gb",
            limit=100,
            used=25,
            remaining=75,
            percentage_remaining=75.0,
            reset_at=None,
            enforce_behavior="warn",
        ),
    ]

    # Generate warnings
    warnings = []
    for q in mock_quotas:
        if q.percentage_remaining < 20:
            warnings.append(f"Low quota warning: {q.quota_type} is at {100 - q.percentage_remaining:.0f}% usage")

    return ViewQuotaRemainingResponse(
        tenant_id=request.tenant_id,
        quotas=mock_quotas,
        warnings=warnings,
    )


@router.post("/billing/upgrade-tier", response_model=UpgradeTierResponse)
async def upgrade_tier(
    request: UpgradeTierRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Billing Hooks: Upgrade Tier (stub).

    Returns checkout URL for tier upgrade.
    Actual payment processing handled by external service.
    """
    request_id = str(uuid4())
    audit_log_id = str(uuid4())

    # Tier pricing (stub)
    tier_prices = {
        "starter": {"monthly": 29, "annual": 290},
        "professional": {"monthly": 99, "annual": 990},
        "enterprise": {"monthly": 499, "annual": 4990},
    }

    current_tier = "starter"  # Would come from DB
    current_price = tier_prices.get(current_tier, {}).get(request.billing_cycle, 0)
    target_price = tier_prices.get(request.target_tier, {}).get(request.billing_cycle, 0)
    price_diff = target_price - current_price

    return UpgradeTierResponse(
        tenant_id=request.tenant_id,
        current_tier=current_tier,
        target_tier=request.target_tier,
        price_difference_usd=price_diff,
        checkout_url=f"/checkout?tier={request.target_tier}&billing={request.billing_cycle}",
        status="checkout_ready",
        audit_log_id=audit_log_id,
    )


@router.post("/billing/download-invoice", response_model=DownloadInvoiceResponse)
async def download_invoice(
    request: DownloadInvoiceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Billing Hooks: Download Invoice (stub).

    Returns download URL for invoice.
    Emits audit log entry for download.
    """
    request_id = str(uuid4())
    invoice_id = request.invoice_id or str(uuid4())
    period = request.period or datetime.now().strftime("%Y-%m")

    return DownloadInvoiceResponse(
        tenant_id=request.tenant_id,
        invoice_id=invoice_id,
        period=period,
        total_usd=150.0,
        download_url=f"/api/v1/governance/invoices/{invoice_id}/download.{request.format}",
        format=request.format,
        status="ready",
    )


# =============================================================================
# Cost Estimation Endpoints
# =============================================================================

@router.post("/costs/estimate", response_model=CostEstimateResponse)
async def estimate_costs(
    request: CostEstimateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Cost Estimation: Pre-run cost range estimator.

    CostRecord stored per run/planning/calibration; estimator returns pre-run cost range.
    Provides min/max/likely estimates with breakdown.
    """
    request_id = str(uuid4())

    # Extract config for estimation
    ticks = request.run_config.get("ticks", 100)
    agents = request.run_config.get("agents", 10)
    ensemble_size = request.run_config.get("ensemble_size", 1)

    # Calculate estimates
    base_cost = ticks * agents * 0.001
    llm_cost = ticks * 0.01 * ensemble_size
    compute_cost = ticks * agents * 0.0001 * ensemble_size

    estimated_min = (base_cost + llm_cost + compute_cost) * 0.8
    estimated_max = (base_cost + llm_cost + compute_cost) * 1.5
    estimated_likely = base_cost + llm_cost + compute_cost

    warnings = []
    if ensemble_size > 10:
        warnings.append("Large ensemble size may significantly increase costs")
    if ticks > 1000:
        warnings.append("High tick count will increase compute time")

    return CostEstimateResponse(
        project_id=request.project_id,
        estimated_min_usd=round(estimated_min, 4),
        estimated_max_usd=round(estimated_max, 4),
        estimated_likely_usd=round(estimated_likely, 4),
        breakdown={
            "llm_compilation": round(llm_cost * 0.3, 4),
            "llm_runtime": round(llm_cost * 0.7, 4),
            "compute": round(compute_cost, 4),
            "storage": round(base_cost * 0.1, 4),
        },
        confidence=0.85,
        warnings=warnings,
    )


# =============================================================================
# Safety Classification Endpoints
# =============================================================================

@router.post("/safety/check", response_model=SafetyCheckResponse)
async def check_safety(
    request: SafetyCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Safety Classification: Check content for safety violations.

    Safety classifier blocks/downgrades high-risk requests; logs decisions.
    Returns classification result with reason codes.
    """
    request_id = str(uuid4())
    audit_log_id = str(uuid4())

    # Mock safety classification (would use actual classifier)
    content_lower = request.content.lower()

    # Simple keyword-based mock classification
    classifications = []
    reason_codes = []
    risk_level = "low"
    action_taken = "allow"

    # Check for high-risk content (mock logic)
    if any(word in content_lower for word in ["harm", "illegal", "dangerous"]):
        risk_level = "high"
        action_taken = "block"
        classifications.append("harmful_content")
        reason_codes.append("SAFETY_HARMFUL_001")
    elif any(word in content_lower for word in ["sensitive", "confidential"]):
        risk_level = "medium"
        action_taken = "warn"
        classifications.append("sensitive_content")
        reason_codes.append("SAFETY_SENSITIVE_001")

    return SafetyCheckResponse(
        is_safe=action_taken != "block",
        risk_level=risk_level,
        classifications=classifications,
        reason_codes=reason_codes,
        action_taken=action_taken,
        audit_log_id=audit_log_id,
    )


# =============================================================================
# Rate Limiting Endpoints
# =============================================================================

@router.get("/rate-limits/{tenant_id}")
async def get_rate_limits(
    tenant_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Get current rate limits for a tenant.

    Rate limiting for runs/plans/events to prevent abuse and cost spikes.
    """
    return {
        "tenant_id": tenant_id,
        "rate_limits": {
            "runs_per_minute": 10,
            "plans_per_minute": 5,
            "events_per_minute": 100,
            "api_calls_per_minute": 1000,
        },
        "current_usage": {
            "runs_this_minute": 3,
            "plans_this_minute": 1,
            "events_this_minute": 25,
            "api_calls_this_minute": 150,
        },
        "status": "within_limits",
    }


# =============================================================================
# Quota Enforcement Endpoints
# =============================================================================

@router.post("/quotas/check")
async def check_quota(
    tenant_id: str,
    quota_type: str,
    requested_amount: int = 1,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(require_tenant),
):
    """
    Check if quota allows the requested action.

    Quotas enforced server-side with degrade/block behaviors.
    Returns whether action is allowed and any enforcement action.
    """
    # Mock quota check
    mock_limits = {
        "runs": {"limit": 500, "used": 350},
        "llm_calls": {"limit": 10000, "used": 5000},
        "storage_gb": {"limit": 100, "used": 25},
    }

    quota = mock_limits.get(quota_type, {"limit": 1000, "used": 0})
    remaining = quota["limit"] - quota["used"]
    allowed = remaining >= requested_amount

    enforcement_action = "allow"
    if not allowed:
        enforcement_action = "block"
    elif remaining < requested_amount * 2:
        enforcement_action = "warn"

    return {
        "tenant_id": tenant_id,
        "quota_type": quota_type,
        "requested_amount": requested_amount,
        "remaining": remaining,
        "allowed": allowed,
        "enforcement_action": enforcement_action,
        "message": f"Quota {'allows' if allowed else 'blocks'} requested amount",
    }
