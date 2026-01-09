"""
Vi World Models
Persistent world state for AI agent simulation visualization.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class WorldStatus(str, Enum):
    """World simulation status."""
    INACTIVE = "inactive"      # World not running
    RUNNING = "running"        # Actively simulating
    PAUSED = "paused"          # Temporarily paused
    INITIALIZING = "initializing"  # Setting up


class WorldState(Base):
    """
    Persistent world state for Vi World simulation.
    Stores NPC positions, chat history, and simulation progress.
    """

    __tablename__ = "world_states"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    template_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persona_templates.id", ondelete="CASCADE"), nullable=False
    )

    # World configuration
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    world_width: Mapped[int] = mapped_column(Integer, default=150, nullable=False)
    world_height: Mapped[int] = mapped_column(Integer, default=114, nullable=False)
    tile_size: Mapped[int] = mapped_column(Integer, default=16, nullable=False)

    # Simulation status
    status: Mapped[str] = mapped_column(String(50), default="inactive", nullable=False)
    is_continuous: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # NPC states - JSONB for flexible storage
    # Structure: {
    #   "npc_id": {
    #     "position": {"x": 100, "y": 200},
    #     "target_position": {"x": 150, "y": 250} | null,
    #     "state": "idle" | "walking" | "chatting",
    #     "direction": "down" | "up" | "left" | "right",
    #     "speed": 45.5,
    #     "last_action_time": 1704067200000,
    #     "chat_cooldown": 1704067200000
    #   }
    # }
    npc_states: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Chat history - JSONB array
    # Structure: [
    #   {
    #     "id": "uuid",
    #     "sender_id": "npc_id",
    #     "sender_name": "John",
    #     "receiver_id": "npc_id",
    #     "message": "Hello!",
    #     "timestamp": 1704067200000
    #   }
    # ]
    chat_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Statistics
    total_messages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_simulation_time: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # in seconds

    # Simulation timing
    simulation_speed: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # 1.0 = realtime
    last_tick_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ticks_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    template = relationship("PersonaTemplate", backref="world_states")


class WorldEvent(Base):
    """
    Events that occur in the world (for replay and analytics).
    """

    __tablename__ = "world_events"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    world_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("world_states.id", ondelete="CASCADE"), nullable=False
    )

    # Event details
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # chat, move, spawn, despawn
    actor_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # NPC ID
    target_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Target NPC ID

    # Event data
    data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Timing
    tick: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    world = relationship("WorldState", backref="events")
