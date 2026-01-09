"""
Focus Group Models
Virtual Focus Group system for LLM-powered interviews with AI personas.

This enables:
- Real-time streaming interview responses
- Follow-up questions with conversation history
- Multi-agent group discussions
- Sentiment/emotion analysis
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class FocusGroupSessionType(str, Enum):
    """Types of focus group sessions."""
    INDIVIDUAL_INTERVIEW = "individual_interview"  # 1-on-1 interview with single agent
    GROUP_DISCUSSION = "group_discussion"          # Multiple agents discussing together
    PANEL_INTERVIEW = "panel_interview"            # Moderator asks questions to panel
    FREE_FORM = "free_form"                        # Open exploration


class FocusGroupSession(Base):
    """
    A focus group session within a product study.
    Tracks the overall interview/discussion session with AI agents.
    """

    __tablename__ = "focus_group_sessions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    product_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_runs.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Session identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    session_type: Mapped[str] = mapped_column(
        String(50), default=FocusGroupSessionType.INDIVIDUAL_INTERVIEW.value, nullable=False
    )

    # Session context
    topic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    objectives: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # ["Understand purchase motivations", "Explore price sensitivity", ...]

    # Selected agents for this session
    agent_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # List of AgentInteraction IDs from the product run

    # Agent persona snapshots (for context continuity)
    agent_contexts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # {
    #   "agent_id_1": {
    #     "persona": {...},
    #     "previous_responses": {...},
    #     "sentiment_baseline": 0.6
    #   }
    # }

    # Discussion guide (optional)
    discussion_guide: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # [
    #   {"topic": "Opening", "questions": ["Tell me about yourself..."]},
    #   {"topic": "Product Experience", "questions": [...]}
    # ]

    # Session configuration
    model_preset: Mapped[str] = mapped_column(String(50), default="balanced", nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)

    # Moderator settings
    moderator_style: Mapped[str] = mapped_column(String(50), default="neutral", nullable=False)
    # neutral, probing, supportive, challenging

    # Session metrics
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Session analysis
    sentiment_trajectory: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # [{"timestamp": "...", "sentiment": 0.7, "agent_id": "..."}]

    key_themes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # ["price_concerns", "quality_expectations", "brand_loyalty"]

    insights_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    # active, paused, completed, archived

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    messages = relationship("FocusGroupMessage", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<FocusGroupSession {self.name} ({self.session_type})>"


class FocusGroupMessage(Base):
    """
    Individual message in a focus group session.
    Captures the full conversation including moderator questions and agent responses.
    """

    __tablename__ = "focus_group_messages"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("focus_group_sessions.id", ondelete="CASCADE"), nullable=False
    )

    # Message identification
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Message source
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    # moderator, agent, system

    agent_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Only set for agent messages - links to AgentInteraction ID

    agent_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Display name for the agent

    # Message content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # For multi-agent responses (group discussion)
    is_group_response: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    responding_agents: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # List of agent IDs who responded in this turn

    # Sentiment analysis
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # -1 to 1 scale

    emotion: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # neutral, happy, frustrated, excited, concerned, etc.

    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Agent's confidence in their response

    # Content analysis
    key_points: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Extracted key points from the message

    themes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Detected themes in this message

    quotes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Notable quotes worth highlighting

    # Token usage
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Response metrics
    response_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    session = relationship("FocusGroupSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<FocusGroupMessage {self.id} ({self.role})>"
