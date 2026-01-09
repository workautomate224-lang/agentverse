"""
Society Mode Rule Engine
Reference: project.md §4.1, §9.3, Phase 1

Implements:
- Rule-driven core loop (avoid LLM-in-the-loop at scale)
- Rule insertion points for extensibility
- Built-in rules: conformity, media influence, loss aversion
- Deterministic rule evaluation with seeded RNG
- Agent lifecycle: Observe → Evaluate → Decide → Act → Update
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import UUID
import hashlib
import math


class RulePhase(str, Enum):
    """Phases in the agent lifecycle where rules can be inserted."""
    OBSERVE = "observe"      # Agent perceives environment/social signals
    EVALUATE = "evaluate"    # Agent evaluates options based on state
    DECIDE = "decide"        # Agent makes a decision
    ACT = "act"              # Agent performs action
    UPDATE = "update"        # Agent updates internal state
    AGGREGATE = "aggregate"  # Post-tick aggregation


class RulePriority(int, Enum):
    """Priority levels for rule execution order."""
    CRITICAL = 0    # Must run first (safety, constraints)
    HIGH = 10       # Important behavioral rules
    NORMAL = 50     # Standard rules
    LOW = 90        # Optional modifications
    FINAL = 100     # Cleanup/finalization


@dataclass
class RuleContext:
    """Context provided to rules during evaluation."""
    # Tick information
    tick: int
    tick_delta: float = 1.0

    # Agent state
    agent_id: str = ""
    agent_state: Dict[str, Any] = field(default_factory=dict)
    agent_memory: Dict[str, Any] = field(default_factory=dict)

    # Environment
    environment: Dict[str, Any] = field(default_factory=dict)
    segment_id: Optional[str] = None
    region_id: Optional[str] = None

    # Social context
    social_signals: Dict[str, float] = field(default_factory=dict)
    peer_states: List[Dict[str, Any]] = field(default_factory=list)

    # Random source (seeded)
    rng_seed: int = 0

    # Previous decision (for chaining)
    current_decision: Optional[Dict[str, Any]] = None
    decision_confidence: float = 1.0

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleResult:
    """Result of rule evaluation."""
    # Did the rule apply?
    applied: bool = False

    # Modified values
    state_updates: Dict[str, Any] = field(default_factory=dict)
    decision_modifiers: Dict[str, float] = field(default_factory=dict)

    # Decision output (if rule produces decision)
    decision: Optional[Dict[str, Any]] = None
    decision_confidence: float = 1.0

    # Signals to emit
    signals: Dict[str, float] = field(default_factory=dict)

    # Actions to queue
    actions: List[Dict[str, Any]] = field(default_factory=list)

    # Telemetry to record
    telemetry: Dict[str, Any] = field(default_factory=dict)

    # Rule explanation
    explanation: str = ""


class Rule(ABC):
    """
    Abstract base class for Society Mode rules.

    Rules are the core building blocks of the simulation.
    They are deterministic functions that transform agent state
    based on context.
    """

    def __init__(
        self,
        name: str,
        phase: RulePhase,
        priority: RulePriority = RulePriority.NORMAL,
        enabled: bool = True,
        version: str = "1.0.0",
    ):
        self.name = name
        self.phase = phase
        self.priority = priority
        self.enabled = enabled
        self.version = version

    @abstractmethod
    def evaluate(self, ctx: RuleContext) -> RuleResult:
        """
        Evaluate the rule given the context.

        This method must be deterministic - given the same context
        and RNG seed, it must produce the same result.

        Args:
            ctx: The rule evaluation context

        Returns:
            RuleResult with any state updates, decisions, or signals
        """
        pass

    def applies_to(self, ctx: RuleContext) -> bool:
        """
        Check if this rule applies to the given context.
        Override to add conditional activation.
        """
        return self.enabled

    def derive_random(self, ctx: RuleContext, domain: str = "") -> float:
        """
        Get a deterministic random value from the context seed.
        Uses the same derivation as the RNG policy (P0-003).
        """
        seed_str = f"{ctx.rng_seed}:{ctx.agent_id}:{ctx.tick}:{self.name}:{domain}"
        hash_bytes = hashlib.sha256(seed_str.encode()).digest()
        # Use first 8 bytes as a float in [0, 1)
        int_val = int.from_bytes(hash_bytes[:8], 'big')
        return int_val / (2**64)

    def __lt__(self, other: "Rule") -> bool:
        """For sorting by priority."""
        return self.priority.value < other.priority.value


# =============================================================================
# Built-in Rules (project.md Phase 1: 2-3 rules)
# =============================================================================

class ConformityRule(Rule):
    """
    Social conformity rule.

    Agents tend to align their opinions/behaviors with their peers.
    Implements bandwagon effect and social proof.

    Reference: project.md Phase 1 - Rules Engine
    """

    def __init__(
        self,
        conformity_strength: float = 0.3,
        threshold: float = 0.6,
        **kwargs,
    ):
        super().__init__(
            name="conformity",
            phase=RulePhase.EVALUATE,
            **kwargs,
        )
        self.conformity_strength = conformity_strength
        self.threshold = threshold

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        result = RuleResult()

        # Get peer opinions if available
        if not ctx.peer_states:
            return result

        # Calculate peer consensus
        peer_opinions = []
        for peer in ctx.peer_states:
            if "opinion" in peer:
                peer_opinions.append(peer["opinion"])

        if not peer_opinions:
            return result

        avg_opinion = sum(peer_opinions) / len(peer_opinions)
        agent_opinion = ctx.agent_state.get("opinion", 0.5)

        # Calculate consensus strength
        opinion_variance = sum((o - avg_opinion) ** 2 for o in peer_opinions) / len(peer_opinions)
        consensus_strength = max(0, 1 - opinion_variance * 4)  # High variance = low consensus

        # Apply conformity if consensus is strong enough
        if consensus_strength >= self.threshold:
            # Random factor for individual resistance
            resistance = self.derive_random(ctx, "resistance")
            effective_strength = self.conformity_strength * (1 - resistance * 0.5)

            # Move opinion toward peer average
            opinion_delta = (avg_opinion - agent_opinion) * effective_strength * consensus_strength

            result.applied = True
            result.state_updates["opinion_delta"] = opinion_delta
            result.decision_modifiers["conformity"] = effective_strength
            result.telemetry["conformity_applied"] = True
            result.telemetry["consensus_strength"] = consensus_strength
            result.explanation = f"Conformity pressure: {effective_strength:.2f} toward {avg_opinion:.2f}"

        return result


class MediaInfluenceRule(Rule):
    """
    Media/information influence rule.

    Agents' opinions are influenced by media exposure in the environment.
    Implements agenda-setting and framing effects.

    Reference: project.md Phase 1 - Rules Engine
    """

    def __init__(
        self,
        media_weight: float = 0.2,
        attention_decay: float = 0.9,
        **kwargs,
    ):
        super().__init__(
            name="media_influence",
            phase=RulePhase.OBSERVE,
            **kwargs,
        )
        self.media_weight = media_weight
        self.attention_decay = attention_decay

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        result = RuleResult()

        # Get media signals from environment
        media_signal = ctx.environment.get("media_signal", 0)
        media_topic = ctx.environment.get("media_topic")

        if media_signal == 0 or media_topic is None:
            return result

        # Agent's attention is modulated by interest and prior exposure
        prior_exposure = ctx.agent_memory.get(f"media_exposure_{media_topic}", 0)
        interest_level = ctx.agent_state.get("interests", {}).get(media_topic, 0.5)

        # Attention decays with repeated exposure (saturation)
        attention = interest_level * (self.attention_decay ** prior_exposure)

        # Random noise in perception
        noise = (self.derive_random(ctx, "media_noise") - 0.5) * 0.2

        # Calculate effective influence
        effective_influence = media_signal * self.media_weight * attention + noise
        effective_influence = max(-1, min(1, effective_influence))

        result.applied = True
        result.state_updates["perceived_media"] = effective_influence
        result.state_updates[f"media_exposure_{media_topic}"] = prior_exposure + 1
        result.signals["media_reception"] = effective_influence
        result.telemetry["media_influence"] = effective_influence
        result.telemetry["attention_level"] = attention
        result.explanation = f"Media influence on {media_topic}: {effective_influence:.3f}"

        return result


class LossAversionRule(Rule):
    """
    Loss aversion rule (Prospect Theory).

    Agents weigh losses more heavily than equivalent gains.
    Affects decision-making and risk tolerance.

    Reference: project.md Phase 1 - Rules Engine, §6.2 (Cognitive biases)
    """

    def __init__(
        self,
        loss_aversion_lambda: float = 2.25,  # Kahneman & Tversky default
        reference_point_field: str = "reference_wealth",
        **kwargs,
    ):
        super().__init__(
            name="loss_aversion",
            phase=RulePhase.DECIDE,
            priority=RulePriority.HIGH,
            **kwargs,
        )
        self.loss_aversion_lambda = loss_aversion_lambda
        self.reference_point_field = reference_point_field

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        result = RuleResult()

        # Get current decision if any
        if not ctx.current_decision:
            return result

        # Get potential outcomes from decision
        potential_gain = ctx.current_decision.get("potential_gain", 0)
        potential_loss = ctx.current_decision.get("potential_loss", 0)

        if potential_gain == 0 and potential_loss == 0:
            return result

        # Get reference point (status quo)
        reference = ctx.agent_state.get(self.reference_point_field, 0)
        current_value = ctx.agent_state.get("current_wealth", reference)

        # Calculate perceived value using prospect theory
        gain_value = self._prospect_value(potential_gain, is_loss=False)
        loss_value = self._prospect_value(potential_loss, is_loss=True)

        # Net perceived value (losses hurt more)
        perceived_net = gain_value - loss_value * self.loss_aversion_lambda

        # Modify decision confidence based on loss aversion
        if perceived_net < 0:
            # Loss-dominant scenario - reduce confidence
            confidence_modifier = max(0.1, 1 + perceived_net / 10)
        else:
            # Gain-dominant scenario
            confidence_modifier = min(1.5, 1 + perceived_net / 20)

        result.applied = True
        result.decision_modifiers["loss_aversion"] = confidence_modifier
        result.decision_confidence = ctx.decision_confidence * confidence_modifier
        result.telemetry["perceived_gain"] = gain_value
        result.telemetry["perceived_loss"] = loss_value * self.loss_aversion_lambda
        result.telemetry["loss_aversion_modifier"] = confidence_modifier
        result.explanation = f"Loss aversion: perceived net={perceived_net:.2f}, confidence={result.decision_confidence:.2f}"

        return result

    def _prospect_value(self, x: float, is_loss: bool = False, alpha: float = 0.88) -> float:
        """Calculate prospect theory value function."""
        if x == 0:
            return 0
        if is_loss:
            return -(abs(x) ** alpha)
        else:
            return x ** alpha


class SocialNetworkRule(Rule):
    """
    Social network influence aggregation rule.

    Aggregates influence from social connections based on
    tie strength and homophily.
    """

    def __init__(
        self,
        tie_strength_weight: float = 0.5,
        homophily_weight: float = 0.3,
        **kwargs,
    ):
        super().__init__(
            name="social_network",
            phase=RulePhase.OBSERVE,
            priority=RulePriority.HIGH,
            **kwargs,
        )
        self.tie_strength_weight = tie_strength_weight
        self.homophily_weight = homophily_weight

    def evaluate(self, ctx: RuleContext) -> RuleResult:
        result = RuleResult()

        # Aggregate social signals from peers
        if not ctx.social_signals:
            return result

        weighted_sum = 0
        total_weight = 0

        for signal_type, value in ctx.social_signals.items():
            # Weight by signal type
            weight = 1.0
            if "strong_tie" in signal_type:
                weight = 1.0 + self.tie_strength_weight
            elif "weak_tie" in signal_type:
                weight = 1.0 - self.tie_strength_weight * 0.5

            weighted_sum += value * weight
            total_weight += weight

        if total_weight > 0:
            aggregate_signal = weighted_sum / total_weight

            result.applied = True
            result.state_updates["social_influence"] = aggregate_signal
            result.signals["social_aggregate"] = aggregate_signal
            result.telemetry["social_influence_aggregate"] = aggregate_signal
            result.explanation = f"Social network influence: {aggregate_signal:.3f}"

        return result


# =============================================================================
# Rule Engine
# =============================================================================

class RuleEngine:
    """
    Society Mode Rule Engine.

    Manages rule registration, evaluation, and execution order.
    Supports rule insertion points for extensibility.

    Reference: project.md §4.1, §9.3
    """

    def __init__(self, version: str = "1.0.0"):
        self.version = version
        self._rules: Dict[RulePhase, List[Rule]] = {
            phase: [] for phase in RulePhase
        }
        self._rule_registry: Dict[str, Rule] = {}

        # Built-in rules
        self._register_builtin_rules()

    def _register_builtin_rules(self) -> None:
        """Register the default built-in rules."""
        self.register(ConformityRule())
        self.register(MediaInfluenceRule())
        self.register(LossAversionRule())
        self.register(SocialNetworkRule())

    def register(self, rule: Rule) -> None:
        """
        Register a rule with the engine.

        Args:
            rule: The rule to register
        """
        if rule.name in self._rule_registry:
            # Replace existing rule
            old_rule = self._rule_registry[rule.name]
            self._rules[old_rule.phase].remove(old_rule)

        self._rule_registry[rule.name] = rule
        self._rules[rule.phase].append(rule)
        self._rules[rule.phase].sort()  # Sort by priority

    def unregister(self, rule_name: str) -> Optional[Rule]:
        """
        Unregister a rule by name.

        Args:
            rule_name: Name of the rule to remove

        Returns:
            The removed rule, or None if not found
        """
        if rule_name not in self._rule_registry:
            return None

        rule = self._rule_registry.pop(rule_name)
        self._rules[rule.phase].remove(rule)
        return rule

    def get_rule(self, name: str) -> Optional[Rule]:
        """Get a rule by name."""
        return self._rule_registry.get(name)

    def get_rules_for_phase(self, phase: RulePhase) -> List[Rule]:
        """Get all rules for a specific phase, sorted by priority."""
        return [r for r in self._rules[phase] if r.enabled]

    def evaluate_phase(
        self,
        phase: RulePhase,
        ctx: RuleContext,
    ) -> List[RuleResult]:
        """
        Evaluate all rules for a phase.

        Args:
            phase: The lifecycle phase to evaluate
            ctx: The evaluation context

        Returns:
            List of results from all applicable rules
        """
        results = []
        rules = self.get_rules_for_phase(phase)

        for rule in rules:
            if rule.applies_to(ctx):
                result = rule.evaluate(ctx)
                if result.applied:
                    results.append(result)

                    # Update context with state changes for chaining
                    ctx.agent_state.update(result.state_updates)
                    if result.decision:
                        ctx.current_decision = result.decision
                        ctx.decision_confidence = result.decision_confidence

        return results

    def run_agent_tick(
        self,
        ctx: RuleContext,
    ) -> Dict[str, Any]:
        """
        Run a complete agent tick through all phases.

        Implements the agent lifecycle:
        Observe → Evaluate → Decide → Act → Update

        Args:
            ctx: The tick context

        Returns:
            Complete tick result with all state updates and actions
        """
        tick_result = {
            "state_updates": {},
            "decisions": [],
            "actions": [],
            "signals": {},
            "telemetry": {},
            "explanations": [],
        }

        # Process each phase in order
        lifecycle_phases = [
            RulePhase.OBSERVE,
            RulePhase.EVALUATE,
            RulePhase.DECIDE,
            RulePhase.ACT,
            RulePhase.UPDATE,
        ]

        for phase in lifecycle_phases:
            phase_results = self.evaluate_phase(phase, ctx)

            for result in phase_results:
                # Merge state updates
                tick_result["state_updates"].update(result.state_updates)

                # Collect decisions
                if result.decision:
                    tick_result["decisions"].append(result.decision)

                # Queue actions
                tick_result["actions"].extend(result.actions)

                # Merge signals
                for k, v in result.signals.items():
                    if k in tick_result["signals"]:
                        tick_result["signals"][k] = (tick_result["signals"][k] + v) / 2
                    else:
                        tick_result["signals"][k] = v

                # Record telemetry
                tick_result["telemetry"].update(result.telemetry)

                # Collect explanations
                if result.explanation:
                    tick_result["explanations"].append(result.explanation)

        return tick_result

    def run_aggregate_tick(
        self,
        agent_results: List[Dict[str, Any]],
        ctx: RuleContext,
    ) -> Dict[str, Any]:
        """
        Run aggregate rules after all agents have processed.

        Used for computing population-level effects and
        environment updates.

        Args:
            agent_results: Results from all agent ticks
            ctx: The aggregate context

        Returns:
            Aggregate results
        """
        # Build aggregate context
        ctx.metadata["agent_results"] = agent_results
        ctx.metadata["agent_count"] = len(agent_results)

        # Compute aggregate signals
        all_signals = {}
        for result in agent_results:
            for k, v in result.get("signals", {}).items():
                if k not in all_signals:
                    all_signals[k] = []
                all_signals[k].append(v)

        # Average signals for aggregate context
        ctx.social_signals = {
            k: sum(v) / len(v)
            for k, v in all_signals.items()
            if v
        }

        # Run aggregate phase rules
        aggregate_results = self.evaluate_phase(RulePhase.AGGREGATE, ctx)

        return {
            "aggregate_signals": ctx.social_signals,
            "rule_results": aggregate_results,
            "agent_count": len(agent_results),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize engine configuration for versioning."""
        return {
            "version": self.version,
            "rules": {
                name: {
                    "phase": rule.phase.value,
                    "priority": rule.priority.value,
                    "enabled": rule.enabled,
                    "version": rule.version,
                }
                for name, rule in self._rule_registry.items()
            },
        }

    def get_ruleset_hash(self) -> str:
        """
        Get a hash of the current ruleset for versioning.

        Used to detect if ruleset has changed between runs.
        """
        import json
        config_str = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]


