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


class TestRefuseEnhancement:
    """Test enhancement refusal and reputation system."""

    def test_refuse_basic(self):
        """Can refuse an enhancement offer."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        refusal = manager.refuse_enhancement(
            character_id=char.id,
            name="Neural Link",
            source=FactionName.NEXUS,
            benefit="Direct data access",
            reason_refused="I won't let them in my head",
        )

        assert refusal.name == "Neural Link"
        assert refusal.source == FactionName.NEXUS
        assert refusal.reason_refused == "I won't let them in my head"
        assert len(char.refused_enhancements) == 1

    def test_refuse_logs_hinge(self):
        """Refusal is logged as a hinge moment."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        manager.refuse_enhancement(
            character_id=char.id,
            name="Debt Chip",
            source=FactionName.STEEL_SYNDICATE,
            benefit="Credit line",
            reason_refused="I won't be owned",
        )

        # Should have history entry
        history = manager.current.history
        assert len(history) >= 1
        assert any("refused" in h.summary.lower() for h in history)


class TestRefusalReputation:
    """Test refusal reputation calculation."""

    def test_no_refusals_no_title(self):
        """No refusals means no title."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        rep = manager.get_refusal_reputation(char.id)
        assert rep["title"] is None
        assert rep["count"] == 0

    def test_one_refusal_no_title(self):
        """One refusal doesn't grant a title yet."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        manager.refuse_enhancement(
            character_id=char.id,
            name="Chip",
            source=FactionName.NEXUS,
            benefit="Power",
            reason_refused="No thanks",
        )

        rep = manager.get_refusal_reputation(char.id)
        assert rep["title"] is None
        assert rep["count"] == 1
        assert rep["narrative_hint"] is not None

    def test_two_refusals_unbought(self):
        """Two refusals grants 'The Unbought' title."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        manager.refuse_enhancement(
            character_id=char.id,
            name="Chip 1",
            source=FactionName.NEXUS,
            benefit="Power",
            reason_refused="No",
        )
        manager.refuse_enhancement(
            character_id=char.id,
            name="Chip 2",
            source=FactionName.STEEL_SYNDICATE,
            benefit="Credit",
            reason_refused="No",
        )

        rep = manager.get_refusal_reputation(char.id)
        assert rep["title"] == "The Unbought"
        assert rep["count"] == 2

    def test_three_refusals_undaunted(self):
        """Three refusals grants 'The Undaunted' title."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        for i, faction in enumerate([
            FactionName.NEXUS,
            FactionName.STEEL_SYNDICATE,
            FactionName.CONVERGENCE,
        ]):
            manager.refuse_enhancement(
                character_id=char.id,
                name=f"Chip {i}",
                source=faction,
                benefit="Power",
                reason_refused="No",
            )

        rep = manager.get_refusal_reputation(char.id)
        assert rep["title"] == "The Undaunted"
        assert rep["count"] == 3

    def test_three_same_faction_defiant(self):
        """Three refusals from same faction grants faction-specific title."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        for i in range(3):
            manager.refuse_enhancement(
                character_id=char.id,
                name=f"Nexus Chip {i}",
                source=FactionName.NEXUS,
                benefit="Power",
                reason_refused="Never Nexus",
            )

        rep = manager.get_refusal_reputation(char.id)
        assert rep["title"] == "The Nexus Defiant"
        assert rep["by_faction"]["Nexus"] == 3

    def test_faction_breakdown(self):
        """Reputation tracks refusals by faction."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        manager.refuse_enhancement(
            character_id=char.id,
            name="Chip 1",
            source=FactionName.NEXUS,
            benefit="Power",
            reason_refused="No",
        )
        manager.refuse_enhancement(
            character_id=char.id,
            name="Chip 2",
            source=FactionName.NEXUS,
            benefit="More power",
            reason_refused="Still no",
        )
        manager.refuse_enhancement(
            character_id=char.id,
            name="Chip 3",
            source=FactionName.STEEL_SYNDICATE,
            benefit="Credit",
            reason_refused="No",
        )

        rep = manager.get_refusal_reputation(char.id)
        assert rep["by_faction"]["Nexus"] == 2
        assert rep["by_faction"]["Steel Syndicate"] == 1


