"""
Event Compiler Service
Reference: project.md §11 Phase 4

The Event Compiler transforms natural language "What if..." questions into
executable event scripts. It is C5 compliant: LLM is used for compilation,
but events execute deterministically without LLM at runtime.

Components:
1. Intent & Scope Analyzer - Classifies prompt, extracts scope
2. Decomposer - Breaks one prompt into multiple sub-effects
3. Variable Mapper - Maps sub-effects to environment/perception variables
4. Scenario Generator - Generates candidate scenarios (no hard cap)
5. Clustering Algorithm - Groups similar scenarios for progressive expansion
6. Explanation Generator - Creates causal chain summaries
"""

import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.event_script import (
    EventScript,
    EventBundle,
    EventBundleMember,
    EventType,
    IntensityProfileType,
    DeltaOperation,
)
# LLM Router Integration (GAPS.md GAP-P0-001)
from app.services.llm_router import LLMRouter, LLMRouterContext


# =============================================================================
# Data Classes for Compiler Output
# =============================================================================

class IntentType(str, Enum):
    """Types of user intents detected from prompts."""
    EVENT = "event"           # "What if there's a new policy?"
    VARIABLE = "variable"     # "What if trust increases by 10%?"
    QUERY = "query"           # "What is the current adoption rate?"
    COMPARISON = "comparison" # "Compare scenario A vs B"
    EXPLANATION = "explanation"  # "Why did adoption drop?"


class PromptScope(str, Enum):
    """Scope of the prompt's effect."""
    GLOBAL = "global"         # Affects entire simulation
    REGIONAL = "regional"     # Affects specific regions
    SEGMENT = "segment"       # Affects specific persona segments
    INDIVIDUAL = "individual" # Affects specific individuals
    TEMPORAL = "temporal"     # Time-bounded effect


@dataclass
class ExtractedIntent:
    """Result of intent analysis."""
    intent_type: IntentType
    confidence: float  # 0.0 - 1.0
    original_prompt: str
    normalized_prompt: str
    scope: PromptScope
    affected_regions: List[str] = field(default_factory=list)
    affected_segments: List[str] = field(default_factory=list)
    time_window: Optional[Dict[str, int]] = None  # start_tick, end_tick
    key_entities: List[str] = field(default_factory=list)
    domain_hints: List[str] = field(default_factory=list)


@dataclass
class SubEffect:
    """A single sub-effect extracted from a prompt."""
    effect_id: str
    description: str
    target_type: str  # "environment" or "perception" or "action"
    target_variable: Optional[str]
    operation: DeltaOperation
    magnitude: Optional[float]  # Relative change (-1.0 to 1.0 or absolute)
    confidence: float
    dependencies: List[str] = field(default_factory=list)  # Other effect IDs
    rationale: str = ""


@dataclass
class VariableMapping:
    """Mapping from a sub-effect to concrete variable deltas."""
    sub_effect_id: str
    variable_name: str
    variable_type: str  # "environment", "perception", "action_prior"
    operation: DeltaOperation
    value: Any
    uncertainty: float  # 0.0 - 1.0
    mapping_rationale: str = ""


@dataclass
class CandidateScenario:
    """A candidate scenario generated from variable mappings."""
    scenario_id: str
    label: str
    description: str
    probability: float  # Prior probability estimate
    event_scripts: List[Dict[str, Any]]  # EventScript-compatible dicts
    affected_variables: List[str]
    intervention_magnitude: float  # Total intervention size
    cluster_id: Optional[str] = None
    parent_scenario_id: Optional[str] = None


@dataclass
class ScenarioCluster:
    """A cluster of similar scenarios for progressive expansion."""
    cluster_id: str
    label: str
    representative_scenario: CandidateScenario
    member_scenario_ids: List[str]
    aggregate_probability: float
    centroid_features: Dict[str, float]
    expandable: bool = True
    depth: int = 0


@dataclass
class CausalExplanation:
    """Explanation of how a prompt leads to outcomes."""
    explanation_id: str
    summary: str
    causal_chain: List[Dict[str, str]]  # [{cause, effect, mechanism}, ...]
    key_drivers: List[Dict[str, Any]]  # [{variable, importance, direction}, ...]
    uncertainty_notes: List[str]
    assumptions: List[str]
    confidence_level: str  # "high", "medium", "low"
    event_script_refs: List[str]  # Event IDs for linking


