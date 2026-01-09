"""
Role-Based Access Control (RBAC) system
Reference: project.md §8 (Security)

Supports both:
- Organization-based permissions (legacy)
- Tenant-based permissions (new, spec-compliant)
"""

from enum import Enum
from typing import Optional, Set
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
)


class Permission(str, Enum):
    """Available permissions in the system."""
    # Organization management (legacy)
    ORG_VIEW = "org:view"
    ORG_UPDATE = "org:update"
    ORG_DELETE = "org:delete"
    ORG_MANAGE_BILLING = "org:manage_billing"

    # Member management
    MEMBER_VIEW = "member:view"
    MEMBER_INVITE = "member:invite"
    MEMBER_REMOVE = "member:remove"
    MEMBER_UPDATE_ROLE = "member:update_role"

    # Project management (§6.1)
    PROJECT_CREATE = "project:create"
    PROJECT_VIEW = "project:view"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    PROJECT_SHARE = "project:share"

    # Persona management (§6.2)
    PERSONA_CREATE = "persona:create"
    PERSONA_VIEW = "persona:view"
    PERSONA_UPDATE = "persona:update"
    PERSONA_DELETE = "persona:delete"
    PERSONA_IMPORT = "persona:import"

    # Event Script management (§6.4)
    EVENT_CREATE = "event:create"
    EVENT_VIEW = "event:view"
    EVENT_UPDATE = "event:update"
    EVENT_DELETE = "event:delete"

    # Run management (§6.5, §6.6)
    RUN_CREATE = "run:create"
    RUN_VIEW = "run:view"
    RUN_CANCEL = "run:cancel"
    RUN_DELETE = "run:delete"

    # Node/Universe Map management (§6.7)
    NODE_VIEW = "node:view"
    NODE_EXPAND = "node:expand"
    NODE_FORK = "node:fork"
    NODE_DELETE = "node:delete"

    # Telemetry access (§6.8)
    TELEMETRY_VIEW = "telemetry:view"
    TELEMETRY_EXPORT = "telemetry:export"
    TELEMETRY_DELETE = "telemetry:delete"

    # Reliability reports (§7.1)
    RELIABILITY_VIEW = "reliability:view"
    RELIABILITY_COMPUTE = "reliability:compute"

    # Legacy simulation management (to be deprecated)
    SIMULATION_RUN = "simulation:run"
    SIMULATION_VIEW = "simulation:view"
    SIMULATION_DELETE = "simulation:delete"

    # Results access (legacy)
    RESULT_VIEW = "result:view"
    RESULT_EXPORT = "result:export"

    # Audit logs
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"

    # Settings
    SETTINGS_VIEW = "settings:view"
    SETTINGS_UPDATE = "settings:update"

    # API Keys (for M2M)
    API_KEY_CREATE = "api_key:create"
    API_KEY_VIEW = "api_key:view"
    API_KEY_REVOKE = "api_key:revoke"

    # Tenant management (admin only)
    TENANT_VIEW = "tenant:view"
    TENANT_UPDATE = "tenant:update"
    TENANT_MANAGE_QUOTA = "tenant:manage_quota"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[OrganizationRole, Set[Permission]] = {
    OrganizationRole.OWNER: {
        # Organization (legacy)
        Permission.ORG_VIEW,
        Permission.ORG_UPDATE,
        Permission.ORG_DELETE,
        Permission.ORG_MANAGE_BILLING,
        # Members
        Permission.MEMBER_VIEW,
        Permission.MEMBER_INVITE,
        Permission.MEMBER_REMOVE,
        Permission.MEMBER_UPDATE_ROLE,
        # Projects
        Permission.PROJECT_CREATE,
        Permission.PROJECT_VIEW,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_SHARE,
        # Personas
        Permission.PERSONA_CREATE,
        Permission.PERSONA_VIEW,
        Permission.PERSONA_UPDATE,
        Permission.PERSONA_DELETE,
        Permission.PERSONA_IMPORT,
        # Events
        Permission.EVENT_CREATE,
        Permission.EVENT_VIEW,
        Permission.EVENT_UPDATE,
        Permission.EVENT_DELETE,
        # Runs
        Permission.RUN_CREATE,
        Permission.RUN_VIEW,
        Permission.RUN_CANCEL,
        Permission.RUN_DELETE,
        # Nodes
        Permission.NODE_VIEW,
        Permission.NODE_EXPAND,
        Permission.NODE_FORK,
        Permission.NODE_DELETE,
        # Telemetry
        Permission.TELEMETRY_VIEW,
        Permission.TELEMETRY_EXPORT,
        Permission.TELEMETRY_DELETE,
        # Reliability
        Permission.RELIABILITY_VIEW,
        Permission.RELIABILITY_COMPUTE,
        # Legacy
        Permission.SIMULATION_RUN,
        Permission.SIMULATION_VIEW,
        Permission.SIMULATION_DELETE,
        Permission.RESULT_VIEW,
        Permission.RESULT_EXPORT,
        # Audit
        Permission.AUDIT_VIEW,
        Permission.AUDIT_EXPORT,
        # Settings
        Permission.SETTINGS_VIEW,
        Permission.SETTINGS_UPDATE,
        # API Keys
        Permission.API_KEY_CREATE,
        Permission.API_KEY_VIEW,
        Permission.API_KEY_REVOKE,
        # Tenant
        Permission.TENANT_VIEW,
        Permission.TENANT_UPDATE,
        Permission.TENANT_MANAGE_QUOTA,
    },
    OrganizationRole.ADMIN: {
        # Organization (limited)
        Permission.ORG_VIEW,
        Permission.ORG_UPDATE,
        # Members
        Permission.MEMBER_VIEW,
        Permission.MEMBER_INVITE,
        Permission.MEMBER_REMOVE,
        Permission.MEMBER_UPDATE_ROLE,
        # Projects
        Permission.PROJECT_CREATE,
        Permission.PROJECT_VIEW,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.PROJECT_SHARE,
        # Personas
        Permission.PERSONA_CREATE,
        Permission.PERSONA_VIEW,
        Permission.PERSONA_UPDATE,
        Permission.PERSONA_DELETE,
        Permission.PERSONA_IMPORT,
        # Events
        Permission.EVENT_CREATE,
        Permission.EVENT_VIEW,
        Permission.EVENT_UPDATE,
        Permission.EVENT_DELETE,
        # Runs
        Permission.RUN_CREATE,
        Permission.RUN_VIEW,
        Permission.RUN_CANCEL,
        Permission.RUN_DELETE,
        # Nodes
        Permission.NODE_VIEW,
        Permission.NODE_EXPAND,
        Permission.NODE_FORK,
        Permission.NODE_DELETE,
        # Telemetry
        Permission.TELEMETRY_VIEW,
        Permission.TELEMETRY_EXPORT,
        Permission.TELEMETRY_DELETE,
        # Reliability
        Permission.RELIABILITY_VIEW,
        Permission.RELIABILITY_COMPUTE,
        # Legacy
        Permission.SIMULATION_RUN,
        Permission.SIMULATION_VIEW,
        Permission.SIMULATION_DELETE,
        Permission.RESULT_VIEW,
        Permission.RESULT_EXPORT,
        # Audit
        Permission.AUDIT_VIEW,
        # Settings
        Permission.SETTINGS_VIEW,
        Permission.SETTINGS_UPDATE,
        # API Keys
        Permission.API_KEY_CREATE,
        Permission.API_KEY_VIEW,
        Permission.API_KEY_REVOKE,
        # Tenant (view only)
        Permission.TENANT_VIEW,
    },
    OrganizationRole.MEMBER: {
        # Organization (view only)
        Permission.ORG_VIEW,
        Permission.MEMBER_VIEW,
        # Projects
        Permission.PROJECT_CREATE,
        Permission.PROJECT_VIEW,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_SHARE,
        # Personas
        Permission.PERSONA_CREATE,
        Permission.PERSONA_VIEW,
        Permission.PERSONA_UPDATE,
        Permission.PERSONA_IMPORT,
        # Events
        Permission.EVENT_CREATE,
        Permission.EVENT_VIEW,
        Permission.EVENT_UPDATE,
        # Runs
        Permission.RUN_CREATE,
        Permission.RUN_VIEW,
        Permission.RUN_CANCEL,
        # Nodes
        Permission.NODE_VIEW,
        Permission.NODE_EXPAND,
        Permission.NODE_FORK,
        # Telemetry
        Permission.TELEMETRY_VIEW,
        Permission.TELEMETRY_EXPORT,
        # Reliability
        Permission.RELIABILITY_VIEW,
        # Legacy
        Permission.SIMULATION_RUN,
        Permission.SIMULATION_VIEW,
        Permission.RESULT_VIEW,
        Permission.RESULT_EXPORT,
        # Settings (view only)
        Permission.SETTINGS_VIEW,
    },
    OrganizationRole.VIEWER: {
        # Read-only access
        Permission.ORG_VIEW,
        Permission.MEMBER_VIEW,
        Permission.PROJECT_VIEW,
        Permission.PERSONA_VIEW,
        Permission.EVENT_VIEW,
        Permission.RUN_VIEW,
        Permission.NODE_VIEW,
        Permission.TELEMETRY_VIEW,
        Permission.RELIABILITY_VIEW,
        Permission.SIMULATION_VIEW,
        Permission.RESULT_VIEW,
        Permission.SETTINGS_VIEW,
    },
}


