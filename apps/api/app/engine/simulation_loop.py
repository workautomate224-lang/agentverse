"""
Simulation Loop for Predictive Simulation

Main orchestrator for running multi-agent simulations.
Handles step execution, event scheduling, and result collection.
Optimized for 10,000+ agent simulations.
"""

import asyncio
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple, AsyncGenerator
from uuid import UUID
import time
import logging
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.state_manager import StateManager, GlobalState
from app.engine.behavioral_model import BehavioralModel, create_default_behavioral_params
from app.engine.action_space import (
    ActionSpace,
    DiscreteActionSpace,
    RewardFunction,
    ActionType,
)

logger = logging.getLogger(__name__)


class SimulationStatus(str, Enum):
    """Simulation execution status."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SimulationConfig:
    """Configuration for simulation execution."""

    # Time configuration
    total_steps: int = 100
    steps_per_day: int = 1  # Simulation steps per simulated day
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Batch processing
    batch_size: int = 1000
    parallel_batches: int = 4

    # Decision parameters
    decision_temperature: float = 1.0  # Softmax temperature
    commitment_threshold: float = 0.7  # Certainty needed to commit

    # Event parameters
    event_probability_per_step: float = 0.05
    event_decay_rate: float = 0.9

    # Social network
    influence_radius: int = 5  # Network hops for influence
    influence_decay: float = 0.5  # Decay per hop

    # Checkpoint and persistence
    checkpoint_interval: int = 10
    persist_interval: int = 50

    # Monte Carlo
    num_monte_carlo_runs: int = 1

    # Logging
    log_interval: int = 10
    verbose: bool = False


@dataclass
class StepResult:
    """Result of a single simulation step."""

    step: int
    timestamp: datetime
    actions_taken: int
    commitments_made: int
    state_changes: int
    events_applied: List[Dict[str, Any]]
    aggregate_distribution: Dict[str, float]
    computation_time_ms: float


@dataclass
class SimulationResult:
    """Complete simulation results."""

    status: SimulationStatus
    total_steps: int
    start_time: datetime
    end_time: datetime
    computation_time_seconds: float

    # Final predictions
    final_distribution: Dict[str, float]
    confidence_intervals: Dict[str, Tuple[float, float]]

    # Regional breakdown
    regional_results: Dict[str, Dict[str, float]]

    # Demographic breakdown
    demographic_results: Dict[str, Dict[str, Dict[str, float]]]

    # Key metrics
    commitment_rate: float
    convergence_step: Optional[int]
    stability_score: float

    # Monte Carlo results (if multiple runs)
    monte_carlo_distributions: Optional[List[Dict[str, float]]] = None
    monte_carlo_mean: Optional[Dict[str, float]] = None
    monte_carlo_std: Optional[Dict[str, float]] = None

    # History
    step_history: List[StepResult] = field(default_factory=list)
    distribution_history: List[Dict[str, float]] = field(default_factory=list)


class SimulationLoop:
    """
    Main simulation loop orchestrator.
    Manages step-by-step execution, agent decisions, and result collection.
    """

    def __init__(
        self,
        config: SimulationConfig,
        state_manager: StateManager,
        behavioral_model: BehavioralModel,
        action_space: DiscreteActionSpace,
        reward_function: Optional[RewardFunction] = None,
    ):
        """
        Initialize simulation loop.

        Args:
            config: Simulation configuration
            state_manager: State management instance
            behavioral_model: Behavioral economics model
            action_space: Action space for agent decisions
            reward_function: Optional reward function
        """
        self.config = config
        self.state_manager = state_manager
        self.behavioral_model = behavioral_model
        self.action_space = action_space
        self.reward_function = reward_function or RewardFunction()

        # Execution state
        self.status = SimulationStatus.PENDING
        self.current_step = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # History tracking
        self.step_results: List[StepResult] = []
        self.distribution_history: List[Dict[str, float]] = []

        # Event queue
        self.scheduled_events: List[Tuple[int, Dict[str, Any]]] = []

        # Callbacks
        self.progress_callbacks: List[Callable[[int, int, Dict[str, Any]], None]] = []
        self.step_callbacks: List[Callable[[StepResult], None]] = []

        # Cancellation flag
        self._cancelled = False

        # Performance metrics
        self.total_computation_time = 0.0

    def add_progress_callback(
        self,
        callback: Callable[[int, int, Dict[str, Any]], None]
    ) -> None:
        """Add progress callback (current_step, total_steps, data)."""
        self.progress_callbacks.append(callback)

    def add_step_callback(self, callback: Callable[[StepResult], None]) -> None:
        """Add step completion callback."""
        self.step_callbacks.append(callback)

    def schedule_event(self, step: int, event: Dict[str, Any]) -> None:
        """Schedule an external event at a specific step."""
        self.scheduled_events.append((step, event))
        self.scheduled_events.sort(key=lambda x: x[0])

    def cancel(self) -> None:
        """Cancel the running simulation."""
        self._cancelled = True
        self.status = SimulationStatus.CANCELLED

    async def run(
        self,
        db: Optional[AsyncSession] = None,
    ) -> SimulationResult:
        """
        Run the complete simulation.

        Args:
            db: Optional database session for persistence

        Returns:
            Complete simulation results
        """
        self.status = SimulationStatus.INITIALIZING
        self.start_time = datetime.utcnow()
        self._cancelled = False

        try:
            # Initialize simulation date
            current_date = self.config.start_date or datetime.utcnow()

            self.status = SimulationStatus.RUNNING
            logger.info(f"Starting simulation with {self.state_manager.agent_count} agents")

            # Main simulation loop
            for step in range(self.config.total_steps):
                if self._cancelled:
                    break

                self.current_step = step
                step_start = time.time()

                # Execute single step
                step_result = await self._execute_step(step, current_date)
                self.step_results.append(step_result)

                # Store distribution history
                self.distribution_history.append(step_result.aggregate_distribution.copy())

                # Advance simulation date
                if self.config.steps_per_day > 0:
                    current_date += timedelta(days=1.0 / self.config.steps_per_day)

                # Callbacks
                self._notify_progress(step + 1, self.config.total_steps)
                self._notify_step_complete(step_result)

                # Periodic persistence
                if db and step > 0 and step % self.config.persist_interval == 0:
                    await self.state_manager.persist_to_database(db)

                # Logging
                if self.config.verbose and step % self.config.log_interval == 0:
                    logger.info(
                        f"Step {step}/{self.config.total_steps} - "
                        f"Commitments: {step_result.commitments_made} - "
                        f"Time: {step_result.computation_time_ms:.1f}ms"
                    )

                step_time = time.time() - step_start
                self.total_computation_time += step_time

            # Finalize
            self.end_time = datetime.utcnow()
            self.status = SimulationStatus.COMPLETED if not self._cancelled else SimulationStatus.CANCELLED

            # Build final result
            result = self._build_result()

            # Final persistence
            if db:
                await self.state_manager.persist_to_database(db)

            logger.info(f"Simulation completed in {self.total_computation_time:.2f}s")
            return result

        except Exception as e:
            self.status = SimulationStatus.FAILED
            self.end_time = datetime.utcnow()
            logger.error(f"Simulation failed: {e}")
            raise

    async def _execute_step(
        self,
        step: int,
        current_date: datetime,
    ) -> StepResult:
        """
        Execute a single simulation step.

        Args:
            step: Current step number
            current_date: Simulated date

        Returns:
            Step execution result
        """
        step_start = time.time()
        events_applied = []

        # Apply scheduled events
        while self.scheduled_events and self.scheduled_events[0][0] <= step:
            _, event = self.scheduled_events.pop(0)
            self.state_manager.apply_global_event(event)
            events_applied.append(event)

        # Random event generation
        if np.random.random() < self.config.event_probability_per_step:
            random_event = self._generate_random_event(step)
            if random_event:
                self.state_manager.apply_global_event(random_event)
                events_applied.append(random_event)

        # Decay active events
        self._decay_events()

        # Get agent states for batch processing
        preferences, issues, scalars = self.state_manager.get_batch_states()

        # Build decision context
        context = self._build_decision_context(step)

        # Compute base utilities (rational choice)
        base_utilities = self._compute_base_utilities(preferences)

        # Build behavioral parameters from scalars
        behavioral_params = self._build_behavioral_params(scalars)

        # Apply behavioral model
        adjusted_utilities = self.behavioral_model.compute_decision_utilities(
            base_utilities=base_utilities,
            behavioral_params=behavioral_params,
            context=context,
        )

        # Make decisions
        actions, action_probs = self.behavioral_model.make_decisions(
            utilities=adjusted_utilities,
            temperature=self.config.decision_temperature,
        )

        # Process actions and update states
        actions_taken, commitments_made, state_changes = await self._process_actions(
            actions,
            action_probs,
            step,
        )

        # Update aggregate statistics
        self.state_manager.compute_global_aggregates()

        # Advance time
        self.state_manager.advance_time_step()

        step_time = (time.time() - step_start) * 1000  # milliseconds

        return StepResult(
            step=step,
            timestamp=current_date,
            actions_taken=actions_taken,
            commitments_made=commitments_made,
            state_changes=state_changes,
            events_applied=events_applied,
            aggregate_distribution=self.state_manager.global_state.aggregate_stats.get(
                "choice_distribution", {}
            ),
            computation_time_ms=step_time,
        )

    def _compute_base_utilities(self, preferences: np.ndarray) -> np.ndarray:
        """
        Compute base utilities from preferences.
        These represent "rational" expected utilities before behavioral adjustments.

        Args:
            preferences: Shape (num_agents, num_options)

        Returns:
            Base utility matrix
        """
        # For voting: utility is roughly proportional to preference strength
        # Add small random variation to break ties
        noise = np.random.normal(0, 0.01, preferences.shape)
        return preferences + noise

    def _build_behavioral_params(self, scalars: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Build behavioral parameter arrays from scalar state matrix.

        Args:
            scalars: Shape (num_agents, 7)

        Returns:
            Dict of behavioral parameters
        """
        num_agents = scalars.shape[0]

        # Map scalar columns to behavioral parameters
        # Scalars: [engagement, certainty, susceptibility, info_exposure, commitment, centrality, echo_chamber]

        # Derive behavioral params from scalar states
        engagement = scalars[:, 0]
        certainty = scalars[:, 1]
        susceptibility = scalars[:, 2]
        echo_chamber = scalars[:, 6]

        return {
            "status_quo_strength": certainty * 0.4,  # More certain = stronger status quo
            "bandwagon_susceptibility": susceptibility * 0.5,
            "social_proof_weight": susceptibility * 0.6,
            "bounded_rationality": 1 - (certainty * 0.5),  # Less certain = more bounded
            "confirmation_bias": echo_chamber * 0.6,  # Echo chamber increases confirmation
            "anchoring_strength": certainty * 0.5,
            "loss_aversion_lambda": np.full(num_agents, 2.25),
            "reference_point": np.zeros(num_agents),
        }

    def _build_decision_context(self, step: int) -> Dict[str, np.ndarray]:
        """
        Build context information for decision-making.

        Args:
            step: Current step

        Returns:
            Context dictionary
        """
        context = {}

        # Current choices (committed)
        context["current_choices"] = self.state_manager.committed_choices

        # Population distribution
        aggregates = self.state_manager.global_state.aggregate_stats
        if "mean_preferences" in aggregates:
            context["population_distribution"] = np.array(aggregates["mean_preferences"])
        else:
            # Use uniform
            num_options = self.state_manager.preferences_matrix.shape[1]
            context["population_distribution"] = np.ones(num_options) / num_options

        # Peer choices (from social network)
        # Simplified: sample random peers for each agent
        num_agents = self.state_manager.agent_count
        num_peers = min(10, num_agents - 1)
        peer_choices = np.full((num_agents, num_peers), -1, dtype=np.int32)

        for i in range(num_agents):
            # Get peer indices (excluding self)
            peer_candidates = np.concatenate([np.arange(i), np.arange(i+1, num_agents)])
            if len(peer_candidates) > 0:
                peer_indices = np.random.choice(
                    peer_candidates,
                    size=min(num_peers, len(peer_candidates)),
                    replace=False
                )
                peer_choices[i, :len(peer_indices)] = self.state_manager.committed_choices[peer_indices]

        context["peer_choices"] = peer_choices
        context["social_weights"] = np.ones((num_agents, num_peers)) * 0.1

        # Framing (from active events)
        num_options = self.state_manager.preferences_matrix.shape[1]
        framing = np.zeros(num_options)

        for event in self.state_manager.global_state.active_events:
            if "framing" in event:
                for opt_idx, valence in event["framing"].items():
                    if int(opt_idx) < num_options:
                        framing[int(opt_idx)] += valence * event.get("current_magnitude", 1.0)

        context["framing_valence"] = np.clip(framing, -1, 1)

        return context

    async def _process_actions(
        self,
        actions: np.ndarray,
        action_probs: np.ndarray,
        step: int,
    ) -> Tuple[int, int, int]:
        """
        Process agent actions and update states.

        Args:
            actions: Shape (num_agents,) - chosen action indices
            action_probs: Shape (num_agents, num_actions) - action probabilities
            step: Current step

        Returns:
            Tuple of (actions_taken, commitments_made, state_changes)
        """
        actions_taken = 0
        commitments_made = 0
        state_changes = 0

        # Process in batches for efficiency
        batch_size = self.config.batch_size
        num_agents = len(actions)

        for batch_start in range(0, num_agents, batch_size):
            batch_end = min(batch_start + batch_size, num_agents)
            batch_indices = np.arange(batch_start, batch_end)
            batch_actions = actions[batch_start:batch_end]
            batch_probs = action_probs[batch_start:batch_end]

            # Update preferences based on action probabilities
            # Actions influence beliefs (commitment reinforces)
            current_prefs = self.state_manager.preferences_matrix[batch_indices]

            # Learning rate based on certainty
            certainty = self.state_manager.scalar_states[batch_indices, 1]
            learning_rate = 0.1 * (1 - certainty)  # Less learning when more certain

            # Update preferences toward chosen action
            for i, (idx, action) in enumerate(zip(batch_indices, batch_actions)):
                action_def = self.action_space.get_action_by_index(int(action))
                if action_def is None:
                    continue

                actions_taken += 1

                if action_def.action_type == ActionType.VOTE:
                    # Voting reinforces preference
                    choice_idx = action  # Assuming vote action index = choice index
                    if choice_idx < current_prefs.shape[1]:
                        # Reinforce chosen option
                        new_prefs = current_prefs[i].copy()
                        new_prefs[choice_idx] += learning_rate[i] * 0.1

                        # Check commitment threshold
                        max_pref = new_prefs.max()
                        current_commitment = self.state_manager.scalar_states[idx, 4]

                        if max_pref > self.config.commitment_threshold:
                            # Make commitment
                            if self.state_manager.committed_choices[idx] < 0:
                                commitments_made += 1
                            self.state_manager.committed_choices[idx] = choice_idx
                            self.state_manager.scalar_states[idx, 4] = min(
                                current_commitment + 0.1, 1.0
                            )

                        # Update certainty
                        certainty_change = 0.02 * (1 - certainty[i])
                        self.state_manager.scalar_states[idx, 1] = min(
                            certainty[i] + certainty_change, 1.0
                        )

                        state_changes += 1

                elif action_def.action_type == ActionType.ABSTAIN:
                    # Abstain may decrease certainty
                    self.state_manager.scalar_states[idx, 1] *= 0.99

                elif action_def.action_type == ActionType.SWITCH_PREFERENCE:
                    # Uncommit
                    if self.state_manager.committed_choices[idx] >= 0:
                        self.state_manager.committed_choices[idx] = -1
                        self.state_manager.scalar_states[idx, 4] *= 0.5
                        state_changes += 1

            # Normalize updated preferences
            self.state_manager.preferences_matrix[batch_indices] = current_prefs
            row_sums = self.state_manager.preferences_matrix[batch_indices].sum(axis=1, keepdims=True)
            row_sums = np.where(row_sums > 0, row_sums, 1)
            self.state_manager.preferences_matrix[batch_indices] /= row_sums

            # Record actions in buffer
            batch_rewards = np.zeros(len(batch_indices))  # Simplified
            self.state_manager.record_actions(batch_indices, batch_actions, batch_rewards)

        return actions_taken, commitments_made, state_changes

    def _generate_random_event(self, step: int) -> Optional[Dict[str, Any]]:
        """Generate a random external event."""
        event_types = [
            {
                "type": "economic_news",
                "magnitude": np.random.uniform(0.5, 1.5),
                "economic_impact": {
                    "consumer_confidence": np.random.uniform(-0.1, 0.1),
                },
                "framing": {
                    "0": np.random.uniform(-0.2, 0.2),
                    "1": np.random.uniform(-0.2, 0.2),
                },
            },
            {
                "type": "political_scandal",
                "magnitude": np.random.uniform(0.3, 1.0),
                "political_impact": {
                    "party_approval": np.random.uniform(-0.15, -0.05),
                },
                "framing": {
                    str(np.random.randint(0, 3)): -0.3,
                },
            },
            {
                "type": "media_campaign",
                "magnitude": np.random.uniform(0.2, 0.8),
                "framing": {
                    str(np.random.randint(0, 3)): np.random.uniform(0.1, 0.3),
                },
            },
        ]

        # Select random event type
        event = np.random.choice(event_types).copy()
        event["step"] = step

        return event

    def _decay_events(self) -> None:
        """Decay magnitude of active events."""
        active_events = self.state_manager.global_state.active_events
        decayed = []

        for event in active_events:
            magnitude = event.get("current_magnitude", event.get("magnitude", 1.0))
            new_magnitude = magnitude * self.config.event_decay_rate

            if new_magnitude > 0.01:  # Keep if still significant
                event["current_magnitude"] = new_magnitude
                decayed.append(event)

        self.state_manager.global_state.active_events = decayed

    def _build_result(self) -> SimulationResult:
        """Build final simulation result."""
        # Calculate final distribution
        aggregates = self.state_manager.compute_global_aggregates()
        final_dist = aggregates.get("choice_distribution", {})

        # Calculate confidence intervals from distribution history
        confidence_intervals = {}
        if len(self.distribution_history) > 10:
            # Use last 20% of steps for CI calculation
            recent_start = int(len(self.distribution_history) * 0.8)
            recent_dists = self.distribution_history[recent_start:]

            for key in final_dist.keys():
                values = [d.get(key, 0) for d in recent_dists]
                if values:
                    mean_val = np.mean(values)
                    std_val = np.std(values)
                    ci_low = mean_val - 1.96 * std_val
                    ci_high = mean_val + 1.96 * std_val
                    confidence_intervals[str(key)] = (
                        max(0, ci_low),
                        min(1, ci_high)
                    )

        # Regional breakdown
        regional_results = self.state_manager.compute_region_aggregates()

        # Demographic breakdown
        demographic_results = {}
        for demo_key in ["age_group", "income_level", "education", "gender"]:
            demo_agg = self.state_manager.compute_demographic_aggregates(demo_key)
            if demo_agg:
                demographic_results[demo_key] = demo_agg

        # Calculate metrics
        commitment_rate = aggregates.get("commitment_rate", 0)

        # Find convergence step (when distribution stabilizes)
        convergence_step = self._find_convergence_step()

        # Stability score (inverse of recent variance)
        stability_score = self._calculate_stability_score()

        return SimulationResult(
            status=self.status,
            total_steps=self.config.total_steps,
            start_time=self.start_time or datetime.utcnow(),
            end_time=self.end_time or datetime.utcnow(),
            computation_time_seconds=self.total_computation_time,
            final_distribution={str(k): v for k, v in final_dist.items()},
            confidence_intervals=confidence_intervals,
            regional_results=regional_results,
            demographic_results=demographic_results,
            commitment_rate=commitment_rate,
            convergence_step=convergence_step,
            stability_score=stability_score,
            step_history=self.step_results,
            distribution_history=self.distribution_history,
        )

    def _find_convergence_step(self, threshold: float = 0.01) -> Optional[int]:
        """Find step where distribution converged."""
        if len(self.distribution_history) < 10:
            return None

        for i in range(10, len(self.distribution_history)):
            # Check if recent distribution is stable
            recent = self.distribution_history[i-10:i]

            # Calculate variance across recent steps
            all_keys = set()
            for d in recent:
                all_keys.update(d.keys())

            is_stable = True
            for key in all_keys:
                values = [d.get(key, 0) for d in recent]
                if np.std(values) > threshold:
                    is_stable = False
                    break

            if is_stable:
                return i - 10

        return None

    def _calculate_stability_score(self) -> float:
        """Calculate distribution stability score."""
        if len(self.distribution_history) < 5:
            return 0.0

        recent = self.distribution_history[-5:]

        all_keys = set()
        for d in recent:
            all_keys.update(d.keys())

        total_variance = 0
        for key in all_keys:
            values = [d.get(key, 0) for d in recent]
            total_variance += np.var(values)

        # Invert and normalize (lower variance = higher stability)
        stability = 1.0 / (1.0 + total_variance * 100)

        return stability

    def _notify_progress(self, current: int, total: int) -> None:
        """Notify progress callbacks."""
        data = {
            "distribution": self.state_manager.global_state.aggregate_stats.get("choice_distribution", {}),
            "commitment_rate": self.state_manager.global_state.aggregate_stats.get("commitment_rate", 0),
        }
        for callback in self.progress_callbacks:
            try:
                callback(current, total, data)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def _notify_step_complete(self, result: StepResult) -> None:
        """Notify step callbacks."""
        for callback in self.step_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Step callback error: {e}")

    async def run_monte_carlo(
        self,
        num_runs: int,
        db: Optional[AsyncSession] = None,
    ) -> SimulationResult:
        """
        Run multiple simulations for Monte Carlo analysis.

        Args:
            num_runs: Number of simulation runs
            db: Optional database session

        Returns:
            Aggregated results with distribution statistics
        """
        all_distributions = []
        all_results = []

        for run in range(num_runs):
            logger.info(f"Monte Carlo run {run + 1}/{num_runs}")

            # Reset state for new run
            # Note: This assumes state can be reset; in practice may need to reinitialize

            # Run simulation
            result = await self.run(db)
            all_results.append(result)
            all_distributions.append(result.final_distribution)

            # Reset for next run
            self.step_results = []
            self.distribution_history = []
            self.current_step = 0

        # Aggregate results
        final_result = all_results[-1]  # Use last run as base

        # Calculate Monte Carlo statistics
        all_keys = set()
        for d in all_distributions:
            all_keys.update(d.keys())

        mc_mean = {}
        mc_std = {}
        for key in all_keys:
            values = [d.get(key, 0) for d in all_distributions]
            mc_mean[key] = float(np.mean(values))
            mc_std[key] = float(np.std(values))

        final_result.monte_carlo_distributions = all_distributions
        final_result.monte_carlo_mean = mc_mean
        final_result.monte_carlo_std = mc_std

        # Update confidence intervals with Monte Carlo data
        for key in all_keys:
            mean_val = mc_mean[key]
            std_val = mc_std[key]
            ci_low = mean_val - 1.96 * std_val
            ci_high = mean_val + 1.96 * std_val
            final_result.confidence_intervals[key] = (max(0, ci_low), min(1, ci_high))

        return final_result


