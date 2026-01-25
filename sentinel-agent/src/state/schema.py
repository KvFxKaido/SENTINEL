"""
Pydantic models for SENTINEL game state.

All state is versioned for migration support.
Designed to serialize to JSON but structured like database tables.
"""

from datetime import datetime
from enum import Enum
from typing import ClassVar, Literal
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


# Inter-faction relationships: positive = allies, negative = rivals
# Range: -50 (deep rivalry) to +50 (strong alliance)
# These relationships drive cascade effects when player helps/opposes a faction
FACTION_RELATIONS: dict[tuple[str, str], int] = {
    # Nexus relationships
    ("Nexus", "Ghost Networks"): -50,       # Deep rivalry: surveillance vs anonymity
    ("Nexus", "Lattice"): 30,               # Cooperation: both infrastructure-focused
    ("Nexus", "Witnesses"): -30,            # Tension: control vs truth

    # Ember Colonies relationships
    ("Ember Colonies", "Cultivators"): 40,  # Alliance: survival/sustainability
    ("Ember Colonies", "Wanderers"): 25,    # Mutual survival focus
    ("Ember Colonies", "Ghost Networks"): 20,  # Both distrust central authority

    # Covenant relationships
    ("Covenant", "Convergence"): -40,       # Ideological: ethics vs enhancement
    ("Covenant", "Witnesses"): 25,          # Both value truth/ethics

    # Convergence relationships
    ("Convergence", "Architects"): 15,      # Both tech-forward, build toward future

    # Lattice relationships
    ("Lattice", "Cultivators"): 15,         # Infrastructure supports farming
    ("Lattice", "Steel Syndicate"): -15,    # Competition over resources

    # Steel Syndicate relationships
    ("Steel Syndicate", "Architects"): -20, # Tension: profit vs legacy
    ("Steel Syndicate", "Wanderers"): 10,   # Trade partners

    # Witnesses relationships
    ("Witnesses", "Architects"): 20,        # Both value records/history

    # Ghost Networks relationships
    ("Ghost Networks", "Wanderers"): 15,    # Both value mobility/freedom
}


def get_faction_relation(faction1: FactionName, faction2: FactionName) -> int:
    """
    Get the relationship score between two factions.

    Returns score from -50 to +50, or 0 if no defined relationship.
    Handles bidirectional lookup (order doesn't matter).
    """
    if faction1 == faction2:
        return 0

    key1 = (faction1.value, faction2.value)
    key2 = (faction2.value, faction1.value)

    return FACTION_RELATIONS.get(key1, FACTION_RELATIONS.get(key2, 0))


def get_faction_allies(faction: FactionName, threshold: int = 20) -> list[FactionName]:
    """Get factions that are allies (relationship >= threshold)."""
    allies = []
    for other in FactionName:
        if other != faction:
            relation = get_faction_relation(faction, other)
            if relation >= threshold:
                allies.append(other)
    return allies


def get_faction_rivals(faction: FactionName, threshold: int = -20) -> list[FactionName]:
    """Get factions that are rivals (relationship <= threshold)."""
    rivals = []
    for other in FactionName:
        if other != faction:
            relation = get_faction_relation(faction, other)
            if relation <= threshold:
                rivals.append(other)
    return rivals


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


class Location(str, Enum):
    """Player character's current location. Gates available commands."""
    SAFE_HOUSE = "safe_house"      # Default between missions — full access
    FIELD = "field"                # During mission execution — tactical only
    FACTION_HQ = "faction_hq"      # At a faction's base — faction shop, consult
    MARKET = "market"              # Wanderer market — general goods
    TRANSIT = "transit"            # Traveling — limited actions


class Region(str, Enum):
    """Post-Collapse North American regions from geography.md."""
    RUST_CORRIDOR = "rust_corridor"           # Great Lakes - Lattice/Syndicate
    APPALACHIAN_HOLLOWS = "appalachian_hollows"  # Mountains - Ember/Cultivators
    GULF_PASSAGE = "gulf_passage"             # Gulf Coast - Wanderers/Ghost
    BREADBASKET = "breadbasket"               # Great Plains - Cultivators/Wanderers
    NORTHERN_REACHES = "northern_reaches"     # Former Canada - Covenant/Ember
    PACIFIC_CORRIDOR = "pacific_corridor"     # West Coast - Convergence/Architects
    DESERT_SPRAWL = "desert_sprawl"           # Southwest - Ghost/Syndicate
    NORTHEAST_SCAR = "northeast_scar"         # Boston-DC - Architects/Nexus
    SOVEREIGN_SOUTH = "sovereign_south"       # Deep South - Witnesses/Covenant
    TEXAS_SPINE = "texas_spine"               # Central TX - Syndicate/Lattice
    FROZEN_EDGE = "frozen_edge"               # Alaska/Yukon - Ember (isolated)


