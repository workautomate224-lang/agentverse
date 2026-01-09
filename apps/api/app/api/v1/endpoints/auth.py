"""
Authentication Endpoints
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.schemas.user import (
    LoginRequest,
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserResponse,
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Register a new user.
    """
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_in.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        company=user_in.company,
    )

    db.add(user)
    await db.flush()
    await db.refresh(user)

    return user


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Login with email and password.
    """
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.flush()

    # Determine if user is admin
    is_admin = user.role == "admin"

    return {
        "access_token": create_access_token(
            subject=str(user.id),
            role=user.role,
            is_admin=is_admin,
        ),
        "refresh_token": create_refresh_token(subject=str(user.id)),
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Refresh access token using refresh token.
    """
    try:
        payload = decode_token(refresh_data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        return {
            "access_token": create_access_token(subject=str(user.id)),
            "refresh_token": create_refresh_token(subject=str(user.id)),
            "token_type": "bearer",
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Logout current user (client should discard tokens).
    """
    # In a production system, you'd invalidate the token here
    # by adding it to a blacklist or using token versioning
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user information.
    """
    return current_user
