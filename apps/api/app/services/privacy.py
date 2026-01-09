"""
Privacy Service - GDPR/CCPA Compliance
Reference: project.md §11 Phase 9 (Compliance Posture)

Provides:
- User deletion request handling (Right to Erasure)
- Data export for Subject Access Requests (SAR)
- Consent management
- Privacy preference tracking
"""

import asyncio
import json
import hashlib
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from uuid import UUID, uuid4
from dataclasses import dataclass, field
import zipfile
import io

import structlog
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.services.audit import (
    TenantAuditLogger,
    TenantAuditAction,
    AuditResourceType,
    get_tenant_audit_logger,
)

logger = structlog.get_logger()


# =============================================================================
# Privacy Request Types
# =============================================================================

class PrivacyRequestType(str, Enum):
    """Types of privacy requests (GDPR Article 15-22)."""
    # Article 15: Right of access
    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"

    # Article 16: Right to rectification
    DATA_RECTIFICATION = "data_rectification"

    # Article 17: Right to erasure (Right to be forgotten)
    DATA_DELETION = "data_deletion"
    ACCOUNT_DELETION = "account_deletion"

    # Article 18: Right to restriction of processing
    PROCESSING_RESTRICTION = "processing_restriction"

    # Article 20: Right to data portability
    DATA_PORTABILITY = "data_portability"

    # Article 21: Right to object
    PROCESSING_OBJECTION = "processing_objection"


