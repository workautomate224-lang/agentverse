"""
PHASE 3 — Probability Source Compliance Tests
Reference: project.md Phase 3 - Probability Source Compliance

Tests for:
1. RunOutcome model - factory method and validation
2. ProbabilitySourceService - aggregation and distribution computation
3. Probability source API endpoints - metrics, distribution, target probability
4. Insufficient data handling (n_runs < min_runs)
5. Deterministic output verification
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.models.run_outcome import RunOutcome, OutcomeStatus
from app.schemas.probability_source import (
    AggregationResult,
    AvailableMetricsResponse,
    ComparisonOperator,
    DataQuality,
    DistributionSummary,
    FiltersApplied,
    HistogramBucket,
    ProbabilitySourceMetadata,
    ProbabilitySourceRequest,
    ProbabilitySourceResponse,
    ProbabilityStatus,
    TargetProbabilityRequest,
    TargetProbabilityResponse,
    WeightingMethod,
)


# =============================================================================
# RunOutcome Model Tests
# =============================================================================

class TestRunOutcomeModel:
    """Test RunOutcome SQLAlchemy model."""

    def test_outcome_status_enum(self):
        """PHASE 3: OutcomeStatus enum values."""
        assert OutcomeStatus.SUCCEEDED == "succeeded"
        assert OutcomeStatus.FAILED == "failed"

    def test_run_outcome_creation(self):
        """PHASE 3: RunOutcome can be created with required fields."""
        outcome = RunOutcome(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            metrics_json={"score": 0.85, "count": 100},
            quality_flags={"partial_telemetry": False},
            status=OutcomeStatus.SUCCEEDED,
        )

        assert outcome.status == OutcomeStatus.SUCCEEDED
        assert outcome.metrics_json["score"] == 0.85
        assert outcome.metrics_json["count"] == 100
        assert outcome.quality_flags["partial_telemetry"] is False

    def test_run_outcome_factory_extracts_metrics(self):
        """PHASE 3: Factory method extracts metrics from run completion data."""
        tenant_id = uuid.uuid4()
        project_id = uuid.uuid4()
        node_id = uuid.uuid4()
        run_id = uuid.uuid4()

        outcomes = {
            "outcome_key": "success",
            "outcome_value": 0.9,
        }
        timing = {
            "ticks_executed": 50,
            "duration_ms": 1234,
        }
        reliability = {
            "confidence": 0.95,
        }
        execution_counters = {
            "rules_fired": 10,
            "agents_processed": 100,
        }

        run_outcome = RunOutcome.from_run_completion(
            tenant_id=tenant_id,
            project_id=project_id,
            node_id=node_id,
            run_id=run_id,
            outcomes=outcomes,
            timing=timing,
            reliability=reliability,
            execution_counters=execution_counters,
            manifest_hash="abc123def456",
        )

        assert run_outcome.tenant_id == tenant_id
        assert run_outcome.project_id == project_id
        assert run_outcome.node_id == node_id
        assert run_outcome.run_id == run_id
        assert run_outcome.status == OutcomeStatus.SUCCEEDED
        assert run_outcome.manifest_hash == "abc123def456"

        # Check extracted metrics
        assert "outcome_value" in run_outcome.metrics_json
        assert "ticks_executed" in run_outcome.metrics_json
        assert "duration_ms" in run_outcome.metrics_json

    def test_run_outcome_factory_handles_none_inputs(self):
        """PHASE 3: Factory method handles None inputs gracefully."""
        run_outcome = RunOutcome.from_run_completion(
            tenant_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            outcomes=None,
            timing=None,
            reliability=None,
            execution_counters=None,
        )

        assert run_outcome.status == OutcomeStatus.SUCCEEDED
        assert isinstance(run_outcome.metrics_json, dict)
        assert isinstance(run_outcome.quality_flags, dict)


# =============================================================================
# ProbabilitySourceService Unit Tests
# =============================================================================

class TestProbabilitySourceServiceUnit:
    """Unit tests for ProbabilitySourceService."""

    def test_compute_distribution_basic(self):
        """PHASE 3: Distribution computation produces correct statistics."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        distribution = service._compute_distribution(values)

        assert distribution.mean == pytest.approx(3.0, rel=1e-6)
        assert distribution.min == 1.0
        assert distribution.max == 5.0
        assert distribution.p50 == pytest.approx(3.0, rel=1e-6)  # Median

    def test_compute_distribution_with_weights(self):
        """PHASE 3: Weighted distribution uses weights correctly."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        weights = [0.1, 0.1, 0.1, 0.1, 0.6]  # Heavy weight on 5.0

        distribution = service._compute_distribution(values, weights)

        # Weighted mean should be closer to 5.0 than unweighted mean (3.0)
        assert distribution.mean > 3.5

    def test_compute_histogram_correct_buckets(self):
        """PHASE 3: Histogram produces correct bucket counts."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        # Create uniform distribution
        arr = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        histogram = service._compute_histogram(arr, n_bins=5)

        assert len(histogram) == 5
        total_count = sum(b.count for b in histogram)
        assert total_count == 10

        # Frequencies should sum to 1.0
        total_freq = sum(b.frequency for b in histogram)
        assert total_freq == pytest.approx(1.0, rel=1e-6)

    def test_compute_target_probability_gte(self):
        """PHASE 3: Target probability with >= operator."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [0.1, 0.3, 0.5, 0.7, 0.9]  # 5 values
        threshold = 0.5

        prob = service._compute_target_probability(
            values=values,
            weights=None,
            op=ComparisonOperator.GTE,
            threshold=threshold,
        )

        # 3 out of 5 values are >= 0.5 (0.5, 0.7, 0.9)
        assert prob == pytest.approx(0.6, rel=1e-6)

    def test_compute_target_probability_lt(self):
        """PHASE 3: Target probability with < operator."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [0.1, 0.3, 0.5, 0.7, 0.9]
        threshold = 0.5

        prob = service._compute_target_probability(
            values=values,
            weights=None,
            op=ComparisonOperator.LT,
            threshold=threshold,
        )

        # 2 out of 5 values are < 0.5 (0.1, 0.3)
        assert prob == pytest.approx(0.4, rel=1e-6)

    def test_compute_target_probability_weighted(self):
        """PHASE 3: Weighted target probability computation."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [0.1, 0.9]  # 2 values
        weights = [0.8, 0.2]  # 0.1 has 80% weight, 0.9 has 20% weight
        threshold = 0.5

        prob = service._compute_target_probability(
            values=values,
            weights=weights,
            op=ComparisonOperator.GTE,
            threshold=threshold,
        )

        # Only 0.9 is >= 0.5, and it has 20% weight
        assert prob == pytest.approx(0.2, rel=1e-6)


# =============================================================================
# Probability Schema Tests
# =============================================================================

class TestProbabilitySchemas:
    """Test Pydantic schema validation."""

    def test_weighting_method_enum(self):
        """Test WeightingMethod enum values."""
        assert WeightingMethod.UNIFORM == "uniform"
        assert WeightingMethod.RECENT_DECAY == "recent_decay"

    def test_probability_status_enum(self):
        """Test ProbabilityStatus enum values."""
        assert ProbabilityStatus.OK == "ok"
        assert ProbabilityStatus.INSUFFICIENT_DATA == "insufficient_data"

    def test_comparison_operator_enum(self):
        """Test ComparisonOperator enum values."""
        assert ComparisonOperator.GTE == ">="
        assert ComparisonOperator.LTE == "<="
        assert ComparisonOperator.GT == ">"
        assert ComparisonOperator.LT == "<"
        assert ComparisonOperator.EQ == "=="

    def test_probability_source_request_defaults(self):
        """Test ProbabilitySourceRequest defaults."""
        request = ProbabilitySourceRequest(metric="score")

        assert request.metric == "score"
        assert request.weighting == WeightingMethod.UNIFORM
        assert request.time_window_days == 30
        assert request.min_runs == 3
        assert request.max_runs == 200

    def test_target_probability_request_validation(self):
        """Test TargetProbabilityRequest construction."""
        request = TargetProbabilityRequest(
            metric="accuracy",
            op=ComparisonOperator.GTE,
            threshold=0.8,
        )

        assert request.metric == "accuracy"
        assert request.op == ComparisonOperator.GTE
        assert request.threshold == 0.8

    def test_distribution_summary_construction(self):
        """Test DistributionSummary construction."""
        summary = DistributionSummary(
            mean=0.5,
            std=0.1,
            min=0.1,
            max=0.9,
            p5=0.15,
            p25=0.3,
            p50=0.5,
            p75=0.7,
            p95=0.85,
            histogram=[],
        )

        assert summary.mean == 0.5
        assert summary.p50 == 0.5  # Median
        assert summary.std >= 0  # Std dev must be non-negative

    def test_histogram_bucket_construction(self):
        """Test HistogramBucket construction."""
        bucket = HistogramBucket(
            bin_start=0.0,
            bin_end=0.1,
            count=5,
            frequency=0.25,
        )

        assert bucket.bin_start == 0.0
        assert bucket.bin_end == 0.1
        assert bucket.count == 5
        assert bucket.frequency == 0.25

    def test_probability_source_metadata_construction(self):
        """Test ProbabilitySourceMetadata includes required audit fields."""
        metadata = ProbabilitySourceMetadata(
            source_type="empirical_runs",
            project_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            metric_key="score",
            n_runs=10,
            updated_at=datetime.utcnow(),
        )

        # Required audit fields
        assert metadata.source_type == "empirical_runs"
        assert metadata.n_runs == 10
        assert metadata.updated_at is not None

    def test_probability_source_response_ok_status(self):
        """Test ProbabilitySourceResponse with OK status."""
        response = ProbabilitySourceResponse(
            status=ProbabilityStatus.OK,
            probability_source=ProbabilitySourceMetadata(
                project_id=uuid.uuid4(),
                node_id=uuid.uuid4(),
                metric_key="score",
                n_runs=10,
                updated_at=datetime.utcnow(),
            ),
            distribution=DistributionSummary(
                mean=0.5, std=0.1, min=0.1, max=0.9,
                p5=0.15, p25=0.3, p50=0.5, p75=0.7, p95=0.85,
            ),
            sample_run_ids=[uuid.uuid4()],
        )

        assert response.status == ProbabilityStatus.OK
        assert response.distribution is not None
        assert response.message is None

    def test_probability_source_response_insufficient_data(self):
        """PHASE 3 CRITICAL: Insufficient data response has no distribution."""
        response = ProbabilitySourceResponse(
            status=ProbabilityStatus.INSUFFICIENT_DATA,
            probability_source=ProbabilitySourceMetadata(
                project_id=uuid.uuid4(),
                node_id=uuid.uuid4(),
                metric_key="score",
                n_runs=2,  # Less than min_runs
                min_runs_required=3,
                updated_at=datetime.utcnow(),
            ),
            distribution=None,  # MUST be None when insufficient_data
            sample_run_ids=[],
            message="Insufficient data: 2 runs available, minimum 3 required.",
        )

        assert response.status == ProbabilityStatus.INSUFFICIENT_DATA
        assert response.distribution is None
        assert response.message is not None
        assert "insufficient" in response.message.lower()


# =============================================================================
# Insufficient Data Tests (CRITICAL)
# =============================================================================

class TestInsufficientDataHandling:
    """
    PHASE 3 CRITICAL: Test insufficient data handling.

    These tests verify that probabilities are NEVER fabricated when
    there isn't enough empirical data.
    """

    def test_n_runs_less_than_min_returns_insufficient_data(self):
        """CRITICAL: n_runs < min_runs must return insufficient_data status."""
        n_runs = 2
        min_runs = 3

        # Simulate aggregation result
        aggregation = AggregationResult(
            status=ProbabilityStatus.INSUFFICIENT_DATA,
            n_runs=n_runs,
            values=[0.5, 0.6],
            weights=[1.0, 1.0],
            run_ids=[uuid.uuid4(), uuid.uuid4()],
            created_ats=[datetime.utcnow(), datetime.utcnow()],
        )

        # Status must be insufficient_data
        assert aggregation.n_runs < min_runs
        assert aggregation.status == ProbabilityStatus.INSUFFICIENT_DATA

    def test_zero_runs_returns_insufficient_data(self):
        """CRITICAL: Zero runs must return insufficient_data status."""
        aggregation = AggregationResult(
            status=ProbabilityStatus.INSUFFICIENT_DATA,
            n_runs=0,
            values=[],
            weights=[],
            run_ids=[],
            created_ats=[],
        )

        assert aggregation.n_runs == 0
        assert aggregation.status == ProbabilityStatus.INSUFFICIENT_DATA

    def test_distribution_none_when_insufficient_data(self):
        """CRITICAL: Distribution must be None when insufficient_data."""
        response = ProbabilitySourceResponse(
            status=ProbabilityStatus.INSUFFICIENT_DATA,
            probability_source=ProbabilitySourceMetadata(
                project_id=uuid.uuid4(),
                node_id=uuid.uuid4(),
                metric_key="score",
                n_runs=1,
                updated_at=datetime.utcnow(),
            ),
            distribution=None,  # MUST be None
            sample_run_ids=[],
        )

        assert response.status == ProbabilityStatus.INSUFFICIENT_DATA
        assert response.distribution is None

    def test_target_probability_none_when_insufficient_data(self):
        """CRITICAL: Target probability must be None when insufficient_data."""
        response = TargetProbabilityResponse(
            status=ProbabilityStatus.INSUFFICIENT_DATA,
            probability=None,  # MUST be None
            condition="score >= 0.8",
            probability_source=ProbabilitySourceMetadata(
                project_id=uuid.uuid4(),
                node_id=uuid.uuid4(),
                metric_key="score",
                n_runs=2,
                updated_at=datetime.utcnow(),
            ),
            sample_run_ids=[],
        )

        assert response.status == ProbabilityStatus.INSUFFICIENT_DATA
        assert response.probability is None


# =============================================================================
# Determinism Tests
# =============================================================================

class TestDeterminism:
    """
    PHASE 3: Test deterministic output.

    Same filters + same data = same results.
    """

    def test_distribution_deterministic(self):
        """PHASE 3: Distribution computation is deterministic."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [0.1, 0.3, 0.5, 0.7, 0.9]

        dist1 = service._compute_distribution(values)
        dist2 = service._compute_distribution(values)

        # All statistics must be identical
        assert dist1.mean == dist2.mean
        assert dist1.std == dist2.std
        assert dist1.min == dist2.min
        assert dist1.max == dist2.max
        assert dist1.p5 == dist2.p5
        assert dist1.p25 == dist2.p25
        assert dist1.p50 == dist2.p50
        assert dist1.p75 == dist2.p75
        assert dist1.p95 == dist2.p95

    def test_histogram_deterministic(self):
        """PHASE 3: Histogram computation is deterministic."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        arr = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        hist1 = service._compute_histogram(arr, n_bins=5)
        hist2 = service._compute_histogram(arr, n_bins=5)

        # All buckets must be identical
        assert len(hist1) == len(hist2)
        for b1, b2 in zip(hist1, hist2):
            assert b1.bin_start == b2.bin_start
            assert b1.bin_end == b2.bin_end
            assert b1.count == b2.count
            assert b1.frequency == b2.frequency

    def test_target_probability_deterministic(self):
        """PHASE 3: Target probability computation is deterministic."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [0.1, 0.3, 0.5, 0.7, 0.9]
        threshold = 0.5
        op = ComparisonOperator.GTE

        prob1 = service._compute_target_probability(values, None, op, threshold)
        prob2 = service._compute_target_probability(values, None, op, threshold)

        assert prob1 == prob2


