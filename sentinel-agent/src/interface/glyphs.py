"""
Glyph system for SENTINEL visual indicators.

Uses Unicode symbols with ASCII fallbacks.
Toggle USE_UNICODE based on terminal support.
"""

USE_UNICODE = True  # Set False for basic terminals


def g(name: str) -> str:
    """Get glyph by name, with fallback support."""
    glyphs = GLYPHS_UNICODE if USE_UNICODE else GLYPHS_ASCII
    return glyphs.get(name, "?")


# -----------------------------------------------------------------------------
# Unicode Glyphs (default)
# -----------------------------------------------------------------------------

GLYPHS_UNICODE = {
    # Faction standings
    "hostile": "◆",      # Filled diamond - danger
    "unfriendly": "◇",   # Empty diamond - caution
    "neutral": "○",      # Empty circle - baseline
    "friendly": "●",     # Filled circle - positive
    "allied": "★",       # Star - strong bond

    # Social energy states
    "centered": "▰",     # Full bar
    "steady": "▰",       # Full bar
    "frayed": "▱",       # Empty bar
    "overloaded": "▱",   # Empty bar
    "shutdown": "✕",     # X mark

    # Energy bar segments
    "energy_full": "█",
    "energy_mid": "▓",
    "energy_low": "░",
    "energy_empty": "·",

    # Mission phases
    "briefing": "◈",     # Diamond with dot
    "planning": "◎",     # Bullseye
    "execution": "▶",    # Play/forward
    "resolution": "◉",   # Target
    "debrief": "◇",      # Empty diamond
    "between": "…",      # Ellipsis

    # Events and moments
    "hinge": "⬡",        # Hexagon - pivotal choice
    "thread": "◌",       # Dashed circle - dormant
    "triggered": "◉",    # Filled target - activated
    "canon": "▣",        # Filled square - permanent

    # Enhancements
    "enhanced": "⚡",     # Lightning - power
    "refused": "⊘",      # Null sign - rejected
    "leverage": "⚖",     # Scales - faction debt

    # NPCs
    "npc_active": "◉",
    "npc_dormant": "○",

    # Actions
    "roll": "⚄",         # Die face
    "success": "✓",
    "failure": "✗",
    "advantage": "▲",
    "disadvantage": "▼",

    # UI elements
    "prompt": "›",
    "arrow": "→",
    "bullet": "•",
    "warning": "⚠",
    "info": "ℹ",
    "save": "◆",
    "load": "◇",

    # Faction glyphs (for codec boxes and council)
    "nexus": "◈",           # Diamond with dot - surveillance, data
    "ember_colonies": "◆",  # Solid diamond - resilience, community
    "lattice": "▣",         # Grid square - infrastructure
    "convergence": "⚡",     # Lightning - enhancement, change
    "covenant": "⚖",        # Scales - oaths, ethics
    "wanderers": "◇",       # Empty diamond - movement, freedom
    "cultivators": "❋",     # Flower - growth, sustainability
    "steel_syndicate": "⚙", # Gear - industry, leverage
    "witnesses": "◎",       # Target/eye - observation, records
    "architects": "▲",      # Triangle - structure, pre-collapse
    "ghost_networks": "◌",  # Dashed circle - hidden, ephemeral
}


# -----------------------------------------------------------------------------
# ASCII Fallbacks
# -----------------------------------------------------------------------------

GLYPHS_ASCII = {
    # Faction standings
    "hostile": "[X]",
    "unfriendly": "[-]",
    "neutral": "[ ]",
    "friendly": "[+]",
    "allied": "[*]",

    # Social energy states
    "centered": "[=]",
    "steady": "[=]",
    "frayed": "[~]",
    "overloaded": "[!]",
    "shutdown": "[X]",

    # Energy bar segments
    "energy_full": "#",
    "energy_mid": "=",
    "energy_low": "-",
    "energy_empty": ".",

    # Mission phases
    "briefing": "[B]",
    "planning": "[P]",
    "execution": "[E]",
    "resolution": "[R]",
    "debrief": "[D]",
    "between": "...",

    # Events and moments
    "hinge": "[H]",
    "thread": "[~]",
    "triggered": "[!]",
    "canon": "[#]",

    # Enhancements
    "enhanced": "[+]",
    "refused": "[-]",
    "leverage": "[!]",

    # NPCs
    "npc_active": "[*]",
    "npc_dormant": "[ ]",

    # Actions
    "roll": "[d]",
    "success": "[+]",
    "failure": "[-]",
    "advantage": "[^]",
    "disadvantage": "[v]",

    # UI elements
    "prompt": ">",
    "arrow": "->",
    "bullet": "*",
    "warning": "[!]",
    "info": "[i]",
    "save": "[S]",
    "load": "[L]",

    # Faction glyphs (for codec boxes and council)
    "nexus": "[NX]",
    "ember_colonies": "[EM]",
    "lattice": "[LA]",
    "convergence": "[CV]",
    "covenant": "[CO]",
    "wanderers": "[WA]",
    "cultivators": "[CU]",
    "steel_syndicate": "[SS]",
    "witnesses": "[WI]",
    "architects": "[AR]",
    "ghost_networks": "[GN]",
}


