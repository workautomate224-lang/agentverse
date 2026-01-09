"""
Simulation Schemas
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Project Schemas
class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    domain: Optional[str] = Field(None, pattern="^(marketing|political|finance|custom)$")
    settings: dict = {}


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    domain: Optional[str] = Field(None, pattern="^(marketing|political|finance|custom)$")
    settings: Optional[dict] = None


class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Scenario Schemas
class QuestionSchema(BaseModel):
    """Schema for scenario questions."""
    id: str
    type: str = Field(..., pattern="^(multiple_choice|yes_no|scale|open_ended)$")
    text: str
    options: Optional[list[str]] = None
    scale_min: Optional[int] = None
    scale_max: Optional[int] = None
    required: bool = True


class DemographicsSchema(BaseModel):
    """Schema for demographics configuration."""
    age_range: Optional[tuple[int, int]] = (18, 65)
    income_brackets: Optional[list[str]] = None
    regions: Optional[list[str]] = None
    education_levels: Optional[list[str]] = None
    custom_attributes: Optional[dict] = None


class ScenarioBase(BaseModel):
    """Base scenario schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    scenario_type: Optional[str] = Field(
        None, pattern="^(survey|election|product_launch|policy|custom)$"
    )
    context: str
    questions: list[dict[str, Any]]
    variables: dict = {}
    population_size: int = Field(default=1000, ge=10, le=1000000)
    demographics: dict
    persona_template: Optional[dict] = None
    model_config_json: dict = {}
    simulation_mode: str = Field(default="batch", pattern="^(batch|streaming|real-time)$")


class ScenarioCreate(ScenarioBase):
    """Schema for creating a scenario."""
    project_id: UUID


class ScenarioUpdate(BaseModel):
    """Schema for updating a scenario."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    scenario_type: Optional[str] = None
    context: Optional[str] = None
    questions: Optional[list[dict[str, Any]]] = None
    variables: Optional[dict] = None
    population_size: Optional[int] = Field(None, ge=10, le=1000000)
    demographics: Optional[dict] = None
    persona_template: Optional[dict] = None
    model_config_json: Optional[dict] = None
    simulation_mode: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|ready|running|completed)$")


class ScenarioResponse(ScenarioBase):
    """Schema for scenario response."""
    id: UUID
    project_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Simulation Run Schemas
class SimulationRunCreate(BaseModel):
    """Schema for creating a simulation run."""
    scenario_id: UUID
    run_config: dict = {}
    model_used: Optional[str] = "openai/gpt-4o-mini"
    agent_count: int = Field(..., ge=10, le=1000000)


class SimulationRunResponse(BaseModel):
    """Schema for simulation run response."""
    id: UUID
    scenario_id: UUID
    user_id: UUID
    run_config: dict
    model_used: Optional[str]
    agent_count: int
    status: str
    progress: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    results_summary: Optional[dict]
    confidence_score: Optional[float]
    tokens_used: int
    cost_usd: float
    created_at: datetime

    class Config:
        from_attributes = True


class SimulationProgress(BaseModel):
    """Schema for simulation progress updates."""
    run_id: UUID
    status: str
    progress: int
    agents_completed: int
    agents_total: int
    current_batch: Optional[int] = None
    total_batches: Optional[int] = None


# Agent Response Schemas
class AgentResponseSchema(BaseModel):
    """Schema for agent response."""
    id: UUID
    run_id: UUID
    agent_index: int
    persona: dict
    question_id: Optional[str]
    response: dict
    reasoning: Optional[str]
    confidence: Optional[float]
    tokens_used: Optional[int]
    response_time_ms: Optional[int]
    model_used: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AgentInterviewRequest(BaseModel):
    """Schema for interviewing agents (virtual focus group)."""
    agent_ids: list[UUID]
    question: str
    context: Optional[str] = None


class AgentInterviewResponse(BaseModel):
    """Schema for agent interview response."""
    agent_id: UUID
    persona: dict
    response: str
    reasoning: Optional[str] = None
