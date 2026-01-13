"""
Target Plan Schemas - API schemas for user-defined intervention plans.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class TargetPlanSource(str, Enum):
    """Source of the target plan."""
    MANUAL = "manual"
    AI = "ai"


# =============================================================================
# Intervention Step Schema
# =============================================================================

class InterventionStep(BaseModel):
    """A single intervention step in a plan."""
    id: str = Field(..., description="Unique step identifier")
    tick: int = Field(..., ge=0, description="Tick when intervention occurs")
    action_type: str = Field(..., description="Type of action (e.g., 'price_change', 'marketing_campaign')")
    target: str = Field(..., description="Target of the intervention (e.g., agent type, metric)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters")
    description: Optional[str] = Field(None, description="Human-readable description")


class PlanConstraints(BaseModel):
    """Constraints for a target plan."""
    max_budget: Optional[float] = Field(None, description="Maximum budget for interventions")
    max_interventions: Optional[int] = Field(None, description="Maximum number of interventions")
    time_constraints: Optional[Dict[str, Any]] = Field(None, description="Timing constraints")
    custom: Optional[Dict[str, Any]] = Field(None, description="Custom constraints")


# =============================================================================
# Create/Update Schemas
# =============================================================================

class TargetPlanCreate(BaseModel):
    """Schema for creating a new target plan."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    node_id: Optional[UUID] = Field(None, description="Starting node for this plan")
    target_metric: str = Field(..., min_length=1, max_length=100)
    target_value: float
    horizon_ticks: int = Field(default=100, ge=1, le=10000)
    constraints_json: Optional[PlanConstraints] = None
    steps_json: Optional[List[InterventionStep]] = None
    source: TargetPlanSource = TargetPlanSource.MANUAL
    ai_prompt: Optional[str] = None


class TargetPlanUpdate(BaseModel):
    """Schema for updating a target plan."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    node_id: Optional[UUID] = None
    target_metric: Optional[str] = Field(None, min_length=1, max_length=100)
    target_value: Optional[float] = None
    horizon_ticks: Optional[int] = Field(None, ge=1, le=10000)
    constraints_json: Optional[PlanConstraints] = None
    steps_json: Optional[List[InterventionStep]] = None


# =============================================================================
# Response Schemas
# =============================================================================

class TargetPlanResponse(BaseModel):
    """Response schema for a target plan."""
    id: UUID
    tenant_id: UUID
    project_id: UUID
    node_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    target_metric: str
    target_value: float
    horizon_ticks: int
    constraints_json: Optional[Dict[str, Any]] = None
    steps_json: Optional[List[Dict[str, Any]]] = None
    source: str
    ai_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TargetPlanListResponse(BaseModel):
    """Response schema for listing target plans."""
    plans: List[TargetPlanResponse]
    total: int


# =============================================================================
# AI Generation Schemas
# =============================================================================

class AIGeneratePlanRequest(BaseModel):
    """Request schema for AI-generated plan."""
    prompt: str = Field(..., min_length=10, max_length=2000, description="What-if question or goal description")
    node_id: Optional[UUID] = Field(None, description="Starting node context")
    target_metric: Optional[str] = Field(None, description="Suggested target metric")
    horizon_ticks: int = Field(default=100, ge=1, le=10000)
    constraints: Optional[PlanConstraints] = None


class AIGeneratePlanResponse(BaseModel):
    """Response schema for AI-generated plan."""
    plan: TargetPlanResponse
    reasoning: str = Field(..., description="AI reasoning for the plan")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")


# =============================================================================
# Branch Creation Schema
# =============================================================================

class CreateBranchFromPlanRequest(BaseModel):
    """Request to create a new branch from a target plan."""
    plan_id: UUID
    branch_name: Optional[str] = Field(None, description="Optional name for the new branch node")


class CreateBranchFromPlanResponse(BaseModel):
    """Response after creating a branch from a plan."""
    node_id: UUID = Field(..., description="ID of the newly created branch node")
    plan_id: UUID
    message: str
