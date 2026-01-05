"""
Pydantic models for SENTINEL game state.

All state is versioned for migration support.
Designed to serialize to JSON but structured like database tables.
"""

from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field
from uuid import uuid4


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------

class Background(str, Enum):
    CARETAKER = "Caretaker"      # Healer, protector, the one who keeps others alive
    SURVIVOR = "Survivor"        # Endured the worst, still standing
    OPERATIVE = "Operative"      # Trained for missions, intel, shadows
    TECHNICIAN = "Technician"    # Keeps the machines running
    PILGRIM = "Pilgrim"          # Seeker, wanderer, searching for meaning
    WITNESS = "Witness"          # Observer, recorder, keeper of truth
    GHOST = "Ghost"              # Erased, forgotten, never officially existed


class FactionName(str, Enum):
    NEXUS = "Nexus"
    EMBER_COLONIES = "Ember Colonies"
    LATTICE = "Lattice"
    CONVERGENCE = "Convergence"
    COVENANT = "Covenant"
    WANDERERS = "Wanderers"
    CULTIVATORS = "Cultivators"
    STEEL_SYNDICATE = "Steel Syndicate"
    WITNESSES = "Witnesses"
    ARCHITECTS = "Architects"
    GHOST_NETWORKS = "Ghost Networks"


class Standing(str, Enum):
    HOSTILE = "Hostile"
    UNFRIENDLY = "Unfriendly"
    NEUTRAL = "Neutral"
    FRIENDLY = "Friendly"
    ALLIED = "Allied"


class Disposition(str, Enum):
    HOSTILE = "hostile"
    WARY = "wary"
    NEUTRAL = "neutral"
    WARM = "warm"
    LOYAL = "loyal"


class MissionPhase(str, Enum):
    BRIEFING = "briefing"
    PLANNING = "planning"
    EXECUTION = "execution"
    RESOLUTION = "resolution"
    DEBRIEF = "debrief"
    BETWEEN = "between"


class MissionType(str, Enum):
    INVESTIGATION = "Investigation"
    RESCUE = "Rescue"
    DIPLOMACY = "Diplomacy"
    SABOTAGE = "Sabotage"
    ESCORT = "Escort"


class HistoryType(str, Enum):
    MISSION = "mission"
    HINGE = "hinge"
    FACTION_SHIFT = "faction_shift"
    CONSEQUENCE = "consequence"
    CANON = "canon"


class ThreadSeverity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"


class LeverageWeight(str, Enum):
    """How heavily a faction leans on this leverage."""
    LIGHT = "light"      # Subtle reminders, minor asks
    MEDIUM = "medium"    # Direct asks, moderate pressure
    HEAVY = "heavy"      # Ultimatums, significant consequences


# -----------------------------------------------------------------------------
# Core Models
# -----------------------------------------------------------------------------

def generate_id() -> str:
    return str(uuid4())[:8]


class GearItem(BaseModel):
    """Equipment carried by a character."""
    id: str = Field(default_factory=generate_id)
    name: str
    category: str  # Surveillance, Hacking, Infiltration, etc.
    description: str = ""
    cost: int = 0


class SocialEnergy(BaseModel):
    """Tracks emotional bandwidth for interaction."""
    name: str = "Pistachios"  # Customizable track name
    current: int = 100  # 0-100

    # What restores and drains this character specifically
    restorers: list[str] = Field(default_factory=list)
    # e.g., ["solo technical work", "quiet environments", "honest conversations"]
    drains: list[str] = Field(default_factory=list)
    # e.g., ["extended meetings", "ideological debates", "moral grandstanding"]

    @property
    def state(self) -> str:
        """Narrative band for current energy level."""
        if self.current >= 51:
            return "Centered"
        elif self.current >= 26:
            return "Frayed"
        elif self.current >= 1:
            return "Overloaded"
        else:
            return "Shutdown"

    @property
    def narrative_hint(self) -> str:
        """Flavor text for current state."""
        hints = {
            "Centered": "ready for anything",
            "Frayed": "edges showing",
            "Overloaded": "running on fumes",
            "Shutdown": "need space",
        }
        return hints.get(self.state, "")


