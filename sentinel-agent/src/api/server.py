"""
SENTINEL 2D FastAPI Server.

Phase 1 of 2D Conversion Plan: Backend API Refactor.

Architecture:
- Python becomes stateful REST/WebSocket service
- Frontend drives real-time exploration, Python responds only to commits
- State persists between requests
- LLM invoked only when ambiguity collapses into meaning

Endpoints:
- GET  /state     - Full game state snapshot
- POST /action    - Commit player action
- POST /dialogue  - Crystallize meaning via LLM
- WS   /updates   - Real-time state stream
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    GameStateResponse,
    ActionRequest,
    ActionResponse,
    ActionResult,
    CascadeNotice,
    DialogueRequest,
    DialogueResponse,
    DialogueOption,
    ErrorResponse,
    StateUpdateEvent,
    NPCMovementEvent,
    GameClockEvent,
    ConsequenceEvent,
    CampaignInfo,
    CharacterState,
    FactionState,
    NPCState,
    DormantThread,
    MapState,
    RegionState,
    LocalMapState,
    Position,
    SocialEnergyState,
    GearItem,
    Enhancement,
    Vehicle,
    LocationType,
    ConnectivityLevel,
    AlertState,
    ActionType,
)


class ConnectionManager:
    """Manages WebSocket connections for real-time state updates."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send message to a specific client."""
        await websocket.send_json(message)


