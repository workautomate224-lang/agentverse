"""
Run Manifest Schemas - PHASE 2: Reproducibility & Auditability

Pydantic v2 schemas for run manifest API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Version Info Schemas
# =============================================================================

class VersionsInfo(BaseModel):
    """Version information for reproducibility."""
    code_version: str = Field(
        default="unknown",
        description="Git SHA or docker image tag"
    )
    sim_engine_version: str = Field(
        default="1.0.0",
        description="Simulation engine version"
    )
    rules_version: str = Field(
        default="unknown",
        description="Hash of rules content"
    )
    personas_version: str = Field(
        default="unknown",
        description="Hash of persona set content"
    )
    model_version: str = Field(
        default="unknown",
        description="LLM model name + params"
    )
    dataset_version: str = Field(
        default="unknown",
        description="Dataset version if any"
    )


class ConfigSnapshot(BaseModel):
    """Normalized configuration snapshot."""
    max_ticks: int = Field(default=100, ge=1, le=10000)
    agent_batch_size: int = Field(default=100, ge=1, le=1000)
    run_mode: str = Field(default="society")
    environment_params: Optional[Dict[str, Any]] = None
    scheduler_config: Optional[Dict[str, Any]] = None
    scenario_patch: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"  # Allow additional config fields


# =============================================================================
# Response Schemas
# =============================================================================

class RunManifestResponse(BaseModel):
    """Response schema for GET /manifest endpoint."""
    id: UUID
    run_id: UUID
    project_id: UUID
    node_id: Optional[UUID] = None
    seed: int = Field(..., description="Global deterministic seed")
    config_json: Dict[str, Any] = Field(
        ...,
        description="Normalized config snapshot"
    )
    versions_json: Dict[str, Any] = Field(
        ...,
        description="Version info for all components"
    )
    manifest_hash: str = Field(
        ...,
        description="SHA256 hash of canonical manifest"
    )
    storage_ref: Optional[Dict[str, Any]] = Field(
        None,
        description="S3 pointer if stored externally"
    )
    is_immutable: bool = Field(
        default=True,
        description="True if manifest cannot be modified"
    )
    source_run_id: Optional[UUID] = Field(
        None,
        description="Original run_id if this is a reproduction"
    )
    created_at: datetime
    created_by_user_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class ProvenanceResponse(BaseModel):
    """Short audit summary for GET /provenance endpoint."""
    run_id: UUID
    manifest_hash: str
    seed: int
    created_at: datetime
    created_by_user_id: Optional[UUID] = None
    source_run_id: Optional[UUID] = None
    node_id: Optional[UUID] = None
    project_id: UUID
    is_reproduction: bool = Field(
        default=False,
        description="True if this run was reproduced from another"
    )
    code_version: str
    engine_version: str
    branch_info: Optional[Dict[str, Any]] = Field(
        None,
        description="Branch/fork information if applicable"
    )


# =============================================================================
# Reproduce Endpoint Schemas
# =============================================================================

class ReproduceMode(str, Enum):
    """Mode for reproduction endpoint."""
    SAME_NODE = "same_node"
    FORK_NODE = "fork_node"


class ReproduceRunRequest(BaseModel):
    """Request schema for POST /reproduce endpoint."""
    mode: ReproduceMode = Field(
        default=ReproduceMode.FORK_NODE,
        description="same_node: attach to same node, fork_node: create new node"
    )
    label: Optional[str] = Field(
        None,
        description="Optional label for the new run"
    )
    auto_start: bool = Field(
        default=False,
        description="Start the run immediately after creation"
    )


class ReproduceRunResponse(BaseModel):
    """Response schema for POST /reproduce endpoint."""
    new_run_id: UUID = Field(..., description="ID of the newly created run")
    new_node_id: Optional[UUID] = Field(
        None,
        description="ID of new node (if fork_node mode)"
    )
    manifest_hash: str = Field(
        ...,
        description="Should match original manifest_hash"
    )
    seed: int = Field(..., description="Same seed as original")
    mode: ReproduceMode
    source_run_id: UUID = Field(..., description="Original run that was reproduced")
    task_id: Optional[str] = Field(
        None,
        description="Celery task ID if auto_start=true"
    )
    deep_link: str = Field(
        ...,
        description="UI-friendly deep link to the new run"
    )


# =============================================================================
# Manifest Creation (Internal Use)
# =============================================================================

class CreateManifestInput(BaseModel):
    """Internal schema for creating a manifest."""
    tenant_id: UUID
    project_id: UUID
    run_id: UUID
    node_id: Optional[UUID] = None
    seed: int
    config_json: Dict[str, Any]
    versions_json: Dict[str, Any]
    created_by_user_id: Optional[UUID] = None
    source_run_id: Optional[UUID] = None


# =============================================================================
# List/Search Schemas
# =============================================================================

class ManifestSearchParams(BaseModel):
    """Parameters for searching manifests."""
    project_id: Optional[UUID] = None
    node_id: Optional[UUID] = None
    manifest_hash: Optional[str] = None
    seed: Optional[int] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class ManifestListResponse(BaseModel):
    """Response for listing manifests."""
    manifests: List[RunManifestResponse]
    total: int


# =============================================================================
# Integrity Verification
# =============================================================================

class VerifyManifestResponse(BaseModel):
    """Response for manifest integrity verification."""
    run_id: UUID
    manifest_hash: str
    computed_hash: str
    is_valid: bool = Field(
        ...,
        description="True if computed hash matches stored hash"
    )
    verified_at: datetime
