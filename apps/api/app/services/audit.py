"""
Audit Logging Service
Reference: project.md §8 (Security - Auditing)

Provides:
- Structured audit logging for all resource operations
- Actor tracking (user, system, API key)
- Change diff recording
- Tenant-scoped audit trails
- Async batch writing for performance
- Legacy organization-based audit (backward compatible)
"""

import asyncio
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Any, Callable
from uuid import UUID, uuid4
from dataclasses import dataclass, field

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from app.models.organization import AuditLog, AuditAction
from app.models.user import User

logger = structlog.get_logger()


# =============================================================================
# Enhanced Audit Types (project.md §8 compliant)
# =============================================================================

class TenantAuditAction(str, Enum):
    """Types of auditable actions (spec-compliant)."""
    # CRUD operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    # Simulation operations
    RUN_START = "run_start"
    RUN_COMPLETE = "run_complete"
    RUN_CANCEL = "run_cancel"
    RUN_FAIL = "run_fail"

    # Node/Universe operations (C1 - fork not mutate)
    NODE_FORK = "node_fork"
    NODE_EXPAND = "node_expand"
    NODE_ARCHIVE = "node_archive"

    # Auth operations
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"

    # Admin operations
    PERMISSION_CHANGE = "permission_change"
    ROLE_CHANGE = "role_change"
    MEMBER_INVITE = "member_invite"
    MEMBER_REMOVE = "member_remove"

    # Export/Import
    EXPORT = "export"
    IMPORT = "import"

    # System
    SYSTEM_EVENT = "system_event"


class AuditResourceType(str, Enum):
    """Types of auditable resources (spec-compliant)."""
    USER = "user"
    TENANT = "tenant"
    PROJECT = "project"
    PERSONA = "persona"
    AGENT = "agent"
    EVENT_SCRIPT = "event_script"
    RUN = "run"
    NODE = "node"
    TELEMETRY = "telemetry"
    RELIABILITY_REPORT = "reliability_report"
    API_KEY = "api_key"
    ORGANIZATION = "organization"
    MEMBERSHIP = "membership"
    SETTINGS = "settings"
    SYSTEM = "system"


class AuditActorType(str, Enum):
    """Types of actors that can perform actions."""
    USER = "user"
    API_KEY = "api_key"
    SYSTEM = "system"
    SCHEDULER = "scheduler"


@dataclass
class AuditActor:
    """Represents the actor performing an action."""
    type: AuditActorType
    id: Optional[str] = None
    name: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "id": self.id,
            "name": self.name,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }


@dataclass
class AuditChange:
    """Represents a change to a resource."""
    field: str
    old_value: Any = None
    new_value: Any = None

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "old_value": self._serialize(self.old_value),
            "new_value": self._serialize(self.new_value),
        }

    @staticmethod
    def _serialize(value: Any) -> Any:
        """Serialize value to JSON-compatible format."""
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, (list, tuple)):
            return [AuditChange._serialize(v) for v in value]
        if isinstance(value, dict):
            return {k: AuditChange._serialize(v) for k, v in value.items()}
        return str(value)


@dataclass
class AuditEntry:
    """A complete audit log entry."""
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: Optional[str] = None

    # Action details
    action: TenantAuditAction = TenantAuditAction.SYSTEM_EVENT
    resource_type: AuditResourceType = AuditResourceType.SYSTEM
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None

    # Actor details
    actor: Optional[AuditActor] = None

    # Change details
    changes: list = field(default_factory=list)

    # Context
    description: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    # Request context
    request_id: Optional[str] = None
    session_id: Optional[str] = None

    # Status
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": self.tenant_id,
            "action": self.action.value if isinstance(self.action, Enum) else self.action,
            "resource_type": self.resource_type.value if isinstance(self.resource_type, Enum) else self.resource_type,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "actor": self.actor.to_dict() if self.actor else None,
            "changes": [c.to_dict() if hasattr(c, 'to_dict') else c for c in self.changes],
            "description": self.description,
            "metadata": self.metadata,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "success": self.success,
            "error_message": self.error_message,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


# =============================================================================
# Tenant-Aware Audit Logger (new spec-compliant approach)
# =============================================================================

