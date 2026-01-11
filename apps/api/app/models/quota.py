"""
Quota and Usage Tracking Models for Step 4 Production Hardening

Tables:
- quota_policy: Tier-based quota limits
- usage_daily_rollup: Daily usage aggregation for audit
- usage_events: Individual usage events (high-volume)
- alpha_whitelist: Whitelist for internal alpha users
- run_estimates: Pre-run cost estimates

Redis Key Scheme (documented as required):
- quota:user:{user_id}:runs_created:{date} - Daily run count per user
- quota:user:{user_id}:steps_executed:{date} - Daily steps per user
- quota:user:{user_id}:exports:{date} - Daily exports per user
- quota:project:{project_id}:runs_created:{date} - Daily runs per project
- quota:run:{run_id}:steps - Step count for a run
- quota:run:{run_id}:llm_calls - LLM call count for a run
- quota:run:{run_id}:tokens - Token count for a run
- quota:run:{run_id}:start_time - Run start timestamp
- quota:run:{run_id}:cost_usd - Accumulated cost for a run
- rate_limit:ip:{ip}:{endpoint} - Rate limit by IP
- rate_limit:user:{user_id}:{endpoint} - Rate limit by user
"""

from datetime import datetime, date
from typing import Optional
from uuid import uuid4
from enum import Enum

from sqlalchemy import Boolean, DateTime, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class UserTier(str, Enum):
    """User tier levels."""
    FREE = "free"
    ALPHA = "alpha"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class QuotaPolicy(Base):
    """
    Quota policy definitions per tier.
    Defines limits that apply to users of each tier.
    """
    __tablename__ = "quota_policies"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tier: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )  # free, alpha, team, enterprise

    # Per user per day limits
    max_runs_per_user_per_day: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_steps_per_user_per_day: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    max_exports_per_user_per_day: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    # Per project per day limits
    max_runs_per_project_per_day: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    # Per run hard caps
    max_steps_per_run: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    max_agents_per_run: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    max_llm_calls_per_run: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    max_tokens_per_run: Mapped[int] = mapped_column(Integer, default=100000, nullable=False)
    max_wall_clock_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    max_cost_usd_per_run: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Concurrent limits
    max_concurrent_runs: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Feature flags
    force_full_rep: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<QuotaPolicy tier={self.tier}>"


class UsageDailyRollup(Base):
    """
    Daily usage aggregation for audit purposes.
    Rolled up from Redis counters at end of day.
    """
    __tablename__ = "usage_daily_rollups"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    rollup_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Usage counts
    runs_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    steps_executed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exports_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint('user_id', 'rollup_date', name='uq_usage_user_date'),
    )

    def __repr__(self) -> str:
        return f"<UsageDailyRollup user={self.user_id} date={self.rollup_date}>"


class UsageEvent(Base):
    """
    Individual usage events for detailed tracking.
    High-volume table - consider partitioning in production.
    """
    __tablename__ = "usage_events"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    project_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    run_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # Event type
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # run_created, step_executed, llm_call, export, quota_exceeded

    # Event data
    event_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<UsageEvent {self.event_type} user={self.user_id}>"


class AlphaWhitelist(Base):
    """
    Whitelist for internal alpha users.
    Only whitelisted users can create runs in alpha phase.
    """
    __tablename__ = "alpha_whitelist"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, unique=True
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    added_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<AlphaWhitelist email={self.email}>"


class RunEstimate(Base):
    """
    Pre-run cost estimates.
    Logged when a run starts for audit trail.
    """
    __tablename__ = "run_estimates"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    run_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Estimates
    estimated_llm_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_tokens_min: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_tokens_max: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost_usd_min: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_cost_usd_max: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_runtime_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_rep_outputs: Mapped[int] = mapped_column(Integer, nullable=False)

    # Policy thresholds used
    policy_tier: Mapped[str] = mapped_column(String(50), nullable=False)
    policy_thresholds: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<RunEstimate run={self.run_id}>"


class RunAbortLog(Base):
    """
    Log of run aborts/kills for audit.
    Records when and why a run was stopped.
    """
    __tablename__ = "run_abort_logs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    run_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    # Abort details
    abort_reason: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # max_tokens, max_llm_calls, max_runtime, max_cost, admin_kill, user_cancel
    abort_message: Mapped[str] = mapped_column(Text, nullable=False)

    # State at abort
    tokens_at_abort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_calls_at_abort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    runtime_at_abort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_at_abort: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Who triggered
    triggered_by: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # system, admin, user

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<RunAbortLog run={self.run_id} reason={self.abort_reason}>"
