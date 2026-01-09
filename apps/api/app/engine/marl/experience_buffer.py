"""
Experience Buffer for MARL Training

Stores and manages agent experiences for policy training.
Optimized for large-scale multi-agent simulations.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Generator
import logging

# PyTorch imports with fallback
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class Experience:
    """Single experience tuple (s, a, r, s', done)."""

    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool

    # Optional additional info
    log_prob: Optional[float] = None
    value: Optional[float] = None
    advantage: Optional[float] = None
    returns: Optional[float] = None

    # Agent identification
    agent_id: Optional[int] = None
    time_step: Optional[int] = None


@dataclass
class Trajectory:
    """Complete trajectory for an agent episode."""

    states: np.ndarray  # Shape (T, state_dim)
    actions: np.ndarray  # Shape (T,)
    rewards: np.ndarray  # Shape (T,)
    dones: np.ndarray  # Shape (T,)

    # Training data
    log_probs: Optional[np.ndarray] = None
    values: Optional[np.ndarray] = None
    advantages: Optional[np.ndarray] = None
    returns: Optional[np.ndarray] = None

    # Metadata
    agent_id: Optional[int] = None
    episode_return: Optional[float] = None
    episode_length: Optional[int] = None

    def __len__(self) -> int:
        return len(self.states)

    def compute_returns(
        self,
        gamma: float = 0.99,
        last_value: float = 0.0,
    ) -> np.ndarray:
        """
        Compute discounted returns.

        Args:
            gamma: Discount factor
            last_value: Bootstrap value for incomplete episodes

        Returns:
            Array of returns
        """
        T = len(self.rewards)
        returns = np.zeros(T, dtype=np.float32)

        running_return = last_value
        for t in reversed(range(T)):
            running_return = self.rewards[t] + gamma * running_return * (1 - self.dones[t])
            returns[t] = running_return

        self.returns = returns
        return returns

    def compute_gae(
        self,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        last_value: float = 0.0,
    ) -> np.ndarray:
        """
        Compute Generalized Advantage Estimation.

        Args:
            gamma: Discount factor
            gae_lambda: GAE lambda parameter
            last_value: Bootstrap value

        Returns:
            Array of advantages
        """
        if self.values is None:
            raise ValueError("Values required for GAE computation")

        T = len(self.rewards)
        advantages = np.zeros(T, dtype=np.float32)

        # Extend values with bootstrap
        values_ext = np.append(self.values, last_value)

        running_gae = 0.0
        for t in reversed(range(T)):
            # TD error
            delta = self.rewards[t] + gamma * values_ext[t + 1] * (1 - self.dones[t]) - values_ext[t]
            # GAE
            running_gae = delta + gamma * gae_lambda * (1 - self.dones[t]) * running_gae
            advantages[t] = running_gae

        self.advantages = advantages
        self.returns = advantages + self.values

        return advantages


class ExperienceBuffer:
    """
    Buffer for storing and sampling agent experiences.
    Supports both on-policy (PPO) and off-policy (DQN) algorithms.
    """

    def __init__(
        self,
        capacity: int = 100000,
        state_dim: int = 50,
        num_agents: int = 1,
        prioritized: bool = False,
        priority_alpha: float = 0.6,
    ):
        """
        Initialize experience buffer.

        Args:
            capacity: Maximum buffer size
            state_dim: Dimension of state vectors
            num_agents: Number of agents (for multi-agent)
            prioritized: Use prioritized experience replay
            priority_alpha: Priority exponent
        """
        self.capacity = capacity
        self.state_dim = state_dim
        self.num_agents = num_agents
        self.prioritized = prioritized
        self.priority_alpha = priority_alpha

        # Pre-allocate arrays for efficiency
        self.states = np.zeros((capacity, state_dim), dtype=np.float32)
        self.actions = np.zeros(capacity, dtype=np.int64)
        self.rewards = np.zeros(capacity, dtype=np.float32)
        self.next_states = np.zeros((capacity, state_dim), dtype=np.float32)
        self.dones = np.zeros(capacity, dtype=np.bool_)

        # Optional training data
        self.log_probs = np.zeros(capacity, dtype=np.float32)
        self.values = np.zeros(capacity, dtype=np.float32)
        self.advantages = np.zeros(capacity, dtype=np.float32)
        self.returns = np.zeros(capacity, dtype=np.float32)

        # Agent tracking
        self.agent_ids = np.zeros(capacity, dtype=np.int32)
        self.time_steps = np.zeros(capacity, dtype=np.int32)

        # Prioritized replay
        if prioritized:
            self.priorities = np.zeros(capacity, dtype=np.float32)
            self.max_priority = 1.0

        # Buffer state
        self.position = 0
        self.size = 0

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        log_prob: Optional[float] = None,
        value: Optional[float] = None,
        agent_id: int = 0,
        time_step: int = 0,
    ) -> None:
        """
        Add a single experience to the buffer.

        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Episode done flag
            log_prob: Action log probability
            value: Value estimate
            agent_id: Agent identifier
            time_step: Simulation time step
        """
        idx = self.position

        self.states[idx] = state
        self.actions[idx] = action
        self.rewards[idx] = reward
        self.next_states[idx] = next_state
        self.dones[idx] = done

        if log_prob is not None:
            self.log_probs[idx] = log_prob
        if value is not None:
            self.values[idx] = value

        self.agent_ids[idx] = agent_id
        self.time_steps[idx] = time_step

        if self.prioritized:
            self.priorities[idx] = self.max_priority

        self.position = (self.position + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def add_batch(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        next_states: np.ndarray,
        dones: np.ndarray,
        log_probs: Optional[np.ndarray] = None,
        values: Optional[np.ndarray] = None,
        agent_ids: Optional[np.ndarray] = None,
        time_step: int = 0,
    ) -> None:
        """
        Add batch of experiences.

        Args:
            states: Shape (batch_size, state_dim)
            actions: Shape (batch_size,)
            rewards: Shape (batch_size,)
            next_states: Shape (batch_size, state_dim)
            dones: Shape (batch_size,)
            log_probs: Optional shape (batch_size,)
            values: Optional shape (batch_size,)
            agent_ids: Optional shape (batch_size,)
            time_step: Simulation time step
        """
        batch_size = len(states)

        # Handle wraparound
        end_idx = self.position + batch_size

        if end_idx <= self.capacity:
            # No wraparound
            self.states[self.position:end_idx] = states
            self.actions[self.position:end_idx] = actions
            self.rewards[self.position:end_idx] = rewards
            self.next_states[self.position:end_idx] = next_states
            self.dones[self.position:end_idx] = dones

            if log_probs is not None:
                self.log_probs[self.position:end_idx] = log_probs
            if values is not None:
                self.values[self.position:end_idx] = values
            if agent_ids is not None:
                self.agent_ids[self.position:end_idx] = agent_ids

            self.time_steps[self.position:end_idx] = time_step

            if self.prioritized:
                self.priorities[self.position:end_idx] = self.max_priority
        else:
            # Wraparound needed
            first_part = self.capacity - self.position
            second_part = batch_size - first_part

            # First part
            self.states[self.position:] = states[:first_part]
            self.actions[self.position:] = actions[:first_part]
            self.rewards[self.position:] = rewards[:first_part]
            self.next_states[self.position:] = next_states[:first_part]
            self.dones[self.position:] = dones[:first_part]

            # Second part
            self.states[:second_part] = states[first_part:]
            self.actions[:second_part] = actions[first_part:]
            self.rewards[:second_part] = rewards[first_part:]
            self.next_states[:second_part] = next_states[first_part:]
            self.dones[:second_part] = dones[first_part:]

            if log_probs is not None:
                self.log_probs[self.position:] = log_probs[:first_part]
                self.log_probs[:second_part] = log_probs[first_part:]
            if values is not None:
                self.values[self.position:] = values[:first_part]
                self.values[:second_part] = values[first_part:]

        self.position = end_idx % self.capacity
        self.size = min(self.size + batch_size, self.capacity)

    def add_trajectory(self, trajectory: Trajectory) -> None:
        """Add a complete trajectory to the buffer."""
        self.add_batch(
            states=trajectory.states,
            actions=trajectory.actions,
            rewards=trajectory.rewards,
            next_states=np.roll(trajectory.states, -1, axis=0),  # Approximate next states
            dones=trajectory.dones,
            log_probs=trajectory.log_probs,
            values=trajectory.values,
            agent_ids=np.full(len(trajectory), trajectory.agent_id) if trajectory.agent_id else None,
        )

        if trajectory.advantages is not None:
            start_idx = (self.position - len(trajectory)) % self.capacity
            if start_idx + len(trajectory) <= self.capacity:
                self.advantages[start_idx:start_idx + len(trajectory)] = trajectory.advantages
                if trajectory.returns is not None:
                    self.returns[start_idx:start_idx + len(trajectory)] = trajectory.returns

    def sample(
        self,
        batch_size: int,
        replace: bool = False,
    ) -> Dict[str, np.ndarray]:
        """
        Sample random batch of experiences.

        Args:
            batch_size: Number of experiences to sample
            replace: Sample with replacement

        Returns:
            Dict of experience arrays
        """
        if self.prioritized:
            return self._prioritized_sample(batch_size)

        indices = np.random.choice(self.size, batch_size, replace=replace)
        return self._get_batch(indices)

    def _prioritized_sample(
        self,
        batch_size: int,
        beta: float = 0.4,
    ) -> Dict[str, np.ndarray]:
        """Sample with prioritized experience replay."""
        priorities = self.priorities[:self.size]
        probs = priorities ** self.priority_alpha
        probs /= probs.sum()

        indices = np.random.choice(self.size, batch_size, p=probs, replace=False)

        # Importance sampling weights
        weights = (self.size * probs[indices]) ** (-beta)
        weights /= weights.max()

        batch = self._get_batch(indices)
        batch["weights"] = weights.astype(np.float32)
        batch["indices"] = indices

        return batch

    def update_priorities(
        self,
        indices: np.ndarray,
        td_errors: np.ndarray,
        epsilon: float = 1e-6,
    ) -> None:
        """Update priorities based on TD errors."""
        if not self.prioritized:
            return

        priorities = np.abs(td_errors) + epsilon
        self.priorities[indices] = priorities
        self.max_priority = max(self.max_priority, priorities.max())

    def _get_batch(self, indices: np.ndarray) -> Dict[str, np.ndarray]:
        """Get batch by indices."""
        return {
            "states": self.states[indices],
            "actions": self.actions[indices],
            "rewards": self.rewards[indices],
            "next_states": self.next_states[indices],
            "dones": self.dones[indices],
            "log_probs": self.log_probs[indices],
            "values": self.values[indices],
            "advantages": self.advantages[indices],
            "returns": self.returns[indices],
            "agent_ids": self.agent_ids[indices],
        }

    def get_all(self) -> Dict[str, np.ndarray]:
        """Get all experiences in buffer."""
        return {
            "states": self.states[:self.size],
            "actions": self.actions[:self.size],
            "rewards": self.rewards[:self.size],
            "next_states": self.next_states[:self.size],
            "dones": self.dones[:self.size],
            "log_probs": self.log_probs[:self.size],
            "values": self.values[:self.size],
            "advantages": self.advantages[:self.size],
            "returns": self.returns[:self.size],
            "agent_ids": self.agent_ids[:self.size],
        }

    def iterate_batches(
        self,
        batch_size: int,
        shuffle: bool = True,
    ) -> Generator[Dict[str, np.ndarray], None, None]:
        """
        Iterate through buffer in batches.

        Args:
            batch_size: Size of each batch
            shuffle: Shuffle indices before iterating

        Yields:
            Batch dictionaries
        """
        indices = np.arange(self.size)
        if shuffle:
            np.random.shuffle(indices)

        for start in range(0, self.size, batch_size):
            end = min(start + batch_size, self.size)
            batch_indices = indices[start:end]
            yield self._get_batch(batch_indices)

    def compute_advantages(
        self,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
    ) -> None:
        """
        Compute advantages for all experiences using GAE.

        Args:
            gamma: Discount factor
            gae_lambda: GAE lambda
        """
        # Group by agent for trajectory-based computation
        agent_indices = {}
        for idx in range(self.size):
            aid = self.agent_ids[idx]
            if aid not in agent_indices:
                agent_indices[aid] = []
            agent_indices[aid].append(idx)

        for aid, indices in agent_indices.items():
            indices = np.array(indices)

            # Sort by time step
            time_order = np.argsort(self.time_steps[indices])
            sorted_indices = indices[time_order]

            values_ext = np.append(self.values[sorted_indices], 0.0)
            rewards = self.rewards[sorted_indices]
            dones = self.dones[sorted_indices]

            T = len(sorted_indices)
            advantages = np.zeros(T, dtype=np.float32)

            running_gae = 0.0
            for t in reversed(range(T)):
                delta = rewards[t] + gamma * values_ext[t + 1] * (1 - dones[t]) - values_ext[t]
                running_gae = delta + gamma * gae_lambda * (1 - dones[t]) * running_gae
                advantages[t] = running_gae

            self.advantages[sorted_indices] = advantages
            self.returns[sorted_indices] = advantages + self.values[sorted_indices]

    def normalize_advantages(self) -> None:
        """Normalize advantages to zero mean and unit variance."""
        if self.size == 0:
            return

        adv = self.advantages[:self.size]
        mean = adv.mean()
        std = adv.std() + 1e-8
        self.advantages[:self.size] = (adv - mean) / std

    def clear(self) -> None:
        """Clear the buffer."""
        self.position = 0
        self.size = 0

        if self.prioritized:
            self.priorities.fill(0)
            self.max_priority = 1.0

    def __len__(self) -> int:
        return self.size

    def to_torch(self, batch: Dict[str, np.ndarray], device: str = "cpu") -> Dict[str, Any]:
        """Convert batch to PyTorch tensors."""
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch required for to_torch()")

        return {
            "states": torch.from_numpy(batch["states"]).float().to(device),
            "actions": torch.from_numpy(batch["actions"]).long().to(device),
            "rewards": torch.from_numpy(batch["rewards"]).float().to(device),
            "next_states": torch.from_numpy(batch["next_states"]).float().to(device),
            "dones": torch.from_numpy(batch["dones"]).float().to(device),
            "log_probs": torch.from_numpy(batch["log_probs"]).float().to(device),
            "values": torch.from_numpy(batch["values"]).float().to(device),
            "advantages": torch.from_numpy(batch["advantages"]).float().to(device),
            "returns": torch.from_numpy(batch["returns"]).float().to(device),
        }


class RolloutBuffer:
    """
    On-policy rollout buffer for PPO.
    Stores complete rollouts before training updates.
    """

    def __init__(
        self,
        buffer_size: int,
        state_dim: int,
        action_dim: int,
        num_agents: int = 1,
        device: str = "cpu",
    ):
        """
        Initialize rollout buffer.

        Args:
            buffer_size: Steps per rollout
            state_dim: State dimension
            action_dim: Action dimension (for multi-discrete)
            num_agents: Number of agents
            device: PyTorch device
        """
        self.buffer_size = buffer_size
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.num_agents = num_agents
        self.device = device

        self.reset()

    def reset(self) -> None:
        """Reset buffer for new rollout."""
        self.states = np.zeros((self.buffer_size, self.num_agents, self.state_dim), dtype=np.float32)
        self.actions = np.zeros((self.buffer_size, self.num_agents), dtype=np.int64)
        self.rewards = np.zeros((self.buffer_size, self.num_agents), dtype=np.float32)
        self.dones = np.zeros((self.buffer_size, self.num_agents), dtype=np.bool_)
        self.log_probs = np.zeros((self.buffer_size, self.num_agents), dtype=np.float32)
        self.values = np.zeros((self.buffer_size, self.num_agents), dtype=np.float32)

        self.advantages = None
        self.returns = None

        self.pos = 0
        self.full = False

    def add(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        dones: np.ndarray,
        log_probs: np.ndarray,
        values: np.ndarray,
    ) -> None:
        """
        Add a step to the rollout.

        Args:
            states: Shape (num_agents, state_dim)
            actions: Shape (num_agents,)
            rewards: Shape (num_agents,)
            dones: Shape (num_agents,)
            log_probs: Shape (num_agents,)
            values: Shape (num_agents,)
        """
        self.states[self.pos] = states
        self.actions[self.pos] = actions
        self.rewards[self.pos] = rewards
        self.dones[self.pos] = dones
        self.log_probs[self.pos] = log_probs
        self.values[self.pos] = values

        self.pos += 1
        if self.pos == self.buffer_size:
            self.full = True

    def compute_returns_and_advantages(
        self,
        last_values: np.ndarray,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
    ) -> None:
        """
        Compute returns and advantages for the rollout.

        Args:
            last_values: Bootstrap values shape (num_agents,)
            gamma: Discount factor
            gae_lambda: GAE lambda
        """
        self.advantages = np.zeros_like(self.rewards)
        self.returns = np.zeros_like(self.rewards)

        last_gae = np.zeros(self.num_agents, dtype=np.float32)

        for t in reversed(range(self.buffer_size)):
            if t == self.buffer_size - 1:
                next_values = last_values
            else:
                next_values = self.values[t + 1]

            delta = self.rewards[t] + gamma * next_values * (1 - self.dones[t]) - self.values[t]
            last_gae = delta + gamma * gae_lambda * (1 - self.dones[t]) * last_gae

            self.advantages[t] = last_gae
            self.returns[t] = last_gae + self.values[t]

    def get_batches(
        self,
        batch_size: int,
        shuffle: bool = True,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Generate training batches from rollout.

        Args:
            batch_size: Batch size
            shuffle: Shuffle data

        Yields:
            Batch dictionaries with PyTorch tensors
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch required for get_batches()")

        # Flatten (buffer_size, num_agents, ...) to (buffer_size * num_agents, ...)
        total_samples = self.buffer_size * self.num_agents

        flat_states = self.states.reshape(total_samples, -1)
        flat_actions = self.actions.reshape(total_samples)
        flat_log_probs = self.log_probs.reshape(total_samples)
        flat_values = self.values.reshape(total_samples)
        flat_advantages = self.advantages.reshape(total_samples)
        flat_returns = self.returns.reshape(total_samples)

        # Normalize advantages
        adv_mean = flat_advantages.mean()
        adv_std = flat_advantages.std() + 1e-8
        flat_advantages = (flat_advantages - adv_mean) / adv_std

        # Generate indices
        indices = np.arange(total_samples)
        if shuffle:
            np.random.shuffle(indices)

        for start in range(0, total_samples, batch_size):
            end = min(start + batch_size, total_samples)
            batch_indices = indices[start:end]

            yield {
                "states": torch.from_numpy(flat_states[batch_indices]).float().to(self.device),
                "actions": torch.from_numpy(flat_actions[batch_indices]).long().to(self.device),
                "old_log_probs": torch.from_numpy(flat_log_probs[batch_indices]).float().to(self.device),
                "values": torch.from_numpy(flat_values[batch_indices]).float().to(self.device),
                "advantages": torch.from_numpy(flat_advantages[batch_indices]).float().to(self.device),
                "returns": torch.from_numpy(flat_returns[batch_indices]).float().to(self.device),
            }
