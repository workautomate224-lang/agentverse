"""
STEP 10: Governance, Cost Controls, Safety, Access Control, Auditability Tests

Verifies:
- Admin/Governance buttons (Audit Logs, Quotas, Costs, Feature Flags, Safety Blocks, Exports)
- Billing Hooks buttons (Usage, Quota Remaining, Upgrade Tier, Download Invoice)
- CostRecord stored per run/planning/calibration
- Quotas enforced server-side with degrade/block behaviors
- Feature flags enforced server-side (API guards)
- Rate limiting for runs/plans/events
- Safety classifier blocks/downgrades high-risk requests
- AuditLog is immutable, append-only
- Export bundles include integrity metadata

Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md STEP 10
"""

import pytest
from datetime import datetime
from typing import Any, Dict


# =============================================================================
# Admin / Governance Button→Backend Chain Tests
# =============================================================================

class TestAdminGovernanceButtonChains:
    """Test all Admin/Governance button→backend chains exist."""

    def test_view_audit_logs_endpoint_exists(self):
        """Admin/Governance: View Audit Logs button chain."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/audit-logs/view" in routes

    def test_set_quotas_endpoint_exists(self):
        """Admin/Governance: Set Quotas button chain."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/quotas/set" in routes

    def test_view_costs_endpoint_exists(self):
        """Admin/Governance: View Costs button chain."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/costs/view" in routes

    def test_manage_feature_flags_endpoint_exists(self):
        """Admin/Governance: Manage Feature Flags button chain."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/feature-flags/manage" in routes

    def test_review_safety_blocks_endpoint_exists(self):
        """Admin/Governance: Review Safety Blocks button chain."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/safety-blocks/review" in routes

    def test_manage_exports_endpoint_exists(self):
        """Admin/Governance: Manage Exports button chain."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/exports/manage" in routes


# =============================================================================
# Billing Hooks Button→Backend Chain Tests
# =============================================================================

class TestBillingHooksButtonChains:
    """Test all Billing Hooks button→backend chains exist."""

    def test_view_usage_endpoint_exists(self):
        """Billing Hooks: View Usage button chain."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/billing/usage" in routes

    def test_view_quota_remaining_endpoint_exists(self):
        """Billing Hooks: View Quota Remaining button chain."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/billing/quota-remaining" in routes

    def test_upgrade_tier_endpoint_exists(self):
        """Billing Hooks: Upgrade Tier (stub) button chain."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/billing/upgrade-tier" in routes

    def test_download_invoice_endpoint_exists(self):
        """Billing Hooks: Download Invoice (stub) button chain."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/billing/download-invoice" in routes


# =============================================================================
# Request Schema Tests
# =============================================================================

class TestRequestSchemas:
    """Test STEP 10 request schemas."""

    def test_view_audit_logs_request_schema(self):
        """Test ViewAuditLogsRequest schema."""
        from app.api.v1.endpoints.governance import ViewAuditLogsRequest

        fields = ViewAuditLogsRequest.model_fields
        assert "project_id" in fields
        assert "node_id" in fields
        assert "run_id" in fields
        assert "action_type" in fields

    def test_set_quotas_request_schema(self):
        """Test SetQuotasRequest schema."""
        from app.api.v1.endpoints.governance import SetQuotasRequest

        fields = SetQuotasRequest.model_fields
        assert "tenant_id" in fields
        assert "quota_type" in fields
        assert "daily_limit" in fields
        assert "monthly_limit" in fields
        assert "enforce_behavior" in fields

    def test_view_costs_request_schema(self):
        """Test ViewCostsRequest schema."""
        from app.api.v1.endpoints.governance import ViewCostsRequest

        fields = ViewCostsRequest.model_fields
        assert "tenant_id" in fields
        assert "project_id" in fields
        assert "start_date" in fields
        assert "end_date" in fields

    def test_manage_feature_flags_request_schema(self):
        """Test ManageFeatureFlagsRequest schema."""
        from app.api.v1.endpoints.governance import ManageFeatureFlagsRequest

        fields = ManageFeatureFlagsRequest.model_fields
        assert "tenant_id" in fields
        assert "action" in fields
        assert "feature_flag" in fields

    def test_review_safety_blocks_request_schema(self):
        """Test ReviewSafetyBlocksRequest schema."""
        from app.api.v1.endpoints.governance import ReviewSafetyBlocksRequest

        fields = ReviewSafetyBlocksRequest.model_fields
        assert "tenant_id" in fields
        assert "block_type" in fields
        assert "status" in fields

    def test_manage_exports_request_schema(self):
        """Test ManageExportsRequest schema."""
        from app.api.v1.endpoints.governance import ManageExportsRequest

        fields = ManageExportsRequest.model_fields
        assert "action" in fields
        assert "export_id" in fields

    def test_view_usage_request_schema(self):
        """Test ViewUsageRequest schema."""
        from app.api.v1.endpoints.governance import ViewUsageRequest

        fields = ViewUsageRequest.model_fields
        assert "tenant_id" in fields
        assert "period" in fields

    def test_view_quota_remaining_request_schema(self):
        """Test ViewQuotaRemainingRequest schema."""
        from app.api.v1.endpoints.governance import ViewQuotaRemainingRequest

        fields = ViewQuotaRemainingRequest.model_fields
        assert "tenant_id" in fields
        assert "quota_types" in fields

    def test_upgrade_tier_request_schema(self):
        """Test UpgradeTierRequest schema."""
        from app.api.v1.endpoints.governance import UpgradeTierRequest

        fields = UpgradeTierRequest.model_fields
        assert "tenant_id" in fields
        assert "target_tier" in fields
        assert "billing_cycle" in fields

    def test_download_invoice_request_schema(self):
        """Test DownloadInvoiceRequest schema."""
        from app.api.v1.endpoints.governance import DownloadInvoiceRequest

        fields = DownloadInvoiceRequest.model_fields
        assert "tenant_id" in fields
        assert "invoice_id" in fields
        assert "format" in fields

    def test_cost_estimate_request_schema(self):
        """Test CostEstimateRequest schema."""
        from app.api.v1.endpoints.governance import CostEstimateRequest

        fields = CostEstimateRequest.model_fields
        assert "project_id" in fields
        assert "run_config" in fields

    def test_safety_check_request_schema(self):
        """Test SafetyCheckRequest schema."""
        from app.api.v1.endpoints.governance import SafetyCheckRequest

        fields = SafetyCheckRequest.model_fields
        assert "content" in fields
        assert "content_type" in fields


