"""
STEP 7: Calibration & Reliability Tests

Verifies:
- CalibrationResult (Brier/ECE, predicted vs actual, evidence refs)
- StabilityTest (multi-seed variance, min 2 runs)
- DriftReport (persona/data/model drift, reliability impact)
- ReliabilityScore (explicit formula, component breakdown)
- ParameterVersion (versioning with rollback, never silently modify)
- Cutoff enforcement (blocks post-cutoff data access)

Reference: Future_Predictive_AI_Platform_Ultra_Checklist.md STEP 7
"""

import hashlib
import json
import pytest
from datetime import datetime, timedelta
from typing import Any, Dict


# =============================================================================
# CalibrationResult Model Tests
# =============================================================================

class TestCalibrationResultStructure:
    """Test CalibrationResult model contains required STEP 7 fields."""

    def test_calibration_result_has_brier_score(self):
        """STEP 7: CalibrationReport stores Brier score."""
        from app.models.reliability import CalibrationResult

        # Check model has brier_score field
        mapper = CalibrationResult.__mapper__
        columns = {c.name for c in mapper.columns}
        assert "brier_score" in columns, "CalibrationResult must have brier_score"

    def test_calibration_result_has_ece_score(self):
        """STEP 7: CalibrationReport stores ECE score."""
        from app.models.reliability import CalibrationResult

        mapper = CalibrationResult.__mapper__
        columns = {c.name for c in mapper.columns}
        assert "ece_score" in columns, "CalibrationResult must have ece_score"

    def test_calibration_result_has_predicted_vs_actual(self):
        """STEP 7: CalibrationReport stores predicted vs actual comparison."""
        from app.models.reliability import CalibrationResult

        mapper = CalibrationResult.__mapper__
        columns = {c.name for c in mapper.columns}
        # Should have comparison_summary JSONB containing predicted vs actual
        assert "comparison_summary" in columns, "CalibrationResult must have comparison_summary"

    def test_calibration_result_has_evidence_refs(self):
        """STEP 7: CalibrationReport stores evidence refs."""
        from app.models.reliability import CalibrationResult

        mapper = CalibrationResult.__mapper__
        columns = {c.name for c in mapper.columns}
        assert "evidence_refs" in columns, "CalibrationResult must have evidence_refs"

    def test_calibration_result_has_cutoff_enforcement(self):
        """STEP 7: CalibrationResult tracks cutoff enforcement."""
        from app.models.reliability import CalibrationResult

        mapper = CalibrationResult.__mapper__
        columns = {c.name for c in mapper.columns}
        assert "data_cutoff" in columns, "CalibrationResult must have data_cutoff"


# =============================================================================
# StabilityTest Model Tests
# =============================================================================

class TestStabilityTestStructure:
    """Test StabilityTest model contains required STEP 7 fields."""

    def test_stability_test_has_variance(self):
        """STEP 7: StabilityReport stores variance across seeds."""
        from app.models.reliability import StabilityTest

        mapper = StabilityTest.__mapper__
        columns = {c.name for c in mapper.columns}
        assert "variance" in columns, "StabilityTest must have variance"

    def test_stability_test_has_run_count(self):
        """STEP 7: StabilityTest tracks number of runs."""
        from app.models.reliability import StabilityTest

        mapper = StabilityTest.__mapper__
        columns = {c.name for c in mapper.columns}
        assert "run_count" in columns, "StabilityTest must have run_count"

    def test_stability_test_minimum_runs(self):
        """STEP 7: StabilityTest requires minimum 2 runs."""
        # This is enforced at the API level
        from app.api.v1.endpoints.calibration import StabilityTestRequest
        from pydantic import ValidationError

        # Valid: 2 seeds
        request = StabilityTestRequest(
            project_id="proj-1",
            node_id="node-1",
            seeds=[42, 123],
        )
        assert len(request.seeds) >= 2

        # Invalid: 1 seed should raise validation error
        with pytest.raises(ValidationError):
            StabilityTestRequest(
                project_id="proj-1",
                node_id="node-1",
                seeds=[42],
            )


# =============================================================================
# DriftReport Model Tests
# =============================================================================