class FavorType(str, Enum):
    """Types of favors NPCs can provide."""
    RIDE = "ride"                             # Transport to a location/region
    INTEL = "intel"                           # Faction information
    GEAR_LOAN = "gear_loan"                   # Borrow equipment temporarily
    INTRODUCTION = "introduction"             # Connect to another NPC
    SAFE_HOUSE = "safe_house"                 # Temporary shelter in their territory


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


class ArcType(str, Enum):
    """Character arc types that emerge from play patterns."""
    DIPLOMAT = "diplomat"      # Consistent negotiation, conflict avoidance
    PARTISAN = "partisan"      # Faction loyalty, true believer
    BROKER = "broker"          # Information gathering, deals, trades
    PACIFIST = "pacifist"      # Violence avoidance, de-escalation
    PRAGMATIST = "pragmatist"  # Resource focus, practical choices
    SURVIVOR = "survivor"      # Self-preservation, trust issues
    PROTECTOR = "protector"    # Shields others, takes hits for allies
    SEEKER = "seeker"          # Truth-focused, uncovers secrets
    AUTONOMIST = "autonomist"  # Values independence, opposes coercion


class ArcStatus(str, Enum):
    """Status of a detected character arc."""
    SUGGESTED = "suggested"  # Detected, awaiting player response
    ACCEPTED = "accepted"    # Player embraced this arc
    REJECTED = "rejected"    # Player declined this arc
    DORMANT = "dormant"      # Was active but pattern faded


class LeverageWeight(str, Enum):
    """How heavily a faction leans on this leverage."""
    LIGHT = "light"      # Subtle reminders, minor asks
    MEDIUM = "medium"    # Direct asks, moderate pressure
    HEAVY = "heavy"      # Ultimatums, significant consequences


class Urgency(str, Enum):
    """Mission urgency tier — determines deadline and consequences."""
    ROUTINE = "routine"      # No deadline, opportunity passes quietly
    PRESSING = "pressing"    # 2 sessions, minor consequence if ignored
    URGENT = "urgent"        # 1 session, dormant thread created
    CRITICAL = "critical"    # This session only, immediate fallout


class CampaignStatus(str, Enum):
    """Campaign lifecycle status for endgame tracking."""
    ACTIVE = "active"                    # Normal play
    APPROACHING_END = "approaching_end"  # High readiness, suggestions surfacing
    EPILOGUE = "epilogue"                # Final session in progress
    CONCLUDED = "concluded"              # Campaign complete


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
    single_use: bool = False  # Consumed after one use (Trauma Kit, Encryption Breaker)
    used: bool = False  # Has this been expended? (reset between missions for non-single-use)


class Vehicle(BaseModel):
    """Transport that enables faster travel and unlocks certain jobs."""
    id: str = Field(default_factory=generate_id)
    name: str
    type: str                                 # "motorcycle", "truck", "boat", etc.
    description: str = ""
    cost: int = 0

    # Capabilities
    terrain: list[str] = Field(default_factory=list)  # ["road", "off-road", "water"]
    capacity: int = 1                         # Crew + passengers
    cargo: bool = False                       # Can carry cargo
    stealth: bool = False                     # Low-profile travel

    # Job unlocks
    unlocks_tags: list[str] = Field(default_factory=list)  # ["delivery", "extraction"]

    # Maintenance (0-100 scale)
    fuel: int = 100                           # Depletes on travel, refuel at shop
    condition: int = 100                      # Degrades on use, repair at shop
    fuel_cost_per_trip: int = 10              # Fuel used per region travel
    condition_loss_per_trip: int = 5          # Wear per region travel

    @property
    def is_operational(self) -> bool:
        """Vehicle needs fuel > 0 and condition > 20 to operate."""
        return self.fuel > 0 and self.condition > 20

    @property
    def status(self) -> str:
        """Human-readable status."""
        if self.condition <= 20:
            return "Broken Down"
        elif self.fuel <= 0:
            return "Out of Fuel"
        elif self.condition <= 40:
            return "Needs Repair"
        elif self.fuel <= 20:
            return "Low Fuel"
        else:
            return "Operational"


