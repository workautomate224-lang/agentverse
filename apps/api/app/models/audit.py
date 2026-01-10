"""
Audit Models Stub

Provides compatibility interfaces for audit logging.
This module bridges calibration.py with the actual audit service.
"""

from enum import Enum
from typing import Optional, Any, Dict
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class TenantAuditAction(str, Enum):
    """Audit action types for calibration and reliability features."""
    # Calibration operations
    CALIBRATION_SCENARIO_CREATED = "calibration_scenario_created"
    CALIBRATION_RUN_COMPLETED = "calibration_run_completed"
    CALIBRATION_METRICS_VIEWED = "calibration_metrics_viewed"

    # Stability operations
    STABILITY_TEST_COMPLETED = "stability_test_completed"
    DRIFT_SCAN_COMPLETED = "drift_scan_completed"

    # Auto-tune operations
    AUTO_TUNE_COMPLETED = "auto_tune_completed"
    ROLLBACK_COMPLETED = "rollback_completed"

    # Reliability operations
    RELIABILITY_REPORT_DOWNLOADED = "reliability_report_downloaded"
    RELIABILITY_METRICS_VIEWED = "reliability_metrics_viewed"


class TenantAuditService:
    """
    Audit logging service for tenant operations.

    Provides a static interface for logging audit events.
    This stub logs to structlog for staging purposes.
    """

    @staticmethod
    async def log_action(
        db: AsyncSession,
        tenant_id: UUID,
        action: TenantAuditAction,
        user_id: UUID,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Log an audit action.

        Args:
            db: Database session (for transaction context)
            tenant_id: Tenant identifier
            action: Type of action being audited
            user_id: User performing the action
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional action details
        """
        logger.info(
            "audit_action",
            tenant_id=str(tenant_id),
            action=action.value if isinstance(action, Enum) else action,
            user_id=str(user_id),
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
