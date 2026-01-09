"""
PPO Trainer for Multi-Agent Reinforcement Learning

Implements Proximal Policy Optimization for training agent policies.
Supports distributed training and multi-agent settings.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
import time
import logging
from pathlib import Path
import json

# PyTorch imports with fallback
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.tensorboard import SummaryWriter
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from app.engine.marl.policy_network import (
    PolicyConfig,
    ActorCriticNetwork,
    SharedActorCritic,
    MultiAgentPolicyNetwork,
)
from app.engine.marl.experience_buffer import RolloutBuffer, ExperienceBuffer

logger = logging.getLogger(__name__)


@dataclass
class PPOConfig:
    """Configuration for PPO training."""

    # Learning
    learning_rate: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95

    # PPO specific
    clip_ratio: float = 0.2
    clip_value: bool = True
    value_clip_range: float = 0.2

    # Loss coefficients
    value_loss_coef: float = 0.5
    entropy_coef: float = 0.01
    max_grad_norm: float = 0.5

    # Training
    epochs_per_update: int = 10
    batch_size: int = 256
    rollout_steps: int = 2048

    # Multi-agent
    num_agents: int = 1000
    shared_policy: bool = True

    # Schedule
    lr_schedule: str = "linear"  # linear, constant, cosine
    target_kl: Optional[float] = 0.01  # Early stopping on KL

    # Normalization
    normalize_advantages: bool = True
    normalize_rewards: bool = False

    # Device
    device: str = "cpu"

    # Logging
    log_interval: int = 10
    save_interval: int = 100
    tensorboard: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "learning_rate": self.learning_rate,
            "gamma": self.gamma,
            "gae_lambda": self.gae_lambda,
            "clip_ratio": self.clip_ratio,
            "clip_value": self.clip_value,
            "value_clip_range": self.value_clip_range,
            "value_loss_coef": self.value_loss_coef,
            "entropy_coef": self.entropy_coef,
            "max_grad_norm": self.max_grad_norm,
            "epochs_per_update": self.epochs_per_update,
            "batch_size": self.batch_size,
            "rollout_steps": self.rollout_steps,
            "num_agents": self.num_agents,
            "shared_policy": self.shared_policy,
            "lr_schedule": self.lr_schedule,
            "target_kl": self.target_kl,
            "normalize_advantages": self.normalize_advantages,
            "normalize_rewards": self.normalize_rewards,
            "device": self.device,
        }


@dataclass
class TrainingMetrics:
    """Training metrics for monitoring."""

    # Loss metrics
    policy_loss: float = 0.0
    value_loss: float = 0.0
    entropy_loss: float = 0.0
    total_loss: float = 0.0

    # PPO metrics
    approx_kl: float = 0.0
    clip_fraction: float = 0.0

    # Performance metrics
    mean_reward: float = 0.0
    mean_episode_length: float = 0.0
    mean_value: float = 0.0

    # Prediction accuracy (for calibration)
    prediction_accuracy: float = 0.0

    # Training progress
    update_count: int = 0
    total_steps: int = 0
    elapsed_time: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for logging."""
        return {
            "policy_loss": self.policy_loss,
            "value_loss": self.value_loss,
            "entropy_loss": self.entropy_loss,
            "total_loss": self.total_loss,
            "approx_kl": self.approx_kl,
            "clip_fraction": self.clip_fraction,
            "mean_reward": self.mean_reward,
            "mean_episode_length": self.mean_episode_length,
            "mean_value": self.mean_value,
            "prediction_accuracy": self.prediction_accuracy,
            "update_count": self.update_count,
            "total_steps": self.total_steps,
        }


