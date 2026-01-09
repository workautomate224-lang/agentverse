"""
AI Content Generation Endpoints
Provides templates and AI-generated content for scenarios and products.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.ai_content_generator import (
    get_ai_content_generator,
    ContentTemplate,
    GeneratedContent,
)

router = APIRouter()


class GenerateContentRequest(BaseModel):
    """Request model for content generation."""
    title: str = Field(..., min_length=3, max_length=500, description="Title to generate content for")
    product_type: Optional[str] = Field(None, description="Product type: predict, insight, simulate")
    sub_type: Optional[str] = Field(None, description="Product subtype")
    target_market: Optional[dict] = Field(None, description="Target market configuration")


class TemplateListResponse(BaseModel):
    """Response model for template list."""
    templates: List[ContentTemplate]
    total: int


class GenerateContentResponse(BaseModel):
    """Response model for generated content."""
    success: bool
    content: GeneratedContent


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by category: marketing, political, research, qualitative, product"),
    current_user: User = Depends(get_current_user),
):
    """
    List all available content templates.

    Templates provide predefined context and questions for common research scenarios.
    """
    generator = get_ai_content_generator()
    templates = generator.get_templates(category=category)
    return TemplateListResponse(
        templates=templates,
        total=len(templates),
    )


@router.get("/templates/{template_id}", response_model=ContentTemplate)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific template by ID.

    Returns full template details including context and questions.
    """
    generator = get_ai_content_generator()
    template = generator.get_template_by_id(template_id)

    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{template_id}' not found",
        )

    return template


@router.post("/generate", response_model=GenerateContentResponse)
async def generate_content(
    request: GenerateContentRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate AI content based on title and parameters.

    Uses intelligent pattern matching to generate:
    - Description: Brief summary of the research
    - Context: Detailed context for AI agents
    - Questions: Relevant survey questions
    - Recommendations: Study recommendations

    The generated content is fully editable by users.
    """
    generator = get_ai_content_generator()

    content = await generator.generate_context(
        title=request.title,
        product_type=request.product_type,
        sub_type=request.sub_type,
        target_market=request.target_market,
    )

    return GenerateContentResponse(
        success=True,
        content=content,
    )


@router.get("/categories")
async def list_categories(
    current_user: User = Depends(get_current_user),
):
    """
    List all available template categories.
    """
    return {
        "categories": [
            {"id": "marketing", "name": "Marketing", "description": "Product launches, brand studies, pricing research"},
            {"id": "political", "name": "Political", "description": "Election polls, policy sentiment, voter behavior"},
            {"id": "research", "name": "Research", "description": "Market research, customer satisfaction studies"},
            {"id": "qualitative", "name": "Qualitative", "description": "Focus groups, in-depth interviews"},
            {"id": "product", "name": "Product", "description": "UX testing, feature evaluation"},
        ]
    }