@dataclass
class CompilationResult:
    """Complete result of compiling a prompt."""
    compilation_id: str
    original_prompt: str
    intent: ExtractedIntent
    sub_effects: List[SubEffect]
    variable_mappings: List[VariableMapping]
    candidate_scenarios: List[CandidateScenario]
    clusters: List[ScenarioCluster]
    explanation: CausalExplanation
    compiler_version: str
    compiled_at: datetime
    total_cost_usd: float
    compilation_time_ms: int
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# Event Compiler Service
# =============================================================================

class EventCompiler:
    """
    Compiles natural language prompts into executable event scripts.

    This service implements C5: LLMs are compilers, not runtime brains.
    Events are compiled once and can be executed deterministically.

    Uses LLMRouter for centralized model management (GAPS.md GAP-P0-001).
    """

    COMPILER_VERSION = "1.0.0"

    def __init__(
        self,
        db: AsyncSession,
        llm_router: Optional[LLMRouter] = None,
    ):
        """
        Initialize the Event Compiler.

        Args:
            db: Database session (required for LLMRouter)
            llm_router: Optional pre-configured LLMRouter instance
        """
        self.db = db
        self.llm_router = llm_router or LLMRouter(db)

    # =========================================================================
    # Main Compilation Pipeline
    # =========================================================================

    async def compile(
        self,
        prompt: str,
        project_context: Dict[str, Any],
        db: AsyncSession,
        tenant_id: uuid.UUID,
        max_scenarios: int = 20,
        clustering_enabled: bool = True,
    ) -> CompilationResult:
        """
        Compile a natural language prompt into event scripts.

        Args:
            prompt: The "What if..." question from the user
            project_context: Context about the project (domain, variables, etc.)
            db: Database session for persistence
            tenant_id: Tenant ID for multi-tenancy
            max_scenarios: Maximum scenarios to generate (soft limit, no hard cap)
            clustering_enabled: Whether to cluster scenarios

        Returns:
            CompilationResult with all compiled artifacts
        """
        import time
        start_time = time.time()
        total_cost = 0.0
        warnings = []

        compilation_id = str(uuid.uuid4())

        # Step 1: Intent & Scope Analysis
        intent, cost = await self._analyze_intent(prompt, project_context)
        total_cost += cost

        # If it's a query, we handle differently
        if intent.intent_type == IntentType.QUERY:
            warnings.append("Query intent detected - no events generated")
            return self._create_query_result(
                compilation_id, prompt, intent, start_time, total_cost
            )

        # Step 2: Decompose into sub-effects
        sub_effects, cost = await self._decompose(prompt, intent, project_context)
        total_cost += cost

        # Step 3: Map to variables
        mappings, cost = await self._map_variables(
            sub_effects, project_context
        )
        total_cost += cost

        # Step 4: Generate scenarios
        scenarios, cost = await self._generate_scenarios(
            prompt, intent, sub_effects, mappings, project_context, max_scenarios
        )
        total_cost += cost

        # Step 5: Cluster scenarios (if enabled)
        clusters = []
        if clustering_enabled and len(scenarios) > 1:
            clusters = self._cluster_scenarios(scenarios)

        # Step 6: Generate explanation
        explanation, cost = await self._generate_explanation(
            prompt, intent, sub_effects, mappings, scenarios, project_context
        )
        total_cost += cost

        compilation_time_ms = int((time.time() - start_time) * 1000)

        return CompilationResult(
            compilation_id=compilation_id,
            original_prompt=prompt,
            intent=intent,
            sub_effects=sub_effects,
            variable_mappings=mappings,
            candidate_scenarios=scenarios,
            clusters=clusters,
            explanation=explanation,
            compiler_version=self.COMPILER_VERSION,
            compiled_at=datetime.utcnow(),
            total_cost_usd=total_cost,
            compilation_time_ms=compilation_time_ms,
            warnings=warnings,
        )

    # =========================================================================
    # Step 1: Intent & Scope Analyzer (P4-001)
    # =========================================================================

    async def _analyze_intent(
        self,
        prompt: str,
        context: Dict[str, Any],
    ) -> Tuple[ExtractedIntent, float]:
        """Analyze the user's intent and extract scope from the prompt."""

        domain = context.get("domain", "general")
        available_regions = context.get("regions", [])
        available_segments = context.get("segments", [])

        system_prompt = f"""You are an intent analyzer for a predictive simulation system.
Analyze the user's "What if..." question and extract:

1. Intent Type: One of:
   - event: A discrete event or intervention (policy change, shock, news)
   - variable: A direct variable change (trust increases by 10%)
   - query: Asking about current state (what is adoption rate?)
   - comparison: Comparing scenarios
   - explanation: Asking why something happened

2. Scope: One of:
   - global: Affects entire simulation
   - regional: Affects specific regions
   - segment: Affects specific persona segments
   - individual: Affects specific individuals
   - temporal: Time-bounded effect

3. Extract:
   - Affected regions (from: {available_regions})
   - Affected segments (from: {available_segments})
   - Time window (start_tick, end_tick if mentioned)
   - Key entities mentioned
   - Domain hints

Domain context: {domain}

Respond in JSON format:
{{
  "intent_type": "event|variable|query|comparison|explanation",
  "confidence": 0.0-1.0,
  "normalized_prompt": "cleaned version of prompt",
  "scope": "global|regional|segment|individual|temporal",
  "affected_regions": [],
  "affected_segments": [],
  "time_window": {{"start_tick": null, "end_tick": null}},
  "key_entities": [],
  "domain_hints": []
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        # Use LLMRouter with EVENT_COMPILER_INTENT profile
        response = await self.llm_router.complete(
            profile_key="EVENT_COMPILER_INTENT",
            messages=messages,
            temperature_override=0.3,  # Low temperature for consistent classification
            max_tokens_override=500,
        )

        try:
            # Parse JSON from response
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content)

            intent = ExtractedIntent(
                intent_type=IntentType(result.get("intent_type", "event")),
                confidence=result.get("confidence", 0.8),
                original_prompt=prompt,
                normalized_prompt=result.get("normalized_prompt", prompt),
                scope=PromptScope(result.get("scope", "global")),
                affected_regions=result.get("affected_regions", []),
                affected_segments=result.get("affected_segments", []),
                time_window=result.get("time_window"),
                key_entities=result.get("key_entities", []),
                domain_hints=result.get("domain_hints", []),
            )
        except (json.JSONDecodeError, ValueError):
            # Fallback to defaults
            intent = ExtractedIntent(
                intent_type=IntentType.EVENT,
                confidence=0.5,
                original_prompt=prompt,
                normalized_prompt=prompt,
                scope=PromptScope.GLOBAL,
            )

        return intent, response.cost_usd

    # =========================================================================
    # Step 2: Decomposer (P4-002)
    # =========================================================================

    async def _decompose(
        self,
        prompt: str,
        intent: ExtractedIntent,
        context: Dict[str, Any],
    ) -> Tuple[List[SubEffect], float]:
        """Decompose a prompt into multiple sub-effects."""

        domain = context.get("domain", "general")
        available_variables = context.get("variables", {})

        system_prompt = f"""You are an event decomposer for a predictive simulation system.
