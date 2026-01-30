"""
Additional API routes for SENTINEL 2D.

These routes extend the core server with specialized endpoints
for the 2D exploration experience.
"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

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

# Load region data for route calculations
_REGIONS_DATA: dict | None = None


def _load_regions_data() -> dict:
    """Load regions.json data, cached."""
    global _REGIONS_DATA
    if _REGIONS_DATA is None:
        data_path = Path(__file__).parent.parent.parent / "data" / "regions.json"
        if data_path.exists():
            with open(data_path) as f:
                _REGIONS_DATA = json.load(f)
        else:
            _REGIONS_DATA = {"regions": {}}
    return _REGIONS_DATA


def _get_routes_from_region(from_region: str, campaign) -> list[dict]:
    """Calculate available routes from a region."""
    data = _load_regions_data()
    regions = data.get("regions", {})
    
    if from_region not in regions:
        return []
    
    region_data = regions[from_region]
    routes_data = region_data.get("routes", {})
    routes = []
    
    for dest_id, route_info in routes_data.items():
        requirements = route_info.get("requirements", [])
        feasible = True
        blocked_reason = None
        
        # Check requirements
        for req in requirements:
            req_type = req.get("type")
            if req_type == "faction":
                # Check faction standing
                faction_id = req.get("faction", "").lower().replace(" ", "_")
                min_standing = req.get("min_standing", "neutral")
                standing = _get_faction_standing(campaign, faction_id)
                if not _meets_standing_requirement(standing, min_standing):
                    feasible = False
                    blocked_reason = f"Requires {min_standing} standing with {faction_id.replace('_', ' ').title()}"
            elif req_type == "vehicle":
                # Check vehicle capability
                capability = req.get("capability")
                if capability and not _has_vehicle_capability(campaign, capability):
                    feasible = False
                    blocked_reason = f"Requires vehicle with {capability} capability"
            elif req_type == "contact":
                # Check if player has contact in faction
                faction_id = req.get("faction", "").lower().replace(" ", "_")
                if not _has_faction_contact(campaign, faction_id):
                    feasible = False
                    blocked_reason = f"Requires contact in {faction_id.replace('_', ' ').title()}"
        
        routes.append({
            "destination": dest_id,
            "destination_name": regions.get(dest_id, {}).get("name", dest_id.replace("_", " ").title()),
            "terrain": route_info.get("terrain", []),
            "description": route_info.get("travel_description", ""),
            "feasible": feasible,
            "blocked_reason": blocked_reason,
            "alternatives": route_info.get("alternatives", []),
        })
    
    return routes


def _get_faction_standing(campaign, faction_id: str) -> str:
    """Get player's standing with a faction."""
    if not campaign or not campaign.factions:
        return "neutral"
    faction_standing = getattr(campaign.factions, faction_id, None)
    if faction_standing:
        return faction_standing.standing.value.lower()
    return "neutral"


def _meets_standing_requirement(current: str, required: str) -> bool:
    """Check if current standing meets requirement."""
    standing_order = ["hostile", "unfriendly", "neutral", "friendly", "allied"]
    try:
        current_idx = standing_order.index(current.lower())
        required_idx = standing_order.index(required.lower())
        return current_idx >= required_idx
    except ValueError:
        return True  # Unknown standings default to passing


def _has_vehicle_capability(campaign, capability: str) -> bool:
    """Check if player has a vehicle with required capability."""
    if not campaign or not campaign.characters:
        return False
    char = campaign.characters[0]
    for vehicle in getattr(char, 'vehicles', []):
        if vehicle.status.value == "owned":
            # Check terrain capabilities
            if capability == "offroad" and "off-road" in vehicle.terrain:
                return True
            if capability == "water" and "water" in vehicle.terrain:
                return True
            if capability in vehicle.terrain:
                return True
    return False


