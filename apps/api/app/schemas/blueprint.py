"""
Blueprint Schemas (blueprint.md §3)
Reference: blueprint.md §3, §4, §5, §6, §7

Pydantic schemas for Blueprint-related API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Enums
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
    READY = "ready"
    NEEDS_ATTENTION = "needs_attention"
    BLOCKED = "blocked"
    NOT_STARTED = "not_started"


class TaskAction(str, Enum):
    """Available actions for tasks (blueprint.md §3.1.D)"""
    AI_GENERATE = "ai_generate"
    AI_RESEARCH = "ai_research"
    MANUAL_ADD = "manual_add"
    CONNECT_SOURCE = "connect_source"


class PILJobStatus(str, Enum):
    """Job state machine (blueprint.md §5.3)"""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class PILJobType(str, Enum):
    """Types of PIL background jobs"""
    GOAL_ANALYSIS = "goal_analysis"
    CLARIFICATION_GENERATE = "clarification_generate"
    BLUEPRINT_BUILD = "blueprint_build"
    SLOT_VALIDATION = "slot_validation"
    SLOT_SUMMARIZATION = "slot_summarization"
    SLOT_ALIGNMENT_SCORING = "slot_alignment_scoring"
    SLOT_COMPILATION = "slot_compilation"
    TASK_VALIDATION = "task_validation"
    TASK_GUIDANCE_GENERATE = "task_guidance_generate"
    CALIBRATION_CHECK = "calibration_check"
    BACKTEST_VALIDATION = "backtest_validation"
    RELIABILITY_ANALYSIS = "reliability_analysis"
    AI_RESEARCH = "ai_research"
    AI_GENERATION = "ai_generation"


# ============================================================================
# Nested Schemas
# ============================================================================

class HorizonSchema(BaseModel):
    """Time horizon configuration"""
    range: str = Field(..., description="e.g., '6 months', '2026-Q1'")
    granularity: str = Field(
        default="monthly",
        pattern="^(daily|weekly|monthly|event_based)$"
    )


class ScopeSchema(BaseModel):
    """Scope configuration"""
    geography: Optional[str] = None
    entity: Optional[str] = None


class SuccessMetricsSchema(BaseModel):
    """Success metrics configuration"""
    description: str
    evaluation_metrics: List[str] = []


class SchemaRequirements(BaseModel):
    """Schema requirements for a slot"""
    min_fields: Optional[List[str]] = None
    types: Optional[Dict[str, str]] = None
    allowed_values: Optional[Dict[str, List[str]]] = None


class TemporalRequirements(BaseModel):
    """Temporal requirements for a slot"""
    must_have_timestamps: bool = False
    must_be_before_cutoff: bool = False
    required_window: Optional[str] = None


class QualityRequirements(BaseModel):
    """Quality requirements for a slot"""
    missing_threshold: Optional[float] = Field(None, ge=0, le=1)
    dedupe_rules: Optional[List[str]] = None
    min_coverage: Optional[float] = Field(None, ge=0, le=1)


class ValidationPlan(BaseModel):
    """Validation plan for a slot"""
    ai_checks: List[str] = []
    programmatic_checks: List[str] = []


class FulfilledByRef(BaseModel):
    """Reference to what fulfills a slot"""
    type: str
    id: str
    name: str


# ============================================================================
# Slot Schemas
# ============================================================================

class BlueprintSlotBase(BaseModel):
    """Base slot schema"""
    slot_id: str = Field(..., min_length=1, max_length=100)
    slot_name: str = Field(..., min_length=1, max_length=255)
    slot_type: SlotType = SlotType.TABLE
    required_level: RequiredLevel = RequiredLevel.REQUIRED
    description: Optional[str] = None


class BlueprintSlotCreate(BlueprintSlotBase):
    """Schema for creating a slot"""
    schema_requirements: Optional[SchemaRequirements] = None
    temporal_requirements: Optional[TemporalRequirements] = None
    quality_requirements: Optional[QualityRequirements] = None
    allowed_acquisition_methods: Optional[List[AcquisitionMethod]] = None
    validation_plan: Optional[ValidationPlan] = None
    derived_artifacts: Optional[List[str]] = None


class BlueprintSlotUpdate(BaseModel):
    """Schema for updating a slot"""
    status: Optional[AlertState] = None
    status_reason: Optional[str] = None
    fulfilled: Optional[bool] = None
    fulfilled_by: Optional[FulfilledByRef] = None
    fulfillment_method: Optional[AcquisitionMethod] = None
    alignment_score: Optional[float] = Field(None, ge=0, le=1)
    alignment_reasons: Optional[List[str]] = None


class BlueprintSlotResponse(BlueprintSlotBase):
    """Schema for slot response"""
    id: UUID
    blueprint_id: UUID
    schema_requirements: Optional[Dict[str, Any]] = None
    temporal_requirements: Optional[Dict[str, Any]] = None
    quality_requirements: Optional[Dict[str, Any]] = None
    allowed_acquisition_methods: Optional[List[str]] = None
    validation_plan: Optional[Dict[str, Any]] = None
    derived_artifacts: Optional[List[str]] = None
    status: AlertState = AlertState.NOT_STARTED
    status_reason: Optional[str] = None
    fulfilled: bool = False
    fulfilled_by: Optional[Dict[str, Any]] = None
    fulfillment_method: Optional[str] = None
    alignment_score: Optional[float] = None
    alignment_reasons: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Task Schemas
# ============================================================================

class CompletionCriteria(BaseModel):
    """Completion criteria for a task"""
    artifact_type: str
    artifact_exists: bool = True


class AlertConfig(BaseModel):
    """Alert configuration for a task"""
    warn_if_incomplete: bool = True
    warn_if_low_quality: bool = True
    quality_threshold: Optional[float] = Field(None, ge=0, le=1)


class BlueprintTaskBase(BaseModel):
    """Base task schema"""
    task_id: str = Field(..., min_length=1, max_length=100)
    section_id: str = Field(..., min_length=1, max_length=100)
    sort_order: int = 0
    title: str = Field(..., min_length=1, max_length=255)


class BlueprintTaskCreate(BlueprintTaskBase):
    """Schema for creating a task"""
    description: Optional[str] = None
    why_it_matters: Optional[str] = None
    linked_slot_ids: Optional[List[str]] = None
    available_actions: Optional[List[TaskAction]] = None
    completion_criteria: Optional[CompletionCriteria] = None
    alert_config: Optional[AlertConfig] = None


class BlueprintTaskUpdate(BaseModel):
    """Schema for updating a task"""
    status: Optional[AlertState] = None
    status_reason: Optional[str] = None
    last_summary_ref: Optional[UUID] = None
    last_validation_ref: Optional[UUID] = None


class BlueprintTaskResponse(BlueprintTaskBase):
    """Schema for task response"""
    id: UUID
    blueprint_id: UUID
    description: Optional[str] = None
    why_it_matters: Optional[str] = None
    linked_slot_ids: Optional[List[str]] = None
    available_actions: Optional[List[str]] = None
    completion_criteria: Optional[Dict[str, Any]] = None
    alert_config: Optional[Dict[str, Any]] = None
    status: AlertState = AlertState.NOT_STARTED
    status_reason: Optional[str] = None
    last_summary_ref: Optional[UUID] = None
    last_validation_ref: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Blueprint Schemas
# ============================================================================

class CalibrationPlan(BaseModel):
    """Calibration plan (blueprint.md §3.1.E)"""
    required_historical_windows: List[str] = []
    labels_needed: List[str] = []
    evaluation_metrics: List[str] = []
    min_test_suite_size: int = 1


class BranchingPlan(BaseModel):
    """Branching plan for Universe Map (blueprint.md §3.1.F)"""
    branchable_variables: List[str] = []
    event_template_suggestions: List[str] = []
    probability_aggregation_policy: str = "mean"
    node_metadata_requirements: List[str] = []


class BlueprintBase(BaseModel):
    """Base blueprint schema"""
    goal_text: str = Field(..., min_length=1)


class BlueprintCreate(BlueprintBase):
    """Schema for creating a blueprint (blueprint.md §4.2)"""
    project_id: UUID
    skip_clarification: bool = False


class BlueprintUpdate(BaseModel):
    """Schema for updating a blueprint"""
    goal_summary: Optional[str] = None
    domain_guess: Optional[DomainGuess] = None
    target_outputs: Optional[List[TargetOutput]] = None
    horizon: Optional[HorizonSchema] = None
    scope: Optional[ScopeSchema] = None
    success_metrics: Optional[SuccessMetricsSchema] = None
    recommended_core: Optional[str] = None
    primary_drivers: Optional[List[PrimaryDriver]] = None
    required_modules: Optional[List[str]] = None
    calibration_plan: Optional[CalibrationPlan] = None
    branching_plan: Optional[BranchingPlan] = None
    clarification_answers: Optional[Dict[str, str]] = None
    constraints_applied: Optional[List[str]] = None
    risk_notes: Optional[List[str]] = None
    is_draft: Optional[bool] = None


class BlueprintResponse(BlueprintBase):
    """Schema for blueprint response"""
    id: UUID
    project_id: UUID
    tenant_id: UUID
    version: int
    policy_version: str
    is_active: bool
    # Project Profile
    goal_summary: Optional[str] = None
    domain_guess: DomainGuess = DomainGuess.GENERIC
    target_outputs: Optional[List[str]] = None
    horizon: Optional[Dict[str, Any]] = None
    scope: Optional[Dict[str, Any]] = None
    success_metrics: Optional[Dict[str, Any]] = None
    # Strategy
    recommended_core: str = "collective"
    primary_drivers: Optional[List[str]] = None
    required_modules: Optional[List[str]] = None
    # Plans
    calibration_plan: Optional[Dict[str, Any]] = None
    branching_plan: Optional[Dict[str, Any]] = None
    # Audit
    clarification_answers: Optional[Dict[str, str]] = None
    constraints_applied: Optional[List[str]] = None
    risk_notes: Optional[List[str]] = None
    created_by: Optional[UUID] = None
    is_draft: bool = True
    created_at: datetime
    updated_at: datetime
    # Nested
    slots: List[BlueprintSlotResponse] = []
    tasks: List[BlueprintTaskResponse] = []

    class Config:
        from_attributes = True


class BlueprintSummary(BaseModel):
    """Summary for blueprint lists"""
    id: UUID
    project_id: UUID
    version: int
    is_active: bool
    goal_summary: Optional[str] = None
    domain_guess: DomainGuess = DomainGuess.GENERIC
    is_draft: bool = True
    created_at: datetime
    slots_ready: int = 0
    slots_total: int = 0
    tasks_ready: int = 0
    tasks_total: int = 0

    class Config:
        from_attributes = True


# ============================================================================
# Goal Analysis & Clarification Schemas (blueprint.md §4.2)
# ============================================================================

class ClarifyingQuestion(BaseModel):
    """A clarifying question for goal analysis (blueprint.md §4.2.1)"""
    id: str
    question: str
    reason: str = Field(..., description="Why we ask this question")
    type: str = Field(
        default="single_select",
        pattern="^(single_select|multi_select|short_input)$"
    )
    options: Optional[List[str]] = None
    required: bool = True


class GoalAnalysisResult(BaseModel):
    """Result of goal analysis job"""
    goal_summary: str
    domain_guess: DomainGuess
    clarifying_questions: List[ClarifyingQuestion]
    blueprint_preview: Dict[str, Any] = Field(
        description="Preview of required/recommended slots and tasks"
    )
    risk_notes: List[str] = []


class ClarificationAnswer(BaseModel):
    """User's answer to a clarifying question"""
    question_id: str
    answer: str


