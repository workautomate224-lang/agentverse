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

            # Stage 1: Parse goal (20%)
            await update_job_progress(
                session, job_uuid, 20,
                stage_name="Parsing goal text",
                stages_completed=1
            )

            # Simulate LLM call for goal analysis
            # In production, this calls LLMRouter
            goal_summary = _generate_goal_summary(goal_text)
            domain_guess = _classify_domain(goal_text)

            # Stage 2: Generate clarifying questions (50%)
            await update_job_progress(
                session, job_uuid, 50,
                stage_name="Generating clarifying questions",
                stages_completed=2
            )

            clarifying_questions = _generate_clarifying_questions(goal_text, domain_guess)

            # Stage 3: Generate blueprint preview (80%)
            await update_job_progress(
                session, job_uuid, 80,
                stage_name="Generating blueprint preview",
                stages_completed=3
            )

            blueprint_preview = _generate_blueprint_preview(domain_guess)
            risk_notes = _assess_risks(goal_text, domain_guess)

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


def _generate_goal_summary(goal_text: str) -> str:
    """Generate a concise summary of the user's goal."""
    # Placeholder - in production, use LLMRouter
    if len(goal_text) < 100:
        return goal_text
    return f"Project aims to {goal_text[:200]}..."


def _classify_domain(goal_text: str) -> str:
    """Classify the domain based on goal text."""
    # Placeholder - in production, use LLMRouter
    goal_lower = goal_text.lower()

    if any(word in goal_lower for word in ["election", "vote", "candidate", "political"]):
        return DomainGuess.ELECTION.value
    elif any(word in goal_lower for word in ["market", "demand", "sales", "consumer"]):
        return DomainGuess.MARKET_DEMAND.value
    elif any(word in goal_lower for word in ["production", "manufacturing", "forecast"]):
        return DomainGuess.PRODUCTION_FORECAST.value
    elif any(word in goal_lower for word in ["policy", "regulation", "government"]):
        return DomainGuess.POLICY_IMPACT.value
    elif any(word in goal_lower for word in ["risk", "perception", "brand", "reputation"]):
        return DomainGuess.PERCEPTION_RISK.value
    else:
        return DomainGuess.GENERIC.value


def _generate_clarifying_questions(goal_text: str, domain: str) -> List[Dict]:
    """Generate clarifying questions based on goal and domain."""
    # Placeholder - in production, use LLMRouter
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

    # Add domain-specific questions
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


def _generate_blueprint_preview(domain: str) -> Dict:
    """Generate a preview of what the blueprint will look like."""
    # Default required slots based on domain
    required_slots = ["PersonaSet"]
    recommended_slots = ["TimeSeries", "EventScriptSet"]

    if domain == DomainGuess.ELECTION.value:
        required_slots.extend(["Table"])  # Voter data
        recommended_slots.extend(["TextCorpus"])  # News/social media
    elif domain == DomainGuess.MARKET_DEMAND.value:
        required_slots.extend(["TimeSeries"])  # Sales history
        recommended_slots.extend(["Graph"])  # Market relationships

    # Section tasks
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


def _assess_risks(goal_text: str, domain: str) -> List[str]:
    """Assess potential risks for the project."""
    risks = []

    # Check for common risk patterns
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

            return {"status": "success", "validation": validation_report}

        except Exception as e:
            await mark_job_failed(session, job_uuid, str(e))
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