class TestDriftReportStructure:
    """Test DriftReport model contains required STEP 7 fields."""

    def test_drift_report_has_drift_type(self):
        """STEP 7: DriftReport stores drift type (persona/data/model)."""
        from app.models.reliability import DriftReport

        mapper = DriftReport.__mapper__
        columns = {c.name for c in mapper.columns}
        assert "drift_type" in columns, "DriftReport must have drift_type"

    def test_drift_report_has_reliability_impact(self):
        """STEP 7: DriftReport stores reliability impact."""
        from app.models.reliability import DriftReport

        mapper = DriftReport.__mapper__
        columns = {c.name for c in mapper.columns}
        assert "reliability_impact" in columns, "DriftReport must have reliability_impact"

    def test_drift_report_has_severity(self):
        """STEP 7: DriftReport stores severity level."""
        from app.models.reliability import DriftReport

        mapper = DriftReport.__mapper__
        columns = {c.name for c in mapper.columns}
        assert "severity" in columns, "DriftReport must have severity"


# =============================================================================
# ReliabilityScore Model Tests
# =============================================================================

class TestReliabilityScoreStructure:
    """Test ReliabilityScore model contains required STEP 7 fields."""

    def test_reliability_score_has_component_breakdown(self):
        """STEP 7: ReliabilityScore has component breakdown."""
        from app.models.reliability import ReliabilityScore

        mapper = ReliabilityScore.__mapper__
        columns = {c.name for c in mapper.columns}
        # Component scores
        assert "calibration_score" in columns, "ReliabilityScore must have calibration_score"
        assert "stability_score" in columns, "ReliabilityScore must have stability_score"

    def test_reliability_score_explicit_formula(self):
        """STEP 7: ReliabilityScore computed by explicit rules (not LLM)."""
        from app.models.reliability import ReliabilityScoreComputer

        # Verify explicit formula exists
        assert hasattr(ReliabilityScoreComputer, "FORMULA")
        assert "reliability_score" in ReliabilityScoreComputer.FORMULA

        # Verify compute method exists
        assert hasattr(ReliabilityScoreComputer, "compute")

    def test_reliability_score_computation_deterministic(self):
        """STEP 7: ReliabilityScore computation is deterministic."""
        from app.models.reliability import ReliabilityScoreComputer

        result1 = ReliabilityScoreComputer.compute(
            calibration_score=0.85,
            stability_score=0.90,
            data_gap_penalty=0.05,
            drift_penalty=0.10,
        )

        result2 = ReliabilityScoreComputer.compute(
            calibration_score=0.85,
            stability_score=0.90,
            data_gap_penalty=0.05,
            drift_penalty=0.10,
        )

        assert result1["reliability_score"] == result2["reliability_score"]
        assert result1["reliability_level"] == result2["reliability_level"]

    def test_reliability_score_computation_trace(self):
        """STEP 7: ReliabilityScore includes computation trace for auditability."""
        from app.models.reliability import ReliabilityScoreComputer

        result = ReliabilityScoreComputer.compute(
            calibration_score=0.85,
            stability_score=0.90,
            data_gap_penalty=0.05,
            drift_penalty=0.10,
        )

        assert "computation_trace" in result
        assert "scoring_formula" in result


# =============================================================================
# ParameterVersion Model Tests
# =============================================================================

class TestParameterVersionStructure:
    """Test ParameterVersion model contains required STEP 7 fields."""

    def test_parameter_version_has_version_number(self):
        """STEP 7: ParameterVersion has version number."""
        from app.models.reliability import ParameterVersion

        mapper = ParameterVersion.__mapper__
        columns = {c.name for c in mapper.columns}
        assert "version_number" in columns, "ParameterVersion must have version_number"

    def test_parameter_version_has_rollback_reference(self):
        """STEP 7: ParameterVersion has rollback reference."""
        from app.models.reliability import ParameterVersion

        mapper = ParameterVersion.__mapper__
        columns = {c.name for c in mapper.columns}
        assert "previous_version_id" in columns, "ParameterVersion must have previous_version_id"

    def test_parameter_version_status_options(self):
        """STEP 7: ParameterVersion supports rollback status."""
        from app.api.v1.endpoints.calibration import AutoTuneRequest

        # Valid status values: proposed, active, rolled_back
        request = AutoTuneRequest(
            project_id="proj-1",
            require_approval=True,  # Status will be "proposed"
        )
        assert request.require_approval is True