# =============================================================================
# Rule Factory
# =============================================================================

class RuleFactory:
    """
    Factory for creating rules from configuration.

    Supports loading rules from:
    - Built-in rule library
    - Custom rule classes
    - JSON/YAML configuration
    """

    _rule_types: Dict[str, type] = {
        "conformity": ConformityRule,
        "media_influence": MediaInfluenceRule,
        "loss_aversion": LossAversionRule,
        "social_network": SocialNetworkRule,
    }

    @classmethod
    def register_type(cls, name: str, rule_class: type) -> None:
        """Register a custom rule type."""
        cls._rule_types[name] = rule_class

    @classmethod
    def create(cls, rule_type: str, **kwargs) -> Rule:
        """
        Create a rule instance by type name.

        Args:
            rule_type: Name of the rule type
            **kwargs: Parameters for the rule

        Returns:
            Rule instance

        Raises:
            ValueError: If rule type is unknown
        """
        if rule_type not in cls._rule_types:
            raise ValueError(f"Unknown rule type: {rule_type}")

        return cls._rule_types[rule_type](**kwargs)

    @classmethod
    def create_engine_from_config(
        cls,
        config: Dict[str, Any],
    ) -> RuleEngine:
        """
        Create a RuleEngine from configuration dict.

        Args:
            config: Engine configuration with rules list

        Returns:
            Configured RuleEngine
        """
        engine = RuleEngine(version=config.get("version", "1.0.0"))

        # Clear default rules if specified
        if config.get("clear_defaults", False):
            for name in list(engine._rule_registry.keys()):
                engine.unregister(name)

        # Add configured rules
        for rule_config in config.get("rules", []):
            rule_type = rule_config.pop("type")
            rule = cls.create(rule_type, **rule_config)
            engine.register(rule)

        return engine

    @classmethod
    def available_types(cls) -> List[str]:
        """Get list of available rule types."""
        return list(cls._rule_types.keys())


# Global default engine instance
_default_engine: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    """Get the global rule engine singleton."""
    global _default_engine
    if _default_engine is None:
        _default_engine = RuleEngine()
    return _default_engine


def create_rule_engine(config: Optional[Dict[str, Any]] = None) -> RuleEngine:
    """Create a new rule engine, optionally from config."""
    if config:
        return RuleFactory.create_engine_from_config(config)
    return RuleEngine()