Break down the user's prompt into discrete sub-effects. Each sub-effect should be:

1. Atomic: One change at a time
2. Measurable: Can be quantified
3. Mappable: Can be linked to simulation variables

Domain: {domain}
Available variable categories:
- Environment: economic conditions, media sentiment, policy state
- Perception: trust, awareness, concern, optimism
- Action: adoption propensity, engagement level, decision thresholds

For each sub-effect, specify:
- Description of the effect
- Target type: "environment" or "perception" or "action"
- Target variable (if known): specific variable name
- Operation: "set", "add", "multiply"
- Magnitude: relative change (-1.0 to 1.0) or absolute value
- Confidence in this interpretation
- Dependencies on other effects (by ID)
- Rationale for this decomposition

Respond in JSON format:
{{
  "sub_effects": [
    {{
      "effect_id": "effect_1",
      "description": "...",
      "target_type": "environment|perception|action",
      "target_variable": "variable_name or null",
      "operation": "set|add|multiply",
      "magnitude": 0.0,
      "confidence": 0.0-1.0,
      "dependencies": [],
      "rationale": "..."
    }}
  ]
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Prompt: {prompt}\n\nIntent: {intent.intent_type.value}\nScope: {intent.scope.value}"}
        ]

        # Use LLMRouter with EVENT_COMPILER_DECOMPOSE profile
        response = await self.llm_router.complete(
            profile_key="EVENT_COMPILER_DECOMPOSE",
            messages=messages,
            temperature_override=0.5,
            max_tokens_override=1500,
        )

        sub_effects = []
        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content)

            for effect_data in result.get("sub_effects", []):
                sub_effects.append(SubEffect(
                    effect_id=effect_data.get("effect_id", str(uuid.uuid4())[:8]),
                    description=effect_data.get("description", ""),
                    target_type=effect_data.get("target_type", "environment"),
                    target_variable=effect_data.get("target_variable"),
                    operation=DeltaOperation(effect_data.get("operation", "add")),
                    magnitude=effect_data.get("magnitude"),
                    confidence=effect_data.get("confidence", 0.7),
                    dependencies=effect_data.get("dependencies", []),
                    rationale=effect_data.get("rationale", ""),
                ))
        except (json.JSONDecodeError, ValueError):
            # Create a single fallback effect
            sub_effects = [SubEffect(
                effect_id="effect_1",
                description=prompt,
                target_type="environment",
                target_variable=None,
                operation=DeltaOperation.ADD,
                magnitude=0.1,
                confidence=0.5,
            )]

        return sub_effects, response.cost_usd

    # =========================================================================
    # Step 3: Variable Mapper (P4-003)
    # =========================================================================

    async def _map_variables(
        self,
        sub_effects: List[SubEffect],
        context: Dict[str, Any],
    ) -> Tuple[List[VariableMapping], float]:
        """Map sub-effects to concrete environment/perception variables."""

        domain = context.get("domain", "general")
        variable_catalog = context.get("variable_catalog") or self._default_variable_catalog()

        # Build a description of available variables
        var_descriptions = []
        for category, variables in variable_catalog.items():
            for var_name, var_info in variables.items():
                var_descriptions.append(
                    f"- {category}.{var_name}: {var_info.get('description', '')} "
                    f"(range: {var_info.get('min', 0)}-{var_info.get('max', 1)})"
                )

        effects_text = "\n".join([
            f"- {e.effect_id}: {e.description} (target: {e.target_type}, magnitude: {e.magnitude})"
            for e in sub_effects
        ])

        system_prompt = f"""You are a variable mapper for a predictive simulation system.
Map each sub-effect to concrete simulation variables.

Domain: {domain}

Available variables:
{chr(10).join(var_descriptions)}

Sub-effects to map:
{effects_text}

For each mapping, specify:
- Which sub-effect it maps from
- Which variable to modify
- The operation to apply
- The concrete value to use
- Uncertainty in this mapping (0.0 = certain, 1.0 = very uncertain)
- Rationale for this mapping

Respond in JSON format:
{{
  "mappings": [
    {{
      "sub_effect_id": "effect_1",
      "variable_name": "category.variable_name",
      "variable_type": "environment|perception|action_prior",
      "operation": "set|add|multiply|min|max",
      "value": 0.0,
      "uncertainty": 0.0-1.0,
      "mapping_rationale": "..."
    }}
  ]
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Map the sub-effects to variables."}
        ]

        # Use LLMRouter with EVENT_COMPILER_VARIABLE_MAP profile
        response = await self.llm_router.complete(
            profile_key="EVENT_COMPILER_VARIABLE_MAP",
            messages=messages,
            temperature_override=0.4,
            max_tokens_override=1500,
        )

        mappings = []
        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content)

            for mapping_data in result.get("mappings", []):
                mappings.append(VariableMapping(
                    sub_effect_id=mapping_data.get("sub_effect_id", ""),
                    variable_name=mapping_data.get("variable_name", ""),
                    variable_type=mapping_data.get("variable_type", "environment"),
                    operation=DeltaOperation(mapping_data.get("operation", "add")),
                    value=mapping_data.get("value", 0.0),
                    uncertainty=mapping_data.get("uncertainty", 0.3),
                    mapping_rationale=mapping_data.get("mapping_rationale", ""),
                ))
        except (json.JSONDecodeError, ValueError):
            pass

        return mappings, response.cost_usd

    # =========================================================================
    # Step 4: Scenario Generator (P4-004)
    # =========================================================================

    async def _generate_scenarios(
        self,
        prompt: str,
        intent: ExtractedIntent,
        sub_effects: List[SubEffect],
        mappings: List[VariableMapping],
        context: Dict[str, Any],
        max_scenarios: int,
    ) -> Tuple[List[CandidateScenario], float]:
        """Generate candidate scenarios from variable mappings."""

        domain = context.get("domain", "general")
        project_id = context.get("project_id", str(uuid.uuid4()))

        # Build scenario variations based on uncertainty
        mappings_text = "\n".join([
            f"- {m.variable_name}: {m.operation.value} {m.value} (uncertainty: {m.uncertainty})"
            for m in mappings
        ])

        system_prompt = f"""You are a scenario generator for a predictive simulation system.
