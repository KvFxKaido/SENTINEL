"""
Additional API routes for SENTINEL 2D.

These routes extend the core server with specialized endpoints
for the 2D exploration experience.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .schemas import (
    NPCState,
    RegionState,
    LocalMapState,
    Position,
    ConnectivityLevel,
    AlertState,
    ErrorResponse,
    CombatActionRequest,
    CombatActionResponse,
    CombatEndRequest,
    CombatEndResponse,
)
from .server import SentinelAPI


# Create router for additional endpoints
router = APIRouter()


# -----------------------------------------------------------------------------
# Map Endpoints
# -----------------------------------------------------------------------------

class MapOverviewResponse(BaseModel):
    """Overview of all regions for world map."""
    ok: bool = True
    current_region: str
    regions: list[RegionState]
    routes: list[dict] = []  # Available routes from current region


class RegionDetailResponse(BaseModel):
    """Detailed info for a specific region."""
    ok: bool = True
    region: RegionState
    routes_from_current: list[dict] = []
    content: dict = {}  # NPCs, jobs, threads in region


class LocalMapResponse(BaseModel):
    """Local map data for exploration."""
    ok: bool = True
    map: LocalMapState | None = None
    npcs: list[NPCState] = []
    objects: list[dict] = []
    patrol_routes: list[dict] = []


@router.get("/map", response_model=MapOverviewResponse)
async def get_map_overview(api: SentinelAPI = Depends(lambda: None)):
    """
    Get world map overview.
    
    Returns all regions with their connectivity and markers.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")
    
    # Get current region
    current_region = "rust_corridor"
    if campaign.session and hasattr(campaign.session, 'region'):
        current_region = campaign.session.region.value if campaign.session.region else current_region
    
    # Build region list
    regions = []
    for region_id, connectivity in campaign.region_connectivity.items():
        regions.append(RegionState(
            id=region_id,
            name=region_id.replace("_", " ").title(),
            connectivity=ConnectivityLevel(connectivity.value),
        ))
    
    # Get available routes
    routes = []
    # TODO: Implement route calculation from travel system
    
    return MapOverviewResponse(
        current_region=current_region,
        regions=regions,
        routes=routes,
    )


@router.get("/map/region/{region_id}", response_model=RegionDetailResponse)
async def get_region_detail(
    region_id: str,
    api: SentinelAPI = Depends(lambda: None),
):
    """
    Get detailed info for a specific region.
    
    Includes route feasibility from current location.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")
    
    # Check if region exists
    if region_id not in campaign.region_connectivity:
        raise HTTPException(status_code=404, detail=f"Region not found: {region_id}")
    
    connectivity = campaign.region_connectivity[region_id]
    
    region = RegionState(
        id=region_id,
        name=region_id.replace("_", " ").title(),
        connectivity=ConnectivityLevel(connectivity.value),
    )
    
    # Get content in region
    content = {
        "npcs": [npc.id for npc in campaign.npcs if hasattr(npc, 'region') and npc.region == region_id],
        "jobs": [],  # TODO: Get jobs in region
        "threads": [],  # TODO: Get threads related to region
    }
    
    return RegionDetailResponse(
        region=region,
        content=content,
    )


@router.get("/map/local", response_model=LocalMapResponse)
async def get_local_map(api: SentinelAPI = Depends(lambda: None)):
    """
    Get current local map for exploration.
    
    Returns tile data, NPCs, objects, and patrol routes.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")
    
    # TODO: Implement local map system
    # For now, return placeholder data
    return LocalMapResponse(
        map=None,
        npcs=[],
        objects=[],
        patrol_routes=[],
    )


# -----------------------------------------------------------------------------
# NPC Endpoints
# -----------------------------------------------------------------------------

class NPCListResponse(BaseModel):
    """List of NPCs in current context."""
    ok: bool = True
    npcs: list[NPCState]
    total: int


class NPCDetailResponse(BaseModel):
    """Detailed NPC information."""
    ok: bool = True
    npc: NPCState
    memories: list[str] = []
    leverage: list[dict] = []
    favors_owed: list[dict] = []


class NPCPositionUpdate(BaseModel):
    """Update NPC position (for patrol simulation)."""
    npc_id: str
    position: Position
    alert_state: AlertState = AlertState.PATROLLING