# -----------------------------------------------------------------------------
# Convenience exports
# -----------------------------------------------------------------------------

# Faction
HOSTILE = g("hostile")
UNFRIENDLY = g("unfriendly")
NEUTRAL = g("neutral")
FRIENDLY = g("friendly")
ALLIED = g("allied")

# Energy
CENTERED = g("centered")
FRAYED = g("frayed")
OVERLOADED = g("overloaded")
SHUTDOWN = g("shutdown")

# Events
HINGE = g("hinge")
THREAD = g("thread")
CANON = g("canon")

# Actions
SUCCESS = g("success")
FAILURE = g("failure")
ADVANTAGE = g("advantage")
DISADVANTAGE = g("disadvantage")


def energy_bar(percent: int, width: int = 10) -> str:
    """Generate a visual energy bar."""
    filled = int((percent / 100) * width)

    if percent > 50:
        char = g("energy_full")
    elif percent > 25:
        char = g("energy_mid")
    else:
        char = g("energy_low")

    empty = g("energy_empty")

    return char * filled + empty * (width - filled)


def standing_indicator(standing: str) -> str:
    """Get glyph for faction standing."""
    mapping = {
        "Hostile": g("hostile"),
        "Unfriendly": g("unfriendly"),
        "Neutral": g("neutral"),
        "Friendly": g("friendly"),
        "Allied": g("allied"),
    }
    return mapping.get(standing, g("neutral"))


# -----------------------------------------------------------------------------
# Context Meter
# -----------------------------------------------------------------------------

# Approximate tokens per character (rough estimate)
CHARS_PER_TOKEN = 4

# Context window sizes for common models
CONTEXT_LIMITS = {
    "default": 16384,      # 16k - safe default
    "small": 4096,         # 4k - older models
    "medium": 8192,        # 8k
    "large": 32768,        # 32k
    "huge": 131072,        # 128k
}

# Narrative bands for context depth
CONTEXT_BANDS = [
    (0.0, 0.25, "shallow", "fresh start, full clarity"),
    (0.25, 0.50, "moderate", "building history"),
    (0.50, 0.75, "deep", "rich context, edges blurring"),
    (0.75, 0.90, "saturated", "memory straining"),
    (0.90, 1.0, "critical", "fragmenting soon"),
]


def estimate_tokens(text: str) -> int:
    """Rough token estimate from text length."""
    return len(text) // CHARS_PER_TOKEN


def estimate_conversation_tokens(messages: list) -> int:
    """Estimate total tokens in a conversation."""
    total = 0
    for msg in messages:
        if hasattr(msg, 'content'):
            total += estimate_tokens(msg.content)
        elif isinstance(msg, dict):
            total += estimate_tokens(msg.get('content', ''))
        elif isinstance(msg, str):
            total += estimate_tokens(msg)
    return total


def get_context_band(usage_ratio: float) -> tuple[str, str]:
    """Get narrative band name and description for usage ratio."""
    for low, high, name, desc in CONTEXT_BANDS:
        if low <= usage_ratio < high:
            return name, desc
    return "critical", "fragmenting soon"


def context_bar(usage_ratio: float, width: int = 10) -> str:
    """Generate visual context usage bar."""
    filled = int(usage_ratio * width)
    filled = min(filled, width)  # Cap at width

    if usage_ratio < 0.5:
        char = g("energy_full")
    elif usage_ratio < 0.75:
        char = g("energy_mid")
    else:
        char = g("energy_low")

    empty = g("energy_empty")
    return char * filled + empty * (width - filled)


def format_context_meter(
    messages: list,
    context_limit: int = CONTEXT_LIMITS["default"],
    show_bar: bool = True,
    show_band: bool = True,
    show_turns: bool = True,
) -> str:
    """
    Format a complete context meter display.

    Args:
        messages: Conversation messages
        context_limit: Max tokens for the model
        show_bar: Include visual bar
        show_band: Include narrative band
        show_turns: Include turn count

    Returns:
        Formatted string like "▰▰▰▱▱▱▱▱▱▱ moderate (12 turns)"
    """
    tokens = estimate_conversation_tokens(messages)
    usage_ratio = min(tokens / context_limit, 1.0)
    turns = len(messages) // 2  # Rough: user + assistant = 1 turn

    parts = []

    if show_bar:
        parts.append(context_bar(usage_ratio))

    if show_band:
        band_name, _ = get_context_band(usage_ratio)
        parts.append(band_name)

    if show_turns:
        parts.append(f"({turns} turns)")

    return " ".join(parts)


def context_warning(usage_ratio: float) -> str | None:
    """
    Get warning message if context is getting full.

    Returns None if no warning needed.
    """
    if usage_ratio >= 0.90:
        return "Memory fragmenting — consider /debrief to preserve and reset"
    elif usage_ratio >= 0.75:
        return "Context deep — older details may blur"
    return None