class FavorToken(BaseModel):
    """Tracks a single favor usage with an NPC."""
    npc_id: str
    npc_name: str
    favor_type: FavorType
    session_used: int
    standing_cost: int                        # How much standing was spent
    description: str = ""                     # What was requested


class FavorTracker(BaseModel):
    """Per-session favor limitations for the campaign."""
    tokens_per_session: int = 2               # Can call 2 favors per session
    tokens_used: list[FavorToken] = Field(default_factory=list)

    def tokens_remaining(self, session: int) -> int:
        """Count remaining favor tokens for this session."""
        used_this_session = len([t for t in self.tokens_used if t.session_used == session])
        return max(0, self.tokens_per_session - used_this_session)

    def can_call_favor(self, session: int) -> bool:
        """Check if player can call another favor this session."""
        return self.tokens_remaining(session) > 0

    def has_used_npc_this_session(self, npc_id: str, session: int) -> bool:
        """Check if this specific NPC has been called this session."""
        return any(
            t.npc_id == npc_id and t.session_used == session
            for t in self.tokens_used
        )

    def can_call_npc(self, npc_id: str, session: int) -> bool:
        """Check if player can call this specific NPC (tokens + per-NPC cooldown)."""
        return self.can_call_favor(session) and not self.has_used_npc_this_session(npc_id, session)


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


class LeverageDemand(BaseModel):
    """
    A faction's formal demand using leverage from an enhancement.

    Represents active pressure from a faction calling in a favor.
    The threat_basis covers both informational leverage ("we know about Sector 7")
    and functional leverage ("we can disable your neural interface").
    """
    id: str = Field(default_factory=generate_id)
    faction: FactionName
    enhancement_id: str
    enhancement_name: str  # Denormalized for display
    demand: str  # What they're asking
    threat_basis: list[str] = Field(default_factory=list)  # Why leverage works
    deadline: str | None = None  # Human-facing ("Before the convoy leaves")
    deadline_session: int | None = None  # Authoritative for overdue calc
    consequences: list[str] = Field(default_factory=list)  # What happens if ignored
    created_session: int = 0
    weight: LeverageWeight = LeverageWeight.MEDIUM


class Leverage(BaseModel):
    """Tracks faction leverage from enhancements."""
    last_called: datetime | None = None
    pending_obligation: str | None = None  # Legacy field, migrated to pending_demand
    pending_demand: LeverageDemand | None = None  # Rich demand object
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


class CharacterArc(BaseModel):
    """Emergent character arc detected from play patterns.

    Arcs are recognition of player behavior, not rails.
    Players can accept, reject, or ignore detected arcs.
    Multiple arcs can coexist.
    """
    id: str = Field(default_factory=generate_id)
    arc_type: ArcType
    title: str  # "The Reluctant Mediator", "True Believer"
    description: str  # What this arc means for the character

    # Detection info
    detected_session: int  # When first detected
    evidence: list[str] = Field(default_factory=list)  # Session refs supporting this
    strength: float = 0.5  # 0.0-1.0, how strong the pattern is

    # Status
    status: ArcStatus = ArcStatus.SUGGESTED

    # Effects when accepted (narrative prompts, not mechanics)
    effects: list[str] = Field(default_factory=list)
    # e.g., ["NPCs recognize you as a mediator", "Factions may request you broker deals"]

    # Tracking
    last_reinforced: int | None = None  # Last session that reinforced this
    times_reinforced: int = 0


