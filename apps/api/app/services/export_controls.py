"""
Export Controls & Redaction Service
Reference: project.md §11 Phase 9

Provides:
- Export permission validation (role-based, project-level)
- Sensitive data redaction (PII, confidential fields)
- Export format support (JSON, CSV, Parquet)
- Export audit logging for compliance
- Privacy level enforcement (public/internal/confidential/restricted)
"""

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID

import structlog

from app.core.permissions import Permission, check_tenant_permission
from app.services.audit import (
    TenantAuditAction,
    AuditResourceType,
    get_tenant_audit_logger,
)

logger = structlog.get_logger()


# =============================================================================
# Privacy & Sensitivity Levels
# =============================================================================

class PrivacyLevel(str, Enum):
    """Privacy levels for project data (project.md §6.1)."""
    PUBLIC = "public"  # Can be exported without restrictions
    INTERNAL = "internal"  # Requires org membership
    CONFIDENTIAL = "confidential"  # Requires explicit export permission
    RESTRICTED = "restricted"  # Requires admin approval, redaction mandatory


class SensitivityType(str, Enum):
    """Types of sensitive data that may need redaction."""
    PII = "pii"  # Personally identifiable information
    FINANCIAL = "financial"  # Financial data
    HEALTH = "health"  # Health-related information
    BEHAVIORAL = "behavioral"  # Detailed behavioral patterns
    DEMOGRAPHIC = "demographic"  # Demographic details
    LOCATION = "location"  # Geographic/location data
    CONTACT = "contact"  # Contact information
    PREDICTION = "prediction"  # Model predictions
    CONFIDENCE = "confidence"  # Confidence scores
    INTERNAL = "internal"  # Internal system data


class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    EXCEL = "xlsx"


# =============================================================================
# Redaction Configuration
# =============================================================================

@dataclass
class RedactionRule:
    """A rule for redacting sensitive data."""
    name: str
    sensitivity_type: SensitivityType
    field_patterns: list[str]  # Regex patterns for field names
    value_patterns: Optional[list[str]] = None  # Regex patterns for values
    redaction_method: str = "mask"  # mask, hash, remove, generalize
    replacement: str = "[REDACTED]"

    def matches_field(self, field_name: str) -> bool:
        """Check if field name matches any pattern."""
        for pattern in self.field_patterns:
            if re.match(pattern, field_name, re.IGNORECASE):
                return True
        return False

    def matches_value(self, value: str) -> bool:
        """Check if value matches any pattern."""
        if not self.value_patterns:
            return False
        for pattern in self.value_patterns:
            if re.search(pattern, str(value), re.IGNORECASE):
                return True
        return False


