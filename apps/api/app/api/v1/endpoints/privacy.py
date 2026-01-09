"""
Privacy API Endpoints
Reference: project.md §11 Phase 9 (Compliance Posture)

Provides endpoints for:
- Privacy request management (GDPR/CCPA)
- Data deletion requests (Right to Erasure)
- Data export requests (Subject Access Request)
- Data retention policy management
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import get_current_user, get_current_admin_user
from app.models.user import User
from app.services.privacy import (
    PrivacyService,
    PrivacyRequest,
    PrivacyRequestType,
    PrivacyRequestStatus,
    DataCategory,
    DeletionResult,
    DataExportResult,
    get_privacy_service,
)
from app.services.data_retention import (
    DataRetentionService,
    RetentionPolicy,
    RetentionResourceType,
    RetentionAction,
    RetentionResult,
    get_data_retention_service,
)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class PrivacyRequestCreate(BaseModel):
    """Request to create a privacy request."""
    request_type: PrivacyRequestType
    reason: Optional[str] = None
    categories: Optional[List[DataCategory]] = None


class PrivacyRequestResponse(BaseModel):
    """Privacy request response."""
    id: str
    request_type: PrivacyRequestType
    status: PrivacyRequestStatus
    user_email: str
    reason: Optional[str] = None
    categories: List[DataCategory] = []
    verified_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    result_url: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None


class PrivacyRequestVerify(BaseModel):
    """Request to verify a privacy request."""
    verification_token: str


class DeletionResultResponse(BaseModel):
    """Deletion result response."""
    request_id: str
    user_id: str
    success: bool
    deleted_counts: dict
    retained_items: List[dict] = []
    errors: List[str] = []


class DataExportResultResponse(BaseModel):
    """Data export result response."""
    request_id: str
    user_id: str
    success: bool
    format: str
    file_size_bytes: int
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    categories_included: List[DataCategory] = []
    errors: List[str] = []


class RetentionPolicyCreate(BaseModel):
    """Request to create/update a retention policy."""
    resource_type: RetentionResourceType
    retention_days: int = Field(..., gt=0, le=3650)
    action: RetentionAction = RetentionAction.DELETE
    enabled: bool = True
    description: Optional[str] = None
    grace_period_days: int = Field(7, ge=0, le=30)
    exclude_if_referenced: bool = True
    exclude_starred: bool = True


class RetentionPolicyResponse(BaseModel):
    """Retention policy response."""
    resource_type: RetentionResourceType
    retention_days: int
    action: RetentionAction
    enabled: bool
    tenant_id: Optional[str] = None
    description: Optional[str] = None
    grace_period_days: int
    exclude_if_referenced: bool
    exclude_starred: bool


class RetentionEnforcementResponse(BaseModel):
    """Retention enforcement result response."""
    resource_type: RetentionResourceType
    action: RetentionAction
    items_processed: int
    items_deleted: int
    items_archived: int
    items_anonymized: int
    items_skipped: int
    errors: List[str] = []
    duration_seconds: float


# =============================================================================
# Dependencies
# =============================================================================

def get_privacy_svc() -> PrivacyService:
    """Get privacy service instance."""
    return get_privacy_service()


def get_retention_svc() -> DataRetentionService:
    """Get data retention service instance."""
    return get_data_retention_service()


# =============================================================================
# Privacy Request Endpoints
# =============================================================================

@router.post(
    "/requests",
    response_model=PrivacyRequestResponse,
    summary="Create privacy request",
    description="Create a new privacy request (data access, deletion, export, etc.)",
)
async def create_privacy_request(
    request: PrivacyRequestCreate,
    current_user: User = Depends(get_current_user),
    privacy_service: PrivacyService = Depends(get_privacy_svc),
) -> PrivacyRequestResponse:
    """Create a new privacy request for the current user."""
    privacy_request = await privacy_service.create_request(
        request_type=request.request_type,
        user_id=str(current_user.id),
        user_email=current_user.email,
        tenant_id=None,  # Would come from tenant context
        reason=request.reason,
        categories=request.categories,
    )

    return PrivacyRequestResponse(
        id=privacy_request.id,
        request_type=privacy_request.request_type,
        status=privacy_request.status,
        user_email=privacy_request.user_email,
        reason=privacy_request.reason,
        categories=privacy_request.categories,
        verified_at=privacy_request.verified_at,
        processed_at=privacy_request.processed_at,
        result_url=privacy_request.result_url,
        rejection_reason=privacy_request.rejection_reason,
        created_at=privacy_request.created_at,
        expires_at=privacy_request.expires_at,
    )


@router.get(
    "/requests",
    response_model=List[PrivacyRequestResponse],
    summary="List privacy requests",
    description="List privacy requests for the current user",
)
async def list_privacy_requests(
    status: Optional[PrivacyRequestStatus] = None,
    request_type: Optional[PrivacyRequestType] = None,
    current_user: User = Depends(get_current_user),
    privacy_service: PrivacyService = Depends(get_privacy_svc),
) -> List[PrivacyRequestResponse]:
    """List privacy requests for the current user."""
    requests = await privacy_service.list_requests(
        user_id=str(current_user.id),
        status=status,
        request_type=request_type,
    )

    return [
        PrivacyRequestResponse(
            id=r.id,
            request_type=r.request_type,
            status=r.status,
            user_email=r.user_email,
            reason=r.reason,
            categories=r.categories,
            verified_at=r.verified_at,
            processed_at=r.processed_at,
            result_url=r.result_url,
            rejection_reason=r.rejection_reason,
            created_at=r.created_at,
            expires_at=r.expires_at,
        )
        for r in requests
    ]


@router.get(
    "/requests/{request_id}",
    response_model=PrivacyRequestResponse,
    summary="Get privacy request",
    description="Get details of a specific privacy request",
)
async def get_privacy_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    privacy_service: PrivacyService = Depends(get_privacy_svc),
) -> PrivacyRequestResponse:
    """Get a specific privacy request."""
    privacy_request = privacy_service.get_request(request_id)

    if not privacy_request:
        raise HTTPException(status_code=404, detail="Privacy request not found")

    if privacy_request.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this request")

    return PrivacyRequestResponse(
        id=privacy_request.id,
        request_type=privacy_request.request_type,
        status=privacy_request.status,
        user_email=privacy_request.user_email,
        reason=privacy_request.reason,
        categories=privacy_request.categories,
        verified_at=privacy_request.verified_at,
        processed_at=privacy_request.processed_at,
        result_url=privacy_request.result_url,
        rejection_reason=privacy_request.rejection_reason,
        created_at=privacy_request.created_at,
        expires_at=privacy_request.expires_at,
    )


@router.post(
    "/requests/{request_id}/verify",
    response_model=dict,
    summary="Verify privacy request",
    description="Verify a privacy request with the verification token",
)
async def verify_privacy_request(
    request_id: str,
    verification: PrivacyRequestVerify,
    privacy_service: PrivacyService = Depends(get_privacy_svc),
) -> dict:
    """Verify a privacy request."""
    success = await privacy_service.verify_request(
        request_id=request_id,
        verification_token=verification.verification_token,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Verification failed")

    return {"verified": True, "message": "Request verified successfully"}


# =============================================================================
# Deletion Request Endpoints
# =============================================================================

@router.post(
    "/delete-my-data",
    response_model=PrivacyRequestResponse,
    summary="Request data deletion",
    description="Request deletion of all personal data (Right to Erasure)",
)
async def request_data_deletion(
    reason: Optional[str] = None,
    categories: Optional[List[DataCategory]] = None,
    current_user: User = Depends(get_current_user),
    privacy_service: PrivacyService = Depends(get_privacy_svc),
) -> PrivacyRequestResponse:
    """
    Request deletion of personal data.

    This creates a deletion request that requires verification before processing.
    A verification email will be sent to confirm the request.
    """
    privacy_request = await privacy_service.create_request(
        request_type=PrivacyRequestType.DATA_DELETION,
        user_id=str(current_user.id),
        user_email=current_user.email,
        reason=reason,
        categories=categories or list(DataCategory),
    )

    # Set status to awaiting verification
    privacy_request.status = PrivacyRequestStatus.AWAITING_VERIFICATION

    return PrivacyRequestResponse(
        id=privacy_request.id,
        request_type=privacy_request.request_type,
        status=privacy_request.status,
        user_email=privacy_request.user_email,
        reason=privacy_request.reason,
        categories=privacy_request.categories,
        created_at=privacy_request.created_at,
        expires_at=privacy_request.expires_at,
    )


@router.post(
    "/requests/{request_id}/process-deletion",
    response_model=DeletionResultResponse,
    summary="Process deletion request",
    description="Process a verified deletion request (admin only)",
)
async def process_deletion_request(
    request_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
    privacy_service: PrivacyService = Depends(get_privacy_svc),
) -> DeletionResultResponse:
    """Process a verified deletion request."""
    privacy_request = privacy_service.get_request(request_id)

    if not privacy_request:
        raise HTTPException(status_code=404, detail="Request not found")

    if privacy_request.status != PrivacyRequestStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail=f"Request is not ready for processing (status: {privacy_request.status.value})",
        )

    result = await privacy_service.process_deletion_request(request_id)

    return DeletionResultResponse(
        request_id=result.request_id,
        user_id=result.user_id,
        success=result.success,
        deleted_counts=result.deleted_counts,
        retained_items=result.retained_items,
        errors=result.errors,
    )


# =============================================================================
# Data Export Endpoints
# =============================================================================

@router.post(
    "/export-my-data",
    response_model=PrivacyRequestResponse,
    summary="Request data export",
    description="Request export of all personal data (Subject Access Request)",
)
async def request_data_export(
    categories: Optional[List[DataCategory]] = None,
    current_user: User = Depends(get_current_user),
    privacy_service: PrivacyService = Depends(get_privacy_svc),
) -> PrivacyRequestResponse:
    """
    Request export of personal data.

    This creates an export request that will generate a downloadable archive
    of all personal data associated with the account.
    """
    privacy_request = await privacy_service.create_request(
        request_type=PrivacyRequestType.DATA_EXPORT,
        user_id=str(current_user.id),
        user_email=current_user.email,
        categories=categories or list(DataCategory),
    )

    # Process export immediately (could be async for large datasets)
    result = await privacy_service.process_export_request(
        request_id=privacy_request.id,
        format="zip",
    )

    # Update request with result
    privacy_request = privacy_service.get_request(privacy_request.id)

    return PrivacyRequestResponse(
        id=privacy_request.id,
        request_type=privacy_request.request_type,
        status=privacy_request.status,
        user_email=privacy_request.user_email,
        result_url=privacy_request.result_url,
        created_at=privacy_request.created_at,
        expires_at=privacy_request.expires_at,
    )


@router.get(
    "/exports/{request_id}/download",
    summary="Download data export",
    description="Download the exported data file",
)
async def download_data_export(
    request_id: str,
    current_user: User = Depends(get_current_user),
    privacy_service: PrivacyService = Depends(get_privacy_svc),
):
    """Download an exported data file."""
    privacy_request = privacy_service.get_request(request_id)

    if not privacy_request:
        raise HTTPException(status_code=404, detail="Export not found")

    if privacy_request.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    if privacy_request.status != PrivacyRequestStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Export not ready")

    # In production, this would return the file from S3
    raise HTTPException(status_code=501, detail="Download not implemented yet")


# =============================================================================
# Data Retention Policy Endpoints (Admin)
# =============================================================================

@router.get(
    "/retention/policies",
    response_model=List[RetentionPolicyResponse],
    summary="List retention policies",
    description="List all data retention policies",
)
async def list_retention_policies(
    current_user: User = Depends(get_current_admin_user),
    retention_service: DataRetentionService = Depends(get_retention_svc),
) -> List[RetentionPolicyResponse]:
    """List all retention policies."""
    policies = retention_service.list_policies()

    return [
        RetentionPolicyResponse(
            resource_type=p.resource_type,
            retention_days=p.retention_days,
            action=p.action,
            enabled=p.enabled,
            tenant_id=p.tenant_id,
            description=p.description,
            grace_period_days=p.grace_period_days,
            exclude_if_referenced=p.exclude_if_referenced,
            exclude_starred=p.exclude_starred,
        )
        for p in policies
    ]


@router.put(
    "/retention/policies/{resource_type}",
    response_model=RetentionPolicyResponse,
    summary="Update retention policy",
    description="Create or update a data retention policy",
)
async def update_retention_policy(
    resource_type: RetentionResourceType,
    policy_data: RetentionPolicyCreate,
    current_user: User = Depends(get_current_admin_user),
    retention_service: DataRetentionService = Depends(get_retention_svc),
) -> RetentionPolicyResponse:
    """Create or update a retention policy."""
    policy = RetentionPolicy(
        resource_type=resource_type,
        retention_days=policy_data.retention_days,
        action=policy_data.action,
        enabled=policy_data.enabled,
        description=policy_data.description,
        grace_period_days=policy_data.grace_period_days,
        exclude_if_referenced=policy_data.exclude_if_referenced,
        exclude_starred=policy_data.exclude_starred,
    )

    retention_service.set_policy(policy)

    return RetentionPolicyResponse(
        resource_type=policy.resource_type,
        retention_days=policy.retention_days,
        action=policy.action,
        enabled=policy.enabled,
        tenant_id=policy.tenant_id,
        description=policy.description,
        grace_period_days=policy.grace_period_days,
        exclude_if_referenced=policy.exclude_if_referenced,
        exclude_starred=policy.exclude_starred,
    )


@router.post(
    "/retention/enforce",
    response_model=List[RetentionEnforcementResponse],
    summary="Enforce retention policies",
    description="Manually trigger retention policy enforcement (admin only)",
)
async def enforce_retention_policies(
    resource_type: Optional[RetentionResourceType] = None,
    dry_run: bool = Query(True, description="If true, don't actually delete data"),
    current_user: User = Depends(get_current_admin_user),
    retention_service: DataRetentionService = Depends(get_retention_svc),
) -> List[RetentionEnforcementResponse]:
    """Manually enforce retention policies."""
    if resource_type:
        results = [
            await retention_service.enforce_policy(
                resource_type=resource_type,
                dry_run=dry_run,
            )
        ]
    else:
        results = await retention_service.enforce_all_policies(dry_run=dry_run)

    return [
        RetentionEnforcementResponse(
            resource_type=r.resource_type,
            action=r.action,
            items_processed=r.items_processed,
            items_deleted=r.items_deleted,
            items_archived=r.items_archived,
            items_anonymized=r.items_anonymized,
            items_skipped=r.items_skipped,
            errors=r.errors,
            duration_seconds=r.duration_seconds,
        )
        for r in results
    ]


# =============================================================================
# Compliance Info Endpoints
# =============================================================================

@router.get(
    "/compliance/rights",
    summary="Get privacy rights information",
    description="Get information about user privacy rights",
)
async def get_privacy_rights() -> dict:
    """Get information about privacy rights available to users."""
    return {
        "rights": [
            {
                "name": "Right of Access",
                "article": "GDPR Article 15",
                "description": "You can request a copy of all personal data we hold about you.",
                "endpoint": "/api/v1/privacy/export-my-data",
            },
            {
                "name": "Right to Rectification",
                "article": "GDPR Article 16",
                "description": "You can request correction of inaccurate personal data.",
                "endpoint": "/api/v1/users/me",
            },
            {
                "name": "Right to Erasure",
                "article": "GDPR Article 17",
                "description": "You can request deletion of your personal data.",
                "endpoint": "/api/v1/privacy/delete-my-data",
            },
            {
                "name": "Right to Data Portability",
                "article": "GDPR Article 20",
                "description": "You can receive your data in a machine-readable format.",
                "endpoint": "/api/v1/privacy/export-my-data",
            },
        ],
        "contact": "privacy@agentverse.ai",
        "dpo": "Data Protection Officer contact available on request",
    }


@router.get(
    "/compliance/data-categories",
    summary="Get data categories",
    description="Get list of personal data categories we collect",
)
async def get_data_categories() -> dict:
    """Get information about data categories."""
    return {
        "categories": [
            {
                "name": DataCategory.IDENTITY.value,
                "description": "Name, email, username",
                "retention": "Account lifetime + 30 days",
                "legal_basis": "Contract performance",
            },
            {
                "name": DataCategory.BEHAVIORAL.value,
                "description": "Usage patterns, preferences, session data",
                "retention": "90 days",
                "legal_basis": "Legitimate interest",
            },
            {
                "name": DataCategory.SIMULATION.value,
                "description": "Simulation configurations, results, personas",
                "retention": "2 years",
                "legal_basis": "Contract performance",
            },
            {
                "name": DataCategory.TECHNICAL.value,
                "description": "IP address, device info, logs",
                "retention": "90 days",
                "legal_basis": "Legitimate interest (security)",
            },
        ],
    }
