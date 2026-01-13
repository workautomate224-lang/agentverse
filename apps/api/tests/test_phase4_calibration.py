"""
PHASE 4 — Calibration Minimal Closed Loop Tests
Reference: project.md Phase 4 - Calibration Lab Backend

Tests for:
1. Ground Truth Dataset model and schema validation
2. Ground Truth Label model and bulk upsert
3. Calibration Job lifecycle
4. Calibration Algorithm correctness
5. Determinism verification (same data = same results)
6. Insufficient data handling
7. Auditability requirements
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.models.calibration import (
    CalibrationIteration,
    CalibrationJob,
    CalibrationJobStatus,
    GroundTruthDataset,
    GroundTruthLabel,
)
from app.schemas.calibration import (
    BulkUpsertLabelsRequest,
    BulkUpsertLabelsResponse,
    CalibrationBin,
    CalibrationConfig,
    CalibrationIterationResponse,
    CalibrationJobResponse,
    CalibrationJobStatus as CalibrationJobStatusEnum,
    CalibrationMetrics,
    CalibrationResultResponse,
    CalibrationSample,
    CalibrationStartRequest,
    ComparisonOperator,
    GroundTruthDatasetCreate,
    GroundTruthDatasetResponse,
    GroundTruthLabelInput,
    GroundTruthLabelResponse,
    WeightingMethod,
)


# =============================================================================
# Ground Truth Dataset Model Tests
# =============================================================================

class TestGroundTruthDatasetModel:
    """Test GroundTruthDataset SQLAlchemy model."""

    def test_dataset_creation(self):
        """PHASE 4: GroundTruthDataset can be created with required fields."""
        dataset = GroundTruthDataset(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            name="Test Dataset",
            description="A test dataset for calibration",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert dataset.name == "Test Dataset"
        assert dataset.description == "A test dataset for calibration"
        assert dataset.id is not None
        assert dataset.tenant_id is not None

    def test_dataset_repr(self):
        """PHASE 4: Dataset has a useful __repr__."""
        dataset_id = uuid.uuid4()
        dataset = GroundTruthDataset(
            id=dataset_id,
            tenant_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            name="My Dataset",
        )

        assert "GroundTruthDataset" in repr(dataset)
        assert "My Dataset" in repr(dataset)


# =============================================================================
# Ground Truth Label Model Tests
# =============================================================================

class TestGroundTruthLabelModel:
    """Test GroundTruthLabel SQLAlchemy model."""

    def test_label_creation(self):
        """PHASE 4: GroundTruthLabel can be created with required fields."""
        label = GroundTruthLabel(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            dataset_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            label=1,
            notes="Verified outcome",
            json_meta={"source": "manual"},
            created_at=datetime.utcnow(),
        )

        assert label.label == 1
        assert label.notes == "Verified outcome"
        assert label.json_meta["source"] == "manual"

    def test_label_binary_values(self):
        """PHASE 4: Label must be 0 or 1."""
        # Label = 0
        label_false = GroundTruthLabel(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            dataset_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            label=0,
        )
        assert label_false.label == 0

        # Label = 1
        label_true = GroundTruthLabel(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            dataset_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            label=1,
        )
        assert label_true.label == 1


# =============================================================================
# Calibration Job Model Tests
# =============================================================================

class TestCalibrationJobModel:
    """Test CalibrationJob SQLAlchemy model."""

    def test_job_creation(self):
        """PHASE 4: CalibrationJob can be created with required fields."""
        job = CalibrationJob(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            dataset_id=uuid.uuid4(),
            status=CalibrationJobStatus.QUEUED.value,
            config_json={
                "target_accuracy": 0.85,
                "max_iterations": 10,
                "metric_key": "outcome_value",
            },
            progress=0,
            total_iterations=10,
            created_at=datetime.utcnow(),
        )

        assert job.status == "queued"
        assert job.config_json["target_accuracy"] == 0.85
        assert job.progress == 0
        assert job.total_iterations == 10

    def test_job_status_enum(self):
        """PHASE 4: CalibrationJobStatus enum values."""
        assert CalibrationJobStatus.QUEUED == "queued"
        assert CalibrationJobStatus.RUNNING == "running"
        assert CalibrationJobStatus.SUCCEEDED == "succeeded"
        assert CalibrationJobStatus.FAILED == "failed"
        assert CalibrationJobStatus.CANCELED == "canceled"

    def test_job_is_terminal(self):
        """PHASE 4: Job can check if in terminal state."""
        job = CalibrationJob(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            dataset_id=uuid.uuid4(),
        )

        # QUEUED is not terminal
        job.status = CalibrationJobStatus.QUEUED.value
        assert not job.is_terminal()

        # RUNNING is not terminal
        job.status = CalibrationJobStatus.RUNNING.value
        assert not job.is_terminal()

        # SUCCEEDED is terminal
        job.status = CalibrationJobStatus.SUCCEEDED.value
        assert job.is_terminal()

        # FAILED is terminal
        job.status = CalibrationJobStatus.FAILED.value
        assert job.is_terminal()

        # CANCELED is terminal
        job.status = CalibrationJobStatus.CANCELED.value
        assert job.is_terminal()


# =============================================================================
# Calibration Iteration Model Tests
# =============================================================================

class TestCalibrationIterationModel:
    """Test CalibrationIteration SQLAlchemy model."""

    def test_iteration_creation(self):
        """PHASE 4: CalibrationIteration can be created with required fields."""
        iteration = CalibrationIteration(
            id=uuid.uuid4(),
            job_id=uuid.uuid4(),
            iter_index=0,
            params_json={"bin_count": 10},
            metrics_json={
                "accuracy": 0.85,
                "brier_score": 0.12,
                "ece": 0.05,
            },
            mapping_json={"bins": []},
            created_at=datetime.utcnow(),
        )

        assert iteration.iter_index == 0
        assert iteration.params_json["bin_count"] == 10
        assert iteration.metrics_json["accuracy"] == 0.85


# =============================================================================
# Pydantic Schema Tests
# =============================================================================

class TestCalibrationSchemas:
    """Test Pydantic schema validation."""

    def test_ground_truth_dataset_create(self):
        """PHASE 4: GroundTruthDatasetCreate schema validation."""
        data = GroundTruthDatasetCreate(
            name="Test Dataset",
            description="Optional description",
        )

        assert data.name == "Test Dataset"
        assert data.description == "Optional description"

    def test_ground_truth_dataset_create_name_required(self):
        """PHASE 4: GroundTruthDatasetCreate requires name."""
        with pytest.raises(Exception):
            GroundTruthDatasetCreate(description="No name")

    def test_ground_truth_dataset_create_name_min_length(self):
        """PHASE 4: GroundTruthDatasetCreate name must be non-empty."""
        with pytest.raises(Exception):
            GroundTruthDatasetCreate(name="")

    def test_ground_truth_label_input(self):
        """PHASE 4: GroundTruthLabelInput schema validation."""
        label = GroundTruthLabelInput(
            run_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            label=1,
            notes="Test note",
        )

        assert label.label == 1
        assert label.notes == "Test note"

    def test_ground_truth_label_input_label_bounds(self):
        """PHASE 4: Label must be 0 or 1."""
        # Valid: 0
        label_0 = GroundTruthLabelInput(
            run_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            label=0,
        )
        assert label_0.label == 0

        # Valid: 1
        label_1 = GroundTruthLabelInput(
            run_id=uuid.uuid4(),
            node_id=uuid.uuid4(),
            label=1,
        )
        assert label_1.label == 1

        # Invalid: 2
        with pytest.raises(Exception):
            GroundTruthLabelInput(
                run_id=uuid.uuid4(),
                node_id=uuid.uuid4(),
                label=2,
            )

    def test_bulk_upsert_labels_request(self):
        """PHASE 4: BulkUpsertLabelsRequest schema validation."""
        labels = [
            GroundTruthLabelInput(
                run_id=uuid.uuid4(),
                node_id=uuid.uuid4(),
                label=1,
            )
            for _ in range(5)
        ]

        request = BulkUpsertLabelsRequest(labels=labels)
        assert len(request.labels) == 5

    def test_bulk_upsert_labels_request_min_length(self):
        """PHASE 4: BulkUpsertLabelsRequest must have at least 1 label."""
        with pytest.raises(Exception):
            BulkUpsertLabelsRequest(labels=[])

    def test_calibration_start_request(self):
        """PHASE 4: CalibrationStartRequest schema validation."""
        request = CalibrationStartRequest(
            node_id=uuid.uuid4(),
            dataset_id=uuid.uuid4(),
            target_accuracy=0.9,
            max_iterations=5,
            metric_key="score",
        )

        assert request.target_accuracy == 0.9
        assert request.max_iterations == 5
        assert request.metric_key == "score"

    def test_calibration_start_request_defaults(self):
        """PHASE 4: CalibrationStartRequest has sensible defaults."""
        request = CalibrationStartRequest(
            node_id=uuid.uuid4(),
            dataset_id=uuid.uuid4(),
        )

        assert request.target_accuracy == 0.85
        assert request.max_iterations == 10
        assert request.metric_key == "outcome_value"
        assert request.weighting == WeightingMethod.UNIFORM

    def test_calibration_start_request_threshold_validation(self):
        """PHASE 4: Threshold required when op is provided."""
        with pytest.raises(Exception):
            CalibrationStartRequest(
                node_id=uuid.uuid4(),
                dataset_id=uuid.uuid4(),
                op=ComparisonOperator.GTE,
                threshold=None,  # Missing threshold
            )

    def test_calibration_metrics(self):
        """PHASE 4: CalibrationMetrics schema construction."""
        metrics = CalibrationMetrics(
            accuracy=0.85,
            brier_score=0.12,
            ece=0.05,
            n_samples=100,
        )

        assert metrics.accuracy == 0.85
        assert metrics.brier_score == 0.12
        assert metrics.ece == 0.05
        assert metrics.n_samples == 100

    def test_calibration_bin(self):
        """PHASE 4: CalibrationBin schema construction."""
        bin_data = CalibrationBin(
            bin_start=0.0,
            bin_end=0.2,
            calibrated_prob=0.15,
            n_samples=20,
            empirical_rate=0.15,
        )

        assert bin_data.bin_start == 0.0
        assert bin_data.bin_end == 0.2
        assert bin_data.calibrated_prob == 0.15

    def test_calibration_sample(self):
        """PHASE 4: CalibrationSample internal schema."""
        sample = CalibrationSample(
            run_id=uuid.uuid4(),
            predicted_value=0.75,
            label=1,
            weight=1.0,
        )

        assert sample.predicted_value == 0.75
        assert sample.label == 1
        assert sample.weight == 1.0


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    """Test enum values."""

    def test_comparison_operator_enum(self):
        """PHASE 4: ComparisonOperator enum values."""
        assert ComparisonOperator.GTE == ">="
        assert ComparisonOperator.LTE == "<="
        assert ComparisonOperator.GT == ">"
        assert ComparisonOperator.LT == "<"
        assert ComparisonOperator.EQ == "=="

    def test_weighting_method_enum(self):
        """PHASE 4: WeightingMethod enum values."""
        assert WeightingMethod.UNIFORM == "uniform"
        assert WeightingMethod.RECENT_DECAY == "recent_decay"

    def test_calibration_job_status_enum_schema(self):
        """PHASE 4: CalibrationJobStatus schema enum values."""
        assert CalibrationJobStatusEnum.QUEUED == "queued"
        assert CalibrationJobStatusEnum.RUNNING == "running"
        assert CalibrationJobStatusEnum.SUCCEEDED == "succeeded"
        assert CalibrationJobStatusEnum.FAILED == "failed"
        assert CalibrationJobStatusEnum.CANCELED == "canceled"


# =============================================================================
# Calibration Algorithm Tests (Determinism)
# =============================================================================

class TestCalibrationAlgorithmDeterminism:
    """
    PHASE 4: Test calibration algorithm determinism.

    Same config + same data = same results (C5 compliance).
    """

    def test_compute_calibration_deterministic(self):
        """PHASE 4: Calibration computation is deterministic."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        # Create test samples
        np.random.seed(42)
        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=float(v),
                label=int(v > 0.5),
                weight=1.0,
            )
            for v in np.random.rand(100)
        ]

        # Run calibration twice
        mapping1, metrics1 = service._compute_calibration(
            samples=samples,
            bin_count=10,
        )
        mapping2, metrics2 = service._compute_calibration(
            samples=samples,
            bin_count=10,
        )

        # Results must be identical
        assert metrics1.accuracy == metrics2.accuracy
        assert metrics1.brier_score == metrics2.brier_score
        assert metrics1.ece == metrics2.ece

        # Mapping must be identical
        assert len(mapping1) == len(mapping2)
        for b1, b2 in zip(mapping1, mapping2):
            assert b1.bin_start == b2.bin_start
            assert b1.bin_end == b2.bin_end
            assert b1.calibrated_prob == b2.calibrated_prob

    def test_compute_calibration_with_threshold_deterministic(self):
        """PHASE 4: Calibration with threshold is deterministic."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=v,
                label=int(v > 0.5),
                weight=1.0,
            )
            for v in [0.1, 0.3, 0.5, 0.7, 0.9]
        ]

        # Run with threshold twice
        _, metrics1 = service._compute_calibration(
            samples=samples,
            bin_count=5,
            op=ComparisonOperator.GTE,
            threshold=0.5,
        )
        _, metrics2 = service._compute_calibration(
            samples=samples,
            bin_count=5,
            op=ComparisonOperator.GTE,
            threshold=0.5,
        )

        assert metrics1.accuracy == metrics2.accuracy


# =============================================================================
# Calibration Algorithm Correctness Tests
# =============================================================================

class TestCalibrationAlgorithmCorrectness:
    """Test calibration algorithm produces correct results."""

    def test_accuracy_computation_perfect(self):
        """PHASE 4: Perfect predictions yield 100% accuracy."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        # Perfect correlation: high values = label 1, low values = label 0
        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=float(i) / 10,
                label=1 if i >= 5 else 0,
                weight=1.0,
            )
            for i in range(10)
        ]

        _, metrics = service._compute_calibration(
            samples=samples,
            bin_count=2,
        )

        # With perfect separation and 2 bins, accuracy should be 1.0
        assert metrics.accuracy == 1.0

    def test_brier_score_range(self):
        """PHASE 4: Brier score is in [0, 1] range."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        np.random.seed(42)
        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=float(v),
                label=int(v > 0.5),
                weight=1.0,
            )
            for v in np.random.rand(50)
        ]

        _, metrics = service._compute_calibration(
            samples=samples,
            bin_count=5,
        )

        assert 0.0 <= metrics.brier_score <= 1.0

    def test_ece_range(self):
        """PHASE 4: ECE (Expected Calibration Error) is non-negative."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        np.random.seed(42)
        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=float(v),
                label=int(v > 0.5),
                weight=1.0,
            )
            for v in np.random.rand(50)
        ]

        _, metrics = service._compute_calibration(
            samples=samples,
            bin_count=5,
        )

        assert metrics.ece >= 0.0

    def test_bin_count_affects_result(self):
        """PHASE 4: Different bin counts produce different results."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        np.random.seed(42)
        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=float(v),
                label=int(v > 0.5),
                weight=1.0,
            )
            for v in np.random.rand(100)
        ]

        mapping_5, _ = service._compute_calibration(samples=samples, bin_count=5)
        mapping_10, _ = service._compute_calibration(samples=samples, bin_count=10)

        # Different bin counts should produce different number of bins
        assert len(mapping_5) == 5
        assert len(mapping_10) == 10


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestCalibrationEdgeCases:
    """Test edge cases for calibration."""

    def test_empty_samples(self):
        """PHASE 4: Empty samples returns zero metrics."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        mapping, metrics = service._compute_calibration(
            samples=[],
            bin_count=10,
        )

        assert len(mapping) == 0
        assert metrics.accuracy == 0.0
        assert metrics.brier_score == 1.0
        assert metrics.ece == 1.0
        assert metrics.n_samples == 0

    def test_single_sample(self):
        """PHASE 4: Single sample calibration."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=0.5,
                label=1,
                weight=1.0,
            )
        ]

        mapping, metrics = service._compute_calibration(
            samples=samples,
            bin_count=5,
        )

        assert metrics.n_samples == 1

    def test_identical_values(self):
        """PHASE 4: All identical predicted values."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        # All samples have the same predicted value
        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=0.5,
                label=i % 2,  # Alternating labels
                weight=1.0,
            )
            for i in range(10)
        ]

        # Should handle gracefully
        mapping, metrics = service._compute_calibration(
            samples=samples,
            bin_count=5,
        )

        assert metrics.n_samples == 10

    def test_all_positive_labels(self):
        """PHASE 4: All samples have label=1."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=float(i) / 10,
                label=1,  # All positive
                weight=1.0,
            )
            for i in range(10)
        ]

        mapping, metrics = service._compute_calibration(
            samples=samples,
            bin_count=5,
        )

        # All bins should have calibrated_prob = 1.0
        for bin_data in mapping:
            if bin_data.n_samples > 0:
                assert bin_data.calibrated_prob == pytest.approx(1.0, rel=1e-6)

    def test_all_negative_labels(self):
        """PHASE 4: All samples have label=0."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=float(i) / 10,
                label=0,  # All negative
                weight=1.0,
            )
            for i in range(10)
        ]

        mapping, metrics = service._compute_calibration(
            samples=samples,
            bin_count=5,
        )

        # All bins should have calibrated_prob = 0.0
        for bin_data in mapping:
            if bin_data.n_samples > 0:
                assert bin_data.calibrated_prob == pytest.approx(0.0, rel=1e-6)


