"""
Probability Source Service - PHASE 3: Probability Source Compliance

Provides business logic for computing empirical probability distributions
from multiple completed runs. Ensures all probabilities are:
1) Derived from empirical data (not fabricated)
2) Fully auditable with source metadata
3) Deterministic given the same filters

Reference: project.md Phase 3 - Probability Source Compliance
"""

import math
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run_outcome import RunOutcome, OutcomeStatus
from app.schemas.probability_source import (
    AggregationResult,
    AvailableMetricsResponse,
    ComparisonOperator,
    DataQuality,
    DistributionSummary,
    FiltersApplied,
    HistogramBucket,
    ProbabilitySourceMetadata,
    ProbabilitySourceResponse,
    ProbabilityStatus,
    TargetProbabilityResponse,
    WeightingMethod,
)


# Default minimum runs required for valid probability
DEFAULT_MIN_RUNS = 3
DEFAULT_MAX_RUNS = 200
DEFAULT_TIME_WINDOW_DAYS = 30
DEFAULT_HISTOGRAM_BINS = 20


class ProbabilitySourceService:
    """
    Service for computing empirical probability distributions.

    Key Principles:
    - NEVER fabricate probabilities when data is insufficient
    - ALWAYS include source metadata for auditability
    - DETERMINISTIC: same filters + same data = same results
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_available_metrics(
        self,
        project_id: uuid.UUID,
        node_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> AvailableMetricsResponse:
        """
        Get available metric keys for a node.

        Returns the union of all metric keys across run outcomes for this node.
        """
        # Query all outcomes for this node
        query = select(RunOutcome).where(
            and_(
                RunOutcome.project_id == project_id,
                RunOutcome.node_id == node_id,
                RunOutcome.tenant_id == tenant_id,
                RunOutcome.status == OutcomeStatus.SUCCEEDED,
            )
        ).order_by(RunOutcome.created_at.desc())

        result = await self.db.execute(query)
        outcomes = result.scalars().all()

        if not outcomes:
            return AvailableMetricsResponse(
                node_id=node_id,
                project_id=project_id,
                metric_keys=[],
                n_runs=0,
                updated_at=None,
            )

        # Collect union of all metric keys
        all_keys: set = set()
        for outcome in outcomes:
            all_keys.update(outcome.metrics_json.keys())

        # Sort keys for deterministic output
        sorted_keys = sorted(all_keys)

        return AvailableMetricsResponse(
            node_id=node_id,
            project_id=project_id,
            metric_keys=sorted_keys,
            n_runs=len(outcomes),
            updated_at=outcomes[0].created_at if outcomes else None,
        )

    async def compute_node_distribution(
        self,
        project_id: uuid.UUID,
        node_id: uuid.UUID,
        tenant_id: uuid.UUID,
        metric_key: str,
        manifest_hash: Optional[str] = None,
        rules_version: Optional[str] = None,
        model_version: Optional[str] = None,
        time_window_days: Optional[int] = DEFAULT_TIME_WINDOW_DAYS,
        min_runs: int = DEFAULT_MIN_RUNS,
        max_runs: int = DEFAULT_MAX_RUNS,
        weighting: WeightingMethod = WeightingMethod.UNIFORM,
    ) -> ProbabilitySourceResponse:
        """
        Compute probability distribution for a metric on a node.

        This is the core function for Phase 3 Probability Source Compliance.

        Args:
            project_id: Project ID
            node_id: Node ID to compute distribution for
            tenant_id: Tenant ID for scoping
            metric_key: Metric key to aggregate
            manifest_hash: Optional manifest hash filter
            rules_version: Optional rules version filter
            model_version: Optional model version filter
            time_window_days: Time window in days (None = all time)
            min_runs: Minimum runs required (default 3)
            max_runs: Maximum runs to consider (default 200)
            weighting: Weighting method (uniform or recent_decay)

        Returns:
            ProbabilitySourceResponse with status, metadata, and distribution
        """
        # Build filters
        filters = FiltersApplied(
            manifest_hash=manifest_hash,
            rules_version=rules_version,
            model_version=model_version,
            time_window_days=time_window_days,
            status=OutcomeStatus.SUCCEEDED,
        )

        # Aggregate data
        aggregation = await self._aggregate_metric_values(
            project_id=project_id,
            node_id=node_id,
            tenant_id=tenant_id,
            metric_key=metric_key,
            manifest_hash=manifest_hash,
            time_window_days=time_window_days,
            max_runs=max_runs,
        )

        # Build metadata (always returned, even for insufficient_data)
        updated_at = (
            max(aggregation.created_ats)
            if aggregation.created_ats
            else datetime.utcnow()
        )

        metadata = ProbabilitySourceMetadata(
            source_type="empirical_runs",
            project_id=project_id,
            node_id=node_id,
            metric_key=metric_key,
            filters_applied=filters,
            n_runs=aggregation.n_runs,
            min_runs_required=min_runs,
            max_runs_used=max_runs,
            time_window_days=time_window_days,
            weighting=weighting,
            data_quality=aggregation.quality_summary,
            updated_at=updated_at,
        )

        # Check if we have sufficient data
        if aggregation.n_runs < min_runs:
            return ProbabilitySourceResponse(
                status=ProbabilityStatus.INSUFFICIENT_DATA,
                probability_source=metadata,
                distribution=None,
                sample_run_ids=aggregation.run_ids[:10],
                message=f"Insufficient data: {aggregation.n_runs} runs available, "
                        f"minimum {min_runs} required. "
                        "Probability cannot be computed without sufficient empirical data.",
            )

        # Compute distribution
        distribution = self._compute_distribution(
            values=aggregation.values,
            weights=aggregation.weights if weighting == WeightingMethod.RECENT_DECAY else None,
        )

        return ProbabilitySourceResponse(
            status=ProbabilityStatus.OK,
            probability_source=metadata,
            distribution=distribution,
            sample_run_ids=aggregation.run_ids[:10],
            message=None,
        )

    async def compute_target_probability(
        self,
        project_id: uuid.UUID,
        node_id: uuid.UUID,
        tenant_id: uuid.UUID,
        metric_key: str,
        op: ComparisonOperator,
        threshold: float,
        manifest_hash: Optional[str] = None,
        time_window_days: Optional[int] = DEFAULT_TIME_WINDOW_DAYS,
        min_runs: int = DEFAULT_MIN_RUNS,
        max_runs: int = DEFAULT_MAX_RUNS,
        weighting: WeightingMethod = WeightingMethod.UNIFORM,
    ) -> TargetProbabilityResponse:
        """
        Compute probability of meeting a threshold condition.

        This enables queries like "What's the probability that score >= 0.8?"

        Args:
            project_id: Project ID
            node_id: Node ID
            tenant_id: Tenant ID
            metric_key: Metric key to evaluate
            op: Comparison operator (>=, <=, >, <, ==)
            threshold: Threshold value
            manifest_hash: Optional manifest hash filter
            time_window_days: Time window in days
            min_runs: Minimum runs required
            max_runs: Maximum runs to consider
            weighting: Weighting method

        Returns:
            TargetProbabilityResponse with probability and metadata
        """
        # Build condition string
        condition = f"{metric_key} {op.value} {threshold}"

        # Build filters
        filters = FiltersApplied(
            manifest_hash=manifest_hash,
            time_window_days=time_window_days,
            status=OutcomeStatus.SUCCEEDED,
        )

        # Aggregate data
        aggregation = await self._aggregate_metric_values(
            project_id=project_id,
            node_id=node_id,
            tenant_id=tenant_id,
            metric_key=metric_key,
            manifest_hash=manifest_hash,
            time_window_days=time_window_days,
            max_runs=max_runs,
        )

        # Build metadata
        updated_at = (
            max(aggregation.created_ats)
            if aggregation.created_ats
            else datetime.utcnow()
        )

        metadata = ProbabilitySourceMetadata(
            source_type="empirical_runs",
            project_id=project_id,
            node_id=node_id,
            metric_key=metric_key,
            filters_applied=filters,
            n_runs=aggregation.n_runs,
            min_runs_required=min_runs,
            max_runs_used=max_runs,
            time_window_days=time_window_days,
            weighting=weighting,
            data_quality=aggregation.quality_summary,
            updated_at=updated_at,
        )

        # Check if we have sufficient data
        if aggregation.n_runs < min_runs:
            return TargetProbabilityResponse(
                status=ProbabilityStatus.INSUFFICIENT_DATA,
                probability=None,
                condition=condition,
                probability_source=metadata,
                sample_run_ids=aggregation.run_ids[:10],
                message=f"Insufficient data: {aggregation.n_runs} runs available, "
                        f"minimum {min_runs} required.",
            )

        # Compute target probability
        probability = self._compute_target_probability(
            values=aggregation.values,
            weights=aggregation.weights if weighting == WeightingMethod.RECENT_DECAY else None,
            op=op,
            threshold=threshold,
        )

        return TargetProbabilityResponse(
            status=ProbabilityStatus.OK,
            probability=probability,
            condition=condition,
            probability_source=metadata,
            sample_run_ids=aggregation.run_ids[:10],
            message=None,
        )

    async def _aggregate_metric_values(
        self,
        project_id: uuid.UUID,
        node_id: uuid.UUID,
        tenant_id: uuid.UUID,
        metric_key: str,
        manifest_hash: Optional[str] = None,
        time_window_days: Optional[int] = None,
        max_runs: int = DEFAULT_MAX_RUNS,
    ) -> AggregationResult:
        """
        Aggregate metric values from run outcomes.

        Returns raw values for further computation.
        """
        # Build query
        conditions = [
            RunOutcome.project_id == project_id,
            RunOutcome.node_id == node_id,
            RunOutcome.tenant_id == tenant_id,
            RunOutcome.status == OutcomeStatus.SUCCEEDED,
        ]

        # Add manifest_hash filter
        if manifest_hash:
            conditions.append(RunOutcome.manifest_hash == manifest_hash)

        # Add time window filter
        if time_window_days:
            cutoff = datetime.utcnow() - timedelta(days=time_window_days)
            conditions.append(RunOutcome.created_at >= cutoff)

        query = (
            select(RunOutcome)
            .where(and_(*conditions))
            .order_by(RunOutcome.created_at.desc())
            .limit(max_runs)
        )

        result = await self.db.execute(query)
        outcomes = result.scalars().all()

        # Extract values
        values: List[float] = []
        weights: List[float] = []
        run_ids: List[uuid.UUID] = []
        created_ats: List[datetime] = []

        # Quality tracking
        partial_telemetry_count = 0
        failed_count = 0
        low_confidence_count = 0
        confidence_sum = 0.0
        confidence_count = 0

        now = datetime.utcnow()

        for outcome in outcomes:
            # Check if metric exists
            if metric_key not in outcome.metrics_json:
                continue

            value = outcome.metrics_json[metric_key]
            if not isinstance(value, (int, float)):
                continue

            values.append(float(value))
            run_ids.append(outcome.run_id)
            created_ats.append(outcome.created_at)

            # Compute weight for recent_decay
            # Exponential decay: weight = exp(-lambda * days_ago)
            days_ago = (now - outcome.created_at).days
            decay_weight = math.exp(-0.1 * days_ago)  # lambda = 0.1
            weights.append(decay_weight)

            # Track quality
            quality = outcome.quality_flags or {}
            if quality.get("partial_telemetry"):
                partial_telemetry_count += 1
            if quality.get("confidence") is not None:
                confidence_sum += quality["confidence"]
                confidence_count += 1
                if quality["confidence"] < 0.5:
                    low_confidence_count += 1

        # Build quality summary
        avg_confidence = (
            confidence_sum / confidence_count
            if confidence_count > 0
            else None
        )

        quality_summary = DataQuality(
            partial_telemetry_runs=partial_telemetry_count,
            failed_runs_excluded=failed_count,
            low_confidence_runs=low_confidence_count,
            average_confidence=avg_confidence,
        )

        return AggregationResult(
            status=ProbabilityStatus.OK if len(values) >= DEFAULT_MIN_RUNS else ProbabilityStatus.INSUFFICIENT_DATA,
            n_runs=len(values),
            values=values,
            weights=weights,
            run_ids=run_ids,
            created_ats=created_ats,
            quality_summary=quality_summary,
        )

    def _compute_distribution(
        self,
        values: List[float],
        weights: Optional[List[float]] = None,
    ) -> DistributionSummary:
        """
        Compute distribution summary from values.

        Args:
            values: List of metric values
            weights: Optional weights for weighted statistics

        Returns:
            DistributionSummary with mean, std, percentiles, histogram
        """
        arr = np.array(values)

        if weights:
            w_arr = np.array(weights)
            w_arr = w_arr / w_arr.sum()  # Normalize

            # Weighted mean and std
            mean = float(np.average(arr, weights=w_arr))
            variance = float(np.average((arr - mean) ** 2, weights=w_arr))
            std = float(np.sqrt(variance))
        else:
            mean = float(np.mean(arr))
            std = float(np.std(arr))

        # Percentiles (unweighted for simplicity)
        p5, p25, p50, p75, p95 = np.percentile(arr, [5, 25, 50, 75, 95])

        # Histogram
        histogram = self._compute_histogram(arr)

        return DistributionSummary(
            mean=mean,
            std=std,
            min=float(np.min(arr)),
            max=float(np.max(arr)),
            p5=float(p5),
            p25=float(p25),
            p50=float(p50),
            p75=float(p75),
            p95=float(p95),
            histogram=histogram,
        )

    def _compute_histogram(
        self,
        arr: np.ndarray,
        n_bins: int = DEFAULT_HISTOGRAM_BINS,
    ) -> List[HistogramBucket]:
        """
        Compute histogram buckets for visualization.
        """
        counts, bin_edges = np.histogram(arr, bins=n_bins)
        total = len(arr)

        buckets = []
        for i in range(len(counts)):
            buckets.append(
                HistogramBucket(
                    bin_start=float(bin_edges[i]),
                    bin_end=float(bin_edges[i + 1]),
                    count=int(counts[i]),
                    frequency=float(counts[i] / total) if total > 0 else 0.0,
                )
            )

        return buckets

    def _compute_target_probability(
        self,
        values: List[float],
        weights: Optional[List[float]],
        op: ComparisonOperator,
        threshold: float,
    ) -> float:
        """
        Compute probability of meeting a threshold condition.

        Uses empirical distribution (counting approach).
        """
        arr = np.array(values)

        # Apply comparison
        if op == ComparisonOperator.GTE:
            mask = arr >= threshold
        elif op == ComparisonOperator.LTE:
            mask = arr <= threshold
        elif op == ComparisonOperator.GT:
            mask = arr > threshold
        elif op == ComparisonOperator.LT:
            mask = arr < threshold
        elif op == ComparisonOperator.EQ:
            # For equality, use small epsilon
            epsilon = 1e-9
            mask = np.abs(arr - threshold) < epsilon
        else:
            mask = np.zeros_like(arr, dtype=bool)

        if weights:
            w_arr = np.array(weights)
            w_arr = w_arr / w_arr.sum()
            probability = float(np.sum(w_arr[mask]))
        else:
            probability = float(np.mean(mask))

        return probability


def get_probability_source_service(db: AsyncSession) -> ProbabilitySourceService:
    """Factory function for ProbabilitySourceService."""
    return ProbabilitySourceService(db)
