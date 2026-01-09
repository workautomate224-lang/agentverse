"""
Middleware Package
Reference: project.md §8

Provides:
- TenantMiddleware: Multi-tenancy isolation
- RateLimitMiddleware: Request throttling
- QuotaManager: Job quota enforcement
"""

from app.middleware.tenant import (
    TenantMiddleware,
    TenantContext,
    get_tenant_context,
    get_current_tenant_id,
    get_current_user_id,
    require_tenant,
    TenantScopedSession,
)

from app.middleware.rate_limit import (
    RateLimitMiddleware,
    RateLimiter,
    RateLimitConfig,
    RateLimitScope,
    get_rate_limiter,
    QuotaManager,
    TenantQuota,
    QuotaUsage,
    get_quota_manager,
    require_run_quota,
)

__all__ = [
    # Tenant
    "TenantMiddleware",
    "TenantContext",
    "get_tenant_context",
    "get_current_tenant_id",
    "get_current_user_id",
    "require_tenant",
    "TenantScopedSession",
    # Rate limiting
    "RateLimitMiddleware",
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitScope",
    "get_rate_limiter",
    # Quotas
    "QuotaManager",
    "TenantQuota",
    "QuotaUsage",
    "get_quota_manager",
    "require_run_quota",
]