class SentinelAPI:
    """
    SENTINEL 2D API backend.
    
    Wraps the game engine and provides stateful REST/WebSocket interface.
    This is the core of Phase 1: Backend API Refactor.
    """
    
    def __init__(
        self,
        campaigns_dir: Path | str = "campaigns",
        prompts_dir: Path | str | None = None,
        lore_dir: Path | str | None = None,
        wiki_dir: Path | str | None = None,
        backend: str = "auto",
        local_mode: bool = False,
    ):
        from ..state import CampaignManager
        from ..agent import SentinelAgent
        from ..systems.turns import TurnOrchestrator
        from ..systems.validation import ActionValidator
        from ..systems.travel import TravelResolver
        from ..systems.cascades import CascadeProcessor
        
        self.campaigns_dir = Path(campaigns_dir)
        
        # Resolve paths
        base_dir = Path(__file__).parent.parent.parent.parent
        self.prompts_dir = Path(prompts_dir) if prompts_dir else base_dir / "prompts"
        self.lore_dir = Path(lore_dir) if lore_dir else (base_dir / "lore" if (base_dir / "lore").exists() else None)
        self.wiki_dir = Path(wiki_dir) if wiki_dir else (base_dir / "wiki" if (base_dir / "wiki").exists() else None)
        
        # Initialize core systems
        self.manager = CampaignManager(
            self.campaigns_dir,
            wiki_dir=self.wiki_dir,
        )
        
        self.agent = SentinelAgent(
            self.manager,
            prompts_dir=self.prompts_dir,
            lore_dir=self.lore_dir,
            backend=backend,
            local_mode=local_mode,
        )
        
        # Turn-based systems
        self._validator = ActionValidator()
        self._travel_resolver = TravelResolver()
        self._cascade_processor = CascadeProcessor()
        self._orchestrator: TurnOrchestrator | None = None
        
        # State versioning for optimistic updates
        self._state_version = 0
        self._turn_number = 0
        
        # WebSocket connection manager
        self.connections = ConnectionManager()
        
        # Event subscriptions
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Subscribe to game events for WebSocket broadcasting."""
        from ..state import get_event_bus, EventType
        
        bus = get_event_bus()
        for event_type in EventType:
            bus.on(event_type, self._handle_game_event)
    
    async def _handle_game_event(self, event):
        """Forward game events to WebSocket clients."""
        await self.connections.broadcast({
            "type": "game_event",
            "event_type": event.type.value,
            "data": event.data,
            "timestamp": datetime.now().isoformat(),
        })
    
    def _ensure_orchestrator(self):
        """Ensure turn orchestrator is bound to current campaign."""
        from ..systems.turns import TurnOrchestrator
        
        campaign = self.manager.current
        if not campaign:
            return None
        
        if self._orchestrator is None or self._orchestrator.campaign is not campaign:
            self._orchestrator = TurnOrchestrator(campaign)
            self._orchestrator.set_validator(self._validator.validate)
            self._orchestrator.register_resolver("travel", self._travel_resolver.resolve)
            self._orchestrator.set_cascade_processor(
                lambda event, camp: self._cascade_processor.process(event, camp)
            )
            self._orchestrator.set_persist_fn(lambda camp: self.manager.save_campaign())
        
        return self._orchestrator
    
    def _increment_version(self) -> int:
        """Increment and return new state version."""
        self._state_version += 1
        return self._state_version
    
    # -------------------------------------------------------------------------
    # State Serialization
    # -------------------------------------------------------------------------
    
    def get_game_state(self) -> GameStateResponse:
        """
        Get full game state snapshot.
        
        This is the primary state query endpoint.
        Frontend caches this and updates via WebSocket stream.
        """
        campaign = self.manager.current
        
        if not campaign:
            return GameStateResponse(
                ok=True,
                version=self._state_version,
                timestamp=datetime.now(),
            )
        
        # Build character state
        character = None
        if campaign.characters:
            char = campaign.characters[0]
            character = CharacterState(
                id=char.id,
                name=char.name,
                background=char.background.value if char.background else None,
                social_energy=SocialEnergyState(
                    current=char.social_energy.current,
                    max=100,  # SocialEnergy uses 0-100 scale
                    percentage=float(char.social_energy.current),
                ),
                credits=char.credits,
                gear=[
                    GearItem(
                        id=item.id,
                        name=item.name,
                        category=item.category,
                        description=item.description,
                        used=item.used,
                        single_use=item.single_use,
                    )
                    for item in char.gear
                ],
                loadout=getattr(char, 'loadout', []),
                enhancements=[
                    Enhancement(
                        id=enh.id,
                        name=enh.name,
                        source=enh.source.value if hasattr(enh.source, 'value') else str(enh.source),
                        benefit=enh.benefit,
                    )
                    for enh in char.enhancements
                ],
                vehicles=[
                    Vehicle(
                        id=v.id,
                        name=v.name,
                        type=v.type,
                        fuel=v.fuel,
                        condition=v.condition,
                        status=v.status.value if hasattr(v.status, 'value') else str(v.status),
                        terrain=v.terrain,
                        capacity=v.capacity,
                        cargo=v.cargo,
                        stealth=v.stealth,
                    )
                    for v in char.vehicles
                ],
            )
        
        # Build faction states
        factions = []
        faction_attrs = [
            'nexus', 'ember_colonies', 'lattice', 'convergence', 'covenant',
            'wanderers', 'cultivators', 'steel_syndicate', 'witnesses',
            'architects', 'ghost_networks'
        ]
        for attr in faction_attrs:
            faction_standing = getattr(campaign.factions, attr, None)
            if faction_standing:
                factions.append(FactionState(
                    id=attr,
                    name=attr.replace("_", " ").title(),
                    standing=faction_standing.standing.value,
                    reputation=faction_standing.numeric_value,
                ))
        
        # Build NPC states
        npcs = []
        all_npcs = campaign.npcs.active + campaign.npcs.dormant if hasattr(campaign.npcs, 'active') else []
        for npc in all_npcs:
            npcs.append(NPCState(
                id=npc.id,
                name=npc.name,
                faction=npc.faction.value if npc.faction else None,
                disposition=npc.disposition.value,
                visible=npc.status == "active",
                interactable=npc.status == "active",
                last_interaction=npc.last_interaction.isoformat() if npc.last_interaction else None,
            ))
        
        # Build dormant threads
        threads = []
        for thread in campaign.dormant_threads:
            threads.append(DormantThread(
                id=thread.id,
                origin=thread.origin,
                trigger=thread.trigger_condition,
                consequence=thread.consequence,
                severity=thread.severity.value,
                created_session=thread.created_session,
            ))
        
        # Build map state
        map_state = self._build_map_state(campaign)
        
        # Get location
        location = LocationType.SAFE_HOUSE
        if campaign.session and campaign.session.location:
            try:
                location = LocationType(campaign.session.location.value)
            except ValueError:
                pass
        
        return GameStateResponse(
            ok=True,
            version=self._state_version,
            timestamp=datetime.now(),
            campaign=CampaignInfo(
                id=campaign.meta.id,
                name=campaign.meta.name,
                session=campaign.meta.session_count,
                phase=campaign.session.phase.value if campaign.session else None,
            ),
            character=character,
            location=location,
            factions=factions,
            npcs=npcs,
            threads=threads,
            map=map_state,
            paused=False,
        )
    
    def _build_map_state(self, campaign) -> MapState | None:
        """Build map state from campaign data."""
        if not campaign:
            return None
        
        # Get current region
        current_region = "rust_corridor"  # Default
        if campaign.session and hasattr(campaign.session, 'region'):
            current_region = campaign.session.region.value if campaign.session.region else current_region
        
        # Build region states from campaign map_state
        regions = {}
        if hasattr(campaign, 'map_state') and campaign.map_state:
            for region_enum, region_state in campaign.map_state.regions.items():
                region_id = region_enum.value if hasattr(region_enum, 'value') else str(region_enum)
                regions[region_id] = RegionState(
                    id=region_id,
                    name=region_id.replace("_", " ").title(),
                    connectivity=ConnectivityLevel(region_state.connectivity.value),
                )
        
        return MapState(
            current_region=current_region,
            regions=regions,
        )
    
    # -------------------------------------------------------------------------
    # Action Handling
    # -------------------------------------------------------------------------
    
    async def commit_action(self, request: ActionRequest) -> ActionResponse:
        """
        Commit a player action.
        
        This is the commitment gate. Frontend drives exploration;
        this endpoint resolves actions deterministically.
        """
        campaign = self.manager.current
        if not campaign:
            return ActionResponse(
                ok=False,
                action_id="",
                success=False,
                state_version=self._state_version,
                turn_number=self._turn_number,
                error="No campaign loaded",
            )
        
        # Check state version for conflict detection
        if request.state_version < self._state_version:
            return ActionResponse(
                ok=False,
                action_id="",
                success=False,
                state_version=self._state_version,
                turn_number=self._turn_number,
                error="State conflict: client state is stale",
            )
        
        action_id = str(uuid4())[:8]
        results = []
        cascade_notices = []
        narrative_hooks = []
        state_delta = {}
        
        try:
            # Route to appropriate handler based on action type
            if request.action_type == ActionType.MOVE:
                result = await self._handle_move(request)
            elif request.action_type == ActionType.INTERACT:
                result = await self._handle_interact(request)
            elif request.action_type == ActionType.TRAVEL:
                result = await self._handle_travel(request)
            elif request.action_type == ActionType.USE_ITEM:
                result = await self._handle_use_item(request)
            elif request.action_type == ActionType.WAIT:
                result = await self._handle_wait(request)
            else:
                result = ActionResult(
                    success=False,
                    message=f"Unknown action type: {request.action_type}",
                )
            
            results.append(result)
            
            # Process cascades if action succeeded
            if result.success:
                self._turn_number += 1
                new_version = self._increment_version()
                
                # Broadcast state update
                await self.connections.broadcast({
                    "type": "state_update",
                    "version": new_version,
                    "timestamp": datetime.now().isoformat(),
                    "changes": result.changes,
                    "source": "player",
                })
                
                # Save campaign
                self.manager.save_campaign()
            
            return ActionResponse(
                ok=True,
                action_id=action_id,
                success=result.success,
                state_version=self._state_version,
                turn_number=self._turn_number,
                results=results,
                cascade_notices=cascade_notices,
                state_delta=state_delta,
                narrative_hooks=narrative_hooks,
            )
            
        except Exception as e:
            return ActionResponse(
                ok=False,
                action_id=action_id,
                success=False,
                state_version=self._state_version,
                turn_number=self._turn_number,
                error=str(e),
            )
    
    async def _handle_move(self, request: ActionRequest) -> ActionResult:
        """Handle movement action within local map."""
        if not request.position:
            return ActionResult(success=False, message="No position specified")
        
        # TODO: Implement collision detection, patrol awareness
        # For now, just acknowledge the move
        return ActionResult(
            success=True,
            message=f"Moved to ({request.position.x}, {request.position.y})",
            changes={"position": {"x": request.position.x, "y": request.position.y}},
        )
    
    async def _handle_interact(self, request: ActionRequest) -> ActionResult:
        """Handle interaction with NPC or object."""
        if not request.target:
            return ActionResult(success=False, message="No target specified")
        
        campaign = self.manager.current
        
        # Check if target is an NPC
        npc = self.manager.get_npc(request.target)
        if npc:
            # Track NPC interaction
            self.manager.track_session_npc(request.target)
            return ActionResult(
                success=True,
                message=f"Interacting with {npc.name}",
                changes={"interaction": {"npc_id": request.target, "npc_name": npc.name}},
            )
        
        # Check if target is an object
        # TODO: Implement object interaction system
        return ActionResult(
            success=True,
            message=f"Interacting with {request.target}",
            changes={"interaction": {"target": request.target}},
        )
    
    async def _handle_travel(self, request: ActionRequest) -> ActionResult:
        """Handle travel between regions."""
        if not request.target:
            return ActionResult(success=False, message="No destination specified")
        
        orchestrator = self._ensure_orchestrator()
        if not orchestrator:
            return ActionResult(success=False, message="No campaign loaded")
        
        # Use turn orchestrator for travel resolution
        try:
            # Propose and commit travel
            proposal = orchestrator.propose_action({
                "type": "travel",
                "region_id": request.target,
            })
            
            if not proposal.get("feasible", False):
                return ActionResult(
                    success=False,
                    message=proposal.get("summary", "Travel not feasible"),
                )
            
            result = orchestrator.commit_action()
            return ActionResult(
                success=result.get("success", False),
                message=f"Traveled to {request.target}",
                changes={"region": request.target},
            )
        except Exception as e:
            return ActionResult(success=False, message=str(e))
    
    async def _handle_use_item(self, request: ActionRequest) -> ActionResult:
        """Handle using an inventory item."""
        if not request.target:
            return ActionResult(success=False, message="No item specified")
        
        campaign = self.manager.current
        if not campaign or not campaign.characters:
            return ActionResult(success=False, message="No character loaded")
        
        char = campaign.characters[0]
        
        # Find item in inventory
        item = None
        for gear in char.gear:
            if gear.id == request.target or gear.name.lower() == request.target.lower():
                item = gear
                break
        
        if not item:
            return ActionResult(success=False, message=f"Item not found: {request.target}")
        
        if item.used and item.single_use:
            return ActionResult(success=False, message=f"{item.name} has already been used")
        
        # Mark as used if single-use
        if item.single_use:
            item.used = True
        
        return ActionResult(
            success=True,
            message=f"Used {item.name}",
            changes={"item_used": {"id": item.id, "name": item.name}},
        )
    
    async def _handle_wait(self, request: ActionRequest) -> ActionResult:
        """Handle waiting/passing time."""
        # Advance game clock
        # TODO: Implement game clock system
        return ActionResult(
            success=True,
            message="Time passes...",
            changes={"time_advanced": True},
        )
    
    # -------------------------------------------------------------------------
    # Dialogue Handling
    # -------------------------------------------------------------------------
    
    async def crystallize_dialogue(self, request: DialogueRequest) -> DialogueResponse:
        """
        Crystallize meaning via LLM.
        
        Invoked only when pressure collapses into dialogue.
        Design Rule: Silence is a valid (and often preferred) outcome.
        """
        campaign = self.manager.current
        if not campaign:
            return DialogueResponse(
                ok=False,
                npc_id=request.npc_id,
                state_version=self._state_version,
                npc_response="",
                error="No campaign loaded",
            )
        
        # Get NPC
        npc = self.manager.get_npc(request.npc_id)
        if not npc:
            return DialogueResponse(
                ok=False,
                npc_id=request.npc_id,
                state_version=self._state_version,
                npc_response="",
                error=f"NPC not found: {request.npc_id}",
            )
        
        # Check if agent is available
        if not self.agent.is_available:
            return DialogueResponse(
                ok=False,
                npc_id=request.npc_id,
                state_version=self._state_version,
                npc_response="",
                error="LLM backend not available",
            )
        
        try:
            # Build dialogue prompt
            prompt = self._build_dialogue_prompt(npc, request)
            
            # Get LLM response
            response = self.agent.respond(prompt, [])
            
            # Parse response for dialogue options
            # TODO: Implement proper dialogue parsing
            options = [
                DialogueOption(id="1", text="Continue conversation", tone="neutral"),
                DialogueOption(id="2", text="Ask about something else", tone="neutral"),
                DialogueOption(id="3", text="End conversation", tone="neutral"),
            ]
            
            # Calculate social energy cost
            social_cost = 5  # Base cost
            
            # Update state version
            new_version = self._increment_version()
            
            return DialogueResponse(
                ok=True,
                npc_id=request.npc_id,
                state_version=new_version,
                npc_response=response,
                tone="neutral",
                options=options,
                social_energy_cost=social_cost,
            )
            
        except Exception as e:
            return DialogueResponse(
                ok=False,
                npc_id=request.npc_id,
                state_version=self._state_version,
                npc_response="",
                error=str(e),
            )
    
    def _build_dialogue_prompt(self, npc, request: DialogueRequest) -> str:
        """Build prompt for dialogue crystallization."""
        return f"""You are {npc.name}, a {npc.faction.value if npc.faction else 'independent'} character.
