"""
World Schemas
Pydantic schemas for Vi World API endpoints.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Position Schema
class PositionSchema(BaseModel):
    """Position in the world."""
    x: float
    y: float


# NPC State Schema
class NPCStateSchema(BaseModel):
    """Individual NPC state."""
    position: PositionSchema
    target_position: Optional[PositionSchema] = None
    state: str = Field(default="idle", pattern="^(idle|walking|chatting)$")
    direction: str = Field(default="down", pattern="^(down|up|left|right)$")
    speed: float = Field(default=45.0, ge=0, le=200)
    last_action_time: int = 0
    chat_cooldown: int = 0


# Chat Message Schema
class ChatMessageSchema(BaseModel):
    """Chat message in the world."""
    id: str
    sender_id: str
    sender_name: str
    receiver_id: Optional[str] = None
    message: str
    timestamp: int


# World Event Schema
class WorldEventSchema(BaseModel):
    """Event in the world."""
    event_type: str
    actor_id: Optional[str] = None
    target_id: Optional[str] = None
    data: dict = {}
    tick: int
    timestamp: datetime


# World State Schemas
class WorldStateBase(BaseModel):
    """Base world state schema."""
    seed: Optional[int] = None
    world_width: int = Field(default=150, ge=10, le=500)
    world_height: int = Field(default=114, ge=10, le=500)
    tile_size: int = Field(default=16, ge=8, le=64)
    simulation_speed: float = Field(default=1.0, ge=0.1, le=10.0)
    is_continuous: bool = True


class WorldStateCreate(WorldStateBase):
    """Schema for creating a world state."""
    template_id: UUID


class WorldStateUpdate(BaseModel):
    """Schema for updating a world state."""
    status: Optional[str] = Field(None, pattern="^(inactive|running|paused|initializing)$")
    simulation_speed: Optional[float] = Field(None, ge=0.1, le=10.0)
    npc_states: Optional[dict[str, NPCStateSchema]] = None
    is_continuous: Optional[bool] = None


class WorldStateResponse(WorldStateBase):
    """Schema for world state response."""
    id: UUID
    template_id: UUID
    status: str
    npc_states: dict = {}
    chat_history: list = []
    total_messages: int = 0
    total_simulation_time: int = 0
    ticks_processed: int = 0
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    last_tick_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorldStateListResponse(BaseModel):
    """Schema for list of world states."""
    id: UUID
    template_id: UUID
    status: str
    total_messages: int
    ticks_processed: int
    is_continuous: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# NPC State Update (batch update)
class NPCStatesUpdateSchema(BaseModel):
    """Schema for batch updating NPC states."""
    npc_states: dict[str, NPCStateSchema]


# Chat History Response
class ChatHistoryResponse(BaseModel):
    """Schema for chat history."""
    messages: list[ChatMessageSchema]
    total: int
    page: int
    page_size: int


# World Statistics
class WorldStatsResponse(BaseModel):
    """Schema for world statistics."""
    population: int
    active_chats: int
    total_messages: int
    total_simulation_time: int
    ticks_processed: int
    status: str
    uptime_seconds: Optional[int] = None


# Simulation Control
class SimulationControlSchema(BaseModel):
    """Schema for controlling simulation."""
    action: str = Field(..., pattern="^(start|pause|resume|stop|reset)$")
    simulation_speed: Optional[float] = Field(None, ge=0.1, le=10.0)


# Tick Update Schema (from background worker)
class TickUpdateSchema(BaseModel):
    """Schema for tick updates from background worker."""
    tick: int
    npc_states: dict[str, NPCStateSchema]
    new_chats: list[ChatMessageSchema] = []
    events: list[WorldEventSchema] = []
