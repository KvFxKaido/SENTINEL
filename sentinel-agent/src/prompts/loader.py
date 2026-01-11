"""
Hot-reloadable prompt loader for SENTINEL.

Loads prompt modules from disk and assembles them into system prompts.
Supports caching with modification time checking for hot-reload.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..state import CampaignManager
    from ..state.schema import Campaign


class PromptLoader:
    """
    Hot-reloadable prompt loader.

    Loads prompt modules from disk and assembles them into system prompts.
    Watches file modification times to enable hot-reload without restart.
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
        campaign: "Campaign | None" = None,
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
        campaign: "Campaign | None" = None,
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
        self,
        campaign: "Campaign",
        manager: "CampaignManager | None" = None,
    ) -> str:
        """Format current campaign state for injection into prompts."""
        from ..state.schema import FactionName, ArcStatus

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
