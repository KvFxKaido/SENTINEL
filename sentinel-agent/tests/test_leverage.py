"""Tests for enhancement leverage system."""

import pytest
from src.state.schema import (
    FactionName,
    LeverageWeight,
    Character,
    Background,
)
from src.state.manager import CampaignManager
from src.state.store import MemoryCampaignStore


class TestGrantEnhancement:
    """Test enhancement granting."""

    def test_grant_basic(self):
        """Can grant enhancement to character."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        enhancement = manager.grant_enhancement(
            character_id=char.id,
            name="Neural Link",
            source=FactionName.NEXUS,
            benefit="Direct data access",
            cost="Nexus can see your thoughts",
        )

        assert enhancement.name == "Neural Link"
        assert enhancement.source == FactionName.NEXUS
        assert enhancement.leverage.weight == LeverageWeight.LIGHT
        assert enhancement.leverage.compliance_count == 0
        assert enhancement.leverage.resistance_count == 0
        assert enhancement.leverage.pending_obligation is None

    def test_grant_sets_session(self):
        """Enhancement records which session it was granted."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")
        manager.current.meta.session_count = 3

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        enhancement = manager.grant_enhancement(
            character_id=char.id,
            name="Debt Chip",
            source=FactionName.STEEL_SYNDICATE,
            benefit="Credit line",
            cost="They own you",
        )

        assert enhancement.granted_session == 3

    def test_grant_extracts_keywords(self):
        """Enhancement should have keywords for hint matching."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        enhancement = manager.grant_enhancement(
            character_id=char.id,
            name="Ghost Protocol Access",
            source=FactionName.GHOST_NETWORKS,
            benefit="Emergency extraction",
            cost="Owe them a favor",
        )

        assert len(enhancement.leverage_keywords) > 0
        assert any("ghost" in kw for kw in enhancement.leverage_keywords)

    def test_wanderers_cannot_grant(self):
        """Wanderers don't offer enhancements."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.PILGRIM)
        manager.add_character(char)

        with pytest.raises(ValueError, match="does not offer enhancements"):
            manager.grant_enhancement(
                character_id=char.id,
                name="Road Knowledge",
                source=FactionName.WANDERERS,
                benefit="Know the routes",
                cost="None",
            )

    def test_cultivators_cannot_grant(self):
        """Cultivators don't offer enhancements."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.CARETAKER)
        manager.add_character(char)

        with pytest.raises(ValueError, match="does not offer enhancements"):
            manager.grant_enhancement(
                character_id=char.id,
                name="Seed Vault Access",
                source=FactionName.CULTIVATORS,
                benefit="Food security",
                cost="None",
            )


class TestCallLeverage:
    """Test leverage calling."""

    @pytest.fixture
    def setup_with_enhancement(self):
        """Create manager with character who has enhancement."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        enhancement = manager.grant_enhancement(
            character_id=char.id,
            name="Neural Link",
            source=FactionName.NEXUS,
            benefit="Data access",
            cost="Surveillance",
        )

        return manager, char, enhancement

    def test_call_leverage_basic(self, setup_with_enhancement):
        """Can call leverage on enhancement."""
        manager, char, enhancement = setup_with_enhancement

        result = manager.call_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            demand="Access the Lattice network for us",
            weight="medium",
        )

        assert result["enhancement"] == "Neural Link"
        assert result["faction"] == "Nexus"
        assert result["demand"] == "Access the Lattice network for us"
        assert result["weight"] == "medium"

        # Check the enhancement was updated
        updated = char.enhancements[0]
        assert updated.leverage.pending_obligation == "Access the Lattice network for us"
        assert updated.leverage.weight == LeverageWeight.MEDIUM

    def test_no_double_call(self, setup_with_enhancement):
        """Cannot call leverage while another is pending."""
        manager, char, enhancement = setup_with_enhancement

        manager.call_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            demand="First demand",
        )

        result = manager.call_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            demand="Second demand",
        )

        assert "error" in result
        assert "pending" in result["error"].lower()


