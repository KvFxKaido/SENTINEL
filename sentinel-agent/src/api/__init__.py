"""
SENTINEL 2D API Server.

FastAPI-based REST/WebSocket API for the 2D conversion.
Replaces CLI-driven game loop with request-response architecture.

Phase 1 of 2D Conversion Plan:
- Python becomes stateful REST/WebSocket service
- Frontend drives real-time exploration
- Python responds only to commits
"""

from .server import create_app, SentinelAPI
from .schemas import (
    GameStateResponse,
    ActionRequest,
    ActionResponse,
    DialogueRequest,
    DialogueResponse,
    CampaignInfo,
    CharacterState,
    FactionState,
    NPCState,
    MapState,
    RegionState,
)

__all__ = [
    "create_app",
    "SentinelAPI",
    "GameStateResponse",
    "ActionRequest",
    "ActionResponse",
    "DialogueRequest",
    "DialogueResponse",
    "CampaignInfo",
    "CharacterState",
    "FactionState",
    "NPCState",
    "MapState",
    "RegionState",
]
