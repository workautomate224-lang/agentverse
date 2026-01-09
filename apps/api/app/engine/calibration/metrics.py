"""
Accuracy Metrics for Prediction Calibration

Implements various metrics for measuring prediction accuracy against ground truth.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class AccuracyMetrics:
    """Comprehensive accuracy metrics for predictions."""

    # Core accuracy
    accuracy: float = 0.0  # Overall accuracy percentage
    mae: float = 0.0  # Mean Absolute Error
    rmse: float = 0.0  # Root Mean Squared Error
    mape: float = 0.0  # Mean Absolute Percentage Error

    # Probabilistic metrics
    kl_divergence: float = 0.0  # KL divergence from ground truth
    brier_score: float = 0.0  # Brier score for probabilistic predictions
    log_loss: float = 0.0  # Log loss / cross entropy

    # Confidence interval metrics
    coverage_probability: float = 0.0  # % of actual values within CI
    ci_width: float = 0.0  # Average confidence interval width

    # Correlation
    correlation: float = 0.0  # Pearson correlation
    rank_correlation: float = 0.0  # Spearman rank correlation

    # Per-category breakdown
    category_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Regional breakdown
    regional_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "accuracy": self.accuracy,
            "mae": self.mae,
            "rmse": self.rmse,
            "mape": self.mape,
            "kl_divergence": self.kl_divergence,
            "brier_score": self.brier_score,
            "log_loss": self.log_loss,
            "coverage_probability": self.coverage_probability,
            "ci_width": self.ci_width,
            "correlation": self.correlation,
            "rank_correlation": self.rank_correlation,
            "category_metrics": self.category_metrics,
            "regional_metrics": self.regional_metrics,
        }

    @property
    def is_above_threshold(self) -> bool:
        """Check if accuracy meets >80% target."""
        return self.accuracy >= 0.80


def compute_kl_divergence(
    predicted: np.ndarray,
    actual: np.ndarray,
    epsilon: float = 1e-10,
) -> float:
    """
    Compute KL divergence between predicted and actual distributions.

    D_KL(P || Q) = sum(P(x) * log(P(x) / Q(x)))

    Args:
        predicted: Predicted probability distribution
        actual: Actual probability distribution (ground truth)
        epsilon: Small value to avoid log(0)

    Returns:
        KL divergence (lower is better, 0 is perfect)
    """
    # Normalize distributions
    p = np.asarray(actual).flatten()
    q = np.asarray(predicted).flatten()

    p = p / (p.sum() + epsilon)
    q = q / (q.sum() + epsilon)

    # Clip to avoid numerical issues
    p = np.clip(p, epsilon, 1 - epsilon)
    q = np.clip(q, epsilon, 1 - epsilon)

    # KL divergence
    kl = np.sum(p * np.log(p / q))

    return float(kl)


def compute_brier_score(
    predicted: np.ndarray,
    actual: np.ndarray,
) -> float:
    """
    Compute Brier score for probabilistic predictions.

    BS = (1/N) * sum((predicted - actual)^2)

    Args:
        predicted: Predicted probabilities
        actual: Actual outcomes (0 or 1, or probabilities)

    Returns:
        Brier score (lower is better, 0 is perfect)
    """
    p = np.asarray(predicted).flatten()
    a = np.asarray(actual).flatten()

    return float(np.mean((p - a) ** 2))


def compute_log_loss(
    predicted: np.ndarray,
    actual: np.ndarray,
    epsilon: float = 1e-10,
) -> float:
    """
    Compute log loss (cross entropy).

    Args:
        predicted: Predicted probabilities
        actual: Actual outcomes

    Returns:
        Log loss (lower is better)
    """
    p = np.asarray(predicted).flatten()
    a = np.asarray(actual).flatten()

    p = np.clip(p, epsilon, 1 - epsilon)

    return float(-np.mean(a * np.log(p) + (1 - a) * np.log(1 - p)))


def compute_mae(predicted: np.ndarray, actual: np.ndarray) -> float:
    """Compute Mean Absolute Error."""
    return float(np.mean(np.abs(predicted - actual)))


def compute_rmse(predicted: np.ndarray, actual: np.ndarray) -> float:
    """Compute Root Mean Squared Error."""
    return float(np.sqrt(np.mean((predicted - actual) ** 2)))


def compute_mape(
    predicted: np.ndarray,
    actual: np.ndarray,
    epsilon: float = 1e-10,
) -> float:
    """Compute Mean Absolute Percentage Error."""
    a = np.asarray(actual).flatten()
    p = np.asarray(predicted).flatten()

    # Avoid division by zero
    mask = np.abs(a) > epsilon
    if not mask.any():
        return 0.0

    return float(np.mean(np.abs((a[mask] - p[mask]) / a[mask])) * 100)


def compute_correlation(
    predicted: np.ndarray,
    actual: np.ndarray,
) -> Tuple[float, float]:
    """
    Compute Pearson and Spearman correlations.

    Returns:
        Tuple of (pearson, spearman)
    """
    from scipy import stats

    p = np.asarray(predicted).flatten()
    a = np.asarray(actual).flatten()

    if len(p) < 2:
        return 0.0, 0.0

    pearson = float(np.corrcoef(p, a)[0, 1])
    spearman = float(stats.spearmanr(p, a)[0])

    # Handle NaN
    pearson = pearson if not np.isnan(pearson) else 0.0
    spearman = spearman if not np.isnan(spearman) else 0.0

    return pearson, spearman


def compute_coverage_probability(
    predicted: np.ndarray,
    actual: np.ndarray,
    ci_lower: np.ndarray,
    ci_upper: np.ndarray,
) -> Tuple[float, float]:
    """
    Compute confidence interval coverage and width.

    Args:
        predicted: Point predictions
        actual: Actual values
        ci_lower: Lower bound of confidence interval
        ci_upper: Upper bound of confidence interval

    Returns:
        Tuple of (coverage_probability, mean_ci_width)
    """
    a = np.asarray(actual).flatten()
    lower = np.asarray(ci_lower).flatten()
    upper = np.asarray(ci_upper).flatten()

    # Coverage: fraction of actual values within CI
    within_ci = (a >= lower) & (a <= upper)
    coverage = float(np.mean(within_ci))

    # Average CI width
    ci_width = float(np.mean(upper - lower))

    return coverage, ci_width


def compute_accuracy_metrics(
    predictions: Dict[str, float],
    ground_truth: Dict[str, float],
    confidence_intervals: Optional[Dict[str, Tuple[float, float]]] = None,
    regional_predictions: Optional[Dict[str, Dict[str, float]]] = None,
    regional_ground_truth: Optional[Dict[str, Dict[str, float]]] = None,
) -> AccuracyMetrics:
    """
    Compute comprehensive accuracy metrics.

    Args:
        predictions: Dict of predicted values by category
        ground_truth: Dict of actual values by category
        confidence_intervals: Optional CI for each category
        regional_predictions: Optional regional breakdown
        regional_ground_truth: Optional regional ground truth

    Returns:
        AccuracyMetrics object
    """
    metrics = AccuracyMetrics()

    # Align keys
    common_keys = set(predictions.keys()) & set(ground_truth.keys())
    if not common_keys:
        logger.warning("No common keys between predictions and ground truth")
        return metrics

    # Extract aligned arrays
    pred_values = np.array([predictions[k] for k in common_keys])
    actual_values = np.array([ground_truth[k] for k in common_keys])

    # Core metrics
    metrics.mae = compute_mae(pred_values, actual_values)
    metrics.rmse = compute_rmse(pred_values, actual_values)
    metrics.mape = compute_mape(pred_values, actual_values)

    # Probabilistic metrics
    metrics.kl_divergence = compute_kl_divergence(pred_values, actual_values)
    metrics.brier_score = compute_brier_score(pred_values, actual_values)
    metrics.log_loss = compute_log_loss(pred_values, actual_values)

    # Correlation
    pearson, spearman = compute_correlation(pred_values, actual_values)
    metrics.correlation = pearson
    metrics.rank_correlation = spearman

    # Confidence intervals
    if confidence_intervals:
        ci_lower = np.array([confidence_intervals[k][0] for k in common_keys if k in confidence_intervals])
        ci_upper = np.array([confidence_intervals[k][1] for k in common_keys if k in confidence_intervals])

        if len(ci_lower) > 0:
            coverage, ci_width = compute_coverage_probability(
                pred_values[:len(ci_lower)],
                actual_values[:len(ci_lower)],
                ci_lower,
                ci_upper,
            )
            metrics.coverage_probability = coverage
            metrics.ci_width = ci_width

    # Calculate overall accuracy
    # Accuracy = 1 - normalized error
    max_error = 1.0  # Maximum possible error for probability distributions
    error_rate = min(metrics.mae / max_error, 1.0)
    metrics.accuracy = 1.0 - error_rate

    # Alternative: accuracy based on correct rank ordering
    if len(pred_values) > 1:
        pred_ranks = np.argsort(np.argsort(-pred_values))
        actual_ranks = np.argsort(np.argsort(-actual_values))
        rank_accuracy = 1.0 - np.mean(np.abs(pred_ranks - actual_ranks)) / len(pred_values)
        metrics.accuracy = max(metrics.accuracy, rank_accuracy)

    # Per-category metrics
    for key in common_keys:
        pred = predictions[key]
        actual = ground_truth[key]
        error = abs(pred - actual)

        metrics.category_metrics[key] = {
            "predicted": pred,
            "actual": actual,
            "error": error,
            "error_percent": error / (actual + 1e-10) * 100,
        }

    # Regional metrics
    if regional_predictions and regional_ground_truth:
        for region in set(regional_predictions.keys()) & set(regional_ground_truth.keys()):
            region_pred = regional_predictions[region]
            region_actual = regional_ground_truth[region]

            region_common = set(region_pred.keys()) & set(region_actual.keys())
            if not region_common:
                continue

            region_pred_values = np.array([region_pred[k] for k in region_common])
            region_actual_values = np.array([region_actual[k] for k in region_common])

            metrics.regional_metrics[region] = {
                "mae": compute_mae(region_pred_values, region_actual_values),
                "rmse": compute_rmse(region_pred_values, region_actual_values),
                "kl_divergence": compute_kl_divergence(region_pred_values, region_actual_values),
            }

    return metrics


def compare_predictions(
    predictions_list: List[Dict[str, float]],
    ground_truth: Dict[str, float],
    labels: Optional[List[str]] = None,
) -> Dict[str, AccuracyMetrics]:
    """
    Compare multiple prediction sets against ground truth.

    Args:
        predictions_list: List of prediction dictionaries
        ground_truth: Ground truth dictionary
        labels: Optional labels for each prediction set

    Returns:
        Dict mapping label to AccuracyMetrics
    """
    if labels is None:
        labels = [f"prediction_{i}" for i in range(len(predictions_list))]

    results = {}
    for label, predictions in zip(labels, predictions_list):
        results[label] = compute_accuracy_metrics(predictions, ground_truth)

    return results


def compute_calibration_improvement(
    before_metrics: AccuracyMetrics,
    after_metrics: AccuracyMetrics,
) -> Dict[str, float]:
    """
    Compute improvement in accuracy after calibration.

    Args:
        before_metrics: Metrics before calibration
        after_metrics: Metrics after calibration

    Returns:
        Dict of improvement values (positive = better)
    """
    return {
        "accuracy_improvement": after_metrics.accuracy - before_metrics.accuracy,
        "mae_reduction": before_metrics.mae - after_metrics.mae,
        "rmse_reduction": before_metrics.rmse - after_metrics.rmse,
        "kl_reduction": before_metrics.kl_divergence - after_metrics.kl_divergence,
        "brier_reduction": before_metrics.brier_score - after_metrics.brier_score,
        "correlation_improvement": after_metrics.correlation - before_metrics.correlation,
    }


class AccuracyTracker:
    """Track accuracy metrics over time for monitoring improvement."""

    def __init__(self, target_accuracy: float = 0.80):
        self.target_accuracy = target_accuracy
        self.history: List[AccuracyMetrics] = []
        self.best_metrics: Optional[AccuracyMetrics] = None

    def add(self, metrics: AccuracyMetrics) -> None:
        """Add metrics to history."""
        self.history.append(metrics)

        if self.best_metrics is None or metrics.accuracy > self.best_metrics.accuracy:
            self.best_metrics = metrics

    def get_trend(self, window: int = 10) -> Dict[str, float]:
        """Get accuracy trend over recent history."""
        if len(self.history) < 2:
            return {"trend": 0.0, "mean": self.history[-1].accuracy if self.history else 0.0}

        recent = self.history[-window:] if len(self.history) >= window else self.history
        accuracies = [m.accuracy for m in recent]

        # Linear trend
        x = np.arange(len(accuracies))
        slope = np.polyfit(x, accuracies, 1)[0]

        return {
            "trend": float(slope),
            "mean": float(np.mean(accuracies)),
            "std": float(np.std(accuracies)),
            "min": float(np.min(accuracies)),
            "max": float(np.max(accuracies)),
            "latest": accuracies[-1],
            "target_gap": self.target_accuracy - accuracies[-1],
        }

    def is_improving(self, window: int = 5) -> bool:
        """Check if accuracy is improving."""
        trend = self.get_trend(window)
        return trend["trend"] > 0

    def meets_target(self) -> bool:
        """Check if current accuracy meets target."""
        if not self.history:
            return False
        return self.history[-1].accuracy >= self.target_accuracy
