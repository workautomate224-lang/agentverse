"""
Evidence Pack Schemas
Reference: verification_checklist_v2.md §1

Evidence Pack is the canonical proof bundle for verification.
All compliance checks derive from Evidence Packs.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class EnginePathType(str, Enum):
    """Engine execution paths - defines which engine executed the run."""
    SOCIETY = "society"
    TARGET = "target"
    HYBRID = "hybrid"
    COMPILER = "compiler"
    REPLAY = "replay"
    CALIBRATION = "calibration"


class ProofStatus(str, Enum):
    """Status of a verification proof."""
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    NOT_TESTED = "not_tested"


# =============================================================================
# Artifact Lineage (§1.1)
# =============================================================================

class ArtifactLineage(BaseModel):
    """
    Complete lineage of all artifacts involved in a run/node.
    Every artifact must be traceable to its source.
    """
    project_id: str
    project_version: str

    node_id: Optional[str] = None
    parent_node_id: Optional[str] = None
    node_depth: int = 0

    run_id: Optional[str] = None
    run_config_id: Optional[str] = None

    # Version references (all must be pinned)
    engine_version: str = Field(..., description="Simulation engine version")
    ruleset_version: str = Field(..., description="Rule pack version")
    dataset_version: str = Field(..., description="Persona/data version")
    schema_version: str = Field(default="1.0.0", description="Evidence schema version")

    # Storage references
    telemetry_ref: Optional[Dict[str, Any]] = Field(
        None, description="Reference to telemetry blob in storage"
    )
    reliability_ref: Optional[Dict[str, Any]] = Field(
        None, description="Reference to reliability report"
    )

    # Timestamps
    created_at: datetime
    completed_at: Optional[datetime] = None


# =============================================================================
# Execution Proof (§3.1)
# =============================================================================

class LoopStageCounters(BaseModel):
    """
    Counters for each stage of the agent loop.
    Required for Society Mode verification (§3.1).
    """
    observe: int = Field(default=0, description="Number of observe() calls")
    evaluate: int = Field(default=0, description="Number of evaluate() calls")
    decide: int = Field(default=0, description="Number of decide() calls")
    act: int = Field(default=0, description="Number of act() calls")
    update: int = Field(default=0, description="Number of update() calls")

    def total_cycles(self) -> int:
        """A complete cycle means all 5 stages executed."""
        return min(self.observe, self.evaluate, self.decide, self.act, self.update)


class RuleApplicationCount(BaseModel):
    """Count of how many times a rule was applied at each insertion point."""
    rule_name: str
    rule_version: str
    insertion_point: str  # observe | evaluate | decide | act | update
    application_count: int
    agents_affected: int


class ExecutionProof(BaseModel):
    """
    Proof that simulation was actually executed through the correct engine path.
    """
    engine_path: EnginePathType

    # Tick counters
    ticks_executed: int = Field(..., description="Total ticks completed")
    ticks_configured: int = Field(..., description="Max ticks from config")

    # Agent counters
    agent_count: int = Field(..., description="Number of agents in simulation")
    agent_steps_executed: int = Field(
        default=0,
        description="Total agent step executions across all ticks"
    )

    # Loop stage counters (Society Mode proof)
    loop_stage_counters: LoopStageCounters = Field(
        default_factory=LoopStageCounters,
        description="Counts per agent loop stage"
    )

    # Rule application counts
    rule_application_counts: List[RuleApplicationCount] = Field(
        default_factory=list,
        description="Per-rule application statistics"
    )

    # LLM usage (must be 0 in tick loop per C5)
    llm_calls_in_tick_loop: int = Field(
        default=0,
        description="LLM calls during tick loop (MUST be 0)"
    )
    llm_calls_in_compilation: int = Field(
        default=0,
        description="LLM calls during compilation phase (allowed)"
    )

    # Scheduler metrics (§3.3)
    scheduler_profile: str = Field(default="default")
    partitions_count: int = Field(default=0)
    batches_count: int = Field(default=0)
    backpressure_events: int = Field(default=0)

    # Hybrid Mode metrics (§5.1)
    target_decision_steps_executed: int = Field(
        default=0,
        description="Total decision steps executed by key/target actor"
    )
    hybrid_coupling_events: int = Field(
        default=0,
        description="Total bidirectional coupling events"
    )


# =============================================================================
# Hybrid Coupling Proof (§5.1)
# =============================================================================

class CouplingEventRecord(BaseModel):
    """Single coupling event for audit trail."""
    tick: int
    direction: str = Field(..., description="key_to_society or society_to_key")
    effect_type: str
    magnitude: float
    affected_count: int
    description: str = ""


class HybridCouplingProof(BaseModel):
    """
    Proof of bidirectional coupling in Hybrid Mode.
    Required for §5.1 verification.
    """
    # Direction counts
    key_to_society_events: int = Field(
        default=0,
        description="Events from key actor to society"
    )
    society_to_key_events: int = Field(
        default=0,
        description="Events from society to key actor"
    )

    # Magnitude totals
    key_to_society_total_magnitude: float = Field(
        default=0.0,
        description="Sum of all key→society effect magnitudes"
    )
    society_to_key_total_magnitude: float = Field(
        default=0.0,
        description="Sum of all society→key effect magnitudes"
    )

    # Balance verification
    bidirectional_balance_score: float = Field(
        default=0.0,
        description="Score 0-1, 0.5 = perfectly balanced"
    )
    is_truly_bidirectional: bool = Field(
        default=False,
        description="True if both directions have events"
    )

    # Decision counters (matches ExecutionProof)
    society_agent_steps: int = Field(default=0)
    target_decision_steps: int = Field(default=0)

    # Coupling log (limited for export, full log in storage)
    coupling_events_sample: List[CouplingEventRecord] = Field(
        default_factory=list,
        max_length=100,
        description="Sample of coupling events (first 100)"
    )

    # Joint outcome
    joint_success: bool = Field(default=False)
    synergy_score: float = Field(default=0.0)


# =============================================================================
# Determinism Signatures (§1.2)
# =============================================================================

class DeterminismSignature(BaseModel):
    """
    Hash signatures for determinism verification.
    Same config + seed must produce identical hashes.
    """
    run_config_hash: str = Field(
        ...,
        description="SHA256 of normalized RunConfig"
    )
    result_hash: str = Field(
        ...,
        description="SHA256 of aggregated outcomes"
    )
    telemetry_hash: str = Field(
        ...,
        description="SHA256 of telemetry summary"
    )

    # Additional context
    seed_used: int
    algorithm: str = Field(default="sha256")
    computed_at: datetime


# =============================================================================
# Telemetry Proof (§6.2)
# =============================================================================

class TelemetryProof(BaseModel):
    """
    Proof that telemetry was properly captured and is intact.
    §6.2: Telemetry Sufficiency & Integrity.
    """
    telemetry_ref: Dict[str, Any]
    keyframe_count: int
    delta_count: int
    total_events: int

    # Integrity (§6.2)
    telemetry_hash: str = Field(..., description="SHA256 of telemetry data - must be stable")
    is_complete: bool = Field(default=True, description="True if all expected ticks present")
    replay_degraded: bool = Field(
        default=False,
        description="True if telemetry is incomplete for full replay"
    )
    integrity_issues: List[str] = Field(
        default_factory=list,
        description="List of integrity issues found during validation"
    )


# =============================================================================
# Results Proof (§4)
# =============================================================================

class ResultsProof(BaseModel):
    """
    Proof that results were computed from actual simulation.
    """
    outcomes_hash: str
    primary_outcome: str
    primary_probability: float
    outcome_distribution: Dict[str, float]

    # Key metrics
    key_metrics: List[Dict[str, Any]]
    variance_metrics: Optional[Dict[str, float]] = None


# =============================================================================
# Reliability Proof (§7)
# =============================================================================

class ReliabilityProof(BaseModel):
    """
    Proof of reliability metrics computation.
    """
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    confidence_level: str  # high | medium | low | very_low

    # Calibration (§7.1-7.2)
    calibration_score: Optional[float] = None
    calibration_bounded: bool = Field(default=False)

    # Stability (§7.3)
    stability_variance: Optional[float] = None
    seeds_tested: List[int] = Field(default_factory=list)

    # Drift (§7.4)
    drift_score: Optional[float] = None
    drift_detected: bool = Field(default=False)

    # Data gaps
    data_gaps: List[str] = Field(default_factory=list)


# =============================================================================
# Anti-Leakage Proof (§1.3, §7.1)
# =============================================================================

class AntiLeakageProof(BaseModel):
    """
    Proof that time cutoff was enforced (for backtests).
    """
    cutoff_time: Optional[datetime] = Field(
        None,
        description="Time cutoff for data access"
    )
    leakage_guard_enabled: bool = Field(default=False)
    blocked_access_attempts: int = Field(default=0)
    dataset_filtered: bool = Field(default=False)

    # If cutoff was violated
    leakage_detected: bool = Field(default=False)
    leakage_details: Optional[str] = None


# =============================================================================
# Audit Proof (§8.3)
# =============================================================================

class AuditProof(BaseModel):
    """
    Proof of audit trail for this run/node.
    """
    audit_log_refs: List[str] = Field(
        default_factory=list,
        description="References to audit log entries"
    )
    actions_recorded: int = Field(default=0)
    actor_id: Optional[str] = None
    actor_type: str = Field(default="user")  # user | system | api
    tenant_id: str


# =============================================================================
# Evidence Pack (§1.1 - Main Export)
# =============================================================================

class EvidencePack(BaseModel):
    """
    Complete Evidence Pack for a run or node.
    This is the canonical proof bundle for verification.

    Reference: verification_checklist_v2.md §1.1
    """
    # Identity
    evidence_pack_id: str
    evidence_pack_version: str = Field(default="1.0.0")
    generated_at: datetime

    # What this pack is for
    run_id: Optional[str] = None
    node_id: Optional[str] = None

    # Core proofs
    artifact_lineage: ArtifactLineage
    execution_proof: ExecutionProof
    determinism_signature: DeterminismSignature
    telemetry_proof: TelemetryProof
    results_proof: ResultsProof
    reliability_proof: ReliabilityProof
    audit_proof: AuditProof

    # Optional proofs
    anti_leakage_proof: Optional[AntiLeakageProof] = None
    hybrid_coupling_proof: Optional[HybridCouplingProof] = Field(
        None,
        description="§5.1 Bidirectional coupling proof (Hybrid Mode only)"
    )

    # Metadata
    tenant_id: str
    project_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "evidence_pack_id": "ep-123",
                "evidence_pack_version": "1.0.0",
                "run_id": "run-456",
                "node_id": "node-789",
            }
        }


# =============================================================================
# Comparison Response (§1.2)
# =============================================================================

class DeterminismComparisonResult(BaseModel):
    """
    Result of comparing two runs for determinism.
    """
    run_id_a: str
    run_id_b: str

    # Hash comparisons
    config_hash_match: bool
    result_hash_match: bool
    telemetry_hash_match: bool

    # Overall
    is_deterministic: bool

    # Details if mismatch
    differences: List[str] = Field(default_factory=list)


# =============================================================================
# API Response Models
# =============================================================================

class EvidencePackResponse(BaseModel):
    """API response wrapping an Evidence Pack."""
    success: bool
    evidence_pack: EvidencePack
    warnings: List[str] = Field(default_factory=list)


class EvidencePackListResponse(BaseModel):
    """List of Evidence Packs."""
    evidence_packs: List[EvidencePack]
    total: int
    page: int
    page_size: int


class ComparisonResponse(BaseModel):
    """API response for determinism comparison."""
    success: bool
    comparison: DeterminismComparisonResult
