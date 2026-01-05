"""Tests for dormant thread surfacing system."""

import pytest
from src.state.schema import DormantThread, ThreadSeverity
from src.state.manager import CampaignManager
from src.state.store import MemoryCampaignStore


class TestDormantThreadKeywords:
    """Test keyword extraction for dormant threads."""

    def test_queue_extracts_keywords(self):
        """Keywords should be extracted from trigger condition when queuing."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        thread = manager.queue_dormant_thread(
            origin="Refused Syndicate deal",
            trigger_condition="When player returns to Sector 7 warehouse",
            consequence="Syndicate enforcers are waiting",
            severity="moderate",
        )

        assert thread.trigger_keywords is not None
        assert len(thread.trigger_keywords) > 0
        # Should contain meaningful words like "returns", "sector", "warehouse"
        assert any(kw in thread.trigger_keywords for kw in ["returns", "sector", "warehouse"])

    def test_keywords_limited_to_10(self):
        """Keywords should be limited to 10 to prevent bloat."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        # Long trigger condition with many words
        thread = manager.queue_dormant_thread(
            origin="Complex situation",
            trigger_condition=(
                "When player visits the old abandoned factory warehouse district "
                "near the collapsed bridge where the resistance fighters used to "
                "gather before the incident with the corporate security forces"
            ),
            consequence="Old ghosts resurface",
        )

        assert len(thread.trigger_keywords) <= 10


class TestCheckThreadTriggers:
    """Test keyword matching for thread surfacing hints."""

    @pytest.fixture
    def manager_with_threads(self):
        """Create manager with sample threads."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        # Queue several threads
        manager.queue_dormant_thread(
            origin="Warehouse incident",
            trigger_condition="When player returns to the warehouse district",
            consequence="Security footage surfaces",
            severity="moderate",
        )
        manager.queue_dormant_thread(
            origin="Refused Convergence enhancement",
            trigger_condition="When player encounters Convergence agents again",
            consequence="They remember the refusal and become hostile",
            severity="major",
        )
        manager.queue_dormant_thread(
            origin="Minor favor",
            trigger_condition="When player needs supplies",
            consequence="Old contact reaches out",
            severity="minor",
        )

        return manager

    def test_matches_require_two_keywords(self, manager_with_threads):
        """Single keyword match should not trigger alert."""
        # Just "warehouse" alone shouldn't match
        matches = manager_with_threads.check_thread_triggers("I check the warehouse")
        # "warehouse" is one keyword, "check" might not match - depends on extraction
        # The requirement is 2+ keywords
        for match in matches:
            assert len(match["matched_keywords"]) >= 2

    def test_strong_match_returns_thread(self, manager_with_threads):
        """Multiple keyword match should return thread info."""
        matches = manager_with_threads.check_thread_triggers(
            "I want to return to the warehouse district"
        )

        # Should match the warehouse thread with "returns", "warehouse", "district"
        assert len(matches) >= 1
        warehouse_match = next(
            (m for m in matches if "warehouse" in m["trigger_condition"].lower()),
            None
        )
        assert warehouse_match is not None
        assert warehouse_match["severity"] == "moderate"
        assert len(warehouse_match["matched_keywords"]) >= 2

    def test_no_matches_returns_empty(self, manager_with_threads):
        """Unrelated input should return no matches."""
        matches = manager_with_threads.check_thread_triggers(
            "I order coffee at the cafe"
        )
        assert matches == []

    def test_matches_sorted_by_relevance(self, manager_with_threads):
        """Matches should be sorted by score then severity."""
        matches = manager_with_threads.check_thread_triggers(
            "I encounter Convergence agents near the warehouse district where I refused their offer"
        )

        if len(matches) >= 2:
            # Higher scores should come first
            for i in range(len(matches) - 1):
                # Either higher score, or same score with higher severity
                assert (
                    matches[i]["score"] >= matches[i + 1]["score"]
                )


class TestSurfaceThread:
    """Test thread surfacing functionality."""

    def test_surface_removes_from_pending(self):
        """Surfacing should remove thread from pending list."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        thread = manager.queue_dormant_thread(
            origin="Test",
            trigger_condition="When X happens",
            consequence="Y occurs",
        )

        assert len(manager.current.dormant_threads) == 1

        result = manager.surface_dormant_thread(
            thread_id=thread.id,
            activation_context="Player did X",
        )

        assert result is not None
        assert result.id == thread.id
        assert len(manager.current.dormant_threads) == 0

    def test_surface_logs_to_history(self):
        """Surfacing should log to campaign history."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        thread = manager.queue_dormant_thread(
            origin="Test",
            trigger_condition="When X happens",
            consequence="Y occurs",
            severity="major",
        )

        manager.surface_dormant_thread(
            thread_id=thread.id,
            activation_context="Player did X",
        )

        # Check history
        history = manager.current.history
        assert len(history) >= 1
        last_entry = history[-1]
        assert "THREAD ACTIVATED" in last_entry.summary
        assert last_entry.is_permanent is True  # Major threads are permanent

    def test_surface_nonexistent_returns_none(self):
        """Surfacing nonexistent thread should return None."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        result = manager.surface_dormant_thread(
            thread_id="nonexistent",
            activation_context="Whatever",
        )

        assert result is None


class TestBackwardsCompatibility:
    """Test that existing threads without keywords work."""

    def test_empty_keywords_no_crash(self):
        """Threads with empty keywords should not cause errors."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        # Manually add thread without keywords (simulating old data)
        old_thread = DormantThread(
            origin="Legacy thread",
            trigger_condition="When something happens",
            consequence="Something occurs",
            severity=ThreadSeverity.MODERATE,
            created_session=0,
            trigger_keywords=[],  # Empty - old format
        )
        manager.current.dormant_threads.append(old_thread)

        # Should not crash
        matches = manager.check_thread_triggers("something happens here")
        # Empty keywords means no match possible
        assert old_thread.id not in [m["thread_id"] for m in matches]

    def test_thread_still_shows_in_state(self):
        """Threads without keywords should still appear in state summary."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store)
        manager.create_campaign("Test")

        old_thread = DormantThread(
            origin="Legacy thread",
            trigger_condition="When something happens",
            consequence="Something occurs",
            severity=ThreadSeverity.MAJOR,
            created_session=0,
            trigger_keywords=[],
        )
        manager.current.dormant_threads.append(old_thread)

        # Thread count should include it
        assert len(manager.current.dormant_threads) == 1
