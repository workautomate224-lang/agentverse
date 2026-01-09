"""
Vi World API Endpoints
Endpoints for managing persistent world states and simulations.
"""

import random
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.world import WorldState, WorldEvent, WorldStatus
from app.models.persona import PersonaTemplate, PersonaRecord
from app.schemas.world import (
    WorldStateCreate,
    WorldStateUpdate,
    WorldStateResponse,
    WorldStateListResponse,
    NPCStatesUpdateSchema,
    ChatHistoryResponse,
    ChatMessageSchema,
    WorldStatsResponse,
    SimulationControlSchema,
    TickUpdateSchema,
)

router = APIRouter()


# ============= World State CRUD =============

@router.post("/", response_model=WorldStateResponse, status_code=status.HTTP_201_CREATED)
async def create_world(
    world_in: WorldStateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorldState:
    """
    Create a new world state for a persona template.
    """
    # Verify template ownership
    result = await db.execute(
        select(PersonaTemplate).where(
            PersonaTemplate.id == world_in.template_id,
            PersonaTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona template not found",
        )

    # Check if world already exists for this template
    existing = await db.execute(
        select(WorldState).where(WorldState.template_id == world_in.template_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="World already exists for this template",
        )

    # Generate seed if not provided
    seed = world_in.seed if world_in.seed is not None else random.randint(1, 2**31 - 1)

    # Create world state
    world = WorldState(
        template_id=world_in.template_id,
        seed=seed,
        world_width=world_in.world_width,
        world_height=world_in.world_height,
        tile_size=world_in.tile_size,
        simulation_speed=world_in.simulation_speed,
        is_continuous=world_in.is_continuous,
        status=WorldStatus.INACTIVE.value,
        npc_states={},
        chat_history=[],
    )

    db.add(world)
    await db.flush()
    await db.refresh(world)

    return world


@router.get("/", response_model=list[WorldStateListResponse])
async def list_worlds(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, pattern="^(inactive|running|paused|initializing)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorldState]:
    """
    List all worlds for the current user's templates.
    """
    # Get user's template IDs
    template_query = select(PersonaTemplate.id).where(
        PersonaTemplate.user_id == current_user.id
    )
    template_result = await db.execute(template_query)
    template_ids = [row[0] for row in template_result.fetchall()]

    if not template_ids:
        return []

    # Query worlds
    query = select(WorldState).where(WorldState.template_id.in_(template_ids))

    if status_filter:
        query = query.where(WorldState.status == status_filter)

    query = query.offset(skip).limit(limit).order_by(WorldState.updated_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/by-template/{template_id}", response_model=WorldStateResponse)
async def get_world_by_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorldState:
    """
    Get world state by template ID.
    """
    # Verify template ownership
    result = await db.execute(
        select(PersonaTemplate).where(
            PersonaTemplate.id == template_id,
            PersonaTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona template not found",
        )

    # Get world
    result = await db.execute(
        select(WorldState).where(WorldState.template_id == template_id)
    )
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World not found for this template",
        )

    return world


@router.get("/{world_id}", response_model=WorldStateResponse)
async def get_world(
    world_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorldState:
    """
    Get world state by ID.
    """
    # Get world with template for ownership check
    result = await db.execute(
        select(WorldState)
        .where(WorldState.id == world_id)
        .options(selectinload(WorldState.template))
    )
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World not found",
        )

    # Verify ownership
    if world.template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this world",
        )

    return world


@router.put("/{world_id}", response_model=WorldStateResponse)
async def update_world(
    world_id: UUID,
    world_update: WorldStateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorldState:
    """
    Update world state.
    """
    # Get world with template for ownership check
    result = await db.execute(
        select(WorldState)
        .where(WorldState.id == world_id)
        .options(selectinload(WorldState.template))
    )
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World not found",
        )

    # Verify ownership
    if world.template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this world",
        )

    # Update fields
    update_data = world_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(world, field, value)

    world.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(world)

    return world


@router.delete("/{world_id}")
async def delete_world(
    world_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Delete world state.
    """
    # Get world with template for ownership check
    result = await db.execute(
        select(WorldState)
        .where(WorldState.id == world_id)
        .options(selectinload(WorldState.template))
    )
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World not found",
        )

    # Verify ownership
    if world.template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this world",
        )

    await db.delete(world)

    return {"message": "World deleted successfully"}


# ============= Simulation Control =============

@router.post("/{world_id}/control", response_model=WorldStateResponse)
async def control_simulation(
    world_id: UUID,
    control: SimulationControlSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorldState:
    """
    Control the simulation (start, pause, resume, stop, reset).
    """
    # Get world with template for ownership check
    result = await db.execute(
        select(WorldState)
        .where(WorldState.id == world_id)
        .options(selectinload(WorldState.template))
    )
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World not found",
        )

    # Verify ownership
    if world.template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to control this world",
        )

    # Handle action
    action = control.action
    now = datetime.utcnow()

    if action == "start":
        if world.status in [WorldStatus.RUNNING.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="World is already running",
            )
        world.status = WorldStatus.RUNNING.value
        world.started_at = now
        world.last_tick_at = now

        # Initialize NPC states if empty
        if not world.npc_states:
            await _initialize_npc_states(db, world)

    elif action == "pause":
        if world.status != WorldStatus.RUNNING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="World is not running",
            )
        world.status = WorldStatus.PAUSED.value

    elif action == "resume":
        if world.status != WorldStatus.PAUSED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="World is not paused",
            )
        world.status = WorldStatus.RUNNING.value
        world.last_tick_at = now

    elif action == "stop":
        world.status = WorldStatus.INACTIVE.value

    elif action == "reset":
        world.status = WorldStatus.INACTIVE.value
        world.npc_states = {}
        world.chat_history = []
        world.total_messages = 0
        world.total_simulation_time = 0
        world.ticks_processed = 0
        world.started_at = None
        world.last_tick_at = None

    # Update simulation speed if provided
    if control.simulation_speed is not None:
        world.simulation_speed = control.simulation_speed

    world.updated_at = now

    await db.flush()
    await db.refresh(world)

    return world


async def _initialize_npc_states(db: AsyncSession, world: WorldState) -> None:
    """
    Initialize NPC states from persona records.
    """
    # Get persona records for this template
    result = await db.execute(
        select(PersonaRecord).where(PersonaRecord.template_id == world.template_id)
    )
    personas = result.scalars().all()

    # Generate random starting positions
    import random
    random.seed(world.seed)

    npc_states = {}
    for persona in personas:
        # Generate random position within world bounds
        x = random.randint(50, (world.world_width * world.tile_size) - 50)
        y = random.randint(50, (world.world_height * world.tile_size) - 50)

        npc_states[str(persona.id)] = {
            "position": {"x": x, "y": y},
            "target_position": None,
            "state": "idle",
            "direction": random.choice(["down", "up", "left", "right"]),
            "speed": random.uniform(35, 55),
            "last_action_time": 0,
            "chat_cooldown": 0,
        }

    world.npc_states = npc_states


# ============= NPC State Management =============

@router.put("/{world_id}/npcs", response_model=WorldStateResponse)
async def update_npc_states(
    world_id: UUID,
    npc_update: NPCStatesUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorldState:
    """
    Batch update NPC states.
    """
    # Get world with template for ownership check
    result = await db.execute(
        select(WorldState)
        .where(WorldState.id == world_id)
        .options(selectinload(WorldState.template))
    )
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World not found",
        )

    # Verify ownership
    if world.template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this world",
        )

    # Update NPC states
    for npc_id, state in npc_update.npc_states.items():
        world.npc_states[npc_id] = state.model_dump()

    world.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(world)

    return world


# ============= Chat History =============

@router.get("/{world_id}/chat", response_model=ChatHistoryResponse)
async def get_chat_history(
    world_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get chat history for a world.
    """
    # Get world with template for ownership check
    result = await db.execute(
        select(WorldState)
        .where(WorldState.id == world_id)
        .options(selectinload(WorldState.template))
    )
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World not found",
        )

    # Verify ownership
    if world.template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this world",
        )

    # Paginate chat history
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    messages = world.chat_history[start_idx:end_idx]

    return {
        "messages": messages,
        "total": len(world.chat_history),
        "page": page,
        "page_size": page_size,
    }


@router.post("/{world_id}/chat")
async def add_chat_message(
    world_id: UUID,
    message: ChatMessageSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Add a chat message to the world history.
    """
    # Get world with template for ownership check
    result = await db.execute(
        select(WorldState)
        .where(WorldState.id == world_id)
        .options(selectinload(WorldState.template))
    )
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World not found",
        )

    # Verify ownership
    if world.template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this world",
        )

    # Add message to history
    world.chat_history.append(message.model_dump())
    world.total_messages += 1
    world.updated_at = datetime.utcnow()

    await db.flush()

    return {"message": "Chat message added", "total_messages": world.total_messages}


# ============= Statistics =============

@router.get("/{world_id}/stats", response_model=WorldStatsResponse)
async def get_world_stats(
    world_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get statistics for a world.
    """
    # Get world with template for ownership check
    result = await db.execute(
        select(WorldState)
        .where(WorldState.id == world_id)
        .options(selectinload(WorldState.template))
    )
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World not found",
        )

    # Verify ownership
    if world.template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this world",
        )

    # Count NPCs
    population = len(world.npc_states)

    # Count active chats (NPCs in chatting state)
    active_chats = sum(
        1 for state in world.npc_states.values()
        if state.get("state") == "chatting"
    )

    # Calculate uptime
    uptime_seconds = None
    if world.started_at:
        uptime_seconds = int((datetime.utcnow() - world.started_at).total_seconds())

    return {
        "population": population,
        "active_chats": active_chats,
        "total_messages": world.total_messages,
        "total_simulation_time": world.total_simulation_time,
        "ticks_processed": world.ticks_processed,
        "status": world.status,
        "uptime_seconds": uptime_seconds,
    }


# ============= Tick Updates (for background worker) =============

@router.post("/{world_id}/tick")
async def process_tick(
    world_id: UUID,
    tick_update: TickUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Process a simulation tick update (typically called by background worker).
    """
    # Get world with template for ownership check
    result = await db.execute(
        select(WorldState)
        .where(WorldState.id == world_id)
        .options(selectinload(WorldState.template))
    )
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World not found",
        )

    # Verify ownership
    if world.template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this world",
        )

    # Update NPC states
    for npc_id, state in tick_update.npc_states.items():
        world.npc_states[npc_id] = state.model_dump()

    # Add new chats to history
    for chat in tick_update.new_chats:
        world.chat_history.append(chat.model_dump())
        world.total_messages += 1

    # Record events
    for event in tick_update.events:
        world_event = WorldEvent(
            world_id=world_id,
            event_type=event.event_type,
            actor_id=event.actor_id,
            target_id=event.target_id,
            data=event.data,
            tick=event.tick,
            timestamp=event.timestamp,
        )
        db.add(world_event)

    # Update tick counter and time
    world.ticks_processed = tick_update.tick
    world.last_tick_at = datetime.utcnow()
    world.updated_at = datetime.utcnow()

    await db.flush()

    return {
        "tick": tick_update.tick,
        "npc_count": len(world.npc_states),
        "new_messages": len(tick_update.new_chats),
    }


# ============= Auto-Create World for Template =============

@router.post("/auto-create/{template_id}", response_model=WorldStateResponse)
async def auto_create_world(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorldState:
    """
    Auto-create and start a world for a template.
    This is called when personas are generated to automatically start the world.
    """
    # Verify template ownership
    result = await db.execute(
        select(PersonaTemplate).where(
            PersonaTemplate.id == template_id,
            PersonaTemplate.user_id == current_user.id,
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona template not found",
        )

    # Check if world already exists
    result = await db.execute(
        select(WorldState).where(WorldState.template_id == template_id)
    )
    world = result.scalar_one_or_none()

    if world:
        # World exists, just return it
        return world

    # Create new world
    seed = random.randint(1, 2**31 - 1)

    world = WorldState(
        template_id=template_id,
        seed=seed,
        world_width=150,
        world_height=114,
        tile_size=16,
        simulation_speed=1.0,
        is_continuous=True,
        status=WorldStatus.INITIALIZING.value,
        npc_states={},
        chat_history=[],
    )

    db.add(world)
    await db.flush()

    # Initialize NPC states
    await _initialize_npc_states(db, world)

    # Start the world
    world.status = WorldStatus.RUNNING.value
    world.started_at = datetime.utcnow()
    world.last_tick_at = datetime.utcnow()

    await db.flush()
    await db.refresh(world)

    return world
