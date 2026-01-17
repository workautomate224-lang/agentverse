"""
ProjectSpec Model (Universe Map)
Reference: project.md §6.1, temporal.md §4

Maps to the spec-compliant project_specs table (migration 0002).
This model enables SQLAlchemy ORM relationships with Node, Run, etc.

Temporal Knowledge Isolation fields added per temporal.md §4:
- mode: 'live' or 'backtest'
- as_of_datetime: cutoff timestamp for backtest mode
- timezone: IANA timezone for cutoff evaluation
- isolation_level: 1 (basic), 2 (strict), 3 (audit-first)
- allowed_sources: JSON array of source identifiers
- policy_version: version of source capability registry
- temporal_lock_status: 'locked' (default) or 'unlocked'
- temporal_lock_history: JSONB audit trail of lock changes
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

    # ==========================================================================
    # Temporal Knowledge Isolation (temporal.md §4)
    # ==========================================================================
    # Mode: 'live' (default) or 'backtest'
    temporal_mode: Mapped[str] = mapped_column(
        String(20), default="live", nullable=False
    )
    # As-of datetime for backtest mode (cutoff timestamp)
    as_of_datetime: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # IANA timezone for cutoff evaluation
    temporal_timezone: Mapped[str] = mapped_column(
        String(50), default="Asia/Kuala_Lumpur", nullable=False
    )
    # Isolation level: 1 (basic), 2 (strict, default for backtest), 3 (audit-first)
    isolation_level: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    # Allowed sources for this project (JSON array of source identifiers)
    allowed_sources: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    # Policy version (from Source Capability Registry)
    temporal_policy_version: Mapped[str] = mapped_column(
        String(50), default="1.0.0", nullable=False
    )
    # Lock status: 'locked' (default) or 'unlocked'
    temporal_lock_status: Mapped[str] = mapped_column(
        String(20), default="locked", nullable=False
    )
    # Audit trail for temporal lock changes (who/when/why)
    temporal_lock_history: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )

    # Baseline status
    has_baseline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    root_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL", use_alter=True),
        nullable=True
    )

    # ==========================================================================
    # Slice 1C: Draft / Resume (Project-level Persistence)
    # ==========================================================================
    # Project status: DRAFT (wizard in progress), ACTIVE (wizard completed), ARCHIVED
    status: Mapped[str] = mapped_column(
        String(20), default="ACTIVE", nullable=False
    )
    # Wizard state JSONB for persisting wizard progress (step, goal_text, answers, etc.)
    wizard_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    # Optimistic concurrency version for wizard_state updates
    wizard_state_version: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
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
            # Temporal Knowledge Isolation fields
            "temporal_mode": self.temporal_mode,
            "as_of_datetime": self.as_of_datetime.isoformat() if self.as_of_datetime else None,
            "temporal_timezone": self.temporal_timezone,
            "isolation_level": self.isolation_level,
            "allowed_sources": self.allowed_sources,
            "temporal_policy_version": self.temporal_policy_version,
            "temporal_lock_status": self.temporal_lock_status,
            "temporal_lock_history": self.temporal_lock_history,
            # Baseline and node fields
            "has_baseline": self.has_baseline,
            "root_node_id": str(self.root_node_id) if self.root_node_id else None,
            # Slice 1C: Draft / Resume fields
            "status": self.status,
            "wizard_state": self.wizard_state,
            "wizard_state_version": self.wizard_state_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_temporal_context(self) -> Dict[str, Any]:
        """Return temporal context for this project (used by DataGateway)."""
        return {
            "mode": self.temporal_mode,
            "as_of_datetime": self.as_of_datetime,
            "timezone": self.temporal_timezone,
            "isolation_level": self.isolation_level,
            "allowed_sources": self.allowed_sources or [],
            "policy_version": self.temporal_policy_version,
            "lock_status": self.temporal_lock_status,
        }

    def is_backtest(self) -> bool:
        """Check if this project is in backtest mode."""
        return self.temporal_mode == "backtest"

    def is_temporal_locked(self) -> bool:
        """Check if temporal context is locked."""
        return self.temporal_lock_status == "locked"
