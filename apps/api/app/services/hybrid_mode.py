"""
Hybrid Mode Service
Reference: project.md §11 Phase 6

Combines Target Mode (key actors) with Society Mode (population dynamics).
Key actors follow planned paths while influencing and being influenced by
the surrounding society population.

Constraints:
- C1: Fork-not-mutate - Hybrid runs create new nodes only
- C2: On-demand execution - No continuous simulation
- C5: LLMs compile once at start (Target Mode planning), not per tick
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

from pydantic import BaseModel, Field

from app.services.target_mode import (
    TargetPersonaCompiler,
    ActionSpace,
    ConstraintChecker,
    PathPlanner,
    PathNodeBridge,
    TargetPersona,
    PlannedPath,
    PathAction,
)
from app.engine.rules import RuleEngine, RuleContext, RuleResult, RulePhase
from app.engine.agent import Agent, AgentFactory, AgentPool


# =============================================================================
# Hybrid Mode Schemas
# =============================================================================

class CouplingDirection(str, Enum):
    """Direction of influence in hybrid coupling."""
    KEY_TO_SOCIETY = "key_to_society"  # Key actor actions affect society
    SOCIETY_TO_KEY = "society_to_key"  # Society state affects key actor
    BIDIRECTIONAL = "bidirectional"    # Both directions


class CouplingStrength(str, Enum):
    """Strength of coupling between key actors and society."""
    WEAK = "weak"        # 10% influence transfer
    MODERATE = "moderate"  # 25% influence transfer
    STRONG = "strong"      # 50% influence transfer
    DOMINANT = "dominant"  # 75% influence transfer


@dataclass
class HybridCouplingConfig:
    """Configuration for hybrid mode coupling."""
    direction: CouplingDirection = CouplingDirection.BIDIRECTIONAL
    strength: CouplingStrength = CouplingStrength.MODERATE

    # Key actor → Society influence
    key_action_reach: float = 0.3  # % of society affected by key actor actions
    key_influence_decay: float = 0.1  # Per-tick decay of key actor influence

    # Society → Key actor influence
    society_feedback_weight: float = 0.2  # How much society state affects key actor
    momentum_threshold: float = 0.6  # Society stance threshold for momentum bonus

    # Joint outcome weights
    society_weight: float = 0.6  # Weight of society outcome in joint success
    key_actor_weight: float = 0.4  # Weight of key actor outcome in joint success


class HybridAgentState(BaseModel):
    """State of a key actor in hybrid mode."""
    agent_id: str
    target_persona_id: str
    current_path_id: Optional[str] = None
    path_index: int = 0  # Current position in path
    path_utility: float = 0.0
    cumulative_influence: float = 0.0  # Total influence on society
    constraint_violations: int = 0
    is_blocked: bool = False

    # Inherited from base agent
    stance: float = 0.0
    emotion: float = 0.0
    influence: float = 0.0


class SocietySnapshot(BaseModel):
    """Snapshot of society state for key actor feedback."""
    tick: int
    mean_stance: float
    stance_distribution: Dict[str, float]  # segment → mean stance
    adoption_rate: float
    momentum: float  # Rate of change in stance
    active_events: List[str] = Field(default_factory=list)


class CouplingEffect(BaseModel):
    """Effect of coupling between key actor and society."""
    source: str  # "key_actor" or "society"
    target: str  # "society" or "key_actor"
    effect_type: str  # "stance_shift", "exposure_boost", "constraint_update"
    magnitude: float
    affected_segments: List[str] = Field(default_factory=list)
    affected_regions: List[str] = Field(default_factory=list)
    description: str = ""


class HybridTickResult(BaseModel):
    """Result of a single tick in hybrid simulation."""
    tick: int

    # Key actor state
    key_actor_action: Optional[str] = None
    key_actor_utility_delta: float = 0.0
    key_actor_state: Optional[HybridAgentState] = None

    # Society state
    society_snapshot: Optional[SocietySnapshot] = None

    # Coupling effects applied this tick
    coupling_effects: List[CouplingEffect] = Field(default_factory=list)

    # Constraint status
    constraints_checked: int = 0
    constraints_violated: int = 0


class HybridOutcome(BaseModel):
    """Joint outcome of a hybrid simulation."""
    run_id: str
    node_id: str
    total_ticks: int

    # Society outcomes
    society_outcome_distribution: Dict[str, float]
    society_confidence: float
    society_adoption_rate: float

    # Key actor outcomes
    key_actor_path_id: str
    key_actor_path_completion: float  # 0-1, how much of path was followed
    key_actor_path_utility: float
    key_actor_influence_total: float  # Total influence on society

    # Joint outcomes
    joint_success: bool  # Did both achieve goals?
    synergy_score: float  # Positive interaction effect
    goal_alignment: float  # How aligned were key actor and society goals

    # Explanations
    key_drivers: List[str] = Field(default_factory=list)
    turning_points: List[Dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# Hybrid Agent - Key Actor with Path Following
# =============================================================================

class HybridAgent:
    """
    A key actor that follows a planned path while interacting with society.

    Extends the base Agent concept with Target Mode capabilities:
    - Follows a pre-planned path of actions
    - Tracks utility accumulation
    - Can be blocked by constraint violations
    - Influences and is influenced by society
    """

    def __init__(
        self,
        agent_id: str,
        target_persona: TargetPersona,
        planned_path: PlannedPath,
        coupling_config: HybridCouplingConfig,
    ):
        self.agent_id = agent_id
        self.target_persona = target_persona
        self.planned_path = planned_path
        self.coupling_config = coupling_config

        # State
        self.path_index = 0
        self.cumulative_utility = 0.0
        self.cumulative_influence = 0.0
        self.constraint_violations = 0
        self.is_blocked = False

        # Track effects on society
        self.effects_applied: List[CouplingEffect] = []

    def get_current_action(self) -> Optional[PathAction]:
        """Get the current action from the path."""
        if self.is_blocked or self.path_index >= len(self.planned_path.actions):
            return None
        return self.planned_path.actions[self.path_index]

    def advance_path(self) -> bool:
        """Move to next action in path. Returns True if path continues."""
        if self.is_blocked:
            return False
        self.path_index += 1
        return self.path_index < len(self.planned_path.actions)

    def get_path_completion(self) -> float:
        """Get fraction of path completed (0-1)."""
        if not self.planned_path.actions:
            return 1.0
        return self.path_index / len(self.planned_path.actions)

    def apply_utility(self, utility_delta: float):
        """Apply utility from action execution."""
        self.cumulative_utility += utility_delta

    def apply_influence(self, influence: float):
        """Track influence on society."""
        self.cumulative_influence += influence

    def check_constraints(
        self,
        constraint_checker: ConstraintChecker,
        current_state: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Check if current action violates constraints.
        Returns (is_valid, violation_messages).
        """
        action = self.get_current_action()
        if not action:
            return True, []

        # Build action dict for constraint checking
        action_dict = {
            "action_id": action.action_id,
            "action_type": action.action_type,
            "parameters": action.parameters,
        }

        violations = constraint_checker.check_hard_constraints(
            action_dict,
            current_state,
            self.target_persona.hard_constraints,
        )

        if violations:
            self.constraint_violations += 1
            if self.constraint_violations >= 3:
                self.is_blocked = True
            return False, violations

        return True, []

    def get_state(self) -> HybridAgentState:
        """Get current state as HybridAgentState."""
        return HybridAgentState(
            agent_id=self.agent_id,
            target_persona_id=self.target_persona.persona_id,
            current_path_id=self.planned_path.path_id,
            path_index=self.path_index,
            path_utility=self.cumulative_utility,
            cumulative_influence=self.cumulative_influence,
            constraint_violations=self.constraint_violations,
            is_blocked=self.is_blocked,
            stance=self.target_persona.initial_state.get("stance", 0.0),
            emotion=self.target_persona.initial_state.get("emotion", 0.0),
            influence=self.target_persona.initial_state.get("influence", 0.5),
        )


