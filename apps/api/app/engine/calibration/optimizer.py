"""
Parameter Optimization for Calibration

Implements Bayesian and Grid Search optimization for finding optimal simulation parameters.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

logger = logging.getLogger(__name__)


@dataclass
class ParameterBounds:
    """Defines bounds and constraints for a parameter."""

    name: str
    lower: float
    upper: float
    dtype: str = "float"  # float, int, categorical
    log_scale: bool = False  # Use log scale for sampling
    categories: Optional[List[Any]] = None  # For categorical parameters

    def sample_uniform(self, rng: np.random.Generator) -> Union[float, int, Any]:
        """Sample uniformly within bounds."""
        if self.dtype == "categorical" and self.categories:
            return rng.choice(self.categories)

        if self.log_scale:
            log_val = rng.uniform(np.log(self.lower), np.log(self.upper))
            val = np.exp(log_val)
        else:
            val = rng.uniform(self.lower, self.upper)

        if self.dtype == "int":
            return int(round(val))
        return val

    def clip(self, value: float) -> Union[float, int]:
        """Clip value to bounds."""
        clipped = np.clip(value, self.lower, self.upper)
        if self.dtype == "int":
            return int(round(clipped))
        return float(clipped)

    def normalize(self, value: float) -> float:
        """Normalize value to [0, 1]."""
        if self.log_scale:
            return (np.log(value) - np.log(self.lower)) / (np.log(self.upper) - np.log(self.lower))
        return (value - self.lower) / (self.upper - self.lower)

    def denormalize(self, normalized: float) -> Union[float, int]:
        """Denormalize from [0, 1] to actual value."""
        if self.log_scale:
            log_val = normalized * (np.log(self.upper) - np.log(self.lower)) + np.log(self.lower)
            val = np.exp(log_val)
        else:
            val = normalized * (self.upper - self.lower) + self.lower

        if self.dtype == "int":
            return int(round(val))
        return val


@dataclass
class OptimizationResult:
    """Result of parameter optimization."""

    best_params: Dict[str, Any]
    best_score: float
    history: List[Dict[str, Any]] = field(default_factory=list)
    n_iterations: int = 0
    converged: bool = False
    convergence_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "n_iterations": self.n_iterations,
            "converged": self.converged,
            "convergence_reason": self.convergence_reason,
            "history_length": len(self.history),
        }


class GridSearchOptimizer:
    """Grid search parameter optimization."""

    def __init__(
        self,
        parameter_bounds: List[ParameterBounds],
        n_points_per_dim: int = 5,
        n_workers: int = 4,
    ):
        self.parameter_bounds = {p.name: p for p in parameter_bounds}
        self.n_points_per_dim = n_points_per_dim
        self.n_workers = n_workers
        self.history: List[Dict[str, Any]] = []

    def _generate_grid(self) -> List[Dict[str, Any]]:
        """Generate parameter grid."""
        import itertools

        param_values = {}
        for name, bounds in self.parameter_bounds.items():
            if bounds.dtype == "categorical" and bounds.categories:
                param_values[name] = bounds.categories
            elif bounds.log_scale:
                param_values[name] = np.exp(
                    np.linspace(np.log(bounds.lower), np.log(bounds.upper), self.n_points_per_dim)
                )
            else:
                param_values[name] = np.linspace(bounds.lower, bounds.upper, self.n_points_per_dim)

            if bounds.dtype == "int":
                param_values[name] = list(set(int(round(v)) for v in param_values[name]))

        # Generate all combinations
        keys = list(param_values.keys())
        values = [param_values[k] for k in keys]

        grid = []
        for combo in itertools.product(*values):
            grid.append(dict(zip(keys, combo)))

        return grid

    def optimize(
        self,
        objective_fn: Callable[[Dict[str, Any]], float],
        maximize: bool = True,
    ) -> OptimizationResult:
        """
        Run grid search optimization.

        Args:
            objective_fn: Function that takes params dict and returns score
            maximize: If True, maximize objective; else minimize

        Returns:
            OptimizationResult with best parameters found
        """
        grid = self._generate_grid()
        logger.info(f"Grid search over {len(grid)} parameter combinations")

        results = []

        # Parallel evaluation
        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            future_to_params = {
                executor.submit(objective_fn, params): params
                for params in grid
            }

            for future in as_completed(future_to_params):
                params = future_to_params[future]
                try:
                    score = future.result()
                    results.append({"params": params, "score": score})
                    self.history.append({"params": params, "score": score})
                except Exception as e:
                    logger.error(f"Error evaluating params {params}: {e}")

        if not results:
            return OptimizationResult(
                best_params={},
                best_score=float('-inf') if maximize else float('inf'),
                history=self.history,
                n_iterations=len(grid),
            )

        # Find best
        if maximize:
            best = max(results, key=lambda x: x["score"])
        else:
            best = min(results, key=lambda x: x["score"])

        return OptimizationResult(
            best_params=best["params"],
            best_score=best["score"],
            history=self.history,
            n_iterations=len(grid),
            converged=True,
            convergence_reason="grid_complete",
        )


class BayesianOptimizer:
    """
    Bayesian optimization using Gaussian Process surrogate model.

    Uses Expected Improvement (EI) acquisition function.
    """

    def __init__(
        self,
        parameter_bounds: List[ParameterBounds],
        n_initial: int = 10,
        n_iterations: int = 50,
        exploration_weight: float = 0.1,
        convergence_threshold: float = 1e-4,
        convergence_patience: int = 10,
        random_seed: Optional[int] = None,
    ):
        self.parameter_bounds = {p.name: p for p in parameter_bounds}
        self.param_names = list(self.parameter_bounds.keys())
        self.n_params = len(self.param_names)
        self.n_initial = n_initial
        self.n_iterations = n_iterations
        self.exploration_weight = exploration_weight
        self.convergence_threshold = convergence_threshold
        self.convergence_patience = convergence_patience

        self.rng = np.random.default_rng(random_seed)

        # Observed data
        self.X: List[np.ndarray] = []
        self.y: List[float] = []
        self.history: List[Dict[str, Any]] = []

        # GP hyperparameters
        self.length_scales = np.ones(self.n_params) * 0.2
        self.noise_var = 1e-6

    def _params_to_array(self, params: Dict[str, Any]) -> np.ndarray:
        """Convert params dict to normalized array."""
        arr = np.zeros(self.n_params)
        for i, name in enumerate(self.param_names):
            bounds = self.parameter_bounds[name]
            arr[i] = bounds.normalize(params[name])
        return arr

    def _array_to_params(self, arr: np.ndarray) -> Dict[str, Any]:
        """Convert normalized array to params dict."""
        params = {}
        for i, name in enumerate(self.param_names):
            bounds = self.parameter_bounds[name]
            params[name] = bounds.denormalize(arr[i])
        return params

    def _rbf_kernel(self, X1: np.ndarray, X2: np.ndarray) -> np.ndarray:
        """RBF kernel with automatic relevance determination."""
        X1 = np.atleast_2d(X1)
        X2 = np.atleast_2d(X2)

        # Scale by length scales
        X1_scaled = X1 / self.length_scales
        X2_scaled = X2 / self.length_scales

        # Squared distances
        sq_dist = (
            np.sum(X1_scaled ** 2, axis=1, keepdims=True) +
            np.sum(X2_scaled ** 2, axis=1) -
            2 * X1_scaled @ X2_scaled.T
        )

        return np.exp(-0.5 * sq_dist)

    def _gp_predict(
        self,
        X_test: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Predict mean and variance using GP."""
        if len(self.X) == 0:
            return np.zeros(len(X_test)), np.ones(len(X_test))

        X_train = np.array(self.X)
        y_train = np.array(self.y)

        # Normalize y
        y_mean = np.mean(y_train)
        y_std = np.std(y_train) + 1e-8
        y_norm = (y_train - y_mean) / y_std

        # Kernel matrices
        K = self._rbf_kernel(X_train, X_train)
        K += self.noise_var * np.eye(len(X_train))
        K_s = self._rbf_kernel(X_test, X_train)
        K_ss = self._rbf_kernel(X_test, X_test)

        # GP prediction
        try:
            L = np.linalg.cholesky(K)
            alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_norm))
            v = np.linalg.solve(L, K_s.T)

            mu = K_s @ alpha
            var = np.diag(K_ss) - np.sum(v ** 2, axis=0)
            var = np.maximum(var, 1e-8)

            # Denormalize
            mu = mu * y_std + y_mean
            var = var * (y_std ** 2)

            return mu, var

        except np.linalg.LinAlgError:
            # Fallback for numerical issues
            return np.full(len(X_test), y_mean), np.ones(len(X_test)) * y_std ** 2

    def _expected_improvement(
        self,
        X: np.ndarray,
        best_y: float,
        maximize: bool = True,
    ) -> np.ndarray:
        """Compute Expected Improvement acquisition."""
        mu, var = self._gp_predict(X)
        std = np.sqrt(var)

        if maximize:
            improvement = mu - best_y - self.exploration_weight
        else:
            improvement = best_y - mu - self.exploration_weight

        Z = improvement / (std + 1e-8)

        # EI formula
        from scipy.stats import norm
        ei = improvement * norm.cdf(Z) + std * norm.pdf(Z)
        ei = np.where(std > 1e-8, ei, 0.0)

        return ei

    def _sample_initial(self) -> List[Dict[str, Any]]:
        """Sample initial points using Latin Hypercube."""
        # Simple random sampling (could use LHS for better coverage)
        samples = []
        for _ in range(self.n_initial):
            params = {}
            for name, bounds in self.parameter_bounds.items():
                params[name] = bounds.sample_uniform(self.rng)
            samples.append(params)
        return samples

    def _optimize_acquisition(self, best_y: float, maximize: bool) -> Dict[str, Any]:
        """Find next point by optimizing acquisition function."""
        # Random search for acquisition optimization
        n_candidates = 1000

        candidates = np.zeros((n_candidates, self.n_params))
        for i in range(n_candidates):
            for j, name in enumerate(self.param_names):
                bounds = self.parameter_bounds[name]
                candidates[i, j] = bounds.normalize(bounds.sample_uniform(self.rng))

        ei = self._expected_improvement(candidates, best_y, maximize)
        best_idx = np.argmax(ei)

        return self._array_to_params(candidates[best_idx])

    def optimize(
        self,
        objective_fn: Callable[[Dict[str, Any]], float],
        maximize: bool = True,
    ) -> OptimizationResult:
        """
        Run Bayesian optimization.

        Args:
            objective_fn: Function that takes params dict and returns score
            maximize: If True, maximize objective; else minimize

        Returns:
            OptimizationResult with best parameters found
        """
        # Initial sampling
        initial_samples = self._sample_initial()

        logger.info(f"Bayesian optimization: {self.n_initial} initial + {self.n_iterations} iterations")

        best_score = float('-inf') if maximize else float('inf')
        best_params = {}
        no_improvement_count = 0

        for params in initial_samples:
            try:
                score = objective_fn(params)
                self.X.append(self._params_to_array(params))
                self.y.append(score)
                self.history.append({"params": params, "score": score, "phase": "initial"})

                if (maximize and score > best_score) or (not maximize and score < best_score):
                    best_score = score
                    best_params = params.copy()

            except Exception as e:
                logger.error(f"Error in initial evaluation: {e}")

        # Bayesian optimization iterations
        for iteration in range(self.n_iterations):
            # Get next point
            next_params = self._optimize_acquisition(best_score, maximize)

            try:
                score = objective_fn(next_params)
                self.X.append(self._params_to_array(next_params))
                self.y.append(score)
                self.history.append({
                    "params": next_params,
                    "score": score,
                    "phase": "optimization",
                    "iteration": iteration,
                })

                # Check improvement
                improved = (maximize and score > best_score) or (not maximize and score < best_score)

                if improved:
                    improvement = abs(score - best_score)
                    best_score = score
                    best_params = next_params.copy()
                    no_improvement_count = 0

                    logger.debug(f"Iteration {iteration}: New best score {best_score:.4f}")

                    # Check convergence
                    if improvement < self.convergence_threshold:
                        return OptimizationResult(
                            best_params=best_params,
                            best_score=best_score,
                            history=self.history,
                            n_iterations=len(self.y),
                            converged=True,
                            convergence_reason="threshold_reached",
                        )
                else:
                    no_improvement_count += 1

                # Check patience
                if no_improvement_count >= self.convergence_patience:
                    return OptimizationResult(
                        best_params=best_params,
                        best_score=best_score,
                        history=self.history,
                        n_iterations=len(self.y),
                        converged=True,
                        convergence_reason="patience_exceeded",
                    )

            except Exception as e:
                logger.error(f"Error in iteration {iteration}: {e}")

        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            history=self.history,
            n_iterations=len(self.y),
            converged=False,
            convergence_reason="max_iterations",
        )

    def suggest_next(self, maximize: bool = True) -> Dict[str, Any]:
        """Suggest next parameters to evaluate without running full optimization."""
        if len(self.y) == 0:
            # No observations yet, sample randomly
            params = {}
            for name, bounds in self.parameter_bounds.items():
                params[name] = bounds.sample_uniform(self.rng)
            return params

        best_y = max(self.y) if maximize else min(self.y)
        return self._optimize_acquisition(best_y, maximize)

    def update(self, params: Dict[str, Any], score: float) -> None:
        """Add observation to GP model."""
        self.X.append(self._params_to_array(params))
        self.y.append(score)
        self.history.append({"params": params, "score": score, "phase": "update"})


