"""
TargetPlan Model - User-defined intervention plans for Target Mode.

This is a simpler model for user-created plans with intervention steps,
separate from the PlanningSpec model used for simulation-based evaluation.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.node import Node
    from app.models.project_spec import ProjectSpec


class TargetPlanSource(str, Enum):
    """Source of the target plan."""
    MANUAL = "manual"  # User-created
    AI = "ai"  # AI-generated


class TargetPlan(Base):
    """
    User-defined intervention plan for Target Mode.

    Stores target metric, value, constraints, and intervention steps.
    Can be linked to a specific node as the starting point.
    """
    __tablename__ = "target_plans"

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
    node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional starting node for this plan"
    )

    # Plan definition
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Target specification
    target_metric: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Metric to optimize (e.g., 'market_share', 'revenue')"
    )
    target_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Target value to achieve"
    )
    horizon_ticks: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
        comment="Time horizon in simulation ticks"
    )

    # Constraints and steps (JSONB for flexibility)
    constraints_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Constraints for the plan (budget, timing, etc.)"
    )
    steps_json: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Intervention steps array"
    )

    # Metadata
    source: Mapped[str] = mapped_column(
        String(20),
        default=TargetPlanSource.MANUAL.value,
        nullable=False,
        comment="How the plan was created: manual or ai"
    )
    ai_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Original prompt if AI-generated"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    project: Mapped["ProjectSpec"] = relationship(
        "ProjectSpec",
        foreign_keys=[project_id]
    )
    node: Mapped[Optional["Node"]] = relationship(
        "Node",
        foreign_keys=[node_id]
    )

    def __repr__(self) -> str:
        return f"<TargetPlan {self.id} name={self.name}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "project_id": str(self.project_id),
            "node_id": str(self.node_id) if self.node_id else None,
            "name": self.name,
            "description": self.description,
            "target_metric": self.target_metric,
            "target_value": self.target_value,
            "horizon_ticks": self.horizon_ticks,
            "constraints_json": self.constraints_json,
            "steps_json": self.steps_json,
            "source": self.source,
            "ai_prompt": self.ai_prompt,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
