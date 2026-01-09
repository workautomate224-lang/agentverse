"""
RunConfig Model
Reference: project.md §6.5

Immutable configuration for simulation runs.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.node import Run
    from app.models.project_spec import ProjectSpec


class RunConfig(Base):
    """
    Immutable configuration for simulation runs.

    Per project.md §6.5, run configs define:
    - Versions (engine, ruleset, dataset, schema)
    - Seed configuration
    - Horizon (ticks)
    - Scheduler and logging profiles
    """
    __tablename__ = "run_configs"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Version info (per §6.5)
    versions: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Seed configuration
    seed_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    # Simulation parameters
    horizon: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    tick_rate: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Profiles
    scheduler_profile: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    logging_profile: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Scenario patch (variable deltas from parent node)
    scenario_patch: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Limits
    max_execution_time_ms: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )
    max_agents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    runs: Mapped[list["Run"]] = relationship(
        "Run",
        back_populates="run_config",
        foreign_keys="Run.run_config_ref"
    )

    def __repr__(self) -> str:
        return f"<RunConfig {self.id} horizon={self.horizon}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "project_id": str(self.project_id),
            "versions": self.versions,
            "seed_config": self.seed_config,
            "horizon": self.horizon,
            "tick_rate": self.tick_rate,
            "scheduler_profile": self.scheduler_profile,
            "logging_profile": self.logging_profile,
            "scenario_patch": self.scenario_patch,
            "max_execution_time_ms": self.max_execution_time_ms,
            "max_agents": self.max_agents,
            "label": self.label,
            "description": self.description,
            "is_template": self.is_template,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