def _has_faction_contact(campaign, faction_id: str) -> bool:
    """Check if player has met an NPC from the faction."""
    if not campaign:
        return False
    faction_name = faction_id.replace("_", " ").title()
    all_npcs = campaign.npcs.active + campaign.npcs.dormant if hasattr(campaign.npcs, 'active') else []
    for npc in all_npcs:
        if npc.faction and npc.faction.value == faction_name:
            return True
    return False


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
    
    # Get available routes from current region
    routes = _get_routes_from_region(current_region, campaign)
    
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
    
    # Get NPCs associated with this region (by faction presence)
    data = _load_regions_data()
    region_info = data.get("regions", {}).get(region_id, {})
    primary_faction = region_info.get("primary_faction", "")
    contested_by = region_info.get("contested_by", [])
    region_factions = [primary_faction] + contested_by
    
    npc_ids = []
    all_npcs = campaign.npcs.active + campaign.npcs.dormant if hasattr(campaign.npcs, 'active') else []
    for npc in all_npcs:
        if npc.faction:
            faction_key = npc.faction.value.lower().replace(" ", "_")
            if faction_key in region_factions:
                npc_ids.append(npc.id)
    
    # Get jobs in region
    jobs = []
    if hasattr(campaign, 'job_board') and campaign.job_board:
        for job in campaign.job_board.available_jobs:
            if hasattr(job, 'region') and job.region and job.region.value == region_id:
                jobs.append({
                    "id": job.id,
                    "title": job.title,
                    "faction": job.faction.value if job.faction else None,
                })
    
    # Get threads related to region
    threads = []
    for thread in campaign.dormant_threads:
        # Check if thread trigger or consequence mentions region
        region_name = region_id.replace("_", " ")
        if region_name.lower() in thread.trigger_condition.lower() or region_name.lower() in thread.consequence.lower():
            threads.append({
                "id": thread.id,
                "trigger": thread.trigger_condition,
                "severity": thread.severity.value,
            })
    
    content = {
        "npcs": npc_ids,
        "jobs": jobs,
        "threads": threads,
        "primary_faction": primary_faction,
        "contested_by": contested_by,
        "terrain": region_info.get("terrain", []),
        "character": region_info.get("character", ""),
    }
    
    # Calculate routes from current region to this region
    current_region = "rust_corridor"
    if campaign.session and hasattr(campaign.session, 'region'):
        current_region = campaign.session.region.value if campaign.session.region else current_region
    
    routes_from_current = []
    if current_region != region_id:
        all_routes = _get_routes_from_region(current_region, campaign)
        routes_from_current = [r for r in all_routes if r["destination"] == region_id]
    
    return RegionDetailResponse(
        region=region,
        routes_from_current=routes_from_current,
        content=content,
    )


