"""
Target Mode Service
Single-target, many possible futures engine.
Reference: project.md §11 Phase 5

Implements:
- P5-001: Target Persona Compiler
- P5-002: Action Space Definition
- P5-003: Constraint System
- P5-004: Path Planner
- P5-005: Path → Node Bridge
- P5-006: Target Mode Telemetry
"""

import logging
import time
import random
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4
from functools import lru_cache
import heapq

from sqlalchemy.orm import Session

from app.schemas.target_mode import (
    TargetPersona,
    TargetPersonaCreate,
    UtilityFunction,
    UtilityWeight,
    UtilityDimension,
    ActionDefinition,
    ActionPrior,
    ActionCatalog,
    ActionCategory,
    StateVector,
    StateCondition,
    StateEffect,
    Constraint,
    ConstraintType,
    ConstraintSet,
    Path,
    PathStep,
    PathCluster,
    PathStatus,
    PlanResult,
    PlanStatus,
    TargetPlanRequest,
    ExpandClusterRequest,
    BranchToNodeRequest,
)

logger = logging.getLogger(__name__)


# =============================================================================
# P5-001: Target Persona Compiler
# =============================================================================

class TargetPersonaCompiler:
    """
    Compiles Target persona with utility function, action priors, and state vector.
    Reference: project.md §11 Phase 5
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def compile_from_persona(
        self,
        persona_id: str,
        utility_weights: Optional[List[UtilityWeight]] = None,
        custom_actions: Optional[List[ActionDefinition]] = None,
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> TargetPersona:
        """
        Compile a Target from an existing PersonaRecord.

        Extracts:
        - Utility function from psychographics
        - Action priors from behavioral patterns
        - State vector from current context
        """
        # TODO: Fetch PersonaRecord from database
        # For now, create defaults

        # Build utility function from persona psychographics
        utility_function = self._infer_utility_function(persona_id)
        if utility_weights:
            utility_function.weights = utility_weights

        # Build action priors from behavioral patterns
        action_priors = self._infer_action_priors(persona_id)

        # Build initial state
        state = StateVector(variables=initial_state or {})

        target = TargetPersona(
            target_id=str(uuid4()),
            persona_id=persona_id,
            name=f"Target from {persona_id[:8]}",
            utility_function=utility_function,
            action_priors=action_priors,
            initial_state=state,
            custom_actions=custom_actions,
        )

        logger.info(f"Compiled Target persona {target.target_id} from persona {persona_id}")
        return target

    def compile_from_scratch(
        self,
        create_data: TargetPersonaCreate,
    ) -> TargetPersona:
        """Create a new Target persona from scratch."""
        target_id = str(uuid4())

        # Default utility function if not provided
        utility_function = create_data.utility_function or UtilityFunction(
            weights=[
                UtilityWeight(dimension=UtilityDimension.WEALTH, weight=0.3),
                UtilityWeight(dimension=UtilityDimension.SECURITY, weight=0.3),
                UtilityWeight(dimension=UtilityDimension.RELATIONSHIPS, weight=0.2),
                UtilityWeight(dimension=UtilityDimension.ACHIEVEMENT, weight=0.2),
            ]
        )

        # Initial state
        initial_state = StateVector(
            variables=create_data.initial_state or {}
        )

        target = TargetPersona(
            target_id=target_id,
            project_id=create_data.project_id,
            persona_id=create_data.persona_id,
            name=create_data.name,
            description=create_data.description,
            utility_function=utility_function,
            action_priors=create_data.action_priors or [],
            initial_state=initial_state,
            action_catalog_id=create_data.action_catalog_id,
            custom_actions=create_data.custom_actions,
            personal_constraints=create_data.personal_constraints,
            planning_horizon=create_data.planning_horizon,
            discount_factor=create_data.discount_factor,
            exploration_rate=create_data.exploration_rate,
            domain=create_data.domain,
            tags=create_data.tags,
        )

        logger.info(f"Created new Target persona {target_id}")
        return target

    def _infer_utility_function(self, persona_id: str) -> UtilityFunction:
        """Infer utility function from persona psychographics."""
        # TODO: Fetch persona and analyze psychographics
        # For now, return balanced defaults
        return UtilityFunction(
            weights=[
                UtilityWeight(dimension=UtilityDimension.WEALTH, weight=0.25),
                UtilityWeight(dimension=UtilityDimension.SECURITY, weight=0.25),
                UtilityWeight(dimension=UtilityDimension.RELATIONSHIPS, weight=0.25),
                UtilityWeight(dimension=UtilityDimension.ACHIEVEMENT, weight=0.25),
            ],
            risk_aversion=0.5,
            time_preference=0.5,
            loss_aversion=2.0,
        )

    def _infer_action_priors(self, persona_id: str) -> List[ActionPrior]:
        """Infer action priors from persona behavioral patterns."""
        # TODO: Analyze persona behavioral patterns
        return []


# =============================================================================
# P5-002: Action Space Definition
# =============================================================================

class ActionSpace:
    """
    Manages available actions and their definitions.
    Reference: project.md §11 Phase 5
    """

    # Default action catalogs per domain
    DEFAULT_CATALOGS: Dict[str, List[ActionDefinition]] = {
        "consumer": [
            ActionDefinition(
                action_id="purchase_product",
                name="Purchase Product",
                category=ActionCategory.CONSUMPTION,
                preconditions=[
                    StateCondition(variable="budget", operator="gte", value=0)
                ],
                effects=[
                    StateEffect(variable="budget", operation="add", value=-100),
                    StateEffect(variable="satisfaction", operation="add", value=10),
                ],
                monetary_cost=100.0,
                risk_level=0.1,
            ),
            ActionDefinition(
                action_id="switch_brand",
                name="Switch Brand",
                category=ActionCategory.CONSUMPTION,
                effects=[
                    StateEffect(variable="brand_loyalty", operation="set", value=0),
                    StateEffect(variable="exploration", operation="add", value=1),
                ],
                social_cost=-0.1,
                risk_level=0.2,
            ),
            ActionDefinition(
                action_id="recommend_to_friend",
                name="Recommend to Friend",
                category=ActionCategory.SOCIAL,
                preconditions=[
                    StateCondition(variable="satisfaction", operator="gte", value=7)
                ],
                effects=[
                    StateEffect(variable="social_capital", operation="add", value=1),
                    StateEffect(variable="network_influence", operation="add", value=0.1),
                ],
                social_cost=0.1,
            ),
            ActionDefinition(
                action_id="write_review",
                name="Write Review",
                category=ActionCategory.COMMUNICATION,
                effects=[
                    StateEffect(variable="reputation", operation="add", value=1),
                ],
                time_cost=0.5,
            ),
            ActionDefinition(
                action_id="compare_alternatives",
                name="Compare Alternatives",
                category=ActionCategory.CONSUMPTION,
                effects=[
                    StateEffect(variable="knowledge", operation="add", value=1),
                ],
                time_cost=1.0,
            ),
        ],
        "financial": [
            ActionDefinition(
                action_id="invest",
                name="Make Investment",
                category=ActionCategory.FINANCIAL,
                preconditions=[
                    StateCondition(variable="liquid_assets", operator="gte", value=1000)
                ],
                effects=[
                    StateEffect(variable="liquid_assets", operation="add", value=-1000),
                    StateEffect(variable="investments", operation="add", value=1000),
                ],
                risk_level=0.3,
                reversibility=0.7,
            ),
            ActionDefinition(
                action_id="save",
                name="Add to Savings",
                category=ActionCategory.FINANCIAL,
                effects=[
                    StateEffect(variable="income", operation="add", value=-100),
                    StateEffect(variable="savings", operation="add", value=100),
                ],
                risk_level=0.0,
            ),
            ActionDefinition(
                action_id="take_loan",
                name="Take Loan",
                category=ActionCategory.FINANCIAL,
                effects=[
                    StateEffect(variable="liquid_assets", operation="add", value=5000),
                    StateEffect(variable="debt", operation="add", value=5500),
                ],
                risk_level=0.4,
                reversibility=0.3,
            ),
        ],
        "career": [
            ActionDefinition(
                action_id="apply_job",
                name="Apply for New Job",
                category=ActionCategory.PROFESSIONAL,
                effects=[
                    StateEffect(variable="job_applications", operation="add", value=1),
                ],
                time_cost=2.0,
                effort_cost=0.3,
            ),
            ActionDefinition(
                action_id="negotiate_salary",
                name="Negotiate Salary",
                category=ActionCategory.PROFESSIONAL,
                preconditions=[
                    StateCondition(variable="tenure_months", operator="gte", value=12)
                ],
                effects=[
                    StateEffect(variable="salary", operation="multiply", value=1.1, probability=0.5),
                ],
                social_cost=-0.2,
                risk_level=0.2,
            ),
            ActionDefinition(
                action_id="take_course",
                name="Take Training Course",
                category=ActionCategory.PROFESSIONAL,
                effects=[
                    StateEffect(variable="skills", operation="add", value=1),
                    StateEffect(variable="knowledge", operation="add", value=2),
                ],
                monetary_cost=500.0,
                time_cost=40.0,
            ),
        ],
    }

    def __init__(self, domain: Optional[str] = None):
        self.domain = domain
        self._custom_actions: List[ActionDefinition] = []
        self._loaded_catalogs: Dict[str, ActionCatalog] = {}

    def get_available_actions(
        self,
        target: TargetPersona,
        current_state: StateVector,
    ) -> List[ActionDefinition]:
        """Get all actions available to target in current state."""
        actions = []

        # Get domain catalog
        if self.domain and self.domain in self.DEFAULT_CATALOGS:
            actions.extend(self.DEFAULT_CATALOGS[self.domain])

        # Add custom actions from target
        if target.custom_actions:
            actions.extend(target.custom_actions)

        # Add any loaded catalogs
        for catalog in self._loaded_catalogs.values():
            actions.extend(catalog.actions)

        # Filter by preconditions
        available = []
        for action in actions:
            if self._check_preconditions(action, current_state):
                available.append(action)

        return available

    def _check_preconditions(
        self,
        action: ActionDefinition,
        state: StateVector,
    ) -> bool:
        """Check if action preconditions are met."""
        for condition in action.preconditions:
            value = state.get(condition.variable)
            if value is None:
                return False

            if not self._evaluate_condition(condition, value):
                return False

        return True

    def _evaluate_condition(self, condition: StateCondition, value: Any) -> bool:
        """Evaluate a state condition."""
        ops = {
            "eq": lambda v, t: v == t,
            "ne": lambda v, t: v != t,
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
            "in": lambda v, t: v in t,
            "not_in": lambda v, t: v not in t,
        }

        op_func = ops.get(condition.operator)
        if op_func:
            try:
                return op_func(value, condition.value)
            except (TypeError, ValueError):
                return False
        return False

    def add_custom_actions(self, actions: List[ActionDefinition]) -> None:
        """Add custom actions to the space."""
        self._custom_actions.extend(actions)

    def load_catalog(self, catalog: ActionCatalog) -> None:
        """Load an action catalog."""
        self._loaded_catalogs[catalog.catalog_id] = catalog


# =============================================================================
# P5-003: Constraint System
# =============================================================================

class ConstraintChecker:
    """
    Evaluates constraints for path pruning.
    Reference: project.md §11 Phase 5
    """

    def __init__(self, constraints: Optional[List[Constraint]] = None):
        self.constraints = constraints or []
        self._hard_constraints = [c for c in self.constraints if c.constraint_type == ConstraintType.HARD]
        self._soft_constraints = [c for c in self.constraints if c.constraint_type == ConstraintType.SOFT]

    def add_constraint(self, constraint: Constraint) -> None:
        """Add a constraint."""
        self.constraints.append(constraint)
        if constraint.constraint_type == ConstraintType.HARD:
            self._hard_constraints.append(constraint)
        else:
            self._soft_constraints.append(constraint)

    def check_hard_constraints(
        self,
        state: StateVector,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check hard constraints. Returns (is_valid, violation_reason).
        """
        for constraint in self._hard_constraints:
            value = state.get(constraint.condition.variable)
            if value is None:
                continue

            if self._evaluate_condition(constraint.condition, value):
                # Constraint condition is TRUE, meaning violation
                return False, constraint.violation_explanation or f"Violated: {constraint.name}"

        return True, None

    def calculate_soft_penalty(
        self,
        state: StateVector,
    ) -> Tuple[float, List[str]]:
        """
        Calculate penalty from soft constraints.
        Returns (total_penalty, list of violated constraint names).
        """
        total_penalty = 0.0
        violated = []

        for constraint in self._soft_constraints:
            value = state.get(constraint.condition.variable)
            if value is None:
                continue

            if self._evaluate_condition(constraint.condition, value):
                penalty = constraint.penalty_weight or 0.1
                total_penalty += penalty
                violated.append(constraint.name)

        return total_penalty, violated

    def _evaluate_condition(self, condition: StateCondition, value: Any) -> bool:
        """Evaluate a constraint condition (returns True if violated)."""
        ops = {
            "eq": lambda v, t: v == t,
            "ne": lambda v, t: v != t,
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
        }

        op_func = ops.get(condition.operator)
        if op_func:
            try:
                return op_func(value, condition.value)
            except (TypeError, ValueError):
                return False
        return False