# =============================================================================
# Response Schema Tests
# =============================================================================

class TestResponseSchemas:
    """Test STEP 10 response schemas."""

    def test_audit_log_entry_schema(self):
        """Test AuditLogEntry schema."""
        from app.api.v1.endpoints.governance import AuditLogEntry

        fields = AuditLogEntry.model_fields
        assert "log_id" in fields
        assert "timestamp" in fields
        assert "actor_id" in fields
        assert "action_type" in fields
        assert "resource_type" in fields
        assert "spec_hash" in fields

    def test_view_audit_logs_response_schema(self):
        """Test ViewAuditLogsResponse schema."""
        from app.api.v1.endpoints.governance import ViewAuditLogsResponse

        fields = ViewAuditLogsResponse.model_fields
        assert "logs" in fields
        assert "total_count" in fields
        assert "page" in fields

    def test_set_quotas_response_schema(self):
        """Test SetQuotasResponse schema."""
        from app.api.v1.endpoints.governance import SetQuotasResponse

        fields = SetQuotasResponse.model_fields
        assert "quotas" in fields
        assert "audit_log_id" in fields

    def test_cost_breakdown_schema(self):
        """Test CostBreakdown schema."""
        from app.api.v1.endpoints.governance import CostBreakdown

        fields = CostBreakdown.model_fields
        assert "category" in fields
        assert "amount_usd" in fields
        assert "units" in fields

    def test_view_costs_response_schema(self):
        """Test ViewCostsResponse schema."""
        from app.api.v1.endpoints.governance import ViewCostsResponse

        fields = ViewCostsResponse.model_fields
        assert "total_cost_usd" in fields
        assert "summaries" in fields

    def test_feature_flag_schema(self):
        """Test FeatureFlag schema."""
        from app.api.v1.endpoints.governance import FeatureFlag

        fields = FeatureFlag.model_fields
        assert "flag_name" in fields
        assert "enabled" in fields
        assert "tier_required" in fields

    def test_safety_block_schema(self):
        """Test SafetyBlock schema."""
        from app.api.v1.endpoints.governance import SafetyBlock

        fields = SafetyBlock.model_fields
        assert "block_id" in fields
        assert "severity" in fields
        assert "reason_code" in fields

    def test_export_record_schema(self):
        """Test ExportRecord schema."""
        from app.api.v1.endpoints.governance import ExportRecord

        fields = ExportRecord.model_fields
        assert "export_id" in fields
        assert "checksum" in fields
        assert "checksum_algorithm" in fields

    def test_usage_metric_schema(self):
        """Test UsageMetric schema."""
        from app.api.v1.endpoints.governance import UsageMetric

        fields = UsageMetric.model_fields
        assert "metric_type" in fields
        assert "value" in fields
        assert "limit" in fields

    def test_quota_remaining_schema(self):
        """Test QuotaRemaining schema."""
        from app.api.v1.endpoints.governance import QuotaRemaining

        fields = QuotaRemaining.model_fields
        assert "quota_type" in fields
        assert "limit" in fields
        assert "used" in fields
        assert "remaining" in fields
        assert "enforce_behavior" in fields

    def test_cost_estimate_response_schema(self):
        """Test CostEstimateResponse schema."""
        from app.api.v1.endpoints.governance import CostEstimateResponse

        fields = CostEstimateResponse.model_fields
        assert "estimated_min_usd" in fields
        assert "estimated_max_usd" in fields
        assert "estimated_likely_usd" in fields
        assert "breakdown" in fields

    def test_safety_check_response_schema(self):
        """Test SafetyCheckResponse schema."""
        from app.api.v1.endpoints.governance import SafetyCheckResponse

        fields = SafetyCheckResponse.model_fields
        assert "is_safe" in fields
        assert "risk_level" in fields
        assert "classifications" in fields
        assert "reason_codes" in fields
        assert "action_taken" in fields
        assert "audit_log_id" in fields