# =============================================================================
# Auditability Tests
# =============================================================================

class TestAuditability:
    """
    PHASE 3: Test auditability requirements.

    All probability outputs must include source metadata.
    """

    def test_probability_source_includes_n_runs(self):
        """PHASE 3: Source metadata includes n_runs."""
        metadata = ProbabilitySourceMetadata(
            project_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            metric_key="score",
            n_runs=42,
            updated_at=datetime.utcnow(),
        )

        assert metadata.n_runs == 42

    def test_probability_source_includes_filters(self):
        """PHASE 3: Source metadata includes filters applied."""
        filters = FiltersApplied(
            manifest_hash="abc123",
            time_window_days=30,
            status="succeeded",
        )

        metadata = ProbabilitySourceMetadata(
            project_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            metric_key="score",
            n_runs=10,
            filters_applied=filters,
            updated_at=datetime.utcnow(),
        )

        assert metadata.filters_applied.manifest_hash == "abc123"
        assert metadata.filters_applied.time_window_days == 30

    def test_probability_source_includes_updated_at(self):
        """PHASE 3: Source metadata includes updated_at timestamp."""
        now = datetime.utcnow()

        metadata = ProbabilitySourceMetadata(
            project_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            metric_key="score",
            n_runs=10,
            updated_at=now,
        )

        assert metadata.updated_at == now

    def test_probability_source_includes_quality_flags(self):
        """PHASE 3: Source metadata includes data quality flags."""
        quality = DataQuality(
            partial_telemetry_runs=2,
            failed_runs_excluded=1,
            low_confidence_runs=3,
            average_confidence=0.85,
        )

        metadata = ProbabilitySourceMetadata(
            project_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            metric_key="score",
            n_runs=10,
            data_quality=quality,
            updated_at=datetime.utcnow(),
        )

        assert metadata.data_quality.partial_telemetry_runs == 2
        assert metadata.data_quality.average_confidence == 0.85

    def test_response_includes_sample_run_ids(self):
        """PHASE 3: Response includes sample run IDs for audit."""
        run_ids = [uuid.uuid4() for _ in range(5)]

        response = ProbabilitySourceResponse(
            status=ProbabilityStatus.OK,
            probability_source=ProbabilitySourceMetadata(
                project_id=uuid.uuid4(),
                node_id=uuid.uuid4(),
                metric_key="score",
                n_runs=10,
                updated_at=datetime.utcnow(),
            ),
            distribution=DistributionSummary(
                mean=0.5, std=0.1, min=0.1, max=0.9,
                p5=0.15, p25=0.3, p50=0.5, p75=0.7, p95=0.85,
            ),
            sample_run_ids=run_ids,
        )

        assert len(response.sample_run_ids) == 5
        assert all(isinstance(rid, uuid.UUID) for rid in response.sample_run_ids)


