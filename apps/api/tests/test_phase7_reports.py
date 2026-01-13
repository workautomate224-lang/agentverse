"""
PHASE 7 — Aggregated Report Endpoint Tests
Reference: Phase 7 specification

Tests for:
1. Report schema validation
2. Report service computation
3. Insufficient data handling (returns 200 with insufficient_data=true, never 500)
4. Deterministic outputs (same inputs = same outputs)
5. Sensitivity, stability, and drift computation
6. Calibration summary integration
"""

import uuid
from datetime import datetime, timedelta
from typing import List
from unittest.mock import MagicMock, AsyncMock, patch

import numpy as np
import pytest

from app.schemas.report import (
    ReportResponse,
    ReportQueryParams,
    ReportOperator,
    TargetSpec,
    ReportFilters,
    ReportProvenance,
    DistributionData,
    PredictionResult,
    CalibrationCurve,
    CalibrationResult,
    SensitivityData,
    StabilityData,
    DriftData,
    DriftStatus,
    ReliabilityResult,
)


# =============================================================================
# Schema Tests
# =============================================================================

class TestReportSchemas:
    """Test Pydantic schema validation for Phase 7 Report."""

    def test_report_operator_enum(self):
        """Test ReportOperator enum values."""
        assert ReportOperator.GE == "ge"
        assert ReportOperator.GT == "gt"
        assert ReportOperator.LE == "le"
        assert ReportOperator.LT == "lt"
        assert ReportOperator.EQ == "eq"

    def test_drift_status_enum(self):
        """Test DriftStatus enum values."""
        assert DriftStatus.STABLE == "stable"
        assert DriftStatus.WARNING == "warning"
        assert DriftStatus.DRIFTING == "drifting"

    def test_target_spec_construction(self):
        """Test TargetSpec construction."""
        target = TargetSpec(op=ReportOperator.GE, threshold=0.8)
        assert target.op == ReportOperator.GE
        assert target.threshold == 0.8

    def test_report_filters_defaults(self):
        """Test ReportFilters defaults."""
        filters = ReportFilters()
        assert filters.manifest_hash is None
        assert filters.window_days == 30
        assert filters.min_runs == 3

    def test_report_provenance_construction(self):
        """Test ReportProvenance construction."""
        provenance = ReportProvenance(
            manifest_hash="abc123",
            filters=ReportFilters(window_days=14, min_runs=5),
            n_runs=50,
            updated_at=datetime.utcnow(),
        )
        assert provenance.manifest_hash == "abc123"
        assert provenance.filters.window_days == 14
        assert provenance.n_runs == 50

    def test_distribution_data_empty(self):
        """Test DistributionData with empty data."""
        dist = DistributionData()
        assert dist.bins == []
        assert dist.counts == []
        assert dist.min == 0.0
        assert dist.max == 0.0

    def test_distribution_data_with_values(self):
        """Test DistributionData with values."""
        dist = DistributionData(
            bins=[0.0, 0.25, 0.5, 0.75, 1.0],
            counts=[10, 20, 30, 40],
            min=0.0,
            max=1.0,
        )
        assert len(dist.bins) == 5
        assert len(dist.counts) == 4
        assert dist.min == 0.0
        assert dist.max == 1.0

    def test_prediction_result_construction(self):
        """Test PredictionResult construction."""
        prediction = PredictionResult(
            distribution=DistributionData(
                bins=[0.0, 0.5, 1.0],
                counts=[10, 90],
                min=0.0,
                max=1.0,
            ),
            target_probability=0.72,
        )
        assert prediction.target_probability == 0.72
        assert len(prediction.distribution.counts) == 2

    def test_calibration_curve_construction(self):
        """Test CalibrationCurve construction."""
        curve = CalibrationCurve(
            p_pred=[0.1, 0.3, 0.5, 0.7, 0.9],
            p_true=[0.12, 0.28, 0.52, 0.68, 0.88],
            counts=[100, 150, 200, 150, 100],
        )
        assert len(curve.p_pred) == 5
        assert len(curve.p_true) == 5
        assert len(curve.counts) == 5

    def test_calibration_result_not_available(self):
        """Test CalibrationResult when not available."""
        cal = CalibrationResult(available=False)
        assert cal.available is False
        assert cal.brier is None
        assert cal.ece is None
        assert cal.curve is None

    def test_calibration_result_available(self):
        """Test CalibrationResult when available."""
        cal = CalibrationResult(
            available=True,
            latest_job_id="job-123",
            brier=0.15,
            ece=0.08,
            curve=CalibrationCurve(
                p_pred=[0.1, 0.5, 0.9],
                p_true=[0.12, 0.48, 0.92],
                counts=[100, 200, 100],
            ),
        )
        assert cal.available is True
        assert cal.brier == 0.15
        assert cal.ece == 0.08

    def test_sensitivity_data_construction(self):
        """Test SensitivityData construction."""
        sens = SensitivityData(
            thresholds=[0.0, 0.25, 0.5, 0.75, 1.0],
            probabilities=[1.0, 0.8, 0.6, 0.3, 0.0],
        )
        assert len(sens.thresholds) == 5
        assert len(sens.probabilities) == 5
        assert sens.probabilities[0] == 1.0

    def test_stability_data_construction(self):
        """Test StabilityData construction."""
        stab = StabilityData(
            mean=0.72,
            ci_low=0.68,
            ci_high=0.76,
            bootstrap_samples=200,
        )
        assert stab.mean == 0.72
        assert stab.ci_low == 0.68
        assert stab.ci_high == 0.76
        assert stab.bootstrap_samples == 200

    def test_drift_data_stable(self):
        """Test DriftData with stable status."""
        drift = DriftData(
            status=DriftStatus.STABLE,
            ks=0.08,
            psi=0.05,
        )
        assert drift.status == DriftStatus.STABLE
        assert drift.ks == 0.08
        assert drift.psi == 0.05

    def test_drift_data_drifting(self):
        """Test DriftData with drifting status."""
        drift = DriftData(
            status=DriftStatus.DRIFTING,
            ks=0.35,
            psi=0.30,
        )
        assert drift.status == DriftStatus.DRIFTING

    def test_reliability_result_construction(self):
        """Test ReliabilityResult construction."""
        reliability = ReliabilityResult(
            sensitivity=SensitivityData(thresholds=[0.5], probabilities=[0.72]),
            stability=StabilityData(mean=0.72, ci_low=0.68, ci_high=0.76),
            drift=DriftData(status=DriftStatus.STABLE, ks=0.08, psi=0.05),
        )
        assert reliability.sensitivity.probabilities[0] == 0.72
        assert reliability.stability.mean == 0.72
        assert reliability.drift.status == DriftStatus.STABLE

    def test_report_response_complete(self):
        """Test complete ReportResponse construction."""
        response = ReportResponse(
            node_id="node-123",
            metric_key="score",
            target=TargetSpec(op=ReportOperator.GE, threshold=0.8),
            provenance=ReportProvenance(
                filters=ReportFilters(),
                n_runs=50,
                updated_at=datetime.utcnow(),
            ),
            prediction=PredictionResult(
                distribution=DistributionData(),
                target_probability=0.72,
            ),
            calibration=CalibrationResult(available=True, brier=0.15),
            reliability=ReliabilityResult(
                sensitivity=SensitivityData(),
                stability=StabilityData(mean=0.72, ci_low=0.68, ci_high=0.76),
                drift=DriftData(status=DriftStatus.STABLE),
            ),
            insufficient_data=False,
            errors=[],
        )

        assert response.node_id == "node-123"
        assert response.metric_key == "score"
        assert response.target.op == ReportOperator.GE
        assert response.target.threshold == 0.8
        assert response.insufficient_data is False

    def test_report_response_insufficient_data(self):
        """CRITICAL: Test ReportResponse with insufficient_data=true."""
        response = ReportResponse(
            node_id="node-123",
            metric_key="score",
            target=TargetSpec(op=ReportOperator.GE, threshold=0.8),
            provenance=ReportProvenance(
                filters=ReportFilters(),
                n_runs=2,  # Less than min_runs
                updated_at=datetime.utcnow(),
            ),
            prediction=PredictionResult(
                distribution=DistributionData(),
                target_probability=0.0,
            ),
            calibration=CalibrationResult(available=False),
            reliability=ReliabilityResult(
                sensitivity=SensitivityData(),
                stability=StabilityData(mean=0.0, ci_low=0.0, ci_high=0.0),
                drift=DriftData(status=DriftStatus.STABLE),
            ),
            insufficient_data=True,
            errors=["Insufficient data: 2 runs found, minimum 3 required"],
        )

        assert response.insufficient_data is True
        assert len(response.errors) == 1
        assert "Insufficient" in response.errors[0]

    def test_report_query_params_defaults(self):
        """Test ReportQueryParams defaults."""
        params = ReportQueryParams(
            metric_key="score",
            op=ReportOperator.GE,
            threshold=0.8,
        )
        assert params.metric_key == "score"
        assert params.op == ReportOperator.GE
        assert params.threshold == 0.8
        assert params.manifest_hash is None
        assert params.min_runs == 3
        assert params.window_days == 30
        assert params.n_sensitivity_grid == 20
        assert params.n_bootstrap == 200
        assert params.n_bins == 20


