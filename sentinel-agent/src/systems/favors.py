"""
Favor system for SENTINEL.

Handles NPC favor requests - rides, intel, gear loans, introductions, safe houses.
NPCs can be called on for help based on disposition and standing.

Favor costs are a combination of:
- Token limits (2 per session by default)
- Standing cost (varies by disposition and favor type)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..state.schema import (
    Disposition,
    FavorToken,
    FavorType,
    NPC,
)
from ..state.event_bus import get_event_bus, EventType

if TYPE_CHECKING:
    from ..state.manager import CampaignManager


# Standing cost by favor type (base costs)
FAVOR_COSTS: dict[FavorType, int] = {
    FavorType.RIDE: 10,
    FavorType.INTEL: 15,
    FavorType.GEAR_LOAN: 15,
    FavorType.INTRODUCTION: 20,
    FavorType.SAFE_HOUSE: 10,
}

# Disposition modifiers to standing cost
# Lower disposition = higher cost (they're less willing)
DISPOSITION_COST_MODIFIER: dict[Disposition, float] = {
    Disposition.HOSTILE: 0,      # Can't call favors
    Disposition.WARY: 0,         # Can't call favors
    Disposition.NEUTRAL: 2.5,    # 250% cost (only rides available)
    Disposition.WARM: 1.5,       # 150% cost
    Disposition.LOYAL: 1.0,      # Base cost
}

# Which favor types are available at each disposition
DISPOSITION_FAVORS: dict[Disposition, list[FavorType]] = {
    Disposition.HOSTILE: [],
    Disposition.WARY: [],
    Disposition.NEUTRAL: [FavorType.RIDE],  # Neutral only offers rides
    Disposition.WARM: list(FavorType),      # Warm offers everything
    Disposition.LOYAL: list(FavorType),     # Loyal offers everything
}


class FavorSystem:
    """
    Manages favor requests to NPCs.

    Favors are limited by:
    - Session tokens (2 per session default)
    - NPC disposition (must be NEUTRAL+ for any favor)
    - Standing cost (deducted from personal standing)
    """

    def __init__(self, manager: "CampaignManager"):
        self.manager = manager

    @property
    def _campaign(self):
        return self.manager.current

    @property
    def _favor_tracker(self):
        return self._campaign.favor_tracker

    def get_current_session(self) -> int:
        """Get current session number."""
        if self._campaign.session:
            return self._campaign.session.session_number
        return 0

    def tokens_remaining(self) -> int:
        """How many favor tokens remain this session."""
        return self._favor_tracker.tokens_remaining(self.get_current_session())

    def can_call_favor(self) -> bool:
        """Check if player has tokens remaining this session."""
        return self._favor_tracker.can_call_favor(self.get_current_session())

    def get_available_npcs(self) -> list[NPC]:
        """
        Get NPCs that can provide favors.

        Returns NPCs with disposition NEUTRAL or better who can provide
        at least one type of favor.
        """
        available = []
        for npc in self._campaign.npcs.npcs:
            # Get faction standing if NPC has a faction
            faction_standing = None
            if npc.faction:
                faction_standing = self._campaign.factions.get_standing(npc.faction)

            # Get effective disposition
            disposition = npc.get_effective_disposition(faction_standing)

            # Check if they can provide any favors
            if DISPOSITION_FAVORS.get(disposition, []):
                available.append(npc)

        return available

    def get_npc_favor_options(self, npc: NPC) -> list[tuple[FavorType, int]]:
        """
        Get available favor types and costs for a specific NPC.

        Returns list of (FavorType, standing_cost) tuples.
        """
        # Get faction standing if NPC has a faction
        faction_standing = None
        if npc.faction:
            faction_standing = self._campaign.factions.get_standing(npc.faction)

        # Get effective disposition
        disposition = npc.get_effective_disposition(faction_standing)

        # Get available favor types for this disposition
        available_types = DISPOSITION_FAVORS.get(disposition, [])

        # Calculate costs
        cost_modifier = DISPOSITION_COST_MODIFIER.get(disposition, 1.0)

        options = []
        for favor_type in available_types:
            base_cost = FAVOR_COSTS[favor_type]
            final_cost = int(base_cost * cost_modifier)
            options.append((favor_type, final_cost))

        return options

    def can_afford_favor(self, npc: NPC, favor_type: FavorType) -> tuple[bool, str]:
        """
        Check if player can afford a specific favor from an NPC.

        Returns (can_afford, reason) tuple.
        """
        if not self.can_call_favor():
            remaining = self.tokens_remaining()
            return False, f"No favor tokens remaining this session ({remaining}/2)"

        # Get favor options
        options = self.get_npc_favor_options(npc)

        # Check if favor type is available
        available_types = [opt[0] for opt in options]
        if favor_type not in available_types:
            # Get disposition for error message
            faction_standing = None
            if npc.faction:
                faction_standing = self._campaign.factions.get_standing(npc.faction)
            disposition = npc.get_effective_disposition(faction_standing)

            return False, f"{npc.name} ({disposition.value}) won't offer {favor_type.value} favors"

        # Get cost for this favor type
        cost = next(c for t, c in options if t == favor_type)

        # Check personal standing
        if npc.personal_standing < cost:
            return False, f"Not enough standing with {npc.name} ({npc.personal_standing}/{cost})"

        return True, f"Favor will cost {cost} standing with {npc.name}"

    def call_favor(
        self,
        npc: NPC,
        favor_type: FavorType,
        description: str = "",
    ) -> dict:
        """
        Call in a favor from an NPC.

        Deducts standing and uses a favor token.

        Args:
            npc: The NPC to ask
            favor_type: Type of favor requested
            description: What specifically is being requested

        Returns:
            Dict with result info or error
        """
        # Check affordability
        can_afford, reason = self.can_afford_favor(npc, favor_type)
        if not can_afford:
            return {"error": reason}

        # Get the cost
        options = self.get_npc_favor_options(npc)
        cost = next(c for t, c in options if t == favor_type)

        # Deduct standing
        old_standing = npc.personal_standing
        npc.personal_standing -= cost

        # Record the token usage
        token = FavorToken(
            npc_id=npc.id,
            npc_name=npc.name,
            favor_type=favor_type,
            session_used=self.get_current_session(),
            standing_cost=cost,
            description=description,
        )
        self._favor_tracker.tokens_used.append(token)

        # Emit event for UI update
        bus = get_event_bus()
        bus.emit(EventType.NPC_UPDATED, {
            "npc_id": npc.id,
            "npc_name": npc.name,
            "change": "favor_called",
            "favor_type": favor_type.value,
            "standing_change": -cost,
        })

        # Save state
        self.manager.save_campaign()

        return {
            "success": True,
            "npc_name": npc.name,
            "favor_type": favor_type.value,
            "standing_cost": cost,
            "old_standing": old_standing,
            "new_standing": npc.personal_standing,
            "tokens_remaining": self.tokens_remaining(),
            "description": description,
            "narrative_hint": self._get_favor_narrative(npc, favor_type),
        }

    def _get_favor_narrative(self, npc: NPC, favor_type: FavorType) -> str:
        """Generate narrative flavor for the favor."""
        narratives = {
            FavorType.RIDE: f"{npc.name} can arrange transport. They know the routes.",
            FavorType.INTEL: f"{npc.name} shares what they know. Information has a price.",
            FavorType.GEAR_LOAN: f"{npc.name} hands over the equipment. Return it when you're done.",
            FavorType.INTRODUCTION: f"{npc.name} makes a call. You'll owe them for this.",
            FavorType.SAFE_HOUSE: f"{npc.name} gives you an address. Don't lead anyone there.",
        }
        return narratives.get(favor_type, f"{npc.name} agrees to help.")

    def get_favor_history(self, session: int | None = None) -> list[FavorToken]:
        """
        Get history of favor usage.

        Args:
            session: Filter to specific session, or None for all
        """
        if session is None:
            return self._favor_tracker.tokens_used
        return [t for t in self._favor_tracker.tokens_used if t.session_used == session]

    def find_npc_by_name(self, name: str) -> NPC | None:
        """Find an NPC by name (case-insensitive partial match)."""
        name_lower = name.lower()
        for npc in self._campaign.npcs.npcs:
            if name_lower in npc.name.lower():
                return npc
        return None
