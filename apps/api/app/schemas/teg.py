"""
Thought Expansion Graph (TEG) API Schemas

Pydantic v2 schemas for TEG API endpoints.
Reference: docs/TEG_UNIVERSE_MAP_EXECUTION.md
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Enums (mirror the model enums)
# =============================================================================

class TEGNodeType(str, Enum):
    """Type of TEG node."""
    OUTCOME_VERIFIED = "OUTCOME_VERIFIED"
    SCENARIO_DRAFT = "SCENARIO_DRAFT"
    EVIDENCE = "EVIDENCE"


class TEGNodeStatus(str, Enum):
    """Status of TEG node."""
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class TEGEdgeRelation(str, Enum):
    """Relationship type between TEG nodes."""
    EXPANDS_TO = "EXPANDS_TO"
    RUNS_TO = "RUNS_TO"
    FORKS_FROM = "FORKS_FROM"
    SUPPORTS = "SUPPORTS"
    CONFLICTS = "CONFLICTS"


# =============================================================================
# Node Payload Schemas
# =============================================================================

class VerifiedOutcomePayload(BaseModel):
    """Payload for OUTCOME_VERIFIED nodes."""
    primary_outcome_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Primary outcome probability from run"
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence/reliability score"
    )
    metrics: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metrics from run outcome"
    )
    run_duration_ms: Optional[int] = Field(
        None,
        description="Duration of the run in milliseconds"
    )
    ticks_executed: Optional[int] = Field(
        None,
        description="Number of simulation ticks executed"
    )

    class Config:
        extra = "allow"


class DraftScenarioPayload(BaseModel):
    """Payload for SCENARIO_DRAFT nodes."""
    estimated_delta: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Estimated probability change from baseline"
    )
    scenario_description: Optional[str] = Field(
        None,
        description="Natural language description of the scenario"
    )
    suggested_changes: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="List of suggested parameter/event changes"
    )
    llm_reasoning: Optional[str] = Field(
        None,
        description="LLM reasoning for the estimate"
    )
    temporal_cutoff: Optional[datetime] = Field(
        None,
        description="Temporal cutoff used for this estimate"
    )

    class Config:
        extra = "allow"


class FailedOutcomePayload(BaseModel):
    """Payload for FAILED nodes."""
    error_message: str = Field(..., description="Error message from failed run")
    error_code: Optional[str] = Field(None, description="Error code if available")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    last_stage: Optional[str] = Field(None, description="Last execution stage before failure")

    class Config:
        extra = "allow"


class EvidencePayload(BaseModel):
    """Payload for EVIDENCE nodes."""
    evidence_type: str = Field(..., description="Type of evidence (document, data, etc.)")
    source: Optional[str] = Field(None, description="Source of the evidence")
    relevance: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Relevance score"
    )
    content_summary: Optional[str] = Field(None, description="Summary of evidence content")

    class Config:
        extra = "allow"


# =============================================================================
# Node Links Schema
# =============================================================================

class TEGNodeLinks(BaseModel):
    """Links to existing infrastructure."""
    run_ids: Optional[List[UUID]] = Field(None, description="Associated run IDs")
    node_id: Optional[UUID] = Field(None, description="Link to nodes table")
    run_outcome_id: Optional[UUID] = Field(None, description="Link to run_outcomes table")
    manifest_hash: Optional[str] = Field(None, description="Manifest hash for reproducibility")
    persona_version: Optional[str] = Field(None, description="Persona snapshot version")
    evidence_ids: Optional[List[UUID]] = Field(None, description="Evidence references")

    class Config:
        extra = "allow"


# =============================================================================
# Node Response Schema
# =============================================================================

class TEGNodeResponse(BaseModel):
    """Response schema for a TEG node."""
    node_id: UUID = Field(..., description="Unique node ID")
    type: TEGNodeType = Field(..., description="Node type")
    status: TEGNodeStatus = Field(..., description="Node status")
    title: str = Field(..., description="Display title")
    summary: Optional[str] = Field(None, description="Summary text")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Type-specific payload")
    links: Optional[TEGNodeLinks] = Field(None, description="Links to infrastructure")
    parent_node_id: Optional[UUID] = Field(None, description="Parent node ID")
    position: Optional[Dict[str, float]] = Field(None, description="Graph position {x, y}")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TEGNodeDetail(TEGNodeResponse):
    """Extended node response with additional details for the right panel."""
    # Computed fields for display
    children_count: int = Field(default=0, description="Number of child nodes")
    related_runs_count: int = Field(default=0, description="Number of related runs")

    # Comparison info (populated when baseline available)
    delta_from_baseline: Optional[float] = Field(
        None,
        description="Probability delta from baseline"
    )
    baseline_probability: Optional[float] = Field(
        None,
        description="Baseline probability for comparison"
    )


# =============================================================================
# Edge Response Schema
# =============================================================================

class TEGEdgeResponse(BaseModel):
    """Response schema for a TEG edge."""
    edge_id: UUID = Field(..., description="Unique edge ID")
    from_node_id: UUID = Field(..., description="Source node ID")
    to_node_id: UUID = Field(..., description="Target node ID")
    relation: TEGEdgeRelation = Field(..., description="Relationship type")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Edge metadata")
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Graph Response Schema
# =============================================================================

class TEGGraphResponse(BaseModel):
    """Response schema for GET /projects/{projectId}/teg endpoint."""
    graph_id: UUID = Field(..., description="Graph ID")
    project_id: UUID = Field(..., description="Project ID")
    active_baseline_node_id: Optional[UUID] = Field(
        None,
        description="Currently active baseline node for comparisons"
    )
    nodes: List[TEGNodeResponse] = Field(default_factory=list)
    edges: List[TEGEdgeResponse] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Graph metadata")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Create/Update Request Schemas
# =============================================================================

class CreateTEGNodeRequest(BaseModel):
    """Request schema for creating a new TEG node."""
    type: TEGNodeType = Field(..., description="Node type")
    title: str = Field(..., min_length=1, max_length=255, description="Display title")
    summary: Optional[str] = Field(None, description="Summary text")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Type-specific payload")
    parent_node_id: Optional[UUID] = Field(None, description="Parent node for tree structure")
    position: Optional[Dict[str, float]] = Field(None, description="Graph position {x, y}")


class UpdateTEGNodeRequest(BaseModel):
    """Request schema for updating a TEG node."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    summary: Optional[str] = None
    status: Optional[TEGNodeStatus] = None
    payload: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, float]] = None


