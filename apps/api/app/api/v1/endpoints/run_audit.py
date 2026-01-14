"""
Run Audit API Endpoints
Reference: temporal.md §8 Phase 5

Provides endpoints for:
- GET /runs/{run_id}/audit - Full audit report
- GET /runs/{run_id}/audit/manifest - Data manifest only
- GET /runs/{run_id}/audit/isolation - PASS/FAIL status

The audit report shows:
- Temporal context (as_of_datetime, timezone, isolation level)
- All sources accessed with endpoints, time windows, record counts
- Payload hashes for data integrity verification
- PASS/FAIL isolation indicator
- Export as JSON supported
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.middleware.tenant import (
    require_permission,
    get_current_tenant_id,
)
from app.models.user import User
from app.models.run_manifest import RunManifest


router = APIRouter()


# =============================================================================
# Response Schemas (temporal.md §8 Phase 5)
# =============================================================================

class TemporalContextAudit(BaseModel):
    """Temporal context in audit report."""
    mode: str = Field(..., description="'live' or 'backtest'")
    as_of_datetime: Optional[str] = Field(None, description="Cutoff datetime (ISO 8601)")
    timezone: str = Field(..., description="IANA timezone")
    isolation_level: int = Field(..., description="1=Basic, 2=Strict, 3=Audit-First")
    policy_version: str = Field(..., description="Policy version at run time")


class SourceAccessEntry(BaseModel):
    """A single source access record in the manifest."""
    source_name: str
    endpoint: str
    params: Dict[str, Any]
    params_hash: str
    time_window: Optional[Dict[str, Any]] = None
    record_count: int
    filtered_count: int
    payload_hash: str
    timestamp: str
    response_time_ms: int


class DataManifestResponse(BaseModel):
    """Data manifest for a run."""
    run_id: str
    entries: List[SourceAccessEntry]
    total_records: int
    total_filtered: int
    sources_accessed: List[str]
    generated_at: str


class IsolationViolation(BaseModel):
    """A single isolation violation."""
    violation_type: str
    description: str
    severity: str
    evidence: str
    line_number: Optional[int] = None
    confidence: float


class IsolationStatusResponse(BaseModel):
    """Isolation status with violations."""
    run_id: str
    status: str = Field(..., description="'PASS' or 'FAIL'")
    compliance_score: float = Field(..., description="0.0 to 1.0")
    violations: List[IsolationViolation]
    grounded_facts_count: int
    ungrounded_facts_count: int
    checked_at: str


class VersionSnapshot(BaseModel):
    """Version information at run time."""
    engine_version: str
    ruleset_version: str
    dataset_version: str
    policy_version: str


class RunAuditReportResponse(BaseModel):
    """Full audit report for a run (temporal.md §8 Phase 5)."""
    run_id: str
    project_id: str
    node_id: Optional[str] = None

    # Temporal Context
    temporal_context: TemporalContextAudit

    # Isolation Status
    isolation_status: str = Field(..., description="'PASS' or 'FAIL'")
    compliance_score: float
    violations: List[IsolationViolation]

    # Data Manifest
    sources_accessed: List[SourceAccessEntry]
    total_records: int
    total_filtered: int
    payload_hashes: Dict[str, str]  # source_name -> hash

    # Versions
    versions: VersionSnapshot

    # Metadata
    random_seed: Optional[int] = None
    created_at: str
    completed_at: Optional[str] = None


# =============================================================================
# API Endpoints
# =============================================================================

@router.get(
    "/runs/{run_id}/audit",
    response_model=RunAuditReportResponse,
    summary="Get full audit report for a run",
    description="Returns complete temporal audit report including isolation status, manifest, and versions."
)
async def get_run_audit_report(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    Get the full audit report for a run.

    The audit report includes:
    - Temporal context (mode, cutoff, timezone, isolation level)
    - Isolation status (PASS/FAIL with compliance score)
    - Data manifest (all sources accessed)
    - Payload hashes for integrity verification
    - Version information

    Reference: temporal.md §8 Phase 5 item 13
    """
    # Look up the run manifest
    stmt = select(RunManifest).where(
        RunManifest.id == UUID(run_id),
        RunManifest.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    manifest = result.scalar_one_or_none()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run manifest not found: {run_id}"
        )

    # Extract temporal audit report from manifest
    temporal_report = manifest.get_temporal_audit_report() if hasattr(manifest, 'get_temporal_audit_report') else {}

    # Build source access entries from data_manifest_ref
    sources_accessed = []
    payload_hashes = {}
    total_records = 0
    total_filtered = 0

    data_manifest = manifest.data_manifest_ref or {}
    entries = data_manifest.get('entries', [])

    for entry in entries:
        source_entry = SourceAccessEntry(
            source_name=entry.get('source_name', ''),
            endpoint=entry.get('endpoint', ''),
            params=entry.get('params', {}),
            params_hash=entry.get('params_hash', ''),
            time_window=entry.get('time_window'),
            record_count=entry.get('record_count', 0),
            filtered_count=entry.get('filtered_count', 0),
            payload_hash=entry.get('payload_hash', ''),
            timestamp=entry.get('timestamp', datetime.utcnow().isoformat()),
            response_time_ms=entry.get('response_time_ms', 0),
        )
        sources_accessed.append(source_entry)
        payload_hashes[source_entry.source_name] = source_entry.payload_hash
        total_records += source_entry.record_count
        total_filtered += source_entry.filtered_count

    # Build violations list
    violations = []
    isolation_violations = manifest.isolation_violations or []
    for v in isolation_violations:
        violations.append(IsolationViolation(
            violation_type=v.get('violation_type', 'unknown'),
            description=v.get('description', ''),
            severity=v.get('severity', 'medium'),
            evidence=v.get('evidence', ''),
            line_number=v.get('line_number'),
            confidence=v.get('confidence', 0.5),
        ))

    # Get temporal context
    temporal_context = TemporalContextAudit(
        mode=temporal_report.get('temporal_mode', 'live'),
        as_of_datetime=temporal_report.get('cutoff_applied_as_of_datetime'),
        timezone=temporal_report.get('timezone', 'UTC'),
        isolation_level=temporal_report.get('isolation_level', 1),
        policy_version=temporal_report.get('policy_version', '1.0.0'),
    )

    # Get version info
    config = manifest.config or {}
    versions = VersionSnapshot(
        engine_version=config.get('engine_version', '0.1.0'),
        ruleset_version=config.get('ruleset_version', '1.0.0'),
        dataset_version=config.get('dataset_version', '1.0.0'),
        policy_version=temporal_report.get('policy_version', '1.0.0'),
    )

    return RunAuditReportResponse(
        run_id=str(manifest.id),
        project_id=str(manifest.project_spec_id) if manifest.project_spec_id else '',
        node_id=str(manifest.node_id) if manifest.node_id else None,
        temporal_context=temporal_context,
        isolation_status=manifest.isolation_status or 'PASS',
        compliance_score=temporal_report.get('compliance_score', 1.0),
        violations=violations,
        sources_accessed=sources_accessed,
        total_records=total_records,
        total_filtered=total_filtered,
        payload_hashes=payload_hashes,
        versions=versions,
        random_seed=config.get('seed'),
        created_at=manifest.created_at.isoformat() if manifest.created_at else datetime.utcnow().isoformat(),
        completed_at=manifest.completed_at.isoformat() if manifest.completed_at else None,
    )


