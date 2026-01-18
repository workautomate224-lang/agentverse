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
    FINAL_BLUEPRINT_BUILD = "final_blueprint_build"  # Slice 2A: Blueprint v2
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
    sort_order: int = 0
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
    section_id: str = Field(..., min_length=1, max_length=50)
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
    last_summary_ref: Optional[str] = None


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
    last_summary_ref: Optional[str] = None
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


# ============================================================================
# Blueprint v2 Schemas (Slice 2A: Final Blueprint Build)
# ============================================================================

class BlueprintV2Intent(BaseModel):
    """Blueprint v2: Intent section - captures the user's goal and objective."""
    goal_text: str = Field(..., description="Original user goal text")
    summary: str = Field(..., description="AI-generated concise summary")
    domain: DomainGuess = Field(..., description="Classified domain category")
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Confidence in domain classification"
    )


class BlueprintV2PredictionTarget(BaseModel):
    """Blueprint v2: Prediction Target section - what the simulation aims to predict."""
    primary_metric: str = Field(..., description="The main quantity being predicted")
    metric_type: str = Field(
        default="distribution",
        description="Type: distribution | point_estimate | ranked_outcomes | paths"
    )
    entity_type: str = Field(..., description="What entity is being predicted for")
    aggregation_level: str = Field(
        default="population", description="Level of aggregation for predictions"
    )


class BlueprintV2Horizon(BaseModel):
    """Blueprint v2: Horizon section - time boundaries for the prediction."""
    prediction_window: str = Field(..., description="How far ahead to predict, e.g., '6 months'")
    granularity: str = Field(
        default="monthly",
        description="Time granularity: daily | weekly | monthly | event_based"
    )
    start_date: Optional[str] = Field(None, description="Optional explicit start date")
    end_date: Optional[str] = Field(None, description="Optional explicit end date")


class BlueprintV2OutputFormat(BaseModel):
    """Blueprint v2: Output Format section - how results should be structured."""
    output_types: List[TargetOutput] = Field(
        ..., description="Types of output required"
    )
    visualization_requirements: List[str] = Field(
        default_factory=list, description="Required visualization types"
    )
    export_formats: List[str] = Field(
        default_factory=lambda: ["json", "csv"],
        description="Required export formats"
    )
    confidence_intervals: bool = Field(
        default=True, description="Include confidence intervals in output"
    )


class BlueprintV2EvaluationPlan(BaseModel):
    """Blueprint v2: Evaluation Plan section - how to validate the predictions."""
    evaluation_metrics: List[str] = Field(
        ..., description="Metrics to evaluate prediction quality"
    )
    calibration_requirements: CalibrationPlan = Field(
        ..., description="Calibration plan details"
    )
    backtest_windows: List[str] = Field(
        default_factory=list, description="Historical windows for backtesting"
    )
    success_criteria: Optional[str] = Field(
        None, description="What constitutes a successful prediction"
    )


class BlueprintV2RequiredInput(BaseModel):
    """Blueprint v2: Single required input specification."""
    slot_id: str = Field(..., description="Unique identifier for this input slot")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="What this input is for")
    data_type: SlotType = Field(..., description="Type of data expected")
    required_level: RequiredLevel = Field(..., description="How critical this input is")
    example_sources: List[str] = Field(
        default_factory=list, description="Where this data might come from"
    )
    schema_hint: Optional[Dict[str, Any]] = Field(
        None, description="Optional schema requirements"
    )


class BlueprintV2Provenance(BaseModel):
    """Blueprint v2: Provenance metadata - LLM proof for auditability."""
    call_id: str = Field(..., description="Unique identifier for the LLM call")
    model: str = Field(..., description="Model used for generation")
    provider: str = Field(..., description="LLM provider (e.g., openrouter)")
    input_tokens: int = Field(..., description="Number of input tokens")
    output_tokens: int = Field(..., description="Number of output tokens")
    cost_usd: float = Field(..., description="Cost of the LLM call in USD")
    cache_hit: bool = Field(..., description="Whether this was served from cache")
    timestamp: str = Field(..., description="ISO timestamp of generation")
    fallback_used: bool = Field(default=False, description="Whether fallback was used")


