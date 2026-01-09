"""
Ask API Endpoints
Reference: project.md §11 Phase 4, Interaction_design.md §5.9

The "Ask" feature allows users to input natural language "What if..." questions
and receive branching scenarios in the Universe Map.

Endpoints:
- POST /ask/compile - Compile a prompt into event scripts
- POST /ask/expand - Expand a scenario cluster progressively
- GET /ask/compilations - List recent compilations
- GET /ask/compilations/{id} - Get compilation details
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_tenant, TenantContext
from app.models.user import User
from app.services.event_compiler import (
    EventCompiler,
    CompilationResult,
    IntentType,
    PromptScope,
    ScenarioCluster,
    get_event_compiler,
)

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class AskCompileRequest(BaseModel):
    """Request to compile a "What if..." prompt."""
    prompt: str = Field(..., min_length=10, max_length=2000, description="The natural language question")
    project_id: UUID = Field(..., description="Project to compile for")
    max_scenarios: int = Field(default=10, ge=1, le=50, description="Maximum scenarios to generate")
    clustering_enabled: bool = Field(default=True, description="Whether to cluster scenarios")
    model_tier: str = Field(default="quality", description="LLM tier: fast, balanced, quality, premium")
    persist: bool = Field(default=True, description="Whether to persist events to database")

    # Optional context overrides
    regions: Optional[List[str]] = Field(default=None, description="Available regions")
    segments: Optional[List[str]] = Field(default=None, description="Available persona segments")
    variable_catalog: Optional[Dict[str, Any]] = Field(default=None, description="Custom variable catalog")


class IntentResponse(BaseModel):
    """Extracted intent from the prompt."""
    intent_type: str
    confidence: float
    normalized_prompt: str
    scope: str
    affected_regions: List[str]
    affected_segments: List[str]
    time_window: Optional[Dict[str, int]]
    key_entities: List[str]
    domain_hints: List[str]


class SubEffectResponse(BaseModel):
    """A decomposed sub-effect."""
    effect_id: str
    description: str
    target_type: str
    target_variable: Optional[str]
    operation: str
    magnitude: Optional[float]
    confidence: float
    dependencies: List[str]
    rationale: str


class VariableMappingResponse(BaseModel):
    """Mapping from sub-effect to variable."""
    sub_effect_id: str
    variable_name: str
    variable_type: str
    operation: str
    value: Any
    uncertainty: float
    mapping_rationale: str


class EventScriptSummary(BaseModel):
    """Summary of a generated event script."""
    event_type: str
    label: str
    scope: Dict[str, Any]
    affected_variables: List[str]


class CandidateScenarioResponse(BaseModel):
    """A candidate scenario."""
    scenario_id: str
    label: str
    description: str
    probability: float
    intervention_magnitude: float
    event_count: int
    affected_variables: List[str]
    cluster_id: Optional[str]


class ScenarioClusterResponse(BaseModel):
    """A cluster of scenarios."""
    cluster_id: str
    label: str
    representative_scenario_id: str
    member_count: int
    aggregate_probability: float
    expandable: bool
    depth: int


class ExplanationResponse(BaseModel):
    """Causal explanation."""
    explanation_id: str
    summary: str
    causal_chain: List[Dict[str, str]]
    key_drivers: List[Dict[str, Any]]
    uncertainty_notes: List[str]
    assumptions: List[str]
    confidence_level: str
    event_script_refs: List[str]


class AskCompileResponse(BaseModel):
    """Response from compiling a prompt."""
    compilation_id: str
    original_prompt: str
    intent: IntentResponse
    sub_effects: List[SubEffectResponse]
    variable_mappings: List[VariableMappingResponse]
    candidate_scenarios: List[CandidateScenarioResponse]
    clusters: List[ScenarioClusterResponse]
    explanation: ExplanationResponse
    compiler_version: str
    compiled_at: datetime
    total_cost_usd: float
    compilation_time_ms: int
    warnings: List[str]

    # Persisted artifacts
    created_event_ids: List[str] = []
    created_bundle_id: Optional[str] = None


class ExpandClusterRequest(BaseModel):
    """Request to expand a scenario cluster."""
    cluster_id: str = Field(..., description="Cluster ID to expand")
    project_id: UUID = Field(..., description="Project ID")
    max_children: int = Field(default=5, ge=1, le=20, description="Max child scenarios")


class ExpandClusterResponse(BaseModel):
    """Response from expanding a cluster."""
    cluster_id: str
    expanded_scenarios: List[CandidateScenarioResponse]
    new_clusters: List[ScenarioClusterResponse]
    expansion_depth: int


class CompilationListItem(BaseModel):
    """Summary item for compilation listing."""
    compilation_id: str
    original_prompt: str
    intent_type: str
    scenario_count: int
    cluster_count: int
    compiled_at: datetime


# =============================================================================
# In-memory compilation cache (for expansion)
# In production, this would use Redis or database persistence
# =============================================================================

_compilation_cache: Dict[str, CompilationResult] = {}
_MAX_CACHE_SIZE = 100


def _cache_compilation(result: CompilationResult):
    """Cache a compilation result for later expansion."""
    global _compilation_cache
    if len(_compilation_cache) >= _MAX_CACHE_SIZE:
        # Remove oldest entries
        oldest = sorted(_compilation_cache.keys())[:10]
        for key in oldest:
            del _compilation_cache[key]
    _compilation_cache[result.compilation_id] = result


def _get_cached_compilation(compilation_id: str) -> Optional[CompilationResult]:
    """Get a cached compilation result."""
    return _compilation_cache.get(compilation_id)


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/compile", response_model=AskCompileResponse, status_code=status.HTTP_200_OK)
async def compile_prompt(
    request: AskCompileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(require_tenant),
):
    """
    Compile a natural language "What if..." prompt into event scripts.

    This is the main entry point for the Ask feature. It:
    1. Analyzes the intent and scope of the prompt
    2. Decomposes it into sub-effects
    3. Maps to simulation variables
    4. Generates candidate scenarios
    5. Clusters similar scenarios
    6. Generates causal explanation

    The result can be used to create branches in the Universe Map.
    """
    # Build project context
    # In production, fetch from database based on project_id
    project_context = {
        "project_id": str(request.project_id),
        "domain": "general",  # Would fetch from project
        "regions": request.regions or ["global"],
        "segments": request.segments or [],
        "variable_catalog": request.variable_catalog,
    }

    # Get compiler
    compiler = EventCompiler(db=db)

    # Compile the prompt
    try:
        result = await compiler.compile(
            prompt=request.prompt,
            project_context=project_context,
            db=db,
            tenant_id=tenant_ctx.tenant_id,
            max_scenarios=request.max_scenarios,
            clustering_enabled=request.clustering_enabled,
        )
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Ask Compile Error: {str(e)}\nTraceback:\n{error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compilation failed: {str(e)}"
        )

    # Persist if requested
    created_event_ids = []
    created_bundle_id = None

    if request.persist and result.candidate_scenarios:
        try:
            events, bundle = await compiler.persist_compilation(
                result=result,
                db=db,
                tenant_id=tenant_ctx.tenant_id,
                project_id=request.project_id,
            )
            created_event_ids = [str(e.id) for e in events]
            if bundle:
                created_bundle_id = str(bundle.id)
        except Exception as e:
            # Log but don't fail - compilation succeeded
            result.warnings.append(f"Persistence failed: {str(e)}")

    # Cache for later expansion
    _cache_compilation(result)

    # Convert to response
    return AskCompileResponse(
        compilation_id=result.compilation_id,
        original_prompt=result.original_prompt,
        intent=IntentResponse(
            intent_type=result.intent.intent_type.value,
            confidence=result.intent.confidence,
            normalized_prompt=result.intent.normalized_prompt,
            scope=result.intent.scope.value,
            affected_regions=result.intent.affected_regions,
            affected_segments=result.intent.affected_segments,
            time_window=result.intent.time_window,
            key_entities=result.intent.key_entities,
            domain_hints=result.intent.domain_hints,
        ),
        sub_effects=[
            SubEffectResponse(
                effect_id=e.effect_id,
                description=e.description,
                target_type=e.target_type,
                target_variable=e.target_variable,
                operation=e.operation.value,
                magnitude=e.magnitude,
                confidence=e.confidence,
                dependencies=e.dependencies,
                rationale=e.rationale,
            )
            for e in result.sub_effects
        ],
        variable_mappings=[
            VariableMappingResponse(
                sub_effect_id=m.sub_effect_id,
                variable_name=m.variable_name,
                variable_type=m.variable_type,
                operation=m.operation.value,
                value=m.value,
                uncertainty=m.uncertainty,
                mapping_rationale=m.mapping_rationale,
            )
            for m in result.variable_mappings
        ],
        candidate_scenarios=[
            CandidateScenarioResponse(
                scenario_id=s.scenario_id,
                label=s.label,
                description=s.description,
                probability=s.probability,
                intervention_magnitude=s.intervention_magnitude,
                event_count=len(s.event_scripts),
                affected_variables=s.affected_variables,
                cluster_id=s.cluster_id,
            )
            for s in result.candidate_scenarios
        ],
        clusters=[
            ScenarioClusterResponse(
                cluster_id=c.cluster_id,
                label=c.label,
                representative_scenario_id=c.representative_scenario.scenario_id,
                member_count=len(c.member_scenario_ids),
                aggregate_probability=c.aggregate_probability,
                expandable=c.expandable,
                depth=c.depth,
            )
            for c in result.clusters
        ],
        explanation=ExplanationResponse(
            explanation_id=result.explanation.explanation_id,
            summary=result.explanation.summary,
            causal_chain=result.explanation.causal_chain,
            key_drivers=result.explanation.key_drivers,
            uncertainty_notes=result.explanation.uncertainty_notes,
            assumptions=result.explanation.assumptions,
            confidence_level=result.explanation.confidence_level,
            event_script_refs=result.explanation.event_script_refs,
        ),
        compiler_version=result.compiler_version,
        compiled_at=result.compiled_at,
        total_cost_usd=result.total_cost_usd,
        compilation_time_ms=result.compilation_time_ms,
        warnings=result.warnings,
        created_event_ids=created_event_ids,
        created_bundle_id=created_bundle_id,
    )


@router.post("/expand", response_model=ExpandClusterResponse, status_code=status.HTTP_200_OK)
async def expand_cluster(
    request: ExpandClusterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Expand a scenario cluster to show more detailed variations.

    This implements progressive expansion per project.md Phase 4:
    - Clusters can be expanded to reveal child scenarios
    - Each expansion shows more granular variations
    - No hard cap on depth, but practical limits apply
    """
    # Find the compilation containing this cluster
    compilation = None
    cluster = None

    for cached_result in _compilation_cache.values():
        for c in cached_result.clusters:
            if c.cluster_id == request.cluster_id:
                compilation = cached_result
                cluster = c
                break
        if cluster:
            break

    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster {request.cluster_id} not found"
        )

    if not cluster.expandable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cluster is not expandable (single scenario)"
        )

    # Get the scenarios in this cluster
    cluster_scenarios = [
        s for s in compilation.candidate_scenarios
        if s.cluster_id == request.cluster_id
    ]

    # Generate child scenarios by varying parameters
    # In production, this would use the compiler to generate more variations
    expanded_scenarios = []
    new_clusters = []

    for i, scenario in enumerate(cluster_scenarios[:request.max_children]):
        # Create variations by adjusting probability/magnitude
        for variant in ["low", "high"]:
            new_scenario_id = f"{scenario.scenario_id}_{variant}_{i}"
            prob_adjust = 0.8 if variant == "low" else 1.2
            mag_adjust = 0.7 if variant == "low" else 1.3

            expanded_scenarios.append(CandidateScenarioResponse(
                scenario_id=new_scenario_id,
                label=f"{scenario.label} ({variant.title()} Impact)",
                description=f"Variation of {scenario.label} with {variant} impact",
                probability=min(1.0, scenario.probability * prob_adjust),
                intervention_magnitude=min(1.0, scenario.intervention_magnitude * mag_adjust),
                event_count=len(scenario.event_scripts),
                affected_variables=scenario.affected_variables,
                cluster_id=f"{request.cluster_id}_expanded",
            ))

    # Create new cluster for expanded scenarios
    if expanded_scenarios:
        new_clusters.append(ScenarioClusterResponse(
            cluster_id=f"{request.cluster_id}_expanded",
            label=f"Expanded: {cluster.label}",
            representative_scenario_id=expanded_scenarios[0].scenario_id,
            member_count=len(expanded_scenarios),
            aggregate_probability=sum(s.probability for s in expanded_scenarios) / len(expanded_scenarios),
            expandable=len(expanded_scenarios) > 2,
            depth=cluster.depth + 1,
        ))

    return ExpandClusterResponse(
        cluster_id=request.cluster_id,
        expanded_scenarios=expanded_scenarios,
        new_clusters=new_clusters,
        expansion_depth=cluster.depth + 1,
    )


