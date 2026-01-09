"""
Action Space for Predictive Simulation

Defines discrete and continuous action spaces for agents.
Supports election voting, consumer behavior, and other decision domains.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of actions agents can take."""
    # Electoral actions
    VOTE = "vote"
    ABSTAIN = "abstain"
    SWITCH_PREFERENCE = "switch_preference"
    COMMIT = "commit"

    # Information actions
    SEEK_INFORMATION = "seek_information"
    SHARE_INFORMATION = "share_information"
    IGNORE_INFORMATION = "ignore_information"

    # Social actions
    DISCUSS = "discuss"
    PERSUADE = "persuade"
    LISTEN = "listen"
    AVOID = "avoid"

    # Consumer actions
    PURCHASE = "purchase"
    CONSIDER = "consider"
    REJECT = "reject"
    RECOMMEND = "recommend"

    # General
    WAIT = "wait"
    EXIT = "exit"


@dataclass
class ActionDefinition:
    """Definition of a single action."""
    action_type: ActionType
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[str] = field(default_factory=list)
    effects: Dict[str, Any] = field(default_factory=dict)
    reward_components: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_type": self.action_type.value,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "preconditions": self.preconditions,
            "effects": self.effects,
            "reward_components": self.reward_components,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionDefinition":
        """Create from dictionary."""
        return cls(
            action_type=ActionType(data["action_type"]),
            name=data["name"],
            description=data["description"],
            parameters=data.get("parameters", {}),
            preconditions=data.get("preconditions", []),
            effects=data.get("effects", {}),
            reward_components=data.get("reward_components", {}),
        )


class BaseActionSpace(ABC):
    """Abstract base class for action spaces."""

    @abstractmethod
    def sample(self, n: int = 1) -> np.ndarray:
        """Sample random actions."""
        pass

    @abstractmethod
    def contains(self, action: Any) -> bool:
        """Check if action is valid."""
        pass

    @abstractmethod
    def get_action_mask(self, agent_state: Dict[str, Any]) -> np.ndarray:
        """Get mask of valid actions for agent state."""
        pass

    @property
    @abstractmethod
    def n(self) -> int:
        """Number of actions (for discrete spaces)."""
        pass

    @property
    @abstractmethod
    def shape(self) -> Tuple[int, ...]:
        """Shape of action space."""
        pass