class CreateTEGEdgeRequest(BaseModel):
    """Request schema for creating a TEG edge."""
    from_node_id: UUID = Field(..., description="Source node ID")
    to_node_id: UUID = Field(..., description="Target node ID")
    relation: TEGEdgeRelation = Field(..., description="Relationship type")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Edge metadata")


# =============================================================================
# Expand Feature Schemas (Task 4)
# =============================================================================

class ExpandScenarioRequest(BaseModel):
    """Request schema for expanding a node into draft scenarios."""
    source_node_id: UUID = Field(..., description="Node to expand from")
    what_if_prompt: Optional[str] = Field(
        None,
        description="Optional prompt like 'What if prices increase 20%?'"
    )
    num_scenarios: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of draft scenarios to generate"
    )
    include_opposite: bool = Field(
        default=False,
        description="Include an opposite scenario"
    )


class ExpandScenarioResponse(BaseModel):
    """Response schema for expand operation."""
    source_node_id: UUID
    created_nodes: List[TEGNodeResponse]
    created_edges: List[TEGEdgeResponse]
    llm_call_id: Optional[UUID] = Field(
        None,
        description="LLM call ID for audit trail"
    )


# =============================================================================
# Run Scenario Schemas (Task 5)
# =============================================================================

class RunScenarioRequest(BaseModel):
    """Request schema for running a draft scenario."""
    node_id: UUID = Field(..., description="Draft node to execute")
    auto_compare: bool = Field(
        default=True,
        description="Automatically compare with baseline after completion"
    )


class RunScenarioResponse(BaseModel):
    """Response schema for run scenario operation."""
    draft_node_id: UUID = Field(..., description="Original draft node")
    verified_node_id: UUID = Field(..., description="New verified outcome node")
    run_id: UUID = Field(..., description="Simulation run ID")
    task_id: Optional[str] = Field(None, description="Celery task ID")
    edge_id: UUID = Field(..., description="RUNS_TO edge connecting draft to verified")


# =============================================================================
# Compare Schemas (Task 6)
# =============================================================================

class CompareNodesRequest(BaseModel):
    """Request schema for comparing two nodes."""
    node_a_id: UUID = Field(..., description="First node to compare")
    node_b_id: UUID = Field(..., description="Second node to compare")


class CompareNodesResponse(BaseModel):
    """Response schema for node comparison."""
    node_a: TEGNodeResponse
    node_b: TEGNodeResponse
    probability_delta: Optional[float] = Field(
        None,
        description="Difference in primary probability"
    )
    metrics_diff: Optional[Dict[str, Any]] = Field(
        None,
        description="Differences in metrics"
    )
    common_ancestor_id: Optional[UUID] = Field(
        None,
        description="Common ancestor node if any"
    )


# =============================================================================
# Evidence Attach Schemas (Task 7)
# =============================================================================

class EvidenceItem(BaseModel):
    """Single evidence item to attach."""
    url: str = Field(..., description="URL of the evidence source")
    title: Optional[str] = Field(None, description="Title/description of the evidence")


class AttachEvidenceRequest(BaseModel):
    """Request schema for attaching evidence to a node."""
    urls: List[str] = Field(..., min_length=1, description="List of evidence URLs")


class EvidenceComplianceResult(BaseModel):
    """Result of evidence compliance check."""
    evidence_pack_id: UUID = Field(..., description="Created evidence pack ID")
    source_url: str = Field(..., description="Source URL")
    temporal_compliance: str = Field(
        ...,
        description="Compliance status: PASS, WARN, or FAIL"
    )
    snapshot_time: Optional[datetime] = Field(None, description="When evidence was snapshotted")
    hash: Optional[str] = Field(None, description="Content hash for verification")


class AttachEvidenceResponse(BaseModel):
    """Response schema for attach evidence operation."""
    node_id: UUID = Field(..., description="Node the evidence was attached to")
    evidence_results: List[EvidenceComplianceResult] = Field(
        ...,
        description="Compliance results for each evidence URL"
    )
    updated_node: TEGNodeResponse = Field(
        ...,
        description="Updated node with evidence refs"
    )


# =============================================================================
# Sync from Runs (for initial population)
# =============================================================================

class SyncFromRunsResponse(BaseModel):
    """Response for syncing TEG from existing runs."""
    nodes_created: int
    edges_created: int
    baseline_node_id: Optional[UUID] = None