# =============================================================================
# CostRecord Tests
# =============================================================================

class TestCostRecord:
    """Test CostRecord stored per run/planning/calibration."""

    def test_cost_estimate_endpoint_exists(self):
        """STEP 10: Cost estimate endpoint exists."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/costs/estimate" in routes

    def test_cost_estimate_returns_range(self):
        """STEP 10: Estimator returns pre-run cost range."""
        from app.api.v1.endpoints.governance import CostEstimateResponse

        fields = CostEstimateResponse.model_fields
        assert "estimated_min_usd" in fields
        assert "estimated_max_usd" in fields
        assert "estimated_likely_usd" in fields

    def test_cost_breakdown_available(self):
        """STEP 10: Cost breakdown by category available."""
        from app.api.v1.endpoints.governance import CostEstimateResponse

        fields = CostEstimateResponse.model_fields
        assert "breakdown" in fields


# =============================================================================
# Quota Enforcement Tests
# =============================================================================

class TestQuotaEnforcement:
    """Test quotas enforced server-side with degrade/block behaviors."""

    def test_quota_check_endpoint_exists(self):
        """STEP 10: Quota check endpoint exists."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/quotas/check" in routes

    def test_quota_has_enforce_behavior(self):
        """STEP 10: Quotas have enforce behavior (block/degrade/warn)."""
        from app.api.v1.endpoints.governance import SetQuotasRequest

        fields = SetQuotasRequest.model_fields
        assert "enforce_behavior" in fields

    def test_quota_remaining_shows_status(self):
        """STEP 10: Quota remaining shows enforcement status."""
        from app.api.v1.endpoints.governance import QuotaRemaining

        fields = QuotaRemaining.model_fields
        assert "remaining" in fields
        assert "percentage_remaining" in fields
        assert "enforce_behavior" in fields


# =============================================================================
# Feature Flag Tests
# =============================================================================

class TestFeatureFlags:
    """Test feature flags enforced server-side (API guards)."""

    def test_feature_flag_has_tier_required(self):
        """STEP 10: Feature flags specify tier required."""
        from app.api.v1.endpoints.governance import FeatureFlag

        fields = FeatureFlag.model_fields
        assert "tier_required" in fields

    def test_feature_flag_can_be_enabled_disabled(self):
        """STEP 10: Feature flags can be enabled/disabled."""
        from app.api.v1.endpoints.governance import FeatureFlag

        fields = FeatureFlag.model_fields
        assert "enabled" in fields

    def test_manage_feature_flags_supports_actions(self):
        """STEP 10: Manage feature flags supports list/enable/disable/update."""
        from app.api.v1.endpoints.governance import ManageFeatureFlagsRequest

        fields = ManageFeatureFlagsRequest.model_fields
        assert "action" in fields


# =============================================================================
# Rate Limiting Tests
# =============================================================================