def get_role_permissions(role: OrganizationRole) -> Set[Permission]:
    """Get all permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: OrganizationRole, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in get_role_permissions(role)


async def get_user_org_role(
    db: AsyncSession,
    user_id: UUID,
    organization_id: UUID,
) -> Optional[OrganizationRole]:
    """Get user's role in an organization."""
    result = await db.execute(
        select(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        # Check if user is the owner
        org_result = await db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = org_result.scalar_one_or_none()
        if org and org.owner_id == user_id:
            return OrganizationRole.OWNER
        return None

    return OrganizationRole(membership.role)


async def check_org_permission(
    db: AsyncSession,
    user_id: UUID,
    organization_id: UUID,
    permission: Permission,
) -> bool:
    """Check if user has a specific permission in an organization."""
    role = await get_user_org_role(db, user_id, organization_id)
    if not role:
        return False
    return has_permission(role, permission)


async def require_org_permission(
    db: AsyncSession,
    user_id: UUID,
    organization_id: UUID,
    permission: Permission,
) -> OrganizationRole:
    """
    Require user to have a specific permission in an organization.
    Raises HTTPException if not authorized.
    Returns the user's role if authorized.
    """
    role = await get_user_org_role(db, user_id, organization_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )

    if not has_permission(role, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have permission to perform this action: {permission.value}",
        )

    return role


async def require_org_membership(
    db: AsyncSession,
    user_id: UUID,
    organization_id: UUID,
) -> OrganizationRole:
    """
    Require user to be a member of an organization.
    Raises HTTPException if not a member.
    Returns the user's role.
    """
    role = await get_user_org_role(db, user_id, organization_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )

    return role


async def require_org_admin(
    db: AsyncSession,
    user_id: UUID,
    organization_id: UUID,
) -> OrganizationRole:
    """
    Require user to be an admin or owner of an organization.
    Raises HTTPException if not authorized.
    Returns the user's role.
    """
    role = await get_user_org_role(db, user_id, organization_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )

    if role not in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires admin or owner privileges",
        )

    return role


async def require_org_owner(
    db: AsyncSession,
    user_id: UUID,
    organization_id: UUID,
) -> OrganizationRole:
    """
    Require user to be the owner of an organization.
    Raises HTTPException if not authorized.
    """
    role = await get_user_org_role(db, user_id, organization_id)

    if role != OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires owner privileges",
        )

    return role


