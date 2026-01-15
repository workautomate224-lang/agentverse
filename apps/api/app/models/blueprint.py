"""
Blueprint Model (blueprint.md §3)
Reference: blueprint.md §3, §10 Phase A

Blueprint is the "single source of truth" for every project.
- Every project has a Blueprint (versioned)
- Every run references a specific blueprint version
- Any blueprint change creates a new version and is audit-tracked
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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.project_spec import ProjectSpec
    from app.models.user import User


# ============================================================================
# Enums (blueprint.md §3.1, §7.2)
# ============================================================================

class DomainGuess(str, Enum):
    """Domain classification for project goals (blueprint.md §3.1.A)"""
    ELECTION = "election"
    MARKET_DEMAND = "market_demand"
    PRODUCTION_FORECAST = "production_forecast"
    POLICY_IMPACT = "policy_impact"
    PERCEPTION_RISK = "perception_risk"
    CRIME_ROUTE = "crime_route"
    PERSONAL_DECISION = "personal_decision"
    GENERIC = "generic"


class TargetOutput(str, Enum):
    """Output types required (blueprint.md §3.1.A)"""
    DISTRIBUTION = "distribution"
    POINT_ESTIMATE = "point_estimate"
    RANKED_OUTCOMES = "ranked_outcomes"
    PATHS = "paths"
    RECOMMENDATIONS = "recommendations"


class PrimaryDriver(str, Enum):
    """Primary drivers for prediction (blueprint.md §3.1.B)"""
    POPULATION = "population"
    TIMESERIES = "timeseries"
    NETWORK = "network"
    CONSTRAINTS = "constraints"
    EVENTS = "events"
    SENTIMENT = "sentiment"
    MIXED = "mixed"


class SlotType(str, Enum):
    """Input slot types (blueprint.md §3.1.C)"""
    TIMESERIES = "TimeSeries"
    TABLE = "Table"
    ENTITY_SET = "EntitySet"
    GRAPH = "Graph"
    TEXT_CORPUS = "TextCorpus"
    LABELS = "Labels"
    RULESET = "Ruleset"
    ASSUMPTION_SET = "AssumptionSet"
    PERSONA_SET = "PersonaSet"
    EVENT_SCRIPT_SET = "EventScriptSet"


class RequiredLevel(str, Enum):
    """Requirement level for slots (blueprint.md §3.1.C)"""
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class AcquisitionMethod(str, Enum):
    """How a slot can be fulfilled (blueprint.md §6.2)"""
    MANUAL_UPLOAD = "manual_upload"
    CONNECT_API = "connect_api"
    AI_RESEARCH = "ai_research"
    AI_GENERATION = "ai_generation"
    SNAPSHOT_IMPORT = "snapshot_import"


class AlertState(str, Enum):
    """Checklist item alert states (blueprint.md §7.2)"""
    READY = "ready"               # ✅ Ready
    NEEDS_ATTENTION = "needs_attention"  # 🟡 Needs attention
    BLOCKED = "blocked"           # 🔴 Blocked
    NOT_STARTED = "not_started"   # ⚪ Not started


class TaskAction(str, Enum):
    """Available actions for tasks (blueprint.md §3.1.D)"""
    AI_GENERATE = "ai_generate"
    AI_RESEARCH = "ai_research"
    MANUAL_ADD = "manual_add"
    CONNECT_SOURCE = "connect_source"


# ============================================================================
# Blueprint Model (blueprint.md §3)
# ============================================================================

class Blueprint(Base):
    """
    Blueprint - the versioned, auditable "construction plan" for a project.

    Reference: blueprint.md §3

    Each project can have multiple blueprint versions.
    Each run references a specific blueprint version.
    Blueprint changes create new versions (audit-tracked).
    """
    __tablename__ = "blueprints"
    __table_args__ = (
        UniqueConstraint('project_id', 'version', name='uq_blueprint_project_version'),
    )

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Versioning (blueprint.md §1.1)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # =========================================================================
    # A) Project Profile (blueprint.md §3.1.A)
    # =========================================================================
    goal_text: Mapped[str] = mapped_column(Text, nullable=False)
    goal_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    domain_guess: Mapped[str] = mapped_column(
        String(50), default=DomainGuess.GENERIC.value, nullable=False
    )
    target_outputs: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # List of TargetOutput values
    horizon: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # {range: str, granularity: str}
    scope: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # {geography: str, entity: str}
    success_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # What "good prediction" means

    # =========================================================================
    # B) Strategy (blueprint.md §3.1.B)
    # =========================================================================
    recommended_core: Mapped[str] = mapped_column(
        String(50), default="collective", nullable=False
    )  # collective / targeted / hybrid
    primary_drivers: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # List of PrimaryDriver values
    required_modules: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # List of enabled engine modules

    # =========================================================================
    # C) Input Slots (Contract) - stored as JSON array
    # =========================================================================
    input_slots: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # List of InputSlot objects

    # =========================================================================
    # D) Section Task Map - stored as JSON object
    # =========================================================================
    section_task_map: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # {section_id: [tasks]}

    # =========================================================================
    # E) Calibration + Backtest Plan (blueprint.md §3.1.E)
    # =========================================================================
    calibration_plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # {required_windows, labels_needed, metrics, min_test_suite}

    # =========================================================================
    # F) Universe Map / Branching Plan (blueprint.md §3.1.F)
    # =========================================================================
    branching_plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # {branchable_variables, event_suggestions, aggregation_policy}

    # =========================================================================
    # G) Policy + Audit Metadata (blueprint.md §3.1.G)
    # =========================================================================
    clarification_answers: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # User answers during clarification Q&A
    constraints_applied: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # What policy rules forced
    risk_notes: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True
    )  # Risk notes from goal analysis

    # Audit fields
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
        nullable=False
    )

    # Draft status (blueprint.md §4.3)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    draft_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    project: Mapped["ProjectSpec"] = relationship(
        "ProjectSpec",
        foreign_keys=[project_id],
        backref="blueprints"
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by]
    )
    slots: Mapped[List["BlueprintSlot"]] = relationship(
        "BlueprintSlot",
        back_populates="blueprint",
        cascade="all, delete-orphan"
    )
    tasks: Mapped[List["BlueprintTask"]] = relationship(
        "BlueprintTask",
        back_populates="blueprint",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Blueprint {self.id} project={self.project_id} v{self.version}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation."""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "tenant_id": str(self.tenant_id),
            "version": self.version,
            "policy_version": self.policy_version,
            "is_active": self.is_active,
            # Project Profile
            "goal_text": self.goal_text,
            "goal_summary": self.goal_summary,
            "domain_guess": self.domain_guess,
            "target_outputs": self.target_outputs,
            "horizon": self.horizon,
            "scope": self.scope,
            "success_metrics": self.success_metrics,
            # Strategy
            "recommended_core": self.recommended_core,
            "primary_drivers": self.primary_drivers,
            "required_modules": self.required_modules,
            # Input Slots
            "input_slots": self.input_slots,
            # Section Task Map
            "section_task_map": self.section_task_map,
            # Plans
            "calibration_plan": self.calibration_plan,
            "branching_plan": self.branching_plan,
            # Audit
            "clarification_answers": self.clarification_answers,
            "constraints_applied": self.constraints_applied,
            "risk_notes": self.risk_notes,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_draft": self.is_draft,
        }


