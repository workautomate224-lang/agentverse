"""
Event Script Executor
Reference: project.md §6.4, §11 Phase 3

Executes event scripts deterministically without LLM involvement at runtime.
Events are pre-compiled from natural language prompts into executable scripts.

Key Principles:
- C5: LLMs are compilers, not runtime brains
- Events are deterministic given the same seed and state
- Intensity profiles control how effects decay over time
- All applications are logged for telemetry (P3-003)
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4


class IntensityProfileType(str, Enum):
    """Intensity profile types for event effects over time."""
    INSTANTANEOUS = "instantaneous"
    LINEAR_DECAY = "linear_decay"
    EXPONENTIAL_DECAY = "exponential_decay"
    LAGGED = "lagged"
    PULSE = "pulse"
    STEP = "step"
    CUSTOM = "custom"


class DeltaOperation(str, Enum):
    """Operations for applying deltas."""
    SET = "set"
    ADD = "add"
    MULTIPLY = "multiply"
    MIN = "min"
    MAX = "max"


@dataclass
class Delta:
    """A single change to apply to state."""
    variable: str
    operation: DeltaOperation
    value: Any
    conditions: Optional[Dict[str, Any]] = None


@dataclass
class EventScope:
    """Who/where/when is affected by an event."""
    affected_regions: Optional[List[str]] = None
    affected_persona_segments: Optional[List[str]] = None
    target_agent_ids: Optional[List[str]] = None
    start_tick: Optional[int] = None
    end_tick: Optional[int] = None

    def is_active(self, current_tick: int) -> bool:
        """Check if event is active at the given tick."""
        if self.start_tick is not None and current_tick < self.start_tick:
            return False
        if self.end_tick is not None and current_tick > self.end_tick:
            return False
        return True

    def matches_agent(
        self,
        agent_id: str,
        agent_region: Optional[str],
        agent_segment: Optional[str]
    ) -> bool:
        """Check if agent is in scope."""
        # If specific agent IDs are set, check membership
        if self.target_agent_ids is not None:
            if agent_id not in self.target_agent_ids:
                return False
            # If agent is targeted, don't apply region/segment filters
            return True

        # Check region filter
        if self.affected_regions is not None:
            if agent_region is None or agent_region not in self.affected_regions:
                return False

        # Check segment filter
        if self.affected_persona_segments is not None:
            if agent_segment is None or agent_segment not in self.affected_persona_segments:
                return False

        return True


@dataclass
class IntensityProfile:
    """How the event effect applies over time."""
    profile_type: IntensityProfileType = IntensityProfileType.INSTANTANEOUS
    initial_intensity: float = 1.0
    decay_rate: Optional[float] = None
    half_life_ticks: Optional[int] = None
    lag_ticks: Optional[int] = None
    custom_profile: Optional[List[float]] = None

    def get_intensity(self, ticks_since_start: int) -> float:
        """Calculate intensity at a given tick offset from event start."""
        if ticks_since_start < 0:
            return 0.0

        # Handle lag
        if self.lag_ticks is not None and ticks_since_start < self.lag_ticks:
            return 0.0

        adjusted_ticks = ticks_since_start
        if self.lag_ticks is not None:
            adjusted_ticks -= self.lag_ticks

        if self.profile_type == IntensityProfileType.INSTANTANEOUS:
            return self.initial_intensity if adjusted_ticks == 0 else 0.0

        elif self.profile_type == IntensityProfileType.STEP:
            return self.initial_intensity

        elif self.profile_type == IntensityProfileType.LINEAR_DECAY:
            rate = self.decay_rate or 0.1
            intensity = self.initial_intensity - (rate * adjusted_ticks)
            return max(0.0, intensity)

        elif self.profile_type == IntensityProfileType.EXPONENTIAL_DECAY:
            if self.half_life_ticks is not None and self.half_life_ticks > 0:
                # Calculate decay constant from half-life
                decay_constant = math.log(2) / self.half_life_ticks
                intensity = self.initial_intensity * math.exp(-decay_constant * adjusted_ticks)
            elif self.decay_rate is not None:
                intensity = self.initial_intensity * math.exp(-self.decay_rate * adjusted_ticks)
            else:
                intensity = self.initial_intensity * (0.9 ** adjusted_ticks)
            return max(0.0, intensity)

        elif self.profile_type == IntensityProfileType.PULSE:
            # Oscillating intensity
            frequency = self.decay_rate or 0.5
            intensity = self.initial_intensity * abs(math.sin(frequency * adjusted_ticks))
            return intensity

        elif self.profile_type == IntensityProfileType.CUSTOM:
            if self.custom_profile and adjusted_ticks < len(self.custom_profile):
                return self.custom_profile[adjusted_ticks] * self.initial_intensity
            return 0.0

        return self.initial_intensity


@dataclass
class EventScript:
    """An executable event script."""
    event_id: str
    label: str
    event_type: str
    scope: EventScope
    environment_deltas: List[Delta] = field(default_factory=list)
    perception_deltas: List[Delta] = field(default_factory=list)
    custom_deltas: List[Delta] = field(default_factory=list)
    intensity_profile: IntensityProfile = field(default_factory=IntensityProfile)
    occurrence_probability: float = 1.0
    is_active: bool = True


@dataclass
class ExecutionContext:
    """Context for event execution."""
    run_id: str
    current_tick: int
    rng_seed: int
    environment_state: Dict[str, Any] = field(default_factory=dict)
    agent_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def get_deterministic_random(self, event_id: str, agent_id: str = "") -> float:
        """Get a deterministic random value for an event/agent combination."""
        import hashlib
        combined = f"{self.rng_seed}:{self.current_tick}:{event_id}:{agent_id}"
        hash_bytes = hashlib.sha256(combined.encode()).digest()
        # Use first 8 bytes as float between 0 and 1
        value = int.from_bytes(hash_bytes[:8], 'big') / (2**64 - 1)
        return value


@dataclass
class DeltaApplication:
    """Record of a delta being applied."""
    variable: str
    operation: DeltaOperation
    old_value: Any
    new_value: Any
    applied_value: Any


@dataclass
class ExecutionResult:
    """Result of executing an event script."""
    event_id: str
    run_id: str
    executed_at_tick: int
    occurred: bool  # False if probability check failed
    affected_agent_ids: List[str] = field(default_factory=list)
    affected_regions: Set[str] = field(default_factory=set)
    affected_segments: Set[str] = field(default_factory=set)
    applied_intensity: float = 0.0
    environment_deltas_applied: List[DeltaApplication] = field(default_factory=list)
    agent_deltas_applied: Dict[str, List[DeltaApplication]] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def affected_agent_count(self) -> int:
        return len(self.affected_agent_ids)

    @property
    def affected_region_count(self) -> int:
        return len(self.affected_regions)

    @property
    def affected_segment_count(self) -> int:
        return len(self.affected_segments)


class EventExecutor:
    """
    Executes event scripts deterministically.

    This is the runtime component that applies pre-compiled events.
    No LLM involvement at runtime (C5 compliant).
    """

    def __init__(self):
        """Initialize the event executor."""
        self._condition_evaluators: Dict[str, Callable] = {}
        self._register_default_condition_evaluators()

    def _register_default_condition_evaluators(self) -> None:
        """Register default condition evaluators."""
        self._condition_evaluators["gte"] = lambda a, b: a >= b
        self._condition_evaluators["lte"] = lambda a, b: a <= b
        self._condition_evaluators["gt"] = lambda a, b: a > b
        self._condition_evaluators["lt"] = lambda a, b: a < b
        self._condition_evaluators["eq"] = lambda a, b: a == b
        self._condition_evaluators["neq"] = lambda a, b: a != b
        self._condition_evaluators["in"] = lambda a, b: a in b
        self._condition_evaluators["not_in"] = lambda a, b: a not in b
        self._condition_evaluators["contains"] = lambda a, b: b in a

    def register_condition_evaluator(
        self,
        name: str,
        evaluator: Callable[[Any, Any], bool]
    ) -> None:
        """Register a custom condition evaluator."""
        self._condition_evaluators[name] = evaluator

    def execute(
        self,
        event: EventScript,
        context: ExecutionContext,
        intensity_override: Optional[float] = None
    ) -> ExecutionResult:
        """
        Execute an event script in the given context.

        Args:
            event: The event script to execute
            context: Execution context with current state
            intensity_override: Optional intensity override (0-1)

        Returns:
            ExecutionResult with details of what was applied
        """
        result = ExecutionResult(
            event_id=event.event_id,
            run_id=context.run_id,
            executed_at_tick=context.current_tick,
            occurred=False
        )

        # Check if event is active
        if not event.is_active:
            return result

        # Check tick scope
        if not event.scope.is_active(context.current_tick):
            return result

        # Probability check (deterministic)
        if event.occurrence_probability < 1.0:
            random_val = context.get_deterministic_random(event.event_id)
            if random_val > event.occurrence_probability:
                return result

        result.occurred = True

        # Calculate intensity
        ticks_since_start = context.current_tick - (event.scope.start_tick or context.current_tick)
        intensity = intensity_override if intensity_override is not None else \
            event.intensity_profile.get_intensity(ticks_since_start)
        result.applied_intensity = intensity

        if intensity <= 0:
            return result

        # Apply environment deltas
        for delta in event.environment_deltas:
            if self._check_conditions(delta.conditions, context.environment_state):
                application = self._apply_delta(
                    delta, context.environment_state, intensity
                )
                if application:
                    result.environment_deltas_applied.append(application)

        # Apply perception/agent deltas
        for agent_id, agent_state in context.agent_states.items():
            # Check if agent is in scope
            agent_region = agent_state.get("region_id")
            agent_segment = agent_state.get("segment_id")

            if not event.scope.matches_agent(agent_id, agent_region, agent_segment):
                continue

            agent_applications = []

            # Apply perception deltas
            perception = agent_state.get("perception", {})
            for delta in event.perception_deltas:
                if self._check_conditions(delta.conditions, agent_state):
                    application = self._apply_delta(delta, perception, intensity)
                    if application:
                        agent_applications.append(application)

            # Apply custom deltas to agent state
            for delta in event.custom_deltas:
                if self._check_conditions(delta.conditions, agent_state):
                    application = self._apply_delta(delta, agent_state, intensity)
                    if application:
                        agent_applications.append(application)

            if agent_applications:
                result.affected_agent_ids.append(agent_id)
                result.agent_deltas_applied[agent_id] = agent_applications
                if agent_region:
                    result.affected_regions.add(agent_region)
                if agent_segment:
                    result.affected_segments.add(agent_segment)

        return result

    def execute_bundle(
        self,
        events: List[EventScript],
        context: ExecutionContext,
        joint_probability: float = 1.0,
        skip_probability_check: bool = False
    ) -> List[ExecutionResult]:
        """
        Execute a bundle of events atomically.

        Args:
            events: List of events to execute in order
            context: Execution context
            joint_probability: Combined probability of bundle
            skip_probability_check: If True, ignore probability

        Returns:
            List of execution results for each event
        """
        results = []

        # Bundle-level probability check
        if not skip_probability_check and joint_probability < 1.0:
            random_val = context.get_deterministic_random("bundle")
            if random_val > joint_probability:
                # Return non-occurred results for all events
                for event in events:
                    results.append(ExecutionResult(
                        event_id=event.event_id,
                        run_id=context.run_id,
                        executed_at_tick=context.current_tick,
                        occurred=False
                    ))
                return results

        # Execute each event in order
        for event in events:
            result = self.execute(event, context)
            results.append(result)

        return results

    def _check_conditions(
        self,
        conditions: Optional[Dict[str, Any]],
        state: Dict[str, Any]
    ) -> bool:
        """Check if conditions are met."""
        if not conditions:
            return True

        for key, condition in conditions.items():
            if isinstance(condition, dict):
                # Complex condition: {"op": "gte", "value": 0.5}
                op = condition.get("op", "eq")
                expected = condition.get("value")
                actual = self._get_nested_value(state, key)

                evaluator = self._condition_evaluators.get(op)
                if evaluator is None:
                    continue

                if not evaluator(actual, expected):
                    return False
            else:
                # Simple equality check
                actual = self._get_nested_value(state, key)
                if actual != condition:
                    return False

        return True

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get a nested value from a dict using dot notation."""
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _set_nested_value(
        self,
        data: Dict[str, Any],
        path: str,
        value: Any
    ) -> None:
        """Set a nested value in a dict using dot notation."""
        parts = path.split(".")
        current = data
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def _apply_delta(
        self,
        delta: Delta,
        state: Dict[str, Any],
        intensity: float
    ) -> Optional[DeltaApplication]:
        """Apply a delta to state."""
        old_value = self._get_nested_value(state, delta.variable)

        # Scale value by intensity for numeric operations
        applied_value = delta.value
        if isinstance(delta.value, (int, float)) and intensity < 1.0:
            if delta.operation in (DeltaOperation.ADD, DeltaOperation.MULTIPLY):
                # Scale the delta by intensity
                if delta.operation == DeltaOperation.ADD:
                    applied_value = delta.value * intensity
                # For multiply, interpolate toward 1.0
                elif delta.operation == DeltaOperation.MULTIPLY:
                    applied_value = 1.0 + (delta.value - 1.0) * intensity

        # Calculate new value based on operation
        if delta.operation == DeltaOperation.SET:
            new_value = applied_value
        elif delta.operation == DeltaOperation.ADD:
            if old_value is None:
                old_value = 0
            new_value = old_value + applied_value
        elif delta.operation == DeltaOperation.MULTIPLY:
            if old_value is None:
                old_value = 1
            new_value = old_value * applied_value
        elif delta.operation == DeltaOperation.MIN:
            if old_value is None:
                new_value = applied_value
            else:
                new_value = min(old_value, applied_value)
        elif delta.operation == DeltaOperation.MAX:
            if old_value is None:
                new_value = applied_value
            else:
                new_value = max(old_value, applied_value)
        else:
            return None

        # Apply the change
        self._set_nested_value(state, delta.variable, new_value)

        return DeltaApplication(
            variable=delta.variable,
            operation=delta.operation,
            old_value=old_value,
            new_value=new_value,
            applied_value=applied_value
        )


