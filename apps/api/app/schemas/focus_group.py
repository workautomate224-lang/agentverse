"""
Focus Group Schemas
Pydantic schemas for Virtual Focus Group system.
"""

from datetime import datetime
from typing import Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


# Session Schemas
class FocusGroupSessionBase(BaseModel):
    """Base focus group session schema."""
    name: str = Field(..., min_length=1, max_length=255)
    session_type: str = Field(
        default="individual_interview",
        pattern="^(individual_interview|group_discussion|panel_interview|free_form)$"
    )
    topic: Optional[str] = None
    objectives: Optional[List[str]] = None
    discussion_guide: Optional[List[dict]] = None
    model_preset: str = Field(default="balanced", pattern="^(fast|balanced|quality|premium)$")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    moderator_style: str = Field(
        default="neutral",
        pattern="^(neutral|probing|supportive|challenging)$"
    )


class FocusGroupSessionCreate(FocusGroupSessionBase):
    """Schema for creating a focus group session."""
    product_id: UUID
    run_id: Optional[UUID] = None
    agent_ids: List[str] = Field(..., min_length=1, description="List of agent interaction IDs")


class FocusGroupSessionUpdate(BaseModel):
    """Schema for updating a focus group session."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    topic: Optional[str] = None
    objectives: Optional[List[str]] = None
    discussion_guide: Optional[List[dict]] = None
    model_preset: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    moderator_style: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|paused|completed|archived)$")
    insights_summary: Optional[str] = None
    key_themes: Optional[List[str]] = None


class AgentContext(BaseModel):
    """Schema for agent context in a session."""
    persona: dict
    previous_responses: Optional[dict] = None
    sentiment_baseline: Optional[float] = None


class FocusGroupSessionResponse(FocusGroupSessionBase):
    """Schema for focus group session response."""
    id: UUID
    product_id: UUID
    run_id: Optional[UUID]
    user_id: UUID
    agent_ids: List[str]
    agent_contexts: dict
    message_count: int
    total_tokens: int
    estimated_cost: float
    sentiment_trajectory: Optional[List[dict]] = None
    key_themes: Optional[List[str]] = None
    insights_summary: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FocusGroupSessionListResponse(BaseModel):
    """Schema for listing focus group sessions."""
    id: UUID
    name: str
    session_type: str
    agent_count: int
    message_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# Message Schemas
class FocusGroupMessageBase(BaseModel):
    """Base focus group message schema."""
    role: str = Field(..., pattern="^(moderator|agent|system)$")
    content: str = Field(..., min_length=1)


class FocusGroupMessageCreate(FocusGroupMessageBase):
    """Schema for creating a focus group message (sending a question)."""
    target_agent_ids: Optional[List[str]] = None  # None means all agents
    is_group_discussion: bool = False


class FocusGroupMessageResponse(FocusGroupMessageBase):
    """Schema for focus group message response."""
    id: UUID
    session_id: UUID
    sequence_number: int
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    is_group_response: bool
    responding_agents: Optional[List[str]] = None
    sentiment_score: Optional[float] = None
    emotion: Optional[str] = None
    confidence: Optional[float] = None
    key_points: Optional[List[str]] = None
    themes: Optional[List[str]] = None
    quotes: Optional[List[str]] = None
    input_tokens: int
    output_tokens: int
    response_time_ms: int
    created_at: datetime

    class Config:
        from_attributes = True


# Interview Request/Response Schemas
class InterviewRequest(BaseModel):
    """Schema for sending an interview question."""
    question: str = Field(..., min_length=1, max_length=2000)
    target_agent_ids: Optional[List[str]] = None  # None means selected agents in session
    context: Optional[str] = None  # Additional context for this question
    follow_up: bool = False  # Whether this is a follow-up to a previous response


class InterviewResponse(BaseModel):
    """Schema for interview response from an agent."""
    agent_id: str
    agent_name: str
    persona_summary: dict
    response: str
    sentiment_score: float
    emotion: str
    confidence: float
    key_points: List[str]
    response_time_ms: int


class StreamingInterviewChunk(BaseModel):
    """Schema for streaming interview response chunk."""
    agent_id: str
    agent_name: str
    chunk: str
    is_final: bool = False
    sentiment_score: Optional[float] = None
    emotion: Optional[str] = None


# Group Discussion Schemas
class GroupDiscussionRequest(BaseModel):
    """Schema for initiating a group discussion."""
    topic: str = Field(..., min_length=1, max_length=1000)
    initial_question: str = Field(..., min_length=1, max_length=2000)
    max_turns: int = Field(default=5, ge=1, le=20)
    agent_ids: Optional[List[str]] = None  # None means all agents in session


class GroupDiscussionTurn(BaseModel):
    """Schema for a single turn in a group discussion."""
    turn_number: int
    agent_id: str
    agent_name: str
    response: str
    responding_to: Optional[str] = None  # Agent ID they're responding to
    agreement_level: Optional[float] = None  # -1 to 1 scale
    sentiment_score: float
    emotion: str


class GroupDiscussionResponse(BaseModel):
    """Schema for group discussion response."""
    topic: str
    turns: List[GroupDiscussionTurn]
    consensus_points: List[str]
    disagreement_points: List[str]
    key_themes: List[str]
    sentiment_summary: dict


# Session Summary Schemas
class SessionSummaryRequest(BaseModel):
    """Schema for requesting a session summary."""
    include_quotes: bool = True
    include_themes: bool = True
    include_sentiment: bool = True


class SessionSummaryResponse(BaseModel):
    """Schema for session summary response."""
    session_id: UUID
    session_name: str
    agent_count: int
    message_count: int
    duration_minutes: Optional[float] = None
    key_insights: List[str]
    key_themes: List[str]
    notable_quotes: List[dict]
    sentiment_trajectory: List[dict]
    recommendations: List[str]
    executive_summary: str


# Agent Selection Schemas
class AvailableAgentResponse(BaseModel):
    """Schema for available agents to interview."""
    agent_id: str
    agent_index: int
    persona_summary: dict
    original_sentiment: Optional[float] = None
    key_themes: Optional[List[str]] = None

    class Config:
        from_attributes = True
