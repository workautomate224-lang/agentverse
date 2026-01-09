"""
Audit Log Admin API Endpoints
Reference: GAPS.md GAP-P0-006

Admin-only endpoints for querying audit logs.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_

from app.api.deps import get_current_admin_user, get_db, require_tenant
from app.core.security import TenantContext
from app.models.organization import AuditLog
from app.models.user import User
from app.schemas.audit import (
    AuditLogResponse,
    AuditLogListResponse,
    AuditLogStatsResponse,
    AuditLogExportResponse,
)

router = APIRouter()


# =============================================================================
# Audit Log Query Endpoints
# =============================================================================

@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    # Filter parameters
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant/organization ID"),
    start_date: Optional[datetime] = Query(None, description="Filter events after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter events before this date"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    search: Optional[str] = Query(None, description="Search in details (JSON contains)"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    # Sorting
    sort_by: str = Query("created_at", description="Sort by field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    # Dependencies
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    List audit logs with filtering and pagination.

    Admin-only endpoint to query all audit logs across tenants.
    Supports filtering by action type, resource type, user, date range, and more.
    """
    # Build query conditions
    conditions = []

    if tenant_id:
        try:
            conditions.append(AuditLog.organization_id == UUID(tenant_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant_id format"
            )

    if action:
        conditions.append(AuditLog.action == action)

    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)

    if resource_id:
        try:
            conditions.append(AuditLog.resource_id == UUID(resource_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid resource_id format"
            )

    if user_id:
        try:
            conditions.append(AuditLog.user_id == UUID(user_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user_id format"
            )

    if start_date:
        conditions.append(AuditLog.created_at >= start_date)

    if end_date:
        conditions.append(AuditLog.created_at <= end_date)

    if ip_address:
        conditions.append(AuditLog.ip_address == ip_address)

    # Count total matching records
    count_query = select(func.count(AuditLog.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Build main query
    query = select(AuditLog)
    if conditions:
        query = query.where(and_(*conditions))

    # Add sorting
    if sort_order.lower() == "asc":
        query = query.order_by(getattr(AuditLog, sort_by, AuditLog.created_at))
    else:
        query = query.order_by(desc(getattr(AuditLog, sort_by, AuditLog.created_at)))

    # Add pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()

    # Fetch user emails for enrichment
    user_ids = {log.user_id for log in logs if log.user_id}
    user_map = {}
    if user_ids:
        user_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = user_result.scalars().all()
        user_map = {user.id: user.email for user in users}

    # Build response
    total_pages = (total + page_size - 1) // page_size

    return AuditLogListResponse(
        logs=[
            AuditLogResponse(
                id=str(log.id),
                organization_id=str(log.organization_id) if log.organization_id else None,
                tenant_id=str(log.organization_id) if log.organization_id else None,
                user_id=str(log.user_id) if log.user_id else None,
                user_email=user_map.get(log.user_id) if log.user_id else None,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=str(log.resource_id) if log.resource_id else None,
                details=log.details or {},
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/audit-logs/stats", response_model=AuditLogStatsResponse)
async def get_audit_stats(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant/organization ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Get audit log statistics.

    Admin-only endpoint to view audit event statistics including:
    - Total events
    - Events by action type
    - Events by resource type
    - Top active users
    - Activity trends
    """
    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_today - timedelta(days=start_of_today.weekday())
    start_period = now - timedelta(days=days)

    # Base condition for tenant filter
    base_conditions = []
    if tenant_id:
        try:
            base_conditions.append(AuditLog.organization_id == UUID(tenant_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant_id format"
            )

    # Total events in period
    total_query = select(func.count(AuditLog.id)).where(
        and_(
            AuditLog.created_at >= start_period,
            *base_conditions
        )
    )
    total_result = await db.execute(total_query)
    total_events = total_result.scalar_one()

    # Events today
    today_query = select(func.count(AuditLog.id)).where(
        and_(
            AuditLog.created_at >= start_of_today,
            *base_conditions
        )
    )
    today_result = await db.execute(today_query)
    events_today = today_result.scalar_one()

    # Events this week
    week_query = select(func.count(AuditLog.id)).where(
        and_(
            AuditLog.created_at >= start_of_week,
            *base_conditions
        )
    )
    week_result = await db.execute(week_query)
    events_this_week = week_result.scalar_one()

    # Events by action
    action_query = (
        select(AuditLog.action, func.count(AuditLog.id))
        .where(and_(AuditLog.created_at >= start_period, *base_conditions))
        .group_by(AuditLog.action)
        .order_by(desc(func.count(AuditLog.id)))
    )
    action_result = await db.execute(action_query)
    events_by_action = {row[0]: row[1] for row in action_result.all()}

    # Events by resource type
    resource_query = (
        select(AuditLog.resource_type, func.count(AuditLog.id))
        .where(
            and_(
                AuditLog.created_at >= start_period,
                AuditLog.resource_type.isnot(None),
                *base_conditions
            )
        )
        .group_by(AuditLog.resource_type)
        .order_by(desc(func.count(AuditLog.id)))
    )
    resource_result = await db.execute(resource_query)
    events_by_resource_type = {row[0]: row[1] for row in resource_result.all() if row[0]}

    # Top users
    user_query = (
        select(AuditLog.user_id, func.count(AuditLog.id))
        .where(
            and_(
                AuditLog.created_at >= start_period,
                AuditLog.user_id.isnot(None),
                *base_conditions
            )
        )
        .group_by(AuditLog.user_id)
        .order_by(desc(func.count(AuditLog.id)))
        .limit(10)
    )
    user_result = await db.execute(user_query)
    top_user_data = user_result.all()

    # Fetch user emails
    user_ids = [row[0] for row in top_user_data if row[0]]
    user_map = {}
    if user_ids:
        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = users_result.scalars().all()
        user_map = {user.id: user.email for user in users}

    top_users = [
        {
            "user_id": str(row[0]) if row[0] else None,
            "email": user_map.get(row[0], "Unknown"),
            "event_count": row[1],
        }
        for row in top_user_data
    ]

    # Daily activity trend (last 7 days)
    trend_data = []
    for i in range(7):
        day_start = start_of_today - timedelta(days=6-i)
        day_end = day_start + timedelta(days=1)

        day_query = select(func.count(AuditLog.id)).where(
            and_(
                AuditLog.created_at >= day_start,
                AuditLog.created_at < day_end,
                *base_conditions
            )
        )
        day_result = await db.execute(day_query)
        day_count = day_result.scalar_one()

        trend_data.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": day_count,
        })

    return AuditLogStatsResponse(
        total_events=total_events,
        events_today=events_today,
        events_this_week=events_this_week,
        events_by_action=events_by_action,
        events_by_resource_type=events_by_resource_type,
        top_users=top_users,
        recent_activity_trend=trend_data,
    )


@router.get("/audit-logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Get a specific audit log entry.

    Admin-only endpoint to retrieve detailed information about a single audit event.
    """
    try:
        log_uuid = UUID(log_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid log_id format"
        )

    result = await db.execute(
        select(AuditLog).where(AuditLog.id == log_uuid)
    )
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found"
        )

    # Fetch user email if available
    user_email = None
    if log.user_id:
        user_result = await db.execute(
            select(User.email).where(User.id == log.user_id)
        )
        user_email = user_result.scalar_one_or_none()

    return AuditLogResponse(
        id=str(log.id),
        organization_id=str(log.organization_id) if log.organization_id else None,
        tenant_id=str(log.organization_id) if log.organization_id else None,
        user_id=str(log.user_id) if log.user_id else None,
        user_email=user_email,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=str(log.resource_id) if log.resource_id else None,
        details=log.details or {},
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        created_at=log.created_at,
    )


@router.get("/audit-logs/export", response_model=AuditLogExportResponse)
async def export_audit_logs(
    format: str = Query("json", description="Export format (json or csv)"),
    # Filter parameters
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant/organization ID"),
    start_date: Optional[datetime] = Query(None, description="Filter events after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter events before this date"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum records to export"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Export audit logs to JSON or CSV format.

    Admin-only endpoint to export audit logs for compliance or reporting.
    Limited to 10,000 records per export.
    """
    if format.lower() not in ["json", "csv"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be 'json' or 'csv'"
        )

    # Build query conditions
    conditions = []

    if tenant_id:
        try:
            conditions.append(AuditLog.organization_id == UUID(tenant_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant_id format"
            )

    if action:
        conditions.append(AuditLog.action == action)

    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)

    if user_id:
        try:
            conditions.append(AuditLog.user_id == UUID(user_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user_id format"
            )

    if start_date:
        conditions.append(AuditLog.created_at >= start_date)

    if end_date:
        conditions.append(AuditLog.created_at <= end_date)

    # Build and execute query
    query = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query)
    logs = result.scalars().all()

    # Fetch user emails
    user_ids = {log.user_id for log in logs if log.user_id}
    user_map = {}
    if user_ids:
        users_result = await db.execute(
            select(User).where(User.id.in_(user_ids))
        )
        users = users_result.scalars().all()
        user_map = {user.id: user.email for user in users}

    # Build export data
    export_data = [
        {
            "id": str(log.id),
            "timestamp": log.created_at.isoformat() if log.created_at else None,
            "organization_id": str(log.organization_id) if log.organization_id else None,
            "user_id": str(log.user_id) if log.user_id else None,
            "user_email": user_map.get(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "details": log.details,
            "ip_address": log.ip_address,
        }
        for log in logs
    ]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"audit_logs_{timestamp}.{format.lower()}"

    return AuditLogExportResponse(
        filename=filename,
        format=format.lower(),
        total_records=len(export_data),
        data=export_data if format.lower() == "json" else None,
    )


@router.get("/audit-logs/actions", response_model=List[str])
async def list_audit_actions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    List all unique action types in audit logs.

    Admin-only endpoint to get available action types for filtering.
    """
    result = await db.execute(
        select(AuditLog.action)
        .distinct()
        .where(AuditLog.action.isnot(None))
        .order_by(AuditLog.action)
    )
    actions = [row[0] for row in result.all() if row[0]]
    return actions


@router.get("/audit-logs/resource-types", response_model=List[str])
async def list_resource_types(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    List all unique resource types in audit logs.

    Admin-only endpoint to get available resource types for filtering.
    """
    result = await db.execute(
        select(AuditLog.resource_type)
        .distinct()
        .where(AuditLog.resource_type.isnot(None))
        .order_by(AuditLog.resource_type)
    )
    resource_types = [row[0] for row in result.all() if row[0]]
    return resource_types
