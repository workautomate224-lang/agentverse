"""
Historical Scenario Runner

P7-001: Run simulations against historical data with time cutoffs.
Enforces no-leakage policy per project.md §7.2.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


class LeakageViolationType(str, Enum):
    """Types of data leakage violations."""
    FUTURE_DATA = "future_data"
    TIMESTAMP_MISSING = "timestamp_missing"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    UNTAGGED_SOURCE = "untagged_source"


@dataclass
class LeakageViolation:
    """A detected leakage violation."""
    data_source: str
    data_date: Optional[str]
    violation_type: LeakageViolationType
    description: str
    severity: str = "high"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_source": self.data_source,
            "data_date": self.data_date,
            "violation_type": self.violation_type.value,
            "description": self.description,
            "severity": self.severity,
        }


@dataclass
class TimeCutoff:
    """Time cutoff configuration for historical runs."""
    cutoff_date: date
    cutoff_datetime: datetime = field(default=None)

    # Strict mode fails on any violation; lenient logs warnings
    strict_mode: bool = True

    # Grace period for data sources (e.g., allow 1 day lag)
    grace_period_days: int = 0

    def __post_init__(self):
        if self.cutoff_datetime is None:
            self.cutoff_datetime = datetime.combine(
                self.cutoff_date,
                datetime.max.time()
            )

    def is_valid_date(self, data_date: date) -> bool:
        """Check if a data date is valid (before cutoff)."""
        grace_date = self.cutoff_date
        if self.grace_period_days:
            from datetime import timedelta
            grace_date = self.cutoff_date + timedelta(days=self.grace_period_days)
        return data_date <= grace_date

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cutoff_date": self.cutoff_date.isoformat(),
            "strict_mode": self.strict_mode,
            "grace_period_days": self.grace_period_days,
        }


class LeakageValidator:
    """
    Validates data against time cutoff to prevent leakage.

    All data used in historical validation must be tagged with timestamps.
    Any data newer than cutoff is rejected.
    """

    def __init__(self, time_cutoff: TimeCutoff):
        self.time_cutoff = time_cutoff
        self.violations: List[LeakageViolation] = []
        self.sources_validated: List[str] = []

    def validate_data_point(
        self,
        source: str,
        data_date: Optional[date],
        data_value: Any,
    ) -> bool:
        """
        Validate a single data point.

        Returns True if valid, False if violation detected.
        """
        self.sources_validated.append(source)

        if data_date is None:
            self.violations.append(LeakageViolation(
                data_source=source,
                data_date=None,
                violation_type=LeakageViolationType.TIMESTAMP_MISSING,
                description=f"Data point from {source} missing timestamp",
            ))
            return False

        if not self.time_cutoff.is_valid_date(data_date):
            self.violations.append(LeakageViolation(
                data_source=source,
                data_date=data_date.isoformat(),
                violation_type=LeakageViolationType.FUTURE_DATA,
                description=(
                    f"Data from {source} dated {data_date} is after "
                    f"cutoff {self.time_cutoff.cutoff_date}"
                ),
            ))
            return False

        return True

    def validate_dataset(
        self,
        dataset: Dict[str, Any],
        date_field: str = "date",
        source_name: str = "dataset",
    ) -> bool:
        """
        Validate an entire dataset.

        Expects dataset to be a list of records with date fields.
        """
        if not isinstance(dataset, list):
            dataset = [dataset]

        all_valid = True
        for record in dataset:
            record_date = record.get(date_field)
            if isinstance(record_date, str):
                record_date = date.fromisoformat(record_date)

            if not self.validate_data_point(
                source=source_name,
                data_date=record_date,
                data_value=record,
            ):
                all_valid = False
                if self.time_cutoff.strict_mode:
                    return False

        return all_valid

    def detect_suspicious_patterns(
        self,
        predictions: Dict[str, float],
        actual_outcomes: Dict[str, float],
    ) -> bool:
        """
        Detect suspiciously accurate predictions that might indicate leakage.

        Returns True if suspicious, False if OK.
        """
        # Perfect prediction is suspicious
        import numpy as np

        common_keys = set(predictions.keys()) & set(actual_outcomes.keys())
        if not common_keys:
            return False

        pred_values = np.array([predictions[k] for k in common_keys])
        actual_values = np.array([actual_outcomes[k] for k in common_keys])

        correlation = np.corrcoef(pred_values, actual_values)[0, 1]
        mae = np.mean(np.abs(pred_values - actual_values))

        # Suspicious if correlation > 0.99 or MAE < 0.001
        if correlation > 0.99 or mae < 0.001:
            self.violations.append(LeakageViolation(
                data_source="predictions",
                data_date=None,
                violation_type=LeakageViolationType.SUSPICIOUS_PATTERN,
                description=(
                    f"Suspiciously accurate predictions (corr={correlation:.4f}, "
                    f"MAE={mae:.6f}). Possible data leakage."
                ),
                severity="warning",
            ))
            return True

        return False

    def get_validation_result(self) -> Dict[str, Any]:
        """Get validation result summary."""
        return {
            "validation_passed": len(self.violations) == 0,
            "cutoff_date": self.time_cutoff.cutoff_date.isoformat(),
            "violations": [v.to_dict() for v in self.violations],
            "sources_validated": list(set(self.sources_validated)),
            "violation_count": len(self.violations),
        }


@dataclass
class HistoricalDataset:
    """A historical dataset for validation."""
    dataset_id: str
    name: str

    # The actual outcomes (ground truth)
    outcomes: Dict[str, float]

    # When outcomes occurred
    outcome_date: date

    # When prediction would have been made
    prediction_date: date

    # Regional breakdown (optional)
    regional_outcomes: Optional[Dict[str, Dict[str, float]]] = None

    # Time series (optional)
    time_series: Optional[Dict[str, List[Tuple[date, float]]]] = None

    # Source metadata
    source: str = ""
    sample_size: Optional[int] = None

    # Data checksum for reproducibility
    checksum: Optional[str] = None

    def __post_init__(self):
        if self.checksum is None:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        """Compute checksum of outcome data."""
        data_str = json.dumps(self.outcomes, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "outcome_date": self.outcome_date.isoformat(),
            "prediction_date": self.prediction_date.isoformat(),
            "source": self.source,
            "sample_size": self.sample_size,
            "checksum": self.checksum,
            "outcome_keys": list(self.outcomes.keys()),
        }


@dataclass
class HistoricalScenario:
    """A complete historical scenario for validation."""
    scenario_id: str
    name: str
    description: str

    # The dataset with actual outcomes
    dataset: HistoricalDataset

    # Initial conditions at prediction time
    initial_state: Dict[str, Any]

    # Time cutoff for the scenario
    time_cutoff: TimeCutoff

    # Simulation parameters to use
    simulation_params: Dict[str, Any] = field(default_factory=dict)

    # Tags for filtering
    tags: List[str] = field(default_factory=list)

    # Domain (e.g., "elections", "consumer", "economics")
    domain: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "dataset": self.dataset.to_dict(),
            "time_cutoff": self.time_cutoff.to_dict(),
            "simulation_params": self.simulation_params,
            "tags": self.tags,
            "domain": self.domain,
        }


@dataclass
class HistoricalRunResult:
    """Result of running a historical scenario."""
    scenario_id: str
    run_id: str

    # Predictions from simulation
    predictions: Dict[str, float]

    # Actual outcomes from dataset
    actuals: Dict[str, float]

    # Error metrics
    distribution_error: float
    ranking_error: float
    turning_point_error: Optional[float]

    # Overall accuracy
    accuracy: float

    # Leakage validation
    leakage_check_passed: bool
    leakage_violations: List[Dict[str, Any]]

    # Timing
    run_started_at: datetime
    run_completed_at: datetime
    computation_time_ms: float

    # Seed used
    seed: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "run_id": self.run_id,
            "predictions": self.predictions,
            "actuals": self.actuals,
            "distribution_error": self.distribution_error,
            "ranking_error": self.ranking_error,
            "turning_point_error": self.turning_point_error,
            "accuracy": self.accuracy,
            "leakage_check_passed": self.leakage_check_passed,
            "leakage_violations": self.leakage_violations,
            "computation_time_ms": self.computation_time_ms,
            "seed": self.seed,
        }


class HistoricalScenarioRunner:
    """
    Runs simulations against historical scenarios with anti-leakage enforcement.

    Key features:
    - Time cutoff enforcement
    - Leakage detection
    - Error metrics computation
    - Result persistence
    """

    def __init__(
        self,
        simulation_runner: Callable[[Dict[str, Any]], Dict[str, float]],
        error_metrics_calculator: Optional[Callable] = None,
    ):
        """
        Initialize the historical runner.

        Args:
            simulation_runner: Function that runs simulation with params
            error_metrics_calculator: Optional custom error calculator
        """
        self.simulation_runner = simulation_runner
        self.error_metrics_calculator = error_metrics_calculator
        self.run_history: List[HistoricalRunResult] = []

    def run_scenario(
        self,
        scenario: HistoricalScenario,
        seed: int = 42,
        validate_leakage: bool = True,
    ) -> HistoricalRunResult:
        """
        Run a single historical scenario.

        Args:
            scenario: The scenario to run
            seed: Random seed for reproducibility
            validate_leakage: Whether to check for data leakage

        Returns:
            HistoricalRunResult with predictions and errors
        """
        import uuid
        from time import time

        run_id = str(uuid.uuid4())
        start_time = datetime.now()
        start_ms = time() * 1000

        logger.info(f"Running historical scenario: {scenario.name}")

        # Validate leakage if requested
        leakage_violations = []
        if validate_leakage:
            validator = LeakageValidator(scenario.time_cutoff)

            # Validate initial state has valid dates
            for key, value in scenario.initial_state.items():
                if isinstance(value, dict) and "date" in value:
                    validator.validate_data_point(
                        source=f"initial_state.{key}",
                        data_date=date.fromisoformat(value["date"]),
                        data_value=value,
                    )

            leakage_violations = [v.to_dict() for v in validator.violations]

            if validator.violations and scenario.time_cutoff.strict_mode:
                return HistoricalRunResult(
                    scenario_id=scenario.scenario_id,
                    run_id=run_id,
                    predictions={},
                    actuals=scenario.dataset.outcomes,
                    distribution_error=1.0,
                    ranking_error=1.0,
                    turning_point_error=None,
                    accuracy=0.0,
                    leakage_check_passed=False,
                    leakage_violations=leakage_violations,
                    run_started_at=start_time,
                    run_completed_at=datetime.now(),
                    computation_time_ms=time() * 1000 - start_ms,
                    seed=seed,
                )

        # Build simulation params
        params = {
            **scenario.simulation_params,
            "initial_state": scenario.initial_state,
            "seed": seed,
        }

        # Run simulation
        try:
            predictions = self.simulation_runner(params)
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            return HistoricalRunResult(
                scenario_id=scenario.scenario_id,
                run_id=run_id,
                predictions={},
                actuals=scenario.dataset.outcomes,
                distribution_error=1.0,
                ranking_error=1.0,
                turning_point_error=None,
                accuracy=0.0,
                leakage_check_passed=len(leakage_violations) == 0,
                leakage_violations=leakage_violations,
                run_started_at=start_time,
                run_completed_at=datetime.now(),
                computation_time_ms=time() * 1000 - start_ms,
                seed=seed,
            )

        # Compute error metrics
        actuals = scenario.dataset.outcomes
        distribution_error = self._compute_distribution_error(predictions, actuals)
        ranking_error = self._compute_ranking_error(predictions, actuals)
        turning_point_error = None

        if scenario.dataset.time_series:
            turning_point_error = self._compute_turning_point_error(
                predictions,
                actuals,
                scenario.dataset.time_series,
            )

        # Compute accuracy
        accuracy = 1.0 - min(distribution_error, 1.0)

        # Check for suspicious patterns
        if validate_leakage:
            validator = LeakageValidator(scenario.time_cutoff)
            validator.detect_suspicious_patterns(predictions, actuals)
            leakage_violations.extend([v.to_dict() for v in validator.violations])

        result = HistoricalRunResult(
            scenario_id=scenario.scenario_id,
            run_id=run_id,
            predictions=predictions,
            actuals=actuals,
            distribution_error=distribution_error,
            ranking_error=ranking_error,
            turning_point_error=turning_point_error,
            accuracy=accuracy,
            leakage_check_passed=len(leakage_violations) == 0,
            leakage_violations=leakage_violations,
            run_started_at=start_time,
            run_completed_at=datetime.now(),
            computation_time_ms=time() * 1000 - start_ms,
            seed=seed,
        )

        self.run_history.append(result)

        logger.info(
            f"Scenario {scenario.name} complete: "
            f"accuracy={accuracy:.4f}, dist_error={distribution_error:.4f}"
        )

        return result

    def run_multiple_scenarios(
        self,
        scenarios: List[HistoricalScenario],
        seeds: Optional[List[int]] = None,
        validate_leakage: bool = True,
    ) -> List[HistoricalRunResult]:
        """
        Run multiple historical scenarios.

        Args:
            scenarios: List of scenarios to run
            seeds: Optional list of seeds (one per scenario)
            validate_leakage: Whether to check for leakage

        Returns:
            List of HistoricalRunResult
        """
        if seeds is None:
            seeds = [42 + i for i in range(len(scenarios))]

        results = []
        for scenario, seed in zip(scenarios, seeds):
            result = self.run_scenario(scenario, seed, validate_leakage)
            results.append(result)

        return results

    def _compute_distribution_error(
        self,
        predictions: Dict[str, float],
        actuals: Dict[str, float],
    ) -> float:
        """Compute distribution error between predictions and actuals."""
        import numpy as np

        common_keys = set(predictions.keys()) & set(actuals.keys())
        if not common_keys:
            return 1.0

        pred = np.array([predictions[k] for k in common_keys])
        actual = np.array([actuals[k] for k in common_keys])

        # Normalize to distributions
        pred = pred / (pred.sum() + 1e-10)
        actual = actual / (actual.sum() + 1e-10)

        # Total Variation Distance
        tv_distance = 0.5 * np.sum(np.abs(pred - actual))

        return float(tv_distance)

    def _compute_ranking_error(
        self,
        predictions: Dict[str, float],
        actuals: Dict[str, float],
    ) -> float:
        """Compute ranking error (did we predict correct ordering?)."""
        import numpy as np

        common_keys = list(set(predictions.keys()) & set(actuals.keys()))
        if len(common_keys) < 2:
            return 0.0

        pred_values = [predictions[k] for k in common_keys]
        actual_values = [actuals[k] for k in common_keys]

        # Get rankings
        pred_ranks = np.argsort(np.argsort(-np.array(pred_values)))
        actual_ranks = np.argsort(np.argsort(-np.array(actual_values)))

        # Normalized Kendall tau distance
        n = len(common_keys)
        discordant = 0
        for i in range(n):
            for j in range(i + 1, n):
                if (pred_ranks[i] - pred_ranks[j]) * (actual_ranks[i] - actual_ranks[j]) < 0:
                    discordant += 1

        max_discordant = n * (n - 1) / 2
        ranking_error = discordant / max_discordant if max_discordant > 0 else 0.0

        return float(ranking_error)

    def _compute_turning_point_error(
        self,
        predictions: Dict[str, float],
        actuals: Dict[str, float],
        time_series: Dict[str, List[Tuple[date, float]]],
    ) -> float:
        """Compute turning point detection error."""
        # Detect turning points in actual time series
        # Compare with predicted direction

        turning_point_errors = []

        for key, series in time_series.items():
            if key not in predictions or key not in actuals:
                continue

            if len(series) < 3:
                continue

            # Detect turning points (local extrema)
            values = [v for _, v in sorted(series)]
            turning_points = []

            for i in range(1, len(values) - 1):
                if (values[i] > values[i-1] and values[i] > values[i+1]) or \
                   (values[i] < values[i-1] and values[i] < values[i+1]):
                    turning_points.append(i)

            # Check if prediction captures the trend direction
            if len(turning_points) > 0:
                # Simplified: did we predict right final direction?
                actual_trend = actuals[key] - values[0]
                pred_trend = predictions[key] - values[0]

                if actual_trend * pred_trend < 0:  # Wrong direction
                    turning_point_errors.append(1.0)
                else:
                    turning_point_errors.append(0.0)

        if not turning_point_errors:
            return 0.0

        import numpy as np
        return float(np.mean(turning_point_errors))

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all historical runs."""
        if not self.run_history:
            return {"total_runs": 0}

        import numpy as np

        accuracies = [r.accuracy for r in self.run_history]
        dist_errors = [r.distribution_error for r in self.run_history]
        rank_errors = [r.ranking_error for r in self.run_history]

        return {
            "total_runs": len(self.run_history),
            "mean_accuracy": float(np.mean(accuracies)),
            "std_accuracy": float(np.std(accuracies)),
            "min_accuracy": float(np.min(accuracies)),
            "max_accuracy": float(np.max(accuracies)),
            "mean_distribution_error": float(np.mean(dist_errors)),
            "mean_ranking_error": float(np.mean(rank_errors)),
            "leakage_violations": sum(
                len(r.leakage_violations) for r in self.run_history
            ),
            "runs_with_violations": sum(
                1 for r in self.run_history if not r.leakage_check_passed
            ),
        }
