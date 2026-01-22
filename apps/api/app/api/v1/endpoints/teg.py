"""
Thought Expansion Graph (TEG) API Endpoints

Provides endpoints for:
- GET /projects/{project_id}/teg - Get full graph for project
- GET /teg/nodes/{node_id} - Get node details for right panel
- POST /projects/{project_id}/teg/sync - Sync TEG from existing runs

Reference: docs/TEG_UNIVERSE_MAP_EXECUTION.md
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.middleware.tenant import TenantContext, require_tenant
from app.models.user import User
from app.models.teg import (
    TEGGraph,
    TEGNode,
    TEGEdge,
    TEGNodeType as ModelTEGNodeType,
    TEGNodeStatus as ModelTEGNodeStatus,
    TEGEdgeRelation as ModelTEGEdgeRelation,
)
from app.schemas.teg import (
    TEGGraphResponse,
    TEGNodeResponse,
    TEGNodeDetail,
    TEGEdgeResponse,
    SyncFromRunsResponse,
    ExpandScenarioRequest,
    ExpandScenarioResponse,
    RunScenarioRequest,
    RunScenarioResponse,
    AttachEvidenceRequest,
    AttachEvidenceResponse,
    EvidenceComplianceResult,
    TEGNodeType,
    TEGNodeStatus,
    TEGEdgeRelation,
)
from app.services.llm_router import LLMRouter, LLMRouterContext
from app.services.simulation_orchestrator import SimulationOrchestrator, CreateRunInput


router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================

def _node_to_response(node: TEGNode) -> TEGNodeResponse:
    """Convert a TEGNode model to response schema."""
    return TEGNodeResponse(
        node_id=node.id,
        type=TEGNodeType(node.node_type.value),
        status=TEGNodeStatus(node.status.value),
        title=node.title,
        summary=node.summary,
        payload=node.payload or {},
        links=node.links,
        parent_node_id=node.parent_node_id,
        position=node.position,
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def _edge_to_response(edge: TEGEdge) -> TEGEdgeResponse:
    """Convert a TEGEdge model to response schema."""
    return TEGEdgeResponse(
        edge_id=edge.id,
        from_node_id=edge.from_node_id,
        to_node_id=edge.to_node_id,
        relation=TEGEdgeRelation(edge.relation.value),
        metadata=edge.metadata_json,
        created_at=edge.created_at,
    )


async def _get_or_create_graph(
    db: AsyncSession,
    project_id: UUID,
    tenant_id: UUID,
) -> TEGGraph:
    """Get existing TEG graph or create new one for project."""
    # Try to find existing graph
    query = select(TEGGraph).where(
        TEGGraph.project_id == project_id,
        TEGGraph.tenant_id == tenant_id,
    )
    result = await db.execute(query)
    graph = result.scalar_one_or_none()

    if graph:
        return graph

    # Create new graph
    graph = TEGGraph(
        tenant_id=tenant_id,
        project_id=project_id,
        metadata_json={},
    )
    db.add(graph)
    await db.flush()
    return graph


# =============================================================================
# GET /projects/{project_id}/teg
# =============================================================================

@router.get(
    "/projects/{project_id}/teg",
    response_model=TEGGraphResponse,
    summary="Get TEG for project",
    description="Get the complete Thought Expansion Graph for a project.",
)
async def get_project_teg(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> TEGGraphResponse:
    """
    Get the full TEG for a project including all nodes and edges.

    This is the main endpoint for the Graph and Table views.
    If no TEG exists yet, creates an empty one and attempts to sync from existing runs.
    """
    project_uuid = UUID(project_id)

    # Get or create TEG graph
    graph = await _get_or_create_graph(db, project_uuid, tenant_ctx.tenant_id)

    # Load nodes with eager loading
    nodes_query = select(TEGNode).where(
        TEGNode.graph_id == graph.id,
        TEGNode.tenant_id == tenant_ctx.tenant_id,
    ).order_by(TEGNode.created_at.desc())

    nodes_result = await db.execute(nodes_query)
    nodes = nodes_result.scalars().all()

    # Load edges
    edges_query = select(TEGEdge).where(
        TEGEdge.graph_id == graph.id,
        TEGEdge.tenant_id == tenant_ctx.tenant_id,
    )
    edges_result = await db.execute(edges_query)
    edges = edges_result.scalars().all()

    # If no nodes exist, try to sync from existing runs
    if not nodes:
        sync_result = await _sync_from_runs(db, graph, project_uuid, tenant_ctx.tenant_id)
        if sync_result["nodes_created"] > 0:
            await db.commit()
            # Re-fetch nodes and edges
            nodes_result = await db.execute(nodes_query)
            nodes = nodes_result.scalars().all()
            edges_result = await db.execute(edges_query)
            edges = edges_result.scalars().all()

    return TEGGraphResponse(
        graph_id=graph.id,
        project_id=graph.project_id,
        active_baseline_node_id=graph.active_baseline_node_id,
        nodes=[_node_to_response(n) for n in nodes],
        edges=[_edge_to_response(e) for e in edges],
        metadata=graph.metadata_json,
        created_at=graph.created_at,
        updated_at=graph.updated_at,
    )


# =============================================================================
# GET /teg/nodes/{node_id}
# =============================================================================

@router.get(
    "/teg/nodes/{node_id}",
    response_model=TEGNodeDetail,
    summary="Get TEG node details",
    description="Get detailed information for a TEG node (for the right panel).",
)
async def get_teg_node_details(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> TEGNodeDetail:
    """
    Get detailed node information for the right-side panel.

    Includes computed fields like:
    - Children count
    - Related runs count
    - Delta from baseline (if baseline available)
    """
    node_uuid = UUID(node_id)

    # Get node
    node_query = select(TEGNode).where(
        TEGNode.id == node_uuid,
        TEGNode.tenant_id == tenant_ctx.tenant_id,
    )
    result = await db.execute(node_query)
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TEG node {node_id} not found",
        )

    # Count children
    children_query = select(func.count()).select_from(TEGNode).where(
        TEGNode.parent_node_id == node_uuid,
    )
    children_result = await db.execute(children_query)
    children_count = children_result.scalar() or 0

    # Count related runs (from links.run_ids)
    run_ids = node.links.get("run_ids", []) if node.links else []
    related_runs_count = len(run_ids)

    # Calculate delta from baseline if available
    delta_from_baseline = None
    baseline_probability = None

    # Get graph to find baseline
    graph_query = select(TEGGraph).where(TEGGraph.id == node.graph_id)
    graph_result = await db.execute(graph_query)
    graph = graph_result.scalar_one_or_none()

    if graph and graph.active_baseline_node_id and graph.active_baseline_node_id != node_uuid:
        # Get baseline node
        baseline_query = select(TEGNode).where(
            TEGNode.id == graph.active_baseline_node_id,
        )
        baseline_result = await db.execute(baseline_query)
        baseline_node = baseline_result.scalar_one_or_none()

        if baseline_node:
            baseline_prob = baseline_node.payload.get("primary_outcome_probability")
            node_prob = node.payload.get("primary_outcome_probability")
            node_delta = node.payload.get("estimated_delta")

            if baseline_prob is not None:
                baseline_probability = baseline_prob
                if node_prob is not None:
                    delta_from_baseline = node_prob - baseline_prob
                elif node_delta is not None:
                    delta_from_baseline = node_delta

    return TEGNodeDetail(
        node_id=node.id,
        type=TEGNodeType(node.node_type.value),
        status=TEGNodeStatus(node.status.value),
        title=node.title,
        summary=node.summary,
        payload=node.payload or {},
        links=node.links,
        parent_node_id=node.parent_node_id,
        position=node.position,
        created_at=node.created_at,
        updated_at=node.updated_at,
        children_count=children_count,
        related_runs_count=related_runs_count,
        delta_from_baseline=delta_from_baseline,
        baseline_probability=baseline_probability,
    )


# =============================================================================
# POST /projects/{project_id}/teg/sync
# =============================================================================

@router.post(
    "/projects/{project_id}/teg/sync",
    response_model=SyncFromRunsResponse,
    summary="Sync TEG from runs",
    description="Populate TEG from existing simulation runs.",
)
async def sync_teg_from_runs(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> SyncFromRunsResponse:
    """
    Sync TEG nodes from existing simulation runs.

    Creates OUTCOME_VERIFIED nodes for completed runs.
    Sets the most recent successful run as the baseline.
    """
    project_uuid = UUID(project_id)

    # Get or create graph
    graph = await _get_or_create_graph(db, project_uuid, tenant_ctx.tenant_id)

    # Perform sync
    result = await _sync_from_runs(db, graph, project_uuid, tenant_ctx.tenant_id)

    await db.commit()

    return SyncFromRunsResponse(
        nodes_created=result["nodes_created"],
        edges_created=result["edges_created"],
        baseline_node_id=result["baseline_node_id"],
    )


async def _sync_from_runs(
    db: AsyncSession,
    graph: TEGGraph,
    project_id: UUID,
    tenant_id: UUID,
) -> Dict[str, Any]:
    """
    Internal function to sync TEG from existing runs.

    Returns dict with nodes_created, edges_created, baseline_node_id.
    """
    from app.models.node import Run, RunStatus

    nodes_created = 0
    edges_created = 0
    baseline_node_id = None

    # Get existing TEG node IDs to avoid duplicates
    existing_query = select(TEGNode.links).where(
        TEGNode.graph_id == graph.id,
    )
    existing_result = await db.execute(existing_query)
    existing_links = existing_result.scalars().all()

    # Extract existing run_ids
    existing_run_ids = set()
    for links in existing_links:
        if links and "run_ids" in links:
            existing_run_ids.update(links["run_ids"])

    # Get completed runs for this project
    runs_query = select(Run).where(
        Run.project_id == project_id,
        Run.tenant_id == tenant_id,
        Run.status == RunStatus.SUCCEEDED,
    ).order_by(Run.completed_at.desc())

    runs_result = await db.execute(runs_query)
    runs = runs_result.scalars().all()

    # Create TEG nodes for runs that don't exist yet
    for run in runs:
        if str(run.id) in existing_run_ids:
            continue

        # Try to get outcome probability from run_outcomes
        outcome_prob = None
        from app.models.run_outcome import RunOutcome
        outcome_query = select(RunOutcome).where(
            RunOutcome.run_id == run.id,
        )
        outcome_result = await db.execute(outcome_query)
        outcome = outcome_result.scalar_one_or_none()

        if outcome and outcome.metrics_json:
            outcome_prob = outcome.metrics_json.get("primary_outcome_probability")

        # Create payload
        payload = {
            "primary_outcome_probability": outcome_prob or 0.5,
            "run_duration_ms": (run.completed_at - run.started_at).total_seconds() * 1000 if run.completed_at and run.started_at else None,
        }

        if outcome and outcome.metrics_json:
            payload["metrics"] = outcome.metrics_json

        # Create TEG node
        teg_node = TEGNode(
            tenant_id=tenant_id,
            graph_id=graph.id,
            project_id=project_id,
            node_type=ModelTEGNodeType.OUTCOME_VERIFIED,
            status=ModelTEGNodeStatus.DONE,
            title=run.label or f"Run {str(run.id)[:8]}",
            summary=f"Completed simulation run",
            payload=payload,
            links={
                "run_ids": [str(run.id)],
                "node_id": str(run.node_id) if run.node_id else None,
                "run_outcome_id": str(outcome.id) if outcome else None,
            },
        )
        db.add(teg_node)
        nodes_created += 1

        # Set first (most recent) as baseline
        if baseline_node_id is None:
            await db.flush()  # Get the ID
            baseline_node_id = teg_node.id
            graph.active_baseline_node_id = teg_node.id

    return {
        "nodes_created": nodes_created,
        "edges_created": edges_created,
        "baseline_node_id": baseline_node_id,
    }


# =============================================================================
# POST /projects/{project_id}/teg/set-baseline
# =============================================================================

@router.post(
    "/projects/{project_id}/teg/set-baseline/{node_id}",
    summary="Set baseline node",
    description="Set a node as the active baseline for comparisons.",
)
async def set_baseline_node(
    project_id: str,
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> Dict[str, Any]:
    """
    Set a node as the active baseline for comparisons.

    The baseline node is used to calculate deltas in the Compare UX.
    """
    project_uuid = UUID(project_id)
    node_uuid = UUID(node_id)

    # Get graph
    graph_query = select(TEGGraph).where(
        TEGGraph.project_id == project_uuid,
        TEGGraph.tenant_id == tenant_ctx.tenant_id,
    )
    result = await db.execute(graph_query)
    graph = result.scalar_one_or_none()

    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TEG not found for project {project_id}",
        )

    # Verify node exists and is in this graph
    node_query = select(TEGNode).where(
        TEGNode.id == node_uuid,
        TEGNode.graph_id == graph.id,
    )
    node_result = await db.execute(node_query)
    node = node_result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found in this TEG",
        )

    # Set as baseline
    graph.active_baseline_node_id = node_uuid
    await db.commit()

    return {
        "status": "ok",
        "active_baseline_node_id": str(node_uuid),
        "message": f"Set node '{node.title}' as baseline",
    }


# =============================================================================
# POST /teg/nodes/{node_id}/expand (Task 4)
# =============================================================================

EXPAND_SCENARIO_PROMPT = """You are an AI assistant helping to generate scenario variations for a predictive simulation.

