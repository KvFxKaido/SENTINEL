"""
Pytest fixtures for SENTINEL agent tests.

Provides in-memory stores and mock clients for isolated testing.
"""

import pytest
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.state import (
    CampaignManager,
    MemoryCampaignStore,
    Campaign,
    Character,
    NPC,
)
from src.state.schema import (
    Background,
    FactionName,
    Disposition,
    NPCAgenda,
    DispositionModifier,
    MemoryTrigger,
)
from src.llm import MockLLMClient


@pytest.fixture
def memory_store():
    """In-memory campaign store for testing."""
    return MemoryCampaignStore()


@pytest.fixture
def manager(memory_store):
    """Campaign manager with in-memory store."""
    return CampaignManager(memory_store)


@pytest.fixture
def campaign(manager):
    """Fresh campaign for testing."""
    return manager.create_campaign("Test Campaign")


@pytest.fixture
def character():
    """Sample player character."""
    return Character(
        name="Test Operative",
        callsign="Ghost",
        background=Background.OPERATIVE,
    )


@pytest.fixture
def campaign_with_character(manager, character):
    """Campaign with a character added."""
    campaign = manager.create_campaign("Test Campaign")
    manager.add_character(character)
    return campaign


@pytest.fixture
def npc_with_triggers():
    """NPC with memory triggers configured."""
    return NPC(
        name="Marta",
        faction=FactionName.EMBER_COLONIES,
        agenda=NPCAgenda(
            wants="Protect the settlement",
            fears="Nexus surveillance",
        ),
        disposition=Disposition.NEUTRAL,
        memory_triggers=[
            MemoryTrigger(
                condition="helped_ember_colonies",  # Tag format: helped_{faction_name}
                effect="warms up, shares more",
                disposition_shift=1,
                one_shot=True,
            ),
            MemoryTrigger(
                condition="betrayed_ember_colonies",  # Tag format: betrayed_{faction_name}
                effect="becomes hostile, cuts contact",
                disposition_shift=-2,
                one_shot=True,
            ),
            MemoryTrigger(
                condition="knows_secret",
                effect="mentions the hidden cache",
                disposition_shift=0,
                one_shot=False,  # Can trigger multiple times
            ),
        ],
    )


@pytest.fixture
def npc_with_modifiers():
    """NPC with disposition modifiers configured."""
    return NPC(
        name="Director Chen",
        faction=FactionName.NEXUS,
        agenda=NPCAgenda(
            wants="Expand Nexus influence",
            fears="Losing control of the network",
        ),
        disposition=Disposition.NEUTRAL,
        disposition_modifiers={
            "hostile": DispositionModifier(
                tone="cold and threatening",
                reveals=["nothing useful"],
                withholds=["everything"],
                tells=["hand near panic button", "guards on alert"],
            ),
            "wary": DispositionModifier(
                tone="clipped and formal",
                reveals=["public information only"],
                withholds=["operational details", "personal opinions"],
                tells=["maintains distance", "checks exits"],
            ),
            "neutral": DispositionModifier(
                tone="professional but guarded",
                reveals=["general faction goals", "public projects"],
                withholds=["surveillance capabilities", "internal politics"],
                tells=["polite but measured responses"],
            ),
            "warm": DispositionModifier(
                tone="collegial, drops some formality",
                reveals=["some internal concerns", "personal motivations"],
                withholds=["classified operations"],
                tells=["genuine smiles", "uses first names"],
            ),
            "loyal": DispositionModifier(
                tone="frank and trusting",
                reveals=["classified concerns", "doubts about leadership"],
                withholds=["only things that would endanger others"],
                tells=["speaks freely", "asks for advice"],
            ),
        },
    )


@pytest.fixture
def mock_llm():
    """Mock LLM client for testing agent without API calls."""
    return MockLLMClient(
        responses=["The GM responds with narrative text."],
        model_name="test-model",
    )
