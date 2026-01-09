"""
Simulation Execution Endpoints
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.simulation import AgentResponse, Project, Scenario, SimulationRun
from app.models.user import User
from app.schemas.simulation import (
    AgentInterviewRequest,
    AgentInterviewResponse,
    AgentResponseSchema,
    SimulationProgress,
    SimulationRunCreate,
    SimulationRunResponse,
)

router = APIRouter()


async def verify_scenario_access(
    scenario_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> Scenario:
    """Verify user has access to the scenario."""
    result = await db.execute(
        select(Scenario)
        .join(Project)
        .where(
            Scenario.id == scenario_id,
            Project.user_id == user_id,
        )
    )
    scenario = result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    return scenario


@router.get("/", response_model=list[SimulationRunResponse])
async def list_simulations(
    scenario_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(
        None, pattern="^(pending|running|completed|failed)$"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SimulationRun]:
    """
    List simulation runs.
    """
    query = select(SimulationRun).where(SimulationRun.user_id == current_user.id)

    if scenario_id:
        query = query.where(SimulationRun.scenario_id == scenario_id)

    if status_filter:
        query = query.where(SimulationRun.status == status_filter)

    query = query.offset(skip).limit(limit).order_by(SimulationRun.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=SimulationRunResponse, status_code=status.HTTP_201_CREATED)
async def create_simulation(
    simulation_in: SimulationRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SimulationRun:
    """
    Start a new simulation run.
    """
    # Verify scenario access and status
    scenario = await verify_scenario_access(simulation_in.scenario_id, current_user.id, db)

    if scenario.status not in ["ready", "completed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scenario must be 'ready' to run. Current status: {scenario.status}",
        )

    # Check for running simulations on same scenario
    running_result = await db.execute(
        select(SimulationRun).where(
            SimulationRun.scenario_id == simulation_in.scenario_id,
            SimulationRun.status == "running",
        )
    )
    if running_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A simulation is already running for this scenario",
        )

    # Create simulation run
    simulation = SimulationRun(
        scenario_id=simulation_in.scenario_id,
        user_id=current_user.id,
        run_config=simulation_in.run_config,
        model_used=simulation_in.model_used,
        agent_count=simulation_in.agent_count,
        status="pending",
    )

    db.add(simulation)
    await db.flush()
    await db.refresh(simulation)

    # Update scenario status
    scenario.status = "running"
    await db.flush()

    # Queue the simulation task (would be Celery in production)
    # background_tasks.add_task(run_simulation_task, str(simulation.id))

    return simulation


@router.get("/{run_id}", response_model=SimulationRunResponse)
async def get_simulation(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SimulationRun:
    """
    Get simulation run by ID.
    """
    result = await db.execute(
        select(SimulationRun).where(
            SimulationRun.id == run_id,
            SimulationRun.user_id == current_user.id,
        )
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )

    return simulation


@router.post("/{run_id}/run")
async def run_simulation(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SimulationRunResponse:
    """
    Execute a pending simulation run.
    """
    from app.services.simulation import SimulationService

    result = await db.execute(
        select(SimulationRun)
        .options(selectinload(SimulationRun.scenario))
        .where(
            SimulationRun.id == run_id,
            SimulationRun.user_id == current_user.id,
        )
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )

    if simulation.status not in ["pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Simulation must be 'pending' to run. Current status: {simulation.status}",
        )

    # Get the scenario
    scenario_result = await db.execute(
        select(Scenario).where(Scenario.id == simulation.scenario_id)
    )
    scenario = scenario_result.scalar_one_or_none()

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    # Run the simulation
    service = SimulationService()
    try:
        await service.run_simulation(scenario, simulation, db)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}",
        )

    # Refresh and return
    await db.refresh(simulation)
    return simulation


@router.get("/{run_id}/stream")
async def stream_simulation(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream simulation progress using Server-Sent Events.
    """
    result = await db.execute(
        select(SimulationRun).where(
            SimulationRun.id == run_id,
            SimulationRun.user_id == current_user.id,
        )
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )

    async def event_generator():
        """Generate SSE events for simulation progress."""
        import asyncio
        import json

        while True:
            # Refresh simulation status
            await db.refresh(simulation)

            progress_data = {
                "run_id": str(simulation.id),
                "status": simulation.status,
                "progress": simulation.progress,
                "agents_completed": int(simulation.progress * simulation.agent_count / 100),
                "agents_total": simulation.agent_count,
            }

            yield f"data: {json.dumps(progress_data)}\n\n"

            if simulation.status in ["completed", "failed"]:
                # Send final results
                if simulation.results_summary:
                    yield f"data: {json.dumps({'type': 'results', 'data': simulation.results_summary})}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/{run_id}/cancel")
