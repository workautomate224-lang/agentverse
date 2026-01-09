"""
Validation API Endpoints
Manages benchmarks, validation records, and accuracy tracking.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.validation import (
    ValidationService,
    BenchmarkCreate,
    BenchmarkResponse,
    ValidationCreate,
    ValidationResponse,
    AccuracyStats,
)


router = APIRouter()


# ==================== Benchmarks ====================

@router.get("/benchmarks", response_model=list[BenchmarkResponse])
async def list_benchmarks(
    category: Optional[str] = Query(None, description="Filter by category (election, product_launch, etc.)"),
    region: Optional[str] = Query(None, description="Filter by region (us, europe, etc.)"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all benchmarks with optional filtering."""
    service = ValidationService(db)
    benchmarks = await service.list_benchmarks(
        category=category,
        region=region,
        is_public=is_public,
        limit=limit,
        offset=offset
    )
    return benchmarks


@router.post("/benchmarks", response_model=BenchmarkResponse)
async def create_benchmark(
    data: BenchmarkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new benchmark record."""
    service = ValidationService(db)
    benchmark = await service.create_benchmark(data, user_id=current_user.id)
    await db.commit()
    return benchmark


@router.get("/benchmarks/{benchmark_id}", response_model=BenchmarkResponse)
async def get_benchmark(
    benchmark_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific benchmark by ID."""
    service = ValidationService(db)
    benchmark = await service.get_benchmark(benchmark_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return benchmark


@router.delete("/benchmarks/{benchmark_id}")
async def delete_benchmark(
    benchmark_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a benchmark."""
    service = ValidationService(db)
    benchmark = await service.get_benchmark(benchmark_id)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    # Only owner or admin can delete
    if benchmark.user_id and benchmark.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this benchmark")

    await service.delete_benchmark(benchmark_id)
    await db.commit()
    return {"status": "deleted", "id": str(benchmark_id)}


@router.patch("/benchmarks/{benchmark_id}/verify")
async def verify_benchmark(
    benchmark_id: UUID,
    status: str = Query(..., pattern="^(pending|verified|rejected)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update benchmark verification status (admin only)."""
    # TODO: Add admin check
    service = ValidationService(db)
    benchmark = await service.update_benchmark_verification(benchmark_id, status)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    await db.commit()
    return {"status": "updated", "verification_status": status}


@router.post("/benchmarks/seed-elections")
async def seed_election_benchmarks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seed historical election benchmarks for validation."""
    service = ValidationService(db)
    benchmarks = await service.seed_election_benchmarks()
    await db.commit()
    return {
        "status": "success",
        "message": f"Seeded {len(benchmarks)} election benchmarks",
        "benchmarks": [{"id": str(b.id), "name": b.name} for b in benchmarks]
    }


# ==================== Validation ====================

@router.get("/records", response_model=list[ValidationResponse])
async def list_validations(
    product_id: Optional[UUID] = Query(None),
    benchmark_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List validation records with filtering."""
    service = ValidationService(db)
    validations = await service.list_validations(
        product_id=product_id,
        benchmark_id=benchmark_id,
        limit=limit,
        offset=offset
    )
    return validations


@router.post("/validate", response_model=ValidationResponse)
async def validate_prediction(
    data: ValidationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate a product's prediction against a benchmark.
    Calculates accuracy score and creates a validation record.
    """
    service = ValidationService(db)
    validation = await service.validate_prediction(
        product_id=data.product_id,
        benchmark_id=data.benchmark_id
    )
    if not validation:
        raise HTTPException(
            status_code=400,
            detail="Could not validate: Product result or benchmark not found"
        )
    await db.commit()
    return validation


@router.get("/records/{validation_id}", response_model=ValidationResponse)
async def get_validation(
    validation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific validation record."""
    service = ValidationService(db)
    validation = await service.get_validation(validation_id)
    if not validation:
        raise HTTPException(status_code=404, detail="Validation record not found")
    return validation


# ==================== Statistics ====================

@router.get("/stats", response_model=AccuracyStats)
async def get_accuracy_stats(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get comprehensive accuracy statistics for the current user."""
    service = ValidationService(db)
    stats = await service.get_accuracy_stats(
        user_id=current_user.id,
        category=category
    )
    return stats


@router.get("/stats/global", response_model=AccuracyStats)
async def get_global_accuracy_stats(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get global accuracy statistics across all users."""
    service = ValidationService(db)
    stats = await service.get_accuracy_stats(category=category)
    return stats


# ==================== Categories ====================

@router.get("/categories")
async def get_benchmark_categories():
    """Get available benchmark categories."""
    return {
        "categories": [
            {
                "id": "election",
                "name": "Elections",
                "description": "Presidential, parliamentary, and local elections"
            },
            {
                "id": "product_launch",
                "name": "Product Launches",
                "description": "Consumer product launch predictions"
            },
            {
                "id": "campaign",
                "name": "Marketing Campaigns",
                "description": "Marketing and advertising campaign outcomes"
            },
            {
                "id": "survey",
                "name": "Survey Validation",
                "description": "Compare AI simulation vs real survey results"
            },
            {
                "id": "market_research",
                "name": "Market Research",
                "description": "Market trends and consumer behavior predictions"
            }
        ]
    }
