"""
World Simulation Background Tasks
Handles continuous world simulation processing.
"""

import asyncio
import random
import math
from datetime import datetime
from typing import Any
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.world import WorldState, WorldEvent, WorldStatus


# Create async engine for background tasks
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(name="app.tasks.world_simulation.process_all_active_worlds")
def process_all_active_worlds():
    """
    Process all active worlds. Called every second by Celery Beat.
    """
    return run_async(_process_all_active_worlds())


async def _process_all_active_worlds():
    """
    Async implementation of processing all active worlds.
    """
    async with AsyncSessionLocal() as db:
        # Get all running worlds
        result = await db.execute(
            select(WorldState).where(WorldState.status == WorldStatus.RUNNING.value)
        )
        worlds = result.scalars().all()

        processed = 0
        for world in worlds:
            try:
                await _process_world_tick(db, world)
                processed += 1
            except Exception as e:
                # Log error but continue processing other worlds
                print(f"Error processing world {world.id}: {e}")

        await db.commit()

        return {"processed": processed, "timestamp": datetime.utcnow().isoformat()}


async def _process_world_tick(db: AsyncSession, world: WorldState):
    """
    Process a single tick for a world.
    Updates NPC positions, handles chat interactions, and records events.
    """
    now = datetime.utcnow()

    # Calculate delta time (in seconds)
    if world.last_tick_at:
        delta = (now - world.last_tick_at).total_seconds()
    else:
        delta = 0.016  # Default to ~60fps

    # Apply simulation speed
    delta *= world.simulation_speed

    # Don't process if too little time has passed
    if delta < 0.016:  # Less than 1 frame at 60fps
        return

    # Get world dimensions
    world_pixel_width = world.world_width * world.tile_size
    world_pixel_height = world.world_height * world.tile_size

    # Process each NPC
    npc_states = dict(world.npc_states)  # Create mutable copy
    npc_ids = list(npc_states.keys())
    new_chats = []

    for npc_id in npc_ids:
        state = npc_states[npc_id]

        # Update movement
        state = _update_npc_movement(state, delta, world_pixel_width, world_pixel_height)

        # Check for chat interactions
        if state["state"] != "chatting" and state.get("chat_cooldown", 0) <= now.timestamp() * 1000:
            chat = _check_chat_interaction(npc_id, state, npc_states, now)
            if chat:
                new_chats.append(chat)
                state["state"] = "chatting"
                state["chat_cooldown"] = int((now.timestamp() + 10) * 1000)  # 10 second cooldown

        npc_states[npc_id] = state

    # Update world state
    world.npc_states = npc_states
    world.last_tick_at = now
    world.ticks_processed += 1
    world.total_simulation_time += int(delta)
    world.updated_at = now

    # Add new chats to history
    if new_chats:
        chat_history = list(world.chat_history)
        chat_history.extend(new_chats)
        # Keep only last 1000 messages
        if len(chat_history) > 1000:
            chat_history = chat_history[-1000:]
        world.chat_history = chat_history
        world.total_messages += len(new_chats)

    # Create events for new chats
    for chat in new_chats:
        event = WorldEvent(
            world_id=world.id,
            event_type="chat",
            actor_id=chat["sender_id"],
            target_id=chat.get("receiver_id"),
            data={"message": chat["message"]},
            tick=world.ticks_processed,
            timestamp=now,
        )
        db.add(event)


def _update_npc_movement(
    state: dict,
    delta: float,
    world_width: int,
    world_height: int
) -> dict:
    """
    Update NPC position based on movement state.
    """
    # If chatting, don't move
    if state["state"] == "chatting":
        return state

    position = state["position"]
    target = state.get("target_position")
    speed = state.get("speed", 45)

    # If no target or reached target, set new random target
    if not target or (
        abs(position["x"] - target["x"]) < 5 and
        abs(position["y"] - target["y"]) < 5
    ):
        # Random chance to set new target
        if random.random() < 0.02:  # 2% chance per tick
            margin = 50
            target = {
                "x": random.randint(margin, world_width - margin),
                "y": random.randint(margin, world_height - margin),
            }
            state["target_position"] = target
            state["state"] = "walking"
        else:
            state["state"] = "idle"
            state["target_position"] = None
            return state

    # Move towards target
    if target:
        dx = target["x"] - position["x"]
        dy = target["y"] - position["y"]
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # Normalize and apply speed
            move_distance = min(speed * delta, distance)
            position["x"] += (dx / distance) * move_distance
            position["y"] += (dy / distance) * move_distance

            # Update direction based on movement
            if abs(dx) > abs(dy):
                state["direction"] = "right" if dx > 0 else "left"
            else:
                state["direction"] = "down" if dy > 0 else "up"

            state["position"] = position
            state["state"] = "walking"

    return state


def _check_chat_interaction(
    npc_id: str,
    state: dict,
    all_states: dict,
    now: datetime
) -> dict | None:
    """
    Check if NPC should start a chat with nearby NPC.
    """
    # Low probability of starting chat
    if random.random() > 0.005:  # 0.5% chance per tick
        return None

    position = state["position"]
    proximity_threshold = 80  # pixels

    # Find nearby NPCs
    for other_id, other_state in all_states.items():
        if other_id == npc_id:
            continue

        if other_state["state"] == "chatting":
            continue

        other_pos = other_state["position"]
        dx = position["x"] - other_pos["x"]
        dy = position["y"] - other_pos["y"]
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < proximity_threshold:
            # Generate chat message
            messages = [
                "Hey, nice weather today!",
                "Have you heard the latest news?",
                "What are you working on?",
                "This place is great!",
                "Nice to see you!",
                "How's it going?",
                "Lovely day for a walk!",
                "Did you try the new cafe?",
                "I'm exploring the area.",
                "See anything interesting?",
            ]

            import uuid
            return {
                "id": str(uuid.uuid4()),
                "sender_id": npc_id,
                "sender_name": f"NPC-{npc_id[:8]}",
                "receiver_id": other_id,
                "message": random.choice(messages),
                "timestamp": int(now.timestamp() * 1000),
            }

    return None


@shared_task(name="app.tasks.world_simulation.start_world")
def start_world(world_id: str):
    """
    Start a specific world's simulation.
    """
    return run_async(_start_world(UUID(world_id)))


async def _start_world(world_id: UUID):
    """
    Async implementation of starting a world.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorldState).where(WorldState.id == world_id)
        )
        world = result.scalar_one_or_none()

        if not world:
            return {"error": "World not found"}

        if world.status == WorldStatus.RUNNING.value:
            return {"status": "already_running"}

        world.status = WorldStatus.RUNNING.value
        world.started_at = datetime.utcnow()
        world.last_tick_at = datetime.utcnow()
        world.updated_at = datetime.utcnow()

        await db.commit()

        return {
            "world_id": str(world_id),
            "status": "started",
            "timestamp": datetime.utcnow().isoformat(),
        }


@shared_task(name="app.tasks.world_simulation.stop_world")
def stop_world(world_id: str):
    """
    Stop a specific world's simulation.
    """
    return run_async(_stop_world(UUID(world_id)))


async def _stop_world(world_id: UUID):
    """
    Async implementation of stopping a world.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorldState).where(WorldState.id == world_id)
        )
        world = result.scalar_one_or_none()

        if not world:
            return {"error": "World not found"}

        world.status = WorldStatus.INACTIVE.value
        world.updated_at = datetime.utcnow()

        await db.commit()

        return {
            "world_id": str(world_id),
            "status": "stopped",
            "timestamp": datetime.utcnow().isoformat(),
        }
