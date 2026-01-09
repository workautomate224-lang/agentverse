"""
Multi-Agent Reinforcement Learning (MARL) Module

Implements policy networks, training algorithms, and distributed training
for predictive simulation agents.
"""

from app.engine.marl.policy_network import (
    PolicyNetwork,
    ActorCriticNetwork,
    SharedActorCritic,
    PolicyConfig,
)
from app.engine.marl.ppo_trainer import (
    PPOTrainer,
    PPOConfig,
    TrainingMetrics,
)
from app.engine.marl.experience_buffer import (
    ExperienceBuffer,
    Experience,
    Trajectory,
)

__all__ = [
    "PolicyNetwork",
    "ActorCriticNetwork",
    "SharedActorCritic",
    "PolicyConfig",
    "PPOTrainer",
    "PPOConfig",
    "TrainingMetrics",
    "ExperienceBuffer",
    "Experience",
    "Trajectory",
]
