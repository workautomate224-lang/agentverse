"""
Reliability Report Generator

P7-007: Generate comprehensive reliability reports.
Combines calibration, stability, sensitivity, drift, and data gaps analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, date, timedelta
from enum import Enum
import numpy as np
import logging
import json
from uuid import uuid4

from .historical_runner import HistoricalScenarioRunner, HistoricalDataset
from .error_metrics import ErrorMetricsSuite, compute_error_metrics_suite
from .auto_tune import BoundedAutoTune, TuneConfig, TuneResult
from .stability import StabilityAnalyzer, SeedVarianceReport, MultiSeedRunner
from .sensitivity import SensitivityScanner, SensitivityReport, VariableBound
from .drift_detector import DriftDetector, DriftReport, DriftSeverity

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence level for predictions."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass
class CalibrationScore:
    """Calibration metrics for reliability report."""
    accuracy: float  # 0-1
    historical_scenarios_run: int
    best_scenario_accuracy: float
    worst_scenario_accuracy: float
    mean_error: float
    error_metrics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "historical_scenarios_run": self.historical_scenarios_run,
            "best_scenario_accuracy": self.best_scenario_accuracy,
            "worst_scenario_accuracy": self.worst_scenario_accuracy,
            "mean_error": self.mean_error,
            "error_metrics": self.error_metrics,
        }


@dataclass
class StabilityScore:
    """Stability metrics for reliability report."""
    score: float  # 0-1
    seeds_tested: int
    variance_coefficient: float
    is_stable: bool
    most_stable_outcome: str
    least_stable_outcome: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "seeds_tested": self.seeds_tested,
            "variance_coefficient": self.variance_coefficient,
            "is_stable": self.is_stable,
            "most_stable_outcome": self.most_stable_outcome,
            "least_stable_outcome": self.least_stable_outcome,
        }


@dataclass
class SensitivitySummary:
    """Sensitivity analysis summary for reliability report."""
    n_high_impact_variables: int
    top_impact_variables: List[str]
    impact_scores: Dict[str, float]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_high_impact_variables": self.n_high_impact_variables,
            "top_impact_variables": self.top_impact_variables,
            "impact_scores": self.impact_scores,
            "recommendations": self.recommendations,
        }


@dataclass
class DriftStatus:
    """Drift detection status for reliability report."""
    drift_detected: bool
    severity: str
    drifted_variables: List[str]
    last_check: datetime
    days_since_calibration: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "drift_detected": self.drift_detected,
            "severity": self.severity,
            "drifted_variables": self.drifted_variables,
            "last_check": self.last_check.isoformat(),
            "days_since_calibration": self.days_since_calibration,
        }


@dataclass
class DataGapsSummary:
    """Data gaps analysis for reliability report."""
    total_variables: int
    variables_with_gaps: int
    gap_percentage: float
    critical_gaps: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_variables": self.total_variables,
            "variables_with_gaps": self.variables_with_gaps,
            "gap_percentage": self.gap_percentage,
            "critical_gaps": self.critical_gaps,
            "recommendations": self.recommendations,
        }


@dataclass
class ConfidenceBreakdown:
    """Confidence breakdown by category."""
    overall: float  # 0-1
    by_category: Dict[str, float]
    by_time_horizon: Dict[str, float]
    factors: Dict[str, float]  # What contributes to confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "by_category": self.by_category,
            "by_time_horizon": self.by_time_horizon,
            "factors": self.factors,
        }


@dataclass
class ReliabilityReport:
    """Complete reliability report per project.md §7.1."""

    # Identifiers
    report_id: str
    project_id: str
    node_id: Optional[str]

    # Timestamps
    generated_at: datetime
    valid_until: datetime

    # Version info
    engine_version: str
    report_version: str = "1.0.0"

    # Core sections
    calibration: CalibrationScore
    stability: StabilityScore
    sensitivity: SensitivitySummary
    drift: DriftStatus
    data_gaps: DataGapsSummary
    confidence: ConfidenceBreakdown

    # Overall
    overall_reliability_score: float  # 0-1
    confidence_level: ConfidenceLevel
    is_reliable: bool
    reliability_threshold: float = 0.7

    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Raw reports (optional, for deep inspection)
    raw_stability_report: Optional[Dict[str, Any]] = None
    raw_sensitivity_report: Optional[Dict[str, Any]] = None
    raw_drift_report: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "project_id": self.project_id,
            "node_id": self.node_id,
            "generated_at": self.generated_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "engine_version": self.engine_version,
            "report_version": self.report_version,
            "calibration": self.calibration.to_dict(),
            "stability": self.stability.to_dict(),
            "sensitivity": self.sensitivity.to_dict(),
            "drift": self.drift.to_dict(),
            "data_gaps": self.data_gaps.to_dict(),
            "confidence": self.confidence.to_dict(),
            "overall_reliability_score": self.overall_reliability_score,
            "confidence_level": self.confidence_level.value,
            "is_reliable": self.is_reliable,
            "reliability_threshold": self.reliability_threshold,
            "recommendations": self.recommendations,
            "warnings": self.warnings,
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    # General
    engine_version: str = "0.1.0"
    validity_days: int = 7

    # Calibration
    run_calibration: bool = True
    min_historical_scenarios: int = 5
    target_accuracy: float = 0.8

    # Stability
    run_stability: bool = True
    n_seeds: int = 10
    stability_threshold: float = 0.1

    # Sensitivity
    run_sensitivity: bool = True
    sensitivity_perturbation: float = 0.1
    high_impact_threshold: float = 0.5

    # Drift
    run_drift: bool = True
    drift_threshold: float = 0.05
    reference_window_days: int = 30

    # Data gaps
    check_data_gaps: bool = True
    gap_threshold: float = 0.1

    # Weights for overall score
    weights: Dict[str, float] = field(default_factory=lambda: {
        "calibration": 0.35,
        "stability": 0.25,
        "sensitivity": 0.15,
        "drift": 0.15,
        "data_gaps": 0.10,
    })


class ReliabilityReportGenerator:
    """
    Generates comprehensive reliability reports.

    Orchestrates all reliability analysis components:
    - Historical calibration
    - Multi-seed stability
    - Sensitivity analysis
    - Drift detection
    - Data gaps analysis
    """

    def __init__(
        self,
        config: ReportConfig,
        simulation_fn: Optional[Callable[[Dict[str, float]], Dict[str, float]]] = None,
    ):
        """
        Initialize report generator.

        Args:
            config: Report generation configuration
            simulation_fn: Function to run simulations for analysis
        """
        self.config = config
        self.simulation_fn = simulation_fn or self._default_simulation_fn

        # Initialize analyzers
        self.stability_analyzer = StabilityAnalyzer(
            stability_threshold=config.stability_threshold,
        )
        self.sensitivity_scanner = SensitivityScanner(
            perturbation_amount=config.sensitivity_perturbation,
            high_impact_threshold=config.high_impact_threshold,
        )
        self.drift_detector = DriftDetector(
            drift_threshold=config.drift_threshold,
        )

    def generate(
        self,
        project_id: str,
        node_id: Optional[str] = None,
        historical_data: Optional[List[HistoricalDataset]] = None,
        current_params: Optional[Dict[str, float]] = None,
        variable_bounds: Optional[Dict[str, VariableBound]] = None,
        reference_data: Optional[Dict[str, List[float]]] = None,
        current_data: Optional[Dict[str, List[float]]] = None,
    ) -> ReliabilityReport:
        """
        Generate complete reliability report.

        Args:
            project_id: Project identifier
            node_id: Optional node identifier
            historical_data: Historical datasets for calibration
            current_params: Current parameter values
            variable_bounds: Variable bounds for sensitivity analysis
            reference_data: Reference period data for drift detection
            current_data: Current period data for drift detection

        Returns:
            Complete ReliabilityReport
        """
        logger.info(f"Generating reliability report for project {project_id}")

        generated_at = datetime.now()
        valid_until = generated_at + timedelta(days=self.config.validity_days)

        # Initialize scores with defaults
        calibration = self._default_calibration()
        stability = self._default_stability()
        sensitivity = self._default_sensitivity()
        drift = self._default_drift()
        data_gaps = self._default_data_gaps()

        raw_stability = None
        raw_sensitivity = None
        raw_drift = None

        # Run calibration analysis
        if self.config.run_calibration and historical_data:
            calibration = self._run_calibration(historical_data, current_params or {})

        # Run stability analysis
        if self.config.run_stability and current_params:
            stability, raw_stability = self._run_stability(current_params)

        # Run sensitivity analysis
        if self.config.run_sensitivity and variable_bounds:
            sensitivity, raw_sensitivity = self._run_sensitivity(
                variable_bounds, current_params or {}
            )

        # Run drift detection
        if self.config.run_drift and reference_data and current_data:
            drift, raw_drift = self._run_drift(reference_data, current_data)

        # Check data gaps
        if self.config.check_data_gaps and current_data:
            data_gaps = self._check_data_gaps(current_data)

        # Compute overall reliability score
        overall_score = self._compute_overall_score(
            calibration, stability, sensitivity, drift, data_gaps
        )

        # Determine confidence level
        if overall_score >= 0.8:
            confidence_level = ConfidenceLevel.HIGH
        elif overall_score >= 0.6:
            confidence_level = ConfidenceLevel.MODERATE
        else:
            confidence_level = ConfidenceLevel.LOW

        # Build confidence breakdown
        confidence = self._build_confidence_breakdown(
            calibration, stability, sensitivity, drift, data_gaps
        )

        # Generate recommendations and warnings
        recommendations, warnings = self._generate_recommendations(
            calibration, stability, sensitivity, drift, data_gaps
        )

        report = ReliabilityReport(
            report_id=str(uuid4()),
            project_id=project_id,
            node_id=node_id,
            generated_at=generated_at,
            valid_until=valid_until,
            engine_version=self.config.engine_version,
            calibration=calibration,
            stability=stability,
            sensitivity=sensitivity,
            drift=drift,
            data_gaps=data_gaps,
            confidence=confidence,
            overall_reliability_score=overall_score,
            confidence_level=confidence_level,
            is_reliable=overall_score >= self.config.weights.get("threshold", 0.7),
            recommendations=recommendations,
            warnings=warnings,
            raw_stability_report=raw_stability,
            raw_sensitivity_report=raw_sensitivity,
            raw_drift_report=raw_drift,
        )

        logger.info(
            f"Reliability report generated. Score: {overall_score:.2f}, "
            f"Level: {confidence_level.value}"
        )

        return report

    def _run_calibration(
        self,
        historical_data: List[HistoricalDataset],
        current_params: Dict[str, float],
    ) -> CalibrationScore:
        """Run calibration analysis on historical data."""
        accuracies = []

        for dataset in historical_data:
            # Simulate with current params and compare to actual
            try:
                predicted = self.simulation_fn(current_params)
                actual = dataset.data  # Assuming data contains actual outcomes

                if isinstance(actual, dict):
                    metrics = compute_error_metrics_suite(predicted, actual)
                    accuracies.append(metrics.accuracy)
            except Exception as e:
                logger.warning(f"Calibration scenario failed: {e}")
                continue

        if not accuracies:
            return self._default_calibration()

        return CalibrationScore(
            accuracy=float(np.mean(accuracies)),
            historical_scenarios_run=len(accuracies),
            best_scenario_accuracy=float(np.max(accuracies)),
            worst_scenario_accuracy=float(np.min(accuracies)),
            mean_error=float(1.0 - np.mean(accuracies)),
        )

    def _run_stability(
        self,
        params: Dict[str, float],
    ) -> tuple[StabilityScore, Dict[str, Any]]:
        """Run stability analysis with multiple seeds."""
        runner = MultiSeedRunner(
            n_seeds=self.config.n_seeds,
            base_seed=42,
        )

        def sim_with_seed(seed: int) -> Dict[str, float]:
            # Inject seed into params
            seeded_params = params.copy()
            seeded_params["_seed"] = seed
            return self.simulation_fn(seeded_params)

        results = runner.run_with_seeds(sim_with_seed, parallel=False)
        report = self.stability_analyzer.analyze(results)

        score = StabilityScore(
            score=report.stability_score,
            seeds_tested=report.n_seeds,
            variance_coefficient=report.mean_variance,
            is_stable=report.is_stable,
            most_stable_outcome=report.most_stable_outcome,
            least_stable_outcome=report.least_stable_outcome,
        )

        return score, report.to_dict()

    def _run_sensitivity(
        self,
        variable_bounds: Dict[str, VariableBound],
        baseline_params: Dict[str, float],
    ) -> tuple[SensitivitySummary, Dict[str, Any]]:
        """Run sensitivity analysis."""
        report = self.sensitivity_scanner.scan(
            variables=variable_bounds,
            simulation_fn=self.simulation_fn,
            baseline_params=baseline_params,
        )

        summary = SensitivitySummary(
            n_high_impact_variables=len(report.high_impact_variables),
            top_impact_variables=report.impact_ranking[:5],
            impact_scores={
                v: report.variable_impacts[v].impact_score
                for v in report.impact_ranking[:10]
            },
            recommendations=[
                self.sensitivity_scanner._get_recommendation(report)
            ],
        )

        return summary, report.to_dict()

    def _run_drift(
        self,
        reference_data: Dict[str, List[float]],
        current_data: Dict[str, List[float]],
    ) -> tuple[DriftStatus, Dict[str, Any]]:
        """Run drift detection."""
        today = date.today()
        ref_start = today - timedelta(days=self.config.reference_window_days * 2)
        ref_end = today - timedelta(days=self.config.reference_window_days)
        curr_start = today - timedelta(days=self.config.reference_window_days)
        curr_end = today

        report = self.drift_detector.detect(
            reference_data=reference_data,
            current_data=current_data,
            reference_dates=(ref_start, ref_end),
            current_dates=(curr_start, curr_end),
        )

        status = DriftStatus(
            drift_detected=report.overall_drift_detected,
            severity=report.overall_severity.value,
            drifted_variables=report.drifted_variables[:5],
            last_check=datetime.now(),
            days_since_calibration=self.config.reference_window_days,
        )

        return status, report.to_dict()

    def _check_data_gaps(
        self,
        data: Dict[str, List[float]],
    ) -> DataGapsSummary:
        """Check for data gaps in current data."""
        total_vars = len(data)
        vars_with_gaps = 0
        critical_gaps = []

        for var_name, values in data.items():
            if not values:
                vars_with_gaps += 1
                critical_gaps.append(var_name)
                continue

            # Check for NaN/None values
            arr = np.array(values)
            nan_ratio = np.isnan(arr).sum() / len(arr) if len(arr) > 0 else 1.0

            if nan_ratio > self.config.gap_threshold:
                vars_with_gaps += 1
                if nan_ratio > 0.5:
                    critical_gaps.append(var_name)

        gap_percentage = vars_with_gaps / total_vars if total_vars > 0 else 0.0

        recommendations = []
        if critical_gaps:
            recommendations.append(
                f"Critical data gaps in: {', '.join(critical_gaps[:5])}. "
                "Update data sources before running predictions."
            )

        return DataGapsSummary(
            total_variables=total_vars,
            variables_with_gaps=vars_with_gaps,
            gap_percentage=gap_percentage,
            critical_gaps=critical_gaps[:10],
            recommendations=recommendations,
        )

    def _compute_overall_score(
        self,
        calibration: CalibrationScore,
        stability: StabilityScore,
        sensitivity: SensitivitySummary,
        drift: DriftStatus,
        data_gaps: DataGapsSummary,
    ) -> float:
        """Compute weighted overall reliability score."""
        weights = self.config.weights

        # Convert each component to 0-1 score
        calibration_score = calibration.accuracy

        stability_score = stability.score

        # Sensitivity: fewer high-impact variables is better
        sensitivity_score = max(0.0, 1.0 - (sensitivity.n_high_impact_variables / 10))

        # Drift: no drift is 1.0, critical drift is 0.0
        drift_scores = {
            DriftSeverity.NONE.value: 1.0,
            DriftSeverity.LOW.value: 0.8,
            DriftSeverity.MODERATE.value: 0.5,
            DriftSeverity.HIGH.value: 0.2,
            DriftSeverity.CRITICAL.value: 0.0,
        }
        drift_score = drift_scores.get(drift.severity, 0.5)

        # Data gaps: fewer gaps is better
        data_gaps_score = 1.0 - data_gaps.gap_percentage

        # Weighted sum
        overall = (
            weights.get("calibration", 0.35) * calibration_score +
            weights.get("stability", 0.25) * stability_score +
            weights.get("sensitivity", 0.15) * sensitivity_score +
            weights.get("drift", 0.15) * drift_score +
            weights.get("data_gaps", 0.10) * data_gaps_score
        )

        return float(np.clip(overall, 0.0, 1.0))

    def _build_confidence_breakdown(
        self,
        calibration: CalibrationScore,
        stability: StabilityScore,
        sensitivity: SensitivitySummary,
        drift: DriftStatus,
        data_gaps: DataGapsSummary,
    ) -> ConfidenceBreakdown:
        """Build detailed confidence breakdown."""
        # Overall from components
        overall = self._compute_overall_score(
            calibration, stability, sensitivity, drift, data_gaps
        )

        # By category (placeholder - would need actual category data)
        by_category = {}

        # By time horizon
        by_time_horizon = {
            "1_week": overall * 0.95,
            "1_month": overall * 0.85,
            "3_months": overall * 0.70,
            "6_months": overall * 0.50,
        }

        # Factors
        factors = {
            "calibration": calibration.accuracy,
            "stability": stability.score,
            "data_quality": 1.0 - data_gaps.gap_percentage,
            "drift_free": 1.0 if not drift.drift_detected else 0.5,
        }

        return ConfidenceBreakdown(
            overall=overall,
            by_category=by_category,
            by_time_horizon=by_time_horizon,
            factors=factors,
        )

    def _generate_recommendations(
        self,
        calibration: CalibrationScore,
        stability: StabilityScore,
        sensitivity: SensitivitySummary,
        drift: DriftStatus,
        data_gaps: DataGapsSummary,
    ) -> tuple[List[str], List[str]]:
        """Generate recommendations and warnings."""
        recommendations = []
        warnings = []

        # Calibration recommendations
        if calibration.accuracy < 0.7:
            recommendations.append(
                "Calibration accuracy is below 70%. Consider running auto-tune with more historical scenarios."
            )
        if calibration.accuracy < 0.5:
            warnings.append(
                "CRITICAL: Calibration accuracy is very low. Predictions may be unreliable."
            )

        # Stability recommendations
        if not stability.is_stable:
            recommendations.append(
                f"Model shows instability in '{stability.least_stable_outcome}'. "
                "Consider increasing population size or adjusting rule weights."
            )
            warnings.append(
                "Model produces inconsistent results across seeds. Exercise caution with predictions."
            )

        # Sensitivity recommendations
        if sensitivity.n_high_impact_variables > 3:
            recommendations.append(
                f"Found {sensitivity.n_high_impact_variables} high-impact variables. "
                "Validate data quality for these inputs carefully."
            )

        # Drift warnings
        if drift.drift_detected:
            if drift.severity in ["high", "critical"]:
                warnings.append(
                    f"Significant data drift detected ({drift.severity}). "
                    "Recalibration recommended before making predictions."
                )
            recommendations.append(
                f"Address drift in: {', '.join(drift.drifted_variables[:3])}"
            )

        # Data gap warnings
        if data_gaps.critical_gaps:
            warnings.append(
                f"Critical data gaps in {len(data_gaps.critical_gaps)} variables. "
                "Update data sources before running predictions."
            )

        return recommendations, warnings

    def _default_calibration(self) -> CalibrationScore:
        """Return default calibration score."""
        return CalibrationScore(
            accuracy=0.0,
            historical_scenarios_run=0,
            best_scenario_accuracy=0.0,
            worst_scenario_accuracy=0.0,
            mean_error=1.0,
        )

    def _default_stability(self) -> StabilityScore:
        """Return default stability score."""
        return StabilityScore(
            score=0.0,
            seeds_tested=0,
            variance_coefficient=1.0,
            is_stable=False,
            most_stable_outcome="",
            least_stable_outcome="",
        )

    def _default_sensitivity(self) -> SensitivitySummary:
        """Return default sensitivity summary."""
        return SensitivitySummary(
            n_high_impact_variables=0,
            top_impact_variables=[],
            impact_scores={},
            recommendations=["Run sensitivity analysis to identify high-impact variables."],
        )

    def _default_drift(self) -> DriftStatus:
        """Return default drift status."""
        return DriftStatus(
            drift_detected=False,
            severity="unknown",
            drifted_variables=[],
            last_check=datetime.now(),
            days_since_calibration=0,
        )

    def _default_data_gaps(self) -> DataGapsSummary:
        """Return default data gaps summary."""
        return DataGapsSummary(
            total_variables=0,
            variables_with_gaps=0,
            gap_percentage=0.0,
            critical_gaps=[],
            recommendations=["Provide data to check for gaps."],
        )

    def _default_simulation_fn(
        self,
        params: Dict[str, float],
    ) -> Dict[str, float]:
        """Default simulation function (placeholder)."""
        # Returns random distribution - should be replaced with real simulation
        return {
            "outcome_a": np.random.uniform(0.2, 0.4),
            "outcome_b": np.random.uniform(0.3, 0.5),
            "outcome_c": np.random.uniform(0.1, 0.3),
        }
