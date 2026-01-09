"""
Error Metrics Suite

P7-002: Comprehensive error metrics for prediction validation.
Includes distribution error, ranking error, and turning-point error.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import date
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class DistributionError:
    """Distribution error between predicted and actual probability distributions."""

    # Core metrics
    total_variation_distance: float  # TVD: 0.5 * sum(|p - q|)
    kl_divergence: float  # D_KL(actual || predicted)
    js_divergence: float  # Jensen-Shannon divergence (symmetric)
    hellinger_distance: float  # sqrt(0.5 * sum((sqrt(p) - sqrt(q))^2))

    # Category-level breakdown
    category_errors: Dict[str, float] = field(default_factory=dict)

    # Summary
    worst_category: Optional[str] = None
    best_category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_variation_distance": self.total_variation_distance,
            "kl_divergence": self.kl_divergence,
            "js_divergence": self.js_divergence,
            "hellinger_distance": self.hellinger_distance,
            "category_errors": self.category_errors,
            "worst_category": self.worst_category,
            "best_category": self.best_category,
        }


@dataclass
class RankingError:
    """Ranking/ordering error between predicted and actual outcomes."""

    # Correlation-based
    spearman_correlation: float  # Rank correlation (-1 to 1)
    kendall_tau: float  # Kendall tau (-1 to 1)

    # Distance-based
    rank_distance: float  # Normalized rank distance (0 to 1)
    top_k_accuracy: Dict[int, float] = field(default_factory=dict)  # Accuracy of top-k

    # Detailed
    pairwise_inversions: int  # Number of pairwise ordering mistakes
    total_pairs: int

    # Which categories were misordered
    misranked_pairs: List[Tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spearman_correlation": self.spearman_correlation,
            "kendall_tau": self.kendall_tau,
            "rank_distance": self.rank_distance,
            "top_k_accuracy": self.top_k_accuracy,
            "pairwise_inversions": self.pairwise_inversions,
            "total_pairs": self.total_pairs,
            "misranked_pairs": self.misranked_pairs[:10],  # Limit to top 10
        }


@dataclass
class TurningPointError:
    """Error in detecting and predicting turning points in time series."""

    # Detection accuracy
    turning_points_detected: int
    turning_points_actual: int
    turning_points_correct: int

    # Precision/Recall
    precision: float  # Correct detected / Total detected
    recall: float  # Correct detected / Actual turning points
    f1_score: float

    # Timing error
    mean_timing_error_days: float  # How far off were we on timing?
    max_timing_error_days: float

    # Direction errors
    direction_accuracy: float  # % of directions correctly predicted

    # Detailed breakdown
    turning_point_details: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turning_points_detected": self.turning_points_detected,
            "turning_points_actual": self.turning_points_actual,
            "turning_points_correct": self.turning_points_correct,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "mean_timing_error_days": self.mean_timing_error_days,
            "max_timing_error_days": self.max_timing_error_days,
            "direction_accuracy": self.direction_accuracy,
            "turning_point_details": self.turning_point_details,
        }


def compute_distribution_error(
    predictions: Dict[str, float],
    actuals: Dict[str, float],
    epsilon: float = 1e-10,
) -> DistributionError:
    """
    Compute comprehensive distribution error metrics.

    Args:
        predictions: Predicted probability distribution
        actuals: Actual probability distribution
        epsilon: Small value to avoid numerical issues

    Returns:
        DistributionError with all metrics
    """
    # Align keys
    common_keys = list(set(predictions.keys()) & set(actuals.keys()))
    if not common_keys:
        return DistributionError(
            total_variation_distance=1.0,
            kl_divergence=float('inf'),
            js_divergence=1.0,
            hellinger_distance=1.0,
        )

    # Extract and normalize
    p = np.array([predictions[k] for k in common_keys])
    q = np.array([actuals[k] for k in common_keys])

    # Normalize to probability distributions
    p = p / (p.sum() + epsilon)
    q = q / (q.sum() + epsilon)

    # Clip for numerical stability
    p = np.clip(p, epsilon, 1 - epsilon)
    q = np.clip(q, epsilon, 1 - epsilon)

    # Re-normalize after clipping
    p = p / p.sum()
    q = q / q.sum()

    # Total Variation Distance
    tvd = 0.5 * np.sum(np.abs(p - q))

    # KL Divergence: D_KL(q || p) - how well does p approximate q
    kl = np.sum(q * np.log(q / p))

    # Jensen-Shannon Divergence (symmetric)
    m = 0.5 * (p + q)
    js = 0.5 * np.sum(p * np.log(p / m)) + 0.5 * np.sum(q * np.log(q / m))

    # Hellinger Distance
    hellinger = np.sqrt(0.5 * np.sum((np.sqrt(p) - np.sqrt(q)) ** 2))

    # Category-level errors
    category_errors = {}
    for i, key in enumerate(common_keys):
        category_errors[key] = abs(p[i] - q[i])

    # Find worst and best categories
    sorted_errors = sorted(category_errors.items(), key=lambda x: x[1])
    best_category = sorted_errors[0][0] if sorted_errors else None
    worst_category = sorted_errors[-1][0] if sorted_errors else None

    return DistributionError(
        total_variation_distance=float(tvd),
        kl_divergence=float(kl),
        js_divergence=float(js),
        hellinger_distance=float(hellinger),
        category_errors=category_errors,
        worst_category=worst_category,
        best_category=best_category,
    )


def compute_ranking_error(
    predictions: Dict[str, float],
    actuals: Dict[str, float],
) -> RankingError:
    """
    Compute comprehensive ranking error metrics.

    Args:
        predictions: Predicted values by category
        actuals: Actual values by category

    Returns:
        RankingError with all metrics
    """
    from scipy import stats

    # Align keys
    common_keys = list(set(predictions.keys()) & set(actuals.keys()))
    if len(common_keys) < 2:
        return RankingError(
            spearman_correlation=0.0,
            kendall_tau=0.0,
            rank_distance=1.0,
            pairwise_inversions=0,
            total_pairs=0,
        )

    pred_values = np.array([predictions[k] for k in common_keys])
    actual_values = np.array([actuals[k] for k in common_keys])

    # Spearman correlation
    spearman, _ = stats.spearmanr(pred_values, actual_values)
    spearman = float(spearman) if not np.isnan(spearman) else 0.0

    # Kendall tau
    kendall, _ = stats.kendalltau(pred_values, actual_values)
    kendall = float(kendall) if not np.isnan(kendall) else 0.0

    # Count pairwise inversions
    pred_ranks = np.argsort(np.argsort(-pred_values))
    actual_ranks = np.argsort(np.argsort(-actual_values))

    n = len(common_keys)
    inversions = 0
    misranked_pairs = []

    for i in range(n):
        for j in range(i + 1, n):
            pred_order = np.sign(pred_ranks[i] - pred_ranks[j])
            actual_order = np.sign(actual_ranks[i] - actual_ranks[j])
            if pred_order * actual_order < 0:
                inversions += 1
                misranked_pairs.append((common_keys[i], common_keys[j]))

    total_pairs = n * (n - 1) // 2
    rank_distance = inversions / total_pairs if total_pairs > 0 else 0.0

    # Top-k accuracy
    top_k_accuracy = {}
    for k in [1, 3, 5]:
        if k <= n:
            pred_top_k = set(np.array(common_keys)[np.argsort(-pred_values)[:k]])
            actual_top_k = set(np.array(common_keys)[np.argsort(-actual_values)[:k]])
            overlap = len(pred_top_k & actual_top_k)
            top_k_accuracy[k] = overlap / k

    return RankingError(
        spearman_correlation=spearman,
        kendall_tau=kendall,
        rank_distance=float(rank_distance),
        top_k_accuracy=top_k_accuracy,
        pairwise_inversions=inversions,
        total_pairs=total_pairs,
        misranked_pairs=misranked_pairs,
    )


def compute_turning_point_error(
    predicted_series: List[Tuple[date, float]],
    actual_series: List[Tuple[date, float]],
    tolerance_days: int = 7,
) -> TurningPointError:
    """
    Compute turning point detection error.

    A turning point is a local maximum or minimum in the time series.

    Args:
        predicted_series: Predicted time series [(date, value), ...]
        actual_series: Actual time series
        tolerance_days: How close timing needs to be to count as correct

    Returns:
        TurningPointError with all metrics
    """
    from datetime import timedelta

    def detect_turning_points(
        series: List[Tuple[date, float]]
    ) -> List[Tuple[date, str, float]]:
        """Detect turning points (local extrema)."""
        if len(series) < 3:
            return []

        sorted_series = sorted(series, key=lambda x: x[0])
        turning_points = []

        for i in range(1, len(sorted_series) - 1):
            prev_date, prev_val = sorted_series[i - 1]
            curr_date, curr_val = sorted_series[i]
            next_date, next_val = sorted_series[i + 1]

            if curr_val > prev_val and curr_val > next_val:
                turning_points.append((curr_date, "peak", curr_val))
            elif curr_val < prev_val and curr_val < next_val:
                turning_points.append((curr_date, "trough", curr_val))

        return turning_points

    # Detect turning points
    pred_tp = detect_turning_points(predicted_series)
    actual_tp = detect_turning_points(actual_series)

    turning_points_detected = len(pred_tp)
    turning_points_actual = len(actual_tp)

    # Match predicted to actual turning points
    matched = []
    timing_errors = []
    direction_correct = 0

    for p_date, p_type, p_val in pred_tp:
        best_match = None
        best_distance = float('inf')

        for a_date, a_type, a_val in actual_tp:
            distance = abs((p_date - a_date).days)
            if distance < best_distance:
                best_distance = distance
                best_match = (a_date, a_type, a_val)

        if best_match and best_distance <= tolerance_days:
            matched.append((p_date, best_match[0], best_distance))
            timing_errors.append(best_distance)

            if p_type == best_match[1]:
                direction_correct += 1

    turning_points_correct = len(matched)

    # Compute precision/recall/F1
    precision = turning_points_correct / turning_points_detected if turning_points_detected > 0 else 0.0
    recall = turning_points_correct / turning_points_actual if turning_points_actual > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Timing errors
    mean_timing_error = float(np.mean(timing_errors)) if timing_errors else 0.0
    max_timing_error = float(np.max(timing_errors)) if timing_errors else 0.0

    # Direction accuracy
    direction_accuracy = direction_correct / turning_points_correct if turning_points_correct > 0 else 0.0

    # Detailed breakdown
    details = []
    for i, (p_date, p_type, p_val) in enumerate(pred_tp):
        detail = {
            "predicted_date": p_date.isoformat(),
            "predicted_type": p_type,
            "predicted_value": float(p_val),
            "matched": i < len(matched),
        }
        if i < len(matched):
            detail["actual_date"] = matched[i][1].isoformat()
            detail["timing_error_days"] = matched[i][2]
        details.append(detail)

    return TurningPointError(
        turning_points_detected=turning_points_detected,
        turning_points_actual=turning_points_actual,
        turning_points_correct=turning_points_correct,
        precision=precision,
        recall=recall,
        f1_score=f1,
        mean_timing_error_days=mean_timing_error,
        max_timing_error_days=max_timing_error,
        direction_accuracy=direction_accuracy,
        turning_point_details=details,
    )


@dataclass
class ErrorMetricsSuite:
    """Complete error metrics for a prediction."""

    distribution: DistributionError
    ranking: RankingError
    turning_points: Optional[TurningPointError] = None

    # Composite scores
    overall_error: float = 0.0
    accuracy: float = 0.0

    # Weights used for composite
    distribution_weight: float = 0.4
    ranking_weight: float = 0.4
    turning_point_weight: float = 0.2

    def __post_init__(self):
        self._compute_composite()

    def _compute_composite(self):
        """Compute overall error from components."""
        # Distribution error (TVD is 0-1)
        dist_error = self.distribution.total_variation_distance

        # Ranking error (convert from correlation to error)
        rank_error = (1.0 - self.ranking.spearman_correlation) / 2.0

        # Turning point error
        tp_error = 0.0
        if self.turning_points:
            tp_error = 1.0 - self.turning_points.f1_score

        # Weighted sum
        if self.turning_points:
            self.overall_error = (
                self.distribution_weight * dist_error +
                self.ranking_weight * rank_error +
                self.turning_point_weight * tp_error
            )
        else:
            # Redistribute weights if no turning points
            total_weight = self.distribution_weight + self.ranking_weight
            self.overall_error = (
                (self.distribution_weight / total_weight) * dist_error +
                (self.ranking_weight / total_weight) * rank_error
            )

        self.accuracy = 1.0 - self.overall_error

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "distribution": self.distribution.to_dict(),
            "ranking": self.ranking.to_dict(),
            "overall_error": self.overall_error,
            "accuracy": self.accuracy,
            "weights": {
                "distribution": self.distribution_weight,
                "ranking": self.ranking_weight,
                "turning_point": self.turning_point_weight,
            },
        }
        if self.turning_points:
            result["turning_points"] = self.turning_points.to_dict()
        return result


def compute_error_metrics_suite(
    predictions: Dict[str, float],
    actuals: Dict[str, float],
    predicted_series: Optional[List[Tuple[date, float]]] = None,
    actual_series: Optional[List[Tuple[date, float]]] = None,
    distribution_weight: float = 0.4,
    ranking_weight: float = 0.4,
    turning_point_weight: float = 0.2,
) -> ErrorMetricsSuite:
    """
    Compute complete error metrics suite.

    Args:
        predictions: Predicted distribution
        actuals: Actual distribution
        predicted_series: Optional predicted time series
        actual_series: Optional actual time series
        distribution_weight: Weight for distribution error
        ranking_weight: Weight for ranking error
        turning_point_weight: Weight for turning point error

    Returns:
        ErrorMetricsSuite with all metrics
    """
    # Compute distribution error
    distribution = compute_distribution_error(predictions, actuals)

    # Compute ranking error
    ranking = compute_ranking_error(predictions, actuals)

    # Compute turning point error if time series provided
    turning_points = None
    if predicted_series and actual_series:
        turning_points = compute_turning_point_error(
            predicted_series,
            actual_series,
        )

    return ErrorMetricsSuite(
        distribution=distribution,
        ranking=ranking,
        turning_points=turning_points,
        distribution_weight=distribution_weight,
        ranking_weight=ranking_weight,
        turning_point_weight=turning_point_weight,
    )
