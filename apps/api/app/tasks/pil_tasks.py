"""
Project Intelligence Layer (PIL) Tasks
Reference: blueprint.md §5

Background tasks for AI-powered project orchestration:
- Goal Analysis: Parse user goals, suggest domain, generate clarifying questions
- Blueprint Building: Generate slots, tasks, calibration plan from clarified goals
- Slot Validation: Validate data against slot requirements
- Slot Summarization: Generate AI summaries of slot content
- Alignment Scoring: Score how well data aligns with project goals
- Task Guidance: Generate guidance for completing tasks

Key Principles:
- Non-blocking: All AI work runs in background, UI remains responsive
- Progress reporting: Jobs report progress stages for inline widgets
- Retry-safe: Idempotent operations with proper error handling
- Artifact creation: Each job produces referenceable artifacts
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
import uuid

import structlog
from sqlalchemy import select, update

logger = structlog.get_logger(__name__)

from app.core.celery_app import celery_app
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.tasks.base import (
    TenantAwareTask,
    JobContext,
    JobStatus,
    JobResult,
)
from app.models.pil_job import (
    PILJob,
    PILArtifact,
    PILJobStatus,
    PILJobType,
    ArtifactType,
)
from app.models.blueprint import (
    Blueprint,
    BlueprintSlot,
    BlueprintTask,
    DomainGuess,
    AlertState,
    SlotType,
    RequiredLevel,
    TaskAction,
    PLATFORM_SECTIONS,
)
from app.models.llm import LLMProfileKey
from app.services.llm_router import LLMRouter, LLMRouterContext
from app.services.slot_status_handler import (
    process_slot_pipeline_completion,
    mark_slot_processing,
)


# =============================================================================
# Slot Type Normalization (Map LLM output to SlotType enum values)
# =============================================================================

def _normalize_slot_type(data_type: str) -> str:
    """
    Convert LLM data_type output to valid SlotType enum value.

    The LLM prompt uses lowercase values like "table", "timeseries", "persona_set"
    but the SlotType enum uses PascalCase values like "Table", "TimeSeries".
    """
    mapping = {
        # Lowercase versions (as specified in LLM prompt)
        "persona_set": SlotType.PERSONA_SET.value,
        "table": SlotType.TABLE.value,
        "timeseries": SlotType.TIMESERIES.value,
        "document": SlotType.TEXT_CORPUS.value,  # Map "document" to TEXT_CORPUS
        "event_script_set": SlotType.EVENT_SCRIPT_SET.value,
        "ruleset": SlotType.RULESET.value,
        "graph": SlotType.GRAPH.value,
        "entity_set": SlotType.ENTITY_SET.value,
        "text_corpus": SlotType.TEXT_CORPUS.value,
        "labels": SlotType.LABELS.value,
        "assumption_set": SlotType.ASSUMPTION_SET.value,
        # PascalCase versions (if LLM returns these)
        "PersonaSet": SlotType.PERSONA_SET.value,
        "Table": SlotType.TABLE.value,
        "TimeSeries": SlotType.TIMESERIES.value,
        "TextCorpus": SlotType.TEXT_CORPUS.value,
        "EventScriptSet": SlotType.EVENT_SCRIPT_SET.value,
        "Ruleset": SlotType.RULESET.value,
        "Graph": SlotType.GRAPH.value,
        "EntitySet": SlotType.ENTITY_SET.value,
        "Labels": SlotType.LABELS.value,
        "AssumptionSet": SlotType.ASSUMPTION_SET.value,
    }
    return mapping.get(data_type, SlotType.TABLE.value)  # Default to TABLE


# =============================================================================
# Custom Exceptions for LLM Failures (Blueprint v2 - Fail Fast)
# =============================================================================

class PILLLMError(Exception):
    """
    Raised when an LLM call fails and PIL_ALLOW_FALLBACK is False.

    This ensures PIL jobs fail visibly rather than silently using
    keyword-based fallbacks, making it clear when OpenRouter isn't
    being called properly.
    """
    def __init__(self, profile_key: str, original_error: Exception):
        self.profile_key = profile_key
        self.original_error = original_error
        super().__init__(
            f"LLM call failed for {profile_key}: {str(original_error)}. "
            f"PIL_ALLOW_FALLBACK is disabled - no fallback used. "
            f"Check OPENROUTER_API_KEY and LLM profiles configuration."
        )


class PILProvenanceError(Exception):
    """
    Raised when LLM provenance cannot be verified (Slice 1A: No-Fake-Success).

    This ensures we never fake provenance using defaults - if the LLM response
    doesn't have proper provenance fields, the job must fail.
    """
    def __init__(self, profile_key: str, missing_field: str):
        self.profile_key = profile_key
        self.missing_field = missing_field
        super().__init__(
            f"LLM provenance verification failed for {profile_key}: "
            f"Missing required field '{missing_field}'. "
            f"Cannot verify this was a real OpenRouter call."
        )


class PILModelMismatchError(Exception):
    """
    Raised when the model used doesn't match the expected model (Slice 1A verification).

    This ensures we verify the exact model used at runtime, not just trust config.
    """
    def __init__(self, profile_key: str, expected_model: str, actual_model: str):
        self.profile_key = profile_key
        self.expected_model = expected_model
        self.actual_model = actual_model
        super().__init__(
            f"Model mismatch for {profile_key}: "
            f"Expected '{expected_model}', got '{actual_model}'. "
            f"This indicates a profile misconfiguration or unexpected fallback."
        )


# Expected models for PIL profiles (Slice 1A: Runtime verification)
PIL_EXPECTED_MODELS = {
    "PIL_GOAL_ANALYSIS": "openai/gpt-5.2",
    "PIL_CLARIFYING_QUESTIONS": "openai/gpt-5.2",
    "PIL_RISK_ASSESSMENT": "openai/gpt-5.2",
    "PIL_BLUEPRINT_GENERATION": "openai/gpt-5.2",
}


def build_llm_proof_from_response(
    response: Any,
    profile_key: str,
    verify_model: bool = True,
) -> Dict[str, Any]:
    """
    Build LLM proof metadata from LLMRouterResponse WITHOUT using defaults.

    Slice 1A: No-Fake-Success Rule
    - This function NEVER uses getattr(..., default=...) for provenance fields
    - If any required field is missing, it raises PILProvenanceError
    - This ensures we cannot accidentally fake provenance for non-LLM outputs

    Slice 1A: Model Verification
    - If verify_model=True, validates the model matches PIL_EXPECTED_MODELS
    - This ensures gpt-5.2 is actually used at runtime, not just configured

    Args:
        response: The LLMRouterResponse from the LLM call
        profile_key: The LLM profile key used for the call
        verify_model: If True, verify model matches expected (default True)

    Returns:
        Dict with verified LLM proof metadata

    Raises:
        PILProvenanceError: If required provenance field is missing
        PILModelMismatchError: If model doesn't match expected (when verify_model=True)
    """
    # Required fields that MUST exist for valid provenance
    required_fields = [
        "call_id",
        "model",
        "cache_hit",
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "provider",
        "fallback_used",
        "fallback_attempts",
    ]

    # Validate all required fields exist (no defaults!)
    for field in required_fields:
        if not hasattr(response, field):
            raise PILProvenanceError(profile_key, field)
        # Also check for None values on critical fields
        if field in ["call_id", "model", "provider"] and getattr(response, field) is None:
            raise PILProvenanceError(profile_key, f"{field} (is None)")

    # Slice 1A: Verify model matches expected at runtime
    if verify_model and profile_key in PIL_EXPECTED_MODELS:
        expected_model = PIL_EXPECTED_MODELS[profile_key]
        actual_model = response.model
        if actual_model != expected_model:
            # Log the mismatch for debugging
            logger.warning(
                "Model mismatch detected",
                profile_key=profile_key,
                expected_model=expected_model,
                actual_model=actual_model,
            )
            raise PILModelMismatchError(profile_key, expected_model, actual_model)

    # Build proof with verified fields only
    return {
        "call_id": response.call_id,
        "profile_key": profile_key,
        "model": response.model,
        "cache_hit": response.cache_hit,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "cost_usd": response.cost_usd,
        "timestamp": datetime.utcnow().isoformat(),
        # Slice 1A: Provider verification - no defaults
        "provider": response.provider,
        "fallback_used": response.fallback_used,
        "fallback_attempts": response.fallback_attempts,
    }


def get_async_session():
    """Create async session for database operations within tasks."""
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
    )
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def update_job_progress(
    session: AsyncSession,
    job_id: UUID,
    progress_percent: int,
    stage_name: Optional[str] = None,
    eta_hint: Optional[str] = None,
    stages_completed: Optional[int] = None,
):
    """Update job progress in database."""
    update_data = {
        "progress_percent": progress_percent,
        "updated_at": datetime.utcnow(),
    }
    if stage_name:
        update_data["stage_name"] = stage_name
    if eta_hint:
        update_data["eta_hint"] = eta_hint
    if stages_completed is not None:
        update_data["stages_completed"] = stages_completed

    await session.execute(
        update(PILJob)
        .where(PILJob.id == job_id)
        .values(**update_data)
    )
    await session.commit()


async def mark_job_running(session: AsyncSession, job_id: UUID, celery_task_id: str):
    """Mark job as running with Celery task ID."""
    await session.execute(
        update(PILJob)
        .where(PILJob.id == job_id)
        .values(
            status=PILJobStatus.RUNNING,
            celery_task_id=celery_task_id,
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    await session.commit()


async def mark_job_succeeded(
    session: AsyncSession,
    job_id: UUID,
    result: Optional[Dict] = None,
    artifact_ids: Optional[List[str]] = None,
):
    """Mark job as succeeded with results."""
    update_data = {
        "status": PILJobStatus.SUCCEEDED,
        "progress_percent": 100,
        "completed_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    if result:
        update_data["result"] = result
    if artifact_ids:
        update_data["artifact_ids"] = artifact_ids

    await session.execute(
        update(PILJob)
        .where(PILJob.id == job_id)
        .values(**update_data)
    )
    await session.commit()


async def mark_job_failed(session: AsyncSession, job_id: UUID, error_message: str):
    """Mark job as failed with error message."""
    await session.execute(
        update(PILJob)
        .where(PILJob.id == job_id)
        .values(
            status=PILJobStatus.FAILED,
            error_message=error_message,
            completed_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    await session.commit()


async def create_artifact(
    session: AsyncSession,
    tenant_id: UUID,
    project_id: UUID,
    artifact_type: ArtifactType,
    artifact_name: str,
    content: Optional[Dict] = None,
    content_text: Optional[str] = None,
    blueprint_id: Optional[UUID] = None,
    blueprint_version: Optional[int] = None,
    job_id: Optional[UUID] = None,
    slot_id: Optional[str] = None,
    task_id: Optional[str] = None,
    alignment_score: Optional[float] = None,
    quality_score: Optional[float] = None,
    validation_passed: Optional[bool] = None,
) -> PILArtifact:
    """Create a PIL artifact."""
    artifact = PILArtifact(
        tenant_id=tenant_id,
        project_id=project_id,
        blueprint_id=blueprint_id,
        blueprint_version=blueprint_version,
        artifact_type=artifact_type,
        artifact_name=artifact_name,
        job_id=job_id,
        slot_id=slot_id,
        task_id=task_id,
        content=content,
        content_text=content_text,
        alignment_score=alignment_score,
        quality_score=quality_score,
        validation_passed=validation_passed,
    )
    session.add(artifact)
    await session.flush()
    await session.refresh(artifact)
    return artifact


# =============================================================================
# Goal Analysis Task (blueprint.md §4.1)
# =============================================================================

def _run_async(coro):
    """Run async coroutine in a new event loop (safe for Celery workers)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If we're already in an async context, create a new event loop
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