@router.get("/map/local", response_model=LocalMapResponse)
async def get_local_map(
    map_id: str | None = None,
    api: SentinelAPI = Depends(lambda: None),
):
    """
    Get current local map for exploration.
    
    Returns tile data, NPCs, objects, and patrol routes.
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")
    
    # Get current region to determine available maps
    current_region = "rust_corridor"
    if campaign.session and hasattr(campaign.session, 'region'):
        current_region = campaign.session.region.value if campaign.session.region else current_region
    
    # Get current location type
    location = campaign.location if hasattr(campaign, 'location') else None
    location_value = location.value if location else "safe_house"
    
    # Map location types to local map IDs
    location_to_map = {
        "safe_house": "safehouse_main",
        "market": "market",
        "field": "street",
        "faction_hq": "faction_hq",
    }
    
    resolved_map_id = map_id or location_to_map.get(location_value, "safehouse_main")
    
    # Build local map state
    local_map = LocalMapState(
        id=resolved_map_id,
        name=resolved_map_id.replace("_", " ").title(),
        region_id=current_region,
    )
    
    # Get NPCs that could be present based on location and faction
    data = _load_regions_data()
    region_info = data.get("regions", {}).get(current_region, {})
    primary_faction = region_info.get("primary_faction", "")
    contested_by = region_info.get("contested_by", [])
    
    npcs = []
    active_npcs = campaign.npcs.active if hasattr(campaign.npcs, 'active') else []
    for npc in active_npcs:
        if npc.faction:
            faction_key = npc.faction.value.lower().replace(" ", "_")
            if faction_key == primary_faction or faction_key in contested_by:
                npcs.append(NPCState(
                    id=npc.id,
                    name=npc.name,
                    faction=npc.faction.value if npc.faction else None,
                    disposition=npc.disposition.value,
                    visible=True,
                    interactable=True,
                ))
    
    # Generate patrol routes for NPCs based on faction behavior
    patrol_routes = _generate_patrol_routes(npcs, resolved_map_id)
    
    return LocalMapResponse(
        map=local_map,
        npcs=npcs,
        objects=[],
        patrol_routes=patrol_routes,
    )


def _generate_patrol_routes(npcs: list[NPCState], map_id: str) -> list[dict]:
    """Generate patrol routes for NPCs based on faction behavior patterns."""
    routes = []
    
    # Faction behavior patterns from Phase 3
    faction_behaviors = {
        "lattice": "sweep",           # Coordinated sweeps across chokepoints
        "steel_syndicate": "sweep",   # Similar coordinated patterns
        "ember_colonies": "wander",   # Loose, wandering solo paths
        "ghost_networks": "static",   # Static presence, sudden relocation
        "covenant": "ritual",         # Ritualized, time-bound circuits
    }
    
    for i, npc in enumerate(npcs):
        if not npc.faction:
            continue
        
        faction_key = npc.faction.lower().replace(" ", "_")
        behavior = faction_behaviors.get(faction_key, "wander")
        
        # Generate waypoints based on behavior
        if behavior == "sweep":
            # Horizontal or vertical sweep patterns
            waypoints = [
                {"x": 100 + i * 50, "y": 100},
                {"x": 300 + i * 50, "y": 100},
                {"x": 300 + i * 50, "y": 200},
                {"x": 100 + i * 50, "y": 200},
            ]
        elif behavior == "static":
            # Single position with occasional jumps
            waypoints = [
                {"x": 150 + i * 80, "y": 150},
            ]
        elif behavior == "ritual":
            # Circular/ritual pattern
            waypoints = [
                {"x": 200, "y": 100 + i * 30},
                {"x": 250, "y": 150 + i * 30},
                {"x": 200, "y": 200 + i * 30},
                {"x": 150, "y": 150 + i * 30},
            ]
        else:  # wander
            # Random-ish patrol points
            waypoints = [
                {"x": 100 + (i * 37) % 200, "y": 100 + (i * 53) % 150},
                {"x": 200 + (i * 41) % 150, "y": 150 + (i * 47) % 100},
                {"x": 150 + (i * 31) % 180, "y": 200 + (i * 59) % 80},
            ]
        
        routes.append({
            "npc_id": npc.id,
            "behavior": behavior,
            "waypoints": waypoints,
            "cycle_time": 30.0 if behavior == "sweep" else 45.0,
            "pause_duration": 2.0 if behavior == "static" else 1.0,
        })
    
    return routes


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
    all_npcs = campaign.npcs.active + campaign.npcs.dormant if hasattr(campaign.npcs, 'active') else []
    for npc in all_npcs:
        # Apply filters
        is_active = npc in (campaign.npcs.active if hasattr(campaign.npcs, 'active') else [])
        if visible_only and not is_active:
            continue
        if faction and (not npc.faction or npc.faction.value != faction):
            continue
        
        # Region filtering: check if NPC's faction is present in that region
        if region:
            data = _load_regions_data()
            region_info = data.get("regions", {}).get(region, {})
            region_factions = [region_info.get("primary_faction", "")] + region_info.get("contested_by", [])
            if npc.faction:
                faction_key = npc.faction.value.lower().replace(" ", "_")
                if faction_key not in region_factions:
                    continue
            else:
                continue  # No faction = skip for region filter
        
        npcs.append(NPCState(
            id=npc.id,
            name=npc.name,
            faction=npc.faction.value if npc.faction else None,
            disposition=npc.disposition.value,
            visible=is_active,
            interactable=is_active,
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
    
    # Get current region NPCs
    current_region = "rust_corridor"
    if campaign.session and hasattr(campaign.session, 'region'):
        current_region = campaign.session.region.value if campaign.session.region else current_region
    
    data = _load_regions_data()
    region_info = data.get("regions", {}).get(current_region, {})
    region_factions = [region_info.get("primary_faction", "")] + region_info.get("contested_by", [])
    
    # Build patrol states for NPCs in region
    patrols = []
    active_npcs = campaign.npcs.active if hasattr(campaign.npcs, 'active') else []
    for npc in active_npcs:
        if not npc.faction:
            continue
        
        faction_key = npc.faction.value.lower().replace(" ", "_")
        if faction_key not in region_factions:
            continue
        
        # Determine behavior from faction
        faction_behaviors = {
            "lattice": "sweep",
            "steel_syndicate": "sweep", 
            "ember_colonies": "wander",
            "ghost_networks": "static",
            "covenant": "ritual",
        }
        behavior = faction_behaviors.get(faction_key, "wander")
        
        patrols.append({
            "npc_id": npc.id,
            "npc_name": npc.name,
            "faction": npc.faction.value,
            "behavior": behavior,
            "alert_state": "patrolling",
            "position": {"x": 150, "y": 150},  # Default position
        })
    
    return PatrolStateResponse(
        patrols=patrols,
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
    
    # Determine behavior from faction
    faction_behaviors = {
        "lattice": "sweep",
        "steel_syndicate": "sweep",
        "ember_colonies": "wander", 
        "ghost_networks": "static",
        "covenant": "ritual",
    }
    
    faction_key = npc.faction.value.lower().replace(" ", "_") if npc.faction else ""
    behavior = faction_behaviors.get(faction_key, "wander")
    
    # Generate route based on behavior
    if behavior == "sweep":
        route = [
            Position(x=100, y=100),
            Position(x=300, y=100),
            Position(x=300, y=200),
            Position(x=100, y=200),
        ]
        cycle_time = 30.0
    elif behavior == "static":
        route = [Position(x=150, y=150)]
        cycle_time = 60.0
    elif behavior == "ritual":
        route = [
            Position(x=200, y=100),
            Position(x=250, y=150),
            Position(x=200, y=200),
            Position(x=150, y=150),
        ]
        cycle_time = 45.0
    else:  # wander
        route = [
            Position(x=120, y=130),
            Position(x=220, y=180),
            Position(x=170, y=220),
        ]
        cycle_time = 45.0
    
    return PatrolRouteResponse(
        npc_id=npc_id,
        route=route,
        behavior=behavior,
        cycle_time=cycle_time,
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
    
    # Get active leverage demands from enhancements
    leverage_demands = []
    if campaign.characters:
        char = campaign.characters[0]
        for enh in getattr(char, 'enhancements', []):
            if hasattr(enh, 'source') and hasattr(enh, 'called_in') and not enh.called_in:
                leverage_demands.append({
                    "enhancement_id": enh.id,
                    "enhancement_name": enh.name,
                    "faction": enh.source.value if hasattr(enh.source, 'value') else str(enh.source),
                    "benefit": enh.benefit,
                    "status": "pending",
                })
    
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


# Clock pause state (in-memory for now, would be persisted in production)
_clock_paused: bool = False


@router.post("/clock/pause")
async def pause_game_clock(api: SentinelAPI = Depends(lambda: None)):
    """Pause game clock (e.g., during dialogue)."""
    global _clock_paused
    _clock_paused = True
    return {"ok": True, "paused": True}


@router.post("/clock/resume")
async def resume_game_clock(api: SentinelAPI = Depends(lambda: None)):
    """Resume game clock."""
    global _clock_paused
    _clock_paused = False
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

# Injury types from Phase 5 design
INJURY_TYPES = ["grazed", "impaired_movement", "reduced_accuracy", "gear_damaged", "bleeding"]


def _resolve_combat_hit(action: str, actor_id: str, target_id: str | None, round_num: int) -> tuple[bool, str | None]:
    """
    Resolve whether an action hits and what injury results.
    
    Uses deterministic resolution based on action type and round.
    """
    # Base hit chance varies by action
    base_hit_chance = {
        "fire": 55,
        "strike": 70,
        "suppress": 40,  # Suppress is about control, not damage
        "move": 100,     # Move always succeeds
        "flee": 85,      # Usually succeeds
        "talk": 100,     # Talking always "hits"
        "interact": 100,
    }
    
    chance = base_hit_chance.get(action.lower(), 50)
    
    # Deterministic "random" based on inputs
    seed = hash(f"{actor_id}:{target_id}:{round_num}:{action}") % 100
    hit = seed < chance
    
    # Determine injury if hit with damaging action
    injury = None
    if hit and action.lower() in ("fire", "strike"):
        injury_seed = hash(f"injury:{actor_id}:{target_id}:{round_num}") % len(INJURY_TYPES)
        injury = INJURY_TYPES[injury_seed]
    
    return hit, injury


@router.post("/combat/action", response_model=CombatActionResponse)
async def resolve_combat_action(
    request: CombatActionRequest,
    api: SentinelAPI = Depends(lambda: None),
):
    """
    Resolve a combat action.

    Deterministic resolution of hits, injuries, and status changes.
    Combat design rules (Phase 5):
    - Positioning > Abilities
    - Injuries > HP (damage creates persistent conditions)
    - Fast resolution or spiral
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")

    # Resolve the action
    hit, injury = _resolve_combat_hit(
        request.action,
        request.actor_id,
        request.target_id,
        request.round,
    )
    
    # Build action summary
    action_verb = {
        "fire": "fires",
        "strike": "strikes",
        "suppress": "suppresses",
        "move": "moves",
        "flee": "attempts to flee",
        "talk": "attempts to talk",
        "interact": "interacts with",
    }.get(request.action.lower(), "acts")
    
    if request.action.lower() == "move":
        summary = f"{request.actor_id} repositions"
        if request.target_position:
            summary += f" to ({request.target_position.x:.0f}, {request.target_position.y:.0f})"
    elif request.action.lower() == "flee":
        if hit:
            summary = f"{request.actor_id} successfully disengages"
        else:
            summary = f"{request.actor_id} is cut off while trying to flee"
    elif request.action.lower() == "suppress":
        summary = f"{request.actor_id} lays down suppressing fire"
        if request.target_id:
            summary += f", pinning {request.target_id}"
    elif request.action.lower() == "talk":
        summary = f"{request.actor_id} calls out"
        if request.target_id:
            summary += f" to {request.target_id}"
    else:
        summary = f"{request.actor_id} {action_verb}"
        if request.target_id:
            if hit:
                summary += f" and hits {request.target_id}"
                if injury:
                    summary += f" ({injury.replace('_', ' ')})"
            else:
                summary += f" at {request.target_id} but misses"
    
    # Determine target status after injury
    target_status = None
    if injury:
        if injury == "bleeding":
            target_status = "critical"
        elif injury in ("impaired_movement", "reduced_accuracy"):
            target_status = "wounded"
        else:
            target_status = "injured"
    
    return CombatActionResponse(
        action=request,
        hit=hit,
        injury=injury,
        target_status=target_status,
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
    Combat consequences (Phase 5/6):
    - Retreat carries social/faction consequences, not mechanical punishment
    - Combat leaves lasting marks on world and character
    """
    campaign = api.manager.current
    if not campaign:
        raise HTTPException(status_code=400, detail="No campaign loaded")

    # Determine faction impact based on outcome and context
    impact = {}
    injuries = {}
    
    # Get current region's factions
    current_region = "rust_corridor"
    if campaign.session and hasattr(campaign.session, 'region'):
        current_region = campaign.session.region.value if campaign.session.region else current_region
    
    data = _load_regions_data()
    region_info = data.get("regions", {}).get(current_region, {})
    primary_faction = region_info.get("primary_faction", "")
    contested_by = region_info.get("contested_by", [])
    
    if request.outcome == "victory":
        # Victory against primary faction damages standing, helps rivals
        if primary_faction:
            impact[primary_faction] = -10
        for rival in contested_by:
            impact[rival] = 3
    elif request.outcome == "defeat":
        # Defeat increases faction standing (they won)
        if primary_faction:
            impact[primary_faction] = 5
    elif request.outcome == "fled":
        # Fleeing has minor reputation cost
        if primary_faction:
            impact[primary_faction] = -2
        # But player may have injuries from fleeing
        if request.rounds > 2:
            injuries["player"] = {"type": "grazed", "source": "combat_retreat"}
    elif request.outcome == "negotiated":
        # Talking your way out can improve standing
        if primary_faction:
            impact[primary_faction] = 2
    
    # Apply faction changes to campaign (if methods exist)
    for faction_id, change in impact.items():
        faction_attr = faction_id.lower().replace(" ", "_")
        faction_standing = getattr(campaign.factions, faction_attr, None)
        if faction_standing and hasattr(faction_standing, 'adjust_reputation'):
            faction_standing.adjust_reputation(change)
    
    # Save campaign state
    api.manager.save_campaign()
    
    return CombatEndResponse(
        outcome=request.outcome,
        faction_impact=impact,
        injuries=injuries,
        rounds=request.rounds,
        state_version=campaign.state_version,
    )
