"""
Source Capability Registry Seed Data
Reference: temporal.md §5 - DataGateway Source Capability Registry

This file defines the initial set of source capabilities for temporal isolation.
Run this seed to populate the source_capabilities table for a tenant.

Each source declares:
- Timestamp availability (full, partial, none)
- Historical query support
- Safe isolation levels (1=Basic, 2=Strict, 3=Audit-First)

Usage:
    from app.db.seed_sources import seed_source_capabilities
    await seed_source_capabilities(db, tenant_id)
"""

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source_registry import SourceCapability, SourceCapabilityAudit


# =============================================================================
# Seed Data Definitions
# =============================================================================

# Initial source capabilities per temporal.md §5
SOURCE_CAPABILITY_SEEDS: List[Dict[str, Any]] = [
    # ---------------------------------------------------------------------
    # Census Data Sources (full timestamp support)
    # ---------------------------------------------------------------------
    {
        "source_name": "census_bureau",
        "display_name": "US Census Bureau",
        "description": "US Census Bureau demographic and population data with full historical support via ACS/Decennial APIs.",
        "endpoint_pattern": "/data/*",
        "timestamp_availability": "full",
        "historical_query_support": True,
        "timestamp_field": "year",
        "required_cutoff_params": {
            "param_name": "time",
            "format": "year",
            "description": "Year parameter to limit data to specific time period",
        },
        "safe_isolation_levels": [1, 2, 3],
        "block_message": None,
        "owner": "data-team",
        "compliance_classification": "approved",
        "policy_version": "1.0.0",
    },
    {
        "source_name": "dosm_census",
        "display_name": "DOSM Census Malaysia",
        "description": "Department of Statistics Malaysia census data with historical time series.",
        "endpoint_pattern": "/api/*",
        "timestamp_availability": "full",
        "historical_query_support": True,
        "timestamp_field": "year",
        "required_cutoff_params": {
            "param_name": "year",
            "format": "year",
        },
        "safe_isolation_levels": [1, 2, 3],
        "block_message": None,
        "owner": "data-team",
        "compliance_classification": "approved",
        "policy_version": "1.0.0",
    },
    {
        "source_name": "eurostat",
        "display_name": "Eurostat",
        "description": "European Union statistics office with comprehensive historical data.",
        "endpoint_pattern": "/api/*",
        "timestamp_availability": "full",
        "historical_query_support": True,
        "timestamp_field": "time",
        "required_cutoff_params": {
            "param_name": "time",
            "format": "iso8601",
        },
        "safe_isolation_levels": [1, 2, 3],
        "block_message": None,
        "owner": "data-team",
        "compliance_classification": "approved",
        "policy_version": "1.0.0",
    },
    # ---------------------------------------------------------------------
    # Regional Data Sources (full timestamp support)
    # ---------------------------------------------------------------------
    {
        "source_name": "regional_demographics",
        "display_name": "Regional Demographics",
        "description": "Regional demographic profiles with historical snapshots.",
        "endpoint_pattern": "/regions/*",
        "timestamp_availability": "full",
        "historical_query_support": True,
        "timestamp_field": "snapshot_date",
        "required_cutoff_params": {
            "param_name": "as_of_date",
            "format": "iso8601",
        },
        "safe_isolation_levels": [1, 2, 3],
        "block_message": None,
        "owner": "data-team",
        "compliance_classification": "approved",
        "policy_version": "1.0.0",
    },
    {
        "source_name": "economic_indicators",
        "display_name": "Economic Indicators",
        "description": "Economic indicators (GDP, inflation, unemployment) with time series.",
        "endpoint_pattern": "/economic/*",
        "timestamp_availability": "full",
        "historical_query_support": True,
        "timestamp_field": "period",
        "required_cutoff_params": {
            "param_name": "period_end",
            "format": "iso8601",
        },
        "safe_isolation_levels": [1, 2, 3],
        "block_message": None,
        "owner": "data-team",
        "compliance_classification": "approved",
        "policy_version": "1.0.0",
    },
    # ---------------------------------------------------------------------
    # Market Data Sources (partial timestamp support)
    # ---------------------------------------------------------------------
    {
        "source_name": "market_prices",
        "display_name": "Market Prices",
        "description": "Market price data with timestamps but limited historical query support.",
        "endpoint_pattern": "/prices/*",
        "timestamp_availability": "partial",
        "historical_query_support": False,
        "timestamp_field": "timestamp",
        "required_cutoff_params": None,
        "safe_isolation_levels": [1, 2],
        "block_message": "Blocked in Level 3 Backtest: Limited historical query support. Use archived snapshots instead.",
        "owner": "data-team",
        "compliance_classification": "restricted",
        "policy_version": "1.0.0",
    },
    {
        "source_name": "news_feed",
        "display_name": "News Feed",
        "description": "News articles with publication timestamps.",
        "endpoint_pattern": "/news/*",
        "timestamp_availability": "full",
        "historical_query_support": False,
        "timestamp_field": "published_at",
        "required_cutoff_params": {
            "param_name": "before",
            "format": "iso8601",
        },
        "safe_isolation_levels": [1, 2],
        "block_message": "Blocked in Level 3 Backtest: No native as-of query support.",
        "owner": "data-team",
        "compliance_classification": "restricted",
        "policy_version": "1.0.0",
    },
    # ---------------------------------------------------------------------
    # LLM Sources (no timestamp support - restricted)
    # ---------------------------------------------------------------------
    {
        "source_name": "openrouter",
        "display_name": "OpenRouter LLM API",
        "description": "LLM inference API. No timestamp support - model weights contain knowledge cutoff but no granular control.",
        "endpoint_pattern": "/api/v1/*",
        "timestamp_availability": "none",
        "historical_query_support": False,
        "timestamp_field": None,
        "required_cutoff_params": None,
        "safe_isolation_levels": [1],
        "block_message": "Blocked in Strict/Audit Backtest: LLM models have inherent knowledge cutoffs that cannot be controlled. Use DataGateway-only tools in backtest mode.",
        "owner": "ai-team",
        "compliance_classification": "restricted",
        "policy_version": "1.0.0",
    },
    {
        "source_name": "openai",
        "display_name": "OpenAI API",
        "description": "OpenAI inference API. No timestamp support for model knowledge.",
        "endpoint_pattern": "/v1/*",
        "timestamp_availability": "none",
        "historical_query_support": False,
        "timestamp_field": None,
        "required_cutoff_params": None,
        "safe_isolation_levels": [1],
        "block_message": "Blocked in Strict/Audit Backtest: LLM models have inherent knowledge cutoffs that cannot be controlled.",
        "owner": "ai-team",
        "compliance_classification": "restricted",
        "policy_version": "1.0.0",
    },
    {
        "source_name": "anthropic",
        "display_name": "Anthropic API",
        "description": "Anthropic Claude inference API. No timestamp support for model knowledge.",
        "endpoint_pattern": "/v1/*",
        "timestamp_availability": "none",
        "historical_query_support": False,
        "timestamp_field": None,
        "required_cutoff_params": None,
        "safe_isolation_levels": [1],
        "block_message": "Blocked in Strict/Audit Backtest: LLM models have inherent knowledge cutoffs that cannot be controlled.",
        "owner": "ai-team",
        "compliance_classification": "restricted",
        "policy_version": "1.0.0",
    },
    # ---------------------------------------------------------------------
    # Internal Data Sources (simulation artifacts)
    # ---------------------------------------------------------------------
    {
        "source_name": "simulation_artifacts",
        "display_name": "Simulation Artifacts",
        "description": "Internal simulation run artifacts with full versioning and timestamps.",
        "endpoint_pattern": "/artifacts/*",
        "timestamp_availability": "full",
        "historical_query_support": True,
        "timestamp_field": "created_at",
        "required_cutoff_params": {
            "param_name": "created_before",
            "format": "iso8601",
        },
        "safe_isolation_levels": [1, 2, 3],
        "block_message": None,
        "owner": "platform-team",
        "compliance_classification": "approved",
        "policy_version": "1.0.0",
    },
    {
        "source_name": "persona_snapshots",
        "display_name": "Persona Snapshots",
        "description": "Versioned persona snapshots with creation timestamps.",
        "endpoint_pattern": "/personas/*",
        "timestamp_availability": "full",
        "historical_query_support": True,
        "timestamp_field": "snapshot_at",
        "required_cutoff_params": {
            "param_name": "as_of",
            "format": "iso8601",
        },
        "safe_isolation_levels": [1, 2, 3],
        "block_message": None,
        "owner": "platform-team",
        "compliance_classification": "approved",
        "policy_version": "1.0.0",
    },
    {
        "source_name": "ground_truth",
        "display_name": "Ground Truth Data",
        "description": "Ground truth labels for calibration with event timestamps.",
        "endpoint_pattern": "/ground_truth/*",
        "timestamp_availability": "full",
        "historical_query_support": True,
        "timestamp_field": "event_date",
        "required_cutoff_params": {
            "param_name": "event_before",
            "format": "iso8601",
        },
        "safe_isolation_levels": [1, 2, 3],
        "block_message": None,
        "owner": "platform-team",
        "compliance_classification": "approved",
        "policy_version": "1.0.0",
    },
    # ---------------------------------------------------------------------
    # Web Sources (no timestamp support - blocked in backtest)
    # ---------------------------------------------------------------------
    {
        "source_name": "web_search",
        "display_name": "Web Search API",
        "description": "Generic web search. Returns current results with no historical control.",
        "endpoint_pattern": "/search/*",
        "timestamp_availability": "none",
        "historical_query_support": False,
        "timestamp_field": None,
        "required_cutoff_params": None,
        "safe_isolation_levels": [1],
        "block_message": "Blocked in Backtest: Web search returns current results that cannot be controlled for historical accuracy.",
        "owner": "data-team",
        "compliance_classification": "restricted",
        "policy_version": "1.0.0",
    },
    {
        "source_name": "wikipedia",
        "display_name": "Wikipedia API",
        "description": "Wikipedia content. Partial historical support via revision IDs.",
        "endpoint_pattern": "/api/*",
        "timestamp_availability": "partial",
        "historical_query_support": True,
        "timestamp_field": "revision_timestamp",
        "required_cutoff_params": {
            "param_name": "oldid",
            "format": "revision_id",
            "description": "Use specific revision ID for historical content",
        },
        "safe_isolation_levels": [1, 2],
        "block_message": "Blocked in Level 3 Backtest: Requires specific revision ID management for full audit compliance.",
        "owner": "data-team",
        "compliance_classification": "restricted",
        "policy_version": "1.0.0",
    },
]


