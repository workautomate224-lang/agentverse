"""
Product Models - 3-Model System Architecture
Advanced simulation product system: Predict, Insight, Simulate

This implements a comprehensive framework that goes beyond traditional approaches:
- Predict: Quantitative prediction with confidence intervals
- Insight: Qualitative deep-dive into motivations and behaviors
- Simulate: Real-time interactive simulation with agent dynamics
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ProductType(str, Enum):
    """The six core product types - Original 3 + Advanced 3."""
    # Original product types
    PREDICT = "predict"      # Quantitative predictions
    INSIGHT = "insight"      # Qualitative analysis
    SIMULATE = "simulate"    # Interactive simulations

    # Advanced AI Models (Aaru-equivalent)
    ORACLE = "oracle"        # Market Intelligence & Consumer Prediction (Lumen equivalent)
    PULSE = "pulse"          # Dynamic Political & Election Simulation (Dynamo equivalent)
    PRISM = "prism"          # Policy Impact & Public Sector Analytics (Seraph equivalent)


class PredictionType(str, Enum):
    """Types of predictions supported."""
    ELECTION = "election"
    MARKET_ADOPTION = "market_adoption"
    PRODUCT_LAUNCH = "product_launch"
    CAMPAIGN_RESPONSE = "campaign_response"
    BRAND_PERCEPTION = "brand_perception"
    PRICE_SENSITIVITY = "price_sensitivity"
    FEATURE_PREFERENCE = "feature_preference"
    PURCHASE_INTENT = "purchase_intent"
    CHURN_RISK = "churn_risk"
    TREND_FORECAST = "trend_forecast"
    CUSTOM = "custom"


class InsightType(str, Enum):
    """Types of insights supported."""
    MOTIVATION_ANALYSIS = "motivation_analysis"
    DECISION_JOURNEY = "decision_journey"
    BARRIER_IDENTIFICATION = "barrier_identification"
    VALUE_DRIVER = "value_driver"
    PERSONA_CLUSTERING = "persona_clustering"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    COMPETITIVE_PERCEPTION = "competitive_perception"
    NEED_GAP_ANALYSIS = "need_gap_analysis"
    BEHAVIORAL_PATTERN = "behavioral_pattern"
    CULTURAL_CONTEXT = "cultural_context"
    CUSTOM = "custom"


class SimulationType(str, Enum):
    """Types of simulations supported."""
    FOCUS_GROUP = "focus_group"
    PRODUCT_TEST = "product_test"
    CAMPAIGN_TEST = "campaign_test"
    CONCEPT_TEST = "concept_test"
    PRICE_TEST = "price_test"
    MESSAGE_TEST = "message_test"
    UX_TEST = "ux_test"
    MARKET_ENTRY = "market_entry"
    COMPETITIVE_SCENARIO = "competitive_scenario"
    CRISIS_RESPONSE = "crisis_response"
    CUSTOM = "custom"


# ============= ORACLE Types (Market Intelligence) =============
class OracleType(str, Enum):
    """
    ORACLE - Market Intelligence & Consumer Prediction
    Equivalent to Aaru Lumen - simulates customer decisions for private-sector,
    models hard-to-reach segments, predicts market behavior.
    """
    MARKET_SHARE = "market_share"                # Market share forecasting
    CONSUMER_DECISION = "consumer_decision"      # Customer decision simulation
    BRAND_SWITCHING = "brand_switching"          # Brand switching analysis
    PURCHASE_BEHAVIOR = "purchase_behavior"      # Purchase behavior prediction
    SEGMENT_DISCOVERY = "segment_discovery"      # Hard-to-reach segment modeling
    PRICE_ELASTICITY = "price_elasticity"        # Price sensitivity analysis
    PRODUCT_POSITIONING = "product_positioning"  # Product positioning optimization
    COMPETITIVE_INTEL = "competitive_intel"      # Competitive intelligence
    DEMAND_FORECAST = "demand_forecast"          # Demand forecasting
    CUSTOMER_LIFETIME = "customer_lifetime"      # Customer lifetime value prediction
    CHANNEL_PREFERENCE = "channel_preference"    # Channel preference analysis
    CUSTOM = "custom"


# ============= PULSE Types (Political Simulation) =============
class PulseType(str, Enum):
    """
    PULSE - Dynamic Political & Election Simulation
    Equivalent to Aaru Dynamo - voter agents that ingest campaign info,
    real-time electorate simulation, election prediction.
    """
    ELECTION_FORECAST = "election_forecast"      # Election outcome prediction
    VOTER_BEHAVIOR = "voter_behavior"            # Voter behavior simulation
    CAMPAIGN_IMPACT = "campaign_impact"          # Campaign message impact analysis
    SWING_VOTER = "swing_voter"                  # Swing voter identification
    TURNOUT_PREDICTION = "turnout_prediction"    # Voter turnout prediction
    POLICY_RESPONSE = "policy_response"          # Policy announcement response
    DEBATE_IMPACT = "debate_impact"              # Debate performance impact
    DEMOGRAPHIC_SHIFT = "demographic_shift"      # Demographic voting shift analysis
    ISSUE_SALIENCE = "issue_salience"            # Issue importance ranking
    COALITION_ANALYSIS = "coalition_analysis"    # Coalition building analysis
    REAL_TIME_TRACKING = "real_time_tracking"    # Real-time polling simulation
    CUSTOM = "custom"


# ============= PRISM Types (Public Sector Analytics) =============
class PrismType(str, Enum):
    """
    PRISM - Policy Impact & Public Sector Analytics
    Equivalent to Aaru Seraph - configurable simulations for any time/place,
    policy impact analysis, crisis management simulation.
    """
    POLICY_IMPACT = "policy_impact"              # Policy impact assessment
    CRISIS_RESPONSE = "crisis_response"          # Crisis management simulation
    PUBLIC_OPINION = "public_opinion"            # Public opinion modeling
    STAKEHOLDER_MAPPING = "stakeholder_mapping"  # Stakeholder response prediction
    SCENARIO_PLANNING = "scenario_planning"      # Strategic scenario planning
    REGULATORY_IMPACT = "regulatory_impact"      # Regulatory change impact
    SOCIAL_PROGRAM = "social_program"            # Social program effectiveness
    INFRASTRUCTURE_IMPACT = "infrastructure_impact"  # Infrastructure project impact
    COMMUNITY_RESPONSE = "community_response"    # Community engagement simulation
    CULTURAL_SENSITIVITY = "cultural_sensitivity"  # Cultural context analysis
    HISTORICAL_PARALLEL = "historical_parallel"  # Historical event simulation
    CUSTOM = "custom"


class Product(Base):
    """
    Core product configuration.
    Represents a Predict, Insight, or Simulate study.
    """

    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Product identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    product_type: Mapped[str] = mapped_column(String(50), nullable=False)  # predict, insight, simulate
    sub_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # election, focus_group, etc.

    # Target configuration
    target_market: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {
    #   "regions": ["us", "europe", "southeast_asia"],
    #   "countries": ["USA", "UK", "Singapore"],
    #   "demographics": {...},
    #   "sample_size": 1000
    # }

    # Persona configuration
    persona_template_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_templates.id", ondelete="SET NULL"), nullable=True
    )
    persona_count: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    persona_source: Mapped[str] = mapped_column(String(50), default="ai_generated", nullable=False)

    # Study configuration (specific to product type)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # For PREDICT:
    # {
    #   "prediction_type": "market_adoption",
    #   "time_horizon": "6_months",
    #   "variables": [...],
    #   "scenarios": [...]
    # }
    # For INSIGHT:
    # {
    #   "insight_type": "motivation_analysis",
    #   "depth": "comprehensive",
    #   "themes": [...],
    #   "questions": [...]
    # }
    # For SIMULATE:
    # {
    #   "simulation_type": "focus_group",
    #   "duration_minutes": 60,
    #   "moderator_style": "exploratory",
    #   "discussion_guide": [...]
    # }

    # Stimulus/Test materials
    stimulus_materials: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {
    #   "concepts": [...],
    #   "images": [...],
    #   "videos": [...],
    #   "prototypes": [...],
    #   "messages": [...],
    #   "prices": [...]
    # }

    # Quality and validation
    methodology: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    validation_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    confidence_target: Mapped[float] = mapped_column(Float, default=0.9, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    # draft, configured, running, completed, failed

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    runs = relationship("ProductRun", back_populates="product", cascade="all, delete-orphan")
    results = relationship("ProductResult", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Product {self.name} ({self.product_type})>"


class ProductRun(Base):
    """
    Individual run of a product study.
    Tracks execution and agent interactions.
    """

    __tablename__ = "product_runs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    product_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    # Run identification
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Configuration snapshot (for reproducibility)
    config_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    persona_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Execution tracking
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    agents_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    agents_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    agents_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Cost tracking
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    product = relationship("Product", back_populates="runs")
    agent_interactions = relationship("AgentInteraction", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ProductRun {self.id} (Run #{self.run_number})>"


class AgentInteraction(Base):
    """
    Individual agent interaction within a product run.
    Captures the full dialogue and analysis.
    """

    __tablename__ = "agent_interactions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    run_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_runs.id", ondelete="CASCADE"), nullable=False
    )
    persona_record_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_records.id", ondelete="SET NULL"), nullable=True
    )

    # Agent identity
    agent_index: Mapped[int] = mapped_column(Integer, nullable=False)
    persona_summary: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Interaction content
    interaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # survey, interview, focus_group, product_test, etc.

    # Full conversation/interaction
    conversation: Mapped[list] = mapped_column(JSONB, nullable=False)
    # [
    #   {"role": "system", "content": "..."},
    #   {"role": "moderator", "content": "..."},
    #   {"role": "agent", "content": "..."},
    #   ...
    # ]

    # Extracted data
    responses: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # {
    #   "question_1": {"answer": "...", "sentiment": 0.8, "confidence": 0.9},
    #   "question_2": {...}
    # }

    # Analysis
    sentiment_overall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    key_themes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    behavioral_signals: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Quality metrics
    coherence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    authenticity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Cost
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    run = relationship("ProductRun", back_populates="agent_interactions")

    def __repr__(self) -> str:
        return f"<AgentInteraction {self.id} (Agent #{self.agent_index})>"


class ProductResult(Base):
    """
    Aggregated results from a product study.
    Contains predictions, insights, or simulation outcomes.
    """

    __tablename__ = "product_results"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    product_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_runs.id", ondelete="SET NULL"), nullable=True
    )

    # Result identification
    result_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # For PREDICT: prediction, confidence_interval, scenario_comparison
    # For INSIGHT: theme_analysis, motivation_map, decision_journey
    # For SIMULATE: session_summary, interaction_analysis, recommendation

    # ============= PREDICT Results =============
    predictions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {
    #   "primary_prediction": {
    #     "outcome": "Product A wins 62% market share",
    #     "value": 0.62,
    #     "confidence_interval": [0.58, 0.66],
    #     "confidence_level": 0.95
    #   },
    #   "scenario_predictions": [...],
    #   "segment_breakdown": {...},
    #   "time_series": [...]
    # }

    # ============= INSIGHT Results =============
    insights: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {
    #   "key_insights": [
    #     {
    #       "theme": "Price is secondary to quality",
    #       "strength": 0.85,
    #       "supporting_evidence": [...],
    #       "segments_affected": [...]
    #     }
    #   ],
    #   "motivation_analysis": {...},
    #   "barrier_analysis": {...},
    #   "opportunity_areas": [...],
    #   "recommendations": [...]
    # }

    # ============= SIMULATE Results =============
    simulation_outcomes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {
    #   "session_dynamics": {...},
    #   "consensus_points": [...],
    #   "disagreement_points": [...],
    #   "key_quotes": [...],
    #   "behavioral_observations": [...],
    #   "group_sentiment_trajectory": [...]
    # }

    # ============= ORACLE Results (Market Intelligence) =============
    oracle_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {
    #   "market_forecast": {
    #     "predicted_share": 0.42,
    #     "confidence_interval": [0.38, 0.46],
    #     "time_horizon": "12_months",
    #     "trend_direction": "growth"
    #   },
    #   "consumer_segments": [
    #     {"segment": "Early Adopters", "size": 0.15, "conversion_prob": 0.72},
    #     {"segment": "Mainstream", "size": 0.60, "conversion_prob": 0.45},
    #     ...
    #   ],
    #   "decision_drivers": [...],
    #   "brand_perception": {...},
    #   "competitive_position": {...},
    #   "price_sensitivity_curve": [...],
    #   "channel_effectiveness": {...}
    # }

    # ============= PULSE Results (Political Simulation) =============
    pulse_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {
    #   "election_forecast": {
    #     "candidates": [
    #       {"name": "Candidate A", "predicted_vote": 0.48, "ci": [0.45, 0.51]},
    #       {"name": "Candidate B", "predicted_vote": 0.44, "ci": [0.41, 0.47]},
    #       ...
    #     ],
    #     "predicted_winner": "Candidate A",
    #     "win_probability": 0.73
    #   },
    #   "voter_segments": [...],
    #   "swing_voter_analysis": {...},
    #   "turnout_prediction": {...},
    #   "issue_importance": [...],
    #   "campaign_effectiveness": {...},
    #   "demographic_breakdown": {...},
    #   "momentum_trajectory": [...]
    # }

    # ============= PRISM Results (Public Sector Analytics) =============
    prism_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {
    #   "policy_impact": {
    #     "overall_support": 0.62,
    #     "approval_trajectory": [...],
    #     "affected_groups": [...]
    #   },
    #   "stakeholder_map": [
    #     {"group": "Business", "position": 0.7, "influence": 0.8},
    #     {"group": "Labor", "position": -0.3, "influence": 0.6},
    #     ...
    #   ],
    #   "crisis_scenarios": [...],
    #   "public_sentiment": {...},
    #   "implementation_risks": [...],
    #   "mitigation_strategies": [...],
    #   "historical_parallels": [...],
    #   "timeline_projections": [...]
    # }

    # ============= Common Analysis =============
    statistical_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {
    #   "sample_size": 1000,
    #   "margin_of_error": 0.03,
    #   "statistical_significance": true,
    #   "p_value": 0.01,
    #   "effect_size": 0.45
    # }

    segment_analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {
    #   "by_age": {...},
    #   "by_income": {...},
    #   "by_region": {...},
    #   "by_psychographic_cluster": {...}
    # }

    # Validation and quality
    validation_results: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    quality_metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Executive summary
    executive_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_takeaways: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    recommendations: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Visualizations (stored as configs for frontend rendering)
    visualizations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    product = relationship("Product", back_populates="results")

    def __repr__(self) -> str:
        return f"<ProductResult {self.id} ({self.result_type})>"


class Benchmark(Base):
    """
    Benchmark data for validation.
    Stores historical real-world outcomes to validate predictions.
    """

    __tablename__ = "benchmarks"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Benchmark identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    # election, product_launch, campaign, etc.

    # Event details
    event_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Actual outcome
    actual_outcome: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {
    #   "result": "Candidate A won with 52.1%",
    #   "value": 0.521,
    #   "detailed_breakdown": {...}
    # }

    # Data source
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    # Usage
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Benchmark {self.name}>"


class ValidationRecord(Base):
    """
    Track validation of our predictions against real outcomes.
    This builds the accuracy tracking system.
    """

    __tablename__ = "validation_records"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    product_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    benchmark_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("benchmarks.id", ondelete="CASCADE"), nullable=False
    )

    # Prediction vs Actual
    predicted_outcome: Mapped[dict] = mapped_column(JSONB, nullable=False)
    actual_outcome: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Accuracy metrics
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=False)
    # 0-1 scale, 1 being perfect prediction

    deviation: Mapped[float] = mapped_column(Float, nullable=False)
    # Absolute deviation from actual

    within_confidence_interval: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Detailed analysis
    analysis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {
    #   "segment_accuracy": {...},
    #   "factors_contributing_to_deviation": [...],
    #   "lessons_learned": [...]
    # }

    # Timestamps
    validated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<ValidationRecord {self.id} (Accuracy: {self.accuracy_score:.2%})>"