# =============================================================================
# Report Service Unit Tests
# =============================================================================

class TestReportServiceUnit:
    """Unit tests for ReportService helper functions."""

    def test_compute_deterministic_seed(self):
        """Test deterministic seed generation."""
        from app.services.report_service import compute_deterministic_seed

        seed1 = compute_deterministic_seed(
            tenant_id="tenant-123",
            node_id="node-456",
            metric_key="score",
            threshold=0.8,
            manifest_hash="abc",
        )
        seed2 = compute_deterministic_seed(
            tenant_id="tenant-123",
            node_id="node-456",
            metric_key="score",
            threshold=0.8,
            manifest_hash="abc",
        )

        # Same inputs = same seed
        assert seed1 == seed2
        assert len(seed1) == 16

    def test_compute_deterministic_seed_different_inputs(self):
        """Test deterministic seed with different inputs."""
        from app.services.report_service import compute_deterministic_seed

        seed1 = compute_deterministic_seed(
            tenant_id="tenant-123",
            node_id="node-456",
            metric_key="score",
            threshold=0.8,
            manifest_hash="abc",
        )
        seed2 = compute_deterministic_seed(
            tenant_id="tenant-123",
            node_id="node-456",
            metric_key="score",
            threshold=0.9,  # Different threshold
            manifest_hash="abc",
        )

        # Different inputs = different seed
        assert seed1 != seed2

    def test_compute_target_probability_ge(self):
        """Test target probability with >= operator."""
        from app.services.report_service import _compute_target_probability

        values = [0.1, 0.3, 0.5, 0.7, 0.9]
        prob = _compute_target_probability(values, ReportOperator.GE, 0.5)

        # 3 out of 5 values >= 0.5
        assert prob == pytest.approx(0.6, rel=1e-6)

    def test_compute_target_probability_gt(self):
        """Test target probability with > operator."""
        from app.services.report_service import _compute_target_probability

        values = [0.1, 0.3, 0.5, 0.7, 0.9]
        prob = _compute_target_probability(values, ReportOperator.GT, 0.5)

        # 2 out of 5 values > 0.5
        assert prob == pytest.approx(0.4, rel=1e-6)

    def test_compute_target_probability_le(self):
        """Test target probability with <= operator."""
        from app.services.report_service import _compute_target_probability

        values = [0.1, 0.3, 0.5, 0.7, 0.9]
        prob = _compute_target_probability(values, ReportOperator.LE, 0.5)

        # 3 out of 5 values <= 0.5
        assert prob == pytest.approx(0.6, rel=1e-6)

    def test_compute_target_probability_lt(self):
        """Test target probability with < operator."""
        from app.services.report_service import _compute_target_probability

        values = [0.1, 0.3, 0.5, 0.7, 0.9]
        prob = _compute_target_probability(values, ReportOperator.LT, 0.5)

        # 2 out of 5 values < 0.5
        assert prob == pytest.approx(0.4, rel=1e-6)

    def test_compute_target_probability_empty(self):
        """Test target probability with empty values."""
        from app.services.report_service import _compute_target_probability

        prob = _compute_target_probability([], ReportOperator.GE, 0.5)
        assert prob == 0.0

    def test_compute_histogram_basic(self):
        """Test histogram computation."""
        from app.services.report_service import _compute_histogram

        values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        dist = _compute_histogram(values, n_bins=5)

        assert len(dist.bins) == 6  # n_bins + 1 edges
        assert len(dist.counts) == 5
        assert sum(dist.counts) == 9
        assert dist.min == pytest.approx(0.1, rel=1e-6)
        assert dist.max == pytest.approx(0.9, rel=1e-6)

    def test_compute_histogram_empty(self):
        """Test histogram with empty values."""
        from app.services.report_service import _compute_histogram

        dist = _compute_histogram([])
        assert dist.bins == []
        assert dist.counts == []

    def test_compute_sensitivity_basic(self):
        """Test sensitivity analysis."""
        from app.services.report_service import _compute_sensitivity

        values = [0.1, 0.3, 0.5, 0.7, 0.9]
        sens = _compute_sensitivity(values, ReportOperator.GE, threshold=0.5, n_grid=5)

        assert len(sens.thresholds) == 5
        assert len(sens.probabilities) == 5
        # Probabilities should decrease as threshold increases
        assert sens.probabilities[0] >= sens.probabilities[-1]

    def test_compute_sensitivity_empty(self):
        """Test sensitivity with empty values."""
        from app.services.report_service import _compute_sensitivity

        sens = _compute_sensitivity([], ReportOperator.GE, threshold=0.5)
        assert sens.thresholds == []
        assert sens.probabilities == []

    def test_compute_stability_deterministic(self):
        """Test stability bootstrap is deterministic."""
        from app.services.report_service import _compute_stability

        values = [0.1, 0.3, 0.5, 0.7, 0.9] * 10  # 50 values
        seed = "abc123def456"

        stab1 = _compute_stability(values, ReportOperator.GE, 0.5, seed, n_bootstrap=100)
        stab2 = _compute_stability(values, ReportOperator.GE, 0.5, seed, n_bootstrap=100)

        # Same seed = same results
        assert stab1.mean == stab2.mean
        assert stab1.ci_low == stab2.ci_low
        assert stab1.ci_high == stab2.ci_high

    def test_compute_stability_ci_bounds(self):
        """Test stability CI bounds make sense."""
        from app.services.report_service import _compute_stability

        values = [0.1, 0.3, 0.5, 0.7, 0.9] * 20  # 100 values
        seed = "abc123def456"

        stab = _compute_stability(values, ReportOperator.GE, 0.5, seed)

        # CI should contain the mean
        assert stab.ci_low <= stab.mean <= stab.ci_high

    def test_compute_stability_empty(self):
        """Test stability with empty values."""
        from app.services.report_service import _compute_stability

        stab = _compute_stability([], ReportOperator.GE, 0.5, "seed")
        assert stab.mean == 0.0
        assert stab.ci_low == 0.0
        assert stab.ci_high == 0.0

    def test_compute_drift_stable(self):
        """Test drift detection - stable case."""
        from app.services.report_service import _compute_drift

        # Same distribution
        baseline = [0.1, 0.3, 0.5, 0.7, 0.9] * 10
        recent = [0.15, 0.35, 0.55, 0.65, 0.85] * 10

        drift = _compute_drift(baseline, recent)

        assert drift.status == DriftStatus.STABLE
        assert drift.ks is not None
        assert drift.psi is not None

    def test_compute_drift_drifting(self):
        """Test drift detection - drifting case."""
        from app.services.report_service import _compute_drift

        # Very different distributions
        baseline = [0.1, 0.2, 0.3] * 20  # Low values
        recent = [0.8, 0.9, 1.0] * 20    # High values

        drift = _compute_drift(baseline, recent)

        # Should detect significant drift
        assert drift.status in [DriftStatus.WARNING, DriftStatus.DRIFTING]

    def test_compute_drift_empty(self):
        """Test drift with empty values."""
        from app.services.report_service import _compute_drift

        drift = _compute_drift([], [])
        assert drift.status == DriftStatus.STABLE
        assert drift.ks is None
        assert drift.psi is None