@router.get("/npcs", response_model=NPCListResponse)
async def list_npcs(
    region: str | None = None,
    faction: str | None = None,
    visible_only: bool = True,
    api: SentinelAPI = Depends(lambda: None),
):
    """
    List NPCs with optional filtering.
    
    Used for patrol visualization and interaction targets.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")
    
    npcs = []
    for npc in campaign.npcs:
        # Apply filters
        if visible_only and npc.status != "active":
            continue
        if faction and (not npc.faction or npc.faction.value != faction):
            continue
        # TODO: Add region filtering when NPCs have region data
        
        npcs.append(NPCState(
            id=npc.id,
            name=npc.name,
            faction=npc.faction.value if npc.faction else None,
            disposition=npc.disposition.value,
            visible=npc.status == "active",
            interactable=npc.status == "active",
            last_interaction=npc.last_interaction.isoformat() if npc.last_interaction else None,
        ))
    
    return NPCListResponse(
        npcs=npcs,
        total=len(npcs),
    )


@router.get("/npcs/{npc_id}", response_model=NPCDetailResponse)
async def get_npc_detail(
    npc_id: str,
    api: SentinelAPI = Depends(lambda: None),
):
    """
    Get detailed NPC information.
    
    Includes memories, leverage, and favor state.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")
    
    npc = api.manager.get_npc(npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail=f"NPC not found: {npc_id}")
    
    npc_state = NPCState(
        id=npc.id,
        name=npc.name,
        faction=npc.faction.value if npc.faction else None,
        disposition=npc.disposition.value,
        visible=npc.status == "active",
        interactable=npc.status == "active",
        last_interaction=npc.last_interaction.isoformat() if npc.last_interaction else None,
    )
    
    # Get memories
    memories = [m.content for m in npc.memories] if hasattr(npc, 'memories') else []
    
    # Get leverage
    leverage = []
    if hasattr(npc, 'leverage') and npc.leverage:
        for lev in npc.leverage:
            leverage.append({
                "type": lev.type,
                "description": lev.description,
            })
    
    # Get favors
    favors = []
    if hasattr(npc, 'favors_owed') and npc.favors_owed:
        for favor in npc.favors_owed:
            favors.append({
                "type": favor.type.value if hasattr(favor.type, 'value') else str(favor.type),
                "description": favor.description if hasattr(favor, 'description') else "",
            })
    
    return NPCDetailResponse(
        npc=npc_state,
        memories=memories,
        leverage=leverage,
        favors_owed=favors,
    )


# -----------------------------------------------------------------------------
# Patrol AI Endpoints (Phase 3 preparation)
# -----------------------------------------------------------------------------

class PatrolStateResponse(BaseModel):
    """Current patrol state for all NPCs."""
    ok: bool = True
    patrols: list[dict]
    timestamp: datetime


class PatrolRouteResponse(BaseModel):
    """Patrol route definition."""
    ok: bool = True
    npc_id: str
    route: list[Position]
    behavior: str  # "lattice", "ember", "ghost", "covenant"
    cycle_time: float  # Seconds per patrol cycle


@router.get("/patrols", response_model=PatrolStateResponse)
async def get_patrol_state(api: SentinelAPI = Depends(lambda: None)):
    """
    Get current patrol state for all NPCs.
    
    Used for real-time patrol visualization.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")
    
    # TODO: Implement patrol system
    # For now, return empty state
    return PatrolStateResponse(
        patrols=[],
        timestamp=datetime.now(),
    )


@router.get("/patrols/{npc_id}/route", response_model=PatrolRouteResponse)
async def get_patrol_route(
    npc_id: str,
    api: SentinelAPI = Depends(lambda: None),
):
    """
    Get patrol route for a specific NPC.
    
    Returns waypoints and behavior pattern.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")
    
    npc = api.manager.get_npc(npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail=f"NPC not found: {npc_id}")
    
    # TODO: Implement patrol routes
    # For now, return placeholder
    return PatrolRouteResponse(
        npc_id=npc_id,
        route=[],
        behavior="patrolling",
        cycle_time=60.0,
    )


# -----------------------------------------------------------------------------
# Faction Pressure Endpoints
# -----------------------------------------------------------------------------

class FactionPressureResponse(BaseModel):
    """Faction pressure state for visualization."""
    ok: bool = True
    pressures: list[dict]
    leverage_demands: list[dict] = []


