"""
Source Capability Registry Model
Reference: temporal.md §5 - DataGateway Source Capability Registry

Maintains a registry of all external data sources and their capabilities
for temporal isolation enforcement. Each source declares:
- Timestamp availability (full, partial, none)
- Historical query support
- Required cutoff parameters
- Safe isolation levels

Production requirements per temporal.md §3:
- Each source has an owner, review date, and compliance classification
- Any change to the registry increments policy_version
- Governed artifact with audit trail
"""

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SourceCapability(Base):
    """
    Source capability registration for temporal isolation.

    Each external data source must be registered with its capabilities
    to enable DataGateway to enforce cutoff rules correctly.

    Timestamp Availability:
    - 'full': Source returns full timestamps on all records
    - 'partial': Some records have timestamps, some don't
    - 'none': Source only returns latest data, no timestamps

    Safe Isolation Levels:
    - Level 1 (Basic): Source can be used with warnings
    - Level 2 (Strict): Source must support timestamps (full or partial)
    - Level 3 (Audit-First): Source must support full historical queries
    """
    __tablename__ = "source_capabilities"

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

    # Source identification
    source_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Unique source identifier (e.g., 'census_bureau', 'eurostat')"
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable display name"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Description of the data source"
    )
    endpoint_pattern: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="*",
        comment="Pattern for matching endpoints (e.g., '/data/*')"
    )

    # Timestamp capabilities
    timestamp_availability: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="none",
        comment="'full', 'partial', or 'none'"
    )
    historical_query_support: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether source supports as-of/historical queries"
    )
    timestamp_field: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Name of the timestamp field in responses (e.g., 'timestamp', 'created_at')"
    )

    # Cutoff enforcement
    required_cutoff_params: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="How to pass as_of to this source: {param_name: 'time_end', format: 'iso8601'}"
    )
    safe_isolation_levels: Mapped[List[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        default=[1],
        comment="Which isolation levels allow this source: [1], [1,2], [1,2,3]"
    )
    block_message: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Message to show when source is blocked (e.g., 'Blocked in Strict Backtest: no timestamp support')"
    )

    # Governance (production requirements)
    owner: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="unassigned",
        comment="Responsible team/person for this source"
    )
    review_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Last review date for this source capability"
    )
    compliance_classification: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending_review",
        comment="Compliance status: 'approved', 'restricted', 'pending_review', 'deprecated'"
    )

    # Policy versioning
    policy_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0.0",
        comment="Version increments on any change to this source's capabilities"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this source is currently active"
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

    def __repr__(self) -> str:
        return f"<SourceCapability {self.source_name} ts={self.timestamp_availability} levels={self.safe_isolation_levels}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return dictionary representation."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "source_name": self.source_name,
            "display_name": self.display_name,
            "description": self.description,
            "endpoint_pattern": self.endpoint_pattern,
            "timestamp_availability": self.timestamp_availability,
            "historical_query_support": self.historical_query_support,
            "timestamp_field": self.timestamp_field,
            "required_cutoff_params": self.required_cutoff_params,
            "safe_isolation_levels": self.safe_isolation_levels,
            "block_message": self.block_message,
            "owner": self.owner,
            "review_date": self.review_date.isoformat() if self.review_date else None,
            "compliance_classification": self.compliance_classification,
            "policy_version": self.policy_version,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_safe_for_level(self, isolation_level: int) -> bool:
        """
        Check if this source is safe to use at the given isolation level.

        Args:
            isolation_level: 1, 2, or 3

        Returns:
            True if source can be used at this level
        """
        return isolation_level in (self.safe_isolation_levels or [1])

    def get_badge_text(self) -> str:
        """
        Get the badge text for UI display per temporal.md §3.

        Returns badge text based on capabilities:
        - "Supports historical/as-of queries"
        - "Timestamped but no native as-of filtering"
        - "No timestamps / latest-only (unsafe for backtest)"
        """
        if self.historical_query_support:
            return "Supports historical/as-of queries"
        elif self.timestamp_availability in ("full", "partial"):
            return "Timestamped but no native as-of filtering"
        else:
            return "No timestamps / latest-only (unsafe for backtest)"

    def get_block_reason(self, isolation_level: int) -> Optional[str]:
        """
        Get the reason why this source would be blocked at the given level.

        Returns None if source is safe at this level.
        """
        if self.is_safe_for_level(isolation_level):
            return None

        return self.block_message or f"Blocked in Level {isolation_level} Backtest: {self.get_badge_text()}"


class SourceCapabilityAudit(Base):
    """
    Audit trail for Source Capability Registry changes.

    Any change to a source capability creates an audit record,
    incrementing the policy_version.
    """
    __tablename__ = "source_capability_audits"

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
    source_capability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_capabilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Change details
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="'create', 'update', 'deactivate'"
    )
    previous_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    new_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    changes: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Diff of changes made"
    )
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for the change"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"<SourceCapabilityAudit {self.action} v{self.previous_version}→{self.new_version}>"