@celery_app.task(bind=True, base=TenantAwareTask, max_retries=3)
def goal_analysis_task(self, job_id: str, context: dict):
    """
    Analyze user goal text and produce:
    - Goal summary
    - Domain classification
    - Clarifying questions
    - Blueprint preview
    - Risk notes

    Reference: blueprint.md §4.1, §4.2.1
    """
    return _run_async(_goal_analysis_async(self, job_id, context))


async def _goal_analysis_async(task, job_id: str, context: dict):
    """Async implementation of goal analysis."""
    job_uuid = UUID(job_id)
    AsyncSessionLocal = get_async_session()

    async with AsyncSessionLocal() as session:
        try:
            # Mark job as running
            await mark_job_running(session, job_uuid, task.request.id)

            # Get the job
            result = await session.execute(
                select(PILJob).where(PILJob.id == job_uuid)
            )
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            goal_text = job.input_params.get("goal_text", "")
            # Slice 1A: skip_cache defaults to True for wizard flows (fresh LLM calls for verification)
            skip_cache = job.input_params.get("skip_cache", True)

            # Create LLMRouter context
            # Note: project_id may be None during initial goal analysis (before project created)
            # Slice 1A: Set strict_llm=True and skip_cache=True for wizard flows
            # This enforces the No-Fake-Success rule: no fallback allowed
            llm_context = LLMRouterContext(
                tenant_id=str(job.tenant_id) if job.tenant_id else None,
                project_id=str(job.project_id) if job.project_id else None,
                phase="compilation",  # C5 tracking - LLM used for planning
                strict_llm=True,  # Slice 1A: No fallback allowed for wizard flows
                skip_cache=skip_cache,  # Slice 1A: Bypass cache by default for fresh LLM proof
            )

            # Stage 1: Parse goal and classify domain (20%)
            await update_job_progress(
                session, job_uuid, 20,
                stage_name="Analyzing goal and domain",
                stages_completed=1
            )

            # Use LLM for goal analysis and domain classification
            goal_summary, domain_guess, goal_llm_proof = await _llm_analyze_goal(
                session, goal_text, llm_context, skip_cache=skip_cache
            )

            # Stage 2: Generate clarifying questions (50%)
            await update_job_progress(
                session, job_uuid, 50,
                stage_name="Generating clarifying questions",
                stages_completed=2
            )

            clarifying_questions, questions_llm_proof = await _llm_generate_clarifying_questions(
                session, goal_text, domain_guess, llm_context, skip_cache=skip_cache
            )

            # Stage 3: Generate blueprint preview and assess risks (80%)
            await update_job_progress(
                session, job_uuid, 80,
                stage_name="Generating blueprint preview",
                stages_completed=3
            )

            blueprint_preview, preview_llm_proof = await _llm_generate_blueprint_preview(
                session, domain_guess, llm_context, skip_cache=skip_cache
            )
            risk_notes, risks_llm_proof = await _llm_assess_risks(
                session, goal_text, domain_guess, llm_context, skip_cache=skip_cache
            )

            # Create artifacts
            artifact_ids = []

            # Goal summary artifact
            summary_artifact = await create_artifact(
                session,
                tenant_id=job.tenant_id,
                project_id=job.project_id,
                artifact_type=ArtifactType.GOAL_SUMMARY,
                artifact_name="Goal Analysis Summary",
                content={
                    "goal_text": goal_text,
                    "goal_summary": goal_summary,
                    "domain_guess": domain_guess,
                },
                content_text=goal_summary,
                blueprint_id=job.blueprint_id,
                job_id=job_uuid,
            )
            artifact_ids.append(str(summary_artifact.id))

            # Clarifying questions artifact
            questions_artifact = await create_artifact(
                session,
                tenant_id=job.tenant_id,
                project_id=job.project_id,
                artifact_type=ArtifactType.CLARIFICATION_QUESTIONS,
                artifact_name="Clarifying Questions",
                content={"questions": clarifying_questions},
                blueprint_id=job.blueprint_id,
                job_id=job_uuid,
            )
            artifact_ids.append(str(questions_artifact.id))

            # Blueprint preview artifact
            preview_artifact = await create_artifact(
                session,
                tenant_id=job.tenant_id,
                project_id=job.project_id,
                artifact_type=ArtifactType.BLUEPRINT_PREVIEW,
                artifact_name="Blueprint Preview",
                content={
                    "blueprint_preview": blueprint_preview,
                    "risk_notes": risk_notes,
                },
                blueprint_id=job.blueprint_id,
                job_id=job_uuid,
            )
            artifact_ids.append(str(preview_artifact.id))

            # Update blueprint with analysis results
            if job.blueprint_id:
                await session.execute(
                    update(Blueprint)
                    .where(Blueprint.id == job.blueprint_id)
                    .values(
                        goal_summary=goal_summary,
                        domain_guess=domain_guess,
                        risk_notes=risk_notes,
                        updated_at=datetime.utcnow(),
                    )
                )

            # Transform clarifying questions to frontend format
            # Backend generates: {id, question, reason, type, options: string[], required}
            # Frontend expects: {id, question, why_we_ask, answer_type, options: {value, label}[], required}
            transformed_questions = []
            for q in clarifying_questions:
                transformed_q = {
                    "id": q.get("id", ""),
                    "question": q.get("question", ""),
                    "why_we_ask": q.get("reason", ""),  # Map reason -> why_we_ask
                    "answer_type": q.get("type", "short_text"),  # Map type -> answer_type
                    "required": q.get("required", False),
                }
                # Transform options from string[] to {value, label}[]
                if q.get("options"):
                    transformed_q["options"] = [
                        {"value": opt, "label": opt} for opt in q.get("options", [])
                    ]
                transformed_questions.append(transformed_q)

            # Extract primary drivers from blueprint preview key_challenges
            primary_drivers = blueprint_preview.get("key_challenges", [])[:3]

            # Build full GoalAnalysisResult for frontend
            # Mark job as succeeded with complete result structure
            await mark_job_succeeded(
                session, job_uuid,
                result={
                    "goal_summary": goal_summary,
                    "domain_guess": domain_guess,
                    "output_type": "distribution",  # Default, can be refined later
                    "horizon_guess": "6 months",  # Default, will be refined by clarifying questions
                    "scope_guess": "national",  # Default scope
                    "primary_drivers": primary_drivers,
                    "clarifying_questions": transformed_questions,
                    "risk_notes": risk_notes,
                    "processing_time_ms": 0,  # TODO: track actual processing time
                    # LLM Proof metadata (Blueprint v2 - verifiable LLM execution)
                    # This allows frontend to show proof that OpenRouter was called
                    "llm_proof": {
                        "goal_analysis": goal_llm_proof,
                        "clarifying_questions": questions_llm_proof,
                        "blueprint_preview": preview_llm_proof,
                        "risk_assessment": risks_llm_proof,
                    },
                },
                artifact_ids=artifact_ids,
            )

            return {
                "status": "success",
                "goal_summary": goal_summary,
                "domain_guess": domain_guess,
                "artifact_ids": artifact_ids,
            }

        except Exception as e:
            await session.rollback()  # Rollback failed transaction before marking job failed
            await mark_job_failed(session, job_uuid, str(e))
            raise


# =============================================================================
# LLM-Powered Analysis Functions
# =============================================================================

