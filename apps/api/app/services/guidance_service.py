"""
Guidance Service (Slice 2C: Project Genesis)
Reference: blueprint.md §7 - Section Guidance

Service functions for managing project-specific guidance lifecycle:
- Mark guidance as stale when blueprint changes
- Trigger regeneration of guidance
- Track version history for audit
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.project_guidance import (
    GuidanceSection,
    GuidanceStatus,
    ProjectGuidance,
)
from app.models.pil_job import PILJob, PILJobStatus, PILJobType, PILJobPriority


async def mark_guidance_stale(
    db: AsyncSession,
    project_id: UUID,
    reason: str = "blueprint_updated"
) -> int:
    """
    Mark all active guidance for a project as stale.

    Called when the blueprint changes and existing guidance
    needs to be regenerated.

    Args:
        db: Database session
        project_id: Project UUID
        reason: Reason for marking as stale (for audit)

    Returns:
        Number of guidance records marked as stale
    """
    # Update all active guidance for this project to stale status
    result = await db.execute(
        sql_update(ProjectGuidance)
        .where(
            ProjectGuidance.project_id == project_id,
            ProjectGuidance.is_active == True,
            ProjectGuidance.status == GuidanceStatus.READY.value,
        )
        .values(
            status=GuidanceStatus.STALE.value,
            updated_at=datetime.utcnow(),
        )
        .returning(ProjectGuidance.id)
    )
    stale_count = len(result.fetchall())
    await db.flush()  # Don't commit yet - let caller handle transaction
    return stale_count


async def trigger_guidance_regeneration(
    db: AsyncSession,
    tenant_id: UUID,
    project_id: UUID,
    blueprint_id: UUID,
    blueprint_version: int,
) -> PILJob:
    """
    Trigger regeneration of project guidance.

    Creates a new PROJECT_GENESIS job to regenerate all section guidance
    based on the new blueprint version.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        project_id: Project UUID
        blueprint_id: Blueprint UUID
        blueprint_version: Current blueprint version

    Returns:
        The created PILJob for tracking
    """
    # First, mark existing guidance as stale
    await mark_guidance_stale(db, project_id, reason="regeneration_triggered")

    # Create a new PROJECT_GENESIS job
    job = PILJob(
        tenant_id=tenant_id,
        project_id=project_id,
        blueprint_id=blueprint_id,
        job_type=PILJobType.PROJECT_GENESIS,
        status=PILJobStatus.PENDING,
        priority=PILJobPriority.HIGH,
        input_data={
            "trigger": "regeneration",
            "blueprint_version": blueprint_version,
        },
    )
    db.add(job)
    await db.flush()

    return job


async def get_guidance_status_summary(
    db: AsyncSession,
    project_id: UUID,
) -> dict:
    """
    Get a summary of guidance status for all sections.

    Args:
        db: Database session
        project_id: Project UUID

    Returns:
        Dictionary with section statuses
    """
    result = await db.execute(
        select(ProjectGuidance)
        .where(
            ProjectGuidance.project_id == project_id,
            ProjectGuidance.is_active == True,
        )
    )
    guidance_list = result.scalars().all()

    status_summary = {
        "total_sections": len(GuidanceSection),
        "ready": 0,
        "generating": 0,
        "pending": 0,
        "stale": 0,
        "failed": 0,
        "missing": 0,
        "sections": {},
    }

    # Map found guidance
    found_sections = set()
    for guidance in guidance_list:
        section = guidance.section
        found_sections.add(section)
        status_summary["sections"][section] = {
            "status": guidance.status,
            "blueprint_version": guidance.blueprint_version,
            "updated_at": guidance.updated_at.isoformat() if guidance.updated_at else None,
        }

        # Count by status
        status_key = guidance.status
        if status_key in status_summary:
            status_summary[status_key] += 1

    # Count missing sections
    all_sections = {s.value for s in GuidanceSection}
    missing = all_sections - found_sections
    status_summary["missing"] = len(missing)

    # Calculate overall health
    if status_summary["ready"] == len(GuidanceSection):
        status_summary["overall"] = "healthy"
    elif status_summary["stale"] > 0:
        status_summary["overall"] = "stale"
    elif status_summary["generating"] > 0:
        status_summary["overall"] = "generating"
    elif status_summary["failed"] > 0:
        status_summary["overall"] = "error"
    else:
        status_summary["overall"] = "incomplete"

    return status_summary


async def deactivate_old_guidance(
    db: AsyncSession,
    project_id: UUID,
    new_blueprint_version: int,
) -> int:
    """
    Deactivate guidance from older blueprint versions.

    Called when new guidance is generated to maintain version history
    while marking old records as inactive.

    Args:
        db: Database session
        project_id: Project UUID
        new_blueprint_version: The new version being activated

    Returns:
        Number of records deactivated
    """
    result = await db.execute(
        sql_update(ProjectGuidance)
        .where(
            ProjectGuidance.project_id == project_id,
            ProjectGuidance.blueprint_version < new_blueprint_version,
            ProjectGuidance.is_active == True,
        )
        .values(
            is_active=False,
            updated_at=datetime.utcnow(),
        )
        .returning(ProjectGuidance.id)
    )
    deactivated_count = len(result.fetchall())
    await db.flush()
    return deactivated_count