# Arc detection patterns - keywords and behaviors that suggest each arc
ARC_PATTERNS: dict[ArcType, dict] = {
    ArcType.DIPLOMAT: {
        "keywords": ["negotiate", "talk", "convince", "persuade", "mediate", "broker", "peace", "agreement", "compromise"],
        "anti_keywords": ["attack", "fight", "kill", "destroy", "betray"],
        "title_templates": ["The Reluctant Mediator", "Voice of Reason", "The Bridge Builder"],
        "description": "Your character consistently chooses words over weapons, seeking common ground even in hostile situations.",
        "effects": [
            "NPCs may seek you out to broker disputes",
            "Factions might request mediation services",
            "Breaking from diplomacy carries extra narrative weight",
        ],
    },
    ArcType.PARTISAN: {
        "keywords": ["loyal", "faction", "serve", "believe", "cause", "mission", "duty"],
        "faction_focus": True,  # Looks for consistent faction loyalty
        "title_templates": ["True Believer", "The Faithful", "Devoted Agent"],
        "description": "Your character has shown unwavering loyalty to a faction, embracing their cause as their own.",
        "effects": [
            "Your faction recognizes your dedication",
            "Rival factions view you with suspicion",
            "Betrayal would be devastating to your identity",
        ],
    },
    ArcType.BROKER: {
        "keywords": ["information", "intel", "trade", "deal", "exchange", "secret", "learn", "discover", "know"],
        "title_templates": ["The One Who Knows", "Information Dealer", "The Connector"],
        "description": "Your character trades in secrets and connections, always seeking to know more than others.",
        "effects": [
            "NPCs may approach you with intel to trade",
            "You hear rumors others don't",
            "Knowledge can become a liability",
        ],
    },
    ArcType.PACIFIST: {
        "keywords": ["peaceful", "avoid", "de-escalate", "calm", "gentle", "protect", "save", "spare"],
        "anti_keywords": ["kill", "attack", "destroy", "violence", "weapon"],
        "title_templates": ["The Unarmed", "Peaceful Resistance", "The Gentle Hand"],
        "description": "Your character avoids violence, finding other solutions even when bloodshed seems inevitable.",
        "effects": [
            "Some see your restraint as wisdom",
            "Others see it as weakness to exploit",
            "Breaking your code would be a defining hinge moment",
        ],
    },
    ArcType.PRAGMATIST: {
        "keywords": ["practical", "resource", "prepare", "plan", "efficient", "useful", "value", "cost", "benefit"],
        "title_templates": ["The Prepared", "Cold Calculator", "The Practical One"],
        "description": "Your character focuses on what works, accumulating resources and making choices based on outcomes.",
        "effects": [
            "You're rarely caught unprepared",
            "Others may see you as cold or mercenary",
            "Emotional choices feel foreign",
        ],
    },
    ArcType.SURVIVOR: {
        "keywords": ["survive", "escape", "alone", "trust", "betray", "self", "safe", "risk"],
        "anti_keywords": ["sacrifice", "die for", "give everything"],
        "title_templates": ["Trust No One", "The Survivor", "Last One Standing"],
        "description": "Your character prioritizes self-preservation, keeping escape routes open and trust limited.",
        "effects": [
            "You're hard to pin down or trap",
            "Deep relationships are difficult to form",
            "Loyalty feels like a cage",
        ],
    },
    ArcType.PROTECTOR: {
        "keywords": ["protect", "shield", "defend", "save", "guard", "sacrifice", "take the hit", "cover"],
        "title_templates": ["The Shield", "Guardian", "First Into Danger"],
        "description": "Your character puts themselves between danger and others, taking hits so they don't have to.",
        "effects": [
            "Those you protect feel genuine loyalty",
            "Enemies may target you specifically",
            "Your own wellbeing becomes secondary",
        ],
    },
    ArcType.SEEKER: {
        "keywords": ["truth", "discover", "investigate", "uncover", "reveal", "understand", "why", "what really"],
        "title_templates": ["The Truth Seeker", "Digger", "The Questioner"],
        "description": "Your character is driven to uncover truth, questioning narratives and digging for what's hidden.",
        "effects": [
            "You notice inconsistencies others miss",
            "Some secrets are dangerous to know",
            "The truth isn't always liberating",
        ],
    },
    ArcType.AUTONOMIST: {
        # Core keywords (voluntary action, opposition to control)
        "keywords": ["voluntary", "cooperation", "choice", "framework", "coercion", "coercive", "force", "autonomy", "independence"],
        "title_templates": ["The Free Agent", "Framework Architect", "The Uncollared"],
        "description": "Your character values independence and opposes coercion, preferring systems that preserve choice.",
        "effects": [
            "Factions recognize you won't be controlled",
            "You're trusted to broker voluntary agreements",
            "Accepting constraints feels like betrayal of self",
        ],
    },
}


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
    vehicles: list[Vehicle] = Field(default_factory=list)

    social_energy: SocialEnergy = Field(default_factory=SocialEnergy)
    establishing_incident: EstablishingIncident | None = None

    enhancements: list[Enhancement] = Field(default_factory=list)
    refused_enhancements: list[RefusedEnhancement] = Field(default_factory=list)
    hinge_history: list[HingeMoment] = Field(default_factory=list)

    # Emergent character arcs detected from play patterns
    arcs: list[CharacterArc] = Field(default_factory=list)

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


