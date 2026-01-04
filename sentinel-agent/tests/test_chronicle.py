"""
Tests for chronicle/history logging system.

The chronicle tracks significant campaign events including
hinge moments, faction shifts, and mission completions.
"""

import pytest
from src.state.schema import (
    HistoryType,
    HistoryEntry,
    SessionReflection,
)


class TestHistoryLogging:
    """Test basic history logging operations."""

    def test_log_history_creates_entry(self, manager, campaign):
        """log_history adds entry to campaign history."""
        entry = manager.log_history(
            type=HistoryType.CANON,
            summary="The faction war began",
            is_permanent=True,
        )

        assert entry.type == HistoryType.CANON
        assert entry.summary == "The faction war began"
        assert entry.is_permanent is True
        assert len(manager.current.history) == 1

    def test_history_entries_have_session_number(self, manager, campaign):
        """History entries record the session they occurred in."""
        manager.current.meta.session_count = 3

        entry = manager.log_history(
            type=HistoryType.CONSEQUENCE,
            summary="Past decision caught up",
        )

        assert entry.session == 3

    def test_multiple_entries_accumulate(self, manager, campaign):
        """Multiple history entries are preserved."""
        manager.log_history(HistoryType.MISSION, "First mission")
        manager.log_history(HistoryType.FACTION_SHIFT, "Faction changed")
        manager.log_history(HistoryType.HINGE, "Major decision")

        assert len(manager.current.history) == 3


class TestHingeMomentLogging:
    """Test hinge moment (irreversible choice) logging."""

    def test_log_hinge_moment_creates_entry(self, manager, campaign):
        """log_hinge_moment creates a permanent history entry."""
        entry = manager.log_hinge_moment(
            situation="Guard discovered the infiltration",
            choice="I killed the guard",
            reasoning="No witnesses, survival priority",
        )

        assert entry.type == HistoryType.HINGE
        assert entry.is_permanent is True
        assert "HINGE" in entry.summary

    def test_hinge_moment_includes_metadata(self, manager, campaign):
        """Hinge moments store situation, choice, and reasoning."""
        entry = manager.log_hinge_moment(
            situation="Ember contact offered escape route",
            choice="I betrayed their location to Nexus",
            reasoning="Nexus had leverage on me",
        )

        # The hinge details should be stored as HingeMoment model
        assert entry.hinge is not None
        assert entry.hinge.situation == "Ember contact offered escape route"
        assert entry.hinge.choice == "I betrayed their location to Nexus"
        assert entry.hinge.reasoning == "Nexus had leverage on me"


class TestSessionEndLogging:
    """Test session end and reflection logging."""

    def test_end_session_logs_mission(self, manager, campaign):
        """end_session creates a mission history entry."""
        manager.current.meta.session_count = 2

        entry = manager.end_session(summary="Escaped the facility")

        assert entry is not None
        assert entry.type == HistoryType.MISSION
        assert "Session 2" in entry.summary

    def test_end_session_with_reflections(self, manager, campaign):
        """end_session can include player reflections."""
        reflections = SessionReflection(
            cost="I lost my ally's trust",
            learned="Sometimes survival requires sacrifice",
            would_refuse="I wouldn't betray a friend again",
        )

        # Provide mission_title to ensure MissionOutcome is created
        entry = manager.end_session(
            summary="Mission complete",
            reflections=reflections,
            mission_title="The Extraction",
        )

        assert entry.mission is not None
        assert entry.mission.reflections is not None
        assert entry.mission.reflections.cost == "I lost my ally's trust"

    def test_end_session_resets_social_energy(self, manager, campaign_with_character):
        """end_session resets social energy by default."""
        # Drain some energy
        char = manager.current.characters[0]
        char.social_energy.current = 25

        manager.end_session(summary="Session done")

        assert char.social_energy.current == 100

    def test_end_session_can_skip_reset(self, manager, campaign_with_character):
        """end_session can skip social energy reset."""
        char = manager.current.characters[0]
        char.social_energy.current = 25

        manager.end_session(
            summary="Session done",
            reset_social_energy=False,
        )

        assert char.social_energy.current == 25


class TestHistoryFiltering:
    """Test filtering history by type."""

    def test_can_filter_by_type(self, manager, campaign):
        """History can be filtered by entry type."""
        manager.log_history(HistoryType.MISSION, "Mission 1")
        manager.log_history(HistoryType.HINGE, "Hinge 1")
        manager.log_history(HistoryType.MISSION, "Mission 2")
        manager.log_history(HistoryType.FACTION_SHIFT, "Faction change")

        history = manager.current.history
        missions = [e for e in history if e.type == HistoryType.MISSION]
        hinges = [e for e in history if e.type == HistoryType.HINGE]

        assert len(missions) == 2
        assert len(hinges) == 1

    def test_can_filter_permanent_entries(self, manager, campaign):
        """Can filter to only permanent (canon) entries."""
        manager.log_history(HistoryType.MISSION, "Regular mission", is_permanent=False)
        manager.log_hinge_moment("Situation", "Choice", "Reasoning")  # Permanent
        manager.log_history(HistoryType.CANON, "World event", is_permanent=True)

        history = manager.current.history
        permanent = [e for e in history if e.is_permanent]

        assert len(permanent) == 2