class DiscreteActionSpace(BaseActionSpace):
    """
    Discrete action space with named actions.
    Used for voting, purchasing decisions, etc.
    """

    def __init__(
        self,
        actions: List[ActionDefinition],
        allow_abstain: bool = True,
    ):
        """
        Initialize discrete action space.

        Args:
            actions: List of action definitions
            allow_abstain: Whether to include abstain/wait action
        """
        self.actions = actions
        self.allow_abstain = allow_abstain

        # Add abstain if not present
        if allow_abstain:
            abstain_exists = any(a.action_type == ActionType.ABSTAIN for a in actions)
            if not abstain_exists:
                self.actions.append(ActionDefinition(
                    action_type=ActionType.ABSTAIN,
                    name="abstain",
                    description="Take no action this step",
                ))

        # Create action index mapping
        self.action_to_index = {a.name: i for i, a in enumerate(self.actions)}
        self.index_to_action = {i: a for i, a in enumerate(self.actions)}

        self._n = len(self.actions)

    @property
    def n(self) -> int:
        return self._n

    @property
    def shape(self) -> Tuple[int, ...]:
        return (self._n,)

    def sample(self, n: int = 1) -> np.ndarray:
        """Sample random actions."""
        return np.random.randint(0, self._n, size=n)

    def sample_with_mask(
        self,
        mask: np.ndarray,
        n: int = 1,
    ) -> np.ndarray:
        """
        Sample random actions respecting validity mask.

        Args:
            mask: Shape (n, num_actions) - 1 for valid, 0 for invalid
            n: Number of samples (should match mask first dimension)

        Returns:
            Action indices
        """
        results = np.zeros(n, dtype=np.int64)

        for i in range(n):
            valid_actions = np.where(mask[i] > 0)[0]
            if len(valid_actions) > 0:
                results[i] = np.random.choice(valid_actions)
            else:
                # Fallback to abstain or first action
                abstain_idx = self.action_to_index.get("abstain", 0)
                results[i] = abstain_idx

        return results

    def contains(self, action: Any) -> bool:
        """Check if action is valid."""
        if isinstance(action, int):
            return 0 <= action < self._n
        elif isinstance(action, str):
            return action in self.action_to_index
        return False

    def get_action_mask(self, agent_state: Dict[str, Any]) -> np.ndarray:
        """
        Get mask of valid actions for agent state.

        Args:
            agent_state: Agent's current state

        Returns:
            Boolean mask where True = valid action
        """
        mask = np.ones(self._n, dtype=bool)

        for i, action in enumerate(self.actions):
            for precondition in action.preconditions:
                # Parse precondition string
                if precondition == "is_committed":
                    if not agent_state.get("is_committed", False):
                        mask[i] = False
                elif precondition == "not_committed":
                    if agent_state.get("is_committed", False):
                        mask[i] = False
                elif precondition == "has_information":
                    if not agent_state.get("has_information", False):
                        mask[i] = False
                elif precondition.startswith("certainty_above_"):
                    threshold = float(precondition.split("_")[-1])
                    if agent_state.get("certainty", 0) < threshold:
                        mask[i] = False
                elif precondition.startswith("certainty_below_"):
                    threshold = float(precondition.split("_")[-1])
                    if agent_state.get("certainty", 0) >= threshold:
                        mask[i] = False

        return mask

    def get_batch_action_masks(
        self,
        agent_states: List[Dict[str, Any]],
    ) -> np.ndarray:
        """
        Get action masks for multiple agents.

        Args:
            agent_states: List of agent states

        Returns:
            Shape (num_agents, num_actions) boolean mask
        """
        masks = np.ones((len(agent_states), self._n), dtype=bool)

        for i, state in enumerate(agent_states):
            masks[i] = self.get_action_mask(state)

        return masks

    def get_action_by_index(self, index: int) -> Optional[ActionDefinition]:
        """Get action definition by index."""
        return self.index_to_action.get(index)

    def get_action_by_name(self, name: str) -> Optional[ActionDefinition]:
        """Get action definition by name."""
        idx = self.action_to_index.get(name)
        if idx is not None:
            return self.actions[idx]
        return None

    def get_action_index(self, name: str) -> int:
        """Get action index by name."""
        return self.action_to_index.get(name, -1)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "type": "discrete",
            "actions": [a.to_dict() for a in self.actions],
            "allow_abstain": self.allow_abstain,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiscreteActionSpace":
        """Create from dictionary."""
        actions = [ActionDefinition.from_dict(a) for a in data["actions"]]
        return cls(actions=actions, allow_abstain=data.get("allow_abstain", True))


class ContinuousActionSpace(BaseActionSpace):
    """
    Continuous action space.
    Used for continuous preference shifts, investment amounts, etc.
    """

    def __init__(
        self,
        low: np.ndarray,
        high: np.ndarray,
        names: Optional[List[str]] = None,
    ):
        """
        Initialize continuous action space.

        Args:
            low: Lower bounds for each dimension
            high: Upper bounds for each dimension
            names: Optional names for each dimension
        """
        self.low = np.asarray(low, dtype=np.float32)
        self.high = np.asarray(high, dtype=np.float32)
        self.names = names or [f"dim_{i}" for i in range(len(low))]

        assert len(self.low) == len(self.high), "Low and high must have same length"
        self._shape = (len(self.low),)

    @property
    def n(self) -> int:
        """Not applicable for continuous space."""
        return -1

    @property
    def shape(self) -> Tuple[int, ...]:
        return self._shape

    def sample(self, n: int = 1) -> np.ndarray:
        """Sample random actions uniformly within bounds."""
        return np.random.uniform(
            low=self.low,
            high=self.high,
            size=(n, len(self.low)),
        ).astype(np.float32)

    def contains(self, action: np.ndarray) -> bool:
        """Check if action is within bounds."""
        return np.all(action >= self.low) and np.all(action <= self.high)

    def get_action_mask(self, agent_state: Dict[str, Any]) -> np.ndarray:
        """For continuous space, return full bounds."""
        return np.ones(self._shape[0], dtype=bool)

    def clip(self, action: np.ndarray) -> np.ndarray:
        """Clip action to valid range."""
        return np.clip(action, self.low, self.high)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "type": "continuous",
            "low": self.low.tolist(),
            "high": self.high.tolist(),
            "names": self.names,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContinuousActionSpace":
        """Create from dictionary."""
        return cls(
            low=np.array(data["low"]),
            high=np.array(data["high"]),
            names=data.get("names"),
        )


