"""
Marketplace API Endpoints

Browse, publish, and use scenario templates in the marketplace.
"""

import re
import secrets
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.simulation import Scenario
from app.models.marketplace import (
    MarketplaceCategory,
    MarketplaceTemplate,
    TemplateReview,
    TemplateLike,
    TemplateUsage,
    TemplateStatus,
)
from app.schemas.marketplace import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithChildren,
    TemplateCreate,
    TemplateCreateFromScenario,
    TemplateUpdate,
    TemplateListItem,
    TemplateDetail,
    TemplateSearchParams,
    TemplateListResponse,
    FeaturedTemplatesResponse,
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    ReviewListResponse,
    UseTemplateRequest,
    UseTemplateResponse,
    MarketplaceStats,
    AuthorStats,
)


router = APIRouter()


def generate_slug(name: str, suffix: Optional[str] = None) -> str:
    """Generate a URL-friendly slug from name."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    if suffix:
        slug = f"{slug}-{suffix}"
    return slug[:200]


async def ensure_unique_slug(db: AsyncSession, base_slug: str, exclude_id: Optional[UUID] = None) -> str:
    """Ensure slug is unique by appending random suffix if needed."""
    slug = base_slug
    query = select(MarketplaceTemplate).where(MarketplaceTemplate.slug == slug)
    if exclude_id:
        query = query.where(MarketplaceTemplate.id != exclude_id)

    result = await db.execute(query)
    if result.scalar_one_or_none():
        slug = f"{base_slug[:190]}-{secrets.token_hex(4)}"
    return slug


# ============================================================
# Category Endpoints
# ============================================================

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> List[CategoryResponse]:
    """
    List all marketplace categories.
    """
    query = select(MarketplaceCategory).order_by(
        MarketplaceCategory.display_order,
        MarketplaceCategory.name
    )

    if not include_inactive:
        query = query.where(MarketplaceCategory.is_active == True)

    result = await db.execute(query)
    categories = result.scalars().all()

    return [
        CategoryResponse(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            icon=cat.icon,
            color=cat.color,
            parent_id=cat.parent_id,
            display_order=cat.display_order,
            is_active=cat.is_active,
            template_count=cat.template_count,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
        )
        for cat in categories
    ]


@router.get("/categories/tree", response_model=List[CategoryWithChildren])
async def get_category_tree(
    db: AsyncSession = Depends(get_db),
) -> List[CategoryWithChildren]:
    """
    Get categories as a nested tree structure.
    """
    query = select(MarketplaceCategory).where(
        MarketplaceCategory.is_active == True
    ).order_by(
        MarketplaceCategory.display_order,
        MarketplaceCategory.name
    )

    result = await db.execute(query)
    all_categories = result.scalars().all()

    # Build tree structure
    cat_map = {}
    root_categories = []

    for cat in all_categories:
        cat_response = CategoryWithChildren(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            icon=cat.icon,
            color=cat.color,
            parent_id=cat.parent_id,
            display_order=cat.display_order,
            is_active=cat.is_active,
            template_count=cat.template_count,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
            children=[],
        )
        cat_map[cat.id] = cat_response

        if cat.parent_id is None:
            root_categories.append(cat_response)

    # Assign children
    for cat in all_categories:
        if cat.parent_id and cat.parent_id in cat_map:
            cat_map[cat.parent_id].children.append(cat_map[cat.id])

    return root_categories


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_in: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    """
    Create a new marketplace category (admin only).
    """
    # TODO: Check admin permission

    # Check slug uniqueness
    existing = await db.execute(
        select(MarketplaceCategory).where(MarketplaceCategory.slug == category_in.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A category with this slug already exists",
        )

    # Check parent exists if provided
    if category_in.parent_id:
        parent = await db.execute(
            select(MarketplaceCategory).where(MarketplaceCategory.id == category_in.parent_id)
        )
        if not parent.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category not found",
            )

    category = MarketplaceCategory(
        name=category_in.name,
        slug=category_in.slug,
        description=category_in.description,
        icon=category_in.icon,
        color=category_in.color,
        parent_id=category_in.parent_id,
        display_order=category_in.display_order,
    )

    db.add(category)
    await db.flush()
    await db.refresh(category)

    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        icon=category.icon,
        color=category.color,
        parent_id=category.parent_id,
        display_order=category.display_order,
        is_active=category.is_active,
        template_count=0,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    category_update: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    """
    Update a marketplace category (admin only).
    """
    # TODO: Check admin permission

    result = await db.execute(
        select(MarketplaceCategory).where(MarketplaceCategory.id == category_id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    update_data = category_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.flush()
    await db.refresh(category)

    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        icon=category.icon,
        color=category.color,
        parent_id=category.parent_id,
        display_order=category.display_order,
        is_active=category.is_active,
        template_count=category.template_count,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


# ============================================================
# Template Browse Endpoints
# ============================================================

@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    query: Optional[str] = Query(None, description="Search query"),
    category_id: Optional[UUID] = Query(None),
    category_slug: Optional[str] = Query(None),
    scenario_type: Optional[str] = Query(None),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    author_id: Optional[UUID] = Query(None),
    organization_id: Optional[UUID] = Query(None),
    is_featured: Optional[bool] = Query(None),
    is_verified: Optional[bool] = Query(None),
    is_premium: Optional[bool] = Query(None),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    min_usage: Optional[int] = Query(None, ge=0),
    sort_by: str = Query("popular", pattern="^(popular|newest|rating|usage|name)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> TemplateListResponse:
    """
    Browse marketplace templates with filtering and sorting.
    """
    # Base query for published templates
    base_query = select(MarketplaceTemplate).where(
        MarketplaceTemplate.status == TemplateStatus.PUBLISHED.value
    )

    # Apply filters
    if query:
        search_pattern = f"%{query}%"
        base_query = base_query.where(
            or_(
                MarketplaceTemplate.name.ilike(search_pattern),
                MarketplaceTemplate.description.ilike(search_pattern),
                MarketplaceTemplate.short_description.ilike(search_pattern),
            )
        )

    if category_id:
        base_query = base_query.where(MarketplaceTemplate.category_id == category_id)
    elif category_slug:
        cat_result = await db.execute(
            select(MarketplaceCategory).where(MarketplaceCategory.slug == category_slug)
        )
        cat = cat_result.scalar_one_or_none()
        if cat:
            base_query = base_query.where(MarketplaceTemplate.category_id == cat.id)

    if scenario_type:
        base_query = base_query.where(MarketplaceTemplate.scenario_type == scenario_type)

    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        for tag in tag_list:
            base_query = base_query.where(MarketplaceTemplate.tags.contains([tag]))

    if author_id:
        base_query = base_query.where(MarketplaceTemplate.author_id == author_id)

    if organization_id:
        base_query = base_query.where(MarketplaceTemplate.organization_id == organization_id)

    if is_featured is not None:
        base_query = base_query.where(MarketplaceTemplate.is_featured == is_featured)

    if is_verified is not None:
        base_query = base_query.where(MarketplaceTemplate.is_verified == is_verified)

    if is_premium is not None:
        base_query = base_query.where(MarketplaceTemplate.is_premium == is_premium)

    if min_rating is not None:
        base_query = base_query.where(MarketplaceTemplate.rating_average >= min_rating)

    if min_usage is not None:
        base_query = base_query.where(MarketplaceTemplate.usage_count >= min_usage)

    # Count total
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply sorting
    if sort_by == "popular":
        base_query = base_query.order_by(
            desc(MarketplaceTemplate.usage_count),
            desc(MarketplaceTemplate.like_count)
        )
    elif sort_by == "newest":
        base_query = base_query.order_by(desc(MarketplaceTemplate.published_at))
    elif sort_by == "rating":
        base_query = base_query.order_by(
            desc(MarketplaceTemplate.rating_average),
            desc(MarketplaceTemplate.rating_count)
        )
    elif sort_by == "usage":
        base_query = base_query.order_by(desc(MarketplaceTemplate.usage_count))
    elif sort_by == "name":
        base_query = base_query.order_by(asc(MarketplaceTemplate.name))

    # Apply pagination
    offset = (page - 1) * page_size
    base_query = base_query.offset(offset).limit(page_size)

    # Execute query with eager loading
    base_query = base_query.options(
        selectinload(MarketplaceTemplate.author),
        selectinload(MarketplaceTemplate.category),
    )

    result = await db.execute(base_query)
    templates = result.scalars().all()

    items = [
        TemplateListItem(
            id=t.id,
            name=t.name,
            slug=t.slug,
            short_description=t.short_description,
            category_id=t.category_id,
            category_name=t.category.name if t.category else None,
            author_id=t.author_id,
            author_name=t.author.full_name if t.author else None,
            scenario_type=t.scenario_type,
            tags=t.tags or [],
            status=t.status,
            is_featured=t.is_featured,
            is_verified=t.is_verified,
            is_premium=t.is_premium,
            price_usd=t.price_usd,
            usage_count=t.usage_count,
            rating_average=t.rating_average,
            rating_count=t.rating_count,
            like_count=t.like_count,
            preview_image_url=t.preview_image_url,
            created_at=t.created_at,
            published_at=t.published_at,
        )
        for t in templates
    ]

    return TemplateListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/templates/featured", response_model=FeaturedTemplatesResponse)
async def get_featured_templates(
    db: AsyncSession = Depends(get_db),
) -> FeaturedTemplatesResponse:
    """
    Get featured, trending, and newest templates for homepage.
    """
    base_filter = MarketplaceTemplate.status == TemplateStatus.PUBLISHED.value

    # Featured templates
    featured_result = await db.execute(
        select(MarketplaceTemplate)
        .options(selectinload(MarketplaceTemplate.author), selectinload(MarketplaceTemplate.category))
        .where(and_(base_filter, MarketplaceTemplate.is_featured == True))
        .order_by(desc(MarketplaceTemplate.rating_average))
        .limit(8)
    )
    featured = featured_result.scalars().all()

    # Trending (most used in last 30 days - for now, just high usage)
    trending_result = await db.execute(
        select(MarketplaceTemplate)
        .options(selectinload(MarketplaceTemplate.author), selectinload(MarketplaceTemplate.category))
        .where(base_filter)
        .order_by(desc(MarketplaceTemplate.usage_count))
        .limit(8)
    )
    trending = trending_result.scalars().all()

    # Newest
    newest_result = await db.execute(
        select(MarketplaceTemplate)
        .options(selectinload(MarketplaceTemplate.author), selectinload(MarketplaceTemplate.category))
        .where(base_filter)
        .order_by(desc(MarketplaceTemplate.published_at))
        .limit(8)
    )
    newest = newest_result.scalars().all()

    # Templates by category
    categories_result = await db.execute(
        select(MarketplaceCategory)
        .where(MarketplaceCategory.is_active == True)
        .order_by(desc(MarketplaceCategory.template_count))
        .limit(4)
    )
    top_categories = categories_result.scalars().all()

    by_category = {}
    for cat in top_categories:
        cat_templates_result = await db.execute(
            select(MarketplaceTemplate)
            .options(selectinload(MarketplaceTemplate.author), selectinload(MarketplaceTemplate.category))
            .where(and_(base_filter, MarketplaceTemplate.category_id == cat.id))
            .order_by(desc(MarketplaceTemplate.rating_average))
            .limit(4)
        )
        cat_templates = cat_templates_result.scalars().all()
        by_category[cat.name] = [
            _to_template_list_item(t) for t in cat_templates
        ]

    return FeaturedTemplatesResponse(
        featured=[_to_template_list_item(t) for t in featured],
        trending=[_to_template_list_item(t) for t in trending],
        newest=[_to_template_list_item(t) for t in newest],
        by_category=by_category,
    )


def _to_template_list_item(t: MarketplaceTemplate) -> TemplateListItem:
    """Convert template model to list item schema."""
    return TemplateListItem(
        id=t.id,
        name=t.name,
        slug=t.slug,
        short_description=t.short_description,
        category_id=t.category_id,
        category_name=t.category.name if t.category else None,
        author_id=t.author_id,
        author_name=t.author.full_name if t.author else None,
        scenario_type=t.scenario_type,
        tags=t.tags or [],
        status=t.status,
        is_featured=t.is_featured,
        is_verified=t.is_verified,
        is_premium=t.is_premium,
        price_usd=t.price_usd,
        usage_count=t.usage_count,
        rating_average=t.rating_average,
        rating_count=t.rating_count,
        like_count=t.like_count,
        preview_image_url=t.preview_image_url,
        created_at=t.created_at,
        published_at=t.published_at,
    )


@router.get("/templates/{slug}", response_model=TemplateDetail)
async def get_template(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> TemplateDetail:
    """
    Get template details by slug.
    """
    result = await db.execute(
        select(MarketplaceTemplate)
        .options(
            selectinload(MarketplaceTemplate.author),
            selectinload(MarketplaceTemplate.category),
            selectinload(MarketplaceTemplate.organization),
        )
        .where(MarketplaceTemplate.slug == slug)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Check visibility
    if template.status != TemplateStatus.PUBLISHED.value:
        if not current_user or template.author_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found",
            )

    # Increment view count
    template.view_count += 1
    await db.flush()

    # Check if user liked this template
    is_liked = False
    user_review = None

    if current_user:
        like_result = await db.execute(
            select(TemplateLike).where(
                TemplateLike.template_id == template.id,
                TemplateLike.user_id == current_user.id,
            )
        )
        is_liked = like_result.scalar_one_or_none() is not None

        review_result = await db.execute(
            select(TemplateReview).where(
                TemplateReview.template_id == template.id,
                TemplateReview.user_id == current_user.id,
            )
        )
        review = review_result.scalar_one_or_none()
        if review:
            user_review = ReviewResponse(
                id=review.id,
                template_id=review.template_id,
                user_id=review.user_id,
                rating=review.rating,
                title=review.title,
                content=review.content,
                is_verified_purchase=review.is_verified_purchase,
                is_helpful_count=review.is_helpful_count,
                created_at=review.created_at,
                updated_at=review.updated_at,
            )

    return TemplateDetail(
        id=template.id,
        name=template.name,
        slug=template.slug,
        short_description=template.short_description,
        description=template.description,
        category_id=template.category_id,
        category_name=template.category.name if template.category else None,
        author_id=template.author_id,
        author_name=template.author.full_name if template.author else None,
        organization_id=template.organization_id,
        organization_name=template.organization.name if template.organization else None,
        scenario_type=template.scenario_type,
        tags=template.tags or [],
        status=template.status,
        is_featured=template.is_featured,
        is_verified=template.is_verified,
        is_premium=template.is_premium,
        price_usd=template.price_usd,
        usage_count=template.usage_count,
        rating_average=template.rating_average,
        rating_count=template.rating_count,
        like_count=template.like_count,
        view_count=template.view_count,
        preview_image_url=template.preview_image_url,
        created_at=template.created_at,
        published_at=template.published_at,
        updated_at=template.updated_at,
        context=template.context,
        questions=template.questions,
        variables=template.variables or {},
        demographics=template.demographics or {},
        persona_template=template.persona_template,
        llm_config=template.llm_config or {},
        recommended_population_size=template.recommended_population_size,
        stimulus_materials=template.stimulus_materials,
        methodology=template.methodology,
        sample_results=template.sample_results,
        version=template.version,
        is_liked_by_user=is_liked,
        user_review=user_review,
    )


# ============================================================
# Template Publishing Endpoints
# ============================================================

@router.post("/templates", response_model=TemplateDetail, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_in: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateDetail:
    """
    Create and publish a new template.
    """
    # Generate unique slug
    base_slug = generate_slug(template_in.name)
    slug = await ensure_unique_slug(db, base_slug)

    # Validate category if provided
    if template_in.category_id:
        cat_result = await db.execute(
            select(MarketplaceCategory).where(MarketplaceCategory.id == template_in.category_id)
        )
        if not cat_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found",
            )

    template = MarketplaceTemplate(
        name=template_in.name,
        slug=slug,
        description=template_in.description,
        short_description=template_in.short_description,
        category_id=template_in.category_id,
        tags=template_in.tags,
        author_id=current_user.id,
        organization_id=template_in.organization_id,
        scenario_type=template_in.scenario_type,
        context=template_in.context,
        questions=template_in.questions,
        variables=template_in.variables,
        demographics=template_in.demographics,
        persona_template=template_in.persona_template,
        llm_config=template_in.llm_config,
        recommended_population_size=template_in.recommended_population_size,
        stimulus_materials=template_in.stimulus_materials,
        methodology=template_in.methodology,
        preview_image_url=template_in.preview_image_url,
        sample_results=template_in.sample_results,
        source_scenario_id=template_in.source_scenario_id,
        is_premium=template_in.is_premium,
        price_usd=template_in.price_usd,
        status=TemplateStatus.PUBLISHED.value,
        published_at=datetime.utcnow(),
    )

    db.add(template)
    await db.flush()
    await db.refresh(template)

    # Update category template count
    if template.category_id:
        await db.execute(
            select(MarketplaceCategory)
            .where(MarketplaceCategory.id == template.category_id)
            .with_for_update()
        )
        cat_result = await db.execute(
            select(MarketplaceCategory).where(MarketplaceCategory.id == template.category_id)
        )
        cat = cat_result.scalar_one()
        cat.template_count += 1

    # Load relationships
    await db.refresh(template, ["author", "category", "organization"])

    return TemplateDetail(
        id=template.id,
        name=template.name,
        slug=template.slug,
        short_description=template.short_description,
        description=template.description,
        category_id=template.category_id,
        category_name=template.category.name if template.category else None,
        author_id=template.author_id,
        author_name=template.author.full_name if template.author else None,
        organization_id=template.organization_id,
        organization_name=template.organization.name if template.organization else None,
        scenario_type=template.scenario_type,
        tags=template.tags or [],
        status=template.status,
        is_featured=template.is_featured,
        is_verified=template.is_verified,
        is_premium=template.is_premium,
        price_usd=template.price_usd,
        usage_count=template.usage_count,
        rating_average=template.rating_average,
        rating_count=template.rating_count,
        like_count=template.like_count,
        view_count=template.view_count,
        preview_image_url=template.preview_image_url,
        created_at=template.created_at,
        published_at=template.published_at,
        updated_at=template.updated_at,
        context=template.context,
        questions=template.questions,
        variables=template.variables or {},
        demographics=template.demographics or {},
        persona_template=template.persona_template,
        llm_config=template.llm_config or {},
        recommended_population_size=template.recommended_population_size,
        stimulus_materials=template.stimulus_materials,
        methodology=template.methodology,
        sample_results=template.sample_results,
        version=template.version,
        is_liked_by_user=False,
        user_review=None,
    )


@router.post("/templates/from-scenario", response_model=TemplateDetail, status_code=status.HTTP_201_CREATED)
async def create_template_from_scenario(
    template_in: TemplateCreateFromScenario,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateDetail:
    """
    Publish a template from an existing scenario.
    """
    # Get scenario
    scenario_result = await db.execute(
        select(Scenario).where(Scenario.id == template_in.scenario_id)
    )
    scenario = scenario_result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    # Check ownership (via project)
    from app.models.simulation import Project
    project_result = await db.execute(
        select(Project).where(Project.id == scenario.project_id)
    )
    project = project_result.scalar_one_or_none()

    if not project or project.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to publish this scenario",
        )

    # Generate unique slug
    base_slug = generate_slug(template_in.name)
    slug = await ensure_unique_slug(db, base_slug)

    # Create template from scenario
    template = MarketplaceTemplate(
        name=template_in.name,
        slug=slug,
        description=template_in.description or scenario.description,
        short_description=template_in.short_description,
        category_id=template_in.category_id,
        tags=template_in.tags,
        author_id=current_user.id,
        organization_id=template_in.organization_id,
        scenario_type=scenario.scenario_type,
        context=scenario.context,
        questions=scenario.questions or [],
        variables=scenario.variables or {},
        demographics=scenario.demographics or {},
        persona_template=scenario.persona_template,
        llm_config=getattr(scenario, 'model_config_json', {}) or {},
        recommended_population_size=scenario.population_size,
        source_scenario_id=scenario.id,
        is_premium=template_in.is_premium,
        price_usd=template_in.price_usd,
        status=TemplateStatus.PUBLISHED.value,
        published_at=datetime.utcnow(),
    )

    db.add(template)
    await db.flush()
    await db.refresh(template)

    # Update category template count
    if template.category_id:
        cat_result = await db.execute(
            select(MarketplaceCategory).where(MarketplaceCategory.id == template.category_id)
        )
        cat = cat_result.scalar_one_or_none()
        if cat:
            cat.template_count += 1

    # Load relationships
    await db.refresh(template, ["author", "category", "organization"])

    return TemplateDetail(
        id=template.id,
        name=template.name,
        slug=template.slug,
        short_description=template.short_description,
        description=template.description,
        category_id=template.category_id,
        category_name=template.category.name if template.category else None,
        author_id=template.author_id,
        author_name=template.author.full_name if template.author else None,
        organization_id=template.organization_id,
        organization_name=template.organization.name if template.organization else None,
        scenario_type=template.scenario_type,
        tags=template.tags or [],
        status=template.status,
        is_featured=template.is_featured,
        is_verified=template.is_verified,
        is_premium=template.is_premium,
        price_usd=template.price_usd,
        usage_count=template.usage_count,
        rating_average=template.rating_average,
        rating_count=template.rating_count,
        like_count=template.like_count,
        view_count=template.view_count,
        preview_image_url=template.preview_image_url,
        created_at=template.created_at,
        published_at=template.published_at,
        updated_at=template.updated_at,
        context=template.context,
        questions=template.questions,
        variables=template.variables or {},
        demographics=template.demographics or {},
        persona_template=template.persona_template,
        llm_config=template.llm_config or {},
        recommended_population_size=template.recommended_population_size,
        stimulus_materials=template.stimulus_materials,
        methodology=template.methodology,
        sample_results=template.sample_results,
        version=template.version,
        is_liked_by_user=False,
        user_review=None,
    )


@router.put("/templates/{template_id}", response_model=TemplateDetail)
async def update_template(
    template_id: UUID,
    template_update: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateDetail:
    """
    Update a template (author only).
    """
    result = await db.execute(
        select(MarketplaceTemplate)
        .options(
            selectinload(MarketplaceTemplate.author),
            selectinload(MarketplaceTemplate.category),
            selectinload(MarketplaceTemplate.organization),
        )
        .where(MarketplaceTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Check ownership
    if template.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this template",
        )

    # Update fields
    update_data = template_update.model_dump(exclude_unset=True)
    old_category_id = template.category_id

    for field, value in update_data.items():
        setattr(template, field, value)

    # Handle category change
    new_category_id = template.category_id
    if old_category_id != new_category_id:
        if old_category_id:
            old_cat = await db.execute(
                select(MarketplaceCategory).where(MarketplaceCategory.id == old_category_id)
            )
            old_cat_obj = old_cat.scalar_one_or_none()
            if old_cat_obj:
                old_cat_obj.template_count = max(0, old_cat_obj.template_count - 1)

        if new_category_id:
            new_cat = await db.execute(
                select(MarketplaceCategory).where(MarketplaceCategory.id == new_category_id)
            )
            new_cat_obj = new_cat.scalar_one_or_none()
            if new_cat_obj:
                new_cat_obj.template_count += 1

    await db.flush()
    await db.refresh(template, ["author", "category", "organization"])

    return TemplateDetail(
        id=template.id,
        name=template.name,
        slug=template.slug,
        short_description=template.short_description,
        description=template.description,
        category_id=template.category_id,
        category_name=template.category.name if template.category else None,
        author_id=template.author_id,
        author_name=template.author.full_name if template.author else None,
        organization_id=template.organization_id,
        organization_name=template.organization.name if template.organization else None,
        scenario_type=template.scenario_type,
        tags=template.tags or [],
        status=template.status,
        is_featured=template.is_featured,
        is_verified=template.is_verified,
        is_premium=template.is_premium,
        price_usd=template.price_usd,
        usage_count=template.usage_count,
        rating_average=template.rating_average,
        rating_count=template.rating_count,
        like_count=template.like_count,
        view_count=template.view_count,
        preview_image_url=template.preview_image_url,
        created_at=template.created_at,
        published_at=template.published_at,
        updated_at=template.updated_at,
        context=template.context,
        questions=template.questions,
        variables=template.variables or {},
        demographics=template.demographics or {},
        persona_template=template.persona_template,
        llm_config=template.llm_config or {},
        recommended_population_size=template.recommended_population_size,
        stimulus_materials=template.stimulus_materials,
        methodology=template.methodology,
        sample_results=template.sample_results,
        version=template.version,
        is_liked_by_user=False,
        user_review=None,
    )


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Delete a template (author only).
    """
    result = await db.execute(
        select(MarketplaceTemplate).where(MarketplaceTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    if template.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this template",
        )

    # Update category count
    if template.category_id:
        cat_result = await db.execute(
            select(MarketplaceCategory).where(MarketplaceCategory.id == template.category_id)
        )
        cat = cat_result.scalar_one_or_none()
        if cat:
            cat.template_count = max(0, cat.template_count - 1)

    await db.delete(template)

    return {"message": "Template deleted successfully"}


@router.get("/my-templates", response_model=TemplateListResponse)
async def list_my_templates(
    status_filter: Optional[str] = Query(None, pattern="^(draft|pending_review|published|rejected|archived)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateListResponse:
    """
    List templates authored by the current user.
    """
    query = select(MarketplaceTemplate).where(
        MarketplaceTemplate.author_id == current_user.id
    )

    if status_filter:
        query = query.where(MarketplaceTemplate.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(MarketplaceTemplate.created_at))
    query = query.offset(offset).limit(page_size)
    query = query.options(
        selectinload(MarketplaceTemplate.author),
        selectinload(MarketplaceTemplate.category),
    )

    result = await db.execute(query)
    templates = result.scalars().all()

    items = [_to_template_list_item(t) for t in templates]

    return TemplateListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================
# Template Usage Endpoints
# ============================================================

@router.post("/templates/{template_id}/use", response_model=UseTemplateResponse)
async def use_template(
    template_id: UUID,
    use_request: UseTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UseTemplateResponse:
    """
    Use a template to create a new scenario.
    """
    result = await db.execute(
        select(MarketplaceTemplate).where(MarketplaceTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    if template.status != TemplateStatus.PUBLISHED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template is not available for use",
        )

    # TODO: Handle premium templates and payment

    # Get or create target project
    from app.models.simulation import Project

    if use_request.target_project_id:
        project_result = await db.execute(
            select(Project).where(Project.id == use_request.target_project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project or project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid target project",
            )
    else:
        # Create a new project
        project = Project(
            name=f"From Template: {template.name}",
            description=f"Created from marketplace template: {template.name}",
            user_id=current_user.id,
        )
        db.add(project)
        await db.flush()

    # Create scenario from template
    scenario_name = use_request.name or f"{template.name} (Copy)"

    scenario = Scenario(
        name=scenario_name,
        description=template.description,
        project_id=project.id,
        scenario_type=template.scenario_type,
        context=template.context,
        questions=template.questions,
        variables=template.variables,
        demographics=template.demographics,
        persona_template=template.persona_template,
        model_config_json=template.llm_config,
        population_size=template.recommended_population_size,
    )

    # Apply customizations
    if use_request.customizations:
        for key, value in use_request.customizations.items():
            if hasattr(scenario, key):
                setattr(scenario, key, value)

    db.add(scenario)
    await db.flush()
    await db.refresh(scenario)

    # Record usage
    usage = TemplateUsage(
        template_id=template.id,
        user_id=current_user.id,
        created_scenario_id=scenario.id,
        customizations=use_request.customizations,
    )
    db.add(usage)

    # Update template usage count
    template.usage_count += 1

    return UseTemplateResponse(
        usage_id=usage.id,
        template_id=template.id,
        created_type="scenario",
        created_id=scenario.id,
        created_name=scenario.name,
        message=f"Successfully created scenario '{scenario.name}' from template",
    )


# ============================================================
# Like & Review Endpoints
# ============================================================

@router.post("/templates/{template_id}/like")
async def toggle_like(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Toggle like on a template.
    """
    result = await db.execute(
        select(MarketplaceTemplate).where(MarketplaceTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Check existing like
    like_result = await db.execute(
        select(TemplateLike).where(
            TemplateLike.template_id == template_id,
            TemplateLike.user_id == current_user.id,
        )
    )
    existing_like = like_result.scalar_one_or_none()

    if existing_like:
        # Unlike
        await db.delete(existing_like)
        template.like_count = max(0, template.like_count - 1)
        return {"liked": False, "like_count": template.like_count}
    else:
        # Like
        like = TemplateLike(
            template_id=template_id,
            user_id=current_user.id,
        )
        db.add(like)
        template.like_count += 1
        return {"liked": True, "like_count": template.like_count}


@router.get("/templates/{template_id}/reviews", response_model=ReviewListResponse)
async def list_reviews(
    template_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ReviewListResponse:
    """
    List reviews for a template.
    """
    result = await db.execute(
        select(MarketplaceTemplate).where(MarketplaceTemplate.id == template_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Count total
    count_result = await db.execute(
        select(func.count(TemplateReview.id))
        .where(TemplateReview.template_id == template_id)
    )
    total = count_result.scalar()

    # Get reviews
    offset = (page - 1) * page_size
    reviews_result = await db.execute(
        select(TemplateReview, User)
        .join(User, TemplateReview.user_id == User.id)
        .where(TemplateReview.template_id == template_id)
        .order_by(desc(TemplateReview.created_at))
        .offset(offset)
        .limit(page_size)
    )

    items = []
    for review, user in reviews_result.all():
        items.append(ReviewResponse(
            id=review.id,
            template_id=review.template_id,
            user_id=review.user_id,
            user_name=user.full_name,
            rating=review.rating,
            title=review.title,
            content=review.content,
            is_verified_purchase=review.is_verified_purchase,
            is_helpful_count=review.is_helpful_count,
            created_at=review.created_at,
            updated_at=review.updated_at,
        ))

    # Get rating distribution
    distribution_result = await db.execute(
        select(TemplateReview.rating, func.count(TemplateReview.id))
        .where(TemplateReview.template_id == template_id)
        .group_by(TemplateReview.rating)
    )
    rating_distribution = {i: 0 for i in range(1, 6)}
    for rating, count in distribution_result.all():
        rating_distribution[rating] = count

    # Calculate average
    avg_result = await db.execute(
        select(func.avg(TemplateReview.rating))
        .where(TemplateReview.template_id == template_id)
    )
    average_rating = avg_result.scalar() or 0.0

    return ReviewListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        average_rating=float(average_rating),
        rating_distribution=rating_distribution,
    )


@router.post("/templates/{template_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    template_id: UUID,
    review_in: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewResponse:
    """
    Create or update a review for a template.
    """
    result = await db.execute(
        select(MarketplaceTemplate).where(MarketplaceTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Check existing review
    existing_result = await db.execute(
        select(TemplateReview).where(
            TemplateReview.template_id == template_id,
            TemplateReview.user_id == current_user.id,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this template. Use PUT to update.",
        )

    # Check if user has used this template
    usage_result = await db.execute(
        select(TemplateUsage).where(
            TemplateUsage.template_id == template_id,
            TemplateUsage.user_id == current_user.id,
        )
    )
    is_verified_purchase = usage_result.scalar_one_or_none() is not None

    review = TemplateReview(
        template_id=template_id,
        user_id=current_user.id,
        rating=review_in.rating,
        title=review_in.title,
        content=review_in.content,
        is_verified_purchase=is_verified_purchase,
    )

    db.add(review)
    await db.flush()

    # Update template rating
    await _update_template_rating(db, template_id)

    return ReviewResponse(
        id=review.id,
        template_id=review.template_id,
        user_id=review.user_id,
        user_name=current_user.full_name,
        rating=review.rating,
        title=review.title,
        content=review.content,
        is_verified_purchase=review.is_verified_purchase,
        is_helpful_count=review.is_helpful_count,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


@router.put("/templates/{template_id}/reviews", response_model=ReviewResponse)
async def update_review(
    template_id: UUID,
    review_update: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewResponse:
    """
    Update your review for a template.
    """
    result = await db.execute(
        select(TemplateReview).where(
            TemplateReview.template_id == template_id,
            TemplateReview.user_id == current_user.id,
        )
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    update_data = review_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review, field, value)

    await db.flush()

    # Update template rating if rating changed
    if "rating" in update_data:
        await _update_template_rating(db, template_id)

    return ReviewResponse(
        id=review.id,
        template_id=review.template_id,
        user_id=review.user_id,
        user_name=current_user.full_name,
        rating=review.rating,
        title=review.title,
        content=review.content,
        is_verified_purchase=review.is_verified_purchase,
        is_helpful_count=review.is_helpful_count,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


@router.delete("/templates/{template_id}/reviews")
async def delete_review(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Delete your review for a template.
    """
    result = await db.execute(
        select(TemplateReview).where(
            TemplateReview.template_id == template_id,
            TemplateReview.user_id == current_user.id,
        )
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    await db.delete(review)

    # Update template rating
    await _update_template_rating(db, template_id)

    return {"message": "Review deleted successfully"}


async def _update_template_rating(db: AsyncSession, template_id: UUID):
    """Update template's rating average and count."""
    result = await db.execute(
        select(
            func.count(TemplateReview.id),
            func.avg(TemplateReview.rating)
        ).where(TemplateReview.template_id == template_id)
    )
    count, avg = result.one()

    template_result = await db.execute(
        select(MarketplaceTemplate).where(MarketplaceTemplate.id == template_id)
    )
    template = template_result.scalar_one()
    template.rating_count = count or 0
    template.rating_average = float(avg) if avg else 0.0


# ============================================================
# Stats Endpoints
# ============================================================

@router.get("/stats", response_model=MarketplaceStats)
async def get_marketplace_stats(
    db: AsyncSession = Depends(get_db),
) -> MarketplaceStats:
    """
    Get overall marketplace statistics.
    """
    # Total templates
    templates_result = await db.execute(
        select(func.count(MarketplaceTemplate.id))
        .where(MarketplaceTemplate.status == TemplateStatus.PUBLISHED.value)
    )
    total_templates = templates_result.scalar()

    # Total categories
    categories_result = await db.execute(
        select(func.count(MarketplaceCategory.id))
        .where(MarketplaceCategory.is_active == True)
    )
    total_categories = categories_result.scalar()

    # Total usages
    usages_result = await db.execute(
        select(func.count(TemplateUsage.id))
    )
    total_usages = usages_result.scalar()

    # Total reviews
    reviews_result = await db.execute(
        select(func.count(TemplateReview.id))
    )
    total_reviews = reviews_result.scalar()

    # Average rating
    avg_result = await db.execute(
        select(func.avg(MarketplaceTemplate.rating_average))
        .where(
            MarketplaceTemplate.status == TemplateStatus.PUBLISHED.value,
            MarketplaceTemplate.rating_count > 0
        )
    )
    average_rating = float(avg_result.scalar() or 0.0)

    # Top categories
    top_cats_result = await db.execute(
        select(MarketplaceCategory)
        .where(MarketplaceCategory.is_active == True)
        .order_by(desc(MarketplaceCategory.template_count))
        .limit(5)
    )
    top_categories = [
        {"name": cat.name, "slug": cat.slug, "count": cat.template_count}
        for cat in top_cats_result.scalars().all()
    ]

    # Top authors
    top_authors_result = await db.execute(
        select(
            MarketplaceTemplate.author_id,
            User.full_name,
            func.count(MarketplaceTemplate.id).label("template_count"),
            func.sum(MarketplaceTemplate.usage_count).label("total_usage")
        )
        .join(User, MarketplaceTemplate.author_id == User.id)
        .where(MarketplaceTemplate.status == TemplateStatus.PUBLISHED.value)
        .group_by(MarketplaceTemplate.author_id, User.full_name)
        .order_by(desc("total_usage"))
        .limit(5)
    )
    top_authors = [
        {
            "author_id": str(author_id),
            "name": name,
            "template_count": template_count,
            "total_usage": total_usage or 0
        }
        for author_id, name, template_count, total_usage in top_authors_result.all()
    ]

    return MarketplaceStats(
        total_templates=total_templates,
        total_categories=total_categories,
        total_usages=total_usages,
        total_reviews=total_reviews,
        average_rating=average_rating,
        top_categories=top_categories,
        top_authors=top_authors,
    )


@router.get("/authors/{author_id}/stats", response_model=AuthorStats)
async def get_author_stats(
    author_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AuthorStats:
    """
    Get statistics for a specific author.
    """
    # Check author exists
    author_result = await db.execute(
        select(User).where(User.id == author_id)
    )
    if not author_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Author not found",
        )

    # Get author's templates
    templates_query = select(MarketplaceTemplate).where(
        MarketplaceTemplate.author_id == author_id,
        MarketplaceTemplate.status == TemplateStatus.PUBLISHED.value
    ).options(
        selectinload(MarketplaceTemplate.author),
        selectinload(MarketplaceTemplate.category),
    )

    templates_result = await db.execute(templates_query)
    templates = templates_result.scalars().all()

    total_templates = len(templates)
    total_usages = sum(t.usage_count for t in templates)
    total_likes = sum(t.like_count for t in templates)

    # Total reviews
    reviews_result = await db.execute(
        select(func.count(TemplateReview.id))
        .join(MarketplaceTemplate)
        .where(MarketplaceTemplate.author_id == author_id)
    )
    total_reviews = reviews_result.scalar()

    # Average rating
    if templates:
        rated_templates = [t for t in templates if t.rating_count > 0]
        if rated_templates:
            average_rating = sum(t.rating_average for t in rated_templates) / len(rated_templates)
        else:
            average_rating = 0.0
    else:
        average_rating = 0.0

    return AuthorStats(
        total_templates=total_templates,
        total_usages=total_usages,
        total_reviews=total_reviews,
        average_rating=average_rating,
        total_likes=total_likes,
        templates=[_to_template_list_item(t) for t in templates],
    )
