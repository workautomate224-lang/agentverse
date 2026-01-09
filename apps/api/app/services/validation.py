"""
Validation Service
Manages benchmarks, validates predictions against real outcomes,
and tracks accuracy over time.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Benchmark, ValidationRecord, Product, ProductResult


logger = logging.getLogger(__name__)


# Pydantic Models for API
class BenchmarkCreate(BaseModel):
    """Create a new benchmark."""
    name: str
    description: Optional[str] = None
    category: str  # election, product_launch, campaign, survey, etc.
    event_date: Optional[datetime] = None
    region: str
    country: Optional[str] = None
    actual_outcome: dict
    source: str
    source_url: Optional[str] = None
    is_public: bool = True


class BenchmarkResponse(BaseModel):
    """Benchmark response model."""
    id: UUID
    name: str
    description: Optional[str]
    category: str
    event_date: Optional[datetime]
    region: str
    country: Optional[str]
    actual_outcome: dict
    source: str
    source_url: Optional[str]
    verification_status: str
    is_public: bool
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ValidationCreate(BaseModel):
    """Create a validation record."""
    product_id: UUID
    benchmark_id: UUID


class ValidationResponse(BaseModel):
    """Validation response model."""
    id: UUID
    product_id: UUID
    benchmark_id: UUID
    predicted_outcome: dict
    actual_outcome: dict
    accuracy_score: float
    deviation: float
    within_confidence_interval: bool
    analysis: Optional[dict]
    validated_at: datetime

    class Config:
        from_attributes = True


class AccuracyStats(BaseModel):
    """Accuracy statistics model."""
    total_validations: int
    average_accuracy: float
    median_accuracy: float
    accuracy_by_category: dict[str, float]
    accuracy_trend: list[dict]  # [{date, accuracy}]
    within_ci_rate: float
    best_performing_category: Optional[str]
    areas_for_improvement: list[str]


class ValidationService:
    """Service for managing validation and accuracy tracking."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== Benchmark Management ====================

    async def create_benchmark(
        self,
        data: BenchmarkCreate,
        user_id: Optional[UUID] = None
    ) -> Benchmark:
        """Create a new benchmark record."""
        benchmark = Benchmark(
            id=uuid4(),
            user_id=user_id,
            name=data.name,
            description=data.description,
            category=data.category,
            event_date=data.event_date,
            region=data.region,
            country=data.country,
            actual_outcome=data.actual_outcome,
            source=data.source,
            source_url=data.source_url,
            verification_status="pending",
            is_public=data.is_public,
            usage_count=0,
        )
        self.session.add(benchmark)
        await self.session.flush()
        logger.info(f"Created benchmark: {benchmark.name} ({benchmark.id})")
        return benchmark

    async def get_benchmark(self, benchmark_id: UUID) -> Optional[Benchmark]:
        """Get a benchmark by ID."""
        result = await self.session.execute(
            select(Benchmark).where(Benchmark.id == benchmark_id)
        )
        return result.scalar_one_or_none()

    async def list_benchmarks(
        self,
        category: Optional[str] = None,
        region: Optional[str] = None,
        is_public: Optional[bool] = None,
        user_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[Benchmark]:
        """List benchmarks with filtering."""
        query = select(Benchmark)

        conditions = []
        if category:
            conditions.append(Benchmark.category == category)
        if region:
            conditions.append(Benchmark.region == region)
        if is_public is not None:
            conditions.append(Benchmark.is_public == is_public)
        if user_id:
            conditions.append(Benchmark.user_id == user_id)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(Benchmark.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_benchmark_verification(
        self,
        benchmark_id: UUID,
        status: str
    ) -> Optional[Benchmark]:
        """Update benchmark verification status."""
        benchmark = await self.get_benchmark(benchmark_id)
        if benchmark:
            benchmark.verification_status = status
            await self.session.flush()
        return benchmark

    async def delete_benchmark(self, benchmark_id: UUID) -> bool:
        """Delete a benchmark."""
        benchmark = await self.get_benchmark(benchmark_id)
        if benchmark:
            await self.session.delete(benchmark)
            await self.session.flush()
            return True
        return False

    # ==================== Validation ====================

    async def validate_prediction(
        self,
        product_id: UUID,
        benchmark_id: UUID
    ) -> Optional[ValidationRecord]:
        """
        Validate a product's prediction against a benchmark.
        Calculates accuracy metrics and creates a validation record.
        """
        # Get product and its results
        product_result = await self.session.execute(
            select(ProductResult).where(ProductResult.product_id == product_id)
        )
        result = product_result.scalar_one_or_none()
        if not result:
            logger.warning(f"No results found for product {product_id}")
            return None

        # Get benchmark
        benchmark = await self.get_benchmark(benchmark_id)
        if not benchmark:
            logger.warning(f"Benchmark not found: {benchmark_id}")
            return None

        # Extract predictions
        predictions = result.predictions or {}
        primary_prediction = predictions.get("primary_prediction", {})
        predicted_value = primary_prediction.get("value", 0)
        confidence_interval = primary_prediction.get("confidence_interval", [0, 0])

        # Extract actual outcome
        actual_outcome = benchmark.actual_outcome
        actual_value = actual_outcome.get("value", 0)

        # Calculate accuracy metrics
        deviation = abs(predicted_value - actual_value)
        accuracy_score = max(0, 1 - deviation)  # Simple accuracy: 1 - deviation

        # Check if actual is within confidence interval
        within_ci = confidence_interval[0] <= actual_value <= confidence_interval[1]

        # Detailed analysis
        analysis = self._generate_validation_analysis(
            predicted_value=predicted_value,
            actual_value=actual_value,
            confidence_interval=confidence_interval,
            predictions=predictions,
            actual_outcome=actual_outcome
        )

        # Create validation record
        validation = ValidationRecord(
            id=uuid4(),
            product_id=product_id,
            benchmark_id=benchmark_id,
            predicted_outcome={
                "value": predicted_value,
                "confidence_interval": confidence_interval,
                "full_predictions": predictions
            },
            actual_outcome=actual_outcome,
            accuracy_score=accuracy_score,
            deviation=deviation,
            within_confidence_interval=within_ci,
            analysis=analysis,
        )
        self.session.add(validation)

        # Increment benchmark usage
        benchmark.usage_count += 1

        await self.session.flush()
        logger.info(
            f"Validated product {product_id} against benchmark {benchmark_id}: "
            f"Accuracy={accuracy_score:.2%}, Within CI={within_ci}"
        )
        return validation

    def _generate_validation_analysis(
        self,
        predicted_value: float,
        actual_value: float,
        confidence_interval: list,
        predictions: dict,
        actual_outcome: dict
    ) -> dict:
        """Generate detailed validation analysis."""
        analysis = {
            "prediction_summary": {
                "predicted": predicted_value,
                "actual": actual_value,
                "difference": actual_value - predicted_value,
                "absolute_error": abs(predicted_value - actual_value),
                "percentage_error": abs(predicted_value - actual_value) / actual_value * 100 if actual_value else 0
            },
            "confidence_interval_analysis": {
                "lower_bound": confidence_interval[0] if len(confidence_interval) > 0 else 0,
                "upper_bound": confidence_interval[1] if len(confidence_interval) > 1 else 0,
                "actual_within_bounds": confidence_interval[0] <= actual_value <= confidence_interval[1] if len(confidence_interval) >= 2 else False,
                "ci_width": confidence_interval[1] - confidence_interval[0] if len(confidence_interval) >= 2 else 0
            },
            "lessons_learned": [],
            "recommendations": []
        }

        # Generate lessons and recommendations
        error_pct = analysis["prediction_summary"]["percentage_error"]
        if error_pct < 5:
            analysis["lessons_learned"].append("Prediction was highly accurate")
        elif error_pct < 10:
            analysis["lessons_learned"].append("Prediction was reasonably accurate")
        else:
            analysis["lessons_learned"].append("Significant deviation from actual outcome")
            analysis["recommendations"].append("Consider increasing sample size")
            analysis["recommendations"].append("Review demographic coverage")

        if not analysis["confidence_interval_analysis"]["actual_within_bounds"]:
            analysis["recommendations"].append("Confidence interval methodology may need adjustment")

        return analysis

    async def get_validation(self, validation_id: UUID) -> Optional[ValidationRecord]:
        """Get a validation record by ID."""
        result = await self.session.execute(
            select(ValidationRecord).where(ValidationRecord.id == validation_id)
        )
        return result.scalar_one_or_none()

    async def list_validations(
        self,
        product_id: Optional[UUID] = None,
        benchmark_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[ValidationRecord]:
        """List validation records with filtering."""
        query = select(ValidationRecord)

        conditions = []
        if product_id:
            conditions.append(ValidationRecord.product_id == product_id)
        if benchmark_id:
            conditions.append(ValidationRecord.benchmark_id == benchmark_id)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(ValidationRecord.validated_at)).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ==================== Accuracy Statistics ====================

    async def get_accuracy_stats(
        self,
        user_id: Optional[UUID] = None,
        category: Optional[str] = None
    ) -> AccuracyStats:
        """Get comprehensive accuracy statistics."""
        # Base query for validations
        query = select(ValidationRecord)
        if user_id:
            query = query.join(Product).where(Product.user_id == user_id)

        result = await self.session.execute(query)
        validations = list(result.scalars().all())

        if not validations:
            return AccuracyStats(
                total_validations=0,
                average_accuracy=0.0,
                median_accuracy=0.0,
                accuracy_by_category={},
                accuracy_trend=[],
                within_ci_rate=0.0,
                best_performing_category=None,
                areas_for_improvement=[]
            )

        # Calculate stats
        accuracies = [v.accuracy_score for v in validations]
        total = len(validations)
        avg_accuracy = sum(accuracies) / total
        sorted_accuracies = sorted(accuracies)
        median_accuracy = sorted_accuracies[total // 2]
        within_ci_count = sum(1 for v in validations if v.within_confidence_interval)

        # Accuracy by category (need to join with benchmark)
        accuracy_by_category = {}
        for v in validations:
            benchmark = await self.get_benchmark(v.benchmark_id)
            if benchmark:
                cat = benchmark.category
                if cat not in accuracy_by_category:
                    accuracy_by_category[cat] = []
                accuracy_by_category[cat].append(v.accuracy_score)

        category_averages = {
            cat: sum(scores) / len(scores)
            for cat, scores in accuracy_by_category.items()
        }

        best_category = max(category_averages, key=category_averages.get) if category_averages else None

        # Accuracy trend (by month)
        trend_data = {}
        for v in validations:
            month_key = v.validated_at.strftime("%Y-%m")
            if month_key not in trend_data:
                trend_data[month_key] = []
            trend_data[month_key].append(v.accuracy_score)

        accuracy_trend = [
            {"date": date, "accuracy": sum(scores) / len(scores)}
            for date, scores in sorted(trend_data.items())
        ]

        # Areas for improvement
        areas = []
        if avg_accuracy < 0.8:
            areas.append("Overall prediction accuracy below 80%")
        if within_ci_count / total < 0.9:
            areas.append("Confidence interval calibration needs improvement")
        for cat, avg in category_averages.items():
            if avg < 0.7:
                areas.append(f"{cat} category predictions need improvement")

        return AccuracyStats(
            total_validations=total,
            average_accuracy=avg_accuracy,
            median_accuracy=median_accuracy,
            accuracy_by_category=category_averages,
            accuracy_trend=accuracy_trend,
            within_ci_rate=within_ci_count / total if total > 0 else 0,
            best_performing_category=best_category,
            areas_for_improvement=areas
        )

    # ==================== Seed Historical Data ====================

    async def seed_election_benchmarks(self) -> list[Benchmark]:
        """Seed historical election data for validation."""
        election_data = [
            {
                "name": "2020 US Presidential Election",
                "description": "Joe Biden vs Donald Trump presidential election",
                "category": "election",
                "event_date": datetime(2020, 11, 3, tzinfo=timezone.utc),
                "region": "us",
                "country": "United States",
                "actual_outcome": {
                    "result": "Joe Biden (Democrat) won",
                    "value": 0.513,  # 51.3% popular vote
                    "detailed_breakdown": {
                        "biden_votes": 81283501,
                        "trump_votes": 74223975,
                        "biden_percentage": 51.31,
                        "trump_percentage": 46.86,
                        "electoral_college": {"biden": 306, "trump": 232}
                    }
                },
                "source": "Federal Election Commission",
                "source_url": "https://www.fec.gov/resources/cms-content/documents/federalelections2020.pdf",
            },
            {
                "name": "2016 US Presidential Election",
                "description": "Hillary Clinton vs Donald Trump presidential election",
                "category": "election",
                "event_date": datetime(2016, 11, 8, tzinfo=timezone.utc),
                "region": "us",
                "country": "United States",
                "actual_outcome": {
                    "result": "Donald Trump (Republican) won Electoral College",
                    "value": 0.461,  # Trump's popular vote (lost popular, won EC)
                    "detailed_breakdown": {
                        "trump_votes": 62984828,
                        "clinton_votes": 65853514,
                        "trump_percentage": 46.09,
                        "clinton_percentage": 48.18,
                        "electoral_college": {"trump": 304, "clinton": 227}
                    }
                },
                "source": "Federal Election Commission",
                "source_url": "https://www.fec.gov/resources/cms-content/documents/federalelections2016.pdf",
            },
            {
                "name": "2024 US Presidential Election",
                "description": "Kamala Harris vs Donald Trump presidential election",
                "category": "election",
                "event_date": datetime(2024, 11, 5, tzinfo=timezone.utc),
                "region": "us",
                "country": "United States",
                "actual_outcome": {
                    "result": "Donald Trump (Republican) won",
                    "value": 0.498,  # Approximate based on current counts
                    "detailed_breakdown": {
                        "trump_votes": 77303520,
                        "harris_votes": 75014912,
                        "trump_percentage": 49.8,
                        "harris_percentage": 48.3,
                        "electoral_college": {"trump": 312, "harris": 226}
                    }
                },
                "source": "Associated Press",
                "source_url": "https://apnews.com/projects/election-results-2024/",
            },
            {
                "name": "Brexit Referendum 2016",
                "description": "UK European Union membership referendum",
                "category": "election",
                "event_date": datetime(2016, 6, 23, tzinfo=timezone.utc),
                "region": "europe",
                "country": "United Kingdom",
                "actual_outcome": {
                    "result": "Leave won",
                    "value": 0.519,  # 51.9% voted Leave
                    "detailed_breakdown": {
                        "leave_votes": 17410742,
                        "remain_votes": 16141241,
                        "leave_percentage": 51.89,
                        "remain_percentage": 48.11,
                        "turnout": 72.21
                    }
                },
                "source": "UK Electoral Commission",
                "source_url": "https://www.electoralcommission.org.uk/who-we-are-and-what-we-do/elections-and-referendums/past-elections-and-referendums/eu-referendum",
            }
        ]

        benchmarks = []
        for data in election_data:
            # Check if already exists
            existing = await self.session.execute(
                select(Benchmark).where(Benchmark.name == data["name"])
            )
            if existing.scalar_one_or_none():
                continue

            benchmark = Benchmark(
                id=uuid4(),
                user_id=None,
                name=data["name"],
                description=data["description"],
                category=data["category"],
                event_date=data["event_date"],
                region=data["region"],
                country=data["country"],
                actual_outcome=data["actual_outcome"],
                source=data["source"],
                source_url=data["source_url"],
                verification_status="verified",
                is_public=True,
                usage_count=0,
            )
            self.session.add(benchmark)
            benchmarks.append(benchmark)

        await self.session.flush()
        logger.info(f"Seeded {len(benchmarks)} election benchmarks")
        return benchmarks
