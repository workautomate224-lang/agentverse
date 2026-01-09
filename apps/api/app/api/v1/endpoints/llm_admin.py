"""
LLM Admin API Endpoints
Reference: GAPS.md GAP-P0-001

Admin-only endpoints for managing LLM profiles, viewing call logs,
and tracking costs.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_current_admin_user, get_db, require_tenant
from app.core.security import TenantContext
from app.models.llm import LLMCall, LLMProfile
from app.models.user import User
from app.schemas.llm import (
    STANDARD_PROFILE_KEYS,
    AvailableModel,
    AvailableModelsResponse,
    LLMCallListResponse,
    LLMCallResponse,
    LLMCostByProfile,
    LLMCostReport,
    LLMCostSummary,
    LLMProfileCreate,
    LLMProfileListResponse,
    LLMProfileResponse,
    LLMProfileUpdate,
    ProfileKeyInfo,
    ProfileKeysResponse,
)
from app.services.llm_router import LLMRouter
from app.services.openrouter import AVAILABLE_MODELS

router = APIRouter()


# =============================================================================
# Profile Management Endpoints
# =============================================================================

@router.get("/profiles", response_model=LLMProfileListResponse)
async def list_profiles(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    include_global: bool = Query(True, description="Include global profiles"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    List all LLM profiles.

    Admin-only endpoint to view all configured LLM profiles.
    Can filter by tenant or include global defaults.
    """
    router_service = LLMRouter(db)
    profiles = await router_service.list_profiles(
        tenant_id=tenant_id,
        include_global=include_global,
    )

    return LLMProfileListResponse(
        profiles=[
            LLMProfileResponse(
                id=str(p.id),
                tenant_id=str(p.tenant_id) if p.tenant_id else None,
                profile_key=p.profile_key,
                label=p.label,
                description=p.description,
                model=p.model,
                temperature=p.temperature,
                max_tokens=p.max_tokens,
                top_p=p.top_p,
                frequency_penalty=p.frequency_penalty,
                presence_penalty=p.presence_penalty,
                cost_per_1k_input_tokens=p.cost_per_1k_input_tokens,
                cost_per_1k_output_tokens=p.cost_per_1k_output_tokens,
                fallback_models=p.fallback_models,
                rate_limit_rpm=p.rate_limit_rpm,
                rate_limit_tpm=p.rate_limit_tpm,
                cache_enabled=p.cache_enabled,
                cache_ttl_seconds=p.cache_ttl_seconds,
                system_prompt_template=p.system_prompt_template,
                priority=p.priority,
                is_active=p.is_active,
                is_default=p.is_default,
                created_at=p.created_at,
                updated_at=p.updated_at,
                created_by_id=str(p.created_by_id) if p.created_by_id else None,
            )
            for p in profiles
        ],
        total=len(profiles),
    )


