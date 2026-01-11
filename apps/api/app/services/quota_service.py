"""
Quota Enforcement Service for Step 4 Production Hardening

Handles:
- Quota checking at API level
- Usage tracking in Redis (fast) + Postgres (audit)
- Tier-based limit enforcement
- Admin override support
- Structured error responses

Redis Key Scheme:
- quota:user:{user_id}:runs_created:{YYYYMMDD}
- quota:user:{user_id}:steps_executed:{YYYYMMDD}
- quota:user:{user_id}:exports:{YYYYMMDD}
- quota:project:{project_id}:runs_created:{YYYYMMDD}
- quota:run:{run_id}:steps
- quota:run:{run_id}:llm_calls
- quota:run:{run_id}:tokens
- quota:run:{run_id}:cost_usd
- quota:run:{run_id}:start_time
"""

import logging
from datetime import datetime, timezone, date
from typing import Optional, Tuple, Dict, Any
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.quota import QuotaPolicy, UsageEvent, UsageDailyRollup, RunAbortLog, UserTier
from app.models.user import User

logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    """Raised when a quota limit is exceeded."""

    def __init__(
        self,
        error_code: str,
        limit: int,
        used: int,
        reset_at: str,
        message: str = "Quota exceeded"
    ):
        self.error_code = error_code
        self.limit = limit
        self.used = used
        self.reset_at = reset_at
        self.message = message
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": "quota_exceeded",
            "error_code": self.error_code,
            "limit": self.limit,
            "used": self.used,
            "reset_at": self.reset_at,
            "message": self.message
        }


# Default quota policies per tier (used if not in DB)
DEFAULT_POLICIES = {
    UserTier.FREE.value: {
        "max_runs_per_user_per_day": 5,
        "max_steps_per_user_per_day": 500,
        "max_exports_per_user_per_day": 10,
        "max_runs_per_project_per_day": 10,
        "max_steps_per_run": 50,
        "max_agents_per_run": 100,
        "max_llm_calls_per_run": 100,
        "max_tokens_per_run": 50000,
        "max_wall_clock_seconds": 120,
        "max_cost_usd_per_run": 0.50,
        "max_concurrent_runs": 1,
        "force_full_rep": True,
    },
    UserTier.ALPHA.value: {
        "max_runs_per_user_per_day": 20,
        "max_steps_per_user_per_day": 2000,
        "max_exports_per_user_per_day": 50,
        "max_runs_per_project_per_day": 50,
        "max_steps_per_run": 100,
        "max_agents_per_run": 500,
        "max_llm_calls_per_run": 500,
        "max_tokens_per_run": 200000,
        "max_wall_clock_seconds": 300,
        "max_cost_usd_per_run": 2.0,
        "max_concurrent_runs": 3,
        "force_full_rep": True,
    },
    UserTier.TEAM.value: {
        "max_runs_per_user_per_day": 100,
        "max_steps_per_user_per_day": 10000,
        "max_exports_per_user_per_day": 200,
        "max_runs_per_project_per_day": 200,
        "max_steps_per_run": 500,
        "max_agents_per_run": 5000,
        "max_llm_calls_per_run": 2000,
        "max_tokens_per_run": 1000000,
        "max_wall_clock_seconds": 600,
        "max_cost_usd_per_run": 10.0,
        "max_concurrent_runs": 10,
        "force_full_rep": True,
    },
    UserTier.ENTERPRISE.value: {
        "max_runs_per_user_per_day": 1000,
        "max_steps_per_user_per_day": 100000,
        "max_exports_per_user_per_day": 1000,
        "max_runs_per_project_per_day": 1000,
        "max_steps_per_run": 1000,
        "max_agents_per_run": 100000,
        "max_llm_calls_per_run": 10000,
        "max_tokens_per_run": 10000000,
        "max_wall_clock_seconds": 3600,
        "max_cost_usd_per_run": 100.0,
        "max_concurrent_runs": 50,
        "force_full_rep": True,
    },
}


