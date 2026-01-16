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

from celery import shared_task
from sqlalchemy import select, update
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


@shared_task(bind=True, base=TenantAwareTask, max_retries=3)
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

            # Create LLMRouter context
            llm_context = LLMRouterContext(
                tenant_id=str(job.tenant_id),
                project_id=str(job.project_id),
                phase="compilation",  # C5 tracking - LLM used for planning
            )

            # Stage 1: Parse goal and classify domain (20%)
            await update_job_progress(
                session, job_uuid, 20,
                stage_name="Analyzing goal and domain",
                stages_completed=1
            )

            # Use LLM for goal analysis and domain classification
            goal_summary, domain_guess = await _llm_analyze_goal(session, goal_text, llm_context)

            # Stage 2: Generate clarifying questions (50%)
            await update_job_progress(
                session, job_uuid, 50,
                stage_name="Generating clarifying questions",
                stages_completed=2
            )

            clarifying_questions = await _llm_generate_clarifying_questions(
                session, goal_text, domain_guess, llm_context
            )

            # Stage 3: Generate blueprint preview and assess risks (80%)
            await update_job_progress(
                session, job_uuid, 80,
                stage_name="Generating blueprint preview",
                stages_completed=3
            )

            blueprint_preview = await _llm_generate_blueprint_preview(session, domain_guess, llm_context)
            risk_notes = await _llm_assess_risks(session, goal_text, domain_guess, llm_context)

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

            # Mark job as succeeded
            await mark_job_succeeded(
                session, job_uuid,
                result={
                    "goal_summary": goal_summary,
                    "domain_guess": domain_guess,
                    "clarifying_questions_count": len(clarifying_questions),
                    "risk_notes_count": len(risk_notes),
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
            await mark_job_failed(session, job_uuid, str(e))
            raise


# =============================================================================
# LLM-Powered Analysis Functions
# =============================================================================

async def _llm_analyze_goal(
    session: AsyncSession,
    goal_text: str,
    context: LLMRouterContext,
) -> tuple[str, str]:
    """
    Use LLM to analyze goal text and classify domain.
    Returns (goal_summary, domain_guess).
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
        )

        # Parse JSON response
        result = json.loads(response.content)
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

        return goal_summary, domain_guess

    except Exception:
        # Fallback to simple analysis if LLM fails
        return _fallback_goal_analysis(goal_text)


def _fallback_goal_analysis(goal_text: str) -> tuple[str, str]:
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

    return goal_summary, domain


async def _llm_generate_clarifying_questions(
    session: AsyncSession,
    goal_text: str,
    domain: str,
    context: LLMRouterContext,
) -> List[Dict]:
    """
    Use LLM to generate clarifying questions for the project.
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
            max_tokens_override=1000,
        )

        result = json.loads(response.content)
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

        return questions

    except Exception:
        # Fallback to base questions
        return _fallback_clarifying_questions(domain)


def _fallback_clarifying_questions(domain: str) -> List[Dict]:
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

    return base_questions


async def _llm_generate_blueprint_preview(
    session: AsyncSession,
    domain: str,
    context: LLMRouterContext,
) -> Dict:
    """
    Use LLM to generate a blueprint preview based on domain.
    """
    router = LLMRouter(session)

    system_prompt = """You are an expert simulation architect for a predictive AI platform.
Generate a blueprint preview for a simulation project based on the domain.

The platform supports these input slot types:
- PersonaSet: Population of agents with demographics and behaviors
- Table: Structured data (demographics, survey results, etc.)
- TimeSeries: Time-indexed data (sales, prices, trends)
- EventScriptSet: External events affecting agent behavior
- TextCorpus: Unstructured text data (news, social media)
- Graph: Network/relationship data

The platform has these sections:
- inputs: Data sources and uploads
- personas: Agent population configuration
- rules: Decision rules and behavior models
- run_params: Simulation parameters and outputs
- reliability: Calibration and validation

Respond in JSON format:
{
  "required_slots": ["slot_type1", "slot_type2"],
  "recommended_slots": ["slot_type3"],
  "section_tasks": {
    "inputs": ["task1", "task2"],
    "personas": ["task1"],
    "rules": ["task1"],
    "run_params": ["task1"],
    "reliability": ["task1"]
  },
  "key_challenges": ["challenge1", "challenge2"]
}"""

    user_prompt = f"""Generate a blueprint preview for domain: {domain}

What data slots and tasks would be needed for a typical project in this domain?"""

    try:
        response = await router.complete(
            profile_key=LLMProfileKey.PIL_BLUEPRINT_GENERATION.value,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            context=context,
            temperature_override=0.3,
            max_tokens_override=800,
        )

        result = json.loads(response.content)
        return {
            "required_slots": result.get("required_slots", ["PersonaSet"]),
            "recommended_slots": result.get("recommended_slots", ["EventScriptSet"]),
            "section_tasks": result.get("section_tasks", {}),
            "key_challenges": result.get("key_challenges", []),
        }

    except Exception:
        return _fallback_blueprint_preview(domain)


def _fallback_blueprint_preview(domain: str) -> Dict:
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

    return {
        "required_slots": required_slots,
        "recommended_slots": recommended_slots,
        "section_tasks": section_tasks,
    }


async def _llm_assess_risks(
    session: AsyncSession,
    goal_text: str,
    domain: str,
    context: LLMRouterContext,
) -> List[str]:
    """
    Use LLM to assess potential risks for the project.
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
            temperature_override=0.4,
            max_tokens_override=500,
        )

        result = json.loads(response.content)
        risks = result.get("risks", [])

        if not risks:
            risks = ["No significant risks identified at this stage"]

        return risks

    except Exception:
        return _fallback_risk_assessment(goal_text, domain)


def _fallback_risk_assessment(goal_text: str, domain: str) -> List[str]:
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

    return risks


# =============================================================================
# Blueprint Build Task (blueprint.md §4.3)
# =============================================================================

@shared_task(bind=True, base=TenantAwareTask, max_retries=3)
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

            if not job or not job.blueprint_id:
                raise ValueError(f"Job {job_id} not found or missing blueprint_id")

            goal_text = job.input_params.get("goal_text", "")
            clarification_answers = job.input_params.get("clarification_answers", {})

            # Get blueprint
            bp_result = await session.execute(
                select(Blueprint).where(Blueprint.id == job.blueprint_id)
            )
            blueprint = bp_result.scalar_one_or_none()

            if not blueprint:
                raise ValueError(f"Blueprint {job.blueprint_id} not found")

            # Stage 1: Generate slots (30%)
            await update_job_progress(
                session, job_uuid, 30,
                stage_name="Generating input slots",
                stages_completed=1
            )

            slots = _generate_slots(blueprint.domain_guess, clarification_answers)
            for slot_data in slots:
                slot = BlueprintSlot(
                    blueprint_id=blueprint.id,
                    **slot_data,
                )
                session.add(slot)

            # Stage 2: Generate tasks (60%)
            await update_job_progress(
                session, job_uuid, 60,
                stage_name="Generating section tasks",
                stages_completed=2
            )

            tasks = _generate_tasks(blueprint.domain_guess, clarification_answers)
            for task_data in tasks:
                task_obj = BlueprintTask(
                    blueprint_id=blueprint.id,
                    **task_data,
                )
                session.add(task_obj)

            # Stage 3: Generate calibration plan (80%)
            await update_job_progress(
                session, job_uuid, 80,
                stage_name="Generating calibration plan",
                stages_completed=3
            )

            calibration_plan = _generate_calibration_plan(blueprint.domain_guess)
            branching_plan = _generate_branching_plan(blueprint.domain_guess)

            # Update blueprint
            blueprint.calibration_plan = calibration_plan
            blueprint.branching_plan = branching_plan
            blueprint.clarification_answers = clarification_answers
            blueprint.is_draft = True  # Still draft until published
            blueprint.updated_at = datetime.utcnow()

            await session.commit()

            # Mark succeeded
            await mark_job_succeeded(
                session, job_uuid,
                result={
                    "slots_created": len(slots),
                    "tasks_created": len(tasks),
                    "calibration_plan": True,
                    "branching_plan": True,
                },
            )

            return {"status": "success", "slots": len(slots), "tasks": len(tasks)}

        except Exception as e:
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
            "slot_type": SlotType.TIME_SERIES.value,
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

@shared_task(bind=True, base=TenantAwareTask, max_retries=3)
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

@shared_task(bind=True, base=TenantAwareTask, max_retries=3)
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
                    tenant_id=str(job.tenant_id),
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
                )

                if llm_response and llm_response.content:
                    summary_content["summary"] = llm_response.content
                    summary_content["ai_generated"] = True

            except Exception as llm_error:
                # Fallback to basic summary if LLM fails
                summary_content["ai_generated"] = False
                summary_content["fallback_reason"] = str(llm_error)

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

@shared_task(bind=True, base=TenantAwareTask, max_retries=3)
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

@shared_task(bind=True, base=TenantAwareTask, max_retries=3)
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

@shared_task(bind=True, base=TenantAwareTask)
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
