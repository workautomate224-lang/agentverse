"""
Focus Group API Endpoints
Virtual focus group interviews with LLM-powered AI agents.
"""

import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.focus_group import (
    FocusGroupSessionCreate,
    FocusGroupSessionUpdate,
    FocusGroupSessionResponse,
    FocusGroupSessionListResponse,
    FocusGroupMessageResponse,
    InterviewRequest,
    InterviewResponse,
    GroupDiscussionRequest,
    GroupDiscussionResponse,
    SessionSummaryRequest,
    SessionSummaryResponse,
    AvailableAgentResponse,
)
from app.services.focus_group import FocusGroupService

router = APIRouter()


# ============= Session Endpoints =============

@router.post("/sessions", response_model=FocusGroupSessionResponse)
async def create_session(
    data: FocusGroupSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new focus group session.

    Select agents from a product run to interview in this session.
    """
    service = FocusGroupService(db, current_user.id)

    session = await service.create_session(
        product_id=data.product_id,
        name=data.name,
        agent_ids=data.agent_ids,
        run_id=data.run_id,
        session_type=data.session_type,
        topic=data.topic,
        objectives=data.objectives,
        discussion_guide=data.discussion_guide,
        model_preset=data.model_preset,
        temperature=data.temperature,
        moderator_style=data.moderator_style,
    )

    return session


@router.get("/sessions", response_model=List[FocusGroupSessionListResponse])
async def list_sessions(
    product_id: Optional[UUID] = Query(None, description="Filter by product ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List focus group sessions."""
    service = FocusGroupService(db, current_user.id)

    sessions = await service.list_sessions(
        product_id=product_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    return [
        FocusGroupSessionListResponse(
            id=s.id,
            name=s.name,
            session_type=s.session_type,
            agent_count=len(s.agent_ids),
            message_count=s.message_count,
            status=s.status,
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=FocusGroupSessionResponse)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a focus group session by ID."""
    service = FocusGroupService(db, current_user.id)

    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.patch("/sessions/{session_id}", response_model=FocusGroupSessionResponse)
async def update_session(
    session_id: UUID,
    data: FocusGroupSessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a focus group session."""
    service = FocusGroupService(db, current_user.id)

    session = await service.update_session(
        session_id,
        **data.model_dump(exclude_unset=True),
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.post("/sessions/{session_id}/end", response_model=FocusGroupSessionResponse)
async def end_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    End a focus group session.

    Generates a summary and marks the session as completed.
    """
    service = FocusGroupService(db, current_user.id)

    session = await service.end_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


# ============= Interview Endpoints =============

@router.post("/sessions/{session_id}/interview", response_model=InterviewResponse)
async def interview_agent(
    session_id: UUID,
    request: InterviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a question to an agent and get a response.

    For individual interviews or targeted questions.
    """
    service = FocusGroupService(db, current_user.id)

    # Get first target agent if specified
    target_agent = request.target_agent_ids[0] if request.target_agent_ids else None

    try:
        response = await service.interview_agent(
            session_id=session_id,
            question=request.question,
            target_agent_id=target_agent,
            context=request.context,
        )

        return InterviewResponse(**response)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/interview/stream")
async def interview_agent_stream(
    session_id: UUID,
    request: InterviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream an interview response from an agent.

    Returns Server-Sent Events (SSE) with response chunks.
    """
    service = FocusGroupService(db, current_user.id)

    # Verify session exists
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    target_agent = request.target_agent_ids[0] if request.target_agent_ids else None

    async def generate_stream():
        try:
            async for chunk in service.interview_agent_stream(
                session_id=session_id,
                question=request.question,
                target_agent_id=target_agent,
                context=request.context,
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============= Group Discussion Endpoints =============

@router.post("/sessions/{session_id}/discuss", response_model=GroupDiscussionResponse)
async def group_discussion(
    session_id: UUID,
    request: GroupDiscussionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start a group discussion with multiple agents.

    Agents will respond to each other over multiple turns.
    """
    service = FocusGroupService(db, current_user.id)

    try:
        result = await service.group_discussion(
            session_id=session_id,
            topic=request.topic,
            initial_question=request.initial_question,
            max_turns=request.max_turns,
            agent_ids=request.agent_ids,
        )

        return GroupDiscussionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============= Message History Endpoints =============

@router.get("/sessions/{session_id}/messages", response_model=List[FocusGroupMessageResponse])
async def get_session_messages(
    session_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all messages in a focus group session."""
    service = FocusGroupService(db, current_user.id)

    # Verify session exists
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await service.get_messages(
        session_id=session_id,
        limit=limit,
        offset=offset,
    )

    return messages


# ============= Summary Endpoints =============

@router.post("/sessions/{session_id}/summary", response_model=SessionSummaryResponse)
async def generate_session_summary(
    session_id: UUID,
    request: SessionSummaryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a summary of a focus group session.

    Includes key insights, themes, and notable quotes.
    """
    service = FocusGroupService(db, current_user.id)

    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    summary = await service._generate_session_summary(session)

    # Calculate duration if session ended
    duration_minutes = None
    if session.ended_at and session.created_at:
        delta = session.ended_at - session.created_at
        duration_minutes = delta.total_seconds() / 60

    return SessionSummaryResponse(
        session_id=session.id,
        session_name=session.name,
        agent_count=len(session.agent_ids),
        message_count=session.message_count,
        duration_minutes=duration_minutes,
        key_insights=summary.get("key_points", []),
        key_themes=summary.get("key_themes", []),
        notable_quotes=summary.get("notable_quotes", []),
        sentiment_trajectory=session.sentiment_trajectory or [],
        recommendations=[],  # Could be generated by LLM
        executive_summary=summary.get("executive_summary", ""),
    )


# ============= Agent Selection Endpoints =============

@router.get("/products/{product_id}/available-agents", response_model=List[AvailableAgentResponse])
async def get_available_agents(
    product_id: UUID,
    run_id: Optional[UUID] = Query(None, description="Filter by specific run"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get available agents from a product that can be interviewed.

    Returns agents from completed product runs.
    """
    service = FocusGroupService(db, current_user.id)

    agents = await service.get_available_agents(
        product_id=product_id,
        run_id=run_id,
    )

    return [AvailableAgentResponse(**a) for a in agents]
