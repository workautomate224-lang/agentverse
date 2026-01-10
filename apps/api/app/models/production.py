"""
STEP 10: Production Readiness Models

This module provides infrastructure for:
1. Cost Tracking (per Run/Plan/Project)
2. Budgets and Quotas (enforceable limits)
3. Feature Flags / Plan Tiers
4. Safety Guardrails (risk classification)
5. Export Integrity (checksums/hashes)

All models support multi-tenancy (C6) and full auditability (C4).
"""

import hashlib
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# =============================================================================
# Enums
# =============================================================================

class PlanTier(str, Enum):
    """Subscription plan tiers."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class QuotaType(str, Enum):
    """Types of quotas that can be enforced."""
    DAILY_RUNS = "daily_runs"
    MONTHLY_RUNS = "monthly_runs"
    CONCURRENT_RUNS = "concurrent_runs"
    DAILY_PLANNING = "daily_planning"
    MONTHLY_PLANNING = "monthly_planning"
    ENSEMBLE_SIZE = "ensemble_size"
    MAX_AGENTS = "max_agents"
    MAX_TICKS = "max_ticks"
    STORAGE_MB = "storage_mb"
    LLM_TOKENS_DAILY = "llm_tokens_daily"
    LLM_TOKENS_MONTHLY = "llm_tokens_monthly"


class QuotaAction(str, Enum):
    """Action to take when quota is exceeded."""
    BLOCK = "block"              # Hard block, reject request
    DEGRADE = "degrade"          # Continue with degraded settings
    WARN = "warn"                # Allow but warn
    LOG_ONLY = "log_only"        # Just log, don't restrict


class RiskLevel(str, Enum):
    """Risk classification levels for safety guardrails."""
    SAFE = "safe"                # No concerns
    LOW = "low"                  # Minor concerns, proceed with logging
    MEDIUM = "medium"            # Needs review, may be degraded
    HIGH = "high"                # Blocked or requires approval
    CRITICAL = "critical"        # Always blocked


class SafetyAction(str, Enum):
    """Action taken by safety guardrails."""
    ALLOWED = "allowed"          # Request allowed
    LOGGED = "logged"            # Allowed with logging
    DEGRADED = "degraded"        # Allowed with reduced capabilities
    BLOCKED = "blocked"          # Request blocked
    REQUIRES_APPROVAL = "requires_approval"  # Needs human review


class GovernanceActionType(str, Enum):
    """Types of governance audit actions."""
    # Project lifecycle
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"
    PROJECT_ARCHIVED = "project_archived"

    # Persona lifecycle
    PERSONAS_SNAPSHOT_CREATED = "personas_snapshot_created"
    PERSONAS_SNAPSHOT_MODIFIED = "personas_snapshot_modified"
    PERSONAS_IMPORTED = "personas_imported"

    # Node lifecycle
    NODE_FORKED = "node_forked"
    NODE_PATCH_APPLIED = "node_patch_applied"
    NODE_PRUNED = "node_pruned"
    NODE_ANNOTATED = "node_annotated"

    # Event lifecycle
    EVENT_CREATED = "event_created"
    EVENT_APPLIED = "event_applied"
    EVENT_REMOVED = "event_removed"
    EVENT_VALIDATED = "event_validated"

    # Run lifecycle
    RUN_CREATED = "run_created"
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"

    # Planning lifecycle
    PLANNING_CREATED = "planning_created"
    PLANNING_STARTED = "planning_started"
    PLANNING_COMPLETED = "planning_completed"
    PLAN_EVALUATED = "plan_evaluated"

    # Calibration/reliability
    CALIBRATION_RUN = "calibration_run"
    AUTOTUNE_APPLIED = "autotune_applied"
    DRIFT_DETECTED = "drift_detected"
    RELIABILITY_COMPUTED = "reliability_computed"

    # Export
    EXPORT_GENERATED = "export_generated"
    EXPORT_DOWNLOADED = "export_downloaded"

    # Quota/billing
    QUOTA_EXCEEDED = "quota_exceeded"
    QUOTA_WARNING = "quota_warning"
    TIER_CHANGED = "tier_changed"

    # Safety
    SAFETY_BLOCKED = "safety_blocked"
    SAFETY_DEGRADED = "safety_degraded"


# =============================================================================
# Cost Tracking Models (STEP 10 Requirement 1)
# =============================================================================

class RunCostRecord(Base):
    """
    STEP 10: Cost record for a single simulation run.

    Aggregates all costs associated with a run:
    - LLM token usage (prompt + completion)
    - Compute time / worker time
    - Ensemble count
    - Queue latency

    Every run MUST have a cost record (STEP 10 requirement).
    """
    __tablename__ = "run_cost_records"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="STEP 10: Every run must have exactly one cost record"
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # LLM Token Usage
    llm_input_tokens: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False,
        comment="Total prompt tokens used"
    )
    llm_output_tokens: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False,
        comment="Total completion tokens used"
    )
    llm_total_tokens: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False,
        comment="Total tokens (input + output)"
    )
    llm_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), default=Decimal("0.0"), nullable=False,
        comment="Total LLM cost in USD"
    )
    llm_call_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Number of LLM calls made"
    )

    # Compute Time
    compute_time_ms: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False,
        comment="Total compute time in milliseconds"
    )
    worker_time_ms: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False,
        comment="Time spent in worker execution"
    )
    queue_latency_ms: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False,
        comment="Time spent waiting in queue"
    )

    # Ensemble tracking
    ensemble_index: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Index in ensemble (0, 1, 2, ...)"
    )
    ensemble_size: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False,
        comment="Total ensemble size for this node"
    )

    # Simulation specifics
    tick_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Number of ticks executed"
    )
    agent_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Number of agents in simulation"
    )

    # Total cost (computed)
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), default=Decimal("0.0"), nullable=False,
        comment="Total cost including compute (LLM + estimated compute)"
    )

    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<RunCostRecord run={self.run_id} cost=${self.total_cost_usd}>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": str(self.run_id),
            "llm_input_tokens": self.llm_input_tokens,
            "llm_output_tokens": self.llm_output_tokens,
            "llm_total_tokens": self.llm_total_tokens,
            "llm_cost_usd": float(self.llm_cost_usd),
            "llm_call_count": self.llm_call_count,
            "compute_time_ms": self.compute_time_ms,
            "worker_time_ms": self.worker_time_ms,
            "queue_latency_ms": self.queue_latency_ms,
            "ensemble_index": self.ensemble_index,
            "ensemble_size": self.ensemble_size,
            "tick_count": self.tick_count,
            "agent_count": self.agent_count,
            "total_cost_usd": float(self.total_cost_usd),
        }


class PlanningCostRecord(Base):
    """
    STEP 10: Cost record for a planning operation.

    Aggregates costs across all plan evaluations.
    """
    __tablename__ = "planning_cost_records"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    planning_spec_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planning_specs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # LLM costs (for plan generation/evaluation)
    llm_input_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    llm_output_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    llm_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0.0"), nullable=False)

    # Evaluation costs (simulations run for plan evaluation)
    evaluation_run_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Number of simulation runs for evaluation"
    )
    evaluation_run_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), default=Decimal("0.0"), nullable=False,
        comment="Total cost of evaluation runs"
    )

    # Candidates
    candidates_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidates_evaluated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidates_pruned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timing
    total_time_ms: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Total
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0.0"), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<PlanningCostRecord planning={self.planning_spec_id} cost=${self.total_cost_usd}>"


class ProjectCostSummary(Base):
    """
    STEP 10: Aggregated cost summary per project per period.

    Updated periodically (hourly/daily) to provide cost dashboards.
    """
    __tablename__ = "project_cost_summaries"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Period
    period_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="hourly, daily, weekly, monthly"
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Run costs
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    run_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0.0"), nullable=False)

    # Planning costs
    planning_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    planning_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0.0"), nullable=False)

    # LLM costs (subset)
    llm_tokens_total: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    llm_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0.0"), nullable=False)

    # Totals
    total_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0.0"), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint('project_id', 'period_type', 'period_start', name='uq_project_cost_period'),
        Index('ix_project_cost_tenant_period', 'tenant_id', 'period_type', 'period_start'),
    )


# =============================================================================
# Budgets and Quotas (STEP 10 Requirement 2)
# =============================================================================

class TenantQuotaConfig(Base):
    """
    STEP 10: Database-backed quota configuration per tenant.

    Quotas are enforceable limits that block or degrade execution when exceeded.
    Server-side enforcement is REQUIRED (not UI-only).
    """
    __tablename__ = "tenant_quota_configs"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Plan tier (determines default limits)
    plan_tier: Mapped[str] = mapped_column(
        String(50), default=PlanTier.FREE.value, nullable=False,
        comment="STEP 10: Plan tier determines default quotas"
    )

    # Run limits
    daily_run_limit: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False,
        comment="Max runs per day"
    )
    monthly_run_limit: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False,
        comment="Max runs per month"
    )
    concurrent_run_limit: Mapped[int] = mapped_column(
        Integer, default=2, nullable=False,
        comment="Max concurrent runs"
    )

    # Planning limits
    daily_planning_limit: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False,
        comment="Max planning operations per day"
    )
    planning_evaluation_budget: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False,
        comment="Max evaluation runs per planning operation"
    )

    # Simulation limits
    max_ensemble_size: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False,
        comment="Max ensemble size per node"
    )
    max_agents_per_run: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False,
        comment="Max agents per simulation"
    )
    max_ticks_per_run: Mapped[int] = mapped_column(
        Integer, default=1000, nullable=False,
        comment="Max ticks per simulation"
    )

    # Token limits
    daily_llm_token_limit: Mapped[int] = mapped_column(
        BigInteger, default=100000, nullable=False,
        comment="Max LLM tokens per day"
    )
    monthly_llm_token_limit: Mapped[int] = mapped_column(
        BigInteger, default=1000000, nullable=False,
        comment="Max LLM tokens per month"
    )

    # Storage
    storage_limit_mb: Mapped[int] = mapped_column(
        Integer, default=1024, nullable=False,
        comment="Storage quota in MB"
    )

    # Cost limits
    daily_cost_limit_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True,
        comment="Optional daily cost limit"
    )
    monthly_cost_limit_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True,
        comment="Optional monthly cost limit"
    )

    # Enforcement action
    exceeded_action: Mapped[str] = mapped_column(
        String(20), default=QuotaAction.BLOCK.value, nullable=False,
        comment="Action when quota exceeded: block, degrade, warn, log_only"
    )

    # Active status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint('tenant_id', name='uq_tenant_quota_tenant'),
    )

    def __repr__(self) -> str:
        return f"<TenantQuotaConfig tenant={self.tenant_id} tier={self.plan_tier}>"


class QuotaUsageRecord(Base):
    """
    STEP 10: Tracks current quota usage per tenant per period.

    Updated in real-time as resources are consumed.
    Server-side enforcement checks this table.
    """
    __tablename__ = "quota_usage_records"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Period
    period_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="daily, monthly"
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Usage counters
    runs_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    concurrent_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    planning_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_tokens_used: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    storage_used_mb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_used_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0.0"), nullable=False)

    # Timestamps
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint('tenant_id', 'period_type', 'period_start', name='uq_quota_usage_period'),
        Index('ix_quota_usage_tenant_period', 'tenant_id', 'period_type', 'period_start'),
    )


class QuotaViolation(Base):
    """
    STEP 10: Log of quota violations for audit and alerting.

    Records every time a quota limit is hit.
    """
    __tablename__ = "quota_violations"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Violation details
    quota_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Type of quota violated"
    )
    limit_value: Mapped[int] = mapped_column(
        BigInteger, nullable=False,
        comment="The limit that was exceeded"
    )
    current_value: Mapped[int] = mapped_column(
        BigInteger, nullable=False,
        comment="Current usage when violation occurred"
    )
    requested_value: Mapped[int] = mapped_column(
        BigInteger, nullable=False,
        comment="What was requested"
    )

    # Action taken
    action_taken: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Action taken: block, degrade, warn"
    )

    # Request context
    request_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Type of request that triggered violation"
    )
    request_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="ID of the blocked/degraded request"
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )


# =============================================================================
# Feature Flags / Plan Tiers (STEP 10 Requirement 3)
# =============================================================================

class FeatureFlag(Base):
    """
    STEP 10: Feature flag definitions.

    Server-side feature gating (not UI-only).
    Users cannot bypass gates via API.
    """
    __tablename__ = "feature_flags"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Flag identification
    flag_key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True,
        comment="Unique identifier for the feature flag"
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Default state
    is_enabled_by_default: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Tier-based access (JSON array of tiers that have access)
    enabled_tiers: Mapped[List[str]] = mapped_column(
        ARRAY(String(50)), nullable=False, default=list,
        comment="List of plan tiers that have access to this feature"
    )

    # Percentage rollout (0-100)
    rollout_percentage: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False,
        comment="Percentage of eligible users who see this feature"
    )

    # Override settings
    allow_tenant_override: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
        comment="Whether tenant-specific overrides are allowed"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<FeatureFlag {self.flag_key}>"


class TenantFeatureOverride(Base):
    """
    STEP 10: Tenant-specific feature flag overrides.

    Allows enabling/disabling features for specific tenants.
    """
    __tablename__ = "tenant_feature_overrides"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    feature_flag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("feature_flags.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Override
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Optional expiration for temporary overrides"
    )

    __table_args__ = (
        UniqueConstraint('tenant_id', 'feature_flag_id', name='uq_tenant_feature_override'),
    )


# Standard feature flag keys
class FeatureFlagKey(str, Enum):
    """Standard feature flag keys for STEP 10."""
    # Ensemble features
    ENSEMBLE_LARGE = "ensemble_large"           # ensemble_size > 5
    ENSEMBLE_UNLIMITED = "ensemble_unlimited"   # unlimited ensemble

    # Calibration features
    CALIBRATION_BASIC = "calibration_basic"
    CALIBRATION_ADVANCED = "calibration_advanced"
    AUTOTUNE = "autotune"

    # Replay features
    REPLAY_BASIC = "replay_basic"
    REPLAY_FULL_TELEMETRY = "replay_full_telemetry"
    REPLAY_EXPORT = "replay_export"

    # Export features
    EXPORT_JSON = "export_json"
    EXPORT_CSV = "export_csv"
    EXPORT_FULL_BUNDLE = "export_full_bundle"

    # Planning features
    PLANNING_BASIC = "planning_basic"
    PLANNING_DEEP = "planning_deep"             # depth > 3
    PLANNING_UNLIMITED = "planning_unlimited"

    # Safety/compliance
    SAFETY_OVERRIDE = "safety_override"         # Enterprise only


# =============================================================================
# Safety Guardrails (STEP 10 Requirement 5)
# =============================================================================

class SafetyRule(Base):
    """
    STEP 10: Safety rules for risk classification.

    High-risk requests are blocked or downgraded.
    """
    __tablename__ = "safety_rules"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Rule identification
    rule_key: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Rule configuration
    risk_level: Mapped[str] = mapped_column(
        String(20), default=RiskLevel.MEDIUM.value, nullable=False
    )
    action_on_match: Mapped[str] = mapped_column(
        String(20), default=SafetyAction.BLOCKED.value, nullable=False
    )

    # Detection patterns (keywords, regex patterns)
    detection_patterns: Mapped[List[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list,
        comment="Patterns to detect (keywords, regex)"
    )
    detection_type: Mapped[str] = mapped_column(
        String(20), default="keyword", nullable=False,
        comment="keyword, regex, semantic"
    )

    # Applies to
    applies_to: Mapped[List[str]] = mapped_column(
        ARRAY(String(50)), nullable=False, default=list,
        comment="Request types this rule applies to: event_prompt, planning_prompt, etc."
    )

    # Active status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class SafetyIncident(Base):
    """
    STEP 10: Log of safety incidents.

    Records risk level and action taken WITHOUT storing sensitive content.
    """
    __tablename__ = "safety_incidents"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Incident details
    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("safety_rules.id", ondelete="SET NULL"),
        nullable=True
    )
    rule_key: Mapped[str] = mapped_column(String(100), nullable=False)

    # Risk assessment (no sensitive content stored)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    action_taken: Mapped[str] = mapped_column(String(20), nullable=False)

    # Request context (sanitized)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    request_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="SHA-256 hash of request for deduplication (no content stored)"
    )

    # Additional context (optional, sanitized)
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
        comment="Sanitized context (no sensitive content)"
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )


# =============================================================================
# Governance Audit Logs (STEP 10 Requirement 6)
# =============================================================================

class GovernanceAuditLog(Base):
    """
    STEP 10: Immutable audit log for governance actions.

    Key requirement: All actions must be traceable with:
    - actor (user_id/org_id)
    - timestamp
    - entity ids
    - spec_hash or version hash
    - action type

    This table is append-only (immutable).
    """
    __tablename__ = "governance_audit_logs"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Actor
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    actor_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="user, system, api_key, scheduler"
    )
    actor_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Action
    action_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="Action type from GovernanceActionType enum"
    )

    # Entity references (at least one must be populated)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    planning_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    event_script_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    persona_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # Version/hash for reproducibility
    spec_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True,
        comment="SHA-256 hash of the spec/config at time of action"
    )
    version: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Version identifier if applicable"
    )

    # Additional details (JSONB for flexibility)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
        comment="Additional action-specific details"
    )

    # Result
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp (immutable)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    __table_args__ = (
        Index('ix_governance_audit_action_time', 'action_type', 'created_at'),
        Index('ix_governance_audit_project_time', 'project_id', 'created_at'),
        Index('ix_governance_audit_user_time', 'user_id', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<GovernanceAuditLog {self.action_type} by {self.actor_type}>"


# =============================================================================
# Export Integrity (STEP 10 Requirement 7)
# =============================================================================

class ExportBundle(Base):
    """
    STEP 10: Export bundle with integrity metadata.

    Every export must include:
    - spec hashes
    - artifact ids
    - checksums for verification
    """
    __tablename__ = "export_bundles"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Export type
    export_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="run, planning, node, project, evidence_pack"
    )

    # Source references
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    node_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    planning_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Artifact IDs included in export
    artifact_ids: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False,
        comment="Map of artifact type to ID: {run_spec_id, run_trace_id, outcome_id, planning_spec_id, plan_trace_id}"
    )

    # Integrity hashes
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="SHA-256 hash of the export content"
    )
    spec_hashes: Mapped[Dict[str, str]] = mapped_column(
        JSONB, nullable=False,
        comment="Map of spec type to hash: {run_config_hash, project_spec_hash, ...}"
    )

    # File info
    file_format: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="json, zip, tar.gz"
    )
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Export metadata
    export_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="1.0.0",
        comment="Export format version for compatibility"
    )
    included_components: Mapped[List[str]] = mapped_column(
        ARRAY(String(50)), nullable=False,
        comment="What's included: config, telemetry, outcomes, traces, etc."
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Optional expiration for temporary exports"
    )
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<ExportBundle {self.export_type} hash={self.content_hash[:8]}>"

    def verify_integrity(self, content: bytes) -> bool:
        """Verify content matches stored hash."""
        computed_hash = hashlib.sha256(content).hexdigest()
        return computed_hash == self.content_hash

    @staticmethod
    def compute_hash(content: bytes) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()


# =============================================================================
# Default Tier Configurations
# =============================================================================

TIER_DEFAULTS = {
    PlanTier.FREE: {
        "daily_run_limit": 10,
        "monthly_run_limit": 100,
        "concurrent_run_limit": 1,
        "daily_planning_limit": 3,
        "planning_evaluation_budget": 5,
        "max_ensemble_size": 2,
        "max_agents_per_run": 50,
        "max_ticks_per_run": 500,
        "daily_llm_token_limit": 50000,
        "monthly_llm_token_limit": 500000,
        "storage_limit_mb": 256,
        "features": [
            FeatureFlagKey.REPLAY_BASIC.value,
            FeatureFlagKey.EXPORT_JSON.value,
        ],
    },
    PlanTier.STARTER: {
        "daily_run_limit": 50,
        "monthly_run_limit": 500,
        "concurrent_run_limit": 3,
        "daily_planning_limit": 10,
        "planning_evaluation_budget": 10,
        "max_ensemble_size": 5,
        "max_agents_per_run": 200,
        "max_ticks_per_run": 1000,
        "daily_llm_token_limit": 200000,
        "monthly_llm_token_limit": 2000000,
        "storage_limit_mb": 1024,
        "features": [
            FeatureFlagKey.REPLAY_BASIC.value,
            FeatureFlagKey.REPLAY_FULL_TELEMETRY.value,
            FeatureFlagKey.EXPORT_JSON.value,
            FeatureFlagKey.EXPORT_CSV.value,
            FeatureFlagKey.CALIBRATION_BASIC.value,
            FeatureFlagKey.PLANNING_BASIC.value,
        ],
    },
    PlanTier.PROFESSIONAL: {
        "daily_run_limit": 200,
        "monthly_run_limit": 2000,
        "concurrent_run_limit": 10,
        "daily_planning_limit": 50,
        "planning_evaluation_budget": 25,
        "max_ensemble_size": 10,
        "max_agents_per_run": 500,
        "max_ticks_per_run": 2000,
        "daily_llm_token_limit": 1000000,
        "monthly_llm_token_limit": 10000000,
        "storage_limit_mb": 10240,
        "features": [
            FeatureFlagKey.REPLAY_BASIC.value,
            FeatureFlagKey.REPLAY_FULL_TELEMETRY.value,
            FeatureFlagKey.REPLAY_EXPORT.value,
            FeatureFlagKey.EXPORT_JSON.value,
            FeatureFlagKey.EXPORT_CSV.value,
            FeatureFlagKey.EXPORT_FULL_BUNDLE.value,
            FeatureFlagKey.CALIBRATION_BASIC.value,
            FeatureFlagKey.CALIBRATION_ADVANCED.value,
            FeatureFlagKey.AUTOTUNE.value,
            FeatureFlagKey.PLANNING_BASIC.value,
            FeatureFlagKey.PLANNING_DEEP.value,
            FeatureFlagKey.ENSEMBLE_LARGE.value,
        ],
    },
    PlanTier.ENTERPRISE: {
        "daily_run_limit": -1,  # Unlimited
        "monthly_run_limit": -1,
        "concurrent_run_limit": 50,
        "daily_planning_limit": -1,
        "planning_evaluation_budget": 100,
        "max_ensemble_size": -1,
        "max_agents_per_run": -1,
        "max_ticks_per_run": -1,
        "daily_llm_token_limit": -1,
        "monthly_llm_token_limit": -1,
        "storage_limit_mb": -1,
        "features": "all",  # All features enabled
    },
}