async def cancel_simulation(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Cancel a running simulation.
    """
    result = await db.execute(
        select(SimulationRun).where(
            SimulationRun.id == run_id,
            SimulationRun.user_id == current_user.id,
        )
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )

    if simulation.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel simulation with status: {simulation.status}",
        )

    simulation.status = "failed"
    simulation.completed_at = datetime.utcnow()

    # Update scenario status
    scenario_result = await db.execute(
        select(Scenario).where(Scenario.id == simulation.scenario_id)
    )
    scenario = scenario_result.scalar_one_or_none()
    if scenario:
        scenario.status = "ready"

    await db.flush()

    return {"message": "Simulation cancelled", "run_id": str(run_id)}


@router.get("/{run_id}/agents", response_model=list[AgentResponseSchema])
async def get_agent_responses(
    run_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    question_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AgentResponse]:
    """
    Get agent responses for a simulation run.
    """
    # Verify access
    run_result = await db.execute(
        select(SimulationRun).where(
            SimulationRun.id == run_id,
            SimulationRun.user_id == current_user.id,
        )
    )
    if not run_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )

    query = select(AgentResponse).where(AgentResponse.run_id == run_id)

    if question_id:
        query = query.where(AgentResponse.question_id == question_id)

    query = query.offset(skip).limit(limit).order_by(AgentResponse.agent_index)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{run_id}/results")
async def get_simulation_results(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get aggregated results for a completed simulation.
    """
    result = await db.execute(
        select(SimulationRun).where(
            SimulationRun.id == run_id,
            SimulationRun.user_id == current_user.id,
        )
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )

    if simulation.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Simulation not completed. Status: {simulation.status}",
        )

    return {
        "run_id": str(simulation.id),
        "scenario_id": str(simulation.scenario_id),
        "status": simulation.status,
        "agent_count": simulation.agent_count,
        "model_used": simulation.model_used,
        "results_summary": simulation.results_summary,
        "confidence_score": simulation.confidence_score,
        "tokens_used": simulation.tokens_used,
        "cost_usd": simulation.cost_usd,
        "started_at": simulation.started_at.isoformat() if simulation.started_at else None,
        "completed_at": simulation.completed_at.isoformat() if simulation.completed_at else None,
        "duration_seconds": (
            (simulation.completed_at - simulation.started_at).total_seconds()
            if simulation.started_at and simulation.completed_at
            else None
        ),
    }