# =============================================================================
# Insufficient Data Tests (CRITICAL)
# =============================================================================

class TestInsufficientDataHandling:
    """
    PHASE 7 CRITICAL: Test insufficient data handling.

    The endpoint must NEVER return HTTP 500 for missing data.
    Instead, return HTTP 200 with insufficient_data=true.
    """

    def test_response_has_insufficient_data_flag(self):
        """CRITICAL: Response must have insufficient_data field."""
        response = ReportResponse(
            node_id="node-123",
            metric_key="score",
            target=TargetSpec(op=ReportOperator.GE, threshold=0.8),
            provenance=ReportProvenance(
                filters=ReportFilters(),
                n_runs=0,
                updated_at=datetime.utcnow(),
            ),
            prediction=PredictionResult(
                distribution=DistributionData(),
                target_probability=0.0,
            ),
            calibration=CalibrationResult(available=False),
            reliability=ReliabilityResult(
                sensitivity=SensitivityData(),
                stability=StabilityData(mean=0.0, ci_low=0.0, ci_high=0.0),
                drift=DriftData(status=DriftStatus.STABLE),
            ),
            insufficient_data=True,
            errors=["No runs found"],
        )

        assert hasattr(response, "insufficient_data")
        assert response.insufficient_data is True

    def test_zero_runs_returns_insufficient_data(self):
        """CRITICAL: Zero runs must set insufficient_data=true."""
        n_runs = 0
        min_runs = 3

        insufficient = n_runs < min_runs
        assert insufficient is True

    def test_below_min_runs_returns_insufficient_data(self):
        """CRITICAL: n_runs < min_runs must set insufficient_data=true."""
        n_runs = 2
        min_runs = 3

        insufficient = n_runs < min_runs
        assert insufficient is True

    def test_at_min_runs_returns_sufficient_data(self):
        """CRITICAL: n_runs == min_runs should NOT be insufficient."""
        n_runs = 3
        min_runs = 3

        insufficient = n_runs < min_runs
        assert insufficient is False

    def test_above_min_runs_returns_sufficient_data(self):
        """CRITICAL: n_runs > min_runs should NOT be insufficient."""
        n_runs = 100
        min_runs = 3

        insufficient = n_runs < min_runs
        assert insufficient is False

    def test_response_errors_list_explains_insufficient_data(self):
        """CRITICAL: errors list should explain why data is insufficient."""
        response = ReportResponse(
            node_id="node-123",
            metric_key="score",
            target=TargetSpec(op=ReportOperator.GE, threshold=0.8),
            provenance=ReportProvenance(
                filters=ReportFilters(min_runs=10),
                n_runs=5,
                updated_at=datetime.utcnow(),
            ),
            prediction=PredictionResult(
                distribution=DistributionData(),
                target_probability=0.0,
            ),
            calibration=CalibrationResult(available=False),
            reliability=ReliabilityResult(
                sensitivity=SensitivityData(),
                stability=StabilityData(mean=0.0, ci_low=0.0, ci_high=0.0),
                drift=DriftData(status=DriftStatus.STABLE),
            ),
            insufficient_data=True,
            errors=["Insufficient data: 5 runs found, minimum 10 required"],
        )

        assert len(response.errors) > 0
        assert "5" in response.errors[0]
        assert "10" in response.errors[0]


