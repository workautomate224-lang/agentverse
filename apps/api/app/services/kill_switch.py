"""
Kill Switch Service for Step 4 Production Hardening

Implements:
- Automatic run termination when limits exceeded
- Manual admin kill capability
- Graceful shutdown with state preservation
- Audit logging of all aborts

Kill Triggers:
- max_tokens: Token limit exceeded
- max_llm_calls: LLM call limit exceeded
- max_runtime: Wall clock time exceeded
- max_cost: Cost limit exceeded
- admin_kill: Admin-initiated termination
- user_cancel: User-initiated cancellation

Integration Points:
- Called by worker after each LLM call
- Called by periodic health check task
- Admin endpoint for manual kills
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from enum import Enum
import asyncio

import redis.asyncio as redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.quota_service import QuotaService
from app.models.quota import RunAbortLog

logger = logging.getLogger(__name__)


class KillReason(str, Enum):
    """Reasons for killing a run."""
    MAX_TOKENS = "max_tokens"
    MAX_LLM_CALLS = "max_llm_calls"
    MAX_RUNTIME = "max_runtime"
    MAX_COST = "max_cost"
    ADMIN_KILL = "admin_kill"
    USER_CANCEL = "user_cancel"
    SYSTEM_ERROR = "system_error"


class KillSwitchService:
    """
    Service for monitoring and terminating runs that exceed limits.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.quota_service = QuotaService(db)
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> Optional[redis.Redis]:
        """Lazy-load Redis connection."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(settings.REDIS_URL)
                await self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis unavailable for kill switch: {e}")
                self._redis = None
        return self._redis

    async def check_and_kill_if_needed(
        self,
        run_id: UUID,
        user_id: UUID
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Check if a run should be killed and kill it if so.
        Called after each LLM call or step.

        Returns:
            (should_continue, kill_reason, details)
            - should_continue: True if run can continue, False if killed
            - kill_reason: Reason for kill if killed
            - details: Additional details about the kill
        """
        # Check if already marked for kill
        r = await self._get_redis()
        if r:
            kill_flag = await r.get(f"kill:run:{run_id}")
            if kill_flag:
                reason = kill_flag.decode() if isinstance(kill_flag, bytes) else str(kill_flag)
                return False, reason, {"source": "kill_flag"}

        # Check quota limits
        within_limits, violation, details = await self.quota_service.check_run_limits(
            run_id=run_id,
            user_id=user_id
        )

        if not within_limits:
            # Kill the run
            await self.kill_run(
                run_id=run_id,
                user_id=user_id,
                reason=KillReason(violation),
                message=f"Run exceeded {violation} limit",
                triggered_by="system"
            )
            return False, violation, details

        return True, None, None

    async def kill_run(
        self,
        run_id: UUID,
        user_id: UUID,
        reason: KillReason,
        message: str,
        triggered_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Kill a running simulation.

        Args:
            run_id: ID of the run to kill
            user_id: User who owns the run
            reason: Reason for killing
            message: Human-readable message
            triggered_by: Who triggered the kill (system, admin, user)

        Returns:
            Kill result details
        """
        logger.warning(
            f"KILL_RUN: run_id={run_id}, reason={reason}, triggered_by={triggered_by}"
        )

        result = {
            "run_id": str(run_id),
            "reason": reason.value,
            "message": message,
            "triggered_by": triggered_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": False
        }

        try:
            # Set kill flag in Redis (workers check this)
            r = await self._get_redis()
            if r:
                await r.set(
                    f"kill:run:{run_id}",
                    reason.value,
                    ex=3600  # 1 hour TTL
                )

            # Log the abort to database
            await self.quota_service.log_run_abort(
                run_id=run_id,
                user_id=user_id,
                reason=reason.value,
                message=message,
                triggered_by=triggered_by
            )

            # Update run status in database
            # Note: This assumes a Run model with a status field
            try:
                from app.models.node import Run, RunStatus
                stmt = (
                    update(Run)
                    .where(Run.id == run_id)
                    .values(
                        status=RunStatus.FAILED,
                        error_message=f"Run killed: {message}",
                        ended_at=datetime.now(timezone.utc)
                    )
                )
                await self.db.execute(stmt)
                await self.db.commit()
            except ImportError:
                # If models not available, log and continue
                logger.warning("Run model not available for status update")

            # Revoke Celery task if possible
            try:
                from celery.result import AsyncResult
                from app.core.celery_app import celery_app

                # Get task ID from Redis
                if r:
                    task_id = await r.get(f"run:{run_id}:task_id")
                    if task_id:
                        task_id = task_id.decode() if isinstance(task_id, bytes) else str(task_id)
                        celery_app.control.revoke(task_id, terminate=True)
                        result["task_revoked"] = True
            except Exception as e:
                logger.warning(f"Could not revoke Celery task: {e}")

            result["success"] = True

        except Exception as e:
            logger.error(f"Error killing run {run_id}: {e}")
            result["error"] = str(e)

        return result

    async def admin_kill_run(
        self,
        run_id: UUID,
        admin_id: UUID,
        reason: str = "Admin intervention"
    ) -> Dict[str, Any]:
        """
        Admin-initiated kill of a run.
        """
        # Get run info to find user_id
        try:
            from app.models.node import Run
            result = await self.db.execute(
                select(Run.user_id).where(Run.id == run_id)
            )
            user_id = result.scalar_one_or_none()
            if not user_id:
                return {
                    "success": False,
                    "error": "Run not found"
                }
        except Exception as e:
            logger.error(f"Error finding run owner: {e}")
            return {
                "success": False,
                "error": str(e)
            }

        return await self.kill_run(
            run_id=run_id,
            user_id=user_id,
            reason=KillReason.ADMIN_KILL,
            message=reason,
            triggered_by=f"admin:{admin_id}"
        )

    async def user_cancel_run(
        self,
        run_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        User-initiated cancellation of a run.
        """
        return await self.kill_run(
            run_id=run_id,
            user_id=user_id,
            reason=KillReason.USER_CANCEL,
            message="User cancelled the run",
            triggered_by="user"
        )

    async def is_run_killed(self, run_id: UUID) -> Tuple[bool, Optional[str]]:
        """
        Check if a run has been killed.

        Returns:
            (is_killed, reason)
        """
        r = await self._get_redis()
        if not r:
            return False, None

        kill_flag = await r.get(f"kill:run:{run_id}")
        if kill_flag:
            reason = kill_flag.decode() if isinstance(kill_flag, bytes) else str(kill_flag)
            return True, reason

        return False, None

    async def get_kill_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get kill statistics for monitoring.
        """
        try:
            from sqlalchemy import func
            from datetime import timedelta

            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

            # Count by reason
            result = await self.db.execute(
                select(
                    RunAbortLog.abort_reason,
                    func.count(RunAbortLog.id)
                )
                .where(RunAbortLog.created_at >= cutoff)
                .group_by(RunAbortLog.abort_reason)
            )
            by_reason = {row[0]: row[1] for row in result.fetchall()}

            # Count by trigger
            result = await self.db.execute(
                select(
                    RunAbortLog.triggered_by,
                    func.count(RunAbortLog.id)
                )
                .where(RunAbortLog.created_at >= cutoff)
                .group_by(RunAbortLog.triggered_by)
            )
            by_trigger = {row[0]: row[1] for row in result.fetchall()}

            # Total
            result = await self.db.execute(
                select(func.count(RunAbortLog.id))
                .where(RunAbortLog.created_at >= cutoff)
            )
            total = result.scalar() or 0

            return {
                "period_hours": hours,
                "total_kills": total,
                "by_reason": by_reason,
                "by_trigger": by_trigger,
            }

        except Exception as e:
            logger.error(f"Error getting kill stats: {e}")
            return {
                "period_hours": hours,
                "total_kills": 0,
                "error": str(e)
            }

    async def clear_kill_flag(self, run_id: UUID) -> bool:
        """
        Clear kill flag for a run (for cleanup or retry).
        """
        r = await self._get_redis()
        if r:
            await r.delete(f"kill:run:{run_id}")
            return True
        return False


class KillSwitchGuard:
    """
    Context manager for checking kill switch during long operations.
    Use this to wrap operations that should be killable.
    """

    def __init__(
        self,
        db: AsyncSession,
        run_id: UUID,
        user_id: UUID,
        check_interval: float = 1.0
    ):
        self.service = KillSwitchService(db)
        self.run_id = run_id
        self.user_id = user_id
        self.check_interval = check_interval
        self._killed = False
        self._kill_reason = None

    async def check(self) -> bool:
        """
        Check if run should continue.
        Returns False if run was killed.
        """
        if self._killed:
            return False

        should_continue, reason, _ = await self.service.check_and_kill_if_needed(
            run_id=self.run_id,
            user_id=self.user_id
        )

        if not should_continue:
            self._killed = True
            self._kill_reason = reason

        return should_continue

    @property
    def killed(self) -> bool:
        return self._killed

    @property
    def kill_reason(self) -> Optional[str]:
        return self._kill_reason

    async def raise_if_killed(self) -> None:
        """Raise exception if run was killed."""
        if self._killed:
            raise RunKilledException(
                run_id=self.run_id,
                reason=self._kill_reason
            )


class RunKilledException(Exception):
    """Raised when a run is killed during execution."""

    def __init__(self, run_id: UUID, reason: Optional[str] = None):
        self.run_id = run_id
        self.reason = reason
        super().__init__(f"Run {run_id} was killed: {reason}")
