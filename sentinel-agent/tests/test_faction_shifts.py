"""
Tests for faction standing system.

Faction standings track player reputation and generate
chronicle entries when changed.
"""

import pytest
from src.state.schema import (
    FactionName,
    Standing,
    FactionStanding,
    HistoryType,
)


class TestFactionStandingModel:
    """Test the FactionStanding model directly."""

    def test_initial_standing_is_neutral(self):
        """New faction standings start at Neutral."""
        standing = FactionStanding(faction=FactionName.NEXUS)
        assert standing.standing == Standing.NEUTRAL

    def test_positive_shift_increases_standing(self):
        """Positive delta moves toward Allied."""
        standing = FactionStanding(faction=FactionName.EMBER_COLONIES)

        new_standing = standing.shift(1)

        assert new_standing == Standing.FRIENDLY
        assert standing.standing == Standing.FRIENDLY

    def test_negative_shift_decreases_standing(self):
        """Negative delta moves toward Hostile."""
        standing = FactionStanding(faction=FactionName.LATTICE)

        new_standing = standing.shift(-1)

        assert new_standing == Standing.UNFRIENDLY

    def test_shift_clamps_at_hostile(self):
        """Cannot go below Hostile."""
        standing = FactionStanding(
            faction=FactionName.CONVERGENCE,
            standing=Standing.HOSTILE,
        )

        new_standing = standing.shift(-5)

        assert new_standing == Standing.HOSTILE

    def test_shift_clamps_at_allied(self):
        """Cannot go above Allied."""
        standing = FactionStanding(
            faction=FactionName.COVENANT,
            standing=Standing.ALLIED,
        )

        new_standing = standing.shift(5)

        assert new_standing == Standing.ALLIED

    def test_multiple_shifts_accumulate(self):
        """Multiple shifts can be applied in sequence."""
        standing = FactionStanding(faction=FactionName.WANDERERS)

        standing.shift(1)  # Neutral -> Friendly
        standing.shift(1)  # Friendly -> Allied

        assert standing.standing == Standing.ALLIED


class TestManagerFactionOperations:
    """Test faction operations through the manager."""

    def test_shift_faction_returns_before_after(self, manager, campaign):
        """shift_faction returns before and after standings."""
        result = manager.shift_faction(
            faction=FactionName.EMBER_COLONIES,
            delta=1,
            reason="Helped with evacuation",
        )

        assert result["before"] == "Neutral"
        assert result["after"] == "Friendly"
        assert result["reason"] == "Helped with evacuation"

    def test_shift_faction_logs_to_history(self, manager, campaign):
        """Faction shifts are logged to campaign history."""
        manager.shift_faction(
            faction=FactionName.NEXUS,
            delta=-1,
            reason="Refused surveillance request",
        )

        history = manager.current.history
        assert len(history) == 1
        assert history[0].type == HistoryType.FACTION_SHIFT
        assert "Nexus" in history[0].summary
        assert "Unfriendly" in history[0].summary

    def test_betray_shift_is_larger(self, manager, campaign):
        """Betrayal (delta=-2) causes larger reputation loss."""
        result = manager.shift_faction(
            faction=FactionName.LATTICE,
            delta=-2,
            reason="Sold their secrets to Steel Syndicate",
        )

        assert result["before"] == "Neutral"
        assert result["after"] == "Hostile"

    def test_shift_generates_trigger_tags(self, manager, campaign):
        """Faction shifts generate appropriate trigger tags for NPCs."""
        # We can't easily test the tags directly, but we can verify
        # the method returns npc_reactions (even if empty)
        result = manager.shift_faction(
            faction=FactionName.EMBER_COLONIES,
            delta=1,
            reason="Test",
        )

        assert "npc_reactions" in result


class TestCrossFactionEffects:
    """Test interactions between factions."""

    def test_helping_one_faction_doesnt_affect_others(self, manager, campaign):
        """Helping one faction doesn't automatically affect others."""
        manager.shift_faction(FactionName.EMBER_COLONIES, 1, "Helped")

        # Check other factions are still neutral
        for faction in FactionName:
            if faction != FactionName.EMBER_COLONIES:
                standing = manager.current.factions.get(faction)
                assert standing.standing == Standing.NEUTRAL

    def test_can_have_mixed_standings(self, manager, campaign):
        """Player can be Allied with one faction and Hostile with another."""
        manager.shift_faction(FactionName.EMBER_COLONIES, 1, "Helped")
        manager.shift_faction(FactionName.EMBER_COLONIES, 1, "Helped again")
        manager.shift_faction(FactionName.NEXUS, -1, "Refused")
        manager.shift_faction(FactionName.NEXUS, -1, "Refused again")

        ember_standing = manager.current.factions.get(FactionName.EMBER_COLONIES)
        nexus_standing = manager.current.factions.get(FactionName.NEXUS)

        assert ember_standing.standing == Standing.ALLIED
        assert nexus_standing.standing == Standing.HOSTILE
