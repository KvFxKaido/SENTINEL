"""
SENTINEL Agent Orchestrator.

Coordinates LLM calls with game state and tools.
Supports local backends: LM Studio, Ollama.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal
from concurrent.futures import ThreadPoolExecutor, as_completed

from .state import CampaignManager, Campaign
from .state.schema import FactionName, HistoryType, LeverageWeight
from .tools.registry import get_all_schemas, create_default_registry, ToolRegistry
from .tools.hinge_detector import detect_hinge, get_hinge_context
from .llm.base import LLMClient, Message
from .llm import create_llm_client
from .lore import UnifiedRetriever
from .lore.quotes import get_relevant_quotes, format_quote_for_gm, get_faction_motto
from .context import (
    PromptPacker,
    PackInfo,
    StrainTier,
    RollingWindow,
    TranscriptBlock,
    format_strain_notice,
)


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

    def get_sections(
        self,
        campaign: Campaign | None = None,
        manager: "CampaignManager | None" = None,
    ) -> dict[str, str]:
        """
        Get prompt sections separately for PromptPacker.

        Returns dict with keys: system, rules_core, rules_narrative, state

        Rules are split into two tiers:
        - rules_core: Decision logic that must survive truncation (always included)
        - rules_narrative: Flavor/examples that can be cut under strain
        """
        # System section: core identity
        system = self.load("core")

        # Rules core: mechanics + core decision logic (always included, never cut)
        core_parts = [
            self.load("mechanics"),
            self._load_rules_file("core_logic"),
        ]
        if campaign and campaign.session:
            phase_guidance = self.load_phase(campaign.session.phase.value)
            if phase_guidance:
                core_parts.append(phase_guidance)
        rules_core = "\n\n".join(filter(None, core_parts))

        # Rules narrative: flavor/examples (strain-aware, cut under pressure)
        rules_narrative = self._load_rules_file("narrative_guidance")

        # State section: campaign state summary
        state = ""
        if campaign:
            state = self._format_state_summary(campaign, manager)

        return {
            "system": system,
            "rules_core": rules_core,
            "rules_narrative": rules_narrative,
            "state": state,
        }

    def _load_rules_file(self, name: str) -> str:
        """Load a rules file from prompts/rules/ directory."""
        path = self.prompts_dir / "rules" / f"{name}.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

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

                # Show accepted character arcs
                from .state.schema import ArcStatus
                accepted_arcs = [a for a in char.arcs if a.status == ArcStatus.ACCEPTED]
                if accepted_arcs:
                    lines.append("  **Character Arcs** (recognized patterns):")
                    for arc in accepted_arcs:
                        lines.append(f"  → {arc.title} ({arc.arc_type.value})")
                        lines.append(f"    {arc.description}")
                        if arc.effects:
                            lines.append(f"    Effects: {'; '.join(arc.effects[:2])}")

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
    BACKENDS = ["lmstudio", "ollama", "auto"]

    def __init__(
        self,
        campaign_manager: CampaignManager,
        prompts_dir: Path | str = "prompts",
        lore_dir: Path | str | None = None,
        client: LLMClient | None = None,
        backend: str = "auto",
        lmstudio_url: str = "http://127.0.0.1:1234/v1",
        ollama_url: str = "http://127.0.0.1:11434/v1",
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
            ollama_url: URL for Ollama server
        """
        self.manager = campaign_manager
        self.prompt_loader = PromptLoader(prompts_dir)

        # Store config for backend switching
        self._config = {
            "lmstudio_url": lmstudio_url,
            "ollama_url": ollama_url,
        }

        # Initialize unified retriever (lore + campaign memory) if lore_dir provided
        self.unified_retriever: UnifiedRetriever | None = None
        if lore_dir:
            lore_path = Path(lore_dir)
            if lore_path.exists():
                from .lore import LoreRetriever
                lore_retriever = LoreRetriever(lore_path)
                memvid = getattr(self.manager, 'memvid', None)
                self.unified_retriever = UnifiedRetriever(
                    lore_retriever,
                    memvid=memvid,
                )

        # Tool registry (centralized in src/tools/registry.py)
        self.tool_registry = create_default_registry(self.manager)

        # Initialize prompt packer for context control
        self.packer = PromptPacker()
        self._last_pack_info: PackInfo | None = None
        self._conversation_window = RollingWindow()

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
                ollama_url=ollama_url,
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

    @property
    def lore_retriever(self):
        """Backwards compatibility - access lore via unified retriever."""
        return self.unified_retriever.lore if self.unified_retriever else None

    def get_tools(self) -> list[dict]:
        """Get all tool schemas for the API."""
        return get_all_schemas()

    def execute_tool(self, name: str, arguments: dict) -> dict:
        """Execute a tool and return the result."""
        return self.tool_registry.execute(name, arguments)

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

    def _get_relevant_quotes(self, user_message: str) -> str:
        """
        Get relevant lore quotes for GM context.

        Provides curated faction quotes and world truths that NPCs
        can weave into their dialogue to reinforce lore continuity.
        """
        # Get primary faction from context
        primary_faction = None
        active_factions = self._get_active_factions()
        if active_factions:
            primary_faction = active_factions[0]

        # Find relevant quotes
        quotes = get_relevant_quotes(
            text=user_message,
            faction=primary_faction,
            limit=3,
        )

        if not quotes:
            return ""

        # Format for GM context
        lines = [
            "[LORE QUOTES - NPC Dialogue Flavor]",
            "Weave these naturally into NPC speech when thematically appropriate:",
            "",
        ]

        for quote in quotes:
            lines.append(format_quote_for_gm(quote))
            lines.append("")

        lines.append("Use sparingly. One quote per scene maximum.")
        lines.append("NPCs should sound like themselves — quotes are seasoning, not scripts.")

        return "\n".join(lines)

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

        Uses PromptPacker for deterministic context control with token budgets.

        Args:
            user_message: The player's input
            conversation: Previous messages in the conversation

        Returns:
            The agent's response text
        """
        from datetime import datetime
        from uuid import uuid4

        if not self.client:
            return (
                "[No LLM backend available]\n"
                "Start LM Studio or Ollama with a model loaded.\n"
            )

        # Build messages for LLM
        messages = list(conversation or [])
        messages.append(Message(role="user", content=user_message))

        # Update conversation window with new messages
        self._update_conversation_window(messages)

        # Get base sections from prompt loader
        sections = self.prompt_loader.get_sections(
            self.manager.current,
            self.manager,
        )

        # Build dynamic hints (hinge detection, thread triggers, etc.)
        dynamic_hints = self._build_dynamic_hints(user_message)

        # Calculate preliminary strain for retrieval budget
        preliminary_pressure = self.packer.get_pressure(
            system=sections["system"],
            rules_core=sections["rules_core"],
            rules_narrative=sections["rules_narrative"],
            state=sections["state"] + "\n\n" + dynamic_hints if dynamic_hints else sections["state"],
        )
        strain_tier = StrainTier.from_pressure(preliminary_pressure)

        # Retrieve with strain-aware budget
        retrieval_content = ""
        if self.unified_retriever:
            unified_result = self.unified_retriever.query(
                topic=user_message,
                factions=self._get_active_factions(),
                strain_tier=strain_tier,  # Pass strain for budget adjustment
            )
            if not unified_result.is_empty:
                retrieval_content = self.unified_retriever.format_for_prompt(unified_result)

        # Add lore quotes to retrieval
        quote_context = self._get_relevant_quotes(user_message)
        if quote_context:
            retrieval_content = (
                retrieval_content + "\n\n" + quote_context
                if retrieval_content else quote_context
            )

        # Combine state with dynamic hints
        state_content = sections["state"]
        if dynamic_hints:
            state_content = state_content + "\n\n---\n\n" + dynamic_hints

        # Pack everything with budget enforcement
        # rules_core (decision logic) is always included
        # rules_narrative (flavor) is cut under strain II+
        system_prompt, pack_info = self.packer.pack(
            system=sections["system"],
            rules_core=sections["rules_core"],
            rules_narrative=sections["rules_narrative"],
            state=state_content,
            window=self._conversation_window,
            retrieval=retrieval_content,
            user_input=user_message,
        )

        # Store pack info for /context command
        self._last_pack_info = pack_info

        # Add strain notice if elevated
        strain_notice = format_strain_notice(pack_info.strain_tier)
        if strain_notice:
            system_prompt = system_prompt + "\n\n---\n\n" + strain_notice

        # Use the client's tool loop
        def tool_executor(name: str, args: dict) -> dict:
            return self.execute_tool(name, args)

        response = self.client.chat_with_tools(
            messages=messages,
            system=system_prompt,
            tools=self.get_tools() if self.client.supports_tools else None,
            tool_executor=tool_executor,
        )

        # Update window with assistant response
        self._conversation_window.add_block(TranscriptBlock(
            id=str(uuid4()),
            timestamp=datetime.now(),
            role="assistant",
            content=response[:500],  # Truncate for window storage
            block_type=self._detect_response_type(response),
        ))

        return response

    def _update_conversation_window(self, messages: list[Message]) -> None:
        """Update the rolling window with conversation messages."""
        from datetime import datetime
        from uuid import uuid4

        # Add any new messages not already in window
        existing_ids = {b.id for b in self._conversation_window.blocks}

        for i, msg in enumerate(messages):
            # Create a stable ID based on position and content hash
            msg_id = f"msg_{i}_{hash(msg.content[:50]) % 10000}"
            if msg_id not in existing_ids:
                # Detect block type for assistant messages
                block_type = "NARRATIVE"
                if msg.role == "user":
                    block_type = "CHOICE"
                elif msg.role == "assistant":
                    block_type = self._detect_response_type(msg.content)

                self._conversation_window.add_block(TranscriptBlock(
                    id=msg_id,
                    timestamp=datetime.now(),
                    role=msg.role,
                    content=msg.content[:500],  # Truncate long messages
                    block_type=block_type,
                ))

    def _detect_response_type(self, content: str) -> str:
        """Detect the type of GM response for block classification."""
        content_lower = content.lower()

        # Check for choice blocks
        if "---choice---" in content_lower or (
            any(f"{i}." in content for i in range(1, 5)) and
            ("?" in content or "choose" in content_lower or "option" in content_lower)
        ):
            return "CHOICE"

        # Check for intel blocks
        intel_markers = ["[intel]", "[info]", "[data]", "faction standing", "reputation"]
        if any(marker in content_lower for marker in intel_markers):
            return "INTEL"

        # Check for system blocks
        if content.startswith("[") and "]" in content[:50]:
            return "SYSTEM"

        return "NARRATIVE"

    def _build_dynamic_hints(self, user_message: str) -> str:
        """Build dynamic context hints (hinge detection, thread triggers, etc.)."""
        hints = []

        # Detect hinge moments in player input
        hinge_detection = detect_hinge(user_message)
        if hinge_detection:
            hints.append(get_hinge_context(hinge_detection))

        # Check for dormant thread triggers
        thread_matches = self.manager.check_thread_triggers(user_message)
        if thread_matches:
            hints.append(self._format_thread_hints(thread_matches))

        # Check for leverage hints
        leverage_hints = self.manager.check_leverage_hints(user_message)
        if leverage_hints:
            hints.append(self._format_leverage_hints(leverage_hints))

        # Check for demand deadlines (overdue/urgent demands)
        urgent_demands = self.manager.check_demand_deadlines()
        if urgent_demands:
            hints.append(self._format_demand_alerts(urgent_demands))

        return "\n\n---\n\n".join(hints) if hints else ""

    # -------------------------------------------------------------------------
    # Council / Consult
    # -------------------------------------------------------------------------

    ADVISORS = {
        "nexus": "NEXUS ANALYST",
        "ember": "EMBER CONTACT",
        "witness": "WITNESS ARCHIVIST",
    }

    # Map advisor names to faction names for context retrieval
    ADVISOR_FACTIONS = {
        "nexus": "nexus",
        "ember": "ember_colonies",
        "witness": "witnesses",
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

        # Add faction-specific campaign history if available
        if self.unified_retriever:
            faction = self.ADVISOR_FACTIONS.get(advisor)
            if faction:
                unified_result = self.unified_retriever.query_for_faction(
                    faction=faction,
                    topic=question,
                    limit_lore=1,
                    limit_campaign=5,
                )
                if unified_result.has_campaign:
                    history_section = self.unified_retriever.format_for_prompt(unified_result)
                    system = system + "\n\n---\n\n" + history_section

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
    backend: Literal["lmstudio", "ollama", "auto"] = "auto",
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
