"""
Event Script Schemas
Pydantic schemas for Event Script API endpoints.
Reference: project.md §6.4, §11 Phase 3
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Enums (matching models/event_script.py)
# =============================================================================

class EventType(str, Enum):
    """Types of events (project.md §6.4)."""
    POLICY = "policy"
    MEDIA = "media"
    SHOCK = "shock"
    INDIVIDUAL_ACTION = "individual_action"
    ENVIRONMENTAL = "environmental"
    SOCIAL = "social"
    CUSTOM = "custom"


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


class TriggerSource(str, Enum):
    """How an event was triggered."""
    SCHEDULED = "scheduled"
    CONDITION = "condition"
    MANUAL = "manual"


# =============================================================================
# Delta Schemas
# =============================================================================

class DeltaSchema(BaseModel):
    """A single delta (change) to apply."""
    variable: str = Field(..., description="Variable path to modify")
    operation: DeltaOperation = Field(default=DeltaOperation.SET)
    value: Any = Field(..., description="Value to apply")
    conditions: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional conditions for applying this delta"
    )


class DeltasSchema(BaseModel):
    """Collection of deltas for an event."""
    environment_deltas: List[DeltaSchema] = Field(default_factory=list)
    perception_deltas: List[DeltaSchema] = Field(default_factory=list)
    custom_deltas: List[DeltaSchema] = Field(default_factory=list)


# =============================================================================
# Scope Schemas
# =============================================================================

class ScopeSchema(BaseModel):
    """Who/where/when is affected by an event."""
    affected_regions: Optional[List[str]] = Field(
        default=None, description="List of region IDs affected"
    )
    affected_persona_segments: Optional[List[str]] = Field(
        default=None, description="List of persona segment IDs affected"
    )
    target_agent_ids: Optional[List[UUID]] = Field(
        default=None, description="Specific agent IDs to target"
    )
    start_tick: Optional[int] = Field(
        default=None, description="Tick when event starts"
    )
    end_tick: Optional[int] = Field(
        default=None, description="Tick when event ends (None = permanent)"
    )


# =============================================================================
# Intensity Profile Schemas
# =============================================================================

class IntensityProfileSchema(BaseModel):
    """How the event effect applies over time."""
    profile_type: IntensityProfileType = Field(default=IntensityProfileType.INSTANTANEOUS)
    initial_intensity: float = Field(default=1.0, ge=0.0, le=1.0)
    decay_rate: Optional[float] = Field(
        default=None, description="Decay rate for linear/exponential profiles"
    )
    half_life_ticks: Optional[int] = Field(
        default=None, description="Half-life in ticks for exponential decay"
    )
    lag_ticks: Optional[int] = Field(
        default=None, description="Delay before effect starts (lagged profile)"
    )
    custom_profile: Optional[List[float]] = Field(
        default=None, description="Custom intensity values per tick"
    )


# =============================================================================
# Uncertainty Schemas
# =============================================================================

class UncertaintySchema(BaseModel):
    """Uncertainty quantification for an event."""
    occurrence_probability: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Probability that this event occurs"
    )
    intensity_variance: float = Field(
        default=0.0, ge=0.0,
        description="Variance in intensity application"
    )
    assumptions: Optional[List[str]] = Field(
        default=None, description="Assumptions underlying this event"
    )
    compilation_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Confidence in the compilation from NL"
    )


# =============================================================================
# Provenance Schemas
# =============================================================================

class ProvenanceSchema(BaseModel):
    """Where an event came from (C5: LLMs as compilers)."""
    compiled_from: Optional[str] = Field(
        default=None, description="Original natural language prompt"
    )
    compiler_version: Optional[str] = Field(
        default=None, description="Version of the event compiler"
    )
    compiler_model: Optional[str] = Field(
        default=None, description="LLM model used for compilation"
    )
    compiled_at: Optional[datetime] = Field(
        default=None, description="When compilation occurred"
    )
    manually_edited: bool = Field(
        default=False, description="Whether human-edited after compilation"
    )


# =============================================================================
# Event Script Schemas
# =============================================================================

class EventScriptBase(BaseModel):
    """Base event script schema."""
    event_type: EventType = Field(default=EventType.CUSTOM)
    label: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    scope: ScopeSchema = Field(default_factory=ScopeSchema)
    deltas: DeltasSchema = Field(default_factory=DeltasSchema)
    intensity_profile: IntensityProfileSchema = Field(
        default_factory=IntensityProfileSchema
    )
    uncertainty: UncertaintySchema = Field(default_factory=UncertaintySchema)
    tags: Optional[List[str]] = None


class EventScriptCreate(EventScriptBase):
    """Schema for creating an event script."""
    project_id: UUID
    provenance: Optional[ProvenanceSchema] = None


class EventScriptUpdate(BaseModel):
    """Schema for updating an event script."""
    event_type: Optional[EventType] = None
    label: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    scope: Optional[ScopeSchema] = None
    deltas: Optional[DeltasSchema] = None
    intensity_profile: Optional[IntensityProfileSchema] = None
    uncertainty: Optional[UncertaintySchema] = None
    provenance: Optional[ProvenanceSchema] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_validated: Optional[bool] = None


class EventScriptResponse(EventScriptBase):
    """Schema for event script response."""
    event_id: UUID
    project_id: UUID
    provenance: ProvenanceSchema
    event_version: str
    schema_version: str
    is_active: bool
    is_validated: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventScriptListResponse(BaseModel):
    """Schema for list of event scripts."""
    event_id: UUID
    project_id: UUID
    event_type: EventType
    label: str
    is_active: bool
    is_validated: bool
    tags: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Event Bundle Schemas (P3-002)
# =============================================================================

class EventBundleBase(BaseModel):
    """Base event bundle schema."""
    label: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    joint_probability: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Combined probability of all events in bundle"
    )


class EventBundleCreate(EventBundleBase):
    """Schema for creating an event bundle."""
    project_id: UUID
    event_ids: List[UUID] = Field(
        ..., min_length=1, description="Event script IDs to include"
    )
    execution_order: Optional[List[UUID]] = Field(
        default=None, description="Order to execute events (if dependencies)"
    )
    provenance: Optional[ProvenanceSchema] = None


class EventBundleUpdate(BaseModel):
    """Schema for updating an event bundle."""
    label: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    event_ids: Optional[List[UUID]] = None
    execution_order: Optional[List[UUID]] = None
    joint_probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_active: Optional[bool] = None


class EventBundleResponse(EventBundleBase):
    """Schema for event bundle response."""
    bundle_id: UUID
    project_id: UUID
    event_ids: List[UUID]
    execution_order: Optional[List[UUID]] = None
    provenance: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Event Trigger Log Schemas (P3-003)
# =============================================================================

class EventTriggerLogCreate(BaseModel):
    """Schema for creating a trigger log entry."""
    run_id: UUID
    event_script_id: Optional[UUID] = None
    triggered_at_tick: int = Field(..., ge=0)
    trigger_source: TriggerSource
    affected_agent_count: int = Field(default=0, ge=0)
    affected_segment_count: int = Field(default=0, ge=0)
    affected_region_count: int = Field(default=0, ge=0)
    applied_deltas: Dict[str, Any] = Field(default_factory=dict)
    applied_intensity: float = Field(default=1.0, ge=0.0, le=1.0)
    effect_summary: Dict[str, Any] = Field(default_factory=dict)


class EventTriggerLogResponse(BaseModel):
    """Schema for trigger log response."""
    log_id: UUID
    run_id: UUID
    event_id: Optional[UUID] = None
    triggered_at_tick: int
    trigger_source: TriggerSource
    affected_agent_count: int
    affected_segment_count: int
    affected_region_count: int
    applied_deltas: Dict[str, Any]
    applied_intensity: float
    effect_summary: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class EventTriggerLogListResponse(BaseModel):
    """Schema for list of trigger logs."""
    log_id: UUID
    run_id: UUID
    event_id: Optional[UUID] = None
    triggered_at_tick: int
    trigger_source: TriggerSource
    affected_agent_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Execution Request/Response Schemas
# =============================================================================

class EventExecutionRequest(BaseModel):
    """Request to execute an event script."""
    event_id: UUID
    run_id: UUID
    current_tick: int = Field(..., ge=0)
    target_agent_ids: Optional[List[UUID]] = Field(
        default=None, description="Override scope with specific agents"
    )
    intensity_override: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Override intensity"
    )


class EventExecutionResult(BaseModel):
    """Result of executing an event script."""
    event_id: UUID
    run_id: UUID
    executed_at_tick: int
    affected_agent_count: int
    affected_segment_count: int
    affected_region_count: int
    applied_intensity: float
    deltas_applied: DeltasSchema
    effect_summary: Dict[str, Any]
    trigger_log_id: UUID


class BundleExecutionRequest(BaseModel):
    """Request to execute an event bundle."""
    bundle_id: UUID
    run_id: UUID
    current_tick: int = Field(..., ge=0)
    skip_probability_check: bool = Field(
        default=False, description="Execute regardless of joint_probability"
    )


class BundleExecutionResult(BaseModel):
    """Result of executing an event bundle."""
    bundle_id: UUID
    run_id: UUID
    executed_at_tick: int
    events_executed: int
    events_skipped: int
    total_affected_agents: int
    event_results: List[EventExecutionResult]
