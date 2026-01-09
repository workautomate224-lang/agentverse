"""
Calibration System for Predictive Simulations

Main orchestrator for calibrating simulation parameters against ground truth.
Designed to achieve >80% predictive accuracy.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
from datetime import datetime
import logging
import json
import asyncio

from app.engine.calibration.metrics import (
    AccuracyMetrics,
    AccuracyTracker,
    compute_accuracy_metrics,
    compute_calibration_improvement,
)
from app.engine.calibration.optimizer import (
    BayesianOptimizer,
    GridSearchOptimizer,
    RandomSearchOptimizer,
    ParameterBounds,
    OptimizationResult,
    create_optimizer,
)

logger = logging.getLogger(__name__)


class CalibrationMethod(str, Enum):
    """Available calibration methods."""

    BAYESIAN = "bayesian"
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    ENSEMBLE = "ensemble"
    ADAPTIVE = "adaptive"


@dataclass
class CalibrationConfig:
    """Configuration for calibration process."""

    method: CalibrationMethod = CalibrationMethod.BAYESIAN
    target_accuracy: float = 0.80  # >80% accuracy target
    max_iterations: int = 100
    patience: int = 10  # Early stopping patience
    convergence_threshold: float = 1e-4

    # Validation settings
    validation_split: float = 0.2  # Hold out for validation
    cross_validation_folds: int = 5
    use_cross_validation: bool = False

    # Parameter bounds for common simulation parameters
    parameter_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)

    # Weights for composite objective
    accuracy_weight: float = 0.6
    kl_weight: float = 0.2
    coverage_weight: float = 0.2

    # Run settings
    n_parallel_evaluations: int = 4
    timeout_seconds: int = 3600

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "target_accuracy": self.target_accuracy,
            "max_iterations": self.max_iterations,
            "patience": self.patience,
            "convergence_threshold": self.convergence_threshold,
            "validation_split": self.validation_split,
            "cross_validation_folds": self.cross_validation_folds,
            "use_cross_validation": self.use_cross_validation,
            "parameter_bounds": self.parameter_bounds,
            "accuracy_weight": self.accuracy_weight,
            "kl_weight": self.kl_weight,
            "coverage_weight": self.coverage_weight,
        }


@dataclass
class GroundTruth:
    """Ground truth data for calibration."""

    # Main outcome distributions
    category_distributions: Dict[str, float]  # e.g., party -> vote share

    # Regional breakdown (optional)
    regional_distributions: Optional[Dict[str, Dict[str, float]]] = None

    # Time series data (optional)
    temporal_data: Optional[Dict[str, List[float]]] = None

    # Confidence intervals (if available)
    confidence_intervals: Optional[Dict[str, Tuple[float, float]]] = None

    # Metadata
    source: str = ""
    date: Optional[datetime] = None
    sample_size: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category_distributions": self.category_distributions,
            "regional_distributions": self.regional_distributions,
            "temporal_data": self.temporal_data,
            "confidence_intervals": self.confidence_intervals,
            "source": self.source,
            "date": self.date.isoformat() if self.date else None,
            "sample_size": self.sample_size,
        }


@dataclass
class CalibrationResult:
    """Result of calibration process."""

    success: bool
    best_params: Dict[str, Any]
    best_metrics: AccuracyMetrics
    improvement: Dict[str, float]
    n_iterations: int
    total_time_seconds: float
    method_used: CalibrationMethod
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)

    # Validation metrics
    validation_metrics: Optional[AccuracyMetrics] = None
    cross_validation_scores: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "best_params": self.best_params,
            "best_metrics": self.best_metrics.to_dict(),
            "improvement": self.improvement,
            "n_iterations": self.n_iterations,
            "total_time_seconds": self.total_time_seconds,
            "method_used": self.method_used.value,
            "meets_target": self.best_metrics.is_above_threshold,
        }


class Calibrator:
    """
    Main calibration orchestrator.

    Optimizes simulation parameters to match ground truth data,
    targeting >80% predictive accuracy.
    """

    def __init__(
        self,
        config: CalibrationConfig,
        simulation_runner: Callable[[Dict[str, Any]], Dict[str, float]],
    ):
        """
        Initialize calibrator.

        Args:
            config: Calibration configuration
            simulation_runner: Function that runs simulation with params and returns predictions
        """
        self.config = config
        self.simulation_runner = simulation_runner
        self.accuracy_tracker = AccuracyTracker(target_accuracy=config.target_accuracy)

        # Build parameter bounds
        self.parameter_bounds = self._build_parameter_bounds()

        # Initialize optimizer
        self.optimizer = self._create_optimizer()

        # Tracking
        self.baseline_metrics: Optional[AccuracyMetrics] = None
        self.calibration_history: List[Dict[str, Any]] = []

    def _build_parameter_bounds(self) -> List[ParameterBounds]:
        """Build parameter bounds from config."""
        bounds = []

        # Default behavioral parameters if not specified
        default_bounds = {
            "loss_aversion": (1.0, 3.0),
            "probability_weight_alpha": (0.5, 1.0),
            "probability_weight_beta": (0.5, 1.0),
            "status_quo_bias": (0.0, 1.0),
            "bandwagon_susceptibility": (0.0, 1.0),
            "confirmation_bias": (0.0, 1.0),
            "social_influence_weight": (0.0, 1.0),
            "noise_temperature": (0.01, 1.0),
            "learning_rate": (0.001, 0.1),
        }

        # Merge with config bounds
        all_bounds = {**default_bounds, **self.config.parameter_bounds}

        for name, (lower, upper) in all_bounds.items():
            bounds.append(ParameterBounds(
                name=name,
                lower=lower,
                upper=upper,
                dtype="float",
                log_scale=name in ["learning_rate", "noise_temperature"],
            ))

        return bounds

    def _create_optimizer(self):
        """Create optimizer based on method."""
        return create_optimizer(
            method=self.config.method.value.replace("_search", ""),
            parameter_bounds=self.parameter_bounds,
            n_iterations=self.config.max_iterations,
            convergence_threshold=self.config.convergence_threshold,
            convergence_patience=self.config.patience,
        )

    def _compute_objective(
        self,
        params: Dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """
        Compute calibration objective.

        Combines multiple metrics into single objective for optimization.
        Higher is better.
        """
        try:
            # Run simulation with parameters
            predictions = self.simulation_runner(params)

            # Compute metrics
            metrics = compute_accuracy_metrics(
                predictions=predictions,
                ground_truth=ground_truth.category_distributions,
                confidence_intervals=ground_truth.confidence_intervals,
                regional_predictions=None,  # Could add regional support
                regional_ground_truth=ground_truth.regional_distributions,
            )

            # Track metrics
            self.accuracy_tracker.add(metrics)

            # Composite objective
            # Higher accuracy is better, lower KL/Brier is better
            objective = (
                self.config.accuracy_weight * metrics.accuracy +
                self.config.kl_weight * (1.0 - min(metrics.kl_divergence, 1.0)) +
                self.config.coverage_weight * metrics.coverage_probability
            )

            # Record history
            self.calibration_history.append({
                "params": params,
                "metrics": metrics.to_dict(),
                "objective": objective,
                "timestamp": datetime.now().isoformat(),
            })

            logger.debug(f"Objective: {objective:.4f}, Accuracy: {metrics.accuracy:.4f}")

            return objective

        except Exception as e:
            logger.error(f"Error computing objective: {e}")
            return 0.0  # Worst case for failed evaluations

    def calibrate(
        self,
        ground_truth: GroundTruth,
        initial_params: Optional[Dict[str, Any]] = None,
    ) -> CalibrationResult:
        """
        Run calibration process.

        Args:
            ground_truth: Ground truth data to calibrate against
            initial_params: Optional starting parameters

        Returns:
            CalibrationResult with optimized parameters
        """
        start_time = datetime.now()

        logger.info(f"Starting calibration with method: {self.config.method.value}")
        logger.info(f"Target accuracy: {self.config.target_accuracy:.1%}")

        # Compute baseline if initial params provided
        if initial_params:
            predictions = self.simulation_runner(initial_params)
            self.baseline_metrics = compute_accuracy_metrics(
                predictions=predictions,
                ground_truth=ground_truth.category_distributions,
            )
            logger.info(f"Baseline accuracy: {self.baseline_metrics.accuracy:.4f}")

        # Create objective function
        def objective(params: Dict[str, Any]) -> float:
            return self._compute_objective(params, ground_truth)

        # Run optimization
        if self.config.method == CalibrationMethod.ENSEMBLE:
            result = self._run_ensemble_calibration(objective)
        elif self.config.method == CalibrationMethod.ADAPTIVE:
            result = self._run_adaptive_calibration(objective, ground_truth)
        else:
            result = self.optimizer.optimize(objective, maximize=True)

        # Get best metrics
        if self.calibration_history:
            best_entry = max(self.calibration_history, key=lambda x: x["objective"])
            best_metrics = AccuracyMetrics(**{
                k: v for k, v in best_entry["metrics"].items()
                if k in AccuracyMetrics.__dataclass_fields__
            })
        else:
            best_metrics = AccuracyMetrics()

        # Compute improvement
        if self.baseline_metrics:
            improvement = compute_calibration_improvement(
                self.baseline_metrics,
                best_metrics,
            )
        else:
            improvement = {"accuracy_improvement": best_metrics.accuracy}

        elapsed = (datetime.now() - start_time).total_seconds()

        calibration_result = CalibrationResult(
            success=best_metrics.accuracy >= self.config.target_accuracy,
            best_params=result.best_params,
            best_metrics=best_metrics,
            improvement=improvement,
            n_iterations=result.n_iterations,
            total_time_seconds=elapsed,
            method_used=self.config.method,
            optimization_history=self.calibration_history,
        )

        # Log results
        logger.info(f"Calibration complete in {elapsed:.1f}s")
        logger.info(f"Best accuracy: {best_metrics.accuracy:.4f}")
        logger.info(f"Target met: {calibration_result.success}")

        return calibration_result

    def _run_ensemble_calibration(
        self,
        objective: Callable[[Dict[str, Any]], float],
    ) -> OptimizationResult:
        """Run multiple optimization methods and combine results."""
        results = []

        # Run each method
        methods = [
            CalibrationMethod.BAYESIAN,
            CalibrationMethod.GRID_SEARCH,
            CalibrationMethod.RANDOM_SEARCH,
        ]

        for method in methods:
            try:
                optimizer = create_optimizer(
                    method=method.value.replace("_search", ""),
                    parameter_bounds=self.parameter_bounds,
                    n_iterations=self.config.max_iterations // len(methods),
                )
                result = optimizer.optimize(objective, maximize=True)
                results.append(result)
            except Exception as e:
                logger.error(f"Error in {method.value}: {e}")

        # Return best result
        if results:
            return max(results, key=lambda r: r.best_score)
        else:
            return OptimizationResult(best_params={}, best_score=0.0)

    def _run_adaptive_calibration(
        self,
        objective: Callable[[Dict[str, Any]], float],
        ground_truth: GroundTruth,
    ) -> OptimizationResult:
        """
        Adaptive calibration that switches methods based on progress.

        Starts with random search for exploration, then Bayesian for exploitation.
        """
        # Phase 1: Random exploration
        random_optimizer = RandomSearchOptimizer(
            parameter_bounds=self.parameter_bounds,
            n_iterations=self.config.max_iterations // 4,
        )
        random_result = random_optimizer.optimize(objective, maximize=True)

        # Check if we already meet target
        if self.accuracy_tracker.meets_target():
            return random_result

        # Phase 2: Bayesian refinement
        bayesian_optimizer = BayesianOptimizer(
            parameter_bounds=self.parameter_bounds,
            n_initial=5,
            n_iterations=self.config.max_iterations * 3 // 4,
            convergence_patience=self.config.patience,
        )

        # Initialize with random search results
        for entry in random_optimizer.history:
            bayesian_optimizer.update(entry["params"], entry["score"])

        bayesian_result = bayesian_optimizer.optimize(objective, maximize=True)

        # Return best overall
        if bayesian_result.best_score > random_result.best_score:
            return bayesian_result
        return random_result

    async def calibrate_async(
        self,
        ground_truth: GroundTruth,
        initial_params: Optional[Dict[str, Any]] = None,
    ) -> CalibrationResult:
        """Async version of calibration for integration with async simulation."""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.calibrate(ground_truth, initial_params),
        )

    def get_progress(self) -> Dict[str, Any]:
        """Get current calibration progress."""
        trend = self.accuracy_tracker.get_trend()
        return {
            "n_evaluations": len(self.calibration_history),
            "current_accuracy": trend.get("latest", 0.0),
            "best_accuracy": trend.get("max", 0.0),
            "mean_accuracy": trend.get("mean", 0.0),
            "trend": trend.get("trend", 0.0),
            "improving": self.accuracy_tracker.is_improving(),
            "meets_target": self.accuracy_tracker.meets_target(),
            "target_gap": trend.get("target_gap", 1.0),
        }


def create_calibrator(
    config: CalibrationConfig,
    simulation_runner: Callable[[Dict[str, Any]], Dict[str, float]],
) -> Calibrator:
    """Factory function to create calibrator."""
    return Calibrator(config, simulation_runner)


class CalibrationManager:
    """
    Manages multiple calibration sessions and stores results.

    Useful for A/B testing different calibration approaches.
    """

    def __init__(self):
        self.sessions: Dict[str, Calibrator] = {}
        self.results: Dict[str, CalibrationResult] = {}

    def create_session(
        self,
        session_id: str,
        config: CalibrationConfig,
        simulation_runner: Callable[[Dict[str, Any]], Dict[str, float]],
    ) -> Calibrator:
        """Create new calibration session."""
        calibrator = Calibrator(config, simulation_runner)
        self.sessions[session_id] = calibrator
        return calibrator

    def run_session(
        self,
        session_id: str,
        ground_truth: GroundTruth,
        initial_params: Optional[Dict[str, Any]] = None,
    ) -> CalibrationResult:
        """Run calibration session."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        calibrator = self.sessions[session_id]
        result = calibrator.calibrate(ground_truth, initial_params)
        self.results[session_id] = result

        return result

    def compare_sessions(self, session_ids: List[str]) -> Dict[str, Any]:
        """Compare results across sessions."""
        comparison = {}

        for sid in session_ids:
            if sid in self.results:
                result = self.results[sid]
                comparison[sid] = {
                    "accuracy": result.best_metrics.accuracy,
                    "iterations": result.n_iterations,
                    "time_seconds": result.total_time_seconds,
                    "method": result.method_used.value,
                    "success": result.success,
                }

        # Rank by accuracy
        ranked = sorted(comparison.items(), key=lambda x: x[1]["accuracy"], reverse=True)

        return {
            "comparison": comparison,
            "ranking": [sid for sid, _ in ranked],
            "best_session": ranked[0][0] if ranked else None,
        }

    def get_session_progress(self, session_id: str) -> Dict[str, Any]:
        """Get progress for a session."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}

        return self.sessions[session_id].get_progress()