# =============================================================================
# Factory Functions
# =============================================================================

def create_event_from_dict(data: Dict[str, Any]) -> EventScript:
    """Create an EventScript from a dictionary (e.g., from database)."""
    scope_data = data.get("scope", {})
    scope = EventScope(
        affected_regions=scope_data.get("affected_regions"),
        affected_persona_segments=scope_data.get("affected_persona_segments"),
        target_agent_ids=scope_data.get("target_agent_ids"),
        start_tick=scope_data.get("start_tick"),
        end_tick=scope_data.get("end_tick"),
    )

    profile_data = data.get("intensity_profile", {})
    profile = IntensityProfile(
        profile_type=IntensityProfileType(profile_data.get("profile_type", "instantaneous")),
        initial_intensity=profile_data.get("initial_intensity", 1.0),
        decay_rate=profile_data.get("decay_rate"),
        half_life_ticks=profile_data.get("half_life_ticks"),
        lag_ticks=profile_data.get("lag_ticks"),
        custom_profile=profile_data.get("custom_profile"),
    )

    deltas_data = data.get("deltas", {})
    environment_deltas = [
        Delta(
            variable=d["variable"],
            operation=DeltaOperation(d.get("operation", "set")),
            value=d["value"],
            conditions=d.get("conditions"),
        )
        for d in deltas_data.get("environment_deltas", [])
    ]
    perception_deltas = [
        Delta(
            variable=d["variable"],
            operation=DeltaOperation(d.get("operation", "set")),
            value=d["value"],
            conditions=d.get("conditions"),
        )
        for d in deltas_data.get("perception_deltas", [])
    ]
    custom_deltas = [
        Delta(
            variable=d["variable"],
            operation=DeltaOperation(d.get("operation", "set")),
            value=d["value"],
            conditions=d.get("conditions"),
        )
        for d in deltas_data.get("custom_deltas", [])
    ]

    uncertainty_data = data.get("uncertainty", {})

    return EventScript(
        event_id=str(data.get("event_id", data.get("id", ""))),
        label=data.get("label", ""),
        event_type=data.get("event_type", "custom"),
        scope=scope,
        environment_deltas=environment_deltas,
        perception_deltas=perception_deltas,
        custom_deltas=custom_deltas,
        intensity_profile=profile,
        occurrence_probability=uncertainty_data.get("occurrence_probability", 1.0),
        is_active=data.get("is_active", True),
    )


# =============================================================================
# Singleton Executor Instance
# =============================================================================

_executor: Optional[EventExecutor] = None


def get_event_executor() -> EventExecutor:
    """Get the singleton event executor instance."""
    global _executor
    if _executor is None:
        _executor = EventExecutor()
    return _executor