@router.get("/profiles/{profile_id}", response_model=LLMProfileResponse)
async def get_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Get a specific LLM profile by ID."""
    router_service = LLMRouter(db)
    profile = await router_service.get_profile(profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile {profile_id} not found",
        )

    return LLMProfileResponse(
        id=str(profile.id),
        tenant_id=str(profile.tenant_id) if profile.tenant_id else None,
        profile_key=profile.profile_key,
        label=profile.label,
        description=profile.description,
        model=profile.model,
        temperature=profile.temperature,
        max_tokens=profile.max_tokens,
        top_p=profile.top_p,
        frequency_penalty=profile.frequency_penalty,
        presence_penalty=profile.presence_penalty,
        cost_per_1k_input_tokens=profile.cost_per_1k_input_tokens,
        cost_per_1k_output_tokens=profile.cost_per_1k_output_tokens,
        fallback_models=profile.fallback_models,
        rate_limit_rpm=profile.rate_limit_rpm,
        rate_limit_tpm=profile.rate_limit_tpm,
        cache_enabled=profile.cache_enabled,
        cache_ttl_seconds=profile.cache_ttl_seconds,
        system_prompt_template=profile.system_prompt_template,
        priority=profile.priority,
        is_active=profile.is_active,
        is_default=profile.is_default,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        created_by_id=str(profile.created_by_id) if profile.created_by_id else None,
    )


@router.post("/profiles", response_model=LLMProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    data: LLMProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Create a new LLM profile.

    Admin-only endpoint to create a new LLM profile configuration.
    If tenant_id is not provided, creates a global profile.
    """
    router_service = LLMRouter(db)
    profile = await router_service.create_profile(
        profile_key=data.profile_key,
        label=data.label,
        model=data.model,
        tenant_id=data.tenant_id,
        created_by_id=str(current_user.id),
        description=data.description,
        temperature=data.temperature,
        max_tokens=data.max_tokens,
        top_p=data.top_p,
        frequency_penalty=data.frequency_penalty,
        presence_penalty=data.presence_penalty,
        cost_per_1k_input_tokens=data.cost_per_1k_input_tokens,
        cost_per_1k_output_tokens=data.cost_per_1k_output_tokens,
        fallback_models=data.fallback_models,
        rate_limit_rpm=data.rate_limit_rpm,
        rate_limit_tpm=data.rate_limit_tpm,
        cache_enabled=data.cache_enabled,
        cache_ttl_seconds=data.cache_ttl_seconds,
        system_prompt_template=data.system_prompt_template,
        priority=data.priority,
        is_default=data.is_default,
    )

    return LLMProfileResponse(
        id=str(profile.id),
        tenant_id=str(profile.tenant_id) if profile.tenant_id else None,
        profile_key=profile.profile_key,
        label=profile.label,
        description=profile.description,
        model=profile.model,
        temperature=profile.temperature,
        max_tokens=profile.max_tokens,
        top_p=profile.top_p,
        frequency_penalty=profile.frequency_penalty,
        presence_penalty=profile.presence_penalty,
        cost_per_1k_input_tokens=profile.cost_per_1k_input_tokens,
        cost_per_1k_output_tokens=profile.cost_per_1k_output_tokens,
        fallback_models=profile.fallback_models,
        rate_limit_rpm=profile.rate_limit_rpm,
        rate_limit_tpm=profile.rate_limit_tpm,
        cache_enabled=profile.cache_enabled,
        cache_ttl_seconds=profile.cache_ttl_seconds,
        system_prompt_template=profile.system_prompt_template,
        priority=profile.priority,
        is_active=profile.is_active,
        is_default=profile.is_default,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        created_by_id=str(profile.created_by_id) if profile.created_by_id else None,
    )