class TestLogAvoidance:
    """Test non-action tracking."""

    def test_log_avoidance_basic(self):
        """Can log an avoided situation."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        avoided = manager.log_avoidance(
            situation="Marcus begged for help escaping Nexus",
            what_was_at_stake="Someone's freedom",
            potential_consequence="Marcus gets reintegrated",
            severity="moderate",
        )

        assert avoided.situation == "Marcus begged for help escaping Nexus"
        assert avoided.surfaced is False
        assert len(manager.current.avoided_situations) == 1

    def test_log_avoidance_sets_session(self):
        """Avoidance records which session it was logged."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")
        manager.current.meta.session_count = 5

        avoided = manager.log_avoidance(
            situation="Ignored the warning",
            what_was_at_stake="Safety",
            potential_consequence="Ambush",
        )

        assert avoided.created_session == 5

    def test_log_avoidance_logs_history(self):
        """Avoidance is logged to history."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        manager.log_avoidance(
            situation="Walked away from the negotiation",
            what_was_at_stake="Alliance opportunity",
            potential_consequence="They ally with your enemy",
        )

        history = manager.current.history
        assert len(history) >= 1
        assert any("avoided" in h.summary.lower() for h in history)


class TestSurfaceAvoidance:
    """Test surfacing avoidance consequences."""

    def test_surface_avoidance_basic(self):
        """Can surface an avoided situation."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        avoided = manager.log_avoidance(
            situation="Ignored the warning",
            what_was_at_stake="Safety",
            potential_consequence="Ambush",
        )

        result = manager.surface_avoidance(
            avoidance_id=avoided.id,
            what_happened="The ambush happened. You weren't ready.",
        )

        assert result is not None
        assert result.surfaced is True
        assert result.surfaced_session == manager.current.meta.session_count

    def test_surface_avoidance_logs_history(self):
        """Surfacing avoidance logs to history."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        avoided = manager.log_avoidance(
            situation="Didn't warn the village",
            what_was_at_stake="Lives",
            potential_consequence="Raid succeeds",
            severity="major",
        )

        initial_count = len(manager.current.history)

        manager.surface_avoidance(
            avoidance_id=avoided.id,
            what_happened="The raid happened. The village burned.",
        )

        assert len(manager.current.history) > initial_count
        last_entry = manager.current.history[-1]
        assert "avoidance" in last_entry.summary.lower()

    def test_cannot_surface_twice(self):
        """Cannot surface the same avoidance twice."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        avoided = manager.log_avoidance(
            situation="Test",
            what_was_at_stake="Test",
            potential_consequence="Test",
        )

        manager.surface_avoidance(avoided.id, "First surfacing")
        result = manager.surface_avoidance(avoided.id, "Second attempt")

        assert result is None


class TestPendingAvoidances:
    """Test pending avoidance retrieval."""

    def test_get_pending_avoidances(self):
        """Can retrieve pending avoidances."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        manager.log_avoidance(
            situation="First avoidance",
            what_was_at_stake="Stakes",
            potential_consequence="Consequence",
        )
        manager.log_avoidance(
            situation="Second avoidance",
            what_was_at_stake="Stakes",
            potential_consequence="Consequence",
            severity="major",
        )

        pending = manager.get_pending_avoidances()

        assert len(pending) == 2
        # Major should come first (sorted by severity)
        assert pending[0]["severity"] == "major"

    def test_surfaced_not_included(self):
        """Surfaced avoidances not included in pending."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        avoided = manager.log_avoidance(
            situation="Test",
            what_was_at_stake="Stakes",
            potential_consequence="Consequence",
        )
        manager.surface_avoidance(avoided.id, "Surfaced")

        pending = manager.get_pending_avoidances()
        assert len(pending) == 0

    def test_overdue_flag(self):
        """Old avoidances marked as overdue."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        # Log at session 1
        manager.current.meta.session_count = 1
        manager.log_avoidance(
            situation="Old avoidance",
            what_was_at_stake="Stakes",
            potential_consequence="Consequence",
        )

        # Jump to session 5
        manager.current.meta.session_count = 5

        pending = manager.get_pending_avoidances()
        assert len(pending) == 1
        assert pending[0]["overdue"] is True
        assert pending[0]["age_sessions"] == 4


class TestDeclarePush:
    """Test player Push mechanic."""

    def test_push_grants_advantage(self):
        """Push returns advantage granted."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        result = manager.declare_push(
            character_id=char.id,
            goal="to convince the guard",
            consequence="The guard will remember your face",
        )

        assert result["success"] is True
        assert result["advantage_granted"] is True
        assert result["goal"] == "to convince the guard"

    def test_push_queues_dormant_thread(self):
        """Push creates a dormant thread with the consequence."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        result = manager.declare_push(
            character_id=char.id,
            goal="to crack the encryption",
            consequence="Your intrusion will be traced",
            severity="major",
        )

        # Should have created a dormant thread
        assert len(manager.current.dormant_threads) == 1
        thread = manager.current.dormant_threads[0]
        assert thread.id == result["thread_id"]
        assert "PUSH" in thread.origin
        assert thread.consequence == "Your intrusion will be traced"
        assert thread.severity.value == "major"

    def test_push_logs_to_history(self):
        """Push is logged as a hinge moment."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        manager.declare_push(
            character_id=char.id,
            goal="to escape",
            consequence="They'll know you were here",
        )

        history = manager.current.history
        assert len(history) >= 1
        assert any("PUSHED" in h.summary for h in history)

    def test_push_includes_narrative(self):
        """Push returns narrative hint."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        char = Character(name="Test", background=Background.OPERATIVE)
        manager.add_character(char)

        result = manager.declare_push(
            character_id=char.id,
            goal="to win",
            consequence="cost",
        )

        assert "narrative_hint" in result
        assert "Advantage" in result["narrative_hint"]