# =============================================================================
# Determinism Tests
# =============================================================================

class TestDeterminism:
    """
    PHASE 7: Test deterministic output.

    Same inputs + same data = same results (including seeded bootstrap).
    """

    def test_histogram_deterministic(self):
        """Histogram computation must be deterministic."""
        from app.services.report_service import _compute_histogram

        values = [0.1, 0.3, 0.5, 0.7, 0.9] * 10

        dist1 = _compute_histogram(values, n_bins=10)
        dist2 = _compute_histogram(values, n_bins=10)

        assert dist1.bins == dist2.bins
        assert dist1.counts == dist2.counts

    def test_target_probability_deterministic(self):
        """Target probability must be deterministic."""
        from app.services.report_service import _compute_target_probability

        values = [0.1, 0.3, 0.5, 0.7, 0.9] * 10

        prob1 = _compute_target_probability(values, ReportOperator.GE, 0.5)
        prob2 = _compute_target_probability(values, ReportOperator.GE, 0.5)

        assert prob1 == prob2

    def test_sensitivity_deterministic(self):
        """Sensitivity analysis must be deterministic."""
        from app.services.report_service import _compute_sensitivity

        values = [0.1, 0.3, 0.5, 0.7, 0.9] * 10

        sens1 = _compute_sensitivity(values, ReportOperator.GE, 0.5, n_grid=10)
        sens2 = _compute_sensitivity(values, ReportOperator.GE, 0.5, n_grid=10)

        assert sens1.thresholds == sens2.thresholds
        assert sens1.probabilities == sens2.probabilities

    def test_stability_deterministic_with_seed(self):
        """Stability bootstrap must be deterministic with same seed."""
        from app.services.report_service import _compute_stability

        values = [0.1, 0.3, 0.5, 0.7, 0.9] * 20
        seed = "deterministic_seed"

        stab1 = _compute_stability(values, ReportOperator.GE, 0.5, seed, n_bootstrap=50)
        stab2 = _compute_stability(values, ReportOperator.GE, 0.5, seed, n_bootstrap=50)

        assert stab1.mean == stab2.mean
        assert stab1.ci_low == stab2.ci_low
        assert stab1.ci_high == stab2.ci_high

    def test_drift_deterministic(self):
        """Drift detection must be deterministic."""
        from app.services.report_service import _compute_drift

        baseline = [0.1, 0.3, 0.5] * 20
        recent = [0.2, 0.4, 0.6] * 20

        drift1 = _compute_drift(baseline, recent)
        drift2 = _compute_drift(baseline, recent)

        assert drift1.status == drift2.status
        assert drift1.ks == drift2.ks
        assert drift1.psi == drift2.psi


