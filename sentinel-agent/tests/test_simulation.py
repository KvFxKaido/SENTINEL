"""Tests for simulation module."""

import pytest
from src.simulation.personas import PERSONAS, get_persona_system_prompt
from src.simulation.player import AIPlayer
from src.simulation.runner import (
    SimulationTranscript,
    extract_choices,
    create_simulation_character,
)
from src.state.manager import CampaignManager
from src.state.store import MemoryCampaignStore
from src.llm import MockLLMClient


class TestPersonas:
    """Test persona definitions."""

    def test_all_personas_exist(self):
        """All four personas are defined."""
        assert "cautious" in PERSONAS
        assert "opportunist" in PERSONAS
        assert "principled" in PERSONAS
        assert "chaotic" in PERSONAS

    def test_persona_has_required_fields(self):
        """Each persona has required fields."""
        for name, persona in PERSONAS.items():
            assert "name" in persona, f"{name} missing 'name'"
            assert "values" in persona, f"{name} missing 'values'"
            assert "style" in persona, f"{name} missing 'style'"
            assert "fears" in persona, f"{name} missing 'fears'"
            assert "enhancement_stance" in persona, f"{name} missing 'enhancement_stance'"

    def test_get_persona_system_prompt(self):
        """System prompt includes persona details."""
        prompt = get_persona_system_prompt("cautious", "Val")

        assert "Val" in prompt
        assert "Cautious" in prompt
        assert "safety" in prompt.lower()

    def test_unknown_persona_defaults_to_cautious(self):
        """Unknown persona falls back to cautious."""
        prompt = get_persona_system_prompt("nonexistent", "Test")
        assert "Cautious" in prompt


class TestAIPlayer:
    """Test AIPlayer class."""

    def test_player_creation(self):
        """Can create AI player with persona."""
        client = MockLLMClient(responses=["I wait and observe."])
        player = AIPlayer(client, persona="cautious")

        assert player.persona_name == "cautious"
        assert player.persona["name"] == "Cautious"

    def test_player_responds(self):
        """Player generates response to GM text."""
        client = MockLLMClient(responses=["I approach carefully."])
        player = AIPlayer(client, persona="cautious")

        response = player.respond("You see a guard at the checkpoint.")

        assert response == "I approach carefully."
        assert len(client.calls) == 1

    def test_player_with_choices(self):
        """Player can respond when given choices."""
        client = MockLLMClient(responses=["I choose option 2."])
        player = AIPlayer(client, persona="opportunist")

        response = player.respond(
            "What do you do?",
            choices=["Fight", "Flee", "Negotiate"]
        )

        assert response == "I choose option 2."

    def test_player_tracks_decisions(self):
        """Player tracks key decisions."""
        client = MockLLMClient(responses=[
            "I improvise something unexpected.",
            "I accept the enhancement gladly.",
            "I refuse the offer.",
        ])
        player = AIPlayer(client, persona="chaotic")

        player.respond("Choice?", choices=["A", "B"])  # improvised
        player.respond("Accept enhancement?")  # accepted
        player.respond("Another offer?")  # refused

        stats = player.get_stats()
        assert stats["improvisations"] == 1
        assert stats["enhancements_accepted"] == 1
        assert stats["offers_refused"] == 1


class TestExtractChoices:
    """Test choice extraction from GM text."""

    def test_numbered_choices(self):
        """Extract numbered list choices."""
        text = """You stand at the crossroads.

1. Take the left path
2. Take the right path
3. Go back the way you came
"""
        choices = extract_choices(text)
        assert len(choices) == 3
        assert "Take the left path" in choices
        assert "Take the right path" in choices

    def test_no_choices(self):
        """Returns empty list when no choices."""
        text = "The door opens. Inside is darkness."
        choices = extract_choices(text)
        assert choices == []

    def test_formal_choice_block(self):
        """Extract formal choice block format."""
        text = """---CHOICE---
stakes: high
options:
- Accept the deal
- Walk away
- Counter-offer
---END---"""
        choices = extract_choices(text)
        assert len(choices) == 3
        assert "Accept the deal" in choices


class TestSimulationTranscript:
    """Test transcript management."""

    def test_add_turns(self):
        """Can add turns to transcript."""
        transcript = SimulationTranscript(persona="cautious")

        transcript.add_turn("gm", "The scene begins...")
        transcript.add_turn("player", "I look around.")
        transcript.add_turn("gm", "You see a door.")

        assert len(transcript.turns) == 3

    def test_turn_numbering(self):
        """Turns are numbered correctly."""
        transcript = SimulationTranscript()

        transcript.add_turn("gm", "GM text 1")
        transcript.add_turn("player", "Player 1")
        transcript.add_turn("gm", "GM text 2")
        transcript.add_turn("player", "Player 2")

        gm_turns = [t for t in transcript.turns if t.role == "gm"]
        assert gm_turns[0].turn_number == 1
        assert gm_turns[1].turn_number == 2

    def test_to_markdown(self):
        """Transcript converts to markdown."""
        transcript = SimulationTranscript(
            persona="opportunist",
            character_name="Kade",
            character_background="Operative",
        )
        transcript.add_turn("gm", "The mission begins.", ["Accept", "Refuse"])
        transcript.add_turn("player", "I accept.")
        transcript.player_stats = {"total_decisions": 1}

        md = transcript.to_markdown()

        assert "# Simulation Transcript" in md
        assert "opportunist" in md
        assert "Kade" in md
        assert "The mission begins." in md
        assert "Accept" in md


class TestCreateSimulationCharacter:
    """Test character creation for simulation."""

    def test_creates_character(self):
        """Creates character for persona."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = create_simulation_character(manager, "cautious")

        assert char.name == "Val"
        assert char.background.value == "Witness"
        assert char in manager.current.characters

    def test_different_personas_different_backgrounds(self):
        """Different personas get different backgrounds."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        cautious = create_simulation_character(manager, "cautious")
        manager.current.characters.clear()

        opportunist = create_simulation_character(manager, "opportunist")

        assert cautious.background != opportunist.background
