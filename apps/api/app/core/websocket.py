"""
WebSocket Manager for Real-time Progress Updates
Handles WebSocket connections for simulation progress broadcasting.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    type: str
    data: dict


class RunProgress(BaseModel):
    """Progress update for a product run."""
    run_id: str
    progress: int
    agents_completed: int
    agents_failed: int
    agents_total: int
    status: str
    extra: Optional[dict] = None


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting.
    Supports subscribing to specific run_ids for targeted updates.
    """

    def __init__(self):
        # Active connections by run_id
        self._connections: Dict[str, Set[WebSocket]] = {}
        # All active connections (for broadcast)
        self._all_connections: Set[WebSocket] = set()
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, run_id: Optional[str] = None):
        """Accept a WebSocket connection."""
        await websocket.accept()

        async with self._lock:
            self._all_connections.add(websocket)

            if run_id:
                if run_id not in self._connections:
                    self._connections[run_id] = set()
                self._connections[run_id].add(websocket)

        logger.info(f"WebSocket connected. Run ID: {run_id}. Total connections: {len(self._all_connections)}")

    async def disconnect(self, websocket: WebSocket, run_id: Optional[str] = None):
        """Handle WebSocket disconnection."""
        async with self._lock:
            self._all_connections.discard(websocket)

            if run_id and run_id in self._connections:
                self._connections[run_id].discard(websocket)
                if not self._connections[run_id]:
                    del self._connections[run_id]

        logger.info(f"WebSocket disconnected. Run ID: {run_id}")

    async def subscribe(self, websocket: WebSocket, run_id: str):
        """Subscribe a connection to a specific run."""
        async with self._lock:
            if run_id not in self._connections:
                self._connections[run_id] = set()
            self._connections[run_id].add(websocket)

        logger.debug(f"WebSocket subscribed to run {run_id}")

    async def unsubscribe(self, websocket: WebSocket, run_id: str):
        """Unsubscribe a connection from a specific run."""
        async with self._lock:
            if run_id in self._connections:
                self._connections[run_id].discard(websocket)
                if not self._connections[run_id]:
                    del self._connections[run_id]

        logger.debug(f"WebSocket unsubscribed from run {run_id}")

    async def send_to_run(self, run_id: str, message: dict):
        """Send a message to all connections subscribed to a run."""
        async with self._lock:
            connections = self._connections.get(run_id, set()).copy()

        if not connections:
            return

        # Send to all subscribed connections
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            await self.disconnect(ws, run_id)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        async with self._lock:
            connections = self._all_connections.copy()

        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        for ws in disconnected:
            await self.disconnect(ws)

    async def send_progress(
        self,
        run_id: str,
        progress: int,
        agents_completed: int,
        agents_failed: int,
        agents_total: int,
        status: str = "running",
        extra: Optional[dict] = None
    ):
        """Send progress update for a specific run."""
        message = {
            "type": "progress",
            "data": {
                "run_id": run_id,
                "progress": progress,
                "agents_completed": agents_completed,
                "agents_failed": agents_failed,
                "agents_total": agents_total,
                "status": status,
                "extra": extra or {}
            }
        }
        await self.send_to_run(run_id, message)

    async def send_agent_complete(
        self,
        run_id: str,
        agent_index: int,
        tokens_used: int,
        response_preview: Optional[str] = None
    ):
        """Send notification that an agent completed."""
        message = {
            "type": "agent_complete",
            "data": {
                "run_id": run_id,
                "agent_index": agent_index,
                "tokens_used": tokens_used,
                "response_preview": response_preview[:200] if response_preview else None
            }
        }
        await self.send_to_run(run_id, message)

    async def send_run_complete(
        self,
        run_id: str,
        result_id: str,
        summary: dict
    ):
        """Send notification that a run completed."""
        message = {
            "type": "run_complete",
            "data": {
                "run_id": run_id,
                "result_id": result_id,
                "summary": summary
            }
        }
        await self.send_to_run(run_id, message)

    async def send_run_failed(
        self,
        run_id: str,
        error: str
    ):
        """Send notification that a run failed."""
        message = {
            "type": "run_failed",
            "data": {
                "run_id": run_id,
                "error": error
            }
        }
        await self.send_to_run(run_id, message)

    def get_connection_count(self, run_id: Optional[str] = None) -> int:
        """Get the number of active connections."""
        if run_id:
            return len(self._connections.get(run_id, set()))
        return len(self._all_connections)


# Global WebSocket manager instance
ws_manager = WebSocketManager()


def get_ws_manager() -> WebSocketManager:
    """Get the global WebSocket manager."""
    return ws_manager


# ============= WebSocket Route Handler =============

async def websocket_endpoint(websocket: WebSocket, run_id: Optional[str] = None):
    """
    WebSocket endpoint handler.

    Usage:
        ws://host/ws/{run_id}  - Subscribe to specific run
        ws://host/ws           - General connection

    Client messages:
        {"type": "subscribe", "run_id": "..."}
        {"type": "unsubscribe", "run_id": "..."}
        {"type": "ping"}

    Server messages:
        {"type": "progress", "data": {...}}
        {"type": "agent_complete", "data": {...}}
        {"type": "run_complete", "data": {...}}
        {"type": "run_failed", "data": {...}}
        {"type": "pong"}
    """
    manager = get_ws_manager()
    await manager.connect(websocket, run_id)

    try:
        while True:
            # Wait for client messages
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "subscribe":
                    new_run_id = message.get("run_id")
                    if new_run_id:
                        await manager.subscribe(websocket, new_run_id)
                        await websocket.send_json({
                            "type": "subscribed",
                            "run_id": new_run_id
                        })

                elif msg_type == "unsubscribe":
                    old_run_id = message.get("run_id")
                    if old_run_id:
                        await manager.unsubscribe(websocket, old_run_id)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "run_id": old_run_id
                        })

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })

    except WebSocketDisconnect:
        await manager.disconnect(websocket, run_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket, run_id)


# ============= Progress Callback Factory =============

def create_progress_callback(run_id: str, manager: Optional[WebSocketManager] = None):
    """
    Create a progress callback function for use with ProductExecutionService.

    Returns an async callback that broadcasts progress updates via WebSocket.
    """
    ws = manager or get_ws_manager()

    async def progress_callback(
        progress: int,
        agents_completed: int,
        agents_failed: int,
        extra: Optional[dict] = None
    ):
        """Callback to send progress updates via WebSocket."""
        agents_total = extra.get("total", agents_completed + agents_failed) if extra else 0

        await ws.send_progress(
            run_id=run_id,
            progress=progress,
            agents_completed=agents_completed,
            agents_failed=agents_failed,
            agents_total=agents_total,
            status="running",
            extra=extra
        )

    return progress_callback
