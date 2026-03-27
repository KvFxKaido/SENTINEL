from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, Field

"""Shared Enums and Utilities for SENTINEL."""

class Background(str, Enum):
    CARETAKER = "Caretaker"
    SURVIVOR = "Survivor"
    OPERATIVE = "Operative"
    TECHNICIAN = "Technician"
    PILGRIM = "Pilgrim"
    WITNESS = "Witness"
    GHOST = "Ghost"

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

class Location(str, Enum):
    SAFE_HOUSE = "safe_house"
    FIELD = "field"
    FACTION_HQ = "faction_hq"
    MARKET = "market"
    TRANSIT = "transit"

class Region(str, Enum):
    RUST_CORRIDOR = "rust_corridor"
    APPALACHIAN_HOLLOWS = "appalachian_hollows"
    GULF_PASSAGE = "gulf_passage"
    BREADBASKET = "breadbasket"
    NORTHERN_REACHES = "northern_reaches"
    PACIFIC_CORRIDOR = "pacific_corridor"
    DESERT_SPRAWL = "desert_sprawl"
    NORTHEAST_SCAR = "northeast_scar"
    SOVEREIGN_SOUTH = "sovereign_south"
    TEXAS_SPINE = "texas_spine"
    FROZEN_EDGE = "frozen_edge"

class RegionConnectivity(str, Enum):
    DISCONNECTED = "disconnected"
    AWARE = "aware"
    CONNECTED = "connected"
    EMBEDDED = "embedded"

class RequirementType(str, Enum):
    FACTION = "faction"
    VEHICLE = "vehicle"
    CONTACT = "contact"
    STORY = "story"
    HAZARD = "hazard"

class FavorType(str, Enum):
    RIDE = "ride"
    INTEL = "intel"
    GEAR_LOAN = "gear_loan"
    INTRODUCTION = "introduction"
    SAFE_HOUSE = "safe_house"

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

class Urgency(str, Enum):
    ROUTINE = "routine"
    PRESSING = "pressing"
    URGENT = "urgent"
    CRITICAL = "critical"

class LeverageWeight(str, Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"

class CampaignStatus(str, Enum):
    ACTIVE = "active"
    APPROACHING_END = "approaching_end"
    EPILOGUE = "epilogue"
    CONCLUDED = "concluded"

class ArcType(str, Enum):
    DIPLOMAT = "diplomat"
    PARTISAN = "partisan"
    BROKER = "broker"
    PACIFIST = "pacifist"
    PRAGMATIST = "pragmatist"
    SURVIVOR = "survivor"
    PROTECTOR = "protector"
    SEEKER = "seeker"
    AUTONOMIST = "autonomist"

class ArcStatus(str, Enum):
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DORMANT = "dormant"

def generate_id() -> str:
    return str(uuid4())[:8]
