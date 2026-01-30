"""
WebSocket handler for SENTINEL 2D real-time updates.

Provides real-time state streaming for:
- NPC position updates (patrol visualization)
- Game clock advancement
- State changes from other sources
- Consequence propagation events

Design Constraints:
- Backend remains source of truth
- Frontend may optimistically render but must reconcile
- Patrols should be predictable before surprising
"""

import asyncio
import json
from datetime import datetime
from typing import Callable, Any
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .schemas import (
    StateUpdateEvent,
    NPCMovementEvent,
    GameClockEvent,
    ConsequenceEvent,
    Position,
    AlertState,
)


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure."""
    type: str
    timestamp: datetime = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)


class SubscriptionManager:
    """
    Manages WebSocket subscriptions for different event types.
    
    Clients can subscribe to specific event types:
    - "all" - All events
    - "state" - State changes only
    - "npcs" - NPC movement only
    - "clock" - Game clock only
    - "consequences" - Consequence events only
    """
    
    def __init__(self):
        self.subscriptions: dict[str, set[str]] = {}  # client_id -> set of event types
        self.clients: dict[str, WebSocket] = {}  # client_id -> WebSocket
    
    def add_client(self, client_id: str, websocket: WebSocket):
        """Add a new client with default subscriptions."""
        self.clients[client_id] = websocket
        self.subscriptions[client_id] = {"all"}  # Default to all events
    
    def remove_client(self, client_id: str):
        """Remove a client and their subscriptions."""
        self.clients.pop(client_id, None)
        self.subscriptions.pop(client_id, None)
    
    def update_subscriptions(self, client_id: str, event_types: list[str]):
        """Update a client's subscriptions."""
        if client_id in self.subscriptions:
            self.subscriptions[client_id] = set(event_types)
    
    def get_subscribers(self, event_type: str) -> list[WebSocket]:
        """Get all WebSocket connections subscribed to an event type."""
        subscribers = []
        for client_id, types in self.subscriptions.items():
            if "all" in types or event_type in types:
                if client_id in self.clients:
                    subscribers.append(self.clients[client_id])
        return subscribers


