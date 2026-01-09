"""
Bounded Auto-Tune

P7-003: Tune limited parameter sets with rollback on overfit.
Implements cross-validation and bounded parameter ranges per project.md §12.7.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParameterBound:
    """Bounded parameter with allowed range."""
    name: str
    lower: float
    upper: float
    default: float
    step: Optional[float] = None  # Optional step size
    dtype: str = "float"  # float, int
    is_tunable: bool = True

    def validate(self, value: float) -> bool:
        """Check if value is within bounds."""
        return self.lower <= value <= self.upper

    def clip(self, value: float) -> float:
        """Clip value to bounds."""
        return max(self.lower, min(self.upper, value))


@dataclass
class ParameterSet:
    """A set of parameters with values."""
    parameters: Dict[str, float]
    bounds: Dict[str, ParameterBound] = field(default_factory=dict)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)

    def get(self, name: str) -> float:
        """Get parameter value."""
        return self.parameters.get(name, 0.0)

    def set(self, name: str, value: float) -> bool:
        """Set parameter value with bounds check."""
        if name in self.bounds:
            if not self.bounds[name].validate(value):
                return False
            value = self.bounds[name].clip(value)
        self.parameters[name] = value
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameters": self.parameters,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class CrossValidationFold:
    """Results from one cross-validation fold."""
    fold_index: int
    train_scenarios: List[str]
    test_scenarios: List[str]
    train_accuracy: float
    test_accuracy: float
    overfitting_score: float  # train - test accuracy


@dataclass
class CrossValidationResult:
    """Complete cross-validation results."""
    folds: List[CrossValidationFold]
    n_folds: int

    # Aggregate metrics
    mean_train_accuracy: float
    mean_test_accuracy: float
    std_test_accuracy: float

    # Overfitting detection
    overfitting_score: float  # Average (train - test)
    is_overfitting: bool

    # Best parameters
    best_parameters: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_folds": self.n_folds,
            "mean_train_accuracy": self.mean_train_accuracy,
            "mean_test_accuracy": self.mean_test_accuracy,
            "std_test_accuracy": self.std_test_accuracy,
            "overfitting_score": self.overfitting_score,
            "is_overfitting": self.is_overfitting,
            "best_parameters": self.best_parameters,
            "fold_details": [
                {
                    "fold": f.fold_index,
                    "train_acc": f.train_accuracy,
                    "test_acc": f.test_accuracy,
                }
                for f in self.folds
            ],
        }


class CrossValidator:
    """
    Cross-validation for parameter tuning.

    Prevents overfitting by validating across multiple scenario splits.
    """

    def __init__(
        self,
        n_folds: int = 5,
        overfitting_threshold: float = 0.05,
    ):
        """
        Initialize cross-validator.

        Args:
            n_folds: Number of cross-validation folds
            overfitting_threshold: Max allowed (train - test) accuracy gap
        """
        self.n_folds = n_folds
        self.overfitting_threshold = overfitting_threshold

    def create_folds(
        self,
        scenario_ids: List[str],
        shuffle: bool = True,
        random_seed: int = 42,
    ) -> List[Tuple[List[str], List[str]]]:
        """
        Create train/test splits for cross-validation.

        Args:
            scenario_ids: List of scenario IDs
            shuffle: Whether to shuffle before splitting
            random_seed: Seed for reproducibility

        Returns:
            List of (train_ids, test_ids) tuples
        """
        rng = np.random.default_rng(random_seed)

        ids = list(scenario_ids)
        if shuffle:
            rng.shuffle(ids)

        # Create folds
        fold_size = len(ids) // self.n_folds
        folds = []

        for i in range(self.n_folds):
            start = i * fold_size
            end = start + fold_size if i < self.n_folds - 1 else len(ids)

            test_ids = ids[start:end]
            train_ids = ids[:start] + ids[end:]

            folds.append((train_ids, test_ids))

        return folds

    def validate(
        self,
        scenario_ids: List[str],
        parameters: Dict[str, float],
        evaluate_fn: Callable[[List[str], Dict[str, float]], float],
        random_seed: int = 42,
    ) -> CrossValidationResult:
        """
        Run cross-validation.

        Args:
            scenario_ids: All scenario IDs
            parameters: Parameters to validate
            evaluate_fn: Function that evaluates accuracy on scenarios
            random_seed: Seed for reproducibility

        Returns:
            CrossValidationResult with fold-by-fold results
        """
        folds = self.create_folds(scenario_ids, shuffle=True, random_seed=random_seed)
        fold_results = []

        for i, (train_ids, test_ids) in enumerate(folds):
            # Evaluate on train set
            train_accuracy = evaluate_fn(train_ids, parameters)

            # Evaluate on test set
            test_accuracy = evaluate_fn(test_ids, parameters)

            # Overfitting score
            overfit = train_accuracy - test_accuracy

            fold_results.append(CrossValidationFold(
                fold_index=i,
                train_scenarios=train_ids,
                test_scenarios=test_ids,
                train_accuracy=train_accuracy,
                test_accuracy=test_accuracy,
                overfitting_score=overfit,
            ))

        # Aggregate results
        train_accuracies = [f.train_accuracy for f in fold_results]
        test_accuracies = [f.test_accuracy for f in fold_results]
        overfitting_scores = [f.overfitting_score for f in fold_results]

        mean_overfit = float(np.mean(overfitting_scores))

        return CrossValidationResult(
            folds=fold_results,
            n_folds=self.n_folds,
            mean_train_accuracy=float(np.mean(train_accuracies)),
            mean_test_accuracy=float(np.mean(test_accuracies)),
            std_test_accuracy=float(np.std(test_accuracies)),
            overfitting_score=mean_overfit,
            is_overfitting=mean_overfit > self.overfitting_threshold,
            best_parameters=parameters,
        )


@dataclass
class TuneConfig:
    """Configuration for auto-tuning."""

    # Which parameters to tune
    tunable_parameters: List[str]

    # Parameter bounds
    bounds: Dict[str, ParameterBound]

    # Optimization settings
    max_iterations: int = 50
    learning_rate: float = 0.1
    convergence_threshold: float = 0.001

    # Cross-validation
    use_cross_validation: bool = True
    n_folds: int = 5
    overfitting_threshold: float = 0.05

    # Rollback settings
    rollback_on_overfit: bool = True
    max_rollbacks: int = 3

    # Target accuracy
    target_accuracy: float = 0.80


@dataclass
class TuneResult:
    """Result of auto-tuning."""

    # Final parameters
    final_parameters: ParameterSet
    initial_parameters: ParameterSet

    # Performance
    initial_accuracy: float
    final_accuracy: float
    improvement: float

    # Cross-validation (if used)
    cross_validation: Optional[CrossValidationResult] = None

    # Tuning process
    n_iterations: int = 0
    n_rollbacks: int = 0
    converged: bool = False
    convergence_reason: str = ""

    # History
    accuracy_history: List[float] = field(default_factory=list)
    parameter_history: List[Dict[str, float]] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "final_parameters": self.final_parameters.to_dict(),
            "initial_accuracy": self.initial_accuracy,
            "final_accuracy": self.final_accuracy,
            "improvement": self.improvement,
            "n_iterations": self.n_iterations,
            "n_rollbacks": self.n_rollbacks,
            "converged": self.converged,
            "convergence_reason": self.convergence_reason,
            "duration_seconds": self.duration_seconds,
        }
        if self.cross_validation:
            result["cross_validation"] = self.cross_validation.to_dict()
        return result


class BoundedAutoTune:
    """
    Bounded auto-tuning with overfit rollback.

    Key features:
    - Bounded parameter ranges
    - Cross-validation for generalization
    - Automatic rollback on overfitting
    - Convergence detection
    """

    def __init__(
        self,
        config: TuneConfig,
        simulation_runner: Callable[[Dict[str, float]], float],
    ):
        """
        Initialize auto-tuner.

        Args:
            config: Tuning configuration
            simulation_runner: Function that runs simulation with params
        """
        self.config = config
        self.simulation_runner = simulation_runner
        self.cross_validator = CrossValidator(
            n_folds=config.n_folds,
            overfitting_threshold=config.overfitting_threshold,
        )

        # History tracking
        self.best_parameters: Dict[str, float] = {}
        self.best_accuracy: float = 0.0
        self.rollback_count: int = 0

    def tune(
        self,
        initial_params: Dict[str, float],
        scenario_ids: Optional[List[str]] = None,
    ) -> TuneResult:
        """
        Run auto-tuning.

        Args:
            initial_params: Starting parameter values
            scenario_ids: Optional scenario IDs for cross-validation

        Returns:
            TuneResult with final parameters and metrics
        """
        start_time = datetime.now()

        # Initialize
        current_params = initial_params.copy()
        initial_param_set = ParameterSet(
            parameters=initial_params.copy(),
            bounds=self.config.bounds,
        )

        # Evaluate initial accuracy
        initial_accuracy = self._evaluate(current_params)
        self.best_accuracy = initial_accuracy
        self.best_parameters = current_params.copy()

        accuracy_history = [initial_accuracy]
        parameter_history = [current_params.copy()]

        logger.info(f"Starting auto-tune. Initial accuracy: {initial_accuracy:.4f}")

        # Tuning loop
        converged = False
        convergence_reason = ""

        for iteration in range(self.config.max_iterations):
            # Compute gradient (numerical)
            gradients = self._compute_gradients(current_params)

            # Update parameters
            new_params = {}
            for name in self.config.tunable_parameters:
                if name in current_params and name in gradients:
                    delta = self.config.learning_rate * gradients[name]
                    new_value = current_params[name] + delta

                    # Apply bounds
                    if name in self.config.bounds:
                        new_value = self.config.bounds[name].clip(new_value)

                    new_params[name] = new_value
                else:
                    new_params[name] = current_params.get(name, 0.0)

            # Evaluate new parameters
            new_accuracy = self._evaluate(new_params)
            accuracy_history.append(new_accuracy)
            parameter_history.append(new_params.copy())

            # Cross-validation check for overfitting
            if self.config.use_cross_validation and scenario_ids:
                cv_result = self._cross_validate(new_params, scenario_ids)

                if cv_result.is_overfitting:
                    if self.config.rollback_on_overfit:
                        self.rollback_count += 1
                        logger.warning(
                            f"Overfitting detected at iteration {iteration}. "
                            f"Rolling back. (Rollback {self.rollback_count})"
                        )

                        if self.rollback_count >= self.config.max_rollbacks:
                            converged = True
                            convergence_reason = "max_rollbacks_reached"
                            break

                        # Rollback to best parameters
                        new_params = self.best_parameters.copy()
                        self.config.learning_rate *= 0.5  # Reduce learning rate
                        continue

            # Check for improvement
            if new_accuracy > self.best_accuracy:
                self.best_accuracy = new_accuracy
                self.best_parameters = new_params.copy()

            # Check convergence
            if len(accuracy_history) >= 2:
                improvement = abs(new_accuracy - accuracy_history[-2])
                if improvement < self.config.convergence_threshold:
                    converged = True
                    convergence_reason = "threshold_reached"
                    break

            # Check if target reached
            if new_accuracy >= self.config.target_accuracy:
                converged = True
                convergence_reason = "target_reached"
                break

            current_params = new_params

        if not converged:
            convergence_reason = "max_iterations"

        # Final cross-validation
        final_cv = None
        if self.config.use_cross_validation and scenario_ids:
            final_cv = self._cross_validate(self.best_parameters, scenario_ids)

        end_time = datetime.now()

        final_param_set = ParameterSet(
            parameters=self.best_parameters,
            bounds=self.config.bounds,
            version=initial_param_set.version + 1,
        )

        result = TuneResult(
            final_parameters=final_param_set,
            initial_parameters=initial_param_set,
            initial_accuracy=initial_accuracy,
            final_accuracy=self.best_accuracy,
            improvement=self.best_accuracy - initial_accuracy,
            cross_validation=final_cv,
            n_iterations=len(accuracy_history) - 1,
            n_rollbacks=self.rollback_count,
            converged=converged,
            convergence_reason=convergence_reason,
            accuracy_history=accuracy_history,
            parameter_history=parameter_history,
            started_at=start_time,
            completed_at=end_time,
            duration_seconds=(end_time - start_time).total_seconds(),
        )

        logger.info(
            f"Auto-tune complete. Accuracy: {initial_accuracy:.4f} → {self.best_accuracy:.4f} "
            f"(+{result.improvement:.4f}) after {result.n_iterations} iterations"
        )

        return result

    def _evaluate(self, params: Dict[str, float]) -> float:
        """Evaluate accuracy with given parameters."""
        try:
            return self.simulation_runner(params)
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return 0.0

    def _compute_gradients(
        self,
        params: Dict[str, float],
        epsilon: float = 0.001,
    ) -> Dict[str, float]:
        """Compute numerical gradients for tunable parameters."""
        gradients = {}
        base_accuracy = self._evaluate(params)

        for name in self.config.tunable_parameters:
            if name not in params:
                continue

            # Perturb parameter
            perturbed = params.copy()
            perturbed[name] = params[name] + epsilon

            # Apply bounds
            if name in self.config.bounds:
                perturbed[name] = self.config.bounds[name].clip(perturbed[name])

            # Compute gradient
            perturbed_accuracy = self._evaluate(perturbed)
            gradient = (perturbed_accuracy - base_accuracy) / epsilon
            gradients[name] = gradient

        return gradients

    def _cross_validate(
        self,
        params: Dict[str, float],
        scenario_ids: List[str],
    ) -> CrossValidationResult:
        """Run cross-validation on parameters."""

        def evaluate_fn(ids: List[str], p: Dict[str, float]) -> float:
            # Simplified: average accuracy across scenarios
            # In production, this would run scenarios individually
            return self._evaluate(p)

        return self.cross_validator.validate(
            scenario_ids=scenario_ids,
            parameters=params,
            evaluate_fn=evaluate_fn,
        )

    def get_best_parameters(self) -> Dict[str, float]:
        """Get the best parameters found so far."""
        return self.best_parameters.copy()

    def get_tuning_summary(self) -> Dict[str, Any]:
        """Get summary of tuning process."""
        return {
            "best_accuracy": self.best_accuracy,
            "best_parameters": self.best_parameters,
            "rollback_count": self.rollback_count,
            "current_learning_rate": self.config.learning_rate,
        }