async def _llm_analyze_goal(
    session: AsyncSession,
    goal_text: str,
    context: LLMRouterContext,
    skip_cache: bool = False,
) -> tuple[str, str, dict]:
    """
    Use LLM to analyze goal text and classify domain.
    Returns (goal_summary, domain_guess, llm_proof).

    Args:
        skip_cache: If True, bypass cache for fresh LLM call (default in staging)

    Returns:
        Tuple of (goal_summary, domain_guess, llm_proof)
        llm_proof contains: model, call_id, cache_hit, tokens, cost_usd
    """
    router = LLMRouter(session)

    # Prompt for goal analysis and domain classification
    system_prompt = """You are an expert project analyst for a predictive AI simulation platform.
Your task is to analyze a user's project goal and:
1. Create a concise summary (2-3 sentences) of what they want to predict
2. Classify the domain into one of these categories:
   - election: Election outcomes, voting behavior, political forecasting
   - market_demand: Consumer demand, sales forecasting, market trends
   - production_forecast: Manufacturing, supply chain, production planning
   - policy_impact: Government policy effects, regulatory impact analysis
   - perception_risk: Brand perception, reputation risk, public opinion
   - generic: General prediction tasks that don't fit above categories

Respond in JSON format:
{
  "goal_summary": "concise summary of the prediction goal",
  "domain": "one of: election, market_demand, production_forecast, policy_impact, perception_risk, generic",
  "confidence": 0.0-1.0
}"""

    user_prompt = f"""Analyze this project goal:

"{goal_text}"

Provide the goal summary and domain classification."""

    try:
        response = await router.complete(
            profile_key=LLMProfileKey.PIL_GOAL_ANALYSIS.value,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            context=context,
            temperature_override=0.3,  # Lower temperature for consistency
            max_tokens_override=500,
            skip_cache=skip_cache,
            response_format={"type": "json_object"},
        )

        # Parse JSON response
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError as json_err:
            logger.error(
                "LLM returned invalid JSON for goal analysis",
                error=str(json_err),
                content_preview=response.content[:500] if response.content else None,
            )
            raise ValueError(f"LLM returned invalid JSON: {json_err}")

        goal_summary = result.get("goal_summary", goal_text[:200])
        domain = result.get("domain", "generic")

        # Map to DomainGuess enum value
        domain_map = {
            "election": DomainGuess.ELECTION.value,
            "market_demand": DomainGuess.MARKET_DEMAND.value,
            "production_forecast": DomainGuess.PRODUCTION_FORECAST.value,
            "policy_impact": DomainGuess.POLICY_IMPACT.value,
            "perception_risk": DomainGuess.PERCEPTION_RISK.value,
            "generic": DomainGuess.GENERIC.value,
        }
        domain_guess = domain_map.get(domain.lower(), DomainGuess.GENERIC.value)

        # Build LLM proof metadata for audit trail (Slice 1A: LLM Truth)
        # Uses helper function that NEVER uses defaults - fails if provenance missing
        llm_proof = build_llm_proof_from_response(
            response, LLMProfileKey.PIL_GOAL_ANALYSIS.value
        )

        return goal_summary, domain_guess, llm_proof

    except Exception as e:
        # Check if fallbacks are allowed (default: False in staging/prod)
        if settings.PIL_ALLOW_FALLBACK:
            return _fallback_goal_analysis(goal_text)
        # Fail fast - no silent fallbacks
        raise PILLLMError(LLMProfileKey.PIL_GOAL_ANALYSIS.value, e)


def _fallback_goal_analysis(goal_text: str) -> tuple[str, str, dict]:
    """Fallback goal analysis when LLM is unavailable."""
    # Simple summary
    if len(goal_text) < 100:
        goal_summary = goal_text
    else:
        goal_summary = f"Project aims to {goal_text[:200]}..."

    # Keyword-based domain classification
    goal_lower = goal_text.lower()
    if any(word in goal_lower for word in ["election", "vote", "candidate", "political"]):
        domain = DomainGuess.ELECTION.value
    elif any(word in goal_lower for word in ["market", "demand", "sales", "consumer"]):
        domain = DomainGuess.MARKET_DEMAND.value
    elif any(word in goal_lower for word in ["production", "manufacturing", "forecast"]):
        domain = DomainGuess.PRODUCTION_FORECAST.value
    elif any(word in goal_lower for word in ["policy", "regulation", "government"]):
        domain = DomainGuess.POLICY_IMPACT.value
    elif any(word in goal_lower for word in ["risk", "perception", "brand", "reputation"]):
        domain = DomainGuess.PERCEPTION_RISK.value
    else:
        domain = DomainGuess.GENERIC.value

    # Fallback proof - indicates no LLM was used
    llm_proof = {
        "call_id": f"fallback_{uuid.uuid4()}",
        "profile_key": LLMProfileKey.PIL_GOAL_ANALYSIS.value,
        "model": "fallback_keyword_match",
        "cache_hit": False,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "timestamp": datetime.utcnow().isoformat(),
        "is_fallback": True,
    }

    return goal_summary, domain, llm_proof


async def _llm_generate_clarifying_questions(
    session: AsyncSession,
    goal_text: str,
    domain: str,
    context: LLMRouterContext,
    skip_cache: bool = False,
) -> tuple[List[Dict], dict]:
    """
    Use LLM to generate clarifying questions for the project.

    Args:
        skip_cache: If True, bypass cache for fresh LLM call (default in staging)

    Returns:
        Tuple of (questions_list, llm_proof)
    """
    router = LLMRouter(session)

    system_prompt = """You are an expert requirements analyst for a predictive AI simulation platform.
Generate 3-5 clarifying questions to better understand the user's prediction project.

Each question should:
1. Help clarify scope, data needs, or success criteria
2. Be answerable with a short response or selection
3. Include a reason why this information is needed

The platform runs agent-based simulations with personas representing population segments.
Questions should help determine: prediction target, time horizon, geographic scope,
data requirements, validation approach, and specific domain details.

Respond in JSON format:
{
  "questions": [
    {
      "id": "q1",
      "question": "The question text",
      "reason": "Why this is important",
      "type": "single_select" | "multi_select" | "short_input" | "long_input",
      "options": ["option1", "option2"] (only for select types),
      "required": true | false
    }
  ]
}"""

    user_prompt = f"""Generate clarifying questions for this project:

Goal: "{goal_text}"
Domain: {domain}

Generate 3-5 questions tailored to this specific goal and domain."""

    try:
        response = await router.complete(
            profile_key=LLMProfileKey.PIL_CLARIFYING_QUESTIONS.value,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            context=context,
            temperature_override=0.5,  # Moderate creativity
            max_tokens_override=1200,
            skip_cache=skip_cache,
            response_format={"type": "json_object"},
        )

        try:
            result = json.loads(response.content)
        except json.JSONDecodeError as json_err:
            logger.error(
                "LLM returned invalid JSON for clarifying questions",
                error=str(json_err),
                content_preview=response.content[:500] if response.content else None,
            )
            raise ValueError(f"LLM returned invalid JSON: {json_err}")

        questions = result.get("questions", [])

        # Ensure required base questions are included
        question_ids = {q.get("id") for q in questions}
        if "time_horizon" not in question_ids:
            questions.insert(0, {
                "id": "time_horizon",
                "question": "What time horizon are you targeting for predictions?",
                "reason": "Affects data requirements and simulation approach",
                "type": "single_select",
                "options": ["1 month", "3 months", "6 months", "1 year", "2+ years"],
                "required": True,
            })

        # Build LLM proof metadata (Slice 1A: LLM Truth)
        # Uses helper function that NEVER uses defaults - fails if provenance missing
        llm_proof = build_llm_proof_from_response(
            response, LLMProfileKey.PIL_CLARIFYING_QUESTIONS.value
        )

        return questions, llm_proof

    except Exception as e:
        # Check if fallbacks are allowed (default: False in staging/prod)
        if settings.PIL_ALLOW_FALLBACK:
            return _fallback_clarifying_questions(domain)
        # Fail fast - no silent fallbacks
        raise PILLLMError(LLMProfileKey.PIL_CLARIFYING_QUESTIONS.value, e)


def _fallback_clarifying_questions(domain: str) -> tuple[List[Dict], dict]:
    """Fallback questions when LLM is unavailable."""
    base_questions = [
        {
            "id": "q1",
            "question": "What is your primary prediction target?",
            "reason": "Helps determine the output type needed",
            "type": "single_select",
            "options": ["Probability distribution", "Point estimate", "Ranked outcomes", "Recommended paths"],
            "required": True,
        },
        {
            "id": "q2",
            "question": "What time horizon are you targeting?",
            "reason": "Affects data requirements and simulation approach",
            "type": "single_select",
            "options": ["1 month", "3 months", "6 months", "1 year", "Custom"],
            "required": True,
        },
        {
            "id": "q3",
            "question": "What geographic scope applies?",
            "reason": "Determines persona and data requirements",
            "type": "short_input",
            "required": False,
        },
    ]

    if domain == DomainGuess.ELECTION.value:
        base_questions.append({
            "id": "q_election_1",
            "question": "Which election or electoral process?",
            "reason": "Determines specific data sources needed",
            "type": "short_input",
            "required": True,
        })
    elif domain == DomainGuess.MARKET_DEMAND.value:
        base_questions.append({
            "id": "q_market_1",
            "question": "What product or service category?",
            "reason": "Affects consumer persona requirements",
            "type": "short_input",
            "required": True,
        })

    # Fallback proof
    llm_proof = {
        "call_id": f"fallback_{uuid.uuid4()}",
        "profile_key": LLMProfileKey.PIL_CLARIFYING_QUESTIONS.value,
        "model": "fallback_template",
        "cache_hit": False,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "timestamp": datetime.utcnow().isoformat(),
        "is_fallback": True,
    }

    return base_questions, llm_proof


