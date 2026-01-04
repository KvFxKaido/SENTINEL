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