class NPCInteraction(BaseModel):
    """Record of a single interaction with an NPC."""
    session: int
    action: str  # What the player did
    outcome: str  # How it resolved
    standing_change: int = 0  # How it affected personal standing (-20 to +20)
    timestamp: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)  # For searching/triggers


# Mapping faction Standing to numeric scores for disposition calculation
STANDING_SCORES: dict[str, int] = {
    "Hostile": -50,
    "Unfriendly": -25,
    "Neutral": 0,
    "Friendly": 25,
    "Allied": 50,
}

# Thresholds for converting effective score to Disposition
# Format: (max_score, disposition) - first match wins
DISPOSITION_THRESHOLDS: list[tuple[int, Disposition]] = [
    (-30, Disposition.HOSTILE),
    (-10, Disposition.WARY),
    (10, Disposition.NEUTRAL),
    (30, Disposition.WARM),
    (100, Disposition.LOYAL),
]


def score_to_disposition(score: int) -> Disposition:
    """Convert numeric score to Disposition enum."""
    for threshold, disposition in DISPOSITION_THRESHOLDS:
        if score <= threshold:
            return disposition
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

    # NEW: Personal standing independent of faction (-100 to +100)
    personal_standing: int = 0

    # NEW: Interaction history with this specific NPC
    interactions: list[NPCInteraction] = Field(default_factory=list)

    # Disposition-based behavior modifiers
    disposition_modifiers: dict[str, DispositionModifier] = Field(default_factory=dict)
    # Keys are disposition values: "hostile", "wary", "neutral", "warm", "loyal"

    # Memory triggers - react to tagged events
    memory_triggers: list[MemoryTrigger] = Field(default_factory=list)

    def get_effective_disposition(self, faction_standing: Standing | None = None) -> Disposition:
        """
        Calculate effective disposition from faction + personal standing.

        Personal standing weighs more heavily (60%) than faction (40%).
        This allows NPCs to have individual relationships despite faction politics.

        Args:
            faction_standing: Player's standing with NPC's faction (optional)

        Returns:
            Effective Disposition combining both factors
        """
        # Get faction score (0 if no faction or no standing provided)
        if faction_standing:
            faction_score = STANDING_SCORES.get(faction_standing.value, 0)
        else:
            faction_score = 0

        # Weight: 40% faction, 60% personal
        effective_score = (faction_score * 0.4) + (self.personal_standing * 0.6)

        return score_to_disposition(int(effective_score))

    def record_interaction(
        self,
        session: int,
        action: str,
        outcome: str,
        standing_change: int = 0,
        tags: list[str] | None = None,
    ) -> NPCInteraction:
        """
        Record an interaction and update personal standing.

        Args:
            session: Session number
            action: What the player did
            outcome: How it resolved
            standing_change: Change to personal standing (-20 to +20)
            tags: Tags for searching/triggers

        Returns:
            The created interaction record
        """
        # Clamp standing change
        standing_change = max(-20, min(20, standing_change))

        interaction = NPCInteraction(
            session=session,
            action=action,
            outcome=outcome,
            standing_change=standing_change,
            tags=tags or [],
        )
        self.interactions.append(interaction)

        # Update personal standing (clamped to -100 to +100)
        self.personal_standing = max(-100, min(100, self.personal_standing + standing_change))

        # Update last_interaction for quick reference
        self.last_interaction = f"S{session}: {action[:50]}"

        return interaction

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

    # Numeric mapping for standing levels (used by job system)
    STANDING_VALUES: ClassVar[dict[Standing, int]] = {
        Standing.HOSTILE: -50,
        Standing.UNFRIENDLY: -20,
        Standing.NEUTRAL: 0,
        Standing.FRIENDLY: 20,
        Standing.ALLIED: 50,
    }

    @property
    def numeric_value(self) -> int:
        """Get numeric standing value for job eligibility checks."""
        return self.STANDING_VALUES.get(self.standing, 0)

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


