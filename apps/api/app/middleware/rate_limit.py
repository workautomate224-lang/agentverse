"""
Rate Limiting Middleware
Reference: project.md §8 (Security), C6 (rate limits mandatory)

Implements:
- Per-tenant rate limiting
- Per-endpoint rate limiting
- Job quota enforcement
- Sliding window algorithm
"""

import time
from dataclasses import dataclass
from typing import Callable, Optional
from enum import Enum

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.middleware.tenant import get_tenant_context


class RateLimitScope(str, Enum):
    """Rate limit scopes."""
    GLOBAL = "global"  # Per tenant, all endpoints
    ENDPOINT = "endpoint"  # Per tenant, per endpoint
    USER = "user"  # Per user


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit."""
    requests: int  # Max requests
    window_seconds: int  # Time window
    scope: RateLimitScope = RateLimitScope.ENDPOINT


# Default rate limits by endpoint pattern
DEFAULT_RATE_LIMITS = {
    # Run execution (expensive)
    "/api/v1/runs": RateLimitConfig(requests=10, window_seconds=60),
    "/api/v1/runs/*/execute": RateLimitConfig(requests=5, window_seconds=60),

    # Node expansion (expensive)
    "/api/v1/nodes/*/expand": RateLimitConfig(requests=20, window_seconds=60),

    # General API
    "/api/v1/projects": RateLimitConfig(requests=100, window_seconds=60),
    "/api/v1/personas": RateLimitConfig(requests=100, window_seconds=60),

    # Auth (prevent brute force)
    "/api/v1/auth/login": RateLimitConfig(requests=10, window_seconds=300),
    "/api/v1/auth/register": RateLimitConfig(requests=5, window_seconds=300),

    # Default for all other endpoints
    "*": RateLimitConfig(
        requests=settings.RATE_LIMIT_PER_MINUTE,
        window_seconds=60
    ),
}


class RateLimiter:
    """
    Sliding window rate limiter using Redis.
    Falls back to in-memory if Redis unavailable.
    """

    def __init__(self):
        self._local_store: dict[str, list[float]] = {}
        self._redis = None

    async def _get_redis(self):
        """Lazy-load Redis client."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(settings.REDIS_URL)
            except Exception:
                self._redis = False  # Mark as unavailable
        return self._redis if self._redis else None

    async def check_rate_limit(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.

        Returns:
            (allowed, remaining, reset_time)
        """
        redis = await self._get_redis()

        if redis:
            return await self._check_redis(redis, key, config)
        else:
            return self._check_local(key, config)

    async def _check_redis(
        self,
        redis,
        key: str,
        config: RateLimitConfig,
    ) -> tuple[bool, int, int]:
        """Check rate limit using Redis."""
        now = time.time()
        window_start = now - config.window_seconds

        pipe = redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current entries
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Set expiry
        pipe.expire(key, config.window_seconds)

        results = await pipe.execute()
        current_count = results[1]

        allowed = current_count < config.requests
        remaining = max(0, config.requests - current_count - 1)
        reset_time = int(now + config.window_seconds)

        return allowed, remaining, reset_time

    def _check_local(
        self,
        key: str,
        config: RateLimitConfig,
    ) -> tuple[bool, int, int]:
        """Check rate limit using local memory (fallback)."""
        now = time.time()
        window_start = now - config.window_seconds

        # Get or create entry
        if key not in self._local_store:
            self._local_store[key] = []

        # Remove old entries
        self._local_store[key] = [
            ts for ts in self._local_store[key]
            if ts > window_start
        ]

        current_count = len(self._local_store[key])
        allowed = current_count < config.requests

        if allowed:
            self._local_store[key].append(now)

        remaining = max(0, config.requests - current_count - 1)
        reset_time = int(now + config.window_seconds)

        return allowed, remaining, reset_time


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    Applies rate limits based on tenant and endpoint.
    """

    # Paths exempt from rate limiting
    EXEMPT_PATHS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Apply rate limiting."""
        path = request.url.path

        # Skip exempt paths
        if path in self.EXEMPT_PATHS or path.startswith("/static"):
            return await call_next(request)

        # Get tenant context
        ctx = get_tenant_context()
        if not ctx:
            # No tenant = public endpoint, use IP-based limiting
            client_ip = request.client.host if request.client else "unknown"
            tenant_key = f"ip:{client_ip}"
        else:
            tenant_key = f"tenant:{ctx.tenant_id}"

        # Get rate limit config
        config = self._get_config(path)

        # Build rate limit key
        rate_key = f"rate_limit:{tenant_key}:{path}"

        # Check limit
        limiter = get_rate_limiter()
        allowed, remaining, reset_time = await limiter.check_rate_limit(
            rate_key, config
        )

        if not allowed:
            return Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "X-RateLimit-Limit": str(config.requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(config.window_seconds),
                    "Content-Type": "application/json",
                },
            )

        # Continue with request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(config.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_config(self, path: str) -> RateLimitConfig:
        """Get rate limit config for path."""
        # Check exact match
        if path in DEFAULT_RATE_LIMITS:
            return DEFAULT_RATE_LIMITS[path]

        # Check pattern match (simple wildcard)
        for pattern, config in DEFAULT_RATE_LIMITS.items():
            if pattern == "*":
                continue
            if self._match_pattern(pattern, path):
                return config

        # Return default
        return DEFAULT_RATE_LIMITS["*"]

    def _match_pattern(self, pattern: str, path: str) -> bool:
        """Simple wildcard pattern matching."""
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")

        if len(pattern_parts) != len(path_parts):
            return False

        for p, v in zip(pattern_parts, path_parts):
            if p == "*":
                continue
            if p != v:
                return False

        return True


# =============================================================================
# Job Quota Management
# =============================================================================

@dataclass
class TenantQuota:
    """Quota configuration for a tenant."""
    max_agents: int = settings.MAX_AGENTS_FREE
    max_runs_per_day: int = 100
    max_concurrent_runs: int = 5
    max_storage_mb: int = 1024


@dataclass
class QuotaUsage:
    """Current usage for a tenant."""
    agents_count: int = 0
    runs_today: int = 0
    concurrent_runs: int = 0
    storage_mb: float = 0


class QuotaManager:
    """
    Manages job quotas per tenant.
    Reference: project.md C6 (job quotas mandatory)
    """

    def __init__(self):
        self._redis = None

    async def _get_redis(self):
        """Lazy-load Redis client."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(settings.REDIS_URL)
            except Exception:
                self._redis = False
        return self._redis if self._redis else None

    async def get_quota(self, tenant_id: str) -> TenantQuota:
        """
        Get quota configuration for tenant.
        TODO: Load from database based on tenant plan.
        """
        # For now, return default quota
        # In production, this would query the tenant's plan
        return TenantQuota()

    async def get_usage(self, tenant_id: str) -> QuotaUsage:
        """Get current usage for tenant."""
        redis = await self._get_redis()

        if not redis:
            return QuotaUsage()

        # Get usage counters from Redis
        try:
            runs_today = await redis.get(f"quota:{tenant_id}:runs_today") or 0
            concurrent = await redis.get(f"quota:{tenant_id}:concurrent_runs") or 0

            return QuotaUsage(
                runs_today=int(runs_today),
                concurrent_runs=int(concurrent),
            )
        except Exception:
            return QuotaUsage()

    async def check_can_start_run(self, tenant_id: str) -> tuple[bool, str]:
        """
        Check if tenant can start a new run.
        Returns (allowed, reason).
        """
        quota = await self.get_quota(tenant_id)
        usage = await self.get_usage(tenant_id)

        if usage.runs_today >= quota.max_runs_per_day:
            return False, f"Daily run limit exceeded ({quota.max_runs_per_day})"

        if usage.concurrent_runs >= quota.max_concurrent_runs:
            return False, f"Max concurrent runs exceeded ({quota.max_concurrent_runs})"

        return True, ""

    async def increment_run_count(self, tenant_id: str) -> None:
        """Increment run counters when a run starts."""
        redis = await self._get_redis()
        if not redis:
            return

        try:
            pipe = redis.pipeline()

            # Increment daily count
            daily_key = f"quota:{tenant_id}:runs_today"
            pipe.incr(daily_key)
            # Set expiry to end of day (simplified: 24h from now)
            pipe.expire(daily_key, 86400)

            # Increment concurrent count
            concurrent_key = f"quota:{tenant_id}:concurrent_runs"
            pipe.incr(concurrent_key)

            await pipe.execute()
        except Exception:
            pass

    async def decrement_concurrent_runs(self, tenant_id: str) -> None:
        """Decrement concurrent run counter when a run completes."""
        redis = await self._get_redis()
        if not redis:
            return

        try:
            concurrent_key = f"quota:{tenant_id}:concurrent_runs"
            await redis.decr(concurrent_key)
        except Exception:
            pass


# Global quota manager instance
_quota_manager: Optional[QuotaManager] = None


def get_quota_manager() -> QuotaManager:
    """Get quota manager singleton."""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = QuotaManager()
    return _quota_manager


async def require_run_quota(tenant_id: str) -> None:
    """
    Require that tenant has quota to start a run.
    Raises HTTPException if quota exceeded.
    """
    manager = get_quota_manager()
    allowed, reason = await manager.check_can_start_run(tenant_id)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Quota exceeded: {reason}",
        )
