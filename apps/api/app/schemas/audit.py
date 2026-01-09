"""
Audit Log Schemas
Reference: GAPS.md GAP-P0-006

Pydantic schemas for audit log API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from enum import Enum

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class AuditActionType(str, Enum):
    """Types of auditable actions."""
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

    # Node/Universe operations
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

    # Legacy organization actions
    ORG_CREATED = "org_created"
    ORG_UPDATED = "org_updated"
    MEMBER_INVITED = "member_invited"
    MEMBER_JOINED = "member_joined"
    MEMBER_REMOVED = "member_removed"
    MEMBER_ROLE_CHANGED = "member_role_changed"
    PROJECT_CREATED = "project_created"
    SIMULATION_RUN = "simulation_run"
    SETTINGS_UPDATED = "settings_updated"

    # Export/Import
    EXPORT = "export"
    IMPORT = "import"

    # System
    SYSTEM_EVENT = "system_event"


class AuditResourceType(str, Enum):
    """Types of auditable resources."""
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
    SIMULATION = "simulation"
    SYSTEM = "system"


# =============================================================================
# Response Schemas
# =============================================================================

class AuditLogResponse(BaseModel):
    """Single audit log entry response."""
    id: str
    organization_id: Optional[str] = None
    tenant_id: Optional[str] = None  # Alias for organization_id
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated list of audit logs."""
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditLogStatsResponse(BaseModel):
    """Audit log statistics."""
    total_events: int
    events_today: int
    events_this_week: int
    events_by_action: Dict[str, int]
    events_by_resource_type: Dict[str, int]
    top_users: List[Dict[str, Any]]
    recent_activity_trend: List[Dict[str, Any]]


class AuditLogExportResponse(BaseModel):
    """Audit log export response."""
    filename: str
    format: str
    total_records: int
    download_url: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None


# =============================================================================
# Request Schemas
# =============================================================================

class AuditLogFilter(BaseModel):
    """Filter parameters for audit log queries."""
    action: Optional[str] = Field(None, description="Filter by action type")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[str] = Field(None, description="Filter by resource ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    ip_address: Optional[str] = Field(None, description="Filter by IP address")
    search: Optional[str] = Field(None, description="Search in details")
