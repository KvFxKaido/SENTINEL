"""
Tests for NPC memory trigger system.

Memory triggers allow NPCs to react to tagged events,
shifting disposition and remembering past interactions.
"""

import pytest
from src.state.schema import (
    NPC,
    NPCAgenda,
    Disposition,
    MemoryTrigger,
    FactionName,
)


class TestMemoryTriggerFiring:
    """Test that triggers fire correctly."""

    def test_trigger_fires_on_matching_tag(self, npc_with_triggers):
        """Trigger fires when its condition tag is present."""
        npc = npc_with_triggers
        assert npc.disposition == Disposition.NEUTRAL

        fired = npc.check_triggers(["helped_ember_colonies"])

        assert len(fired) == 1
        assert fired[0].condition == "helped_ember_colonies"
        assert fired[0].triggered is True

    def test_trigger_does_not_fire_on_non_matching_tag(self, npc_with_triggers):
        """Trigger does not fire for unrelated tags."""
        npc = npc_with_triggers

        fired = npc.check_triggers(["helped_nexus", "random_event"])

        assert len(fired) == 0

    def test_one_shot_trigger_fires_only_once(self, npc_with_triggers):
        """One-shot triggers only fire once."""
        npc = npc_with_triggers

        # First trigger
        fired1 = npc.check_triggers(["helped_ember_colonies"])
        assert len(fired1) == 1

        # Second trigger attempt - should not fire
        fired2 = npc.check_triggers(["helped_ember_colonies"])
        assert len(fired2) == 0

    def test_repeatable_trigger_fires_multiple_times(self, npc_with_triggers):
        """Non-one-shot triggers can fire multiple times."""
        npc = npc_with_triggers

        # First trigger
        fired1 = npc.check_triggers(["knows_secret"])
        assert len(fired1) == 1

        # Second trigger - should still fire
        fired2 = npc.check_triggers(["knows_secret"])
        assert len(fired2) == 1

    def test_multiple_triggers_can_fire_together(self):
        """Multiple triggers can fire from the same tag list."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            memory_triggers=[
                MemoryTrigger(condition="tag_a", effect="effect a", one_shot=True),
                MemoryTrigger(condition="tag_b", effect="effect b", one_shot=True),
            ],
        )

        fired = npc.check_triggers(["tag_a", "tag_b"])

        assert len(fired) == 2


class TestDispositionShift:
    """Test disposition changes from triggers."""

    def test_positive_shift_increases_disposition(self, npc_with_triggers):
        """Positive disposition_shift moves toward loyal."""
        npc = npc_with_triggers
        assert npc.disposition == Disposition.NEUTRAL

        npc.check_triggers(["helped_ember_colonies"])

        assert npc.disposition == Disposition.WARM

    def test_negative_shift_decreases_disposition(self, npc_with_triggers):
        """Negative disposition_shift moves toward hostile."""
        npc = npc_with_triggers
        assert npc.disposition == Disposition.NEUTRAL

        npc.check_triggers(["betrayed_ember_colonies"])

        # -2 from neutral should go to hostile
        assert npc.disposition == Disposition.HOSTILE

    def test_shift_clamps_at_boundaries(self):
        """Disposition shift cannot go below hostile or above loyal."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            disposition=Disposition.HOSTILE,
            memory_triggers=[
                MemoryTrigger(condition="extreme_betrayal", effect="even more hostile", disposition_shift=-5),
            ],
        )

        npc.check_triggers(["extreme_betrayal"])

        # Should stay at hostile, not go negative
        assert npc.disposition == Disposition.HOSTILE

    def test_zero_shift_does_not_change_disposition(self, npc_with_triggers):
        """Triggers with disposition_shift=0 don't change disposition."""
        npc = npc_with_triggers
        original = npc.disposition

        npc.check_triggers(["knows_secret"])

        assert npc.disposition == original


class TestManagerTriggerIntegration:
    """Test trigger checking through the campaign manager."""

    def test_manager_checks_all_active_npcs(self, manager, campaign, npc_with_triggers):
        """Manager.check_npc_triggers checks all active NPCs."""
        manager.add_npc(npc_with_triggers, active=True)

        results = manager.check_npc_triggers(["helped_ember_colonies"])

        assert len(results) == 1
        assert results[0]["npc_name"] == "Marta"
        assert results[0]["new_disposition"] == "warm"

    def test_faction_shift_generates_trigger_tags(self, manager, campaign, npc_with_triggers):
        """Faction shifts generate appropriate trigger tags."""
        manager.add_npc(npc_with_triggers, active=True)

        # This should generate "helped_ember_colonies" tag and trigger the NPC
        result = manager.shift_faction(
            faction=FactionName.EMBER_COLONIES,
            delta=1,
            reason="Helped with supply run",
        )

        # Check that NPC reactions were included
        assert "npc_reactions" in result
        assert len(result["npc_reactions"]) == 1
