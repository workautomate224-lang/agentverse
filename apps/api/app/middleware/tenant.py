"""
Tenant Context Middleware
Reference: project.md §8.1 (Tenant isolation)

Provides multi-tenancy support via:
- Request context with tenant_id
- Database query scoping
- Resource access control

Every request is scoped to a tenant. Tenant ID is extracted from:
1. JWT token (primary method)
2. API key header (for M2M)
3. Request header (for internal services)
"""

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.security import decode_token


# Context variable for tenant information
_tenant_context: ContextVar[Optional["TenantContext"]] = ContextVar(
    "tenant_context", default=None
)


@dataclass
class TenantContext:
    """
    Tenant context for the current request.
    Available throughout the request lifecycle.
    """
    tenant_id: str
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    is_admin: bool = False
    is_system: bool = False  # For internal service calls
    permissions: list[str] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []

    def has_permission(self, permission: str) -> bool:
        """Check if context has a specific permission."""
        if self.is_admin or self.is_system:
            return True
        return permission in self.permissions

    def can_access_tenant(self, target_tenant_id: str) -> bool:
        """Check if context can access a specific tenant."""
        if self.is_system:
            return True  # System can access all tenants
        return self.tenant_id == target_tenant_id


def get_tenant_context() -> Optional[TenantContext]:
    """Get the current tenant context."""
    return _tenant_context.get()


def get_current_tenant_id() -> str:
    """
    Get the current tenant ID.
    Raises HTTPException if no tenant context.
    """
    ctx = get_tenant_context()
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context not available",
        )
    return ctx.tenant_id


def get_current_user_id() -> Optional[str]:
    """Get the current user ID (may be None for system calls)."""
    ctx = get_tenant_context()
    return ctx.user_id if ctx else None


def require_tenant(
    tenant_context: TenantContext = Depends(lambda: get_tenant_context()),
) -> TenantContext:
    """
    Dependency that requires a valid tenant context.
    Use in endpoints that need tenant isolation.
    """
    if not tenant_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return tenant_context


def require_permission(permission: str):
    """
    Dependency factory that requires a specific permission.

    Usage:
        @app.get("/admin/users")
        async def list_users(
            ctx: TenantContext = Depends(require_permission("admin:users:read"))
        ):
            ...
    """
    def dependency(
        tenant_context: TenantContext = Depends(require_tenant),
    ) -> TenantContext:
        if not tenant_context.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return tenant_context
    return dependency


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts tenant context from requests.

    Supports multiple authentication methods:
    1. Bearer token (JWT)
    2. X-API-Key header
    3. X-Tenant-ID header (internal only)
    """

    # Paths that don't require tenant context
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        f"{settings.API_V1_STR}/openapi.json",
        f"{settings.API_V1_STR}/auth/login",
        f"{settings.API_V1_STR}/auth/register",
        f"{settings.API_V1_STR}/auth/refresh",
    }

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request and set tenant context."""

        # Skip public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # Extract tenant context
        tenant_context = await self._extract_tenant_context(request)

        # Set context for this request
        token = _tenant_context.set(tenant_context)

        try:
            response = await call_next(request)
            return response
        finally:
            # Reset context
            _tenant_context.reset(token)

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no auth required)."""
        # Exact match
        if path in self.PUBLIC_PATHS:
            return True

        # Static files
        if path.startswith("/static"):
            return True

        # Docs paths
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True

        return False

    async def _extract_tenant_context(
        self,
        request: Request,
    ) -> Optional[TenantContext]:
        """Extract tenant context from request."""

        # Method 1: Bearer token (JWT)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_token(token)
                return TenantContext(
                    tenant_id=payload.get("tenant_id", payload.get("sub")),
                    user_id=payload.get("sub"),
                    user_role=payload.get("role"),
                    is_admin=payload.get("is_admin", False),
                    permissions=payload.get("permissions", []),
                )
            except JWTError:
                # Invalid token - continue to try other methods
                pass

        # Method 2: API Key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            context = await self._validate_api_key(api_key)
            if context:
                return context

        # Method 3: Internal service header
        # Only allowed from internal IPs
        if self._is_internal_request(request):
            tenant_id = request.headers.get("X-Tenant-ID")
            if tenant_id:
                return TenantContext(
                    tenant_id=tenant_id,
                    is_system=True,
                )

        return None

    async def _validate_api_key(self, api_key: str) -> Optional[TenantContext]:
        """
        Validate API key and return tenant context.
        API keys are stored in database with tenant association.
        """
        # TODO: Implement API key validation with database lookup
        # For now, return None (not implemented)
        return None

    def _is_internal_request(self, request: Request) -> bool:
        """Check if request is from internal network."""
        if not request.client:
            return False

        client_host = request.client.host

        # Allow localhost
        if client_host in ("127.0.0.1", "localhost", "::1"):
            return True

        # Allow private IP ranges
        import ipaddress
        try:
            ip = ipaddress.ip_address(client_host)
            return ip.is_private
        except ValueError:
            return False


def scope_query_to_tenant(tenant_id: str):
    """
    SQLAlchemy filter helper for tenant scoping.

    Usage:
        query = select(ProjectSpec).where(
            *scope_query_to_tenant(tenant_id),
            ProjectSpec.id == project_id,
        )
    """
    from sqlalchemy import and_

    def apply_scope(model_class):
        """Apply tenant scope to a model class."""
        if hasattr(model_class, "tenant_id"):
            return model_class.tenant_id == tenant_id
        raise ValueError(f"Model {model_class.__name__} does not have tenant_id field")

    return apply_scope


class TenantScopedSession:
    """
    Database session wrapper that automatically scopes queries to tenant.

    Usage:
        async with TenantScopedSession(db, tenant_id) as scoped_db:
            # All queries automatically filtered by tenant
            projects = await scoped_db.query(ProjectSpec).all()
    """

    def __init__(self, session, tenant_id: str):
        self._session = session
        self._tenant_id = tenant_id

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    def query(self, model_class):
        """Create a tenant-scoped query."""
        from sqlalchemy import select
        query = select(model_class)
        if hasattr(model_class, "tenant_id"):
            query = query.where(model_class.tenant_id == self._tenant_id)
        return query

    async def execute(self, query):
        """Execute a query."""
        return await self._session.execute(query)

    async def add(self, instance):
        """Add an instance, setting tenant_id if applicable."""
        if hasattr(instance, "tenant_id"):
            instance.tenant_id = self._tenant_id
        self._session.add(instance)

    async def commit(self):
        """Commit the transaction."""
        await self._session.commit()

    async def rollback(self):
        """Rollback the transaction."""
        await self._session.rollback()