@router.get("/compilations", response_model=List[CompilationListItem])
async def list_compilations(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    List recent compilations.

    Returns a summary of recent Ask compilations, useful for reviewing
    past questions and their generated scenarios.
    """
    # Get from cache (in production, would query database)
    compilations = list(_compilation_cache.values())

    # Sort by compiled_at descending
    compilations.sort(key=lambda c: c.compiled_at, reverse=True)

    # Filter by project if specified
    if project_id:
        # Would filter in production
        pass

    # Limit results
    compilations = compilations[:limit]

    return [
        CompilationListItem(
            compilation_id=c.compilation_id,
            original_prompt=c.original_prompt[:100] + "..." if len(c.original_prompt) > 100 else c.original_prompt,
            intent_type=c.intent.intent_type.value,
            scenario_count=len(c.candidate_scenarios),
            cluster_count=len(c.clusters),
            compiled_at=c.compiled_at,
        )
        for c in compilations
    ]


@router.get("/compilations/{compilation_id}", response_model=AskCompileResponse)
async def get_compilation(
    compilation_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific compilation by ID.

    Returns the full compilation result including all scenarios and explanation.
    """
    result = _get_cached_compilation(compilation_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compilation {compilation_id} not found"
        )

    # Convert to response (same as compile endpoint)
    return AskCompileResponse(
        compilation_id=result.compilation_id,
        original_prompt=result.original_prompt,
        intent=IntentResponse(
            intent_type=result.intent.intent_type.value,
            confidence=result.intent.confidence,
            normalized_prompt=result.intent.normalized_prompt,
            scope=result.intent.scope.value,
            affected_regions=result.intent.affected_regions,
            affected_segments=result.intent.affected_segments,
            time_window=result.intent.time_window,
            key_entities=result.intent.key_entities,
            domain_hints=result.intent.domain_hints,
        ),
        sub_effects=[
            SubEffectResponse(
                effect_id=e.effect_id,
                description=e.description,
                target_type=e.target_type,
                target_variable=e.target_variable,
                operation=e.operation.value,
                magnitude=e.magnitude,
                confidence=e.confidence,
                dependencies=e.dependencies,
                rationale=e.rationale,
            )
            for e in result.sub_effects
        ],
        variable_mappings=[
            VariableMappingResponse(
                sub_effect_id=m.sub_effect_id,
                variable_name=m.variable_name,
                variable_type=m.variable_type,
                operation=m.operation.value,
                value=m.value,
                uncertainty=m.uncertainty,
                mapping_rationale=m.mapping_rationale,
            )
            for m in result.variable_mappings
        ],
        candidate_scenarios=[
            CandidateScenarioResponse(
                scenario_id=s.scenario_id,
                label=s.label,
                description=s.description,
                probability=s.probability,
                intervention_magnitude=s.intervention_magnitude,
                event_count=len(s.event_scripts),
                affected_variables=s.affected_variables,
                cluster_id=s.cluster_id,
            )
            for s in result.candidate_scenarios
        ],
        clusters=[
            ScenarioClusterResponse(
                cluster_id=c.cluster_id,
                label=c.label,
                representative_scenario_id=c.representative_scenario.scenario_id,
                member_count=len(c.member_scenario_ids),
                aggregate_probability=c.aggregate_probability,
                expandable=c.expandable,
                depth=c.depth,
            )
            for c in result.clusters
        ],
        explanation=ExplanationResponse(
            explanation_id=result.explanation.explanation_id,
            summary=result.explanation.summary,
            causal_chain=result.explanation.causal_chain,
            key_drivers=result.explanation.key_drivers,
            uncertainty_notes=result.explanation.uncertainty_notes,
            assumptions=result.explanation.assumptions,
            confidence_level=result.explanation.confidence_level,
            event_script_refs=result.explanation.event_script_refs,
        ),
        compiler_version=result.compiler_version,
        compiled_at=result.compiled_at,
        total_cost_usd=result.total_cost_usd,
        compilation_time_ms=result.compilation_time_ms,
        warnings=result.warnings,
        created_event_ids=[],  # Would fetch from DB
        created_bundle_id=None,  # Would fetch from DB
    )


@router.delete("/compilations/{compilation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_compilation(
    compilation_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a compilation from cache.

    Note: This only removes from cache. Persisted event scripts remain in DB.
    """
    if compilation_id in _compilation_cache:
        del _compilation_cache[compilation_id]
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compilation {compilation_id} not found"
        )
