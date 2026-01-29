"""
TurnEvent schema — individual events produced during turn resolution.

Events are the atoms of the turn system. A single Action produces
one or more Events, and cascade processing may produce more.

Events serve two audiences:
1. Audit log: Full provenance chain for debugging and replay
2. Player feed: Grouped notices for readable UX

The cascaded_from field links derived events to their source,
forming an event tree that can be visualized for debugging.
"""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class TurnEvent(BaseModel):
    """
    A single event produced during turn resolution.

    Events are immutable records of what happened. They never
    mutate state directly — the resolver applies state changes
    and emits events as a record.

    The cascade processor reads events to determine derived effects,
    producing new events with cascaded_from set to the source event_id.
    """
    event_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    event_type: str  # e.g., "travel.arrived", "standing.changed", "thread.surfaced"
    source_action: str | None = None  # action_id that triggered this
    payload: dict = Field(default_factory=dict)
    # Payload varies by event_type:
    # travel.arrived: {"from": "rust_corridor", "to": "appalachian_hollows"}
    # standing.changed: {"faction": "Ember Colonies", "delta": -1, "new_standing": "Neutral"}
    # thread.surfaced: {"thread_id": "abc123", "trigger": "returned to sector 7"}
    # npc.reacted: {"npc_id": "xyz", "reaction": "became wary", "reason": "faction shift"}

    # Cascade provenance — None for direct effects, event_id for cascaded
    cascaded_from: str | None = None
    cascade_depth: int = 0  # 0 = direct, 1+ = cascaded

    # Human-readable summary for player feed
    summary: str = ""  # "Arrived in Appalachian Hollows"

    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def is_cascaded(self) -> bool:
        """Whether this event was produced by cascade processing."""
        return self.cascaded_from is not None

    @property
    def is_direct(self) -> bool:
        """Whether this event was produced directly by the action."""
        return self.cascaded_from is None
