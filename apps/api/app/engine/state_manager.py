"""
State Manager for Predictive Simulation

Manages global environment state and individual agent states.
Handles state transitions, persistence, and rollback capabilities.
Optimized for 10,000+ agent simulations.
"""

import asyncio
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Tuple
from uuid import UUID
from collections import defaultdict
import copy
import json
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class GlobalState:
    """Global environment state at a specific time step."""

    time_step: int = 0
    simulation_date: Optional[datetime] = None

    # Economic indicators
    economic_indicators: Dict[str, float] = field(default_factory=lambda: {
        "gdp_growth": 0.0,
        "unemployment_rate": 0.0,
        "inflation_rate": 0.0,
        "consumer_confidence": 0.0,
        "stock_market_index": 0.0,
        "interest_rate": 0.0,
    })

    # Political state
    political_state: Dict[str, Any] = field(default_factory=lambda: {
        "party_approval_ratings": {},
        "incumbent_party": None,
        "days_to_event": None,
        "campaign_intensity": 0.0,
        "media_coverage": {},
    })

    # Social indicators
    social_indicators: Dict[str, float] = field(default_factory=lambda: {
        "social_unrest_index": 0.0,
        "trust_in_government": 0.0,
        "media_polarization": 0.0,
        "social_mobility": 0.0,
    })

    # Active events
    active_events: List[Dict[str, Any]] = field(default_factory=list)

    # Aggregate statistics
    aggregate_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "time_step": self.time_step,
            "simulation_date": self.simulation_date.isoformat() if self.simulation_date else None,
            "economic_indicators": self.economic_indicators,
            "political_state": self.political_state,
            "social_indicators": self.social_indicators,
            "active_events": self.active_events,
            "aggregate_stats": self.aggregate_stats,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GlobalState":
        """Create from dictionary."""
        state = cls()
        state.time_step = data.get("time_step", 0)
        if data.get("simulation_date"):
            state.simulation_date = datetime.fromisoformat(data["simulation_date"])
        state.economic_indicators = data.get("economic_indicators", state.economic_indicators)
        state.political_state = data.get("political_state", state.political_state)
        state.social_indicators = data.get("social_indicators", state.social_indicators)
        state.active_events = data.get("active_events", [])
        state.aggregate_stats = data.get("aggregate_stats", {})
        return state

    def copy(self) -> "GlobalState":
        """Create a deep copy of the state."""
        new_state = GlobalState()
        new_state.time_step = self.time_step
        new_state.simulation_date = self.simulation_date
        new_state.economic_indicators = copy.deepcopy(self.economic_indicators)
        new_state.political_state = copy.deepcopy(self.political_state)
        new_state.social_indicators = copy.deepcopy(self.social_indicators)
        new_state.active_events = copy.deepcopy(self.active_events)
        new_state.aggregate_stats = copy.deepcopy(self.aggregate_stats)
        return new_state


@dataclass
class AgentStateVector:
    """
    Vectorized agent state for efficient batch processing.
    Designed for numpy operations on 10,000+ agents.
    """

    agent_id: UUID
    agent_index: int

    # Core beliefs/preferences (as probability distributions)
    preferences: np.ndarray = field(default_factory=lambda: np.zeros(10))  # e.g., party preferences

    # Issue priorities (importance weights)
    issue_priorities: np.ndarray = field(default_factory=lambda: np.zeros(10))

    # Behavioral parameters
    engagement_level: float = 0.5
    certainty: float = 0.5
    influence_susceptibility: float = 0.5
    information_exposure: float = 0.5

    # Commitment
    committed_choice: Optional[int] = None
    commitment_strength: float = 0.0

    # Social network position
    network_centrality: float = 0.0
    echo_chamber_score: float = 0.0

    # Recent history (circular buffer indices)
    recent_actions: List[int] = field(default_factory=list)
    recent_rewards: List[float] = field(default_factory=list)

    def to_vector(self) -> np.ndarray:
        """Convert to flat numpy vector for batch processing."""
        return np.concatenate([
            self.preferences,
            self.issue_priorities,
            np.array([
                self.engagement_level,
                self.certainty,
                self.influence_susceptibility,
                self.information_exposure,
                self.commitment_strength,
                self.network_centrality,
                self.echo_chamber_score,
            ])
        ])

    @classmethod
    def from_vector(cls, agent_id: UUID, agent_index: int, vector: np.ndarray,
                   pref_size: int = 10, issue_size: int = 10) -> "AgentStateVector":
        """Create from flat numpy vector."""
        state = cls(agent_id=agent_id, agent_index=agent_index)
        idx = 0
        state.preferences = vector[idx:idx+pref_size]
        idx += pref_size
        state.issue_priorities = vector[idx:idx+issue_size]
        idx += issue_size
        state.engagement_level = vector[idx]
        state.certainty = vector[idx+1]
        state.influence_susceptibility = vector[idx+2]
        state.information_exposure = vector[idx+3]
        state.commitment_strength = vector[idx+4]
        state.network_centrality = vector[idx+5]
        state.echo_chamber_score = vector[idx+6]
        return state