@router.get(
    "/runs/{run_id}/audit/manifest",
    response_model=DataManifestResponse,
    summary="Get data manifest for a run",
    description="Returns the data manifest showing all sources accessed during the run."
)
async def get_run_audit_manifest(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    Get the data manifest for a run.

    The manifest includes all external data sources accessed during
    the run with endpoints, parameters, record counts, and payload hashes.

    Reference: temporal.md §5
    """
    stmt = select(RunManifest).where(
        RunManifest.id == UUID(run_id),
        RunManifest.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    manifest = result.scalar_one_or_none()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run manifest not found: {run_id}"
        )

    # Extract manifest entries
    data_manifest = manifest.data_manifest_ref or {}
    entries = []
    sources_set = set()
    total_records = 0
    total_filtered = 0

    for entry in data_manifest.get('entries', []):
        source_entry = SourceAccessEntry(
            source_name=entry.get('source_name', ''),
            endpoint=entry.get('endpoint', ''),
            params=entry.get('params', {}),
            params_hash=entry.get('params_hash', ''),
            time_window=entry.get('time_window'),
            record_count=entry.get('record_count', 0),
            filtered_count=entry.get('filtered_count', 0),
            payload_hash=entry.get('payload_hash', ''),
            timestamp=entry.get('timestamp', datetime.utcnow().isoformat()),
            response_time_ms=entry.get('response_time_ms', 0),
        )
        entries.append(source_entry)
        sources_set.add(source_entry.source_name)
        total_records += source_entry.record_count
        total_filtered += source_entry.filtered_count

    return DataManifestResponse(
        run_id=str(manifest.id),
        entries=entries,
        total_records=total_records,
        total_filtered=total_filtered,
        sources_accessed=sorted(list(sources_set)),
        generated_at=data_manifest.get('generated_at', datetime.utcnow().isoformat()),
    )


@router.get(
    "/runs/{run_id}/audit/isolation",
    response_model=IsolationStatusResponse,
    summary="Get isolation status for a run",
    description="Returns the PASS/FAIL isolation status with compliance score and violations."
)
async def get_run_isolation_status(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    Get the isolation status for a run.

    Returns PASS or FAIL based on temporal compliance, along with
    a compliance score (0.0 to 1.0) and list of violations.

    Reference: temporal.md §8 Phase 5
    """
    stmt = select(RunManifest).where(
        RunManifest.id == UUID(run_id),
        RunManifest.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    manifest = result.scalar_one_or_none()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run manifest not found: {run_id}"
        )

    # Get temporal report for compliance score
    temporal_report = manifest.get_temporal_audit_report() if hasattr(manifest, 'get_temporal_audit_report') else {}

    # Build violations list
    violations = []
    for v in (manifest.isolation_violations or []):
        violations.append(IsolationViolation(
            violation_type=v.get('violation_type', 'unknown'),
            description=v.get('description', ''),
            severity=v.get('severity', 'medium'),
            evidence=v.get('evidence', ''),
            line_number=v.get('line_number'),
            confidence=v.get('confidence', 0.5),
        ))

    return IsolationStatusResponse(
        run_id=str(manifest.id),
        status=manifest.isolation_status or 'PASS',
        compliance_score=temporal_report.get('compliance_score', 1.0),
        violations=violations,
        grounded_facts_count=temporal_report.get('grounded_facts_count', 0),
        ungrounded_facts_count=temporal_report.get('ungrounded_facts_count', 0),
        checked_at=datetime.utcnow().isoformat(),
    )


@router.get(
    "/runs/{run_id}/audit/export",
    summary="Export audit report as JSON",
    description="Returns the complete audit report as a downloadable JSON file."
)
async def export_run_audit_report(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    Export the audit report as a downloadable JSON file.

    Reference: temporal.md §8 Phase 5
    """
    # Get the full audit report
    stmt = select(RunManifest).where(
        RunManifest.id == UUID(run_id),
        RunManifest.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    manifest = result.scalar_one_or_none()

    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run manifest not found: {run_id}"
        )

    # Build the export data
    temporal_report = manifest.get_temporal_audit_report() if hasattr(manifest, 'get_temporal_audit_report') else {}
    data_manifest = manifest.data_manifest_ref or {}
    config = manifest.config or {}

    export_data = {
        "run_id": str(manifest.id),
        "project_id": str(manifest.project_spec_id) if manifest.project_spec_id else None,
        "node_id": str(manifest.node_id) if manifest.node_id else None,
        "temporal_context": {
            "mode": temporal_report.get('temporal_mode', 'live'),
            "as_of_datetime": temporal_report.get('cutoff_applied_as_of_datetime'),
            "timezone": temporal_report.get('timezone', 'UTC'),
            "isolation_level": temporal_report.get('isolation_level', 1),
            "policy_version": temporal_report.get('policy_version', '1.0.0'),
        },
        "isolation_status": manifest.isolation_status or 'PASS',
        "compliance_score": temporal_report.get('compliance_score', 1.0),
        "violations": manifest.isolation_violations or [],
        "data_manifest": data_manifest,
        "versions": {
            "engine_version": config.get('engine_version', '0.1.0'),
            "ruleset_version": config.get('ruleset_version', '1.0.0'),
            "dataset_version": config.get('dataset_version', '1.0.0'),
            "policy_version": temporal_report.get('policy_version', '1.0.0'),
        },
        "random_seed": config.get('seed'),
        "created_at": manifest.created_at.isoformat() if manifest.created_at else None,
        "completed_at": manifest.completed_at.isoformat() if manifest.completed_at else None,
        "exported_at": datetime.utcnow().isoformat(),
    }

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f'attachment; filename="audit_report_{run_id}.json"'
        }
    )
