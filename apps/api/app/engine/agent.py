"""
Agent State Machine
Reference: project.md §6.3 (Agent), Phase 1

Implements:
- Agent as runtime instance derived from Persona
- State machine with lifecycle phases
- Social graph edges
- Memory and belief systems
- Integration with Rule Engine
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4
import hashlib
import copy


class AgentState(str, Enum):
    """Agent lifecycle states."""
    INITIALIZING = "initializing"
    IDLE = "idle"
    OBSERVING = "observing"
    EVALUATING = "evaluating"
    DECIDING = "deciding"
    ACTING = "acting"
    UPDATING = "updating"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class SocialEdgeType(str, Enum):
    """Types of social relationships."""
    FAMILY = "family"
    FRIEND = "friend"
    COLLEAGUE = "colleague"
    ACQUAINTANCE = "acquaintance"
    FOLLOWER = "follower"
    LEADER = "leader"
    NEIGHBOR = "neighbor"
    STRANGER = "stranger"


@dataclass
class SocialEdge:
    """
    Represents a social connection to another agent.
    Reference: project.md §6.3 - social edges
    """
    target_agent_id: str
    edge_type: SocialEdgeType
    weight: float = 1.0  # Influence strength 0-1
    trust: float = 0.5   # Trust level 0-1
    frequency: float = 0.5  # Interaction frequency 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def influence_strength(self) -> float:
        """Calculate effective influence from this edge."""
        return self.weight * self.trust * self.frequency


@dataclass
class AgentMemory:
    """
    Agent's memory system.
    Stores experiences, beliefs, and learned patterns.
    """
    # Short-term memory (recent events)
    recent_events: List[Dict[str, Any]] = field(default_factory=list)
    max_recent: int = 50

    # Long-term beliefs (learned over time)
    beliefs: Dict[str, float] = field(default_factory=dict)

    # Episodic memory (key events)
    episodes: List[Dict[str, Any]] = field(default_factory=list)
    max_episodes: int = 100

    # Learned associations
    associations: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def add_event(self, event: Dict[str, Any]) -> None:
        """Add an event to recent memory."""
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_recent:
            # Move significant events to episodes
            old_event = self.recent_events.pop(0)
            if old_event.get("significance", 0) > 0.7:
                self.add_episode(old_event)

    def add_episode(self, episode: Dict[str, Any]) -> None:
        """Add a significant episode to long-term memory."""
        self.episodes.append(episode)
        if len(self.episodes) > self.max_episodes:
            # Remove least significant
            self.episodes.sort(key=lambda e: e.get("significance", 0))
            self.episodes.pop(0)

    def update_belief(self, key: str, value: float, learning_rate: float = 0.1) -> None:
        """Update a belief with exponential moving average."""
        if key in self.beliefs:
            self.beliefs[key] = self.beliefs[key] * (1 - learning_rate) + value * learning_rate
        else:
            self.beliefs[key] = value

    def get_belief(self, key: str, default: float = 0.5) -> float:
        """Get a belief value."""
        return self.beliefs.get(key, default)

    def add_association(self, trigger: str, response: str, strength: float) -> None:
        """Add or strengthen an association."""
        if trigger not in self.associations:
            self.associations[trigger] = {}
        if response in self.associations[trigger]:
            # Strengthen existing
            self.associations[trigger][response] = min(
                1.0,
                self.associations[trigger][response] + strength * 0.1
            )
        else:
            self.associations[trigger][response] = strength

    def to_dict(self) -> Dict[str, Any]:
        """Serialize memory state."""
        return {
            "recent_events": self.recent_events,
            "beliefs": self.beliefs,
            "episodes": self.episodes,
            "associations": self.associations,
        }


@dataclass
class AgentProfile:
    """
    Agent profile derived from Persona.
    Contains stable characteristics.
    Reference: project.md §6.2 (Persona) → §6.3 (Agent)
    """
    # Identity
    agent_id: str = field(default_factory=lambda: str(uuid4()))
    persona_id: Optional[str] = None
    label: str = ""

    # Demographics (from Persona)
    age: int = 30
    gender: str = "unknown"
    region: str = ""
    segment: str = ""

    # Psychographics (stable traits)
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5

    # Economic
    income_bracket: str = "middle"
    risk_tolerance: float = 0.5

    # Cognitive biases (from Persona §6.2)
    confirmation_bias: float = 0.5
    anchoring_bias: float = 0.5
    availability_bias: float = 0.5
    loss_aversion: float = 2.25  # Kahneman default

    # Action tendencies
    action_probabilities: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_persona(cls, persona: Dict[str, Any]) -> "AgentProfile":
        """Create profile from Persona data."""
        profile = cls()

        profile.persona_id = persona.get("persona_id")
        profile.label = persona.get("label", "")

        # Demographics
        demographics = persona.get("demographics", {})
        profile.age = demographics.get("age", 30)
        profile.gender = demographics.get("gender", "unknown")
        profile.region = demographics.get("region", "")
        profile.segment = demographics.get("segment", "")

        # Psychographics
        psychographics = persona.get("psychographics", {})
        big_five = psychographics.get("big_five", {})
        profile.openness = big_five.get("openness", 0.5)
        profile.conscientiousness = big_five.get("conscientiousness", 0.5)
        profile.extraversion = big_five.get("extraversion", 0.5)
        profile.agreeableness = big_five.get("agreeableness", 0.5)
        profile.neuroticism = big_five.get("neuroticism", 0.5)

        # Economic
        economic = persona.get("economic", {})
        profile.income_bracket = economic.get("income_bracket", "middle")
        profile.risk_tolerance = economic.get("risk_tolerance", 0.5)

        # Biases
        biases = persona.get("cognitive_biases", {})
        profile.confirmation_bias = biases.get("confirmation_bias", 0.5)
        profile.anchoring_bias = biases.get("anchoring_bias", 0.5)
        profile.availability_bias = biases.get("availability_bias", 0.5)
        profile.loss_aversion = biases.get("loss_aversion", 2.25)

        # Action probabilities
        profile.action_probabilities = persona.get("action_probabilities", {})

        return profile


class Agent:
    """
    Runtime agent instance.

    Represents an active agent in simulation derived from a Persona.
    Maintains current state, social connections, and memory.

    Reference: project.md §6.3
    """

    def __init__(
        self,
        profile: AgentProfile,
        initial_state: Optional[Dict[str, Any]] = None,
    ):
        self.profile = profile
        self.id = profile.agent_id

        # Current state
        self._state = AgentState.INITIALIZING
        self._variables: Dict[str, Any] = initial_state or {}

        # Social graph
        self._social_edges: Dict[str, SocialEdge] = {}

        # Memory
        self._memory = AgentMemory()

        # Current tick
        self._current_tick = 0
        self._last_action_tick = -1

        # Pending actions
        self._pending_actions: List[Dict[str, Any]] = []

        # Telemetry
        self._state_history: List[Tuple[int, AgentState]] = []

    @property
    def state(self) -> AgentState:
        return self._state

    @state.setter
    def state(self, new_state: AgentState) -> None:
        if new_state != self._state:
            self._state_history.append((self._current_tick, new_state))
        self._state = new_state

    @property
    def variables(self) -> Dict[str, Any]:
        return self._variables

    @property
    def memory(self) -> AgentMemory:
        return self._memory

    # =========================================================================
    # State Access
    # =========================================================================

    def get_var(self, key: str, default: Any = None) -> Any:
        """Get a state variable."""
        return self._variables.get(key, default)

    def set_var(self, key: str, value: Any) -> None:
        """Set a state variable."""
        self._variables[key] = value

    def update_vars(self, updates: Dict[str, Any]) -> None:
        """Batch update variables."""
        self._variables.update(updates)

    # =========================================================================
    # Social Graph
    # =========================================================================

    def add_social_edge(self, edge: SocialEdge) -> None:
        """Add a social connection."""
        self._social_edges[edge.target_agent_id] = edge

    def remove_social_edge(self, target_id: str) -> Optional[SocialEdge]:
        """Remove a social connection."""
        return self._social_edges.pop(target_id, None)

    def get_social_edges(
        self,
        edge_type: Optional[SocialEdgeType] = None,
    ) -> List[SocialEdge]:
        """Get social connections, optionally filtered by type."""
        edges = list(self._social_edges.values())
        if edge_type:
            edges = [e for e in edges if e.edge_type == edge_type]
        return edges

    def get_peer_ids(self) -> List[str]:
        """Get IDs of all connected agents."""
        return list(self._social_edges.keys())

    def get_influence_from(self, agent_id: str) -> float:
        """Get influence strength from a specific agent."""
        edge = self._social_edges.get(agent_id)
        return edge.influence_strength() if edge else 0.0

    # =========================================================================
    # Lifecycle Methods
    # =========================================================================

    def initialize(self) -> None:
        """Initialize the agent for simulation."""
        self.state = AgentState.IDLE

        # Set default variables if not present
        defaults = {
            "opinion": 0.5,
            "satisfaction": 0.5,
            "energy": 1.0,
            "attention": 1.0,
        }
        for key, value in defaults.items():
            if key not in self._variables:
                self._variables[key] = value

    def tick(self, tick_number: int) -> None:
        """Advance agent to a new tick."""
        self._current_tick = tick_number

    def observe(self, environment: Dict[str, Any], peer_states: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Observe phase: gather information from environment and peers.

        Returns observation context for rule evaluation.
        """
        self.state = AgentState.OBSERVING

        # Calculate social signals from peers
        social_signals = {}
        for peer_state in peer_states:
            peer_id = peer_state.get("agent_id")
            influence = self.get_influence_from(peer_id) if peer_id else 0

            if influence > 0:
                for key, value in peer_state.items():
                    if isinstance(value, (int, float)) and key not in ("agent_id",):
                        signal_key = f"peer_{key}"
                        if signal_key not in social_signals:
                            social_signals[signal_key] = 0
                        social_signals[signal_key] += value * influence

        # Normalize social signals
        peer_count = len(peer_states) if peer_states else 1
        social_signals = {k: v / peer_count for k, v in social_signals.items()}

        observation = {
            "environment": environment,
            "social_signals": social_signals,
            "peer_states": peer_states,
            "self_state": dict(self._variables),
        }

        # Record to memory
        self._memory.add_event({
            "tick": self._current_tick,
            "type": "observation",
            "data": observation,
            "significance": 0.3,
        })

        return observation

    def evaluate(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate phase: assess options based on current state.

        Returns evaluation context for decision-making.
        """
        self.state = AgentState.EVALUATING

        # Combine profile traits with current state
        evaluation = {
            "observation": observation,
            "traits": {
                "openness": self.profile.openness,
                "risk_tolerance": self.profile.risk_tolerance,
                "loss_aversion": self.profile.loss_aversion,
            },
            "beliefs": dict(self._memory.beliefs),
            "current_state": dict(self._variables),
        }

        return evaluation

    def decide(self, evaluation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Decide phase: make a decision based on evaluation.

        Returns decision or None if no action needed.
        """
        self.state = AgentState.DECIDING

        # Get action probabilities based on profile and state
        decision = None

        # Check each possible action
        for action_type, base_prob in self.profile.action_probabilities.items():
            # Modify probability based on current state
            modified_prob = base_prob

            # Apply trait modifiers
            if action_type == "risky_action":
                modified_prob *= self.profile.risk_tolerance
            elif action_type == "social_action":
                modified_prob *= self.profile.extraversion

            # TODO: Integrate with RuleEngine decisions

            if modified_prob > 0.5:  # Threshold
                decision = {
                    "action_type": action_type,
                    "probability": modified_prob,
                    "context": evaluation,
                }
                break

        return decision

    def act(self, decision: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Act phase: execute decision and produce actions.

        Returns list of actions to be processed.
        """
        self.state = AgentState.ACTING
        actions = []

        if decision:
            action = {
                "agent_id": self.id,
                "tick": self._current_tick,
                "action_type": decision.get("action_type"),
                "parameters": decision.get("parameters", {}),
                "confidence": decision.get("probability", 1.0),
            }
            actions.append(action)
            self._last_action_tick = self._current_tick

            # Record to memory
            self._memory.add_event({
                "tick": self._current_tick,
                "type": "action",
                "data": action,
                "significance": 0.5,
            })

        return actions

    def update(self, action_results: List[Dict[str, Any]], state_updates: Dict[str, Any]) -> None:
        """
        Update phase: update internal state based on action results.
        """
        self.state = AgentState.UPDATING

        # Apply state updates
        self.update_vars(state_updates)

        # Process action results
        for result in action_results:
            if result.get("success"):
                # Positive reinforcement
                self._memory.update_belief(
                    f"action_{result.get('action_type')}_success",
                    1.0,
                    learning_rate=0.1
                )
            else:
                # Negative reinforcement
                self._memory.update_belief(
                    f"action_{result.get('action_type')}_success",
                    0.0,
                    learning_rate=0.05
                )

        # Return to idle
        self.state = AgentState.IDLE

    def suspend(self) -> None:
        """Suspend the agent (pause simulation)."""
        self.state = AgentState.SUSPENDED

    def resume(self) -> None:
        """Resume suspended agent."""
        if self.state == AgentState.SUSPENDED:
            self.state = AgentState.IDLE

    def terminate(self) -> None:
        """Terminate the agent."""
        self.state = AgentState.TERMINATED

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_snapshot(self) -> Dict[str, Any]:
        """Create a snapshot of agent state for telemetry."""
        return {
            "agent_id": self.id,
            "persona_id": self.profile.persona_id,
            "tick": self._current_tick,
            "state": self.state.value,
            "variables": dict(self._variables),
            "memory_summary": {
                "belief_count": len(self._memory.beliefs),
                "episode_count": len(self._memory.episodes),
            },
            "social_edge_count": len(self._social_edges),
        }

    def to_full_state(self) -> Dict[str, Any]:
        """Serialize complete agent state for persistence."""
        return {
            "agent_id": self.id,
            "profile": {
                "persona_id": self.profile.persona_id,
                "label": self.profile.label,
                "age": self.profile.age,
                "gender": self.profile.gender,
                "region": self.profile.region,
                "segment": self.profile.segment,
                "openness": self.profile.openness,
                "conscientiousness": self.profile.conscientiousness,
                "extraversion": self.profile.extraversion,
                "agreeableness": self.profile.agreeableness,
                "neuroticism": self.profile.neuroticism,
                "risk_tolerance": self.profile.risk_tolerance,
                "loss_aversion": self.profile.loss_aversion,
            },
            "state": self.state.value,
            "variables": self._variables,
            "memory": self._memory.to_dict(),
            "social_edges": [
                {
                    "target_agent_id": e.target_agent_id,
                    "edge_type": e.edge_type.value,
                    "weight": e.weight,
                    "trust": e.trust,
                    "frequency": e.frequency,
                }
                for e in self._social_edges.values()
            ],
            "tick": self._current_tick,
            "state_history": self._state_history[-10:],  # Last 10 transitions
        }

    @classmethod
    def from_state(cls, state_dict: Dict[str, Any]) -> "Agent":
        """Recreate agent from serialized state."""
        profile_data = state_dict.get("profile", {})
        profile = AgentProfile(
            agent_id=state_dict["agent_id"],
            persona_id=profile_data.get("persona_id"),
            label=profile_data.get("label", ""),
            age=profile_data.get("age", 30),
            gender=profile_data.get("gender", "unknown"),
            region=profile_data.get("region", ""),
            segment=profile_data.get("segment", ""),
            openness=profile_data.get("openness", 0.5),
            conscientiousness=profile_data.get("conscientiousness", 0.5),
            extraversion=profile_data.get("extraversion", 0.5),
            agreeableness=profile_data.get("agreeableness", 0.5),
            neuroticism=profile_data.get("neuroticism", 0.5),
            risk_tolerance=profile_data.get("risk_tolerance", 0.5),
            loss_aversion=profile_data.get("loss_aversion", 2.25),
        )

        agent = cls(profile, initial_state=state_dict.get("variables", {}))

        # Restore state
        agent._state = AgentState(state_dict.get("state", "idle"))
        agent._current_tick = state_dict.get("tick", 0)

        # Restore memory
        memory_data = state_dict.get("memory", {})
        agent._memory.beliefs = memory_data.get("beliefs", {})
        agent._memory.episodes = memory_data.get("episodes", [])
        agent._memory.associations = memory_data.get("associations", {})

        # Restore social edges
        for edge_data in state_dict.get("social_edges", []):
            edge = SocialEdge(
                target_agent_id=edge_data["target_agent_id"],
                edge_type=SocialEdgeType(edge_data["edge_type"]),
                weight=edge_data.get("weight", 1.0),
                trust=edge_data.get("trust", 0.5),
                frequency=edge_data.get("frequency", 0.5),
            )
            agent.add_social_edge(edge)

        return agent


# =============================================================================
# Agent Factory
# =============================================================================

class AgentFactory:
    """
    Factory for creating agents from Personas.

    Handles the Persona → Agent compilation step.
    Reference: project.md Phase 1 - Persona → Agent compiler
    """

    @classmethod
    def create_from_persona(
        cls,
        persona: Dict[str, Any],
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> Agent:
        """
        Create an agent from a Persona definition.

        Args:
            persona: Persona data dictionary
            initial_state: Optional initial state variables

        Returns:
            Initialized Agent instance
        """
        profile = AgentProfile.from_persona(persona)
        agent = Agent(profile, initial_state)
        agent.initialize()
        return agent

    @classmethod
    def create_batch(
        cls,
        personas: List[Dict[str, Any]],
        initial_state_generator: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> List[Agent]:
        """
        Create multiple agents from a list of personas.

        Args:
            personas: List of Persona data dictionaries
            initial_state_generator: Optional function to generate initial state

        Returns:
            List of initialized Agent instances
        """
        agents = []
        for persona in personas:
            initial_state = None
            if initial_state_generator:
                initial_state = initial_state_generator(persona)

            agent = cls.create_from_persona(persona, initial_state)
            agents.append(agent)

        return agents

    @classmethod
    def create_population(
        cls,
        count: int,
        persona_template: Dict[str, Any],
        variation_factor: float = 0.1,
        rng_seed: int = 42,
    ) -> List[Agent]:
        """
        Create a population of agents with variation around a template.

        Args:
            count: Number of agents to create
            persona_template: Base persona template
            variation_factor: How much to vary traits (0-1)
            rng_seed: Seed for reproducible variation

        Returns:
            List of varied agents
        """
        import random
        rng = random.Random(rng_seed)

        agents = []
        for i in range(count):
            # Create varied persona
            persona = copy.deepcopy(persona_template)
            persona["persona_id"] = str(uuid4())
            persona["label"] = f"Agent_{i}"

            # Vary psychographics
            psychographics = persona.setdefault("psychographics", {})
            big_five = psychographics.setdefault("big_five", {})

            for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
                base_value = big_five.get(trait, 0.5)
                variation = (rng.random() - 0.5) * 2 * variation_factor
                big_five[trait] = max(0, min(1, base_value + variation))

            # Vary economic
            economic = persona.setdefault("economic", {})
            base_risk = economic.get("risk_tolerance", 0.5)
            variation = (rng.random() - 0.5) * 2 * variation_factor
            economic["risk_tolerance"] = max(0, min(1, base_risk + variation))

            agent = cls.create_from_persona(persona)
            agents.append(agent)

        return agents


# =============================================================================
# Agent Pool (for simulation management)
# =============================================================================

class AgentPool:
    """
    Manages a collection of agents for simulation.

    Provides efficient access patterns for:
    - Batch processing
    - Segment/region filtering
    - Social network traversal
    """

    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._by_segment: Dict[str, Set[str]] = {}
        self._by_region: Dict[str, Set[str]] = {}

    def add(self, agent: Agent) -> None:
        """Add an agent to the pool."""
        self._agents[agent.id] = agent

        # Index by segment
        segment = agent.profile.segment
        if segment:
            if segment not in self._by_segment:
                self._by_segment[segment] = set()
            self._by_segment[segment].add(agent.id)

        # Index by region
        region = agent.profile.region
        if region:
            if region not in self._by_region:
                self._by_region[region] = set()
            self._by_region[region].add(agent.id)

    def remove(self, agent_id: str) -> Optional[Agent]:
        """Remove an agent from the pool."""
        agent = self._agents.pop(agent_id, None)
        if agent:
            # Remove from indices
            segment = agent.profile.segment
            if segment and segment in self._by_segment:
                self._by_segment[segment].discard(agent_id)

            region = agent.profile.region
            if region and region in self._by_region:
                self._by_region[region].discard(agent_id)

        return agent

    def get(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def get_all(self) -> List[Agent]:
        """Get all agents."""
        return list(self._agents.values())

    def get_by_segment(self, segment: str) -> List[Agent]:
        """Get all agents in a segment."""
        agent_ids = self._by_segment.get(segment, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_by_region(self, region: str) -> List[Agent]:
        """Get all agents in a region."""
        agent_ids = self._by_region.get(region, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_peers(self, agent: Agent) -> List[Agent]:
        """Get an agent's social network peers."""
        peer_ids = agent.get_peer_ids()
        return [self._agents[pid] for pid in peer_ids if pid in self._agents]

    def count(self) -> int:
        """Get total agent count."""
        return len(self._agents)

    def segments(self) -> List[str]:
        """Get all segment names."""
        return list(self._by_segment.keys())

    def regions(self) -> List[str]:
        """Get all region names."""
        return list(self._by_region.keys())

    def initialize_all(self) -> None:
        """Initialize all agents."""
        for agent in self._agents.values():
            if agent.state == AgentState.INITIALIZING:
                agent.initialize()

    def tick_all(self, tick_number: int) -> None:
        """Advance all agents to a new tick."""
        for agent in self._agents.values():
            agent.tick(tick_number)