class PatrolSimulator:
    """
    Simulates NPC patrol movement for real-time updates.
    
    Faction behavior patterns:
    - Lattice: Coordinated sweeps across chokepoints
    - Ember: Loose, wandering solo paths
    - Ghost: Static presence → sudden relocation
    - Covenant: Ritualized, time-bound circuits
    """
    
    def __init__(self):
        self.patrol_routes: dict[str, list[Position]] = {}
        self.patrol_indices: dict[str, int] = {}
        self.patrol_behaviors: dict[str, str] = {}
        self._running = False
        self._task: asyncio.Task | None = None
    
    def register_patrol(
        self,
        npc_id: str,
        route: list[Position],
        behavior: str = "standard",
    ):
        """Register a patrol route for an NPC."""
        self.patrol_routes[npc_id] = route
        self.patrol_indices[npc_id] = 0
        self.patrol_behaviors[npc_id] = behavior
    
    def unregister_patrol(self, npc_id: str):
        """Remove a patrol route."""
        self.patrol_routes.pop(npc_id, None)
        self.patrol_indices.pop(npc_id, None)
        self.patrol_behaviors.pop(npc_id, None)
    
    def get_next_position(self, npc_id: str) -> Position | None:
        """Get the next position in an NPC's patrol route."""
        if npc_id not in self.patrol_routes:
            return None
        
        route = self.patrol_routes[npc_id]
        if not route:
            return None
        
        index = self.patrol_indices.get(npc_id, 0)
        position = route[index]
        
        # Advance index based on behavior
        behavior = self.patrol_behaviors.get(npc_id, "standard")
        if behavior == "ghost":
            # Ghost: Random jumps
            import random
            self.patrol_indices[npc_id] = random.randint(0, len(route) - 1)
        else:
            # Standard: Sequential
            self.patrol_indices[npc_id] = (index + 1) % len(route)
        
        return position
    
    async def start(self, broadcast_fn: Callable[[dict], Any], interval: float = 1.0):
        """Start the patrol simulation loop."""
        self._running = True
        
        async def simulation_loop():
            while self._running:
                # Generate movement events for all patrols
                for npc_id in list(self.patrol_routes.keys()):
                    position = self.get_next_position(npc_id)
                    if position:
                        event = NPCMovementEvent(
                            npc_id=npc_id,
                            position=position,
                            alert_state=AlertState.PATROLLING,
                            timestamp=datetime.now(),
                        )
                        await broadcast_fn(event.model_dump())
                
                await asyncio.sleep(interval)
        
        self._task = asyncio.create_task(simulation_loop())
    
    async def stop(self):
        """Stop the patrol simulation."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


class GameClock:
    """
    Game clock for time-based events.
    
    The local game clock pauses during dialogue.
    """
    
    def __init__(self):
        self.day = 1
        self.hour = 8
        self.minute = 0
        self.paused = False
        self.time_scale = 1.0  # Real seconds per game minute
        self._running = False
        self._task: asyncio.Task | None = None
    
    def advance(self, minutes: int = 0, hours: int = 0, days: int = 0):
        """Advance the game clock."""
        total_minutes = minutes + (hours * 60) + (days * 24 * 60)
        
        self.minute += total_minutes
        while self.minute >= 60:
            self.minute -= 60
            self.hour += 1
        while self.hour >= 24:
            self.hour -= 24
            self.day += 1
    
    def get_state(self) -> dict:
        """Get current clock state."""
        return {
            "day": self.day,
            "hour": self.hour,
            "minute": self.minute,
            "paused": self.paused,
            "time_scale": self.time_scale,
        }
    
    async def start(self, broadcast_fn: Callable[[dict], Any]):
        """Start the game clock."""
        self._running = True
        
        async def clock_loop():
            while self._running:
                if not self.paused:
                    self.advance(minutes=1)
                    event = GameClockEvent(
                        game_time=self.get_state(),
                        paused=self.paused,
                        timestamp=datetime.now(),
                    )
                    await broadcast_fn(event.model_dump())
                
                await asyncio.sleep(self.time_scale)
        
        self._task = asyncio.create_task(clock_loop())
    
    async def stop(self):
        """Stop the game clock."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    def pause(self):
        """Pause the game clock."""
        self.paused = True
    
    def resume(self):
        """Resume the game clock."""
        self.paused = False


