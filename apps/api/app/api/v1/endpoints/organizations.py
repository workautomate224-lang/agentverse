"""
Organization Management Endpoints
"""

import re
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationInvitation,
    OrganizationRole,
    OrganizationTier,
    InvitationStatus,
    AuditLog,
)
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationDetailResponse,
    OrganizationListResponse,
    MembershipUpdate,
    MembershipResponse,
    MemberInfo,
    UserOrganization,
    UserOrganizationsResponse,
    InvitationCreate,
    InvitationResponse,
    InvitationListResponse,
    AuditLogResponse,
    AuditLogListResponse,
    OrganizationStats,
    OrganizationDashboard,
)
from app.core.permissions import (
    Permission,
    require_org_permission,
    require_org_membership,
    require_org_admin,
    require_org_owner,
    can_modify_role,
    can_remove_member,
    get_user_org_role,
)
from app.services.audit import AuditService

router = APIRouter()


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from name."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug[:100]


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# ============================================================
# Organization CRUD Endpoints
# ============================================================

@router.get("/", response_model=UserOrganizationsResponse)
async def list_my_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOrganizationsResponse:
    """
    List all organizations the current user belongs to.
    """
    # Get organizations where user is owner
    owned_result = await db.execute(
        select(Organization).where(Organization.owner_id == current_user.id)
    )
    owned_orgs = owned_result.scalars().all()

    # Get organizations where user is a member
    membership_result = await db.execute(
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.organization))
        .where(OrganizationMembership.user_id == current_user.id)
    )
    memberships = membership_result.scalars().all()

    # Combine results
    items = []

    # Add owned organizations
    for org in owned_orgs:
        # Count members
        member_count_result = await db.execute(
            select(func.count(OrganizationMembership.id))
            .where(OrganizationMembership.organization_id == org.id)
        )
        member_count = member_count_result.scalar() + 1  # +1 for owner

        org_response = OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            description=org.description,
            logo_url=org.logo_url,
            owner_id=org.owner_id,
            tier=org.tier,
            max_members=org.max_members,
            max_projects=org.max_projects,
            max_simulations_per_month=org.max_simulations_per_month,
            current_month_simulations=org.current_month_simulations,
            is_active=org.is_active,
            created_at=org.created_at,
            updated_at=org.updated_at,
            member_count=member_count,
        )
        items.append(UserOrganization(
            organization=org_response,
            role=OrganizationRole.OWNER.value,
            joined_at=org.created_at,
        ))

    # Add member organizations (avoiding duplicates)
    owned_ids = {org.id for org in owned_orgs}
    for membership in memberships:
        if membership.organization_id not in owned_ids:
            org = membership.organization
            # Count members
            member_count_result = await db.execute(
                select(func.count(OrganizationMembership.id))
                .where(OrganizationMembership.organization_id == org.id)
            )
            member_count = member_count_result.scalar() + 1

            org_response = OrganizationResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                description=org.description,
                logo_url=org.logo_url,
                owner_id=org.owner_id,
                tier=org.tier,
                max_members=org.max_members,
                max_projects=org.max_projects,
                max_simulations_per_month=org.max_simulations_per_month,
                current_month_simulations=org.current_month_simulations,
                is_active=org.is_active,
                created_at=org.created_at,
                updated_at=org.updated_at,
                member_count=member_count,
            )
            items.append(UserOrganization(
                organization=org_response,
                role=membership.role,
                joined_at=membership.joined_at,
            ))

    return UserOrganizationsResponse(items=items)


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_in: OrganizationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationResponse:
    """
    Create a new organization.
    """
    # Generate slug if not provided
    slug = org_in.slug or generate_slug(org_in.name)

    # Check if slug is unique
    existing = await db.execute(
        select(Organization).where(Organization.slug == slug)
    )
    if existing.scalar_one_or_none():
        # Append random suffix
        slug = f"{slug}-{secrets.token_hex(3)}"

    # Create organization
    org = Organization(
        name=org_in.name,
        slug=slug,
        description=org_in.description,
        owner_id=current_user.id,
        tier=OrganizationTier.FREE.value,
        max_members=5,
        max_projects=10,
        max_simulations_per_month=100,
    )

    db.add(org)
    await db.flush()
    await db.refresh(org)

    # Log the creation
    audit = AuditService(db)
    await audit.log_org_created(
        organization_id=org.id,
        user_id=current_user.id,
        org_name=org.name,
        ip_address=get_client_ip(request),
    )

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        owner_id=org.owner_id,
        tier=org.tier,
        max_members=org.max_members,
        max_projects=org.max_projects,
        max_simulations_per_month=org.max_simulations_per_month,
        current_month_simulations=org.current_month_simulations,
        is_active=org.is_active,
        created_at=org.created_at,
        updated_at=org.updated_at,
        member_count=1,
    )


