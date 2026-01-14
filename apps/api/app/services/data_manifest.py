"""
DataManifest Service - Per-Run Data Access Manifest Management
Reference: temporal.md §5, §9

This service manages the per-run data access manifests that track:
- All external data sources accessed during a run
- Endpoints called with parameters
- Time windows and record counts
- Payload hashes for integrity verification
- Isolation status computation (PASS/FAIL)

Usage:
    manifest_service = DataManifestService(db)
    await manifest_service.create_entry(
        run_id=run_id,
        source_name="census_bureau",
        endpoint="/data/population",
        params={"region": "US"},
        ...
    )
    status, violations = await manifest_service.compute_isolation_status(run_id)
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run_manifest import RunManifest
from app.services.data_gateway import ManifestEntry


# =============================================================================
# Data Models
# =============================================================================

class IsolationViolation(BaseModel):
    """A single temporal isolation violation."""
    violation_type: str  # 'cutoff_breach', 'unsafe_source', 'missing_timestamp', 'unknown_source'
    source_name: str
    endpoint: Optional[str] = None
    details: str
    severity: str = "error"  # 'error', 'warning'
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ManifestSummary(BaseModel):
    """Summary of a data access manifest."""
    run_id: str
    project_id: str
    entry_count: int
    total_records: int
    total_filtered: int
    sources_accessed: List[str]
    payload_hashes: Dict[str, str]  # {source:endpoint -> hash}
    isolation_status: Optional[str] = None
    violations: List[IsolationViolation] = []
    cutoff_applied: Optional[datetime] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# DataManifest Service
# =============================================================================

class DataManifestService:
    """
    Service for managing per-run data access manifests.

    Responsibilities:
    - Aggregate manifest entries from DataGateway
    - Persist manifests to RunManifest table
    - Compute isolation status (PASS/FAIL)
    - Generate audit reports

    Reference: temporal.md §5, §9
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize DataManifestService.

        Args:
            db: Database session
        """
        self.db = db
        self._pending_entries: Dict[str, List[ManifestEntry]] = {}  # run_id -> entries

    async def add_entry(
        self,
        run_id: str,
        entry: ManifestEntry,
    ) -> None:
        """
        Add a manifest entry for a run.

        Args:
            run_id: Run UUID
            entry: ManifestEntry from DataGateway
        """
        if run_id not in self._pending_entries:
            self._pending_entries[run_id] = []
        self._pending_entries[run_id].append(entry)

    async def add_entries(
        self,
        run_id: str,
        entries: List[ManifestEntry],
    ) -> None:
        """Add multiple manifest entries for a run."""
        for entry in entries:
            await self.add_entry(run_id, entry)

    async def finalize_manifest(
        self,
        run_id: str,
        project_id: str,
        cutoff_time: Optional[datetime] = None,
        isolation_level: int = 1,
    ) -> ManifestSummary:
        """
        Finalize and persist the manifest for a run.

        This should be called at the end of a run to:
        1. Aggregate all entries
        2. Compute payload hashes
        3. Compute isolation status
        4. Persist to database

        Args:
            run_id: Run UUID
            project_id: Project UUID
            cutoff_time: Applied cutoff timestamp
            isolation_level: Isolation level (1-3)

        Returns:
            ManifestSummary with aggregated data and status
        """
        entries = self._pending_entries.get(run_id, [])

        # Aggregate entries
        total_records = sum(e.record_count for e in entries)
        total_filtered = sum(e.filtered_count for e in entries)
        sources_accessed = list(set(e.source_name for e in entries))

        # Build payload hashes dict
        payload_hashes = {}
        for entry in entries:
            key = f"{entry.source_name}:{entry.endpoint}"
            payload_hashes[key] = entry.payload_hash

        # Compute isolation status
        status, violations = await self._compute_isolation_status(
            entries=entries,
            cutoff_time=cutoff_time,
            isolation_level=isolation_level,
        )

        # Create manifest summary
        summary = ManifestSummary(
            run_id=run_id,
            project_id=project_id,
            entry_count=len(entries),
            total_records=total_records,
            total_filtered=total_filtered,
            sources_accessed=sources_accessed,
            payload_hashes=payload_hashes,
            isolation_status=status,
            violations=violations,
            cutoff_applied=cutoff_time,
        )

        # Persist to database
        await self._persist_manifest(run_id, summary, entries)

        # Clean up pending entries
        if run_id in self._pending_entries:
            del self._pending_entries[run_id]

        return summary

    async def get_manifest(
        self,
        run_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the manifest for a run from the database.

        Args:
            run_id: Run UUID

        Returns:
            Manifest dict or None if not found
        """
        run_uuid = uuid.UUID(run_id) if isinstance(run_id, str) else run_id

        stmt = select(RunManifest).where(RunManifest.run_id == run_uuid)
        result = await self.db.execute(stmt)
        run_manifest = result.scalar_one_or_none()

        if run_manifest:
            return run_manifest.data_manifest_ref

        return None

    async def get_isolation_status(
        self,
        run_id: str,
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Get the isolation status for a run.

        Args:
            run_id: Run UUID

        Returns:
            Tuple of (status, violations)
        """
        run_uuid = uuid.UUID(run_id) if isinstance(run_id, str) else run_id

        stmt = select(RunManifest).where(RunManifest.run_id == run_uuid)
        result = await self.db.execute(stmt)
        run_manifest = result.scalar_one_or_none()

        if run_manifest:
            return (
                run_manifest.isolation_status,
                run_manifest.isolation_violations or [],
            )

        return None, []

    async def update_isolation_status(
        self,
        run_id: str,
        status: str,
        violations: Optional[List[IsolationViolation]] = None,
    ) -> None:
        """
        Update the isolation status for a run.

        Args:
            run_id: Run UUID
            status: 'PASS' or 'FAIL'
            violations: List of violations (if status is FAIL)
        """
        run_uuid = uuid.UUID(run_id) if isinstance(run_id, str) else run_id

        violations_dict = [v.model_dump() for v in violations] if violations else None

        stmt = (
            update(RunManifest)
            .where(RunManifest.run_id == run_uuid)
            .values(
                isolation_status=status,
                isolation_violations=violations_dict,
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _compute_isolation_status(
        self,
        entries: List[ManifestEntry],
        cutoff_time: Optional[datetime],
        isolation_level: int,
    ) -> Tuple[str, List[IsolationViolation]]:
        """
        Compute isolation status based on manifest entries.

        Rules:
        - PASS if no violations
        - FAIL if any violations at current isolation level

        Violations:
        - filtered_count > 0 with strict mode (Level 2+)
        - Unknown sources in backtest mode (Level 2+)
        - Missing timestamps for temporal sources

        Returns:
            Tuple of (status, violations)
        """
        violations: List[IsolationViolation] = []

        # Check for cutoff breaches (records filtered out)
        # At Level 2+, any filtered records indicate potential leakage
        if isolation_level >= 2 and cutoff_time:
            for entry in entries:
                if entry.filtered_count > 0:
                    violations.append(IsolationViolation(
                        violation_type="cutoff_breach",
                        source_name=entry.source_name,
                        endpoint=entry.endpoint,
                        details=f"{entry.filtered_count} records filtered after cutoff {cutoff_time.isoformat()}",
                        severity="warning" if isolation_level == 2 else "error",
                    ))

        # At Level 3 (audit-first), any data access without full timestamp support is flagged
        if isolation_level >= 3:
            for entry in entries:
                # Check if time_window was properly captured
                if not entry.time_window:
                    violations.append(IsolationViolation(
                        violation_type="missing_timestamp",
                        source_name=entry.source_name,
                        endpoint=entry.endpoint,
                        details="No time window captured for this data access",
                        severity="warning",
                    ))

        # Determine status
        error_violations = [v for v in violations if v.severity == "error"]
        status = "FAIL" if error_violations else "PASS"

        return status, violations

    async def _persist_manifest(
        self,
        run_id: str,
        summary: ManifestSummary,
        entries: List[ManifestEntry],
    ) -> None:
        """
        Persist manifest to RunManifest table.

        Updates the existing RunManifest record with manifest data.
        """
        run_uuid = uuid.UUID(run_id) if isinstance(run_id, str) else run_id

        # Build manifest reference
        manifest_ref = {
            "entries": [e.model_dump() for e in entries],
            "summary": {
                "entry_count": summary.entry_count,
                "total_records": summary.total_records,
                "total_filtered": summary.total_filtered,
                "sources_accessed": summary.sources_accessed,
            },
            "payload_hashes": summary.payload_hashes,
            "generated_at": summary.generated_at.isoformat(),
        }

        violations_dict = [v.model_dump() for v in summary.violations] if summary.violations else None

        # Update RunManifest
        stmt = (
            update(RunManifest)
            .where(RunManifest.run_id == run_uuid)
            .values(
                data_manifest_ref=manifest_ref,
                cutoff_applied_as_of_datetime=summary.cutoff_applied,
                isolation_status=summary.isolation_status,
                isolation_violations=violations_dict,
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()


# =============================================================================
# Factory Functions
# =============================================================================

def get_data_manifest_service(db: AsyncSession) -> DataManifestService:
    """Get a DataManifestService instance."""
    return DataManifestService(db)


async def finalize_run_manifest(
    db: AsyncSession,
    run_id: str,
    project_id: str,
    entries: List[ManifestEntry],
    cutoff_time: Optional[datetime] = None,
    isolation_level: int = 1,
) -> ManifestSummary:
    """
    Convenience function to finalize a run manifest.

    Args:
        db: Database session
        run_id: Run UUID
        project_id: Project UUID
        entries: List of manifest entries from DataGateway
        cutoff_time: Applied cutoff timestamp
        isolation_level: Isolation level (1-3)

    Returns:
        ManifestSummary
    """
    service = DataManifestService(db)
    await service.add_entries(run_id, entries)
    return await service.finalize_manifest(
        run_id=run_id,
        project_id=project_id,
        cutoff_time=cutoff_time,
        isolation_level=isolation_level,
    )
