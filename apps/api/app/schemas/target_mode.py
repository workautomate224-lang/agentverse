"""
Target Mode Schemas
Schemas for Target Mode Engine - single-target, many possible futures.
Reference: project.md §11 Phase 5, Interaction_design.md §5.13
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Enums
# =============================================================================

class UtilityDimension(str, Enum):
    """Dimensions of utility function."""
    WEALTH = "wealth"
    STATUS = "status"
    SECURITY = "security"
    FREEDOM = "freedom"
    RELATIONSHIPS = "relationships"
    HEALTH = "health"
    ACHIEVEMENT = "achievement"
    COMFORT = "comfort"
    POWER = "power"
    KNOWLEDGE = "knowledge"
    PLEASURE = "pleasure"
    REPUTATION = "reputation"
    CUSTOM = "custom"


class ConstraintType(str, Enum):
    """Types of constraints."""
    HARD = "hard"  # Eliminates invalid paths
    SOFT = "soft"  # Adjusts probabilities


class ActionCategory(str, Enum):
    """Categories of actions."""
    FINANCIAL = "financial"
    SOCIAL = "social"
    PROFESSIONAL = "professional"
    PERSONAL = "personal"
    CONSUMPTION = "consumption"
    COMMUNICATION = "communication"
    MOVEMENT = "movement"
    LEGAL = "legal"
    HEALTH = "health"
    CUSTOM = "custom"


class PlanStatus(str, Enum):
    """Status of a planning job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PathStatus(str, Enum):
    """Status of a path."""
    VALID = "valid"
    PRUNED = "pruned"
    SELECTED = "selected"
    EXECUTED = "executed"


# =============================================================================
# Utility Function Schemas
# =============================================================================

class UtilityWeight(BaseModel):
    """Weight for a utility dimension."""
    dimension: UtilityDimension
    weight: float = Field(..., ge=0.0, le=1.0, description="Importance weight 0-1")
    target_value: Optional[float] = Field(None, description="Target value if applicable")
    threshold_min: Optional[float] = Field(None, description="Minimum acceptable value")
    threshold_max: Optional[float] = Field(None, description="Maximum acceptable value")


class UtilityFunction(BaseModel):
    """
    Utility function defining what the target wants to optimize.
    Reference: project.md §11 Phase 5
    """
    weights: List[UtilityWeight] = Field(default_factory=list)
    risk_aversion: float = Field(0.5, ge=0.0, le=1.0, description="Risk aversion level 0-1")
    time_preference: float = Field(0.5, ge=0.0, le=1.0, description="Preference for immediate vs delayed gratification")
    loss_aversion: float = Field(2.0, ge=1.0, le=5.0, description="Loss aversion coefficient (typically 2.0-2.5)")
    custom_objectives: Optional[Dict[str, float]] = Field(None, description="Custom objective dimensions")

    @field_validator('weights')
    @classmethod
    def validate_weights_sum(cls, v: List[UtilityWeight]) -> List[UtilityWeight]:
        if v:
            total = sum(w.weight for w in v)
            if abs(total - 1.0) > 0.01:
                # Normalize weights
                for w in v:
                    w.weight = w.weight / total
        return v


# =============================================================================
# Action Schemas
# =============================================================================

class StateCondition(BaseModel):
    """A condition on the state."""
    variable: str = Field(..., description="Variable name in state")
    operator: str = Field(..., description="Comparison operator: eq, ne, gt, lt, gte, lte, in, not_in")
    value: Any = Field(..., description="Value to compare against")


class StateEffect(BaseModel):
    """Effect of an action on state."""
    variable: str = Field(..., description="Variable to modify")
    operation: str = Field(..., description="Operation: set, add, multiply, append, remove")
    value: Any = Field(..., description="Value for operation")
    probability: float = Field(1.0, ge=0.0, le=1.0, description="Probability this effect occurs")


