"""
LLM Router Pydantic Schemas
Reference: GAPS.md GAP-P0-001
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# LLM Profile Schemas
# =============================================================================

class LLMProfileBase(BaseModel):
    """Base schema for LLM profile."""
    profile_key: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    model: str = Field(..., min_length=1, max_length=100)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1000, ge=1, le=100000)
    top_p: Optional[float] = Field(default=None, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(default=None, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(default=None, ge=-2, le=2)
    cost_per_1k_input_tokens: float = Field(default=0.0, ge=0)
    cost_per_1k_output_tokens: float = Field(default=0.0, ge=0)
    fallback_models: Optional[List[str]] = None
    rate_limit_rpm: Optional[int] = Field(default=None, ge=1)
    rate_limit_tpm: Optional[int] = Field(default=None, ge=1)
    cache_enabled: bool = True
    cache_ttl_seconds: Optional[int] = Field(default=None, ge=1)
    system_prompt_template: Optional[str] = None
    priority: int = Field(default=100, ge=0)


class LLMProfileCreate(LLMProfileBase):
    """Schema for creating an LLM profile."""
    tenant_id: Optional[str] = None  # NULL = global default
    is_default: bool = False


class LLMProfileUpdate(BaseModel):
    """Schema for updating an LLM profile."""
    label: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    model: Optional[str] = Field(default=None, min_length=1, max_length=100)
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=100000)
    top_p: Optional[float] = Field(default=None, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(default=None, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(default=None, ge=-2, le=2)
    cost_per_1k_input_tokens: Optional[float] = Field(default=None, ge=0)
    cost_per_1k_output_tokens: Optional[float] = Field(default=None, ge=0)
    fallback_models: Optional[List[str]] = None
    rate_limit_rpm: Optional[int] = Field(default=None, ge=1)
    rate_limit_tpm: Optional[int] = Field(default=None, ge=1)
    cache_enabled: Optional[bool] = None
    cache_ttl_seconds: Optional[int] = Field(default=None, ge=1)
    system_prompt_template: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class LLMProfileResponse(LLMProfileBase):
    """Schema for LLM profile response."""
    id: str
    tenant_id: Optional[str] = None
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[str] = None

    class Config:
        from_attributes = True


class LLMProfileListResponse(BaseModel):
    """Schema for listing LLM profiles."""
    profiles: List[LLMProfileResponse]
    total: int


# =============================================================================
# LLM Call Schemas
# =============================================================================

class LLMCallResponse(BaseModel):
    """Schema for LLM call log entry."""
    id: str
    tenant_id: Optional[str] = None
    profile_key: str
    project_id: Optional[str] = None
    run_id: Optional[str] = None
    model_requested: str
    model_used: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    response_time_ms: int
    cost_usd: float
    status: str
    cache_hit: bool
    fallback_attempts: int
    created_at: datetime

    class Config:
        from_attributes = True


class LLMCallListResponse(BaseModel):
    """Schema for listing LLM calls."""
    calls: List[LLMCallResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Cost Summary Schemas
# =============================================================================

class LLMCostSummary(BaseModel):
    """Schema for LLM cost summary."""
    total_calls: int
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_response_time_ms: float
    cache_hits: int
    cache_hit_rate: float


class LLMCostByProfile(BaseModel):
    """Schema for cost breakdown by profile."""
    profile_key: str
    call_count: int
    total_cost_usd: float
    total_tokens: int


class LLMCostReport(BaseModel):
    """Schema for comprehensive cost report."""
    summary: LLMCostSummary
    by_profile: List[LLMCostByProfile]
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


# =============================================================================
# Available Models Schema
# =============================================================================

class AvailableModel(BaseModel):
    """Schema for an available model."""
    model: str
    provider: str
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    max_context_length: int
    description: str


class AvailableModelsResponse(BaseModel):
    """Schema for listing available models."""
    models: List[AvailableModel]


# =============================================================================
# Standard Profile Keys
# =============================================================================

STANDARD_PROFILE_KEYS = [
    {
        "key": "EVENT_COMPILER_INTENT",
        "label": "Event Compiler - Intent Analysis",
        "description": "Classifies user prompts as event/variable/query/comparison/explanation",
        "recommended_model": "openai/gpt-4o-mini",
    },
    {
        "key": "EVENT_COMPILER_DECOMPOSE",
        "label": "Event Compiler - Decomposition",
        "description": "Breaks prompts into granular sub-effects",
        "recommended_model": "openai/gpt-4o-mini",
    },
    {
        "key": "EVENT_COMPILER_VARIABLE_MAP",
        "label": "Event Compiler - Variable Mapping",
        "description": "Maps sub-effects to concrete variable deltas",
        "recommended_model": "openai/gpt-4o-mini",
    },
    {
        "key": "SCENARIO_GENERATOR",
        "label": "Scenario Generator",
        "description": "Generates candidate scenarios from variable deltas",
        "recommended_model": "anthropic/claude-3-haiku-20240307",
    },
    {
        "key": "EXPLANATION_GENERATOR",
        "label": "Explanation Generator",
        "description": "Creates causal chain summaries for simulation outcomes",
        "recommended_model": "anthropic/claude-3-haiku-20240307",
    },
    {
        "key": "PERSONA_ENRICHMENT",
        "label": "Persona Enrichment",
        "description": "Enriches persona attributes from demographics",
        "recommended_model": "openai/gpt-4o-mini",
    },
    {
        "key": "DEEP_SEARCH",
        "label": "Deep Search / AI Research",
        "description": "AI-powered persona research and validation",
        "recommended_model": "anthropic/claude-3-haiku-20240307",
    },
    {
        "key": "FOCUS_GROUP_DIALOGUE",
        "label": "Focus Group Dialogue",
        "description": "Simulates focus group conversations",
        "recommended_model": "anthropic/claude-3-5-sonnet-20241022",
    },
]


class ProfileKeyInfo(BaseModel):
    """Schema for profile key information."""
    key: str
    label: str
    description: str
    recommended_model: str


class ProfileKeysResponse(BaseModel):
    """Schema for listing standard profile keys."""
    keys: List[ProfileKeyInfo]