class SubmitClarificationAnswers(BaseModel):
    """Submit clarification answers to finalize blueprint"""
    blueprint_id: UUID
    answers: List[ClarificationAnswer]


# ============================================================================
# PIL Job Schemas (blueprint.md §5)
# ============================================================================

class PILJobCreate(BaseModel):
    """Schema for creating a PIL job"""
    job_type: PILJobType
    job_name: str = Field(..., min_length=1, max_length=255)
    project_id: Optional[UUID] = None
    blueprint_id: Optional[UUID] = None
    input_params: Optional[Dict[str, Any]] = None
    slot_id: Optional[str] = None
    task_id: Optional[str] = None
    priority: str = "normal"


class PILJobUpdate(BaseModel):
    """Schema for updating a PIL job"""
    status: Optional[PILJobStatus] = None
    progress_percent: Optional[int] = Field(None, ge=0, le=100)
    stage_name: Optional[str] = None
    eta_hint: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    artifact_ids: Optional[List[str]] = None


class PILJobResponse(BaseModel):
    """Schema for PIL job response"""
    id: UUID
    tenant_id: UUID
    project_id: Optional[UUID] = None
    blueprint_id: Optional[UUID] = None
    job_type: PILJobType
    job_name: str
    priority: str
    celery_task_id: Optional[str] = None
    status: PILJobStatus
    progress_percent: int = 0
    stage_name: Optional[str] = None
    eta_hint: Optional[str] = None
    stages_completed: int = 0
    stages_total: int = 1
    input_params: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    artifact_ids: Optional[List[str]] = None
    slot_id: Optional[str] = None
    task_id: Optional[str] = None
    retry_count: int = 0
    created_by: Optional[UUID] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class PILJobProgress(BaseModel):
    """Progress update for a PIL job (blueprint.md §5.4)"""
    job_id: UUID
    progress_percent: int = Field(..., ge=0, le=100)
    stage_name: Optional[str] = None
    eta_hint: Optional[str] = None


