"""
Drift Detector

P7-006: Dataset distribution shift detection.
Monitors for drift between training/calibration data and current data.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
from enum import Enum
import numpy as np
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class DriftType(str, Enum):
    """Types of drift to detect."""
    COVARIATE = "covariate"  # Input distribution shift
    CONCEPT = "concept"  # Relationship between input and output changes
    LABEL = "label"  # Output distribution shift
    TEMPORAL = "temporal"  # Time-based drift


class DriftSeverity(str, Enum):
    """Severity levels for drift."""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DistributionSnapshot:
    """Snapshot of a distribution at a point in time."""
    name: str
    snapshot_date: date
    n_samples: int

    # Distribution statistics
    mean: float
    std: float
    median: float
    min_value: float
    max_value: float
    percentiles: Dict[int, float]  # {5: val, 25: val, 50: val, 75: val, 95: val}

    # Histogram
    histogram_bins: List[float] = field(default_factory=list)
    histogram_counts: List[int] = field(default_factory=list)

    # Category distribution (for categorical variables)
    category_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "snapshot_date": self.snapshot_date.isoformat(),
            "n_samples": self.n_samples,
            "mean": self.mean,
            "std": self.std,
            "median": self.median,
            "min": self.min_value,
            "max": self.max_value,
            "percentiles": self.percentiles,
        }


@dataclass
class DistributionComparison:
    """Comparison between two distributions."""
    variable_name: str
    reference_date: date
    current_date: date

    # Statistical tests
    ks_statistic: float  # Kolmogorov-Smirnov test statistic
    ks_pvalue: float
    js_divergence: float  # Jensen-Shannon divergence
    wasserstein_distance: float  # Earth mover's distance

    # Drift detection
    is_drifted: bool
    drift_severity: DriftSeverity
    drift_threshold: float

    # Change metrics
    mean_change: float
    std_change: float
    distribution_change: float  # Overall change score

    # Details
    reference_snapshot: Optional[DistributionSnapshot] = None
    current_snapshot: Optional[DistributionSnapshot] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable_name": self.variable_name,
            "reference_date": self.reference_date.isoformat(),
            "current_date": self.current_date.isoformat(),
            "ks_statistic": self.ks_statistic,
            "ks_pvalue": self.ks_pvalue,
            "js_divergence": self.js_divergence,
            "wasserstein_distance": self.wasserstein_distance,
            "is_drifted": self.is_drifted,
            "drift_severity": self.drift_severity.value,
            "drift_threshold": self.drift_threshold,
            "mean_change": self.mean_change,
            "std_change": self.std_change,
            "distribution_change": self.distribution_change,
        }


@dataclass
class DriftAlert:
    """Alert for detected drift."""
    variable_name: str
    drift_type: DriftType
    severity: DriftSeverity
    detected_at: datetime
    description: str
    recommendation: str
    comparison: Optional[DistributionComparison] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable_name": self.variable_name,
            "drift_type": self.drift_type.value,
            "severity": self.severity.value,
            "detected_at": self.detected_at.isoformat(),
            "description": self.description,
            "recommendation": self.recommendation,
        }


@dataclass
class DriftReport:
    """Complete drift detection report."""

    # Analysis period
    reference_start: date
    reference_end: date
    current_start: date
    current_end: date

    # Variables analyzed
    n_variables: int
    variables_analyzed: List[str]

    # Drift status
    overall_drift_detected: bool
    overall_severity: DriftSeverity

    # Per-variable comparisons
    comparisons: Dict[str, DistributionComparison]

    # Drifted variables
    drifted_variables: List[str]
    drift_by_severity: Dict[str, List[str]]  # severity -> variable names

    # Alerts
    alerts: List[DriftAlert]

    # Recommendations
    recommendations: List[str]

    # Execution
    analysis_duration_seconds: float

    # Timestamps
    analyzed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference_period": {
                "start": self.reference_start.isoformat(),
                "end": self.reference_end.isoformat(),
            },
            "current_period": {
                "start": self.current_start.isoformat(),
                "end": self.current_end.isoformat(),
            },
            "n_variables": self.n_variables,
            "variables_analyzed": self.variables_analyzed,
            "overall_drift_detected": self.overall_drift_detected,
            "overall_severity": self.overall_severity.value,
            "comparisons": {
                k: v.to_dict() for k, v in self.comparisons.items()
            },
            "drifted_variables": self.drifted_variables,
            "drift_by_severity": self.drift_by_severity,
            "alerts": [a.to_dict() for a in self.alerts],
            "recommendations": self.recommendations,
            "analysis_duration_seconds": self.analysis_duration_seconds,
            "analyzed_at": self.analyzed_at.isoformat(),
        }


class DriftDetector:
    """
    Detects distribution drift between reference and current data.

    Key features:
    - Statistical tests (KS, JS divergence, Wasserstein)
    - Severity classification
    - Alert generation with recommendations
    """

    def __init__(
        self,
        drift_threshold: float = 0.05,
        severity_thresholds: Optional[Dict[DriftSeverity, float]] = None,
        n_histogram_bins: int = 20,
    ):
        """
        Initialize drift detector.

        Args:
            drift_threshold: P-value threshold for KS test
            severity_thresholds: Thresholds for severity levels
            n_histogram_bins: Number of bins for histogram comparison
        """
        self.drift_threshold = drift_threshold
        self.n_histogram_bins = n_histogram_bins

        # Default severity thresholds (based on JS divergence)
        self.severity_thresholds = severity_thresholds or {
            DriftSeverity.LOW: 0.1,
            DriftSeverity.MODERATE: 0.2,
            DriftSeverity.HIGH: 0.3,
            DriftSeverity.CRITICAL: 0.5,
        }

    def detect(
        self,
        reference_data: Dict[str, List[float]],
        current_data: Dict[str, List[float]],
        reference_dates: Tuple[date, date],
        current_dates: Tuple[date, date],
    ) -> DriftReport:
        """
        Detect drift between reference and current data.

        Args:
            reference_data: Variable name -> list of values (reference period)
            current_data: Variable name -> list of values (current period)
            reference_dates: (start, end) dates for reference period
            current_dates: (start, end) dates for current period

        Returns:
            DriftReport with complete analysis
        """
        start_time = datetime.now()

        # Find common variables
        common_vars = set(reference_data.keys()) & set(current_data.keys())

        comparisons = {}
        alerts = []
        drifted_variables = []
        drift_by_severity: Dict[str, List[str]] = {
            s.value: [] for s in DriftSeverity
        }

        for var_name in common_vars:
            ref_values = np.array(reference_data[var_name])
            curr_values = np.array(current_data[var_name])

            # Create snapshots
            ref_snapshot = self._create_snapshot(
                var_name, ref_values, reference_dates[1]
            )
            curr_snapshot = self._create_snapshot(
                var_name, curr_values, current_dates[1]
            )

            # Compare distributions
            comparison = self._compare_distributions(
                var_name=var_name,
                ref_values=ref_values,
                curr_values=curr_values,
                ref_snapshot=ref_snapshot,
                curr_snapshot=curr_snapshot,
                reference_date=reference_dates[1],
                current_date=current_dates[1],
            )

            comparisons[var_name] = comparison

            if comparison.is_drifted:
                drifted_variables.append(var_name)
                drift_by_severity[comparison.drift_severity.value].append(var_name)

                # Generate alert
                alert = self._create_alert(var_name, comparison)
                alerts.append(alert)

        # Determine overall drift status
        if drifted_variables:
            overall_drift = True
            # Overall severity is the max severity
            if drift_by_severity[DriftSeverity.CRITICAL.value]:
                overall_severity = DriftSeverity.CRITICAL
            elif drift_by_severity[DriftSeverity.HIGH.value]:
                overall_severity = DriftSeverity.HIGH
            elif drift_by_severity[DriftSeverity.MODERATE.value]:
                overall_severity = DriftSeverity.MODERATE
            else:
                overall_severity = DriftSeverity.LOW
        else:
            overall_drift = False
            overall_severity = DriftSeverity.NONE

        # Generate recommendations
        recommendations = self._generate_recommendations(
            comparisons, drifted_variables, overall_severity
        )

        duration = (datetime.now() - start_time).total_seconds()

        return DriftReport(
            reference_start=reference_dates[0],
            reference_end=reference_dates[1],
            current_start=current_dates[0],
            current_end=current_dates[1],
            n_variables=len(common_vars),
            variables_analyzed=list(common_vars),
            overall_drift_detected=overall_drift,
            overall_severity=overall_severity,
            comparisons=comparisons,
            drifted_variables=drifted_variables,
            drift_by_severity=drift_by_severity,
            alerts=alerts,
            recommendations=recommendations,
            analysis_duration_seconds=duration,
            analyzed_at=datetime.now(),
        )

    def _create_snapshot(
        self,
        name: str,
        values: np.ndarray,
        snapshot_date: date,
    ) -> DistributionSnapshot:
        """Create distribution snapshot from values."""
        if len(values) == 0:
            return DistributionSnapshot(
                name=name,
                snapshot_date=snapshot_date,
                n_samples=0,
                mean=0.0,
                std=0.0,
                median=0.0,
                min_value=0.0,
                max_value=0.0,
                percentiles={},
            )

        # Compute statistics
        percentile_keys = [5, 25, 50, 75, 95]
        percentiles = {
            p: float(np.percentile(values, p)) for p in percentile_keys
        }

        # Compute histogram
        hist_counts, hist_bins = np.histogram(values, bins=self.n_histogram_bins)

        return DistributionSnapshot(
            name=name,
            snapshot_date=snapshot_date,
            n_samples=len(values),
            mean=float(np.mean(values)),
            std=float(np.std(values)),
            median=float(np.median(values)),
            min_value=float(np.min(values)),
            max_value=float(np.max(values)),
            percentiles=percentiles,
            histogram_bins=hist_bins.tolist(),
            histogram_counts=hist_counts.tolist(),
        )

    def _compare_distributions(
        self,
        var_name: str,
        ref_values: np.ndarray,
        curr_values: np.ndarray,
        ref_snapshot: DistributionSnapshot,
        curr_snapshot: DistributionSnapshot,
        reference_date: date,
        current_date: date,
    ) -> DistributionComparison:
        """Compare two distributions and detect drift."""
        # Kolmogorov-Smirnov test
        if len(ref_values) > 0 and len(curr_values) > 0:
            ks_stat, ks_pvalue = stats.ks_2samp(ref_values, curr_values)
        else:
            ks_stat, ks_pvalue = 0.0, 1.0

        # Jensen-Shannon divergence
        js_div = self._compute_js_divergence(ref_values, curr_values)

        # Wasserstein distance (Earth mover's distance)
        if len(ref_values) > 0 and len(curr_values) > 0:
            wasserstein = float(stats.wasserstein_distance(ref_values, curr_values))
        else:
            wasserstein = 0.0

        # Determine if drifted
        is_drifted = ks_pvalue < self.drift_threshold

        # Determine severity based on JS divergence
        severity = DriftSeverity.NONE
        for sev in [DriftSeverity.CRITICAL, DriftSeverity.HIGH,
                    DriftSeverity.MODERATE, DriftSeverity.LOW]:
            if js_div >= self.severity_thresholds[sev]:
                severity = sev
                break

        if is_drifted and severity == DriftSeverity.NONE:
            severity = DriftSeverity.LOW

        # Change metrics
        mean_change = curr_snapshot.mean - ref_snapshot.mean
        std_change = curr_snapshot.std - ref_snapshot.std

        # Overall distribution change (normalized)
        if ref_snapshot.std > 0:
            distribution_change = abs(mean_change) / ref_snapshot.std
        else:
            distribution_change = 0.0

        return DistributionComparison(
            variable_name=var_name,
            reference_date=reference_date,
            current_date=current_date,
            ks_statistic=float(ks_stat),
            ks_pvalue=float(ks_pvalue),
            js_divergence=js_div,
            wasserstein_distance=wasserstein,
            is_drifted=is_drifted,
            drift_severity=severity,
            drift_threshold=self.drift_threshold,
            mean_change=mean_change,
            std_change=std_change,
            distribution_change=distribution_change,
            reference_snapshot=ref_snapshot,
            current_snapshot=curr_snapshot,
        )

    def _compute_js_divergence(
        self,
        ref_values: np.ndarray,
        curr_values: np.ndarray,
        epsilon: float = 1e-10,
    ) -> float:
        """Compute Jensen-Shannon divergence between two distributions."""
        if len(ref_values) == 0 or len(curr_values) == 0:
            return 0.0

        # Create common bins
        all_values = np.concatenate([ref_values, curr_values])
        bins = np.histogram_bin_edges(all_values, bins=self.n_histogram_bins)

        # Compute histograms
        ref_hist, _ = np.histogram(ref_values, bins=bins, density=True)
        curr_hist, _ = np.histogram(curr_values, bins=bins, density=True)

        # Add epsilon for numerical stability
        ref_hist = ref_hist + epsilon
        curr_hist = curr_hist + epsilon

        # Normalize to probability distributions
        ref_hist = ref_hist / ref_hist.sum()
        curr_hist = curr_hist / curr_hist.sum()

        # Compute JS divergence
        m = 0.5 * (ref_hist + curr_hist)

        kl_ref = np.sum(ref_hist * np.log(ref_hist / m))
        kl_curr = np.sum(curr_hist * np.log(curr_hist / m))

        js_div = 0.5 * (kl_ref + kl_curr)

        return float(js_div)

    def _create_alert(
        self,
        var_name: str,
        comparison: DistributionComparison,
    ) -> DriftAlert:
        """Create drift alert for a variable."""
        # Determine drift type
        drift_type = DriftType.COVARIATE

        # Create description
        if comparison.mean_change > 0:
            direction = "increased"
        else:
            direction = "decreased"

        description = (
            f"{var_name} has {comparison.drift_severity.value} drift. "
            f"Mean {direction} by {abs(comparison.mean_change):.2f}. "
            f"KS p-value: {comparison.ks_pvalue:.4f}, "
            f"JS divergence: {comparison.js_divergence:.4f}"
        )

        # Create recommendation
        recommendation = self._get_variable_recommendation(var_name, comparison)

        return DriftAlert(
            variable_name=var_name,
            drift_type=drift_type,
            severity=comparison.drift_severity,
            detected_at=datetime.now(),
            description=description,
            recommendation=recommendation,
            comparison=comparison,
        )

    def _get_variable_recommendation(
        self,
        var_name: str,
        comparison: DistributionComparison,
    ) -> str:
        """Get recommendation for a drifted variable."""
        if comparison.drift_severity == DriftSeverity.CRITICAL:
            return (
                f"CRITICAL: Immediately investigate {var_name}. "
                "Consider pausing predictions until drift is addressed."
            )
        elif comparison.drift_severity == DriftSeverity.HIGH:
            return (
                f"Recalibrate model with recent data for {var_name}. "
                "Monitor closely for continued drift."
            )
        elif comparison.drift_severity == DriftSeverity.MODERATE:
            return (
                f"Schedule recalibration for {var_name} within 1-2 weeks. "
                "Continue monitoring."
            )
        else:
            return f"Monitor {var_name} for continued drift."

    def _generate_recommendations(
        self,
        comparisons: Dict[str, DistributionComparison],
        drifted_variables: List[str],
        overall_severity: DriftSeverity,
    ) -> List[str]:
        """Generate overall recommendations based on drift analysis."""
        recommendations = []

        if not drifted_variables:
            recommendations.append(
                "No significant drift detected. Model is well-calibrated for current data."
            )
            return recommendations

        # Overall severity recommendations
        if overall_severity == DriftSeverity.CRITICAL:
            recommendations.append(
                "CRITICAL: Significant data drift detected. "
                "Recommend immediate model recalibration before making predictions."
            )
        elif overall_severity == DriftSeverity.HIGH:
            recommendations.append(
                "HIGH: Substantial drift detected. "
                "Recommend recalibration within 24-48 hours."
            )

        # Count drifted variables
        n_drifted = len(drifted_variables)
        n_total = len(comparisons)

        if n_drifted > n_total * 0.5:
            recommendations.append(
                f"Over half of variables ({n_drifted}/{n_total}) show drift. "
                "Consider updating underlying data sources."
            )

        # Specific variable recommendations
        critical_vars = [
            v for v in drifted_variables
            if comparisons[v].drift_severity == DriftSeverity.CRITICAL
        ]
        if critical_vars:
            recommendations.append(
                f"Priority variables for investigation: {', '.join(critical_vars)}"
            )

        return recommendations

    def get_drift_summary(self, report: DriftReport) -> Dict[str, Any]:
        """
        Get human-readable drift summary.

        Args:
            report: Drift report to summarize

        Returns:
            Summary dictionary with key insights
        """
        if report.overall_drift_detected:
            status = f"DRIFT_DETECTED ({report.overall_severity.value.upper()})"
        else:
            status = "NO_DRIFT"

        return {
            "status": status,
            "overall_severity": report.overall_severity.value,
            "drifted_count": len(report.drifted_variables),
            "total_variables": report.n_variables,
            "drifted_percentage": f"{len(report.drifted_variables) / report.n_variables * 100:.1f}%"
                if report.n_variables > 0 else "0%",
            "top_drifted_variables": report.drifted_variables[:5],
            "recommendations": report.recommendations,
        }