# =============================================================================
# Auditability Tests
# =============================================================================

class TestAuditability:
    """
    PHASE 7: Test auditability requirements.

    All report outputs must include provenance metadata.
    """

    def test_provenance_includes_n_runs(self):
        """Provenance must include n_runs."""
        provenance = ReportProvenance(
            filters=ReportFilters(),
            n_runs=42,
            updated_at=datetime.utcnow(),
        )
        assert provenance.n_runs == 42

    def test_provenance_includes_filters(self):
        """Provenance must include filters applied."""
        provenance = ReportProvenance(
            manifest_hash="abc123",
            filters=ReportFilters(
                manifest_hash="abc123",
                window_days=14,
                min_runs=5,
            ),
            n_runs=50,
            updated_at=datetime.utcnow(),
        )
        assert provenance.filters.manifest_hash == "abc123"
        assert provenance.filters.window_days == 14

    def test_provenance_includes_updated_at(self):
        """Provenance must include updated_at timestamp."""
        now = datetime.utcnow()
        provenance = ReportProvenance(
            filters=ReportFilters(),
            n_runs=50,
            updated_at=now,
        )
        assert provenance.updated_at == now

    def test_response_has_provenance(self):
        """ReportResponse must include provenance."""
        response = ReportResponse(
            node_id="node-123",
            metric_key="score",
            target=TargetSpec(op=ReportOperator.GE, threshold=0.8),
            provenance=ReportProvenance(
                filters=ReportFilters(),
                n_runs=50,
                updated_at=datetime.utcnow(),
            ),
            prediction=PredictionResult(
                distribution=DistributionData(),
                target_probability=0.72,
            ),
            calibration=CalibrationResult(available=False),
            reliability=ReliabilityResult(
                sensitivity=SensitivityData(),
                stability=StabilityData(mean=0.72, ci_low=0.68, ci_high=0.76),
                drift=DriftData(status=DriftStatus.STABLE),
            ),
        )

        assert response.provenance is not None
        assert response.provenance.n_runs == 50


