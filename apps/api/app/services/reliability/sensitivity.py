"""
Sensitivity Scanner

P7-005: Variable perturbation analysis and impact ranking.
Identifies which input variables have the largest effect on outcomes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
import numpy as np
import logging

logger = logging.getLogger(__name__)


class PerturbationType(str, Enum):
    """Types of perturbation to apply."""
    ABSOLUTE = "absolute"  # Add/subtract fixed amount
    RELATIVE = "relative"  # Multiply by factor
    RANGE = "range"  # Sweep across value range


@dataclass
class VariableBound:
    """Bounds for a variable during sensitivity analysis."""
    name: str
    baseline: float
    min_value: float
    max_value: float
    step_size: Optional[float] = None
    is_integer: bool = False

    def get_perturbation_range(
        self,
        n_steps: int = 5,
        perturbation_type: PerturbationType = PerturbationType.RELATIVE,
        perturbation_amount: float = 0.1,
    ) -> List[float]:
        """
        Get list of values to test for this variable.

        Args:
            n_steps: Number of steps for range perturbation
            perturbation_type: Type of perturbation
            perturbation_amount: Amount to perturb (0.1 = 10% for relative)

        Returns:
            List of values to test
        """
        if perturbation_type == PerturbationType.ABSOLUTE:
            values = [
                self.baseline - perturbation_amount,
                self.baseline,
                self.baseline + perturbation_amount,
            ]
        elif perturbation_type == PerturbationType.RELATIVE:
            values = [
                self.baseline * (1 - perturbation_amount),
                self.baseline,
                self.baseline * (1 + perturbation_amount),
            ]
        else:  # RANGE
            values = list(np.linspace(self.min_value, self.max_value, n_steps))

        # Clip to bounds
        values = [max(self.min_value, min(self.max_value, v)) for v in values]

        # Convert to integers if needed
        if self.is_integer:
            values = [int(round(v)) for v in values]

        # Remove duplicates while preserving order
        seen = set()
        unique_values = []
        for v in values:
            if v not in seen:
                seen.add(v)
                unique_values.append(v)

        return unique_values


@dataclass
class PerturbationResult:
    """Result from perturbing a single variable."""
    variable_name: str
    baseline_value: float
    perturbed_value: float
    perturbation_delta: float  # Difference from baseline
    perturbation_ratio: float  # Ratio to baseline

    # Outcomes
    baseline_outcomes: Dict[str, float]
    perturbed_outcomes: Dict[str, float]

    # Impact metrics
    outcome_deltas: Dict[str, float]  # Change in each outcome
    max_impact: float  # Maximum absolute change
    mean_impact: float  # Mean absolute change

    # Execution
    duration_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable_name": self.variable_name,
            "baseline_value": self.baseline_value,
            "perturbed_value": self.perturbed_value,
            "perturbation_delta": self.perturbation_delta,
            "perturbation_ratio": self.perturbation_ratio,
            "outcome_deltas": self.outcome_deltas,
            "max_impact": self.max_impact,
            "mean_impact": self.mean_impact,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class VariableImpact:
    """Aggregated impact analysis for a single variable."""
    variable_name: str

    # Sensitivity metrics
    elasticity: float  # % change in outcome per % change in variable
    impact_score: float  # Normalized 0-1 score
    direction: str  # "positive", "negative", "mixed"

    # Per-outcome sensitivities
    outcome_sensitivities: Dict[str, float]

    # Most affected outcomes
    most_affected_outcome: str
    least_affected_outcome: str

    # Raw perturbation results
    perturbation_results: List[PerturbationResult] = field(default_factory=list)

    # Classification
    is_high_impact: bool = False
    is_linear: bool = True  # Whether impact is approximately linear

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable_name": self.variable_name,
            "elasticity": self.elasticity,
            "impact_score": self.impact_score,
            "direction": self.direction,
            "outcome_sensitivities": self.outcome_sensitivities,
            "most_affected_outcome": self.most_affected_outcome,
            "least_affected_outcome": self.least_affected_outcome,
            "is_high_impact": self.is_high_impact,
            "is_linear": self.is_linear,
            "n_perturbations": len(self.perturbation_results),
        }


@dataclass
class SensitivityReport:
    """Complete sensitivity analysis report."""

    # Variables analyzed
    n_variables: int
    variables_analyzed: List[str]

    # Impact rankings
    variable_impacts: Dict[str, VariableImpact]
    impact_ranking: List[str]  # Variables sorted by impact (highest first)

    # High-impact variables
    high_impact_variables: List[str]
    high_impact_threshold: float

    # Cross-sensitivity (if computed)
    interaction_effects: Dict[Tuple[str, str], float] = field(default_factory=dict)

    # Execution
    total_perturbations: int = 0
    total_duration_seconds: float = 0.0

    # Timestamps
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_variables": self.n_variables,
            "variables_analyzed": self.variables_analyzed,
            "variable_impacts": {
                k: v.to_dict() for k, v in self.variable_impacts.items()
            },
            "impact_ranking": self.impact_ranking,
            "high_impact_variables": self.high_impact_variables,
            "high_impact_threshold": self.high_impact_threshold,
            "total_perturbations": self.total_perturbations,
            "total_duration_seconds": self.total_duration_seconds,
        }


class SensitivityScanner:
    """
    Scans variable sensitivity through controlled perturbations.

    Key features:
    - One-at-a-time (OAT) sensitivity analysis
    - Elasticity calculation (% change in output per % change in input)
    - Impact ranking across all variables
    - High-impact variable identification
    """

    def __init__(
        self,
        perturbation_type: PerturbationType = PerturbationType.RELATIVE,
        perturbation_amount: float = 0.1,
        n_steps: int = 5,
        high_impact_threshold: float = 0.5,
    ):
        """
        Initialize sensitivity scanner.

        Args:
            perturbation_type: How to perturb variables
            perturbation_amount: Amount of perturbation (0.1 = 10%)
            n_steps: Number of steps for range perturbation
            high_impact_threshold: Threshold for high-impact classification
        """
        self.perturbation_type = perturbation_type
        self.perturbation_amount = perturbation_amount
        self.n_steps = n_steps
        self.high_impact_threshold = high_impact_threshold

    def scan(
        self,
        variables: Dict[str, VariableBound],
        simulation_fn: Callable[[Dict[str, float]], Dict[str, float]],
        baseline_params: Optional[Dict[str, float]] = None,
    ) -> SensitivityReport:
        """
        Run sensitivity analysis on all variables.

        Args:
            variables: Variable bounds for sensitivity analysis
            simulation_fn: Function that takes params and returns outcomes
            baseline_params: Optional baseline parameters (uses bound defaults if None)

        Returns:
            SensitivityReport with complete analysis
        """
        start_time = datetime.now()

        # Set up baseline parameters
        if baseline_params is None:
            baseline_params = {
                name: bound.baseline for name, bound in variables.items()
            }

        # Get baseline outcomes
        baseline_outcomes = simulation_fn(baseline_params)

        # Analyze each variable
        variable_impacts = {}
        all_perturbations = []

        for var_name, bound in variables.items():
            impact = self._analyze_variable(
                var_name=var_name,
                bound=bound,
                baseline_params=baseline_params,
                baseline_outcomes=baseline_outcomes,
                simulation_fn=simulation_fn,
            )
            variable_impacts[var_name] = impact
            all_perturbations.extend(impact.perturbation_results)

        # Rank by impact score
        impact_ranking = sorted(
            variable_impacts.keys(),
            key=lambda v: variable_impacts[v].impact_score,
            reverse=True,
        )

        # Identify high-impact variables
        high_impact_variables = [
            v for v in impact_ranking
            if variable_impacts[v].impact_score >= self.high_impact_threshold
        ]

        # Mark high-impact variables
        for var_name in high_impact_variables:
            variable_impacts[var_name].is_high_impact = True

        end_time = datetime.now()

        return SensitivityReport(
            n_variables=len(variables),
            variables_analyzed=list(variables.keys()),
            variable_impacts=variable_impacts,
            impact_ranking=impact_ranking,
            high_impact_variables=high_impact_variables,
            high_impact_threshold=self.high_impact_threshold,
            total_perturbations=len(all_perturbations),
            total_duration_seconds=(end_time - start_time).total_seconds(),
            started_at=start_time,
            completed_at=end_time,
        )

    def _analyze_variable(
        self,
        var_name: str,
        bound: VariableBound,
        baseline_params: Dict[str, float],
        baseline_outcomes: Dict[str, float],
        simulation_fn: Callable[[Dict[str, float]], Dict[str, float]],
    ) -> VariableImpact:
        """Analyze sensitivity for a single variable."""
        perturbation_values = bound.get_perturbation_range(
            n_steps=self.n_steps,
            perturbation_type=self.perturbation_type,
            perturbation_amount=self.perturbation_amount,
        )

        perturbation_results = []
        outcome_changes = {outcome: [] for outcome in baseline_outcomes}

        for value in perturbation_values:
            if value == bound.baseline:
                continue  # Skip baseline

            # Create perturbed params
            perturbed_params = baseline_params.copy()
            perturbed_params[var_name] = value

            # Run simulation
            start_time = datetime.now()
            perturbed_outcomes = simulation_fn(perturbed_params)
            duration = (datetime.now() - start_time).total_seconds()

            # Calculate deltas
            outcome_deltas = {}
            for outcome, baseline_val in baseline_outcomes.items():
                if outcome in perturbed_outcomes:
                    delta = perturbed_outcomes[outcome] - baseline_val
                    outcome_deltas[outcome] = delta
                    outcome_changes[outcome].append((value, delta))

            # Calculate perturbation metrics
            delta = value - bound.baseline
            ratio = value / bound.baseline if bound.baseline != 0 else 0.0

            impacts = [abs(d) for d in outcome_deltas.values()]

            result = PerturbationResult(
                variable_name=var_name,
                baseline_value=bound.baseline,
                perturbed_value=value,
                perturbation_delta=delta,
                perturbation_ratio=ratio,
                baseline_outcomes=baseline_outcomes,
                perturbed_outcomes=perturbed_outcomes,
                outcome_deltas=outcome_deltas,
                max_impact=max(impacts) if impacts else 0.0,
                mean_impact=float(np.mean(impacts)) if impacts else 0.0,
                duration_seconds=duration,
            )

            perturbation_results.append(result)

        # Compute elasticity (average % change in outcome per % change in input)
        elasticities = []
        for result in perturbation_results:
            if result.perturbation_ratio != 1.0 and result.perturbation_ratio != 0:
                input_pct_change = (result.perturbation_ratio - 1.0)
                for outcome, delta in result.outcome_deltas.items():
                    baseline_val = baseline_outcomes.get(outcome, 1.0)
                    if baseline_val != 0:
                        output_pct_change = delta / baseline_val
                        elasticity = output_pct_change / input_pct_change
                        elasticities.append(elasticity)

        mean_elasticity = float(np.mean(np.abs(elasticities))) if elasticities else 0.0

        # Compute impact score (normalized to 0-1)
        all_mean_impacts = [r.mean_impact for r in perturbation_results]
        max_possible_impact = max(all_mean_impacts) if all_mean_impacts else 1.0
        impact_score = mean_elasticity  # Use elasticity as impact score

        # Normalize impact score to 0-1 range
        impact_score = min(1.0, abs(impact_score))

        # Determine direction
        positive_changes = sum(1 for r in perturbation_results
                              if np.mean(list(r.outcome_deltas.values())) > 0)
        negative_changes = len(perturbation_results) - positive_changes

        if positive_changes > 0.8 * len(perturbation_results):
            direction = "positive"
        elif negative_changes > 0.8 * len(perturbation_results):
            direction = "negative"
        else:
            direction = "mixed"

        # Per-outcome sensitivities
        outcome_sensitivities = {}
        for outcome, changes in outcome_changes.items():
            if changes:
                # Use max absolute change as sensitivity
                max_change = max(abs(c[1]) for c in changes)
                baseline_val = baseline_outcomes.get(outcome, 1.0)
                sensitivity = max_change / baseline_val if baseline_val != 0 else 0.0
                outcome_sensitivities[outcome] = sensitivity

        # Most/least affected outcomes
        if outcome_sensitivities:
            sorted_outcomes = sorted(
                outcome_sensitivities.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            most_affected = sorted_outcomes[0][0]
            least_affected = sorted_outcomes[-1][0]
        else:
            most_affected = ""
            least_affected = ""

        # Check linearity (R² of linear fit)
        is_linear = self._check_linearity(perturbation_results, bound.baseline)

        return VariableImpact(
            variable_name=var_name,
            elasticity=mean_elasticity,
            impact_score=impact_score,
            direction=direction,
            outcome_sensitivities=outcome_sensitivities,
            most_affected_outcome=most_affected,
            least_affected_outcome=least_affected,
            perturbation_results=perturbation_results,
            is_high_impact=False,  # Will be set by scan()
            is_linear=is_linear,
        )

    def _check_linearity(
        self,
        results: List[PerturbationResult],
        baseline: float,
        r2_threshold: float = 0.9,
    ) -> bool:
        """
        Check if variable effect is approximately linear.

        Uses R² of linear fit to determine linearity.
        """
        if len(results) < 3:
            return True  # Not enough points to determine

        # Get input-output pairs
        x = [r.perturbed_value - baseline for r in results]
        y = [r.mean_impact for r in results]

        if len(set(y)) <= 1:
            return True  # All same output, technically linear

        x = np.array(x)
        y = np.array(y)

        # Fit linear regression
        if len(x) < 2:
            return True

        # Simple R² calculation
        y_mean = np.mean(y)
        ss_tot = np.sum((y - y_mean) ** 2)

        if ss_tot == 0:
            return True

        # Linear fit
        coeffs = np.polyfit(x, y, 1)
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_pred) ** 2)

        r2 = 1 - (ss_res / ss_tot)

        return r2 >= r2_threshold

    def get_sensitivity_summary(
        self,
        report: SensitivityReport,
    ) -> Dict[str, Any]:
        """
        Get human-readable sensitivity summary.

        Args:
            report: Sensitivity report to summarize

        Returns:
            Summary dictionary with key insights
        """
        if report.high_impact_variables:
            status = "HIGH_SENSITIVITY"
            top_vars = report.high_impact_variables[:3]
            description = f"High-impact variables: {', '.join(top_vars)}"
        else:
            status = "LOW_SENSITIVITY"
            description = "No variables exceed high-impact threshold"

        return {
            "status": status,
            "description": description,
            "top_3_variables": report.impact_ranking[:3],
            "high_impact_count": len(report.high_impact_variables),
            "total_variables": report.n_variables,
            "recommendation": self._get_recommendation(report),
        }

    def _get_recommendation(self, report: SensitivityReport) -> str:
        """Generate recommendation based on sensitivity analysis."""
        if not report.high_impact_variables:
            return "Model is robust to input variations within tested ranges."

        if len(report.high_impact_variables) > 3:
            return (
                f"Many high-impact variables ({len(report.high_impact_variables)}). "
                "Consider: (1) validating input data quality, "
                "(2) running stability tests on these variables, "
                "(3) using bounded ranges in predictions."
            )

        high_vars = ", ".join(report.high_impact_variables)
        return (
            f"Focus validation efforts on high-impact variables: {high_vars}. "
            "Ensure these have accurate, well-validated data sources."
        )
