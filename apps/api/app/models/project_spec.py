"""
ProjectSpec Model (Universe Map)
Reference: project.md §6.1

Maps to the spec-compliant project_specs table (migration 0002).
This model enables SQLAlchemy ORM relationships with Node, Run, etc.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
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
    from app.models.node import Node, Run
    from app.models.user import User


class ProjectSpec(Base):
    """
    Project specification - the top-level container for simulations.

    Maps to the spec-compliant project_specs table created by migration 0002.
    """
    __tablename__ = "project_specs"

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
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Core fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    goal_nl: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Prediction configuration
    prediction_core: Mapped[str] = mapped_column(
        String(50), default="collective", nullable=False
    )
    domain_template: Mapped[str] = mapped_column(
        String(50), default="custom", nullable=False
    )
    default_horizon: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    default_output_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Privacy and policy
    privacy_level: Mapped[str] = mapped_column(
        String(20), default="private", nullable=False
    )
    policy_flags: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Baseline status
    has_baseline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    root_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL", use_alter=True),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    owner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[owner_id])
    nodes: Mapped[List["Node"]] = relationship(
        "Node",
        back_populates="project",
        foreign_keys="Node.project_id"
    )
    runs: Mapped[List["Run"]] = relationship(
        "Run",
        back_populates="project",
        foreign_keys="Run.project_id"
    )

    def __repr__(self) -> str:
        return f"<ProjectSpec {self.id} title={self.title}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "title": self.title,
            "goal_nl": self.goal_nl,
            "description": self.description,
            "prediction_core": self.prediction_core,
            "domain_template": self.domain_template,
            "default_horizon": self.default_horizon,
            "default_output_metrics": self.default_output_metrics,
            "privacy_level": self.privacy_level,
            "policy_flags": self.policy_flags,
            "has_baseline": self.has_baseline,
            "root_node_id": str(self.root_node_id) if self.root_node_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