# ============================================================================
# BlueprintSlot Model (blueprint.md §3.1.C, §6)
# ============================================================================

class BlueprintSlot(Base):
    """
    Input Slot - defines a data requirement for the project.

    Reference: blueprint.md §3.1.C, §6

    Each slot can be fulfilled via:
    - Manual upload (CSV/JSON/docs)
    - Connect API source
    - Snapshot import
    - AI Research (subject to temporal cutoff)
    - AI Generation (synthetic, with explicit labeling)
    """
    __tablename__ = "blueprint_slots"
    __table_args__ = (
        UniqueConstraint('blueprint_id', 'slot_id', name='uq_slot_blueprint'),
    )

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprints.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # Note: tenant_id is inherited from parent blueprint (no direct column needed)

    # Slot definition
    slot_id: Mapped[str] = mapped_column(String(100), nullable=False)
    slot_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slot_type: Mapped[str] = mapped_column(
        String(50), default=SlotType.TABLE.value, nullable=False
    )
    required_level: Mapped[str] = mapped_column(
        String(50), default=RequiredLevel.REQUIRED.value, nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Requirements (blueprint.md §3.1.C)
    schema_requirements: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # {min_fields, types, allowed_values}
    temporal_requirements: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # {must_have_timestamps, must_be_before_cutoff, required_window}
    quality_requirements: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # {missing_thresholds, dedupe_rules, min_coverage}

    # Acquisition methods
    allowed_acquisition_methods: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True
    )  # List of AcquisitionMethod values

    # Validation and derived artifacts
    validation_plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # How we validate it
    derived_artifacts: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True
    )  # What compiled outputs it produces

    # Status (blueprint.md §7.2)
    status: Mapped[str] = mapped_column(
        String(50), default=AlertState.NOT_STARTED.value, nullable=False
    )
    status_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Fulfillment tracking
    fulfilled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fulfilled_by: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # Reference to data source/artifact that fulfills this slot
    fulfillment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # AI artifacts (blueprint.md §6.3)
    validation_artifact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    summary_artifact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    alignment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    alignment_reasons: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True
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
    blueprint: Mapped["Blueprint"] = relationship(
        "Blueprint",
        back_populates="slots"
    )

    def __repr__(self) -> str:
        return f"<BlueprintSlot {self.slot_id} type={self.slot_type}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation."""
        return {
            "id": str(self.id),
            "blueprint_id": str(self.blueprint_id),
            "slot_id": self.slot_id,
            "slot_name": self.slot_name,
            "slot_type": self.slot_type,
            "required_level": self.required_level,
            "description": self.description,
            "schema_requirements": self.schema_requirements,
            "temporal_requirements": self.temporal_requirements,
            "quality_requirements": self.quality_requirements,
            "allowed_acquisition_methods": self.allowed_acquisition_methods,
            "validation_plan": self.validation_plan,
            "derived_artifacts": self.derived_artifacts,
            "status": self.status,
            "status_reason": self.status_reason,
            "fulfilled": self.fulfilled,
            "fulfilled_by": self.fulfilled_by,
            "fulfillment_method": self.fulfillment_method,
            "alignment_score": self.alignment_score,
            "alignment_reasons": self.alignment_reasons,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================================
# BlueprintTask Model (blueprint.md §3.1.D)
# ============================================================================

class BlueprintTask(Base):
    """
    Section Task - defines a task for a project section.

    Reference: blueprint.md §3.1.D, §7, §8

    For every platform section, the blueprint defines tasks with:
    - title, why_it_matters
    - linked_slots
    - actions (AI generate / AI research / manual add / connect source)
    - completion_criteria
    - alerts
    """
    __tablename__ = "blueprint_tasks"
    __table_args__ = (
        UniqueConstraint('blueprint_id', 'task_id', name='uq_task_blueprint'),
    )

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    blueprint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blueprints.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # Note: tenant_id is inherited from parent blueprint (no direct column needed)

    # Task identification
    task_id: Mapped[str] = mapped_column(String(100), nullable=False)
    section_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Task content (blueprint.md §3.1.D)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    why_it_matters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Linked slots
    linked_slot_ids: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True
    )  # List of slot_ids that complete this task

    # Actions (blueprint.md §3.1.D)
    available_actions: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True
    )  # List of TaskAction values

    # Completion criteria
    completion_criteria: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # What artifact must exist for completion

    # Alert configuration
    alert_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )  # What to warn about if incomplete or low quality

    # Status (blueprint.md §7.2)
    status: Mapped[str] = mapped_column(
        String(50), default=AlertState.NOT_STARTED.value, nullable=False
    )
    status_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AI artifacts
    last_summary_ref: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    last_validation_ref: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
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
    blueprint: Mapped["Blueprint"] = relationship(
        "Blueprint",
        back_populates="tasks"
    )

    def __repr__(self) -> str:
        return f"<BlueprintTask {self.task_id} section={self.section_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation."""
        return {
            "id": str(self.id),
            "blueprint_id": str(self.blueprint_id),
            "task_id": self.task_id,
            "section_id": self.section_id,
            "sort_order": self.sort_order,
            "title": self.title,
            "description": self.description,
            "why_it_matters": self.why_it_matters,
            "linked_slot_ids": self.linked_slot_ids,
            "available_actions": self.available_actions,
            "completion_criteria": self.completion_criteria,
            "alert_config": self.alert_config,
            "status": self.status,
            "status_reason": self.status_reason,
            "last_summary_ref": str(self.last_summary_ref) if self.last_summary_ref else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================================
# Section IDs (blueprint.md §8.1)
# ============================================================================

PLATFORM_SECTIONS = [
    "overview",
    "inputs",
    "data",
    "personas",
    "rules",
    "run_params",
    "run_center",
    "event_lab",
    "universe_map",
    "society_simulation",
    "target_planner",
    "reliability",
    "telemetry_replay",
    "world_viewer_2d",
    "reports",
    "settings",
    "library",
    "calibration_lab",
]
