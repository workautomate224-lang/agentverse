"""
Organization-related database models for team collaboration
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OrganizationRole(str, PyEnum):
    """Organization membership roles."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class OrganizationTier(str, PyEnum):
    """Organization subscription tiers."""
    FREE = "free"
    TEAM = "team"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class InvitationStatus(str, PyEnum):
    """Invitation status states."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class AuditAction(str, PyEnum):
    """Audit log action types."""
    # Organization actions
    ORG_CREATED = "org_created"
    ORG_UPDATED = "org_updated"
    ORG_DELETED = "org_deleted"

    # Member actions
    MEMBER_INVITED = "member_invited"
    MEMBER_JOINED = "member_joined"
    MEMBER_REMOVED = "member_removed"
    MEMBER_ROLE_CHANGED = "member_role_changed"

    # Project actions
    PROJECT_CREATED = "project_created"
    PROJECT_SHARED = "project_shared"
    PROJECT_UNSHARED = "project_unshared"

    # Simulation actions
    SIMULATION_RUN = "simulation_run"
    SIMULATION_COMPLETED = "simulation_completed"

    # Settings actions
    SETTINGS_UPDATED = "settings_updated"
    API_KEY_GENERATED = "api_key_generated"


class Organization(Base):
    """Organization model - workspace for team collaboration."""

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Owner
    owner_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Subscription & Limits
    tier: Mapped[str] = mapped_column(
        String(50), default=OrganizationTier.FREE.value, nullable=False
    )
    max_members: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_projects: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_simulations_per_month: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Usage tracking
    current_month_simulations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Settings
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    memberships = relationship(
        "OrganizationMembership", back_populates="organization", cascade="all, delete-orphan"
    )
    invitations = relationship(
        "OrganizationInvitation", back_populates="organization", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"


class OrganizationMembership(Base):
    """Organization membership model - user-org relationship with role."""

    __tablename__ = "organization_memberships"

    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='unique_org_user'),
    )

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Role
    role: Mapped[str] = mapped_column(
        String(50), default=OrganizationRole.MEMBER.value, nullable=False
    )

    # Timestamps
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<OrganizationMembership org={self.organization_id} user={self.user_id}>"


class OrganizationInvitation(Base):
    """Organization invitation model - pending invitations."""

    __tablename__ = "organization_invitations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )

    # Invitation details
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), default=OrganizationRole.MEMBER.value, nullable=False
    )

    # Invitation metadata
    invited_by_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default=InvitationStatus.PENDING.value, nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organization = relationship("Organization", back_populates="invitations")
    invited_by = relationship("User")

    def __repr__(self) -> str:
        return f"<OrganizationInvitation {self.email} to {self.organization_id}>"


class AuditLog(Base):
    """Audit log model - activity tracking for organizations."""

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Actor
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Action details
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Additional context
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by {self.user_id}>"