class TestResolveLeverage:
    """Test leverage resolution."""

    @pytest.fixture
    def setup_with_pending(self):
        """Create manager with pending leverage."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        enhancement = manager.grant_enhancement(
            character_id=char.id,
            name="Syndicate Chip",
            source=FactionName.STEEL_SYNDICATE,
            benefit="Credit access",
            cost="They own you",
        )

        manager.call_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            demand="Transport this package",
            weight="medium",
        )

        return manager, char, enhancement

    def test_comply_clears_obligation(self, setup_with_pending):
        """Compliance clears pending obligation."""
        manager, char, enhancement = setup_with_pending

        result = manager.resolve_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            response="comply",
            outcome="Transported the package without opening it",
        )

        assert result["response"] == "comply"
        assert char.enhancements[0].leverage.pending_obligation is None
        assert char.enhancements[0].leverage.compliance_count == 1

    def test_comply_reduces_weight(self, setup_with_pending):
        """Compliance may reduce leverage weight."""
        manager, char, enhancement = setup_with_pending

        result = manager.resolve_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            response="comply",
            outcome="Did what they asked",
        )

        # Medium -> Light
        assert result["new_weight"] == "light"

    def test_resist_increases_weight(self, setup_with_pending):
        """Resistance escalates leverage weight."""
        manager, char, enhancement = setup_with_pending

        result = manager.resolve_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            response="resist",
            outcome="Refused to transport unknown cargo",
        )

        # Medium -> Heavy
        assert result["new_weight"] == "heavy"
        assert char.enhancements[0].leverage.resistance_count == 1

    def test_negotiate_keeps_weight(self, setup_with_pending):
        """Negotiation keeps weight the same."""
        manager, char, enhancement = setup_with_pending

        result = manager.resolve_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            response="negotiate",
            outcome="Agreed to a different task instead",
        )

        # Medium stays Medium
        assert result["new_weight"] == "medium"

    def test_weight_cannot_go_below_light(self):
        """Weight floors at light."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        enhancement = manager.grant_enhancement(
            character_id=char.id,
            name="Chip",
            source=FactionName.NEXUS,
            benefit="Data",
            cost="Strings",
        )

        # Call at light weight
        manager.call_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            demand="Small favor",
            weight="light",
        )

        result = manager.resolve_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            response="comply",
            outcome="Did it",
        )

        # Still light (can't go lower)
        assert result["new_weight"] == "light"

    def test_weight_cannot_go_above_heavy(self):
        """Weight caps at heavy."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        enhancement = manager.grant_enhancement(
            character_id=char.id,
            name="Chip",
            source=FactionName.STEEL_SYNDICATE,
            benefit="Credit",
            cost="Soul",
        )

        # Call at heavy weight
        manager.call_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            demand="Big demand",
            weight="heavy",
        )

        result = manager.resolve_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            response="resist",
            outcome="Said no",
        )

        # Still heavy (can't go higher)
        assert result["new_weight"] == "heavy"


class TestCheckLeverageHints:
    """Test leverage hint checking."""

    @pytest.fixture
    def setup_with_enhancements(self):
        """Create manager with multiple enhancements."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        manager.grant_enhancement(
            character_id=char.id,
            name="Neural Link",
            source=FactionName.NEXUS,
            benefit="Data access",
            cost="Surveillance",
        )

        manager.grant_enhancement(
            character_id=char.id,
            name="Credit Line",
            source=FactionName.STEEL_SYNDICATE,
            benefit="Emergency funds",
            cost="Interest",
        )

        return manager, char

    def test_keyword_match_returns_hint(self, setup_with_enhancements):
        """Matching keywords returns leverage hints."""
        manager, char = setup_with_enhancements

        # "neural" and "data" should match Neural Link keywords
        hints = manager.check_leverage_hints("I need to access the neural data network")

        # Should find at least one hint
        assert len(hints) >= 1
        nexus_hint = next((h for h in hints if h["faction"] == "Nexus"), None)
        assert nexus_hint is not None
        assert nexus_hint["enhancement_name"] == "Neural Link"

    def test_no_match_returns_empty(self, setup_with_enhancements):
        """No keyword match returns empty list."""
        manager, char = setup_with_enhancements

        hints = manager.check_leverage_hints("I order coffee")
        assert hints == []

    def test_pending_obligation_skipped(self, setup_with_enhancements):
        """Enhancements with pending obligations don't generate hints."""
        manager, char = setup_with_enhancements

        # Call leverage on Nexus enhancement
        nexus_enh = char.enhancements[0]
        manager.call_leverage(
            character_id=char.id,
            enhancement_id=nexus_enh.id,
            demand="Do something",
        )

        # Check for hints - should skip the one with pending
        hints = manager.check_leverage_hints("I need neural data access")
        nexus_hints = [h for h in hints if h["faction"] == "Nexus"]
        assert len(nexus_hints) == 0

    def test_hint_includes_context(self, setup_with_enhancements):
        """Hints include useful context for GM."""
        manager, char = setup_with_enhancements

        hints = manager.check_leverage_hints("I need neural data access from Nexus")

        if hints:
            hint = hints[0]
            assert "character_id" in hint
            assert "enhancement_id" in hint
            assert "weight" in hint
            assert "matched_keywords" in hint
            assert "sessions_since_grant" in hint


class TestLeverageLogging:
    """Test that leverage events are logged to history."""

    def test_grant_logs_hinge(self):
        """Granting enhancement logs a hinge moment."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        manager.grant_enhancement(
            character_id=char.id,
            name="Chip",
            source=FactionName.NEXUS,
            benefit="Power",
            cost="Strings",
        )

        # Should have a history entry
        history = manager.current.history
        assert len(history) >= 1
        assert any("enhancement" in h.summary.lower() for h in history)

    def test_resolve_logs_consequence(self):
        """Resolving leverage logs to history."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        enhancement = manager.grant_enhancement(
            character_id=char.id,
            name="Chip",
            source=FactionName.STEEL_SYNDICATE,
            benefit="Credit",
            cost="Debt",
        )

        manager.call_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            demand="Pay up",
        )

        initial_count = len(manager.current.history)

        manager.resolve_leverage(
            character_id=char.id,
            enhancement_id=enhancement.id,
            response="resist",
            outcome="Refused to pay",
        )

        # Should have new history entry
        assert len(manager.current.history) > initial_count
        last_entry = manager.current.history[-1]
        assert "resist" in last_entry.summary.lower()
