"""
Simulation-related database models
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Project(Base):
    """Project model - container for scenarios."""

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # marketing, political, finance, custom
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="projects")
    scenarios = relationship("Scenario", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project {self.name}>"


class Scenario(Base):
    """Scenario model - simulation configuration."""

    __tablename__ = "scenarios"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scenario_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # survey, election, product_launch, policy

    # Scenario Configuration
    context: Mapped[str] = mapped_column(Text, nullable=False)
    questions: Mapped[list] = mapped_column(JSONB, nullable=False)
    variables: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Audience Configuration
    population_size: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    demographics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    persona_template: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Simulation Settings
    model_config_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    simulation_mode: Mapped[str] = mapped_column(
        String(50), default="batch", nullable=False
    )  # batch, streaming, real-time

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False
    )  # draft, ready, running, completed

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    project = relationship("Project", back_populates="scenarios")
    simulation_runs = relationship(
        "SimulationRun", back_populates="scenario", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Scenario {self.name}>"


class SimulationRun(Base):
    """Simulation run model - individual execution of a scenario."""

    __tablename__ = "simulation_runs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    scenario_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Run Configuration
    run_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    agent_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, running, completed, failed
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Results
    results_summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Costs
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    scenario = relationship("Scenario", back_populates="simulation_runs")
    user = relationship("User", back_populates="simulation_runs")
    agent_responses = relationship(
        "AgentResponse", back_populates="simulation_run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SimulationRun {self.id}>"


class AgentResponse(Base):
    """Agent response model - individual agent decisions."""

    __tablename__ = "agent_responses"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    run_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False
    )
    agent_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Agent Persona
    persona: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Response Data
    question_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Metadata
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    simulation_run = relationship("SimulationRun", back_populates="agent_responses")

    def __repr__(self) -> str:
        return f"<AgentResponse {self.id}>"
