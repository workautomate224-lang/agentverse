"""
LLM Router Models - Centralized LLM management
Reference: GAPS.md GAP-P0-001

Tables:
- LLMProfile: Admin-managed model configurations per feature
- LLMCall: Call logging for cost tracking and debugging
- LLMCache: Deterministic cache for LLM response replay
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class LLMCallStatus(str, Enum):
    """Status of an LLM call."""
    SUCCESS = "success"
    ERROR = "error"
    CACHED = "cached"
    FALLBACK = "fallback"


class LLMProfileKey(str, Enum):
    """
    Standard profile keys for different LLM use cases.
    Admins can create custom keys but these are the defaults.
    """
    # Event Compiler
    EVENT_COMPILER_INTENT = "EVENT_COMPILER_INTENT"
    EVENT_COMPILER_DECOMPOSE = "EVENT_COMPILER_DECOMPOSE"
    EVENT_COMPILER_VARIABLE_MAP = "EVENT_COMPILER_VARIABLE_MAP"

    # Scenario Generation
    SCENARIO_GENERATOR = "SCENARIO_GENERATOR"

    # Explanation
    EXPLANATION_GENERATOR = "EXPLANATION_GENERATOR"

    # Persona
    PERSONA_ENRICHMENT = "PERSONA_ENRICHMENT"
    DEEP_SEARCH = "DEEP_SEARCH"

    # Focus Groups
    FOCUS_GROUP_DIALOGUE = "FOCUS_GROUP_DIALOGUE"

    # General purpose (fallback)
    GENERAL = "GENERAL"


# =============================================================================
# LLM Profile Model
# =============================================================================

class LLMProfile(Base):
    """
    Admin-managed LLM configuration per feature.

    Each profile defines:
    - Which model to use for a specific feature
    - Model parameters (temperature, max_tokens, etc.)
    - Fallback chain for reliability
    - Caching policy
    - Rate limits

    Profiles can be global (tenant_id=NULL) or tenant-specific.
    Tenant-specific profiles override global defaults.
    """
    __tablename__ = "llm_profiles"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,  # NULL = global default
        index=True
    )

    # Profile identification
    profile_key: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Primary model configuration
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    top_p: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    frequency_penalty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    presence_penalty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Cost tracking
    cost_per_1k_input_tokens: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    cost_per_1k_output_tokens: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )

    # Fallback chain
    fallback_models: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String(100)), nullable=True
    )

    # Rate limiting
    rate_limit_rpm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rate_limit_tpm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Caching
    cache_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cache_ttl_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # System prompt template
    system_prompt_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Priority (lower = higher priority)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Audit
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
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
    calls: Mapped[List["LLMCall"]] = relationship("LLMCall", back_populates="profile")

    def __repr__(self) -> str:
        return f"<LLMProfile {self.profile_key} model={self.model}>"

    def to_dict(self) -> Dict[str, Any]:
        """Return profile as dict for API responses."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "profile_key": self.profile_key,
            "label": self.label,
            "description": self.description,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "fallback_models": self.fallback_models or [],
            "cache_enabled": self.cache_enabled,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "cost_per_1k_input_tokens": self.cost_per_1k_input_tokens,
            "cost_per_1k_output_tokens": self.cost_per_1k_output_tokens,
        }


# =============================================================================
# LLM Call Model
# =============================================================================

class LLMCall(Base):
    """
    Log of every LLM call for cost tracking and debugging.

    Each call records:
    - Which profile was used
    - Request/response details
    - Tokens and cost
    - Whether it was cached or fell back
    """
    __tablename__ = "llm_calls"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Profile reference
    profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("llm_profiles.id", ondelete="SET NULL"),
        nullable=True
    )
    profile_key: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    # Context
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project_specs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    node_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Request details
    model_requested: Mapped[str] = mapped_column(String(100), nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    messages_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Response details
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # Cost
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fallback_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Cache
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cache_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # User context
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    profile: Mapped[Optional["LLMProfile"]] = relationship(
        "LLMProfile", back_populates="calls"
    )

    def __repr__(self) -> str:
        return f"<LLMCall {self.id} profile={self.profile_key} status={self.status}>"


# =============================================================================
# LLM Cache Model
# =============================================================================

class LLMCache(Base):
    """
    Deterministic cache for LLM responses.

    Cache key is SHA-256 hash of: profile_key + model + messages + temperature + seed.
    This enables exact replay of LLM calls for reproducibility.
    """
    __tablename__ = "llm_cache"

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Cache key (unique)
    cache_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Request fingerprint
    profile_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    messages_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    seed: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Response content
    response_content: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)

    # Usage stats
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_hit_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # TTL
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<LLMCache {self.cache_key[:16]}... hits={self.hit_count}>"