# =============================================================================
# Hybrid Mode Coupling - Bidirectional Influence
# =============================================================================

class HybridModeCoupling:
    """
    Manages bidirectional coupling between key actors and society.

    Forward coupling (Key → Society):
    - Key actor actions affect society variables (stance, exposure)
    - Reach determined by action type and key actor influence

    Backward coupling (Society → Key):
    - Society state affects key actor constraint checking
    - Momentum provides bonuses or penalties to key actor utility
    """

    def __init__(self, config: HybridCouplingConfig):
        self.config = config
        self.effects_log: List[CouplingEffect] = []

    def compute_key_to_society_effects(
        self,
        key_agent: HybridAgent,
        action: PathAction,
        society_agents: Dict[str, Agent],
    ) -> List[CouplingEffect]:
        """
        Compute effects of key actor action on society.

        Returns list of effects to be applied to society agents.
        """
        effects = []

        if self.config.direction == CouplingDirection.SOCIETY_TO_KEY:
            return effects  # No forward coupling

        # Calculate influence reach
        strength_multiplier = {
            CouplingStrength.WEAK: 0.1,
            CouplingStrength.MODERATE: 0.25,
            CouplingStrength.STRONG: 0.5,
            CouplingStrength.DOMINANT: 0.75,
        }[self.config.strength]

        reach = self.config.key_action_reach * strength_multiplier

        # Determine effect based on action type
        action_type = action.action_type

        if action_type in ["media_campaign", "advertising", "publicity"]:
            # Media actions boost exposure and shift stance
            effect = CouplingEffect(
                source="key_actor",
                target="society",
                effect_type="exposure_boost",
                magnitude=reach * 0.3,
                affected_segments=action.parameters.get("target_segments", []),
                affected_regions=action.parameters.get("target_regions", []),
                description=f"Key actor {action_type} increases exposure by {reach*0.3:.1%}",
            )
            effects.append(effect)

        elif action_type in ["price_change", "promotion", "discount"]:
            # Price actions shift stance for price-sensitive segments
            effect = CouplingEffect(
                source="key_actor",
                target="society",
                effect_type="stance_shift",
                magnitude=reach * 0.2,
                affected_segments=["price_sensitive", "mainstream"],
                description=f"Key actor {action_type} shifts stance by {reach*0.2:.1%}",
            )
            effects.append(effect)

        elif action_type in ["partnership", "endorsement", "collaboration"]:
            # Partnership actions build trust
            effect = CouplingEffect(
                source="key_actor",
                target="society",
                effect_type="trust_boost",
                magnitude=reach * 0.15,
                description=f"Key actor {action_type} boosts trust by {reach*0.15:.1%}",
            )
            effects.append(effect)

        elif action_type in ["event", "launch", "announcement"]:
            # Events create buzz (temporary exposure spike)
            effect = CouplingEffect(
                source="key_actor",
                target="society",
                effect_type="buzz",
                magnitude=reach * 0.4,
                description=f"Key actor {action_type} creates buzz at {reach*0.4:.1%}",
            )
            effects.append(effect)

        # Record effects
        self.effects_log.extend(effects)

        return effects

    def apply_effects_to_society(
        self,
        effects: List[CouplingEffect],
        society_agents: Dict[str, Agent],
        environment: Dict[str, Any],
    ) -> int:
        """
        Apply coupling effects to society agents.

        Returns number of agents affected.
        """
        affected_count = 0

        for effect in effects:
            # Determine which agents are affected
            affected_agents = []

            for agent_id, agent in society_agents.items():
                # Check segment filter
                if effect.affected_segments:
                    if agent.state.get("segment") not in effect.affected_segments:
                        continue

                # Check region filter
                if effect.affected_regions:
                    if agent.state.get("region") not in effect.affected_regions:
                        continue

                # Random selection based on reach (simplified)
                # In real implementation, use deterministic RNG
                affected_agents.append(agent)

            # Apply effect to affected agents
            for agent in affected_agents:
                if effect.effect_type == "exposure_boost":
                    current = agent.state.get("exposure", 0.0)
                    agent.state["exposure"] = min(1.0, current + effect.magnitude)

                elif effect.effect_type == "stance_shift":
                    current = agent.state.get("stance", 0.0)
                    agent.state["stance"] = max(-1.0, min(1.0, current + effect.magnitude))

                elif effect.effect_type == "trust_boost":
                    current = agent.state.get("trust", 0.5)
                    agent.state["trust"] = min(1.0, current + effect.magnitude)

                elif effect.effect_type == "buzz":
                    # Buzz temporarily increases attention/salience
                    current = agent.state.get("attention", 0.5)
                    agent.state["attention"] = min(1.0, current + effect.magnitude)

                affected_count += 1

        return affected_count

    def compute_society_to_key_feedback(
        self,
        key_agent: HybridAgent,
        society_snapshot: SocietySnapshot,
    ) -> CouplingEffect:
        """
        Compute feedback from society to key actor.

        Society momentum and stance distribution affect key actor utility.
        """
        if self.config.direction == CouplingDirection.KEY_TO_SOCIETY:
            return None  # No backward coupling

        # Calculate momentum bonus/penalty
        momentum = society_snapshot.momentum

        if momentum > self.config.momentum_threshold:
            # Positive momentum - society is moving in key actor's direction
            magnitude = self.config.society_feedback_weight * momentum
            effect = CouplingEffect(
                source="society",
                target="key_actor",
                effect_type="momentum_bonus",
                magnitude=magnitude,
                description=f"Positive society momentum ({momentum:.1%}) boosts key actor utility",
            )
        elif momentum < -self.config.momentum_threshold:
            # Negative momentum - society is resisting
            magnitude = self.config.society_feedback_weight * abs(momentum)
            effect = CouplingEffect(
                source="society",
                target="key_actor",
                effect_type="momentum_penalty",
                magnitude=-magnitude,
                description=f"Negative society momentum ({momentum:.1%}) penalizes key actor utility",
            )
        else:
            # Neutral momentum
            effect = CouplingEffect(
                source="society",
                target="key_actor",
                effect_type="neutral",
                magnitude=0.0,
                description="Society momentum is neutral",
            )

        self.effects_log.append(effect)
        return effect

    def apply_feedback_to_key_actor(
        self,
        key_agent: HybridAgent,
        feedback: CouplingEffect,
    ):
        """Apply society feedback to key actor state."""
        if not feedback:
            return

        if feedback.effect_type == "momentum_bonus":
            key_agent.apply_utility(feedback.magnitude * 10)  # Scale to utility
        elif feedback.effect_type == "momentum_penalty":
            key_agent.apply_utility(feedback.magnitude * 10)  # Already negative

    def compute_society_snapshot(
        self,
        tick: int,
        society_agents: Dict[str, Agent],
        previous_snapshot: Optional[SocietySnapshot] = None,
    ) -> SocietySnapshot:
        """Compute current society snapshot for feedback."""
        if not society_agents:
            return SocietySnapshot(
                tick=tick,
                mean_stance=0.0,
                stance_distribution={},
                adoption_rate=0.0,
                momentum=0.0,
            )

        # Calculate mean stance
        stances = [a.state.get("stance", 0.0) for a in society_agents.values()]
        mean_stance = sum(stances) / len(stances)

        # Calculate stance by segment
        segment_stances: Dict[str, List[float]] = {}
        for agent in society_agents.values():
            segment = agent.state.get("segment", "default")
            if segment not in segment_stances:
                segment_stances[segment] = []
            segment_stances[segment].append(agent.state.get("stance", 0.0))

        stance_distribution = {
            seg: sum(vals) / len(vals)
            for seg, vals in segment_stances.items()
        }

        # Calculate adoption rate (stance > 0.5)
        adopters = sum(1 for s in stances if s > 0.5)
        adoption_rate = adopters / len(stances)

        # Calculate momentum (rate of change)
        momentum = 0.0
        if previous_snapshot:
            momentum = mean_stance - previous_snapshot.mean_stance

        return SocietySnapshot(
            tick=tick,
            mean_stance=mean_stance,
            stance_distribution=stance_distribution,
            adoption_rate=adoption_rate,
            momentum=momentum,
        )

    def compute_joint_outcome(
        self,
        key_agent: HybridAgent,
        final_snapshot: SocietySnapshot,
        society_outcome: Dict[str, float],
        goal_stance: float = 0.5,
    ) -> HybridOutcome:
        """
        Compute joint outcome of hybrid simulation.

        Args:
            key_agent: The key actor
            final_snapshot: Final society state
            society_outcome: Outcome distribution from society
            goal_stance: Target stance for success calculation
        """
        # Society success: adoption rate above threshold
        society_success = final_snapshot.adoption_rate >= goal_stance
        society_confidence = min(1.0, final_snapshot.adoption_rate / goal_stance)

        # Key actor success: path completed with positive utility
        key_success = (
            key_agent.get_path_completion() >= 0.8 and
            key_agent.cumulative_utility > 0 and
            not key_agent.is_blocked
        )

        # Joint success
        joint_success = society_success and key_success

        # Synergy: did the combination perform better than expected?
        expected_adoption = 0.3  # Baseline expectation
        actual_adoption = final_snapshot.adoption_rate
        synergy_score = (actual_adoption - expected_adoption) / expected_adoption
        synergy_score = max(-1.0, min(1.0, synergy_score))

        # Goal alignment: how aligned were key actor actions with society movement?
        goal_alignment = 1.0 - abs(final_snapshot.mean_stance - goal_stance)

        # Key drivers
        key_drivers = []
        if key_agent.cumulative_influence > 0.2:
            key_drivers.append("Strong key actor influence on society")
        if final_snapshot.momentum > 0.1:
            key_drivers.append("Positive society momentum")
        if synergy_score > 0.3:
            key_drivers.append("Strong synergy between key actor and society")

        return HybridOutcome(
            run_id="",  # Set by caller
            node_id="",  # Set by caller
            total_ticks=final_snapshot.tick,
            society_outcome_distribution=society_outcome,
            society_confidence=society_confidence,
            society_adoption_rate=final_snapshot.adoption_rate,
            key_actor_path_id=key_agent.planned_path.path_id,
            key_actor_path_completion=key_agent.get_path_completion(),
            key_actor_path_utility=key_agent.cumulative_utility,
            key_actor_influence_total=key_agent.cumulative_influence,
            joint_success=joint_success,
            synergy_score=synergy_score,
            goal_alignment=goal_alignment,
            key_drivers=key_drivers,
        )