if TORCH_AVAILABLE:

    class PPOTrainer:
        """
        Proximal Policy Optimization trainer for multi-agent simulation.
        """

        def __init__(
            self,
            policy_config: PolicyConfig,
            ppo_config: PPOConfig,
            log_dir: Optional[str] = None,
        ):
            """
            Initialize PPO trainer.

            Args:
                policy_config: Network configuration
                ppo_config: Training configuration
                log_dir: Directory for logs and checkpoints
            """
            self.policy_config = policy_config
            self.config = ppo_config
            self.device = torch.device(ppo_config.device)

            # Create policy network
            if ppo_config.shared_policy:
                self.policy = SharedActorCritic(policy_config).to(self.device)
            else:
                self.policy = MultiAgentPolicyNetwork(
                    policy_config,
                    ppo_config.num_agents,
                ).to(self.device)

            # Optimizer
            self.optimizer = optim.Adam(
                self.policy.parameters(),
                lr=ppo_config.learning_rate,
                eps=1e-5,
            )

            # Learning rate scheduler
            self.lr_scheduler = None
            if ppo_config.lr_schedule == "linear":
                self.lr_scheduler = optim.lr_scheduler.LambdaLR(
                    self.optimizer,
                    lr_lambda=lambda step: 1.0 - step / 1000,  # Decay over 1000 updates
                )

            # Rollout buffer
            self.buffer = RolloutBuffer(
                buffer_size=ppo_config.rollout_steps,
                state_dim=policy_config.state_dim,
                action_dim=policy_config.action_dim,
                num_agents=ppo_config.num_agents,
                device=str(self.device),
            )

            # Running statistics for normalization
            self.reward_running_mean = 0.0
            self.reward_running_std = 1.0
            self.reward_count = 0

            # Metrics tracking
            self.metrics = TrainingMetrics()
            self.metrics_history: List[TrainingMetrics] = []

            # Logging
            self.log_dir = Path(log_dir) if log_dir else None
            self.writer = None
            if ppo_config.tensorboard and log_dir:
                self.log_dir.mkdir(parents=True, exist_ok=True)
                self.writer = SummaryWriter(log_dir)

            # Training state
            self.update_count = 0
            self.total_steps = 0
            self.start_time = None

            logger.info(f"PPO Trainer initialized with {sum(p.numel() for p in self.policy.parameters())} parameters")

        def collect_rollout(
            self,
            env_step_fn: Callable[[np.ndarray], Tuple[np.ndarray, np.ndarray, np.ndarray, Dict]],
            initial_states: np.ndarray,
        ) -> Dict[str, float]:
            """
            Collect rollout experience by interacting with environment.

            Args:
                env_step_fn: Function (actions) -> (next_states, rewards, dones, info)
                initial_states: Shape (num_agents, state_dim)

            Returns:
                Rollout statistics
            """
            self.buffer.reset()
            states = initial_states.copy()

            total_rewards = []
            episode_lengths = []
            current_episode_rewards = np.zeros(self.config.num_agents)
            current_episode_lengths = np.zeros(self.config.num_agents)

            for step in range(self.config.rollout_steps):
                # Get actions from policy
                with torch.no_grad():
                    states_tensor = torch.from_numpy(states).float().to(self.device)
                    actions, log_probs, values = self.policy.get_action(states_tensor)

                    actions_np = actions.cpu().numpy()
                    log_probs_np = log_probs.cpu().numpy()
                    values_np = values.cpu().numpy()

                # Step environment
                next_states, rewards, dones, info = env_step_fn(actions_np)

                # Normalize rewards if enabled
                if self.config.normalize_rewards:
                    rewards = self._normalize_rewards(rewards)

                # Track episode stats
                current_episode_rewards += rewards
                current_episode_lengths += 1

                for i, done in enumerate(dones):
                    if done:
                        total_rewards.append(current_episode_rewards[i])
                        episode_lengths.append(current_episode_lengths[i])
                        current_episode_rewards[i] = 0
                        current_episode_lengths[i] = 0

                # Store in buffer
                self.buffer.add(
                    states=states,
                    actions=actions_np,
                    rewards=rewards,
                    dones=dones,
                    log_probs=log_probs_np,
                    values=values_np,
                )

                states = next_states
                self.total_steps += self.config.num_agents

            # Compute last values for bootstrapping
            with torch.no_grad():
                states_tensor = torch.from_numpy(states).float().to(self.device)
                _, _, last_values = self.policy.get_action(states_tensor)
                last_values_np = last_values.cpu().numpy()

            # Compute returns and advantages
            self.buffer.compute_returns_and_advantages(
                last_values=last_values_np,
                gamma=self.config.gamma,
                gae_lambda=self.config.gae_lambda,
            )

            return {
                "mean_reward": np.mean(total_rewards) if total_rewards else 0.0,
                "mean_episode_length": np.mean(episode_lengths) if episode_lengths else 0.0,
                "num_episodes": len(total_rewards),
            }

        def update(self) -> TrainingMetrics:
            """
            Perform PPO update using collected rollout.

            Returns:
                Training metrics
            """
            update_start = time.time()

            # Metrics accumulators
            policy_losses = []
            value_losses = []
            entropy_losses = []
            kl_divs = []
            clip_fractions = []

            for epoch in range(self.config.epochs_per_update):
                for batch in self.buffer.get_batches(self.config.batch_size):
                    # Forward pass
                    log_probs, values, entropy = self.policy.evaluate_actions(
                        batch["states"],
                        batch["actions"],
                    )

                    # Policy loss with PPO clipping
                    ratio = torch.exp(log_probs - batch["old_log_probs"])
                    surr1 = ratio * batch["advantages"]
                    surr2 = torch.clamp(
                        ratio,
                        1 - self.config.clip_ratio,
                        1 + self.config.clip_ratio,
                    ) * batch["advantages"]
                    policy_loss = -torch.min(surr1, surr2).mean()

                    # Value loss with optional clipping
                    if self.config.clip_value:
                        value_clipped = batch["values"] + torch.clamp(
                            values - batch["values"],
                            -self.config.value_clip_range,
                            self.config.value_clip_range,
                        )
                        value_loss1 = (values - batch["returns"]) ** 2
                        value_loss2 = (value_clipped - batch["returns"]) ** 2
                        value_loss = 0.5 * torch.max(value_loss1, value_loss2).mean()
                    else:
                        value_loss = 0.5 * ((values - batch["returns"]) ** 2).mean()

                    # Entropy loss
                    entropy_loss = -entropy.mean()

                    # Total loss
                    loss = (
                        policy_loss
                        + self.config.value_loss_coef * value_loss
                        + self.config.entropy_coef * entropy_loss
                    )

                    # Backward pass
                    self.optimizer.zero_grad()
                    loss.backward()
                    nn.utils.clip_grad_norm_(
                        self.policy.parameters(),
                        self.config.max_grad_norm,
                    )
                    self.optimizer.step()

                    # Track metrics
                    with torch.no_grad():
                        policy_losses.append(policy_loss.item())
                        value_losses.append(value_loss.item())
                        entropy_losses.append(entropy_loss.item())

                        # Approximate KL divergence
                        approx_kl = ((ratio - 1) - torch.log(ratio)).mean().item()
                        kl_divs.append(approx_kl)

                        # Clip fraction
                        clip_frac = ((ratio - 1).abs() > self.config.clip_ratio).float().mean().item()
                        clip_fractions.append(clip_frac)

                # Early stopping on KL
                if self.config.target_kl and np.mean(kl_divs[-len(self.buffer)//self.config.batch_size:]) > self.config.target_kl:
                    logger.debug(f"Early stopping at epoch {epoch} due to KL divergence")
                    break

            # Update learning rate
            if self.lr_scheduler:
                self.lr_scheduler.step()

            self.update_count += 1

            # Build metrics
            metrics = TrainingMetrics(
                policy_loss=np.mean(policy_losses),
                value_loss=np.mean(value_losses),
                entropy_loss=np.mean(entropy_losses),
                total_loss=np.mean(policy_losses) + self.config.value_loss_coef * np.mean(value_losses),
                approx_kl=np.mean(kl_divs),
                clip_fraction=np.mean(clip_fractions),
                update_count=self.update_count,
                total_steps=self.total_steps,
                elapsed_time=time.time() - update_start,
            )

            # Log to tensorboard
            if self.writer:
                self.writer.add_scalar("loss/policy", metrics.policy_loss, self.update_count)
                self.writer.add_scalar("loss/value", metrics.value_loss, self.update_count)
                self.writer.add_scalar("loss/entropy", metrics.entropy_loss, self.update_count)
                self.writer.add_scalar("ppo/approx_kl", metrics.approx_kl, self.update_count)
                self.writer.add_scalar("ppo/clip_fraction", metrics.clip_fraction, self.update_count)

            self.metrics = metrics
            self.metrics_history.append(metrics)

            return metrics

        def train(
            self,
            env_step_fn: Callable,
            get_initial_states_fn: Callable,
            total_updates: int,
            callback: Optional[Callable[[int, TrainingMetrics], bool]] = None,
        ) -> List[TrainingMetrics]:
            """
            Full training loop.

            Args:
                env_step_fn: Environment step function
                get_initial_states_fn: Function to get initial states
                total_updates: Total number of updates
                callback: Optional callback(update, metrics) -> continue_training

            Returns:
                List of training metrics
            """
            self.start_time = time.time()
            all_metrics = []

            for update in range(total_updates):
                # Get initial states
                initial_states = get_initial_states_fn()

                # Collect rollout
                rollout_stats = self.collect_rollout(env_step_fn, initial_states)

                # Update policy
                metrics = self.update()
                metrics.mean_reward = rollout_stats["mean_reward"]
                metrics.mean_episode_length = rollout_stats["mean_episode_length"]

                all_metrics.append(metrics)

                # Logging
                if update % self.config.log_interval == 0:
                    elapsed = time.time() - self.start_time
                    fps = self.total_steps / elapsed
                    logger.info(
                        f"Update {update}/{total_updates} | "
                        f"Reward: {metrics.mean_reward:.2f} | "
                        f"Policy Loss: {metrics.policy_loss:.4f} | "
                        f"Value Loss: {metrics.value_loss:.4f} | "
                        f"KL: {metrics.approx_kl:.4f} | "
                        f"FPS: {fps:.0f}"
                    )

                # Tensorboard reward
                if self.writer:
                    self.writer.add_scalar("rollout/mean_reward", metrics.mean_reward, update)
                    self.writer.add_scalar("rollout/mean_episode_length", metrics.mean_episode_length, update)

                # Save checkpoint
                if self.log_dir and update % self.config.save_interval == 0:
                    self.save_checkpoint(self.log_dir / f"checkpoint_{update}.pt")

                # Callback
                if callback:
                    if not callback(update, metrics):
                        logger.info("Training stopped by callback")
                        break

            # Final save
            if self.log_dir:
                self.save_checkpoint(self.log_dir / "final_checkpoint.pt")

            return all_metrics

        def _normalize_rewards(self, rewards: np.ndarray) -> np.ndarray:
            """Normalize rewards using running statistics."""
            batch_mean = rewards.mean()
            batch_var = rewards.var()
            batch_count = len(rewards)

            # Update running statistics
            delta = batch_mean - self.reward_running_mean
            total_count = self.reward_count + batch_count

            self.reward_running_mean += delta * batch_count / total_count
            m_a = self.reward_running_std ** 2 * self.reward_count
            m_b = batch_var * batch_count
            m2 = m_a + m_b + delta ** 2 * self.reward_count * batch_count / total_count
            self.reward_running_std = np.sqrt(m2 / total_count)
            self.reward_count = total_count

            return (rewards - self.reward_running_mean) / (self.reward_running_std + 1e-8)

        def get_actions(
            self,
            states: np.ndarray,
            deterministic: bool = False,
        ) -> np.ndarray:
            """
            Get actions for states (inference).

            Args:
                states: Shape (batch_size, state_dim)
                deterministic: Use deterministic policy

            Returns:
                Actions array
            """
            with torch.no_grad():
                states_tensor = torch.from_numpy(states).float().to(self.device)
                actions, _, _ = self.policy.get_action(states_tensor, deterministic)
                return actions.cpu().numpy()

        def save_checkpoint(self, path: str) -> None:
            """Save training checkpoint."""
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)

            checkpoint = {
                "policy_state_dict": self.policy.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "update_count": self.update_count,
                "total_steps": self.total_steps,
                "policy_config": self.policy_config.to_dict(),
                "ppo_config": self.config.to_dict(),
                "metrics": self.metrics.to_dict(),
            }

            torch.save(checkpoint, path)
            logger.info(f"Saved checkpoint to {path}")

        def load_checkpoint(self, path: str) -> None:
            """Load training checkpoint."""
            checkpoint = torch.load(path, map_location=self.device)

            self.policy.load_state_dict(checkpoint["policy_state_dict"])
            self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
            self.update_count = checkpoint["update_count"]
            self.total_steps = checkpoint["total_steps"]

            logger.info(f"Loaded checkpoint from {path}")

        def export_policy(self, path: str) -> None:
            """Export policy for inference."""
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)

            export_data = {
                "policy_state_dict": self.policy.state_dict(),
                "policy_config": self.policy_config.to_dict(),
            }

            torch.save(export_data, path)
            logger.info(f"Exported policy to {path}")

        def close(self) -> None:
            """Clean up resources."""
            if self.writer:
                self.writer.close()

else:

    class PPOTrainer:
        """Placeholder when PyTorch is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("PyTorch is required for PPOTrainer. Install with: pip install torch")


def create_ppo_trainer(
    state_dim: int,
    action_dim: int,
    num_agents: int = 1000,
    device: str = "cpu",
    **kwargs,
) -> "PPOTrainer":
    """
    Factory function to create PPO trainer with sensible defaults.

    Args:
        state_dim: State dimension
        action_dim: Action dimension
        num_agents: Number of agents
        device: PyTorch device
        **kwargs: Additional PPO config options

    Returns:
        Configured PPO trainer
    """
    policy_config = PolicyConfig(
        state_dim=state_dim,
        action_dim=action_dim,
        hidden_layers=kwargs.pop("hidden_layers", [256, 256]),
        actor_layers=kwargs.pop("actor_layers", [128]),
        critic_layers=kwargs.pop("critic_layers", [128]),
        device=device,
    )

    ppo_config = PPOConfig(
        num_agents=num_agents,
        device=device,
        **kwargs,
    )

    return PPOTrainer(policy_config, ppo_config)
