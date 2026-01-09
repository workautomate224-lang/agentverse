"""
Reliability & Calibration Services

Phase 7 implementation per project.md §11 Phase 7:
- Historical scenario runner with time cutoffs
- Error metrics suite
- Bounded auto-tune
- Stability suite
- Sensitivity scanner
- Drift detector
- Reliability report generator
"""

from .historical_runner import (
    HistoricalScenarioRunner,
    HistoricalScenario,
    HistoricalDataset,
    HistoricalRunResult,
    TimeCutoff,
    LeakageValidator,
)
from .error_metrics import (
    DistributionError,
    RankingError,
    TurningPointError,
    ErrorMetricsSuite,
    compute_distribution_error,
    compute_ranking_error,
    compute_turning_point_error,
)
from .auto_tune import (
    BoundedAutoTune,
    TuneConfig,
    TuneResult,
    ParameterSet,
    CrossValidator,
)
from .stability import (
    StabilityAnalyzer,
    SeedVarianceReport,
    MultiSeedRunner,
)
from .sensitivity import (
    SensitivityScanner,
    SensitivityReport,
    PerturbationResult,
    VariableImpact,
    VariableBound,
)
from .drift_detector import (
    DriftDetector,
    DriftReport,
    DistributionComparison,
)
from .report_generator import (
    ReliabilityReportGenerator,
    ReliabilityReport,
    ReportConfig,
    CalibrationScore,
    StabilityScore,
    SensitivitySummary,
    DriftStatus,
    DataGapsSummary,
    ConfidenceBreakdown,
)

__all__ = [
    # Historical runner
    'HistoricalScenarioRunner',
    'HistoricalScenario',
    'HistoricalDataset',
    'HistoricalRunResult',
    'TimeCutoff',
    'LeakageValidator',
    # Error metrics
    'DistributionError',
    'RankingError',
    'TurningPointError',
    'ErrorMetricsSuite',
    'compute_distribution_error',
    'compute_ranking_error',
    'compute_turning_point_error',
    # Auto-tune
    'BoundedAutoTune',
    'TuneConfig',
    'TuneResult',
    'ParameterSet',
    'CrossValidator',
    # Stability
    'StabilityAnalyzer',
    'SeedVarianceReport',
    'MultiSeedRunner',
    # Sensitivity
    'SensitivityScanner',
    'SensitivityReport',
    'PerturbationResult',
    'VariableImpact',
    'VariableBound',
    # Drift
    'DriftDetector',
    'DriftReport',
    'DistributionComparison',
    # Report generator
    'ReliabilityReportGenerator',
    'ReliabilityReport',
    'ReportConfig',
    'CalibrationScore',
    'StabilityScore',
    'SensitivitySummary',
    'DriftStatus',
    'DataGapsSummary',
    'ConfidenceBreakdown',
]
