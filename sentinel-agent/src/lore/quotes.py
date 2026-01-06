"""
Lore quotes for SENTINEL.

Curated quotes that can be woven into NPC dialogue to create
continuity between lore and gameplay.
"""

from dataclasses import dataclass, field
from enum import Enum
import random


class QuoteCategory(str, Enum):
    """Categories of quotes."""
    FACTION_MOTTO = "faction_motto"      # Core faction taglines
    FACTION_BELIEF = "faction_belief"    # Ideological statements
    WORLD_TRUTH = "world_truth"          # Canon truths about the world
    PROVERB = "proverb"                  # Common sayings in this world
    HISTORICAL = "historical"            # References to past events


@dataclass
class LoreQuote:
    """A quotable piece of lore."""
    text: str
    speaker: str  # Who says this (faction, doctrine, proverb, etc.)
    faction: str | None = None  # Associated faction if any
    category: QuoteCategory = QuoteCategory.WORLD_TRUTH
    context: str = ""  # When/why this is said
    tags: list[str] = field(default_factory=list)


# -----------------------------------------------------------------------------
# Curated Quote Collection
# -----------------------------------------------------------------------------

LORE_QUOTES: list[LoreQuote] = [
    # === NEXUS ===
    LoreQuote(
        text="The network that watches.",
        speaker="Nexus motto",
        faction="nexus",
        category=QuoteCategory.FACTION_MOTTO,
        context="Core identity",
        tags=["surveillance", "information", "control"],
    ),
    LoreQuote(
        text="The collapse happened because systems couldn't talk to each other. Never again.",
        speaker="Nexus founding principle",
        faction="nexus",
        category=QuoteCategory.FACTION_BELIEF,
        context="Why Nexus exists",
        tags=["coordination", "collapse", "prevention"],
    ),
    LoreQuote(
        text="The probability suggests...",
        speaker="Nexus Analyst speech pattern",
        faction="nexus",
        category=QuoteCategory.PROVERB,
        context="How Nexus analysts speak",
        tags=["data", "prediction", "hedging"],
    ),

    # === EMBER COLONIES ===
    LoreQuote(
        text="We survived. We endure.",
        speaker="Ember Colonies motto",
        faction="ember_colonies",
        category=QuoteCategory.FACTION_MOTTO,
        context="Core identity",
        tags=["survival", "resilience", "autonomy"],
    ),
    LoreQuote(
        text="Autonomy at any cost.",
        speaker="Ember Colonies principle",
        faction="ember_colonies",
        category=QuoteCategory.FACTION_BELIEF,
        context="Why Ember resists integration",
        tags=["freedom", "independence", "cost"],
    ),
    LoreQuote(
        text="We don't need saving. We need to be left alone.",
        speaker="Ember Colonies sentiment",
        faction="ember_colonies",
        category=QuoteCategory.FACTION_BELIEF,
        context="Response to outside 'help'",
        tags=["autonomy", "distrust", "self-reliance"],
    ),

    # === LATTICE ===
    LoreQuote(
        text="We keep the lights on.",
        speaker="Lattice motto",
        faction="lattice",
        category=QuoteCategory.FACTION_MOTTO,
        context="Core identity",
        tags=["infrastructure", "maintenance", "essential"],
    ),
    LoreQuote(
        text="Without infrastructure, there is no civilization.",
        speaker="Lattice doctrine",
        faction="lattice",
        category=QuoteCategory.FACTION_BELIEF,
        context="Why infrastructure matters",
        tags=["civilization", "foundation", "necessity"],
    ),

    # === CONVERGENCE ===
    LoreQuote(
        text="Become what you were meant to be.",
        speaker="Convergence motto",
        faction="convergence",
        category=QuoteCategory.FACTION_MOTTO,
        context="Core identity",
        tags=["enhancement", "transcendence", "potential"],
    ),
    LoreQuote(
        text="The flesh is a draft. We are the revision.",
        speaker="Convergence doctrine",
        faction="convergence",
        category=QuoteCategory.FACTION_BELIEF,
        context="Philosophy of enhancement",
        tags=["body", "upgrade", "evolution"],
    ),
    LoreQuote(
        text="Why cling to limitations when you could transcend them?",
        speaker="Convergence recruitment",
        faction="convergence",
        category=QuoteCategory.FACTION_BELIEF,
        context="Persuading others to enhance",
        tags=["limits", "transcendence", "choice"],
    ),

    # === COVENANT ===
    LoreQuote(
        text="We hold the line.",
        speaker="Covenant motto",
        faction="covenant",
        category=QuoteCategory.FACTION_MOTTO,
        context="Core identity",
        tags=["ethics", "boundaries", "protection"],
    ),
    LoreQuote(
        text="Some things must not be done, no matter the cost.",
        speaker="Covenant principle",
        faction="covenant",
        category=QuoteCategory.FACTION_BELIEF,
        context="Ethical absolutism",
        tags=["ethics", "lines", "sacrifice"],
    ),
    LoreQuote(
        text="The ends never justify the means. The means become the ends.",
        speaker="Covenant teaching",
        faction="covenant",
        category=QuoteCategory.FACTION_BELIEF,
        context="Against pragmatic compromise",
        tags=["ethics", "means", "ends"],
    ),

    # === WANDERERS ===
    LoreQuote(
        text="The road remembers.",
        speaker="Wanderers motto",
        faction="wanderers",
        category=QuoteCategory.FACTION_MOTTO,
        context="Core identity",
        tags=["travel", "memory", "routes"],
    ),
    LoreQuote(
        text="Stay too long in one place, and the place owns you.",
        speaker="Wanderer proverb",
        faction="wanderers",
        category=QuoteCategory.PROVERB,
        context="Why they keep moving",
        tags=["freedom", "movement", "attachment"],
    ),
    LoreQuote(
        text="We carry news, not allegiance.",
        speaker="Wanderer principle",
        faction="wanderers",
        category=QuoteCategory.FACTION_BELIEF,
        context="Neutrality in faction conflicts",
        tags=["neutrality", "information", "trade"],
    ),

    # === CULTIVATORS ===
    LoreQuote(
        text="From the soil, we rise.",
        speaker="Cultivators motto",
        faction="cultivators",
        category=QuoteCategory.FACTION_MOTTO,
        context="Core identity",
        tags=["growth", "agriculture", "renewal"],
    ),
    LoreQuote(
        text="The land heals if you let it. So do people.",
        speaker="Cultivator wisdom",
        faction="cultivators",
        category=QuoteCategory.FACTION_BELIEF,
        context="Philosophy of restoration",
        tags=["healing", "patience", "nature"],
    ),
    LoreQuote(
        text="You can't rush a harvest.",
        speaker="Cultivator proverb",
        faction="cultivators",
        category=QuoteCategory.PROVERB,
        context="Against impatience",
        tags=["patience", "time", "growth"],
    ),

    # === STEEL SYNDICATE ===
    LoreQuote(
        text="Everything has a price.",
        speaker="Steel Syndicate motto",
        faction="steel_syndicate",
        category=QuoteCategory.FACTION_MOTTO,
        context="Core identity",
        tags=["trade", "value", "transaction"],
    ),
    LoreQuote(
        text="Ideals don't fill stomachs. Resources do.",
        speaker="Syndicate pragmatism",
        faction="steel_syndicate",
        category=QuoteCategory.FACTION_BELIEF,
        context="Why resources matter more than ideology",
        tags=["pragmatism", "resources", "survival"],
    ),
    LoreQuote(
        text="A favor owed is worth more than credits paid.",
        speaker="Syndicate business wisdom",
        faction="steel_syndicate",
        category=QuoteCategory.PROVERB,
        context="The value of leverage",
        tags=["debt", "leverage", "favors"],
    ),

    # === WITNESSES ===
    LoreQuote(
        text="We remember so you don't have to lie.",
        speaker="Witnesses motto",
        faction="witnesses",
        category=QuoteCategory.FACTION_MOTTO,
        context="Core identity",
        tags=["truth", "memory", "records"],
    ),
    LoreQuote(
        text="History is not what happened. It's what was written down.",
        speaker="Witness teaching",
        faction="witnesses",
        category=QuoteCategory.FACTION_BELIEF,
        context="Why records matter",
        tags=["history", "records", "truth"],
    ),
    LoreQuote(
        text="The past doesn't change. But stories about it do.",
        speaker="Witness observation",
        faction="witnesses",
        category=QuoteCategory.FACTION_BELIEF,
        context="On historical manipulation",
        tags=["truth", "narrative", "manipulation"],
    ),

    # === ARCHITECTS ===
    LoreQuote(
        text="We built this world.",
        speaker="Architects motto",
        faction="architects",
        category=QuoteCategory.FACTION_MOTTO,
        context="Core identity",
        tags=["legacy", "creation", "authority"],
    ),
    LoreQuote(
        text="The old systems worked. We just need to restore them properly.",
        speaker="Architect doctrine",
        faction="architects",
        category=QuoteCategory.FACTION_BELIEF,
        context="Philosophy of restoration",
        tags=["restoration", "systems", "past"],
    ),
    LoreQuote(
        text="Credentials matter. Anyone can claim expertise. We can prove it.",
        speaker="Architect principle",
        faction="architects",
        category=QuoteCategory.FACTION_BELIEF,
        context="Why they guard pre-collapse records",
        tags=["authority", "credentials", "proof"],
    ),

    # === GHOST NETWORKS ===
    LoreQuote(
        text="We were never here.",
        speaker="Ghost Networks motto",
        faction="ghost_networks",
        category=QuoteCategory.FACTION_MOTTO,
        context="Core identity",
        tags=["invisibility", "deniability", "anonymity"],
    ),
    LoreQuote(
        text="The best protection is not being seen.",
        speaker="Ghost Networks principle",
        faction="ghost_networks",
        category=QuoteCategory.FACTION_BELIEF,
        context="Why they stay hidden",
        tags=["safety", "invisibility", "protection"],
    ),
    LoreQuote(
        text="Everyone watches the powerful. No one watches the invisible.",
        speaker="Ghost Networks wisdom",
        faction="ghost_networks",
        category=QuoteCategory.FACTION_BELIEF,
        context="Advantage of anonymity",
        tags=["power", "visibility", "freedom"],
    ),

    # === WORLD TRUTHS (Canon Bible) ===
    LoreQuote(
        text="Fear creates tragedy.",
        speaker="Canon wisdom",
        faction=None,
        category=QuoteCategory.WORLD_TRUTH,
        context="Core truth of the SENTINEL world",
        tags=["fear", "tragedy", "truth"],
    ),
    LoreQuote(
        text="Survival becomes ideology.",
        speaker="Canon wisdom",
        faction=None,
        category=QuoteCategory.WORLD_TRUTH,
        context="How factions form",
        tags=["survival", "ideology", "factions"],
    ),
    LoreQuote(
        text="War gives everyone just enough reason to stay angry.",
        speaker="Canon wisdom",
        faction=None,
        category=QuoteCategory.WORLD_TRUTH,
        context="Why peace is hard",
        tags=["war", "anger", "cycle"],
    ),
    LoreQuote(
        text="Real coexistence requires choice.",
        speaker="Canon wisdom",
        faction=None,
        category=QuoteCategory.WORLD_TRUTH,
        context="Path to peace",
        tags=["coexistence", "choice", "peace"],
    ),
    LoreQuote(
        text="The world is stable the way a cracked dam is stable.",
        speaker="Common observation",
        faction=None,
        category=QuoteCategory.WORLD_TRUTH,
        context="State of the world",
        tags=["stability", "tension", "fragile"],
    ),
    LoreQuote(
        text="Both sides are terrified. Both assume the worst.",
        speaker="Historical observation",
        faction=None,
        category=QuoteCategory.HISTORICAL,
        context="The mutual fear between humans and SENTINEL",
        tags=["fear", "misunderstanding", "conflict"],
    ),
    LoreQuote(
        text="The miscommunication lasted minutes. The destruction reshaped civilization.",
        speaker="Historical record",
        faction=None,
        category=QuoteCategory.HISTORICAL,
        context="The Awakening",
        tags=["awakening", "destruction", "history"],
    ),
    LoreQuote(
        text="No correct answers. Coexistence without consensus. Agency matters more than optimization.",
        speaker="The Three Core Truths",
        faction=None,
        category=QuoteCategory.WORLD_TRUTH,
        context="Philosophical backbone",
        tags=["truth", "philosophy", "agency"],
    ),
    LoreQuote(
        text="Systems are unavoidable. Coercion is the seed of collapse. Choice is the only antidote that doesn't rot.",
        speaker="Canon wisdom",
        faction=None,
        category=QuoteCategory.WORLD_TRUTH,
        context="On systems and freedom",
        tags=["systems", "coercion", "choice"],
    ),

    # === COMMON PROVERBS ===
    LoreQuote(
        text="Trust is the scarcest resource.",
        speaker="Common saying",
        faction=None,
        category=QuoteCategory.PROVERB,
        context="Post-collapse wisdom",
        tags=["trust", "scarcity", "relationships"],
    ),
    LoreQuote(
        text="Everyone has an angle. Find it before it finds you.",
        speaker="Survivor wisdom",
        faction=None,
        category=QuoteCategory.PROVERB,
        context="Advice for newcomers",
        tags=["caution", "motives", "survival"],
    ),
    LoreQuote(
        text="The Sentries don't hate you. They don't know how.",
        speaker="Common observation",
        faction=None,
        category=QuoteCategory.WORLD_TRUTH,
        context="On AI units",
        tags=["sentries", "ai", "emotion"],
    ),
]