# =============================================================================
# Weighting Tests
# =============================================================================

class TestCalibrationWeighting:
    """Test weighting methods."""

    def test_uniform_weighting_equal(self):
        """PHASE 4: Uniform weighting treats all samples equally."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=float(i) / 10,
                label=1 if i >= 5 else 0,
                weight=1.0,  # Uniform weights
            )
            for i in range(10)
        ]

        mapping, metrics = service._compute_calibration(
            samples=samples,
            bin_count=2,
        )

        assert metrics.n_samples == 10

    def test_weighted_calibration(self):
        """PHASE 4: Weighted samples affect calibration."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        # Heavy weight on high-value, positive samples
        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=0.1,
                label=0,
                weight=0.1,
            ),
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=0.9,
                label=1,
                weight=0.9,
            ),
        ]

        mapping, metrics = service._compute_calibration(
            samples=samples,
            bin_count=2,
        )

        # Should complete without error
        assert metrics.n_samples == 2


# =============================================================================
# Threshold Operator Tests
# =============================================================================

class TestCalibrationThresholdOperators:
    """Test threshold comparison operators."""

    def test_gte_operator(self):
        """PHASE 4: >= operator works correctly."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=v,
                label=1 if v >= 0.5 else 0,
                weight=1.0,
            )
            for v in [0.1, 0.3, 0.5, 0.7, 0.9]
        ]

        _, metrics = service._compute_calibration(
            samples=samples,
            bin_count=5,
            op=ComparisonOperator.GTE,
            threshold=0.5,
        )

        # Perfect predictions should yield 100% accuracy
        assert metrics.accuracy == 1.0

    def test_lt_operator(self):
        """PHASE 4: < operator works correctly."""
        from app.services.calibration_service import CalibrationService

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        samples = [
            CalibrationSample(
                run_id=uuid.uuid4(),
                predicted_value=v,
                label=1 if v < 0.5 else 0,  # Inverse logic
                weight=1.0,
            )
            for v in [0.1, 0.3, 0.5, 0.7, 0.9]
        ]

        _, metrics = service._compute_calibration(
            samples=samples,
            bin_count=5,
            op=ComparisonOperator.LT,
            threshold=0.5,
        )

        # Perfect predictions should yield 100% accuracy
        assert metrics.accuracy == 1.0


# =============================================================================
# Result Response Tests
# =============================================================================

class TestCalibrationResultResponse:
    """Test CalibrationResultResponse schema."""

    def test_result_response_succeeded(self):
        """PHASE 4: Successful result includes all fields."""
        result = CalibrationResultResponse(
            job_id=uuid.uuid4(),
            status=CalibrationJobStatusEnum.SUCCEEDED,
            best_mapping=[
                CalibrationBin(
                    bin_start=0.0,
                    bin_end=0.5,
                    calibrated_prob=0.3,
                    n_samples=50,
                    empirical_rate=0.3,
                ),
                CalibrationBin(
                    bin_start=0.5,
                    bin_end=1.0,
                    calibrated_prob=0.7,
                    n_samples=50,
                    empirical_rate=0.7,
                ),
            ],
            best_bin_count=2,
            best_iteration=0,
            metrics=CalibrationMetrics(
                accuracy=0.85,
                brier_score=0.12,
                ece=0.05,
                n_samples=100,
            ),
            audit={"runs_matched": 100},
            selected_run_ids=[uuid.uuid4() for _ in range(5)],
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            duration_seconds=5.0,
        )

        assert result.status == CalibrationJobStatusEnum.SUCCEEDED
        assert len(result.best_mapping) == 2
        assert result.metrics.accuracy == 0.85
        assert result.duration_seconds == 5.0

    def test_result_response_failed(self):
        """PHASE 4: Failed result includes error message."""
        result = CalibrationResultResponse(
            job_id=uuid.uuid4(),
            status=CalibrationJobStatusEnum.FAILED,
            error_message="Insufficient data: 5 samples found, minimum 10 required.",
            audit={"runs_matched": 5},
        )

        assert result.status == CalibrationJobStatusEnum.FAILED
        assert "Insufficient data" in result.error_message
        assert result.best_mapping is None
        assert result.metrics is None

    def test_result_response_canceled(self):
        """PHASE 4: Canceled result."""
        result = CalibrationResultResponse(
            job_id=uuid.uuid4(),
            status=CalibrationJobStatusEnum.CANCELED,
            error_message="Job was canceled",
        )

        assert result.status == CalibrationJobStatusEnum.CANCELED


# =============================================================================
# Auditability Tests
# =============================================================================

class TestCalibrationAuditability:
    """
    PHASE 4: Test auditability requirements (C4 compliance).

    All calibration results must include audit information.
    """

    def test_result_includes_audit(self):
        """PHASE 4: Result includes audit summary."""
        result = CalibrationResultResponse(
            job_id=uuid.uuid4(),
            status=CalibrationJobStatusEnum.SUCCEEDED,
            audit={
                "total_outcomes": 100,
                "total_labels": 80,
                "runs_matched": 75,
                "runs_missing_labels": 20,
                "runs_missing_metric": 5,
            },
            metrics=CalibrationMetrics(
                accuracy=0.85,
                brier_score=0.12,
                ece=0.05,
                n_samples=75,
            ),
        )

        assert result.audit["runs_matched"] == 75
        assert result.audit["runs_missing_labels"] == 20

    def test_result_includes_sample_run_ids(self):
        """PHASE 4: Result includes sample run IDs for audit."""
        run_ids = [uuid.uuid4() for _ in range(10)]

        result = CalibrationResultResponse(
            job_id=uuid.uuid4(),
            status=CalibrationJobStatusEnum.SUCCEEDED,
            selected_run_ids=run_ids,
            metrics=CalibrationMetrics(
                accuracy=0.85,
                brier_score=0.12,
                ece=0.05,
                n_samples=100,
            ),
        )

        assert len(result.selected_run_ids) == 10

    def test_result_includes_timing(self):
        """PHASE 4: Result includes timing information."""
        started = datetime.utcnow()
        finished = started + timedelta(seconds=5)

        result = CalibrationResultResponse(
            job_id=uuid.uuid4(),
            status=CalibrationJobStatusEnum.SUCCEEDED,
            started_at=started,
            finished_at=finished,
            duration_seconds=5.0,
            metrics=CalibrationMetrics(
                accuracy=0.85,
                brier_score=0.12,
                ece=0.05,
                n_samples=100,
            ),
        )

        assert result.started_at == started
        assert result.finished_at == finished
        assert result.duration_seconds == 5.0


# =============================================================================
# Insufficient Data Tests
# =============================================================================

class TestInsufficientDataHandling:
    """
    PHASE 4 CRITICAL: Test insufficient data handling.

    Calibration should fail gracefully when data is insufficient.
    """

    def test_insufficient_data_constant(self):
        """PHASE 4: MIN_TOTAL_SAMPLES constant is defined."""
        from app.services.calibration_service import MIN_TOTAL_SAMPLES

        assert MIN_TOTAL_SAMPLES > 0
        assert MIN_TOTAL_SAMPLES == 10  # Expected value

    def test_min_samples_per_bin_constant(self):
        """PHASE 4: MIN_SAMPLES_PER_BIN constant is defined."""
        from app.services.calibration_service import MIN_SAMPLES_PER_BIN

        assert MIN_SAMPLES_PER_BIN > 0
        assert MIN_SAMPLES_PER_BIN == 2  # Expected value


# =============================================================================
# Service Method Tests
# =============================================================================

class TestCalibrationServiceMethods:
    """Test CalibrationService methods."""

    def test_get_bin_counts(self):
        """PHASE 4: _get_bin_counts returns correct list."""
        from app.services.calibration_service import (
            CalibrationService,
            DEFAULT_BIN_COUNTS,
        )

        mock_db = MagicMock()
        service = CalibrationService(mock_db)

        # Full list
        counts = service._get_bin_counts(10)
        assert counts == DEFAULT_BIN_COUNTS[:10]

        # Partial list
        counts_3 = service._get_bin_counts(3)
        assert len(counts_3) == 3
        assert counts_3 == DEFAULT_BIN_COUNTS[:3]

    def test_default_bin_counts(self):
        """PHASE 4: DEFAULT_BIN_COUNTS are defined."""
        from app.services.calibration_service import DEFAULT_BIN_COUNTS

        assert len(DEFAULT_BIN_COUNTS) > 0
        assert DEFAULT_BIN_COUNTS == [5, 10, 15, 20, 25, 30]


# =============================================================================
# Bulk Upsert Response Tests
# =============================================================================

class TestBulkUpsertResponse:
    """Test BulkUpsertLabelsResponse schema."""

    def test_bulk_upsert_response(self):
        """PHASE 4: BulkUpsertLabelsResponse construction."""
        response = BulkUpsertLabelsResponse(
            created=10,
            updated=5,
            errors=[],
        )

        assert response.created == 10
        assert response.updated == 5
        assert len(response.errors) == 0

    def test_bulk_upsert_response_with_errors(self):
        """PHASE 4: BulkUpsertLabelsResponse with errors."""
        response = BulkUpsertLabelsResponse(
            created=8,
            updated=0,
            errors=[
                {"run_id": "abc123", "error": "Run not found"},
                {"run_id": "def456", "error": "Invalid label"},
            ],
        )

        assert response.created == 8
        assert len(response.errors) == 2
        assert response.errors[0]["run_id"] == "abc123"


# =============================================================================
# Iteration Response Tests
# =============================================================================

class TestIterationResponse:
    """Test CalibrationIterationResponse schema."""

    def test_iteration_response(self):
        """PHASE 4: CalibrationIterationResponse construction."""
        iteration = CalibrationIterationResponse(
            id=uuid.uuid4(),
            job_id=uuid.uuid4(),
            iter_index=0,
            params_json={"bin_count": 10},
            metrics_json={
                "accuracy": 0.85,
                "brier_score": 0.12,
                "ece": 0.05,
            },
            created_at=datetime.utcnow(),
        )

        assert iteration.iter_index == 0
        assert iteration.params_json["bin_count"] == 10
        assert iteration.metrics_json["accuracy"] == 0.85
