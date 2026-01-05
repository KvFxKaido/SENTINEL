"""
Tests for social energy (Pistachios) system.

Social energy tracks emotional bandwidth for interactions.
It depletes during social encounters and restores during solitude.
"""

import pytest
from src.state.schema import SocialEnergy, Character, Background


class TestSocialEnergyBands:
    """Test the narrative bands for social energy levels."""

    def test_centered_at_high_energy(self):
        """51-100% energy = Centered state."""
        energy = SocialEnergy(current=100)
        assert energy.state == "Centered"

        energy.current = 51
        assert energy.state == "Centered"

    def test_frayed_at_medium_energy(self):
        """26-50% energy = Frayed state."""
        energy = SocialEnergy(current=50)
        assert energy.state == "Frayed"

        energy.current = 26
        assert energy.state == "Frayed"

    def test_overloaded_at_low_energy(self):
        """1-25% energy = Overloaded state."""
        energy = SocialEnergy(current=25)
        assert energy.state == "Overloaded"

        energy.current = 1
        assert energy.state == "Overloaded"

    def test_shutdown_at_zero(self):
        """0% energy = Shutdown state."""
        energy = SocialEnergy(current=0)
        assert energy.state == "Shutdown"


class TestNarrativeHints:
    """Test the narrative flavor text for each state."""

    def test_each_state_has_hint(self):
        """Each energy state has a narrative hint."""
        test_cases = [
            (100, "ready for anything"),
            (50, "edges showing"),
            (10, "running on fumes"),
            (0, "need space"),
        ]

        for current, expected_hint in test_cases:
            energy = SocialEnergy(current=current)
            assert energy.narrative_hint == expected_hint, f"Failed at {current}%"


class TestEnergyBoundaries:
    """Test energy at boundary values."""

    def test_boundary_at_51(self):
        """51% is still Centered (just barely)."""
        energy = SocialEnergy(current=51)
        assert energy.state == "Centered"

        energy.current = 50
        assert energy.state == "Frayed"

    def test_boundary_at_26(self):
        """26% is still Frayed (just barely)."""
        energy = SocialEnergy(current=26)
        assert energy.state == "Frayed"

        energy.current = 25
        assert energy.state == "Overloaded"

    def test_boundary_at_1(self):
        """1% is still Overloaded (just barely)."""
        energy = SocialEnergy(current=1)
        assert energy.state == "Overloaded"

        energy.current = 0
        assert energy.state == "Shutdown"


class TestCharacterEnergy:
    """Test social energy as part of character state."""

    def test_character_starts_centered(self, character):
        """New characters start at full energy (Centered)."""
        assert character.social_energy.current == 100
        assert character.social_energy.state == "Centered"

    def test_energy_can_be_customized(self):
        """Characters can have custom energy track names."""
        char = Character(
            name="Test",
            background=Background.SURVIVOR,
            social_energy=SocialEnergy(
                name="Matches",
                current=75,
            ),
        )

        assert char.social_energy.name == "Matches"
        assert char.social_energy.current == 75


class TestManagerEnergyOperations:
    """Test energy operations through the manager."""

    def test_update_character_adjusts_energy(self, manager, campaign_with_character):
        """Manager can adjust character energy."""
        char = manager.current.characters[0]
        original = char.social_energy.current

        result = manager.update_character(
            character_id=char.id,
            social_energy_delta=-30,
        )

        assert result["before"]["social_energy"] == original
        assert result["after"]["social_energy"] == original - 30

    def test_energy_clamps_at_zero(self, manager, campaign_with_character):
        """Energy cannot go below 0."""
        char = manager.current.characters[0]

        manager.update_character(
            character_id=char.id,
            social_energy_delta=-200,
        )

        assert char.social_energy.current == 0
        assert char.social_energy.state == "Shutdown"

    def test_energy_clamps_at_100(self, manager, campaign_with_character):
        """Energy cannot go above 100."""
        char = manager.current.characters[0]

        manager.update_character(
            character_id=char.id,
            social_energy_delta=50,
        )

        assert char.social_energy.current == 100

    def test_result_includes_narrative_hint(self, manager, campaign_with_character):
        """Energy updates include narrative context."""
        char = manager.current.characters[0]

        result = manager.update_character(
            character_id=char.id,
            social_energy_delta=-80,
        )

        assert "narrative_hint" in result
        # At 20% energy, should be "running on fumes"
        assert result["narrative_hint"] == "running on fumes"