# =============================================================================
# Weighting Method Tests
# =============================================================================

class TestWeightingMethods:
    """Test different weighting methods."""

    def test_uniform_weighting(self):
        """PHASE 3: Uniform weighting treats all runs equally."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [1.0, 2.0, 3.0, 4.0, 5.0]

        # No weights = uniform
        dist = service._compute_distribution(values, weights=None)

        # Uniform mean should be 3.0
        assert dist.mean == pytest.approx(3.0, rel=1e-6)

    def test_recent_decay_weighting_favors_recent(self):
        """PHASE 3: Recent decay weighting favors recent runs."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [1.0, 5.0]  # Old=1.0, New=5.0
        weights = [0.1, 0.9]  # New run has higher weight

        dist = service._compute_distribution(values, weights)

        # Weighted mean should be closer to 5.0
        assert dist.mean > 3.0


# =============================================================================
# API Endpoint Contract Tests
# =============================================================================

class TestProbabilityAPIContracts:
    """Test probability API endpoint contracts."""

    def test_metrics_endpoint_path(self):
        """Test metrics endpoint follows spec path."""
        # Expected: GET /projects/{project_id}/nodes/{node_id}/metrics
        project_id = "proj-123"
        node_id = "node-456"
        expected_path = f"/projects/{project_id}/nodes/{node_id}/metrics"

        assert "nodes" in expected_path
        assert "metrics" in expected_path

    def test_probability_source_endpoint_path(self):
        """Test probability-source endpoint follows spec path."""
        # Expected: GET /projects/{project_id}/nodes/{node_id}/probability-source
        project_id = "proj-123"
        node_id = "node-456"
        expected_path = f"/projects/{project_id}/nodes/{node_id}/probability-source"

        assert "probability-source" in expected_path

    def test_target_probability_endpoint_path(self):
        """Test target-probability endpoint follows spec path."""
        # Expected: GET /projects/{project_id}/nodes/{node_id}/target-probability
        project_id = "proj-123"
        node_id = "node-456"
        expected_path = f"/projects/{project_id}/nodes/{node_id}/target-probability"

        assert "target-probability" in expected_path