@router.get("/{org_slug}", response_model=OrganizationDetailResponse)
async def get_organization(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationDetailResponse:
    """
    Get organization details by slug.
    """
    # Get organization
    result = await db.execute(
        select(Organization)
        .options(selectinload(Organization.memberships))
        .where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check membership
    await require_org_membership(db, current_user.id, org.id)

    # Get members with user info
    members_result = await db.execute(
        select(OrganizationMembership, User)
        .join(User, OrganizationMembership.user_id == User.id)
        .where(OrganizationMembership.organization_id == org.id)
    )
    members = []

    # Add owner
    owner_result = await db.execute(
        select(User).where(User.id == org.owner_id)
    )
    owner = owner_result.scalar_one()
    members.append(MemberInfo(
        id=owner.id,
        email=owner.email,
        full_name=owner.full_name,
        role=OrganizationRole.OWNER.value,
        joined_at=org.created_at,
    ))

    # Add other members
    for membership, user in members_result.all():
        members.append(MemberInfo(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=membership.role,
            joined_at=membership.joined_at,
        ))

    return OrganizationDetailResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        owner_id=org.owner_id,
        tier=org.tier,
        max_members=org.max_members,
        max_projects=org.max_projects,
        max_simulations_per_month=org.max_simulations_per_month,
        current_month_simulations=org.current_month_simulations,
        is_active=org.is_active,
        created_at=org.created_at,
        updated_at=org.updated_at,
        member_count=len(members),
        members=members,
    )


@router.put("/{org_slug}", response_model=OrganizationResponse)
async def update_organization(
    org_slug: str,
    org_update: OrganizationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationResponse:
    """
    Update organization settings.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check permission
    await require_org_permission(db, current_user.id, org.id, Permission.ORG_UPDATE)

    # Update fields
    update_data = org_update.model_dump(exclude_unset=True)
    changes = {}

    for field, value in update_data.items():
        old_value = getattr(org, field)
        if old_value != value:
            changes[field] = {"old": str(old_value), "new": str(value)}
            setattr(org, field, value)

    if changes:
        await db.flush()
        await db.refresh(org)

        # Log the update
        audit = AuditService(db)
        await audit.log_org_updated(
            organization_id=org.id,
            user_id=current_user.id,
            changes=changes,
            ip_address=get_client_ip(request),
        )

    # Count members
    member_count_result = await db.execute(
        select(func.count(OrganizationMembership.id))
        .where(OrganizationMembership.organization_id == org.id)
    )
    member_count = member_count_result.scalar() + 1

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        owner_id=org.owner_id,
        tier=org.tier,
        max_members=org.max_members,
        max_projects=org.max_projects,
        max_simulations_per_month=org.max_simulations_per_month,
        current_month_simulations=org.current_month_simulations,
        is_active=org.is_active,
        created_at=org.created_at,
        updated_at=org.updated_at,
        member_count=member_count,
    )


@router.delete("/{org_slug}")
async def delete_organization(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Delete organization (owner only).
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Only owner can delete
    await require_org_owner(db, current_user.id, org.id)

    await db.delete(org)

    return {"message": "Organization deleted successfully"}


# ============================================================
# Member Management Endpoints
# ============================================================

@router.get("/{org_slug}/members", response_model=List[MemberInfo])
async def list_organization_members(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MemberInfo]:
    """
    List all members of an organization.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check membership
    await require_org_membership(db, current_user.id, org.id)

    # Get members
    members_result = await db.execute(
        select(OrganizationMembership, User)
        .join(User, OrganizationMembership.user_id == User.id)
        .where(OrganizationMembership.organization_id == org.id)
    )

    members = []

    # Add owner
    owner_result = await db.execute(
        select(User).where(User.id == org.owner_id)
    )
    owner = owner_result.scalar_one()
    members.append(MemberInfo(
        id=owner.id,
        email=owner.email,
        full_name=owner.full_name,
        role=OrganizationRole.OWNER.value,
        joined_at=org.created_at,
    ))

    # Add members
    for membership, user in members_result.all():
        members.append(MemberInfo(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=membership.role,
            joined_at=membership.joined_at,
        ))

    return members


@router.put("/{org_slug}/members/{user_id}", response_model=MemberInfo)
async def update_member_role(
    org_slug: str,
    user_id: UUID,
    role_update: MembershipUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberInfo:
    """
    Update a member's role in the organization.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Cannot change owner role
    if org.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change the owner's role",
        )

    # Get actor's role
    actor_role = await get_user_org_role(db, current_user.id, org.id)
    if not actor_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )

    # Get target membership
    membership_result = await db.execute(
        select(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == org.id,
            OrganizationMembership.user_id == user_id,
        )
    )
    membership = membership_result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Check if role change is allowed
    target_current_role = OrganizationRole(membership.role)
    target_new_role = OrganizationRole(role_update.role)

    if not can_modify_role(actor_role, target_current_role, target_new_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to make this role change",
        )

    old_role = membership.role
    membership.role = role_update.role
    await db.flush()

    # Log the change
    audit = AuditService(db)
    await audit.log_member_role_changed(
        organization_id=org.id,
        actor_id=current_user.id,
        target_user_id=user_id,
        old_role=old_role,
        new_role=role_update.role,
        ip_address=get_client_ip(request),
    )

    # Get user info
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one()

    return MemberInfo(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        joined_at=membership.joined_at,
    )


@router.delete("/{org_slug}/members/{user_id}")
async def remove_member(
    org_slug: str,
    user_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Remove a member from the organization.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Cannot remove owner
    if org.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the owner from the organization",
        )

    # Get actor's role
    actor_role = await get_user_org_role(db, current_user.id, org.id)
    if not actor_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )

    # Get target membership
    membership_result = await db.execute(
        select(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == org.id,
            OrganizationMembership.user_id == user_id,
        )
    )
    membership = membership_result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Check if removal is allowed (or self-removal)
    target_role = OrganizationRole(membership.role)
    is_self_removal = user_id == current_user.id

    if not is_self_removal and not can_remove_member(actor_role, target_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to remove this member",
        )

    # Get user email for audit
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one()

    await db.delete(membership)

    # Log the removal
    audit = AuditService(db)
    await audit.log_member_removed(
        organization_id=org.id,
        actor_id=current_user.id,
        removed_user_id=user_id,
        removed_email=user.email,
        ip_address=get_client_ip(request),
    )

    return {"message": "Member removed successfully"}


# ============================================================
# Invitation Endpoints
# ============================================================

@router.get("/{org_slug}/invitations", response_model=InvitationListResponse)
async def list_invitations(
    org_slug: str,
    status_filter: Optional[str] = Query(None, pattern="^(pending|accepted|declined|expired)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvitationListResponse:
    """
    List all invitations for an organization.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check permission
    await require_org_permission(db, current_user.id, org.id, Permission.MEMBER_INVITE)

    # Build query
    query = select(OrganizationInvitation).where(
        OrganizationInvitation.organization_id == org.id
    )

    if status_filter:
        query = query.where(OrganizationInvitation.status == status_filter)

    query = query.order_by(OrganizationInvitation.created_at.desc())

    inv_result = await db.execute(query)
    invitations = inv_result.scalars().all()

    # Get invited_by emails
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
            organization_name=org.name,
            email=inv.email,
            role=inv.role,
            invited_by_email=user_map.get(inv.invited_by_id),
            status=inv.status,
            created_at=inv.created_at,
            expires_at=inv.expires_at,
        ))

    return InvitationListResponse(items=items, total=len(items))


@router.post("/{org_slug}/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    org_slug: str,
    invitation_in: InvitationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvitationResponse:
    """
    Invite a user to join the organization.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check permission
    await require_org_permission(db, current_user.id, org.id, Permission.MEMBER_INVITE)

    # Check member limit
    member_count_result = await db.execute(
        select(func.count(OrganizationMembership.id))
        .where(OrganizationMembership.organization_id == org.id)
    )
    member_count = member_count_result.scalar() + 1  # +1 for owner

    if member_count >= org.max_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization has reached its member limit ({org.max_members})",
        )

    # Check if user is already a member
    existing_user_result = await db.execute(
        select(User).where(User.email == invitation_in.email)
    )
    existing_user = existing_user_result.scalar_one_or_none()

    if existing_user:
        # Check if already owner
        if org.owner_id == existing_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This user is the organization owner",
            )

        # Check if already a member
        membership_result = await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == org.id,
                OrganizationMembership.user_id == existing_user.id,
            )
        )
        if membership_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This user is already a member of the organization",
            )

    # Check for existing pending invitation
    existing_inv_result = await db.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.organization_id == org.id,
            OrganizationInvitation.email == invitation_in.email,
            OrganizationInvitation.status == InvitationStatus.PENDING.value,
        )
    )
    if existing_inv_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invitation has already been sent to this email",
        )

    # Create invitation
    token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation(
        organization_id=org.id,
        email=invitation_in.email,
        role=invitation_in.role,
        invited_by_id=current_user.id,
        token=token,
        status=InvitationStatus.PENDING.value,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )

    db.add(invitation)
    await db.flush()
    await db.refresh(invitation)

    # Log the invitation
    audit = AuditService(db)
    await audit.log_member_invited(
        organization_id=org.id,
        user_id=current_user.id,
        invited_email=invitation_in.email,
        role=invitation_in.role,
        ip_address=get_client_ip(request),
    )

    return InvitationResponse(
        id=invitation.id,
        organization_id=invitation.organization_id,
        organization_name=org.name,
        email=invitation.email,
        role=invitation.role,
        invited_by_email=current_user.email,
        status=invitation.status,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
    )


@router.delete("/{org_slug}/invitations/{invitation_id}")
async def cancel_invitation(
    org_slug: str,
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Cancel a pending invitation.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check permission
    await require_org_permission(db, current_user.id, org.id, Permission.MEMBER_INVITE)

    # Get invitation
    inv_result = await db.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == org.id,
        )
    )
    invitation = inv_result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.status != InvitationStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending invitations can be cancelled",
        )

    await db.delete(invitation)

    return {"message": "Invitation cancelled successfully"}


# ============================================================
# Audit Log Endpoints
# ============================================================

@router.get("/{org_slug}/audit-logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    org_slug: str,
    action: Optional[str] = Query(None),
    user_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditLogListResponse:
    """
    Get audit logs for an organization.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check permission
    await require_org_permission(db, current_user.id, org.id, Permission.AUDIT_VIEW)

    # Get logs
    audit = AuditService(db)
    logs, total = await audit.get_logs(
        organization_id=org.id,
        action=action,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )

    # Enrich with user info
    enriched = await audit.enrich_logs_with_users(logs)

    items = [AuditLogResponse(**log) for log in enriched]

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================
# Dashboard & Stats Endpoints
# ============================================================

@router.get("/{org_slug}/stats", response_model=OrganizationStats)
async def get_organization_stats(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationStats:
    """
    Get organization statistics.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check membership
    await require_org_membership(db, current_user.id, org.id)

    # Count members
    member_count_result = await db.execute(
        select(func.count(OrganizationMembership.id))
        .where(OrganizationMembership.organization_id == org.id)
    )
    total_members = member_count_result.scalar() + 1  # +1 for owner

    # For now, return mock stats for projects/simulations
    # TODO: Link projects to organizations
    return OrganizationStats(
        total_members=total_members,
        total_projects=0,
        total_simulations=0,
        simulations_this_month=org.current_month_simulations,
        simulations_remaining=org.max_simulations_per_month - org.current_month_simulations,
        storage_used_mb=0.0,
    )


@router.get("/{org_slug}/dashboard", response_model=OrganizationDashboard)
async def get_organization_dashboard(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationDashboard:
    """
    Get organization dashboard data.
    """
    result = await db.execute(
        select(Organization).where(Organization.slug == org_slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check membership
    await require_org_membership(db, current_user.id, org.id)

    # Get stats
    member_count_result = await db.execute(
        select(func.count(OrganizationMembership.id))
        .where(OrganizationMembership.organization_id == org.id)
    )
    total_members = member_count_result.scalar() + 1

    stats = OrganizationStats(
        total_members=total_members,
        total_projects=0,
        total_simulations=0,
        simulations_this_month=org.current_month_simulations,
        simulations_remaining=org.max_simulations_per_month - org.current_month_simulations,
        storage_used_mb=0.0,
    )

    # Get recent activity
    audit = AuditService(db)
    recent_logs = await audit.get_recent_activity(org.id, limit=10)
    enriched_logs = await audit.enrich_logs_with_users(recent_logs)
    recent_activity = [AuditLogResponse(**log) for log in enriched_logs]

    # Count pending invitations
    pending_inv_result = await db.execute(
        select(func.count(OrganizationInvitation.id))
        .where(
            OrganizationInvitation.organization_id == org.id,
            OrganizationInvitation.status == InvitationStatus.PENDING.value,
        )
    )
    pending_invitations = pending_inv_result.scalar()

    org_response = OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        owner_id=org.owner_id,
        tier=org.tier,
        max_members=org.max_members,
        max_projects=org.max_projects,
        max_simulations_per_month=org.max_simulations_per_month,
        current_month_simulations=org.current_month_simulations,
        is_active=org.is_active,
        created_at=org.created_at,
        updated_at=org.updated_at,
        member_count=total_members,
    )

    return OrganizationDashboard(
        organization=org_response,
        stats=stats,
        recent_activity=recent_activity,
        pending_invitations=pending_invitations,
    )
