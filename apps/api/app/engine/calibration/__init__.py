"""
Calibration System for Predictive Simulation

Implements parameter optimization, ground truth comparison, and accuracy tracking.
Designed to achieve >80% predictive accuracy through systematic calibration.
"""

from app.engine.calibration.calibrator import (
    Calibrator,
    CalibrationConfig,
    CalibrationMethod,
)
from app.engine.calibration.metrics import (
    AccuracyMetrics,
    compute_accuracy_metrics,
    compute_kl_divergence,
    compute_brier_score,
)
from app.engine.calibration.optimizer import (
    BayesianOptimizer,
    GridSearchOptimizer,
    ParameterBounds,
)

__all__ = [
    "Calibrator",
    "CalibrationConfig",
    "CalibrationMethod",
    "AccuracyMetrics",
    "compute_accuracy_metrics",
    "compute_kl_divergence",
    "compute_brier_score",
    "BayesianOptimizer",
    "GridSearchOptimizer",
    "ParameterBounds",
]