class Leverage(BaseModel):
    """Tracks faction leverage from enhancements."""
    last_called: datetime | None = None
    pending_obligation: str | None = None
    compliance_count: int = 0
    resistance_count: int = 0
    # Escalation tracking
    weight: LeverageWeight = LeverageWeight.LIGHT
    hint_count: int = 0  # How many hints dropped this cycle
    last_hint_session: int | None = None  # Avoid hint spam


class Enhancement(BaseModel):
    """Faction-granted power with strings attached."""
    id: str = Field(default_factory=generate_id)
    name: str
    source: FactionName
    benefit: str
    cost: str
    leverage: Leverage = Field(default_factory=Leverage)
    # Tracking for leverage hints
    granted_session: int = 0
    leverage_keywords: list[str] = Field(default_factory=list)


class EstablishingIncident(BaseModel):
    """The moment that pulled a character into the story."""
    summary: str  # "I walked away from a corporate enhancement contract..."
    location: str = ""  # "Corporate installation, pre-collapse"
    costs: str = ""  # "Lost career, lost protection, gained autonomy"


class RefusedEnhancement(BaseModel):
    """Enhancement consciously rejected — refusal as meaningful choice."""
    id: str = Field(default_factory=generate_id)
    name: str  # What was offered
    source: FactionName  # Who offered
    benefit: str  # What it would have provided
    reason_refused: str  # Why they said no


class HingeMoment(BaseModel):
    """Irreversible choice that defines identity."""
    id: str = Field(default_factory=generate_id)
    session: int
    situation: str
    choice: str
    reasoning: str
    what_shifted: str = ""  # What changed because of this
    timestamp: datetime = Field(default_factory=datetime.now)


class Character(BaseModel):
    """Player character state."""
    id: str = Field(default_factory=generate_id)
    name: str
    callsign: str = ""  # Optional alias
    background: Background
    expertise: list[str] = Field(default_factory=list)

    # Optional identity fields
    pronouns: str = ""  # "she/her", "they/them", etc.
    age: str = ""  # Narrative age, not number ("young", "weathered", "40s")
    appearance: str = ""  # Visible scars, posture, clothing, devices
    survival_note: str = ""  # Why this person is still alive

    affiliation: Literal["aligned", "neutral"] = "neutral"
    aligned_faction: FactionName | None = None

    credits: int = 500
    gear: list[GearItem] = Field(default_factory=list)

    social_energy: SocialEnergy = Field(default_factory=SocialEnergy)
    establishing_incident: EstablishingIncident | None = None

    enhancements: list[Enhancement] = Field(default_factory=list)
    refused_enhancements: list[RefusedEnhancement] = Field(default_factory=list)
    hinge_history: list[HingeMoment] = Field(default_factory=list)

    def model_post_init(self, __context) -> None:
        """Set expertise based on background if not provided."""
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


class NPCAgenda(BaseModel):
    """What makes an NPC a person, not a prop."""
    wants: str  # "Protect her daughter's future"
    fears: str  # "Being seen as a collaborator"
    leverage: str | None = None  # What they have over the player
    owes: str | None = None  # What they owe the player
    lie_to_self: str | None = None  # "It's temporary. We'll give power back later."


class DispositionModifier(BaseModel):
    """How an NPC behaves at a specific disposition level."""
    tone: str  # "clipped and formal" / "warm but guarded"
    reveals: list[str] = Field(default_factory=list)  # What they'll share
    withholds: list[str] = Field(default_factory=list)  # What they hide
    tells: list[str] = Field(default_factory=list)  # Behavioral cues to notice


class MemoryTrigger(BaseModel):
    """NPC reaction to past events."""
    condition: str  # Tag like "helped_ember", "betrayed_lattice", "knows_secret"
    effect: str  # Description: "disposition shifts to wary", "mentions the debt"
    disposition_shift: int = 0  # -2 to +2, applied when triggered
    one_shot: bool = True  # Only fires once
    triggered: bool = False  # Has this already fired?