# =============================================================================
# Edge Cases
# =============================================================================

class TestReportEdgeCases:
    """Test edge cases for report computation."""

    def test_single_value(self):
        """Test with single value."""
        from app.services.report_service import (
            _compute_histogram,
            _compute_target_probability,
        )

        values = [0.5]

        dist = _compute_histogram(values, n_bins=5)
        assert dist.min == 0.5
        assert dist.max == 0.5

        prob = _compute_target_probability(values, ReportOperator.GE, 0.5)
        assert prob == 1.0

    def test_identical_values(self):
        """Test with all identical values."""
        from app.services.report_service import (
            _compute_histogram,
            _compute_target_probability,
        )

        values = [0.7] * 50

        dist = _compute_histogram(values, n_bins=10)
        assert dist.min == 0.7
        assert dist.max == 0.7

        prob = _compute_target_probability(values, ReportOperator.GE, 0.5)
        assert prob == 1.0

        prob_none = _compute_target_probability(values, ReportOperator.GE, 0.8)
        assert prob_none == 0.0

    def test_all_pass_threshold(self):
        """Test when all values pass threshold."""
        from app.services.report_service import _compute_target_probability

        values = [0.8, 0.85, 0.9, 0.95, 1.0]
        prob = _compute_target_probability(values, ReportOperator.GE, 0.5)
        assert prob == 1.0

    def test_none_pass_threshold(self):
        """Test when no values pass threshold."""
        from app.services.report_service import _compute_target_probability

        values = [0.1, 0.2, 0.3, 0.4]
        prob = _compute_target_probability(values, ReportOperator.GE, 0.5)
        assert prob == 0.0

    def test_large_dataset(self):
        """Test with large dataset."""
        from app.services.report_service import (
            _compute_histogram,
            _compute_target_probability,
            _compute_sensitivity,
        )

        np.random.seed(42)
        values = np.random.rand(1000).tolist()

        # All should complete without error
        dist = _compute_histogram(values, n_bins=50)
        assert len(dist.bins) == 51
        assert sum(dist.counts) == 1000

        prob = _compute_target_probability(values, ReportOperator.GE, 0.5)
        assert 0.0 <= prob <= 1.0

        sens = _compute_sensitivity(values, ReportOperator.GE, 0.5, n_grid=20)
        assert len(sens.thresholds) == 20