class TenantAuditLogger:
    """
    Tenant-aware audit logging service.

    Features:
    - Async batch writing for performance
    - Tenant-scoped logging
    - Automatic context extraction
    - Change diff computation
    """

    def __init__(self, batch_size: int = 100, flush_interval: float = 5.0):
        self._batch: List[AuditEntry] = []
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._db_session_factory: Optional[Callable] = None

    def set_db_session_factory(self, factory: Callable):
        """Set the database session factory for persistence."""
        self._db_session_factory = factory

    def _get_current_context(self) -> tuple:
        """Extract current tenant and actor from context."""
        try:
            from app.middleware.tenant import get_tenant_context
            ctx = get_tenant_context()

            if not ctx:
                return None, AuditActor(type=AuditActorType.SYSTEM)

            tenant_id = ctx.tenant_id

            if ctx.is_system:
                actor = AuditActor(
                    type=AuditActorType.SYSTEM,
                    id="system",
                    name="System",
                )
            elif ctx.user_id:
                actor = AuditActor(
                    type=AuditActorType.USER,
                    id=ctx.user_id,
                )
            else:
                actor = AuditActor(type=AuditActorType.SYSTEM)

            return tenant_id, actor
        except Exception:
            return None, AuditActor(type=AuditActorType.SYSTEM)

    async def log(
        self,
        action: TenantAuditAction,
        resource_type: AuditResourceType,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        changes: Optional[List[AuditChange]] = None,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        actor: Optional[AuditActor] = None,
        tenant_id: Optional[str] = None,
    ) -> AuditEntry:
        """
        Log an audit entry.

        Args:
            action: The action being performed
            resource_type: Type of resource being acted upon
            resource_id: ID of the resource
            resource_name: Human-readable name of the resource
            changes: List of field changes (for updates)
            description: Human-readable description of the action
            metadata: Additional context data
            success: Whether the action succeeded
            error_message: Error message if action failed
            actor: Override actor (uses context if not provided)
            tenant_id: Override tenant (uses context if not provided)

        Returns:
            The created audit entry
        """
        # Get context if not provided
        ctx_tenant_id, ctx_actor = self._get_current_context()

        entry = AuditEntry(
            tenant_id=tenant_id or ctx_tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            actor=actor or ctx_actor,
            changes=changes or [],
            description=description,
            metadata=metadata or {},
            success=success,
            error_message=error_message,
        )

        # Add to batch
        async with self._lock:
            self._batch.append(entry)

            if len(self._batch) >= self._batch_size:
                await self._flush()

        # Log to structured logger as well
        log_method = logger.info if success else logger.warning
        log_method(
            "audit_log",
            action=action.value,
            resource_type=resource_type.value,
            resource_id=resource_id,
            tenant_id=entry.tenant_id,
            success=success,
            error_message=error_message,
        )

        return entry

    async def log_create(
        self,
        resource_type: AuditResourceType,
        resource_id: str,
        resource_name: Optional[str] = None,
        data: Optional[dict] = None,
        description: Optional[str] = None,
    ) -> AuditEntry:
        """Log a resource creation."""
        changes = []
        if data:
            for key, value in data.items():
                if not key.startswith("_") and key not in ("password", "secret", "token"):
                    changes.append(AuditChange(field=key, new_value=value))

        return await self.log(
            action=TenantAuditAction.CREATE,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            changes=changes,
            description=description or f"Created {resource_type.value}",
        )

    async def log_update(
        self,
        resource_type: AuditResourceType,
        resource_id: str,
        old_data: Optional[dict] = None,
        new_data: Optional[dict] = None,
        changes: Optional[List[AuditChange]] = None,
        resource_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> AuditEntry:
        """Log a resource update."""
        if not changes and old_data and new_data:
            changes = self.compute_diff(old_data, new_data)

        return await self.log(
            action=TenantAuditAction.UPDATE,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            changes=changes or [],
            description=description or f"Updated {resource_type.value}",
        )

    async def log_delete(
        self,
        resource_type: AuditResourceType,
        resource_id: str,
        resource_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> AuditEntry:
        """Log a resource deletion."""
        return await self.log(
            action=TenantAuditAction.DELETE,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            description=description or f"Deleted {resource_type.value}",
        )

    async def log_run_start(
        self,
        run_id: str,
        run_name: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> AuditEntry:
        """Log a simulation run start."""
        return await self.log(
            action=TenantAuditAction.RUN_START,
            resource_type=AuditResourceType.RUN,
            resource_id=run_id,
            resource_name=run_name,
            metadata={"config": config} if config else {},
            description=f"Started run {run_name or run_id}",
        )

    async def log_run_complete(
        self,
        run_id: str,
        run_name: Optional[str] = None,
        result_summary: Optional[dict] = None,
    ) -> AuditEntry:
        """Log a simulation run completion."""
        return await self.log(
            action=TenantAuditAction.RUN_COMPLETE,
            resource_type=AuditResourceType.RUN,
            resource_id=run_id,
            resource_name=run_name,
            metadata={"result_summary": result_summary} if result_summary else {},
            description=f"Completed run {run_name or run_id}",
        )

    async def log_node_fork(
        self,
        parent_node_id: str,
        child_node_id: str,
        fork_config: Optional[dict] = None,
    ) -> AuditEntry:
        """Log a node fork operation (C1 - fork not mutate)."""
        return await self.log(
            action=TenantAuditAction.NODE_FORK,
            resource_type=AuditResourceType.NODE,
            resource_id=child_node_id,
            metadata={
                "parent_node_id": parent_node_id,
                "fork_config": fork_config or {},
            },
            description=f"Forked node {parent_node_id} → {child_node_id}",
        )

    async def log_auth(
        self,
        action: TenantAuditAction,
        user_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AuditEntry:
        """Log an authentication event."""
        return await self.log(
            action=action,
            resource_type=AuditResourceType.USER,
            resource_id=user_id,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )

    @staticmethod
    def compute_diff(
        old_data: dict,
        new_data: dict,
        exclude_fields: Optional[set] = None,
    ) -> List[AuditChange]:
        """
        Compute the difference between two data dictionaries.

        Args:
            old_data: Previous state
            new_data: New state
            exclude_fields: Fields to exclude from diff

        Returns:
            List of changes
        """
        exclude = exclude_fields or {"updated_at", "password", "secret", "token"}
        changes = []

        all_keys = set(old_data.keys()) | set(new_data.keys())

        for key in all_keys:
            if key in exclude or key.startswith("_"):
                continue

            old_value = old_data.get(key)
            new_value = new_data.get(key)

            if old_value != new_value:
                changes.append(AuditChange(
                    field=key,
                    old_value=old_value,
                    new_value=new_value,
                ))

        return changes

    async def _flush(self) -> None:
        """Flush batch to storage."""
        if not self._batch:
            return

        entries = self._batch.copy()
        self._batch.clear()

        # Write to database if session factory available
        if self._db_session_factory:
            try:
                await self._write_to_db(entries)
            except Exception as e:
                logger.error("Failed to write audit logs to database", error=str(e))
                # Re-add to batch for retry
                self._batch.extend(entries)

    async def _write_to_db(self, entries: List[AuditEntry]) -> None:
        """Write entries to database."""
        if not entries or not self._db_session_factory:
            return

        try:
            async with self._db_session_factory() as session:
                for entry in entries:
                    # Use the existing AuditLog model for storage
                    audit_log = AuditLog(
                        id=UUID(entry.id),
                        organization_id=UUID(entry.tenant_id) if entry.tenant_id else None,
                        user_id=UUID(entry.actor.id) if entry.actor and entry.actor.id else None,
                        action=entry.action.value if isinstance(entry.action, Enum) else entry.action,
                        resource_type=entry.resource_type.value if isinstance(entry.resource_type, Enum) else entry.resource_type,
                        resource_id=UUID(entry.resource_id) if entry.resource_id else None,
                        details={
                            "changes": [c.to_dict() if hasattr(c, 'to_dict') else c for c in entry.changes],
                            "metadata": entry.metadata,
                            "description": entry.description,
                            "success": entry.success,
                            "error_message": entry.error_message,
                        },
                        ip_address=entry.actor.ip_address if entry.actor else None,
                        user_agent=entry.actor.user_agent if entry.actor else None,
                    )
                    session.add(audit_log)

                await session.commit()
        except Exception as e:
            logger.error("Failed to write audit logs", error=str(e))

    async def query(
        self,
        tenant_id: str,
        resource_type: Optional[AuditResourceType] = None,
        resource_id: Optional[str] = None,
        action: Optional[TenantAuditAction] = None,
        actor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """
        Query audit logs.

        Args:
            tenant_id: Tenant to query (required for isolation)
            resource_type: Filter by resource type
            resource_id: Filter by specific resource
            action: Filter by action type
            actor_id: Filter by actor
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Max results
            offset: Pagination offset

        Returns:
            List of audit entries as dictionaries
        """
        if not self._db_session_factory:
            return []

        async with self._db_session_factory() as session:
            conditions = [AuditLog.organization_id == UUID(tenant_id)]

            if resource_type:
                conditions.append(AuditLog.resource_type == resource_type.value)
            if resource_id:
                conditions.append(AuditLog.resource_id == UUID(resource_id))
            if action:
                conditions.append(AuditLog.action == action.value)
            if actor_id:
                conditions.append(AuditLog.user_id == UUID(actor_id))
            if start_time:
                conditions.append(AuditLog.created_at >= start_time)
            if end_time:
                conditions.append(AuditLog.created_at <= end_time)

            query = (
                select(AuditLog)
                .where(and_(*conditions))
                .order_by(desc(AuditLog.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(query)
            logs = result.scalars().all()

            return [
                {
                    "id": str(log.id),
                    "timestamp": log.created_at.isoformat() if log.created_at else None,
                    "tenant_id": str(log.organization_id) if log.organization_id else None,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": str(log.resource_id) if log.resource_id else None,
                    "actor_id": str(log.user_id) if log.user_id else None,
                    "details": log.details,
                    "ip_address": log.ip_address,
                }
                for log in logs
            ]

    async def start_background_flush(self) -> None:
        """Start background task to periodically flush logs."""
        async def flush_loop():
            while True:
                await asyncio.sleep(self._flush_interval)
                async with self._lock:
                    await self._flush()

        self._flush_task = asyncio.create_task(flush_loop())

    async def stop(self) -> None:
        """Stop the audit logger and flush remaining logs."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            await self._flush()


# Global tenant audit logger instance
_tenant_audit_logger: Optional[TenantAuditLogger] = None


def get_tenant_audit_logger() -> TenantAuditLogger:
    """Get the global tenant audit logger singleton."""
    global _tenant_audit_logger
    if _tenant_audit_logger is None:
        _tenant_audit_logger = TenantAuditLogger()
    return _tenant_audit_logger


# Convenience functions for common audit operations
async def audit_create(
    resource_type: AuditResourceType,
    resource_id: str,
    resource_name: Optional[str] = None,
    data: Optional[dict] = None,
) -> AuditEntry:
    """Log a resource creation."""
    return await get_tenant_audit_logger().log_create(
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        data=data,
    )


async def audit_update(
    resource_type: AuditResourceType,
    resource_id: str,
    old_data: Optional[dict] = None,
    new_data: Optional[dict] = None,
    resource_name: Optional[str] = None,
) -> AuditEntry:
    """Log a resource update."""
    return await get_tenant_audit_logger().log_update(
        resource_type=resource_type,
        resource_id=resource_id,
        old_data=old_data,
        new_data=new_data,
        resource_name=resource_name,
    )


async def audit_delete(
    resource_type: AuditResourceType,
    resource_id: str,
    resource_name: Optional[str] = None,
) -> AuditEntry:
    """Log a resource deletion."""
    return await get_tenant_audit_logger().log_delete(
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
    )


# =============================================================================
# Legacy Organization-Based Audit Service (backward compatible)
# =============================================================================

class AuditService:
    """Service for creating and querying audit logs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        organization_id: UUID,
        action: AuditAction,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        log_entry = AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action=action.value,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry

    async def log_org_created(
        self,
        organization_id: UUID,
        user_id: UUID,
        org_name: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log organization creation."""
        return await self.log(
            organization_id=organization_id,
            action=AuditAction.ORG_CREATED,
            user_id=user_id,
            resource_type="organization",
            resource_id=organization_id,
            details={"organization_name": org_name},
            ip_address=ip_address,
        )

    async def log_org_updated(
        self,
        organization_id: UUID,
        user_id: UUID,
        changes: dict,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log organization update."""
        return await self.log(
            organization_id=organization_id,
            action=AuditAction.ORG_UPDATED,
            user_id=user_id,
            resource_type="organization",
            resource_id=organization_id,
            details={"changes": changes},
            ip_address=ip_address,
        )

    async def log_member_invited(
        self,
        organization_id: UUID,
        user_id: UUID,
        invited_email: str,
        role: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log member invitation."""
        return await self.log(
            organization_id=organization_id,
            action=AuditAction.MEMBER_INVITED,
            user_id=user_id,
            details={"invited_email": invited_email, "role": role},
            ip_address=ip_address,
        )

    async def log_member_joined(
        self,
        organization_id: UUID,
        user_id: UUID,
        role: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log member joining organization."""
        return await self.log(
            organization_id=organization_id,
            action=AuditAction.MEMBER_JOINED,
            user_id=user_id,
            details={"role": role},
            ip_address=ip_address,
        )

    async def log_member_removed(
        self,
        organization_id: UUID,
        actor_id: UUID,
        removed_user_id: UUID,
        removed_email: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log member removal from organization."""
        return await self.log(
            organization_id=organization_id,
            action=AuditAction.MEMBER_REMOVED,
            user_id=actor_id,
            details={
                "removed_user_id": str(removed_user_id),
                "removed_email": removed_email,
            },
            ip_address=ip_address,
        )

    async def log_member_role_changed(
        self,
        organization_id: UUID,
        actor_id: UUID,
        target_user_id: UUID,
        old_role: str,
        new_role: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log member role change."""
        return await self.log(
            organization_id=organization_id,
            action=AuditAction.MEMBER_ROLE_CHANGED,
            user_id=actor_id,
            details={
                "target_user_id": str(target_user_id),
                "old_role": old_role,
                "new_role": new_role,
            },
            ip_address=ip_address,
        )

    async def log_project_created(
        self,
        organization_id: UUID,
        user_id: UUID,
        project_id: UUID,
        project_name: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log project creation."""
        return await self.log(
            organization_id=organization_id,
            action=AuditAction.PROJECT_CREATED,
            user_id=user_id,
            resource_type="project",
            resource_id=project_id,
            details={"project_name": project_name},
            ip_address=ip_address,
        )

    async def log_simulation_run(
        self,
        organization_id: UUID,
        user_id: UUID,
        simulation_id: UUID,
        scenario_name: str,
        agent_count: int,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log simulation execution."""
        return await self.log(
            organization_id=organization_id,
            action=AuditAction.SIMULATION_RUN,
            user_id=user_id,
            resource_type="simulation",
            resource_id=simulation_id,
            details={
                "scenario_name": scenario_name,
                "agent_count": agent_count,
            },
            ip_address=ip_address,
        )

    async def log_settings_updated(
        self,
        organization_id: UUID,
        user_id: UUID,
        setting_type: str,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log settings update."""
        return await self.log(
            organization_id=organization_id,
            action=AuditAction.SETTINGS_UPDATED,
            user_id=user_id,
            details={"setting_type": setting_type},
            ip_address=ip_address,
        )

    async def get_logs(
        self,
        organization_id: UUID,
        action: Optional[str] = None,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[AuditLog], int]:
        """
        Get audit logs with filtering and pagination.
        Returns tuple of (logs, total_count).
        """
        # Build base query
        conditions = [AuditLog.organization_id == organization_id]

        if action:
            conditions.append(AuditLog.action == action)
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        if start_date:
            conditions.append(AuditLog.created_at >= start_date)
        if end_date:
            conditions.append(AuditLog.created_at <= end_date)

        # Count total
        from sqlalchemy import func
        count_result = await self.db.execute(
            select(func.count(AuditLog.id)).where(and_(*conditions))
        )
        total = count_result.scalar_one()

        # Get paginated results
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(AuditLog)
            .where(and_(*conditions))
            .order_by(desc(AuditLog.created_at))
            .offset(offset)
            .limit(page_size)
        )
        logs = list(result.scalars().all())

        return logs, total

    async def get_recent_activity(
        self,
        organization_id: UUID,
        limit: int = 10,
    ) -> List[AuditLog]:
        """Get recent activity for an organization."""
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def enrich_logs_with_users(
        self,
        logs: List[AuditLog],
    ) -> List[dict]:
        """Enrich audit logs with user email information."""
        if not logs:
            return []

        # Get unique user IDs
        user_ids = {log.user_id for log in logs if log.user_id}

        # Fetch users
        user_map = {}
        if user_ids:
            result = await self.db.execute(
                select(User).where(User.id.in_(user_ids))
            )
            users = result.scalars().all()
            user_map = {user.id: user.email for user in users}

        # Build enriched response
        enriched = []
        for log in logs:
            log_dict = {
                "id": log.id,
                "organization_id": log.organization_id,
                "user_id": log.user_id,
                "user_email": user_map.get(log.user_id) if log.user_id else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": log.created_at,
            }
            enriched.append(log_dict)

        return enriched