class HybridActionSpace(BaseActionSpace):
    """
    Hybrid action space combining discrete and continuous actions.
    Used when agents can both choose options AND specify magnitudes.
    """

    def __init__(
        self,
        discrete_space: DiscreteActionSpace,
        continuous_space: ContinuousActionSpace,
    ):
        """
        Initialize hybrid action space.

        Args:
            discrete_space: Discrete action selection
            continuous_space: Continuous action parameters
        """
        self.discrete_space = discrete_space
        self.continuous_space = continuous_space

    @property
    def n(self) -> int:
        return self.discrete_space.n

    @property
    def shape(self) -> Tuple[int, ...]:
        return (self.discrete_space.n, *self.continuous_space.shape)

    def sample(self, n: int = 1) -> Tuple[np.ndarray, np.ndarray]:
        """Sample random hybrid actions."""
        discrete_actions = self.discrete_space.sample(n)
        continuous_actions = self.continuous_space.sample(n)
        return discrete_actions, continuous_actions

    def contains(self, action: Tuple[Any, np.ndarray]) -> bool:
        """Check if hybrid action is valid."""
        discrete, continuous = action
        return self.discrete_space.contains(discrete) and \
               self.continuous_space.contains(continuous)

    def get_action_mask(self, agent_state: Dict[str, Any]) -> np.ndarray:
        """Get discrete action mask."""
        return self.discrete_space.get_action_mask(agent_state)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "type": "hybrid",
            "discrete": self.discrete_space.to_dict(),
            "continuous": self.continuous_space.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HybridActionSpace":
        """Create from dictionary."""
        return cls(
            discrete_space=DiscreteActionSpace.from_dict(data["discrete"]),
            continuous_space=ContinuousActionSpace.from_dict(data["continuous"]),
        )


