"""
RBAC Service for Step 4 Production Hardening

Implements:
- Role-based access control (user, admin)
- Project-level isolation (tenant scoping)
- Scope-based permissions (project:read, project:write, run:create, etc.)
- Owner vs collaborator vs viewer permissions

Role Hierarchy:
- admin: Full access to all resources
- user: Access limited to owned/shared projects

Scopes:
- project:read - View project and its runs
- project:write - Modify project settings
- project:delete - Delete project
- run:create - Create runs in project
- run:cancel - Cancel runs
- run:export - Export run artifacts
- admin:users - Manage users
- admin:quotas - Manage quota policies
- admin:whitelist - Manage alpha whitelist
"""

import logging
from typing import Optional, List, Set
from uuid import UUID
from enum import Enum

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.simulation import Project
from app.models.quota import AlphaWhitelist

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles."""
    USER = "user"
    ADMIN = "admin"


class Scope(str, Enum):
    """Permission scopes."""
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"
    RUN_CREATE = "run:create"
    RUN_CANCEL = "run:cancel"
    RUN_EXPORT = "run:export"
    ADMIN_USERS = "admin:users"
    ADMIN_QUOTAS = "admin:quotas"
    ADMIN_WHITELIST = "admin:whitelist"
    ADMIN_KILL_RUN = "admin:kill_run"


class ProjectRole(str, Enum):
    """Role within a project."""
    OWNER = "owner"
    COLLABORATOR = "collaborator"
    VIEWER = "viewer"


# Scopes granted to each project role
PROJECT_ROLE_SCOPES = {
    ProjectRole.OWNER: {
        Scope.PROJECT_READ,
        Scope.PROJECT_WRITE,
        Scope.PROJECT_DELETE,
        Scope.RUN_CREATE,
        Scope.RUN_CANCEL,
        Scope.RUN_EXPORT,
    },
    ProjectRole.COLLABORATOR: {
        Scope.PROJECT_READ,
        Scope.RUN_CREATE,
        Scope.RUN_CANCEL,
        Scope.RUN_EXPORT,
    },
    ProjectRole.VIEWER: {
        Scope.PROJECT_READ,
        Scope.RUN_EXPORT,
    },
}

# Scopes granted to admin role (all scopes)
ADMIN_SCOPES = set(Scope)


class AccessDeniedError(Exception):
    """Raised when access is denied."""

    def __init__(
        self,
        message: str = "Access denied",
        required_scope: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        self.message = message
        self.required_scope = required_scope
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(message)

    def to_dict(self):
        return {
            "error": "access_denied",
            "message": self.message,
            "required_scope": self.required_scope,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
        }


class RBACService:
    """
    Service for role-based access control and project isolation.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_role(self, user_id: UUID) -> Role:
        """Get user's global role."""
        try:
            result = await self.db.execute(
                select(User.role).where(User.id == user_id)
            )
            role = result.scalar_one_or_none()
            return Role(role) if role in [r.value for r in Role] else Role.USER
        except Exception:
            return Role.USER

    async def is_admin(self, user_id: UUID) -> bool:
        """Check if user is admin."""
        role = await self.get_user_role(user_id)
        return role == Role.ADMIN

    async def get_project_role(
        self,
        user_id: UUID,
        project_id: UUID
    ) -> Optional[ProjectRole]:
        """
        Get user's role within a project.
        Returns None if user has no access.
        """
        try:
            # Check if admin (admins have owner access to all projects)
            if await self.is_admin(user_id):
                return ProjectRole.OWNER

            # Check if user is project owner
            result = await self.db.execute(
                select(Project).where(
                    and_(
                        Project.id == project_id,
                        Project.owner_id == user_id
                    )
                )
            )
            project = result.scalar_one_or_none()
            if project:
                return ProjectRole.OWNER

            # TODO: Check project_members table for collaborator/viewer roles
            # For now, non-owners have no access unless admin

            return None

        except Exception as e:
            logger.error(f"Error checking project role: {e}")
            return None

    async def get_user_scopes(
        self,
        user_id: UUID,
        project_id: Optional[UUID] = None
    ) -> Set[Scope]:
        """
        Get all scopes a user has.
        If project_id is provided, includes project-specific scopes.
        """
        scopes = set()

        # Check admin
        if await self.is_admin(user_id):
            return ADMIN_SCOPES.copy()

        # Get project-specific scopes
        if project_id:
            project_role = await self.get_project_role(user_id, project_id)
            if project_role:
                scopes.update(PROJECT_ROLE_SCOPES.get(project_role, set()))

        return scopes

    async def check_scope(
        self,
        user_id: UUID,
        scope: Scope,
        project_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has a specific scope."""
        user_scopes = await self.get_user_scopes(user_id, project_id)
        return scope in user_scopes

    async def require_scope(
        self,
        user_id: UUID,
        scope: Scope,
        project_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> None:
        """
        Require a scope, raising AccessDeniedError if not granted.
        Use this as the primary enforcement method in endpoints.
        """
        has_scope = await self.check_scope(user_id, scope, project_id)
        if not has_scope:
            raise AccessDeniedError(
                message=f"You don't have permission to perform this action",
                required_scope=scope.value,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None
            )

    async def check_project_access(
        self,
        user_id: UUID,
        project_id: UUID,
        required_scope: Scope = Scope.PROJECT_READ
    ) -> bool:
        """Check if user can access a project with required scope."""
        return await self.check_scope(user_id, required_scope, project_id)

    async def require_project_access(
        self,
        user_id: UUID,
        project_id: UUID,
        required_scope: Scope = Scope.PROJECT_READ
    ) -> None:
        """
        Require access to a project, raising AccessDeniedError if denied.
        Enforces tenant isolation.
        """
        await self.require_scope(
            user_id=user_id,
            scope=required_scope,
            project_id=project_id,
            resource_type="project",
            resource_id=str(project_id)
        )

    async def check_run_access(
        self,
        user_id: UUID,
        project_id: UUID,
        run_id: UUID,
        required_scope: Scope = Scope.PROJECT_READ
    ) -> bool:
        """
        Check if user can access a run.
        Runs inherit project access.
        """
        return await self.check_scope(user_id, required_scope, project_id)

    async def require_run_access(
        self,
        user_id: UUID,
        project_id: UUID,
        run_id: UUID,
        required_scope: Scope = Scope.PROJECT_READ
    ) -> None:
        """Require access to a run, raising AccessDeniedError if denied."""
        await self.require_scope(
            user_id=user_id,
            scope=required_scope,
            project_id=project_id,
            resource_type="run",
            resource_id=str(run_id)
        )

    async def is_whitelisted(self, user_id: UUID, email: Optional[str] = None) -> bool:
        """Check if user is on alpha whitelist."""
        try:
            if user_id:
                result = await self.db.execute(
                    select(AlphaWhitelist).where(
                        and_(
                            AlphaWhitelist.user_id == user_id,
                            AlphaWhitelist.is_active == True
                        )
                    )
                )
                if result.scalar_one_or_none():
                    return True

            if email:
                result = await self.db.execute(
                    select(AlphaWhitelist).where(
                        and_(
                            AlphaWhitelist.email == email,
                            AlphaWhitelist.is_active == True
                        )
                    )
                )
                if result.scalar_one_or_none():
                    return True

            return False
        except Exception as e:
            logger.error(f"Error checking whitelist: {e}")
            return False

    async def require_whitelist(
        self,
        user_id: UUID,
        email: Optional[str] = None
    ) -> None:
        """Require user to be whitelisted for alpha access."""
        # Admins bypass whitelist
        if await self.is_admin(user_id):
            return

        if not await self.is_whitelisted(user_id, email):
            raise AccessDeniedError(
                message="You are not on the alpha whitelist. Contact support for access.",
                required_scope="alpha:access",
                resource_type="alpha",
                resource_id=None
            )

    async def list_accessible_projects(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[UUID]:
        """
        List all project IDs accessible to a user.
        Enforces tenant isolation.
        """
        try:
            # Admins see all projects
            if await self.is_admin(user_id):
                result = await self.db.execute(
                    select(Project.id).limit(limit).offset(offset)
                )
                return [row[0] for row in result.fetchall()]

            # Regular users see only their owned projects
            # TODO: Add collaborator/viewer access via project_members table
            result = await self.db.execute(
                select(Project.id).where(
                    Project.owner_id == user_id
                ).limit(limit).offset(offset)
            )
            return [row[0] for row in result.fetchall()]

        except Exception as e:
            logger.error(f"Error listing accessible projects: {e}")
            return []

    async def verify_tenant_scope(
        self,
        user_id: UUID,
        tenant_id: UUID
    ) -> bool:
        """
        Verify user belongs to the tenant.
        Used for multi-tenant isolation (C6).
        """
        try:
            # Admins can access any tenant
            if await self.is_admin(user_id):
                return True

            # Check user's tenant_id matches
            result = await self.db.execute(
                select(User.tenant_id).where(User.id == user_id)
            )
            user_tenant = result.scalar_one_or_none()
            return user_tenant == tenant_id

        except Exception as e:
            logger.error(f"Error verifying tenant scope: {e}")
            return False

    async def require_tenant_scope(
        self,
        user_id: UUID,
        tenant_id: UUID
    ) -> None:
        """Require user to belong to tenant."""
        if not await self.verify_tenant_scope(user_id, tenant_id):
            raise AccessDeniedError(
                message="You don't have access to this tenant",
                required_scope="tenant:access",
                resource_type="tenant",
                resource_id=str(tenant_id)
            )