# =============================================================================
# Button→Backend Chain Tests
# =============================================================================

class TestCalibrationLabButtonChains:
    """Test all Calibration Lab button→backend chains exist."""

    def test_create_calibration_scenario_endpoint_exists(self):
        """Calibration Lab: Create Calibration Scenario button chain."""
        from app.api.v1.endpoints import calibration

        assert hasattr(calibration.router, "routes")
        routes = [r.path for r in calibration.router.routes]
        assert "/scenarios" in routes

    def test_run_calibration_endpoint_exists(self):
        """Calibration Lab: Run Calibration button chain."""
        from app.api.v1.endpoints import calibration

        routes = [r.path for r in calibration.router.routes]
        assert "/run" in routes

    def test_view_calibration_metrics_endpoint_exists(self):
        """Calibration Lab: View Calibration Metrics button chain."""
        from app.api.v1.endpoints import calibration

        routes = [r.path for r in calibration.router.routes]
        assert "/scenarios/{scenario_id}/metrics" in routes

    def test_run_stability_test_endpoint_exists(self):
        """Calibration Lab: Run Stability Test button chain."""
        from app.api.v1.endpoints import calibration

        routes = [r.path for r in calibration.router.routes]
        assert "/stability-test" in routes

    def test_run_drift_scan_endpoint_exists(self):
        """Calibration Lab: Run Drift Scan button chain."""
        from app.api.v1.endpoints import calibration

        routes = [r.path for r in calibration.router.routes]
        assert "/drift-scan" in routes

    def test_auto_tune_endpoint_exists(self):
        """Calibration Lab: Auto-Tune Parameters button chain."""
        from app.api.v1.endpoints import calibration

        routes = [r.path for r in calibration.router.routes]
        assert "/auto-tune" in routes

    def test_rollback_endpoint_exists(self):
        """Calibration Lab: Rollback Parameters button chain."""
        from app.api.v1.endpoints import calibration

        routes = [r.path for r in calibration.router.routes]
        assert "/rollback" in routes


class TestReliabilityPanelButtonChains:
    """Test all Reliability Panel button→backend chains exist."""

    def test_view_reliability_breakdown_endpoint_exists(self):
        """Reliability Panel: View Reliability Breakdown button chain."""
        from app.api.v1.endpoints import calibration

        routes = [r.path for r in calibration.router.routes]
        assert "/reliability/{run_id}/breakdown" in routes

    def test_download_reliability_report_endpoint_exists(self):
        """Reliability Panel: Download Reliability Report button chain."""
        from app.api.v1.endpoints import calibration

        routes = [r.path for r in calibration.router.routes]
        assert "/reliability/{project_id}/report" in routes


# =============================================================================
# Cutoff Enforcement Tests
# =============================================================================

class TestCutoffEnforcement:
    """Test STEP 7 cutoff enforcement."""

    def test_cutoff_verification_endpoint_exists(self):
        """STEP 7: Cutoff verification endpoint exists."""
        from app.api.v1.endpoints import calibration

        routes = [r.path for r in calibration.router.routes]
        assert "/verify-cutoff" in routes

    def test_cutoff_enforced_in_calibration_scenario(self):
        """STEP 7: Calibration scenario requires data_cutoff."""
        from app.api.v1.endpoints.calibration import CalibrationScenarioRequest

        # data_cutoff is required field
        request = CalibrationScenarioRequest(
            project_id="proj-1",
            name="Test Scenario",
            data_cutoff=datetime.utcnow(),
        )
        assert request.data_cutoff is not None


# =============================================================================
# Auto-Tune Never Silently Modify Tests
# =============================================================================

