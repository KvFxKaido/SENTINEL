"""
Headless runner for SENTINEL.

Provides JSON I/O interface for programmatic control.
Input: JSON commands via stdin
Output: JSON events via stdout

This enables embedding SENTINEL in other processes (Deno bridge, testing, etc.)
"""

import json
import os
import sys
import io
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO, Generator

# Signal that we're in headless mode (disables interactive prompts)
os.environ["SENTINEL_HEADLESS"] = "1"

from ..state import CampaignManager, get_event_bus, EventType, GameEvent
from ..agent import SentinelAgent
from ..llm.base import Message
from .commands import register_all_commands
from .tui_commands import register_tui_handlers
from .config import load_config, set_backend


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
        self.wiki_dir = base_dir / "wiki" if (base_dir / "wiki").exists() else Path("wiki")
        self.output = output

        # Load saved backend preference if "auto" is passed
        if backend == "auto":
            config = load_config(self.campaigns_dir)
            backend = config.get("backend", "claude")

        self.manager = CampaignManager(self.campaigns_dir, wiki_dir=self.wiki_dir)
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
        self._init_turn_engine()
    
    def _subscribe_to_events(self):
        """Subscribe to all events and emit them as JSON."""
        bus = get_event_bus()
        for event_type in EventType:
            bus.on(event_type, self._emit_event)

    def _init_turn_engine(self):
        """Initialize the turn-based engine components."""
        from ..systems.turns import TurnOrchestrator
        from ..systems.validation import ActionValidator
        from ..systems.travel import TravelResolver
        from ..systems.cascades import CascadeProcessor

        self._validator = ActionValidator()
        self._travel_resolver = TravelResolver()
        self._cascade_processor = CascadeProcessor()
        self._orchestrator = None  # Created per-campaign in _ensure_orchestrator

    def _ensure_orchestrator(self):
        """Ensure orchestrator exists and is bound to current campaign."""
        from ..systems.turns import TurnOrchestrator

        campaign = self.manager.current
        if not campaign:
            return None

        # Re-create if campaign changed or not yet created
        if (
            self._orchestrator is None
            or self._orchestrator.campaign is not campaign
        ):
            self._orchestrator = TurnOrchestrator(campaign)
            self._orchestrator.set_validator(self._validator.validate)
            self._orchestrator.register_resolver(
                "travel", self._travel_resolver.resolve,
            )
            self._orchestrator.set_cascade_processor(
                lambda event, camp: self._cascade_processor.process(event, camp),
            )
            # Persist via manager save
            self._orchestrator.set_persist_fn(
                lambda camp: self.manager.save_campaign(),
            )

        return self._orchestrator
    
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
            {"cmd": "travel_propose", "region_id": "..."} - Propose travel (turn-based)
            {"cmd": "travel_commit"} - Commit proposed travel
            {"cmd": "travel_cancel"} - Cancel proposed travel
            {"cmd": "quit"} - Exit

        Returns:
            Response dict
        """
        cmd_type = cmd.get("cmd", "")

        if cmd_type == "status":
            return self._cmd_status()
        elif cmd_type == "campaign_state":
            return self._cmd_campaign_state()
        elif cmd_type == "map_state":
            return self._cmd_map_state()
        elif cmd_type == "map_region":
            return self._cmd_map_region(cmd.get("region_id", ""))
        elif cmd_type == "travel_propose":
            return self._cmd_travel_propose(cmd.get("region_id", ""), cmd.get("via"))
        elif cmd_type == "travel_commit":
            return self._cmd_travel_commit()
        elif cmd_type == "travel_cancel":
            return self._cmd_travel_cancel()
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

        # Build gear list
        gear = []
        if char:
            for item in char.gear:
                gear.append({
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "used": item.used,
                })

        # Build enhancements list
        enhancements = []
        if char:
            for enh in char.enhancements:
                enhancements.append({
                    "id": enh.id,
                    "name": enh.name,
                    "source": enh.source.value if hasattr(enh.source, 'value') else str(enh.source),
                    "benefit": enh.benefit,
                })

        # Build vehicles list
        vehicles = []
        if char:
            for v in char.vehicles:
                vehicles.append({
                    "id": v.id,
                    "name": v.name,
                    "type": v.type,
                    "description": v.description,
                    "fuel": v.fuel,
                    "condition": v.condition,
                    "status": v.status,
                    "terrain": v.terrain,
                    "capacity": v.capacity,
                    "cargo": v.cargo,
                    "stealth": v.stealth,
                })

        # Get current loadout (gear IDs selected for mission)
        loadout_ids = campaign.session.loadout if campaign.session else []

        # Build dormant thread list for UI rendering
        thread_list = []
        for thread in campaign.dormant_threads:
            thread_list.append({
                "id": thread.id,
                "origin": thread.origin,
                "trigger": thread.trigger_condition,
                "consequence": thread.consequence,
                "severity": thread.severity.value,
                "created_session": thread.created_session,
            })

        # Build NPC list for UI metadata
        npc_list = []
        active_ids = {n.id for n in campaign.npcs.active}
        for npc in campaign.npcs.active + campaign.npcs.dormant:
            faction_value = npc.faction.value if npc.faction else None
            faction_standing = None
            if npc.faction:
                faction_standing = campaign.factions.get(npc.faction).standing
            effective_disposition = npc.get_effective_disposition(faction_standing)
            npc_list.append({
                "id": npc.id,
                "name": npc.name,
                "faction": faction_value,
                "disposition": effective_disposition.value,
                "base_disposition": npc.disposition.value,
                "personal_standing": npc.personal_standing,
                "status": "active" if npc.id in active_ids else "dormant",
                "last_interaction": npc.last_interaction,
            })

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
                "background": char.background.value if char and hasattr(char.background, 'value') else None,
                "social_energy": {
                    "current": char.social_energy.current if char else 0,
                    "max": 100,  # Social energy is always 0-100
                },
                "credits": char.credits if char else 0,
                "gear": gear,
                "enhancements": enhancements,
            } if char else None,
            "region": campaign.region.value if hasattr(campaign.region, 'value') else str(campaign.region),
            "location": campaign.location.value if hasattr(campaign.location, 'value') else str(campaign.location),
            "session_phase": session_phase,
            "loadout": loadout_ids,
            "factions": factions,
            "npcs": npc_list,
            "threads": thread_list,
            "active_jobs": len(campaign.jobs.active),
            "dormant_threads": len(campaign.dormant_threads),
            "vehicles": vehicles,
        }
    
    # ── Turn-Based Travel Commands ─────────────────────────

    def _cmd_travel_propose(self, region_id: str, via: str | None = None) -> dict:
        """
        Propose travel to a region — returns costs and requirements.

        No state mutation occurs. The player reviews the ProposalResult
            # Serialize ProposalResult for JSON transport
            return {
                "ok": True,
                "proposal": result.model_dump(),
            }
        """
        campaign = self.manager.current
        if not campaign:
            return {"ok": False, "error": "No campaign loaded"}

        if not region_id:
            return {"ok": False, "error": "No region_id provided"}

        orchestrator = self._ensure_orchestrator()
        if not orchestrator:
            return {"ok": False, "error": "Failed to initialize turn engine"}

        from ..state.schemas.action import Proposal, ActionType
        from ..systems.turns import TurnError

        try:
            proposal = Proposal(
                action_type=ActionType.TRAVEL,
                payload={"to": region_id},
            )

            result = orchestrator.propose(proposal)

            # Serialize ProposalResult for JSON transport
            return {
                "ok": True,
                "proposal": {
                    "action_type": "travel",
                    "region_id": region_id,
                    "state_version": campaign.state_version,
                    "feasible": result.feasible,
                    "summary": result.summary,
                    "requirements": [
                        {
                            "label": r.label,
                            "status": r.status.value,
                            "detail": r.detail,
                            "bypass": r.bypass,
                        }
                        for r in result.requirements
                    ],
                    "costs": {
                        "turns": result.costs.turns,
                        "social_energy": result.costs.social_energy,
                        "credits": result.costs.credits,
                        "fuel": result.costs.fuel,
                        "condition": result.costs.condition,
                        "standing_changes": result.costs.standing_changes,
                    },
                    "risks": [
                        {
                            "label": r.label,
                            "severity": r.severity,
                            "detail": r.detail,
                        }
                        for r in result.risks
                    ],
                    "alternatives": [
                        {
                            "label": a.label,
                            "type": a.type,
                            "description": a.description,
                            "consequence": a.consequence,
                            "costs": {
                                "turns": a.additional_costs.turns,
                                "social_energy": a.additional_costs.social_energy,
                                "credits": a.additional_costs.credits,
                            },
                        }
                        for a in result.alternatives
                    ],
                },
            }

        except TurnError as e:
            return {"ok": False, "error": str(e)}

    def _cmd_travel_commit(self, via: str | None = None) -> dict:
        """
        Commit the proposed travel — this is the commitment gate.

        Resolves deterministically, persists state, returns TurnResult.
        """
        campaign = self.manager.current
        if not campaign:
            return {"ok": False, "error": "No campaign loaded"}

        orchestrator = self._ensure_orchestrator()
        if not orchestrator:
            return {"ok": False, "error": "Failed to initialize turn engine"}

        from ..state.schemas.action import Action
        from ..systems.turns import TurnError, TurnPhase

        if orchestrator.phase != TurnPhase.PROPOSED:
            return {
                "ok": False,
                "error": f"No pending proposal (current phase: {orchestrator.phase.value})",
            }

        try:
            # Build action from the pending proposal
            proposal = orchestrator._current_proposal
            if not proposal:
                return {"ok": False, "error": "No proposal in progress"}

            action = Action.from_proposal(
                proposal,
                state_version=campaign.state_version,
                chosen_alternative=via,
            )

            result = orchestrator.commit(action)

            # Serialize TurnResult for JSON transport
            return {
                "ok": True,
                "turn_result": {
                    "action_id": result.action_id,
                    "success": result.success,
                    "state_version": result.state_version,
                    "turn_number": result.turn_number,
                    "events": [
                        {
                            "event_id": e.event_id,
                            "event_type": e.event_type,
                            "summary": e.summary,
                            "cascade_depth": e.cascade_depth,
                            "payload": e.payload,
                        }
                        for e in result.events
                    ],
                    "cascade_notices": result.cascade_notices,
                    "narrative_hooks": result.narrative_hooks,
                    "state_snapshot": result.state_snapshot,
                },
            }

        except TurnError as e:
            return {"ok": False, "error": str(e)}

    def _cmd_travel_cancel(self) -> dict:
        """Cancel the pending travel proposal — zero side effects."""
        orchestrator = self._ensure_orchestrator()
        if not orchestrator:
            return {"ok": False, "error": "Failed to initialize turn engine"}

        from ..systems.turns import TurnError, TurnPhase

        if orchestrator.phase != TurnPhase.PROPOSED:
            return {
                "ok": True,
                "message": "No pending proposal to cancel",
            }

        try:
            orchestrator.cancel()
            return {"ok": True, "message": "Travel proposal cancelled"}
        except TurnError as e:
            return {"ok": False, "error": str(e)}

    def _cmd_map_state(self) -> dict:
        """Return complete map state for the world map UI."""
        campaign = self.manager.current
        if not campaign:
            return {"ok": False, "error": "No campaign loaded"}

        from ..state.schema import Region

        # Build per-region state with content markers
        regions_out = {}
        for region in Region:
            region_state = campaign.map_state.regions.get(region)
            connectivity = (
                region_state.connectivity.value
                if region_state
                else "disconnected"
            )

            markers = self._build_content_markers(
                campaign, region
            )

            regions_out[region.value] = {
                "connectivity": connectivity,
                "markers": markers,
            }

        return {
            "ok": True,
            "current_region": campaign.map_state.current_region.value,
            "regions": regions_out,
        }

    def _cmd_map_region(self, region_id: str) -> dict:
        """Return detailed info for a specific region."""
        campaign = self.manager.current
        if not campaign:
            return {"ok": False, "error": "No campaign loaded"}

        from ..state.schema import Region

        # Validate region
        try:
            region = Region(region_id)
        except ValueError:
            return {
                "ok": False,
                "error": f"Unknown region: {region_id}",
            }

        # Load static region data
        all_regions = self._load_regions_data()
        if all_regions is None:
            return {
                "ok": False,
                "error": "Failed to load region data",
            }

        static = all_regions.get(region_id, {})
        if not static:
            return {
                "ok": False,
                "error": f"No data for region: {region_id}",
            }

        # Region connectivity
        region_state = campaign.map_state.regions.get(region)
        connectivity = (
            region_state.connectivity.value
            if region_state
            else "disconnected"
        )

        # Build route feasibility from current region
        current_id = campaign.map_state.current_region.value
        current_static = all_regions.get(current_id, {})
        current_routes = current_static.get("routes", {})

        routes_from_current = []
        if region_id in current_routes:
            route = self._build_route_feasibility(
                campaign,
                current_id,
                region_id,
                current_routes[region_id],
            )
            routes_from_current.append(route)

        # Content in this region
        npc_names = [
            npc.name for npc in campaign.npcs.active
            if getattr(npc, "location", None) == region_id
        ]
        job_titles = [
            job.title for job in campaign.jobs.active
            if job.region and job.region == region
        ]
        thread_ids = [
            t.id for t in campaign.dormant_threads
            if self._thread_matches_region(t, region_id)
        ]

        return {
            "ok": True,
            "region": {
                "id": region_id,
                "name": static.get("name", ""),
                "description": static.get("description", ""),
                "primary_faction": static.get(
                    "primary_faction", ""
                ),
                "contested_by": static.get("contested_by", []),
                "terrain": static.get("terrain", []),
                "character": static.get("character", ""),
                "connectivity": connectivity,
                "position": static.get(
                    "position", {"x": 50, "y": 50}
                ),
            },
            "routes_from_current": routes_from_current,
            "content": {
                "npcs": npc_names,
                "jobs": job_titles,
                "threads": thread_ids,
            },
        }

    # ── Map helpers ─────────────────────────────────────────

    def _load_regions_data(self) -> dict | None:
        """Load static region data from regions.json."""
        import json
        from pathlib import Path

        data_dir = (
            Path(__file__).parent.parent.parent / "data"
        )
        regions_file = data_dir / "regions.json"
        try:
            with open(regions_file) as f:
                return json.load(f)["regions"]
        except Exception:
            return None

    def _build_content_markers(
        self, campaign, region
    ) -> list[dict]:
        """Build content marker list for a region."""
        markers = []

        if campaign.map_state.current_region == region:
            markers.append({"type": "current"})

        npc_count = sum(
            1 for npc in campaign.npcs.active
            if getattr(npc, "location", None) == region.value
        )
        if npc_count > 0:
            markers.append({"type": "npc", "count": npc_count})

        job_count = sum(
            1 for job in campaign.jobs.active
            if job.region and job.region == region
        )
        if job_count > 0:
            markers.append({"type": "job", "count": job_count})

        thread_count = sum(
            1 for t in campaign.dormant_threads
            if self._thread_matches_region(t, region.value)
        )
        if thread_count > 0:
            markers.append(
                {"type": "thread", "count": thread_count}
            )

        return markers

    @staticmethod
    def _thread_matches_region(thread, region_id: str) -> bool:
        """Check if a dormant thread's trigger mentions a region."""
        trigger = thread.trigger_condition.lower()
        return (
            region_id in trigger
            or region_id.replace("_", " ") in trigger
        )

    def _build_route_feasibility(
        self, campaign, from_id: str, to_id: str, route_data: dict
    ) -> dict:
        """
        Build route feasibility result for travel from one
        region to another.

        Returns a dict with requirements, alternatives,
        traversability, and best travel option.
        """
        requirements = []
        all_met = True

        for req in route_data.get("requirements", []):
            result = self._evaluate_route_requirement(
                campaign, req
            )
            requirements.append(result)
            if not result["met"]:
                all_met = False

        alternatives = []
        for alt in route_data.get("alternatives", []):
            alt_out = {
                "type": alt.get("type", "unknown"),
                "description": alt.get("description", ""),
            }
            if "cost" in alt:
                alt_out["cost"] = alt["cost"]
            if "consequence" in alt:
                alt_out["consequence"] = alt["consequence"]
            alt_out["available"] = True
            alternatives.append(alt_out)

        traversable = all_met or len(alternatives) > 0

        if all_met:
            best = "direct"
        elif alternatives:
            best = "alternative"
        else:
            best = "blocked"

        return {
            "from": from_id,
            "to": to_id,
            "requirements": requirements,
            "alternatives": alternatives,
            "traversable": traversable,
            "best_option": best,
        }

    def _evaluate_route_requirement(
        self, campaign, req: dict
    ) -> dict:
        """Evaluate a single route requirement against campaign state."""
        req_type = req.get("type", "unknown")
        result = {"type": req_type}

        if req_type == "faction":
            faction_id = req.get("faction", "")
            min_standing = req.get("min_standing", "neutral")
            result["faction"] = faction_id
            result["min_standing"] = min_standing
            result["met"] = self._check_faction_standing(
                campaign, faction_id, min_standing
            )
        elif req_type == "vehicle":
            capability = req.get("capability", "")
            result["vehicle_capability"] = capability
            result["met"] = self._check_vehicle_requirement(
                campaign, capability
            )
        else:
            result["met"] = False

        return result

    @staticmethod
    def _check_faction_standing(
        campaign, faction_id: str, min_standing: str
    ) -> bool:
        """Check if the player meets a faction standing requirement."""
        from ..state.schema import FactionName

        standing_order = [
            "Hostile", "Unfriendly", "Neutral",
            "Friendly", "Allied",
        ]
        try:
            name = faction_id.replace("_", " ").title()
            faction_enum = FactionName(name)
            player = campaign.factions.get(faction_enum)
            player_idx = standing_order.index(
                player.standing.value
            )
            req_idx = standing_order.index(
                min_standing.title()
            )
            return player_idx >= req_idx
        except (ValueError, KeyError, AttributeError):
            return False

    @staticmethod
    def _check_vehicle_requirement(
        campaign, capability: str
    ) -> bool:
        """Check if the player has a vehicle with the required capability."""
        if not campaign.characters:
            return False
        char = campaign.characters[0]
        return any(
            capability in v.terrain
            or capability in v.unlocks_tags
            for v in char.vehicles
            if v.is_operational
        )

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

        # Track state before command (for detecting changes)
        campaign_before = self.manager.current.meta.id if self.manager.current else None
        session_before = self.manager.current.session is not None if self.manager.current else False

        try:
            # Capture any Rich console output (tables, formatted text)
            # so it doesn't pollute the JSON stream
            with capture_console_output() as buffer:
                # cmd_obj is a Command dataclass with a .handler attribute
                result = cmd_obj.handler(self.manager, self.agent, args)

            # Sync conversation if campaign or session state changed
            # CLI handlers don't have access to self.conversation, so we sync here
            # Triggers on: /load, /start, /new (campaign change), /debrief (session ends),
            #              /conversation clear (explicit clear)
            campaign_after = self.manager.current.meta.id if self.manager.current else None
            session_after = self.manager.current.session is not None if self.manager.current else False

            should_sync = (
                campaign_after != campaign_before or  # Campaign changed
                (session_before and not session_after) or  # Session ended (e.g., /debrief)
                command in ("/conversation",)  # Explicit conversation management
            )

            if should_sync:
                self._sync_conversation_from_campaign()

            # Get captured console output (strip ANSI codes for clean text)
            console_output = buffer.getvalue().strip()

            # Handle backend switch - result contains new backend name
            if command == "/backend" and result and isinstance(result, str):
                new_backend = result
                # Save preference
                set_backend(new_backend, self.campaigns_dir)
                # Recreate agent with new backend
                self.agent = SentinelAgent(
                    self.manager,
                    prompts_dir=self.prompts_dir,
                    lore_dir=self.lore_dir,
                    backend=new_backend,
                    local_mode=self.agent.local_mode,
                )
                return {
                    "ok": True,
                    "result": f"Switched to {new_backend}",
                    "backend": self.agent.backend_info,
                }

            # Handle GM prompt - commands like /start return ("gm_prompt", text)
            # which means "send this to the agent and return the response"
            if isinstance(result, tuple) and len(result) == 2 and result[0] == "gm_prompt":
                gm_prompt = result[1]
                if self.agent.is_available:
                    try:
                        gm_response = self.agent.respond(gm_prompt, self.conversation)
                        self.conversation.append(Message(role="user", content=gm_prompt))
                        self.conversation.append(Message(role="assistant", content=gm_response))
                        return {
                            "ok": True,
                            "response": gm_response,
                            "output": console_output if console_output else None,
                        }
                    except Exception as e:
                        return {"ok": False, "error": f"Agent error: {e}"}
                else:
                    return {
                        "ok": False,
                        "error": "No LLM backend available",
                        "output": console_output if console_output else None,
                    }

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

            # Restore conversation from session state (mid-mission persistence)
            if self.manager.current and self.manager.current.session:
                from ..llm.base import dict_to_message
                self.conversation = [
                    dict_to_message(d)
                    for d in self.manager.current.session.conversation_log
                ]
            else:
                self.conversation = []

            return {
                "ok": True,
                "campaign": {
                    "id": self.manager.current.meta.id,
                    "name": self.manager.current.meta.name,
                    "session": self.manager.current.meta.session_count,
                },
                "conversation_restored": len(self.conversation),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def _cmd_save(self) -> dict:
        """Save current campaign to disk."""
        if not self.manager.current:
            return {"ok": False, "error": "No campaign loaded"}

        try:
            # Sync conversation to session state before saving
            self._sync_conversation_to_session()

            result = self.manager.persist_campaign()
            response = {"ok": result.get("success", False)}

            # Build output message
            output_lines = ["Campaign saved!"]

            # Include character stubs in response (as filenames)
            if result.get("character_stubs"):
                stubs = [p.name for p in result["character_stubs"]]
                response["character_stubs"] = stubs
                output_lines.append("Created character stubs for portrait generation:")
                for stub in stubs:
                    output_lines.append(f"  • {stub}")

            # Report synced portraits
            sync = result.get("portraits_synced", {})
            synced_count = len(sync.get("copied_to_webui", [])) + len(sync.get("copied_to_wiki", []))
            if synced_count > 0:
                output_lines.append(f"Synced {synced_count} portrait(s) to web UI and wiki")

            response["output"] = "\n".join(output_lines)
            return response
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _sync_conversation_from_campaign(self) -> None:
        """
        Sync conversation from the currently loaded campaign's session state.

        Called after commands that might change the loaded campaign (e.g., /load, /start, /new)
        to ensure self.conversation matches the campaign's saved conversation_log.

        This is needed because CLI command handlers don't have access to self.conversation -
        they only operate on the manager. Without this sync, switching campaigns would leave
        stale conversation data from the previous campaign.
        """
        if self.manager.current and self.manager.current.session:
            from ..llm.base import dict_to_message
            self.conversation = [
                dict_to_message(d)
                for d in self.manager.current.session.conversation_log
            ]
        else:
            # No session or no campaign - start fresh
            self.conversation = []

    def _sync_conversation_to_session(self, max_messages: int = 50) -> None:
        """
        Sync in-memory conversation to session state for mid-mission persistence.

        Limits to recent messages to prevent JSON bloat (~25KB max).
        Only syncs if there's an active session (mid-mission).
        """
        if not self.manager.current or not self.manager.current.session:
            return

        from ..llm.base import message_to_dict

        # Keep only the most recent messages
        messages_to_save = self.conversation[-max_messages:]
        self.manager.current.session.conversation_log = [
            message_to_dict(msg) for msg in messages_to_save
        ]
    
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
