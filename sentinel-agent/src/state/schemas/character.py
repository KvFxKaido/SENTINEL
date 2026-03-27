from datetime import datetime
from typing import Literal, dict, list
from pydantic import BaseModel, Field
from .base import Background, FactionName, ArcType, ArcStatus, LeverageWeight, generate_id

class GearItem(BaseModel):
    """Equipment carried by a character."""
    id: str = Field(default_factory=generate_id)
    name: str
    category: str
    description: str = ""
    cost: int = 0
    single_use: bool = False
    used: bool = False

class Vehicle(BaseModel):
    """Transport state."""
    id: str = Field(default_factory=generate_id)
    name: str
    type: str
    description: str = ""
    cost: int = 0
    terrain: list[str] = Field(default_factory=list)
    capacity: int = 1
    cargo: bool = False
    stealth: bool = False
    unlocks_tags: list[str] = Field(default_factory=list)
    fuel: int = 100
    condition: int = 100
    fuel_cost_per_trip: int = 10
    condition_loss_per_trip: int = 5

    @property
    def is_operational(self) -> bool:
        return self.fuel > 0 and self.condition > 20

class SocialEnergy(BaseModel):
    """Tracks emotional bandwidth."""
    name: str = "Pistachios"
    current: int = 100
    restorers: list[str] = Field(default_factory=list)
    drains: list[str] = Field(default_factory=list)

    @property
    def state(self) -> str:
        if self.current >= 51: return "Centered"
        if self.current >= 26: return "Frayed"
        if self.current >= 1: return "Overloaded"
        return "Shutdown"

class LeverageDemand(BaseModel):
    id: str = Field(default_factory=generate_id)
    faction: FactionName
    enhancement_id: str
    enhancement_name: str
    demand: str
    threat_basis: list[str] = Field(default_factory=list)
    deadline: str | None = None
    deadline_session: int | None = None
    consequences: list[str] = Field(default_factory=list)
    weight: LeverageWeight = LeverageWeight.MEDIUM

class Leverage(BaseModel):
    last_called: datetime | None = None
    pending_demand: LeverageDemand | None = None
    compliance_count: int = 0
    resistance_count: int = 0
    weight: LeverageWeight = LeverageWeight.LIGHT

class Enhancement(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    source: FactionName
    benefit: str
    cost: str
    leverage: Leverage = Field(default_factory=Leverage)

class EstablishingIncident(BaseModel):
    summary: str
    location: str = ""
    costs: str = ""

class RefusedEnhancement(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    source: FactionName
    benefit: str
    reason_refused: str

class HingeMoment(BaseModel):
    id: str = Field(default_factory=generate_id)
    session: int
    situation: str
    choice: str
    reasoning: str
    what_shifted: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)

class CharacterArc(BaseModel):
    id: str = Field(default_factory=generate_id)
    arc_type: ArcType
    title: str
    description: str
    status: ArcStatus = ArcStatus.SUGGESTED

class Character(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    callsign: str = ""
    background: Background
    expertise: list[str] = Field(default_factory=list)
    pronouns: str = ""
    age: str = ""
    appearance: str = ""
    survival_note: str = ""
    affiliation: Literal["aligned", "neutral"] = "neutral"
    aligned_faction: FactionName | None = None
    credits: int = 500
    gear: list[GearItem] = Field(default_factory=list)
    vehicles: list[Vehicle] = Field(default_factory=list)
    social_energy: SocialEnergy = Field(default_factory=SocialEnergy)
    establishing_incident: EstablishingIncident | None = None
    enhancements: list[Enhancement] = Field(default_factory=list)
    refused_enhancements: list[RefusedEnhancement] = Field(default_factory=list)
    hinge_history: list[HingeMoment] = Field(default_factory=list)
    arcs: list[CharacterArc] = Field(default_factory=list)

    def model_post_init(self, __context) -> None:
        if not self.expertise:
            expertise_map = {
                Background.CARETAKER: ["Triage", "Empathy", "Endurance"],
                Background.SURVIVOR: ["Scavenging", "Improvisation", "Threat Assessment"],
                Background.OPERATIVE: ["Systems", "Surveillance", "Stealth"],
                Background.TECHNICIAN: ["Repair", "Infrastructure", "Hacking"],
                Background.PILGRIM: ["Orientation", "Negotiation", "Lore"],
                Background.WITNESS: ["Observation", "Recording", "Reading People"],
                Background.GHOST: ["Evasion", "Forgery", "Disappearing"],
            }
            self.expertise = expertise_map.get(self.background, [])
