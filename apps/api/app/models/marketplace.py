"""
Marketplace models for scenario template sharing and discovery.
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    Index,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class TemplateStatus(str, PyEnum):
    """Status of a marketplace template."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class MarketplaceCategory(Base):
    """Category for organizing marketplace templates."""
    __tablename__ = "marketplace_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Icon identifier (e.g., lucide icon name)
    color = Column(String(20), nullable=True)  # Color for UI display
    parent_id = Column(UUID(as_uuid=True), ForeignKey("marketplace_categories.id"), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    template_count = Column(Integer, default=0)  # Denormalized count for performance
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = relationship("MarketplaceCategory", remote_side=[id], backref="children")
    templates = relationship("MarketplaceTemplate", back_populates="category")

    __table_args__ = (
        Index("ix_marketplace_categories_parent_order", "parent_id", "display_order"),
    )


class MarketplaceTemplate(Base):
    """Published scenario template in the marketplace."""
    __tablename__ = "marketplace_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Basic info
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)

    # Categorization
    category_id = Column(UUID(as_uuid=True), ForeignKey("marketplace_categories.id"), nullable=True)
    tags = Column(JSONB, default=list)  # List of tag strings

    # Author/ownership
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)

    # Template content (from scenario)
    scenario_type = Column(String(50), nullable=False)
    context = Column(Text, nullable=False)
    questions = Column(JSONB, nullable=False, default=list)
    variables = Column(JSONB, default=dict)
    demographics = Column(JSONB, default=dict)
    persona_template = Column(JSONB, nullable=True)
    llm_config = Column(JSONB, default=dict)
    recommended_population_size = Column(Integer, default=100)

    # Stimulus materials and methodology
    stimulus_materials = Column(JSONB, nullable=True)
    methodology = Column(JSONB, nullable=True)

    # Preview/sample data
    preview_image_url = Column(String(500), nullable=True)
    sample_results = Column(JSONB, nullable=True)  # Sample results for preview

    # Status and visibility (using String for compatibility with migration)
    status = Column(String(50), default=TemplateStatus.DRAFT.value, nullable=False)
    is_featured = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)  # Verified by platform
    is_premium = Column(Boolean, default=False)  # Premium/paid template
    price_usd = Column(Float, nullable=True)  # Price if premium

    # Metrics (denormalized for performance)
    usage_count = Column(Integer, default=0)
    rating_average = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)

    # Version tracking
    version = Column(String(20), default="1.0.0")
    source_scenario_id = Column(UUID(as_uuid=True), ForeignKey("scenarios.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

    # Relationships
    author = relationship("User", foreign_keys=[author_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    category = relationship("MarketplaceCategory", back_populates="templates")
    source_scenario = relationship("Scenario", foreign_keys=[source_scenario_id])
    reviews = relationship("TemplateReview", back_populates="template", cascade="all, delete-orphan")
    likes = relationship("TemplateLike", back_populates="template", cascade="all, delete-orphan")
    usages = relationship("TemplateUsage", back_populates="template", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_marketplace_templates_category", "category_id"),
        Index("ix_marketplace_templates_author", "author_id"),
        Index("ix_marketplace_templates_status", "status"),
        Index("ix_marketplace_templates_featured", "is_featured", "status"),
        Index("ix_marketplace_templates_rating", "rating_average", "rating_count"),
        Index("ix_marketplace_templates_usage", "usage_count"),
        Index("ix_marketplace_templates_search", "name", "status"),
        CheckConstraint("rating_average >= 0 AND rating_average <= 5", name="check_rating_range"),
        CheckConstraint("price_usd IS NULL OR price_usd >= 0", name="check_price_positive"),
    )


class TemplateReview(Base):
    """User review for a marketplace template."""
    __tablename__ = "template_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("marketplace_templates.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Review content
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=True)

    # Review metadata
    is_verified_purchase = Column(Boolean, default=False)  # User actually used the template
    is_helpful_count = Column(Integer, default=0)
    is_reported = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    template = relationship("MarketplaceTemplate", back_populates="reviews")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("template_id", "user_id", name="uq_template_review_user"),
        Index("ix_template_reviews_template", "template_id"),
        Index("ix_template_reviews_rating", "template_id", "rating"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_review_rating_range"),
    )


class TemplateLike(Base):
    """User like/favorite for a marketplace template."""
    __tablename__ = "template_likes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("marketplace_templates.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    template = relationship("MarketplaceTemplate", back_populates="likes")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("template_id", "user_id", name="uq_template_like_user"),
        Index("ix_template_likes_template", "template_id"),
        Index("ix_template_likes_user", "user_id"),
    )


class TemplateUsage(Base):
    """Track when a user uses a marketplace template."""
    __tablename__ = "template_usages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("marketplace_templates.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # What was created from the template
    created_scenario_id = Column(UUID(as_uuid=True), ForeignKey("scenarios.id"), nullable=True)
    created_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)

    # Usage metadata
    customizations = Column(JSONB, default=dict)  # What the user changed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    template = relationship("MarketplaceTemplate", back_populates="usages")
    user = relationship("User")
    created_scenario = relationship("Scenario", foreign_keys=[created_scenario_id])
    created_product = relationship("Product", foreign_keys=[created_product_id])

    __table_args__ = (
        Index("ix_template_usages_template", "template_id"),
        Index("ix_template_usages_user", "user_id"),
        Index("ix_template_usages_created_at", "created_at"),
    )
