"""
STEP 6: Planning Models
Reference: STEP 6 Audit Requirements

Planning models for Target Mode as a real planning system.
Key principle: Planner must search action paths and evaluate via simulation,
not just use LLM-only advice.

Models:
- PlanningSpec: Persisted planning request with all required fields
- PlanTrace: Audit artifact recording candidate plans, runs, scoring
- PlanCandidate: Individual candidate plan
- PlanEvaluation: Simulation evaluation result for a candidate
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# =============================================================================
# Enums
# =============================================================================

class PlanningStatus(str, Enum):
    """Status of a planning job."""
    CREATED = "created"      # Initial state
    SEARCHING = "searching"  # Search phase
    EVALUATING = "evaluating"  # Running simulation evaluations
    COMPLETED = "completed"  # Planning complete
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanCandidateStatus(str, Enum):
    """Status of a plan candidate."""
    PENDING = "pending"       # Awaiting evaluation
    EVALUATING = "evaluating"  # Currently being evaluated
    EVALUATED = "evaluated"   # Evaluation complete
    SELECTED = "selected"     # Selected as final plan
    REJECTED = "rejected"     # Did not meet criteria


class SearchAlgorithm(str, Enum):
    """Search algorithm types."""
    BEAM_SEARCH = "beam_search"
    MCTS = "mcts"  # Monte Carlo Tree Search
    A_STAR = "a_star"
    GREEDY = "greedy"
    EXHAUSTIVE = "exhaustive"


# =============================================================================
# PlanningSpec Model (STEP 6 Requirement 1)
# =============================================================================

class PlanningSpec(Base):
    """
    STEP 6: Persisted planning specification.

    Stored in DB - if not stored, STEP 6 FAIL.

    Required fields per STEP 6:
    - planning_id (id)
    - project_id
    - parent_node_id
    - target_snapshot_id
    - goal definition
    - constraints
    - action_library_version
    - search_config
    - evaluation_budget
    - seed
    """
    __tablename__ = "planning_specs"

    # Identity (planning_id)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="STEP 6: planning_id"
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Project reference
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="STEP 6: project_id"
    )

    # Parent node in Universe Map (starting point for planning)
    parent_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="STEP 6: parent_node_id - starting point"
    )

    # Target snapshot - the goal state we're planning toward
    target_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="STEP 6: target_snapshot_id - goal state reference"
    )

    # Target persona reference (for Target Mode)
    target_persona_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="STEP 6: Target persona ID"
    )

    # Goal definition - explicit, auditable goal
    goal_definition: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 6: Goal definition {goal_type, target_metrics, success_criteria}"
    )

    # Constraints - hard and soft
    constraints: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 6: Constraints {hard_constraints, soft_constraints}"
    )

    # Action library version - for reproducibility
    action_library_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0.0",
        comment="STEP 6: action_library_version for reproducibility"
    )

    # Search configuration
    search_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 6: search_config {algorithm, max_depth, beam_width, pruning_threshold}"
    )

    # Evaluation budget - max runs allowed
    evaluation_budget: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        comment="STEP 6: evaluation_budget - max simulation runs"
    )

    # Min runs per candidate (for ensemble evaluation)
    min_runs_per_candidate: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        comment="STEP 6: Minimum runs per candidate (ensemble requirement)"
    )

    # Seed for reproducibility
    seed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="STEP 6: seed for reproducibility"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PlanningStatus.CREATED.value,
        index=True,
        comment="STEP 6: Planning status"
    )

    # Environment state at planning start (for reproducibility)
    initial_environment_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="STEP 6: Environment state snapshot at planning start"
    )

    # Label and description
    label: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Provenance
    compiler_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0.0"
    )
    model_used: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="LLM model used for NL compilation (if any)"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Relationships
    candidates: Mapped[List["PlanCandidate"]] = relationship(
        "PlanCandidate",
        back_populates="planning_spec",
        cascade="all, delete-orphan"
    )
    trace: Mapped[Optional["PlanTrace"]] = relationship(
        "PlanTrace",
        back_populates="planning_spec",
        uselist=False,
        cascade="all, delete-orphan"
    )


# =============================================================================
# PlanCandidate Model (STEP 6 Requirement 2)
# =============================================================================

class PlanCandidate(Base):
    """
    STEP 6: Individual candidate plan generated by search.

    Each candidate represents an action path that will be evaluated
    via actual simulation runs.
    """
    __tablename__ = "plan_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Planning spec reference
    planning_spec_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planning_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Candidate identification
    candidate_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="STEP 6: Index of this candidate in search result"
    )

    # Label and description
    label: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Action sequence - the planned path
    action_sequence: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="STEP 6: Sequence of actions [{action_id, parameters, expected_effects}]"
    )

    # Predicted outcome (before simulation)
    predicted_outcome: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 6: Predicted outcome from search"
    )

    # Search-derived probability (before simulation)
    search_probability: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="STEP 6: Probability from search algorithm"
    )

    # Cluster information (if clustered)
    cluster_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )
    is_cluster_representative: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PlanCandidateStatus.PENDING.value,
        index=True
    )

    # Simulation-derived scores (STEP 6 Requirement 4: Explicit Scoring)
    # These are populated AFTER simulation runs
    success_probability: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="STEP 6: success_probability from simulation (not LLM)"
    )
    cost_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="STEP 6: cost from simulation runs"
    )
    risk_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="STEP 6: risk from simulation variance"
    )

    # Composite score (calculated from above)
    composite_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="STEP 6: Composite score = f(success_probability, cost, risk)"
    )

    # Score confidence (based on number of runs)
    score_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="STEP 6: Confidence in score (higher with more ensemble runs)"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    planning_spec: Mapped["PlanningSpec"] = relationship(
        "PlanningSpec",
        back_populates="candidates"
    )
    evaluations: Mapped[List["PlanEvaluation"]] = relationship(
        "PlanEvaluation",
        back_populates="candidate",
        cascade="all, delete-orphan"
    )


# =============================================================================
# PlanEvaluation Model (STEP 6 Requirement 5: Ensemble Evaluation)
# =============================================================================

class PlanEvaluation(Base):
    """
    STEP 6: Simulation evaluation of a plan candidate.

    Each candidate must have minimum 2 evaluations (ensemble requirement).
    Links to actual Run artifacts for evidence.
    """
    __tablename__ = "plan_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Candidate reference
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plan_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Run reference (STEP 6 Requirement 7: Evidence links)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="STEP 6: FK to actual Run artifact for evidence"
    )

    # Node created for this evaluation
    node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="STEP 6: Node created for evaluation"
    )

    # Evaluation index (for ensemble)
    evaluation_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="STEP 6: Index in ensemble (0, 1, 2, ...)"
    )

    # Seed used for this evaluation
    seed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="STEP 6: Seed for reproducibility"
    )

    # Simulation results
    simulation_outcome: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="STEP 6: Raw simulation outcome"
    )

    # Goal achievement (did simulation reach goal?)
    goal_achieved: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="STEP 6: Did simulation reach goal state?"
    )
    goal_distance: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="STEP 6: Distance from goal at simulation end"
    )

    # Cost metrics from simulation
    execution_cost: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="STEP 6: Cost computed from simulation"
    )

    # Risk metrics from simulation
    outcome_variance: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="STEP 6: Variance in outcome metrics"
    )

    # Run status
    run_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        comment="STEP 6: Status of the evaluation run"
    )

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    # Relationships
    candidate: Mapped["PlanCandidate"] = relationship(
        "PlanCandidate",
        back_populates="evaluations"
    )


# =============================================================================
# PlanTrace Model (STEP 6 Requirement 3)
# =============================================================================

class PlanTrace(Base):
    """
    STEP 6: Audit artifact for planning process.

    Records:
    - Candidate plans list
    - Pruning decisions
    - Runs executed
    - Scoring (explicit, auditable)
    """
    __tablename__ = "plan_traces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Planning spec reference
    planning_spec_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("planning_specs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Search statistics
    total_candidates_generated: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    candidates_pruned: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    candidates_evaluated: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    # Search algorithm details
    search_algorithm: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SearchAlgorithm.BEAM_SEARCH.value
    )
    explored_states_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="STEP 6: Number of unique states explored"
    )
    expanded_nodes_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="STEP 6: Total node expansions in search"
    )

    # Pruning decisions (STEP 6: auditable)
    pruning_decisions: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="STEP 6: List of {candidate_index, reason, constraint_violated}"
    )

    # Runs executed (STEP 6: auditable)
    runs_executed: Mapped[List[str]] = mapped_column(
        ARRAY(String(50)),
        nullable=False,
        server_default="{}",
        comment="STEP 6: List of run_ids executed for evaluation"
    )
    total_runs_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    # Scoring function (STEP 6 Requirement 4: Explicit, non-black-box)
    scoring_function: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="STEP 6: Explicit scoring function {formula, weights, components}"
    )

    # Top-K results (STEP 6 Requirement 7)
    top_k_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5
    )
    top_k_results: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="STEP 6: Top-K plans with evidence links"
    )

    # Selected plan
    selected_candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plan_candidates.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timing
    search_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    evaluation_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    total_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    # Summary (natural language explanation)
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="STEP 6: Natural language summary of planning result"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    planning_spec: Mapped["PlanningSpec"] = relationship(
        "PlanningSpec",
        back_populates="trace"
    )


# =============================================================================
# Explicit Scoring Function Types (STEP 6 Requirement 4)
# =============================================================================

class ScoringWeights:
    """
    STEP 6: Explicit, non-black-box scoring function.

    Composite Score = w1 * success_probability - w2 * cost - w3 * risk

    This is NOT in an LLM - it's explicit Python code.
    """

    DEFAULT_WEIGHTS = {
        "success_probability": 0.5,  # 50% weight on likelihood of success
        "cost": 0.3,                  # 30% weight on cost (negative)
        "risk": 0.2,                  # 20% weight on risk/variance (negative)
    }

    @staticmethod
    def calculate_composite_score(
        success_probability: float,
        cost_score: float,
        risk_score: float,
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        STEP 6: Explicit scoring formula.

        Composite Score = w_success * success_probability
                        - w_cost * normalized_cost
                        - w_risk * normalized_risk

        All values normalized to [0, 1].
        Higher score = better plan.
        """
        w = weights or ScoringWeights.DEFAULT_WEIGHTS

        # Ensure values are in [0, 1]
        success_prob = max(0.0, min(1.0, success_probability))
        cost_norm = max(0.0, min(1.0, cost_score))
        risk_norm = max(0.0, min(1.0, risk_score))

        score = (
            w.get("success_probability", 0.5) * success_prob
            - w.get("cost", 0.3) * cost_norm
            - w.get("risk", 0.2) * risk_norm
        )

        return score

    @staticmethod
    def get_scoring_function_spec(weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        STEP 6: Return explicit specification of scoring function for audit.
        """
        w = weights or ScoringWeights.DEFAULT_WEIGHTS
        return {
            "type": "linear_combination",
            "formula": "w_success * success_probability - w_cost * cost - w_risk * risk",
            "weights": w,
            "components": {
                "success_probability": {
                    "source": "simulation_goal_achievement_rate",
                    "description": "Proportion of ensemble runs that achieved goal",
                    "weight": w.get("success_probability", 0.5),
                    "sign": "positive"
                },
                "cost": {
                    "source": "simulation_execution_cost_mean",
                    "description": "Mean cost from simulation runs",
                    "weight": w.get("cost", 0.3),
                    "sign": "negative"
                },
                "risk": {
                    "source": "simulation_outcome_variance",
                    "description": "Variance in outcome across ensemble runs",
                    "weight": w.get("risk", 0.2),
                    "sign": "negative"
                }
            },
            "normalization": "min-max to [0, 1]",
            "interpretation": "Higher score = better plan"
        }