class QuotaService:
    """
    Service for quota checking and enforcement.
    Uses Redis for fast counters and Postgres for audit.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> Optional[redis.Redis]:
        """Lazy-load Redis connection."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(settings.REDIS_URL)
                await self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis unavailable for quota tracking: {e}")
                self._redis = None
        return self._redis

    def _get_date_key(self) -> str:
        """Get current date key for daily quotas."""
        return datetime.now(timezone.utc).strftime("%Y%m%d")

    def _get_reset_at(self) -> str:
        """Get reset time (midnight UTC tomorrow)."""
        tomorrow = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        tomorrow = tomorrow.replace(day=tomorrow.day + 1)
        return tomorrow.isoformat()

    async def get_policy(self, tier: str) -> Dict[str, Any]:
        """
        Get quota policy for a tier.
        First checks DB, falls back to defaults.
        """
        # Try to get from DB
        try:
            result = await self.db.execute(
                select(QuotaPolicy).where(QuotaPolicy.tier == tier)
            )
            policy = result.scalar_one_or_none()

            if policy:
                return {
                    "max_runs_per_user_per_day": policy.max_runs_per_user_per_day,
                    "max_steps_per_user_per_day": policy.max_steps_per_user_per_day,
                    "max_exports_per_user_per_day": policy.max_exports_per_user_per_day,
                    "max_runs_per_project_per_day": policy.max_runs_per_project_per_day,
                    "max_steps_per_run": policy.max_steps_per_run,
                    "max_agents_per_run": policy.max_agents_per_run,
                    "max_llm_calls_per_run": policy.max_llm_calls_per_run,
                    "max_tokens_per_run": policy.max_tokens_per_run,
                    "max_wall_clock_seconds": policy.max_wall_clock_seconds,
                    "max_cost_usd_per_run": policy.max_cost_usd_per_run,
                    "max_concurrent_runs": policy.max_concurrent_runs,
                    "force_full_rep": policy.force_full_rep,
                }
        except Exception as e:
            logger.warning(f"Error fetching policy from DB: {e}")

        # Fall back to defaults
        return DEFAULT_POLICIES.get(tier, DEFAULT_POLICIES[UserTier.FREE.value])

    async def get_user_tier(self, user_id: UUID) -> str:
        """Get user's tier from DB."""
        try:
            result = await self.db.execute(
                select(User.tier).where(User.id == user_id)
            )
            tier = result.scalar_one_or_none()
            return tier or UserTier.FREE.value
        except Exception:
            return UserTier.FREE.value

    async def is_admin(self, user_id: UUID) -> bool:
        """Check if user is admin (admin override)."""
        try:
            result = await self.db.execute(
                select(User.role).where(User.id == user_id)
            )
            role = result.scalar_one_or_none()
            return role == "admin"
        except Exception:
            return False

    async def check_user_daily_runs(
        self,
        user_id: UUID,
        admin_override: bool = False
    ) -> Tuple[bool, int, int]:
        """
        Check if user can create another run today.
        Returns (allowed, used, limit).
        """
        if admin_override:
            return True, 0, 999999

        tier = await self.get_user_tier(user_id)
        policy = await self.get_policy(tier)
        limit = policy["max_runs_per_user_per_day"]

        r = await self._get_redis()
        if not r:
            return True, 0, limit  # Allow if Redis unavailable

        key = f"quota:user:{user_id}:runs_created:{self._get_date_key()}"
        used = int(await r.get(key) or 0)

        return used < limit, used, limit

    async def check_project_daily_runs(
        self,
        project_id: UUID,
        user_id: UUID,
        admin_override: bool = False
    ) -> Tuple[bool, int, int]:
        """
        Check if project can have another run today.
        Returns (allowed, used, limit).
        """
        if admin_override:
            return True, 0, 999999

        tier = await self.get_user_tier(user_id)
        policy = await self.get_policy(tier)
        limit = policy["max_runs_per_project_per_day"]

        r = await self._get_redis()
        if not r:
            return True, 0, limit

        key = f"quota:project:{project_id}:runs_created:{self._get_date_key()}"
        used = int(await r.get(key) or 0)

        return used < limit, used, limit

    async def check_run_limits(
        self,
        run_id: UUID,
        user_id: UUID,
        check_type: str = "all"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Check if a run has exceeded any limits.
        Returns (within_limits, violation_type, details).

        check_type: "all", "tokens", "llm_calls", "runtime", "cost"
        """
        tier = await self.get_user_tier(user_id)
        policy = await self.get_policy(tier)

        r = await self._get_redis()
        if not r:
            return True, "", {}

        run_key_prefix = f"quota:run:{run_id}"

        # Get current values
        pipe = r.pipeline()
        pipe.get(f"{run_key_prefix}:tokens")
        pipe.get(f"{run_key_prefix}:llm_calls")
        pipe.get(f"{run_key_prefix}:cost_usd")
        pipe.get(f"{run_key_prefix}:start_time")
        results = await pipe.execute()

        tokens = int(results[0] or 0)
        llm_calls = int(results[1] or 0)
        cost_usd = float(results[2] or 0)
        start_time = float(results[3] or 0)

        runtime = 0
        if start_time > 0:
            runtime = int(datetime.now(timezone.utc).timestamp() - start_time)

        details = {
            "tokens": tokens,
            "llm_calls": llm_calls,
            "cost_usd": cost_usd,
            "runtime_seconds": runtime,
            "limits": {
                "max_tokens": policy["max_tokens_per_run"],
                "max_llm_calls": policy["max_llm_calls_per_run"],
                "max_cost_usd": policy["max_cost_usd_per_run"],
                "max_runtime": policy["max_wall_clock_seconds"],
            }
        }

        # Check limits
        if check_type in ("all", "tokens") and tokens >= policy["max_tokens_per_run"]:
            return False, "max_tokens", details

        if check_type in ("all", "llm_calls") and llm_calls >= policy["max_llm_calls_per_run"]:
            return False, "max_llm_calls", details

        if check_type in ("all", "cost") and cost_usd >= policy["max_cost_usd_per_run"]:
            return False, "max_cost_usd", details

        if check_type in ("all", "runtime") and runtime >= policy["max_wall_clock_seconds"]:
            return False, "max_runtime", details

        return True, "", details

    async def increment_user_runs(self, user_id: UUID) -> None:
        """Increment user's daily run count."""
        r = await self._get_redis()
        if not r:
            return

        key = f"quota:user:{user_id}:runs_created:{self._get_date_key()}"
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, 86400 * 2)  # 2 days TTL
        await pipe.execute()

    async def increment_project_runs(self, project_id: UUID) -> None:
        """Increment project's daily run count."""
        r = await self._get_redis()
        if not r:
            return

        key = f"quota:project:{project_id}:runs_created:{self._get_date_key()}"
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, 86400 * 2)
        await pipe.execute()

    async def init_run_tracking(self, run_id: UUID) -> None:
        """Initialize run tracking counters."""
        r = await self._get_redis()
        if not r:
            return

        prefix = f"quota:run:{run_id}"
        now = datetime.now(timezone.utc).timestamp()

        pipe = r.pipeline()
        pipe.set(f"{prefix}:tokens", 0)
        pipe.set(f"{prefix}:llm_calls", 0)
        pipe.set(f"{prefix}:cost_usd", 0)
        pipe.set(f"{prefix}:steps", 0)
        pipe.set(f"{prefix}:start_time", now)
        # Set TTL of 24 hours for run tracking keys
        for key in ["tokens", "llm_calls", "cost_usd", "steps", "start_time"]:
            pipe.expire(f"{prefix}:{key}", 86400)
        await pipe.execute()

    async def increment_run_counters(
        self,
        run_id: UUID,
        tokens: int = 0,
        llm_calls: int = 0,
        cost_usd: float = 0,
        steps: int = 0
    ) -> None:
        """Increment run counters."""
        r = await self._get_redis()
        if not r:
            return

        prefix = f"quota:run:{run_id}"
        pipe = r.pipeline()

        if tokens > 0:
            pipe.incrbyfloat(f"{prefix}:tokens", tokens)
        if llm_calls > 0:
            pipe.incr(f"{prefix}:llm_calls", llm_calls)
        if cost_usd > 0:
            pipe.incrbyfloat(f"{prefix}:cost_usd", cost_usd)
        if steps > 0:
            pipe.incr(f"{prefix}:steps", steps)

        await pipe.execute()

    async def get_run_stats(self, run_id: UUID) -> Dict[str, Any]:
        """Get current run statistics."""
        r = await self._get_redis()
        if not r:
            return {}

        prefix = f"quota:run:{run_id}"
        pipe = r.pipeline()
        pipe.get(f"{prefix}:tokens")
        pipe.get(f"{prefix}:llm_calls")
        pipe.get(f"{prefix}:cost_usd")
        pipe.get(f"{prefix}:steps")
        pipe.get(f"{prefix}:start_time")
        results = await pipe.execute()

        start_time = float(results[4] or 0)
        runtime = 0
        if start_time > 0:
            runtime = int(datetime.now(timezone.utc).timestamp() - start_time)

        return {
            "tokens": int(float(results[0] or 0)),
            "llm_calls": int(results[1] or 0),
            "cost_usd": float(results[2] or 0),
            "steps": int(results[3] or 0),
            "runtime_seconds": runtime,
        }

    async def log_usage_event(
        self,
        user_id: UUID,
        event_type: str,
        project_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a usage event to the database."""
        try:
            event = UsageEvent(
                user_id=user_id,
                project_id=project_id,
                run_id=run_id,
                event_type=event_type,
                event_data=event_data or {}
            )
            self.db.add(event)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log usage event: {e}")

    async def log_run_abort(
        self,
        run_id: UUID,
        user_id: UUID,
        reason: str,
        message: str,
        triggered_by: str = "system"
    ) -> None:
        """Log a run abort to the database."""
        try:
            stats = await self.get_run_stats(run_id)

            abort_log = RunAbortLog(
                run_id=run_id,
                user_id=user_id,
                abort_reason=reason,
                abort_message=message,
                tokens_at_abort=stats.get("tokens", 0),
                llm_calls_at_abort=stats.get("llm_calls", 0),
                runtime_at_abort=stats.get("runtime_seconds", 0),
                cost_at_abort=stats.get("cost_usd", 0),
                triggered_by=triggered_by
            )
            self.db.add(abort_log)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log run abort: {e}")

    async def check_and_enforce_quota(
        self,
        user_id: UUID,
        project_id: UUID,
        quota_type: str,
        admin_override: bool = False
    ) -> None:
        """
        Check quota and raise QuotaExceededError if exceeded.
        Used as pre-flight check before operations.
        """
        if admin_override or await self.is_admin(user_id):
            return

        if quota_type == "run_create":
            # Check user daily runs
            allowed, used, limit = await self.check_user_daily_runs(user_id)
            if not allowed:
                raise QuotaExceededError(
                    error_code="USER_DAILY_RUNS_EXCEEDED",
                    limit=limit,
                    used=used,
                    reset_at=self._get_reset_at(),
                    message=f"You have reached your daily run limit of {limit} runs"
                )

            # Check project daily runs
            allowed, used, limit = await self.check_project_daily_runs(
                project_id, user_id
            )
            if not allowed:
                raise QuotaExceededError(
                    error_code="PROJECT_DAILY_RUNS_EXCEEDED",
                    limit=limit,
                    used=used,
                    reset_at=self._get_reset_at(),
                    message=f"This project has reached its daily run limit of {limit} runs"
                )

    async def get_user_usage_summary(self, user_id: UUID) -> Dict[str, Any]:
        """Get usage summary for a user."""
        tier = await self.get_user_tier(user_id)
        policy = await self.get_policy(tier)

        r = await self._get_redis()
        date_key = self._get_date_key()

        if r:
            pipe = r.pipeline()
            pipe.get(f"quota:user:{user_id}:runs_created:{date_key}")
            pipe.get(f"quota:user:{user_id}:steps_executed:{date_key}")
            pipe.get(f"quota:user:{user_id}:exports:{date_key}")
            results = await pipe.execute()

            runs_today = int(results[0] or 0)
            steps_today = int(results[1] or 0)
            exports_today = int(results[2] or 0)
        else:
            runs_today = 0
            steps_today = 0
            exports_today = 0

        return {
            "tier": tier,
            "usage": {
                "runs_today": runs_today,
                "steps_today": steps_today,
                "exports_today": exports_today,
            },
            "limits": {
                "max_runs_per_day": policy["max_runs_per_user_per_day"],
                "max_steps_per_day": policy["max_steps_per_user_per_day"],
                "max_exports_per_day": policy["max_exports_per_user_per_day"],
            },
            "reset_at": self._get_reset_at(),
        }