# =============================================================================
# Hybrid Mode Runner Configuration
# =============================================================================

class HybridRunConfig(BaseModel):
    """Configuration for a hybrid mode run."""
    # Key actor configuration
    target_persona_id: str
    path_id: str  # Pre-planned path to follow

    # Society configuration
    society_persona_ids: List[str]  # Personas for society agents
    society_agent_count: int = 100

    # Coupling configuration
    coupling_config: HybridCouplingConfig = Field(default_factory=HybridCouplingConfig)

    # Run parameters
    total_ticks: int = 10
    seed: int = 42

    # Goals
    target_adoption_rate: float = 0.5  # Goal for success calculation


# =============================================================================
# Logging
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Hybrid Mode Runner - P6-002
# =============================================================================

class HybridModeRunner:
    """
    Executes hybrid mode simulations combining key actors with society.

    The runner orchestrates:
    1. Key actor path execution (from Target Mode)
    2. Society agent simulation (from Society Mode)
    3. Bidirectional coupling effects
    4. Joint outcome computation

    Constraints:
    - C1: Fork-not-mutate - Creates new nodes, never modifies existing
    - C2: On-demand - Runs only when requested
    - C5: LLMs compile once - Path is pre-planned before execution
    """

    def __init__(
        self,
        rule_engine: RuleEngine,
        agent_factory: AgentFactory,
        constraint_checker: ConstraintChecker,
        seed: int = 42,
    ):
        self.rule_engine = rule_engine
        self.agent_factory = agent_factory
        self.constraint_checker = constraint_checker
        self.seed = seed

        # RNG state (deterministic)
        self._rng_state = seed

    def _xorshift32(self) -> int:
        """Deterministic RNG for reproducibility (same as run_executor)."""
        x = self._rng_state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        self._rng_state = x
        return x

    def _random_float(self) -> float:
        """Random float 0-1 using deterministic RNG."""
        return (self._xorshift32() & 0x7FFFFFFF) / 0x7FFFFFFF

    async def execute_hybrid_run(
        self,
        config: HybridRunConfig,
        key_actor: HybridAgent,
        society_agents: Dict[str, Agent],
        environment: Dict[str, Any],
    ) -> Tuple[HybridOutcome, List[HybridTickResult]]:
        """
        Execute a complete hybrid simulation.

        Args:
            config: Hybrid run configuration
            key_actor: The key actor with planned path
            society_agents: Dictionary of society agents
            environment: Initial environment state

        Returns:
            Tuple of (HybridOutcome, list of tick results)
        """
        logger.info(f"Starting hybrid run with {len(society_agents)} society agents")

        # Initialize coupling
        coupling = HybridModeCoupling(config.coupling_config)

        # Initialize RNG
        self._rng_state = config.seed

        # Track results
        tick_results: List[HybridTickResult] = []
        previous_snapshot: Optional[SocietySnapshot] = None

        # Execute ticks
        for tick in range(config.total_ticks):
            tick_result = await self._execute_tick(
                tick=tick,
                key_actor=key_actor,
                society_agents=society_agents,
                environment=environment,
                coupling=coupling,
                previous_snapshot=previous_snapshot,
            )

            tick_results.append(tick_result)
            previous_snapshot = tick_result.society_snapshot

            # Check if key actor is blocked
            if key_actor.is_blocked:
                logger.warning(f"Key actor blocked at tick {tick}")
                break

        # Compute final society snapshot
        final_snapshot = coupling.compute_society_snapshot(
            tick=config.total_ticks,
            society_agents=society_agents,
            previous_snapshot=previous_snapshot,
        )

        # Aggregate society outcome
        society_outcome = self._aggregate_society_outcome(society_agents)

        # Compute joint outcome
        outcome = coupling.compute_joint_outcome(
            key_agent=key_actor,
            final_snapshot=final_snapshot,
            society_outcome=society_outcome,
            goal_stance=config.target_adoption_rate,
        )

        logger.info(
            f"Hybrid run complete: joint_success={outcome.joint_success}, "
            f"adoption={outcome.society_adoption_rate:.1%}, "
            f"path_completion={outcome.key_actor_path_completion:.1%}"
        )

        return outcome, tick_results

    async def _execute_tick(
        self,
        tick: int,
        key_actor: HybridAgent,
        society_agents: Dict[str, Agent],
        environment: Dict[str, Any],
        coupling: HybridModeCoupling,
        previous_snapshot: Optional[SocietySnapshot],
    ) -> HybridTickResult:
        """Execute a single tick of hybrid simulation."""

        coupling_effects: List[CouplingEffect] = []
        constraints_checked = 0
        constraints_violated = 0

        # 1. Get key actor's current action
        action = key_actor.get_current_action()
        key_action_name = None
        key_utility_delta = 0.0

        if action:
            key_action_name = action.action_id

            # Check constraints
            is_valid, violations = key_actor.check_constraints(
                self.constraint_checker,
                {"tick": tick, "environment": environment},
            )
            constraints_checked = 1
            if not is_valid:
                constraints_violated = 1
                logger.debug(f"Tick {tick}: Key actor constraint violation: {violations}")
            else:
                # Compute key actor effects on society
                effects = coupling.compute_key_to_society_effects(
                    key_actor=key_actor,
                    action=action,
                    society_agents=society_agents,
                )
                coupling_effects.extend(effects)

                # Apply effects to society
                affected = coupling.apply_effects_to_society(
                    effects=effects,
                    society_agents=society_agents,
                    environment=environment,
                )

                # Track influence
                influence = sum(e.magnitude for e in effects)
                key_actor.apply_influence(influence)

                # Calculate utility delta
                key_utility_delta = action.utility * (1.0 - constraints_violated * 0.5)
                key_actor.apply_utility(key_utility_delta)

                # Advance to next action
                key_actor.advance_path()

        # 2. Execute society agents through rule engine
        for agent_id, agent in society_agents.items():
            # Create rule context
            context = RuleContext(
                tick=tick,
                agent_id=agent_id,
                agent_state=agent.state,
                world_state=environment,
                social_network=agent.social_network if hasattr(agent, 'social_network') else {},
            )

            # Execute rules for each phase
            for phase in [RulePhase.OBSERVE, RulePhase.EVALUATE, RulePhase.DECIDE, RulePhase.ACT]:
                results = self.rule_engine.execute_phase(phase, context)
                for result in results:
                    if result.state_changes:
                        agent.state.update(result.state_changes)

        # 3. Compute society snapshot
        snapshot = coupling.compute_society_snapshot(
            tick=tick,
            society_agents=society_agents,
            previous_snapshot=previous_snapshot,
        )

        # 4. Compute society feedback to key actor
        feedback = coupling.compute_society_to_key_feedback(
            key_agent=key_actor,
            society_snapshot=snapshot,
        )
        if feedback:
            coupling_effects.append(feedback)
            coupling.apply_feedback_to_key_actor(key_actor, feedback)

        return HybridTickResult(
            tick=tick,
            key_actor_action=key_action_name,
            key_actor_utility_delta=key_utility_delta,
            key_actor_state=key_actor.get_state(),
            society_snapshot=snapshot,
            coupling_effects=coupling_effects,
            constraints_checked=constraints_checked,
            constraints_violated=constraints_violated,
        )

    def _aggregate_society_outcome(
        self,
        society_agents: Dict[str, Agent],
    ) -> Dict[str, float]:
        """Aggregate society agent states into outcome distribution."""
        if not society_agents:
            return {"adopt": 0.0, "reject": 0.0, "neutral": 0.0}

        adopt = 0
        reject = 0
        neutral = 0

        for agent in society_agents.values():
            stance = agent.state.get("stance", 0.0)
            if stance > 0.3:
                adopt += 1
            elif stance < -0.3:
                reject += 1
            else:
                neutral += 1

        total = len(society_agents)
        return {
            "adopt": adopt / total,
            "reject": reject / total,
            "neutral": neutral / total,
        }

    @classmethod
    def create_from_config(
        cls,
        config: HybridRunConfig,
        rule_engine: RuleEngine,
        agent_factory: AgentFactory,
        constraint_checker: ConstraintChecker,
    ) -> "HybridModeRunner":
        """Factory method to create runner from config."""
        return cls(
            rule_engine=rule_engine,
            agent_factory=agent_factory,
            constraint_checker=constraint_checker,
            seed=config.seed,
        )


# =============================================================================
# Hybrid Mode API Schemas
# =============================================================================

class HybridRunRequest(BaseModel):
    """Request to start a hybrid mode run."""
    project_id: str
    node_id: Optional[str] = None  # Starting node (creates new if None)

    # Key actor config
    target_persona_id: str
    path_id: str

    # Society config
    society_persona_ids: List[str]
    society_agent_count: int = 100

    # Coupling
    coupling_direction: CouplingDirection = CouplingDirection.BIDIRECTIONAL
    coupling_strength: CouplingStrength = CouplingStrength.MODERATE

    # Run params
    total_ticks: int = 10
    seed: Optional[int] = None

    # Goals
    target_adoption_rate: float = 0.5


class HybridRunResponse(BaseModel):
    """Response from hybrid mode run."""
    run_id: str
    node_id: str
    status: str
    outcome: Optional[HybridOutcome] = None
    tick_count: int = 0
    error: Optional[str] = None


class HybridRunProgress(BaseModel):
    """Progress update for hybrid run."""
    run_id: str
    current_tick: int
    total_ticks: int
    key_actor_path_progress: float
    society_adoption_rate: float
    coupling_effects_count: int
