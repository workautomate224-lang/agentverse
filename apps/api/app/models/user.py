"""
User database models
"""

from datetime import datetime
from typing import Optional
from uuid import UUID as UUIDType, uuid4

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    """User model for authentication and profile."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Role and tier
    role: Mapped[str] = mapped_column(
        String(50), default="user", nullable=False
    )  # user, admin, enterprise
    tier: Mapped[str] = mapped_column(
        String(50), default="free", nullable=False
    )  # free, pro, team, enterprise

    # API access
    api_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Settings
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    projects = relationship("Project", back_populates="user", lazy="dynamic")
    simulation_runs = relationship("SimulationRun", back_populates="user", lazy="dynamic")

    @property
    def tenant_id(self) -> UUIDType:
        """
        Return tenant_id for multi-tenant operations.

        MVP: For the MVP, user_id == tenant_id.
        This allows code to consistently use current_user.tenant_id
        instead of current_user.id for tenant scoping.

        TODO: In proper multi-tenancy, this would return the user's
        organization/team tenant_id instead of user's own ID.
        """
        return self.id

    def __repr__(self) -> str:
        return f"<User {self.email}>"
