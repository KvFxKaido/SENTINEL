"""Choice parsing utilities for SENTINEL."""

import re
from dataclasses import dataclass


@dataclass
class ChoiceBlock:
    """Parsed choice options from agent response."""
    stakes: str  # "high" or "normal"
    context: str | None
    options: list[str]


# Pattern for formal high-stakes choice blocks
CHOICE_BLOCK_PATTERN = re.compile(
    r'---CHOICE---\s*'
    r'stakes:\s*(\w+)\s*'
    r'context:\s*"([^"]*)"\s*'
    r'options:\s*'
    r'((?:- "[^"]*"\s*)+)'
    r'---END---',
    re.MULTILINE | re.DOTALL
)

# Pattern for inline numbered options
INLINE_OPTIONS_PATTERN = re.compile(
    r'^(\d)\.\s+(.+)$',
    re.MULTILINE
)


def parse_response(text: str) -> tuple[str, ChoiceBlock | None]:
    """
    Extract narrative and choice block from agent response.

    Returns:
        Tuple of (narrative_text, ChoiceBlock or None)
    """
    # Check for formal choice block first
    match = CHOICE_BLOCK_PATTERN.search(text)
    if match:
        narrative = text[:match.start()].strip()
        options = re.findall(r'- "([^"]*)"', match.group(3))
        return narrative, ChoiceBlock(
            stakes=match.group(1),
            context=match.group(2),
            options=options
        )

    # Check for inline numbered options (1. 2. 3. pattern)
    options = INLINE_OPTIONS_PATTERN.findall(text)
    if len(options) >= 2:
        # Find where options start
        first_option = re.search(r'^\d\.\s+', text, re.MULTILINE)
        if first_option:
            narrative = text[:first_option.start()].strip()
            return narrative, ChoiceBlock(
                stakes="normal",
                context=None,
                options=[opt[1] for opt in options]
            )

    # No choices detected
    return text, None
