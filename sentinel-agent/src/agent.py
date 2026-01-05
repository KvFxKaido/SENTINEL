"""
SENTINEL Agent Orchestrator.

Coordinates LLM calls with game state and tools.
Supports multiple backends: LM Studio (local), Claude (API).
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal
from concurrent.futures import ThreadPoolExecutor, as_completed

from .state import CampaignManager, Campaign
from .state.schema import FactionName, HistoryType, LeverageWeight
from .tools.dice import roll_check, tactical_reset, TOOL_SCHEMAS
from .tools.hinge_detector import detect_hinge, get_hinge_context
from .llm.base import LLMClient, Message
from .llm import create_llm_client
from .lore import LoreRetriever


@dataclass
class AdvisorResponse:
    """Response from a single advisor."""
    advisor: str  # "nexus", "ember", "witness"
    title: str  # Display name
    response: str
    error: str | None = None


class PromptLoader:
    """
    Hot-reloadable prompt loader.

    Loads prompt modules from disk and assembles them into system prompts.
    """

    def __init__(self, prompts_dir: Path | str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self._cache: dict[str, str] = {}
        self._cache_times: dict[str, float] = {}

    def load(self, name: str) -> str:
        """Load a prompt module, using cache if file unchanged."""
        path = self.prompts_dir / f"{name}.md"

        if not path.exists():
            return ""

        mtime = path.stat().st_mtime

        # Check cache
        if name in self._cache and self._cache_times.get(name) == mtime:
            return self._cache[name]

        # Load fresh
        content = path.read_text(encoding="utf-8")
        self._cache[name] = content
        self._cache_times[name] = mtime

        return content

    def assemble_system_prompt(
        self,
        campaign: Campaign | None = None,
        manager: "CampaignManager | None" = None,
    ) -> str:
        """Assemble the full system prompt from modules."""
        parts = [
            self.load("core"),
            self.load("mechanics"),
            self.load("gm_guidance"),
        ]

        # Add phase-specific guidance if in active session
        if campaign and campaign.session:
            phase_guidance = self.load_phase(campaign.session.phase.value)
            if phase_guidance:
                parts.append(phase_guidance)

        # Add campaign state if available
        if campaign:
            parts.append(self._format_state_summary(campaign, manager))

        return "\n\n---\n\n".join(filter(None, parts))

    def load_advisor(self, advisor: str) -> str:
        """Load an advisor prompt."""
        path = self.prompts_dir / "advisors" / f"{advisor}.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def load_phase(self, phase: str) -> str:
        """Load phase-specific GM guidance."""
        path = self.prompts_dir / "phases" / f"{phase}.md"
        if not path.exists():
            return ""

        # Use caching like other loaders
        cache_key = f"phase_{phase}"
        mtime = path.stat().st_mtime

        if cache_key in self._cache and self._cache_times.get(cache_key) == mtime:
            return self._cache[cache_key]

        content = path.read_text(encoding="utf-8")
        self._cache[cache_key] = content
        self._cache_times[cache_key] = mtime

        return content

    def _format_state_summary(
        self, campaign: Campaign, manager: "CampaignManager | None" = None
    ) -> str:
        """Format current campaign state for injection."""
        lines = [
            "# Current State",
            "",
            f"**Campaign:** {campaign.meta.name}",
            f"**Phase:** {campaign.meta.phase} | **Sessions:** {campaign.meta.session_count}",
        ]

        # Characters
        if campaign.characters:
            lines.append("\n**Party:**")
            for char in campaign.characters:
                energy = char.social_energy
                warning = f" (Warning: {energy.state})" if energy.current < 51 else ""
                lines.append(
                    f"- {char.name} ({char.background.value}): "
                    f"{char.credits}cr, {energy.name} {energy.current}%{warning}"
                )

                # Show enhancements with leverage status
                if char.enhancements:
                    for enh in char.enhancements:
                        lev = enh.leverage
                        status_parts = [f"{enh.source.value}"]
                        status_parts.append(f"weight: {lev.weight.value}")
                        # Check for demand (new) or obligation (legacy)
                        if lev.pending_demand:
                            status_parts.append("HAS PENDING DEMAND")
                        elif lev.pending_obligation:
                            status_parts.append(f"PENDING: \"{lev.pending_obligation}\"")
                        if lev.compliance_count or lev.resistance_count:
                            status_parts.append(
                                f"history: {lev.compliance_count}C/{lev.resistance_count}R"
                            )
                        lines.append(f"  → Enhancement: {enh.name} ({', '.join(status_parts)})")

                # Show refusal reputation if any
                if char.refused_enhancements and manager:
                    rep = manager.get_refusal_reputation(char.id)
                    if rep and rep["count"] > 0:
                        if rep["title"]:
                            lines.append(f"  → Reputation: \"{rep['title']}\" ({rep['count']} refusals)")
                        else:
                            lines.append(f"  → Refusals: {rep['count']}")
                        if rep["narrative_hint"]:
                            lines.append(f"    {rep['narrative_hint']}")

        # Active NPCs
        if campaign.npcs.active:
            lines.append("\n**Active NPCs:**")
            for npc in campaign.npcs.active:
                memories = ", ".join(npc.remembers[-3:]) if npc.remembers else "none"
                lines.append(
                    f"- {npc.name}: wants '{npc.agenda.wants}', "
                    f"fears '{npc.agenda.fears}' | "
                    f"Disposition: {npc.disposition.value} | "
                    f"Remembers: {memories}"
                )

                # Include disposition-based behavior guidance
                modifier = npc.get_current_modifier()
                if modifier:
                    lines.append(f"  → Tone: {modifier.tone}")
                    if modifier.reveals:
                        lines.append(f"  → Will reveal: {', '.join(modifier.reveals)}")
                    if modifier.withholds:
                        lines.append(f"  → Withholds: {', '.join(modifier.withholds)}")
                    if modifier.tells:
                        lines.append(f"  → Tells: {', '.join(modifier.tells)}")

        # Faction tensions
        tensions = []
        for faction in FactionName:
            standing = campaign.factions.get(faction)
            if standing.standing.value != "Neutral":
                tensions.append(f"{faction.value}: {standing.standing.value}")

        if tensions:
            lines.append(f"\n**Faction Tensions:** {', '.join(tensions)}")

        # Dormant threads - show all for GM awareness
        if campaign.dormant_threads:
            lines.append("\n**Dormant Threads:**")

            # Group by severity
            by_severity = {"major": [], "moderate": [], "minor": []}
            for thread in campaign.dormant_threads:
                by_severity[thread.severity.value].append(thread)

            # MAJOR: full details
            for thread in by_severity["major"]:
                age = campaign.meta.session_count - thread.created_session
                lines.append(f"  [MAJOR] {thread.id}: \"{thread.trigger_condition}\"")
                consequence_preview = thread.consequence[:60]
                if len(thread.consequence) > 60:
                    consequence_preview += "..."
                lines.append(f"    → {consequence_preview}")
                lines.append(f"    (from: {thread.origin}, age: {age} sessions)")

            # Moderate: one line each
            for thread in by_severity["moderate"]:
                lines.append(f"  [mod] {thread.id}: \"{thread.trigger_condition}\"")

            # Minor: count only
            if by_severity["minor"]:
                lines.append(f"  + {len(by_severity['minor'])} minor threads")

        # Pending avoidances (non-action consequences waiting to surface)
        pending_avoidances = [a for a in campaign.avoided_situations if not a.surfaced]
        if pending_avoidances:
            lines.append("\n**Pending Avoidances** (non-action consequences):")
            for avoided in pending_avoidances:
                age = campaign.meta.session_count - avoided.created_session
                overdue = " [OVERDUE]" if age >= 3 else ""
                lines.append(
                    f"  [{avoided.severity.value.upper()}]{overdue} {avoided.id}: "
                    f"\"{avoided.situation}\""
                )
                lines.append(f"    → If surfaced: {avoided.potential_consequence}")

        # Pending leverage demands (using get_pending_demands from manager)
        pending_demands = manager.get_pending_demands() if manager else []
        if pending_demands:
            lines.append("\n**Pending Leverage Demands:**")
            for demand in pending_demands:
                urgency_marker = {
                    "critical": "[OVERDUE]",
                    "urgent": "[URGENT]",
                    "pending": "",
                }.get(demand["urgency"], "")
                lines.append(
                    f"  {urgency_marker} {demand['faction']} via {demand['enhancement_name']}: "
                    f"\"{demand['demand']}\""
                )
                if demand.get("deadline"):
                    lines.append(f"    Deadline: {demand['deadline']}")
                if demand.get("threat_basis"):
                    lines.append(f"    Threat basis: {', '.join(demand['threat_basis'])}")
                if demand.get("consequences"):
                    lines.append(f"    If ignored: {'; '.join(demand['consequences'])}")

        # Current mission
        if campaign.session:
            lines.append(
                f"\n**Mission:** {campaign.session.mission_title} "
                f"({campaign.session.phase.value})"
            )

        return "\n".join(lines)


class SentinelAgent:
    """
    The SENTINEL Game Master agent.

    Coordinates LLM backend, game state, and tool execution.

    Can be initialized with:
    - An explicit LLMClient (for testing or custom backends)
    - A backend name for auto-creation via create_llm_client()
    """

    # Supported backends
    BACKENDS = ["lmstudio", "claude", "openrouter", "gemini", "codex", "auto"]

    def __init__(
        self,
        campaign_manager: CampaignManager,
        prompts_dir: Path | str = "prompts",
        lore_dir: Path | str | None = None,
        client: LLMClient | None = None,
        backend: str = "auto",
        lmstudio_url: str = "http://localhost:1234/v1",
        claude_model: str = "claude-sonnet-4-20250514",
        openrouter_model: str = "claude-3.5-sonnet",
    ):
        """
        Initialize the SENTINEL agent.

        Args:
            campaign_manager: Manager for campaign state
            prompts_dir: Directory containing prompt modules
            lore_dir: Directory containing lore documents (optional)
            client: Pre-configured LLM client (overrides backend param)
            backend: Backend to use if no client provided ("auto" for detection)
            lmstudio_url: URL for LM Studio server
            claude_model: Model name for Claude API
            openrouter_model: Model name for OpenRouter
        """
        self.manager = campaign_manager
        self.prompt_loader = PromptLoader(prompts_dir)

        # Store config for backend switching
        self._config = {
            "lmstudio_url": lmstudio_url,
            "claude_model": claude_model,
            "openrouter_model": openrouter_model,
        }

        # Initialize lore retriever if lore_dir provided
        self.lore_retriever: LoreRetriever | None = None
        if lore_dir:
            lore_path = Path(lore_dir)
            if lore_path.exists():
                self.lore_retriever = LoreRetriever(lore_path)

        # Tool registry
        self.tools: dict[str, Callable] = {
            "roll_check": self._handle_roll_check,
            "tactical_reset": self._handle_tactical_reset,
            "update_character": self._handle_update_character,
            "update_faction": self._handle_update_faction,
            "update_npc": self._handle_update_npc,
            "trigger_npc_memory": self._handle_trigger_memory,
            "log_hinge_moment": self._handle_log_hinge,
            "queue_dormant_thread": self._handle_queue_thread,
            "surface_dormant_thread": self._handle_surface_thread,
            "grant_enhancement": self._handle_grant_enhancement,
            "refuse_enhancement": self._handle_refuse_enhancement,
            "call_leverage": self._handle_call_leverage,
            "escalate_demand": self._handle_escalate_demand,
            "resolve_leverage": self._handle_resolve_leverage,
            "log_avoidance": self._handle_log_avoidance,
            "surface_avoidance": self._handle_surface_avoidance,
            "invoke_restorer": self._handle_invoke_restorer,
            "declare_push": self._handle_declare_push,
            "set_phase": self._handle_set_phase,
        }

        # Initialize client
        if client is not None:
            # Use injected client directly
            self.client = client
            self.backend = backend if backend != "auto" else "injected"
        else:
            # Create client via factory
            self.backend, self.client = create_llm_client(
                backend=backend,
                lmstudio_url=lmstudio_url,
                claude_model=claude_model,
                openrouter_model=openrouter_model,
            )

    @property
    def is_available(self) -> bool:
        """Check if an LLM backend is available."""
        return self.client is not None

    @property
    def backend_info(self) -> dict:
        """Get info about the current backend."""
        if not self.client:
            return {"available": False, "backend": None}

        return {
            "available": True,
            "backend": self.backend,
            "model": self.client.model_name,
            "supports_tools": self.client.supports_tools,
        }

    def get_tools(self) -> list[dict]:
        """Get all tool schemas for the API."""
        return TOOL_SCHEMAS + [
            {
                "name": "update_character",
                "description": "Modify character state (credits, social energy)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string"},
                        "credits_delta": {"type": "integer", "default": 0},
                        "social_energy_delta": {"type": "integer", "default": 0},
                    },
                    "required": ["character_id"],
                },
            },
            {
                "name": "update_faction",
                "description": "Shift faction standing",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "faction": {
                            "type": "string",
                            "enum": [f.value for f in FactionName],
                        },
                        "delta": {
                            "type": "integer",
                            "enum": [-2, -1, 1],
                            "description": "-2=betray, -1=oppose, +1=help",
                        },
                        "reason": {"type": "string"},
                    },
                    "required": ["faction", "delta", "reason"],
                },
            },
            {
                "name": "log_hinge_moment",
                "description": "Record an irreversible choice",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "situation": {"type": "string"},
                        "choice": {"type": "string"},
                        "reasoning": {"type": "string"},
                    },
                    "required": ["situation", "choice", "reasoning"],
                },
            },
            {
                "name": "queue_dormant_thread",
                "description": "Schedule a delayed consequence",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "origin": {"type": "string"},
                        "trigger_condition": {"type": "string"},
                        "consequence": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["minor", "moderate", "major"],
                            "default": "moderate",
                        },
                    },
                    "required": ["origin", "trigger_condition", "consequence"],
                },
            },
            {
                "name": "update_npc",
                "description": "Update NPC disposition or add memory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "npc_id": {"type": "string"},
                        "disposition": {
                            "type": "string",
                            "enum": ["hostile", "wary", "neutral", "warm", "loyal"],
                        },
                        "memory": {
                            "type": "string",
                            "description": "New memory to add (what the NPC now remembers)",
                        },
                    },
                    "required": ["npc_id"],
                },
            },
            {
                "name": "trigger_npc_memory",
                "description": "Fire NPC memory triggers based on event tags",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Event tags like 'helped_ember', 'betrayed_lattice', 'knows_secret'",
                        },
                    },
                    "required": ["tags"],
                },
            },
            {
                "name": "surface_dormant_thread",
                "description": "Activate a dormant thread when its trigger condition is met. Logs to history and removes from pending.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "thread_id": {
                            "type": "string",
                            "description": "ID of the dormant thread to surface",
                        },
                        "activation_context": {
                            "type": "string",
                            "description": "What player action triggered this consequence",
                        },
                    },
                    "required": ["thread_id", "activation_context"],
                },
            },
            {
                "name": "grant_enhancement",
                "description": "Grant a faction enhancement to a character. Creates leverage tracking. Wanderers and Cultivators don't offer enhancements.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string"},
                        "name": {
                            "type": "string",
                            "description": "Enhancement name (e.g., 'Neural Interface', 'Syndicate Debt Chip')",
                        },
                        "source": {
                            "type": "string",
                            "enum": [f.value for f in FactionName if f not in (
                                FactionName.WANDERERS, FactionName.CULTIVATORS
                            )],
                            "description": "Faction granting the enhancement",
                        },
                        "benefit": {
                            "type": "string",
                            "description": "What the enhancement provides",
                        },
                        "cost": {
                            "type": "string",
                            "description": "The strings attached",
                        },
                    },
                    "required": ["character_id", "name", "source", "benefit", "cost"],
                },
            },
            {
                "name": "refuse_enhancement",
                "description": "Record when a character refuses an enhancement offer. Refusal builds reputation that NPCs react to.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string"},
                        "name": {
                            "type": "string",
                            "description": "Enhancement name that was offered",
                        },
                        "source": {
                            "type": "string",
                            "enum": [f.value for f in FactionName],
                            "description": "Faction that offered the enhancement",
                        },
                        "benefit": {
                            "type": "string",
                            "description": "What the enhancement would have provided",
                        },
                        "reason_refused": {
                            "type": "string",
                            "description": "Why the character refused (in their words)",
                        },
                    },
                    "required": ["character_id", "name", "source", "benefit", "reason_refused"],
                },
            },
            {
                "name": "call_leverage",
                "description": "A faction calls in leverage on an enhancement they granted. Creates a formal demand the player must respond to.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string"},
                        "enhancement_id": {"type": "string"},
                        "demand": {
                            "type": "string",
                            "description": "What the faction is demanding",
                        },
                        "weight": {
                            "type": "string",
                            "enum": ["light", "medium", "heavy"],
                            "default": "medium",
                            "description": "Pressure level: light (subtle), medium (direct), heavy (ultimatum)",
                        },
                        "threat_basis": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Why the faction has leverage: info they know ('Sector 7 incident') or functional control ('neural interface access')",
                        },
                        "deadline": {
                            "type": "string",
                            "description": "Narrative deadline ('Before the convoy leaves', 'By tomorrow')",
                        },
                        "deadline_sessions": {
                            "type": "integer",
                            "description": "Sessions until must resolve (e.g., 2 means deadline in 2 sessions)",
                        },
                        "consequences": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "What happens if the player refuses or ignores the demand",
                        },
                    },
                    "required": ["character_id", "enhancement_id", "demand"],
                },
            },
            {
                "name": "escalate_demand",
                "description": "Escalate an unresolved leverage demand. Use when deadline passes or player ignores faction pressure.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string"},
                        "enhancement_id": {"type": "string"},
                        "escalation_type": {
                            "type": "string",
                            "enum": ["queue_consequence", "increase_weight", "faction_action"],
                            "description": "queue_consequence: create dormant thread; increase_weight: bump pressure; faction_action: log faction taking action",
                        },
                        "narrative": {
                            "type": "string",
                            "description": "What the faction does in response (for faction_action type)",
                        },
                    },
                    "required": ["character_id", "enhancement_id", "escalation_type"],
                },
            },
            {
                "name": "resolve_leverage",
                "description": "Record player's response to a leverage call. Comply reduces future pressure, resist escalates it.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string"},
                        "enhancement_id": {"type": "string"},
                        "response": {
                            "type": "string",
                            "enum": ["comply", "resist", "negotiate"],
                            "description": "How the player responded",
                        },
                        "outcome": {
                            "type": "string",
                            "description": "Narrative description of what happened",
                        },
                    },
                    "required": ["character_id", "enhancement_id", "response", "outcome"],
                },
            },
            {
                "name": "log_avoidance",
                "description": "Record when a player chooses not to engage with a significant situation. Non-action is content — the world doesn't wait.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "situation": {
                            "type": "string",
                            "description": "What was presented that they avoided",
                        },
                        "what_was_at_stake": {
                            "type": "string",
                            "description": "What they were avoiding (confrontation, decision, commitment)",
                        },
                        "potential_consequence": {
                            "type": "string",
                            "description": "What may happen because they didn't act",
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["minor", "moderate", "major"],
                            "default": "moderate",
                        },
                    },
                    "required": ["situation", "what_was_at_stake", "potential_consequence"],
                },
            },
            {
                "name": "surface_avoidance",
                "description": "Mark an avoidance as surfaced when its consequences come due. Logs to history.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "avoidance_id": {
                            "type": "string",
                            "description": "ID of the avoided situation",
                        },
                        "what_happened": {
                            "type": "string",
                            "description": "How the consequence manifested",
                        },
                    },
                    "required": ["avoidance_id", "what_happened"],
                },
            },
            {
                "name": "invoke_restorer",
                "description": "Spend 10% social energy to gain advantage when acting in your element. Only works if the action matches one of the character's restorers.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string"},
                        "action": {
                            "type": "string",
                            "description": "What the character is doing (must align with their restorers)",
                        },
                    },
                    "required": ["character_id", "action"],
                },
            },
            {
                "name": "declare_push",
                "description": "Player explicitly invites a consequence for advantage. Use when player accepts a Devil's Bargain. Queues a dormant thread with the consequence.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "character_id": {"type": "string"},
                        "goal": {
                            "type": "string",
                            "description": "What they're pushing for (e.g., 'to convince the guard')",
                        },
                        "consequence": {
                            "type": "string",
                            "description": "What will happen later as a result of the push",
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["minor", "moderate", "major"],
                            "default": "moderate",
                        },
                    },
                    "required": ["character_id", "goal", "consequence"],
                },
            },
            {
                "name": "set_phase",
                "description": "Advance the mission phase. Each phase changes GM guidance: briefing (present situation), planning (support strategy), execution (complications arise), resolution (land consequences), debrief (four questions), between (downtime).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "phase": {
                            "type": "string",
                            "enum": ["briefing", "planning", "execution", "resolution", "debrief", "between"],
                            "description": "The phase to transition to",
                        },
                    },
                    "required": ["phase"],
                },
            },
        ]

    # -------------------------------------------------------------------------
    # Tool Handlers
    # -------------------------------------------------------------------------

    def _handle_roll_check(self, **kwargs) -> dict:
        """Handle roll_check tool call."""
        result = roll_check(**kwargs)
        return {
            "rolls": result.rolls,
            "used": result.used,
            "modifier": result.modifier,
            "total": result.total,
            "dc": result.dc,
            "success": result.success,
            "margin": result.margin,
            "narrative": result.narrative,
        }

    def _handle_tactical_reset(self, **kwargs) -> dict:
        """Handle tactical_reset tool call."""
        result = tactical_reset(**kwargs)
        return {
            "old_energy": result.old_energy,
            "new_energy": result.new_energy,
            "advantage_granted": result.advantage_granted,
            "narrative_hint": result.narrative_hint,
        }

    def _handle_invoke_restorer(self, **kwargs) -> dict:
        """Handle invoke_restorer tool call."""
        return self.manager.invoke_restorer(
            character_id=kwargs["character_id"],
            action=kwargs["action"],
        )

    def _handle_declare_push(self, **kwargs) -> dict:
        """Handle declare_push tool call."""
        return self.manager.declare_push(
            character_id=kwargs["character_id"],
            goal=kwargs["goal"],
            consequence=kwargs["consequence"],
            severity=kwargs.get("severity", "moderate"),
        )

    def _handle_set_phase(self, **kwargs) -> dict:
        """Handle set_phase tool call."""
        return self.manager.set_phase(phase=kwargs["phase"])

    def _handle_update_character(self, **kwargs) -> dict:
        """Handle update_character tool call."""
        result = self.manager.update_character(
            character_id=kwargs["character_id"],
            credits_delta=kwargs.get("credits_delta", 0),
            social_energy_delta=kwargs.get("social_energy_delta", 0),
        )
        return result or {"error": "Character not found"}

    def _handle_update_faction(self, **kwargs) -> dict:
        """Handle update_faction tool call."""
        faction = FactionName(kwargs["faction"])
        return self.manager.shift_faction(
            faction=faction,
            delta=kwargs["delta"],
            reason=kwargs["reason"],
        )

    def _handle_update_npc(self, **kwargs) -> dict:
        """Handle update_npc tool call."""
        npc_id = kwargs["npc_id"]
        results = {}

        # Update disposition if provided
        if "disposition" in kwargs:
            disp_result = self.manager.update_npc_disposition(
                npc_id=npc_id,
                disposition=kwargs["disposition"],
            )
            if disp_result:
                results["disposition"] = disp_result
            else:
                return {"error": f"NPC not found: {npc_id}"}

        # Add memory if provided
        if "memory" in kwargs:
            success = self.manager.update_npc_memory(npc_id, kwargs["memory"])
            results["memory_added"] = success

        if not results:
            return {"error": "No updates specified"}

        return results

    def _handle_trigger_memory(self, **kwargs) -> dict:
        """Handle trigger_npc_memory tool call."""
        tags = kwargs["tags"]
        triggered = self.manager.check_npc_triggers(tags)
        return {
            "tags_checked": tags,
            "triggered_count": len(triggered),
            "reactions": triggered,
        }

    def _handle_log_hinge(self, **kwargs) -> dict:
        """Handle log_hinge_moment tool call."""
        entry = self.manager.log_hinge_moment(
            situation=kwargs["situation"],
            choice=kwargs["choice"],
            reasoning=kwargs["reasoning"],
        )
        return {"id": entry.id, "logged": True}

    def _handle_queue_thread(self, **kwargs) -> dict:
        """Handle queue_dormant_thread tool call."""
        thread = self.manager.queue_dormant_thread(
            origin=kwargs["origin"],
            trigger_condition=kwargs["trigger_condition"],
            consequence=kwargs["consequence"],
            severity=kwargs.get("severity", "moderate"),
        )
        return {"id": thread.id, "queued": True}

    def _handle_surface_thread(self, **kwargs) -> dict:
        """Handle surface_dormant_thread tool call."""
        thread = self.manager.surface_dormant_thread(
            thread_id=kwargs["thread_id"],
            activation_context=kwargs["activation_context"],
        )
        if thread:
            return {
                "surfaced": True,
                "consequence": thread.consequence,
                "severity": thread.severity.value,
                "origin": thread.origin,
            }
        return {"error": f"Thread not found: {kwargs['thread_id']}"}

    def _handle_grant_enhancement(self, **kwargs) -> dict:
        """Handle grant_enhancement tool call."""
        try:
            source = FactionName(kwargs["source"])
            enhancement = self.manager.grant_enhancement(
                character_id=kwargs["character_id"],
                name=kwargs["name"],
                source=source,
                benefit=kwargs["benefit"],
                cost=kwargs["cost"],
            )
            return {
                "id": enhancement.id,
                "name": enhancement.name,
                "source": enhancement.source.value,
                "benefit": enhancement.benefit,
                "cost": enhancement.cost,
                "granted": True,
                "narrative_hint": f"Accepted {source.value} enhancement. They won't forget.",
            }
        except ValueError as e:
            return {"error": str(e)}

    def _handle_refuse_enhancement(self, **kwargs) -> dict:
        """Handle refuse_enhancement tool call."""
        try:
            source = FactionName(kwargs["source"])
            refusal = self.manager.refuse_enhancement(
                character_id=kwargs["character_id"],
                name=kwargs["name"],
                source=source,
                benefit=kwargs["benefit"],
                reason_refused=kwargs["reason_refused"],
            )

            # Get updated reputation
            rep = self.manager.get_refusal_reputation(kwargs["character_id"])

            result = {
                "id": refusal.id,
                "name": refusal.name,
                "source": refusal.source.value,
                "refused": True,
                "reason": refusal.reason_refused,
            }

            if rep:
                result["reputation"] = rep

            return result
        except ValueError as e:
            return {"error": str(e)}

    def _handle_call_leverage(self, **kwargs) -> dict:
        """Handle call_leverage tool call."""
        return self.manager.call_leverage(
            character_id=kwargs["character_id"],
            enhancement_id=kwargs["enhancement_id"],
            demand=kwargs["demand"],
            weight=kwargs.get("weight", "medium"),
            threat_basis=kwargs.get("threat_basis"),
            deadline=kwargs.get("deadline"),
            deadline_sessions=kwargs.get("deadline_sessions"),
            consequences=kwargs.get("consequences"),
        )

    def _handle_escalate_demand(self, **kwargs) -> dict:
        """Handle escalate_demand tool call."""
        return self.manager.escalate_demand(
            character_id=kwargs["character_id"],
            enhancement_id=kwargs["enhancement_id"],
            escalation_type=kwargs["escalation_type"],
            narrative=kwargs.get("narrative", ""),
        )

    def _handle_resolve_leverage(self, **kwargs) -> dict:
        """Handle resolve_leverage tool call."""
        return self.manager.resolve_leverage(
            character_id=kwargs["character_id"],
            enhancement_id=kwargs["enhancement_id"],
            response=kwargs["response"],
            outcome=kwargs["outcome"],
        )

    def _handle_log_avoidance(self, **kwargs) -> dict:
        """Handle log_avoidance tool call."""
        avoided = self.manager.log_avoidance(
            situation=kwargs["situation"],
            what_was_at_stake=kwargs["what_was_at_stake"],
            potential_consequence=kwargs["potential_consequence"],
            severity=kwargs.get("severity", "moderate"),
        )
        return {
            "id": avoided.id,
            "situation": avoided.situation,
            "severity": avoided.severity.value,
            "narrative_hint": "The world moves on. This may resurface.",
        }

    def _handle_surface_avoidance(self, **kwargs) -> dict:
        """Handle surface_avoidance tool call."""
        avoided = self.manager.surface_avoidance(
            avoidance_id=kwargs["avoidance_id"],
            what_happened=kwargs["what_happened"],
        )
        if avoided:
            return {
                "id": avoided.id,
                "situation": avoided.situation,
                "what_happened": kwargs["what_happened"],
                "severity": avoided.severity.value,
            }
        return {"error": "Avoidance not found or already surfaced"}

    def execute_tool(self, name: str, arguments: dict) -> dict:
        """Execute a tool and return the result."""
        if name not in self.tools:
            return {"error": f"Unknown tool: {name}"}

        try:
            return self.tools[name](**arguments)
        except Exception as e:
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # Message Handling
    # -------------------------------------------------------------------------

    def _get_active_factions(self) -> list[str]:
        """Get factions with non-neutral standing."""
        if not self.manager.current:
            return []
        factions = []
        for faction in FactionName:
            standing = self.manager.current.factions.get(faction)
            if standing.standing.value != "Neutral":
                factions.append(faction.value)
        return factions

    def _get_mission_type(self) -> str | None:
        """Get current mission type if any."""
        if self.manager.current and self.manager.current.session:
            return self.manager.current.session.mission_type.value
        return None

    def _format_thread_hints(self, matches: list[dict]) -> str:
        """Format thread match hints for injection into system prompt."""
        lines = [
            "[DORMANT THREAD ALERT]",
            "Player input may trigger dormant consequences:",
            ""
        ]

        for match in matches[:3]:  # Limit to top 3
            lines.append(f"Thread {match['thread_id']} ({match['severity'].upper()}):")
            lines.append(f"  Trigger: \"{match['trigger_condition']}\"")
            lines.append(f"  Keywords matched: {', '.join(match['matched_keywords'])}")
            lines.append(f"  Consequence: {match['consequence']}")
            lines.append(f"  Origin: {match['origin']} ({match['age_sessions']} sessions ago)")
            lines.append("")

        lines.append("If the current situation matches a trigger condition:")
        lines.append("1. Weave the consequence into the narrative naturally")
        lines.append("2. Call surface_dormant_thread(thread_id, activation_context)")
        lines.append("3. Don't announce 'a thread activated' - just let it happen")

        return "\n".join(lines)

    # Faction pressure styles for leverage hints
    FACTION_PRESSURE_STYLES = {
        FactionName.NEXUS: ("clinical", "Our models indicate you could assist with a matter."),
        FactionName.EMBER_COLONIES: ("desperate", "We need you. Our people need you."),
        FactionName.LATTICE: ("technical", "Infrastructure requires your cooperation."),
        FactionName.CONVERGENCE: ("paternalistic", "This is for your own evolution."),
        FactionName.COVENANT: ("ideological", "You swore. Oaths mean something."),
        FactionName.STEEL_SYNDICATE: ("transactional", "Debts are paid. One way or another."),
        FactionName.WITNESSES: ("collegial", "We helped you. Now we need you."),
        FactionName.ARCHITECTS: ("bureaucratic", "Protocol requires your compliance."),
        FactionName.GHOST_NETWORKS: ("reluctant", "We wouldn't ask if there was another way."),
    }

    def _format_leverage_hints(self, hints: list[dict]) -> str:
        """Format leverage hints for injection into system prompt."""
        lines = [
            "[LEVERAGE HINT]",
            "Faction leverage may be relevant to current context:",
            ""
        ]

        for hint in hints[:2]:  # Limit to top 2
            faction = FactionName(hint["faction"])
            style, example = self.FACTION_PRESSURE_STYLES.get(
                faction, ("neutral", "We have a matter to discuss.")
            )

            lines.append(f"Enhancement: {hint['enhancement_name']} ({hint['faction']})")
            lines.append(f"  Character: {hint['character_name']}")
            lines.append(f"  Weight: {hint['weight']} | Hints so far: {hint['hint_count']}")
            lines.append(f"  Sessions since grant: {hint['sessions_since_grant']}")
            lines.append(f"  Compliance history: {hint['compliance_count']} | Resistance: {hint['resistance_count']}")
            lines.append(f"  Style: {style}")
            lines.append(f"  Example tone: \"{example}\"")
            lines.append("")

        lines.append("Consider whether to:")
        lines.append("1. Drop a subtle hint (NPC mentions the faction, reminder of the debt)")
        lines.append("2. Have faction contact appear with a 'request'")
        lines.append("3. If conditions align, call_leverage() to formalize the demand")
        lines.append("")
        lines.append("Three conditions for calling leverage:")
        lines.append("- Faction believes player needs them")
        lines.append("- Faction believes player can't refuse without cost")
        lines.append("- The moment reinforces the faction's worldview")

        return "\n".join(lines)

    def _format_demand_alerts(self, demands: list[dict]) -> str:
        """Format demand deadline alerts for injection into system prompt."""
        lines = [
            "[DEMAND DEADLINE ALERT]",
            "Faction demands require immediate attention:",
            ""
        ]

        for demand in demands[:3]:  # Limit to top 3 urgent demands
            urgency = demand.get("urgency", "pending").upper()
            lines.append(f"**{urgency}**: {demand['faction']} demands via {demand['enhancement_name']}")
            lines.append(f"  \"{demand['demand']}\"")

            if demand.get("threat_basis"):
                lines.append(f"  They have: {', '.join(demand['threat_basis'])}")

            if demand.get("deadline"):
                lines.append(f"  Deadline: {demand['deadline']}")

            if demand.get("consequences"):
                lines.append(f"  If ignored: {'; '.join(demand['consequences'])}")

            lines.append("")

        lines.append("**As GM, consider:**")
        lines.append("1. Having faction proxy appear with increasing pressure")
        lines.append("2. If deadline passed, use escalate_demand() to queue consequences or increase weight")
        lines.append("3. Show the faction's disappointment/anger through NPC behavior")
        lines.append("")
        lines.append("This is DIFFERENT from [LEVERAGE HINT] — these are active demands requiring response.")

        return "\n".join(lines)

    def respond(
        self,
        user_message: str,
        conversation: list[Message] | None = None,
    ) -> str:
        """
        Generate a response to the user message.

        Args:
            user_message: The player's input
            conversation: Previous messages in the conversation

        Returns:
            The agent's response text
        """
        if not self.client:
            return (
                "[No LLM backend available]\n"
                "Options:\n"
                "1. Start LM Studio with a model loaded\n"
                "2. Set ANTHROPIC_API_KEY for Claude\n"
            )

        # Build messages
        messages = list(conversation or [])
        messages.append(Message(role="user", content=user_message))

        # Get system prompt with current state
        system_prompt = self.prompt_loader.assemble_system_prompt(
            self.manager.current,
            self.manager,
        )

        # Detect hinge moments in player input
        hinge_detection = detect_hinge(user_message)
        if hinge_detection:
            hinge_context = get_hinge_context(hinge_detection)
            system_prompt = system_prompt + "\n\n---\n\n" + hinge_context

        # Check for dormant thread triggers
        thread_matches = self.manager.check_thread_triggers(user_message)
        if thread_matches:
            thread_context = self._format_thread_hints(thread_matches)
            system_prompt = system_prompt + "\n\n---\n\n" + thread_context

        # Check for leverage hints
        leverage_hints = self.manager.check_leverage_hints(user_message)
        if leverage_hints:
            leverage_context = self._format_leverage_hints(leverage_hints)
            system_prompt = system_prompt + "\n\n---\n\n" + leverage_context

        # Check for demand deadlines (overdue/urgent demands)
        urgent_demands = self.manager.check_demand_deadlines()
        if urgent_demands:
            demand_context = self._format_demand_alerts(urgent_demands)
            system_prompt = system_prompt + "\n\n---\n\n" + demand_context

        # Retrieve relevant lore if available
        if self.lore_retriever:
            results = self.lore_retriever.retrieve_for_context(
                player_input=user_message,
                active_factions=self._get_active_factions(),
                mission_type=self._get_mission_type(),
                limit=2,
            )
            if results:
                lore_section = self.lore_retriever.format_for_prompt(results)
                system_prompt = system_prompt + "\n\n---\n\n" + lore_section

        # Use the client's tool loop
        def tool_executor(name: str, args: dict) -> dict:
            return self.execute_tool(name, args)

        response = self.client.chat_with_tools(
            messages=messages,
            system=system_prompt,
            tools=self.get_tools() if self.client.supports_tools else None,
            tool_executor=tool_executor,
        )

        return response

    # -------------------------------------------------------------------------
    # Council / Consult
    # -------------------------------------------------------------------------

    ADVISORS = {
        "nexus": "NEXUS ANALYST",
        "ember": "EMBER CONTACT",
        "witness": "WITNESS ARCHIVIST",
    }

    def _query_advisor(
        self,
        advisor: str,
        question: str,
        context: str,
    ) -> AdvisorResponse:
        """Query a single advisor. Used in parallel."""
        title = self.ADVISORS.get(advisor, advisor.upper())

        if not self.client:
            return AdvisorResponse(
                advisor=advisor,
                title=title,
                response="",
                error="No LLM backend available",
            )

        # Load advisor prompt
        advisor_prompt = self.prompt_loader.load_advisor(advisor)
        if not advisor_prompt:
            return AdvisorResponse(
                advisor=advisor,
                title=title,
                response="",
                error=f"Advisor prompt not found: {advisor}",
            )

        # Build system prompt with advisor personality + context
        system = f"{advisor_prompt}\n\n---\n\n# Current Situation\n\n{context}"

        try:
            # Simple completion without tools
            messages = [Message(role="user", content=question)]
            response = self.client.chat_with_tools(
                messages=messages,
                system=system,
                tools=None,
                tool_executor=lambda n, a: {},
            )
            return AdvisorResponse(
                advisor=advisor,
                title=title,
                response=response.strip(),
            )
        except Exception as e:
            return AdvisorResponse(
                advisor=advisor,
                title=title,
                response="",
                error=str(e),
            )

    def consult(
        self,
        question: str,
        advisors: list[str] | None = None,
    ) -> list[AdvisorResponse]:
        """
        Consult multiple advisors in parallel.

        Args:
            question: The player's question
            advisors: Which advisors to query (default: all three)

        Returns:
            List of AdvisorResponse objects
        """
        if advisors is None:
            advisors = list(self.ADVISORS.keys())

        # Build context from current campaign state
        context_lines = []
        if self.manager.current:
            campaign = self.manager.current

            # Character info
            if campaign.characters:
                char = campaign.characters[0]
                context_lines.append(f"Operative: {char.name} ({char.background.value})")
                context_lines.append(f"Social Energy: {char.social_energy.current}%")

            # Faction standings (non-neutral only)
            tensions = []
            for faction in FactionName:
                standing = campaign.factions.get(faction)
                if standing.standing.value != "Neutral":
                    tensions.append(f"{faction.value}: {standing.standing.value}")
            if tensions:
                context_lines.append(f"Faction Relations: {', '.join(tensions)}")

            # Current mission
            if campaign.session:
                context_lines.append(
                    f"Current Mission: {campaign.session.mission_title} "
                    f"({campaign.session.phase.value} phase)"
                )

        context = "\n".join(context_lines) if context_lines else "No active campaign."

        # Query advisors in parallel
        results: list[AdvisorResponse] = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._query_advisor, adv, question, context): adv
                for adv in advisors
            }
            for future in as_completed(futures):
                results.append(future.result())

        # Sort by advisor order
        order = {adv: i for i, adv in enumerate(advisors)}
        results.sort(key=lambda r: order.get(r.advisor, 99))

        return results


# -----------------------------------------------------------------------------
# Factory Functions
# -----------------------------------------------------------------------------

def create_agent(
    campaigns_dir: str = "campaigns",
    prompts_dir: str = "prompts",
    backend: Literal["lmstudio", "claude", "auto"] = "auto",
) -> SentinelAgent:
    """
    Create a configured agent instance.

    Args:
        campaigns_dir: Directory for campaign save files
        prompts_dir: Directory for prompt modules
        backend: Which LLM backend to use (auto-detects if "auto")

    Returns:
        Configured SentinelAgent
    """
    manager = CampaignManager(campaigns_dir)
    return SentinelAgent(manager, prompts_dir, backend=backend)


def create_lmstudio_agent(
    campaigns_dir: str = "campaigns",
    prompts_dir: str = "prompts",
    url: str = "http://localhost:1234/v1",
) -> SentinelAgent:
    """Create an agent using LM Studio backend."""
    manager = CampaignManager(campaigns_dir)
    return SentinelAgent(
        manager,
        prompts_dir,
        backend="lmstudio",
        lmstudio_url=url,
    )