class AvoidedSituation(BaseModel):
    """
    Non-action as hinge — what they chose NOT to engage with.

    Avoidance is content. The world doesn't wait.
    """
    id: str = Field(default_factory=generate_id)
    situation: str  # What was presented that they avoided
    what_was_at_stake: str  # What they were avoiding (confrontation, decision, etc.)
    potential_consequence: str  # What may happen because they didn't act
    severity: ThreadSeverity = ThreadSeverity.MODERATE
    created_session: int = 0
    surfaced: bool = False  # Has the consequence already happened?
    surfaced_session: int | None = None  # When it came back


class MissionBriefing(BaseModel):
    """Mission setup with explicit dilemma framing."""
    situation: str
    requestor: str
    competing_truths: list[str] = Field(default_factory=list)
    stakes: str


class MissionOffer(BaseModel):
    """
    A time-sensitive mission opportunity.

    Unlike jobs (transactional work-for-hire), missions are story-driven
    opportunities that come with urgency and consequences for ignoring them.
    """
    id: str = Field(default_factory=generate_id)
    title: str
    situation: str  # What's happening
    requestor: str  # Who's asking (NPC name or faction)
    requestor_npc_id: str | None = None  # Link to NPC if applicable
    faction: FactionName | None = None  # Requesting faction

    urgency: Urgency = Urgency.PRESSING
    offered_session: int  # Session when offer was made
    deadline_session: int | None = None  # Session by which player must act (None = no deadline)

    stakes: str  # What's at stake
    consequence_if_ignored: str  # What happens if deadline passes

    # Tracking
    accepted: bool = False
    declined: bool = False
    expired: bool = False
    consequence_triggered: bool = False

    @property
    def sessions_remaining(self) -> int | None:
        """Sessions until deadline. None if no deadline."""
        if self.deadline_session is None:
            return None
        return self.deadline_session - self.offered_session

    def is_expired(self, current_session: int) -> bool:
        """Check if this offer has passed its deadline."""
        if self.deadline_session is None:
            return False
        return current_session > self.deadline_session


class SessionState(BaseModel):
    """Current mission/session state."""
    mission_id: str = Field(default_factory=generate_id)
    mission_title: str
    mission_type: MissionType

    phase: MissionPhase = MissionPhase.BRIEFING
    briefing: MissionBriefing

    active_npc_ids: list[str] = Field(default_factory=list)

    # Gear selected for this mission (subset of character.gear IDs)
    # Selected during planning phase, locked during execution
    loadout: list[str] = Field(default_factory=list)

    # Conversation history for mid-session persistence
    # Each dict: {"role": str, "content": str, "tool_calls": list[dict] | None, "tool_call_id": str | None}
    # Limited to last 50 messages to prevent JSON bloat (~25KB max)
    conversation_log: list[dict] = Field(default_factory=list)


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

    # Provenance tracking (links to MCP event or memvid frame)
    event_id: str | None = None


# -----------------------------------------------------------------------------
# Endgame System
# -----------------------------------------------------------------------------