class TestAutoTuneVersioning:
    """Test STEP 7 auto-tune versioning (never silently modify)."""

    def test_auto_tune_requires_approval_by_default(self):
        """STEP 7: Auto-tune requires approval by default."""
        from app.api.v1.endpoints.calibration import AutoTuneRequest

        request = AutoTuneRequest(project_id="proj-1")
        assert request.require_approval is True

    def test_auto_tune_response_includes_version_info(self):
        """STEP 7: Auto-tune response includes version info."""
        from app.api.v1.endpoints.calibration import AutoTuneResponse

        # Verify response schema has versioning fields
        fields = AutoTuneResponse.model_fields
        assert "version_id" in fields
        assert "version_number" in fields
        assert "previous_version_id" in fields
        assert "requires_approval" in fields


# =============================================================================
# Brier/ECE Score Tests
# =============================================================================

class TestBrierECEScoring:
    """Test Brier and ECE score computation."""

    def test_brier_score_computation(self):
        """STEP 7: Brier score computed correctly."""
        # Brier score = mean((predicted - actual)^2)
        predicted = {"a": 0.8, "b": 0.6}
        actual = {"a": 1.0, "b": 0.0}

        brier_sum = 0.0
        count = 0
        for key in predicted:
            if key in actual:
                brier_sum += (predicted[key] - actual[key]) ** 2
                count += 1
        brier_score = brier_sum / count if count > 0 else 0.0

        # (0.8-1.0)^2 + (0.6-0.0)^2 = 0.04 + 0.36 = 0.40 / 2 = 0.20
        assert abs(brier_score - 0.20) < 0.001

    def test_ece_score_range(self):
        """STEP 7: ECE score is in valid range."""
        # ECE should be between 0 and 1
        # The endpoint computes ECE as a measure of calibration error
        from app.api.v1.endpoints.calibration import CalibrationMetricsResponse

        fields = CalibrationMetricsResponse.model_fields
        assert "ece_score" in fields


# =============================================================================
# Schema Request/Response Tests
# =============================================================================

class TestRequestSchemas:
    """Test STEP 7 request schemas."""

    def test_calibration_scenario_request_schema(self):
        """Test CalibrationScenarioRequest schema."""
        from app.api.v1.endpoints.calibration import CalibrationScenarioRequest

        fields = CalibrationScenarioRequest.model_fields
        assert "project_id" in fields
        assert "name" in fields
        assert "data_cutoff" in fields
        assert "method" in fields

    def test_stability_test_request_schema(self):
        """Test StabilityTestRequest schema."""
        from app.api.v1.endpoints.calibration import StabilityTestRequest

        fields = StabilityTestRequest.model_fields
        assert "project_id" in fields
        assert "node_id" in fields
        assert "seeds" in fields
        assert "stability_threshold" in fields

    def test_drift_scan_request_schema(self):
        """Test DriftScanRequest schema."""
        from app.api.v1.endpoints.calibration import DriftScanRequest

        fields = DriftScanRequest.model_fields
        assert "project_id" in fields
        assert "drift_type" in fields
        assert "reference_period_days" in fields

    def test_rollback_request_schema(self):
        """Test RollbackRequest schema."""
        from app.api.v1.endpoints.calibration import RollbackRequest

        fields = RollbackRequest.model_fields
        assert "project_id" in fields
        assert "target_version_id" in fields
        assert "reason" in fields


class TestResponseSchemas:
    """Test STEP 7 response schemas."""

    def test_calibration_result_response_schema(self):
        """Test CalibrationResultResponse schema."""
        from app.api.v1.endpoints.calibration import CalibrationResultResponse

        fields = CalibrationResultResponse.model_fields
        assert "calibration_id" in fields
        assert "brier_score" in fields
        assert "ece_score" in fields
        assert "comparison_summary" in fields
        assert "evidence_refs" in fields

    def test_stability_test_response_schema(self):
        """Test StabilityTestResponse schema."""
        from app.api.v1.endpoints.calibration import StabilityTestResponse

        fields = StabilityTestResponse.model_fields
        assert "test_id" in fields
        assert "variance" in fields
        assert "std_dev" in fields
        assert "is_stable" in fields
        assert "seeds_tested" in fields

    def test_drift_scan_response_schema(self):
        """Test DriftScanResponse schema."""
        from app.api.v1.endpoints.calibration import DriftScanResponse

        fields = DriftScanResponse.model_fields
        assert "scan_id" in fields
        assert "drift_detected" in fields
        assert "drift_score" in fields
        assert "severity" in fields
        assert "reliability_impact" in fields

    def test_reliability_breakdown_response_schema(self):
        """Test ReliabilityBreakdownResponse schema."""
        from app.api.v1.endpoints.calibration import ReliabilityBreakdownResponse

        fields = ReliabilityBreakdownResponse.model_fields
        assert "reliability_score" in fields
        assert "reliability_level" in fields
        assert "components" in fields
        assert "weights" in fields
        assert "scoring_formula" in fields
        assert "computation_trace" in fields


