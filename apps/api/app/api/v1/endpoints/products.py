"""
Products API Endpoints - 3-Model System
Predict, Insight, Simulate product management
"""

import asyncio
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.product import (
    Product, ProductRun, ProductResult, AgentInteraction,
    ProductType, PredictionType, InsightType, SimulationType
)
from app.models.user import User
from app.api.deps import get_current_user
from app.services.product_execution import ProductExecutionService, get_product_execution_service
from app.core.websocket import get_ws_manager, create_progress_callback
from pydantic import BaseModel, Field
from datetime import datetime


logger = logging.getLogger(__name__)


router = APIRouter()


# ============= Schemas =============

class TargetMarketSchema(BaseModel):
    regions: List[str] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list)
    demographics: dict = Field(default_factory=dict)
    sample_size: int = 100


class ProductCreate(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    product_type: str = Field(..., pattern="^(predict|insight|simulate)$")
    sub_type: Optional[str] = None
    target_market: TargetMarketSchema
    persona_template_id: Optional[UUID] = None
    persona_count: int = Field(default=100, ge=1, le=10000)
    persona_source: str = "ai_generated"
    configuration: dict = Field(default_factory=dict)
    stimulus_materials: Optional[dict] = None
    methodology: Optional[dict] = None
    confidence_target: float = Field(default=0.9, ge=0.5, le=0.99)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    target_market: Optional[TargetMarketSchema] = None
    persona_template_id: Optional[UUID] = None
    persona_count: Optional[int] = Field(None, ge=1, le=10000)
    configuration: Optional[dict] = None
    stimulus_materials: Optional[dict] = None
    methodology: Optional[dict] = None
    confidence_target: Optional[float] = Field(None, ge=0.5, le=0.99)


class ProductResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: Optional[str]
    product_type: str
    sub_type: Optional[str]
    target_market: dict
    persona_template_id: Optional[UUID]
    persona_count: int
    persona_source: str
    configuration: dict
    stimulus_materials: Optional[dict]
    methodology: Optional[dict]
    confidence_target: float
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProductRunCreate(BaseModel):
    name: Optional[str] = None


class ProductRunResponse(BaseModel):
    id: UUID
    product_id: UUID
    run_number: int
    name: Optional[str]
    status: str
    progress: int
    agents_total: int
    agents_completed: int
    agents_failed: int
    tokens_used: int
    estimated_cost: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProductResultResponse(BaseModel):
    id: UUID
    product_id: UUID
    run_id: Optional[UUID]
    result_type: str
    predictions: Optional[dict]
    insights: Optional[dict]
    simulation_outcomes: Optional[dict]
    statistical_analysis: Optional[dict]
    segment_analysis: Optional[dict]
    confidence_score: float
    executive_summary: Optional[str]
    key_takeaways: Optional[list]
    recommendations: Optional[list]
    visualizations: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class ProductStatsResponse(BaseModel):
    total_products: int
    by_type: dict
    by_status: dict
    total_runs: int
    active_runs: int
    completed_runs: int
    total_agents: int
    avg_confidence: float


# ============= Product CRUD =============

@router.get("/", response_model=List[ProductResponse])
async def list_products(
    project_id: Optional[UUID] = None,
    product_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all products for the current user."""
    query = select(Product).where(Product.user_id == current_user.id)

    if project_id:
        query = query.where(Product.project_id == project_id)
    if product_type:
        query = query.where(Product.product_type == product_type)
    if status:
        query = query.where(Product.status == status)

    query = query.order_by(Product.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new product (Predict, Insight, or Simulate)."""
    # Validate sub_type based on product_type
    if product_data.product_type == "predict" and product_data.sub_type:
        valid_types = [e.value for e in PredictionType]
        if product_data.sub_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid prediction sub_type. Must be one of: {valid_types}"
            )
    elif product_data.product_type == "insight" and product_data.sub_type:
        valid_types = [e.value for e in InsightType]
        if product_data.sub_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid insight sub_type. Must be one of: {valid_types}"
            )
    elif product_data.product_type == "simulate" and product_data.sub_type:
        valid_types = [e.value for e in SimulationType]
        if product_data.sub_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid simulation sub_type. Must be one of: {valid_types}"
            )

    product = Product(
        user_id=current_user.id,
        project_id=product_data.project_id,
        name=product_data.name,
        description=product_data.description,
        product_type=product_data.product_type,
        sub_type=product_data.sub_type,
        target_market=product_data.target_market.model_dump(),
        persona_template_id=product_data.persona_template_id,
        persona_count=product_data.persona_count,
        persona_source=product_data.persona_source,
        configuration=product_data.configuration,
        stimulus_materials=product_data.stimulus_materials,
        methodology=product_data.methodology,
        confidence_target=product_data.confidence_target,
        status="draft"
    )

    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("/stats", response_model=ProductStatsResponse)
