"""
Headless runner for SENTINEL.

Provides JSON I/O interface for programmatic control.
Input: JSON commands via stdin
Output: JSON events via stdout

This enables embedding SENTINEL in other processes (Deno bridge, testing, etc.)
"""

import json
import sys
from pathlib import Path
from typing import TextIO

from ..state import CampaignManager, get_event_bus, EventType, GameEvent
from ..agent import SentinelAgent
from ..llm.base import Message
from .commands import register_all_commands
from .tui_commands import register_tui_handlers


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
        handler = registry.get(command)
        
        if not handler:
            return {"ok": False, "error": f"Unknown command: {command}"}
        
        try:
            result = handler(self.manager, self.agent, args)
            return {"ok": True, "result": str(result) if result else None}
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