class ActionSpace:
    """
    Factory class for creating action spaces for different simulation types.
    """

    @staticmethod
    def create_election_space(
        parties: List[str],
        allow_undecided: bool = True,
    ) -> DiscreteActionSpace:
        """
        Create action space for election simulation.

        Args:
            parties: List of party/candidate names
            allow_undecided: Whether agents can remain undecided

        Returns:
            Configured discrete action space
        """
        actions = []

        # Voting actions
        for party in parties:
            actions.append(ActionDefinition(
                action_type=ActionType.VOTE,
                name=f"vote_{party.lower().replace(' ', '_')}",
                description=f"Vote for {party}",
                parameters={"party": party},
                preconditions=["certainty_above_0.3"],
                effects={"committed": True, "choice": party},
                reward_components={"alignment": 0.5, "social_approval": 0.3},
            ))

        # Abstain action
        if allow_undecided:
            actions.append(ActionDefinition(
                action_type=ActionType.ABSTAIN,
                name="abstain",
                description="Do not vote / remain undecided",
                effects={"committed": False},
                reward_components={"avoid_conflict": 0.2},
            ))

        # Switch preference (uncommit)
        actions.append(ActionDefinition(
            action_type=ActionType.SWITCH_PREFERENCE,
            name="reconsider",
            description="Reconsider voting intention",
            preconditions=["is_committed"],
            effects={"committed": False},
            reward_components={"flexibility": 0.1},
        ))

        return DiscreteActionSpace(actions, allow_abstain=False)  # Already added

    @staticmethod
    def create_consumer_space(
        products: List[str],
        allow_wait: bool = True,
    ) -> DiscreteActionSpace:
        """
        Create action space for consumer behavior simulation.

        Args:
            products: List of product/brand names
            allow_wait: Whether agents can delay decision

        Returns:
            Configured discrete action space
        """
        actions = []

        # Purchase actions
        for product in products:
            actions.append(ActionDefinition(
                action_type=ActionType.PURCHASE,
                name=f"purchase_{product.lower().replace(' ', '_')}",
                description=f"Purchase {product}",
                parameters={"product": product},
                preconditions=["certainty_above_0.4"],
                effects={"purchased": product, "committed": True},
                reward_components={"utility": 0.6, "social_proof": 0.2},
            ))

        # Consider actions
        for product in products:
            actions.append(ActionDefinition(
                action_type=ActionType.CONSIDER,
                name=f"consider_{product.lower().replace(' ', '_')}",
                description=f"Consider {product} for future purchase",
                parameters={"product": product},
                effects={"considering": product},
                reward_components={"information_gathering": 0.3},
            ))

        # Wait action
        if allow_wait:
            actions.append(ActionDefinition(
                action_type=ActionType.WAIT,
                name="wait",
                description="Delay purchase decision",
                effects={},
                reward_components={"time_cost": -0.1},
            ))

        # Reject action
        actions.append(ActionDefinition(
            action_type=ActionType.REJECT,
            name="reject_all",
            description="Reject all current options",
            effects={"rejected": True},
            reward_components={"avoided_bad_choice": 0.2},
        ))

        return DiscreteActionSpace(actions, allow_abstain=False)

    @staticmethod
    def create_information_space() -> DiscreteActionSpace:
        """
        Create action space for information-seeking behavior.

        Returns:
            Configured discrete action space
        """
        actions = [
            ActionDefinition(
                action_type=ActionType.SEEK_INFORMATION,
                name="seek_mainstream_media",
                description="Consume mainstream media content",
                parameters={"source_type": "mainstream"},
                effects={"information_exposure": 0.1},
                reward_components={"information_gain": 0.3},
            ),
            ActionDefinition(
                action_type=ActionType.SEEK_INFORMATION,
                name="seek_social_media",
                description="Browse social media for information",
                parameters={"source_type": "social"},
                effects={"information_exposure": 0.15, "echo_chamber_risk": 0.1},
                reward_components={"information_gain": 0.25, "social_connection": 0.15},
            ),
            ActionDefinition(
                action_type=ActionType.SEEK_INFORMATION,
                name="seek_alternative_media",
                description="Consume alternative/independent media",
                parameters={"source_type": "alternative"},
                effects={"information_exposure": 0.1, "perspective_diversity": 0.15},
                reward_components={"information_gain": 0.3},
            ),
            ActionDefinition(
                action_type=ActionType.SHARE_INFORMATION,
                name="share_information",
                description="Share information with social network",
                preconditions=["has_information"],
                effects={"influence_extended": True},
                reward_components={"social_approval": 0.2, "influence": 0.15},
            ),
            ActionDefinition(
                action_type=ActionType.IGNORE_INFORMATION,
                name="ignore_information",
                description="Ignore incoming information",
                effects={},
                reward_components={"cognitive_load_saved": 0.1},
            ),
            ActionDefinition(
                action_type=ActionType.DISCUSS,
                name="discuss_with_peers",
                description="Engage in discussion with social network",
                effects={"social_interaction": True},
                reward_components={"social_connection": 0.25, "information_gain": 0.15},
            ),
        ]

        return DiscreteActionSpace(actions)

    @staticmethod
    def create_social_influence_space() -> DiscreteActionSpace:
        """
        Create action space for social influence behaviors.

        Returns:
            Configured discrete action space
        """
        actions = [
            ActionDefinition(
                action_type=ActionType.PERSUADE,
                name="persuade_others",
                description="Attempt to persuade others to your viewpoint",
                preconditions=["certainty_above_0.6"],
                effects={"influence_attempt": True},
                reward_components={"influence": 0.4, "social_risk": -0.1},
            ),
            ActionDefinition(
                action_type=ActionType.LISTEN,
                name="listen_openly",
                description="Listen to others' viewpoints with openness",
                effects={"susceptibility_increased": True},
                reward_components={"social_harmony": 0.2, "information_gain": 0.2},
            ),
            ActionDefinition(
                action_type=ActionType.AVOID,
                name="avoid_discussion",
                description="Avoid political/sensitive discussions",
                effects={"engagement_decreased": True},
                reward_components={"conflict_avoided": 0.15},
            ),
            ActionDefinition(
                action_type=ActionType.DISCUSS,
                name="neutral_discussion",
                description="Engage in neutral information exchange",
                effects={"social_interaction": True},
                reward_components={"social_connection": 0.2},
            ),
        ]

        return DiscreteActionSpace(actions)

    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> BaseActionSpace:
        """
        Create action space from configuration dictionary.

        Args:
            config: Configuration dict with type and parameters

        Returns:
            Configured action space
        """
        space_type = config.get("type", "discrete")

        if space_type == "discrete":
            return DiscreteActionSpace.from_dict(config)
        elif space_type == "continuous":
            return ContinuousActionSpace.from_dict(config)
        elif space_type == "hybrid":
            return HybridActionSpace.from_dict(config)
        elif space_type == "election":
            return ActionSpace.create_election_space(
                parties=config.get("parties", ["Party A", "Party B"]),
                allow_undecided=config.get("allow_undecided", True),
            )
        elif space_type == "consumer":
            return ActionSpace.create_consumer_space(
                products=config.get("products", ["Product A", "Product B"]),
                allow_wait=config.get("allow_wait", True),
            )
        else:
            raise ValueError(f"Unknown action space type: {space_type}")