class StateManager:
    """
    Manages simulation state for both global environment and individual agents.
    Supports checkpointing, rollback, and efficient batch state updates.
    """

    def __init__(
        self,
        max_agents: int = 10000,
        checkpoint_interval: int = 10,
        max_checkpoints: int = 100,
        preference_dimensions: int = 10,
        issue_dimensions: int = 10,
    ):
        self.max_agents = max_agents
        self.checkpoint_interval = checkpoint_interval
        self.max_checkpoints = max_checkpoints
        self.preference_dimensions = preference_dimensions
        self.issue_dimensions = issue_dimensions

        # Global state
        self.global_state = GlobalState()

        # Agent states (vectorized for efficiency)
        self.agent_count = 0
        self.agent_ids: List[UUID] = []
        self.agent_id_to_index: Dict[UUID, int] = {}

        # Vectorized agent state matrices
        # Shape: (num_agents, dimension)
        self.preferences_matrix: Optional[np.ndarray] = None
        self.issue_priorities_matrix: Optional[np.ndarray] = None
        self.scalar_states: Optional[np.ndarray] = None  # (num_agents, 7) for scalar values

        # Committed choices (-1 = undecided)
        self.committed_choices: Optional[np.ndarray] = None

        # Social network (sparse representation)
        self.network_adjacency: Dict[int, List[Tuple[int, float]]] = defaultdict(list)

        # Memory buffers
        self.recent_actions_buffer: Optional[np.ndarray] = None  # (num_agents, buffer_size)
        self.recent_rewards_buffer: Optional[np.ndarray] = None
        self.buffer_size = 10

        # Checkpoints for rollback
        self.checkpoints: List[Tuple[int, GlobalState, np.ndarray, np.ndarray, np.ndarray]] = []

        # State change tracking
        self.state_change_log: List[Dict[str, Any]] = []

        # Observers for state changes
        self.observers: List[Callable[[str, Any], None]] = []

        # Region aggregations
        self.region_agent_indices: Dict[str, List[int]] = defaultdict(list)

        # Demographic group indices
        self.demographic_indices: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(list))

    def initialize(
        self,
        agent_ids: List[UUID],
        initial_preferences: np.ndarray,
        initial_issue_priorities: np.ndarray,
        initial_scalar_states: np.ndarray,
        global_state: Optional[GlobalState] = None,
    ) -> None:
        """
        Initialize state manager with agent data.

        Args:
            agent_ids: List of agent UUIDs
            initial_preferences: Shape (num_agents, preference_dimensions)
            initial_issue_priorities: Shape (num_agents, issue_dimensions)
            initial_scalar_states: Shape (num_agents, 7) - engagement, certainty, etc.
            global_state: Optional initial global state
        """
        self.agent_count = len(agent_ids)
        self.agent_ids = agent_ids
        self.agent_id_to_index = {aid: i for i, aid in enumerate(agent_ids)}

        # Initialize matrices
        self.preferences_matrix = initial_preferences.copy()
        self.issue_priorities_matrix = initial_issue_priorities.copy()
        self.scalar_states = initial_scalar_states.copy()

        # Initialize commitments (all undecided)
        self.committed_choices = np.full(self.agent_count, -1, dtype=np.int32)

        # Initialize buffers
        self.recent_actions_buffer = np.full((self.agent_count, self.buffer_size), -1, dtype=np.int32)
        self.recent_rewards_buffer = np.zeros((self.agent_count, self.buffer_size), dtype=np.float32)

        # Set global state
        if global_state:
            self.global_state = global_state

        # Create initial checkpoint
        self._create_checkpoint()

        logger.info(f"StateManager initialized with {self.agent_count} agents")

    def initialize_from_agents(
        self,
        agents: List[Any],  # List of SimulationAgent objects
        global_state: Optional[GlobalState] = None,
    ) -> None:
        """
        Initialize from database agent objects.

        Args:
            agents: List of SimulationAgent model instances
            global_state: Optional initial global state
        """
        self.agent_count = len(agents)
        self.agent_ids = [a.id for a in agents]
        self.agent_id_to_index = {a.id: i for i, a in enumerate(agents)}

        # Build matrices from agent data
        self.preferences_matrix = np.zeros((self.agent_count, self.preference_dimensions))
        self.issue_priorities_matrix = np.zeros((self.agent_count, self.issue_dimensions))
        self.scalar_states = np.zeros((self.agent_count, 7))

        for i, agent in enumerate(agents):
            # Extract preferences from state vector
            state_vec = agent.state_vector
            if "political_preference" in state_vec:
                prefs = state_vec["political_preference"]
                for j, (party, prob) in enumerate(prefs.items()):
                    if j < self.preference_dimensions:
                        self.preferences_matrix[i, j] = prob

            # Extract issue priorities
            if "issue_priorities" in state_vec:
                issues = state_vec["issue_priorities"]
                for j, (issue, priority) in enumerate(issues.items()):
                    if j < self.issue_dimensions:
                        self.issue_priorities_matrix[i, j] = priority

            # Extract scalar states
            self.scalar_states[i, 0] = state_vec.get("engagement_level", 0.5)
            self.scalar_states[i, 1] = state_vec.get("certainty", 0.5)
            self.scalar_states[i, 2] = state_vec.get("influence_susceptibility", 0.5)
            self.scalar_states[i, 3] = state_vec.get("information_exposure", 0.5)
            self.scalar_states[i, 4] = agent.commitment_strength

            # Network metrics
            social_net = agent.social_network
            self.scalar_states[i, 5] = social_net.get("centrality", 0.0)
            self.scalar_states[i, 6] = social_net.get("echo_chamber_score", 0.0)

            # Build region indices
            if agent.region_id:
                self.region_agent_indices[agent.region_id].append(i)

            # Build demographic indices
            demo = agent.demographics
            for key, value in demo.items():
                if isinstance(value, str):
                    self.demographic_indices[key][value].append(i)

        # Initialize commitments and buffers
        self.committed_choices = np.full(self.agent_count, -1, dtype=np.int32)
        self.recent_actions_buffer = np.full((self.agent_count, self.buffer_size), -1, dtype=np.int32)
        self.recent_rewards_buffer = np.zeros((self.agent_count, self.buffer_size), dtype=np.float32)

        # Set global state
        if global_state:
            self.global_state = global_state

        # Create initial checkpoint
        self._create_checkpoint()

        logger.info(f"StateManager initialized from {self.agent_count} agent objects")

    def get_agent_state(self, agent_id: UUID) -> Optional[AgentStateVector]:
        """Get state for a specific agent."""
        if agent_id not in self.agent_id_to_index:
            return None

        idx = self.agent_id_to_index[agent_id]
        state = AgentStateVector(
            agent_id=agent_id,
            agent_index=idx,
        )
        state.preferences = self.preferences_matrix[idx].copy()
        state.issue_priorities = self.issue_priorities_matrix[idx].copy()
        state.engagement_level = self.scalar_states[idx, 0]
        state.certainty = self.scalar_states[idx, 1]
        state.influence_susceptibility = self.scalar_states[idx, 2]
        state.information_exposure = self.scalar_states[idx, 3]
        state.commitment_strength = self.scalar_states[idx, 4]
        state.network_centrality = self.scalar_states[idx, 5]
        state.echo_chamber_score = self.scalar_states[idx, 6]

        committed = self.committed_choices[idx]
        state.committed_choice = committed if committed >= 0 else None

        return state

    def get_batch_states(
        self,
        agent_indices: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Get vectorized states for batch processing.

        Args:
            agent_indices: Optional subset of agent indices (default: all)

        Returns:
            Tuple of (preferences, issue_priorities, scalar_states)
        """
        if agent_indices is None:
            return (
                self.preferences_matrix,
                self.issue_priorities_matrix,
                self.scalar_states,
            )

        return (
            self.preferences_matrix[agent_indices],
            self.issue_priorities_matrix[agent_indices],
            self.scalar_states[agent_indices],
        )

    def update_agent_preferences(
        self,
        agent_indices: np.ndarray,
        new_preferences: np.ndarray,
    ) -> None:
        """
        Batch update agent preferences.

        Args:
            agent_indices: Shape (batch_size,) - indices to update
            new_preferences: Shape (batch_size, preference_dimensions)
        """
        # Normalize to ensure valid probability distribution
        new_preferences = np.clip(new_preferences, 0, 1)
        row_sums = new_preferences.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums > 0, row_sums, 1)  # Avoid division by zero
        normalized = new_preferences / row_sums

        self.preferences_matrix[agent_indices] = normalized

        # Log state change
        self.state_change_log.append({
            "time_step": self.global_state.time_step,
            "type": "preference_update",
            "agent_count": len(agent_indices),
        })

    def update_agent_scalars(
        self,
        agent_indices: np.ndarray,
        scalar_updates: Dict[str, np.ndarray],
    ) -> None:
        """
        Batch update agent scalar values.

        Args:
            agent_indices: Shape (batch_size,) - indices to update
            scalar_updates: Dict mapping scalar name to new values
        """
        scalar_map = {
            "engagement_level": 0,
            "certainty": 1,
            "influence_susceptibility": 2,
            "information_exposure": 3,
            "commitment_strength": 4,
            "network_centrality": 5,
            "echo_chamber_score": 6,
        }

        for name, values in scalar_updates.items():
            if name in scalar_map:
                col = scalar_map[name]
                self.scalar_states[agent_indices, col] = np.clip(values, 0, 1)

    def commit_agents(
        self,
        agent_indices: np.ndarray,
        choices: np.ndarray,
        strengths: np.ndarray,
    ) -> None:
        """
        Record agent commitments to specific choices.

        Args:
            agent_indices: Shape (batch_size,)
            choices: Shape (batch_size,) - choice indices
            strengths: Shape (batch_size,) - commitment strengths
        """
        self.committed_choices[agent_indices] = choices
        self.scalar_states[agent_indices, 4] = strengths

    def record_actions(
        self,
        agent_indices: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
    ) -> None:
        """
        Record actions and rewards in circular buffer.

        Args:
            agent_indices: Shape (batch_size,)
            actions: Shape (batch_size,) - action indices
            rewards: Shape (batch_size,) - received rewards
        """
        # Shift buffer left and add new entries
        self.recent_actions_buffer[agent_indices, :-1] = \
            self.recent_actions_buffer[agent_indices, 1:]
        self.recent_actions_buffer[agent_indices, -1] = actions

        self.recent_rewards_buffer[agent_indices, :-1] = \
            self.recent_rewards_buffer[agent_indices, 1:]
        self.recent_rewards_buffer[agent_indices, -1] = rewards

    def advance_time_step(self) -> None:
        """Advance global time step."""
        self.global_state.time_step += 1

        # Check if checkpoint needed
        if self.global_state.time_step % self.checkpoint_interval == 0:
            self._create_checkpoint()

        # Notify observers
        self._notify_observers("time_step_advanced", self.global_state.time_step)

    def apply_global_event(self, event: Dict[str, Any]) -> None:
        """
        Apply an external event to global state.

        Args:
            event: Event data including type, magnitude, affected indicators
        """
        event_type = event.get("type")
        magnitude = event.get("magnitude", 1.0)

        # Update economic indicators
        if "economic_impact" in event:
            for indicator, change in event["economic_impact"].items():
                if indicator in self.global_state.economic_indicators:
                    current = self.global_state.economic_indicators[indicator]
                    self.global_state.economic_indicators[indicator] = current + (change * magnitude)

        # Update political state
        if "political_impact" in event:
            for key, value in event["political_impact"].items():
                if key in self.global_state.political_state:
                    if isinstance(value, dict) and isinstance(self.global_state.political_state[key], dict):
                        for k, v in value.items():
                            self.global_state.political_state[key][k] = v * magnitude
                    else:
                        self.global_state.political_state[key] = value * magnitude

        # Update social indicators
        if "social_impact" in event:
            for indicator, change in event["social_impact"].items():
                if indicator in self.global_state.social_indicators:
                    current = self.global_state.social_indicators[indicator]
                    self.global_state.social_indicators[indicator] = current + (change * magnitude)

        # Add to active events
        event["applied_at_step"] = self.global_state.time_step
        self.global_state.active_events.append(event)

        # Notify observers
        self._notify_observers("event_applied", event)

    def compute_region_aggregates(self) -> Dict[str, Dict[str, float]]:
        """
        Compute aggregate statistics by region.

        Returns:
            Dict mapping region_id to aggregate statistics
        """
        aggregates = {}

        for region_id, indices in self.region_agent_indices.items():
            if not indices:
                continue

            indices_arr = np.array(indices)
            region_prefs = self.preferences_matrix[indices_arr]
            region_scalars = self.scalar_states[indices_arr]

            aggregates[region_id] = {
                "mean_preferences": region_prefs.mean(axis=0).tolist(),
                "preference_variance": region_prefs.var(axis=0).tolist(),
                "mean_engagement": float(region_scalars[:, 0].mean()),
                "mean_certainty": float(region_scalars[:, 1].mean()),
                "committed_count": int((self.committed_choices[indices_arr] >= 0).sum()),
                "agent_count": len(indices),
            }

        return aggregates

    def compute_demographic_aggregates(
        self,
        demographic_key: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Compute aggregate statistics by demographic group.

        Args:
            demographic_key: Demographic category (e.g., "age_group", "income_level")

        Returns:
            Dict mapping demographic value to aggregate statistics
        """
        if demographic_key not in self.demographic_indices:
            return {}

        aggregates = {}

        for demo_value, indices in self.demographic_indices[demographic_key].items():
            if not indices:
                continue

            indices_arr = np.array(indices)
            demo_prefs = self.preferences_matrix[indices_arr]
            demo_scalars = self.scalar_states[indices_arr]

            aggregates[demo_value] = {
                "mean_preferences": demo_prefs.mean(axis=0).tolist(),
                "preference_variance": demo_prefs.var(axis=0).tolist(),
                "mean_engagement": float(demo_scalars[:, 0].mean()),
                "mean_certainty": float(demo_scalars[:, 1].mean()),
                "committed_count": int((self.committed_choices[indices_arr] >= 0).sum()),
                "agent_count": len(indices),
            }

        return aggregates

    def compute_global_aggregates(self) -> Dict[str, Any]:
        """
        Compute overall simulation statistics.

        Returns:
            Dict of global aggregate statistics
        """
        # Choice distribution
        committed_mask = self.committed_choices >= 0
        committed_count = committed_mask.sum()

        choice_dist = {}
        if committed_count > 0:
            unique, counts = np.unique(
                self.committed_choices[committed_mask],
                return_counts=True
            )
            for choice, count in zip(unique, counts):
                choice_dist[int(choice)] = int(count) / int(committed_count)

        # Preference distribution (even for uncommitted)
        mean_prefs = self.preferences_matrix.mean(axis=0)
        std_prefs = self.preferences_matrix.std(axis=0)

        aggregates = {
            "total_agents": self.agent_count,
            "committed_agents": int(committed_count),
            "uncommitted_agents": self.agent_count - int(committed_count),
            "commitment_rate": float(committed_count) / self.agent_count if self.agent_count > 0 else 0,
            "choice_distribution": choice_dist,
            "mean_preferences": mean_prefs.tolist(),
            "preference_std": std_prefs.tolist(),
            "mean_engagement": float(self.scalar_states[:, 0].mean()),
            "mean_certainty": float(self.scalar_states[:, 1].mean()),
            "mean_echo_chamber": float(self.scalar_states[:, 6].mean()),
        }

        # Store in global state
        self.global_state.aggregate_stats = aggregates

        return aggregates

    def _create_checkpoint(self) -> None:
        """Create a state checkpoint for potential rollback."""
        checkpoint = (
            self.global_state.time_step,
            self.global_state.copy(),
            self.preferences_matrix.copy(),
            self.issue_priorities_matrix.copy(),
            self.scalar_states.copy(),
        )

        self.checkpoints.append(checkpoint)

        # Remove old checkpoints if exceeding limit
        while len(self.checkpoints) > self.max_checkpoints:
            self.checkpoints.pop(0)

        logger.debug(f"Created checkpoint at step {self.global_state.time_step}")

    def rollback(self, target_step: Optional[int] = None) -> bool:
        """
        Rollback to a previous checkpoint.

        Args:
            target_step: Target time step (default: previous checkpoint)

        Returns:
            True if rollback successful
        """
        if not self.checkpoints:
            logger.warning("No checkpoints available for rollback")
            return False

        # Find appropriate checkpoint
        checkpoint = None
        if target_step is None:
            checkpoint = self.checkpoints[-1]
        else:
            for cp in reversed(self.checkpoints):
                if cp[0] <= target_step:
                    checkpoint = cp
                    break

        if checkpoint is None:
            logger.warning(f"No checkpoint found for step {target_step}")
            return False

        # Restore state
        step, global_state, prefs, issues, scalars = checkpoint
        self.global_state = global_state.copy()
        self.preferences_matrix = prefs.copy()
        self.issue_priorities_matrix = issues.copy()
        self.scalar_states = scalars.copy()

        logger.info(f"Rolled back to step {step}")
        self._notify_observers("rollback", step)

        return True

    def add_observer(self, callback: Callable[[str, Any], None]) -> None:
        """Add state change observer."""
        self.observers.append(callback)

    def _notify_observers(self, event_type: str, data: Any) -> None:
        """Notify all observers of state change."""
        for observer in self.observers:
            try:
                observer(event_type, data)
            except Exception as e:
                logger.error(f"Observer notification failed: {e}")

    async def persist_to_database(self, db: AsyncSession) -> None:
        """
        Persist current state to database.
        Called periodically during long simulations.
        """
        from app.models.agent import SimulationAgent

        # Batch update agents
        batch_size = 1000
        for batch_start in range(0, self.agent_count, batch_size):
            batch_end = min(batch_start + batch_size, self.agent_count)

            for i in range(batch_start, batch_end):
                agent_id = self.agent_ids[i]

                # Reconstruct state vector dict
                state_vector = {
                    "political_preference": {
                        f"choice_{j}": float(self.preferences_matrix[i, j])
                        for j in range(self.preference_dimensions)
                        if self.preferences_matrix[i, j] > 0.001
                    },
                    "issue_priorities": {
                        f"issue_{j}": float(self.issue_priorities_matrix[i, j])
                        for j in range(self.issue_dimensions)
                        if self.issue_priorities_matrix[i, j] > 0.001
                    },
                    "engagement_level": float(self.scalar_states[i, 0]),
                    "certainty": float(self.scalar_states[i, 1]),
                    "influence_susceptibility": float(self.scalar_states[i, 2]),
                    "information_exposure": float(self.scalar_states[i, 3]),
                }

                # Update in database
                await db.execute(
                    update(SimulationAgent)
                    .where(SimulationAgent.id == agent_id)
                    .values(
                        state_vector=state_vector,
                        commitment_strength=float(self.scalar_states[i, 4]),
                        committed_action=str(self.committed_choices[i]) if self.committed_choices[i] >= 0 else None,
                    )
                )

            await db.flush()

        await db.commit()
        logger.info(f"Persisted state for {self.agent_count} agents")

    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state for logging/display."""
        return {
            "time_step": self.global_state.time_step,
            "agent_count": self.agent_count,
            "committed_agents": int((self.committed_choices >= 0).sum()),
            "checkpoint_count": len(self.checkpoints),
            "active_events": len(self.global_state.active_events),
            "economic_indicators": self.global_state.economic_indicators,
            "aggregate_stats": self.global_state.aggregate_stats,
        }