@router.get("/{run_id}/export")
async def export_simulation(
    run_id: UUID,
    format: str = Query("csv", pattern="^(csv|json|xlsx)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Export simulation results.
    """
    result = await db.execute(
        select(SimulationRun).where(
            SimulationRun.id == run_id,
            SimulationRun.user_id == current_user.id,
        )
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )

    if simulation.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only export completed simulations",
        )

    # Get all agent responses
    responses_result = await db.execute(
        select(AgentResponse)
        .where(AgentResponse.run_id == run_id)
        .order_by(AgentResponse.agent_index)
    )
    responses = responses_result.scalars().all()

    if format == "json":
        import json
        from fastapi.responses import Response

        export_data = {
            "simulation_id": str(simulation.id),
            "scenario_id": str(simulation.scenario_id),
            "status": simulation.status,
            "agent_count": simulation.agent_count,
            "model_used": simulation.model_used,
            "results_summary": simulation.results_summary,
            "confidence_score": simulation.confidence_score,
            "tokens_used": simulation.tokens_used,
            "cost_usd": float(simulation.cost_usd) if simulation.cost_usd else 0,
            "created_at": simulation.created_at.isoformat() if simulation.created_at else None,
            "completed_at": simulation.completed_at.isoformat() if simulation.completed_at else None,
            "responses": [
                {
                    "agent_index": r.agent_index,
                    "persona": r.persona,
                    "response": r.response,
                    "reasoning": r.reasoning,
                    "tokens_used": r.tokens_used,
                    "response_time_ms": r.response_time_ms,
                }
                for r in responses
            ]
        }

        return Response(
            content=json.dumps(export_data, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="simulation_{run_id}.json"'
            }
        )

    elif format == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            "agent_index",
            "answer",
            "reasoning",
            "age",
            "gender",
            "education",
            "income_bracket",
            "tokens_used",
            "response_time_ms",
        ])

        # Data rows
        for r in responses:
            persona = r.persona or {}
            demographics = persona.get("demographics", {})
            response_data = r.response or {}

            writer.writerow([
                r.agent_index,
                response_data.get("answer", response_data.get("raw", "")),
                r.reasoning or "",
                demographics.get("age", ""),
                demographics.get("gender", ""),
                demographics.get("education", ""),
                demographics.get("income_bracket", ""),
                r.tokens_used,
                r.response_time_ms,
            ])

        from fastapi.responses import Response
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="simulation_{run_id}.csv"'
            }
        )

    else:
        # xlsx would require openpyxl library
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="XLSX export not yet implemented. Use CSV or JSON.",
        )


@router.post("/{run_id}/interview", response_model=list[AgentInterviewResponse])
async def interview_agents(
    run_id: UUID,
    interview_request: AgentInterviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """
    Interview specific agents from a completed simulation (Virtual Focus Group).
    """
    # Verify simulation access
    run_result = await db.execute(
        select(SimulationRun).where(
            SimulationRun.id == run_id,
            SimulationRun.user_id == current_user.id,
        )
    )
    simulation = run_result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )

    if simulation.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only interview agents from completed simulations",
        )

    # Get selected agent responses
    agents_result = await db.execute(
        select(AgentResponse).where(
            AgentResponse.run_id == run_id,
            AgentResponse.id.in_(interview_request.agent_ids),
        )
    )
    agents = agents_result.scalars().all()

    if len(agents) != len(interview_request.agent_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some agent IDs not found",
        )

    # In production, this would call OpenRouter to generate interview responses
    # For now, return placeholder responses
    responses = []
    for agent in agents:
        responses.append({
            "agent_id": str(agent.id),
            "persona": agent.persona,
            "response": f"[Simulated interview response for question: {interview_request.question}]",
            "reasoning": "Based on my demographic profile and previous responses...",
        })

    return responses


@router.get("/stats/overview")
async def get_simulation_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get overall simulation statistics for current user.
    """
    # Total runs
    total_result = await db.execute(
        select(func.count(SimulationRun.id)).where(
            SimulationRun.user_id == current_user.id
        )
    )
    total_runs = total_result.scalar()

    # Completed runs
    completed_result = await db.execute(
        select(func.count(SimulationRun.id)).where(
            SimulationRun.user_id == current_user.id,
            SimulationRun.status == "completed",
        )
    )
    completed_runs = completed_result.scalar()

    # Total agents simulated
    agents_result = await db.execute(
        select(func.sum(SimulationRun.agent_count)).where(
            SimulationRun.user_id == current_user.id,
            SimulationRun.status == "completed",
        )
    )
    total_agents = agents_result.scalar() or 0

    # Total cost
    cost_result = await db.execute(
        select(func.sum(SimulationRun.cost_usd)).where(
            SimulationRun.user_id == current_user.id
        )
    )
    total_cost = cost_result.scalar() or 0.0

    # Total tokens
    tokens_result = await db.execute(
        select(func.sum(SimulationRun.tokens_used)).where(
            SimulationRun.user_id == current_user.id
        )
    )
    total_tokens = tokens_result.scalar() or 0

    return {
        "total_runs": total_runs,
        "completed_runs": completed_runs,
        "total_agents_simulated": total_agents,
        "total_cost_usd": round(total_cost, 4),
        "total_tokens_used": total_tokens,
    }
