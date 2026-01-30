"""
Pydantic schemas for SENTINEL 2D API.

These models define the contract between frontend and backend.
Designed for the 2D exploration-first architecture where:
- Frontend has direct read access to permitted state
- Backend remains source of truth
- Frontend may optimistically render but must reconcile
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Enums (mirroring state schema for API consumers)
# -----------------------------------------------------------------------------

class LocationType(str, Enum):
    """Player location types."""
    SAFE_HOUSE = "safe_house"
    FIELD = "field"
    FACTION_HQ = "faction_hq"
    MARKET = "market"
    TRANSIT = "transit"


class ConnectivityLevel(str, Enum):
    """Region connectivity levels."""
    DISCONNECTED = "disconnected"
    AWARE = "aware"
    CONNECTED = "connected"
    EMBEDDED = "embedded"


class AlertState(str, Enum):
    """NPC alert states for patrol AI."""
    PATROLLING = "patrolling"
    INVESTIGATING = "investigating"
    COMBAT = "combat"


class ActionType(str, Enum):
    """Types of committable actions."""
    MOVE = "move"
    INTERACT = "interact"
    DIALOGUE = "dialogue"
    COMBAT = "combat"
    TRAVEL = "travel"
    USE_ITEM = "use_item"
    WAIT = "wait"


# -----------------------------------------------------------------------------
# Nested State Models
# -----------------------------------------------------------------------------

class Position(BaseModel):
    """2D position in local map coordinates."""
    x: float
    y: float
    facing: str | None = None  # Direction character is facing


class CampaignInfo(BaseModel):
    """Basic campaign metadata."""
    id: str
    name: str
    session: int
    phase: str | None = None


class SocialEnergyState(BaseModel):
    """Social energy (Pistachios) state."""
    current: int
    max: int
    percentage: float = Field(ge=0, le=100)


class GearItem(BaseModel):
    """Equipment item."""
    id: str
    name: str
    category: str
    description: str = ""
    used: bool = False
    single_use: bool = False


class Enhancement(BaseModel):
    """Character enhancement."""
    id: str
    name: str
    source: str
    benefit: str


class Vehicle(BaseModel):
    """Vehicle state."""
    id: str
    name: str
    type: str
    fuel: int = Field(ge=0, le=100)
    condition: int = Field(ge=0, le=100)
    status: str
    terrain: list[str] = []
    capacity: int = 1
    cargo: bool = False
    stealth: bool = False


class CharacterState(BaseModel):
    """Player character state for frontend rendering."""
    id: str
    name: str
    background: str | None = None
    position: Position | None = None
    social_energy: SocialEnergyState
    credits: int = 0
    gear: list[GearItem] = []
    loadout: list[str] = []
    enhancements: list[Enhancement] = []
    vehicles: list[Vehicle] = []
    injuries: list[str] = []


class FactionState(BaseModel):
    """Faction standing state."""
    id: str
    name: str
    standing: str
    reputation: int = 0


class NPCState(BaseModel):
    """NPC state for frontend rendering."""
    id: str
    name: str
    faction: str | None = None
    disposition: str
    position: Position | None = None
    alert_state: AlertState = AlertState.PATROLLING
    visible: bool = True
    interactable: bool = True
    last_interaction: str | None = None


class DormantThread(BaseModel):
    """Dormant consequence thread."""
    id: str
    origin: str
    trigger: str
    consequence: str
    severity: str
    created_session: int


class LocalMapState(BaseModel):
    """State of the current local map (room/area)."""
    id: str
    name: str
    region_id: str
    tiles: list[list[int]] | None = None  # Tile grid if needed
    walls: list[dict] = []  # Wall collision data
    exits: list[dict] = []  # Exit points to other maps
    npcs: list[str] = []  # NPC IDs present
    objects: list[dict] = []  # Interactable objects
    patrol_routes: list[dict] = []  # Patrol path data


class RegionState(BaseModel):
    """Region state for overworld map."""
    id: str
    name: str
    connectivity: ConnectivityLevel
    primary_faction: str | None = None
    contested_by: list[str] = []
    markers: list[dict] = []
    position: dict | None = None  # {x, y} for map rendering


class MapState(BaseModel):
    """Complete map state for frontend."""
    current_region: str
    current_local_map: LocalMapState | None = None
    regions: dict[str, RegionState] = {}
    player_position: Position | None = None


# -----------------------------------------------------------------------------
# API Response Models
# -----------------------------------------------------------------------------

class GameStateResponse(BaseModel):
    """
    Full game state snapshot.
    
    GET /state returns this for initial load and reconciliation.
    Frontend caches this and updates via WebSocket stream.
    """
    ok: bool = True
    version: int = Field(description="State version for optimistic updates")
    timestamp: datetime
    
    # Campaign context
    campaign: CampaignInfo | None = None
    
    # Player state
    character: CharacterState | None = None
    location: LocationType = LocationType.SAFE_HOUSE
    
    # World state (permitted read access)
    factions: list[FactionState] = []
    npcs: list[NPCState] = []
    threads: list[DormantThread] = []
    
    # Spatial state (2D specific)
    map: MapState | None = None
    
    # Game clock
    game_time: dict | None = None  # {day, hour, minute}
    paused: bool = False


class ActionRequest(BaseModel):
    """
    Request to commit a player action.
    
    POST /action receives this when player commits to an action.
    Frontend drives exploration; this is the commitment gate.
    """
    action_type: ActionType
    target: str | None = None  # Target ID (NPC, object, exit, etc.)
    position: Position | None = None  # For movement actions
    parameters: dict = {}  # Action-specific parameters
    state_version: int = Field(description="Client's state version for conflict detection")


class ActionResult(BaseModel):
    """Result of a single action."""
    success: bool
    message: str = ""
    changes: dict = {}  # State changes to apply


class CascadeNotice(BaseModel):
    """Notification of cascading consequences."""
    headline: str
    details: list[str] = []
    severity: Literal["info", "warning", "critical"] = "info"


class ActionResponse(BaseModel):
    """
    Response after committing an action.
    
    POST /action returns this with deterministic resolution.
    No LLM involved unless action triggers dialogue.
    """
    ok: bool = True
    action_id: str
    success: bool
    state_version: int = Field(description="New state version after action")
    turn_number: int
    
    # Results
    results: list[ActionResult] = []
    cascade_notices: list[CascadeNotice] = []
    
    # State delta (what changed)
    state_delta: dict = {}
    
    # Narrative hooks (for optional LLM crystallization)
    narrative_hooks: list[str] = []
    
    # Error info
    error: str | None = None


class DialogueRequest(BaseModel):
    """
    Request to crystallize meaning via LLM.
    
    POST /dialogue is invoked only when pressure collapses into dialogue.
    Design Rule: Silence is a valid (and often preferred) outcome.
    """
    npc_id: str
    context: str = ""  # What led to this dialogue
    player_intent: str = ""  # What player wants to achieve
    state_version: int


class DialogueOption(BaseModel):
    """A dialogue choice."""
    id: str
    text: str
    tone: str = "neutral"  # neutral, friendly, hostile, etc.
    social_cost: int = 0
    consequences: list[str] = []


class DialogueResponse(BaseModel):
    """
    Response with crystallized dialogue.

    POST /dialogue returns this with LLM-generated content.
    NPCs may end dialogue autonomously.
    """
    ok: bool = True
    npc_id: str
    state_version: int

    # Dialogue content
    npc_response: str
    tone: str = "neutral"
    options: list[DialogueOption] = []

    # Dialogue state
    dialogue_ended: bool = False
    end_reason: str | None = None  # "player_choice", "npc_ended", "interrupted"

    # State changes from dialogue
    disposition_change: int = 0
    social_energy_cost: int = 0

    # Error info
    error: str | None = None


# -----------------------------------------------------------------------------
# Combat Models
# -----------------------------------------------------------------------------

class CombatActionRequest(BaseModel):
    """Request to resolve a combat action."""
    action: str
    actor_id: str
    target_id: str | None = None
    target_position: Position | None = None
    round: int = 1
    state_version: int


class CombatActionResponse(BaseModel):
    """Result of a combat action."""
    ok: bool = True
    action: CombatActionRequest
    hit: bool | None = None
    injury: str | None = None
    target_status: str | None = None
    outcome: str | None = None
    summary: str | None = None
    state_version: int
    error: str | None = None


class CombatEndRequest(BaseModel):
    """Request to end combat and process consequences."""
    outcome: str
    rounds: int = 1
    state_version: int


class CombatEndResponse(BaseModel):
    """Result of ending combat."""
    ok: bool = True
    outcome: str
    faction_impact: dict[str, int] = {}
    injuries: dict[str, Any] = {}
    rounds: int
    state_version: int
    error: str | None = None


# -----------------------------------------------------------------------------
# WebSocket Event Models
# -----------------------------------------------------------------------------

class StateUpdateEvent(BaseModel):
    """
    Real-time state update via WebSocket.
    
    WS /updates streams these for frontend reconciliation.
    """
    type: Literal["state_update"] = "state_update"
    version: int
    timestamp: datetime
    
    # What changed
    changes: dict = {}
    
    # Source of change
    source: str = "system"  # "player", "npc", "system", "time"


class NPCMovementEvent(BaseModel):
    """NPC position update for patrol visualization."""
    type: Literal["npc_movement"] = "npc_movement"
    npc_id: str
    position: Position
    alert_state: AlertState
    timestamp: datetime


class GameClockEvent(BaseModel):
    """Game time advancement."""
    type: Literal["game_clock"] = "game_clock"
    game_time: dict
    paused: bool
    timestamp: datetime


class ConsequenceEvent(BaseModel):
    """Dormant thread activation or consequence propagation."""
    type: Literal["consequence"] = "consequence"
    thread_id: str | None = None
    headline: str
    details: list[str] = []
    severity: str = "info"
    timestamp: datetime


# Union type for WebSocket events
WSEvent = StateUpdateEvent | NPCMovementEvent | GameClockEvent | ConsequenceEvent


# -----------------------------------------------------------------------------
# Error Models
# -----------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Standard error response."""
    ok: bool = False
    error: str
    code: str | None = None
    details: dict = {}