class ActionPrior(BaseModel):
    """Prior probability/propensity for an action."""
    action_id: str = Field(..., description="Action identifier")
    base_probability: float = Field(..., ge=0.0, le=1.0, description="Base probability of taking action")
    context_modifiers: Optional[Dict[str, float]] = Field(None, description="Modifiers based on context")


class ActionDefinition(BaseModel):
    """
    Definition of an action the target can take.
    Reference: project.md §11 Phase 5
    """
    action_id: str = Field(..., description="Unique action identifier")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Detailed description")
    category: ActionCategory = Field(ActionCategory.CUSTOM)

    # Preconditions
    preconditions: List[StateCondition] = Field(default_factory=list, description="Conditions required to take action")

    # Effects
    effects: List[StateEffect] = Field(default_factory=list, description="Effects on state")

    # Costs
    monetary_cost: float = Field(0.0, description="Monetary cost")
    time_cost: float = Field(0.0, description="Time cost in hours")
    effort_cost: float = Field(0.0, ge=0.0, le=1.0, description="Effort/energy cost 0-1")
    social_cost: float = Field(0.0, ge=-1.0, le=1.0, description="Social capital cost (-1 to 1)")
    opportunity_cost: float = Field(0.0, description="Opportunity cost")

    # Risk
    risk_level: float = Field(0.0, ge=0.0, le=1.0, description="Risk level 0-1")
    failure_probability: float = Field(0.0, ge=0.0, le=1.0, description="Probability of failure")
    reversibility: float = Field(1.0, ge=0.0, le=1.0, description="How reversible 0-1")

    # Timing
    duration: Optional[float] = Field(None, description="Duration in hours")
    cooldown: Optional[float] = Field(None, description="Minimum time before action can be repeated")

    # Dependencies
    requires_actions: Optional[List[str]] = Field(None, description="Actions that must precede this")
    blocks_actions: Optional[List[str]] = Field(None, description="Actions blocked while this is active")

    # Metadata
    tags: Optional[List[str]] = Field(None)
    domain_specific: Optional[Dict[str, Any]] = Field(None)


class ActionCatalog(BaseModel):
    """Catalog of available actions for a domain."""
    catalog_id: str
    domain: str
    version: str = "1.0.0"
    actions: List[ActionDefinition] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Constraint Schemas
# =============================================================================

class Constraint(BaseModel):
    """
    Constraint for path pruning.
    Reference: project.md §11 Phase 5
    """
    constraint_id: str = Field(..., description="Unique constraint identifier")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None)
    constraint_type: ConstraintType = Field(ConstraintType.HARD)

    # Condition
    condition: StateCondition = Field(..., description="Condition that defines the constraint")

    # For soft constraints
    penalty_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Penalty weight for soft constraints")

    # Explanation
    violation_explanation: Optional[str] = Field(None, description="Explanation when constraint is violated")

    # Metadata
    source: Optional[str] = Field(None, description="Source of constraint (e.g., legal, financial, social)")
    priority: int = Field(0, description="Priority for conflict resolution")


class ConstraintSet(BaseModel):
    """Set of constraints for planning."""
    constraints: List[Constraint] = Field(default_factory=list)

    def get_hard_constraints(self) -> List[Constraint]:
        return [c for c in self.constraints if c.constraint_type == ConstraintType.HARD]

    def get_soft_constraints(self) -> List[Constraint]:
        return [c for c in self.constraints if c.constraint_type == ConstraintType.SOFT]


# =============================================================================
# State Vector Schemas
# =============================================================================

class StateVariable(BaseModel):
    """A variable in the state vector."""
    name: str
    value: Any
    data_type: str = Field("float", description="Type: float, int, str, bool, list, dict")
    bounds: Optional[tuple] = Field(None, description="Min/max bounds for numeric")
    description: Optional[str] = None


