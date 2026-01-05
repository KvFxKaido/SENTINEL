"""Import Cipher character from lore files into a campaign save."""

import sys
import os
from pathlib import Path

# Change to sentinel-agent dir and add to path as package
os.chdir(Path(__file__).parent.parent)
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.state.schema import (
    Campaign, CampaignMeta, Character, Background, SocialEnergy,
    EstablishingIncident, RefusedEnhancement, HingeMoment,
    FactionName, Standing, GearItem, HistoryEntry, HistoryType,
    MissionOutcome, FactionShiftRecord,
)
from src.state.store import JsonCampaignStore

def create_cipher_campaign() -> Campaign:
    """Build Cipher's campaign from lore documents."""

    # Character
    cipher = Character(
        name="Cipher",
        callsign="CIPHER",
        pronouns="they/them",
        age="late 20s–early 30s (uncertain)",
        appearance="Quiet posture, utilitarian clothing, subtle surgical traces near temples, keeps tech minimal and visible",
        background=Background.GHOST,
        survival_note="Knows when to disappear. Traded enhancement power for independence. Never stays anywhere long enough to become a target.",
        expertise=["Systems Analysis", "Infrastructure Assessment", "Stealth/Evasion"],

        social_energy=SocialEnergy(
            name="Pistachios",
            current=75,
            restorers=[
                "Solo technical work",
                "Quiet environments",
                "Tactical planning",
                "Honest one-on-one conversations",
                "Clear objectives",
            ],
            drains=[
                "Extended meetings",
                "Ideological debates",
                "Chaotic group dynamics",
                "Moral grandstanding",
                "Coercive negotiation",
            ],
        ),

        establishing_incident=EstablishingIncident(
            summary="I walked away from a corporate enhancement contract that would've made me unstoppable. They wanted neural monitoring rights. I chose vulnerability over control.",
            location="Corporate installation, pre-collapse",
            costs="Lost career, lost protection, gained autonomy",
        ),

        refused_enhancements=[
            RefusedEnhancement(
                name="Neural Optimization Suite",
                source=FactionName.CONVERGENCE,  # Corporate → closest is Convergence
                benefit="Dramatically increased processing, pattern recognition",
                reason_refused="Required neural monitoring & control — unacceptable",
            ),
            RefusedEnhancement(
                name="Syndicate Tactical Package",
                source=FactionName.STEEL_SYNDICATE,
                benefit="Enhanced threat detection, accelerated reflexes",
                reason_refused="Leverage strings too tight; values independence",
            ),
        ],

        hinge_history=[
            HingeMoment(
                session=1,
                situation="Harvest Point: Rogue AI using coercive tactics against infrastructure faction",
                choice="Condemned coercive AI tactics while validating infrastructure risks",
                reasoning="Right problem, wrong solution — nuance over ideology",
                what_shifted="Reputation for nuance; neither faction could fully predict Cipher anymore",
            ),
            HingeMoment(
                session=2,
                situation="RESET Crisis: Centralized vs distributed control of critical systems",
                choice="Framework Over Force — chose voluntary cooperation frameworks",
                reasoning="Voluntary systems preserve autonomy; force creates resentment",
                what_shifted="Became a framework architect; cooperation through choice, not coercion",
            ),
        ],

        gear=[
            GearItem(name="Encrypted laptop", category="Hacking", description="Custom, hardened"),
            GearItem(name="Tactical drone", category="Surveillance", description="Stealth coating + extended battery"),
            GearItem(name="Infiltration kit", category="Infiltration", description="Standard tools"),
            GearItem(name="Sidearm", category="Weapon", description="Rarely used"),
            GearItem(name="Pistachios", category="Personal", description="Tactical snack"),
        ],
    )

    # Create campaign
    campaign = Campaign(
        meta=CampaignMeta(
            name="Cipher's Chronicle",
            phase=1,
            session_count=3,
        ),
        characters=[cipher],
    )

    # Set faction standings
    standings = {
        FactionName.NEXUS: Standing.NEUTRAL,
        FactionName.EMBER_COLONIES: Standing.FRIENDLY,
        FactionName.LATTICE: Standing.NEUTRAL,
        FactionName.CONVERGENCE: Standing.NEUTRAL,
        FactionName.COVENANT: Standing.UNFRIENDLY,
        FactionName.WANDERERS: Standing.FRIENDLY,
        FactionName.CULTIVATORS: Standing.FRIENDLY,
        FactionName.STEEL_SYNDICATE: Standing.ALLIED,
        FactionName.WITNESSES: Standing.ALLIED,
        FactionName.ARCHITECTS: Standing.NEUTRAL,
        FactionName.GHOST_NETWORKS: Standing.FRIENDLY,
    }

    for faction, standing in standings.items():
        campaign.factions.get(faction).standing = standing

    # Add mission history
    campaign.history = [
        HistoryEntry(
            session=1,
            type=HistoryType.MISSION,
            summary="Harvest Point investigation: Rogue AI accountability framework established",
            mission=MissionOutcome(
                title="HP-03: Harvest Point",
                what_we_tried="Investigated rogue AI using coercive tactics",
                result="Complex resolution — AI surrendered",
                immediate_consequence="Accountability framework established",
            ),
        ),
        HistoryEntry(
            session=1,
            type=HistoryType.HINGE,
            summary="Right Problem, Wrong Solution — condemned tactics while validating concerns",
            is_permanent=True,
        ),
        HistoryEntry(
            session=2,
            type=HistoryType.MISSION,
            summary="WIT-07: Civilian extraction successful, earned Witnesses Token",
            mission=MissionOutcome(
                title="WIT-07: Supply Run",
                what_we_tried="Rescue and extraction negotiation",
                result="Civilian extraction successful",
                immediate_consequence="Witnesses Allied; neutrality reinforced",
            ),
        ),
        HistoryEntry(
            session=2,
            type=HistoryType.FACTION_SHIFT,
            summary="Witnesses shifted to Allied after rescue operation",
            faction_shift=FactionShiftRecord(
                faction=FactionName.WITNESSES,
                from_standing=Standing.FRIENDLY,
                to_standing=Standing.ALLIED,
                cause="Earned token through rescue and ethical transparency",
            ),
        ),
        HistoryEntry(
            session=3,
            type=HistoryType.MISSION,
            summary="RESET Response: Distributed protocol succeeds, cross-faction credibility",
            mission=MissionOutcome(
                title="RESET Protocol",
                what_we_tried="Establish distributed cooperation framework",
                result="Distributed protocol succeeds",
                immediate_consequence="Cross-faction credibility; rising expectations",
            ),
        ),
        HistoryEntry(
            session=3,
            type=HistoryType.HINGE,
            summary="Framework Over Force — voluntary cooperation over centralized control",
            is_permanent=True,
        ),
    ]

    return campaign


def main():
    """Create and save the Cipher campaign."""
    campaign = create_cipher_campaign()

    # Save to campaigns directory
    campaigns_dir = Path("campaigns")
    campaigns_dir.mkdir(exist_ok=True)

    store = JsonCampaignStore(campaigns_dir)
    store.save(campaign)

    char = campaign.characters[0]
    print(f"Created campaign: {campaign.meta.name}")
    print(f"  ID: {campaign.meta.id}")
    print(f"  Character: {char.name} ({char.background.value})")
    print(f"  Sessions: {campaign.meta.session_count}")
    print(f"  History entries: {len(campaign.history)}")
    print(f"  Hinge moments: {len(char.hinge_history)}")
    print(f"  Refused enhancements: {len(char.refused_enhancements)}")
    print(f"  Allied: Steel Syndicate, Witnesses")
    print(f"  Friendly: Ember Colonies, Wanderers, Cultivators, Ghost Networks")
    print(f"Saved to: campaigns/{campaign.meta.id}.json")


if __name__ == "__main__":
    main()