async def get_product_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get product statistics for the current user."""
    # Total products
    total_query = select(func.count(Product.id)).where(Product.user_id == current_user.id)
    total_result = await db.execute(total_query)
    total_products = total_result.scalar() or 0

    # By type
    type_query = select(
        Product.product_type,
        func.count(Product.id)
    ).where(Product.user_id == current_user.id).group_by(Product.product_type)
    type_result = await db.execute(type_query)
    by_type = {row[0]: row[1] for row in type_result.all()}

    # By status
    status_query = select(
        Product.status,
        func.count(Product.id)
    ).where(Product.user_id == current_user.id).group_by(Product.status)
    status_result = await db.execute(status_query)
    by_status = {row[0]: row[1] for row in status_result.all()}

    # Total runs
    runs_query = select(func.count(ProductRun.id)).join(
        Product, ProductRun.product_id == Product.id
    ).where(Product.user_id == current_user.id)
    runs_result = await db.execute(runs_query)
    total_runs = runs_result.scalar() or 0

    # Active runs (running or pending)
    active_query = select(func.count(ProductRun.id)).join(
        Product, ProductRun.product_id == Product.id
    ).where(
        and_(
            Product.user_id == current_user.id,
            ProductRun.status.in_(["running", "pending"])
        )
    )
    active_result = await db.execute(active_query)
    active_runs = active_result.scalar() or 0

    # Completed runs
    completed_query = select(func.count(ProductRun.id)).join(
        Product, ProductRun.product_id == Product.id
    ).where(
        and_(
            Product.user_id == current_user.id,
            ProductRun.status == "completed"
        )
    )
    completed_result = await db.execute(completed_query)
    completed_runs = completed_result.scalar() or 0

    # Total agents simulated
    agents_query = select(func.sum(ProductRun.agents_completed)).join(
        Product, ProductRun.product_id == Product.id
    ).where(Product.user_id == current_user.id)
    agents_result = await db.execute(agents_query)
    total_agents = agents_result.scalar() or 0

    # Average confidence
    conf_query = select(func.avg(ProductResult.confidence_score)).join(
        Product, ProductResult.product_id == Product.id
    ).where(Product.user_id == current_user.id)
    conf_result = await db.execute(conf_query)
    avg_confidence = conf_result.scalar() or 0.0

    return ProductStatsResponse(
        total_products=total_products,
        by_type=by_type,
        by_status=by_status,
        total_runs=total_runs,
        active_runs=active_runs,
        completed_runs=completed_runs,
        total_agents=int(total_agents),
        avg_confidence=round(avg_confidence, 3)
    )


@router.get("/types")
async def get_product_types():
    """Get available product types and sub-types."""
    return {
        "product_types": [
            {
                "type": "predict",
                "name": "Predict",
                "description": "Quantitative predictions with confidence intervals",
                "sub_types": [{"value": e.value, "name": e.value.replace("_", " ").title()} for e in PredictionType]
            },
            {
                "type": "insight",
                "name": "Insight",
                "description": "Qualitative deep-dive into motivations and behaviors",
                "sub_types": [{"value": e.value, "name": e.value.replace("_", " ").title()} for e in InsightType]
            },
            {
                "type": "simulate",
                "name": "Simulate",
                "description": "Real-time interactive simulations with agent dynamics",
                "sub_types": [{"value": e.value, "name": e.value.replace("_", " ").title()} for e in SimulationType]
            }
        ]
    }


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific product by ID."""
    query = select(Product).where(
        and_(Product.id == product_id, Product.user_id == current_user.id)
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a product."""
    query = select(Product).where(
        and_(Product.id == product_id, Product.user_id == current_user.id)
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.status not in ["draft", "configured"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot modify product that is running or completed"
        )

    update_data = product_data.model_dump(exclude_unset=True)
    if "target_market" in update_data:
        update_data["target_market"] = update_data["target_market"].model_dump() if hasattr(update_data["target_market"], "model_dump") else update_data["target_market"]

    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a product."""
    query = select(Product).where(
        and_(Product.id == product_id, Product.user_id == current_user.id)
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()


# ============= Product Runs =============

@router.get("/{product_id}/runs", response_model=List[ProductRunResponse])
async def list_product_runs(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all runs for a product."""
    # Verify ownership
    product_query = select(Product).where(
        and_(Product.id == product_id, Product.user_id == current_user.id)
    )
    product_result = await db.execute(product_query)
    if not product_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    query = select(ProductRun).where(
        ProductRun.product_id == product_id
    ).order_by(ProductRun.run_number.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{product_id}/runs", response_model=ProductRunResponse, status_code=status.HTTP_201_CREATED)
async def create_product_run(
    product_id: UUID,
    run_data: ProductRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new run for a product."""
    # Get product
    product_query = select(Product).where(
        and_(Product.id == product_id, Product.user_id == current_user.id)
    )
    product_result = await db.execute(product_query)
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get next run number
    run_count_query = select(func.count(ProductRun.id)).where(
        ProductRun.product_id == product_id
    )
    run_count_result = await db.execute(run_count_query)
    run_number = (run_count_result.scalar() or 0) + 1

    # Create run
    run = ProductRun(
        product_id=product_id,
        run_number=run_number,
        name=run_data.name or f"Run #{run_number}",
        config_snapshot={
            "product_type": product.product_type,
            "sub_type": product.sub_type,
            "target_market": product.target_market,
            "configuration": product.configuration,
            "persona_count": product.persona_count
        },
        agents_total=product.persona_count,
        status="pending"
    )

    db.add(run)

    # Update product status
    product.status = "configured"

    await db.commit()
    await db.refresh(run)
    return run


@router.post("/{product_id}/runs/{run_id}/start", response_model=ProductRunResponse)
async def start_product_run(
    product_id: UUID,
    run_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a product run and execute simulation in background."""
    # Verify ownership
    product_query = select(Product).where(
        and_(Product.id == product_id, Product.user_id == current_user.id)
    )
    product_result = await db.execute(product_query)
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get run
    run_query = select(ProductRun).where(
        and_(ProductRun.id == run_id, ProductRun.product_id == product_id)
    )
    run_result = await db.execute(run_query)
    run = run_result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status != "pending":
        raise HTTPException(status_code=400, detail="Run has already been started")

    # Update status to running
    run.status = "running"
    run.started_at = datetime.utcnow()
    product.status = "running"

    await db.commit()
    await db.refresh(run)

    # Add background task to execute the simulation
    background_tasks.add_task(
        execute_product_run_background,
        product_id=str(product_id),
        run_id=str(run_id)
    )

    return run


async def execute_product_run_background(product_id: str, run_id: str):
    """
    Background task to execute a product run.
    Creates a new database session for the background task.
    """
    from app.db.session import AsyncSessionLocal

    logger.info(f"Starting background execution for product {product_id}, run {run_id}")

    async with AsyncSessionLocal() as db:
        try:
            # Load product and run
            product_query = select(Product).where(Product.id == UUID(product_id))
            product_result = await db.execute(product_query)
            product = product_result.scalar_one_or_none()

            run_query = select(ProductRun).where(ProductRun.id == UUID(run_id))
            run_result = await db.execute(run_query)
            run = run_result.scalar_one_or_none()

            if not product or not run:
                logger.error(f"Product or run not found: {product_id}, {run_id}")
                return

            # Create execution service
            execution_service = get_product_execution_service()

            # Create progress callback for WebSocket updates
            progress_callback = create_progress_callback(run_id)

            # Execute the run
            result = await execution_service.execute_run(
                product=product,
                run=run,
                db=db,
                progress_callback=progress_callback
            )

            # Send completion notification via WebSocket
            ws_manager = get_ws_manager()
            await ws_manager.send_run_complete(
                run_id=run_id,
                result_id=str(result.id),
                summary={
                    "confidence_score": result.confidence_score,
                    "executive_summary": result.executive_summary,
                    "key_takeaways": result.key_takeaways
                }
            )

            logger.info(f"Completed execution for product {product_id}, run {run_id}")

        except Exception as e:
            logger.error(f"Failed execution for product {product_id}, run {run_id}: {str(e)}")

            # Update status to failed
            run_query = select(ProductRun).where(ProductRun.id == UUID(run_id))
            run_result = await db.execute(run_query)
            run = run_result.scalar_one_or_none()

            if run:
                run.status = "failed"
                run.completed_at = datetime.utcnow()
                await db.commit()

            # Send failure notification via WebSocket
            ws_manager = get_ws_manager()
            await ws_manager.send_run_failed(run_id=run_id, error=str(e))


@router.post("/{product_id}/runs/{run_id}/cancel", response_model=ProductRunResponse)
async def cancel_product_run(
    product_id: UUID,
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a running product run."""
    # Verify ownership
    product_query = select(Product).where(
        and_(Product.id == product_id, Product.user_id == current_user.id)
    )
    product_result = await db.execute(product_query)
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get run
    run_query = select(ProductRun).where(
        and_(ProductRun.id == run_id, ProductRun.product_id == product_id)
    )
    run_result = await db.execute(run_query)
    run = run_result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="Run cannot be cancelled")

    run.status = "cancelled"
    run.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(run)
    return run


# ============= Product Results =============

@router.get("/{product_id}/results", response_model=List[ProductResultResponse])
async def list_product_results(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all results for a product."""
    # Verify ownership
    product_query = select(Product).where(
        and_(Product.id == product_id, Product.user_id == current_user.id)
    )
    product_result = await db.execute(product_query)
    if not product_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    query = select(ProductResult).where(
        ProductResult.product_id == product_id
    ).order_by(ProductResult.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{product_id}/results/{result_id}", response_model=ProductResultResponse)
async def get_product_result(
    product_id: UUID,
    result_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific result."""
    # Verify ownership
    product_query = select(Product).where(
        and_(Product.id == product_id, Product.user_id == current_user.id)
    )
    product_result = await db.execute(product_query)
    if not product_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    query = select(ProductResult).where(
        and_(ProductResult.id == result_id, ProductResult.product_id == product_id)
    )
    result = await db.execute(query)
    product_result = result.scalar_one_or_none()

    if not product_result:
        raise HTTPException(status_code=404, detail="Result not found")

    return product_result


# ============= Comparison & Analytics =============

class ComparisonRequest(BaseModel):
    product_ids: List[UUID] = Field(..., min_length=2, max_length=10)
    metrics: List[str] = Field(default=["sentiment", "demographics", "purchase_likelihood"])


class ComparisonResultItem(BaseModel):
    product_id: UUID
    product_name: str
    result_id: Optional[UUID]
    data: dict


class ComparisonResponse(BaseModel):
    products: List[ComparisonResultItem]
    comparison_metrics: dict
    statistical_significance: dict


@router.post("/compare", response_model=ComparisonResponse)
async def compare_products(
    comparison_data: ComparisonRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compare results across multiple products."""
    # Fetch products
    products_query = select(Product).where(
        and_(
            Product.id.in_(comparison_data.product_ids),
            Product.user_id == current_user.id
        )
    )
    products_result = await db.execute(products_query)
    products = products_result.scalars().all()

    if len(products) != len(comparison_data.product_ids):
        raise HTTPException(status_code=404, detail="One or more products not found")

    # Fetch latest result for each product
    comparison_results = []
    all_metrics: dict = {metric: [] for metric in comparison_data.metrics}

    for product in products:
        result_query = select(ProductResult).where(
            ProductResult.product_id == product.id
        ).order_by(ProductResult.created_at.desc()).limit(1)

        result_result = await db.execute(result_query)
        result = result_result.scalar_one_or_none()

        result_data = {}
        if result:
            if "sentiment" in comparison_data.metrics and result.simulation_outcomes:
                result_data["sentiment_distribution"] = result.simulation_outcomes.get("sentiment_distribution", {})
                for sentiment, count in result_data.get("sentiment_distribution", {}).items():
                    all_metrics["sentiment"].append({"product": product.name, "sentiment": sentiment, "count": count})

            if "demographics" in comparison_data.metrics and result.segment_analysis:
                result_data["demographics"] = result.segment_analysis

            if "purchase_likelihood" in comparison_data.metrics and result.predictions:
                result_data["purchase_likelihood"] = result.predictions.get("purchase_likelihood", {})
                for likelihood, count in result_data.get("purchase_likelihood", {}).items():
                    all_metrics["purchase_likelihood"].append({"product": product.name, "likelihood": likelihood, "count": count})

        comparison_results.append(ComparisonResultItem(
            product_id=product.id,
            product_name=product.name,
            result_id=result.id if result else None,
            data=result_data
        ))

    # Calculate statistical significance between products
    significance = {}
    if len(comparison_results) >= 2:
        # Simple chi-square-like comparison for sentiment
        for metric in comparison_data.metrics:
            significance[metric] = {
                "is_significant": False,
                "p_value": 1.0,
                "description": "Comparison across products"
            }
            # Here you would calculate actual statistical significance
            # For now, just marking as placeholder
            if metric == "sentiment" and len(all_metrics.get("sentiment", [])) > 0:
                significance[metric]["description"] = f"Compared {len(products)} products"

    return ComparisonResponse(
        products=comparison_results,
        comparison_metrics=all_metrics,
        statistical_significance=significance
    )


@router.get("/{product_id}/trends")
async def get_product_trends(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get trend data across multiple runs of a product."""
    # Verify ownership
    product_query = select(Product).where(
        and_(Product.id == product_id, Product.user_id == current_user.id)
    )
    product_result = await db.execute(product_query)
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get all results ordered by run
    results_query = select(ProductResult).where(
        ProductResult.product_id == product_id
    ).order_by(ProductResult.created_at.asc())

    results_result = await db.execute(results_query)
    results = results_result.scalars().all()

    # Build trend data
    trends = {
        "confidence_scores": [],
        "sentiment_trends": [],
        "purchase_likelihood_trends": [],
        "run_dates": []
    }

    for i, result in enumerate(results):
        run_label = f"Run {i + 1}"
        trends["run_dates"].append({
            "name": run_label,
            "date": result.created_at.isoformat()
        })
        trends["confidence_scores"].append({
            "name": run_label,
            "value": result.confidence_score
        })

        if result.simulation_outcomes:
            sentiment_dist = result.simulation_outcomes.get("sentiment_distribution", {})
            positive = sentiment_dist.get("positive", 0)
            total = sum(sentiment_dist.values()) if sentiment_dist else 1
            trends["sentiment_trends"].append({
                "name": run_label,
                "positive_ratio": positive / total if total > 0 else 0,
                "distribution": sentiment_dist
            })

        if result.predictions:
            purchase = result.predictions.get("purchase_likelihood", {})
            likely = purchase.get("likely", 0) + purchase.get("very_likely", 0)
            total = sum(purchase.values()) if purchase else 1
            trends["purchase_likelihood_trends"].append({
                "name": run_label,
                "likely_ratio": likely / total if total > 0 else 0,
                "distribution": purchase
            })

    return {
        "product_id": str(product_id),
        "product_name": product.name,
        "total_runs": len(results),
        "trends": trends
    }
