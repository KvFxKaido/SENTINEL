"""
Headless runner for SENTINEL.

Provides JSON I/O interface for programmatic control.
Input: JSON commands via stdin
Output: JSON events via stdout

This enables embedding SENTINEL in other processes (Deno bridge, testing, etc.)
"""

import json
import sys
import io
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO, Generator

from ..state import CampaignManager, get_event_bus, EventType, GameEvent
from ..agent import SentinelAgent
from ..llm.base import Message
from .commands import register_all_commands
from .tui_commands import register_tui_handlers


@contextmanager
def capture_console_output() -> Generator[io.StringIO, None, None]:
    """
    Context manager to capture Rich console output.

    CLI commands use console.print() which goes to stdout.
    In headless mode, we need to capture this output to include
    it in the JSON response instead of polluting the JSON stream.
    """
    from .renderer import console

    # Store the original file
    original_file = console.file

    # Create a buffer to capture output
    buffer = io.StringIO()

    try:
        # Redirect console output to our buffer
        console.file = buffer
        yield buffer
    finally:
        # Restore original file
        console.file = original_file


class HeadlessRunner:
    """
    Headless SENTINEL runner with JSON I/O.
    
    Commands are read from stdin as JSON objects.
    Events and responses are written to stdout as JSON.
    """
    
    def __init__(
        self,
        campaigns_dir: Path | None = None,
        prompts_dir: Path | None = None,
        lore_dir: Path | None = None,
        backend: str = "auto",
        local_mode: bool = False,
        output: TextIO = sys.stdout,
    ):
        self.campaigns_dir = campaigns_dir or Path("campaigns")
        self.prompts_dir = prompts_dir or Path(__file__).parent.parent.parent / "prompts"
        base_dir = Path(__file__).parent.parent.parent.parent
        self.lore_dir = lore_dir or (base_dir / "lore" if (base_dir / "lore").exists() else None)
        self.output = output
        
        self.manager = CampaignManager(self.campaigns_dir)
        self.agent = SentinelAgent(
            self.manager,
            prompts_dir=self.prompts_dir,
            lore_dir=self.lore_dir,
            backend=backend,
            local_mode=local_mode,
        )
        self.conversation: list[Message] = []
        
        register_all_commands()
        register_tui_handlers()
        
        self._subscribe_to_events()
    
    def _subscribe_to_events(self):
        """Subscribe to all events and emit them as JSON."""
        bus = get_event_bus()
        for event_type in EventType:
            bus.on(event_type, self._emit_event)
    
    def _emit_event(self, event: GameEvent):
        """Emit a game event as JSON to stdout."""
        self._write_json({
            "type": "event",
            "event_type": event.type.value,
            "data": event.data,
            "campaign_id": event.campaign_id,
            "session": event.session,
            "timestamp": event.timestamp.isoformat(),
        })
    
    def _write_json(self, obj: dict):
        """Write a JSON object to output followed by newline."""
        json.dump(obj, self.output)
        self.output.write("\n")
        self.output.flush()
    
    def _emit_response(self, response_type: str, **data):
        """Emit a response object."""
        self._write_json({
            "type": response_type,
            **data,
        })
    
    def handle_command(self, cmd: dict) -> dict:
        """
        Handle a JSON command.
        
        Commands:
            {"cmd": "status"} - Get current status
            {"cmd": "say", "text": "..."} - Send player input to GM
            {"cmd": "slash", "command": "/new", "args": [...]} - Run slash command
            {"cmd": "load", "campaign_id": "..."} - Load campaign
            {"cmd": "save"} - Save current campaign
            {"cmd": "quit"} - Exit
        
        Returns:
            Response dict
        """
        cmd_type = cmd.get("cmd", "")
        
        if cmd_type == "status":
            return self._cmd_status()
        elif cmd_type == "campaign_state":
            return self._cmd_campaign_state()
        elif cmd_type == "say":
            return self._cmd_say(cmd.get("text", ""))
        elif cmd_type == "slash":
            return self._cmd_slash(cmd.get("command", ""), cmd.get("args", []))
        elif cmd_type == "load":
            return self._cmd_load(cmd.get("campaign_id", ""))
        elif cmd_type == "save":
            return self._cmd_save()
        elif cmd_type == "quit":
            return {"ok": True, "action": "quit"}
        else:
            return {"ok": False, "error": f"Unknown command: {cmd_type}"}
    
    def _cmd_status(self) -> dict:
        """Return current game status."""
        campaign = self.manager.current
        return {
            "ok": True,
            "backend": self.agent.backend_info,
            "campaign": {
                "id": campaign.meta.id if campaign else None,
                "name": campaign.meta.name if campaign else None,
                "session": campaign.meta.session_count if campaign else 0,
            } if campaign else None,
            "conversation_length": len(self.conversation),
        }

    def _cmd_campaign_state(self) -> dict:
        """Return detailed campaign state for UI rendering."""
        campaign = self.manager.current
        if not campaign:
            return {"ok": False, "error": "No campaign loaded"}

        # Get the first character (player character)
        char = campaign.characters[0] if campaign.characters else None

        # Build faction standings from FactionRegistry attributes
        factions = []
        faction_attrs = [
            'nexus', 'ember_colonies', 'lattice', 'convergence', 'covenant',
            'wanderers', 'cultivators', 'steel_syndicate', 'witnesses',
            'architects', 'ghost_networks'
        ]
        for attr in faction_attrs:
            faction_standing = getattr(campaign.factions, attr, None)
            if faction_standing:
                factions.append({
                    "id": attr,
                    "name": attr.replace("_", " ").title(),
                    "standing": faction_standing.standing.value,
                })

        # Get session phase if in mission
        session_phase = None
        if campaign.session:
            session_phase = campaign.session.mission.phase.value if campaign.session.mission else None

        return {
            "ok": True,
            "campaign": {
                "id": campaign.meta.id,
                "name": campaign.meta.name,
                "session": campaign.meta.session_count,
                "phase": campaign.meta.phase,
            },
            "character": {
                "name": char.name if char else None,
                "social_energy": {
                    "current": char.social_energy.current if char else 0,
                    "max": 100,  # Social energy is always 0-100
                },
                "credits": char.credits if char else 0,
            } if char else None,
            "region": campaign.region.value if hasattr(campaign.region, 'value') else str(campaign.region),
            "location": campaign.location.value if hasattr(campaign.location, 'value') else str(campaign.location),
            "session_phase": session_phase,
            "factions": factions,
            "active_jobs": len(campaign.jobs.active),
            "dormant_threads": len(campaign.dormant_threads),
        }
    
    def _cmd_say(self, text: str) -> dict:
        """Send player input to GM and get response."""
        if not text:
            return {"ok": False, "error": "No text provided"}
        
        if not self.manager.current:
            return {"ok": False, "error": "No campaign loaded"}
        
        if not self.agent.is_available:
            return {"ok": False, "error": "No LLM backend available"}
        
        try:
            response = self.agent.respond(text, self.conversation)
            self.conversation.append(Message(role="user", content=text))
            self.conversation.append(Message(role="assistant", content=response))
            
            return {
                "ok": True,
                "response": response,
                "conversation_length": len(self.conversation),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def _cmd_slash(self, command: str, args: list) -> dict:
        """Execute a slash command."""
        from .command_registry import get_registry

        if not command.startswith("/"):
            command = "/" + command

        registry = get_registry()
        cmd_obj = registry.get(command)

        if not cmd_obj:
            return {"ok": False, "error": f"Unknown command: {command}"}

        try:
            # Capture any Rich console output (tables, formatted text)
            # so it doesn't pollute the JSON stream
            with capture_console_output() as buffer:
                # cmd_obj is a Command dataclass with a .handler attribute
                result = cmd_obj.handler(self.manager, self.agent, args)

            # Get captured console output (strip ANSI codes for clean text)
            console_output = buffer.getvalue().strip()

            response: dict = {"ok": True}
            if result:
                response["result"] = str(result)
            if console_output:
                response["output"] = console_output

            return response
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def _cmd_load(self, campaign_id: str) -> dict:
        """Load a campaign by ID."""
        if not campaign_id:
            return {"ok": False, "error": "No campaign_id provided"}
        
        try:
            self.manager.load_campaign(campaign_id)
            self.conversation = []  # Reset conversation on load
            return {
                "ok": True,
                "campaign": {
                    "id": self.manager.current.meta.id,
                    "name": self.manager.current.meta.name,
                    "session": self.manager.current.meta.session_count,
                },
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def _cmd_save(self) -> dict:
        """Save current campaign."""
        if not self.manager.current:
            return {"ok": False, "error": "No campaign loaded"}
        
        try:
            self.manager.save_campaign()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def run(self):
        """
        Main loop: read JSON commands from stdin, write responses to stdout.
        
        One JSON object per line. Exit on EOF or quit command.
        """
        self._emit_response("ready", version="0.1.0", backend=self.agent.backend_info)
        
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                cmd = json.loads(line)
            except json.JSONDecodeError as e:
                self._emit_response("error", error=f"Invalid JSON: {e}")
                continue
            
            result = self.handle_command(cmd)
            self._emit_response("result", **result)
            
            if result.get("action") == "quit":
                break


def run_headless(
    backend: str = "auto",
    local_mode: bool = False,
):
    """Entry point for headless mode."""
    runner = HeadlessRunner(backend=backend, local_mode=local_mode)
    runner.run()
