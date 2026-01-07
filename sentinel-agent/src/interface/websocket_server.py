"""
WebSocket server for SENTINEL desktop UI.

Bridges the React frontend to the Python game engine.
"""

import asyncio
import json
import logging
from typing import Callable, Any
from dataclasses import dataclass, field

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = Any

from ..state import CampaignManager
from ..state.schema import MissionPhase

logger = logging.getLogger(__name__)


@dataclass
class GameStateSnapshot:
    """Serializable snapshot of game state for the UI."""

    campaign: dict = field(default_factory=dict)
    character: dict = field(default_factory=dict)
    factions: dict = field(default_factory=dict)
    session: dict = field(default_factory=dict)
    loadout: list = field(default_factory=list)
    active_npc: dict | None = None

    def to_dict(self) -> dict:
        return {
            "campaign": self.campaign,
            "character": self.character,
            "factions": self.factions,
            "session": self.session,
            "loadout": self.loadout,
            "activeNpc": self.active_npc,
        }


def extract_game_state(manager: CampaignManager) -> GameStateSnapshot:
    """Extract current game state for UI consumption."""
    if not manager.current:
        return GameStateSnapshot()

    campaign = manager.current
    snapshot = GameStateSnapshot()

    # Campaign info
    snapshot.campaign = {
        "name": campaign.meta.name,
        "session": campaign.meta.session_count,
        "phase": campaign.session.phase.value if campaign.session else "none",
    }

    # Character info
    if campaign.characters:
        char = campaign.characters[0]
        snapshot.character = {
            "name": char.name,
            "background": char.background.value if char.background else "Unknown",
            "socialEnergy": char.social_energy.current,
        }

        # Loadout (gear IDs to names)
        if campaign.session:
            gear_map = {g.id: g for g in char.gear}
            snapshot.loadout = [
                {
                    "id": gid,
                    "name": gear_map[gid].name if gid in gear_map else gid,
                    "singleUse": gear_map[gid].single_use if gid in gear_map else False,
                    "used": gear_map[gid].used if gid in gear_map else False,
                }
                for gid in campaign.session.loadout
                if gid in gear_map
            ]

    # Faction standings
    for standing in campaign.faction_standings:
        snapshot.factions[standing.faction_id] = standing.standing.value

    # Session info
    if campaign.session:
        snapshot.session = {
            "missionId": campaign.session.mission_id,
            "missionTitle": campaign.session.mission_title,
            "phase": campaign.session.phase.value,
        }

    return snapshot


class SentinelWebSocketServer:
    """WebSocket server that bridges UI to game engine."""

    def __init__(
        self,
        manager: CampaignManager,
        host: str = "localhost",
        port: int = 8765,
        on_command: Callable[[str], str] | None = None,
    ):
        self.manager = manager
        self.host = host
        self.port = port
        self.on_command = on_command
        self.clients: set[WebSocketServerProtocol] = set()
        self._server = None
        self._running = False

    async def start(self):
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets library not installed")
            return

        self._running = True
        self._server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
        )
        logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")

    async def stop(self):
        """Stop the WebSocket server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        # Close all client connections
        for client in self.clients:
            await client.close()
        self.clients.clear()
        logger.info("WebSocket server stopped")

    async def broadcast_state(self):
        """Send current game state to all connected clients."""
        if not self.clients:
            return

        state = extract_game_state(self.manager)
        message = json.dumps({
            "type": "state",
            "data": state.to_dict(),
        })

        # Send to all clients
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)

        # Remove disconnected clients
        self.clients -= disconnected

    async def broadcast_message(self, msg_type: str, content: str, **kwargs):
        """Send a message to all connected clients."""
        if not self.clients:
            return

        message = json.dumps({
            "type": msg_type,
            "content": content,
            **kwargs,
        })

        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)

        self.clients -= disconnected

    async def broadcast_narrative(self, content: str):
        """Send narrative text to UI."""
        await self.broadcast_message("narrative", content)

    async def broadcast_choice(self, prompt: str, options: list[str]):
        """Send choice options to UI."""
        await self.broadcast_message("choice", prompt, options=options)

    async def broadcast_npc(
        self,
        name: str,
        faction: str,
        dialogue: str,
        disposition: str = "neutral",
        role: str | None = None,
    ):
        """Send NPC dialogue to UI (triggers codec box)."""
        await self.broadcast_message(
            "npc",
            dialogue,
            npc={
                "name": name,
                "faction": faction,
                "disposition": disposition,
                "role": role,
            },
        )

    async def _handle_client(self, websocket: WebSocketServerProtocol):
        """Handle a single client connection."""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")

        try:
            # Send initial state
            state = extract_game_state(self.manager)
            await websocket.send(json.dumps({
                "type": "state",
                "data": state.to_dict(),
            }))

            # Handle incoming messages
            async for message in websocket:
                await self._handle_message(websocket, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        finally:
            self.clients.discard(websocket)
            logger.info(f"Client removed. Total clients: {len(self.clients)}")

    async def _handle_message(self, websocket: WebSocketServerProtocol, raw: str):
        """Process an incoming message from the UI."""
        try:
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "command":
                # Player issued a command (e.g., /status, /loadout)
                command = data.get("command", "")
                if self.on_command:
                    response = self.on_command(command)
                    await websocket.send(json.dumps({
                        "type": "response",
                        "content": response,
                    }))

            elif msg_type == "input":
                # Player typed something (dialogue or choice selection)
                user_input = data.get("input", "")
                if self.on_command:
                    response = self.on_command(user_input)
                    await websocket.send(json.dumps({
                        "type": "response",
                        "content": response,
                    }))

            elif msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

            elif msg_type == "get_state":
                # UI requesting full state refresh
                state = extract_game_state(self.manager)
                await websocket.send(json.dumps({
                    "type": "state",
                    "data": state.to_dict(),
                }))

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {raw[:100]}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")


async def run_server(
    manager: CampaignManager,
    host: str = "localhost",
    port: int = 8765,
    on_command: Callable[[str], str] | None = None,
):
    """Run the WebSocket server (blocking)."""
    server = SentinelWebSocketServer(manager, host, port, on_command)
    await server.start()

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await server.stop()


def start_server_thread(
    manager: CampaignManager,
    host: str = "localhost",
    port: int = 8765,
    on_command: Callable[[str], str] | None = None,
) -> SentinelWebSocketServer:
    """
    Start the WebSocket server in a background thread.

    Returns the server instance for later control.
    """
    import threading

    server = SentinelWebSocketServer(manager, host, port, on_command)

    def run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.start())
        loop.run_forever()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return server