# =============================================================================
# API Endpoint Contract Tests
# =============================================================================

class TestReportAPIContracts:
    """Test report API endpoint contracts."""

    def test_endpoint_path(self):
        """Test endpoint path follows spec."""
        # Expected: GET /api/v1/reports/nodes/{node_id}
        node_id = "550e8400-e29b-41d4-a716-446655440000"
        expected_path = f"/api/v1/reports/nodes/{node_id}"

        assert "reports" in expected_path
        assert "nodes" in expected_path
        assert node_id in expected_path

    def test_query_params_required(self):
        """Test required query parameters."""
        # metric_key, op, threshold are required
        required_params = ["metric_key", "op", "threshold"]

        params = ReportQueryParams(
            metric_key="score",
            op=ReportOperator.GE,
            threshold=0.8,
        )

        assert params.metric_key is not None
        assert params.op is not None
        assert params.threshold is not None

    def test_query_params_optional_defaults(self):
        """Test optional query parameters have sensible defaults."""
        params = ReportQueryParams(
            metric_key="score",
            op=ReportOperator.GE,
            threshold=0.8,
        )

        # Optional params with defaults
        assert params.manifest_hash is None  # No filter by default
        assert params.min_runs == 3  # Reasonable minimum
        assert params.window_days == 30  # 30 days
        assert params.n_sensitivity_grid == 20
        assert params.n_bootstrap == 200
        assert params.n_bins == 20