class TestEnergyRestorersAndDrains:
    """Test personalized restorers and drains."""

    def test_can_configure_restorers(self):
        """Energy tracks can list what restores them."""
        energy = SocialEnergy(
            restorers=["quiet reading", "solo walks", "technical work"],
        )

        assert len(energy.restorers) == 3
        assert "quiet reading" in energy.restorers

    def test_can_configure_drains(self):
        """Energy tracks can list what drains them."""
        energy = SocialEnergy(
            drains=["large meetings", "confrontation", "small talk"],
        )

        assert len(energy.drains) == 3
        assert "confrontation" in energy.drains


class TestInvokeRestorer:
    """Test the social energy carrot mechanic."""

    def test_invoke_restorer_success(self, manager, campaign_with_character):
        """Can spend energy for advantage when in element."""
        char = manager.current.characters[0]
        char.social_energy.current = 50
        char.social_energy.restorers = ["solo technical work", "quiet spaces"]

        result = manager.invoke_restorer(
            character_id=char.id,
            action="I focus on the technical problem alone",
        )

        assert result["success"] is True
        assert result["advantage_granted"] is True
        assert result["restorer_matched"] == "solo technical work"
        assert result["old_energy"] == 50
        assert result["new_energy"] == 40

    def test_invoke_restorer_not_in_element(self, manager, campaign_with_character):
        """Cannot invoke restorer for unrelated actions."""
        char = manager.current.characters[0]
        char.social_energy.current = 50
        char.social_energy.restorers = ["solo technical work", "quiet spaces"]

        result = manager.invoke_restorer(
            character_id=char.id,
            action="I negotiate with the crowd",
        )

        assert result["success"] is False
        assert result["reason"] == "not_in_element"
        assert "restorers" in result
        # Energy should not be deducted
        assert char.social_energy.current == 50

    def test_invoke_restorer_insufficient_energy(self, manager, campaign_with_character):
        """Cannot invoke restorer with insufficient energy."""
        char = manager.current.characters[0]
        char.social_energy.current = 5
        char.social_energy.restorers = ["solo technical work"]

        result = manager.invoke_restorer(
            character_id=char.id,
            action="I focus on the technical work",
        )

        assert result["success"] is False
        assert result["reason"] == "insufficient_energy"
        # Energy should not be deducted
        assert char.social_energy.current == 5

    def test_invoke_restorer_updates_state(self, manager, campaign_with_character):
        """Invoking restorer actually updates character state."""
        char = manager.current.characters[0]
        char.social_energy.current = 60
        char.social_energy.restorers = ["honest conversations"]

        manager.invoke_restorer(
            character_id=char.id,
            action="I have an honest conversation with them",
        )

        # State should be persisted
        assert char.social_energy.current == 50

    def test_invoke_restorer_narrative_varies_by_state(self, manager, campaign_with_character):
        """Narrative hint changes based on resulting energy state."""
        char = manager.current.characters[0]
        char.social_energy.restorers = ["quiet work"]

        # Test centered result (51+)
        char.social_energy.current = 70
        result = manager.invoke_restorer(char.id, "quiet work alone")
        assert "Advantage gained" in result["narrative_hint"]

        # Test frayed result (26-50)
        char.social_energy.current = 40
        result = manager.invoke_restorer(char.id, "quiet work alone")
        assert "edges are showing" in result["narrative_hint"]

        # Test overloaded result (1-25)
        char.social_energy.current = 20
        result = manager.invoke_restorer(char.id, "quiet work alone")
        assert "Running on fumes" in result["narrative_hint"]
