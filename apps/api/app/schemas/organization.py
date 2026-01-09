"""
Organization Schemas for team collaboration
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# ============================================================
# Organization Schemas
# ============================================================

class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""
    slug: Optional[str] = Field(None, min_length=2, max_length=100)

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Slug must be alphanumeric with hyphens only
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        if v.startswith('-') or v.endswith('-'):
            raise ValueError('Slug cannot start or end with a hyphen')
        return v


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    settings: Optional[dict] = None


class MemberInfo(BaseModel):
    """Basic member info for organization responses."""
    id: UUID
    email: str
    full_name: Optional[str] = None
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True


class OrganizationResponse(OrganizationBase):
    """Schema for organization response."""
    id: UUID
    slug: str
    logo_url: Optional[str] = None
    owner_id: UUID
    tier: str
    max_members: int
    max_projects: int
    max_simulations_per_month: int
    current_month_simulations: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    member_count: Optional[int] = None

    class Config:
        from_attributes = True


class OrganizationDetailResponse(OrganizationResponse):
    """Schema for detailed organization response with members."""
    members: List[MemberInfo] = []


class OrganizationListResponse(BaseModel):
    """Schema for paginated organization list."""
    items: List[OrganizationResponse]
    total: int
    page: int
    page_size: int


# ============================================================
# Membership Schemas
# ============================================================

class MembershipBase(BaseModel):
    """Base membership schema."""
    role: str = Field(default="member")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = ['owner', 'admin', 'member', 'viewer']
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v


class MembershipUpdate(MembershipBase):
    """Schema for updating membership role."""
    pass


class MembershipResponse(MembershipBase):
    """Schema for membership response."""
    id: UUID
    organization_id: UUID
    user_id: UUID
    joined_at: datetime
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    class Config:
        from_attributes = True


class UserOrganization(BaseModel):
    """Schema for a user's organization membership."""
    organization: OrganizationResponse
    role: str
    joined_at: datetime


class UserOrganizationsResponse(BaseModel):
    """Schema for listing user's organizations."""
    items: List[UserOrganization]


# ============================================================
# Invitation Schemas
# ============================================================

class InvitationCreate(BaseModel):
    """Schema for creating an invitation."""
    email: EmailStr
    role: str = Field(default="member")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = ['admin', 'member', 'viewer']
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v


class InvitationResponse(BaseModel):
    """Schema for invitation response."""
    id: UUID
    organization_id: UUID
    organization_name: Optional[str] = None
    email: str
    role: str
    invited_by_email: Optional[str] = None
    status: str
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


class InvitationListResponse(BaseModel):
    """Schema for listing invitations."""
    items: List[InvitationResponse]
    total: int


class InvitationAccept(BaseModel):
    """Schema for accepting an invitation."""
    token: str


class InvitationDecline(BaseModel):
    """Schema for declining an invitation."""
    token: str


# ============================================================
# Audit Log Schemas
# ============================================================

class AuditLogResponse(BaseModel):
    """Schema for audit log response."""
    id: UUID
    organization_id: UUID
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    details: dict = {}
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Schema for paginated audit log list."""
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs."""
    action: Optional[str] = None
    user_id: Optional[UUID] = None
    resource_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ============================================================
# Statistics & Dashboard Schemas
# ============================================================

class OrganizationStats(BaseModel):
    """Schema for organization statistics."""
    total_members: int
    total_projects: int
    total_simulations: int
    simulations_this_month: int
    simulations_remaining: int
    storage_used_mb: float = 0.0


class OrganizationDashboard(BaseModel):
    """Schema for organization dashboard data."""
    organization: OrganizationResponse
    stats: OrganizationStats
    recent_activity: List[AuditLogResponse] = []
    pending_invitations: int = 0
