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
)
from .manager import CampaignManager
from .store import CampaignStore, JsonCampaignStore, MemoryCampaignStore
from .memvid_adapter import (
    MemvidAdapter,
    create_memvid_adapter,
    FrameType,
    MEMVID_AVAILABLE,
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
]
