"""
Admin Endpoints for Step 4 Production Hardening

Endpoints:
- POST /admin/whitelist - Add email to alpha whitelist
- DELETE /admin/whitelist/{email} - Remove from whitelist
- GET /admin/whitelist - List whitelist entries
- POST /admin/kill-run/{run_id} - Kill a running simulation
- GET /admin/kill-stats - Get kill statistics
- GET /admin/usage-stats - Get usage statistics
- POST /admin/quota-policy - Create/update quota policy

All endpoints require admin role.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.quota import AlphaWhitelist, QuotaPolicy, UsageDailyRollup, RunAbortLog, UserTier
from app.services.rbac_service import RBACService, AccessDeniedError, Scope
from app.services.kill_switch import KillSwitchService
from app.services.quota_service import QuotaService, DEFAULT_POLICIES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# Request/Response schemas
class WhitelistAddRequest(BaseModel):
    email: EmailStr
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None


class WhitelistEntry(BaseModel):
    id: str
    email: str
    user_id: Optional[str]
    added_by: Optional[str]
    reason: Optional[str]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]


class KillRunRequest(BaseModel):
    reason: str = "Admin intervention"


class KillRunResponse(BaseModel):
    success: bool
    run_id: str
    reason: str
    message: str
    timestamp: str
    error: Optional[str] = None


class QuotaPolicyRequest(BaseModel):
    tier: str
    max_runs_per_user_per_day: int = 10
    max_steps_per_user_per_day: int = 1000
    max_exports_per_user_per_day: int = 50
    max_runs_per_project_per_day: int = 20
    max_steps_per_run: int = 100
    max_agents_per_run: int = 1000
    max_llm_calls_per_run: int = 500
    max_tokens_per_run: int = 100000
    max_wall_clock_seconds: int = 300
    max_cost_usd_per_run: float = 1.0
    max_concurrent_runs: int = 3
    force_full_rep: bool = True


class CostEstimateRequest(BaseModel):
    agent_count: int
    tick_count: int
    model: str = "openai/gpt-4o-mini"


class CostEstimateResponse(BaseModel):
    estimated_llm_calls: int
    estimated_tokens_min: int
    estimated_tokens_max: int
    estimated_cost_usd_min: float
    estimated_cost_usd_max: float
    estimated_runtime_seconds: int
    estimated_rep_outputs: int
    within_quota: bool
    quota_limits: dict


async def require_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Dependency to require admin role."""
    rbac = RBACService(db)
    if not await rbac.is_admin(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user


# Whitelist endpoints
@router.post("/whitelist", response_model=WhitelistEntry)
async def add_to_whitelist(
    request: WhitelistAddRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Add an email to the alpha whitelist."""
    # Check if already exists
    existing = await db.execute(
        select(AlphaWhitelist).where(AlphaWhitelist.email == request.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Email already whitelisted"
        )

    # Check if user exists with this email
    user_result = await db.execute(
        select(User.id).where(User.email == request.email)
    )
    user_id = user_result.scalar_one_or_none()

    entry = AlphaWhitelist(
        email=request.email,
        user_id=user_id,
        added_by=admin.email,
        reason=request.reason,
        expires_at=request.expires_at,
        is_active=True
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return WhitelistEntry(
        id=str(entry.id),
        email=entry.email,
        user_id=str(entry.user_id) if entry.user_id else None,
        added_by=entry.added_by,
        reason=entry.reason,
        is_active=entry.is_active,
        created_at=entry.created_at,
        expires_at=entry.expires_at
    )


@router.delete("/whitelist/{email}")
async def remove_from_whitelist(
    email: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Remove an email from the alpha whitelist."""
    result = await db.execute(
        delete(AlphaWhitelist).where(AlphaWhitelist.email == email)
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Email not found in whitelist"
        )
    await db.commit()
    return {"success": True, "email": email}


@router.get("/whitelist", response_model=List[WhitelistEntry])
async def list_whitelist(
    active_only: bool = True,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all whitelist entries."""
    query = select(AlphaWhitelist)
    if active_only:
        query = query.where(AlphaWhitelist.is_active == True)
    query = query.limit(limit).offset(offset).order_by(AlphaWhitelist.created_at.desc())

    result = await db.execute(query)
    entries = result.scalars().all()

    return [
        WhitelistEntry(
            id=str(e.id),
            email=e.email,
            user_id=str(e.user_id) if e.user_id else None,
            added_by=e.added_by,
            reason=e.reason,
            is_active=e.is_active,
            created_at=e.created_at,
            expires_at=e.expires_at
        )
        for e in entries
    ]


# Kill run endpoint
@router.post("/kill-run/{run_id}", response_model=KillRunResponse)
async def kill_run(
    run_id: UUID,
    request: KillRunRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Kill a running simulation."""
    kill_service = KillSwitchService(db)
    result = await kill_service.admin_kill_run(
        run_id=run_id,
        admin_id=admin.id,
        reason=request.reason
    )

    return KillRunResponse(
        success=result.get("success", False),
        run_id=str(run_id),
        reason=result.get("reason", "admin_kill"),
        message=result.get("message", request.reason),
        timestamp=result.get("timestamp", datetime.now(timezone.utc).isoformat()),
        error=result.get("error")
    )


@router.get("/kill-stats")
async def get_kill_stats(
    hours: int = Query(24, le=168),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get kill statistics for the specified period."""
    kill_service = KillSwitchService(db)
    return await kill_service.get_kill_stats(hours=hours)


# Usage stats endpoint
@router.get("/usage-stats")
async def get_usage_stats(
    days: int = Query(7, le=30),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get usage statistics for the specified period."""
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)

    # Aggregate usage by date
    result = await db.execute(
        select(
            UsageDailyRollup.rollup_date,
            func.sum(UsageDailyRollup.runs_created),
            func.sum(UsageDailyRollup.steps_executed),
            func.sum(UsageDailyRollup.llm_calls),
            func.sum(UsageDailyRollup.tokens_used),
            func.sum(UsageDailyRollup.cost_usd)
        )
        .where(UsageDailyRollup.rollup_date >= cutoff)
        .group_by(UsageDailyRollup.rollup_date)
        .order_by(UsageDailyRollup.rollup_date)
    )
    rows = result.fetchall()

    daily_stats = [
        {
            "date": str(row[0]),
            "runs_created": int(row[1] or 0),
            "steps_executed": int(row[2] or 0),
            "llm_calls": int(row[3] or 0),
            "tokens_used": int(row[4] or 0),
            "cost_usd": float(row[5] or 0)
        }
        for row in rows
    ]

    # Totals
    totals = {
        "runs_created": sum(d["runs_created"] for d in daily_stats),
        "steps_executed": sum(d["steps_executed"] for d in daily_stats),
        "llm_calls": sum(d["llm_calls"] for d in daily_stats),
        "tokens_used": sum(d["tokens_used"] for d in daily_stats),
        "cost_usd": sum(d["cost_usd"] for d in daily_stats)
    }

    return {
        "period_days": days,
        "daily_stats": daily_stats,
        "totals": totals
    }


# Quota policy endpoints
@router.post("/quota-policy")
async def create_or_update_quota_policy(
    request: QuotaPolicyRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create or update a quota policy."""
    # Check if exists
    result = await db.execute(
        select(QuotaPolicy).where(QuotaPolicy.tier == request.tier)
    )
    policy = result.scalar_one_or_none()

    if policy:
        # Update existing
        policy.max_runs_per_user_per_day = request.max_runs_per_user_per_day
        policy.max_steps_per_user_per_day = request.max_steps_per_user_per_day
        policy.max_exports_per_user_per_day = request.max_exports_per_user_per_day
        policy.max_runs_per_project_per_day = request.max_runs_per_project_per_day
        policy.max_steps_per_run = request.max_steps_per_run
        policy.max_agents_per_run = request.max_agents_per_run
        policy.max_llm_calls_per_run = request.max_llm_calls_per_run
        policy.max_tokens_per_run = request.max_tokens_per_run
        policy.max_wall_clock_seconds = request.max_wall_clock_seconds
        policy.max_cost_usd_per_run = request.max_cost_usd_per_run
        policy.max_concurrent_runs = request.max_concurrent_runs
        policy.force_full_rep = request.force_full_rep
        policy.updated_at = datetime.now(timezone.utc)
    else:
        # Create new
        policy = QuotaPolicy(
            tier=request.tier,
            **request.dict(exclude={"tier"})
        )
        db.add(policy)

    await db.commit()
    await db.refresh(policy)

    return {
        "id": str(policy.id),
        "tier": policy.tier,
        "updated_at": policy.updated_at.isoformat()
    }


@router.get("/quota-policies")
async def list_quota_policies(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all quota policies."""
    result = await db.execute(select(QuotaPolicy))
    policies = result.scalars().all()

    # Merge with defaults
    policy_dict = {p.tier: p for p in policies}
    merged = []

    for tier in UserTier:
        if tier.value in policy_dict:
            p = policy_dict[tier.value]
            merged.append({
                "tier": p.tier,
                "source": "database",
                "max_runs_per_user_per_day": p.max_runs_per_user_per_day,
                "max_steps_per_user_per_day": p.max_steps_per_user_per_day,
                "max_exports_per_user_per_day": p.max_exports_per_user_per_day,
                "max_runs_per_project_per_day": p.max_runs_per_project_per_day,
                "max_steps_per_run": p.max_steps_per_run,
                "max_agents_per_run": p.max_agents_per_run,
                "max_llm_calls_per_run": p.max_llm_calls_per_run,
                "max_tokens_per_run": p.max_tokens_per_run,
                "max_wall_clock_seconds": p.max_wall_clock_seconds,
                "max_cost_usd_per_run": p.max_cost_usd_per_run,
                "max_concurrent_runs": p.max_concurrent_runs,
                "force_full_rep": p.force_full_rep,
            })
        else:
            defaults = DEFAULT_POLICIES.get(tier.value, {})
            merged.append({
                "tier": tier.value,
                "source": "default",
                **defaults
            })

    return merged


# Cost estimate endpoint (public but uses user's tier)
@router.post("/cost-estimate", response_model=CostEstimateResponse)
async def get_cost_estimate(
    request: CostEstimateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get pre-run cost estimate based on configuration.
    Uses user's tier to determine limits.
    """
    quota_service = QuotaService(db)
    policy = await quota_service.get_policy(current_user.tier)

    # Estimate calculations (based on typical usage patterns)
    # Each agent gets persona enrichment LLM call during compilation
    llm_calls = request.agent_count

    # Token estimates (based on typical persona enrichment)
    tokens_per_call_min = 150  # Typical minimum
    tokens_per_call_max = 500  # Typical maximum

    tokens_min = llm_calls * tokens_per_call_min
    tokens_max = llm_calls * tokens_per_call_max

    # Cost estimates (based on gpt-4o-mini pricing)
    cost_per_1k_tokens = 0.00015  # ~$0.15 per 1M tokens
    cost_min = (tokens_min / 1000) * cost_per_1k_tokens
    cost_max = (tokens_max / 1000) * cost_per_1k_tokens

    # Runtime estimate (based on typical execution)
    # ~1 second per agent for compilation + ~0.5s per tick
    runtime_seconds = (request.agent_count * 1) + (request.tick_count * 0.5)

    # REP outputs (5 files)
    rep_outputs = 5

    # Check against quota
    within_quota = (
        llm_calls <= policy["max_llm_calls_per_run"] and
        tokens_max <= policy["max_tokens_per_run"] and
        cost_max <= policy["max_cost_usd_per_run"] and
        runtime_seconds <= policy["max_wall_clock_seconds"]
    )

    return CostEstimateResponse(
        estimated_llm_calls=llm_calls,
        estimated_tokens_min=tokens_min,
        estimated_tokens_max=tokens_max,
        estimated_cost_usd_min=round(cost_min, 6),
        estimated_cost_usd_max=round(cost_max, 6),
        estimated_runtime_seconds=int(runtime_seconds),
        estimated_rep_outputs=rep_outputs,
        within_quota=within_quota,
        quota_limits={
            "max_llm_calls": policy["max_llm_calls_per_run"],
            "max_tokens": policy["max_tokens_per_run"],
            "max_cost_usd": policy["max_cost_usd_per_run"],
            "max_runtime": policy["max_wall_clock_seconds"]
        }
    )
