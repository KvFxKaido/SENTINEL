from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, Field
from .base import (
    FactionName, 
    Urgency, 
    MissionType, 
    MissionPhase, 
    Standing, 
    HistoryType, 
    CampaignStatus,
    Location,
    Region,
    generate_id
)
from .character import Character, HingeMoment
from .npc import NPC
from .world import (
    FactionRegistry, 
    NPCRegistry, 
    DormantThread,
    AvoidedSituation,
    MapState,
    FavorTracker,
    ThreadSeverity
)

class MissionBriefing(BaseModel):
    situation: str
    requestor: str
    competing_truths: list[str] = Field(default_factory=list)
    stakes: str

class MissionOffer(BaseModel):
    id: str = Field(default_factory=generate_id)
    title: str
    situation: str
    requestor: str
    requestor_npc_id: str | None = None
    faction: FactionName | None = None
    urgency: Urgency = Urgency.PRESSING
    offered_session: int
    deadline_session: int | None = None
    stakes: str
    consequence_if_ignored: str
    accepted: bool = False
    declined: bool = False
    expired: bool = False
    consequence_triggered: bool = False

class SessionState(BaseModel):
    mission_id: str = Field(default_factory=generate_id)
    mission_title: str
    mission_type: MissionType
    phase: MissionPhase = MissionPhase.BRIEFING
    briefing: MissionBriefing
    active_npc_ids: list[str] = Field(default_factory=list)
    loadout: list[str] = Field(default_factory=list)
    conversation_log: list[dict] = Field(default_factory=list)

class SessionReflection(BaseModel):
    cost: str = ""
    learned: str = ""
    would_refuse: str = ""

class MissionOutcome(BaseModel):
    title: str
    what_we_tried: str
    result: str
    immediate_consequence: str
    reflections: SessionReflection | None = None

class FactionShiftRecord(BaseModel):
    faction: FactionName
    from_standing: Standing
    to_standing: Standing
    cause: str

class HistoryEntry(BaseModel):
    id: str = Field(default_factory=generate_id)
    session: int
    type: HistoryType
    summary: str
    timestamp: datetime = Field(default_factory=datetime.now)
    mission: MissionOutcome | None = None
    hinge: HingeMoment | None = None
    faction_shift: FactionShiftRecord | None = None
    is_permanent: bool = False
    event_id: str | None = None

class EndgameReadiness(BaseModel):
    hinge_score: float = 0.0
    arc_score: float = 0.0
    faction_score: float = 0.0
    thread_score: float = 0.0
    player_goals: list[str] = Field(default_factory=list)
    goals_met: list[str] = Field(default_factory=list)

class CampaignMeta(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    phase: Literal[1, 2, 3] = 1
    session_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: CampaignStatus = CampaignStatus.ACTIVE
    endgame_readiness: EndgameReadiness = Field(default_factory=EndgameReadiness)
    epilogue_session: int | None = None

class JobStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"

class JobTemplate(BaseModel):
    id: str
    faction: FactionName
    title: str
    type: MissionType
    description: str
    objectives: list[str] = Field(default_factory=list)
    reward_credits: int = 0
    reward_standing: int = 1
    opposing_factions: list[FactionName] = Field(default_factory=list)
    opposing_penalty: int = 1
    time_estimate: str = "1 session"
    tags: list[str] = Field(default_factory=list)
    min_standing: int = -50
    region: Region | None = None
    requires_vehicle: bool = False
    requires_vehicle_type: str | None = None
    requires_vehicle_tags: list[str] = Field(default_factory=list)
    buy_in: int | None = None

class ActiveJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    template_id: str
    title: str
    faction: FactionName
    briefing: str = ""
    objectives: list[str] = Field(default_factory=list)
    reward_credits: int = 0
    reward_standing: int = 1
    opposing_factions: list[FactionName] = Field(default_factory=list)
    opposing_penalty: int = 1
    accepted_session: int = 0
    due_session: int | None = None
    status: JobStatus = JobStatus.ACTIVE
    region: Region | None = None
    buy_in: int | None = None

class JobBoard(BaseModel):
    available: list[str] = Field(default_factory=list)
    active: list[ActiveJob] = Field(default_factory=list)
    completed: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    last_refresh_session: int = 0

class CampaignSnapshot(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    session: int
    factions: dict[FactionName, Standing] = Field(default_factory=dict)
    npc_states: dict[str, dict] = Field(default_factory=dict)
    threads: dict[str, ThreadSeverity] = Field(default_factory=dict)

class Campaign(BaseModel):
    schema_version: str = "1.7.0"
    saved_at: datetime = Field(default_factory=datetime.now)
    persisted_: bool = Field(default=False, exclude=True, alias="_persisted")
    meta: CampaignMeta
    characters: list[Character] = Field(default_factory=list)
    factions: FactionRegistry = Field(default_factory=FactionRegistry)
    npcs: NPCRegistry = Field(default_factory=NPCRegistry)
    history: list[HistoryEntry] = Field(default_factory=list)
    dormant_threads: list[DormantThread] = Field(default_factory=list)
    avoided_situations: list[AvoidedSituation] = Field(default_factory=list)
    session: SessionState | None = None
    location: Location = Location.SAFE_HOUSE
    location_faction: FactionName | None = None
    region: Region = Region.RUST_CORRIDOR
    map_state: MapState = Field(default_factory=MapState)
    jobs: JobBoard = Field(default_factory=JobBoard)
    favor_tracker: FavorTracker = Field(default_factory=FavorTracker)
    mission_offers: list[MissionOffer] = Field(default_factory=list)
    turn_count: int = 0
    state_version: int = 0
    last_session_snapshot: CampaignSnapshot | None = None

    def save_checkpoint(self) -> None:
        self.saved_at = datetime.now()
        self.meta.updated_at = datetime.now()

class PendingEvent(BaseModel):
    """An event from an external source (MCP) waiting to be processed."""
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    timestamp: datetime = Field(default_factory=datetime.now)
    source: Literal["mcp", "external"] = "mcp"
    event_type: str
    campaign_id: str
    payload: dict = Field(default_factory=dict)
    processed: bool = False

class EventQueue(BaseModel):
    """Queue of pending events from external sources."""
    events: list[PendingEvent] = Field(default_factory=list)
    last_processed: datetime | None = None

    def append(self, event: PendingEvent) -> None:
        self.events.append(event)

    def get_pending(self, campaign_id: str | None = None) -> list[PendingEvent]:
        pending = [e for e in self.events if not e.processed]
        if campaign_id:
            pending = [e for e in pending if e.campaign_id == campaign_id]
        return pending

    def mark_processed(self, event_id: str) -> bool:
        for event in self.events:
            if event.id == event_id:
                event.processed = True
                return True
        return False

    def clear_processed(self) -> int:
        original = len(self.events)
        self.events = [e for e in self.events if not e.processed]
        return original - len(self.events)