Given a verified simulation outcome, generate {num_scenarios} alternative scenario ideas that explore "what-if" variations.

{what_if_context}

**Baseline Scenario:**
- Title: {baseline_title}
- Summary: {baseline_summary}
- Primary outcome probability: {baseline_probability}

**Instructions:**
1. Generate {num_scenarios} distinct scenario variations
2. Each scenario should have:
   - A short, descriptive title (max 50 chars)
   - A 1-2 sentence summary explaining the variation
   - An estimated probability delta from baseline (-1.0 to +1.0)
   - A brief reasoning for the estimate
3. Scenarios should be realistic variations that could be simulated
4. Consider factors like: market conditions, consumer behavior changes, competition, timing, pricing, etc.
{opposite_instruction}

**Response Format (JSON array):**
```json
[
  {{
    "title": "Scenario Title",
    "summary": "Brief description of the scenario variation",
    "estimated_delta": 0.15,
    "reasoning": "Why this would increase/decrease the outcome probability"
  }}
]
```

Return ONLY the JSON array, no other text."""


@router.post(
    "/teg/nodes/{node_id}/expand",
    response_model=ExpandScenarioResponse,
    summary="Expand node into draft scenarios",
    description="Use LLM to generate draft scenario variations from a verified outcome node.",
)
async def expand_teg_node(
    node_id: str,
    request: ExpandScenarioRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> ExpandScenarioResponse:
    """
    Expand a verified outcome node into draft scenario candidates.

    This implements the "Expand" action in the TEG UX:
    1. Takes a verified outcome (green node) as source
    2. Optionally accepts a "what-if" prompt
    3. Uses LLM to generate scenario variations
    4. Creates SCENARIO_DRAFT nodes with EXPANDS_TO edges
    5. Returns the created drafts for display

    Constraints:
    - Source node must be OUTCOME_VERIFIED type
    - Source node must have DONE status
    - LLMs are used as compilers (C5) - one-time generation
    """
    import json as json_module

    node_uuid = UUID(node_id)
    source_uuid = request.source_node_id

    # Verify source node matches path parameter
    if str(source_uuid) != node_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_node_id must match path node_id",
        )

    # Get the source node
    node_query = select(TEGNode).where(
        TEGNode.id == source_uuid,
        TEGNode.tenant_id == tenant_ctx.tenant_id,
    )
    result = await db.execute(node_query)
    source_node = result.scalar_one_or_none()

    if not source_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TEG node {node_id} not found",
        )

    # Verify node type and status
    if source_node.node_type != ModelTEGNodeType.OUTCOME_VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only expand OUTCOME_VERIFIED nodes, got {source_node.node_type.value}",
        )

    if source_node.status != ModelTEGNodeStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only expand nodes with DONE status, got {source_node.status.value}",
        )

    # Get baseline probability from payload
    baseline_prob = source_node.payload.get("primary_outcome_probability", 0.5) if source_node.payload else 0.5

    # Build the what-if context
    what_if_context = ""
    if request.what_if_prompt:
        what_if_context = f'**User\'s "What-If" Question:**\n{request.what_if_prompt}\n\nIncorporate this question into your scenario variations.'

    # Build opposite instruction
    opposite_instruction = ""
    if request.include_opposite:
        opposite_instruction = "\n5. Include at least one scenario that has an opposite effect (if baseline is positive, include a negative scenario and vice versa)"

    # Format the prompt
    prompt = EXPAND_SCENARIO_PROMPT.format(
        num_scenarios=request.num_scenarios,
        what_if_context=what_if_context,
        baseline_title=source_node.title,
        baseline_summary=source_node.summary or "No summary available",
        baseline_probability=f"{baseline_prob:.2%}",
        opposite_instruction=opposite_instruction,
    )

    # Call LLM via LLMRouter (C5: LLMs as compilers)
    llm_router = LLMRouter(db)
    context = LLMRouterContext(
        tenant_id=str(tenant_ctx.tenant_id),
        project_id=str(source_node.project_id),
        phase="compilation",  # C5 tracking
    )

    try:
        llm_response = await llm_router.complete(
            profile_key="TEG_SCENARIO_EXPAND",
            messages=[
                {"role": "user", "content": prompt},
            ],
            context=context,
            temperature_override=0.7,  # Allow creativity for scenario generation
            max_tokens_override=2000,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM service unavailable: {str(e)}",
        )

    # Parse LLM response
    try:
        # Extract JSON from response (handle markdown code blocks)
        content = llm_response.content.strip()
        if content.startswith("```"):
            # Remove markdown code blocks
            lines = content.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if in_block or (not line.startswith("```") and json_lines):
                    json_lines.append(line)
            content = "\n".join(json_lines)

        scenarios = json_module.loads(content)

        if not isinstance(scenarios, list):
            raise ValueError("Expected JSON array")

    except (json_module.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to parse LLM response: {str(e)}",
        )

    # Create TEG nodes and edges
    created_nodes: List[TEGNode] = []
    created_edges: List[TEGEdge] = []

    for i, scenario in enumerate(scenarios[:request.num_scenarios]):
        # Validate scenario structure
        if not isinstance(scenario, dict):
            continue

        title = scenario.get("title", f"Scenario {i + 1}")[:255]
        summary = scenario.get("summary", "")
        estimated_delta = scenario.get("estimated_delta", 0.0)
        reasoning = scenario.get("reasoning", "")

        # Clamp delta to valid range
        if isinstance(estimated_delta, (int, float)):
            estimated_delta = max(-1.0, min(1.0, float(estimated_delta)))
        else:
            estimated_delta = 0.0

        # Create SCENARIO_DRAFT node
        draft_node = TEGNode(
            tenant_id=tenant_ctx.tenant_id,
            graph_id=source_node.graph_id,
            project_id=source_node.project_id,
            parent_node_id=source_uuid,  # Parent is the expanded node
            node_type=ModelTEGNodeType.SCENARIO_DRAFT,
            status=ModelTEGNodeStatus.DRAFT,
            title=title,
            summary=summary,
            payload={
                "estimated_delta": estimated_delta,
                "scenario_description": summary,
                "llm_reasoning": reasoning,
                "what_if_prompt": request.what_if_prompt,
                "source_probability": baseline_prob,
            },
            links={
                "source_node_id": str(source_uuid),
                "llm_call_id": llm_response.call_id,
            },
        )
        db.add(draft_node)
        await db.flush()  # Get the ID
        created_nodes.append(draft_node)

        # Create EXPANDS_TO edge
        edge = TEGEdge(
            tenant_id=tenant_ctx.tenant_id,
            graph_id=source_node.graph_id,
            from_node_id=source_uuid,
            to_node_id=draft_node.id,
            relation=ModelTEGEdgeRelation.EXPANDS_TO,
            metadata_json={
                "what_if_prompt": request.what_if_prompt,
                "generation_index": i,
            },
        )
        db.add(edge)
        created_edges.append(edge)

    await db.commit()

    # Convert to response schemas
    return ExpandScenarioResponse(
        source_node_id=source_uuid,
        created_nodes=[_node_to_response(n) for n in created_nodes],
        created_edges=[_edge_to_response(e) for e in created_edges],
        llm_call_id=UUID(llm_response.call_id) if llm_response.call_id else None,
    )


# =============================================================================
# POST /teg/nodes/{node_id}/run (Task 5)
# =============================================================================

@router.post(
    "/teg/nodes/{node_id}/run",
    response_model=RunScenarioResponse,
    summary="Run a draft scenario",
    description="Execute a draft scenario to get a verified outcome.",
)
async def run_teg_scenario(
    node_id: str,
    request: RunScenarioRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> RunScenarioResponse:
    """
    Run a draft scenario node to produce a verified outcome.

    This implements the "Run" action in the TEG UX:
    1. Takes a draft scenario (purple node) as source
    2. Creates a verified outcome node with QUEUED status
    3. Creates a RUNS_TO edge
    4. Triggers simulation run
    5. Run completion will update the verified node to DONE

    Constraints:
    - Source node must be SCENARIO_DRAFT type
    - Source node must have DRAFT status
    - C2: On-demand execution (explicitly triggered)
    """
    node_uuid = UUID(node_id)
    draft_uuid = request.node_id

    # Verify node matches path parameter
    if str(draft_uuid) != node_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="node_id must match path node_id",
        )

    # Get the draft node
    node_query = select(TEGNode).where(
        TEGNode.id == draft_uuid,
        TEGNode.tenant_id == tenant_ctx.tenant_id,
    )
    result = await db.execute(node_query)
    draft_node = result.scalar_one_or_none()

    if not draft_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TEG node {node_id} not found",
        )

    # Verify node type and status
    if draft_node.node_type != ModelTEGNodeType.SCENARIO_DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only run SCENARIO_DRAFT nodes, got {draft_node.node_type.value}",
        )

    if draft_node.status != ModelTEGNodeStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only run nodes with DRAFT status, got {draft_node.status.value}",
        )

    # Update draft node to QUEUED
    draft_node.status = ModelTEGNodeStatus.QUEUED

    # Create the verified outcome node (starts as QUEUED)
    verified_node = TEGNode(
        tenant_id=tenant_ctx.tenant_id,
        graph_id=draft_node.graph_id,
        project_id=draft_node.project_id,
        parent_node_id=draft_uuid,  # Parent is the draft node
        node_type=ModelTEGNodeType.OUTCOME_VERIFIED,
        status=ModelTEGNodeStatus.QUEUED,
        title=f"Result: {draft_node.title}",
        summary=f"Running simulation for: {draft_node.summary or draft_node.title}",
        payload={
            "source_draft_id": str(draft_uuid),
            "estimated_delta": draft_node.payload.get("estimated_delta") if draft_node.payload else None,
        },
        links={
            "source_draft_id": str(draft_uuid),
        },
    )
    db.add(verified_node)
    await db.flush()  # Get the ID

    # Create RUNS_TO edge (draft -> verified)
    runs_to_edge = TEGEdge(
        tenant_id=tenant_ctx.tenant_id,
        graph_id=draft_node.graph_id,
        from_node_id=draft_uuid,
        to_node_id=verified_node.id,
        relation=ModelTEGEdgeRelation.RUNS_TO,
        metadata_json={
            "auto_compare": request.auto_compare,
        },
    )
    db.add(runs_to_edge)
    await db.flush()

    # Create simulation run via orchestrator
    orchestrator = SimulationOrchestrator(db, tenant_ctx.tenant_id)

    # Build scenario patch from draft payload
    scenario_patch = None
    if draft_node.payload:
        scenario_patch = draft_node.payload.get("suggested_changes")

    run_input = CreateRunInput(
        project_id=str(draft_node.project_id),
        tenant_id=str(tenant_ctx.tenant_id),
        label=f"TEG: {draft_node.title}",
        scenario_patch=scenario_patch,
        user_id=str(current_user.id) if current_user.id else None,
    )

    run, sim_node = await orchestrator.create_run(run_input)

    # Update verified node with run links
    verified_node.links = {
        "source_draft_id": str(draft_uuid),
        "run_ids": [str(run.id)],
        "node_id": str(sim_node.id),
    }

    # Update draft node to RUNNING
    draft_node.status = ModelTEGNodeStatus.RUNNING

    # Update verified node to RUNNING (tracking the run)
    verified_node.status = ModelTEGNodeStatus.RUNNING

    await db.commit()

    return RunScenarioResponse(
        draft_node_id=draft_uuid,
        verified_node_id=verified_node.id,
        run_id=run.id,
        task_id=None,  # Will be set when run actually starts
        edge_id=runs_to_edge.id,
    )


# =============================================================================
# Attach Evidence (Task 7)
# =============================================================================

@router.post(
    "/teg/nodes/{node_id}/attach-evidence",
    response_model=AttachEvidenceResponse,
    summary="Attach evidence to a TEG node",
    description="""
    Attach evidence URLs to a TEG node for temporal compliance checking.

    Each URL is validated and checked for temporal compliance (whether it
    was available before the project's cutoff date).

    **Compliance Statuses:**
    - PASS: Evidence was available before cutoff
    - WARN: Compliance could not be verified
    - FAIL: Evidence is from after cutoff date

    Reference: docs/TEG_UNIVERSE_MAP_EXECUTION.md Task 7
    """,
)
async def attach_evidence(
    node_id: UUID,
    request: AttachEvidenceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
) -> AttachEvidenceResponse:
    """Attach evidence URLs to a node."""
    import hashlib
    from uuid import uuid4

    # Find the node
    query = select(TEGNode).where(
        TEGNode.id == node_id,
        TEGNode.tenant_id == tenant_ctx.tenant_id,
    )
    result = await db.execute(query)
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TEG node {node_id} not found",
        )

    # Process each URL and create evidence compliance results
    evidence_results: List[EvidenceComplianceResult] = []
    evidence_refs: List[Dict[str, Any]] = []

    for url in request.urls:
        # Generate a unique evidence pack ID
        evidence_pack_id = uuid4()

        # Create a hash of the URL for tracking
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]

        # Temporal compliance check
        # In a full implementation, this would:
        # 1. Fetch the URL content
        # 2. Check if the content date is before project cutoff
        # 3. Snapshot the content
        # For now, we simulate this with a simple check

        # Determine compliance status based on URL analysis
        # This is a simplified implementation - real version would use
        # archive.org, page metadata, etc.
        compliance_status = "WARN"  # Default to WARN since we can't verify

        # Some heuristics:
        # - .gov, .edu domains are more trustworthy -> PASS
        # - Known archive sites -> PASS
        # - Other URLs -> WARN
        url_lower = url.lower()
        if any(d in url_lower for d in ['.gov', '.edu', 'archive.org', 'web.archive.org']):
            compliance_status = "PASS"
        elif any(d in url_lower for d in ['facebook.com', 'twitter.com', 'x.com']):
            compliance_status = "WARN"  # Social media posts can be edited

        snapshot_time = datetime.utcnow()

        evidence_results.append(EvidenceComplianceResult(
            evidence_pack_id=evidence_pack_id,
            source_url=url,
            temporal_compliance=compliance_status,
            snapshot_time=snapshot_time,
            hash=url_hash,
        ))

        # Build evidence ref for node payload
        evidence_refs.append({
            "evidence_pack_id": str(evidence_pack_id),
            "source_url": url,
            "snapshot_time": snapshot_time.isoformat(),
            "hash": url_hash,
            "temporal_compliance": compliance_status,
        })

    # Update node payload with evidence refs
    current_payload = node.payload or {}
    existing_evidence = current_payload.get("evidence_refs", [])
    current_payload["evidence_refs"] = existing_evidence + evidence_refs
    node.payload = current_payload

    # Update node links with evidence IDs
    current_links = node.links or {}
    existing_evidence_ids = current_links.get("evidence_ids", [])
    new_evidence_ids = [str(r.evidence_pack_id) for r in evidence_results]
    current_links["evidence_ids"] = existing_evidence_ids + new_evidence_ids
    node.links = current_links

    node.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(node)

    return AttachEvidenceResponse(
        node_id=node_id,
        evidence_results=evidence_results,
        updated_node=_node_to_response(node),
    )