class RandomSearchOptimizer:
    """Simple random search optimizer as baseline."""

    def __init__(
        self,
        parameter_bounds: List[ParameterBounds],
        n_iterations: int = 100,
        random_seed: Optional[int] = None,
    ):
        self.parameter_bounds = {p.name: p for p in parameter_bounds}
        self.n_iterations = n_iterations
        self.rng = np.random.default_rng(random_seed)
        self.history: List[Dict[str, Any]] = []

    def optimize(
        self,
        objective_fn: Callable[[Dict[str, Any]], float],
        maximize: bool = True,
    ) -> OptimizationResult:
        """Run random search optimization."""
        best_score = float('-inf') if maximize else float('inf')
        best_params = {}

        for i in range(self.n_iterations):
            params = {}
            for name, bounds in self.parameter_bounds.items():
                params[name] = bounds.sample_uniform(self.rng)

            try:
                score = objective_fn(params)
                self.history.append({"params": params, "score": score, "iteration": i})

                if (maximize and score > best_score) or (not maximize and score < best_score):
                    best_score = score
                    best_params = params.copy()

            except Exception as e:
                logger.error(f"Error in iteration {i}: {e}")

        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            history=self.history,
            n_iterations=self.n_iterations,
            converged=True,
            convergence_reason="iterations_complete",
        )


def create_optimizer(
    method: str,
    parameter_bounds: List[ParameterBounds],
    **kwargs,
) -> Union[BayesianOptimizer, GridSearchOptimizer, RandomSearchOptimizer]:
    """
    Factory function to create optimizer.

    Args:
        method: "bayesian", "grid", or "random"
        parameter_bounds: List of parameter bounds
        **kwargs: Additional arguments for optimizer

    Returns:
        Optimizer instance
    """
    if method == "bayesian":
        return BayesianOptimizer(parameter_bounds, **kwargs)
    elif method == "grid":
        return GridSearchOptimizer(parameter_bounds, **kwargs)
    elif method == "random":
        return RandomSearchOptimizer(parameter_bounds, **kwargs)
    else:
        raise ValueError(f"Unknown optimization method: {method}")
