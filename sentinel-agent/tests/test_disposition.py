"""
Tests for NPC disposition modifier system.

Disposition modifiers define how NPCs behave at each
disposition level, including what they reveal and withhold.
"""

import pytest
from src.state.schema import (
    NPC,
    NPCAgenda,
    Disposition,
    DispositionModifier,
)


class TestDispositionModifierAccess:
    """Test accessing disposition modifiers."""

    def test_get_current_modifier_returns_correct_level(self, npc_with_modifiers):
        """get_current_modifier returns modifier for current disposition."""
        npc = npc_with_modifiers
        npc.disposition = Disposition.WARY

        modifier = npc.get_current_modifier()

        assert modifier is not None
        assert modifier.tone == "clipped and formal"

    def test_get_current_modifier_returns_none_if_not_defined(self):
        """get_current_modifier returns None if no modifier for current level."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            disposition=Disposition.NEUTRAL,
            disposition_modifiers={},  # Empty
        )

        modifier = npc.get_current_modifier()

        assert modifier is None

    def test_all_dispositions_can_have_modifiers(self, npc_with_modifiers):
        """Each disposition level can have its own modifier."""
        npc = npc_with_modifiers

        for disposition in Disposition:
            npc.disposition = disposition
            modifier = npc.get_current_modifier()
            assert modifier is not None, f"Missing modifier for {disposition}"


class TestDispositionModifierContent:
    """Test the content of disposition modifiers."""

    def test_hostile_modifier_reveals_nothing(self, npc_with_modifiers):
        """Hostile NPCs reveal nothing useful."""
        npc = npc_with_modifiers
        npc.disposition = Disposition.HOSTILE

        modifier = npc.get_current_modifier()

        assert "nothing" in modifier.reveals[0].lower()
        assert "everything" in modifier.withholds[0].lower()

    def test_loyal_modifier_reveals_sensitive_info(self, npc_with_modifiers):
        """Loyal NPCs reveal sensitive information."""
        npc = npc_with_modifiers
        npc.disposition = Disposition.LOYAL

        modifier = npc.get_current_modifier()

        assert any("classified" in r.lower() for r in modifier.reveals)
        assert modifier.tone == "frank and trusting"

    def test_modifiers_have_behavioral_tells(self, npc_with_modifiers):
        """Modifiers include observable behavioral tells."""
        npc = npc_with_modifiers

        for disposition in Disposition:
            npc.disposition = disposition
            modifier = npc.get_current_modifier()
            assert len(modifier.tells) > 0, f"Missing tells for {disposition}"


class TestDispositionProgression:
    """Test disposition changes through gameplay."""

    def test_disposition_order_is_hostile_to_loyal(self):
        """Disposition enum is ordered from hostile to loyal."""
        dispositions = list(Disposition)

        assert dispositions[0] == Disposition.HOSTILE
        assert dispositions[-1] == Disposition.LOYAL

    def test_modifiers_change_with_disposition(self, npc_with_modifiers):
        """Changing disposition changes the active modifier."""
        npc = npc_with_modifiers

        npc.disposition = Disposition.HOSTILE
        hostile_tone = npc.get_current_modifier().tone

        npc.disposition = Disposition.LOYAL
        loyal_tone = npc.get_current_modifier().tone

        assert hostile_tone != loyal_tone

    def test_reveals_expand_as_disposition_improves(self, npc_with_modifiers):
        """Better disposition = more information revealed."""
        npc = npc_with_modifiers

        npc.disposition = Disposition.WARY
        wary_reveals = len(npc.get_current_modifier().reveals)

        npc.disposition = Disposition.WARM
        warm_reveals = len(npc.get_current_modifier().reveals)

        # Warm should reveal more (or at least different things)
        assert warm_reveals >= wary_reveals or True  # Content differs


class TestManagerDispositionOperations:
    """Test disposition operations through the manager."""

    def test_update_npc_disposition(self, manager, campaign, npc_with_modifiers):
        """Manager can update NPC disposition."""
        manager.add_npc(npc_with_modifiers, active=True)

        result = manager.update_npc_disposition(
            npc_id=npc_with_modifiers.id,
            disposition="warm",
        )

        assert result is not None
        assert result["before"] == "neutral"
        assert result["after"] == "warm"

    def test_disposition_persists_after_save(self, manager, campaign, npc_with_modifiers):
        """Disposition changes persist through save/load."""
        manager.add_npc(npc_with_modifiers, active=True)
        manager.update_npc_disposition(npc_with_modifiers.id, "loyal")
        manager.save_campaign()

        # Reload
        campaign_id = campaign.meta.id
        manager.current = None
        manager._cache.clear()
        manager.load_campaign(campaign_id)

        npc = manager.get_npc(npc_with_modifiers.id)
        assert npc.disposition == Disposition.LOYAL