class BlueprintV2(BaseModel):
    """
    Blueprint v2: Complete structured blueprint format (Slice 2A).

    This is the deterministic JSON output produced by the final_blueprint_build job.
    All sections are required - validation will fail if any section is missing.
    """
    # Schema version for future compatibility
    schema_version: str = Field(default="2.0.0", description="Blueprint schema version")

    # Core sections (all required)
    intent: BlueprintV2Intent = Field(..., description="Goal and intent section")
    prediction_target: BlueprintV2PredictionTarget = Field(
        ..., description="What is being predicted"
    )
    horizon: BlueprintV2Horizon = Field(..., description="Time boundaries")
    output_format: BlueprintV2OutputFormat = Field(..., description="Output requirements")
    evaluation_plan: BlueprintV2EvaluationPlan = Field(
        ..., description="How to evaluate predictions"
    )
    required_inputs: List[BlueprintV2RequiredInput] = Field(
        ..., description="List of required data inputs (slots)"
    )

    # Section tasks (optional but recommended)
    section_tasks: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
        None, description="Tasks organized by section"
    )

    # Branching configuration (optional)
    branching_plan: Optional[BranchingPlan] = Field(
        None, description="Universe map branching configuration"
    )

    # Clarification answers from Q&A (audit trail)
    clarification_answers: Dict[str, Any] = Field(
        default_factory=dict, description="User answers during Q&A phase"
    )

    # Risk notes and warnings
    risk_notes: List[str] = Field(
        default_factory=list, description="Risk warnings from analysis"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Non-blocking warnings"
    )

    # Provenance (LLM proof - required for audit)
    provenance: BlueprintV2Provenance = Field(
        ..., description="LLM provenance for auditability"
    )

    # Metadata
    generated_at: str = Field(..., description="ISO timestamp of generation")
    processing_time_ms: int = Field(
        default=0, description="Time taken to generate in milliseconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "schema_version": "2.0.0",
                "intent": {
                    "goal_text": "Predict Tesla EV demand for 2026",
                    "summary": "Forecast consumer demand for Tesla electric vehicles in 2026",
                    "domain": "market_demand",
                    "confidence_score": 0.92
                },
                "prediction_target": {
                    "primary_metric": "unit_sales",
                    "metric_type": "distribution",
                    "entity_type": "vehicle_model",
                    "aggregation_level": "national"
                },
                "horizon": {
                    "prediction_window": "12 months",
                    "granularity": "monthly"
                },
                "output_format": {
                    "output_types": ["distribution", "point_estimate"],
                    "visualization_requirements": ["line_chart", "confidence_bands"],
                    "export_formats": ["json", "csv"],
                    "confidence_intervals": True
                },
                "evaluation_plan": {
                    "evaluation_metrics": ["brier_score", "calibration_error"],
                    "calibration_requirements": {
                        "required_historical_windows": ["6 months"],
                        "labels_needed": ["actual_sales"],
                        "evaluation_metrics": ["mape"],
                        "min_test_suite_size": 50
                    },
                    "backtest_windows": ["2024-Q3", "2024-Q4"]
                },
                "required_inputs": [
                    {
                        "slot_id": "slot_1",
                        "name": "Consumer Personas",
                        "description": "Target consumer population for EV market",
                        "data_type": "PersonaSet",
                        "required_level": "required",
                        "example_sources": ["ai_generation", "survey_data"]
                    }
                ],
                "provenance": {
                    "call_id": "call_abc123",
                    "model": "openai/gpt-5.2",
                    "provider": "openrouter",
                    "input_tokens": 1500,
                    "output_tokens": 2000,
                    "cost_usd": 0.05,
                    "cache_hit": False,
                    "timestamp": "2026-01-18T10:30:00Z",
                    "fallback_used": False
                },
                "generated_at": "2026-01-18T10:30:05Z",
                "processing_time_ms": 5000
            }
        }


class BlueprintV2CreateRequest(BaseModel):
    """Request to trigger final_blueprint_build job."""
    project_id: UUID = Field(..., description="Project ID to build blueprint for")
    goal_text: str = Field(..., min_length=10, description="User's goal text")
    clarification_answers: Dict[str, Any] = Field(
        default_factory=dict, description="Answers to clarifying questions"
    )
    goal_summary: Optional[str] = Field(None, description="Pre-computed goal summary")
    domain_guess: Optional[DomainGuess] = Field(None, description="Pre-classified domain")
    skip_cache: bool = Field(
        default=True, description="Skip LLM cache (True for staging/dev)"
    )