class EndgameReadiness(BaseModel):
    """
    Tracks factors contributing to campaign conclusion readiness.

    The endgame system monitors accumulated play (hinges, arcs, faction extremes,
    thread pressure) to suggest when a campaign might be ready to conclude.
    Player always chooses when to end — this just provides visibility.
    """

    # Individual factor scores (0.0-1.0)
    hinge_score: float = 0.0       # Based on count + thematic convergence
    arc_score: float = 0.0         # Based on accepted arcs + reinforcement
    faction_score: float = 0.0     # Based on extremes (very high/low standings)
    thread_score: float = 0.0      # Based on dormant thread count + age

    # Player-stated goals (tracked from debrief fourth question)
    player_goals: list[str] = Field(default_factory=list)  # "What would 'enough' look like?"
    goals_met: list[str] = Field(default_factory=list)     # Goals detected as achieved

    @property
    def overall_score(self) -> float:
        """Weighted average of all factors (0.0-1.0)."""
        return (
            self.hinge_score * 0.30 +
            self.arc_score * 0.25 +
            self.faction_score * 0.20 +
            self.thread_score * 0.25
        )

    @property
    def readiness_level(self) -> str:
        """Human-readable readiness level."""
        score = self.overall_score
        if score >= 0.8:
            return "ready"           # "Your story has come full circle"
        elif score >= 0.6:
            return "approaching"     # "Threads are converging"
        elif score >= 0.4:
            return "developing"      # "Patterns are emerging"
        else:
            return "early"           # "Your story is still unfolding"

    @property
    def readiness_message(self) -> str:
        """Narrative description of readiness level."""
        level = self.readiness_level
        messages = {
            "ready": "Your story has come full circle. The threads are ready to be resolved.",
            "approaching": "Threads are converging. Your choices are beginning to demand resolution.",
            "developing": "Patterns are emerging. Your story is taking shape.",
            "early": "Your story is still unfolding. There is more to discover.",
        }
        return messages.get(level, messages["early"])


class CampaignMeta(BaseModel):
    """Campaign metadata."""
    id: str = Field(default_factory=generate_id)
    name: str
    phase: Literal[1, 2, 3] = 1  # Pattern of Failures, Eyes Everywhere, Who Gets to Decide
    session_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Endgame tracking
    status: CampaignStatus = CampaignStatus.ACTIVE
    endgame_readiness: EndgameReadiness = Field(default_factory=EndgameReadiness)
    epilogue_session: int | None = None  # Session number when epilogue began


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


# -----------------------------------------------------------------------------
# Event Queue (for MCP → Agent communication)
# -----------------------------------------------------------------------------


class PendingEvent(BaseModel):
    """
    An event from an external source (MCP) waiting to be processed by the agent.

    This solves state concurrency: MCP appends events to a queue file,
    agent processes them on startup. No direct state modification by MCP.
    """

    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    timestamp: datetime = Field(default_factory=datetime.now)
    source: Literal["mcp", "external"] = "mcp"
    event_type: str  # e.g., "faction_event", "npc_update"
    campaign_id: str  # Which campaign this affects
    payload: dict = Field(default_factory=dict)  # Event-specific data
    processed: bool = False  # Marked true after agent processes it


class EventQueue(BaseModel):
    """
    Queue of pending events from external sources.

    Stored in a separate file (pending_events.json) to avoid
    conflicts with campaign state files.
    """

    events: list[PendingEvent] = Field(default_factory=list)
    last_processed: datetime | None = None

    def append(self, event: PendingEvent) -> None:
        """Add an event to the queue."""
        self.events.append(event)

    def get_pending(self, campaign_id: str | None = None) -> list[PendingEvent]:
        """Get unprocessed events, optionally filtered by campaign."""
        pending = [e for e in self.events if not e.processed]
        if campaign_id:
            pending = [e for e in pending if e.campaign_id == campaign_id]
        return pending

    def mark_processed(self, event_id: str) -> bool:
        """Mark an event as processed."""
        for event in self.events:
            if event.id == event_id:
                event.processed = True
                return True
        return False

    def clear_processed(self) -> int:
        """Remove all processed events. Returns count removed."""
        original = len(self.events)
        self.events = [e for e in self.events if not e.processed]
        return original - len(self.events)


# -----------------------------------------------------------------------------
# Job System
# -----------------------------------------------------------------------------

class JobStatus(str, Enum):
    """Status of a job in the player's active list."""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class JobTemplate(BaseModel):
    """
    Template for a faction job, stored in JSON.

    Templates define the structure and rewards. When accepted,
    the LLM generates a full narrative briefing.
    """
    id: str
    faction: FactionName
    title: str
    type: MissionType
    description: str                    # Brief premise (1-2 sentences)
    objectives: list[str] = Field(default_factory=list)  # What success looks like
    reward_credits: int = 0
    reward_standing: int = 1            # Standing gain with faction
    opposing_factions: list[FactionName] = Field(default_factory=list)  # Who gets angry
    opposing_penalty: int = 1           # Standing loss with opposing
    time_estimate: str = "1 session"    # "1 session", "2-3 sessions"
    tags: list[str] = Field(default_factory=list)  # For filtering: ["stealth", "combat", "social"]
    min_standing: int = -50             # Minimum standing to see this job

    # Geography and vehicle requirements (optional)
    region: Region | None = None                     # Where this job takes place
    requires_vehicle: bool = False                   # Needs any vehicle
    requires_vehicle_type: str | None = None         # Specific type: "motorcycle", "truck", etc.
    requires_vehicle_tags: list[str] = Field(default_factory=list)  # ["cargo", "stealth"]

    # Buy-in (optional) — credits required to accept job (non-refundable)
    buy_in: int | None = None