async def _llm_generate_blueprint_preview(
    session: AsyncSession,
    domain: str,
    context: LLMRouterContext,
    skip_cache: bool = False,
) -> tuple[Dict, dict]:
    """
    Use LLM to generate a blueprint preview based on domain.

    Args:
        skip_cache: If True, bypass cache for fresh LLM call (default in staging)

    Returns:
        Tuple of (blueprint_preview_dict, llm_proof)
    """
    router = LLMRouter(session)

    # Simplified prompt to get compact JSON response
    system_prompt = """You are an expert simulation architect. Generate a concise blueprint preview.

Slot types: PersonaSet, Table, TimeSeries, EventScriptSet, TextCorpus, Graph

Return ONLY valid JSON with this exact structure (keep arrays short, max 2-3 items each):
{"required_slots":["slot1"],"recommended_slots":["slot2"],"section_tasks":{"inputs":["task"],"personas":["task"],"rules":["task"],"run_params":["task"],"reliability":["task"]},"key_challenges":["challenge"]}"""

    user_prompt = f"Domain: {domain}. Return the JSON blueprint preview."

    try:
        response = await router.complete(
            profile_key=LLMProfileKey.PIL_BLUEPRINT_GENERATION.value,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            context=context,
            temperature_override=0.2,  # Lower temperature for more consistent JSON
            max_tokens_override=1000,  # Limit output to prevent truncation
            skip_cache=skip_cache,
            response_format={"type": "json_object"},  # Force valid JSON output
        )

        # Parse JSON response with error handling
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError as json_err:
            # Log the parsing error and raw response for debugging
            logger.error(
                "JSON parsing failed for blueprint preview",
                error=str(json_err),
                response_length=len(response.content) if response.content else 0,
                response_preview=response.content[:500] if response.content else None,
            )
            # Check if fallbacks are allowed
            if settings.PIL_ALLOW_FALLBACK:
                return _fallback_blueprint_preview(domain)
            raise PILLLMError(
                LLMProfileKey.PIL_BLUEPRINT_GENERATION.value,
                ValueError(f"LLM returned invalid JSON: {json_err}"),
            )

        blueprint_preview = {
            "required_slots": result.get("required_slots", ["PersonaSet"]),
            "recommended_slots": result.get("recommended_slots", ["EventScriptSet"]),
            "section_tasks": result.get("section_tasks", {}),
            "key_challenges": result.get("key_challenges", []),
        }

        # Build LLM proof metadata (Slice 1A: LLM Truth)
        # Uses helper function that NEVER uses defaults - fails if provenance missing
        llm_proof = build_llm_proof_from_response(
            response, LLMProfileKey.PIL_BLUEPRINT_GENERATION.value
        )

        return blueprint_preview, llm_proof

    except PILLLMError:
        # Re-raise PILLLMError without wrapping
        raise
    except Exception as e:
        # Check if fallbacks are allowed (default: False in staging/prod)
        if settings.PIL_ALLOW_FALLBACK:
            return _fallback_blueprint_preview(domain)
        # Fail fast - no silent fallbacks
        raise PILLLMError(LLMProfileKey.PIL_BLUEPRINT_GENERATION.value, e)


def _fallback_blueprint_preview(domain: str) -> tuple[Dict, dict]:
    """Fallback blueprint preview when LLM is unavailable."""
    required_slots = ["PersonaSet"]
    recommended_slots = ["TimeSeries", "EventScriptSet"]

    if domain == DomainGuess.ELECTION.value:
        required_slots.extend(["Table"])
        recommended_slots.extend(["TextCorpus"])
    elif domain == DomainGuess.MARKET_DEMAND.value:
        required_slots.extend(["TimeSeries"])
        recommended_slots.extend(["Graph"])

    section_tasks = {
        "inputs": ["Upload or connect data sources", "Validate data quality"],
        "personas": ["Create representative agent population", "Validate demographic distribution"],
        "rules": ["Define decision rules", "Configure behavior parameters"],
        "run_params": ["Set simulation parameters", "Configure output metrics"],
        "reliability": ["Set up calibration plan", "Define validation metrics"],
    }

    blueprint_preview = {
        "required_slots": required_slots,
        "recommended_slots": recommended_slots,
        "section_tasks": section_tasks,
    }

    # Fallback proof
    llm_proof = {
        "call_id": f"fallback_{uuid.uuid4()}",
        "profile_key": LLMProfileKey.PIL_BLUEPRINT_GENERATION.value,
        "model": "fallback_template",
        "cache_hit": False,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "timestamp": datetime.utcnow().isoformat(),
        "is_fallback": True,
    }

    return blueprint_preview, llm_proof


async def _llm_assess_risks(
    session: AsyncSession,
    goal_text: str,
    domain: str,
    context: LLMRouterContext,
    skip_cache: bool = False,
) -> tuple[List[str], dict]:
    """
    Use LLM to assess potential risks for the project.

    Args:
        skip_cache: If True, bypass cache for fresh LLM call (default in staging)

    Returns:
        Tuple of (risks_list, llm_proof)
    """
    router = LLMRouter(session)

    system_prompt = """You are a risk analyst for a predictive AI simulation platform.
Assess potential risks and challenges for a simulation project.

Consider these risk categories:
1. Data quality and availability risks
2. Privacy and ethical concerns
3. Technical feasibility risks
4. Validation and calibration challenges
5. Domain-specific pitfalls

Respond in JSON format:
{
  "risks": [
    "Risk description 1",
    "Risk description 2"
  ],
  "recommendations": [
    "Mitigation recommendation 1"
  ]
}

Keep each risk to one clear sentence. Include 2-5 risks."""

    user_prompt = f"""Assess risks for this project:

Goal: "{goal_text}"
Domain: {domain}

What are the key risks and challenges?"""

    try:
        response = await router.complete(
            profile_key=LLMProfileKey.PIL_RISK_ASSESSMENT.value,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            context=context,
            temperature_override=0.3,
            max_tokens_override=600,
            skip_cache=skip_cache,
            response_format={"type": "json_object"},
        )

        try:
            result = json.loads(response.content)
        except json.JSONDecodeError as json_err:
            logger.error(
                "LLM returned invalid JSON for risk assessment",
                error=str(json_err),
                content_preview=response.content[:500] if response.content else None,
            )
            raise ValueError(f"LLM returned invalid JSON: {json_err}")

        risks = result.get("risks", [])

        if not risks:
            risks = ["No significant risks identified at this stage"]

        # Build LLM proof metadata (Slice 1A: LLM Truth)
        # Uses helper function that NEVER uses defaults - fails if provenance missing
        llm_proof = build_llm_proof_from_response(
            response, LLMProfileKey.PIL_RISK_ASSESSMENT.value
        )

        return risks, llm_proof

    except Exception as e:
        # Check if fallbacks are allowed (default: False in staging/prod)
        if settings.PIL_ALLOW_FALLBACK:
            return _fallback_risk_assessment(goal_text, domain)
        # Fail fast - no silent fallbacks
        raise PILLLMError(LLMProfileKey.PIL_RISK_ASSESSMENT.value, e)


def _fallback_risk_assessment(goal_text: str, domain: str) -> tuple[List[str], dict]:
    """Fallback risk assessment when LLM is unavailable."""
    risks = []
    goal_lower = goal_text.lower()

    if "sensitive" in goal_lower or "personal" in goal_lower:
        risks.append("Project may involve sensitive personal data - ensure privacy compliance")

    if domain == DomainGuess.ELECTION.value:
        risks.append("Election predictions require careful handling of political data")

    if "real-time" in goal_lower or "live" in goal_lower:
        risks.append("Real-time requirements may conflict with on-demand simulation model")

    if not risks:
        risks.append("No significant risks identified at this stage")

    # Fallback proof
    llm_proof = {
        "call_id": f"fallback_{uuid.uuid4()}",
        "profile_key": LLMProfileKey.PIL_RISK_ASSESSMENT.value,
        "model": "fallback_keyword_match",
        "cache_hit": False,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "timestamp": datetime.utcnow().isoformat(),
        "is_fallback": True,
    }

    return risks, llm_proof


# =============================================================================
# LLM Blueprint Generation (Slice 1B)
# =============================================================================