class NPC(BaseModel):
    """Non-player character with memory and agenda."""
    id: str = Field(default_factory=generate_id)
    name: str
    faction: FactionName | None = None

    agenda: NPCAgenda
    disposition: Disposition = Disposition.NEUTRAL
    last_interaction: str = ""

    remembers: list[str] = Field(default_factory=list)

    # Disposition-based behavior modifiers
    disposition_modifiers: dict[str, DispositionModifier] = Field(default_factory=dict)
    # Keys are disposition values: "hostile", "wary", "neutral", "warm", "loyal"

    # Memory triggers - react to tagged events
    memory_triggers: list[MemoryTrigger] = Field(default_factory=list)

    def get_current_modifier(self) -> DispositionModifier | None:
        """Get behavior modifier for current disposition.

        Delegates to rules.npc.get_disposition_modifier().
        """
        from ..rules.npc import get_disposition_modifier
        return get_disposition_modifier(self)

    def check_triggers(self, tags: list[str]) -> list[MemoryTrigger]:
        """Check which triggers fire for given tags.

        Delegates to rules.npc.check_triggers().
        Returns fired triggers.
        """
        from ..rules.npc import check_triggers
        return check_triggers(self, tags)


class FactionStanding(BaseModel):
    """Player's standing with a faction."""
    faction: FactionName
    standing: Standing = Standing.NEUTRAL

    def shift(self, delta: int) -> Standing:
        """Apply reputation shift and return new standing."""
        standings = list(Standing)
        current_idx = standings.index(self.standing)
        new_idx = max(0, min(len(standings) - 1, current_idx + delta))
        self.standing = standings[new_idx]
        return self.standing


class DormantThread(BaseModel):
    """Delayed consequence waiting to trigger."""
    id: str = Field(default_factory=generate_id)
    origin: str  # Which decision created this
    trigger_condition: str  # "When player returns to Sector 7"
    consequence: str  # What happens
    severity: ThreadSeverity = ThreadSeverity.MODERATE
    created_session: int = 0
    trigger_keywords: list[str] = Field(default_factory=list)  # Extracted for matching


class MissionBriefing(BaseModel):
    """Mission setup with explicit dilemma framing."""
    situation: str
    requestor: str
    competing_truths: list[str] = Field(default_factory=list)
    stakes: str


class SessionState(BaseModel):
    """Current mission/session state."""
    mission_id: str = Field(default_factory=generate_id)
    mission_title: str
    mission_type: MissionType

    phase: MissionPhase = MissionPhase.BRIEFING
    briefing: MissionBriefing

    active_npc_ids: list[str] = Field(default_factory=list)


class SessionReflection(BaseModel):
    """Player reflections at session end."""
    cost: str = ""  # "What did this cost you?"
    learned: str = ""  # "What did you learn?"
    would_refuse: str = ""  # "What would you refuse to do again?"


class MissionOutcome(BaseModel):
    """Structured mission result for history."""
    title: str
    what_we_tried: str
    result: str
    immediate_consequence: str
    reflections: SessionReflection | None = None


class FactionShiftRecord(BaseModel):
    """Structured faction change for history."""
    faction: FactionName
    from_standing: Standing
    to_standing: Standing
    cause: str


class HistoryEntry(BaseModel):
    """Unified history entry (chronicle + canon merged)."""
    id: str = Field(default_factory=generate_id)
    session: int
    type: HistoryType
    summary: str
    timestamp: datetime = Field(default_factory=datetime.now)

    # Optional structured data by type
    mission: MissionOutcome | None = None
    hinge: HingeMoment | None = None
    faction_shift: FactionShiftRecord | None = None

    # Marks entry as permanent world-change
    is_permanent: bool = False