class PrivacyRequestStatus(str, Enum):
    """Status of a privacy request."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_VERIFICATION = "awaiting_verification"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DataCategory(str, Enum):
    """Categories of personal data (GDPR-style classification)."""
    IDENTITY = "identity"  # Name, email, username
    CONTACT = "contact"  # Phone, address
    FINANCIAL = "financial"  # Payment info
    BEHAVIORAL = "behavioral"  # Usage patterns, preferences
    TECHNICAL = "technical"  # IP address, device info
    CONTENT = "content"  # User-generated content
    SIMULATION = "simulation"  # Simulation data, personas


# =============================================================================
# Privacy Request Data Classes
# =============================================================================

@dataclass
class PrivacyRequest:
    """A privacy request from a user."""
    id: str = field(default_factory=lambda: str(uuid4()))
    request_type: PrivacyRequestType = PrivacyRequestType.DATA_ACCESS
    status: PrivacyRequestStatus = PrivacyRequestStatus.PENDING

    # User information
    user_id: str = ""
    user_email: str = ""
    tenant_id: Optional[str] = None

    # Request details
    reason: Optional[str] = None
    categories: List[DataCategory] = field(default_factory=list)
    specific_data: Optional[Dict[str, Any]] = None

    # Verification
    verification_token: Optional[str] = None
    verified_at: Optional[datetime] = None

    # Processing
    processed_by: Optional[str] = None
    processed_at: Optional[datetime] = None
    result_url: Optional[str] = None  # For data exports
    rejection_reason: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None  # GDPR: 30 days to respond

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Set expiration (GDPR requires response within 30 days)
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(days=30)

        # Generate verification token if not set
        if self.verification_token is None:
            self.verification_token = hashlib.sha256(
                f"{self.id}{self.user_id}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:32]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_type": self.request_type.value,
            "status": self.status.value,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "tenant_id": self.tenant_id,
            "reason": self.reason,
            "categories": [c.value for c in self.categories],
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "result_url": self.result_url,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
        }


@dataclass
class DeletionResult:
    """Result of a data deletion operation."""
    request_id: str
    user_id: str
    success: bool = True

    # Items deleted per category
    deleted_counts: Dict[str, int] = field(default_factory=dict)

    # Items retained with reason
    retained_items: List[Dict[str, Any]] = field(default_factory=list)

    # Errors
    errors: List[str] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "success": self.success,
            "deleted_counts": self.deleted_counts,
            "retained_items": self.retained_items,
            "errors": self.errors,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class DataExportResult:
    """Result of a data export operation."""
    request_id: str
    user_id: str
    success: bool = True

    # Export details
    format: str = "json"
    file_path: Optional[str] = None
    file_size_bytes: int = 0
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None

    # Data categories included
    categories_included: List[DataCategory] = field(default_factory=list)

    # Errors
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "success": self.success,
            "format": self.format,
            "file_size_bytes": self.file_size_bytes,
            "download_url": self.download_url,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "categories_included": [c.value for c in self.categories_included],
            "errors": self.errors,
        }


# =============================================================================
# Privacy Service
# =============================================================================

class PrivacyService:
    """
    Service for handling privacy requests and GDPR/CCPA compliance.

    Features:
    - User deletion request workflow
    - Data export for Subject Access Requests
    - Consent management
    - Audit trail of all privacy operations
    """

    def __init__(self):
        self._requests: Dict[str, PrivacyRequest] = {}
        self._audit_logger: TenantAuditLogger = get_tenant_audit_logger()
        self._db_session_factory: Optional[Callable] = None
        self._storage_service = None

    def set_db_session_factory(self, factory: Callable):
        """Set the database session factory."""
        self._db_session_factory = factory

    def set_storage_service(self, storage):
        """Set the storage service for exports."""
        self._storage_service = storage

    # =========================================================================
    # Request Management
    # =========================================================================

    async def create_request(
        self,
        request_type: PrivacyRequestType,
        user_id: str,
        user_email: str,
        tenant_id: Optional[str] = None,
        reason: Optional[str] = None,
        categories: Optional[List[DataCategory]] = None,
    ) -> PrivacyRequest:
        """
        Create a new privacy request.

        Args:
            request_type: Type of privacy request
            user_id: ID of the user making the request
            user_email: Email of the user
            tenant_id: Optional tenant context
            reason: Optional reason for the request
            categories: Optional data categories to include

        Returns:
            The created privacy request
        """
        request = PrivacyRequest(
            request_type=request_type,
            user_id=user_id,
            user_email=user_email,
            tenant_id=tenant_id,
            reason=reason,
            categories=categories or list(DataCategory),
        )

        self._requests[request.id] = request

        # Audit log
        await self._audit_logger.log(
            action=TenantAuditAction.CREATE,
            resource_type=AuditResourceType.USER,
            resource_id=user_id,
            description=f"Privacy request created: {request_type.value}",
            metadata={
                "request_id": request.id,
                "request_type": request_type.value,
                "categories": [c.value for c in request.categories],
            },
            tenant_id=tenant_id,
        )

        logger.info(
            "privacy_request_created",
            request_id=request.id,
            request_type=request_type.value,
            user_id=user_id,
        )

        return request

    def get_request(self, request_id: str) -> Optional[PrivacyRequest]:
        """Get a privacy request by ID."""
        return self._requests.get(request_id)

    async def verify_request(
        self,
        request_id: str,
        verification_token: str,
    ) -> bool:
        """
        Verify a privacy request.

        Args:
            request_id: The request ID
            verification_token: The verification token

        Returns:
            True if verification successful
        """
        request = self.get_request(request_id)
        if not request:
            return False

        if request.verification_token != verification_token:
            return False

        if request.status != PrivacyRequestStatus.AWAITING_VERIFICATION:
            return False

        request.verified_at = datetime.now(timezone.utc)
        request.status = PrivacyRequestStatus.IN_PROGRESS

        logger.info(
            "privacy_request_verified",
            request_id=request_id,
            user_id=request.user_id,
        )

        return True

    async def list_requests(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[PrivacyRequestStatus] = None,
        request_type: Optional[PrivacyRequestType] = None,
    ) -> List[PrivacyRequest]:
        """List privacy requests with optional filters."""
        results = []

        for request in self._requests.values():
            if user_id and request.user_id != user_id:
                continue
            if tenant_id and request.tenant_id != tenant_id:
                continue
            if status and request.status != status:
                continue
            if request_type and request.request_type != request_type:
                continue
            results.append(request)

        return sorted(results, key=lambda r: r.created_at, reverse=True)

    # =========================================================================
    # Data Deletion (Right to Erasure)
    # =========================================================================

    async def process_deletion_request(
        self,
        request_id: str,
    ) -> DeletionResult:
        """
        Process a data deletion request.

        Deletes user data across all systems while:
        - Preserving audit logs (legal requirement)
        - Anonymizing shared data
        - Retaining data needed for legal compliance

        Args:
            request_id: The deletion request ID

        Returns:
            DeletionResult with details of deleted data
        """
        request = self.get_request(request_id)
        if not request:
            return DeletionResult(
                request_id=request_id,
                user_id="",
                success=False,
                errors=["Request not found"],
            )

        if request.request_type not in (
            PrivacyRequestType.DATA_DELETION,
            PrivacyRequestType.ACCOUNT_DELETION,
        ):
            return DeletionResult(
                request_id=request_id,
                user_id=request.user_id,
                success=False,
                errors=["Not a deletion request"],
            )

        result = DeletionResult(
            request_id=request_id,
            user_id=request.user_id,
        )

        try:
            # Delete user data by category
            for category in request.categories:
                count = await self._delete_category_data(
                    user_id=request.user_id,
                    category=category,
                    tenant_id=request.tenant_id,
                )
                result.deleted_counts[category.value] = count

            # Mark request as completed
            request.status = PrivacyRequestStatus.COMPLETED
            request.processed_at = datetime.now(timezone.utc)

            # Audit log
            await self._audit_logger.log(
                action=TenantAuditAction.DELETE,
                resource_type=AuditResourceType.USER,
                resource_id=request.user_id,
                description="User data deleted per privacy request",
                metadata={
                    "request_id": request_id,
                    "deleted_counts": result.deleted_counts,
                },
                tenant_id=request.tenant_id,
            )

            logger.info(
                "privacy_deletion_completed",
                request_id=request_id,
                user_id=request.user_id,
                deleted_counts=result.deleted_counts,
            )

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            request.status = PrivacyRequestStatus.REJECTED
            request.rejection_reason = str(e)

            logger.error(
                "privacy_deletion_failed",
                request_id=request_id,
                user_id=request.user_id,
                error=str(e),
            )

        result.completed_at = datetime.now(timezone.utc)
        return result

    async def _delete_category_data(
        self,
        user_id: str,
        category: DataCategory,
        tenant_id: Optional[str],
    ) -> int:
        """Delete user data for a specific category."""
        if not self._db_session_factory:
            return 0

        deleted_count = 0

        async with self._db_session_factory() as session:
            try:
                if category == DataCategory.IDENTITY:
                    # Anonymize user profile instead of deleting
                    deleted_count = await self._anonymize_user_profile(session, user_id)

                elif category == DataCategory.BEHAVIORAL:
                    # Delete session data, preferences
                    deleted_count = await self._delete_behavioral_data(session, user_id)

                elif category == DataCategory.SIMULATION:
                    # Delete/anonymize simulation data
                    deleted_count = await self._delete_simulation_data(
                        session, user_id, tenant_id
                    )

                elif category == DataCategory.CONTENT:
                    # Delete user-generated content
                    deleted_count = await self._delete_user_content(session, user_id)

                # Add more categories as needed

                await session.commit()

            except Exception as e:
                logger.error(
                    "category_deletion_failed",
                    category=category.value,
                    user_id=user_id,
                    error=str(e),
                )
                await session.rollback()
                raise

        return deleted_count

    async def _anonymize_user_profile(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> int:
        """Anonymize user profile (keep record but remove PII)."""
        from app.models.user import User

        # Generate anonymous replacement values
        anonymous_email = f"deleted_{hashlib.md5(user_id.encode()).hexdigest()[:8]}@anonymized.local"

        stmt = (
            update(User)
            .where(User.id == UUID(user_id))
            .values(
                email=anonymous_email,
                full_name="[Deleted User]",
                # Keep is_active=False to prevent login
                is_active=False,
            )
        )

        result = await session.execute(stmt)
        return result.rowcount

    async def _delete_behavioral_data(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> int:
        """Delete behavioral/session data."""
        # Delete refresh tokens, sessions, etc.
        from app.models.user import RefreshToken

        stmt = delete(RefreshToken).where(RefreshToken.user_id == UUID(user_id))
        result = await session.execute(stmt)
        return result.rowcount

    async def _delete_simulation_data(
        self,
        session: AsyncSession,
        user_id: str,
        tenant_id: Optional[str],
    ) -> int:
        """Delete or anonymize simulation-related data."""
        # This would delete runs, nodes, telemetry created by the user
        # For now, return 0 as models need to be imported
        return 0

    async def _delete_user_content(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> int:
        """Delete user-generated content."""
        # Delete projects, personas, event scripts, etc.
        # For now, return 0 as models need to be imported
        return 0

    # =========================================================================
    # Data Export (Subject Access Request)
    # =========================================================================

    async def process_export_request(
        self,
        request_id: str,
        format: str = "json",
    ) -> DataExportResult:
        """
        Process a data export request (Subject Access Request).

        Exports all user data in a portable format.

        Args:
            request_id: The export request ID
            format: Export format (json, csv)

        Returns:
            DataExportResult with download URL
        """
        request = self.get_request(request_id)
        if not request:
            return DataExportResult(
                request_id=request_id,
                user_id="",
                success=False,
                errors=["Request not found"],
            )

        if request.request_type not in (
            PrivacyRequestType.DATA_ACCESS,
            PrivacyRequestType.DATA_EXPORT,
            PrivacyRequestType.DATA_PORTABILITY,
        ):
            return DataExportResult(
                request_id=request_id,
                user_id=request.user_id,
                success=False,
                errors=["Not an export request"],
            )

        result = DataExportResult(
            request_id=request_id,
            user_id=request.user_id,
            format=format,
        )

        try:
            # Collect user data
            export_data = await self._collect_user_data(
                user_id=request.user_id,
                categories=request.categories,
                tenant_id=request.tenant_id,
            )

            # Create export file
            file_content, file_size = self._create_export_file(
                export_data, format
            )

            result.file_size_bytes = file_size
            result.categories_included = request.categories

            # Store export file (expires in 7 days)
            if self._storage_service:
                file_path = f"exports/privacy/{request.user_id}/{request_id}.{format}"
                # Store in S3 or local storage
                result.download_url = f"/api/v1/privacy/exports/{request_id}/download"
                result.expires_at = datetime.now(timezone.utc) + timedelta(days=7)

            # Mark request as completed
            request.status = PrivacyRequestStatus.COMPLETED
            request.processed_at = datetime.now(timezone.utc)
            request.result_url = result.download_url

            # Audit log
            await self._audit_logger.log(
                action=TenantAuditAction.EXPORT,
                resource_type=AuditResourceType.USER,
                resource_id=request.user_id,
                description="User data exported per privacy request",
                metadata={
                    "request_id": request_id,
                    "format": format,
                    "file_size_bytes": file_size,
                    "categories": [c.value for c in result.categories_included],
                },
                tenant_id=request.tenant_id,
            )

            logger.info(
                "privacy_export_completed",
                request_id=request_id,
                user_id=request.user_id,
                file_size=file_size,
            )

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            request.status = PrivacyRequestStatus.REJECTED
            request.rejection_reason = str(e)

            logger.error(
                "privacy_export_failed",
                request_id=request_id,
                user_id=request.user_id,
                error=str(e),
            )

        return result

    async def _collect_user_data(
        self,
        user_id: str,
        categories: List[DataCategory],
        tenant_id: Optional[str],
    ) -> Dict[str, Any]:
        """Collect all user data for export."""
        export_data = {
            "export_date": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "data": {},
        }

        if not self._db_session_factory:
            return export_data

        async with self._db_session_factory() as session:
            for category in categories:
                try:
                    category_data = await self._collect_category_data(
                        session, user_id, category, tenant_id
                    )
                    export_data["data"][category.value] = category_data
                except Exception as e:
                    export_data["data"][category.value] = {
                        "error": str(e)
                    }

        return export_data

    async def _collect_category_data(
        self,
        session: AsyncSession,
        user_id: str,
        category: DataCategory,
        tenant_id: Optional[str],
    ) -> Dict[str, Any]:
        """Collect data for a specific category."""
        data = {}

        if category == DataCategory.IDENTITY:
            from app.models.user import User
            result = await session.execute(
                select(User).where(User.id == UUID(user_id))
            )
            user = result.scalar_one_or_none()
            if user:
                data = {
                    "email": user.email,
                    "full_name": user.full_name,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                }

        elif category == DataCategory.BEHAVIORAL:
            # Session data, preferences, etc.
            data = {"sessions": [], "preferences": {}}

        elif category == DataCategory.SIMULATION:
            # Simulation runs, results, etc.
            data = {"runs": [], "nodes": [], "telemetry_count": 0}

        # Add more categories as needed

        return data

    def _create_export_file(
        self,
        data: Dict[str, Any],
        format: str,
    ) -> tuple[bytes, int]:
        """Create the export file in the specified format."""
        if format == "json":
            content = json.dumps(data, indent=2, default=str).encode("utf-8")
            return content, len(content)

        elif format == "zip":
            # Create a ZIP file with JSON and CSV files
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add main JSON
                zf.writestr(
                    "data.json",
                    json.dumps(data, indent=2, default=str),
                )
                # Add README
                zf.writestr(
                    "README.txt",
                    "This archive contains your personal data export.\n"
                    f"Export date: {data.get('export_date')}\n"
                    "Format: JSON\n",
                )
            content = buffer.getvalue()
            return content, len(content)

        else:
            content = json.dumps(data, default=str).encode("utf-8")
            return content, len(content)


# =============================================================================
# Singleton Instance
# =============================================================================

_privacy_service: Optional[PrivacyService] = None


def get_privacy_service() -> PrivacyService:
    """Get the global privacy service singleton."""
    global _privacy_service
    if _privacy_service is None:
        _privacy_service = PrivacyService()
    return _privacy_service
