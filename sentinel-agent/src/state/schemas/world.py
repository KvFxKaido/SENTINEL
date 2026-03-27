from typing import ClassVar, dict, list
from pydantic import BaseModel, Field
from .base import ( 
    FactionName, 
    Standing, 
    Region, 
    RegionConnectivity, 
    RequirementType, 
    FavorType, 
    ThreadSeverity, 
    generate_id 
)

# Inter-faction relationships: positive = allies, negative = rivals
FACTION_RELATIONS: dict[tuple[str, str], int] = {
    ("Nexus", "Ghost Networks"): -50,
    ("Nexus", "Lattice"): 30,
    ("Nexus", "Witnesses"): -30,
    ("Ember Colonies", "Cultivators"): 40,
    ("Ember Colonies", "Wanderers"): 25,
    ("Ember Colonies", "Ghost Networks"): 20,
    ("Covenant", "Convergence"): -40,
    ("Covenant", "Witnesses"): 25,
    ("Convergence", "Architects"): 15,
    ("Lattice", "Cultivators"): 15,
    ("Lattice", "Steel Syndicate"): -15,
    ("Steel Syndicate", "Architects"): -20,
    ("Steel Syndicate", "Wanderers"): 10,
    ("Witnesses", "Architects"): 20,
    ("Ghost Networks", "Wanderers"): 15,
}

def get_faction_relation(faction1, faction2):
    if faction1 == faction2: return 0
    key1, key2 = (faction1.value, faction2.value), (faction2.value, faction1.value)
    return FACTION_RELATIONS.get(key1, FACTION_RELATIONS.get(key2, 0))

class FactionStanding(BaseModel):
    faction: FactionName
    standing: Standing = Standing.NEUTRAL
    STANDING_VALUES: ClassVar[dict[Standing, int]] = {
        Standing.HOSTILE: -50,
        Standing.UNFRIENDLY: -20,
        Standing.NEUTRAL: 0,
        Standing.FRIENDLY: 20,
        Standing.ALLIED: 50,
    }
    @property
    def numeric_value(self) -> int:
        return self.STANDING_VALUES.get(self.standing, 0)

    def shift(self, delta: int) -> Standing:
        standings = list(Standing)
        current_idx = standings.index(self.standing)
        new_idx = max(0, min(len(standings) - 1, current_idx + delta))
        self.standing = standings[new_idx]
        return self.standing

class FactionRegistry(BaseModel):
    nexus: FactionStanding = Field(default_factory=lambda: FactionStanding(faction=FactionName.NEXUS))
    ember_colonies: FactionStanding = Field(default_factory=lambda: FactionStanding(faction=FactionName.EMBER_COLONIES))
    lattice: FactionStanding = Field(default_factory=lambda: FactionStanding(faction=FactionName.LATTICE))
    convergence: FactionStanding = Field(default_factory=lambda: FactionStanding(faction=FactionName.CONVERGENCE))
    covenant: FactionStanding = Field(default_factory=lambda: FactionStanding(faction=FactionName.COVENANT))
    wanderers: FactionStanding = Field(default_factory=lambda: FactionStanding(faction=FactionName.WANDERERS))
    cultivators: FactionStanding = Field(default_factory=lambda: FactionStanding(faction=FactionName.CULTIVATORS))
    steel_syndicate: FactionStanding = Field(default_factory=lambda: FactionStanding(faction=FactionName.STEEL_SYNDICATE))
    witnesses: FactionStanding = Field(default_factory=lambda: FactionStanding(faction=FactionName.WITNESSES))
    architects: FactionStanding = Field(default_factory=lambda: FactionStanding(faction=FactionName.ARCHITECTS))
    ghost_networks: FactionStanding = Field(default_factory=lambda: FactionStanding(faction=FactionName.GHOST_NETWORKS))

    def get(self, faction: FactionName) -> FactionStanding:
        mapping = {
            FactionName.NEXUS: self.nexus, FactionName.EMBER_COLONIES: self.ember_colonies,
            FactionName.LATTICE: self.lattice, FactionName.CONVERGENCE: self.convergence,
            FactionName.COVENANT: self.covenant, FactionName.WANDERERS: self.wanderers,
            FactionName.CULTIVATORS: self.cultivators, FactionName.STEEL_SYNDICATE: self.steel_syndicate,
            FactionName.WITNESSES: self.witnesses, FactionName.ARCHITECTS: self.architects,
            FactionName.GHOST_NETWORKS: self.ghost_networks
        }
        return mapping[faction]

class RegionState(BaseModel):
    connectivity: RegionConnectivity = RegionConnectivity.DISCONNECTED
    first_aware_session: int | None = None
    first_visited_session: int | None = None
    embedded_session: int | None = None
    npcs_met: list[str] = Field(default_factory=list)
    threads_resolved: list[str] = Field(default_factory=list)
    significant_jobs: list[str] = Field(default_factory=list)
    notes: str | None = None
    secrets_found: list[str] = Field(default_factory=list)

class MapState(BaseModel):
    regions: dict[Region, RegionState] = Field(default_factory=dict)
    current_region: Region = Region.RUST_CORRIDOR

class FavorToken(BaseModel):
    npc_id: str
    npc_name: str
    favor_type: FavorType
    session_used: int
    standing_cost: int
    description: str = ""

class FavorTracker(BaseModel):
    tokens_per_session: int = 2
    tokens_used: list[FavorToken] = Field(default_factory=list)

class DormantThread(BaseModel):
    id: str = Field(default_factory=generate_id)
    origin: str 
    trigger_condition: str
    consequence: str
    severity: ThreadSeverity = ThreadSeverity.MODERATE
    created_session: int = 0
    trigger_keywords: list[str] = Field(default_factory=list)

class AvoidedSituation(BaseModel):
    id: str = Field(default_factory=generate_id)
    situation: str
    what_was_at_stake: str
    potential_consequence: str
    severity: ThreadSeverity = ThreadSeverity.MODERATE
    created_session: int = 0
    surfaced: bool = False
    surfaced_session: int | None = None
