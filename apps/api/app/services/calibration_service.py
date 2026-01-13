"""
Calibration Service - PHASE 4: Calibration Minimal Closed Loop

Business logic for:
- Ground truth dataset management
- Calibration job orchestration
- Deterministic calibration algorithm

The calibration algorithm is deterministic:
- Same config + same data = same results
- No LLM in the loop (C5 compliance)
- All results auditable (C4 compliance)

Reference: project.md Phase 4 - Calibration Lab Backend
"""

import math
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calibration import (
    CalibrationIteration,
    CalibrationJob,
    CalibrationJobStatus,
    GroundTruthDataset,
    GroundTruthLabel,
)
from app.models.run_outcome import OutcomeStatus, RunOutcome
from app.schemas.calibration import (
    BulkUpsertLabelsRequest,
    BulkUpsertLabelsResponse,
    CalibrationBin,
    CalibrationConfig,
    CalibrationMetrics,
    CalibrationResultResponse,
    CalibrationSample,
    ComparisonOperator,
    GroundTruthDatasetCreate,
    GroundTruthLabelInput,
    WeightingMethod,
)


# Default bin counts to try
DEFAULT_BIN_COUNTS = [5, 10, 15, 20, 25, 30]
MIN_SAMPLES_PER_BIN = 2
MIN_TOTAL_SAMPLES = 10