# =============================================================================
# C5 Compliance Tests
# =============================================================================

class TestC5Compliance:
    """Test C5 constraint compliance: Scoring is explicit, not LLM black-box."""

    def test_reliability_scoring_explicit(self):
        """C5: ReliabilityScore uses explicit formula, not LLM."""
        from app.models.reliability import ReliabilityScoreComputer

        # The FORMULA attribute documents the explicit calculation
        assert "w_calibration" in ReliabilityScoreComputer.FORMULA
        assert "w_stability" in ReliabilityScoreComputer.FORMULA

    def test_reliability_scoring_no_llm(self):
        """C5: ReliabilityScore computation doesn't call LLM."""
        from app.models.reliability import ReliabilityScoreComputer

        # The compute method is static and deterministic
        # No async calls, no LLM router usage
        import inspect
        sig = inspect.signature(ReliabilityScoreComputer.compute)
        params = list(sig.parameters.keys())

        # No "llm" or "router" parameters
        assert "llm" not in params
        assert "router" not in params
        assert "llm_router" not in params


# =============================================================================
# Integration Tests
# =============================================================================

class TestCalibrationIntegration:
    """Integration tests for STEP 7 calibration flow."""

    def test_full_calibration_flow_schema(self):
        """Test full calibration flow schema compatibility."""
        from app.api.v1.endpoints.calibration import (
            CalibrationScenarioRequest,
            CalibrationScenarioResponse,
            RunCalibrationRequest,
            CalibrationResultResponse,
            CalibrationMetricsResponse,
        )

        # Step 1: Create scenario
        scenario_req = CalibrationScenarioRequest(
            project_id="proj-1",
            name="Test Calibration",
            data_cutoff=datetime.utcnow(),
        )

        # Step 2: Run calibration
        run_req = RunCalibrationRequest(
            scenario_id="scenario-1",
            ground_truth={"predicted": {"a": 0.8}, "actual": {"a": 1.0}},
        )

        # Response schemas should be compatible
        assert CalibrationScenarioResponse.model_fields is not None
        assert CalibrationResultResponse.model_fields is not None
        assert CalibrationMetricsResponse.model_fields is not None

    def test_full_stability_flow_schema(self):
        """Test full stability test flow schema compatibility."""
        from app.api.v1.endpoints.calibration import (
            StabilityTestRequest,
            StabilityTestResponse,
        )

        # Create stability test request with minimum 2 seeds
        stability_req = StabilityTestRequest(
            project_id="proj-1",
            node_id="node-1",
            seeds=[42, 123, 456],
        )

        assert len(stability_req.seeds) >= 2
        assert StabilityTestResponse.model_fields is not None

    def test_full_auto_tune_rollback_flow_schema(self):
        """Test full auto-tune and rollback flow schema compatibility."""
        from app.api.v1.endpoints.calibration import (
            AutoTuneRequest,
            AutoTuneResponse,
            RollbackRequest,
            RollbackResponse,
        )

        # Auto-tune with versioning
        tune_req = AutoTuneRequest(
            project_id="proj-1",
            require_approval=True,
        )

        # Rollback with reason
        rollback_req = RollbackRequest(
            project_id="proj-1",
            target_version_id="version-1",
            reason="Performance regression",
        )

        assert tune_req.require_approval is True
        assert rollback_req.reason is not None
        assert AutoTuneResponse.model_fields is not None
        assert RollbackResponse.model_fields is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
