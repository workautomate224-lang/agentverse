"""
STEP 10: Production Readiness Services

This module provides server-side enforcement for:
1. Cost Tracking - Record and aggregate costs per run/plan/project
2. Quota Enforcement - Block or degrade when limits exceeded (server-side)
3. Feature Flag Checking - Tier-based gating (server-side, not UI-only)
4. Safety Guardrails - Risk classification and blocking
5. Governance Audit - Immutable audit logging
6. Export Integrity - Checksum generation and verification

All services enforce multi-tenancy (C6) and provide full auditability (C4).
"""

import hashlib
import json
import re
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.production import (
    PlanTier,
    QuotaType,
    QuotaAction,
    RiskLevel,
    SafetyAction,
    GovernanceActionType,
    FeatureFlagKey,
    RunCostRecord,
    PlanningCostRecord,
    ProjectCostSummary,
    TenantQuotaConfig,
    QuotaUsageRecord,
    QuotaViolation,
    FeatureFlag,
    TenantFeatureOverride,
    SafetyRule,
    SafetyIncident,
    GovernanceAuditLog,
    ExportBundle,
    TIER_DEFAULTS,
)


# =============================================================================
# Cost Tracking Service (STEP 10 Requirement 1)
# =============================================================================

class CostTrackingService:
    """
    STEP 10: Service for recording and tracking costs.

    Every run MUST have a cost record. Costs are tracked for:
    - LLM token usage (prompt + completion)
    - Compute time / worker time
    - Queue latency
    - Ensemble runs
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_run_cost_record(
        self,
        tenant_id: uuid.UUID,
        run_id: uuid.UUID,
        project_id: uuid.UUID,
        node_id: Optional[uuid.UUID] = None,
    ) -> RunCostRecord:
        """Create a cost record for a run. Called when run is created."""
        record = RunCostRecord(
            tenant_id=tenant_id,
            run_id=run_id,
            project_id=project_id,
            node_id=node_id,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def update_run_cost(
        self,
        run_id: uuid.UUID,
        llm_input_tokens: int = 0,
        llm_output_tokens: int = 0,
        llm_cost_usd: Decimal = Decimal("0"),
        llm_call_count: int = 0,
        compute_time_ms: int = 0,
        worker_time_ms: int = 0,
        queue_latency_ms: int = 0,
        tick_count: int = 0,
        agent_count: int = 0,
        ensemble_index: int = 0,
        ensemble_size: int = 1,
    ) -> Optional[RunCostRecord]:
        """Update cost record with actual costs after run completes."""
        result = await self.db.execute(
            select(RunCostRecord).where(RunCostRecord.run_id == run_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            return None

        # Update LLM costs
        record.llm_input_tokens += llm_input_tokens
        record.llm_output_tokens += llm_output_tokens
        record.llm_total_tokens = record.llm_input_tokens + record.llm_output_tokens
        record.llm_cost_usd += llm_cost_usd
        record.llm_call_count += llm_call_count

        # Update compute costs
        record.compute_time_ms = compute_time_ms
        record.worker_time_ms = worker_time_ms
        record.queue_latency_ms = queue_latency_ms

        # Update simulation specifics
        record.tick_count = tick_count
        record.agent_count = agent_count
        record.ensemble_index = ensemble_index
        record.ensemble_size = ensemble_size

        # Calculate total cost (LLM + estimated compute)
        compute_cost = Decimal(compute_time_ms) / Decimal(3600000) * Decimal("0.10")  # $0.10/hr
        record.total_cost_usd = record.llm_cost_usd + compute_cost

        record.completed_at = datetime.utcnow()
        await self.db.flush()
        return record

    async def get_run_cost(self, run_id: uuid.UUID) -> Optional[RunCostRecord]:
        """Get cost record for a run."""
        result = await self.db.execute(
            select(RunCostRecord).where(RunCostRecord.run_id == run_id)
        )
        return result.scalar_one_or_none()

    async def get_project_costs(
        self,
        project_id: uuid.UUID,
        period_type: str = "daily",
        period_start: Optional[datetime] = None,
    ) -> Optional[ProjectCostSummary]:
        """Get cost summary for a project."""
        if not period_start:
            period_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        result = await self.db.execute(
            select(ProjectCostSummary).where(
                and_(
                    ProjectCostSummary.project_id == project_id,
                    ProjectCostSummary.period_type == period_type,
                    ProjectCostSummary.period_start == period_start,
                )
            )
        )
        return result.scalar_one_or_none()

    async def aggregate_project_costs(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        period_type: str = "daily",
    ) -> ProjectCostSummary:
        """Aggregate costs for a project into a summary record."""
        now = datetime.utcnow()

        if period_type == "daily":
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
        elif period_type == "monthly":
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                period_end = period_start.replace(year=now.year + 1, month=1)
            else:
                period_end = period_start.replace(month=now.month + 1)
        else:
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)

        # Aggregate run costs
        run_result = await self.db.execute(
            select(
                func.count(RunCostRecord.id).label("run_count"),
                func.coalesce(func.sum(RunCostRecord.total_cost_usd), 0).label("run_cost"),
                func.coalesce(func.sum(RunCostRecord.llm_total_tokens), 0).label("tokens"),
                func.coalesce(func.sum(RunCostRecord.llm_cost_usd), 0).label("llm_cost"),
            ).where(
                and_(
                    RunCostRecord.project_id == project_id,
                    RunCostRecord.created_at >= period_start,
                    RunCostRecord.created_at < period_end,
                )
            )
        )
        run_stats = run_result.first()

        # Aggregate planning costs
        planning_result = await self.db.execute(
            select(
                func.count(PlanningCostRecord.id).label("planning_count"),
                func.coalesce(func.sum(PlanningCostRecord.total_cost_usd), 0).label("planning_cost"),
            ).where(
                and_(
                    PlanningCostRecord.project_id == project_id,
                    PlanningCostRecord.created_at >= period_start,
                    PlanningCostRecord.created_at < period_end,
                )
            )
        )
        planning_stats = planning_result.first()

        # Upsert summary
        existing = await self.get_project_costs(project_id, period_type, period_start)
        if existing:
            existing.run_count = run_stats.run_count or 0
            existing.run_cost_usd = Decimal(str(run_stats.run_cost or 0))
            existing.planning_count = planning_stats.planning_count or 0
            existing.planning_cost_usd = Decimal(str(planning_stats.planning_cost or 0))
            existing.llm_tokens_total = run_stats.tokens or 0
            existing.llm_cost_usd = Decimal(str(run_stats.llm_cost or 0))
            existing.total_cost_usd = existing.run_cost_usd + existing.planning_cost_usd
            await self.db.flush()
            return existing
        else:
            summary = ProjectCostSummary(
                tenant_id=tenant_id,
                project_id=project_id,
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
                run_count=run_stats.run_count or 0,
                run_cost_usd=Decimal(str(run_stats.run_cost or 0)),
                planning_count=planning_stats.planning_count or 0,
                planning_cost_usd=Decimal(str(planning_stats.planning_cost or 0)),
                llm_tokens_total=run_stats.tokens or 0,
                llm_cost_usd=Decimal(str(run_stats.llm_cost or 0)),
                total_cost_usd=Decimal(str(run_stats.run_cost or 0)) + Decimal(str(planning_stats.planning_cost or 0)),
            )
            self.db.add(summary)
            await self.db.flush()
            return summary


# =============================================================================
# Quota Enforcement Service (STEP 10 Requirement 2)
# =============================================================================

class QuotaEnforcementService:
    """
    STEP 10: Server-side quota enforcement.

    When quota is exceeded: BLOCK or DEGRADE (with explicit labeling).
    Server-side enforcement is REQUIRED (not UI-only).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tenant_quota_config(
        self,
        tenant_id: uuid.UUID,
    ) -> Optional[TenantQuotaConfig]:
        """Get quota config for a tenant."""
        result = await self.db.execute(
            select(TenantQuotaConfig).where(
                and_(
                    TenantQuotaConfig.tenant_id == tenant_id,
                    TenantQuotaConfig.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_quota_config(
        self,
        tenant_id: uuid.UUID,
        plan_tier: str = PlanTier.FREE.value,
    ) -> TenantQuotaConfig:
        """Get or create quota config for a tenant."""
        config = await self.get_tenant_quota_config(tenant_id)
        if config:
            return config

        # Create from tier defaults
        defaults = TIER_DEFAULTS.get(PlanTier(plan_tier), TIER_DEFAULTS[PlanTier.FREE])
        config = TenantQuotaConfig(
            tenant_id=tenant_id,
            plan_tier=plan_tier,
            daily_run_limit=defaults.get("daily_run_limit", 10),
            monthly_run_limit=defaults.get("monthly_run_limit", 100),
            concurrent_run_limit=defaults.get("concurrent_run_limit", 2),
            daily_planning_limit=defaults.get("daily_planning_limit", 5),
            planning_evaluation_budget=defaults.get("planning_evaluation_budget", 10),
            max_ensemble_size=defaults.get("max_ensemble_size", 3),
            max_agents_per_run=defaults.get("max_agents_per_run", 100),
            max_ticks_per_run=defaults.get("max_ticks_per_run", 1000),
            daily_llm_token_limit=defaults.get("daily_llm_token_limit", 100000),
            monthly_llm_token_limit=defaults.get("monthly_llm_token_limit", 1000000),
            storage_limit_mb=defaults.get("storage_limit_mb", 1024),
        )
        self.db.add(config)
        await self.db.flush()
        return config

    async def get_current_usage(
        self,
        tenant_id: uuid.UUID,
        period_type: str = "daily",
    ) -> QuotaUsageRecord:
        """Get or create current usage record for a tenant."""
        now = datetime.utcnow()
        if period_type == "daily":
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period_type == "monthly":
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        result = await self.db.execute(
            select(QuotaUsageRecord).where(
                and_(
                    QuotaUsageRecord.tenant_id == tenant_id,
                    QuotaUsageRecord.period_type == period_type,
                    QuotaUsageRecord.period_start == period_start,
                )
            )
        )
        usage = result.scalar_one_or_none()

        if not usage:
            usage = QuotaUsageRecord(
                tenant_id=tenant_id,
                period_type=period_type,
                period_start=period_start,
            )
            self.db.add(usage)
            await self.db.flush()

        return usage

    async def check_quota(
        self,
        tenant_id: uuid.UUID,
        quota_type: QuotaType,
        requested: int = 1,
        user_id: Optional[uuid.UUID] = None,
    ) -> Tuple[bool, str, Optional[QuotaViolation]]:
        """
        Check if a quota allows the requested action.

        Returns:
            (allowed: bool, action: str, violation: Optional[QuotaViolation])

        Action can be: "allowed", "blocked", "degraded", "warned"
        """
        config = await self.get_or_create_quota_config(tenant_id)
        daily_usage = await self.get_current_usage(tenant_id, "daily")
        monthly_usage = await self.get_current_usage(tenant_id, "monthly")

        # Determine limit and current value based on quota type
        limit = -1  # -1 means unlimited
        current = 0

        if quota_type == QuotaType.DAILY_RUNS:
            limit = config.daily_run_limit
            current = daily_usage.runs_used
        elif quota_type == QuotaType.MONTHLY_RUNS:
            limit = config.monthly_run_limit
            current = monthly_usage.runs_used
        elif quota_type == QuotaType.CONCURRENT_RUNS:
            limit = config.concurrent_run_limit
            current = daily_usage.concurrent_runs
        elif quota_type == QuotaType.DAILY_PLANNING:
            limit = config.daily_planning_limit
            current = daily_usage.planning_used
        elif quota_type == QuotaType.ENSEMBLE_SIZE:
            limit = config.max_ensemble_size
            current = 0  # Ensemble is checked at request time
        elif quota_type == QuotaType.MAX_AGENTS:
            limit = config.max_agents_per_run
            current = 0
        elif quota_type == QuotaType.MAX_TICKS:
            limit = config.max_ticks_per_run
            current = 0
        elif quota_type == QuotaType.LLM_TOKENS_DAILY:
            limit = config.daily_llm_token_limit
            current = daily_usage.llm_tokens_used
        elif quota_type == QuotaType.LLM_TOKENS_MONTHLY:
            limit = config.monthly_llm_token_limit
            current = monthly_usage.llm_tokens_used

        # Check if within limit (-1 means unlimited)
        if limit == -1:
            return True, "allowed", None

        if current + requested <= limit:
            return True, "allowed", None

        # Quota exceeded - determine action
        exceeded_action = config.exceeded_action

        # Record violation
        violation = QuotaViolation(
            tenant_id=tenant_id,
            user_id=user_id,
            quota_type=quota_type.value,
            limit_value=limit,
            current_value=current,
            requested_value=requested,
            action_taken=exceeded_action,
            request_type=quota_type.value,
        )
        self.db.add(violation)
        await self.db.flush()

        if exceeded_action == QuotaAction.BLOCK.value:
            return False, "blocked", violation
        elif exceeded_action == QuotaAction.DEGRADE.value:
            return True, "degraded", violation
        elif exceeded_action == QuotaAction.WARN.value:
            return True, "warned", violation
        else:  # log_only
            return True, "allowed", violation

    async def increment_usage(
        self,
        tenant_id: uuid.UUID,
        quota_type: QuotaType,
        amount: int = 1,
    ) -> None:
        """Increment usage counter after successful action."""
        daily_usage = await self.get_current_usage(tenant_id, "daily")
        monthly_usage = await self.get_current_usage(tenant_id, "monthly")

        if quota_type in [QuotaType.DAILY_RUNS, QuotaType.MONTHLY_RUNS]:
            daily_usage.runs_used += amount
            monthly_usage.runs_used += amount
        elif quota_type == QuotaType.CONCURRENT_RUNS:
            daily_usage.concurrent_runs += amount
        elif quota_type in [QuotaType.DAILY_PLANNING, QuotaType.MONTHLY_PLANNING]:
            daily_usage.planning_used += amount
        elif quota_type in [QuotaType.LLM_TOKENS_DAILY, QuotaType.LLM_TOKENS_MONTHLY]:
            daily_usage.llm_tokens_used += amount
            monthly_usage.llm_tokens_used += amount

        await self.db.flush()

    async def decrement_concurrent_runs(self, tenant_id: uuid.UUID) -> None:
        """Decrement concurrent run counter when run completes."""
        daily_usage = await self.get_current_usage(tenant_id, "daily")
        if daily_usage.concurrent_runs > 0:
            daily_usage.concurrent_runs -= 1
        await self.db.flush()


# =============================================================================
# Feature Flag Service (STEP 10 Requirement 3)
# =============================================================================

class FeatureFlagService:
    """
    STEP 10: Server-side feature flag checking.

    Tier-based gating with server-side checks (not UI-only).
    Users cannot bypass gates via API.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_feature_flag(self, flag_key: str) -> Optional[FeatureFlag]:
        """Get a feature flag by key."""
        result = await self.db.execute(
            select(FeatureFlag).where(FeatureFlag.flag_key == flag_key)
        )
        return result.scalar_one_or_none()

    async def is_feature_enabled(
        self,
        flag_key: str,
        tenant_id: uuid.UUID,
        plan_tier: str,
    ) -> bool:
        """
        Check if a feature is enabled for a tenant.

        Server-side enforcement - users cannot bypass via API.
        """
        flag = await self.get_feature_flag(flag_key)
        if not flag:
            return False

        # Check for tenant-specific override
        override_result = await self.db.execute(
            select(TenantFeatureOverride).where(
                and_(
                    TenantFeatureOverride.tenant_id == tenant_id,
                    TenantFeatureOverride.feature_flag_id == flag.id,
                    or_(
                        TenantFeatureOverride.expires_at.is_(None),
                        TenantFeatureOverride.expires_at > datetime.utcnow(),
                    ),
                )
            )
        )
        override = override_result.scalar_one_or_none()

        if override and flag.allow_tenant_override:
            return override.is_enabled

        # Check tier-based access
        if plan_tier in flag.enabled_tiers:
            # Check rollout percentage (using tenant_id for consistency)
            if flag.rollout_percentage >= 100:
                return True
            tenant_hash = int(hashlib.md5(str(tenant_id).encode()).hexdigest()[:8], 16)
            return (tenant_hash % 100) < flag.rollout_percentage

        # Check default state
        return flag.is_enabled_by_default

    async def get_tenant_features(
        self,
        tenant_id: uuid.UUID,
        plan_tier: str,
    ) -> Dict[str, bool]:
        """Get all feature flags for a tenant."""
        result = await self.db.execute(select(FeatureFlag))
        flags = result.scalars().all()

        features = {}
        for flag in flags:
            features[flag.flag_key] = await self.is_feature_enabled(
                flag.flag_key, tenant_id, plan_tier
            )
        return features

    async def check_feature_or_fail(
        self,
        flag_key: str,
        tenant_id: uuid.UUID,
        plan_tier: str,
    ) -> None:
        """Check feature access - raises exception if not allowed."""
        if not await self.is_feature_enabled(flag_key, tenant_id, plan_tier):
            raise PermissionError(
                f"Feature '{flag_key}' is not available for plan tier '{plan_tier}'. "
                "Upgrade your plan to access this feature."
            )


# =============================================================================
# Safety Guardrails Service (STEP 10 Requirement 5)
# =============================================================================

class SafetyGuardrailService:
    """
    STEP 10: Safety guardrails for risk classification.

    High-risk requests are blocked or downgraded.
    Records risk level and action taken WITHOUT storing sensitive content.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_rules(
        self,
        request_type: str,
    ) -> List[SafetyRule]:
        """Get active safety rules for a request type."""
        result = await self.db.execute(
            select(SafetyRule).where(
                and_(
                    SafetyRule.is_active == True,
                    SafetyRule.applies_to.contains([request_type]),
                )
            )
        )
        return result.scalars().all()

    async def classify_risk(
        self,
        content: str,
        request_type: str,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> Tuple[RiskLevel, SafetyAction, Optional[SafetyIncident]]:
        """
        Classify risk level and determine action.

        Returns:
            (risk_level, action, incident)

        Does NOT store sensitive content - only hash for deduplication.
        """
        rules = await self.get_active_rules(request_type)

        highest_risk = RiskLevel.SAFE
        action = SafetyAction.ALLOWED
        matched_rule: Optional[SafetyRule] = None

        for rule in rules:
            if self._matches_rule(content, rule):
                rule_risk = RiskLevel(rule.risk_level)
                if self._risk_higher(rule_risk, highest_risk):
                    highest_risk = rule_risk
                    action = SafetyAction(rule.action_on_match)
                    matched_rule = rule

        # Record incident if risk detected
        incident = None
        if highest_risk != RiskLevel.SAFE:
            # Hash content for deduplication (no content stored)
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            incident = SafetyIncident(
                tenant_id=tenant_id,
                user_id=user_id,
                rule_id=matched_rule.id if matched_rule else None,
                rule_key=matched_rule.rule_key if matched_rule else "unknown",
                risk_level=highest_risk.value,
                action_taken=action.value,
                request_type=request_type,
                request_hash=content_hash,
                context={
                    "content_length": len(content),
                    "detected_at": datetime.utcnow().isoformat(),
                },
            )
            self.db.add(incident)
            await self.db.flush()

        return highest_risk, action, incident

    def _matches_rule(self, content: str, rule: SafetyRule) -> bool:
        """Check if content matches a safety rule."""
        content_lower = content.lower()

        for pattern in rule.detection_patterns:
            if rule.detection_type == "keyword":
                if pattern.lower() in content_lower:
                    return True
            elif rule.detection_type == "regex":
                if re.search(pattern, content, re.IGNORECASE):
                    return True

        return False

    def _risk_higher(self, a: RiskLevel, b: RiskLevel) -> bool:
        """Check if risk level a is higher than b."""
        order = [RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        return order.index(a) > order.index(b)

    async def check_or_block(
        self,
        content: str,
        request_type: str,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> Tuple[bool, str]:
        """
        Check content and block if high risk.

        Returns:
            (allowed: bool, message: str)
        """
        risk_level, action, _ = await self.classify_risk(
            content, request_type, tenant_id, user_id
        )

        if action == SafetyAction.BLOCKED:
            return False, f"Request blocked due to safety classification: {risk_level.value}"
        elif action == SafetyAction.DEGRADED:
            return True, f"Request allowed with degraded functionality: {risk_level.value}"
        elif action == SafetyAction.REQUIRES_APPROVAL:
            return False, "Request requires manual approval due to safety concerns"
        else:
            return True, "allowed"


# =============================================================================
# Governance Audit Service (STEP 10 Requirement 6)
# =============================================================================

class GovernanceAuditService:
    """
    STEP 10: Immutable governance audit logging.

    All actions must be traceable with:
    - actor (user_id/org_id)
    - timestamp
    - entity ids
    - spec_hash or version hash
    - action type
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_action(
        self,
        tenant_id: uuid.UUID,
        action_type: GovernanceActionType,
        actor_type: str = "user",
        user_id: Optional[uuid.UUID] = None,
        organization_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        node_id: Optional[uuid.UUID] = None,
        run_id: Optional[uuid.UUID] = None,
        planning_id: Optional[uuid.UUID] = None,
        event_script_id: Optional[uuid.UUID] = None,
        persona_snapshot_id: Optional[uuid.UUID] = None,
        spec_hash: Optional[str] = None,
        version: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        actor_ip: Optional[str] = None,
    ) -> GovernanceAuditLog:
        """
        Log a governance action. This is append-only (immutable).
        """
        log = GovernanceAuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            organization_id=organization_id,
            actor_type=actor_type,
            actor_ip=actor_ip,
            action_type=action_type.value,
            project_id=project_id,
            node_id=node_id,
            run_id=run_id,
            planning_id=planning_id,
            event_script_id=event_script_id,
            persona_snapshot_id=persona_snapshot_id,
            spec_hash=spec_hash,
            version=version,
            details=details,
            success=success,
            error_message=error_message,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def get_project_audit_trail(
        self,
        project_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[GovernanceAuditLog]:
        """Get audit trail for a project."""
        result = await self.db.execute(
            select(GovernanceAuditLog)
            .where(GovernanceAuditLog.project_id == project_id)
            .order_by(GovernanceAuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_user_audit_trail(
        self,
        user_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[GovernanceAuditLog]:
        """Get audit trail for a user."""
        result = await self.db.execute(
            select(GovernanceAuditLog)
            .where(GovernanceAuditLog.user_id == user_id)
            .order_by(GovernanceAuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    @staticmethod
    def compute_spec_hash(spec_data: Dict[str, Any]) -> str:
        """Compute SHA-256 hash of a spec for audit trail."""
        canonical = json.dumps(spec_data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()


# =============================================================================
# Export Integrity Service (STEP 10 Requirement 7)
# =============================================================================

class ExportIntegrityService:
    """
    STEP 10: Export integrity verification.

    Every export must include:
    - spec hashes
    - artifact ids
    - checksums for verification
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_export_bundle(
        self,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        export_type: str,
        content: bytes,
        artifact_ids: Dict[str, str],
        spec_hashes: Dict[str, str],
        file_format: str = "json",
        project_id: Optional[uuid.UUID] = None,
        node_id: Optional[uuid.UUID] = None,
        run_id: Optional[uuid.UUID] = None,
        planning_id: Optional[uuid.UUID] = None,
        included_components: List[str] = None,
        storage_path: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> ExportBundle:
        """Create an export bundle with integrity metadata."""
        content_hash = hashlib.sha256(content).hexdigest()

        bundle = ExportBundle(
            tenant_id=tenant_id,
            user_id=user_id,
            export_type=export_type,
            project_id=project_id,
            node_id=node_id,
            run_id=run_id,
            planning_id=planning_id,
            artifact_ids=artifact_ids,
            content_hash=content_hash,
            spec_hashes=spec_hashes,
            file_format=file_format,
            file_size_bytes=len(content),
            storage_path=storage_path,
            included_components=included_components or [],
            expires_at=expires_at,
        )
        self.db.add(bundle)
        await self.db.flush()
        return bundle

    async def get_export_bundle(
        self,
        bundle_id: uuid.UUID,
    ) -> Optional[ExportBundle]:
        """Get an export bundle by ID."""
        result = await self.db.execute(
            select(ExportBundle).where(ExportBundle.id == bundle_id)
        )
        return result.scalar_one_or_none()

    async def verify_bundle_integrity(
        self,
        bundle_id: uuid.UUID,
        content: bytes,
    ) -> Tuple[bool, str]:
        """
        Verify integrity of export content.

        Returns:
            (valid: bool, message: str)
        """
        bundle = await self.get_export_bundle(bundle_id)
        if not bundle:
            return False, "Export bundle not found"

        computed_hash = hashlib.sha256(content).hexdigest()
        if computed_hash != bundle.content_hash:
            return False, f"Content hash mismatch. Expected: {bundle.content_hash}, Got: {computed_hash}"

        return True, "Integrity verified"

    async def record_download(
        self,
        bundle_id: uuid.UUID,
    ) -> None:
        """Record download event for audit trail."""
        bundle = await self.get_export_bundle(bundle_id)
        if bundle:
            bundle.downloaded_at = datetime.utcnow()
            bundle.download_count += 1
            await self.db.flush()

    @staticmethod
    def compute_content_hash(content: bytes) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def compute_spec_hash(spec_data: Dict[str, Any]) -> str:
        """Compute SHA-256 hash of spec data."""
        canonical = json.dumps(spec_data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()
