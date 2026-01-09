"""
API Dependencies
"""

from typing import AsyncGenerator, Optional
from uuid import UUID
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.user import User


@dataclass
class TenantContext:
    """Context object containing tenant information for multi-tenant operations."""
    tenant_id: UUID
    user_id: UUID
    role: str

security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current admin user."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_optional_user(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[User]:
    """Get optional user (for endpoints that work with or without auth)."""
    if credentials is None:
        return None
    try:
        return get_current_user(db, credentials)
    except HTTPException:
        return None


async def get_current_tenant_id(
    current_user: User = Depends(get_current_user),
) -> UUID:
    """Get current tenant ID from user's organization.

    For MVP, we use the user's ID as the tenant ID.
    In multi-tenant mode, this would come from the user's organization.
    """
    # For MVP: use user_id as tenant_id
    # TODO: Implement proper multi-tenancy with organization_id
    return current_user.id


async def get_current_tenant(
    current_user: User = Depends(get_current_user),
) -> str:
    """Get current tenant as string (for endpoints expecting string tenant_id)."""
    return str(current_user.id)


async def require_tenant(
    current_user: User = Depends(get_current_user),
) -> TenantContext:
    """Require and return tenant context for multi-tenant operations.

    For MVP, we use the user's ID as the tenant ID.
    In multi-tenant mode, this would come from the user's organization.
    """
    return TenantContext(
        tenant_id=current_user.id,
        user_id=current_user.id,
        role=current_user.role or "user",
    )
