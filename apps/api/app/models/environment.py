"""
Environment Models for Predictive Simulation
Global world state variables, spatial maps, and external events.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EnvironmentType(str, Enum):
    """Types of simulation environments."""
    ELECTION = "election"
    MARKET = "market"
    SOCIAL = "social"
    POLICY = "policy"
    ECONOMIC = "economic"
    CUSTOM = "custom"


class RegionLevel(str, Enum):
    """Geographic granularity levels."""
    COUNTRY = "country"
    STATE = "state"
    DISTRICT = "district"
    CONSTITUENCY = "constituency"
    CITY = "city"
    NEIGHBORHOOD = "neighborhood"


class SimulationEnvironment(Base):
    """
    Simulation environment configuration.
    Defines the world context in which agents operate.
    """

    __tablename__ = "simulation_environments"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Environment identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    environment_type: Mapped[str] = mapped_column(
        String(50), default="custom", nullable=False
    )

    # Geographic configuration
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    region_level: Mapped[str] = mapped_column(String(50), default="country", nullable=False)
    regions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # Structure: [{"id": "constituency_1", "name": "Kuala Lumpur", "population": 500000, "coordinates": {...}}]

    # Spatial map configuration
    map_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure: {"width": 1000, "height": 800, "tile_size": 16, "boundaries": {...}}

    # State space definition
    state_space: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure: {
    #   "global_variables": ["economic_index", "social_mood", "media_influence"],
    #   "agent_variables": ["political_preference", "economic_concern", "engagement_level"],
    #   "bounds": {"economic_index": [0, 100], "social_mood": [-1, 1]}
    # }

    # Action space definition
    action_space: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure: {
    #   "type": "discrete",  # or "continuous"
    #   "actions": ["vote_party_a", "vote_party_b", "abstain", "undecided"],
    #   "or for continuous": {"dimensions": 3, "bounds": [[-1, 1], [-1, 1], [0, 1]]}
    # }

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", backref="simulation_environments")
    global_states = relationship("EnvironmentState", back_populates="environment", cascade="all, delete-orphan")
    external_events = relationship("ExternalEvent", back_populates="environment", cascade="all, delete-orphan")
    prediction_scenarios = relationship("PredictionScenario", back_populates="environment", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SimulationEnvironment {self.name} ({self.environment_type})>"


class EnvironmentState(Base):
    """
    Global environment state at a specific time step.
    Captures world-level variables that affect all agents.
    """

    __tablename__ = "environment_states"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    environment_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_environments.id", ondelete="CASCADE"), nullable=False
    )
    scenario_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prediction_scenarios.id", ondelete="CASCADE"), nullable=True
    )

    # Time step
    time_step: Mapped[int] = mapped_column(Integer, nullable=False)
    simulation_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Global state variables
    global_state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure: {
    #   "economic_index": 65.5,
    #   "unemployment_rate": 4.2,
    #   "inflation_rate": 2.8,
    #   "consumer_confidence": 72.0,
    #   "social_mood": 0.3,  # -1 to 1
    #   "media_influence": {
    #       "party_a_coverage": 0.45,
    #       "party_b_coverage": 0.40,
    #       "sentiment_party_a": 0.2,
    #       "sentiment_party_b": -0.1
    #   },
    #   "crisis_events": [],
    #   "weather_impact": 0.0
    # }

    # Regional state overrides
    regional_states: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure: {
    #   "region_id_1": {"local_economic_index": 70.0, "local_issues": ["infrastructure"]},
    #   "region_id_2": {"local_economic_index": 55.0, "local_issues": ["unemployment"]}
    # }

    # Aggregate metrics
    aggregate_metrics: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure: {
    #   "total_agents": 10000,
    #   "action_distribution": {"vote_party_a": 4500, "vote_party_b": 3800, "undecided": 1700},
    #   "average_engagement": 0.65,
    #   "polarization_index": 0.42
    # }

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    environment = relationship("SimulationEnvironment", back_populates="global_states")

    def __repr__(self) -> str:
        return f"<EnvironmentState step={self.time_step}>"


class ExternalEvent(Base):
    """
    External events that impact the simulation environment.
    Examples: economic crisis, scandals, policy announcements.
    """

    __tablename__ = "external_events"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    environment_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_environments.id", ondelete="CASCADE"), nullable=False
    )

    # Event identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: scandal, economic_shock, policy_announcement, natural_disaster, media_campaign

    # Timing
    trigger_time_step: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_steps: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    decay_rate: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)  # How quickly impact fades

    # Impact configuration
    impact: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure: {
    #   "global_variables": {
    #       "economic_index": -5.0,  # Additive change
    #       "social_mood": -0.2,
    #       "media_influence.party_a_coverage": 0.1
    #   },
    #   "agent_effects": {
    #       "political_preference_shift": {"party_a": -0.1, "party_b": 0.05},
    #       "engagement_boost": 0.15
    #   },
    #   "regional_scope": ["all"] or ["region_1", "region_2"],
    #   "demographic_targeting": {"age_min": 18, "age_max": 35}  # Optional
    # }

    # Historical event reference (for calibration)
    is_historical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    historical_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    environment = relationship("SimulationEnvironment", back_populates="external_events")

    def __repr__(self) -> str:
        return f"<ExternalEvent {self.name} ({self.event_type})>"


class PredictionScenario(Base):
    """
    A specific prediction scenario within an environment.
    Represents a complete simulation run with configurable parameters.
    """

    __tablename__ = "prediction_scenarios"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    environment_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_environments.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Scenario identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Target event for prediction
    target_event: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "election_2026"
    target_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Simulation parameters
    agent_count: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    time_steps: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    step_duration_days: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # Days per step

    # Agent configuration
    agent_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure: {
    #   "use_marl_policy": true,
    #   "policy_model_id": "uuid",
    #   "behavioral_model": "bounded_rational",
    #   "demographic_distribution": "census_based",
    #   "regional_allocation": {"region_1": 0.3, "region_2": 0.7}
    # }

    # Initial state configuration
    initial_state: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure: {
    #   "global_variables": {"economic_index": 70, "social_mood": 0.1},
    #   "agent_initialization": "from_data_source" or "random"
    # }

    # Events to include
    event_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Simulation status
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    # draft, ready, running, completed, failed
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Results
    prediction_results: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure: {
    #   "final_distribution": {"party_a": 0.45, "party_b": 0.40, "others": 0.15},
    #   "confidence_intervals": {"party_a": [0.42, 0.48], "party_b": [0.37, 0.43]},
    #   "regional_breakdown": {...},
    #   "swing_analysis": {...}
    # }

    # Calibration metrics
    calibration_metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure: {
    #   "accuracy": 0.85,
    #   "rmse": 2.3,
    #   "kl_divergence": 0.05,
    #   "brier_score": 0.12
    # }

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    computation_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Cost tracking
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    compute_credits_used: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    environment = relationship("SimulationEnvironment", back_populates="prediction_scenarios")
    user = relationship("User", backref="prediction_scenarios")
    agents = relationship("SimulationAgent", back_populates="scenario", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PredictionScenario {self.name} ({self.status})>"