# ============================================================================
# PIL Artifact Schemas (blueprint.md §5.6)
# ============================================================================

class PILArtifactCreate(BaseModel):
    """Schema for creating a PIL artifact"""
    artifact_type: str
    artifact_name: str = Field(..., min_length=1, max_length=255)
    project_id: UUID
    blueprint_id: Optional[UUID] = None
    blueprint_version: Optional[int] = None
    job_id: Optional[UUID] = None
    slot_id: Optional[str] = None
    task_id: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    content_text: Optional[str] = None
    alignment_score: Optional[float] = Field(None, ge=0, le=1)
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    validation_passed: Optional[bool] = None


class PILArtifactResponse(BaseModel):
    """Schema for PIL artifact response"""
    id: UUID
    tenant_id: UUID
    project_id: UUID
    blueprint_id: Optional[UUID] = None
    blueprint_version: Optional[int] = None
    artifact_type: str
    artifact_name: str
    job_id: Optional[UUID] = None
    slot_id: Optional[str] = None
    task_id: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    content_text: Optional[str] = None
    alignment_score: Optional[float] = None
    quality_score: Optional[float] = None
    validation_passed: Optional[bool] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Guidance Panel & Checklist Schemas (blueprint.md §7, §8)
# ============================================================================

class NextAction(BaseModel):
    """Next suggested action"""
    action: TaskAction
    target_slot_id: Optional[str] = None
    target_task_id: Optional[str] = None
    reason: str


