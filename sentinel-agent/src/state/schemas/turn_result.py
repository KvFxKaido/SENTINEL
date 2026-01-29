"""
TurnResult schema — the output of a resolved turn.

This is the fourth and final artifact of the Commitment Gate pipeline.
After Action is committed and resolved, the engine returns a TurnResult
containing everything that happened.

Design invariants:
- state_snapshot is authoritative — UI renders ONLY from this (4f)
- seed is persisted for replay and debugging (4b)
- events list contains all effects including cascades
- narrative_hooks are optional — the game works without them
"""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .event import TurnEvent


class TurnResult(BaseModel):
    """
    Complete result of a resolved turn.

    The engine produces this after processing an Action through:
    1. Resolution (deterministic state mutation)
    2. Cascade processing (faction propagation, thread triggers, NPC reactions)
    3. State persistence (saved before narrative — invariant 4a)

    The UI receives this and renders the new state.
    The LLM optionally receives this to generate narrative flavor.
    """
    action_id: str  # Matches the committed Action
    success: bool  # Did the action succeed?
    state_version: int  # New state_version after resolution

    # What happened
    events: list[TurnEvent] = Field(default_factory=list)
    # Authoritative state snapshot — UI renders ONLY from this
    state_snapshot: dict = Field(default_factory=dict)

    # For deterministic replay (invariant 4b)
    seed: int = Field(default_factory=lambda: int(uuid4().int % (2**31)))

    # Optional hooks for LLM narrative generation
    narrative_hooks: list[str] = Field(default_factory=list)
    # e.g., ["Player traveled through hostile territory",
    #        "Ember Colonies noticed the passage",
    #        "A dormant thread stirred"]

    # Cascade summary for player feed (not full audit log)
    cascade_notices: list[dict] = Field(default_factory=list)
    # e.g., [{"headline": "Ripple Effect", "details": ["Ember standing shifted"], "severity": "info"}]

    # Timing metadata
    resolved_at: datetime = Field(default_factory=datetime.now)
    turn_number: int = 0  # Which turn this was

    @property
    def has_cascades(self) -> bool:
        """Whether this turn triggered any cascade effects."""
        return any(e.cascaded_from is not None for e in self.events)

    @property
    def event_summary(self) -> list[str]:
        """Human-readable summary of events for quick display."""
        return [f"[{e.event_type}] {e.summary}" for e in self.events if e.summary]