# Default redaction rules
DEFAULT_REDACTION_RULES: list[RedactionRule] = [
    # PII
    RedactionRule(
        name="email",
        sensitivity_type=SensitivityType.PII,
        field_patterns=[r".*email.*", r".*e_mail.*"],
        value_patterns=[r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"],
        redaction_method="hash",
    ),
    RedactionRule(
        name="phone",
        sensitivity_type=SensitivityType.CONTACT,
        field_patterns=[r".*phone.*", r".*mobile.*", r".*cell.*", r".*tel.*"],
        value_patterns=[r"\+?\d[\d\s\-()]{7,}"],
        redaction_method="mask",
        replacement="[PHONE_REDACTED]",
    ),
    RedactionRule(
        name="ssn",
        sensitivity_type=SensitivityType.PII,
        field_patterns=[r".*ssn.*", r".*social_security.*", r".*nric.*", r".*ic_number.*"],
        redaction_method="remove",
    ),
    RedactionRule(
        name="address",
        sensitivity_type=SensitivityType.LOCATION,
        field_patterns=[r".*address.*", r".*street.*", r".*zip.*", r".*postal.*"],
        redaction_method="generalize",
        replacement="[LOCATION_REDACTED]",
    ),
    RedactionRule(
        name="name",
        sensitivity_type=SensitivityType.PII,
        field_patterns=[r"^name$", r"^full_name$", r".*first_name.*", r".*last_name.*", r".*surname.*"],
        redaction_method="hash",
    ),
    RedactionRule(
        name="dob",
        sensitivity_type=SensitivityType.PII,
        field_patterns=[r".*birth.*", r".*dob.*", r".*born.*"],
        redaction_method="generalize",
        replacement="[AGE_RANGE]",
    ),
    # Financial
    RedactionRule(
        name="income",
        sensitivity_type=SensitivityType.FINANCIAL,
        field_patterns=[r".*income.*", r".*salary.*", r".*wage.*", r".*earning.*"],
        redaction_method="generalize",
        replacement="[INCOME_RANGE]",
    ),
    RedactionRule(
        name="bank_account",
        sensitivity_type=SensitivityType.FINANCIAL,
        field_patterns=[r".*account.*number.*", r".*bank.*", r".*iban.*", r".*routing.*"],
        redaction_method="remove",
    ),
    RedactionRule(
        name="credit_card",
        sensitivity_type=SensitivityType.FINANCIAL,
        field_patterns=[r".*card.*number.*", r".*credit.*", r".*cvv.*"],
        value_patterns=[r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}"],
        redaction_method="remove",
    ),
    # Health
    RedactionRule(
        name="health",
        sensitivity_type=SensitivityType.HEALTH,
        field_patterns=[r".*health.*", r".*medical.*", r".*diagnosis.*", r".*condition.*"],
        redaction_method="remove",
    ),
    # Internal
    RedactionRule(
        name="internal_id",
        sensitivity_type=SensitivityType.INTERNAL,
        field_patterns=[r".*_id$", r"^id$", r".*uuid.*"],
        redaction_method="hash",
    ),
    RedactionRule(
        name="api_keys",
        sensitivity_type=SensitivityType.INTERNAL,
        field_patterns=[r".*api_key.*", r".*secret.*", r".*token.*", r".*password.*"],
        redaction_method="remove",
    ),
]


@dataclass
class RedactionConfig:
    """Configuration for data redaction."""
    enabled: bool = True
    rules: list[RedactionRule] = field(default_factory=lambda: DEFAULT_REDACTION_RULES.copy())
    custom_rules: list[RedactionRule] = field(default_factory=list)
    sensitivity_types_to_redact: set[SensitivityType] = field(
        default_factory=lambda: {
            SensitivityType.PII,
            SensitivityType.FINANCIAL,
            SensitivityType.HEALTH,
            SensitivityType.CONTACT,
        }
    )
    preserve_structure: bool = True  # Keep field names, redact values
    include_redaction_summary: bool = True

    def get_all_rules(self) -> list[RedactionRule]:
        """Get all active rules."""
        return self.rules + self.custom_rules


# =============================================================================
# Export Request & Result
# =============================================================================

@dataclass
class ExportRequest:
    """Request for data export."""
    tenant_id: str
    user_id: str
    project_id: Optional[str] = None
    resource_type: str = "telemetry"  # telemetry, personas, runs, nodes, etc.
    resource_ids: Optional[list[str]] = None  # Specific resources to export
    format: ExportFormat = ExportFormat.JSON
    redaction_config: Optional[RedactionConfig] = None
    include_metadata: bool = True
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None

    # Advanced options
    sample_size: Optional[int] = None  # Limit export size
    include_raw: bool = False  # Include raw telemetry (requires special permission)
    include_pii: bool = False  # Attempt to include PII (requires admin)


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    export_id: str
    format: ExportFormat
    data: Optional[bytes] = None
    file_path: Optional[str] = None  # If saved to storage
    record_count: int = 0
    redacted_field_count: int = 0
    error_message: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary (without data blob)."""
        return {
            "success": self.success,
            "export_id": self.export_id,
            "format": self.format.value,
            "record_count": self.record_count,
            "redacted_field_count": self.redacted_field_count,
            "error_message": self.error_message,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


# =============================================================================
# Export Permission Checker
# =============================================================================

class ExportPermissionChecker:
    """Validates export permissions based on role, project, and privacy level."""

    # Permission requirements by resource type
    RESOURCE_PERMISSIONS: dict[str, Permission] = {
        "telemetry": Permission.TELEMETRY_EXPORT,
        "personas": Permission.RESULT_EXPORT,
        "runs": Permission.RESULT_EXPORT,
        "nodes": Permission.RESULT_EXPORT,
        "reliability": Permission.RESULT_EXPORT,
        "audit": Permission.AUDIT_EXPORT,
        "project": Permission.RESULT_EXPORT,
    }

    # Privacy level requirements
    PRIVACY_LEVEL_REQUIREMENTS: dict[PrivacyLevel, list[str]] = {
        PrivacyLevel.PUBLIC: [],  # No special requirements
        PrivacyLevel.INTERNAL: ["org_membership"],
        PrivacyLevel.CONFIDENTIAL: ["export_permission", "org_membership"],
        PrivacyLevel.RESTRICTED: ["admin_role", "export_permission", "audit_trail"],
    }

    def __init__(
        self,
        user_permissions: list[str],
        user_role: str,
        is_admin: bool = False,
    ):
        self.user_permissions = user_permissions
        self.user_role = user_role
        self.is_admin = is_admin

    def can_export(
        self,
        resource_type: str,
        privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL,
        include_pii: bool = False,
        include_raw: bool = False,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if user can export the requested data.

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        # Admin can export everything
        if self.is_admin:
            return True, None

        # Check resource-specific permission
        required_permission = self.RESOURCE_PERMISSIONS.get(resource_type)
        if required_permission:
            if not check_tenant_permission(
                self.user_permissions,
                required_permission,
                self.is_admin,
            ):
                return False, f"Missing permission: {required_permission.value}"

        # Check privacy level requirements
        requirements = self.PRIVACY_LEVEL_REQUIREMENTS.get(
            privacy_level,
            self.PRIVACY_LEVEL_REQUIREMENTS[PrivacyLevel.INTERNAL],
        )

        if "admin_role" in requirements and self.user_role not in ("owner", "admin"):
            return False, f"Restricted data requires admin role"

        if "export_permission" in requirements:
            if Permission.RESULT_EXPORT.value not in self.user_permissions:
                return False, "Export permission required for confidential data"

        # PII export requires special permission
        if include_pii:
            if self.user_role not in ("owner", "admin"):
                return False, "PII export requires admin privileges"

        # Raw telemetry export requires special permission
        if include_raw:
            if Permission.TELEMETRY_EXPORT.value not in self.user_permissions:
                return False, "Raw telemetry export requires telemetry:export permission"

        return True, None

    def get_allowed_sensitivity_types(
        self,
        privacy_level: PrivacyLevel,
    ) -> set[SensitivityType]:
        """Get sensitivity types that can be exported without redaction."""
        allowed = set()

        # Public data allows everything except internal
        if privacy_level == PrivacyLevel.PUBLIC:
            allowed = set(SensitivityType) - {SensitivityType.INTERNAL}

        # Internal allows less
        elif privacy_level == PrivacyLevel.INTERNAL:
            allowed = {
                SensitivityType.PREDICTION,
                SensitivityType.CONFIDENCE,
                SensitivityType.BEHAVIORAL,
            }

        # Confidential with admin allows more
        elif privacy_level == PrivacyLevel.CONFIDENTIAL:
            if self.is_admin or self.user_role in ("owner", "admin"):
                allowed = {
                    SensitivityType.PREDICTION,
                    SensitivityType.CONFIDENCE,
                    SensitivityType.BEHAVIORAL,
                    SensitivityType.DEMOGRAPHIC,
                }

        # Restricted still redacts most things
        elif privacy_level == PrivacyLevel.RESTRICTED:
            if self.is_admin:
                allowed = {
                    SensitivityType.PREDICTION,
                    SensitivityType.CONFIDENCE,
                }

        return allowed


# =============================================================================
# Data Redactor
# =============================================================================

class DataRedactor:
    """Applies redaction rules to data before export."""

    def __init__(self, config: RedactionConfig):
        self.config = config
        self._redaction_count = 0
        self._redacted_fields: list[str] = []

    def redact(self, data: Any, path: str = "") -> Any:
        """
        Redact sensitive data recursively.

        Args:
            data: Data to redact (dict, list, or primitive)
            path: Current path for tracking redacted fields

        Returns:
            Redacted data
        """
        if not self.config.enabled:
            return data

        if isinstance(data, dict):
            return self._redact_dict(data, path)
        elif isinstance(data, list):
            return self._redact_list(data, path)
        elif isinstance(data, str):
            return self._redact_string(data, path)
        else:
            return data

    def _redact_dict(self, data: dict, path: str) -> dict:
        """Redact dictionary values."""
        result = {}

        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key

            # Check if field matches any redaction rule
            rule = self._find_matching_rule(key)

            if rule and rule.sensitivity_type in self.config.sensitivity_types_to_redact:
                result[key] = self._apply_redaction(value, rule)
                self._redaction_count += 1
                self._redacted_fields.append(current_path)
            elif isinstance(value, (dict, list)):
                result[key] = self.redact(value, current_path)
            else:
                # Check value patterns
                value_rule = self._find_matching_value_rule(str(value))
                if value_rule and value_rule.sensitivity_type in self.config.sensitivity_types_to_redact:
                    result[key] = self._apply_redaction(value, value_rule)
                    self._redaction_count += 1
                    self._redacted_fields.append(current_path)
                else:
                    result[key] = value

        return result

    def _redact_list(self, data: list, path: str) -> list:
        """Redact list items."""
        return [
            self.redact(item, f"{path}[{i}]")
            for i, item in enumerate(data)
        ]

    def _redact_string(self, data: str, path: str) -> str:
        """Redact string value if it matches patterns."""
        rule = self._find_matching_value_rule(data)
        if rule and rule.sensitivity_type in self.config.sensitivity_types_to_redact:
            self._redaction_count += 1
            self._redacted_fields.append(path)
            return self._apply_redaction(data, rule)
        return data

    def _find_matching_rule(self, field_name: str) -> Optional[RedactionRule]:
        """Find redaction rule matching field name."""
        for rule in self.config.get_all_rules():
            if rule.matches_field(field_name):
                return rule
        return None

    def _find_matching_value_rule(self, value: str) -> Optional[RedactionRule]:
        """Find redaction rule matching value pattern."""
        for rule in self.config.get_all_rules():
            if rule.matches_value(value):
                return rule
        return None

    def _apply_redaction(self, value: Any, rule: RedactionRule) -> Any:
        """Apply redaction method to value."""
        if rule.redaction_method == "remove":
            return None if self.config.preserve_structure else "[REMOVED]"

        elif rule.redaction_method == "mask":
            if isinstance(value, str) and len(value) > 4:
                return value[:2] + "*" * (len(value) - 4) + value[-2:]
            return rule.replacement

        elif rule.redaction_method == "hash":
            import hashlib
            if isinstance(value, str):
                hash_val = hashlib.sha256(value.encode()).hexdigest()[:8]
                return f"[HASH_{hash_val}]"
            return rule.replacement

        elif rule.redaction_method == "generalize":
            return rule.replacement

        return rule.replacement

    def get_redaction_summary(self) -> dict:
        """Get summary of redactions performed."""
        return {
            "redaction_count": self._redaction_count,
            "redacted_fields": self._redacted_fields[:100],  # Limit for large exports
            "total_unique_fields": len(set(f.split("[")[0] for f in self._redacted_fields)),
        }

    def reset_counts(self):
        """Reset redaction counters."""
        self._redaction_count = 0
        self._redacted_fields = []


# =============================================================================
# Export Service
# =============================================================================

class ExportService:
    """
    Main export service with permission checks, redaction, and audit logging.
    """

    def __init__(
        self,
        data_fetcher: Optional[Callable] = None,
        storage_saver: Optional[Callable] = None,
    ):
        self.data_fetcher = data_fetcher
        self.storage_saver = storage_saver
        self._audit_logger = get_tenant_audit_logger()

    async def export(self, request: ExportRequest) -> ExportResult:
        """
        Execute an export request.

        Args:
            request: Export request configuration

        Returns:
            ExportResult with data or error
        """
        from uuid import uuid4
        export_id = str(uuid4())

        try:
            # 1. Log export attempt
            await self._log_export_attempt(request, export_id)

            # 2. Validate permissions
            permission_result = await self._validate_permissions(request)
            if not permission_result[0]:
                return ExportResult(
                    success=False,
                    export_id=export_id,
                    format=request.format,
                    error_message=permission_result[1],
                )

            # 3. Fetch data
            data = await self._fetch_data(request)
            if data is None:
                return ExportResult(
                    success=False,
                    export_id=export_id,
                    format=request.format,
                    error_message="No data found for export",
                )

            # 4. Apply redaction
            redaction_config = request.redaction_config or RedactionConfig()
            redactor = DataRedactor(redaction_config)
            redacted_data = redactor.redact(data)
            redaction_summary = redactor.get_redaction_summary()

            # 5. Format output
            output = await self._format_output(redacted_data, request.format)

            # 6. Calculate record count
            record_count = len(data) if isinstance(data, list) else 1

            # 7. Log successful export
            await self._log_export_success(
                request=request,
                export_id=export_id,
                record_count=record_count,
                redaction_count=redaction_summary["redaction_count"],
            )

            # 8. Build result
            result = ExportResult(
                success=True,
                export_id=export_id,
                format=request.format,
                data=output,
                record_count=record_count,
                redacted_field_count=redaction_summary["redaction_count"],
                metadata={
                    "redaction_summary": redaction_summary if redaction_config.include_redaction_summary else {},
                    "export_timestamp": datetime.now(timezone.utc).isoformat(),
                    "resource_type": request.resource_type,
                },
            )

            # 9. Save to storage if configured
            if self.storage_saver:
                file_path = await self.storage_saver(
                    export_id=export_id,
                    data=output,
                    format=request.format,
                    tenant_id=request.tenant_id,
                )
                result.file_path = file_path

            return result

        except Exception as e:
            logger.error(
                "Export failed",
                export_id=export_id,
                error=str(e),
                resource_type=request.resource_type,
            )

            await self._log_export_failure(request, export_id, str(e))

            return ExportResult(
                success=False,
                export_id=export_id,
                format=request.format,
                error_message=f"Export failed: {str(e)}",
            )

    async def _validate_permissions(
        self,
        request: ExportRequest,
    ) -> tuple[bool, Optional[str]]:
        """Validate export permissions."""
        try:
            from app.middleware.tenant import get_tenant_context
            ctx = get_tenant_context()

            if not ctx:
                return False, "Authentication required"

            checker = ExportPermissionChecker(
                user_permissions=ctx.permissions,
                user_role=ctx.role or "viewer",
                is_admin=ctx.is_admin,
            )

            # Determine privacy level (would come from project settings)
            privacy_level = PrivacyLevel.INTERNAL

            return checker.can_export(
                resource_type=request.resource_type,
                privacy_level=privacy_level,
                include_pii=request.include_pii,
                include_raw=request.include_raw,
            )

        except Exception as e:
            logger.error("Permission validation failed", error=str(e))
            return False, f"Permission check failed: {str(e)}"

    async def _fetch_data(self, request: ExportRequest) -> Optional[Any]:
        """Fetch data for export."""
        if self.data_fetcher:
            return await self.data_fetcher(
                tenant_id=request.tenant_id,
                resource_type=request.resource_type,
                resource_ids=request.resource_ids,
                project_id=request.project_id,
                date_range_start=request.date_range_start,
                date_range_end=request.date_range_end,
                sample_size=request.sample_size,
            )

        # Return empty placeholder if no fetcher configured
        return []

    async def _format_output(
        self,
        data: Any,
        format: ExportFormat,
    ) -> bytes:
        """Format data for export."""
        if format == ExportFormat.JSON:
            return json.dumps(data, default=str, indent=2).encode("utf-8")

        elif format == ExportFormat.CSV:
            return self._to_csv(data)

        elif format == ExportFormat.PARQUET:
            return self._to_parquet(data)

        elif format == ExportFormat.EXCEL:
            return self._to_excel(data)

        raise ValueError(f"Unsupported format: {format}")

    def _to_csv(self, data: Any) -> bytes:
        """Convert data to CSV format."""
        if not isinstance(data, list):
            data = [data]

        if not data:
            return b""

        output = io.StringIO()

        # Get all possible headers
        headers = set()
        for item in data:
            if isinstance(item, dict):
                headers.update(item.keys())

        headers = sorted(headers)

        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()

        for item in data:
            if isinstance(item, dict):
                writer.writerow({k: str(v) if v is not None else "" for k, v in item.items()})

        return output.getvalue().encode("utf-8")

    def _to_parquet(self, data: Any) -> bytes:
        """Convert data to Parquet format (requires pyarrow)."""
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq

            if not isinstance(data, list):
                data = [data]

            if not data:
                return b""

            table = pa.Table.from_pylist(data)

            output = io.BytesIO()
            pq.write_table(table, output)
            return output.getvalue()

        except ImportError:
            # Fallback to JSON if pyarrow not available
            logger.warning("pyarrow not available, falling back to JSON")
            return json.dumps(data, default=str).encode("utf-8")

    def _to_excel(self, data: Any) -> bytes:
        """Convert data to Excel format (requires openpyxl)."""
        try:
            import openpyxl
            from openpyxl import Workbook

            if not isinstance(data, list):
                data = [data]

            wb = Workbook()
            ws = wb.active
            ws.title = "Export"

            if data:
                # Headers
                headers = sorted(set().union(*[d.keys() for d in data if isinstance(d, dict)]))
                ws.append(headers)

                # Data rows
                for item in data:
                    if isinstance(item, dict):
                        row = [str(item.get(h, "")) for h in headers]
                        ws.append(row)

            output = io.BytesIO()
            wb.save(output)
            return output.getvalue()

        except ImportError:
            # Fallback to CSV if openpyxl not available
            logger.warning("openpyxl not available, falling back to CSV")
            return self._to_csv(data)

    async def _log_export_attempt(
        self,
        request: ExportRequest,
        export_id: str,
    ) -> None:
        """Log export attempt for audit."""
        await self._audit_logger.log(
            action=TenantAuditAction.EXPORT,
            resource_type=AuditResourceType.TELEMETRY,
            resource_id=export_id,
            tenant_id=request.tenant_id,
            metadata={
                "export_type": request.resource_type,
                "format": request.format.value,
                "include_pii": request.include_pii,
                "include_raw": request.include_raw,
                "resource_count": len(request.resource_ids) if request.resource_ids else "all",
                "status": "attempted",
            },
            description=f"Export {request.resource_type} attempt",
        )

    async def _log_export_success(
        self,
        request: ExportRequest,
        export_id: str,
        record_count: int,
        redaction_count: int,
    ) -> None:
        """Log successful export for audit."""
        await self._audit_logger.log(
            action=TenantAuditAction.EXPORT,
            resource_type=AuditResourceType.TELEMETRY,
            resource_id=export_id,
            tenant_id=request.tenant_id,
            metadata={
                "export_type": request.resource_type,
                "format": request.format.value,
                "record_count": record_count,
                "redaction_count": redaction_count,
                "status": "completed",
            },
            description=f"Exported {record_count} {request.resource_type} records",
            success=True,
        )

    async def _log_export_failure(
        self,
        request: ExportRequest,
        export_id: str,
        error: str,
    ) -> None:
        """Log failed export for audit."""
        await self._audit_logger.log(
            action=TenantAuditAction.EXPORT,
            resource_type=AuditResourceType.TELEMETRY,
            resource_id=export_id,
            tenant_id=request.tenant_id,
            metadata={
                "export_type": request.resource_type,
                "format": request.format.value,
                "status": "failed",
            },
            description=f"Export {request.resource_type} failed: {error}",
            success=False,
            error_message=error,
        )


# =============================================================================
# Global Export Service Instance
# =============================================================================

_export_service: Optional[ExportService] = None


def get_export_service() -> ExportService:
    """Get global export service singleton."""
    global _export_service
    if _export_service is None:
        _export_service = ExportService()
    return _export_service


def configure_export_service(
    data_fetcher: Optional[Callable] = None,
    storage_saver: Optional[Callable] = None,
) -> ExportService:
    """Configure and return the export service."""
    global _export_service
    _export_service = ExportService(
        data_fetcher=data_fetcher,
        storage_saver=storage_saver,
    )
    return _export_service
