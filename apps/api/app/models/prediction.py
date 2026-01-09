"""
Prediction and Calibration Models
Ground truth management, calibration metrics, and prediction results.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EventType(str, Enum):
    """Types of predictable events."""
    ELECTION = "election"
    REFERENDUM = "referendum"
    MARKET_TREND = "market_trend"
    PRODUCT_LAUNCH = "product_launch"
    POLICY_IMPACT = "policy_impact"
    SOCIAL_MOVEMENT = "social_movement"
    CONSUMER_BEHAVIOR = "consumer_behavior"


class CalibrationStatus(str, Enum):
    """Status of calibration process."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class GroundTruth(Base):
    """
    Historical ground truth data for calibration.
    Stores verified outcomes of past events.
    """

    __tablename__ = "ground_truths"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Event identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Geographic scope
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    regions_covered: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Event timing
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_collection_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Actual outcomes
    outcomes: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure for ELECTION:
    # {
    #   "national": {
    #       "party_a": 0.452,
    #       "party_b": 0.385,
    #       "party_c": 0.103,
    #       "others": 0.060,
    #       "voter_turnout": 0.73
    #   },
    #   "regional": {
    #       "region_1": {"party_a": 0.55, "party_b": 0.30, ...},
    #       "region_2": {"party_a": 0.40, "party_b": 0.45, ...}
    #   },
    #   "demographics": {
    #       "age_18_24": {"party_a": 0.35, "party_b": 0.45},
    #       "age_25_34": {...}
    #   }
    # }

    # Contextual data at time of event
    context_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure: {
    #   "economic_indicators": {"gdp_growth": 4.2, "unemployment": 3.8},
    #   "major_events": ["covid_recovery", "inflation_spike"],
    #   "polling_data": {...},
    #   "sentiment_scores": {...}
    # }

    # Data source and quality
    data_sources: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # Structure: [{"name": "Electoral Commission", "url": "...", "reliability": 0.99}]
    data_quality_score: Mapped[float] = mapped_column(Float, default=0.95, nullable=False)

    # Metadata
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verification_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", backref="ground_truths")
    calibration_runs = relationship("CalibrationRun", back_populates="ground_truth", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<GroundTruth {self.name} ({self.event_date.date()})>"


class CalibrationRun(Base):
    """
    A calibration run comparing simulation predictions to ground truth.
    Tracks parameter adjustments and accuracy improvements.
    """

    __tablename__ = "calibration_runs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    ground_truth_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ground_truths.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Calibration identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Calibration method
    calibration_method: Mapped[str] = mapped_column(String(50), nullable=False)
    # Methods: bayesian, grid_search, random_search, genetic_algorithm, manual
    method_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure: {
    #   "max_iterations": 100,
    #   "early_stopping_patience": 10,
    #   "target_metric": "accuracy",
    #   "target_value": 0.80,
    #   "parameter_bounds": {...}
    # }

    # Parameters being calibrated
    parameters_to_calibrate: Mapped[list] = mapped_column(JSONB, nullable=False)
    # Structure: [
    #   {"name": "social_influence_weight", "bounds": [0.1, 0.5], "current": 0.3},
    #   {"name": "media_effect_strength", "bounds": [0.0, 1.0], "current": 0.5}
    # ]

    # Initial parameters
    initial_parameters: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_iteration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_iterations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Results
    best_parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    best_metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure: {
    #   "accuracy": 0.85,
    #   "rmse": 2.1,
    #   "mae": 1.8,
    #   "kl_divergence": 0.03,
    #   "brier_score": 0.10,
    #   "correlation": 0.92
    # }

    # Iteration history
    iteration_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # Structure: [
    #   {"iteration": 1, "parameters": {...}, "metrics": {...}, "improvement": 0.05},
    #   ...
    # ]

    # Final predictions with calibrated parameters
    calibrated_predictions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    computation_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    ground_truth = relationship("GroundTruth", back_populates="calibration_runs")
    user = relationship("User", backref="calibration_runs")

    def __repr__(self) -> str:
        return f"<CalibrationRun {self.name} ({self.status})>"


class PredictionResult(Base):
    """
    Final prediction results from a simulation.
    Stores predictions, confidence intervals, and comparison metrics.
    """

    __tablename__ = "prediction_results"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    scenario_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prediction_scenarios.id", ondelete="CASCADE"), nullable=False
    )
    ground_truth_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ground_truths.id", ondelete="SET NULL"), nullable=True
    )

    # Prediction identification
    prediction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_event_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Main predictions
    predictions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure matches ground truth outcomes format

    # Confidence intervals (95% by default)
    confidence_intervals: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure: {
    #   "party_a": {"lower": 0.42, "upper": 0.48, "confidence": 0.95},
    #   "party_b": {"lower": 0.36, "upper": 0.42, "confidence": 0.95}
    # }

    # Monte Carlo simulation data
    monte_carlo_runs: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    distribution_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure: {
    #   "party_a": {"mean": 0.45, "std": 0.015, "percentiles": {...}},
    #   "histogram": {...}
    # }

    # Scenario analysis
    scenario_comparisons: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure: {
    #   "base_case": {...},
    #   "high_turnout": {...},
    #   "economic_crisis": {...}
    # }

    # Accuracy metrics (if ground truth available)
    accuracy_metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure: {
    #   "accuracy": 0.85,
    #   "rmse": 2.1,
    #   "mae": 1.8,
    #   "kl_divergence": 0.03,
    #   "brier_score": 0.10,
    #   "within_ci": true
    # }

    # Explainability
    key_drivers: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure: {
    #   "top_factors": [
    #       {"factor": "economic_sentiment", "impact": 0.25, "direction": "positive"},
    #       {"factor": "youth_turnout", "impact": 0.18, "direction": "positive"}
    #   ],
    #   "sensitivity_analysis": {...},
    #   "swing_analysis": {...}
    # }

    # Regional breakdown
    regional_predictions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Demographic breakdown
    demographic_predictions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Model confidence
    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    model_uncertainty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<PredictionResult for scenario>"


class AccuracyBenchmark(Base):
    """
    Track historical prediction accuracy for model improvement.
    """

    __tablename__ = "accuracy_benchmarks"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Benchmark identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)

    # Aggregated metrics across multiple predictions
    total_predictions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    predictions_within_ci: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Average metrics
    average_accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_rmse: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_mae: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_brier: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Best and worst performance
    best_accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    worst_accuracy: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Detailed history
    prediction_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # Structure: [
    #   {"prediction_id": "uuid", "event_date": "...", "accuracy": 0.85, "metrics": {...}},
    #   ...
    # ]

    # Model improvement tracking
    accuracy_trend: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # Structure: [{"date": "...", "rolling_avg_accuracy": 0.82}]

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", backref="accuracy_benchmarks")

    def __repr__(self) -> str:
        return f"<AccuracyBenchmark {self.name} ({self.average_accuracy:.1%})>"