class StateVector(BaseModel):
    """
    Current state of the target.
    Reference: project.md §11 Phase 5
    """
    variables: Dict[str, Any] = Field(default_factory=dict)
    variable_metadata: Optional[Dict[str, StateVariable]] = Field(None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value

    def copy(self) -> "StateVector":
        return StateVector(
            variables=self.variables.copy(),
            variable_metadata=self.variable_metadata.copy() if self.variable_metadata else None,
            timestamp=self.timestamp
        )


# =============================================================================
# Target Persona Schemas
# =============================================================================

class TargetPersona(BaseModel):
    """
    Target persona for Target Mode simulation.
    Reference: project.md §11 Phase 5
    """
    target_id: str = Field(..., description="Unique target identifier")
    persona_id: Optional[str] = Field(None, description="Reference to base PersonaRecord")
    name: str = Field(..., description="Target name/label")
    description: Optional[str] = Field(None)

    # Core Target Mode components
    utility_function: UtilityFunction = Field(default_factory=UtilityFunction)
    action_priors: List[ActionPrior] = Field(default_factory=list)
    initial_state: StateVector = Field(default_factory=StateVector)

    # Available actions (or reference to catalog)
    action_catalog_id: Optional[str] = Field(None, description="Reference to ActionCatalog")
    custom_actions: Optional[List[ActionDefinition]] = Field(None, description="Custom actions for this target")

    # Constraints
    personal_constraints: Optional[List[Constraint]] = Field(None)

    # Decision-making parameters
    planning_horizon: int = Field(10, ge=1, le=100, description="Number of steps to plan ahead")
    discount_factor: float = Field(0.95, ge=0.0, le=1.0, description="Discount for future utility")
    exploration_rate: float = Field(0.1, ge=0.0, le=1.0, description="Rate of exploring non-optimal actions")

    # Metadata
    domain: Optional[str] = Field(None)
    tags: Optional[List[str]] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TargetPersonaCreate(BaseModel):
    """Schema for creating a target persona."""
    name: str
    description: Optional[str] = None
    persona_id: Optional[str] = None  # Optional base persona
    utility_function: Optional[UtilityFunction] = None
    action_priors: Optional[List[ActionPrior]] = None
    initial_state: Optional[Dict[str, Any]] = None
    action_catalog_id: Optional[str] = None
    custom_actions: Optional[List[ActionDefinition]] = None
    personal_constraints: Optional[List[Constraint]] = None
    planning_horizon: int = 10
    discount_factor: float = 0.95
    exploration_rate: float = 0.1
    domain: Optional[str] = None
    tags: Optional[List[str]] = None


# =============================================================================
# Path & Plan Schemas
# =============================================================================

class PathStep(BaseModel):
    """A single step in a path."""
    step_index: int
    action: ActionDefinition
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]
    effects_applied: List[StateEffect]
    utility_gained: float
    cumulative_utility: float
    probability: float = Field(1.0, description="Probability of this step succeeding")
    constraints_checked: Optional[List[str]] = Field(None, description="Constraints that were evaluated")
    constraints_violated: Optional[List[str]] = Field(None, description="Soft constraints that were violated")


class Path(BaseModel):
    """
    A sequence of actions with associated probability.
    Reference: project.md §11 Phase 5
    """
    path_id: str
    steps: List[PathStep] = Field(default_factory=list)

    # Probabilities
    path_probability: float = Field(..., ge=0.0, le=1.0, description="Overall path probability")
    success_probability: float = Field(..., ge=0.0, le=1.0, description="Probability path completes successfully")

    # Utility
    total_utility: float = Field(..., description="Total expected utility of path")
    utility_variance: Optional[float] = Field(None, description="Variance in utility outcome")

    # Costs
    total_cost: float = Field(0.0)
    total_time: float = Field(0.0)
    total_risk: float = Field(0.0)

    # Status
    status: PathStatus = Field(PathStatus.VALID)
    pruning_reason: Optional[str] = Field(None, description="Why path was pruned if applicable")

    # Metadata
    cluster_id: Optional[str] = Field(None, description="Cluster this path belongs to")
    is_representative: bool = Field(False, description="Is this the representative path for its cluster")


