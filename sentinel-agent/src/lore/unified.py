"""
Unified retriever combining static lore with dynamic campaign memory.

Queries both LoreRetriever (static world knowledge) and MemvidAdapter
(dynamic campaign events) to provide comprehensive context for the GM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .retriever import LoreRetriever, RetrievalResult
    from ..state import MemvidAdapter


@dataclass
class RetrievalBudget:
    """
    Global budget for retrieval across all layers.

    Prevents context bloat by capping items from each source.
    Total tokens roughly estimated as: (lore*500) + (campaign*200) + (state*100)
    """
    lore: int = 2          # Max lore chunks (static world-building)
    campaign: int = 2      # Max memvid hits (dynamic history)
    state: bool = True     # Whether to include current faction state

    # Convenience presets
    @classmethod
    def minimal(cls) -> "RetrievalBudget":
        """For quick queries or low-context situations."""
        return cls(lore=1, campaign=1, state=True)

    @classmethod
    def standard(cls) -> "RetrievalBudget":
        """Default balanced retrieval."""
        return cls(lore=2, campaign=2, state=True)

    @classmethod
    def deep(cls) -> "RetrievalBudget":
        """For complex queries needing more context."""
        return cls(lore=3, campaign=5, state=True)


# Default budget used when none specified
DEFAULT_BUDGET = RetrievalBudget.standard()


@dataclass
class UnifiedResult:
    """Combined results from lore, campaign memory, and current state."""
    lore: list[dict]
    campaign: list[dict]
    faction_state: dict | None = None  # Current faction standings (authoritative truth)

    @property
    def has_lore(self) -> bool:
        return len(self.lore) > 0

    @property
    def has_campaign(self) -> bool:
        return len(self.campaign) > 0

    @property
    def has_state(self) -> bool:
        return self.faction_state is not None and len(self.faction_state) > 0

    @property
    def is_empty(self) -> bool:
        return not self.has_lore and not self.has_campaign and not self.has_state


class UnifiedRetriever:
    """
    Combines static lore with dynamic campaign memory for comprehensive context.

    Use Cases:
    - When an NPC/faction is mentioned, pull both lore AND campaign history
    - GM context building before generating responses
    - /consult command drawing on both canon and campaign events

    Design Principles:
    - Lore is authoritative (campaign can't contradict canon)
    - Campaign adds specificity ("Nexus is surveillance" + "You helped them in S3")
    - Graceful degradation (works with just lore if memvid disabled)
    """

    def __init__(
        self,
        lore_retriever: LoreRetriever,
        memvid: MemvidAdapter | None = None,
    ):
        """
        Initialize unified retriever.

        Args:
            lore_retriever: Static lore retriever instance
            memvid: Optional memvid adapter (can be None for graceful degradation)
        """
        self.lore = lore_retriever
        self.memvid = memvid

    def query(
        self,
        topic: str,
        factions: list[str] | None = None,
        npc_id: str | None = None,
        npc_name: str | None = None,
        limit_lore: int | None = None,
        limit_campaign: int | None = None,
        faction_state: dict | None = None,
        budget: RetrievalBudget | None = None,
    ) -> UnifiedResult:
        """
        Query both lore and campaign history.

        Args:
            topic: Topic to search for (natural language)
            factions: Factions to prioritize in lore search
            npc_id: NPC ID for targeted campaign history
            npc_name: NPC name for search fallback
            limit_lore: Max lore chunks (overrides budget if specified)
            limit_campaign: Max campaign events (overrides budget if specified)
            faction_state: Current faction standings (injected for authoritative truth)
            budget: RetrievalBudget to control limits across layers

        Returns:
            UnifiedResult with lore, campaign hits, and current state
        """
        # Apply budget (explicit limits override budget)
        budget = budget or DEFAULT_BUDGET
        lore_limit = limit_lore if limit_lore is not None else budget.lore
        campaign_limit = limit_campaign if limit_campaign is not None else budget.campaign

        # Only include state if budget allows and state was provided
        effective_state = faction_state if budget.state else None

        result = UnifiedResult(lore=[], campaign=[], faction_state=effective_state)

        # Static lore retrieval
        lore_hits = self.lore.retrieve(
            query=topic,
            factions=factions,
            limit=lore_limit,
        )
        result.lore = [
            {
                "source": hit.chunk.source,
                "title": hit.chunk.title,
                "section": hit.chunk.section,
                "content": hit.chunk.content,
                "factions": hit.chunk.factions,
                "score": hit.score,
                "match_reasons": hit.match_reasons,
            }
            for hit in lore_hits
        ]

        # Campaign history (if memvid enabled)
        if self.memvid and self.memvid.is_enabled:
            if npc_id:
                # Targeted NPC history
                campaign_hits = self.memvid.get_npc_history(npc_id, campaign_limit)
            elif npc_name:
                # Search by NPC name
                campaign_hits = self.memvid.query(
                    f"npc_name:{npc_name} {topic}",
                    top_k=campaign_limit,
                )
            else:
                # General topic search
                campaign_hits = self.memvid.query(topic, top_k=campaign_limit)

            result.campaign = campaign_hits

        return result

    def query_for_npc(
        self,
        npc_name: str,
        npc_id: str | None = None,
        faction: str | None = None,
        limit_lore: int = 2,
        limit_campaign: int = 5,
    ) -> UnifiedResult:
        """
        Get context for an NPC interaction.

        Retrieves:
        - Faction lore (if faction specified)
        - Past interactions with this NPC

        Args:
            npc_name: NPC's display name
            npc_id: NPC's ID for precise campaign lookup
            faction: NPC's faction for lore context
            limit_lore: Max lore chunks
            limit_campaign: Max campaign events

        Returns:
            UnifiedResult tailored for NPC context
        """
        factions = [faction] if faction else None

        return self.query(
            topic=npc_name,
            factions=factions,
            npc_id=npc_id,
            npc_name=npc_name,
            limit_lore=limit_lore,
            limit_campaign=limit_campaign,
        )

    def query_for_faction(
        self,
        faction: str,
        topic: str = "",
        limit_lore: int = 3,
        limit_campaign: int = 5,
        faction_state: dict | None = None,
    ) -> UnifiedResult:
        """
        Get context for a faction-related query.

        Retrieves:
        - Faction lore
        - Player's history with this faction
        - Current standing (if faction_state provided)

        Args:
            faction: Faction name/ID
            topic: Optional topic to narrow search
            limit_lore: Max lore chunks
            limit_campaign: Max campaign events
            faction_state: Current faction standings dict

        Returns:
            UnifiedResult for faction context
        """
        search_topic = f"{faction} {topic}".strip()

        result = self.query(
            topic=search_topic,
            factions=[faction],
            limit_lore=limit_lore,
            limit_campaign=limit_campaign,
            faction_state=faction_state,
        )

        # Also search for faction shifts specifically
        if self.memvid and self.memvid.is_enabled:
            faction_shifts = self.memvid.query(
                f"type:faction_shift faction:{faction}",
                top_k=3,
            )
            # Prepend faction shifts to campaign results
            result.campaign = faction_shifts + result.campaign
            # Dedupe and limit
            seen = set()
            deduped = []
            for hit in result.campaign:
                key = (hit.get("type"), hit.get("session"), hit.get("timestamp", ""))
                if key not in seen:
                    seen.add(key)
                    deduped.append(hit)
            result.campaign = deduped[:limit_campaign]

        return result

    def format_for_prompt(
        self,
        result: UnifiedResult,
        max_lore_chars: int = 800,
        max_campaign_items: int = 5,
    ) -> str:
        """
        Format unified results for inclusion in GM system prompt.

        Args:
            result: UnifiedResult to format
            max_lore_chars: Max characters per lore chunk
            max_campaign_items: Max campaign events to include

        Returns:
            Formatted markdown string for prompt injection
        """
        if result.is_empty:
            return ""

        lines = []

        # Current state section (authoritative truth - goes first)
        if result.has_state:
            lines.append("## Current Faction Standings")
            lines.append("*Authoritative current state — takes precedence over history*")
            lines.append("")
            for faction, standing in result.faction_state.items():
                faction_display = faction.replace("_", " ").title()
                lines.append(f"- **{faction_display}**: {standing}")
            lines.append("")

        # Lore section
        if result.has_lore:
            lines.append("## Lore Reference")
            lines.append("")
            for hit in result.lore:
                source = hit.get("source", "unknown")
                title = hit.get("title", "")
                section = hit.get("section", "")
                content = hit.get("content", "")

                header = f"**{title}**" if title else f"*From {source}*"
                if section:
                    header += f" — {section}"
                lines.append(header)

                # Truncate content
                if len(content) > max_lore_chars:
                    content = content[:max_lore_chars] + "..."
                lines.append(content)
                lines.append("")

        # Campaign section
        if result.has_campaign:
            lines.append("## Campaign History")
            lines.append("")
            for hit in result.campaign[:max_campaign_items]:
                frame_type = hit.get("type", "event")
                session = hit.get("session", "?")

                # Build summary based on frame type
                if frame_type == "turn_state":
                    summary = hit.get("narrative_summary", "Turn state recorded")
                elif frame_type == "hinge_moment":
                    summary = hit.get("choice", "Hinge moment")
                elif frame_type == "npc_interaction":
                    npc = hit.get("npc_name", "Unknown")
                    action = hit.get("player_action", "")[:60]
                    summary = f"{npc}: {action}"
                elif frame_type == "faction_shift":
                    faction = hit.get("faction", "Unknown")
                    from_s = hit.get("from_standing", "?")
                    to_s = hit.get("to_standing", "?")
                    summary = f"{faction}: {from_s} → {to_s}"
                elif frame_type == "dormant_thread":
                    summary = f"Thread: {hit.get('origin', 'Unknown')[:50]}"
                else:
                    summary = str(hit)[:80]

                lines.append(f"- **S{session}** [{frame_type}]: {summary}")
            lines.append("")

        return "\n".join(lines)

    def format_for_npc_memory(
        self,
        result: UnifiedResult,
        npc_name: str,
    ) -> str:
        """
        Format results specifically for NPC memory context.

        Used when an NPC needs to "remember" past interactions.

        Args:
            result: UnifiedResult from query_for_npc
            npc_name: NPC's name for personalization

        Returns:
            Formatted string from NPC's perspective
        """
        if not result.has_campaign:
            return f"{npc_name} has no recorded history with the player."

        lines = [f"## {npc_name}'s Memory", ""]

        for hit in result.campaign[:5]:
            if hit.get("type") != "npc_interaction":
                continue

            session = hit.get("session", "?")
            player_action = hit.get("player_action", "")
            npc_reaction = hit.get("npc_reaction", "")
            disp_change = hit.get("disposition_change", 0)

            lines.append(f"**Session {session}:**")
            if player_action:
                lines.append(f"- Player: {player_action[:100]}")
            if npc_reaction:
                lines.append(f"- {npc_name}: {npc_reaction[:100]}")
            if disp_change != 0:
                direction = "warmed" if disp_change > 0 else "cooled"
                lines.append(f"- *{npc_name} {direction} toward the player*")
            lines.append("")

        return "\n".join(lines)


def create_unified_retriever(
    lore_dir: str = "lore",
    memvid: MemvidAdapter | None = None,
) -> UnifiedRetriever:
    """
    Factory function to create a UnifiedRetriever.

    Args:
        lore_dir: Path to lore directory
        memvid: Optional memvid adapter

    Returns:
        Configured UnifiedRetriever
    """
    from .retriever import create_retriever

    lore_retriever = create_retriever(lore_dir)
    return UnifiedRetriever(lore_retriever, memvid)


def extract_faction_state(campaign) -> dict[str, str]:
    """
    Extract current faction standings from a campaign for state injection.

    Args:
        campaign: Campaign object with factions attribute

    Returns:
        Dict mapping faction_id -> standing (e.g., {"nexus": "Friendly"})
    """
    if not campaign or not hasattr(campaign, "factions"):
        return {}

    standings = {}
    faction_ids = [
        "nexus", "ember_colonies", "lattice", "convergence", "covenant",
        "wanderers", "cultivators", "steel_syndicate", "witnesses",
        "architects", "ghost_networks"
    ]

    for faction_id in faction_ids:
        faction_obj = getattr(campaign.factions, faction_id, None)
        if faction_obj and hasattr(faction_obj, "standing"):
            standings[faction_id] = faction_obj.standing.value

    return standings