def can_modify_role(
    actor_role: OrganizationRole,
    target_current_role: OrganizationRole,
    target_new_role: OrganizationRole,
) -> bool:
    """
    Check if an actor can modify another member's role.

    Rules:
    - Owner can change anyone's role to anything except owner
    - Admin can change member/viewer roles but not other admins/owners
    - Members and viewers cannot change roles
    """
    if actor_role == OrganizationRole.OWNER:
        # Owner can do anything except create another owner
        return target_new_role != OrganizationRole.OWNER

    if actor_role == OrganizationRole.ADMIN:
        # Admin can only modify members and viewers
        if target_current_role in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
            return False
        # And can only set them to member or viewer
        return target_new_role in (OrganizationRole.MEMBER, OrganizationRole.VIEWER)

    # Members and viewers cannot change roles
    return False


def can_remove_member(
    actor_role: OrganizationRole,
    target_role: OrganizationRole,
) -> bool:
    """
    Check if an actor can remove a member from the organization.

    Rules:
    - Owner can remove anyone except themselves
    - Admin can remove members and viewers but not other admins/owners
    - Members and viewers cannot remove anyone
    """
    if actor_role == OrganizationRole.OWNER:
        # Owner can remove anyone except the owner
        return target_role != OrganizationRole.OWNER

    if actor_role == OrganizationRole.ADMIN:
        # Admin can only remove members and viewers
        return target_role in (OrganizationRole.MEMBER, OrganizationRole.VIEWER)

    return False


