"""
Export API Endpoints
Reference: project.md §11 Phase 9

Provides:
- POST /exports - Request data export
- GET /exports/{id} - Get export status/result
- GET /exports - List user's exports
- GET /exports/formats - List supported formats
- GET /exports/redaction-rules - List available redaction rules
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict
from uuid import UUID
import threading

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import Permission
from app.middleware.tenant import TenantContext, get_tenant_context
from app.services.export_controls import (
    ExportFormat,
    ExportRequest,
    ExportResult,
    PrivacyLevel,
    RedactionConfig,
    SensitivityType,
    get_export_service,
    DEFAULT_REDACTION_RULES,
)

router = APIRouter()

# In-memory cache for exports (temporary until DB persistence is added)
# Key: export_id, Value: dict with result, created_at, tenant_id
_export_cache: Dict[str, dict] = {}
_export_cache_lock = threading.Lock()


# =============================================================================
# Schemas
# =============================================================================

class ExportRequestSchema(BaseModel):
    """Request schema for data export."""
    resource_type: str = Field(
        description="Type of resource to export: telemetry, personas, runs, nodes, reliability",
        examples=["telemetry", "personas", "runs"],
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Limit export to specific project",
    )
    resource_ids: Optional[list[str]] = Field(
        default=None,
        description="Specific resource IDs to export (optional)",
    )
    format: ExportFormat = Field(
        default=ExportFormat.JSON,
        description="Export format",
    )
    date_range_start: Optional[datetime] = Field(
        default=None,
        description="Start of date range filter",
    )
    date_range_end: Optional[datetime] = Field(
        default=None,
        description="End of date range filter",
    )
    sample_size: Optional[int] = Field(
        default=None,
        ge=1,
        le=100000,
        description="Limit export to sample size",
    )
    include_raw: bool = Field(
        default=False,
        description="Include raw telemetry data (requires special permission)",
    )
    include_pii: bool = Field(
        default=False,
        description="Include PII data without redaction (requires admin)",
    )

    # Redaction options
    enable_redaction: bool = Field(
        default=True,
        description="Apply automatic PII redaction",
    )
    redact_types: Optional[list[SensitivityType]] = Field(
        default=None,
        description="Specific sensitivity types to redact",
    )
    include_redaction_summary: bool = Field(
        default=True,
        description="Include summary of redacted fields",
    )


class ExportResponseSchema(BaseModel):
    """Response schema for export request."""
    export_id: str
    status: str  # pending, completed, failed
    format: str
    record_count: Optional[int] = None
    redacted_field_count: Optional[int] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class ExportListItemSchema(BaseModel):
    """List item schema for exports."""
    export_id: str
    resource_type: str
    format: str
    status: str
    record_count: Optional[int] = None
    created_at: datetime


class RedactionRuleSchema(BaseModel):
    """Schema for redaction rule."""
    name: str
    sensitivity_type: str
    field_patterns: list[str]
    value_patterns: Optional[list[str]] = None
    redaction_method: str
    replacement: str


class SupportedFormatsResponse(BaseModel):
    """Response schema for supported formats."""
    formats: list[dict]


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "",
    response_model=ExportResponseSchema,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request data export",
    description="Request an export of data with optional redaction. Export is processed async.",
)
async def create_export(
    request: ExportRequestSchema,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new data export request.

    The export is processed asynchronously. Use the returned export_id
    to check status and download results.

    Permissions required:
    - telemetry: telemetry:export
    - personas/runs/nodes: result:export
    - audit: audit:export

    Notes:
    - PII is automatically redacted unless include_pii=true (requires admin)
    - Raw telemetry requires special telemetry:export permission
    - All exports are logged in audit trail
    """
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # Build redaction config
    redaction_config = None
    if request.enable_redaction:
        sensitivity_types = set(request.redact_types) if request.redact_types else {
            SensitivityType.PII,
            SensitivityType.FINANCIAL,
            SensitivityType.HEALTH,
            SensitivityType.CONTACT,
        }
        redaction_config = RedactionConfig(
            enabled=True,
            sensitivity_types_to_redact=sensitivity_types,
            include_redaction_summary=request.include_redaction_summary,
        )

    # Build export request
    export_request = ExportRequest(
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        project_id=request.project_id,
        resource_type=request.resource_type,
        resource_ids=request.resource_ids,
        format=request.format,
        redaction_config=redaction_config,
        date_range_start=request.date_range_start,
        date_range_end=request.date_range_end,
        sample_size=request.sample_size,
        include_raw=request.include_raw,
        include_pii=request.include_pii,
    )

    # Execute export
    service = get_export_service()
    result = await service.export(export_request)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error_message or "Export failed",
        )

    # Store in cache for later retrieval
    created_at = datetime.utcnow()
    with _export_cache_lock:
        _export_cache[result.export_id] = {
            "result": result,
            "created_at": created_at,
            "tenant_id": ctx.tenant_id if ctx else None,
            "project_id": request.project_id,
            "resource_type": request.resource_type,
            "format": request.format,
        }

    return ExportResponseSchema(
        export_id=result.export_id,
        status="completed",
        format=result.format.value,
        record_count=result.record_count,
        redacted_field_count=result.redacted_field_count,
        download_url=f"/api/v1/exports/{result.export_id}/download" if result.data else None,
        metadata=result.metadata,
        created_at=created_at,
    )


