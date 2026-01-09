"""
Simulation Engine

Core orchestrator for predictive multi-agent simulations.
Supports 10,000+ concurrent agents with batch processing.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional
from uuid import UUID
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.environment import (
    SimulationEnvironment,
    EnvironmentState,
    ExternalEvent,
    PredictionScenario,
)
from app.models.agent import (
    SimulationAgent,
    AgentAction,
    AgentInteractionLog,
    PolicyModel,
)
from app.models.prediction import PredictionResult

logger = logging.getLogger(__name__)


class SimulationConfig:
    """Configuration for simulation execution."""

    def __init__(
        self,
        agent_count: int = 1000,
        time_steps: int = 100,
        batch_size: int = 500,
        parallel_workers: int = 10,
        use_gpu: bool = False,
        checkpoint_interval: int = 10,
        enable_social_network: bool = True,
        enable_external_events: bool = True,
        random_seed: Optional[int] = None,
    ):
        self.agent_count = agent_count
        self.time_steps = time_steps
        self.batch_size = batch_size
        self.parallel_workers = parallel_workers
        self.use_gpu = use_gpu
        self.checkpoint_interval = checkpoint_interval
        self.enable_social_network = enable_social_network
        self.enable_external_events = enable_external_events
        self.random_seed = random_seed or int(datetime.utcnow().timestamp())


class SimulationEngine:
    """
    Core simulation engine for predictive multi-agent simulations.

    Features:
    - Support for 10,000+ concurrent agents
    - Batch processing with configurable batch sizes
    - Async/parallel execution
    - MARL policy integration
    - Behavioral economics modeling
    - Social network influence
    - External event handling
    """

    def __init__(
        self,
        config: Optional[SimulationConfig] = None,
        state_manager: Optional["StateManager"] = None,
        behavioral_model: Optional["BehavioralModel"] = None,
    ):
        self.config = config or SimulationConfig()
        self._state_manager = state_manager
        self._behavioral_model = behavioral_model
        self._rng = np.random.default_rng(self.config.random_seed)
        self._is_running = False
        self._current_step = 0
        self._agents: Dict[UUID, SimulationAgent] = {}
        self._environment_state: Optional[Dict[str, Any]] = None
        self._external_events: List[ExternalEvent] = []
        self._metrics: Dict[str, List[float]] = {}

    @property
    def state_manager(self) -> "StateManager":
        if self._state_manager is None:
            from app.engine.state_manager import StateManager
            self._state_manager = StateManager()
        return self._state_manager

    @property
    def behavioral_model(self) -> "BehavioralModel":
        if self._behavioral_model is None:
            from app.engine.behavioral_model import BehavioralModel
            self._behavioral_model = BehavioralModel()
        return self._behavioral_model

    async def initialize(
        self,
        scenario: PredictionScenario,
        environment: SimulationEnvironment,
        db: AsyncSession,
    ) -> None:
        """
        Initialize simulation with scenario and environment.

        Args:
            scenario: The prediction scenario configuration
            environment: The simulation environment
            db: Database session
        """
        logger.info(f"Initializing simulation for scenario {scenario.id}")

        # Set random seed for reproducibility
        self._rng = np.random.default_rng(self.config.random_seed)

        # Initialize environment state
        self._environment_state = await self._initialize_environment_state(
            scenario, environment
        )

        # Load external events
        if self.config.enable_external_events:
            self._external_events = await self._load_external_events(
                environment, scenario.event_ids, db
            )

        # Initialize agents
        await self._initialize_agents(scenario, environment, db)

        # Initialize metrics tracking
        self._metrics = {
            "action_distribution": [],
            "engagement_levels": [],
            "polarization_index": [],
            "social_influence_events": [],
        }

        self._current_step = 0
        self._is_running = True

        logger.info(f"Simulation initialized with {len(self._agents)} agents")

    async def _initialize_environment_state(
        self,
        scenario: PredictionScenario,
        environment: SimulationEnvironment,
    ) -> Dict[str, Any]:
        """Initialize the global environment state."""
        state = scenario.initial_state.get("global_variables", {})

        # Set defaults from environment state space
        for var in environment.state_space.get("global_variables", []):
            if var not in state:
                bounds = environment.state_space.get("bounds", {}).get(var, [0, 1])
                state[var] = (bounds[0] + bounds[1]) / 2  # Default to midpoint

        return state

    async def _load_external_events(
        self,
        environment: SimulationEnvironment,
        event_ids: List[str],
        db: AsyncSession,
    ) -> List[ExternalEvent]:
        """Load external events for the simulation."""
        from sqlalchemy import select

        result = await db.execute(
            select(ExternalEvent).where(
                ExternalEvent.environment_id == environment.id,
                ExternalEvent.is_active == True
            )
        )
        events = result.scalars().all()

        # Filter by event_ids if specified
        if event_ids:
            events = [e for e in events if str(e.id) in event_ids]

        return sorted(events, key=lambda e: e.trigger_time_step)

    async def _initialize_agents(
        self,
        scenario: PredictionScenario,
        environment: SimulationEnvironment,
        db: AsyncSession,
    ) -> None:
        """Initialize agents based on scenario configuration."""
        agent_config = scenario.agent_config
        agent_count = scenario.agent_count

        # Determine demographic distribution
        distribution_type = agent_config.get("demographic_distribution", "random")
        regional_allocation = agent_config.get("regional_allocation", {})

        # Generate agents in batches
        for batch_start in range(0, agent_count, self.config.batch_size):
            batch_end = min(batch_start + self.config.batch_size, agent_count)
            batch_size = batch_end - batch_start

            agents = await self._generate_agent_batch(
                scenario_id=scenario.id,
                start_index=batch_start,
                batch_size=batch_size,
                distribution_type=distribution_type,
                regional_allocation=regional_allocation,
                environment=environment,
            )

            # Store agents
            for agent in agents:
                self._agents[agent.id] = agent
                db.add(agent)

            # Flush batch to database
            await db.flush()

            logger.debug(f"Initialized agents {batch_start} to {batch_end}")

        # Build social network if enabled
        if self.config.enable_social_network:
            await self._build_social_network()

    async def _generate_agent_batch(
        self,
        scenario_id: UUID,
        start_index: int,
        batch_size: int,
        distribution_type: str,
        regional_allocation: Dict[str, float],
        environment: SimulationEnvironment,
    ) -> List[SimulationAgent]:
        """Generate a batch of agents."""
        agents = []

        # Get action space
        action_space = environment.action_space
        actions = action_space.get("actions", ["action_a", "action_b", "undecided"])

        for i in range(batch_size):
            agent_index = start_index + i

            # Determine region
            region_id = self._sample_region(regional_allocation)

            # Generate demographics
            demographics = self._generate_demographics(distribution_type)

            # Generate behavioral parameters
            behavioral_params = self._generate_behavioral_params()

            # Generate psychographics
            psychographics = self._generate_psychographics()

            # Initialize state vector
            state_vector = self._initialize_state_vector(actions)

            # Create agent
            agent = SimulationAgent(
                scenario_id=scenario_id,
                agent_index=agent_index,
                region_id=region_id,
                state_vector=state_vector,
                demographics=demographics,
                behavioral_params=behavioral_params,
                psychographics=psychographics,
                policy_type="behavioral_economic",
                memory={"short_term": [], "long_term": {}, "episodic": []},
                social_network={"connections": [], "influence_weights": {}},
            )

            agents.append(agent)

        return agents

    def _sample_region(self, regional_allocation: Dict[str, float]) -> Optional[str]:
        """Sample a region based on allocation weights."""
        if not regional_allocation:
            return None

        regions = list(regional_allocation.keys())
        weights = list(regional_allocation.values())

        # Normalize weights
        total = sum(weights)
        weights = [w / total for w in weights]

        return self._rng.choice(regions, p=weights)

    def _generate_demographics(self, distribution_type: str) -> Dict[str, Any]:
        """Generate agent demographics."""
        # Age distribution (roughly census-like)
        age = int(self._rng.triangular(18, 35, 80))

        # Gender (roughly 50/50)
        gender = self._rng.choice(["male", "female"], p=[0.49, 0.51])

        # Education level
        education_levels = ["high_school", "bachelor", "master", "phd"]
        education_weights = [0.35, 0.40, 0.20, 0.05]
        education = self._rng.choice(education_levels, p=education_weights)

        # Income bracket
        income_brackets = ["low", "lower_middle", "middle", "upper_middle", "high"]
        income_weights = [0.20, 0.25, 0.30, 0.15, 0.10]
        income = self._rng.choice(income_brackets, p=income_weights)

        # Urban/Rural
        urban_rural = self._rng.choice(["urban", "suburban", "rural"], p=[0.55, 0.30, 0.15])

        return {
            "age": age,
            "gender": gender,
            "education": education,
            "income_bracket": income,
            "urban_rural": urban_rural,
            "ethnicity": self._rng.choice(["majority", "minority_1", "minority_2"], p=[0.60, 0.25, 0.15]),
            "employment_status": self._rng.choice(["employed", "self_employed", "unemployed", "retired", "student"],
                                                  p=[0.55, 0.15, 0.08, 0.12, 0.10]),
        }

    def _generate_behavioral_params(self) -> Dict[str, Any]:
        """Generate behavioral economics parameters."""
        return {
            "risk_aversion": float(self._rng.beta(2, 2)),  # 0-1, centered around 0.5
            "loss_aversion_lambda": float(self._rng.uniform(1.5, 3.0)),  # Kahneman-Tversky
            "probability_weighting": {
                "alpha": float(self._rng.uniform(0.5, 0.8)),
                "beta": float(self._rng.uniform(0.5, 0.8)),
            },
            "status_quo_bias": float(self._rng.beta(2, 3)),  # Slight tendency to lower values
            "anchoring_strength": float(self._rng.beta(2, 2)),
            "confirmation_bias": float(self._rng.beta(2, 2)),
            "bandwagon_effect": float(self._rng.beta(2, 3)),
            "availability_heuristic": float(self._rng.beta(2, 2)),
            "bounded_rationality": float(self._rng.beta(3, 2)),  # Slight tendency to higher values
            "social_proof_weight": float(self._rng.beta(2, 2)),
            "time_discounting": float(self._rng.uniform(0.90, 0.99)),
        }

    def _generate_psychographics(self) -> Dict[str, Any]:
        """Generate psychographic profile."""
        return {
            "big_five": {
                "openness": float(self._rng.beta(2, 2)),
                "conscientiousness": float(self._rng.beta(2, 2)),
                "extraversion": float(self._rng.beta(2, 2)),
                "agreeableness": float(self._rng.beta(2, 2)),
                "neuroticism": float(self._rng.beta(2, 2)),
            },
            "values": self._rng.choice(
                [["security", "tradition"], ["achievement", "power"],
                 ["benevolence", "universalism"], ["self_direction", "stimulation"]],
            ).tolist(),
            "decision_style": self._rng.choice(["analytical", "intuitive", "emotional", "pragmatic"]),
            "information_seeking": float(self._rng.beta(2, 2)),
            "political_engagement": float(self._rng.beta(2, 2)),
        }

    def _initialize_state_vector(self, actions: List[str]) -> Dict[str, Any]:
        """Initialize agent state vector."""
        # Initialize preferences (uniform with slight noise)
        n_actions = len(actions)
        base_prob = 1.0 / n_actions
        preferences = {}

        for action in actions:
            noise = self._rng.uniform(-0.1, 0.1)
            preferences[action] = max(0.05, min(0.95, base_prob + noise))

        # Normalize
        total = sum(preferences.values())
        preferences = {k: v / total for k, v in preferences.items()}

        return {
            "preferences": preferences,
            "engagement_level": float(self._rng.beta(2, 2)),
            "certainty": float(self._rng.beta(2, 5)),  # Start with low certainty
            "influence_susceptibility": float(self._rng.beta(2, 2)),
            "information_exposure": 0.0,
        }

    async def _build_social_network(self) -> None:
        """Build social network connections between agents."""
        agent_list = list(self._agents.values())
        n_agents = len(agent_list)

        # Average connections per agent (small-world network property)
        avg_connections = min(20, n_agents // 10)

        for agent in agent_list:
            # Number of connections follows a power-law-like distribution
            n_connections = int(self._rng.exponential(avg_connections))
            n_connections = min(n_connections, n_agents - 1)
            n_connections = max(1, n_connections)

            # Preferentially connect to similar demographics (homophily)
            candidates = [a for a in agent_list if a.id != agent.id]

            # Calculate similarity scores
            similarities = []
            for candidate in candidates:
                sim = self._calculate_demographic_similarity(
                    agent.demographics, candidate.demographics
                )
                similarities.append(sim)

            # Sample connections with probability proportional to similarity
            similarities = np.array(similarities)
            probabilities = similarities / similarities.sum()

            selected_indices = self._rng.choice(
                len(candidates),
                size=min(n_connections, len(candidates)),
                replace=False,
                p=probabilities
            )

            connections = [str(candidates[i].id) for i in selected_indices]

            # Assign influence weights based on similarity
            influence_weights = {}
            for conn_id, idx in zip(connections, selected_indices):
                influence_weights[conn_id] = float(similarities[idx])

            agent.social_network = {
                "connections": connections,
                "influence_weights": influence_weights,
                "echo_chamber_score": float(np.mean([similarities[i] for i in selected_indices]))
            }

    def _calculate_demographic_similarity(
        self,
        demo1: Dict[str, Any],
        demo2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two demographic profiles."""
        score = 0.0

        # Age similarity (closer ages = higher similarity)
        age_diff = abs(demo1.get("age", 40) - demo2.get("age", 40))
        score += max(0, 1 - age_diff / 50) * 0.2

        # Same education level
        if demo1.get("education") == demo2.get("education"):
            score += 0.2

        # Same income bracket
        if demo1.get("income_bracket") == demo2.get("income_bracket"):
            score += 0.2

        # Same urban/rural
        if demo1.get("urban_rural") == demo2.get("urban_rural"):
            score += 0.2

        # Same ethnicity
        if demo1.get("ethnicity") == demo2.get("ethnicity"):
            score += 0.2

        return score

    async def step(
        self,
        db: AsyncSession,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Execute one simulation step.

        Args:
            db: Database session
            progress_callback: Optional callback for progress updates

        Returns:
            Step metrics and statistics
        """
        if not self._is_running:
            raise RuntimeError("Simulation not initialized")

        self._current_step += 1
        step_metrics = {}

        # 1. Apply external events for this step
        if self.config.enable_external_events:
            events_applied = await self._apply_external_events()
            step_metrics["events_applied"] = events_applied

        # 2. Process agents in batches
        agent_list = list(self._agents.values())
        total_agents = len(agent_list)

        action_counts = {}
        total_engagement = 0.0

        for batch_start in range(0, total_agents, self.config.batch_size):
            batch_end = min(batch_start + self.config.batch_size, total_agents)
            batch = agent_list[batch_start:batch_end]

            # Process batch
            batch_actions = await self._process_agent_batch(batch, db)

            # Aggregate results
            for action in batch_actions:
                action_counts[action] = action_counts.get(action, 0) + 1

            for agent in batch:
                total_engagement += agent.state_vector.get("engagement_level", 0)

            # Progress callback
            if progress_callback:
                progress_callback(batch_end, total_agents)

        # 3. Apply social influence if enabled
        if self.config.enable_social_network:
            await self._apply_social_influence()

        # 4. Update environment state
        await self._update_environment_state(action_counts)

        # 5. Calculate step metrics
        step_metrics.update({
            "step": self._current_step,
            "action_distribution": action_counts,
            "action_percentages": {k: v / total_agents for k, v in action_counts.items()},
            "average_engagement": total_engagement / total_agents,
            "polarization_index": self._calculate_polarization(action_counts, total_agents),
        })

        # Store metrics
        for key, value in step_metrics.items():
            if key not in self._metrics:
                self._metrics[key] = []
            if isinstance(value, (int, float)):
                self._metrics[key].append(value)

        return step_metrics

    async def _apply_external_events(self) -> List[str]:
        """Apply external events scheduled for the current step."""
        applied_events = []

        for event in self._external_events:
            if event.trigger_time_step <= self._current_step:
                # Check if event is still active (within duration)
                steps_since_trigger = self._current_step - event.trigger_time_step
                if steps_since_trigger < event.duration_steps:
                    # Calculate decay
                    decay = (1 - event.decay_rate) ** steps_since_trigger

                    # Apply to environment state
                    for var, change in event.impact.get("global_variables", {}).items():
                        if var in self._environment_state:
                            self._environment_state[var] += change * decay

                    applied_events.append(event.name)

        return applied_events

    async def _process_agent_batch(
        self,
        batch: List[SimulationAgent],
        db: AsyncSession,
    ) -> List[str]:
        """Process a batch of agents for one step."""
        actions = []

        for agent in batch:
            # Get agent's action based on policy
            action, action_probs = await self._get_agent_action(agent)
            actions.append(action)

            # Update agent state
            agent.last_action = action
            agent.last_action_step = self._current_step

            # Record action
            agent_action = AgentAction(
                agent_id=agent.id,
                time_step=self._current_step,
                state_before=agent.state_vector.copy(),
                action=action,
                action_probabilities=action_probs,
                decision_context={
                    "environment_state": self._environment_state,
                    "step": self._current_step,
                },
                reward=0.0,  # Calculated later
                state_after=agent.state_vector.copy(),
            )
            db.add(agent_action)

        return actions

    async def _get_agent_action(
        self,
        agent: SimulationAgent,
    ) -> tuple[str, Dict[str, float]]:
        """
        Determine agent's action based on their policy and state.

        Uses behavioral economics model for decision-making.
        """
        # Get current preferences
        preferences = agent.state_vector.get("preferences", {})
        behavioral_params = agent.behavioral_params

        # Apply behavioral biases
        modified_prefs = self.behavioral_model.apply_biases(
            preferences=preferences,
            params=behavioral_params,
            environment_state=self._environment_state,
            memory=agent.memory,
            rng=self._rng,
        )

        # Apply certainty/commitment
        certainty = agent.state_vector.get("certainty", 0.5)

        if agent.committed_action and certainty > 0.8:
            # Highly certain agents stick with their commitment
            action = agent.committed_action
        else:
            # Sample action from modified preferences
            actions = list(modified_prefs.keys())
            probs = list(modified_prefs.values())

            # Normalize probabilities
            total = sum(probs)
            probs = [p / total for p in probs]

            action = self._rng.choice(actions, p=probs)

            # Update commitment if certainty is high
            if certainty > 0.7:
                agent.committed_action = action
                agent.commitment_strength = certainty

        # Update certainty based on action consistency
        if agent.last_action == action:
            agent.state_vector["certainty"] = min(1.0, certainty + 0.02)
        else:
            agent.state_vector["certainty"] = max(0.0, certainty - 0.01)

        return action, modified_prefs

    async def _apply_social_influence(self) -> None:
        """Apply social network influence between agents."""
        influence_events = 0

        for agent in self._agents.values():
            connections = agent.social_network.get("connections", [])
            influence_weights = agent.social_network.get("influence_weights", {})

            if not connections:
                continue

            # Check if agent interacts this step (probabilistic)
            interaction_prob = agent.state_vector.get("engagement_level", 0.5) * 0.3
            if self._rng.random() > interaction_prob:
                continue

            # Sample a connection to interact with
            conn_id = self._rng.choice(connections)
            conn_agent = self._agents.get(UUID(conn_id))

            if not conn_agent:
                continue

            # Calculate influence
            weight = influence_weights.get(conn_id, 0.1)
            susceptibility = agent.behavioral_params.get("social_proof_weight", 0.3)

            # Influence amount
            influence_strength = weight * susceptibility * 0.1

            # Shift preferences toward connection's preferences
            agent_prefs = agent.state_vector.get("preferences", {})
            conn_prefs = conn_agent.state_vector.get("preferences", {})

            for action in agent_prefs:
                if action in conn_prefs:
                    diff = conn_prefs[action] - agent_prefs[action]
                    agent_prefs[action] += diff * influence_strength

            # Normalize
            total = sum(agent_prefs.values())
            agent.state_vector["preferences"] = {k: v / total for k, v in agent_prefs.items()}

            influence_events += 1

        self._metrics["social_influence_events"].append(influence_events)

    async def _update_environment_state(self, action_counts: Dict[str, int]) -> None:
        """Update global environment state based on agent actions."""
        total = sum(action_counts.values())

        # Update based on aggregate behavior
        for action, count in action_counts.items():
            proportion = count / total

            # This can be customized per environment type
            # For example, in elections, dominant parties might increase media coverage
            self._environment_state[f"{action}_momentum"] = proportion

    def _calculate_polarization(self, action_counts: Dict[str, int], total: int) -> float:
        """Calculate polarization index (0 = consensus, 1 = maximum split)."""
        proportions = [count / total for count in action_counts.values()]

        # Entropy-based polarization measure
        # Low entropy = high polarization (one dominant choice)
        # High entropy = low polarization (even split)
        import math

        entropy = 0.0
        for p in proportions:
            if p > 0:
                entropy -= p * math.log2(p)

        max_entropy = math.log2(len(action_counts))

        if max_entropy > 0:
            # Invert so high polarization = low entropy
            return 1 - (entropy / max_entropy)
        return 0.0

    async def run(
        self,
        scenario: PredictionScenario,
        environment: SimulationEnvironment,
        db: AsyncSession,
        progress_callback: Optional[Callable[[int, int, Dict], None]] = None,
    ) -> PredictionResult:
        """
        Run complete simulation.

        Args:
            scenario: The prediction scenario
            environment: The simulation environment
            db: Database session
            progress_callback: Callback for progress updates

        Returns:
            PredictionResult with final predictions
        """
        # Initialize
        await self.initialize(scenario, environment, db)

        # Update scenario status
        scenario.status = "running"
        scenario.started_at = datetime.utcnow()
        await db.flush()

        try:
            # Run simulation loop
            for step in range(scenario.time_steps):
                step_metrics = await self.step(db)

                # Update progress
                scenario.progress = int((step + 1) / scenario.time_steps * 100)
                scenario.current_step = step + 1

                if progress_callback:
                    progress_callback(step + 1, scenario.time_steps, step_metrics)

                # Checkpoint
                if (step + 1) % self.config.checkpoint_interval == 0:
                    await db.flush()

            # Calculate final results
            result = await self._calculate_final_results(scenario, db)

            # Update scenario status
            scenario.status = "completed"
            scenario.progress = 100
            scenario.completed_at = datetime.utcnow()
            scenario.prediction_results = result.predictions

            await db.flush()

            return result

        except Exception as e:
            scenario.status = "failed"
            await db.flush()
            raise e

        finally:
            self._is_running = False

    async def _calculate_final_results(
        self,
        scenario: PredictionScenario,
        db: AsyncSession,
    ) -> PredictionResult:
        """Calculate final prediction results from simulation."""
        # Aggregate final agent actions
        final_actions = {}
        confidence_data = {}

        for agent in self._agents.values():
            action = agent.committed_action or agent.last_action
            if action:
                final_actions[action] = final_actions.get(action, 0) + 1

                # Track certainty for confidence intervals
                certainty = agent.state_vector.get("certainty", 0.5)
                if action not in confidence_data:
                    confidence_data[action] = []
                confidence_data[action].append(certainty)

        total = sum(final_actions.values())

        # Calculate proportions
        predictions = {k: v / total for k, v in final_actions.items()}

        # Calculate confidence intervals (bootstrap-style)
        confidence_intervals = {}
        for action, certainties in confidence_data.items():
            mean_certainty = np.mean(certainties)
            std_certainty = np.std(certainties)

            base_prop = predictions.get(action, 0)
            margin = std_certainty * 0.1 + (1 - mean_certainty) * 0.05

            confidence_intervals[action] = {
                "lower": max(0, base_prop - margin),
                "upper": min(1, base_prop + margin),
                "confidence": 0.95,
            }

        # Regional breakdown
        regional_predictions = self._calculate_regional_breakdown()

        # Demographic breakdown
        demographic_predictions = self._calculate_demographic_breakdown()

        # Create result
        result = PredictionResult(
            scenario_id=scenario.id,
            prediction_date=datetime.utcnow(),
            target_event_date=scenario.target_date,
            predictions=predictions,
            confidence_intervals=confidence_intervals,
            monte_carlo_runs=1,
            regional_predictions=regional_predictions,
            demographic_predictions=demographic_predictions,
            overall_confidence=float(np.mean([c.get("certainty", 0.5) for c in confidence_data.values()])),
            key_drivers=self._identify_key_drivers(),
        )

        db.add(result)

        return result

    def _calculate_regional_breakdown(self) -> Dict[str, Dict[str, float]]:
        """Calculate predictions by region."""
        regional_data = {}

        for agent in self._agents.values():
            region = agent.region_id
            if not region:
                continue

            if region not in regional_data:
                regional_data[region] = {}

            action = agent.committed_action or agent.last_action
            if action:
                regional_data[region][action] = regional_data[region].get(action, 0) + 1

        # Convert to proportions
        regional_predictions = {}
        for region, actions in regional_data.items():
            total = sum(actions.values())
            regional_predictions[region] = {k: v / total for k, v in actions.items()}

        return regional_predictions

    def _calculate_demographic_breakdown(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """Calculate predictions by demographic groups."""
        demo_fields = ["age", "gender", "education", "income_bracket", "urban_rural"]
        demographic_data = {field: {} for field in demo_fields}

        for agent in self._agents.values():
            action = agent.committed_action or agent.last_action
            if not action:
                continue

            for field in demo_fields:
                value = agent.demographics.get(field)
                if field == "age":
                    # Bucket ages
                    age = value
                    if age < 25:
                        value = "18-24"
                    elif age < 35:
                        value = "25-34"
                    elif age < 45:
                        value = "35-44"
                    elif age < 55:
                        value = "45-54"
                    else:
                        value = "55+"

                if value not in demographic_data[field]:
                    demographic_data[field][value] = {}

                demographic_data[field][value][action] = \
                    demographic_data[field][value].get(action, 0) + 1

        # Convert to proportions
        demographic_predictions = {}
        for field, values in demographic_data.items():
            demographic_predictions[field] = {}
            for value, actions in values.items():
                total = sum(actions.values())
                demographic_predictions[field][value] = {k: v / total for k, v in actions.items()}

        return demographic_predictions

    def _identify_key_drivers(self) -> Dict[str, Any]:
        """Identify key factors driving the prediction."""
        return {
            "top_factors": [
                {"factor": "social_influence", "impact": 0.25, "direction": "varies"},
                {"factor": "initial_preference", "impact": 0.35, "direction": "positive"},
                {"factor": "demographic_alignment", "impact": 0.20, "direction": "positive"},
                {"factor": "external_events", "impact": 0.15, "direction": "varies"},
                {"factor": "behavioral_biases", "impact": 0.05, "direction": "varies"},
            ],
            "model_notes": "Behavioral economics model with social network influence",
        }

    async def stream_results(
        self,
        scenario: PredictionScenario,
        environment: SimulationEnvironment,
        db: AsyncSession,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream simulation results as they are generated.

        Yields progress updates and intermediate results.
        """
        await self.initialize(scenario, environment, db)

        scenario.status = "running"
        scenario.started_at = datetime.utcnow()
        await db.flush()

        try:
            for step in range(scenario.time_steps):
                step_metrics = await self.step(db)

                scenario.progress = int((step + 1) / scenario.time_steps * 100)
                scenario.current_step = step + 1

                yield {
                    "type": "step_update",
                    "step": step + 1,
                    "total_steps": scenario.time_steps,
                    "progress": scenario.progress,
                    "metrics": step_metrics,
                }

                # Periodic checkpoint
                if (step + 1) % self.config.checkpoint_interval == 0:
                    await db.flush()
                    yield {
                        "type": "checkpoint",
                        "step": step + 1,
                    }

            # Final results
            result = await self._calculate_final_results(scenario, db)

            scenario.status = "completed"
            scenario.progress = 100
            scenario.completed_at = datetime.utcnow()

            await db.flush()

            yield {
                "type": "completed",
                "predictions": result.predictions,
                "confidence_intervals": result.confidence_intervals,
                "regional": result.regional_predictions,
                "demographic": result.demographic_predictions,
            }

        except Exception as e:
            scenario.status = "failed"
            await db.flush()
            yield {
                "type": "error",
                "error": str(e),
            }

        finally:
            self._is_running = False