# =============================================================================
# Tenant-based Permission Helpers (project.md §8)
# =============================================================================

def get_permissions_for_tenant_role(role: str) -> Set[Permission]:
    """
    Get permissions for a tenant role string.
    Maps role names to permission sets.
    """
    role_map = {
        "owner": ROLE_PERMISSIONS[OrganizationRole.OWNER],
        "admin": ROLE_PERMISSIONS[OrganizationRole.ADMIN],
        "member": ROLE_PERMISSIONS[OrganizationRole.MEMBER],
        "viewer": ROLE_PERMISSIONS[OrganizationRole.VIEWER],
    }
    return role_map.get(role.lower(), set())


def check_tenant_permission(
    permissions: list[str],
    required: Permission,
    is_admin: bool = False,
) -> bool:
    """
    Check if a list of permission strings includes the required permission.
    Admin users have all permissions.
    """
    if is_admin:
        return True
    return required.value in permissions


def require_tenant_permission(
    permissions: list[str],
    required: Permission,
    is_admin: bool = False,
) -> None:
    """
    Require a specific permission from tenant context.
    Raises HTTPException if not authorized.
    """
    if not check_tenant_permission(permissions, required, is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {required.value}",
        )


def permission_dependency(required: Permission):
    """
    Create a FastAPI dependency that requires a specific permission.

    Usage:
        @app.get("/runs")
        async def list_runs(
            _: None = Depends(permission_dependency(Permission.RUN_VIEW))
        ):
            ...
    """
    from fastapi import Depends
    from app.middleware.tenant import get_tenant_context, TenantContext

    def check(
        ctx: TenantContext = Depends(lambda: get_tenant_context()),
    ):
        if not ctx:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        if not ctx.has_permission(required.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {required.value}",
            )
        return ctx

    return check


# Convenience permission dependencies for common operations
require_run_create = permission_dependency(Permission.RUN_CREATE)
require_run_view = permission_dependency(Permission.RUN_VIEW)
require_node_view = permission_dependency(Permission.NODE_VIEW)
require_node_expand = permission_dependency(Permission.NODE_EXPAND)
require_telemetry_view = permission_dependency(Permission.TELEMETRY_VIEW)
require_project_create = permission_dependency(Permission.PROJECT_CREATE)
require_project_view = permission_dependency(Permission.PROJECT_VIEW)
require_audit_view = permission_dependency(Permission.AUDIT_VIEW)
