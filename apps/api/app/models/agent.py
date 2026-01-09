"""
Agent Models for Predictive Simulation
Enhanced agent with state vector, policy mechanism, memory store, and reward function.
Supports MARL training and behavioral economics modeling.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AgentState(str, Enum):
    """Agent behavioral states."""
    IDLE = "idle"
    ACTIVE = "active"
    DECIDING = "deciding"
    INTERACTING = "interacting"
    INFLUENCED = "influenced"
    COMMITTED = "committed"


class PolicyType(str, Enum):
    """Types of agent decision policies."""
    RULE_BASED = "rule_based"           # Fixed behavioral rules
    LLM_PROMPTED = "llm_prompted"       # LLM-driven decisions
    MARL_TRAINED = "marl_trained"       # Trained neural network policy
    HYBRID = "hybrid"                   # Combination of approaches
    BEHAVIORAL_ECONOMIC = "behavioral_economic"  # Behavioral economics model


class SimulationAgent(Base):
    """
    Individual agent in a predictive simulation.
    Contains state vector, behavioral parameters, and decision history.
    """

    __tablename__ = "simulation_agents"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    scenario_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prediction_scenarios.id", ondelete="CASCADE"), nullable=False
    )

    # Agent identification
    agent_index: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Region assignment
    region_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    coordinates: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {"x": 100, "y": 200}

    # ============= STATE VECTOR =============
    # Current position in belief/behavior space
    state_vector: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure: {
    #   "political_preference": {
    #       "party_a": 0.45,
    #       "party_b": 0.35,
    #       "undecided": 0.20
    #   },
    #   "issue_priorities": {
    #       "economy": 0.8,
    #       "healthcare": 0.6,
    #       "education": 0.5,
    #       "environment": 0.3
    #   },
    #   "engagement_level": 0.7,
    #   "certainty": 0.6,
    #   "influence_susceptibility": 0.4,
    #   "information_exposure": 0.5
    # }

    # Previous state (for computing changes)
    previous_state_vector: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # ============= DEMOGRAPHICS =============
    demographics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure mirrors PersonaRecord demographics

    # ============= BEHAVIORAL ECONOMICS PARAMETERS =============
    behavioral_params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure: {
    #   "risk_aversion": 0.6,           # 0-1, higher = more risk averse
    #   "loss_aversion_lambda": 2.25,   # Kahneman-Tversky lambda
    #   "probability_weighting": {       # Prelec function parameters
    #       "alpha": 0.65,
    #       "beta": 0.60
    #   },
    #   "status_quo_bias": 0.3,         # Tendency to stick with current choice
    #   "anchoring_strength": 0.5,      # How much initial beliefs anchor
    #   "confirmation_bias": 0.4,       # Tendency to seek confirming info
    #   "bandwagon_effect": 0.3,        # Susceptibility to majority opinion
    #   "availability_heuristic": 0.5,  # Weight given to recent events
    #   "bounded_rationality": 0.6,     # Cognitive limitations
    #   "social_proof_weight": 0.4,     # Influence of peer decisions
    #   "time_discounting": 0.95        # Discount factor for future outcomes
    # }

    # ============= PSYCHOGRAPHICS =============
    psychographics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Big Five traits, values, decision style - mirrors PersonaRecord

    # ============= SOCIAL NETWORK =============
    social_network: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure: {
    #   "connections": ["agent_id_1", "agent_id_2", ...],
    #   "influence_weights": {"agent_id_1": 0.3, "agent_id_2": 0.2},
    #   "group_memberships": ["family", "work", "community"],
    #   "echo_chamber_score": 0.6  # Homophily measure
    # }

    # ============= POLICY MECHANISM =============
    policy_type: Mapped[str] = mapped_column(String(50), default="behavioral_economic", nullable=False)
    policy_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure depends on policy_type:
    # For MARL_TRAINED: {"model_id": "uuid", "network_weights": "path"}
    # For RULE_BASED: {"rules": [...], "priority_order": [...]}
    # For LLM_PROMPTED: {"prompt_template": "...", "model": "gpt-4"}

    # ============= MEMORY STORE =============
    memory: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure: {
    #   "short_term": [  # Recent events (last N steps)
    #       {"step": 1, "action": "vote_party_a", "outcome": "positive", "reward": 0.5},
    #       ...
    #   ],
    #   "long_term": {  # Aggregated experience
    #       "party_a_experiences": {"positive": 5, "negative": 2},
    #       "party_b_experiences": {"positive": 3, "negative": 4},
    #       "learned_associations": {...}
    #   },
    #   "episodic": [  # Significant events
    #       {"event": "economic_crisis", "step": 50, "impact": -0.3},
    #       ...
    #   ]
    # }

    # ============= REWARD TRACKING =============
    cumulative_reward: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_reward: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reward_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # Structure: [{"step": 1, "reward": 0.5, "components": {"accuracy": 0.3, "consistency": 0.2}}]

    # ============= CURRENT STATE =============
    current_state: Mapped[str] = mapped_column(String(50), default="idle", nullable=False)
    last_action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_action_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Action commitment (for election: who they'll vote for)
    committed_action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    commitment_strength: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    commitment_step: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ============= METADATA =============
    source_persona_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # Link to original persona if applicable

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    scenario = relationship("PredictionScenario", back_populates="agents")
    action_history = relationship("AgentAction", back_populates="agent", cascade="all, delete-orphan")
    interactions = relationship("AgentInteractionLog", back_populates="source_agent",
                               foreign_keys="AgentInteractionLog.source_agent_id", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SimulationAgent {self.agent_index}>"


class AgentAction(Base):
    """
    Record of agent actions during simulation.
    Captures the full decision-making context for analysis and training.
    """

    __tablename__ = "agent_actions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    agent_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_agents.id", ondelete="CASCADE"), nullable=False
    )

    # Timing
    time_step: Mapped[int] = mapped_column(Integer, nullable=False)

    # State before action
    state_before: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Action taken
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    action_probabilities: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure: {"vote_party_a": 0.45, "vote_party_b": 0.35, "undecided": 0.20}

    # Decision context
    decision_context: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure: {
    #   "environment_state": {...},
    #   "social_influence": {"peer_actions": {...}, "influence_received": 0.2},
    #   "recent_events": [...],
    #   "cognitive_biases_applied": ["confirmation_bias", "status_quo"]
    # }

    # Outcome
    reward: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reward_components: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # State after action
    state_after: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # For MARL training
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    advantage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # For PPO
    value_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    agent = relationship("SimulationAgent", back_populates="action_history")

    def __repr__(self) -> str:
        return f"<AgentAction step={self.time_step} action={self.action}>"


class AgentInteractionLog(Base):
    """
    Log of agent-to-agent interactions during simulation.
    Tracks social influence and information spread.
    """

    __tablename__ = "agent_interaction_logs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    source_agent_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_agents.id", ondelete="CASCADE"), nullable=False
    )
    target_agent_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_agents.id", ondelete="CASCADE"), nullable=False
    )

    # Timing
    time_step: Mapped[int] = mapped_column(Integer, nullable=False)

    # Interaction type
    interaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: conversation, social_media, family_discussion, work_discussion, media_exposure

    # Content
    content: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure: {
    #   "topic": "economy",
    #   "sentiment": "negative",
    #   "information_shared": {...},
    #   "emotional_valence": -0.3
    # }

    # Influence outcome
    influence_magnitude: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    influence_direction: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "toward_party_a"
    state_change_vector: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    source_agent = relationship("SimulationAgent", back_populates="interactions",
                                foreign_keys=[source_agent_id])

    def __repr__(self) -> str:
        return f"<AgentInteractionLog step={self.time_step} type={self.interaction_type}>"


class PolicyModel(Base):
    """
    Trained MARL policy model.
    Stores trained neural network weights and metadata.
    """

    __tablename__ = "policy_models"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    environment_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_environments.id", ondelete="SET NULL"), nullable=True
    )

    # Model identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)

    # Model architecture
    architecture: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure: {
    #   "type": "actor_critic",
    #   "algorithm": "ppo",
    #   "network": {
    #       "shared_layers": [256, 256],
    #       "actor_layers": [128],
    #       "critic_layers": [128],
    #       "activation": "relu",
    #       "state_dim": 50,
    #       "action_dim": 4
    #   }
    # }

    # Training configuration
    training_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure: {
    #   "learning_rate": 3e-4,
    #   "gamma": 0.99,
    #   "gae_lambda": 0.95,
    #   "clip_ratio": 0.2,
    #   "entropy_coef": 0.01,
    #   "value_coef": 0.5,
    #   "max_grad_norm": 0.5,
    #   "batch_size": 256,
    #   "epochs_per_update": 10
    # }

    # Training status
    training_status: Mapped[str] = mapped_column(String(50), default="untrained", nullable=False)
    # untrained, training, trained, failed
    training_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    training_episodes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Performance metrics
    performance_metrics: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Structure: {
    #   "average_reward": 0.75,
    #   "prediction_accuracy": 0.82,
    #   "policy_loss": 0.05,
    #   "value_loss": 0.08,
    #   "entropy": 0.5,
    #   "training_curves": {...}
    # }

    # Model weights storage
    weights_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # S3/GCS path
    weights_checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA-256

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_trained_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="policy_models")

    def __repr__(self) -> str:
        return f"<PolicyModel {self.name} v{self.version}>"