async def create_simulation_loop(
    scenario_config: Dict[str, Any],
    agent_data: List[Dict[str, Any]],
    action_space_config: Optional[Dict[str, Any]] = None,
) -> SimulationLoop:
    """
    Factory function to create a configured simulation loop.

    Args:
        scenario_config: Scenario configuration
        agent_data: List of agent data dictionaries
        action_space_config: Optional action space configuration

    Returns:
        Configured SimulationLoop
    """
    # Create configuration
    config = SimulationConfig(
        total_steps=scenario_config.get("total_steps", 100),
        steps_per_day=scenario_config.get("steps_per_day", 1),
        batch_size=scenario_config.get("batch_size", 1000),
        decision_temperature=scenario_config.get("temperature", 1.0),
        commitment_threshold=scenario_config.get("commitment_threshold", 0.7),
        verbose=scenario_config.get("verbose", False),
    )

    # Create state manager
    num_agents = len(agent_data)
    pref_dim = scenario_config.get("preference_dimensions", 5)
    issue_dim = scenario_config.get("issue_dimensions", 5)

    state_manager = StateManager(
        max_agents=num_agents,
        preference_dimensions=pref_dim,
        issue_dimensions=issue_dim,
    )

    # Initialize state from agent data
    agent_ids = [a["id"] for a in agent_data]
    initial_prefs = np.array([a.get("preferences", np.zeros(pref_dim)) for a in agent_data])
    initial_issues = np.array([a.get("issue_priorities", np.zeros(issue_dim)) for a in agent_data])
    initial_scalars = np.array([
        [
            a.get("engagement_level", 0.5),
            a.get("certainty", 0.5),
            a.get("influence_susceptibility", 0.5),
            a.get("information_exposure", 0.5),
            a.get("commitment_strength", 0.0),
            a.get("network_centrality", 0.0),
            a.get("echo_chamber_score", 0.0),
        ]
        for a in agent_data
    ])

    state_manager.initialize(
        agent_ids=agent_ids,
        initial_preferences=initial_prefs,
        initial_issue_priorities=initial_issues,
        initial_scalar_states=initial_scalars,
    )

    # Create behavioral model
    behavioral_model = BehavioralModel()

    # Create action space
    if action_space_config:
        action_space = ActionSpace.create_from_config(action_space_config)
    else:
        # Default election action space
        parties = scenario_config.get("parties", ["Party A", "Party B", "Party C"])
        action_space = ActionSpace.create_election_space(parties)

    # Create simulation loop
    loop = SimulationLoop(
        config=config,
        state_manager=state_manager,
        behavioral_model=behavioral_model,
        action_space=action_space,
    )

    return loop