@router.get("/factions/pressure", response_model=FactionPressureResponse)
async def get_faction_pressure(api: SentinelAPI = Depends(lambda: None)):
    """
    Get faction pressure state.
    
    Used for pressure visualization in 2D view.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")
    
    pressures = []
    faction_attrs = [
        'nexus', 'ember_colonies', 'lattice', 'convergence', 'covenant',
        'wanderers', 'cultivators', 'steel_syndicate', 'witnesses',
        'architects', 'ghost_networks'
    ]
    
    for attr in faction_attrs:
        faction_standing = getattr(campaign.factions, attr, None)
        if faction_standing:
            pressures.append({
                "faction_id": attr,
                "faction_name": attr.replace("_", " ").title(),
                "standing": faction_standing.standing.value,
                "reputation": faction_standing.numeric_value,
                "pressure_level": abs(faction_standing.numeric_value) // 20,  # 0-5 scale
            })
    
    # Get active leverage demands
    leverage_demands = []
    # TODO: Get from leverage system
    
    return FactionPressureResponse(
        pressures=pressures,
        leverage_demands=leverage_demands,
    )


# -----------------------------------------------------------------------------
# Game Clock Endpoints
# -----------------------------------------------------------------------------

class GameClockResponse(BaseModel):
    """Current game time state."""
    ok: bool = True
    day: int = 1
    hour: int = 8
    minute: int = 0
    paused: bool = False
    time_scale: float = 1.0


class AdvanceTimeRequest(BaseModel):
    """Request to advance game time."""
    minutes: int = 0
    hours: int = 0
    days: int = 0


@router.get("/clock", response_model=GameClockResponse)
async def get_game_clock(api: SentinelAPI = Depends(lambda: None)):
    """
    Get current game time.

    Used for time-based events and patrol cycles.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")

    # In SENTINEL, time is tracked in sessions and relative minutes
    # Mapping session + minutes to day/hour/minute
    total_minutes = campaign.meta.session_count * 120 # Estimate 2 hours per session

    day = (total_minutes // 1440) + 1
    hour = (total_minutes % 1440) // 60
    minute = total_minutes % 60

    return GameClockResponse(
        day=day,
        hour=hour,
        minute=minute,
        paused=False
    )


@router.post("/clock/advance", response_model=GameClockResponse)
async def advance_game_clock(
    request: AdvanceTimeRequest,
    api: SentinelAPI = Depends(lambda: None),
):
    """
    Advance game time.

    Triggers time-based events and patrol updates.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")

    # Update campaign state (simplified for now)
    # We could add a 'minutes_passed' field to the campaign meta

    return await get_game_clock(api)


@router.post("/clock/pause")
async def pause_game_clock(api: SentinelAPI = Depends(lambda: None)):
    """Pause game clock (e.g., during dialogue)."""
    # TODO: Implement pause
    return {"ok": True, "paused": True}


@router.post("/clock/resume")
async def resume_game_clock(api: SentinelAPI = Depends(lambda: None)):
    """Resume game clock."""
    # TODO: Implement resume
    return {"ok": True, "paused": False}


# -----------------------------------------------------------------------------
# Consequence Endpoints
# -----------------------------------------------------------------------------

class ConsequenceCheckResponse(BaseModel):
    """Check for pending consequences."""
    ok: bool = True
    pending_threads: list[dict] = []
    recent_activations: list[dict] = []


@router.get("/consequences/check", response_model=ConsequenceCheckResponse)
async def check_consequences(
    mapId: str | None = None,
    api: SentinelAPI = Depends(lambda: None),
):
    """
    Check for pending consequences.

    Used to surface dormant threads that may activate.
    Supports filtering by mapId for spatial triggers.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")

    pending = []
    for thread in campaign.dormant_threads:
        # Check if thread is relevant to current map
        # This assumes thread.trigger_condition contains map info or we have spatial metadata
        is_relevant = True
        if mapId and mapId.lower() not in thread.trigger_condition.lower():
            # Basic keyword check for now
            is_relevant = False

        if is_relevant:
            pending.append({
                "id": thread.id,
                "trigger": thread.trigger_condition,
                "severity": thread.severity.value,
                "description": thread.consequence,
                "age_sessions": campaign.meta.session_count - thread.created_session,
                "spatial": {
                    "map_id": mapId or "unknown",
                    "position": {"col": 10, "row": 10} # Placeholder spatial data
                }
            })

    return ConsequenceCheckResponse(
        pending_threads=pending,
        recent_activations=[],
    )


# -----------------------------------------------------------------------------
# Combat Endpoints
# -----------------------------------------------------------------------------

@router.post("/combat/action", response_model=CombatActionResponse)
async def resolve_combat_action(
    request: CombatActionRequest,
    api: SentinelAPI = Depends(lambda: None),
):
    """
    Resolve a combat action.

    Deterministic resolution of hits, injuries, and status changes.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")

    # TODO: Implement combat resolution system
    # For now, return a deterministic-ish mock based on actor_id and round
    seed = hash(request.actor_id + str(request.round)) % 100
    hit = seed > 40

    summary = f"{request.actor_id} performs {request.action}"
    if hit:
        summary += f" and hits {request.target_id or 'target'}"
    else:
        summary += " but misses"

    return CombatActionResponse(
        action=request,
        hit=hit,
        summary=summary,
        state_version=campaign.state_version,
    )


@router.post("/combat/end", response_model=CombatEndResponse)
async def end_combat(
    request: CombatEndRequest,
    api: SentinelAPI = Depends(lambda: None),
):
    """
    End combat and propagate consequences.

    Updates faction reputation and character injuries based on outcome.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")

    # TODO: Implement combat consequence propagation
    # Apply faction impact based on outcome
    impact = {}
    if request.outcome == "victory":
        # Example impact
        impact = {"lattice": -5, "steel_syndicate": 2}

    return CombatEndResponse(
        outcome=request.outcome,
        faction_impact=impact,
        rounds=request.rounds,
        state_version=campaign.state_version,
    )