Generate diverse candidate scenarios that could result from the user's prompt.

Domain: {domain}
Original prompt: {prompt}

Variable mappings to use:
{mappings_text}

Generate {min(max_scenarios, 10)} diverse scenarios. For each:
1. Vary the magnitudes within uncertainty bounds
2. Consider different timing (immediate vs delayed)
3. Consider different intensity profiles (sharp vs gradual)
4. Estimate probability based on plausibility

Each scenario should include complete event script definitions.

Respond in JSON format:
{{
  "scenarios": [
    {{
      "scenario_id": "scenario_1",
      "label": "Brief label",
      "description": "What this scenario represents",
      "probability": 0.0-1.0,
      "intervention_magnitude": 0.0-1.0,
      "event_scripts": [
        {{
          "event_type": "policy|media|shock|individual_action|environmental|social|custom",
          "label": "Event label",
          "description": "Event description",
          "scope": {{
            "affected_regions": [],
            "affected_segments": [],
            "start_tick": 0,
            "end_tick": null
          }},
          "deltas": {{
            "environment_deltas": [
              {{"variable": "name", "operation": "add", "value": 0.1}}
            ],
            "perception_deltas": []
          }},
          "intensity_profile": {{
            "profile_type": "instantaneous|linear_decay|exponential_decay|lagged|pulse|step",
            "initial_intensity": 1.0,
            "decay_rate": null,
            "half_life_ticks": null,
            "lag_ticks": null
          }},
          "uncertainty": {{
            "occurrence_probability": 1.0,
            "intensity_variance": 0.1,
            "assumptions": []
          }}
        }}
      ]
    }}
  ]
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate candidate scenarios."}
        ]

        # Use LLMRouter with SCENARIO_GENERATOR profile
        response = await self.llm_router.complete(
            profile_key="SCENARIO_GENERATOR",
            messages=messages,
            temperature_override=0.7,  # Higher temperature for diversity
            max_tokens_override=4000,
        )

        scenarios = []
        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content)

            for scenario_data in result.get("scenarios", []):
                # Extract affected variables from event scripts
                affected_vars = set()
                for event in scenario_data.get("event_scripts", []):
                    for delta in event.get("deltas", {}).get("environment_deltas", []):
                        affected_vars.add(delta.get("variable", ""))
                    for delta in event.get("deltas", {}).get("perception_deltas", []):
                        affected_vars.add(delta.get("variable", ""))

                scenarios.append(CandidateScenario(
                    scenario_id=scenario_data.get("scenario_id", str(uuid.uuid4())[:8]),
                    label=scenario_data.get("label", "Scenario"),
                    description=scenario_data.get("description", ""),
                    probability=scenario_data.get("probability", 0.5),
                    event_scripts=scenario_data.get("event_scripts", []),
                    affected_variables=list(affected_vars),
                    intervention_magnitude=scenario_data.get("intervention_magnitude", 0.5),
                ))
        except (json.JSONDecodeError, ValueError):
            # Create a single fallback scenario
            scenarios = [self._create_fallback_scenario(mappings)]

        return scenarios, response.cost_usd

    # =========================================================================
    # Step 5: Clustering Algorithm (P4-005)
    # =========================================================================

    def _cluster_scenarios(
        self,
        scenarios: List[CandidateScenario],
        n_clusters: Optional[int] = None,
    ) -> List[ScenarioCluster]:
        """Cluster similar scenarios for progressive expansion."""

        if not scenarios:
            return []

        # Simple clustering by intervention magnitude and affected variables
        # In production, use proper clustering (k-means, hierarchical, etc.)

        # Group by magnitude buckets
        buckets = {"low": [], "medium": [], "high": []}
        for scenario in scenarios:
            if scenario.intervention_magnitude < 0.33:
                buckets["low"].append(scenario)
            elif scenario.intervention_magnitude < 0.67:
                buckets["medium"].append(scenario)
            else:
                buckets["high"].append(scenario)

        clusters = []
        for bucket_name, bucket_scenarios in buckets.items():
            if not bucket_scenarios:
                continue

            # Sort by probability and pick representative
            bucket_scenarios.sort(key=lambda s: s.probability, reverse=True)
            representative = bucket_scenarios[0]

            # Calculate aggregate probability
            aggregate_prob = sum(s.probability for s in bucket_scenarios) / len(bucket_scenarios)

            # Assign cluster IDs to scenarios
            cluster_id = f"cluster_{bucket_name}_{uuid.uuid4().hex[:8]}"
            for s in bucket_scenarios:
                s.cluster_id = cluster_id

            clusters.append(ScenarioCluster(
                cluster_id=cluster_id,
                label=f"{bucket_name.title()} Impact Scenarios",
                representative_scenario=representative,
                member_scenario_ids=[s.scenario_id for s in bucket_scenarios],
                aggregate_probability=aggregate_prob,
                centroid_features={"magnitude": representative.intervention_magnitude},
                expandable=len(bucket_scenarios) > 1,
                depth=0,
            ))

        return clusters

    # =========================================================================
    # Step 6: Explanation Generator (P4-007)
    # =========================================================================

    async def _generate_explanation(
        self,
        prompt: str,
        intent: ExtractedIntent,
        sub_effects: List[SubEffect],
        mappings: List[VariableMapping],
        scenarios: List[CandidateScenario],
        context: Dict[str, Any],
    ) -> Tuple[CausalExplanation, float]:
        """Generate causal chain summary and explanation."""

        domain = context.get("domain", "general")

        effects_text = "\n".join([f"- {e.description}" for e in sub_effects])
        mappings_text = "\n".join([
            f"- {m.variable_name} {m.operation.value} {m.value}"
            for m in mappings
        ])

        system_prompt = f"""You are an explanation generator for a predictive simulation system.
Generate a causal explanation of how the user's prompt leads to simulation outcomes.

Domain: {domain}
Prompt: {prompt}

Decomposed effects:
{effects_text}

Variable mappings:
{mappings_text}

Number of scenarios generated: {len(scenarios)}

Generate:
1. A clear summary of the causal chain (2-3 sentences)
2. Step-by-step causal chain (cause → effect → mechanism)
3. Key drivers ranked by importance
4. Uncertainty notes (what could go differently)
5. Assumptions made
6. Overall confidence level

Respond in JSON format:
{{
  "summary": "...",
  "causal_chain": [
    {{"cause": "...", "effect": "...", "mechanism": "..."}}
  ],
  "key_drivers": [
    {{"variable": "...", "importance": 0.0-1.0, "direction": "increase|decrease"}}
  ],
  "uncertainty_notes": [],
  "assumptions": [],
  "confidence_level": "high|medium|low"
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate the explanation."}
        ]

        # Use LLMRouter with EXPLANATION_GENERATOR profile
        response = await self.llm_router.complete(
            profile_key="EXPLANATION_GENERATOR",
            messages=messages,
            temperature_override=0.4,
            max_tokens_override=1500,
        )

        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content)

            explanation = CausalExplanation(
                explanation_id=str(uuid.uuid4()),
                summary=result.get("summary", ""),
                causal_chain=result.get("causal_chain", []),
                key_drivers=result.get("key_drivers", []),
                uncertainty_notes=result.get("uncertainty_notes", []),
                assumptions=result.get("assumptions", []),
                confidence_level=result.get("confidence_level", "medium"),
                event_script_refs=[],  # Populated when events are persisted
            )
        except (json.JSONDecodeError, ValueError):
            explanation = CausalExplanation(
                explanation_id=str(uuid.uuid4()),
                summary=f"Analysis of: {prompt}",
                causal_chain=[],
                key_drivers=[],
                uncertainty_notes=["Unable to generate detailed explanation"],
                assumptions=[],
                confidence_level="low",
                event_script_refs=[],
            )

        return explanation, response.cost_usd

    # =========================================================================
    # Persistence Methods
    # =========================================================================

    async def persist_compilation(
        self,
        result: CompilationResult,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Tuple[List[EventScript], Optional[EventBundle]]:
        """
        Persist compiled events and bundle to database.

        Returns:
            Tuple of (list of EventScripts, optional EventBundle)
        """
        event_scripts = []

        # Create a bundle if multiple scenarios
        bundle = None
        if len(result.candidate_scenarios) > 1:
            bundle = EventBundle(
                tenant_id=tenant_id,
                project_id=project_id,
                label=f"Compilation: {result.original_prompt[:100]}",
                description=result.explanation.summary,
                provenance={
                    "compiled_from": result.original_prompt,
                    "compiler_version": result.compiler_version,
                    "compiled_at": result.compiled_at.isoformat(),
                },
            )
            db.add(bundle)
            await db.flush()

        # Create event scripts for representative scenarios (one per cluster)
        for cluster in result.clusters:
            scenario = cluster.representative_scenario
            for event_data in scenario.event_scripts:
                event = EventScript(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    event_type=event_data.get("event_type", EventType.CUSTOM.value),
                    label=event_data.get("label", scenario.label),
                    description=event_data.get("description", scenario.description),
                    scope=event_data.get("scope", {}),
                    deltas=event_data.get("deltas", {}),
                    intensity_profile=event_data.get("intensity_profile", {}),
                    uncertainty=event_data.get("uncertainty", {}),
                    provenance={
                        "compiled_from": result.original_prompt,
                        "compiler_version": result.compiler_version,
                        "compiled_at": result.compiled_at.isoformat(),
                        "compilation_id": result.compilation_id,
                        "scenario_id": scenario.scenario_id,
                        "cluster_id": cluster.cluster_id,
                    },
                    is_validated=False,  # Needs validation before execution
                )
                db.add(event)
                event_scripts.append(event)

                # Add to bundle if exists
                if bundle:
                    await db.flush()
                    member = EventBundleMember(
                        bundle_id=bundle.id,
                        event_script_id=event.id,
                        order_index=len(event_scripts) - 1,
                    )
                    db.add(member)

        await db.commit()

        # Update explanation with event refs
        result.explanation.event_script_refs = [str(e.id) for e in event_scripts]

        return event_scripts, bundle

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _default_variable_catalog(self) -> Dict[str, Dict[str, Any]]:
        """Default variable catalog for when none is provided."""
        return {
            "environment": {
                "economic_confidence": {
                    "description": "Overall economic confidence index",
                    "min": -1.0,
                    "max": 1.0,
                },
                "media_sentiment": {
                    "description": "Media sentiment toward the topic",
                    "min": -1.0,
                    "max": 1.0,
                },
                "policy_restrictiveness": {
                    "description": "Level of policy restrictions",
                    "min": 0.0,
                    "max": 1.0,
                },
                "information_availability": {
                    "description": "Availability of relevant information",
                    "min": 0.0,
                    "max": 1.0,
                },
            },
            "perception": {
                "trust": {
                    "description": "General trust level",
                    "min": 0.0,
                    "max": 1.0,
                },
                "awareness": {
                    "description": "Awareness of the topic",
                    "min": 0.0,
                    "max": 1.0,
                },
                "concern": {
                    "description": "Level of concern about the topic",
                    "min": 0.0,
                    "max": 1.0,
                },
                "optimism": {
                    "description": "Optimism about outcomes",
                    "min": 0.0,
                    "max": 1.0,
                },
            },
            "action": {
                "adoption_propensity": {
                    "description": "Propensity to adopt/act",
                    "min": 0.0,
                    "max": 1.0,
                },
                "engagement_level": {
                    "description": "Level of engagement",
                    "min": 0.0,
                    "max": 1.0,
                },
                "decision_threshold": {
                    "description": "Threshold for making decisions",
                    "min": 0.0,
                    "max": 1.0,
                },
            },
        }

    def _create_fallback_scenario(
        self,
        mappings: List[VariableMapping],
    ) -> CandidateScenario:
        """Create a fallback scenario when generation fails."""

        event_scripts = [{
            "event_type": "custom",
            "label": "Fallback Event",
            "description": "Auto-generated fallback event",
            "scope": {},
            "deltas": {
                "environment_deltas": [
                    {
                        "variable": m.variable_name,
                        "operation": m.operation.value,
                        "value": m.value,
                    }
                    for m in mappings if m.variable_type == "environment"
                ],
                "perception_deltas": [
                    {
                        "variable": m.variable_name,
                        "operation": m.operation.value,
                        "value": m.value,
                    }
                    for m in mappings if m.variable_type == "perception"
                ],
            },
            "intensity_profile": {
                "profile_type": "instantaneous",
                "initial_intensity": 1.0,
            },
            "uncertainty": {
                "occurrence_probability": 1.0,
                "intensity_variance": 0.2,
            },
        }]

        return CandidateScenario(
            scenario_id=f"fallback_{uuid.uuid4().hex[:8]}",
            label="Fallback Scenario",
            description="Auto-generated scenario from variable mappings",
            probability=0.5,
            event_scripts=event_scripts,
            affected_variables=[m.variable_name for m in mappings],
            intervention_magnitude=0.5,
        )

    def _create_query_result(
        self,
        compilation_id: str,
        prompt: str,
        intent: ExtractedIntent,
        start_time: float,
        total_cost: float,
    ) -> CompilationResult:
        """Create a result for query-type intents (no events)."""
        import time

        return CompilationResult(
            compilation_id=compilation_id,
            original_prompt=prompt,
            intent=intent,
            sub_effects=[],
            variable_mappings=[],
            candidate_scenarios=[],
            clusters=[],
            explanation=CausalExplanation(
                explanation_id=str(uuid.uuid4()),
                summary="This is a query request, not an event/intervention.",
                causal_chain=[],
                key_drivers=[],
                uncertainty_notes=[],
                assumptions=[],
                confidence_level="high",
                event_script_refs=[],
            ),
            compiler_version=self.COMPILER_VERSION,
            compiled_at=datetime.utcnow(),
            total_cost_usd=total_cost,
            compilation_time_ms=int((time.time() - start_time) * 1000),
            warnings=["Query intent detected - no events generated"],
        )


# =============================================================================
# Factory Function (replaces singleton - LLMRouter requires db session)
# =============================================================================


def get_event_compiler(db: AsyncSession) -> EventCompiler:
    """
    Create an event compiler instance.

    Note: Cannot use singleton pattern as LLMRouter requires db session.
    """
    return EventCompiler(db=db)


async def compile_prompt(
    prompt: str,
    project_context: Dict[str, Any],
    db: AsyncSession,
    tenant_id: uuid.UUID,
    max_scenarios: int = 20,
    persist: bool = True,
) -> CompilationResult:
    """
    Convenience function to compile a prompt.

    Args:
        prompt: The "What if..." question
        project_context: Context about the project
        db: Database session
        tenant_id: Tenant ID
        max_scenarios: Maximum scenarios to generate
        persist: Whether to persist events to database

    Returns:
        CompilationResult with all compiled artifacts
    """
    compiler = EventCompiler(db=db)
    result = await compiler.compile(
        prompt=prompt,
        project_context=project_context,
        db=db,
        tenant_id=tenant_id,
        max_scenarios=max_scenarios,
    )

    if persist and result.candidate_scenarios:
        project_id = uuid.UUID(project_context.get("project_id", str(uuid.uuid4())))
        await compiler.persist_compilation(result, db, tenant_id, project_id)

    return result
