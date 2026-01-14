"""
DataGateway Service - Centralized External Data Access Gateway
Reference: temporal.md §5 - DataGateway, §4 - Temporal Knowledge Isolation

This service is the SINGLE ENTRY POINT for ALL external data access.
No external data should be fetched without going through DataGateway.

Key Responsibilities:
1. Check source capability registry before allowing access
2. Enforce temporal cutoff using LeakageGuard
3. Generate per-request manifest entries with payload hashes
4. Block unsafe sources at strict isolation levels
5. Log all data access for audit

Usage:
    gateway = DataGateway(db, leakage_guard)
    response = await gateway.request(
        source_name="census_bureau",
        endpoint="/data/population",
        params={"region": "US"},
        context=DataGatewayContext(
            tenant_id=tenant_id,
            project_id=project_id,
            run_id=run_id,
            cutoff_time=as_of_datetime,
            isolation_level=2,
        ),
    )
"""

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source_registry import SourceCapability
from app.services.leakage_guard import (
    LeakageGuard,
    LeakageGuardStats,
    LeakageViolationError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class DataGatewayContext(BaseModel):
    """Context for DataGateway requests - mirrors LLMRouterContext pattern."""
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    run_id: Optional[str] = None
    node_id: Optional[str] = None
    user_id: Optional[str] = None
    cutoff_time: Optional[datetime] = None
    isolation_level: int = Field(default=1, ge=1, le=3)
    temporal_mode: str = Field(default="live")  # 'live' or 'backtest'


class ManifestEntry(BaseModel):
    """A single entry in the data access manifest."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_name: str
    endpoint: str
    params: Dict[str, Any]
    params_hash: str
    time_window: Optional[Dict[str, Any]] = None  # {start, end} if applicable
    record_count: int = 0
    filtered_count: int = 0
    payload_hash: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    response_time_ms: int = 0


class DataGatewayResponse(BaseModel):
    """Response from DataGateway - includes data and audit metadata."""
    data: Any
    source_name: str
    endpoint: str
    record_count: int
    filtered_count: int
    payload_hash: str
    manifest_entry: ManifestEntry
    leakage_stats: Optional[Dict[str, Any]] = None
    response_time_ms: int = 0


class SourceBlockedError(Exception):
    """Raised when a source is blocked at the current isolation level."""

    def __init__(self, source_name: str, isolation_level: int, message: str):
        super().__init__(message)
        self.source_name = source_name
        self.isolation_level = isolation_level


class SourceNotFoundError(Exception):
    """Raised when a source is not found in the registry."""

    def __init__(self, source_name: str):
        super().__init__(f"Source '{source_name}' not found in registry")
        self.source_name = source_name


# =============================================================================
# DataGateway Service
# =============================================================================

class DataGateway:
    """
    Single entry point for all external data access with temporal enforcement.

    This service composes LeakageGuard for cutoff filtering and adds:
    - Source capability checking from registry
    - Manifest entry generation with payload hashes
    - Isolation level enforcement
    - Structured logging for audit

    Reference: temporal.md §5
    """

    def __init__(
        self,
        db: AsyncSession,
        leakage_guard: Optional[LeakageGuard] = None,
    ):
        """
        Initialize DataGateway.

        Args:
            db: Database session for source registry lookups
            leakage_guard: Optional LeakageGuard for cutoff enforcement
        """
        self.db = db
        self.leakage_guard = leakage_guard
        self._source_registry_cache: Dict[str, SourceCapability] = {}
        self._source_cache_time: float = 0
        self._source_cache_ttl: float = 300  # 5 minutes
        self._manifest_entries: List[ManifestEntry] = []

    async def request(
        self,
        source_name: str,
        endpoint: str,
        params: Dict[str, Any],
        context: DataGatewayContext,
        data_fetcher: Optional[Any] = None,  # Callable to fetch actual data
        raw_data: Optional[Any] = None,  # Or provide data directly for filtering
        timestamp_field: str = "timestamp",
    ) -> DataGatewayResponse:
        """
        Route a data request through the gateway with temporal enforcement.

        Args:
            source_name: Source identifier (e.g., 'census_bureau')
            endpoint: Endpoint being accessed (e.g., '/data/population')
            params: Request parameters
            context: DataGatewayContext with tenant, project, isolation info
            data_fetcher: Optional async callable to fetch data
            raw_data: Optional raw data to filter (if data_fetcher not provided)
            timestamp_field: Field name for timestamp filtering

        Returns:
            DataGatewayResponse with data and audit metadata

        Raises:
            SourceBlockedError: If source is blocked at current isolation level
            SourceNotFoundError: If source is not in registry
            LeakageViolationError: If cutoff is violated in strict mode
        """
        start_time = time.time()

        # 1. Look up source capability
        source = await self._get_source_capability(source_name, context.tenant_id)
        if not source:
            logger.warning(
                f"Source '{source_name}' not found in registry for tenant {context.tenant_id}"
            )
            # In backtest mode, unknown sources are blocked at Level 2+
            if context.temporal_mode == "backtest" and context.isolation_level >= 2:
                raise SourceNotFoundError(source_name)
            # For live mode or Level 1, create a default placeholder
            source = self._create_default_source(source_name)

        # 2. Check if source is safe at current isolation level
        if not source.is_safe_for_level(context.isolation_level):
            block_reason = source.get_block_reason(context.isolation_level)
            logger.warning(
                f"DATAGATEWAY BLOCKED: {source_name} blocked at Level {context.isolation_level} - {block_reason}"
            )
            raise SourceBlockedError(
                source_name=source_name,
                isolation_level=context.isolation_level,
                message=block_reason or f"Source blocked at isolation level {context.isolation_level}",
            )

        # 3. Fetch data (if fetcher provided)
        if data_fetcher is not None:
            data = await data_fetcher()
        elif raw_data is not None:
            data = raw_data
        else:
            data = []

        # 4. Apply LeakageGuard filtering if in backtest mode
        original_count = len(data) if isinstance(data, list) else 0
        filtered_count = 0

        if self.leakage_guard and self.leakage_guard.is_active():
            if isinstance(data, list):
                # Determine timestamp field from source capability or default
                ts_field = source.timestamp_field or timestamp_field
                filtered_data = self.leakage_guard.filter_dataset(data, ts_field)
                filtered_count = original_count - len(filtered_data)
                data = filtered_data

        record_count = len(data) if isinstance(data, list) else 1

        # 5. Compute payload hash
        payload_hash = self._compute_payload_hash(data)
        params_hash = self._compute_params_hash(params)

        # 6. Create manifest entry
        response_time_ms = int((time.time() - start_time) * 1000)
        manifest_entry = ManifestEntry(
            source_name=source_name,
            endpoint=endpoint,
            params=params,
            params_hash=params_hash,
            time_window=self._extract_time_window(params, context),
            record_count=record_count,
            filtered_count=filtered_count,
            payload_hash=payload_hash,
            response_time_ms=response_time_ms,
        )
        self._manifest_entries.append(manifest_entry)

        # 7. Log the access
        logger.info(
            f"DATAGATEWAY: {source_name}:{endpoint} "
            f"records={record_count} filtered={filtered_count} "
            f"level={context.isolation_level} mode={context.temporal_mode}"
        )

        # 8. Return response
        return DataGatewayResponse(
            data=data,
            source_name=source_name,
            endpoint=endpoint,
            record_count=record_count,
            filtered_count=filtered_count,
            payload_hash=payload_hash,
            manifest_entry=manifest_entry,
            leakage_stats=self.leakage_guard.get_stats().to_dict() if self.leakage_guard else None,
            response_time_ms=response_time_ms,
        )

    async def request_with_cutoff(
        self,
        source_name: str,
        endpoint: str,
        params: Dict[str, Any],
        context: DataGatewayContext,
        data_fetcher: Any,
        timestamp_field: str = "timestamp",
    ) -> DataGatewayResponse:
        """
        Convenience method that creates LeakageGuard from context if needed.

        Use this when you don't have a pre-configured LeakageGuard.
        """
        if context.cutoff_time and context.temporal_mode == "backtest":
            if not self.leakage_guard or not self.leakage_guard.is_active():
                self.leakage_guard = LeakageGuard(
                    cutoff_time=context.cutoff_time,
                    enabled=True,
                    strict_mode=(context.isolation_level >= 2),
                )

        return await self.request(
            source_name=source_name,
            endpoint=endpoint,
            params=params,
            context=context,
            data_fetcher=data_fetcher,
            timestamp_field=timestamp_field,
        )

    def get_manifest_entries(self) -> List[ManifestEntry]:
        """Get all manifest entries from this gateway instance."""
        return self._manifest_entries

    def get_manifest_dict(self) -> Dict[str, Any]:
        """Get manifest as a dictionary for storage."""
        return {
            "entries": [e.model_dump() for e in self._manifest_entries],
            "total_records": sum(e.record_count for e in self._manifest_entries),
            "total_filtered": sum(e.filtered_count for e in self._manifest_entries),
            "sources_accessed": list(set(e.source_name for e in self._manifest_entries)),
            "generated_at": datetime.utcnow().isoformat(),
        }

    def clear_manifest(self):
        """Clear manifest entries (e.g., at start of new run)."""
        self._manifest_entries = []

    # =========================================================================
    # Source Registry Methods
    # =========================================================================

    async def _get_source_capability(
        self,
        source_name: str,
        tenant_id: Optional[str],
    ) -> Optional[SourceCapability]:
        """
        Get source capability from registry.

        Uses caching to reduce database lookups.
        """
        # Check cache first
        cache_key = f"{tenant_id}:{source_name}"
        now = time.time()

        if cache_key in self._source_registry_cache:
            if now - self._source_cache_time < self._source_cache_ttl:
                return self._source_registry_cache[cache_key]

        # Query database
        if tenant_id:
            tenant_uuid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
            stmt = select(SourceCapability).where(
                SourceCapability.tenant_id == tenant_uuid,
                SourceCapability.source_name == source_name,
                SourceCapability.is_active == True,
            )
            result = await self.db.execute(stmt)
            source = result.scalar_one_or_none()

            if source:
                self._source_registry_cache[cache_key] = source
                self._source_cache_time = now
                return source

        return None

    async def get_all_sources(
        self,
        tenant_id: str,
        only_active: bool = True,
    ) -> List[SourceCapability]:
        """Get all source capabilities for a tenant."""
        tenant_uuid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
        stmt = select(SourceCapability).where(
            SourceCapability.tenant_id == tenant_uuid,
        )
        if only_active:
            stmt = stmt.where(SourceCapability.is_active == True)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_sources_for_level(
        self,
        tenant_id: str,
        isolation_level: int,
    ) -> List[SourceCapability]:
        """Get sources that are safe at a given isolation level."""
        all_sources = await self.get_all_sources(tenant_id)
        return [s for s in all_sources if s.is_safe_for_level(isolation_level)]

    def _create_default_source(self, source_name: str) -> SourceCapability:
        """Create a default source capability for unknown sources."""
        # Create a transient object (not persisted)
        return SourceCapability(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),  # Placeholder
            source_name=source_name,
            display_name=source_name,
            timestamp_availability="none",
            historical_query_support=False,
            safe_isolation_levels=[1],  # Only safe at Level 1
            owner="unassigned",
            compliance_classification="pending_review",
            is_active=True,
        )

    # =========================================================================
    # Hash Computation Methods
    # =========================================================================

    def _compute_payload_hash(self, data: Any) -> str:
        """
        Compute SHA256 hash of payload for integrity verification.

        Uses canonical JSON serialization.
        """
        if data is None:
            return hashlib.sha256(b"null").hexdigest()

        try:
            canonical = json.dumps(data, sort_keys=True, separators=(',', ':'), default=str)
            return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
        except (TypeError, ValueError):
            # Fallback for non-serializable data
            return hashlib.sha256(str(data).encode('utf-8')).hexdigest()

    def _compute_params_hash(self, params: Dict[str, Any]) -> str:
        """Compute hash of request parameters."""
        canonical = json.dumps(params, sort_keys=True, separators=(',', ':'), default=str)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]

    def _extract_time_window(
        self,
        params: Dict[str, Any],
        context: DataGatewayContext,
    ) -> Optional[Dict[str, Any]]:
        """Extract time window from params or context."""
        time_window = {}

        # Check common parameter names for time bounds
        for start_key in ['start_date', 'start_time', 'from', 'time_start']:
            if start_key in params:
                time_window['start'] = str(params[start_key])
                break

        for end_key in ['end_date', 'end_time', 'to', 'time_end', 'as_of']:
            if end_key in params:
                time_window['end'] = str(params[end_key])
                break

        # If cutoff is set, that's the effective end
        if context.cutoff_time:
            time_window['cutoff'] = context.cutoff_time.isoformat()

        return time_window if time_window else None


# =============================================================================
# Factory Functions
# =============================================================================

def create_data_gateway(
    db: AsyncSession,
    context: DataGatewayContext,
) -> DataGateway:
    """
    Create a DataGateway with LeakageGuard configured from context.

    Args:
        db: Database session
        context: DataGatewayContext with cutoff and isolation settings

    Returns:
        Configured DataGateway instance
    """
    leakage_guard = None

    if context.temporal_mode == "backtest" and context.cutoff_time:
        leakage_guard = LeakageGuard(
            cutoff_time=context.cutoff_time,
            enabled=True,
            strict_mode=(context.isolation_level >= 2),
        )

    return DataGateway(db=db, leakage_guard=leakage_guard)


def create_data_gateway_from_project(
    db: AsyncSession,
    project: Any,  # ProjectSpec
) -> Tuple[DataGateway, DataGatewayContext]:
    """
    Create a DataGateway from a ProjectSpec.

    Args:
        db: Database session
        project: ProjectSpec with temporal context

    Returns:
        Tuple of (DataGateway, DataGatewayContext)
    """
    context = DataGatewayContext(
        tenant_id=str(project.tenant_id),
        project_id=str(project.id),
        cutoff_time=project.as_of_datetime,
        isolation_level=project.isolation_level,
        temporal_mode=project.temporal_mode,
    )

    gateway = create_data_gateway(db, context)
    return gateway, context


async def get_data_gateway(
    db: AsyncSession,
    tenant_id: str,
    project_id: Optional[str] = None,
    cutoff_time: Optional[datetime] = None,
    isolation_level: int = 1,
    temporal_mode: str = "live",
) -> DataGateway:
    """
    Get a DataGateway instance with specified configuration.

    Convenience function for creating gateways without full context.
    """
    context = DataGatewayContext(
        tenant_id=tenant_id,
        project_id=project_id,
        cutoff_time=cutoff_time,
        isolation_level=isolation_level,
        temporal_mode=temporal_mode,
    )
    return create_data_gateway(db, context)
