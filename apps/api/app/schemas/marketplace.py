"""
Pydantic schemas for marketplace functionality.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator


# ========== Category Schemas ==========

class CategoryBase(BaseModel):
    """Base category fields."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[UUID] = None
    display_order: int = 0


class CategoryCreate(CategoryBase):
    """Schema for creating a category."""
    pass


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[UUID] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    """Category response schema."""
    id: UUID
    is_active: bool
    template_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryWithChildren(CategoryResponse):
    """Category with nested children."""
    children: List["CategoryWithChildren"] = []

    class Config:
        from_attributes = True


# ========== Template Schemas ==========

class TemplateBase(BaseModel):
    """Base template fields."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    category_id: Optional[UUID] = None
    tags: List[str] = Field(default_factory=list)


class TemplateCreate(TemplateBase):
    """Schema for creating/publishing a template."""
    # Content
    scenario_type: str = Field(..., min_length=1, max_length=50)
    context: str = Field(..., min_length=1)
    questions: List[Dict[str, Any]] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict)
    demographics: Dict[str, Any] = Field(default_factory=dict)
    persona_template: Optional[Dict[str, Any]] = None
    llm_config: Dict[str, Any] = Field(default_factory=dict)
    recommended_population_size: int = Field(100, ge=1, le=10000)

    # Optional extras
    stimulus_materials: Optional[Dict[str, Any]] = None
    methodology: Optional[Dict[str, Any]] = None
    preview_image_url: Optional[str] = None
    sample_results: Optional[Dict[str, Any]] = None

    # Publishing options
    organization_id: Optional[UUID] = None
    source_scenario_id: Optional[UUID] = None
    is_premium: bool = False
    price_usd: Optional[float] = Field(None, ge=0)


class TemplateCreateFromScenario(BaseModel):
    """Schema for publishing a template from an existing scenario."""
    scenario_id: UUID
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    category_id: Optional[UUID] = None
    tags: List[str] = Field(default_factory=list)
    organization_id: Optional[UUID] = None
    is_premium: bool = False
    price_usd: Optional[float] = Field(None, ge=0)


class TemplateUpdate(BaseModel):
    """Schema for updating a template."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    context: Optional[str] = None
    questions: Optional[List[Dict[str, Any]]] = None
    variables: Optional[Dict[str, Any]] = None
    demographics: Optional[Dict[str, Any]] = None
    persona_template: Optional[Dict[str, Any]] = None
    llm_config: Optional[Dict[str, Any]] = None
    recommended_population_size: Optional[int] = Field(None, ge=1, le=10000)
    stimulus_materials: Optional[Dict[str, Any]] = None
    methodology: Optional[Dict[str, Any]] = None
    preview_image_url: Optional[str] = None
    sample_results: Optional[Dict[str, Any]] = None
    is_premium: Optional[bool] = None
    price_usd: Optional[float] = Field(None, ge=0)


class TemplateAuthor(BaseModel):
    """Simplified author info for template responses."""
    id: UUID
    full_name: Optional[str] = None
    email: str

    class Config:
        from_attributes = True


class TemplateListItem(BaseModel):
    """Template item for list views."""
    id: UUID
    name: str
    slug: str
    short_description: Optional[str] = None
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    author_id: UUID
    author_name: Optional[str] = None
    scenario_type: str
    tags: List[str]
    status: str
    is_featured: bool
    is_verified: bool
    is_premium: bool
    price_usd: Optional[float] = None
    usage_count: int
    rating_average: float
    rating_count: int
    like_count: int
    preview_image_url: Optional[str] = None
    created_at: datetime
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TemplateDetail(TemplateListItem):
    """Full template detail response."""
    description: Optional[str] = None
    organization_id: Optional[UUID] = None
    organization_name: Optional[str] = None
    context: str
    questions: List[Dict[str, Any]]
    variables: Dict[str, Any]
    demographics: Dict[str, Any]
    persona_template: Optional[Dict[str, Any]] = None
    llm_config: Dict[str, Any]
    recommended_population_size: int
    stimulus_materials: Optional[Dict[str, Any]] = None
    methodology: Optional[Dict[str, Any]] = None
    sample_results: Optional[Dict[str, Any]] = None
    version: str
    view_count: int
    updated_at: datetime
    is_liked_by_user: bool = False
    user_review: Optional["ReviewResponse"] = None

    class Config:
        from_attributes = True


# ========== Review Schemas ==========

class ReviewCreate(BaseModel):
    """Schema for creating a review."""
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = None


class ReviewUpdate(BaseModel):
    """Schema for updating a review."""
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = None


class ReviewResponse(BaseModel):
    """Review response schema."""
    id: UUID
    template_id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    rating: int
    title: Optional[str] = None
    content: Optional[str] = None
    is_verified_purchase: bool
    is_helpful_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    """Paginated review list response."""
    items: List[ReviewResponse]
    total: int
    page: int
    page_size: int
    average_rating: float
    rating_distribution: Dict[int, int]  # {1: count, 2: count, ...}


# ========== Usage Schemas ==========

class UseTemplateRequest(BaseModel):
    """Schema for using a template to create a scenario/product."""
    target_project_id: Optional[UUID] = None
    create_type: str = Field("scenario", pattern="^(scenario|product)$")
    customizations: Dict[str, Any] = Field(default_factory=dict)
    name: Optional[str] = None  # Custom name for the created item


class UseTemplateResponse(BaseModel):
    """Response after using a template."""
    usage_id: UUID
    template_id: UUID
    created_type: str
    created_id: UUID
    created_name: str
    message: str


# ========== Search & Filter Schemas ==========

class TemplateSearchParams(BaseModel):
    """Search and filter parameters for templates."""
    query: Optional[str] = None
    category_id: Optional[UUID] = None
    category_slug: Optional[str] = None
    scenario_type: Optional[str] = None
    tags: Optional[List[str]] = None
    author_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    is_featured: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_premium: Optional[bool] = None
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    min_usage: Optional[int] = Field(None, ge=0)
    sort_by: str = Field("popular", pattern="^(popular|newest|rating|usage|name)$")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class TemplateListResponse(BaseModel):
    """Paginated template list response."""
    items: List[TemplateListItem]
    total: int
    page: int
    page_size: int
    categories: Optional[List[CategoryResponse]] = None  # For filter sidebar


class FeaturedTemplatesResponse(BaseModel):
    """Featured templates for homepage."""
    featured: List[TemplateListItem]
    trending: List[TemplateListItem]
    newest: List[TemplateListItem]
    by_category: Dict[str, List[TemplateListItem]]


# ========== Stats Schemas ==========

class MarketplaceStats(BaseModel):
    """Overall marketplace statistics."""
    total_templates: int
    total_categories: int
    total_usages: int
    total_reviews: int
    average_rating: float
    top_categories: List[Dict[str, Any]]
    top_authors: List[Dict[str, Any]]


class AuthorStats(BaseModel):
    """Author's marketplace statistics."""
    total_templates: int
    total_usages: int
    total_reviews: int
    average_rating: float
    total_likes: int
    templates: List[TemplateListItem]


# Allow forward references
CategoryWithChildren.model_rebuild()
TemplateDetail.model_rebuild()