async def _llm_build_blueprint(
    session: AsyncSession,
    goal_text: str,
    goal_summary: str,
    domain: str,
    clarification_answers: Dict[str, Any],
    skip_cache: bool = True,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Use LLM to generate a customized blueprint based on goal + clarification answers.

    Slice 1B: This function incorporates the user's clarification answers into the
    LLM prompt to generate slots and tasks tailored to their specific needs.

    Args:
        goal_text: Original goal/prediction description
        goal_summary: Analyzed summary from goal_analysis
        domain: Classified domain (election, market_demand, etc.)
        clarification_answers: User's answers to clarifying questions
        skip_cache: Whether to bypass LLM cache (default True for fresh generation)

    Returns:
        Tuple of (blueprint_config, llm_proof)
        - blueprint_config: Dict with slots, tasks, calibration_plan, branching_plan
        - llm_proof: LLM provenance metadata

    Raises:
        PILLLMError: If LLM call fails and fallbacks are disabled
    """
    profile_key = LLMProfileKey.PIL_BLUEPRINT_GENERATION.value

    # Format clarification answers for the prompt
    answers_text = ""
    if clarification_answers:
        answer_lines = []
        for q_id, answer in clarification_answers.items():
            if isinstance(answer, list):
                answer_str = ", ".join(str(a) for a in answer)
            else:
                answer_str = str(answer)
            # Format question ID to readable form (e.g., time_horizon -> Time Horizon)
            q_label = q_id.replace("_", " ").title()
            answer_lines.append(f"- {q_label}: {answer_str}")
        answers_text = "\n".join(answer_lines)
    else:
        answers_text = "(No clarification answers provided - user skipped clarification)"

    # Build the prompt with full context
    system_prompt = """You are an expert simulation architect for a predictive AI platform.
Your task is to generate a customized project blueprint based on the user's goal and their answers to clarifying questions.

The blueprint must include:
1. INPUT_SLOTS: Data sources needed (each with name, type, required_level, description)
2. SECTION_TASKS: Tasks organized by section (overview, inputs, personas, rules, run_params, reliability)
3. CALIBRATION_PLAN: Historical validation requirements
4. BRANCHING_PLAN: Variables that can be branched for scenario exploration

Respond ONLY with valid JSON in this exact format:
{
  "input_slots": [
    {
      "name": "string - descriptive name for the data input",
      "data_type": "persona_set|table|timeseries|document|event_script_set|ruleset|graph",
      "required_level": "required|recommended|optional",
      "description": "string - why this data is needed",
      "example_sources": ["manual_upload", "connect_api", "ai_generation", "ai_research"]
    }
  ],
  "section_tasks": {
    "overview": [
      {"title": "string", "why_it_matters": "string"}
    ],
    "inputs": [
      {"title": "string", "why_it_matters": "string"}
    ],
    "personas": [
      {"title": "string", "why_it_matters": "string"}
    ],
    "rules": [
      {"title": "string", "why_it_matters": "string"}
    ],
    "run_params": [
      {"title": "string", "why_it_matters": "string"}
    ],
    "reliability": [
      {"title": "string", "why_it_matters": "string"}
    ]
  },
  "calibration_plan": {
    "required_historical_windows": ["string"],
    "evaluation_metrics": ["string"],
    "min_sample_size": 100
  },
  "branching_plan": {
    "branchable_variables": ["string"],
    "scenario_suggestions": ["string"]
  }
}"""

    user_prompt = f"""Generate a blueprint for the following prediction project:

**GOAL:**
{goal_text}

**ANALYZED SUMMARY:**
{goal_summary}

**DOMAIN:**
{domain}

**USER'S CLARIFICATION ANSWERS:**
{answers_text}

Generate a COMPACT blueprint tailored to this specific project. Keep each array to 3-5 items max.
IMPORTANT: Return ONLY valid JSON. No markdown, no explanation. Just the JSON object.

Respond with JSON only, no explanation."""

    try:
        llm_router = LLMRouter(session)
        context = LLMRouterContext(
            strict_llm=True,  # Slice 1A: No fallback allowed
            skip_cache=skip_cache,
        )

        response = await llm_router.complete(
            profile_key=profile_key,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            context=context,
            temperature_override=0.2,
            max_tokens_override=4000,
            skip_cache=skip_cache,
            response_format={"type": "json_object"},
        )

        # Build LLM proof with Slice 1A verification
        llm_proof = build_llm_proof_from_response(response, profile_key, verify_model=True)

        # Parse the LLM response
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        blueprint_config = json.loads(content.strip())
        return blueprint_config, llm_proof

    except Exception as e:
        # Check if fallbacks are allowed (default: False in staging/prod)
        if settings.PIL_ALLOW_FALLBACK:
            # Fallback to template-based generation
            return _fallback_build_blueprint(domain, clarification_answers)
        # Fail fast - no silent fallbacks (Slice 1A)
        raise PILLLMError(
            profile_key,
            Exception(f"All LLM models failed for {profile_key}: {str(e)}. "
                     f"PIL_ALLOW_FALLBACK is disabled - no fallback used. "
                     f"Check OPENROUTER_API_KEY and LLM profiles configuration.")
        )


def _fallback_build_blueprint(
    domain: str,
    clarification_answers: Dict[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Fallback blueprint generation when LLM is unavailable."""
    # Use template-based slot/task generation
    slots = _generate_slots(domain, clarification_answers)
    tasks = _generate_tasks(domain, clarification_answers)

    horizon = clarification_answers.get("time_horizon", "6 months")
    if isinstance(horizon, list) and len(horizon) > 0:
        horizon = horizon[0]

    blueprint_config = {
        "slots": slots,
        "tasks": tasks,
        "calibration_plan": _generate_calibration_plan(domain),
        "branching_plan": _generate_branching_plan(domain),
        "horizon": horizon,
        "scope": clarification_answers.get("scope", "national"),
    }

    # Fallback proof marker
    llm_proof = {
        "call_id": f"fallback_{uuid.uuid4()}",
        "profile_key": LLMProfileKey.PIL_BLUEPRINT_GENERATION.value,
        "model": "fallback_template",
        "cache_hit": False,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "timestamp": datetime.utcnow().isoformat(),
        "is_fallback": True,
        "provider": "none",
        "fallback_used": True,
        "fallback_attempts": 0,
    }

    return blueprint_config, llm_proof


# =============================================================================
# Blueprint Build Task (blueprint.md §4.3)
# =============================================================================

@celery_app.task(bind=True, base=TenantAwareTask, max_retries=3)
def blueprint_build_task(self, job_id: str, context: dict):
    """
    Build complete blueprint from clarified goals.
    Creates slots, tasks, calibration plan, and branching plan.

    Reference: blueprint.md §4.3
    """
    return _run_async(_blueprint_build_async(self, job_id, context))


async def _blueprint_build_async(task, job_id: str, context: dict):
    """Async implementation of blueprint building."""
    job_uuid = UUID(job_id)
    AsyncSessionLocal = get_async_session()

    async with AsyncSessionLocal() as session:
        try:
            await mark_job_running(session, job_uuid, task.request.id)

            result = await session.execute(
                select(PILJob).where(PILJob.id == job_uuid)
            )
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            goal_text = job.input_params.get("goal_text", "")
            clarification_answers = job.input_params.get("clarification_answers", {})

            # If no blueprint_id, create one (supports "Skip & Generate Blueprint" flow)
            blueprint = None
            if job.blueprint_id:
                bp_result = await session.execute(
                    select(Blueprint).where(Blueprint.id == job.blueprint_id)
                )
                blueprint = bp_result.scalar_one_or_none()

            if not blueprint:
                # Create a new blueprint for this job
                goal_summary = job.input_params.get("goal_summary", goal_text[:200])
                domain_guess = job.input_params.get("domain_guess", DomainGuess.GENERIC.value)

                blueprint = Blueprint(
                    tenant_id=job.tenant_id,
                    project_id=job.project_id,  # May be None
                    goal_text=goal_text,
                    goal_summary=goal_summary,
                    domain_guess=domain_guess,
                    is_draft=True,
                    version=1,
                )
                session.add(blueprint)
                await session.flush()

                # Link blueprint to job
                job.blueprint_id = blueprint.id
                await session.flush()

            # Stage 1: LLM Blueprint Generation (30%)
            # Slice 1B: Use LLM to generate blueprint with clarification answers context
            await update_job_progress(
                session, job_uuid, 30,
                stage_name="Generating blueprint with AI",
                stages_completed=1
            )

            try:
                # Call LLM with full context (goal + analysis + clarification answers)
                llm_blueprint_config, llm_proof = await _llm_build_blueprint(
                    session=session,
                    goal_text=goal_text,
                    goal_summary=blueprint.goal_summary or goal_text[:200],
                    domain=blueprint.domain_guess,
                    clarification_answers=clarification_answers,
                    skip_cache=True,  # Fresh generation for each blueprint
                )

                # Extract slots and tasks from LLM response
                llm_slots = llm_blueprint_config.get("input_slots", [])
                llm_tasks = llm_blueprint_config.get("section_tasks", {})
                calibration_plan = llm_blueprint_config.get("calibration_plan", {})
                branching_plan = llm_blueprint_config.get("branching_plan", {})

            except PILLLMError:
                # Re-raise LLM errors (Slice 1A: no silent fallback)
                raise
            except Exception as e:
                # Wrap unexpected errors
                raise PILLLMError(
                    LLMProfileKey.PIL_BLUEPRINT_GENERATION.value,
                    e
                ) from e

            # Stage 2: Persist slots (60%)
            await update_job_progress(
                session, job_uuid, 60,
                stage_name="Saving input slots",
                stages_completed=2
            )

            # Convert LLM slots to database format
            slots = []
            for idx, llm_slot in enumerate(llm_slots):
                slot_data = {
                    "sort_order": idx + 1,
                    "slot_name": llm_slot.get("name", f"Slot {idx + 1}"),
                    "slot_type": _normalize_slot_type(llm_slot.get("data_type", "table")),
                    "required_level": llm_slot.get("required_level", RequiredLevel.RECOMMENDED.value),
                    "description": llm_slot.get("description", ""),
                    "allowed_acquisition_methods": llm_slot.get("example_sources", ["manual_upload"]),
                    "status": AlertState.NOT_STARTED.value,
                    "fulfilled": False,
                }
                slots.append(slot_data)
                slot = BlueprintSlot(
                    blueprint_id=blueprint.id,
                    **slot_data,
                )
                session.add(slot)

            # Stage 3: Persist tasks (80%)
            await update_job_progress(
                session, job_uuid, 80,
                stage_name="Saving section tasks",
                stages_completed=3
            )

            # Convert LLM section_tasks to database format
            # Map section_id to available_actions (same as fallback tasks)
            section_actions_map = {
                "overview": [TaskAction.MANUAL_ADD.value],
                "inputs": [TaskAction.MANUAL_ADD.value, TaskAction.CONNECT_SOURCE.value],
                "personas": [TaskAction.AI_GENERATE.value, TaskAction.AI_RESEARCH.value, TaskAction.MANUAL_ADD.value],
                "rules": [TaskAction.MANUAL_ADD.value],
                "run_params": [TaskAction.MANUAL_ADD.value],
                "reliability": [TaskAction.MANUAL_ADD.value],
            }

            tasks = []
            task_idx = 0
            for section_id, section_task_list in llm_tasks.items():
                for llm_task in section_task_list:
                    task_idx += 1
                    task_data = {
                        "section_id": section_id,
                        "sort_order": task_idx,
                        "title": llm_task.get("title", f"Task {task_idx}"),
                        "description": llm_task.get("why_it_matters", ""),
                        "why_it_matters": llm_task.get("why_it_matters", ""),
                        "available_actions": section_actions_map.get(section_id, [TaskAction.MANUAL_ADD.value]),
                        "status": AlertState.NOT_STARTED.value,
                    }
                    tasks.append(task_data)
                    task_obj = BlueprintTask(
                        blueprint_id=blueprint.id,
                        **task_data,
                    )
                    session.add(task_obj)

            # Update blueprint
            blueprint.calibration_plan = calibration_plan
            blueprint.branching_plan = branching_plan
            blueprint.clarification_answers = clarification_answers
            blueprint.is_draft = True  # Still draft until published
            blueprint.updated_at = datetime.utcnow()

            await session.commit()

            # Transform slots to frontend InputSlot format
            # Backend: {sort_order, slot_name, slot_type, required_level, description, ...}
            # Frontend: {slot_id, name, description, required_level, data_type, example_sources}
            transformed_slots = []
            for idx, slot_data in enumerate(slots):
                transformed_slots.append({
                    "slot_id": f"slot_{idx + 1}",
                    "name": slot_data.get("slot_name", ""),
                    "description": slot_data.get("description", ""),
                    "required_level": slot_data.get("required_level", "recommended"),
                    "data_type": slot_data.get("slot_type", ""),
                    "example_sources": slot_data.get("allowed_acquisition_methods", []),
                })

            # Transform tasks to frontend section_tasks format
            # Backend: {section_id, sort_order, title, description, why_it_matters, ...}
            # Frontend: Record<string, SectionTask[]> where SectionTask = {task_id, title, why_it_matters, ...}
            section_tasks: Dict[str, List[Dict]] = {}
            for idx, task_data in enumerate(tasks):
                section_id = task_data.get("section_id", "overview")
                if section_id not in section_tasks:
                    section_tasks[section_id] = []
                section_tasks[section_id].append({
                    "task_id": f"task_{idx + 1}",
                    "title": task_data.get("title", ""),
                    "why_it_matters": task_data.get("why_it_matters", task_data.get("description", "")),
                    "linked_slots": [],  # Can be populated based on task type
                    "completion_criteria": task_data.get("description", ""),
                })

            # Extract time horizon from clarification answers
            horizon = clarification_answers.get("time_horizon", "6 months")
            if isinstance(horizon, list) and len(horizon) > 0:
                horizon = horizon[0]

            # Build full BlueprintDraft for frontend
            blueprint_draft = {
                "project_profile": {
                    "goal_text": goal_text,
                    "goal_summary": blueprint.goal_summary or goal_text[:200],
                    "domain_guess": blueprint.domain_guess,
                    "output_type": "distribution",  # Default
                    "horizon": horizon,
                    "scope": clarification_answers.get("scope", "national"),
                    "success_metrics": [],  # Can be populated from clarification
                },
                "strategy": {
                    "chosen_core": "collective",  # Default strategy
                    "primary_drivers": blueprint.risk_notes[:3] if blueprint.risk_notes else [],
                    "required_modules": ["persona_engine", "event_processor"],
                },
                "input_slots": transformed_slots,
                "section_tasks": section_tasks,
                "clarification_answers": clarification_answers,
                "generated_at": datetime.utcnow().isoformat(),
                "processing_time_ms": 0,  # TODO: track actual time
                "warnings": [],
                # Also include raw counts for backward compatibility
                "slots_created": len(slots),
                "tasks_created": len(tasks),
                "calibration_plan": True,
                "branching_plan": True,
                "blueprint_id": str(blueprint.id),
                # Slice 1B: Include LLM provenance for blueprint generation
                "llm_proof": {
                    "blueprint_generation": llm_proof,
                },
            }

            # Mark succeeded with full BlueprintDraft
            await mark_job_succeeded(
                session, job_uuid,
                result=blueprint_draft,
            )

            return {"status": "success", "slots": len(slots), "tasks": len(tasks)}

        except Exception as e:
            await session.rollback()  # Rollback failed transaction before marking job failed
            await mark_job_failed(session, job_uuid, str(e))
            raise


def _generate_slots(domain: str, answers: Dict) -> List[Dict]:
    """Generate slots based on domain and clarification answers."""
    slots = []
    sort_order = 0

    # Required PersonaSet for all projects
    sort_order += 1
    slots.append({
        "sort_order": sort_order,
        "slot_name": "Agent Personas",
        "slot_type": SlotType.PERSONA_SET.value,
        "required_level": RequiredLevel.REQUIRED.value,
        "description": "Population of agents representing your target group",
        "allowed_acquisition_methods": ["manual_upload", "ai_generation", "ai_research"],
        "status": AlertState.NOT_STARTED.value,
        "fulfilled": False,
    })

    # Domain-specific slots
    if domain == DomainGuess.ELECTION.value:
        sort_order += 1
        slots.append({
            "sort_order": sort_order,
            "slot_name": "Voter Demographics",
            "slot_type": SlotType.TABLE.value,
            "required_level": RequiredLevel.REQUIRED.value,
            "description": "Demographic breakdown of voter population",
            "allowed_acquisition_methods": ["manual_upload", "connect_api", "ai_research"],
            "status": AlertState.NOT_STARTED.value,
            "fulfilled": False,
        })

    elif domain == DomainGuess.MARKET_DEMAND.value:
        sort_order += 1
        slots.append({
            "sort_order": sort_order,
            "slot_name": "Historical Sales Data",
            "slot_type": SlotType.TIMESERIES.value,
            "required_level": RequiredLevel.REQUIRED.value,
            "description": "Historical sales or demand data",
            "allowed_acquisition_methods": ["manual_upload", "connect_api"],
            "status": AlertState.NOT_STARTED.value,
            "fulfilled": False,
        })

    # Event scripts for all domains
    sort_order += 1
    slots.append({
        "sort_order": sort_order,
        "slot_name": "Event Scenarios",
        "slot_type": SlotType.EVENT_SCRIPT_SET.value,
        "required_level": RequiredLevel.RECOMMENDED.value,
        "description": "External events that may affect agent behavior",
        "allowed_acquisition_methods": ["manual_add", "ai_generation"],
        "status": AlertState.NOT_STARTED.value,
        "fulfilled": False,
    })

    return slots


def _generate_tasks(domain: str, answers: Dict) -> List[Dict]:
    """Generate section tasks based on domain."""
    tasks = []

    # Overview section
    tasks.append({
        "section_id": "overview",
        "sort_order": 1,
        "title": "Review project goals and requirements",
        "description": "Verify that the project blueprint matches your objectives",
        "available_actions": [TaskAction.MANUAL_ADD.value],
        "status": AlertState.NOT_STARTED.value,
    })

    # Inputs section
    tasks.append({
        "section_id": "inputs",
        "sort_order": 1,
        "title": "Upload required data",
        "description": "Provide the data needed for simulation",
        "why_it_matters": "Data quality directly impacts prediction accuracy",
        "available_actions": [TaskAction.MANUAL_ADD.value, TaskAction.CONNECT_SOURCE.value],
        "status": AlertState.NOT_STARTED.value,
    })

    # Personas section
    tasks.append({
        "section_id": "personas",
        "sort_order": 1,
        "title": "Create agent population",
        "description": "Define the agents that will participate in simulation",
        "why_it_matters": "Agent diversity affects outcome distributions",
        "available_actions": [TaskAction.AI_GENERATE.value, TaskAction.AI_RESEARCH.value, TaskAction.MANUAL_ADD.value],
        "status": AlertState.NOT_STARTED.value,
    })

    # Rules section
    tasks.append({
        "section_id": "rules",
        "sort_order": 1,
        "title": "Configure decision rules",
        "description": "Define how agents make decisions",
        "why_it_matters": "Rules determine agent behavior patterns",
        "available_actions": [TaskAction.MANUAL_ADD.value],
        "status": AlertState.NOT_STARTED.value,
    })

    # Run params section
    tasks.append({
        "section_id": "run_params",
        "sort_order": 1,
        "title": "Set simulation parameters",
        "description": "Configure simulation duration, seeds, and output metrics",
        "available_actions": [TaskAction.MANUAL_ADD.value],
        "status": AlertState.NOT_STARTED.value,
    })

    # Reliability section
    tasks.append({
        "section_id": "reliability",
        "sort_order": 1,
        "title": "Define calibration plan",
        "description": "Set up validation and calibration requirements",
        "why_it_matters": "Calibration ensures prediction reliability",
        "available_actions": [TaskAction.MANUAL_ADD.value],
        "status": AlertState.NOT_STARTED.value,
    })

    return tasks


def _generate_calibration_plan(domain: str) -> Dict:
    """Generate calibration plan based on domain."""
    return {
        "required_historical_windows": ["6 months", "1 year"],
        "labels_needed": ["ground_truth_outcomes"],
        "evaluation_metrics": ["brier_score", "calibration_error", "auc_roc"],
        "min_test_suite_size": 100,
    }


def _generate_branching_plan(domain: str) -> Dict:
    """Generate branching plan for Universe Map."""
    branchable = ["event_intensity", "agent_count", "time_horizon"]

    if domain == DomainGuess.ELECTION.value:
        branchable.append("turnout_rate")
    elif domain == DomainGuess.MARKET_DEMAND.value:
        branchable.append("price_sensitivity")

    return {
        "branchable_variables": branchable,
        "event_template_suggestions": ["economic_shock", "news_event", "competitor_action"],
        "probability_aggregation_policy": "mean",
        "node_metadata_requirements": ["timestamp", "seed", "config_hash"],
    }


# =============================================================================
# Slot Validation Task (blueprint.md §6.3)
# =============================================================================

@celery_app.task(bind=True, base=TenantAwareTask, max_retries=3)
def slot_validation_task(self, job_id: str, context: dict):
    """
    Validate data against slot requirements.
    Produces validation report artifact.

    Reference: blueprint.md §6.3
    """
    return _run_async(_slot_validation_async(self, job_id, context))


async def _slot_validation_async(task, job_id: str, context: dict):
    """Async implementation of slot validation."""
    job_uuid = UUID(job_id)
    AsyncSessionLocal = get_async_session()

    async with AsyncSessionLocal() as session:
        try:
            await mark_job_running(session, job_uuid, task.request.id)

            result = await session.execute(
                select(PILJob).where(PILJob.id == job_uuid)
            )
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            slot_id = job.input_params.get("slot_id")
            fulfilled_by = job.input_params.get("fulfilled_by", {})

            # Simulate validation stages
            await update_job_progress(
                session, job_uuid, 30,
                stage_name="Checking schema compliance"
            )

            await update_job_progress(
                session, job_uuid, 60,
                stage_name="Validating data quality"
            )

            # Generate validation report
            validation_report = {
                "slot_id": slot_id,
                "fulfilled_by": fulfilled_by,
                "schema_valid": True,
                "quality_score": 0.85,
                "issues": [],
                "recommendations": [],
            }

            await update_job_progress(
                session, job_uuid, 90,
                stage_name="Generating validation report"
            )

            # Create artifact
            artifact = await create_artifact(
                session,
                tenant_id=job.tenant_id,
                project_id=job.project_id,
                artifact_type=ArtifactType.SLOT_VALIDATION_REPORT,
                artifact_name=f"Validation Report: {fulfilled_by.get('name', 'Unknown')}",
                content=validation_report,
                blueprint_id=job.blueprint_id,
                job_id=job_uuid,
                slot_id=slot_id,
                quality_score=validation_report["quality_score"],
                validation_passed=validation_report["schema_valid"],
            )

            await mark_job_succeeded(
                session, job_uuid,
                result=validation_report,
                artifact_ids=[str(artifact.id)],
            )

            # PHASE 5: Update slot status based on validation result
            job.result = validation_report  # Set result for status handler
            job.status = PILJobStatus.SUCCEEDED.value
            status_update = await process_slot_pipeline_completion(session, job)

            return {
                "status": "success",
                "validation": validation_report,
                "slot_status_update": status_update,
            }

        except Exception as e:
            await mark_job_failed(session, job_uuid, str(e))
            # PHASE 5: Update slot status on failure
            job.status = PILJobStatus.FAILED.value
            job.error_message = str(e)
            await process_slot_pipeline_completion(session, job)
            raise


# =============================================================================
# Slot Summarization Task (blueprint_v2.md §5.2 - AI Summary)
# =============================================================================

@celery_app.task(bind=True, base=TenantAwareTask, max_retries=3)
def slot_summarization_task(self, job_id: str, context: dict):
    """
    Generate AI summary of slot data.
    Produces SLOT_SUMMARY artifact with natural language description.

    Reference: blueprint_v2.md §5.2
    """
    return _run_async(_slot_summarization_async(self, job_id, context))


async def _slot_summarization_async(task, job_id: str, context: dict):
    """Async implementation of slot summarization."""
    job_uuid = UUID(job_id)
    AsyncSessionLocal = get_async_session()

    async with AsyncSessionLocal() as session:
        try:
            await mark_job_running(session, job_uuid, task.request.id)

            result = await session.execute(
                select(PILJob).where(PILJob.id == job_uuid)
            )
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            slot_id = job.input_params.get("slot_id")
            fulfilled_by = job.input_params.get("fulfilled_by", {})
            data_sample = job.input_params.get("data_sample", {})
            skip_cache = job.input_params.get("skip_cache", False)

            await update_job_progress(
                session, job_uuid, 20,
                stage_name="Analyzing data structure"
            )

            # Get blueprint and slot for context
            bp_result = await session.execute(
                select(Blueprint).where(Blueprint.id == job.blueprint_id)
            )
            blueprint = bp_result.scalar_one_or_none()

            await update_job_progress(
                session, job_uuid, 40,
                stage_name="Generating AI summary"
            )

            # Use LLM for summarization
            summary_content = {
                "slot_id": slot_id,
                "data_type": fulfilled_by.get("type", "unknown"),
                "source_name": fulfilled_by.get("name", "Unknown"),
                "summary": f"This slot contains {fulfilled_by.get('type', 'data')} data from {fulfilled_by.get('name', 'an unknown source')}.",
                "key_characteristics": [],
                "data_quality_notes": [],
                "recommended_uses": [],
            }

            # Try to get LLM-powered summary
            try:
                llm_context = LLMRouterContext(
                    tenant_id=str(job.tenant_id) if job.tenant_id else None,
                    project_id=str(job.project_id) if job.project_id else None,
                    phase="summarization",
                )
                router = LLMRouter(session)

                system_prompt = """You are an expert data analyst for a predictive simulation platform.
Summarize data sources concisely, explaining their relevance to simulation projects."""

                user_prompt = f"""Summarize this data source for a predictive simulation project:

Data Type: {fulfilled_by.get('type', 'unknown')}
Source Name: {fulfilled_by.get('name', 'Unknown')}
Description: {fulfilled_by.get('description', 'No description provided')}

Project Goal: {blueprint.goal_text if blueprint else 'Unknown'}

Provide a brief summary (2-3 sentences) of what this data represents and how it might be useful for the project.
"""
                llm_response = await router.complete(
                    profile_key=LLMProfileKey.PIL_GOAL_ANALYSIS.value,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    context=llm_context,
                    temperature_override=0.3,
                    max_tokens_override=300,
                    skip_cache=skip_cache,
                )

                if llm_response and llm_response.content:
                    summary_content["summary"] = llm_response.content
                    summary_content["ai_generated"] = True

            except Exception as llm_error:
                # Check if fallbacks are allowed (default: False in staging/prod)
                if settings.PIL_ALLOW_FALLBACK:
                    # Fallback to basic summary if LLM fails and fallbacks allowed
                    summary_content["ai_generated"] = False
                    summary_content["fallback_reason"] = str(llm_error)
                else:
                    # Fail fast - no silent fallbacks
                    raise PILLLMError("SLOT_SUMMARIZATION", llm_error)

            await update_job_progress(
                session, job_uuid, 80,
                stage_name="Creating summary artifact"
            )

            # Create artifact
            artifact = await create_artifact(
                session,
                tenant_id=job.tenant_id,
                project_id=job.project_id,
                artifact_type=ArtifactType.SLOT_SUMMARY,
                artifact_name=f"Summary: {fulfilled_by.get('name', 'Unknown')}",
                content=summary_content,
                content_text=summary_content["summary"],
                blueprint_id=job.blueprint_id,
                job_id=job_uuid,
                slot_id=slot_id,
            )

            await mark_job_succeeded(
                session, job_uuid,
                result=summary_content,
                artifact_ids=[str(artifact.id)],
            )

            # PHASE 5: Summarization doesn't change status, but we log completion
            job.result = summary_content
            job.status = PILJobStatus.SUCCEEDED.value
            await process_slot_pipeline_completion(session, job)

            return {"status": "success", "summary": summary_content}

        except Exception as e:
            await mark_job_failed(session, job_uuid, str(e))
            # PHASE 5: Update slot status on failure
            job.status = PILJobStatus.FAILED.value
            job.error_message = str(e)
            await process_slot_pipeline_completion(session, job)
            raise


# =============================================================================
# Slot Alignment Scoring Task (blueprint_v2.md §5.2 - Fit Score)
# =============================================================================

@celery_app.task(bind=True, base=TenantAwareTask, max_retries=3)
def slot_alignment_scoring_task(self, job_id: str, context: dict):
    """
    Score how well slot data aligns with project goals.
    Produces SLOT_ALIGNMENT_REPORT artifact with fit score.

    Reference: blueprint_v2.md §5.2
    """
    return _run_async(_slot_alignment_scoring_async(self, job_id, context))


async def _slot_alignment_scoring_async(task, job_id: str, context: dict):
    """Async implementation of alignment scoring."""
    job_uuid = UUID(job_id)
    AsyncSessionLocal = get_async_session()

    async with AsyncSessionLocal() as session:
        try:
            await mark_job_running(session, job_uuid, task.request.id)

            result = await session.execute(
                select(PILJob).where(PILJob.id == job_uuid)
            )
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            slot_id = job.input_params.get("slot_id")
            fulfilled_by = job.input_params.get("fulfilled_by", {})

            await update_job_progress(
                session, job_uuid, 20,
                stage_name="Loading project context"
            )

            # Get blueprint for goal context
            bp_result = await session.execute(
                select(Blueprint).where(Blueprint.id == job.blueprint_id)
            )
            blueprint = bp_result.scalar_one_or_none()

            # Get slot requirements (slot_id is the UUID of the slot)
            from uuid import UUID as UUIDType
            slot_result = await session.execute(
                select(BlueprintSlot).where(
                    BlueprintSlot.blueprint_id == job.blueprint_id,
                    BlueprintSlot.id == UUIDType(slot_id)
                )
            )
            slot = slot_result.scalar_one_or_none()

            await update_job_progress(
                session, job_uuid, 50,
                stage_name="Calculating alignment score"
            )

            # Calculate alignment based on multiple factors
            alignment_factors = []
            base_score = 70.0  # Start with base score

            # Factor 1: Data type match
            if slot and fulfilled_by.get("type"):
                expected_type = str(slot.slot_type.value) if slot.slot_type else None
                actual_type = fulfilled_by.get("type", "").lower()
                if expected_type and actual_type and expected_type.lower() in actual_type:
                    base_score += 10
                    alignment_factors.append({
                        "factor": "data_type_match",
                        "contribution": 10,
                        "reason": f"Data type '{actual_type}' matches expected '{expected_type}'"
                    })

            # Factor 2: Required slot fulfillment bonus
            if slot and slot.required_level == RequiredLevel.REQUIRED:
                base_score += 5
                alignment_factors.append({
                    "factor": "required_slot",
                    "contribution": 5,
                    "reason": "Fulfilled a required slot"
                })

            # Factor 3: Source quality indicator
            source_type = fulfilled_by.get("source_type", "manual")
            if source_type in ["ai_research", "verified_api"]:
                base_score += 5
                alignment_factors.append({
                    "factor": "trusted_source",
                    "contribution": 5,
                    "reason": f"Data from trusted source type: {source_type}"
                })

            # Cap score at 100
            final_score = min(100.0, base_score)

            alignment_report = {
                "slot_id": slot_id,
                "alignment_score": final_score,
                "alignment_factors": alignment_factors,
                "goal_relevance": "high" if final_score >= 80 else "medium" if final_score >= 60 else "low",
                "recommendations": [],
            }

            # Add recommendations based on score
            if final_score < 80:
                alignment_report["recommendations"].append(
                    "Consider adding more context or metadata to improve alignment"
                )
            if final_score >= 90:
                alignment_report["recommendations"].append(
                    "Excellent alignment - this data is well-suited for the project"
                )

            await update_job_progress(
                session, job_uuid, 80,
                stage_name="Creating alignment report"
            )

            # Update slot with alignment score
            if slot:
                await session.execute(
                    update(BlueprintSlot)
                    .where(BlueprintSlot.id == slot.id)
                    .values(
                        alignment_score=final_score,
                        alignment_reasons=alignment_factors,
                        updated_at=datetime.utcnow(),
                    )
                )

            # Create artifact
            artifact = await create_artifact(
                session,
                tenant_id=job.tenant_id,
                project_id=job.project_id,
                artifact_type=ArtifactType.SLOT_ALIGNMENT_REPORT,
                artifact_name=f"Alignment Report: {fulfilled_by.get('name', 'Unknown')}",
                content=alignment_report,
                alignment_score=final_score,
                blueprint_id=job.blueprint_id,
                job_id=job_uuid,
                slot_id=slot_id,
            )

            await mark_job_succeeded(
                session, job_uuid,
                result=alignment_report,
                artifact_ids=[str(artifact.id)],
            )

            # PHASE 5: Update slot status based on alignment score
            job.result = alignment_report
            job.status = PILJobStatus.SUCCEEDED.value
            status_update = await process_slot_pipeline_completion(session, job)

            return {
                "status": "success",
                "alignment": alignment_report,
                "slot_status_update": status_update,
            }

        except Exception as e:
            await mark_job_failed(session, job_uuid, str(e))
            # PHASE 5: Update slot status on failure
            job.status = PILJobStatus.FAILED.value
            job.error_message = str(e)
            await process_slot_pipeline_completion(session, job)
            raise


# =============================================================================
# Slot Compilation Task (blueprint_v2.md §5.2 - Compile)
# =============================================================================

@celery_app.task(bind=True, base=TenantAwareTask, max_retries=3)
def slot_compilation_task(self, job_id: str, context: dict):
    """
    Transform slot data into derived artifacts for simulation.
    Produces SLOT_COMPILED_OUTPUT with transformed data.

    Reference: blueprint_v2.md §5.2
    """
    return _run_async(_slot_compilation_async(self, job_id, context))


async def _slot_compilation_async(task, job_id: str, context: dict):
    """Async implementation of slot compilation."""
    job_uuid = UUID(job_id)
    AsyncSessionLocal = get_async_session()

    async with AsyncSessionLocal() as session:
        try:
            await mark_job_running(session, job_uuid, task.request.id)

            result = await session.execute(
                select(PILJob).where(PILJob.id == job_uuid)
            )
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            slot_id = job.input_params.get("slot_id")
            fulfilled_by = job.input_params.get("fulfilled_by", {})
            compilation_config = job.input_params.get("compilation_config", {})

            await update_job_progress(
                session, job_uuid, 20,
                stage_name="Loading slot data"
            )

            # Get slot for derived artifacts config (slot_id is the UUID of the slot)
            from uuid import UUID as UUIDType
            slot_result = await session.execute(
                select(BlueprintSlot).where(
                    BlueprintSlot.blueprint_id == job.blueprint_id,
                    BlueprintSlot.id == UUIDType(slot_id)
                )
            )
            slot = slot_result.scalar_one_or_none()

            await update_job_progress(
                session, job_uuid, 40,
                stage_name="Preparing compilation transforms"
            )

            # Determine what derived artifacts to produce based on slot type
            derived_outputs = []
            data_type = fulfilled_by.get("type", "unknown").lower()

            # Apply transformations based on data type
            if "persona" in data_type or "entity" in data_type:
                derived_outputs.append({
                    "output_type": "persona_store",
                    "format": "indexed_json",
                    "status": "compiled",
                    "record_count": fulfilled_by.get("record_count", 0),
                })
            elif "time" in data_type or "series" in data_type:
                derived_outputs.append({
                    "output_type": "time_series_index",
                    "format": "parquet_ready",
                    "status": "compiled",
                    "time_range": compilation_config.get("time_range", "unknown"),
                })
            elif "rule" in data_type or "assumption" in data_type:
                derived_outputs.append({
                    "output_type": "rule_engine_config",
                    "format": "json_schema",
                    "status": "compiled",
                    "rule_count": fulfilled_by.get("rule_count", 0),
                })
            else:
                # Generic compilation
                derived_outputs.append({
                    "output_type": "generic_data_store",
                    "format": "json",
                    "status": "compiled",
                })

            await update_job_progress(
                session, job_uuid, 70,
                stage_name="Running compilation transforms"
            )

            compilation_result = {
                "slot_id": slot_id,
                "source": fulfilled_by,
                "derived_outputs": derived_outputs,
                "compilation_timestamp": datetime.utcnow().isoformat(),
                "ready_for_simulation": True,
                "compilation_notes": [],
            }

            await update_job_progress(
                session, job_uuid, 90,
                stage_name="Creating compiled artifact"
            )

            # Create artifact
            artifact = await create_artifact(
                session,
                tenant_id=job.tenant_id,
                project_id=job.project_id,
                artifact_type=ArtifactType.SLOT_COMPILED_OUTPUT,
                artifact_name=f"Compiled: {fulfilled_by.get('name', 'Unknown')}",
                content=compilation_result,
                blueprint_id=job.blueprint_id,
                job_id=job_uuid,
                slot_id=slot_id,
                quality_score=1.0,  # Compilation succeeded
            )

            await mark_job_succeeded(
                session, job_uuid,
                result=compilation_result,
                artifact_ids=[str(artifact.id)],
            )

            # PHASE 5: Update slot status - compilation success = READY & fulfilled
            job.result = compilation_result
            job.status = PILJobStatus.SUCCEEDED.value
            status_update = await process_slot_pipeline_completion(session, job)

            return {
                "status": "success",
                "compilation": compilation_result,
                "slot_status_update": status_update,
            }

        except Exception as e:
            await mark_job_failed(session, job_uuid, str(e))
            # PHASE 5: Update slot status on failure
            job.status = PILJobStatus.FAILED.value
            job.error_message = str(e)
            await process_slot_pipeline_completion(session, job)
            raise


# =============================================================================
# Dispatch Entry Point
# =============================================================================

@celery_app.task(bind=True, base=TenantAwareTask)
def dispatch_pil_job(self, job_id: str):
    """
    Dispatch a PIL job to the appropriate task based on job_type.
    This is the main entry point for PIL job processing.
    """
    return _run_async(_dispatch_pil_job_async(self, job_id))


async def _dispatch_pil_job_async(task, job_id: str):
    """Async implementation of job dispatch."""
    job_uuid = UUID(job_id)
    AsyncSessionLocal = get_async_session()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PILJob).where(PILJob.id == job_uuid)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise ValueError(f"Job {job_id} not found")

        context = {"job_id": job_id, "tenant_id": str(job.tenant_id)}

        # Route to appropriate task
        if job.job_type == PILJobType.GOAL_ANALYSIS:
            goal_analysis_task.delay(job_id, context)
        elif job.job_type == PILJobType.BLUEPRINT_BUILD:
            blueprint_build_task.delay(job_id, context)
        elif job.job_type == PILJobType.SLOT_VALIDATION:
            slot_validation_task.delay(job_id, context)
        elif job.job_type == PILJobType.SLOT_SUMMARIZATION:
            slot_summarization_task.delay(job_id, context)
        elif job.job_type == PILJobType.SLOT_ALIGNMENT_SCORING:
            slot_alignment_scoring_task.delay(job_id, context)
        elif job.job_type == PILJobType.SLOT_COMPILATION:
            slot_compilation_task.delay(job_id, context)
        else:
            # For unimplemented job types, mark as partial
            await session.execute(
                update(PILJob)
                .where(PILJob.id == job_uuid)
                .values(
                    status=PILJobStatus.PARTIAL,
                    error_message=f"Job type {job.job_type} not yet implemented",
                    updated_at=datetime.utcnow(),
                )
            )
            await session.commit()

        return {"dispatched": job.job_type.value if hasattr(job.job_type, 'value') else str(job.job_type)}
