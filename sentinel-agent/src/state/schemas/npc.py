from datetime import datetime
from typing import Literal, dict, list
from pydantic import BaseModel, Field
from .base import FactionName, Disposition, Standing, generate_id

class NPCAgenda(BaseModel):
    """What makes an NPC a person, not a prop."""
    wants: str
    fears: str
    leverage: str | None = None
    owes: str | None = None
    lie_to_self: str | None = None

class DispositionModifier(BaseModel):
    """How an NPC behaves at a specific disposition level."""
    tone: str
    reveals: list[str] = Field(default_factory=list)
    withholds: list[str] = Field(default_factory=list)
    tells: list[str] = Field(default_factory=list)

class MemoryTrigger(BaseModel):
    """NPC reaction to past events."""
    condition: str
    effect: str
    disposition_shift: int = 0
    one_shot: bool = True
    triggered: bool = False

class LeverageType(str, Enum):
    FINANCIAL = "financial"
    PERSONAL = "personal"
    PROFESSIONAL = "professional"
    FACTION = "faction"
    CRIMINAL = "criminal"

class PlayerLeverage(BaseModel):
    """Compromising information the player holds."""
    type: LeverageType
    description: str
    acquired_session: int
    used: bool = False
    burned: bool = False
    threat_made: bool = False
    deployed: bool = False

class NPCInteraction(BaseModel):
    """Record of a single interaction with an NPC."""
    session: int
    action: str
    outcome: str
    standing_change: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)

STANDING_SCORES = {"Hostile": -50, "Unfriendly": -25, "Neutral": 0, "Friendly": 25, "Allied": 50}
DISPOSITION_THRESHOLDS = [(-30, Disposition.HOSTILE), (-10, Disposition.WARY), (10, Disposition.NEUTRAL), (30, Disposition.WARM), (100, Disposition.LOYAL)]

def score_to_disposition(score: int) -> Disposition:
    for threshold, disposition in DISPOSITION_THRESHOLDS:
        if score <= threshold: return disposition
    return Disposition.LOYAL

class NPC(BaseModel):
    """Non-player character with memory and agenda."""
    id: str = Field(default_factory=generate_id)
    name: str
    faction: FactionName | None = None
    agenda: NPCAgenda
    disposition: Disposition = Disposition.NEUTRAL
    last_interaction: str = ""
    remembers: list[str] = Field(default_factory=list)
    personal_standing: int = 0
    interactions: list[NPCInteraction] = Field(default_factory=list)
    disposition_modifiers: dict[str, DispositionModifier] = Field(default_factory=dict)
    memory_triggers: list[MemoryTrigger] = Field(default_factory=list)
    player_leverage: PlayerLeverage | None = None
    coerced: bool = False
    resentment: bool = False

    def get_effective_disposition(self, faction_standing: Standing | None = None) -> Disposition:
        faction_score = STANDING_SCORES.get(faction_standing.value if faction_standing else "Neutral", 0)
        effective_score = (faction_score * 0.4) + (self.personal_standing * 0.6)
        return score_to_disposition(int(effective_score))

    def record_interaction(self, session, action, outcome, standing_change=0, tags=None):
        standing_change = max(-20, min(20, standing_change))
        interaction = NPCInteraction(session=session, action=action, outcome=outcome, standing_change=standing_change, tags=tags or [])
        self.interactions.append(interaction)
        self.personal_standing = max(-100, min(100, self.personal_standing + standing_change))
        self.last_interaction = f"S{session}: {action[:50]}"
        return interaction

    @property
    def can_reach_loyal(self) -> bool:
        return not self.coerced
