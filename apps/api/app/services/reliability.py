"""
Reliability Service
Reference: verification_checklist_v2.md §7

Provides reliability assessment including:
- §7.1 Backtest time cutoff enforcement (via LeakageGuard)
- §7.2 Calibration bounding and rollback
- §7.3 Stability and sensitivity analysis
- §7.4 Drift detection
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import hashlib
import json
import logging
import math

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class CalibrationBound:
    """Defines bounds for a calibration parameter."""
    parameter_name: str
    min_value: float
    max_value: float
    current_value: float
    default_value: float

    def is_within_bounds(self) -> bool:
        """Check if current value is within bounds."""
        return self.min_value <= self.current_value <= self.max_value


@dataclass
class CalibrationSnapshot:
    """Snapshot of calibration state for rollback."""
    snapshot_id: str
    created_at: datetime
    parameters: Dict[str, float]
    error_metrics: Dict[str, float]
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at.isoformat(),
            "parameters": self.parameters,
            "error_metrics": self.error_metrics,
            "note": self.note,
        }


@dataclass
class StabilityResult:
    """Result of stability analysis across multiple seeds."""
    variance: float
    std_dev: float
    seeds_tested: List[int]
    outcomes_by_seed: Dict[int, Dict[str, float]]
    is_stable: bool  # True if variance < threshold
    stability_threshold: float = 0.1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variance": self.variance,
            "std_dev": self.std_dev,
            "seeds_tested": self.seeds_tested,
            "is_stable": self.is_stable,
            "stability_threshold": self.stability_threshold,
        }


@dataclass
class SensitivityResult:
    """Result of sensitivity analysis."""
    parameter: str
    base_outcome: float
    perturbed_outcome: float
    perturbation_size: float
    sensitivity_score: float  # How much outcome changes per unit perturbation
    rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter": self.parameter,
            "sensitivity_score": self.sensitivity_score,
            "rank": self.rank,
        }


@dataclass
class DriftResult:
    """Result of drift detection."""
    drift_score: float
    drift_detected: bool
    features_shifted: List[str]
    shift_magnitudes: Dict[str, float]
    reference_period: str
    comparison_period: str
    warning_level: str  # none, low, medium, high

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drift_score": self.drift_score,
            "drift_detected": self.drift_detected,
            "features_shifted": self.features_shifted,
            "shift_magnitudes": self.shift_magnitudes,
            "warning_level": self.warning_level,
        }


@dataclass
class ReliabilityAssessment:
    """Complete reliability assessment for Evidence Pack."""
    confidence_score: float
    confidence_level: str  # high, medium, low, very_low

    # §7.1 - Leakage guard results
    leakage_guard_enabled: bool
    blocked_access_attempts: int
    cutoff_time: Optional[datetime]

    # §7.2 - Calibration
    calibration_score: Optional[float]
    calibration_bounded: bool
    calibration_bounds: List[CalibrationBound] = field(default_factory=list)
    calibration_snapshot_id: Optional[str] = None

    # §7.3 - Stability
    stability_variance: Optional[float]
    seeds_tested: List[int] = field(default_factory=list)
    stability_result: Optional[StabilityResult] = None

    # §7.3 - Sensitivity
    sensitivity_results: List[SensitivityResult] = field(default_factory=list)

    # §7.4 - Drift
    drift_score: Optional[float] = None
    drift_detected: bool = False
    drift_result: Optional[DriftResult] = None

    # Data quality
    data_gaps: List[str] = field(default_factory=list)

    def to_evidence_pack_format(self) -> Dict[str, Any]:
        """Export in format compatible with ReliabilityProof schema."""
        return {
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level,
            "calibration_score": self.calibration_score,
            "calibration_bounded": self.calibration_bounded,
            "stability_variance": self.stability_variance,
            "seeds_tested": self.seeds_tested,
            "drift_score": self.drift_score,
            "drift_detected": self.drift_detected,
            "data_gaps": self.data_gaps,
        }


# =============================================================================
# Reliability Service
# =============================================================================

class ReliabilityService:
    """
    Service for computing and tracking reliability metrics.

    Reference: verification_checklist_v2.md §7
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._calibration_snapshots: Dict[str, CalibrationSnapshot] = {}
        self._calibration_bounds: Dict[str, CalibrationBound] = {}

    # =========================================================================
    # §7.2 - Calibration Bounding and Rollback
    # =========================================================================

    def set_calibration_bounds(
        self,
        parameter_name: str,
        min_value: float,
        max_value: float,
        default_value: float,
    ) -> CalibrationBound:
        """
        Set bounds for a calibration parameter.

        §7.2: Calibration must be bounded to prevent overfitting.
        """
        bound = CalibrationBound(
            parameter_name=parameter_name,
            min_value=min_value,
            max_value=max_value,
            current_value=default_value,
            default_value=default_value,
        )
        self._calibration_bounds[parameter_name] = bound
        logger.info(f"Set calibration bounds for {parameter_name}: [{min_value}, {max_value}]")
        return bound

    def update_calibration_parameter(
        self,
        parameter_name: str,
        new_value: float,
    ) -> Tuple[bool, Optional[str]]:
        """
        Update a calibration parameter, respecting bounds.

        Returns:
            (success, error_message)
        """
        if parameter_name not in self._calibration_bounds:
            return False, f"Parameter {parameter_name} has no bounds defined"

        bound = self._calibration_bounds[parameter_name]

        if new_value < bound.min_value:
            return False, f"Value {new_value} below minimum {bound.min_value}"
        if new_value > bound.max_value:
            return False, f"Value {new_value} above maximum {bound.max_value}"

        bound.current_value = new_value
        logger.info(f"Updated calibration parameter {parameter_name} to {new_value}")
        return True, None

    def create_calibration_snapshot(
        self,
        error_metrics: Dict[str, float],
        note: str = "",
    ) -> CalibrationSnapshot:
        """
        Create a snapshot of current calibration state for rollback.

        §7.2: Calibration must be rollback-able.
        """
        parameters = {
            name: bound.current_value
            for name, bound in self._calibration_bounds.items()
        }

        # Generate unique snapshot ID
        content = json.dumps({
            "params": parameters,
            "metrics": error_metrics,
            "time": datetime.utcnow().isoformat(),
        }, sort_keys=True)
        snapshot_id = hashlib.sha256(content.encode()).hexdigest()[:12]

        snapshot = CalibrationSnapshot(
            snapshot_id=snapshot_id,
            created_at=datetime.utcnow(),
            parameters=parameters,
            error_metrics=error_metrics,
            note=note,
        )

        self._calibration_snapshots[snapshot_id] = snapshot
        logger.info(f"Created calibration snapshot {snapshot_id}")
        return snapshot

    def rollback_calibration(self, snapshot_id: str) -> Tuple[bool, Optional[str]]:
        """
        Rollback calibration to a previous snapshot.

        §7.2: Rollback must restore previous state.
        """
        if snapshot_id not in self._calibration_snapshots:
            return False, f"Snapshot {snapshot_id} not found"

        snapshot = self._calibration_snapshots[snapshot_id]

        for param_name, value in snapshot.parameters.items():
            if param_name in self._calibration_bounds:
                self._calibration_bounds[param_name].current_value = value

        logger.info(f"Rolled back calibration to snapshot {snapshot_id}")
        return True, None

    def get_calibration_state(self) -> Dict[str, Any]:
        """Get current calibration state."""
        return {
            "parameters": {
                name: {
                    "value": bound.current_value,
                    "min": bound.min_value,
                    "max": bound.max_value,
                    "within_bounds": bound.is_within_bounds(),
                }
                for name, bound in self._calibration_bounds.items()
            },
            "all_bounded": all(b.is_within_bounds() for b in self._calibration_bounds.values()),
            "snapshots_available": list(self._calibration_snapshots.keys()),
        }

    # =========================================================================
    # §7.3 - Stability Analysis
    # =========================================================================

    def compute_stability(
        self,
        outcomes_by_seed: Dict[int, Dict[str, float]],
        metric_name: str = "primary_probability",
        stability_threshold: float = 0.1,
    ) -> StabilityResult:
        """
        Compute stability variance across multiple seeds.

        §7.3: Stability must be computed from actual runs.
        """
        seeds = list(outcomes_by_seed.keys())

        if len(seeds) < 2:
            return StabilityResult(
                variance=0.0,
                std_dev=0.0,
                seeds_tested=seeds,
                outcomes_by_seed=outcomes_by_seed,
                is_stable=True,
                stability_threshold=stability_threshold,
            )

        # Extract metric values
        values = []
        for seed, outcome in outcomes_by_seed.items():
            if metric_name in outcome:
                values.append(outcome[metric_name])

        if len(values) < 2:
            return StabilityResult(
                variance=0.0,
                std_dev=0.0,
                seeds_tested=seeds,
                outcomes_by_seed=outcomes_by_seed,
                is_stable=True,
                stability_threshold=stability_threshold,
            )

        # Compute variance
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)

        is_stable = std_dev < stability_threshold

        result = StabilityResult(
            variance=variance,
            std_dev=std_dev,
            seeds_tested=seeds,
            outcomes_by_seed=outcomes_by_seed,
            is_stable=is_stable,
            stability_threshold=stability_threshold,
        )

        logger.info(
            f"Stability analysis: variance={variance:.4f}, std_dev={std_dev:.4f}, "
            f"stable={is_stable} (threshold={stability_threshold})"
        )

        return result

    def compute_sensitivity(
        self,
        base_outcome: Dict[str, float],
        perturbed_outcomes: Dict[str, Dict[str, float]],
        metric_name: str = "primary_probability",
    ) -> List[SensitivityResult]:
        """
        Compute sensitivity of outcome to parameter perturbations.

        §7.3: Sensitivity must be computed from actual perturbations.

        Args:
            base_outcome: Outcome with default parameters
            perturbed_outcomes: Dict mapping parameter names to outcomes when perturbed
            metric_name: Which metric to compute sensitivity for
        """
        results = []
        base_value = base_outcome.get(metric_name, 0.0)

        for param_name, perturbed in perturbed_outcomes.items():
            perturbed_value = perturbed.get(metric_name, 0.0)
            perturbation_size = perturbed.get("_perturbation_size", 0.1)

            if perturbation_size > 0:
                sensitivity_score = abs(perturbed_value - base_value) / perturbation_size
            else:
                sensitivity_score = 0.0

            results.append(SensitivityResult(
                parameter=param_name,
                base_outcome=base_value,
                perturbed_outcome=perturbed_value,
                perturbation_size=perturbation_size,
                sensitivity_score=sensitivity_score,
            ))

        # Rank by sensitivity
        results.sort(key=lambda r: r.sensitivity_score, reverse=True)
        for i, result in enumerate(results):
            result.rank = i + 1

        logger.info(f"Sensitivity analysis: {len(results)} parameters ranked")
        return results

    # =========================================================================
    # §7.4 - Drift Detection
    # =========================================================================

    def detect_drift(
        self,
        reference_distribution: Dict[str, float],
        current_distribution: Dict[str, float],
        drift_threshold: float = 0.15,
    ) -> DriftResult:
        """
        Detect distribution drift between reference and current periods.

        §7.4: Drift detection must identify feature shifts.
        """
        features_shifted = []
        shift_magnitudes = {}
        total_shift = 0.0

        all_features = set(reference_distribution.keys()) | set(current_distribution.keys())

        for feature in all_features:
            ref_value = reference_distribution.get(feature, 0.0)
            curr_value = current_distribution.get(feature, 0.0)

            if ref_value > 0:
                shift = abs(curr_value - ref_value) / ref_value
            else:
                shift = abs(curr_value) if curr_value > 0 else 0.0

            shift_magnitudes[feature] = shift
            total_shift += shift

            if shift > drift_threshold:
                features_shifted.append(feature)

        # Compute overall drift score (average shift)
        drift_score = total_shift / len(all_features) if all_features else 0.0
        drift_detected = len(features_shifted) > 0 or drift_score > drift_threshold

        # Determine warning level
        if drift_score > 0.5:
            warning_level = "high"
        elif drift_score > 0.25:
            warning_level = "medium"
        elif drift_score > drift_threshold:
            warning_level = "low"
        else:
            warning_level = "none"

        result = DriftResult(
            drift_score=drift_score,
            drift_detected=drift_detected,
            features_shifted=features_shifted,
            shift_magnitudes=shift_magnitudes,
            reference_period="baseline",
            comparison_period="current",
            warning_level=warning_level,
        )

        logger.info(
            f"Drift detection: score={drift_score:.4f}, detected={drift_detected}, "
            f"shifted_features={len(features_shifted)}, warning={warning_level}"
        )

        return result

    # =========================================================================
    # Complete Reliability Assessment
    # =========================================================================

    async def compute_reliability_assessment(
        self,
        run_data: Dict[str, Any],
        leakage_stats: Optional[Dict[str, Any]] = None,
        stability_runs: Optional[Dict[int, Dict[str, float]]] = None,
        reference_distribution: Optional[Dict[str, float]] = None,
    ) -> ReliabilityAssessment:
        """
        Compute complete reliability assessment for Evidence Pack.

        This method integrates all §7 requirements:
        - §7.1: Leakage guard enforcement
        - §7.2: Calibration bounding
        - §7.3: Stability and sensitivity
        - §7.4: Drift detection
        """
        outputs = run_data.get("outputs", {})
        reliability_data = outputs.get("reliability", {})

        # Base confidence from run outputs
        confidence_score = reliability_data.get("confidence", 0.5)

        # Determine confidence level
        if confidence_score >= 0.8:
            confidence_level = "high"
        elif confidence_score >= 0.6:
            confidence_level = "medium"
        elif confidence_score >= 0.4:
            confidence_level = "low"
        else:
            confidence_level = "very_low"

        # §7.1 - Leakage guard stats
        leakage_guard_enabled = run_data.get("leakage_guard", False)
        blocked_access_attempts = 0
        cutoff_time = None
        if leakage_stats:
            blocked_access_attempts = leakage_stats.get("blocked_attempts", 0)
        if run_data.get("cutoff_time"):
            cutoff_time = datetime.fromisoformat(run_data["cutoff_time"].replace('Z', '+00:00'))

        # §7.2 - Calibration state
        calibration_state = self.get_calibration_state()
        calibration_bounded = calibration_state.get("all_bounded", False)
        calibration_score = reliability_data.get("calibration")

        # §7.3 - Stability
        stability_result = None
        stability_variance = None
        seeds_tested = [run_data.get("actual_seed", 42)]

        if stability_runs and len(stability_runs) > 1:
            stability_result = self.compute_stability(stability_runs)
            stability_variance = stability_result.variance
            seeds_tested = stability_result.seeds_tested
        else:
            stability_variance = reliability_data.get("stability")

        # §7.4 - Drift detection
        drift_result = None
        drift_score = None
        drift_detected = False

        if reference_distribution:
            current_distribution = outputs.get("outcome_distribution", {})
            if current_distribution:
                drift_result = self.detect_drift(
                    reference_distribution,
                    current_distribution,
                )
                drift_score = drift_result.drift_score
                drift_detected = drift_result.drift_detected

        # Data gaps
        data_gaps = reliability_data.get("data_gaps", [])

        return ReliabilityAssessment(
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            leakage_guard_enabled=leakage_guard_enabled,
            blocked_access_attempts=blocked_access_attempts,
            cutoff_time=cutoff_time,
            calibration_score=calibration_score,
            calibration_bounded=calibration_bounded,
            calibration_bounds=list(self._calibration_bounds.values()),
            stability_variance=stability_variance,
            seeds_tested=seeds_tested,
            stability_result=stability_result,
            drift_score=drift_score,
            drift_detected=drift_detected,
            drift_result=drift_result,
            data_gaps=data_gaps,
        )


# =============================================================================
# Factory Function
# =============================================================================

def get_reliability_service(db: AsyncSession) -> ReliabilityService:
    """Get a ReliabilityService instance."""
    return ReliabilityService(db)