Disposition: {npc.disposition.value}

Context: {request.context}
Player intent: {request.player_intent}

Respond in character. Keep it brief and meaningful.
"""
    
    # -------------------------------------------------------------------------
    # Campaign Management
    # -------------------------------------------------------------------------
    
    def load_campaign(self, campaign_id: str) -> bool:
        """Load a campaign by ID."""
        try:
            result = self.manager.load_campaign(campaign_id)
            if result is None:
                return False
            self._state_version = 0
            self._turn_number = 0
            self._orchestrator = None
            return True
        except Exception:
            return False
    
    def save_campaign(self) -> bool:
        """Save current campaign."""
        try:
            self.manager.save_campaign()
            return True
        except Exception:
            return False
    
    def list_campaigns(self) -> list[dict]:
        """List available campaigns."""
        return [
            {
                "id": meta.id,
                "name": meta.name,
                "session": meta.session_count,
                "last_played": meta.last_played.isoformat() if meta.last_played else None,
            }
            for meta in self.manager.list_campaigns()
        ]


def create_app(
    campaigns_dir: Path | str = "campaigns",
    prompts_dir: Path | str | None = None,
    lore_dir: Path | str | None = None,
    wiki_dir: Path | str | None = None,
    backend: str = "auto",
    local_mode: bool = False,
    enable_realtime: bool = True,
) -> FastAPI:
    """
    Create FastAPI application for SENTINEL 2D.
    
    This is the main entry point for the API server.
    """
    
    # Initialize API backend
    api = SentinelAPI(
        campaigns_dir=campaigns_dir,
        prompts_dir=prompts_dir,
        lore_dir=lore_dir,
        wiki_dir=wiki_dir,
        backend=backend,
        local_mode=local_mode,
    )
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan handler."""
        # Startup
        yield
        # Shutdown - save any pending state
        if api.manager.current:
            api.save_campaign()
    
    app = FastAPI(
        title="SENTINEL 2D API",
        description="REST/WebSocket API for SENTINEL 2D exploration game",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # CORS middleware for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Store API instance for dependency injection
    app.state.api = api
    
    def get_api() -> SentinelAPI:
        return app.state.api
    
    # Include additional routes
    from .routes import router as additional_routes
    app.include_router(additional_routes, tags=["extended"])
    
    # Override route dependencies to use our API instance
    for route in additional_routes.routes:
        if hasattr(route, 'dependant'):
            for dep in route.dependant.dependencies:
                if dep.call.__name__ == '<lambda>':
                    dep.call = get_api
    
    # -------------------------------------------------------------------------
    # REST Endpoints
    # -------------------------------------------------------------------------
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"ok": True, "service": "sentinel-2d-api"}
    
    @app.get("/state", response_model=GameStateResponse)
    async def get_state(api: SentinelAPI = Depends(get_api)):
        """
        Get full game state snapshot.
        
        Frontend calls this for initial load and reconciliation.
        """
        return api.get_game_state()
    
    @app.post("/action", response_model=ActionResponse)
    async def commit_action(
        request: ActionRequest,
        api: SentinelAPI = Depends(get_api),
    ):
        """
        Commit a player action.
        
        This is the commitment gate. Frontend drives exploration;
        this endpoint resolves actions deterministically.
        """
        return await api.commit_action(request)
    
    @app.post("/dialogue", response_model=DialogueResponse)
    async def crystallize_dialogue(
        request: DialogueRequest,
        api: SentinelAPI = Depends(get_api),
    ):
        """
        Crystallize meaning via LLM.
        
        Invoked only when pressure collapses into dialogue.
        """
        return await api.crystallize_dialogue(request)
    
    @app.get("/campaigns")
    async def list_campaigns(api: SentinelAPI = Depends(get_api)):
        """List available campaigns."""
        return {"ok": True, "campaigns": api.list_campaigns()}
    
    @app.post("/campaigns/{campaign_id}/load")
    async def load_campaign(campaign_id: str, api: SentinelAPI = Depends(get_api)):
        """Load a campaign."""
        try:
            success = api.load_campaign(campaign_id)
            if success:
                return {"ok": True, "campaign_id": campaign_id}
            return {"ok": False, "error": f"Failed to load campaign: {campaign_id}"}
        except Exception as e:
            return {"ok": False, "error": f"Campaign not found: {campaign_id}"}
    
    @app.post("/campaigns/save")
    async def save_campaign(api: SentinelAPI = Depends(get_api)):
        """Save current campaign."""
        success = api.save_campaign()
        if success:
            return {"ok": True}
        return {"ok": False, "error": "Failed to save campaign"}
    
    # -------------------------------------------------------------------------
    # WebSocket Endpoint
    # -------------------------------------------------------------------------
    
    @app.websocket("/updates")
    async def websocket_updates(
        websocket: WebSocket,
        api: SentinelAPI = Depends(get_api),
    ):
        """
        Real-time state update stream.
        
        Frontend connects here for live updates.
        """
        await api.connections.connect(websocket)
        
        try:
            # Send initial state
            state = api.get_game_state()
            await websocket.send_json({
                "type": "initial_state",
                "state": state.model_dump(mode='json'),
            })
            
            # Keep connection alive and handle client messages
            while True:
                try:
                    data = await websocket.receive_json()
                    
                    # Handle ping/pong for keepalive
                    if data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    
                except WebSocketDisconnect:
                    break
                    
        finally:
            api.connections.disconnect(websocket)
    
    return app


# Entry point for running directly
if __name__ == "__main__":
    import uvicorn
    
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
