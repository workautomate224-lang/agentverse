"""
Policy Networks for MARL

Implements Actor-Critic neural networks for agent decision-making.
Supports both discrete and continuous action spaces.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
import logging

# PyTorch imports with fallback
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.distributions import Categorical, Normal
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # Create dummy classes for type hints
    class nn:
        class Module:
            pass

logger = logging.getLogger(__name__)


@dataclass
class PolicyConfig:
    """Configuration for policy networks."""

    # Architecture
    state_dim: int = 50
    action_dim: int = 5
    hidden_layers: List[int] = field(default_factory=lambda: [256, 256])
    actor_layers: List[int] = field(default_factory=lambda: [128])
    critic_layers: List[int] = field(default_factory=lambda: [128])

    # Activation
    activation: str = "relu"
    output_activation: str = "softmax"  # For discrete actions

    # Regularization
    dropout: float = 0.0
    layer_norm: bool = True

    # Action space
    action_type: str = "discrete"  # discrete, continuous, hybrid
    action_bounds: Optional[Tuple[float, float]] = None  # For continuous

    # Device
    device: str = "cpu"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "hidden_layers": self.hidden_layers,
            "actor_layers": self.actor_layers,
            "critic_layers": self.critic_layers,
            "activation": self.activation,
            "output_activation": self.output_activation,
            "dropout": self.dropout,
            "layer_norm": self.layer_norm,
            "action_type": self.action_type,
            "action_bounds": self.action_bounds,
            "device": self.device,
        }


if TORCH_AVAILABLE:
    class MLP(nn.Module):
        """Multi-layer perceptron with configurable activation."""

        def __init__(
            self,
            input_dim: int,
            hidden_dims: List[int],
            output_dim: int,
            activation: str = "relu",
            output_activation: Optional[str] = None,
            dropout: float = 0.0,
            layer_norm: bool = False,
        ):
            super().__init__()

            self.layers = nn.ModuleList()
            self.norms = nn.ModuleList() if layer_norm else None
            self.dropout = nn.Dropout(dropout) if dropout > 0 else None

            # Activation functions
            activations = {
                "relu": nn.ReLU(),
                "tanh": nn.Tanh(),
                "elu": nn.ELU(),
                "leaky_relu": nn.LeakyReLU(),
                "gelu": nn.GELU(),
            }
            self.activation = activations.get(activation, nn.ReLU())

            # Build layers
            prev_dim = input_dim
            for hidden_dim in hidden_dims:
                self.layers.append(nn.Linear(prev_dim, hidden_dim))
                if layer_norm:
                    self.norms.append(nn.LayerNorm(hidden_dim))
                prev_dim = hidden_dim

            # Output layer
            self.output_layer = nn.Linear(prev_dim, output_dim)

            # Output activation
            self.output_activation = None
            if output_activation == "softmax":
                self.output_activation = nn.Softmax(dim=-1)
            elif output_activation == "tanh":
                self.output_activation = nn.Tanh()
            elif output_activation == "sigmoid":
                self.output_activation = nn.Sigmoid()

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            for i, layer in enumerate(self.layers):
                x = layer(x)
                if self.norms:
                    x = self.norms[i](x)
                x = self.activation(x)
                if self.dropout:
                    x = self.dropout(x)

            x = self.output_layer(x)

            if self.output_activation:
                x = self.output_activation(x)

            return x


    class PolicyNetwork(nn.Module):
        """
        Simple policy network for discrete action selection.
        Outputs action probabilities.
        """

        def __init__(self, config: PolicyConfig):
            super().__init__()
            self.config = config

            self.network = MLP(
                input_dim=config.state_dim,
                hidden_dims=config.hidden_layers,
                output_dim=config.action_dim,
                activation=config.activation,
                output_activation="softmax" if config.action_type == "discrete" else None,
                dropout=config.dropout,
                layer_norm=config.layer_norm,
            )

            self.to(config.device)

        def forward(self, state: torch.Tensor) -> torch.Tensor:
            """
            Forward pass returning action probabilities or parameters.

            Args:
                state: Shape (batch_size, state_dim)

            Returns:
                Action probabilities/parameters
            """
            return self.network(state)

        def get_action(
            self,
            state: torch.Tensor,
            deterministic: bool = False,
        ) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            Get action from policy.

            Args:
                state: State tensor
                deterministic: If True, select max probability action

            Returns:
                Tuple of (action, log_prob)
            """
            probs = self.forward(state)

            if deterministic:
                action = probs.argmax(dim=-1)
                log_prob = torch.log(probs.gather(-1, action.unsqueeze(-1)) + 1e-10).squeeze(-1)
            else:
                dist = Categorical(probs)
                action = dist.sample()
                log_prob = dist.log_prob(action)

            return action, log_prob

        def evaluate_actions(
            self,
            states: torch.Tensor,
            actions: torch.Tensor,
        ) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            Evaluate log probability and entropy of actions.

            Args:
                states: State tensor
                actions: Action tensor

            Returns:
                Tuple of (log_probs, entropy)
            """
            probs = self.forward(states)
            dist = Categorical(probs)

            log_probs = dist.log_prob(actions)
            entropy = dist.entropy()

            return log_probs, entropy


    class ValueNetwork(nn.Module):
        """
        Value network (critic) for estimating state values.
        """

        def __init__(self, config: PolicyConfig):
            super().__init__()
            self.config = config

            self.network = MLP(
                input_dim=config.state_dim,
                hidden_dims=config.hidden_layers + config.critic_layers,
                output_dim=1,
                activation=config.activation,
                output_activation=None,
                dropout=config.dropout,
                layer_norm=config.layer_norm,
            )

            self.to(config.device)

        def forward(self, state: torch.Tensor) -> torch.Tensor:
            """
            Forward pass returning state value.

            Args:
                state: Shape (batch_size, state_dim)

            Returns:
                State values (batch_size, 1)
            """
            return self.network(state)


    class ActorCriticNetwork(nn.Module):
        """
        Separate actor and critic networks.
        Standard architecture for PPO.
        """

        def __init__(self, config: PolicyConfig):
            super().__init__()
            self.config = config

            # Actor (policy) network
            self.actor = MLP(
                input_dim=config.state_dim,
                hidden_dims=config.hidden_layers + config.actor_layers,
                output_dim=config.action_dim,
                activation=config.activation,
                output_activation="softmax" if config.action_type == "discrete" else None,
                dropout=config.dropout,
                layer_norm=config.layer_norm,
            )

            # Critic (value) network
            self.critic = MLP(
                input_dim=config.state_dim,
                hidden_dims=config.hidden_layers + config.critic_layers,
                output_dim=1,
                activation=config.activation,
                output_activation=None,
                dropout=config.dropout,
                layer_norm=config.layer_norm,
            )

            # For continuous actions
            if config.action_type == "continuous":
                self.log_std = nn.Parameter(torch.zeros(config.action_dim))

            self.to(config.device)

        def forward(
            self,
            state: torch.Tensor,
        ) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            Forward pass for both actor and critic.

            Args:
                state: State tensor

            Returns:
                Tuple of (action_params, value)
            """
            action_params = self.actor(state)
            value = self.critic(state)
            return action_params, value

        def get_action(
            self,
            state: torch.Tensor,
            deterministic: bool = False,
        ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            """
            Get action, log probability, and value estimate.

            Args:
                state: State tensor
                deterministic: If True, select deterministically

            Returns:
                Tuple of (action, log_prob, value)
            """
            action_params, value = self.forward(state)

            if self.config.action_type == "discrete":
                if deterministic:
                    action = action_params.argmax(dim=-1)
                    log_prob = torch.log(
                        action_params.gather(-1, action.unsqueeze(-1)) + 1e-10
                    ).squeeze(-1)
                else:
                    dist = Categorical(action_params)
                    action = dist.sample()
                    log_prob = dist.log_prob(action)
            else:
                # Continuous actions
                mean = action_params
                std = torch.exp(self.log_std)

                if deterministic:
                    action = mean
                    log_prob = torch.zeros(mean.shape[0], device=mean.device)
                else:
                    dist = Normal(mean, std)
                    action = dist.sample()
                    log_prob = dist.log_prob(action).sum(dim=-1)

                # Clip to action bounds if specified
                if self.config.action_bounds:
                    low, high = self.config.action_bounds
                    action = torch.clamp(action, low, high)

            return action, log_prob, value.squeeze(-1)

        def evaluate_actions(
            self,
            states: torch.Tensor,
            actions: torch.Tensor,
        ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            """
            Evaluate actions for training.

            Args:
                states: Batch of states
                actions: Batch of actions

            Returns:
                Tuple of (log_probs, values, entropy)
            """
            action_params, values = self.forward(states)

            if self.config.action_type == "discrete":
                dist = Categorical(action_params)
                log_probs = dist.log_prob(actions)
                entropy = dist.entropy()
            else:
                mean = action_params
                std = torch.exp(self.log_std)
                dist = Normal(mean, std)
                log_probs = dist.log_prob(actions).sum(dim=-1)
                entropy = dist.entropy().sum(dim=-1)

            return log_probs, values.squeeze(-1), entropy


    class SharedActorCritic(nn.Module):
        """
        Actor-critic with shared backbone for efficiency.
        Useful for large agent populations.
        """

        def __init__(self, config: PolicyConfig):
            super().__init__()
            self.config = config

            # Shared backbone
            self.backbone = MLP(
                input_dim=config.state_dim,
                hidden_dims=config.hidden_layers,
                output_dim=config.hidden_layers[-1],
                activation=config.activation,
                output_activation=config.activation,  # Keep activation for shared
                dropout=config.dropout,
                layer_norm=config.layer_norm,
            )

            # Actor head
            actor_input = config.hidden_layers[-1]
            self.actor_head = nn.Sequential(
                *[
                    nn.Sequential(nn.Linear(actor_input if i == 0 else config.actor_layers[i-1],
                                           dim), nn.ReLU())
                    for i, dim in enumerate(config.actor_layers)
                ],
                nn.Linear(config.actor_layers[-1] if config.actor_layers else actor_input,
                         config.action_dim),
                nn.Softmax(dim=-1) if config.action_type == "discrete" else nn.Identity()
            )

            # Critic head
            critic_input = config.hidden_layers[-1]
            self.critic_head = nn.Sequential(
                *[
                    nn.Sequential(nn.Linear(critic_input if i == 0 else config.critic_layers[i-1],
                                           dim), nn.ReLU())
                    for i, dim in enumerate(config.critic_layers)
                ],
                nn.Linear(config.critic_layers[-1] if config.critic_layers else critic_input, 1)
            )

            # For continuous actions
            if config.action_type == "continuous":
                self.log_std = nn.Parameter(torch.zeros(config.action_dim))

            self.to(config.device)

        def forward(
            self,
            state: torch.Tensor,
        ) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            Forward pass.

            Args:
                state: State tensor

            Returns:
                Tuple of (action_params, value)
            """
            features = self.backbone(state)
            action_params = self.actor_head(features)
            value = self.critic_head(features)
            return action_params, value

        def get_action(
            self,
            state: torch.Tensor,
            deterministic: bool = False,
        ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            """Get action with log probability and value."""
            action_params, value = self.forward(state)

            if self.config.action_type == "discrete":
                if deterministic:
                    action = action_params.argmax(dim=-1)
                    log_prob = torch.log(
                        action_params.gather(-1, action.unsqueeze(-1)) + 1e-10
                    ).squeeze(-1)
                else:
                    dist = Categorical(action_params)
                    action = dist.sample()
                    log_prob = dist.log_prob(action)
            else:
                mean = action_params
                std = torch.exp(self.log_std)

                if deterministic:
                    action = mean
                    log_prob = torch.zeros(mean.shape[0], device=mean.device)
                else:
                    dist = Normal(mean, std)
                    action = dist.sample()
                    log_prob = dist.log_prob(action).sum(dim=-1)

            return action, log_prob, value.squeeze(-1)

        def evaluate_actions(
            self,
            states: torch.Tensor,
            actions: torch.Tensor,
        ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            """Evaluate actions for training."""
            action_params, values = self.forward(states)

            if self.config.action_type == "discrete":
                dist = Categorical(action_params)
                log_probs = dist.log_prob(actions)
                entropy = dist.entropy()
            else:
                mean = action_params
                std = torch.exp(self.log_std)
                dist = Normal(mean, std)
                log_probs = dist.log_prob(actions).sum(dim=-1)
                entropy = dist.entropy().sum(dim=-1)

            return log_probs, values.squeeze(-1), entropy


    class MultiAgentPolicyNetwork(nn.Module):
        """
        Policy network that handles multiple agents efficiently.
        Uses parameter sharing with agent-specific embeddings.
        """

        def __init__(
            self,
            config: PolicyConfig,
            num_agents: int,
            embedding_dim: int = 32,
        ):
            super().__init__()
            self.config = config
            self.num_agents = num_agents
            self.embedding_dim = embedding_dim

            # Agent embeddings for heterogeneous behavior
            self.agent_embeddings = nn.Embedding(num_agents, embedding_dim)

            # Shared policy with agent embedding input
            self.policy = ActorCriticNetwork(PolicyConfig(
                state_dim=config.state_dim + embedding_dim,
                action_dim=config.action_dim,
                hidden_layers=config.hidden_layers,
                actor_layers=config.actor_layers,
                critic_layers=config.critic_layers,
                activation=config.activation,
                action_type=config.action_type,
                device=config.device,
            ))

            self.to(config.device)

        def forward(
            self,
            states: torch.Tensor,
            agent_ids: torch.Tensor,
        ) -> Tuple[torch.Tensor, torch.Tensor]:
            """
            Forward pass for multiple agents.

            Args:
                states: Shape (batch_size, state_dim)
                agent_ids: Shape (batch_size,) - agent indices

            Returns:
                Tuple of (action_params, values)
            """
            # Get agent embeddings
            embeddings = self.agent_embeddings(agent_ids)

            # Concatenate state with embedding
            augmented_state = torch.cat([states, embeddings], dim=-1)

            return self.policy.forward(augmented_state)

        def get_actions(
            self,
            states: torch.Tensor,
            agent_ids: torch.Tensor,
            deterministic: bool = False,
        ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            """Get actions for multiple agents."""
            embeddings = self.agent_embeddings(agent_ids)
            augmented_state = torch.cat([states, embeddings], dim=-1)
            return self.policy.get_action(augmented_state, deterministic)


else:
    # Fallback classes when PyTorch is not available
    class PolicyNetwork:
        def __init__(self, config: PolicyConfig):
            raise ImportError("PyTorch is required for PolicyNetwork. Install with: pip install torch")

    class ActorCriticNetwork:
        def __init__(self, config: PolicyConfig):
            raise ImportError("PyTorch is required for ActorCriticNetwork. Install with: pip install torch")

    class SharedActorCritic:
        def __init__(self, config: PolicyConfig):
            raise ImportError("PyTorch is required for SharedActorCritic. Install with: pip install torch")

    class MultiAgentPolicyNetwork:
        def __init__(self, config: PolicyConfig, num_agents: int, embedding_dim: int = 32):
            raise ImportError("PyTorch is required for MultiAgentPolicyNetwork. Install with: pip install torch")


def create_policy_network(
    config: PolicyConfig,
    network_type: str = "actor_critic",
    num_agents: Optional[int] = None,
) -> Any:
    """
    Factory function to create policy networks.

    Args:
        config: Policy configuration
        network_type: Type of network ("policy", "actor_critic", "shared", "multi_agent")
        num_agents: Number of agents (required for multi_agent type)

    Returns:
        Policy network instance
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is required for policy networks. Install with: pip install torch")

    if network_type == "policy":
        return PolicyNetwork(config)
    elif network_type == "actor_critic":
        return ActorCriticNetwork(config)
    elif network_type == "shared":
        return SharedActorCritic(config)
    elif network_type == "multi_agent":
        if num_agents is None:
            raise ValueError("num_agents required for multi_agent network type")
        return MultiAgentPolicyNetwork(config, num_agents)
    else:
        raise ValueError(f"Unknown network type: {network_type}")
