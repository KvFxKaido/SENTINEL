"""
Tests for NPC rules as pure functions.

These tests verify the extracted pure functions work correctly
independent of the NPC model methods.
"""

import pytest
from src.rules.npc import (
    get_disposition_modifier,
    check_triggers,
    apply_disposition_shift,
)
from src.state.schema import (
    NPC,
    NPCAgenda,
    Disposition,
    DispositionModifier,
    MemoryTrigger,
)


class TestGetDispositionModifier:
    """Test get_disposition_modifier pure function."""

    def test_returns_modifier_for_current_disposition(self):
        """Returns the modifier matching current disposition."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            disposition=Disposition.WARY,
            disposition_modifiers={
                "wary": DispositionModifier(
                    tone="cautious",
                    reveals=["nothing sensitive"],
                    withholds=["everything important"],
                    tells=["keeps distance"],
                ),
            },
        )

        modifier = get_disposition_modifier(npc)

        assert modifier is not None
        assert modifier.tone == "cautious"

    def test_returns_none_when_no_modifier_defined(self):
        """Returns None if no modifier for current disposition."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            disposition=Disposition.NEUTRAL,
            disposition_modifiers={},
        )

        modifier = get_disposition_modifier(npc)

        assert modifier is None

    def test_changes_with_disposition_change(self):
        """Returns different modifier when disposition changes."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            disposition=Disposition.NEUTRAL,
            disposition_modifiers={
                "neutral": DispositionModifier(
                    tone="professional",
                    reveals=["public info"],
                    withholds=["secrets"],
                    tells=["measured responses"],
                ),
                "warm": DispositionModifier(
                    tone="friendly",
                    reveals=["personal opinions"],
                    withholds=["classified"],
                    tells=["genuine smiles"],
                ),
            },
        )

        neutral_modifier = get_disposition_modifier(npc)
        assert neutral_modifier.tone == "professional"

        npc.disposition = Disposition.WARM
        warm_modifier = get_disposition_modifier(npc)
        assert warm_modifier.tone == "friendly"


class TestApplyDispositionShift:
    """Test apply_disposition_shift pure function."""

    def test_positive_shift_moves_toward_loyal(self):
        """Positive delta moves disposition toward loyal."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            disposition=Disposition.NEUTRAL,
        )

        new_disposition = apply_disposition_shift(npc, +1)

        assert new_disposition == Disposition.WARM
        assert npc.disposition == Disposition.WARM

    def test_negative_shift_moves_toward_hostile(self):
        """Negative delta moves disposition toward hostile."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            disposition=Disposition.NEUTRAL,
        )

        new_disposition = apply_disposition_shift(npc, -1)

        assert new_disposition == Disposition.WARY
        assert npc.disposition == Disposition.WARY

    def test_clamps_at_loyal(self):
        """Cannot shift past loyal."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            disposition=Disposition.LOYAL,
        )

        new_disposition = apply_disposition_shift(npc, +5)

        assert new_disposition == Disposition.LOYAL

    def test_clamps_at_hostile(self):
        """Cannot shift past hostile."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            disposition=Disposition.HOSTILE,
        )

        new_disposition = apply_disposition_shift(npc, -5)

        assert new_disposition == Disposition.HOSTILE

    def test_zero_shift_no_change(self):
        """Zero delta does not change disposition."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            disposition=Disposition.NEUTRAL,
        )

        new_disposition = apply_disposition_shift(npc, 0)

        assert new_disposition == Disposition.NEUTRAL

    def test_large_shift_multiple_steps(self):
        """Large delta can skip multiple levels."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            disposition=Disposition.NEUTRAL,
        )

        # Neutral -> Wary -> Hostile (-2 steps)
        new_disposition = apply_disposition_shift(npc, -2)

        assert new_disposition == Disposition.HOSTILE


class TestCheckTriggers:
    """Test check_triggers pure function."""

    def test_fires_matching_trigger(self):
        """Fires trigger when condition matches a tag."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            memory_triggers=[
                MemoryTrigger(
                    condition="helped_faction",
                    effect="becomes friendlier",
                    disposition_shift=1,
                ),
            ],
        )

        fired = check_triggers(npc, ["helped_faction"])

        assert len(fired) == 1
        assert fired[0].condition == "helped_faction"
        assert fired[0].triggered is True

    def test_does_not_fire_non_matching(self):
        """Does not fire trigger when condition doesn't match."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            memory_triggers=[
                MemoryTrigger(
                    condition="helped_faction",
                    effect="becomes friendlier",
                ),
            ],
        )

        fired = check_triggers(npc, ["betrayed_faction"])

        assert len(fired) == 0

    def test_one_shot_fires_once(self):
        """One-shot trigger only fires once."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            memory_triggers=[
                MemoryTrigger(
                    condition="secret_revealed",
                    effect="remembers forever",
                    one_shot=True,
                ),
            ],
        )

        # First time
        fired1 = check_triggers(npc, ["secret_revealed"])
        assert len(fired1) == 1

        # Second time - should not fire
        fired2 = check_triggers(npc, ["secret_revealed"])
        assert len(fired2) == 0

    def test_repeatable_fires_multiple_times(self):
        """Non-one-shot trigger can fire multiple times."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            memory_triggers=[
                MemoryTrigger(
                    condition="greeting",
                    effect="acknowledges",
                    one_shot=False,
                ),
            ],
        )

        fired1 = check_triggers(npc, ["greeting"])
        fired2 = check_triggers(npc, ["greeting"])

        assert len(fired1) == 1
        assert len(fired2) == 1

    def test_applies_disposition_shift(self):
        """Firing trigger applies disposition shift."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            disposition=Disposition.NEUTRAL,
            memory_triggers=[
                MemoryTrigger(
                    condition="betrayed",
                    effect="becomes hostile",
                    disposition_shift=-2,
                ),
            ],
        )

        check_triggers(npc, ["betrayed"])

        assert npc.disposition == Disposition.HOSTILE

    def test_multiple_triggers_can_fire(self):
        """Multiple triggers can fire from same tag list."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            memory_triggers=[
                MemoryTrigger(condition="tag_a", effect="effect a"),
                MemoryTrigger(condition="tag_b", effect="effect b"),
                MemoryTrigger(condition="tag_c", effect="effect c"),
            ],
        )

        fired = check_triggers(npc, ["tag_a", "tag_c"])

        assert len(fired) == 2
        conditions = [t.condition for t in fired]
        assert "tag_a" in conditions
        assert "tag_c" in conditions

    def test_zero_shift_no_disposition_change(self):
        """Trigger with zero shift doesn't change disposition."""
        npc = NPC(
            name="Test",
            agenda=NPCAgenda(wants="test", fears="test"),
            disposition=Disposition.NEUTRAL,
            memory_triggers=[
                MemoryTrigger(
                    condition="noticed",
                    effect="takes note",
                    disposition_shift=0,
                ),
            ],
        )

        check_triggers(npc, ["noticed"])

        assert npc.disposition == Disposition.NEUTRAL
