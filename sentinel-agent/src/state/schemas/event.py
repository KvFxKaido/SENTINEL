"""TurnEvent schema — individual events produced during turn resolution."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class TurnEvent(BaseModel):
    """A single event produced during turn resolution."""
    event_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    event_type: str
    source_action: str | None = None
    payload: dict = Field(default_factory=dict)
    cascaded_from: str | None = None
    cascade_depth: int = 0
    summary: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def is_cascaded(self) -> bool:
        return self.cascaded_from is not None

    @property
    def is_direct(self) -> bool:
        return self.cascaded_from is None
