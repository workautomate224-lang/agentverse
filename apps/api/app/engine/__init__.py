"""
Predictive Simulation Engine
Reference: project.md §4.1, §9.3

Core engine components for multi-agent simulation.
Supports Society Mode (rule-driven) and Target Mode (planning-based).
"""

from app.engine.simulation_engine import SimulationEngine
from app.engine.state_manager import StateManager
from app.engine.behavioral_model import BehavioralModel, CognitiveBiases
from app.engine.simulation_loop import SimulationLoop
from app.engine.action_space import ActionSpace, ActionType

# Society Mode Rule Engine (project.md Phase 1)
from app.engine.rules import (
    RuleEngine,
    Rule,
    RulePhase,
    RulePriority,
    RuleContext,
    RuleResult,
    RuleFactory,
    # Built-in rules
    ConformityRule,
    MediaInfluenceRule,
    LossAversionRule,
    SocialNetworkRule,
    # Utilities
    get_rule_engine,
    create_rule_engine,
)

# Agent State Machine (project.md §6.3, Phase 1)
from app.engine.agent import (
    Agent,
    AgentState,
    AgentProfile,
    AgentMemory,
    AgentFactory,
    AgentPool,
    SocialEdge,
    SocialEdgeType,
)

# Event Script Executor (project.md §6.4, Phase 3)
from app.engine.event_executor import (
    EventExecutor,
    EventScript,
    EventScope,
    IntensityProfile,
    Delta,
    DeltaOperation,
    IntensityProfileType,
    ExecutionContext,
    ExecutionResult,
    DeltaApplication,
    create_event_from_dict,
    get_event_executor,
)

__all__ = [
    # Core
    "SimulationEngine",
    "StateManager",
    "BehavioralModel",
    "CognitiveBiases",
    "SimulationLoop",
    "ActionSpace",
    "ActionType",
    # Rule Engine (Society Mode)
    "RuleEngine",
    "Rule",
    "RulePhase",
    "RulePriority",
    "RuleContext",
    "RuleResult",
    "RuleFactory",
    "ConformityRule",
    "MediaInfluenceRule",
    "LossAversionRule",
    "SocialNetworkRule",
    "get_rule_engine",
    "create_rule_engine",
    # Agent State Machine
    "Agent",
    "AgentState",
    "AgentProfile",
    "AgentMemory",
    "AgentFactory",
    "AgentPool",
    "SocialEdge",
    "SocialEdgeType",
    # Event Script Executor (Phase 3)
    "EventExecutor",
    "EventScript",
    "EventScope",
    "IntensityProfile",
    "Delta",
    "DeltaOperation",
    "IntensityProfileType",
    "ExecutionContext",
    "ExecutionResult",
    "DeltaApplication",
    "create_event_from_dict",
    "get_event_executor",
]