class CalibrationService:
    """
    Service for calibration operations.

    Provides:
    - Ground truth dataset and label management
    - Calibration job lifecycle management
    - Deterministic calibration algorithm
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Ground Truth Dataset Operations
    # =========================================================================

    async def create_dataset(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        data: GroundTruthDatasetCreate,
    ) -> GroundTruthDataset:
        """Create a new ground truth dataset."""
        dataset = GroundTruthDataset(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            name=data.name,
            description=data.description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(dataset)
        await self.db.flush()
        return dataset

    async def get_dataset(
        self,
        dataset_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[GroundTruthDataset]:
        """Get a dataset by ID."""
        query = select(GroundTruthDataset).where(
            GroundTruthDataset.id == dataset_id,
            GroundTruthDataset.tenant_id == tenant_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_datasets(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Tuple[List[GroundTruthDataset], int]:
        """List all datasets for a project."""
        query = (
            select(GroundTruthDataset)
            .where(
                GroundTruthDataset.tenant_id == tenant_id,
                GroundTruthDataset.project_id == project_id,
            )
            .order_by(GroundTruthDataset.created_at.desc())
        )
        result = await self.db.execute(query)
        datasets = list(result.scalars().all())
        return datasets, len(datasets)

    async def get_dataset_label_count(
        self,
        dataset_id: uuid.UUID,
    ) -> int:
        """Get count of labels in a dataset."""
        query = select(func.count(GroundTruthLabel.id)).where(
            GroundTruthLabel.dataset_id == dataset_id
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    # =========================================================================
    # Ground Truth Label Operations
    # =========================================================================

    async def bulk_upsert_labels(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        dataset_id: uuid.UUID,
        request: BulkUpsertLabelsRequest,
    ) -> BulkUpsertLabelsResponse:
        """
        Bulk upsert ground truth labels.

        Uses PostgreSQL's ON CONFLICT for idempotent upserts.
        """
        created = 0
        updated = 0
        errors = []

        for label_input in request.labels:
            try:
                # Build values dict
                values = {
                    "id": uuid.uuid4(),
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "dataset_id": dataset_id,
                    "node_id": label_input.node_id,
                    "run_id": label_input.run_id,
                    "label": label_input.label,
                    "notes": label_input.notes,
                    "json_meta": label_input.json_meta or {},
                    "created_at": datetime.utcnow(),
                }

                # Upsert using PostgreSQL INSERT ON CONFLICT
                stmt = insert(GroundTruthLabel).values(**values)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_ground_truth_labels_dataset_run",
                    set_={
                        "label": stmt.excluded.label,
                        "notes": stmt.excluded.notes,
                        "json_meta": stmt.excluded.json_meta,
                    },
                )

                result = await self.db.execute(stmt)

                # Check if it was insert or update
                # (This is approximate - PostgreSQL doesn't easily tell us)
                if result.rowcount > 0:
                    # We'll count as created (accurate on first insert)
                    created += 1

            except Exception as e:
                errors.append({
                    "run_id": str(label_input.run_id),
                    "error": str(e),
                })

        await self.db.flush()

        return BulkUpsertLabelsResponse(
            created=created,
            updated=updated,
            errors=errors,
        )

    async def list_labels(
        self,
        tenant_id: uuid.UUID,
        dataset_id: uuid.UUID,
        node_id: Optional[uuid.UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[GroundTruthLabel], int]:
        """List labels for a dataset."""
        conditions = [
            GroundTruthLabel.tenant_id == tenant_id,
            GroundTruthLabel.dataset_id == dataset_id,
        ]
        if node_id:
            conditions.append(GroundTruthLabel.node_id == node_id)

        # Count total
        count_query = select(func.count(GroundTruthLabel.id)).where(
            and_(*conditions)
        )
        total = (await self.db.execute(count_query)).scalar() or 0

        # Get labels
        query = (
            select(GroundTruthLabel)
            .where(and_(*conditions))
            .order_by(GroundTruthLabel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        labels = list(result.scalars().all())

        return labels, total

    # =========================================================================
    # Calibration Job Operations
    # =========================================================================

    async def create_job(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        config: CalibrationConfig,
        user_id: Optional[uuid.UUID] = None,
    ) -> CalibrationJob:
        """Create a new calibration job."""
        # Calculate total iterations based on bin counts
        bin_counts = self._get_bin_counts(config.max_iterations)
        total_iterations = len(bin_counts)

        job = CalibrationJob(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            node_id=config.node_id,
            dataset_id=config.dataset_id,
            status=CalibrationJobStatus.QUEUED.value,
            config_json={
                "target_accuracy": config.target_accuracy,
                "max_iterations": config.max_iterations,
                "metric_key": config.metric_key,
                "op": config.op.value if config.op else None,
                "threshold": config.threshold,
                "time_window_days": config.time_window_days,
                "weighting": config.weighting.value,
                "seed": config.seed,
            },
            progress=0,
            total_iterations=total_iterations,
            created_at=datetime.utcnow(),
            created_by_user_id=user_id,
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_job(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[CalibrationJob]:
        """Get a job by ID."""
        query = select(CalibrationJob).where(
            CalibrationJob.id == job_id,
            CalibrationJob.tenant_id == tenant_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_job_status(
        self,
        job_id: uuid.UUID,
        status: CalibrationJobStatus,
        error_message: Optional[str] = None,
        result_json: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update job status."""
        update_values = {"status": status.value}

        if status == CalibrationJobStatus.RUNNING:
            update_values["started_at"] = datetime.utcnow()
        elif status in (
            CalibrationJobStatus.SUCCEEDED,
            CalibrationJobStatus.FAILED,
            CalibrationJobStatus.CANCELED,
        ):
            update_values["finished_at"] = datetime.utcnow()

        if error_message:
            update_values["error_message"] = error_message
        if result_json:
            update_values["result_json"] = result_json

        await self.db.execute(
            update(CalibrationJob)
            .where(CalibrationJob.id == job_id)
            .values(**update_values)
        )
        await self.db.flush()

    async def update_job_progress(
        self,
        job_id: uuid.UUID,
        progress: int,
    ) -> None:
        """Update job progress."""
        await self.db.execute(
            update(CalibrationJob)
            .where(CalibrationJob.id == job_id)
            .values(progress=progress)
        )
        await self.db.flush()

    async def cancel_job(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Cancel a job if it's not already in a terminal state."""
        job = await self.get_job(job_id, tenant_id)
        if not job or job.is_terminal():
            return False

        await self.update_job_status(
            job_id,
            CalibrationJobStatus.CANCELED,
            error_message="Canceled by user",
        )
        return True

    async def create_iteration(
        self,
        job_id: uuid.UUID,
        iter_index: int,
        params_json: Dict[str, Any],
        metrics_json: Dict[str, Any],
        mapping_json: Optional[Dict[str, Any]] = None,
    ) -> CalibrationIteration:
        """Create a calibration iteration record."""
        iteration = CalibrationIteration(
            id=uuid.uuid4(),
            job_id=job_id,
            iter_index=iter_index,
            params_json=params_json,
            metrics_json=metrics_json,
            mapping_json=mapping_json,
            created_at=datetime.utcnow(),
        )
        self.db.add(iteration)
        await self.db.flush()
        return iteration

    async def get_job_iterations(
        self,
        job_id: uuid.UUID,
    ) -> List[CalibrationIteration]:
        """Get all iterations for a job."""
        query = (
            select(CalibrationIteration)
            .where(CalibrationIteration.job_id == job_id)
            .order_by(CalibrationIteration.iter_index)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # Calibration Algorithm
    # =========================================================================

    async def run_calibration(
        self,
        job: CalibrationJob,
    ) -> CalibrationResultResponse:
        """
        Run the calibration algorithm.

        This is the core calibration logic that:
        1. Loads samples (run outcomes + ground truth labels)
        2. Iterates through bin counts
        3. Computes calibration mapping + metrics for each
        4. Early stops if target accuracy reached
        5. Returns best result

        DETERMINISTIC: Same config + same data = same results.
        """
        config = CalibrationConfig(
            node_id=job.node_id,
            dataset_id=job.dataset_id,
            target_accuracy=job.config_json.get("target_accuracy", 0.85),
            max_iterations=job.config_json.get("max_iterations", 10),
            metric_key=job.config_json.get("metric_key", "outcome_value"),
            op=ComparisonOperator(job.config_json["op"]) if job.config_json.get("op") else None,
            threshold=job.config_json.get("threshold"),
            time_window_days=job.config_json.get("time_window_days"),
            weighting=WeightingMethod(job.config_json.get("weighting", "uniform")),
            seed=job.config_json.get("seed"),
        )

        # Update job to running
        await self.update_job_status(job.id, CalibrationJobStatus.RUNNING)

        # Load samples
        samples, audit = await self._load_calibration_samples(
            tenant_id=job.tenant_id,
            project_id=job.project_id,
            node_id=config.node_id,
            dataset_id=config.dataset_id,
            metric_key=config.metric_key,
            time_window_days=config.time_window_days,
            weighting=config.weighting,
        )

        # Check for insufficient data
        if len(samples) < MIN_TOTAL_SAMPLES:
            result = CalibrationResultResponse(
                job_id=job.id,
                status=CalibrationJobStatus.FAILED,
                error_message=f"Insufficient data: {len(samples)} samples found, "
                              f"minimum {MIN_TOTAL_SAMPLES} required.",
                audit=audit,
            )
            await self.update_job_status(
                job.id,
                CalibrationJobStatus.FAILED,
                error_message=result.error_message,
                result_json={"audit": audit},
            )
            return result

        # Set seed for reproducibility
        if config.seed is not None:
            np.random.seed(config.seed)

        # Get bin counts to try
        bin_counts = self._get_bin_counts(config.max_iterations)

        # Track best result
        best_mapping = None
        best_metrics = None
        best_bin_count = None
        best_iteration = None

        # Iterate through bin counts
        for i, bin_count in enumerate(bin_counts):
            # Check if job was canceled
            job = await self.get_job(job.id, job.tenant_id)
            if job and job.status == CalibrationJobStatus.CANCELED.value:
                return CalibrationResultResponse(
                    job_id=job.id,
                    status=CalibrationJobStatus.CANCELED,
                    error_message="Job was canceled",
                )

            # Compute calibration for this bin count
            mapping, metrics = self._compute_calibration(
                samples=samples,
                bin_count=bin_count,
                op=config.op,
                threshold=config.threshold,
            )

            # Store iteration
            await self.create_iteration(
                job_id=job.id,
                iter_index=i,
                params_json={"bin_count": bin_count},
                metrics_json={
                    "accuracy": metrics.accuracy,
                    "brier_score": metrics.brier_score,
                    "ece": metrics.ece,
                    "n_samples": metrics.n_samples,
                },
                mapping_json={
                    "bins": [
                        {
                            "bin_start": b.bin_start,
                            "bin_end": b.bin_end,
                            "calibrated_prob": b.calibrated_prob,
                            "n_samples": b.n_samples,
                            "empirical_rate": b.empirical_rate,
                        }
                        for b in mapping
                    ]
                },
            )

            # Update progress
            await self.update_job_progress(job.id, i + 1)

            # Track best
            if best_metrics is None or metrics.accuracy > best_metrics.accuracy:
                best_mapping = mapping
                best_metrics = metrics
                best_bin_count = bin_count
                best_iteration = i

            # Early stop if target accuracy reached
            if metrics.accuracy >= config.target_accuracy:
                break

        # Build result
        sample_run_ids = [s.run_id for s in samples[:50]]  # First 50 for audit

        result_json = {
            "best_mapping": [
                {
                    "bin_start": b.bin_start,
                    "bin_end": b.bin_end,
                    "calibrated_prob": b.calibrated_prob,
                    "n_samples": b.n_samples,
                    "empirical_rate": b.empirical_rate,
                }
                for b in best_mapping
            ] if best_mapping else None,
            "best_bin_count": best_bin_count,
            "best_iteration": best_iteration,
            "metrics": {
                "accuracy": best_metrics.accuracy,
                "brier_score": best_metrics.brier_score,
                "ece": best_metrics.ece,
                "n_samples": best_metrics.n_samples,
            } if best_metrics else None,
            "n_samples": len(samples),
            "selected_run_ids": [str(rid) for rid in sample_run_ids],
            "audit": audit,
        }

        # Update job with final result
        await self.update_job_status(
            job.id,
            CalibrationJobStatus.SUCCEEDED,
            result_json=result_json,
        )

        # Compute duration
        job = await self.get_job(job.id, job.tenant_id)
        duration = None
        if job and job.started_at and job.finished_at:
            duration = (job.finished_at - job.started_at).total_seconds()

        return CalibrationResultResponse(
            job_id=job.id,
            status=CalibrationJobStatus.SUCCEEDED,
            best_mapping=best_mapping,
            best_bin_count=best_bin_count,
            best_iteration=best_iteration,
            metrics=best_metrics,
            audit=audit,
            selected_run_ids=sample_run_ids,
            started_at=job.started_at,
            finished_at=job.finished_at,
            duration_seconds=duration,
        )

    async def _load_calibration_samples(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        node_id: uuid.UUID,
        dataset_id: uuid.UUID,
        metric_key: str,
        time_window_days: Optional[int] = None,
        weighting: WeightingMethod = WeightingMethod.UNIFORM,
    ) -> Tuple[List[CalibrationSample], Dict[str, Any]]:
        """
        Load calibration samples by joining run outcomes with ground truth labels.

        Returns samples and audit information.
        """
        # Build conditions for run outcomes
        outcome_conditions = [
            RunOutcome.tenant_id == tenant_id,
            RunOutcome.project_id == project_id,
            RunOutcome.node_id == node_id,
            RunOutcome.status == OutcomeStatus.SUCCEEDED,
        ]

        if time_window_days:
            cutoff = datetime.utcnow() - timedelta(days=time_window_days)
            outcome_conditions.append(RunOutcome.created_at >= cutoff)

        # Query run outcomes
        outcome_query = select(RunOutcome).where(and_(*outcome_conditions))
        outcome_result = await self.db.execute(outcome_query)
        outcomes = {o.run_id: o for o in outcome_result.scalars().all()}

        # Query ground truth labels
        label_query = select(GroundTruthLabel).where(
            GroundTruthLabel.tenant_id == tenant_id,
            GroundTruthLabel.dataset_id == dataset_id,
            GroundTruthLabel.node_id == node_id,
        )
        label_result = await self.db.execute(label_query)
        labels = {l.run_id: l for l in label_result.scalars().all()}

        # Build samples by matching outcomes with labels
        samples = []
        runs_matched = 0
        runs_missing_labels = 0
        runs_missing_metric = 0
        now = datetime.utcnow()

        for run_id, outcome in outcomes.items():
            # Check if we have a label
            if run_id not in labels:
                runs_missing_labels += 1
                continue

            # Check if metric exists
            if metric_key not in outcome.metrics_json:
                runs_missing_metric += 1
                continue

            predicted_value = outcome.metrics_json[metric_key]
            if not isinstance(predicted_value, (int, float)):
                runs_missing_metric += 1
                continue

            label = labels[run_id]

            # Compute weight
            if weighting == WeightingMethod.RECENT_DECAY:
                days_ago = (now - outcome.created_at).days
                weight = math.exp(-0.1 * days_ago)
            else:
                weight = 1.0

            samples.append(CalibrationSample(
                run_id=run_id,
                predicted_value=float(predicted_value),
                label=label.label,
                weight=weight,
            ))
            runs_matched += 1

        # Sort by predicted value for consistent binning
        samples.sort(key=lambda s: s.predicted_value)

        audit = {
            "total_outcomes": len(outcomes),
            "total_labels": len(labels),
            "runs_matched": runs_matched,
            "runs_missing_labels": runs_missing_labels,
            "runs_missing_metric": runs_missing_metric,
        }

        return samples, audit

    def _get_bin_counts(self, max_iterations: int) -> List[int]:
        """Get list of bin counts to try based on max iterations."""
        # Use default bin counts up to max_iterations
        return DEFAULT_BIN_COUNTS[:max_iterations]

    def _compute_calibration(
        self,
        samples: List[CalibrationSample],
        bin_count: int,
        op: Optional[ComparisonOperator] = None,
        threshold: Optional[float] = None,
    ) -> Tuple[List[CalibrationBin], CalibrationMetrics]:
        """
        Compute calibration mapping and metrics for a given bin count.

        This is a deterministic binning algorithm:
        1. Divide predicted values into equal-width bins
        2. Compute empirical success rate in each bin
        3. Use empirical rate as calibrated probability
        4. Compute metrics (accuracy, Brier, ECE)
        """
        if not samples:
            return [], CalibrationMetrics(
                accuracy=0.0,
                brier_score=1.0,
                ece=1.0,
                n_samples=0,
            )

        # Extract values
        pred_values = np.array([s.predicted_value for s in samples])
        labels = np.array([s.label for s in samples])
        weights = np.array([s.weight for s in samples])

        # Normalize weights
        weights = weights / weights.sum()

        # Compute bin edges
        min_val = pred_values.min()
        max_val = pred_values.max()

        # Handle edge case where all values are the same
        if min_val == max_val:
            bin_edges = [min_val - 0.001, max_val + 0.001]
            bin_count = 1
        else:
            # Add small epsilon to include max value
            bin_edges = np.linspace(min_val, max_val + 1e-9, bin_count + 1)

        # Assign samples to bins
        bin_indices = np.digitize(pred_values, bin_edges[1:-1])

        # Compute per-bin statistics
        mapping = []
        calibrated_probs = np.zeros(len(samples))

        for bin_idx in range(bin_count):
            mask = bin_indices == bin_idx
            n_in_bin = mask.sum()

            bin_start = float(bin_edges[bin_idx])
            bin_end = float(bin_edges[bin_idx + 1])

            if n_in_bin < MIN_SAMPLES_PER_BIN:
                # Not enough samples - use overall rate
                empirical_rate = float(labels.mean())
            else:
                # Compute weighted empirical rate
                bin_weights = weights[mask]
                bin_labels = labels[mask]
                empirical_rate = float((bin_weights * bin_labels).sum() / bin_weights.sum())

            # Store calibrated probability for samples in this bin
            calibrated_probs[mask] = empirical_rate

            mapping.append(CalibrationBin(
                bin_start=bin_start,
                bin_end=bin_end,
                calibrated_prob=empirical_rate,
                n_samples=int(n_in_bin),
                empirical_rate=empirical_rate,
            ))

        # Compute metrics
        # Accuracy: use threshold condition if provided, else round calibrated probs
        if op is not None and threshold is not None:
            # Apply operator to predicted values
            if op == ComparisonOperator.GTE:
                predictions = (pred_values >= threshold).astype(int)
            elif op == ComparisonOperator.GT:
                predictions = (pred_values > threshold).astype(int)
            elif op == ComparisonOperator.LTE:
                predictions = (pred_values <= threshold).astype(int)
            elif op == ComparisonOperator.LT:
                predictions = (pred_values < threshold).astype(int)
            else:  # EQ
                predictions = (np.abs(pred_values - threshold) < 1e-9).astype(int)
        else:
            # Use calibrated probs >= 0.5 as prediction
            predictions = (calibrated_probs >= 0.5).astype(int)

        accuracy = float((predictions == labels).mean())

        # Brier score: mean squared error of calibrated probs vs labels
        brier_score = float(((calibrated_probs - labels) ** 2).mean())

        # ECE: weighted average of |calibrated_prob - empirical_rate| per bin
        ece = 0.0
        for bin_idx, bin_info in enumerate(mapping):
            mask = bin_indices == bin_idx
            n_in_bin = mask.sum()
            if n_in_bin > 0:
                bin_empirical = labels[mask].mean()
                ece += (n_in_bin / len(samples)) * abs(bin_info.calibrated_prob - bin_empirical)
        ece = float(ece)

        metrics = CalibrationMetrics(
            accuracy=accuracy,
            brier_score=brier_score,
            ece=ece,
            n_samples=len(samples),
        )

        return mapping, metrics

    async def get_job_result(
        self,
        job: CalibrationJob,
    ) -> CalibrationResultResponse:
        """Get the result of a calibration job."""
        if job.status != CalibrationJobStatus.SUCCEEDED.value:
            return CalibrationResultResponse(
                job_id=job.id,
                status=CalibrationJobStatus(job.status),
                error_message=job.error_message,
                audit=job.result_json.get("audit") if job.result_json else None,
            )

        result = job.result_json or {}

        # Parse mapping
        mapping = None
        if result.get("best_mapping"):
            mapping = [
                CalibrationBin(**b) for b in result["best_mapping"]
            ]

        # Parse metrics
        metrics = None
        if result.get("metrics"):
            metrics = CalibrationMetrics(**result["metrics"])

        # Parse run IDs
        selected_run_ids = None
        if result.get("selected_run_ids"):
            selected_run_ids = [uuid.UUID(rid) for rid in result["selected_run_ids"]]

        # Compute duration
        duration = None
        if job.started_at and job.finished_at:
            duration = (job.finished_at - job.started_at).total_seconds()

        return CalibrationResultResponse(
            job_id=job.id,
            status=CalibrationJobStatus.SUCCEEDED,
            best_mapping=mapping,
            best_bin_count=result.get("best_bin_count"),
            best_iteration=result.get("best_iteration"),
            metrics=metrics,
            audit=result.get("audit"),
            selected_run_ids=selected_run_ids,
            started_at=job.started_at,
            finished_at=job.finished_at,
            duration_seconds=duration,
        )


def get_calibration_service(db: AsyncSession) -> CalibrationService:
    """Factory function for CalibrationService."""
    return CalibrationService(db)
