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
from .state.schema import FactionName, HistoryType
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

    def assemble_system_prompt(self, campaign: Campaign | None = None) -> str:
        """Assemble the full system prompt from modules."""
        parts = [
            self.load("core"),
            self.load("mechanics"),
            self.load("gm_guidance"),
        ]

        # Add campaign state if available
        if campaign:
            parts.append(self._format_state_summary(campaign))

        return "\n\n---\n\n".join(filter(None, parts))

    def load_advisor(self, advisor: str) -> str:
        """Load an advisor prompt."""
        path = self.prompts_dir / "advisors" / f"{advisor}.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _format_state_summary(self, campaign: Campaign) -> str:
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
            self.manager.current
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
