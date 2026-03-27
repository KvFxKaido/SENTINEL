"""TurnResult schema — the output of a resolved turn."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .event import TurnEvent


class TurnResult(BaseModel):
    action_id: str
    success: bool
    state_version: int
    events: list[TurnEvent] = Field(default_factory=list)
    state_snapshot: dict = Field(default_factory=dict)
    seed: int = Field(default_factory=lambda: int(uuid4().int % (2**31)))
    narrative_hooks: list[str] = Field(default_factory=list)
    cascade_notices: list[dict] = Field(default_factory=list)
    resolved_at: datetime = Field(default_factory=datetime.now)
    turn_number: int = 0

    @property
    def has_cascades(self) -> bool:
        return any(e.cascaded_from is not None for e in self.events)

    @property
    def event_summary(self) -> list[str]:
        return [f"[{e.event_type}] {e.summary}" for e in self.events if e.summary]