# =============================================================================
# P5-004: Path Planner
# =============================================================================

class PathPlanner:
    """
    Generates paths with pruning and clustering.
    Reference: project.md §11 Phase 5

    Uses beam search with constraint checking.
    """

    def __init__(
        self,
        target: TargetPersona,
        action_space: ActionSpace,
        constraint_checker: ConstraintChecker,
        seed: Optional[int] = None,
    ):
        self.target = target
        self.action_space = action_space
        self.constraint_checker = constraint_checker
        self.rng = random.Random(seed)

    def plan(
        self,
        request: TargetPlanRequest,
    ) -> PlanResult:
        """
        Generate paths for the target.

        Uses beam search to explore action space while respecting constraints.
        """
        start_time = time.time()
        plan_id = str(uuid4())

        logger.info(f"Starting path planning for target {request.target_id}")

        # Initialize
        initial_state = self.target.initial_state.copy()
        if request.environment_state:
            for k, v in request.environment_state.items():
                initial_state.set(k, v)

        # Generate paths using beam search
        all_paths: List[Path] = []
        pruned_paths: List[Path] = []
        prune_counts: Dict[str, int] = {}

        # §4.2 Search counters for Evidence Pack
        explored_states: set = set()  # Unique state vectors explored
        expanded_nodes: int = 0  # Total node expansions

        # Priority queue: (negative_utility, path)
        beam: List[Tuple[float, Path]] = []

        # Create initial path
        initial_path = Path(
            path_id=str(uuid4()),
            steps=[],
            path_probability=1.0,
            success_probability=1.0,
            total_utility=0.0,
        )
        heapq.heappush(beam, (0.0, initial_path))

        # Beam search
        beam_width = min(request.max_paths, 50)
        paths_generated = 0

        while beam and paths_generated < request.max_paths:
            # Pop best path
            neg_util, current_path = heapq.heappop(beam)

            # Check depth limit
            if len(current_path.steps) >= request.max_depth:
                all_paths.append(current_path)
                paths_generated += 1
                continue

            # Get current state
            if current_path.steps:
                current_state = StateVector(variables=current_path.steps[-1].state_after.copy())
            else:
                current_state = initial_state.copy()

            # §4.2 Track explored states (hash of state vector)
            state_hash = hash(frozenset(current_state.variables.items()))
            explored_states.add(state_hash)

            # Check hard constraints
            is_valid, violation = self.constraint_checker.check_hard_constraints(current_state)
            if not is_valid:
                current_path.status = PathStatus.PRUNED
                current_path.pruning_reason = violation
                pruned_paths.append(current_path)
                prune_counts[violation or "unknown"] = prune_counts.get(violation or "unknown", 0) + 1
                continue

            # Get available actions
            available_actions = self.action_space.get_available_actions(self.target, current_state)

            if not available_actions:
                # Terminal state
                all_paths.append(current_path)
                paths_generated += 1
                continue

            # Expand with each action
            expansions = 0
            for action in available_actions:
                if expansions >= 5:  # Limit branching factor
                    break

                # §4.2 Track node expansion
                expanded_nodes += 1

                # Apply action
                new_path, new_state = self._apply_action(current_path, action, current_state)

                # Check probability threshold
                if new_path.path_probability < request.pruning_threshold:
                    new_path.status = PathStatus.PRUNED
                    new_path.pruning_reason = "Below probability threshold"
                    pruned_paths.append(new_path)
                    continue

                # Calculate soft constraint penalty
                penalty, _ = self.constraint_checker.calculate_soft_penalty(new_state)

                # Calculate utility
                utility = self._calculate_utility(action, new_state)
                adjusted_utility = utility * (1 - penalty)

                new_path.total_utility = current_path.total_utility + adjusted_utility

                # Add to beam
                heapq.heappush(beam, (-new_path.total_utility, new_path))
                expansions += 1

            # Limit beam width
            while len(beam) > beam_width:
                heapq.heappop(beam)

        # Collect remaining paths from beam
        while beam:
            _, path = heapq.heappop(beam)
            all_paths.append(path)
            paths_generated += 1
            if paths_generated >= request.max_paths:
                break

        # Sort by utility
        all_paths.sort(key=lambda p: p.total_utility, reverse=True)

        # Cluster paths if enabled
        clusters: List[PathCluster] = []
        if request.enable_clustering and len(all_paths) > 1:
            clusters = self._cluster_paths(all_paths, request.max_clusters)
        else:
            # Create single cluster with all paths
            if all_paths:
                clusters = [PathCluster(
                    cluster_id=str(uuid4()),
                    label="All Paths",
                    representative_path=all_paths[0],
                    child_paths=all_paths[1:] if len(all_paths) > 1 else [],
                    aggregated_probability=sum(p.path_probability for p in all_paths),
                    avg_utility=sum(p.total_utility for p in all_paths) / len(all_paths),
                    utility_range=(
                        min(p.total_utility for p in all_paths),
                        max(p.total_utility for p in all_paths),
                    ),
                )]

        # Build result
        planning_time = int((time.time() - start_time) * 1000)

        result = PlanResult(
            plan_id=plan_id,
            target_id=request.target_id,
            project_id=request.project_id,
            status=PlanStatus.COMPLETED,
            total_paths_generated=len(all_paths) + len(pruned_paths),
            total_paths_valid=len(all_paths),
            total_paths_pruned=len(pruned_paths),
            clusters=clusters,
            top_paths=all_paths[:10],
            hard_constraints_applied=[c.name for c in self.constraint_checker._hard_constraints],
            soft_constraints_applied=[c.name for c in self.constraint_checker._soft_constraints],
            paths_pruned_by_constraint=prune_counts,
            planning_time_ms=planning_time,
            # §4.2 Search counters for Evidence Pack
            explored_states_count=len(explored_states),
            expanded_nodes_count=expanded_nodes,
            completed_at=datetime.utcnow(),
        )

        # Generate summary
        result.planning_summary = self._generate_summary(result)

        logger.info(
            f"Path planning complete: {len(all_paths)} valid paths, "
            f"{len(pruned_paths)} pruned, {len(clusters)} clusters"
        )

        return result

    def _apply_action(
        self,
        current_path: Path,
        action: ActionDefinition,
        current_state: StateVector,
    ) -> Tuple[Path, StateVector]:
        """Apply an action and create new path state."""
        new_state = current_state.copy()

        # Apply effects
        effects_applied = []
        for effect in action.effects:
            if self.rng.random() <= effect.probability:
                self._apply_effect(effect, new_state)
                effects_applied.append(effect)

        # Calculate step probability
        step_prob = (1 - action.failure_probability) * action.effects[0].probability if action.effects else 1.0

        # Create step
        step = PathStep(
            step_index=len(current_path.steps),
            action=action,
            state_before=current_state.variables.copy(),
            state_after=new_state.variables.copy(),
            effects_applied=effects_applied,
            utility_gained=0.0,  # Calculated later
            cumulative_utility=current_path.total_utility,
            probability=step_prob,
        )

        # Create new path
        new_path = Path(
            path_id=str(uuid4()),
            steps=current_path.steps + [step],
            path_probability=current_path.path_probability * step_prob,
            success_probability=current_path.success_probability * step_prob,
            total_utility=current_path.total_utility,
            total_cost=current_path.total_cost + action.monetary_cost,
            total_time=current_path.total_time + (action.time_cost or 0),
            total_risk=max(current_path.total_risk, action.risk_level),
        )

        return new_path, new_state

    def _apply_effect(self, effect: StateEffect, state: StateVector) -> None:
        """Apply a state effect."""
        current = state.get(effect.variable, 0)

        if effect.operation == "set":
            state.set(effect.variable, effect.value)
        elif effect.operation == "add":
            state.set(effect.variable, current + effect.value)
        elif effect.operation == "multiply":
            state.set(effect.variable, current * effect.value)
        elif effect.operation == "append":
            if isinstance(current, list):
                current.append(effect.value)
                state.set(effect.variable, current)
        elif effect.operation == "remove":
            if isinstance(current, list) and effect.value in current:
                current.remove(effect.value)
                state.set(effect.variable, current)

    def _calculate_utility(
        self,
        action: ActionDefinition,
        state: StateVector,
    ) -> float:
        """Calculate utility gained from action."""
        utility = 0.0

        # Map action effects to utility dimensions
        for weight in self.target.utility_function.weights:
            dim = weight.dimension
            dim_value = state.get(dim.value, 0)

            if isinstance(dim_value, (int, float)):
                contribution = dim_value * weight.weight
                utility += contribution

        # Apply risk aversion
        risk_penalty = action.risk_level * self.target.utility_function.risk_aversion
        utility *= (1 - risk_penalty)

        # Apply time preference (discount future)
        time_discount = self.target.discount_factor ** (action.time_cost or 0)
        utility *= time_discount

        return utility

    def _cluster_paths(
        self,
        paths: List[Path],
        max_clusters: int,
    ) -> List[PathCluster]:
        """Cluster similar paths."""
        if len(paths) <= max_clusters:
            # Each path is its own cluster
            return [
                PathCluster(
                    cluster_id=str(uuid4()),
                    label=f"Path {i+1}",
                    representative_path=path,
                    child_paths=[],
                    aggregated_probability=path.path_probability,
                    avg_utility=path.total_utility,
                    utility_range=(path.total_utility, path.total_utility),
                )
                for i, path in enumerate(paths)
            ]

        # Simple clustering by utility ranges
        clusters: List[PathCluster] = []

        # Sort by utility
        sorted_paths = sorted(paths, key=lambda p: p.total_utility, reverse=True)

        # Divide into clusters
        chunk_size = max(1, len(sorted_paths) // max_clusters)

        for i in range(0, len(sorted_paths), chunk_size):
            chunk = sorted_paths[i:i + chunk_size]
            if not chunk:
                continue

            # Representative is highest utility in chunk
            representative = chunk[0]
            representative.is_representative = True
            representative.cluster_id = str(uuid4())

            # Assign cluster ID to children
            for path in chunk[1:]:
                path.cluster_id = representative.cluster_id

            # Common actions
            if chunk:
                first_actions = set(s.action.action_id for s in chunk[0].steps) if chunk[0].steps else set()
                common_actions = first_actions
                for path in chunk[1:]:
                    path_actions = set(s.action.action_id for s in path.steps) if path.steps else set()
                    common_actions = common_actions.intersection(path_actions)
            else:
                common_actions = set()

            cluster = PathCluster(
                cluster_id=representative.cluster_id,
                label=self._generate_cluster_label(chunk),
                representative_path=representative,
                child_paths=chunk[1:] if len(chunk) > 1 else [],
                aggregated_probability=sum(p.path_probability for p in chunk),
                avg_utility=sum(p.total_utility for p in chunk) / len(chunk),
                utility_range=(
                    min(p.total_utility for p in chunk),
                    max(p.total_utility for p in chunk),
                ),
                common_actions=list(common_actions) if common_actions else None,
            )
            clusters.append(cluster)

            if len(clusters) >= max_clusters:
                break

        return clusters

    def _generate_cluster_label(self, paths: List[Path]) -> str:
        """Generate human-readable cluster label."""
        if not paths or not paths[0].steps:
            return "Empty Path"

        first_actions = [s.action.name for s in paths[0].steps[:3]]
        return " → ".join(first_actions) if first_actions else "Path Cluster"

    def _generate_summary(self, result: PlanResult) -> str:
        """Generate natural language summary of planning result."""
        if not result.clusters:
            return "No feasible paths found."

        top_cluster = result.clusters[0]
        summary_parts = [
            f"Found {result.total_paths_valid} valid paths across {len(result.clusters)} clusters.",
        ]

        if top_cluster.representative_path.steps:
            first_action = top_cluster.representative_path.steps[0].action.name
            summary_parts.append(f"Most promising approach starts with '{first_action}'.")

        if result.paths_pruned_by_constraint:
            total_pruned = sum(result.paths_pruned_by_constraint.values())
            summary_parts.append(f"{total_pruned} paths pruned by constraints.")

        return " ".join(summary_parts)


# =============================================================================
# P5-005: Path → Node Bridge
# =============================================================================

class PathNodeBridge:
    """
    Converts selected path into Universe Map node/branch.
    Reference: project.md §11 Phase 5
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def create_node_from_path(
        self,
        request: BranchToNodeRequest,
        path: Path,
        target: TargetPersona,
        plan: PlanResult,
    ) -> Dict[str, Any]:
        """
        Create a Universe Map node from a selected path.

        Returns node data for insertion into Node table.
        """
        node_id = str(uuid4())

        # Extract variable deltas from path
        variable_deltas = {}
        if path.steps:
            initial_state = path.steps[0].state_before
            final_state = path.steps[-1].state_after

            for key in set(initial_state.keys()) | set(final_state.keys()):
                old_val = initial_state.get(key)
                new_val = final_state.get(key)
                if old_val != new_val:
                    variable_deltas[key] = {
                        "before": old_val,
                        "after": new_val,
                        "delta": new_val - old_val if isinstance(new_val, (int, float)) and isinstance(old_val, (int, float)) else None
                    }

        # Build node data
        node_data = {
            "node_id": node_id,
            "parent_node_id": request.parent_node_id,
            "label": request.label or f"Target Path: {path.path_id[:8]}",
            "source": "target_mode",

            # Outcome fields
            "probability": path.path_probability,
            "predicted_outcome": {
                "utility": path.total_utility,
                "cost": path.total_cost,
                "time": path.total_time,
                "risk": path.total_risk,
                "final_state": path.steps[-1].state_after if path.steps else {},
            },

            # Target mode specific
            "target_mode_data": {
                "plan_id": request.plan_id,
                "path_id": request.path_id,
                "target_id": target.target_id,
                "target_name": target.name,
                "action_sequence": [
                    {
                        "action_id": step.action.action_id,
                        "action_name": step.action.name,
                        "step_index": step.step_index,
                        "probability": step.probability,
                    }
                    for step in path.steps
                ],
                "variable_deltas": variable_deltas,
            },

            # Fork info
            "fork_reason": f"Target Mode path selection from plan {request.plan_id[:8]}",
            "created_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Created node {node_id} from path {path.path_id}")
        return node_data


# =============================================================================
# P5-006: Target Mode Telemetry
# =============================================================================

class TargetModeTelemetry:
    """
    Logs action sequences and trigger conditions for Target Mode.
    Reference: project.md §11 Phase 5
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self._logs: List[Dict[str, Any]] = []

    def log_plan_start(
        self,
        plan_id: str,
        target_id: str,
        request: TargetPlanRequest,
    ) -> None:
        """Log start of planning."""
        self._logs.append({
            "event_type": "plan_start",
            "plan_id": plan_id,
            "target_id": target_id,
            "max_paths": request.max_paths,
            "max_depth": request.max_depth,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def log_path_generated(
        self,
        plan_id: str,
        path: Path,
    ) -> None:
        """Log path generation."""
        self._logs.append({
            "event_type": "path_generated",
            "plan_id": plan_id,
            "path_id": path.path_id,
            "steps": len(path.steps),
            "probability": path.path_probability,
            "utility": path.total_utility,
            "status": path.status.value,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def log_path_pruned(
        self,
        plan_id: str,
        path: Path,
        reason: str,
    ) -> None:
        """Log path pruning."""
        self._logs.append({
            "event_type": "path_pruned",
            "plan_id": plan_id,
            "path_id": path.path_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def log_action_taken(
        self,
        plan_id: str,
        path_id: str,
        step: PathStep,
    ) -> None:
        """Log action taken in a path."""
        self._logs.append({
            "event_type": "action_taken",
            "plan_id": plan_id,
            "path_id": path_id,
            "step_index": step.step_index,
            "action_id": step.action.action_id,
            "action_name": step.action.name,
            "probability": step.probability,
            "utility_gained": step.utility_gained,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def log_constraint_check(
        self,
        plan_id: str,
        constraint_name: str,
        result: bool,
        state_snapshot: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log constraint evaluation."""
        self._logs.append({
            "event_type": "constraint_check",
            "plan_id": plan_id,
            "constraint_name": constraint_name,
            "passed": result,
            "state_snapshot": state_snapshot,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def log_plan_complete(
        self,
        result: PlanResult,
    ) -> None:
        """Log planning completion."""
        self._logs.append({
            "event_type": "plan_complete",
            "plan_id": result.plan_id,
            "status": result.status.value,
            "total_paths": result.total_paths_generated,
            "valid_paths": result.total_paths_valid,
            "pruned_paths": result.total_paths_pruned,
            "clusters": len(result.clusters),
            "planning_time_ms": result.planning_time_ms,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_logs(self, plan_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get telemetry logs, optionally filtered by plan."""
        if plan_id:
            return [log for log in self._logs if log.get("plan_id") == plan_id]
        return self._logs.copy()

    def get_action_sequence(self, plan_id: str, path_id: str) -> List[Dict[str, Any]]:
        """Get action sequence for a specific path."""
        return [
            log for log in self._logs
            if log.get("plan_id") == plan_id
            and log.get("path_id") == path_id
            and log.get("event_type") == "action_taken"
        ]


# =============================================================================
# Main Target Mode Service
# =============================================================================

class TargetModeService:
    """
    Main service orchestrating Target Mode operations.
    Reference: project.md §11 Phase 5
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.persona_compiler = TargetPersonaCompiler(db)
        self.bridge = PathNodeBridge(db)
        self.telemetry = TargetModeTelemetry(db)

        # Cache for targets and plans
        self._targets: Dict[str, TargetPersona] = {}
        self._plans: Dict[str, PlanResult] = {}

    def create_target(self, create_data: TargetPersonaCreate) -> TargetPersona:
        """Create a new target persona."""
        target = self.persona_compiler.compile_from_scratch(create_data)
        self._targets[target.target_id] = target
        return target

    def get_target(self, target_id: str) -> Optional[TargetPersona]:
        """Get a target persona."""
        return self._targets.get(target_id)

    def list_targets(self, project_id: str) -> List[TargetPersona]:
        """List all target personas for a project."""
        return [
            target for target in self._targets.values()
            if target.project_id == project_id
        ]

    def run_planner(self, request: TargetPlanRequest) -> PlanResult:
        """Run the path planner for a target."""
        target = self._targets.get(request.target_id)
        if not target:
            return PlanResult(
                plan_id=str(uuid4()),
                target_id=request.target_id,
                project_id=request.project_id,
                status=PlanStatus.FAILED,
                error_message=f"Target {request.target_id} not found",
            )

        # Log start
        plan_id = str(uuid4())
        self.telemetry.log_plan_start(plan_id, request.target_id, request)

        # Build action space
        action_space = ActionSpace(domain=target.domain)
        if target.custom_actions:
            action_space.add_custom_actions(target.custom_actions)

        # Build constraint checker
        constraints = target.personal_constraints or []
        if request.additional_constraints:
            constraints.extend(request.additional_constraints)

        constraint_checker = ConstraintChecker(constraints)

        # Run planner
        planner = PathPlanner(target, action_space, constraint_checker)
        result = planner.plan(request)

        # Log completion
        self.telemetry.log_plan_complete(result)

        # Cache result
        self._plans[result.plan_id] = result

        return result

    def get_plan(self, plan_id: str) -> Optional[PlanResult]:
        """Get a plan result."""
        return self._plans.get(plan_id)

    def expand_cluster(self, request: ExpandClusterRequest) -> Optional[PathCluster]:
        """Expand a path cluster to reveal child paths."""
        plan = self._plans.get(request.plan_id)
        if not plan:
            return None

        for cluster in plan.clusters:
            if cluster.cluster_id == request.cluster_id:
                cluster.is_expanded = True
                cluster.expansion_depth += 1
                return cluster

        return None

    def branch_to_node(self, request: BranchToNodeRequest) -> Optional[Dict[str, Any]]:
        """Create a Universe Map node from a selected path."""
        plan = self._plans.get(request.plan_id)
        if not plan:
            return None

        # Find the path
        path = None
        for p in plan.top_paths:
            if p.path_id == request.path_id:
                path = p
                break

        if not path:
            for cluster in plan.clusters:
                if cluster.representative_path.path_id == request.path_id:
                    path = cluster.representative_path
                    break
                for cp in cluster.child_paths:
                    if cp.path_id == request.path_id:
                        path = cp
                        break
                if path:
                    break

        if not path:
            return None

        target = self._targets.get(plan.target_id)
        if not target:
            return None

        return self.bridge.create_node_from_path(request, path, target, plan)

    def get_telemetry(self, plan_id: str) -> List[Dict[str, Any]]:
        """Get telemetry logs for a plan."""
        return self.telemetry.get_logs(plan_id)


# =============================================================================
# Factory function
# =============================================================================

@lru_cache()
def get_target_mode_service() -> TargetModeService:
    """Get singleton Target Mode service."""
    return TargetModeService()
