"""
Event bus for SENTINEL state changes.

Provides decoupled communication between state management and UI.
Components subscribe to events and react without tight coupling.

Usage:
    from .event_bus import get_event_bus, EventType

    # Subscribe (typically in TUI on_mount)
    bus = get_event_bus()
    bus.on(EventType.FACTION_CHANGED, my_handler)

    # Emit (in manager when state changes)
    bus.emit(EventType.FACTION_CHANGED, faction="nexus", before="neutral", after="friendly")

    # Handler receives event
    def my_handler(event: GameEvent):
        print(f"Faction {event.data['faction']} changed!")
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Any


class EventType(Enum):
    """Game events that can be published."""

    # Faction events
    FACTION_CHANGED = "faction.changed"

    # NPC events
    NPC_ADDED = "npc.added"
    NPC_DISPOSITION_CHANGED = "npc.disposition_changed"
    NPC_MEMORY_ADDED = "npc.memory_added"

    # Thread events
    THREAD_QUEUED = "thread.queued"
    THREAD_SURFACED = "thread.surfaced"

    # Character events
    SOCIAL_ENERGY_CHANGED = "energy.changed"
    SOCIAL_ENERGY_DEPLETED = "energy.depleted"
    HINGE_MOMENT = "hinge.moment"
    LOCATION_CHANGED = "location.changed"

    # Enhancement events
    ENHANCEMENT_GRANTED = "enhancement.granted"
    ENHANCEMENT_CALLED = "enhancement.called"

    # Session events
    SESSION_STARTED = "session.started"
    SESSION_ENDED = "session.ended"
    CAMPAIGN_LOADED = "campaign.loaded"
    CAMPAIGN_SAVED = "campaign.saved"


@dataclass
class GameEvent:
    """
    Event payload for the event bus.

    Attributes:
        type: The event type (from EventType enum)
        data: Event-specific payload as dict
        campaign_id: ID of the campaign this event belongs to
        session: Session number when the event occurred
        timestamp: When the event was emitted
    """

    type: EventType
    data: dict = field(default_factory=dict)
    campaign_id: str = ""
    session: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"[{self.type.value}] {self.data}"


# Type alias for event handlers
EventHandler = Callable[[GameEvent], None]


class EventBus:
    """
    Synchronous event bus for SENTINEL.

    Listeners are called immediately on emit().
    For async work, listeners should use asyncio.create_task().

    Design decisions:
    - Synchronous: Matches SENTINEL's @work(thread=True) pattern
    - Type-safe: Uses EventType enum instead of strings
    - Simple: No priority, no async, no middleware
    """

    def __init__(self):
        self._listeners: dict[EventType, list[EventHandler]] = {}
        self._history: list[GameEvent] = []
        self._history_limit = 100  # Keep last N events for debugging

    def on(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: The type of event to listen for
            handler: Callback function that receives GameEvent
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        if handler not in self._listeners[event_type]:
            self._listeners[event_type].append(handler)

    def off(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Unsubscribe from an event type.

        Args:
            event_type: The event type to unsubscribe from
            handler: The handler to remove
        """
        if event_type in self._listeners and handler in self._listeners[event_type]:
            self._listeners[event_type].remove(handler)

    def emit(
        self,
        event_type: EventType,
        campaign_id: str = "",
        session: int = 0,
        **data,
    ) -> GameEvent:
        """
        Emit an event to all subscribers.

        Args:
            event_type: The type of event
            campaign_id: Campaign context (optional)
            session: Session number (optional)
            **data: Event-specific data

        Returns:
            The emitted GameEvent (for chaining/testing)
        """
        event = GameEvent(
            type=event_type,
            data=data,
            campaign_id=campaign_id,
            session=session,
        )

        # Store in history for debugging
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit :]

        # Notify all listeners
        if event_type in self._listeners:
            for handler in self._listeners[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    # Log but don't crash - one bad listener shouldn't break others
                    print(f"[EventBus] Error in handler for {event_type.value}: {e}")

        return event

    def clear(self) -> None:
        """Clear all listeners. Useful for testing."""
        self._listeners.clear()

    def get_history(self, event_type: EventType | None = None) -> list[GameEvent]:
        """
        Get recent event history.

        Args:
            event_type: Filter by type, or None for all events

        Returns:
            List of recent events
        """
        if event_type is None:
            return list(self._history)
        return [e for e in self._history if e.type == event_type]

    def listener_count(self, event_type: EventType) -> int:
        """Get number of listeners for an event type."""
        return len(self._listeners.get(event_type, []))


# Global singleton instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """
    Get the global event bus instance.

    Returns the same instance across all calls (singleton pattern).
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus() -> None:
    """Reset the global event bus. Useful for testing."""
    global _event_bus
    _event_bus = None