@router.get(
    "/{export_id}",
    response_model=ExportResponseSchema,
    summary="Get export status",
    description="Get status and metadata for an export request.",
)
async def get_export(
    export_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Get export status and metadata.

    Returns export details including status, record count, and download URL.
    """
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # Look up export in cache
    with _export_cache_lock:
        cached = _export_cache.get(export_id)

    if not cached:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export {export_id} not found or expired",
        )

    # Verify tenant access
    if cached.get("tenant_id") and ctx.tenant_id != cached.get("tenant_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export {export_id} not found or expired",
        )

    result: ExportResult = cached["result"]
    return ExportResponseSchema(
        export_id=result.export_id,
        status="completed",
        format=result.format.value,
        record_count=result.record_count,
        redacted_field_count=result.redacted_field_count,
        download_url=f"/api/v1/exports/{result.export_id}/download" if result.data else None,
        metadata=result.metadata,
        created_at=cached["created_at"],
    )


@router.get(
    "/{export_id}/download",
    summary="Download export data",
    description="Download the exported data file.",
)
async def download_export(
    export_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Download export data.

    Returns the exported data in the requested format.
    """
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # Look up export in cache
    with _export_cache_lock:
        cached = _export_cache.get(export_id)

    if not cached:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export {export_id} not found or expired",
        )

    # Verify tenant access
    if cached.get("tenant_id") and ctx.tenant_id != cached.get("tenant_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export {export_id} not found or expired",
        )

    result: ExportResult = cached["result"]

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export {export_id} has no data available",
        )

    # Determine content type and filename based on format
    content_type_map = {
        ExportFormat.JSON: "application/json",
        ExportFormat.CSV: "text/csv",
        ExportFormat.PARQUET: "application/vnd.apache.parquet",
        ExportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    extension_map = {
        ExportFormat.JSON: ".json",
        ExportFormat.CSV: ".csv",
        ExportFormat.PARQUET: ".parquet",
        ExportFormat.EXCEL: ".xlsx",
    }

    content_type = content_type_map.get(result.format, "application/octet-stream")
    extension = extension_map.get(result.format, ".bin")
    filename = f"export_{export_id}{extension}"

    return Response(
        content=result.data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    "",
    response_model=list[ExportListItemSchema],
    summary="List exports",
    description="List export requests for the current user/tenant.",
)
async def list_exports(
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List exports for the current tenant.

    Returns paginated list of export requests with basic metadata.
    """
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    # Filter exports from cache by tenant
    with _export_cache_lock:
        tenant_exports = [
            (export_id, data)
            for export_id, data in _export_cache.items()
            if data.get("tenant_id") == ctx.tenant_id or data.get("tenant_id") is None
        ]

    # Apply resource_type filter
    if resource_type:
        tenant_exports = [
            (export_id, data)
            for export_id, data in tenant_exports
            if data.get("resource_type") == resource_type
        ]

    # Sort by created_at descending (newest first)
    tenant_exports.sort(key=lambda x: x[1]["created_at"], reverse=True)

    # Apply pagination
    paginated = tenant_exports[offset:offset + limit]

    # Build response
    result = []
    for export_id, data in paginated:
        export_result: ExportResult = data["result"]
        result.append(
            ExportListItemSchema(
                export_id=export_id,
                resource_type=data.get("resource_type", "unknown"),
                format=export_result.format.value,
                status="completed",
                record_count=export_result.record_count,
                created_at=data["created_at"],
            )
        )

    return result


@router.get(
    "/formats/supported",
    response_model=SupportedFormatsResponse,
    summary="Get supported formats",
    description="Get list of supported export formats.",
)
async def get_supported_formats():
    """
    Get list of supported export formats.

    Returns format details including MIME types and extensions.
    """
    formats = [
        {
            "format": ExportFormat.JSON.value,
            "mime_type": "application/json",
            "extension": ".json",
            "description": "JavaScript Object Notation",
        },
        {
            "format": ExportFormat.CSV.value,
            "mime_type": "text/csv",
            "extension": ".csv",
            "description": "Comma-Separated Values",
        },
        {
            "format": ExportFormat.PARQUET.value,
            "mime_type": "application/vnd.apache.parquet",
            "extension": ".parquet",
            "description": "Apache Parquet columnar storage",
        },
        {
            "format": ExportFormat.EXCEL.value,
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "extension": ".xlsx",
            "description": "Microsoft Excel spreadsheet",
        },
    ]

    return SupportedFormatsResponse(formats=formats)


@router.get(
    "/redaction/rules",
    response_model=list[RedactionRuleSchema],
    summary="Get redaction rules",
    description="Get list of available data redaction rules.",
)
async def get_redaction_rules(
    sensitivity_type: Optional[SensitivityType] = Query(None, description="Filter by type"),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """
    Get available redaction rules.

    Returns list of rules used for automatic PII/sensitive data redaction.
    """
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    rules = DEFAULT_REDACTION_RULES

    if sensitivity_type:
        rules = [r for r in rules if r.sensitivity_type == sensitivity_type]

    return [
        RedactionRuleSchema(
            name=rule.name,
            sensitivity_type=rule.sensitivity_type.value,
            field_patterns=rule.field_patterns,
            value_patterns=rule.value_patterns,
            redaction_method=rule.redaction_method,
            replacement=rule.replacement,
        )
        for rule in rules
    ]


@router.get(
    "/redaction/sensitivity-types",
    summary="Get sensitivity types",
    description="Get list of sensitivity types for redaction configuration.",
)
async def get_sensitivity_types():
    """
    Get available sensitivity types.

    Returns list of sensitivity types that can be configured for redaction.
    """
    return [
        {
            "type": t.value,
            "description": _get_sensitivity_description(t),
        }
        for t in SensitivityType
    ]


@router.get(
    "/privacy-levels",
    summary="Get privacy levels",
    description="Get list of data privacy levels.",
)
async def get_privacy_levels():
    """
    Get data privacy levels.

    Returns list of privacy levels and their export restrictions.
    """
    return [
        {
            "level": PrivacyLevel.PUBLIC.value,
            "description": "Can be exported without restrictions",
            "requirements": [],
        },
        {
            "level": PrivacyLevel.INTERNAL.value,
            "description": "Requires organization membership",
            "requirements": ["org_membership"],
        },
        {
            "level": PrivacyLevel.CONFIDENTIAL.value,
            "description": "Requires explicit export permission",
            "requirements": ["export_permission", "org_membership"],
        },
        {
            "level": PrivacyLevel.RESTRICTED.value,
            "description": "Requires admin approval, redaction mandatory",
            "requirements": ["admin_role", "export_permission", "audit_trail"],
        },
    ]


def _get_sensitivity_description(t: SensitivityType) -> str:
    """Get description for sensitivity type."""
    descriptions = {
        SensitivityType.PII: "Personally identifiable information (name, email, etc.)",
        SensitivityType.FINANCIAL: "Financial data (income, bank accounts, etc.)",
        SensitivityType.HEALTH: "Health-related information",
        SensitivityType.BEHAVIORAL: "Detailed behavioral patterns",
        SensitivityType.DEMOGRAPHIC: "Demographic details",
        SensitivityType.LOCATION: "Geographic/location data",
        SensitivityType.CONTACT: "Contact information",
        SensitivityType.PREDICTION: "Model predictions",
        SensitivityType.CONFIDENCE: "Confidence scores",
        SensitivityType.INTERNAL: "Internal system data",
    }
    return descriptions.get(t, t.value)