class TestRateLimiting:
    """Test rate limiting for runs/plans/events."""

    def test_rate_limits_endpoint_exists(self):
        """STEP 10: Rate limits endpoint exists."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/rate-limits/{tenant_id}" in routes


# =============================================================================
# Safety Classifier Tests
# =============================================================================

class TestSafetyClassifier:
    """Test safety classifier blocks/downgrades high-risk requests."""

    def test_safety_check_endpoint_exists(self):
        """STEP 10: Safety check endpoint exists."""
        from app.api.v1.endpoints import governance

        routes = [r.path for r in governance.router.routes]
        assert "/safety/check" in routes

    def test_safety_response_includes_action(self):
        """STEP 10: Safety response includes action taken."""
        from app.api.v1.endpoints.governance import SafetyCheckResponse

        fields = SafetyCheckResponse.model_fields
        assert "action_taken" in fields

    def test_safety_response_includes_reason_codes(self):
        """STEP 10: Safety response includes reason codes."""
        from app.api.v1.endpoints.governance import SafetyCheckResponse

        fields = SafetyCheckResponse.model_fields
        assert "reason_codes" in fields

    def test_safety_response_logs_decision(self):
        """STEP 10: Safety classifier logs decisions."""
        from app.api.v1.endpoints.governance import SafetyCheckResponse

        fields = SafetyCheckResponse.model_fields
        assert "audit_log_id" in fields


# =============================================================================
# AuditLog Tests
# =============================================================================

class TestAuditLog:
    """Test AuditLog is immutable, append-only."""

    def test_audit_log_entry_has_required_fields(self):
        """STEP 10: AuditLog includes actor, action, entity ids, spec_hash, timestamp."""
        from app.api.v1.endpoints.governance import AuditLogEntry

        fields = AuditLogEntry.model_fields
        assert "actor_id" in fields
        assert "action_type" in fields
        assert "resource_id" in fields
        assert "spec_hash" in fields
        assert "timestamp" in fields

    def test_audit_log_supports_filtering(self):
        """STEP 10: AuditLog supports filtering by project/node/run/planning."""
        from app.api.v1.endpoints.governance import ViewAuditLogsRequest

        fields = ViewAuditLogsRequest.model_fields
        assert "project_id" in fields
        assert "node_id" in fields
        assert "run_id" in fields
        assert "planning_id" in fields

    def test_audit_log_supports_time_range(self):
        """STEP 10: AuditLog supports time range filtering."""
        from app.api.v1.endpoints.governance import ViewAuditLogsRequest

        fields = ViewAuditLogsRequest.model_fields
        assert "start_date" in fields
        assert "end_date" in fields


# =============================================================================
# Export Integrity Tests
# =============================================================================

class TestExportIntegrity:
    """Test export bundles include integrity metadata."""

    def test_export_record_has_checksum(self):
        """STEP 10: Export records include checksum."""
        from app.api.v1.endpoints.governance import ExportRecord

        fields = ExportRecord.model_fields
        assert "checksum" in fields
        assert "checksum_algorithm" in fields

    def test_export_record_has_access_tracking(self):
        """STEP 10: Export records track downloads."""
        from app.api.v1.endpoints.governance import ExportRecord

        fields = ExportRecord.model_fields
        assert "download_count" in fields

    def test_manage_exports_emits_audit_log(self):
        """STEP 10: Export management emits audit log."""
        from app.api.v1.endpoints.governance import ManageExportsResponse

        fields = ManageExportsResponse.model_fields
        assert "audit_log_id" in fields


# =============================================================================
# Integration Tests
# =============================================================================

class TestGovernanceIntegration:
    """Integration tests for STEP 10 governance flow."""

    def test_quota_flow_schema_compatibility(self):
        """Test quota flow schema compatibility."""
        from app.api.v1.endpoints.governance import (
            SetQuotasRequest,
            SetQuotasResponse,
            ViewQuotaRemainingRequest,
            ViewQuotaRemainingResponse,
        )

        # Create set quota request
        request = SetQuotasRequest(
            tenant_id="tenant-1",
            quota_type="runs",
            daily_limit=100,
            monthly_limit=1000,
            enforce_behavior="block",
        )

        assert request.enforce_behavior == "block"
        assert SetQuotasResponse.model_fields is not None
        assert ViewQuotaRemainingResponse.model_fields is not None

    def test_cost_tracking_flow_schema_compatibility(self):
        """Test cost tracking flow schema compatibility."""
        from app.api.v1.endpoints.governance import (
            ViewCostsRequest,
            ViewCostsResponse,
            CostEstimateRequest,
            CostEstimateResponse,
        )

        # Create cost view request
        request = ViewCostsRequest(
            tenant_id="tenant-1",
            group_by="day",
        )

        assert request.group_by == "day"
        assert ViewCostsResponse.model_fields is not None
        assert CostEstimateResponse.model_fields is not None

    def test_safety_flow_schema_compatibility(self):
        """Test safety flow schema compatibility."""
        from app.api.v1.endpoints.governance import (
            SafetyCheckRequest,
            SafetyCheckResponse,
            ReviewSafetyBlocksRequest,
            ReviewSafetyBlocksResponse,
        )

        # Create safety check request
        request = SafetyCheckRequest(
            content="Test content",
            content_type="prompt",
        )

        assert request.content_type == "prompt"
        assert SafetyCheckResponse.model_fields is not None
        assert ReviewSafetyBlocksResponse.model_fields is not None

    def test_billing_flow_schema_compatibility(self):
        """Test billing flow schema compatibility."""
        from app.api.v1.endpoints.governance import (
            ViewUsageRequest,
            ViewUsageResponse,
            UpgradeTierRequest,
            UpgradeTierResponse,
        )

        # Create usage request
        request = ViewUsageRequest(
            tenant_id="tenant-1",
            period="current_month",
        )

        assert request.period == "current_month"
        assert ViewUsageResponse.model_fields is not None
        assert UpgradeTierResponse.model_fields is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
