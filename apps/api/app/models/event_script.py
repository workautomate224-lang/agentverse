"""
Event Script Models
Reference: project.md §6.4, §11 Phase 3

Events must be executable without LLM involvement at runtime.
They are compiled from natural language prompts into deterministic scripts.
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

class EventType(str, Enum):
    """Types of events (project.md §6.4)."""
    POLICY = "policy"                    # Government/regulatory policy change
    MEDIA = "media"                      # News, social media, information events
    SHOCK = "shock"                      # External shocks (economic, natural, etc.)
    INDIVIDUAL_ACTION = "individual_action"  # Specific individual action
    ENVIRONMENTAL = "environmental"      # Environmental/contextual changes
    SOCIAL = "social"                    # Social dynamics events
    CUSTOM = "custom"                    # User-defined event type


class IntensityProfileType(str, Enum):
    """Intensity profile types for event effects over time."""
    INSTANTANEOUS = "instantaneous"      # Full effect immediately
    LINEAR_DECAY = "linear_decay"        # Effect decays linearly over time
    EXPONENTIAL_DECAY = "exponential_decay"  # Effect decays exponentially
    LAGGED = "lagged"                    # Effect appears after delay
    PULSE = "pulse"                      # Effect oscillates
    STEP = "step"                        # Step function (on/off)
    CUSTOM = "custom"                    # Custom profile


class DeltaOperation(str, Enum):
    """Operations for applying deltas."""
    SET = "set"
    ADD = "add"
    MULTIPLY = "multiply"
    MIN = "min"
    MAX = "max"


# =============================================================================
# Event Script Model (project.md §6.4)
# =============================================================================

class EventScript(Base):
    """
    An event script - a deterministic, executable event definition.

    Events are compiled from natural language prompts and can be executed
    without LLM involvement at runtime. They specify:
    - What changes (deltas to environment/perception variables)
    - Who is affected (scope: regions, segments, agents)
    - When and how the effect applies (intensity profile)
    - Provenance (where it came from, compiler version)
    """
    __tablename__ = "event_scripts"

    # Identity
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
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Classification
    event_type: Mapped[str] = mapped_column(
        String(50),
        default=EventType.CUSTOM.value,
        nullable=False,
        index=True
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scope: Who/where/when is affected
    # Structure: { affected_regions, affected_persona_segments, start_tick, end_tick, target_agent_ids }
    scope: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )

    # Deltas: What changes
    # Structure: { environment_deltas: [], perception_deltas: [], custom_deltas: [] }
    deltas: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )

    # Intensity profile: How the effect applies over time
    # Structure: { profile_type, initial_intensity, decay_rate, half_life_ticks, lag_ticks, custom_profile }
    intensity_profile: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )

    # Uncertainty quantification
    # Structure: { occurrence_probability, intensity_variance, assumptions, compilation_confidence }
    uncertainty: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )

    # Provenance: Where did this come from?
    # Structure: { compiled_from, compiler_version, compiled_at, compiler_model, manually_edited }
    provenance: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )

    # Versioning (P3-004)
    event_version: Mapped[str] = mapped_column(
        String(50),
        default="1.0.0",
        nullable=False
    )
    schema_version: Mapped[str] = mapped_column(
        String(50),
        default="1.0.0",
        nullable=False
    )

    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    is_validated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # ==========================================================================
    # STEP 5: Event Audit Fields
    # ==========================================================================

    # Source text: explicit field for original NL input (was buried in provenance)
    source_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="STEP 5: Original natural language input that was compiled"
    )

    # Affected variables: explicit array field (was derived from deltas)
    affected_variables: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String(100)), nullable=True,
        comment="STEP 5: List of variables this event affects"
    )

    # Confidence score: how confident is the compiler in this interpretation
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="STEP 5: Compiler confidence in this interpretation (0.0-1.0)"
    )

    # Ambiguity score: how ambiguous was the original input
    ambiguity_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="STEP 5: Ambiguity level of the original input (0.0-1.0)"
    )

    # Validation result: detailed validation status
    validation_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True,
        comment="STEP 5: Detailed validation result {passed, errors, warnings}"
    )

    # Tags for organization
    tags: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String(100)), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    bundles: Mapped[List["EventBundleMember"]] = relationship(
        "EventBundleMember",
        back_populates="event_script",
        cascade="all, delete-orphan"
    )
    trigger_logs: Mapped[List["EventTriggerLog"]] = relationship(
        "EventTriggerLog",
        back_populates="event_script",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<EventScript {self.id} label={self.label} type={self.event_type}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "event_id": str(self.id),
            "project_id": str(self.project_id),
            "event_type": self.event_type,
            "label": self.label,
            "description": self.description,
            "scope": self.scope,
            "deltas": self.deltas,
            "intensity_profile": self.intensity_profile,
            "uncertainty": self.uncertainty,
            "provenance": self.provenance,
            "event_version": self.event_version,
            "schema_version": self.schema_version,
            "is_active": self.is_active,
            "is_validated": self.is_validated,
            # STEP 5: Audit fields
            "source_text": self.source_text,
            "affected_variables": self.affected_variables,
            "confidence_score": self.confidence_score,
            "ambiguity_score": self.ambiguity_score,
            "validation_result": self.validation_result,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# =============================================================================
# Event Bundle Model (P3-002)
# =============================================================================

class EventBundle(Base):
    """
    A bundle of related events that should be applied together.

    Bundles allow multiple events from a single natural language question
    to be applied atomically and stored with the scenario patch.
    """
    __tablename__ = "event_bundles"

    # Identity
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
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Metadata
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Execution order (if events depend on each other)
    execution_order: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=True
    )

    # Bundle-level probability
    joint_probability: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # Provenance
    # Structure: { compiled_from, compiler_version, compiled_at }
    provenance: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    members: Mapped[List["EventBundleMember"]] = relationship(
        "EventBundleMember",
        back_populates="bundle",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<EventBundle {self.id} label={self.label}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "bundle_id": str(self.id),
            "project_id": str(self.project_id),
            "label": self.label,
            "description": self.description,
            "event_ids": [str(m.event_script_id) for m in self.members],
            "execution_order": [str(eid) for eid in self.execution_order] if self.execution_order else None,
            "joint_probability": self.joint_probability,
            "provenance": self.provenance,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class EventBundleMember(Base):
    """Junction table for event bundle membership."""
    __tablename__ = "event_bundle_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_bundles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    event_script_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_scripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    order_index: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Relationships
    bundle: Mapped["EventBundle"] = relationship(
        "EventBundle",
        back_populates="members"
    )
    event_script: Mapped["EventScript"] = relationship(
        "EventScript",
        back_populates="bundles"
    )


# =============================================================================
# Event Trigger Log Model (P3-003)
# =============================================================================

class EventTriggerLog(Base):
    """
    Log of event triggers during simulation runs.

    Tracks when events were triggered, how many agents/segments were affected,
    and the actual deltas applied. Used for telemetry and debugging.
    """
    __tablename__ = "event_trigger_logs"

    # Identity
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
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    event_script_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_scripts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Trigger details
    triggered_at_tick: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    trigger_source: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "scheduled", "condition", "manual"

    # Affected counts
    affected_agent_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    affected_segment_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    affected_region_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Actual deltas applied (may differ from script due to conditions)
    applied_deltas: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Intensity at trigger time
    applied_intensity: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )

    # Summary of effects
    effect_summary: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    event_script: Mapped[Optional["EventScript"]] = relationship(
        "EventScript",
        back_populates="trigger_logs"
    )

    def __repr__(self) -> str:
        return f"<EventTriggerLog {self.id} tick={self.triggered_at_tick}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "log_id": str(self.id),
            "run_id": str(self.run_id),
            "event_id": str(self.event_script_id) if self.event_script_id else None,
            "triggered_at_tick": self.triggered_at_tick,
            "trigger_source": self.trigger_source,
            "affected_agent_count": self.affected_agent_count,
            "affected_segment_count": self.affected_segment_count,
            "affected_region_count": self.affected_region_count,
            "applied_deltas": self.applied_deltas,
            "applied_intensity": self.applied_intensity,
            "effect_summary": self.effect_summary,
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# STEP 5: Event Candidate Model
# Stores parsed but uncommitted event interpretations from NL input
# =============================================================================

class EventCandidateStatus(str, Enum):
    """Status of an event candidate."""
    PENDING = "pending"        # Awaiting user selection
    SELECTED = "selected"      # User selected this candidate
    REJECTED = "rejected"      # User rejected this candidate
    COMMITTED = "committed"    # Committed to EventScript


class EventCandidate(Base):
    """
    STEP 5: A parsed but uncommitted event interpretation.

    When a user provides natural language input, the EventCompiler generates
    multiple candidate interpretations. These are stored as EventCandidates
    until the user selects one (or more) to commit as EventScripts.

    This enables:
    1. Auditable parsing - all interpretations are stored
    2. User review - users can see and select from options
    3. Reproducibility - same input produces same candidates
    """
    __tablename__ = "event_candidates"

    # Identity
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
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Compilation reference
    compilation_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="STEP 5: ID of the compilation session"
    )

    # Original input
    source_text: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="STEP 5: Original natural language input"
    )

    # Candidate details
    candidate_index: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="STEP 5: Index of this candidate in the compilation result"
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Parsed interpretation
    parsed_intent: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="STEP 5: Structured intent extracted from NL input"
    )
    proposed_deltas: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="STEP 5: Proposed deltas to apply"
    )
    proposed_scope: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="STEP 5: Proposed scope of the event"
    )
    affected_variables: Mapped[List[str]] = mapped_column(
        ARRAY(String(100)), nullable=False, default=list,
        comment="STEP 5: Variables this candidate would affect"
    )

    # Scoring
    probability: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="STEP 5: Probability assigned to this interpretation"
    )
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="STEP 5: Compiler confidence in this interpretation"
    )
    cluster_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="STEP 5: ID of the scenario cluster this belongs to"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=EventCandidateStatus.PENDING.value,
        comment="STEP 5: pending, selected, rejected, committed"
    )
    committed_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_scripts.id", ondelete="SET NULL"),
        nullable=True,
        comment="STEP 5: EventScript ID if this candidate was committed"
    )

    # Provenance
    compiler_version: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    model_used: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    selected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    committed_event: Mapped[Optional["EventScript"]] = relationship(
        "EventScript",
        foreign_keys=[committed_event_id]
    )

    def __repr__(self) -> str:
        return f"<EventCandidate {self.id} status={self.status}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "candidate_id": str(self.id),
            "compilation_id": self.compilation_id,
            "source_text": self.source_text,
            "candidate_index": self.candidate_index,
            "label": self.label,
            "description": self.description,
            "parsed_intent": self.parsed_intent,
            "proposed_deltas": self.proposed_deltas,
            "proposed_scope": self.proposed_scope,
            "affected_variables": self.affected_variables,
            "probability": self.probability,
            "confidence_score": self.confidence_score,
            "cluster_id": self.cluster_id,
            "status": self.status,
            "committed_event_id": str(self.committed_event_id) if self.committed_event_id else None,
            "compiler_version": self.compiler_version,
            "model_used": self.model_used,
            "created_at": self.created_at.isoformat(),
            "selected_at": self.selected_at.isoformat() if self.selected_at else None,
        }


# =============================================================================
# STEP 5: Event Validation Model
# Tracks validation history for events
# =============================================================================

class EventValidationType(str, Enum):
    """Types of event validation."""
    PARAMETER_RANGE = "parameter_range"       # Check parameter values are in valid range
    VARIABLE_EXISTENCE = "variable_existence"  # Check referenced variables exist
    CONFLICT_DETECTION = "conflict_detection"  # Check for conflicts with parent state
    SCHEMA_VALIDATION = "schema_validation"    # Check event schema is valid
    COMPLETENESS = "completeness"              # Check all required fields present


class EventValidation(Base):
    """
    STEP 5: Tracks validation history for events.

    Each validation run is recorded with its results, enabling:
    1. Audit trail of all validations performed
    2. Context-aware validation (with parent Node state)
    3. Detailed error and warning tracking
    """
    __tablename__ = "event_validations"

    # Identity
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
    event_script_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_scripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Validation context
    validation_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="STEP 5: Type of validation performed"
    )
    context_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
        comment="STEP 5: Node context for conflict detection"
    )

    # Results
    passed: Mapped[bool] = mapped_column(
        Boolean, nullable=False
    )
    errors: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list,
        comment="STEP 5: List of validation errors"
    )
    warnings: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list,
        comment="STEP 5: List of validation warnings"
    )
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="STEP 5: Detailed validation output"
    )

    # Timestamp
    validated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    event_script: Mapped["EventScript"] = relationship(
        "EventScript",
        foreign_keys=[event_script_id]
    )

    def __repr__(self) -> str:
        return f"<EventValidation {self.id} type={self.validation_type} passed={self.passed}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "validation_id": str(self.id),
            "event_script_id": str(self.event_script_id),
            "validation_type": self.validation_type,
            "context_node_id": str(self.context_node_id) if self.context_node_id else None,
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details,
            "validated_at": self.validated_at.isoformat(),
        }