class BlueprintV2Response(BaseModel):
    """Response containing Blueprint v2 data."""
    id: UUID = Field(..., description="Blueprint ID in database")
    project_id: UUID = Field(..., description="Associated project ID")
    version: int = Field(..., description="Blueprint version number")
    blueprint_v2: BlueprintV2 = Field(..., description="The structured blueprint data")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# Blueprint v2 Edit Validation Schemas (Slice 2B)
# ============================================================================

class CoreType(str, Enum):
    """Core simulation type for Blueprint v2 edits."""
    COLLECTIVE = "collective"
    TARGETED = "targeted"
    HYBRID = "hybrid"


class TemporalMode(str, Enum):
    """Temporal mode for simulations."""
    LIVE = "live"
    BACKTEST = "backtest"


class IsolationLevel(int, Enum):
    """Isolation level for backtest mode."""
    BASIC = 1  # Basic temporal isolation
    STRICT = 2  # Strict for publishable results
    AUDIT_FIRST = 3  # Full audit trail required


class BlueprintV2EditableFields(BaseModel):
    """Editable fields for Blueprint v2 configuration."""
    project_name: str = Field(..., min_length=3, max_length=100)
    tags: List[str] = Field(default_factory=list, max_length=5)
    core_type: CoreType = Field(..., description="Simulation core type")
    temporal_mode: TemporalMode = Field(..., description="Live or backtest mode")
    as_of_date: Optional[str] = Field(None, description="Backtest as-of date (ISO format)")
    as_of_time: Optional[str] = Field(None, description="Backtest as-of time (HH:MM)")
    timezone: Optional[str] = Field(None, description="Timezone for backtest (e.g., 'UTC')")
    isolation_level: Optional[IsolationLevel] = Field(None, description="Backtest isolation level")


class BlueprintV2Recommendations(BaseModel):
    """AI-generated recommendations from Blueprint v2 analysis."""
    project_name: str = Field(..., description="Recommended project name")
    project_name_rationale: Optional[str] = Field(None, description="Why this name")
    tags: List[str] = Field(default_factory=list, description="Recommended tags")
    tags_rationale: Optional[str] = Field(None, description="Why these tags")

    recommended_core: CoreType = Field(..., description="Recommended core type")
    core_rationale: Optional[str] = Field(None, description="Why this core type")
    allowed_cores: List[CoreType] = Field(..., description="Valid cores for this blueprint")

    temporal_mode: TemporalMode = Field(..., description="Recommended temporal mode")
    temporal_rationale: Optional[str] = Field(None, description="Why this mode")
    suggested_cutoff_date: Optional[str] = Field(None, description="Suggested backtest date")
    suggested_isolation_level: Optional[IsolationLevel] = Field(None, description="Suggested isolation")

    required_inputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Required inputs from blueprint analysis"
    )


class BlueprintV2ValidationError(BaseModel):
    """Single validation error or warning."""
    field: str = Field(..., description="Field that has the error")
    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    severity: str = Field(..., pattern="^(error|warning)$", description="Error severity")


class BlueprintV2ValidationRequest(BaseModel):
    """Request to validate Blueprint v2 editable fields."""
    fields: BlueprintV2EditableFields = Field(..., description="Current field values")
    recommendations: BlueprintV2Recommendations = Field(
        ..., description="Blueprint recommendations to validate against"
    )


class BlueprintV2ValidationResult(BaseModel):
    """Result of Blueprint v2 field validation."""
    valid: bool = Field(..., description="Whether all validations passed (no errors)")
    errors: List[BlueprintV2ValidationError] = Field(
        default_factory=list, description="Blocking validation errors"
    )
    warnings: List[BlueprintV2ValidationError] = Field(
        default_factory=list, description="Non-blocking warnings"
    )


class BlueprintV2OverrideMetadata(BaseModel):
    """Metadata for tracking field overrides."""
    field: str = Field(..., description="Field that was overridden")
    original_value: Any = Field(..., description="Original recommended value")
    new_value: Any = Field(..., description="New user-selected value")
    timestamp: str = Field(..., description="ISO timestamp of override")
    reason: Optional[str] = Field(None, description="Optional user-provided reason")
    user_id: Optional[str] = Field(None, description="User who made the override")


class BlueprintV2SaveRequest(BaseModel):
    """Request to save Blueprint v2 edits with validation."""
    project_id: UUID = Field(..., description="Project ID")
    fields: BlueprintV2EditableFields = Field(..., description="Field values to save")
    overrides: List[BlueprintV2OverrideMetadata] = Field(
        default_factory=list, description="Override tracking metadata"
    )
