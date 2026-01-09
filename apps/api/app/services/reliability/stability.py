"""
Stability Suite

P7-004: Multi-seed variance reporting for prediction stability.
Runs simulations with different seeds and measures variance in outcomes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class SeedRunResult:
    """Result from a single seed run."""
    seed: int
    outcomes: Dict[str, float]  # Probability distribution
    metrics: Dict[str, float]  # Additional metrics
    duration_seconds: float
    success: bool
    error: Optional[str] = None


@dataclass
class OutcomeVariance:
    """Variance analysis for a single outcome category."""
    category: str
    mean: float
    std: float
    variance: float
    min_value: float
    max_value: float
    range: float
    coefficient_of_variation: float  # std / mean (relative variance)
    values_by_seed: Dict[int, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "mean": self.mean,
            "std": self.std,
            "variance": self.variance,
            "min": self.min_value,
            "max": self.max_value,
            "range": self.range,
            "cv": self.coefficient_of_variation,
        }


@dataclass
class SeedVarianceReport:
    """Complete variance report across multiple seeds."""

    # Run configuration
    n_seeds: int
    seeds_used: List[int]
    base_seed: int

    # Outcome variance
    outcome_variances: Dict[str, OutcomeVariance]

    # Aggregate metrics
    mean_variance: float  # Average variance across outcomes
    max_variance: float  # Maximum variance (least stable outcome)
    stability_score: float  # 1 - normalized variance (0-1, higher = more stable)

    # Stability classification
    is_stable: bool
    stability_threshold: float

    # Most/least stable outcomes
    most_stable_outcome: str
    least_stable_outcome: str

    # Run details
    successful_runs: int
    failed_runs: int
    total_duration_seconds: float

    # Timestamps
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_seeds": self.n_seeds,
            "seeds_used": self.seeds_used,
            "base_seed": self.base_seed,
            "outcome_variances": {
                k: v.to_dict() for k, v in self.outcome_variances.items()
            },
            "mean_variance": self.mean_variance,
            "max_variance": self.max_variance,
            "stability_score": self.stability_score,
            "is_stable": self.is_stable,
            "stability_threshold": self.stability_threshold,
            "most_stable_outcome": self.most_stable_outcome,
            "least_stable_outcome": self.least_stable_outcome,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "total_duration_seconds": self.total_duration_seconds,
        }


class MultiSeedRunner:
    """
    Runs simulations with multiple seeds for stability analysis.

    Generates deterministic seeds from a base seed to ensure reproducibility.
    """

    def __init__(
        self,
        n_seeds: int = 10,
        base_seed: int = 42,
        max_workers: int = 4,
    ):
        """
        Initialize multi-seed runner.

        Args:
            n_seeds: Number of seeds to test
            base_seed: Base seed for generating seed sequence
            max_workers: Max parallel workers for running simulations
        """
        self.n_seeds = n_seeds
        self.base_seed = base_seed
        self.max_workers = max_workers

    def generate_seeds(self) -> List[int]:
        """Generate deterministic seed sequence from base seed."""
        rng = np.random.default_rng(self.base_seed)
        return [int(rng.integers(0, 2**31)) for _ in range(self.n_seeds)]

    def run_with_seeds(
        self,
        simulation_fn: Callable[[int], Dict[str, float]],
        seeds: Optional[List[int]] = None,
        parallel: bool = True,
    ) -> List[SeedRunResult]:
        """
        Run simulation with multiple seeds.

        Args:
            simulation_fn: Function that takes a seed and returns outcome distribution
            seeds: Optional custom seed list (uses generated seeds if None)
            parallel: Whether to run in parallel

        Returns:
            List of SeedRunResult for each seed
        """
        if seeds is None:
            seeds = self.generate_seeds()

        results = []

        if parallel and len(seeds) > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_seed = {
                    executor.submit(self._run_single, simulation_fn, seed): seed
                    for seed in seeds
                }

                for future in as_completed(future_to_seed):
                    seed = future_to_seed[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        results.append(SeedRunResult(
                            seed=seed,
                            outcomes={},
                            metrics={},
                            duration_seconds=0.0,
                            success=False,
                            error=str(e),
                        ))
        else:
            # Sequential execution
            for seed in seeds:
                result = self._run_single(simulation_fn, seed)
                results.append(result)

        # Sort by seed for consistent ordering
        results.sort(key=lambda r: r.seed)
        return results

    def _run_single(
        self,
        simulation_fn: Callable[[int], Dict[str, float]],
        seed: int,
    ) -> SeedRunResult:
        """Run a single simulation with given seed."""
        start_time = datetime.now()

        try:
            outcomes = simulation_fn(seed)
            duration = (datetime.now() - start_time).total_seconds()

            return SeedRunResult(
                seed=seed,
                outcomes=outcomes,
                metrics={},
                duration_seconds=duration,
                success=True,
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"Seed run failed (seed={seed}): {e}")

            return SeedRunResult(
                seed=seed,
                outcomes={},
                metrics={},
                duration_seconds=duration,
                success=False,
                error=str(e),
            )


class StabilityAnalyzer:
    """
    Analyzes stability of simulation outcomes across multiple seeds.

    Key features:
    - Variance analysis per outcome category
    - Coefficient of variation for relative stability
    - Stability classification with configurable threshold
    """

    def __init__(
        self,
        stability_threshold: float = 0.1,
        min_successful_runs: int = 3,
    ):
        """
        Initialize stability analyzer.

        Args:
            stability_threshold: Max allowed coefficient of variation for "stable"
            min_successful_runs: Minimum successful runs for valid analysis
        """
        self.stability_threshold = stability_threshold
        self.min_successful_runs = min_successful_runs

    def analyze(
        self,
        results: List[SeedRunResult],
        base_seed: int = 42,
    ) -> SeedVarianceReport:
        """
        Analyze variance across seed runs.

        Args:
            results: List of seed run results
            base_seed: Base seed used for generation

        Returns:
            SeedVarianceReport with complete variance analysis
        """
        start_time = datetime.now()

        # Filter successful runs
        successful_results = [r for r in results if r.success]
        failed_count = len(results) - len(successful_results)

        if len(successful_results) < self.min_successful_runs:
            logger.warning(
                f"Only {len(successful_results)} successful runs, "
                f"minimum {self.min_successful_runs} required"
            )

        # Collect all outcome categories
        all_categories = set()
        for result in successful_results:
            all_categories.update(result.outcomes.keys())

        # Compute variance for each category
        outcome_variances = {}

        for category in all_categories:
            values = []
            values_by_seed = {}

            for result in successful_results:
                if category in result.outcomes:
                    value = result.outcomes[category]
                    values.append(value)
                    values_by_seed[result.seed] = value

            if values:
                values_arr = np.array(values)
                mean = float(np.mean(values_arr))
                std = float(np.std(values_arr))
                variance = float(np.var(values_arr))
                min_val = float(np.min(values_arr))
                max_val = float(np.max(values_arr))

                # Coefficient of variation (relative variance)
                cv = std / mean if mean > 0 else 0.0

                outcome_variances[category] = OutcomeVariance(
                    category=category,
                    mean=mean,
                    std=std,
                    variance=variance,
                    min_value=min_val,
                    max_value=max_val,
                    range=max_val - min_val,
                    coefficient_of_variation=cv,
                    values_by_seed=values_by_seed,
                )

        # Aggregate metrics
        if outcome_variances:
            variances = [v.variance for v in outcome_variances.values()]
            cvs = [v.coefficient_of_variation for v in outcome_variances.values()]

            mean_variance = float(np.mean(variances))
            max_variance = float(np.max(variances))

            # Stability score based on mean CV
            mean_cv = float(np.mean(cvs))
            stability_score = max(0.0, 1.0 - mean_cv)

            # Is stable if all CVs below threshold
            is_stable = all(v.coefficient_of_variation <= self.stability_threshold
                          for v in outcome_variances.values())

            # Most/least stable
            sorted_by_cv = sorted(
                outcome_variances.items(),
                key=lambda x: x[1].coefficient_of_variation
            )
            most_stable = sorted_by_cv[0][0]
            least_stable = sorted_by_cv[-1][0]
        else:
            mean_variance = 0.0
            max_variance = 0.0
            stability_score = 0.0
            is_stable = False
            most_stable = ""
            least_stable = ""

        # Total duration
        total_duration = sum(r.duration_seconds for r in results)

        end_time = datetime.now()

        return SeedVarianceReport(
            n_seeds=len(results),
            seeds_used=[r.seed for r in results],
            base_seed=base_seed,
            outcome_variances=outcome_variances,
            mean_variance=mean_variance,
            max_variance=max_variance,
            stability_score=stability_score,
            is_stable=is_stable,
            stability_threshold=self.stability_threshold,
            most_stable_outcome=most_stable,
            least_stable_outcome=least_stable,
            successful_runs=len(successful_results),
            failed_runs=failed_count,
            total_duration_seconds=total_duration,
            started_at=start_time,
            completed_at=end_time,
        )

    def compare_stability(
        self,
        report_a: SeedVarianceReport,
        report_b: SeedVarianceReport,
    ) -> Dict[str, Any]:
        """
        Compare stability between two configurations.

        Args:
            report_a: First stability report
            report_b: Second stability report

        Returns:
            Comparison summary with improvements/regressions
        """
        comparison = {
            "stability_score_change": report_b.stability_score - report_a.stability_score,
            "is_improvement": report_b.stability_score > report_a.stability_score,
            "mean_variance_change": report_b.mean_variance - report_a.mean_variance,
            "category_changes": {},
        }

        # Compare per-category
        common_categories = set(report_a.outcome_variances.keys()) & set(report_b.outcome_variances.keys())

        for category in common_categories:
            var_a = report_a.outcome_variances[category]
            var_b = report_b.outcome_variances[category]

            comparison["category_changes"][category] = {
                "cv_change": var_b.coefficient_of_variation - var_a.coefficient_of_variation,
                "variance_change": var_b.variance - var_a.variance,
                "improved": var_b.coefficient_of_variation < var_a.coefficient_of_variation,
            }

        return comparison

    def get_stability_summary(
        self,
        report: SeedVarianceReport,
    ) -> Dict[str, Any]:
        """
        Get human-readable stability summary.

        Args:
            report: Stability report to summarize

        Returns:
            Summary dictionary with key insights
        """
        if report.is_stable:
            status = "STABLE"
            status_description = "All outcome categories show consistent results across seeds"
        else:
            status = "UNSTABLE"
            unstable_categories = [
                k for k, v in report.outcome_variances.items()
                if v.coefficient_of_variation > self.stability_threshold
            ]
            status_description = f"High variance in: {', '.join(unstable_categories)}"

        return {
            "status": status,
            "description": status_description,
            "stability_score": f"{report.stability_score:.1%}",
            "most_stable": report.most_stable_outcome,
            "least_stable": report.least_stable_outcome,
            "recommendation": self._get_recommendation(report),
        }

    def _get_recommendation(self, report: SeedVarianceReport) -> str:
        """Generate recommendation based on stability analysis."""
        if report.is_stable:
            return "Simulation is stable. Results can be trusted for predictions."

        if report.stability_score < 0.5:
            return (
                "High instability detected. Consider: "
                "(1) increasing agent population size, "
                "(2) reviewing rule weights, "
                "(3) checking for sensitivity to initial conditions."
            )

        if report.stability_score < 0.8:
            return (
                f"Moderate instability in '{report.least_stable_outcome}'. "
                "Consider running more seeds or adjusting parameters."
            )

        return (
            "Near-stable with minor variance. "
            f"Focus on stabilizing '{report.least_stable_outcome}'."
        )