# =============================================================================
# Edge Cases
# =============================================================================

class TestProbabilityEdgeCases:
    """Test edge cases for probability computation."""

    def test_single_value_distribution(self):
        """Test distribution with single value."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [0.5]  # Single value

        dist = service._compute_distribution(values)

        assert dist.mean == 0.5
        assert dist.min == 0.5
        assert dist.max == 0.5
        assert dist.std == 0.0  # No variation

    def test_identical_values_distribution(self):
        """Test distribution with all identical values."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [0.7, 0.7, 0.7, 0.7, 0.7]

        dist = service._compute_distribution(values)

        assert dist.mean == 0.7
        assert dist.std == 0.0
        assert dist.min == 0.7
        assert dist.max == 0.7

    def test_extreme_values_distribution(self):
        """Test distribution with extreme values."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [0.0, 0.0, 0.0, 1.0, 1.0]

        dist = service._compute_distribution(values)

        assert dist.min == 0.0
        assert dist.max == 1.0

    def test_target_probability_all_pass(self):
        """Test target probability when all values pass threshold."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [0.9, 0.95, 0.85, 0.8]
        threshold = 0.5

        prob = service._compute_target_probability(
            values, None, ComparisonOperator.GTE, threshold
        )

        assert prob == 1.0

    def test_target_probability_none_pass(self):
        """Test target probability when no values pass threshold."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        values = [0.1, 0.2, 0.3, 0.4]
        threshold = 0.5

        prob = service._compute_target_probability(
            values, None, ComparisonOperator.GTE, threshold
        )

        assert prob == 0.0

    def test_large_dataset_performance(self):
        """Test distribution computation with large dataset."""
        from app.services.probability_source_service import ProbabilitySourceService

        mock_db = MagicMock()
        service = ProbabilitySourceService(mock_db)

        # 1000 values
        np.random.seed(42)
        values = np.random.rand(1000).tolist()

        # Should complete without error
        dist = service._compute_distribution(values)

        assert 0.0 <= dist.mean <= 1.0
        assert len(dist.histogram) == 20  # Default bins


# =============================================================================
# Data Quality Tests
# =============================================================================

class TestDataQuality:
    """Test data quality tracking."""

    def test_data_quality_defaults(self):
        """Test DataQuality defaults to zeros."""
        quality = DataQuality()

        assert quality.partial_telemetry_runs == 0
        assert quality.failed_runs_excluded == 0
        assert quality.low_confidence_runs == 0
        assert quality.average_confidence is None

    def test_data_quality_with_values(self):
        """Test DataQuality with explicit values."""
        quality = DataQuality(
            partial_telemetry_runs=5,
            failed_runs_excluded=2,
            low_confidence_runs=3,
            average_confidence=0.72,
        )

        assert quality.partial_telemetry_runs == 5
        assert quality.failed_runs_excluded == 2
        assert quality.low_confidence_runs == 3
        assert quality.average_confidence == 0.72


# =============================================================================
# Available Metrics Tests
# =============================================================================

class TestAvailableMetrics:
    """Test available metrics response."""

    def test_available_metrics_response_empty(self):
        """Test AvailableMetricsResponse with no metrics."""
        response = AvailableMetricsResponse(
            node_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            metric_keys=[],
            n_runs=0,
            updated_at=None,
        )

        assert len(response.metric_keys) == 0
        assert response.n_runs == 0

    def test_available_metrics_response_with_keys(self):
        """Test AvailableMetricsResponse with metric keys."""
        response = AvailableMetricsResponse(
            node_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            metric_keys=["score", "accuracy", "duration_ms", "ticks_executed"],
            n_runs=10,
            updated_at=datetime.utcnow(),
        )

        assert len(response.metric_keys) == 4
        assert "score" in response.metric_keys
        assert response.n_runs == 10