@router.patch("/profiles/{profile_id}", response_model=LLMProfileResponse)
async def update_profile(
    profile_id: str,
    data: LLMProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Update an existing LLM profile."""
    router_service = LLMRouter(db)

    # Only pass fields that were explicitly set
    update_data = data.model_dump(exclude_unset=True)

    profile = await router_service.update_profile(profile_id, **update_data)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile {profile_id} not found",
        )

    return LLMProfileResponse(
        id=str(profile.id),
        tenant_id=str(profile.tenant_id) if profile.tenant_id else None,
        profile_key=profile.profile_key,
        label=profile.label,
        description=profile.description,
        model=profile.model,
        temperature=profile.temperature,
        max_tokens=profile.max_tokens,
        top_p=profile.top_p,
        frequency_penalty=profile.frequency_penalty,
        presence_penalty=profile.presence_penalty,
        cost_per_1k_input_tokens=profile.cost_per_1k_input_tokens,
        cost_per_1k_output_tokens=profile.cost_per_1k_output_tokens,
        fallback_models=profile.fallback_models,
        rate_limit_rpm=profile.rate_limit_rpm,
        rate_limit_tpm=profile.rate_limit_tpm,
        cache_enabled=profile.cache_enabled,
        cache_ttl_seconds=profile.cache_ttl_seconds,
        system_prompt_template=profile.system_prompt_template,
        priority=profile.priority,
        is_active=profile.is_active,
        is_default=profile.is_default,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        created_by_id=str(profile.created_by_id) if profile.created_by_id else None,
    )


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Delete (deactivate) an LLM profile.

    This performs a soft delete by marking the profile as inactive.
    """
    router_service = LLMRouter(db)
    success = await router_service.delete_profile(profile_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile {profile_id} not found",
        )


# =============================================================================
# Call Log Endpoints
# =============================================================================

@router.get("/calls", response_model=LLMCallListResponse)
async def list_calls(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    profile_key: Optional[str] = Query(None, description="Filter by profile key"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    List LLM call logs.

    Admin-only endpoint to view LLM call history for debugging
    and cost tracking.
    """
    import uuid

    conditions = []
    if tenant_id:
        conditions.append(LLMCall.tenant_id == uuid.UUID(tenant_id))
    if project_id:
        conditions.append(LLMCall.project_id == uuid.UUID(project_id))
    if profile_key:
        conditions.append(LLMCall.profile_key == profile_key)
    if status_filter:
        conditions.append(LLMCall.status == status_filter)
    if start_date:
        conditions.append(LLMCall.created_at >= start_date)
    if end_date:
        conditions.append(LLMCall.created_at <= end_date)

    # Count total
    count_stmt = select(func.count(LLMCall.id))
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    stmt = select(LLMCall).order_by(LLMCall.created_at.desc()).offset(offset).limit(page_size)
    if conditions:
        stmt = stmt.where(*conditions)
    result = await db.execute(stmt)
    calls = list(result.scalars().all())

    return LLMCallListResponse(
        calls=[
            LLMCallResponse(
                id=str(c.id),
                tenant_id=str(c.tenant_id) if c.tenant_id else None,
                profile_key=c.profile_key,
                project_id=str(c.project_id) if c.project_id else None,
                run_id=str(c.run_id) if c.run_id else None,
                model_requested=c.model_requested,
                model_used=c.model_used,
                input_tokens=c.input_tokens,
                output_tokens=c.output_tokens,
                total_tokens=c.total_tokens,
                response_time_ms=c.response_time_ms,
                cost_usd=c.cost_usd,
                status=c.status,
                cache_hit=c.cache_hit,
                fallback_attempts=c.fallback_attempts,
                created_at=c.created_at,
            )
            for c in calls
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Cost Reporting Endpoints
# =============================================================================

@router.get("/costs/summary", response_model=LLMCostSummary)
async def get_cost_summary(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, all"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Get LLM cost summary.

    Admin-only endpoint to view aggregated cost metrics.
    """
    router_service = LLMRouter(db)

    # Calculate date range
    start_date = None
    if period == "7d":
        start_date = datetime.utcnow() - timedelta(days=7)
    elif period == "30d":
        start_date = datetime.utcnow() - timedelta(days=30)
    elif period == "90d":
        start_date = datetime.utcnow() - timedelta(days=90)

    summary = await router_service.get_cost_summary(
        tenant_id=tenant_id,
        project_id=project_id,
        start_date=start_date,
    )

    return LLMCostSummary(**summary)


@router.get("/costs/report", response_model=LLMCostReport)
async def get_cost_report(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, all"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Get comprehensive LLM cost report.

    Admin-only endpoint to view detailed cost breakdown by profile.
    """
    router_service = LLMRouter(db)

    # Calculate date range
    start_date = None
    end_date = datetime.utcnow()
    if period == "7d":
        start_date = datetime.utcnow() - timedelta(days=7)
    elif period == "30d":
        start_date = datetime.utcnow() - timedelta(days=30)
    elif period == "90d":
        start_date = datetime.utcnow() - timedelta(days=90)

    summary = await router_service.get_cost_summary(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    by_profile = await router_service.get_cost_by_profile(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    return LLMCostReport(
        summary=LLMCostSummary(**summary),
        by_profile=[LLMCostByProfile(**p) for p in by_profile],
        period_start=start_date,
        period_end=end_date,
    )


# =============================================================================
# Reference Endpoints
# =============================================================================

@router.get("/profile-keys", response_model=ProfileKeysResponse)
async def list_profile_keys(
    current_user: User = Depends(get_current_admin_user),
):
    """
    List standard profile keys.

    Returns the standard profile keys that should be configured
    for the LLM Router to function properly.
    """
    return ProfileKeysResponse(
        keys=[ProfileKeyInfo(**k) for k in STANDARD_PROFILE_KEYS]
    )


@router.get("/available-models", response_model=AvailableModelsResponse)
async def list_available_models(
    current_user: User = Depends(get_current_admin_user),
):
    """
    List available models from OpenRouter.

    Returns the configured model presets with cost information.
    """
    models = []
    for preset_name, config in AVAILABLE_MODELS.items():
        # Extract provider from model name
        provider = config.model.split("/")[0] if "/" in config.model else "unknown"
        models.append(
            AvailableModel(
                model=config.model,
                provider=provider,
                cost_per_1k_input_tokens=config.cost_per_1k_input_tokens,
                cost_per_1k_output_tokens=config.cost_per_1k_output_tokens,
                max_context_length=128000,  # Default context length
                description=config.description,
            )
        )

    return AvailableModelsResponse(models=models)


@router.post("/test-profile/{profile_key}")
async def test_profile(
    profile_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Test an LLM profile with a simple prompt.

    Admin-only endpoint to verify a profile is working correctly.
    """
    from app.services.llm_router import LLMRouterContext

    router_service = LLMRouter(db)

    try:
        response = await router_service.complete(
            profile_key=profile_key,
            messages=[
                {"role": "user", "content": "Say 'Profile test successful' and nothing else."}
            ],
            context=LLMRouterContext(user_id=str(current_user.id)),
            max_tokens_override=20,
            skip_cache=True,
        )

        return {
            "success": True,
            "response": response.content,
            "model": response.model,
            "tokens": response.total_tokens,
            "response_time_ms": response.response_time_ms,
            "cost_usd": response.cost_usd,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