# =============================================================================
# Seed Functions
# =============================================================================

async def seed_source_capabilities(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
    skip_existing: bool = True,
) -> List[SourceCapability]:
    """
    Seed source capabilities for a tenant.

    Args:
        db: Database session
        tenant_id: Tenant UUID to seed capabilities for
        user_id: Optional user UUID for audit trail
        skip_existing: If True, skip sources that already exist

    Returns:
        List of created/existing SourceCapability records
    """
    results: List[SourceCapability] = []

    for seed_data in SOURCE_CAPABILITY_SEEDS:
        source_name = seed_data["source_name"]

        # Check if already exists
        if skip_existing:
            stmt = select(SourceCapability).where(
                SourceCapability.tenant_id == tenant_id,
                SourceCapability.source_name == source_name,
            )
            existing = await db.execute(stmt)
            existing_source = existing.scalar_one_or_none()

            if existing_source:
                results.append(existing_source)
                continue

        # Create new source capability
        source = SourceCapability(
            tenant_id=tenant_id,
            source_name=seed_data["source_name"],
            display_name=seed_data["display_name"],
            description=seed_data.get("description"),
            endpoint_pattern=seed_data.get("endpoint_pattern", "*"),
            timestamp_availability=seed_data.get("timestamp_availability", "none"),
            historical_query_support=seed_data.get("historical_query_support", False),
            timestamp_field=seed_data.get("timestamp_field"),
            required_cutoff_params=seed_data.get("required_cutoff_params"),
            safe_isolation_levels=seed_data.get("safe_isolation_levels", [1]),
            block_message=seed_data.get("block_message"),
            owner=seed_data.get("owner", "unassigned"),
            review_date=date.today(),
            compliance_classification=seed_data.get("compliance_classification", "pending_review"),
            policy_version=seed_data.get("policy_version", "1.0.0"),
            is_active=True,
        )
        db.add(source)
        await db.flush()

        # Create audit entry
        audit = SourceCapabilityAudit(
            tenant_id=tenant_id,
            source_capability_id=source.id,
            user_id=user_id,
            action="create",
            previous_version=None,
            new_version=source.policy_version,
            changes=seed_data,
            reason="Initial seed from temporal isolation implementation",
        )
        db.add(audit)

        results.append(source)

    await db.commit()
    return results