class RealtimeManager:
    """
    Manages all real-time systems for WebSocket updates.
    
    Coordinates:
    - WebSocket connections
    - Patrol simulation
    - Game clock
    - Event broadcasting
    """
    
    def __init__(self):
        self.subscriptions = SubscriptionManager()
        self.patrols = PatrolSimulator()
        self.clock = GameClock()
        self._started = False
    
    async def connect(self, websocket: WebSocket) -> str:
        """
        Accept a new WebSocket connection.
        
        Returns client ID for tracking.
        """
        await websocket.accept()
        client_id = str(uuid4())[:8]
        self.subscriptions.add_client(client_id, websocket)
        
        # Start systems if this is the first connection
        if not self._started:
            await self._start_systems()
        
        return client_id
    
    def disconnect(self, client_id: str):
        """Handle client disconnection."""
        self.subscriptions.remove_client(client_id)
        
        # Stop systems if no more connections
        if not self.subscriptions.clients:
            asyncio.create_task(self._stop_systems())
    
    async def _start_systems(self):
        """Start all real-time systems."""
        self._started = True
        await self.patrols.start(self.broadcast)
        await self.clock.start(self.broadcast)
    
    async def _stop_systems(self):
        """Stop all real-time systems."""
        self._started = False
        await self.patrols.stop()
        await self.clock.stop()
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all subscribed clients."""
        event_type = message.get("type", "unknown")
        
        # Map event types to subscription categories
        category_map = {
            "state_update": "state",
            "npc_movement": "npcs",
            "game_clock": "clock",
            "consequence": "consequences",
        }
        category = category_map.get(event_type, event_type)
        
        subscribers = self.subscriptions.get_subscribers(category)
        disconnected = []
        
        for websocket in subscribers:
            try:
                await websocket.send_json(message)
            except Exception:
                # Find and mark disconnected client
                for client_id, ws in self.subscriptions.clients.items():
                    if ws is websocket:
                        disconnected.append(client_id)
                        break
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def send_to_client(self, client_id: str, message: dict):
        """Send a message to a specific client."""
        if client_id in self.subscriptions.clients:
            websocket = self.subscriptions.clients[client_id]
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(client_id)
    
    async def handle_client_message(self, client_id: str, message: dict):
        """
        Handle a message from a client.
        
        Supported message types:
        - ping: Keepalive ping
        - subscribe: Update subscriptions
        - unsubscribe: Remove subscriptions
        """
        msg_type = message.get("type", "")
        
        if msg_type == "ping":
            await self.send_to_client(client_id, {"type": "pong"})
        
        elif msg_type == "subscribe":
            event_types = message.get("events", ["all"])
            self.subscriptions.update_subscriptions(client_id, event_types)
            await self.send_to_client(client_id, {
                "type": "subscribed",
                "events": event_types,
            })
        
        elif msg_type == "unsubscribe":
            event_types = message.get("events", [])
            current = self.subscriptions.subscriptions.get(client_id, set())
            for event_type in event_types:
                current.discard(event_type)
            self.subscriptions.subscriptions[client_id] = current
            await self.send_to_client(client_id, {
                "type": "unsubscribed",
                "events": event_types,
            })


# Global realtime manager instance
_realtime_manager: RealtimeManager | None = None


def get_realtime_manager() -> RealtimeManager:
    """Get or create the global realtime manager."""
    global _realtime_manager
    if _realtime_manager is None:
        _realtime_manager = RealtimeManager()
    return _realtime_manager


async def websocket_handler(websocket: WebSocket):
    """
    Main WebSocket handler for real-time updates.
    
    Usage:
        @app.websocket("/updates")
        async def updates(websocket: WebSocket):
            await websocket_handler(websocket)
    """
    manager = get_realtime_manager()
    client_id = await manager.connect(websocket)
    
    try:
        # Send initial connection confirmation
        await manager.send_to_client(client_id, {
            "type": "connected",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Handle messages from client
        while True:
            try:
                data = await websocket.receive_json()
                await manager.handle_client_message(client_id, data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                await manager.send_to_client(client_id, {
                    "type": "error",
                    "message": str(e),
                })
    
    finally:
        manager.disconnect(client_id)


# -----------------------------------------------------------------------------
# State Change Broadcasting
# -----------------------------------------------------------------------------

async def broadcast_state_change(
    changes: dict,
    source: str = "system",
    version: int = 0,
):
    """
    Broadcast a state change to all connected clients.
    
    Called by the API when state changes occur.
    """
    manager = get_realtime_manager()
    event = StateUpdateEvent(
        version=version,
        timestamp=datetime.now(),
        changes=changes,
        source=source,
    )
    await manager.broadcast(event.model_dump())


async def broadcast_consequence(
    thread_id: str | None,
    headline: str,
    details: list[str],
    severity: str = "info",
):
    """
    Broadcast a consequence event to all connected clients.
    
    Called when a dormant thread activates or consequence propagates.
    """
    manager = get_realtime_manager()
    event = ConsequenceEvent(
        thread_id=thread_id,
        headline=headline,
        details=details,
        severity=severity,
        timestamp=datetime.now(),
    )
    await manager.broadcast(event.model_dump())
