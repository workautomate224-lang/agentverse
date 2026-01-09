"""
Invitation Management Endpoints (User-facing)
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationInvitation,
    InvitationStatus,
)
from app.schemas.organization import (
    InvitationResponse,
    InvitationListResponse,
)
from app.services.audit import AuditService

router = APIRouter()


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("/pending", response_model=InvitationListResponse)
async def list_pending_invitations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvitationListResponse:
    """
    List all pending invitations for the current user.
    """
    result = await db.execute(
        select(OrganizationInvitation)
        .options(selectinload(OrganizationInvitation.organization))
        .where(
            OrganizationInvitation.email == current_user.email,
            OrganizationInvitation.status == InvitationStatus.PENDING.value,
            OrganizationInvitation.expires_at > datetime.utcnow(),
        )
        .order_by(OrganizationInvitation.created_at.desc())
    )
    invitations = result.scalars().all()

    # Get invited_by users
    user_ids = {inv.invited_by_id for inv in invitations}
    if user_ids:
        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        user_map = {u.id: u.email for u in users_result.scalars().all()}
    else:
        user_map = {}

    items = []
    for inv in invitations:
        items.append(InvitationResponse(
            id=inv.id,
            organization_id=inv.organization_id,
            organization_name=inv.organization.name if inv.organization else None,
            email=inv.email,
            role=inv.role,
            invited_by_email=user_map.get(inv.invited_by_id),
            status=inv.status,
            created_at=inv.created_at,
            expires_at=inv.expires_at,
        ))

    return InvitationListResponse(items=items, total=len(items))


@router.post("/{invitation_id}/accept")
async def accept_invitation(
    invitation_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Accept an invitation to join an organization.
    """
    # Get invitation
    result = await db.execute(
        select(OrganizationInvitation)
        .options(selectinload(OrganizationInvitation.organization))
        .where(OrganizationInvitation.id == invitation_id)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    # Check email matches
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation is not for you",
        )

    # Check status
    if invitation.status != InvitationStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This invitation has already been {invitation.status}",
        )

    # Check expiration
    if invitation.expires_at < datetime.utcnow():
        invitation.status = InvitationStatus.EXPIRED.value
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has expired",
        )

    # Check if already a member
    existing_membership = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == invitation.organization_id,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    if existing_membership.scalar_one_or_none():
        # Update invitation status and return
        invitation.status = InvitationStatus.ACCEPTED.value
        invitation.responded_at = datetime.utcnow()
        await db.flush()
        return {"message": "You are already a member of this organization"}

    # Create membership
    membership = OrganizationMembership(
        organization_id=invitation.organization_id,
        user_id=current_user.id,
        role=invitation.role,
    )
    db.add(membership)

    # Update invitation status
    invitation.status = InvitationStatus.ACCEPTED.value
    invitation.responded_at = datetime.utcnow()

    await db.flush()

    # Log the join
    audit = AuditService(db)
    await audit.log_member_joined(
        organization_id=invitation.organization_id,
        user_id=current_user.id,
        role=invitation.role,
        ip_address=get_client_ip(request),
    )

    org_name = invitation.organization.name if invitation.organization else "the organization"
    return {"message": f"Successfully joined {org_name}"}


@router.post("/{invitation_id}/decline")
async def decline_invitation(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Decline an invitation to join an organization.
    """
    # Get invitation
    result = await db.execute(
        select(OrganizationInvitation).where(OrganizationInvitation.id == invitation_id)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    # Check email matches
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation is not for you",
        )

    # Check status
    if invitation.status != InvitationStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This invitation has already been {invitation.status}",
        )

    # Update status
    invitation.status = InvitationStatus.DECLINED.value
    invitation.responded_at = datetime.utcnow()

    await db.flush()

    return {"message": "Invitation declined"}


@router.get("/by-token/{token}", response_model=InvitationResponse)
async def get_invitation_by_token(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> InvitationResponse:
    """
    Get invitation details by token (public endpoint for email links).
    """
    result = await db.execute(
        select(OrganizationInvitation)
        .options(selectinload(OrganizationInvitation.organization))
        .where(OrganizationInvitation.token == token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    # Get invited_by user
    invited_by_result = await db.execute(
        select(User).where(User.id == invitation.invited_by_id)
    )
    invited_by = invited_by_result.scalar_one_or_none()

    return InvitationResponse(
        id=invitation.id,
        organization_id=invitation.organization_id,
        organization_name=invitation.organization.name if invitation.organization else None,
        email=invitation.email,
        role=invitation.role,
        invited_by_email=invited_by.email if invited_by else None,
        status=invitation.status,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
    )


@router.post("/by-token/{token}/accept")
async def accept_invitation_by_token(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Accept an invitation using the token from email link.
    """
    result = await db.execute(
        select(OrganizationInvitation)
        .options(selectinload(OrganizationInvitation.organization))
        .where(OrganizationInvitation.token == token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    # Check email matches
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation is for a different email address. Please use the email associated with this invitation.",
        )

    # Delegate to the ID-based accept
    return await accept_invitation(invitation.id, request, db, current_user)