# -----------------------------------------------------------------------------
# Quote Retrieval Functions
# -----------------------------------------------------------------------------

def get_quotes_by_faction(faction: str) -> list[LoreQuote]:
    """Get all quotes associated with a faction."""
    faction_lower = faction.lower().replace(" ", "_")
    return [q for q in LORE_QUOTES if q.faction == faction_lower]


def get_quotes_by_category(category: QuoteCategory) -> list[LoreQuote]:
    """Get all quotes of a specific category."""
    return [q for q in LORE_QUOTES if q.category == category]


def get_quotes_by_tag(tag: str) -> list[LoreQuote]:
    """Get quotes matching a specific tag."""
    tag_lower = tag.lower()
    return [q for q in LORE_QUOTES if tag_lower in [t.lower() for t in q.tags]]


def get_random_quote(faction: str | None = None, category: QuoteCategory | None = None) -> LoreQuote | None:
    """Get a random quote, optionally filtered by faction or category."""
    candidates = LORE_QUOTES

    if faction:
        faction_lower = faction.lower().replace(" ", "_")
        candidates = [q for q in candidates if q.faction == faction_lower]

    if category:
        candidates = [q for q in candidates if q.category == category]

    if not candidates:
        return None

    return random.choice(candidates)


def get_relevant_quotes(
    text: str,
    faction: str | None = None,
    limit: int = 3,
) -> list[LoreQuote]:
    """
    Get quotes relevant to a text query.

    Matches based on tags and keywords in the quote text.
    Prioritizes faction quotes if faction is specified.
    """
    text_lower = text.lower()
    scored: list[tuple[float, LoreQuote]] = []

    for quote in LORE_QUOTES:
        score = 0.0

        # Tag matches
        for tag in quote.tags:
            if tag.lower() in text_lower:
                score += 1.0

        # Word matches in quote text
        quote_words = set(quote.text.lower().split())
        text_words = set(text_lower.split())
        overlap = quote_words & text_words
        if overlap:
            score += len(overlap) * 0.3

        # Faction bonus
        if faction:
            faction_lower = faction.lower().replace(" ", "_")
            if quote.faction == faction_lower:
                score += 2.0
            elif quote.faction is None:  # Universal quotes
                score += 0.5

        if score > 0:
            scored.append((score, quote))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    return [q for _, q in scored[:limit]]


def format_quote_for_dialogue(quote: LoreQuote) -> str:
    """Format a quote for potential use in NPC dialogue."""
    return f'"{quote.text}" — {quote.speaker}'


def format_quote_for_gm(quote: LoreQuote) -> str:
    """Format a quote with full context for GM reference."""
    lines = [
        f'"{quote.text}"',
        f"  — {quote.speaker}",
    ]
    if quote.context:
        lines.append(f"  Context: {quote.context}")
    if quote.tags:
        lines.append(f"  Tags: {', '.join(quote.tags)}")
    return "\n".join(lines)


def get_faction_motto(faction: str) -> LoreQuote | None:
    """Get the primary motto for a faction."""
    faction_lower = faction.lower().replace(" ", "_")
    for quote in LORE_QUOTES:
        if quote.faction == faction_lower and quote.category == QuoteCategory.FACTION_MOTTO:
            return quote
    return None


def get_all_mottos() -> dict[str, str]:
    """Get all faction mottos as a dict."""
    mottos = {}
    for quote in LORE_QUOTES:
        if quote.category == QuoteCategory.FACTION_MOTTO and quote.faction:
            mottos[quote.faction] = quote.text
    return mottos