class GuidancePanel(BaseModel):
    """Guidance panel data for a section (blueprint.md §8)"""
    section_id: str
    project_id: UUID
    blueprint_version: int
    tasks: List[BlueprintTaskResponse]
    required_slots: List[BlueprintSlotResponse]
    recommended_slots: List[BlueprintSlotResponse]
    overall_status: AlertState
    next_suggested_action: Optional[NextAction] = None


class ChecklistItem(BaseModel):
    """Checklist item with alert state (blueprint.md §7)"""
    id: str
    title: str
    section_id: str
    status: AlertState
    status_reason: Optional[str] = None
    why_it_matters: Optional[str] = None
    missing_items: Optional[List[str]] = None
    next_action: Optional[Dict[str, str]] = None
    latest_summary: Optional[str] = None
    match_score: Optional[float] = None


class ProjectChecklist(BaseModel):
    """Project checklist (blueprint.md §7)"""
    project_id: UUID
    blueprint_id: UUID
    blueprint_version: int
    items: List[ChecklistItem]
    ready_count: int = 0
    needs_attention_count: int = 0
    blocked_count: int = 0
    not_started_count: int = 0
    overall_readiness: str = "needs_work"


# ============================================================================
# Job Notification Schema (blueprint.md §5.5)
# ============================================================================

class JobNotification(BaseModel):
    """Notification for job completion (blueprint.md §5.5)"""
    job_id: UUID
    job_type: PILJobType
    job_name: str
    status: PILJobStatus
    message: str
    artifact_ids: Optional[List[str]] = None
    timestamp: datetime
