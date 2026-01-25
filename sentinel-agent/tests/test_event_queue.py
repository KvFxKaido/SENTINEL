"""Tests for MCP event queue system."""

import pytest
from src.state.schema import (
    PendingEvent,
    EventQueue,
    Background,
    Character,
)
from src.state.manager import CampaignManager
from src.state.store import MemoryCampaignStore, MemoryEventQueueStore


class TestPendingEvent:
    """Test PendingEvent model."""

    def test_event_has_id(self):
        """Events get auto-generated IDs."""
        event = PendingEvent(
            event_type="faction_event",
            campaign_id="test123",
        )
        assert event.id is not None
        assert len(event.id) == 8

    def test_event_has_timestamp(self):
        """Events get auto-generated timestamps."""
        event = PendingEvent(
            event_type="faction_event",
            campaign_id="test123",
        )
        assert event.timestamp is not None

    def test_event_defaults_to_unprocessed(self):
        """Events start as unprocessed."""
        event = PendingEvent(
            event_type="faction_event",
            campaign_id="test123",
        )
        assert event.processed is False


class TestEventQueue:
    """Test EventQueue model."""

    def test_append_event(self):
        """Can append events to queue."""
        queue = EventQueue()
        event = PendingEvent(
            event_type="faction_event",
            campaign_id="test123",
        )
        queue.append(event)
        assert len(queue.events) == 1

    def test_get_pending_all(self):
        """Get all pending events."""
        queue = EventQueue()
        for i in range(3):
            queue.append(PendingEvent(
                event_type="faction_event",
                campaign_id=f"campaign{i}",
            ))

        pending = queue.get_pending()
        assert len(pending) == 3

    def test_get_pending_by_campaign(self):
        """Filter pending events by campaign."""
        queue = EventQueue()
        queue.append(PendingEvent(event_type="test", campaign_id="camp1"))
        queue.append(PendingEvent(event_type="test", campaign_id="camp2"))
        queue.append(PendingEvent(event_type="test", campaign_id="camp1"))

        pending = queue.get_pending("camp1")
        assert len(pending) == 2

    def test_mark_processed(self):
        """Can mark events as processed."""
        queue = EventQueue()
        event = PendingEvent(event_type="test", campaign_id="test")
        queue.append(event)

        assert queue.mark_processed(event.id)
        assert event.processed is True
        assert len(queue.get_pending()) == 0

    def test_clear_processed(self):
        """Can clear processed events."""
        queue = EventQueue()
        e1 = PendingEvent(event_type="test", campaign_id="test")
        e2 = PendingEvent(event_type="test", campaign_id="test")
        queue.append(e1)
        queue.append(e2)

        queue.mark_processed(e1.id)
        removed = queue.clear_processed()

        assert removed == 1
        assert len(queue.events) == 1
        assert queue.events[0].id == e2.id


class TestMemoryEventQueueStore:
    """Test in-memory event queue store."""

    def test_append_and_retrieve(self):
        """Can append and retrieve events."""
        store = MemoryEventQueueStore()
        event = PendingEvent(
            event_type="faction_event",
            campaign_id="test123",
            payload={"faction": "nexus", "summary": "Helped them"},
        )

        event_id = store.append_event(event)
        assert event_id == event.id

        pending = store.get_pending_events("test123")
        assert len(pending) == 1
        assert pending[0].payload["faction"] == "nexus"

    def test_mark_and_clear(self):
        """Can mark processed and clear."""
        store = MemoryEventQueueStore()
        event = PendingEvent(event_type="test", campaign_id="test")
        store.append_event(event)

        store.mark_processed(event.id)
        assert len(store.get_pending_events()) == 0

        removed = store.clear_processed()
        assert removed == 1


class TestEventProcessing:
    """Test agent processing of MCP events."""

    def test_faction_event_creates_history(self):
        """Faction events create history entries."""
        store = MemoryCampaignStore()
        event_queue = MemoryEventQueueStore()
        manager = CampaignManager(store, event_queue)
        manager.create_campaign("Test")

        # Get campaign ID
        campaign_id = manager.current.meta.id

        # Persist campaign so it can be reloaded
        manager.persist_campaign()

        # Queue a faction event
        event = PendingEvent(
            event_type="faction_event",
            campaign_id=campaign_id,
            payload={
                "faction": "nexus",
                "event_type": "help",
                "summary": "Shared intelligence",
                "session": 1,
                "is_permanent": False,
            },
        )
        event_queue.append_event(event)

        # Reload campaign - should process event
        manager.current = None  # Force reload
        manager._cache.clear()
        manager.load_campaign(campaign_id)

        # Check history was updated
        history = manager.current.history
        assert len(history) == 1
        assert "Nexus" in history[0].summary
        assert "Shared intelligence" in history[0].summary

    def test_processed_events_are_cleared(self):
        """Processed events are removed from queue."""
        store = MemoryCampaignStore()
        event_queue = MemoryEventQueueStore()
        manager = CampaignManager(store, event_queue)
        manager.create_campaign("Test")
        campaign_id = manager.current.meta.id

        # Persist campaign so it can be reloaded
        manager.persist_campaign()

        # Queue an event
        event = PendingEvent(
            event_type="faction_event",
            campaign_id=campaign_id,
            payload={"faction": "ember_colonies", "summary": "Test"},
        )
        event_queue.append_event(event)

        # Reload - processes event
        manager.current = None
        manager._cache.clear()
        manager.load_campaign(campaign_id)

        # Queue should be empty
        assert len(event_queue.get_pending_events()) == 0

    def test_events_filtered_by_campaign(self):
        """Only events for current campaign are processed."""
        store = MemoryCampaignStore()
        event_queue = MemoryEventQueueStore()
        manager = CampaignManager(store, event_queue)

        # Create two campaigns and persist them
        manager.create_campaign("Campaign 1")
        camp1_id = manager.current.meta.id
        manager.persist_campaign()

        manager.create_campaign("Campaign 2")
        camp2_id = manager.current.meta.id
        manager.persist_campaign()

        # Queue events for both
        event_queue.append_event(PendingEvent(
            event_type="faction_event",
            campaign_id=camp1_id,
            payload={"faction": "nexus", "summary": "For camp 1"},
        ))
        event_queue.append_event(PendingEvent(
            event_type="faction_event",
            campaign_id=camp2_id,
            payload={"faction": "lattice", "summary": "For camp 2"},
        ))

        # Load campaign 1
        manager.current = None
        manager._cache.clear()
        manager.load_campaign(camp1_id)

        # Only camp1 event processed
        camp1_history = manager.current.history
        assert len(camp1_history) == 1
        assert "Nexus" in camp1_history[0].summary

        # Camp2 event still pending
        pending = event_queue.get_pending_events(camp2_id)
        assert len(pending) == 1

    def test_no_event_queue_no_crash(self):
        """Manager works without event queue."""
        store = MemoryCampaignStore()
        manager = CampaignManager(store, event_queue=None)
        manager.create_campaign("Test")
        manager.persist_campaign()  # Persist so it can be reloaded

        # Should not crash
        campaign_id = manager.current.meta.id
        manager.current = None
        manager._cache.clear()
        loaded = manager.load_campaign(campaign_id)

        assert loaded is not None