class CampaignMeta(BaseModel):
    """Campaign metadata."""
    id: str = Field(default_factory=generate_id)
    name: str
    phase: Literal[1, 2, 3] = 1  # Pattern of Failures, Eyes Everywhere, Who Gets to Decide
    session_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class NPCRegistry(BaseModel):
    """NPCs indexed by active/dormant status."""
    active: list[NPC] = Field(default_factory=list)
    dormant: list[NPC] = Field(default_factory=list)

    def get(self, npc_id: str) -> NPC | None:
        """Find NPC by ID in either list."""
        for npc in self.active + self.dormant:
            if npc.id == npc_id:
                return npc
        return None

    def activate(self, npc_id: str) -> bool:
        """Move NPC from dormant to active."""
        for i, npc in enumerate(self.dormant):
            if npc.id == npc_id:
                self.active.append(self.dormant.pop(i))
                return True
        return False

    def deactivate(self, npc_id: str) -> bool:
        """Move NPC from active to dormant."""
        for i, npc in enumerate(self.active):
            if npc.id == npc_id:
                self.dormant.append(self.active.pop(i))
                return True
        return False


class FactionRegistry(BaseModel):
    """All faction standings."""
    nexus: FactionStanding = Field(
        default_factory=lambda: FactionStanding(faction=FactionName.NEXUS)
    )
    ember_colonies: FactionStanding = Field(
        default_factory=lambda: FactionStanding(faction=FactionName.EMBER_COLONIES)
    )
    lattice: FactionStanding = Field(
        default_factory=lambda: FactionStanding(faction=FactionName.LATTICE)
    )
    convergence: FactionStanding = Field(
        default_factory=lambda: FactionStanding(faction=FactionName.CONVERGENCE)
    )
    covenant: FactionStanding = Field(
        default_factory=lambda: FactionStanding(faction=FactionName.COVENANT)
    )
    wanderers: FactionStanding = Field(
        default_factory=lambda: FactionStanding(faction=FactionName.WANDERERS)
    )
    cultivators: FactionStanding = Field(
        default_factory=lambda: FactionStanding(faction=FactionName.CULTIVATORS)
    )
    steel_syndicate: FactionStanding = Field(
        default_factory=lambda: FactionStanding(faction=FactionName.STEEL_SYNDICATE)
    )
    witnesses: FactionStanding = Field(
        default_factory=lambda: FactionStanding(faction=FactionName.WITNESSES)
    )
    architects: FactionStanding = Field(
        default_factory=lambda: FactionStanding(faction=FactionName.ARCHITECTS)
    )
    ghost_networks: FactionStanding = Field(
        default_factory=lambda: FactionStanding(faction=FactionName.GHOST_NETWORKS)
    )

    def get(self, faction: FactionName) -> FactionStanding:
        """Get standing for a faction."""
        mapping = {
            FactionName.NEXUS: self.nexus,
            FactionName.EMBER_COLONIES: self.ember_colonies,
            FactionName.LATTICE: self.lattice,
            FactionName.CONVERGENCE: self.convergence,
            FactionName.COVENANT: self.covenant,
            FactionName.WANDERERS: self.wanderers,
            FactionName.CULTIVATORS: self.cultivators,
            FactionName.STEEL_SYNDICATE: self.steel_syndicate,
            FactionName.WITNESSES: self.witnesses,
            FactionName.ARCHITECTS: self.architects,
            FactionName.GHOST_NETWORKS: self.ghost_networks,
        }
        return mapping[faction]


class Campaign(BaseModel):
    """
    Complete campaign state.

    This is the root model that gets serialized to JSON.
    Versioned for migration support.
    """
    schema_version: str = "1.0.0"
    saved_at: datetime = Field(default_factory=datetime.now)

    meta: CampaignMeta
    characters: list[Character] = Field(default_factory=list)
    factions: FactionRegistry = Field(default_factory=FactionRegistry)
    npcs: NPCRegistry = Field(default_factory=NPCRegistry)
    history: list[HistoryEntry] = Field(default_factory=list)
    dormant_threads: list[DormantThread] = Field(default_factory=list)
    session: SessionState | None = None

    def save_checkpoint(self) -> None:
        """Update timestamp before save."""
        self.saved_at = datetime.now()
        self.meta.updated_at = datetime.now()