class ActiveJob(BaseModel):
    """A job the player has accepted."""
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    template_id: str
    title: str                          # May be LLM-customized
    faction: FactionName
    briefing: str = ""                  # LLM-generated full briefing
    objectives: list[str] = Field(default_factory=list)
    reward_credits: int = 0
    reward_standing: int = 1
    opposing_factions: list[FactionName] = Field(default_factory=list)
    opposing_penalty: int = 1
    accepted_session: int = 0
    due_session: int | None = None      # Deadline (session number)
    status: JobStatus = JobStatus.ACTIVE

    # Geography (copied from template when accepted)
    region: Region | None = None        # Where the job takes place

    # Buy-in (copied from template — tracks what was paid)
    buy_in: int | None = None           # Non-refundable on failure/abandon


class JobBoard(BaseModel):
    """
    Available and active jobs for the campaign.

    The job board refreshes each session with new offerings
    based on faction standings and location.
    """
    available: list[str] = Field(default_factory=list)  # Template IDs currently offered
    active: list[ActiveJob] = Field(default_factory=list)
    completed: list[str] = Field(default_factory=list)  # Template IDs (for history)
    failed: list[str] = Field(default_factory=list)     # Template IDs that were failed/abandoned
    last_refresh_session: int = 0       # Session when board was last refreshed


class CampaignSnapshot(BaseModel):
    """Snapshot of campaign state for session bridging."""
    timestamp: datetime = Field(default_factory=datetime.now)
    session: int
    factions: dict[FactionName, Standing] = Field(default_factory=dict)
    # Store minimal NPC data: id -> (disposition, personal_standing)
    npc_states: dict[str, dict] = Field(default_factory=dict)
    # Threads: id -> severity
    threads: dict[str, ThreadSeverity] = Field(default_factory=dict)


class Campaign(BaseModel):
    """
    Complete campaign state.

    This is the root model that gets serialized to JSON.
    Versioned for migration support.

    Note: _persisted tracks whether this campaign has been explicitly saved.
    Campaigns exist in-memory by default and only write to disk on /save.
    """
    schema_version: str = "1.7.0"  # Added conversation_log for mid-session persistence
    saved_at: datetime = Field(default_factory=datetime.now)

    # Internal state - not serialized to JSON
    # Tracks whether campaign has been explicitly saved to disk
    persisted_: bool = Field(default=False, exclude=True, alias="_persisted")

    meta: CampaignMeta
    characters: list[Character] = Field(default_factory=list)
    factions: FactionRegistry = Field(default_factory=FactionRegistry)
    npcs: NPCRegistry = Field(default_factory=NPCRegistry)
    history: list[HistoryEntry] = Field(default_factory=list)
    dormant_threads: list[DormantThread] = Field(default_factory=list)
    avoided_situations: list[AvoidedSituation] = Field(default_factory=list)
    session: SessionState | None = None

    # Location tracking — gates available commands
    location: Location = Location.SAFE_HOUSE
    location_faction: FactionName | None = None  # If at a faction HQ, which one

    # Region tracking — geography from lore
    region: Region = Region.RUST_CORRIDOR  # Starting region

    # Job board — available and active jobs
    jobs: JobBoard = Field(default_factory=JobBoard)

    # Favor tracking — NPC favor usage per session
    favor_tracker: FavorTracker = Field(default_factory=FavorTracker)

    # Mission offers — time-sensitive story opportunities
    mission_offers: list[MissionOffer] = Field(default_factory=list)

    # Session Bridging
    last_session_snapshot: CampaignSnapshot | None = None

    def save_checkpoint(self) -> None:
        """Update timestamp before save."""
        self.saved_at = datetime.now()
        self.meta.updated_at = datetime.now()
