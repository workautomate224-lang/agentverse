"""
Security utilities for authentication and authorization
Reference: project.md §8 (Security)
"""

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID
from dataclasses import dataclass

from jose import jwt
import bcrypt

from app.core.config import settings


@dataclass
class TenantContext:
    """Context object containing tenant information for multi-tenant operations."""
    tenant_id: UUID
    user_id: UUID
    role: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def create_access_token(
    subject: str | Any,
    tenant_id: Optional[str] = None,
    role: Optional[str] = None,
    permissions: Optional[list[str]] = None,
    is_admin: bool = False,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT access token with tenant context.

    Args:
        subject: User ID
        tenant_id: Tenant ID for multi-tenancy (required for tenant isolation)
        role: User role name
        permissions: List of permission strings
        is_admin: Whether user is admin
        expires_delta: Custom expiration time
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
    }

    # Add tenant context for multi-tenancy (C6)
    if tenant_id:
        to_encode["tenant_id"] = tenant_id
    if role:
        to_encode["role"] = role
    if permissions:
        to_encode["permissions"] = permissions
    if is_admin:
        to_encode["is_admin"] = is_admin

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(
    subject: str | Any,
    tenant_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT refresh token.

    Args:
        subject: User ID
        tenant_id: Tenant ID for multi-tenancy
        expires_delta: Custom expiration time
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
    }

    if tenant_id:
        to_encode["tenant_id"] = tenant_id

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and validate JWT token."""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