class PathCluster(BaseModel):
    """Cluster of similar paths for progressive expansion."""
    cluster_id: str
    label: str = Field(..., description="Human-readable cluster label")
    description: Optional[str] = None

    # Paths
    representative_path: Path = Field(..., description="Representative path for this cluster")
    child_paths: List[Path] = Field(default_factory=list, description="Other paths in cluster")

    # Aggregated metrics
    aggregated_probability: float = Field(..., ge=0.0, le=1.0)
    avg_utility: float
    utility_range: tuple = Field(..., description="(min, max) utility in cluster")

    # Expansion
    is_expanded: bool = Field(False)
    expansion_depth: int = Field(0)
    can_expand: bool = Field(True)

    # Common characteristics
    common_actions: Optional[List[str]] = Field(None, description="Actions common to all paths")
    distinguishing_features: Optional[List[str]] = Field(None, description="What distinguishes this cluster")


class PlanResult(BaseModel):
    """
    Result of Target Mode planning.
    Reference: project.md §11 Phase 5
    """
    plan_id: str
    target_id: str
    project_id: str

    # Status
    status: PlanStatus = Field(PlanStatus.COMPLETED)
    error_message: Optional[str] = None

    # Results
    total_paths_generated: int = Field(0)
    total_paths_valid: int = Field(0)
    total_paths_pruned: int = Field(0)

    # Clustered results
    clusters: List[PathCluster] = Field(default_factory=list)

    # Top paths (for quick access)
    top_paths: List[Path] = Field(default_factory=list, max_length=10)

    # Constraint summary
    hard_constraints_applied: List[str] = Field(default_factory=list)
    soft_constraints_applied: List[str] = Field(default_factory=list)
    paths_pruned_by_constraint: Dict[str, int] = Field(default_factory=dict)

    # Explanation
    planning_summary: Optional[str] = Field(None, description="Natural language summary")
    key_decision_points: Optional[List[str]] = Field(None)

    # Performance
    planning_time_ms: int = Field(0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# =============================================================================
# API Request/Response Schemas
# =============================================================================

class TargetPlanRequest(BaseModel):
    """Request to run Target Mode planner."""
    project_id: str
    target_id: str

    # Planning parameters
    max_paths: int = Field(100, ge=1, le=1000, description="Maximum paths to generate")
    max_depth: int = Field(10, ge=1, le=50, description="Maximum steps per path")
    pruning_threshold: float = Field(0.01, ge=0.0, le=1.0, description="Prune paths below this probability")

    # Clustering
    enable_clustering: bool = Field(True)
    max_clusters: int = Field(5, ge=1, le=20)

    # Constraints override
    additional_constraints: Optional[List[Constraint]] = None
    disable_soft_constraints: bool = Field(False)

    # Context
    environment_state: Optional[Dict[str, Any]] = Field(None, description="Environmental context")
    start_node_id: Optional[str] = Field(None, description="Starting node in Universe Map")


class ExpandClusterRequest(BaseModel):
    """Request to expand a path cluster."""
    plan_id: str
    cluster_id: str
    max_paths: int = Field(10, ge=1, le=50)


class BranchToNodeRequest(BaseModel):
    """Request to create Universe Map node from selected path."""
    plan_id: str
    path_id: str
    parent_node_id: str
    label: Optional[str] = None
    auto_run: bool = Field(False, description="Automatically run simulation after creating node")


class TargetPlanListItem(BaseModel):
    """Summary of a target plan for listing."""
    plan_id: str
    target_id: str
    target_name: str
    project_id: str
    status: PlanStatus
    total_paths: int
    total_clusters: int
    top_path_utility: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]
