"""State management for SENTINEL campaigns."""

from .schema import (
    Campaign,
    Character,
    NPC,
    Enhancement,
    RefusedEnhancement,
    EstablishingIncident,
    SocialEnergy,
    DormantThread,
    HistoryEntry,
    SessionState,
    FactionStanding,
    HingeMoment,
    Background,
    FactionName,
    MissionType,
    MissionPhase,
    Location,
)
from .manager import CampaignManager
from .store import CampaignStore, JsonCampaignStore, MemoryCampaignStore
from .memvid_adapter import (
    MemvidAdapter,
    create_memvid_adapter,
    FrameType,
    MEMVID_AVAILABLE,
)
from .event_bus import (
    EventBus,
    EventType,
    GameEvent,
    get_event_bus,
    reset_event_bus,
)

__all__ = [
    # Schema
    "Campaign",
    "Character",
    "NPC",
    "Enhancement",
    "RefusedEnhancement",
    "EstablishingIncident",
    "SocialEnergy",
    "DormantThread",
    "HistoryEntry",
    "SessionState",
    "FactionStanding",
    "HingeMoment",
    "Background",
    "FactionName",
    "MissionType",
    "MissionPhase",
    "Location",
    # Manager
    "CampaignManager",
    # Store
    "CampaignStore",
    "JsonCampaignStore",
    "MemoryCampaignStore",
    # Memvid
    "MemvidAdapter",
    "create_memvid_adapter",
    "FrameType",
    "MEMVID_AVAILABLE",
    # Event Bus
    "EventBus",
    "EventType",
    "GameEvent",
    "get_event_bus",
    "reset_event_bus",
]
