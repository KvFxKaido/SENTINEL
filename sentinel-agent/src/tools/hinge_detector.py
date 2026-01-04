"""
Hinge Moment Detection.

Detects player statements that indicate irreversible choices,
allowing the GM to flag and log pivotal moments.

Patterns from Sovwren's self-focus guard, adapted for SENTINEL.
"""

import re
from dataclasses import dataclass
from enum import Enum


class HingeCategory(str, Enum):
    """Categories of irreversible actions."""
    VIOLENCE = "violence"           # Killing, destroying
    BETRAYAL = "betrayal"           # Betraying, revealing secrets
    COMMITMENT = "commitment"       # Promises, oaths
    ENHANCEMENT = "enhancement"     # Accepting faction powers
    DISCLOSURE = "disclosure"       # Telling factions about others
    SACRIFICE = "sacrifice"         # Giving up something important
    REJECTION = "rejection"         # Refusing offers, walking away


@dataclass
class HingeDetection:
    """Result of hinge pattern detection."""
    detected: bool
    category: HingeCategory | None
    pattern_matched: str
    excerpt: str  # The relevant portion of player input
    severity: str  # "minor", "moderate", "major"
    suggested_prompt: str  # For GM to confirm with player


# Pattern definitions: (regex, category, severity, gm_prompt_template)
HINGE_PATTERNS = [
    # Violence
    (
        r"\bi\s+(kill|murder|execute|eliminate|end)\b",
        HingeCategory.VIOLENCE,
        "major",
        "This ends a life. There's no coming back from this. Are you sure?"
    ),
    (
        r"\bi\s+(destroy|demolish|sabotage|blow up)\b",
        HingeCategory.VIOLENCE,
        "moderate",
        "This destruction will have consequences. Do you proceed?"
    ),

    # Betrayal
    (
        r"\bi\s+(betray|sell out|turn on|double-cross)\b",
        HingeCategory.BETRAYAL,
        "major",
        "Betrayal changes everything. They will remember this. Continue?"
    ),
    (
        r"\bi\s+(reveal|expose|tell .+ about|share .+ secret)\b",
        HingeCategory.DISCLOSURE,
        "moderate",
        "Once revealed, this information can't be taken back. Proceed?"
    ),

    # Commitment
    (
        r"\bi\s+(promise|swear|vow|pledge|commit)\b",
        HingeCategory.COMMITMENT,
        "moderate",
        "A promise made is a debt unpaid. Are you ready to be bound by this?"
    ),
    (
        r"\bi\s+(give my word|stake my reputation)\b",
        HingeCategory.COMMITMENT,
        "major",
        "Your word is your currency. Breaking it will cost everything."
    ),

    # Enhancements
    (
        r"\bi\s+(accept|take|receive)\s+(the\s+)?enhancement\b",
        HingeCategory.ENHANCEMENT,
        "major",
        "This enhancement comes with strings. The faction gains leverage over you."
    ),
    (
        r"\bi\s+(accept|agree to)\s+.*(offer|deal|terms|package)\b",
        HingeCategory.ENHANCEMENT,
        "moderate",
        "Accepting this binds you to their terms. You understand the cost?"
    ),

    # Rejection
    (
        r"\bi\s+(refuse|reject|decline|turn down)\s+(the\s+)?enhancement\b",
        HingeCategory.REJECTION,
        "moderate",
        "Refusing this closes a door. But it keeps you free. Confirmed?"
    ),
    (
        r"\bi\s+(walk away|leave .+ behind|abandon)\b",
        HingeCategory.REJECTION,
        "moderate",
        "Walking away means you can't go back. Are you at peace with this?"
    ),

    # Sacrifice
    (
        r"\bi\s+(sacrifice|give up|surrender|trade away)\b",
        HingeCategory.SACRIFICE,
        "major",
        "What you sacrifice stays lost. Is this worth the cost?"
    ),
    (
        r"\bi\s+(let .+ die|choose .+ over)\b",
        HingeCategory.SACRIFICE,
        "major",
        "This choice will haunt you. You're certain?"
    ),

    # Faction disclosure
    (
        r"\bi\s+tell\s+(nexus|ember|lattice|convergence|covenant|wanderers|cultivators|syndicate|witnesses|architects|ghost)\b",
        HingeCategory.DISCLOSURE,
        "moderate",
        "Sharing this with {faction} changes the game. They'll act on this information."
    ),
]


def detect_hinge(player_input: str) -> HingeDetection | None:
    """
    Analyze player input for hinge moment patterns.

    Returns HingeDetection if an irreversible choice is detected,
    None otherwise.
    """
    text = player_input.lower().strip()

    for pattern, category, severity, prompt_template in HINGE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Extract context around the match
            start = max(0, match.start() - 20)
            end = min(len(player_input), match.end() + 40)
            excerpt = player_input[start:end].strip()
            if start > 0:
                excerpt = "..." + excerpt
            if end < len(player_input):
                excerpt = excerpt + "..."

            # Format the prompt template
            suggested_prompt = prompt_template
            # Handle faction-specific prompts
            if "{faction}" in suggested_prompt:
                faction_match = re.search(
                    r"(nexus|ember|lattice|convergence|covenant|wanderers|cultivators|syndicate|witnesses|architects|ghost)",
                    text,
                    re.IGNORECASE
                )
                if faction_match:
                    suggested_prompt = suggested_prompt.format(
                        faction=faction_match.group(1).title()
                    )

            return HingeDetection(
                detected=True,
                category=category,
                pattern_matched=pattern,
                excerpt=excerpt,
                severity=severity,
                suggested_prompt=suggested_prompt,
            )

    return None


def get_hinge_context(detection: HingeDetection) -> str:
    """
    Generate context string for the GM about detected hinge moment.

    This gets injected into the GM's context so they know to treat
    this as a pivotal moment.
    """
    return f"""
[HINGE MOMENT DETECTED]
Category: {detection.category.value}
Severity: {detection.severity}
Player said: "{detection.excerpt}"

This appears to be an irreversible choice. Before proceeding:
1. Confirm the player understands the permanence
2. Present the stakes clearly
3. If they proceed, log this as a hinge moment

Suggested confirmation: "{detection.suggested_prompt}"
"""


# Convenience function for quick checks
def is_hinge_moment(text: str) -> bool:
    """Quick check if text contains hinge patterns."""
    return detect_hinge(text) is not None