class RewardFunction:
    """
    Computes rewards for agent actions.
    Supports multiple reward components and weighted aggregation.
    """

    def __init__(
        self,
        component_weights: Optional[Dict[str, float]] = None,
        discount_factor: float = 0.99,
    ):
        """
        Initialize reward function.

        Args:
            component_weights: Weights for reward components
            discount_factor: Temporal discount factor
        """
        self.component_weights = component_weights or {
            "alignment": 1.0,
            "social_approval": 0.5,
            "information_gain": 0.3,
            "consistency": 0.4,
            "accuracy": 2.0,  # High weight for prediction accuracy
        }
        self.discount_factor = discount_factor

    def compute_reward(
        self,
        action: ActionDefinition,
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[float, Dict[str, float]]:
        """
        Compute reward for an action.

        Args:
            action: Action taken
            state_before: State before action
            state_after: State after action
            context: Environmental context

        Returns:
            Tuple of (total_reward, reward_components)
        """
        components = {}

        # Base reward from action definition
        for comp, value in action.reward_components.items():
            if comp in self.component_weights:
                components[comp] = value * self.component_weights[comp]

        # Alignment reward - how well action aligns with preferences
        if "preferences" in state_after and "choice" in action.effects:
            choice = action.effects["choice"]
            if choice in state_after.get("preferences", {}):
                alignment = state_after["preferences"][choice]
                components["alignment"] = alignment * self.component_weights.get("alignment", 1.0)

        # Social approval - peer support for choice
        if "peer_support" in context:
            peer_support = context["peer_support"]
            components["social_approval"] = peer_support * self.component_weights.get("social_approval", 0.5)

        # Consistency reward - not changing too frequently
        if state_before.get("committed_choice") == state_after.get("committed_choice"):
            if state_before.get("committed_choice") is not None:
                components["consistency"] = 0.1 * self.component_weights.get("consistency", 0.4)

        # Information gain
        info_before = state_before.get("information_level", 0)
        info_after = state_after.get("information_level", 0)
        info_gain = max(0, info_after - info_before)
        if info_gain > 0:
            components["information_gain"] = info_gain * self.component_weights.get("information_gain", 0.3)

        # Calculate total reward
        total_reward = sum(components.values())

        return total_reward, components

    def compute_batch_rewards(
        self,
        actions: np.ndarray,
        action_space: DiscreteActionSpace,
        states_before: List[Dict[str, Any]],
        states_after: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> Tuple[np.ndarray, List[Dict[str, float]]]:
        """
        Compute rewards for batch of actions.

        Args:
            actions: Shape (batch_size,) - action indices
            action_space: The action space used
            states_before: List of states before actions
            states_after: List of states after actions
            context: Shared context

        Returns:
            Tuple of (rewards array, list of component dicts)
        """
        batch_size = len(actions)
        rewards = np.zeros(batch_size)
        all_components = []

        for i in range(batch_size):
            action_def = action_space.get_action_by_index(int(actions[i]))
            if action_def:
                reward, components = self.compute_reward(
                    action_def,
                    states_before[i],
                    states_after[i],
                    context,
                )
                rewards[i] = reward
                all_components.append(components)
            else:
                rewards[i] = 0
                all_components.append({})

        return rewards, all_components

    def compute_accuracy_reward(
        self,
        predictions: np.ndarray,
        ground_truth: np.ndarray,
        accuracy_weight: float = 2.0,
    ) -> np.ndarray:
        """
        Compute reward based on prediction accuracy (for calibration).

        Args:
            predictions: Shape (batch_size, num_options) - predicted probabilities
            ground_truth: Shape (num_options,) - actual outcome distribution
            accuracy_weight: Weight for accuracy reward

        Returns:
            Rewards for each agent based on prediction accuracy
        """
        # Calculate KL divergence from predictions to ground truth
        # Lower KL = higher reward
        epsilon = 1e-10
        kl_div = np.sum(
            ground_truth * np.log((ground_truth + epsilon) / (predictions + epsilon)),
            axis=1
        )

        # Convert to reward (higher is better)
        accuracy_reward = np.exp(-kl_div) * accuracy_weight

        return accuracy_reward