async def get_source_capability(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    source_name: str,
) -> Optional[SourceCapability]:
    """
    Get a specific source capability by name.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        source_name: Source identifier

    Returns:
        SourceCapability or None
    """
    stmt = select(SourceCapability).where(
        SourceCapability.tenant_id == tenant_id,
        SourceCapability.source_name == source_name,
        SourceCapability.is_active == True,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_source_capabilities(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    isolation_level: Optional[int] = None,
    only_active: bool = True,
) -> List[SourceCapability]:
    """
    List source capabilities for a tenant.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        isolation_level: Optional filter by safe isolation level
        only_active: If True, only return active sources

    Returns:
        List of SourceCapability records
    """
    stmt = select(SourceCapability).where(
        SourceCapability.tenant_id == tenant_id,
    )

    if only_active:
        stmt = stmt.where(SourceCapability.is_active == True)

    result = await db.execute(stmt)
    sources = list(result.scalars().all())

    # Filter by isolation level if specified
    if isolation_level is not None:
        sources = [s for s in sources if s.is_safe_for_level(isolation_level)]

    return sources


async def update_source_capability(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    source_name: str,
    updates: Dict[str, Any],
    user_id: Optional[uuid.UUID] = None,
    reason: Optional[str] = None,
) -> Optional[SourceCapability]:
    """
    Update a source capability with audit trail.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        source_name: Source identifier
        updates: Dictionary of fields to update
        user_id: User making the change
        reason: Reason for the change

    Returns:
        Updated SourceCapability or None
    """
    source = await get_source_capability(db, tenant_id, source_name)
    if not source:
        return None

    # Capture previous state
    previous_version = source.policy_version
    changes = {}

    # Apply updates
    for key, value in updates.items():
        if hasattr(source, key):
            old_value = getattr(source, key)
            if old_value != value:
                changes[key] = {"old": old_value, "new": value}
                setattr(source, key, value)

    # Increment version if changes made
    if changes:
        # Simple version increment
        version_parts = source.policy_version.split(".")
        version_parts[-1] = str(int(version_parts[-1]) + 1)
        source.policy_version = ".".join(version_parts)

        # Create audit entry
        audit = SourceCapabilityAudit(
            tenant_id=tenant_id,
            source_capability_id=source.id,
            user_id=user_id,
            action="update",
            previous_version=previous_version,
            new_version=source.policy_version,
            changes=changes,
            reason=reason,
        )
        db.add(audit)

    await db.commit()
    return source


async def deactivate_source_capability(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    source_name: str,
    user_id: Optional[uuid.UUID] = None,
    reason: Optional[str] = None,
) -> Optional[SourceCapability]:
    """
    Deactivate a source capability (soft delete with audit).

    Args:
        db: Database session
        tenant_id: Tenant UUID
        source_name: Source identifier
        user_id: User making the change
        reason: Reason for deactivation

    Returns:
        Deactivated SourceCapability or None
    """
    return await update_source_capability(
        db=db,
        tenant_id=tenant_id,
        source_name=source_name,
        updates={"is_active": False},
        user_id=user_id,
        reason=reason or "Source deactivated",
    )


# =============================================================================
# CLI Seed Command (for manual seeding)
# =============================================================================

async def seed_all_tenants(db: AsyncSession) -> Dict[str, int]:
    """
    Seed source capabilities for all existing tenants.

    Returns:
        Dict mapping tenant_id to number of sources seeded
    """
    from app.models.tenant import Tenant

    stmt = select(Tenant)
    result = await db.execute(stmt)
    tenants = result.scalars().all()

    results = {}
    for tenant in tenants:
        sources = await seed_source_capabilities(db, tenant.id, skip_existing=True)
        results[str(tenant.id)] = len(sources)

    return results
