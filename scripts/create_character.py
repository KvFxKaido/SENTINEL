#!/usr/bin/env python3
"""
Interactive character appearance creator for SENTINEL.

Creates detailed character descriptions for portrait and profile generation.
Saves to YAML for consistency and regeneration.

Usage:
    python scripts/create_character.py                    # Interactive mode
    python scripts/create_character.py --load cipher.yaml # Load existing

After creating a character YAML, use these skills:
    /portrait <name>  - Generate character portrait (via Gemini NanoBanana)
    /profile <name>   - Generate full NPC profile (via Codex)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
CHARACTERS_DIR = PROJECT_ROOT / "assets" / "characters"

# =============================================================================
# Options for each category
# =============================================================================

GENDER_OPTIONS = {
    "1": ("masculine", "Masculine presenting"),
    "2": ("feminine", "Feminine presenting"),
    "3": ("androgynous", "Androgynous/neutral presenting"),
}

AGE_OPTIONS = {
    "1": ("young", "Young adult (20s)"),
    "2": ("adult", "Adult (30s-40s)"),
    "3": ("middle-aged", "Middle-aged (50s)"),
    "4": ("elder", "Elder (60s+)"),
}

SKIN_TONE_OPTIONS = {
    "1": ("pale", "Pale/fair"),
    "2": ("light", "Light"),
    "3": ("medium", "Medium/olive"),
    "4": ("tan", "Tan"),
    "5": ("brown", "Brown"),
    "6": ("dark", "Dark/deep"),
}

HAIR_COLOR_OPTIONS = {
    "1": ("black", "Black"),
    "2": ("dark brown", "Dark brown"),
    "3": ("brown", "Brown"),
    "4": ("auburn", "Auburn/reddish brown"),
    "5": ("red", "Red"),
    "6": ("blonde", "Blonde"),
    "7": ("grey", "Grey/silver"),
    "8": ("white", "White"),
    "9": ("shaved", "Shaved/bald"),
    "0": ("other", "Other (specify)"),
}

HAIR_LENGTH_OPTIONS = {
    "1": ("very short", "Very short/buzzed"),
    "2": ("short", "Short"),
    "3": ("medium", "Medium length"),
    "4": ("long", "Long"),
    "5": ("very long", "Very long"),
    "0": ("n/a", "N/A (bald/shaved)"),
}

HAIR_STYLE_OPTIONS = {
    "1": ("straight", "Straight"),
    "2": ("wavy", "Wavy"),
    "3": ("curly", "Curly"),
    "4": ("coily", "Coily/kinky"),
    "5": ("tied back", "Tied back/ponytail"),
    "6": ("braided", "Braided"),
    "7": ("dreadlocks", "Dreadlocks/locs"),
    "8": ("mohawk", "Mohawk/undercut"),
    "0": ("n/a", "N/A (bald/shaved)"),
}

BUILD_OPTIONS = {
    "1": ("lean", "Lean/thin"),
    "2": ("wiry", "Wiry/sinewy"),
    "3": ("average", "Average"),
    "4": ("athletic", "Athletic/fit"),
    "5": ("stocky", "Stocky/broad"),
    "6": ("heavy", "Heavy/large"),
}

FACIAL_FEATURES_OPTIONS = {
    "1": ("sharp", "Sharp/angular features"),
    "2": ("soft", "Soft/rounded features"),
    "3": ("weathered", "Weathered/lined"),
    "4": ("scarred", "Scarred"),
    "5": ("gaunt", "Gaunt/hollow"),
    "6": ("strong jaw", "Strong jaw"),
    "7": ("high cheekbones", "High cheekbones"),
}

EYE_COLOR_OPTIONS = {
    "1": ("brown", "Brown"),
    "2": ("dark brown", "Dark brown"),
    "3": ("hazel", "Hazel"),
    "4": ("green", "Green"),
    "5": ("blue", "Blue"),
    "6": ("grey", "Grey"),
    "7": ("amber", "Amber"),
    "8": ("augmented", "Augmented/cybernetic"),
}

# =============================================================================
# Interactive prompts
# =============================================================================

def print_options(options: dict, title: str) -> None:
    """Print numbered options."""
    print(f"\n{title}")
    print("-" * len(title))
    for key, (_, desc) in options.items():
        print(f"  [{key}] {desc}")


def get_choice(options: dict, title: str, allow_custom: bool = False) -> str:
    """Get user choice from options."""
    print_options(options, title)

    while True:
        choice = input("\nChoice: ").strip()
        if choice in options:
            value = options[choice][0]
            if value == "other" and allow_custom:
                custom = input("Specify: ").strip()
                return custom if custom else "unspecified"
            return value
        print("Invalid choice, try again.")


def get_multi_choice(options: dict, title: str, max_choices: int = 3) -> list[str]:
    """Get multiple choices from options."""
    print_options(options, title)
    print(f"\n(Enter up to {max_choices} choices separated by commas, or press Enter to skip)")

    choice_str = input("\nChoices: ").strip()
    if not choice_str:
        return []

    choices = []
    for c in choice_str.split(","):
        c = c.strip()
        if c in options:
            choices.append(options[c][0])

    return choices[:max_choices]


def get_text(prompt: str, required: bool = False) -> str:
    """Get free text input."""
    while True:
        value = input(f"\n{prompt}: ").strip()
        if value or not required:
            return value
        print("This field is required.")


def create_character_interactive() -> dict:
    """Run interactive character creation."""
    print("\n" + "=" * 50)
    print("  SENTINEL Character Appearance Creator")
    print("=" * 50)

    character = {}

    # Basic info
    character["name"] = get_text("Character name", required=True)
    character["type"] = get_choice({
        "1": ("npc", "NPC"),
        "2": ("player", "Player Character"),
    }, "Character Type")

    # Faction (optional for players)
    faction_choice = get_choice({
        "1": ("nexus", "Nexus"),
        "2": ("ember_colonies", "Ember Colonies"),
        "3": ("lattice", "Lattice"),
        "4": ("convergence", "Convergence"),
        "5": ("covenant", "Covenant"),
        "6": ("wanderers", "Wanderers"),
        "7": ("cultivators", "Cultivators"),
        "8": ("steel_syndicate", "Steel Syndicate"),
        "9": ("witnesses", "Witnesses"),
        "a": ("architects", "Architects"),
        "b": ("ghost_networks", "Ghost Networks"),
        "0": ("none", "None/Independent"),
    }, "Faction")
    if faction_choice != "none":
        character["faction"] = faction_choice

    # Role/archetype
    character["role"] = get_text("Role/archetype (e.g., scout, elder, fixer, medic)", required=True)

    print("\n" + "-" * 50)
    print("  Physical Appearance")
    print("-" * 50)

    # Core appearance
    character["gender"] = get_choice(GENDER_OPTIONS, "Gender/Presentation")
    character["age"] = get_choice(AGE_OPTIONS, "Age Range")
    character["skin_tone"] = get_choice(SKIN_TONE_OPTIONS, "Skin Tone")
    character["build"] = get_choice(BUILD_OPTIONS, "Build")

    # Hair
    print("\n--- Hair ---")
    character["hair_color"] = get_choice(HAIR_COLOR_OPTIONS, "Hair Color", allow_custom=True)

    if character["hair_color"] not in ["shaved", "bald"]:
        character["hair_length"] = get_choice(HAIR_LENGTH_OPTIONS, "Hair Length")
        if character["hair_length"] != "n/a":
            character["hair_style"] = get_choice(HAIR_STYLE_OPTIONS, "Hair Style")

    # Face
    print("\n--- Face ---")
    character["eye_color"] = get_choice(EYE_COLOR_OPTIONS, "Eye Color")
    character["facial_features"] = get_multi_choice(
        FACIAL_FEATURES_OPTIONS,
        "Facial Features (select up to 3)"
    )

    # Distinguishing marks
    print("\n--- Distinguishing Features ---")
    print("(These make the character memorable)")

    scars = get_text("Scars (e.g., 'scar across left cheek', or leave blank)")
    if scars:
        character["scars"] = scars

    augments = get_text("Augmentations/cybernetics (e.g., 'cybernetic left eye', or leave blank)")
    if augments:
        character["augmentations"] = augments

    tattoos = get_text("Tattoos/markings (e.g., 'faction symbol on neck', or leave blank)")
    if tattoos:
        character["tattoos"] = tattoos

    other = get_text("Other distinguishing features (or leave blank)")
    if other:
        character["other_features"] = other

    # Expression default based on disposition
    character["default_expression"] = get_choice({
        "1": ("neutral", "Neutral/calm"),
        "2": ("wary", "Wary/guarded"),
        "3": ("warm", "Warm/approachable"),
        "4": ("stern", "Stern/serious"),
        "5": ("tired", "Tired/worn"),
    }, "Default Expression")

    return character


# =============================================================================
# YAML save/load
# =============================================================================

def save_character(character: dict, filepath: Path | None = None) -> Path:
    """Save character to YAML file."""
    if filepath is None:
        CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = character["name"].lower().replace(" ", "_").replace("'", "")
        filepath = CHARACTERS_DIR / f"{safe_name}.yaml"

    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(character, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"\nSaved character to: {filepath}")
    return filepath


def load_character(filepath: Path) -> dict:
    """Load character from YAML file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# =============================================================================
# Portrait description builder
# =============================================================================

def _build_person_descriptor(gender: str, skin_tone: str, age_desc: str) -> str:
    """
    Build an explicit person descriptor to anchor image generation.

    NanoBanana needs explicit descriptors like "Black man" or "East Asian woman"
    rather than vague terms like "masculine with brown skin" to stay on target.
    """
    # Map gender to gendered noun
    gender_noun = {
        "masculine": "man",
        "feminine": "woman",
        "androgynous": "person",
    }.get(gender, "person")

    # Map skin tone to explicit ethnic/racial descriptor
    # These are intentionally explicit to anchor the image generation
    skin_descriptor = {
        "pale": "pale-skinned",
        "light": "light-skinned",
        "medium": "olive-skinned",
        "tan": "tan",
        "brown": "Black",  # Explicit for brown skin
        "dark": "dark-skinned Black",  # Explicit for dark skin
    }.get(skin_tone, "")

    # Build the descriptor
    if age_desc and skin_descriptor:
        return f"{age_desc} {skin_descriptor} {gender_noun}"
    elif age_desc:
        return f"{age_desc} {gender_noun}"
    elif skin_descriptor:
        return f"{skin_descriptor} {gender_noun}"
    else:
        return gender_noun


def build_portrait_description(character: dict) -> str:
    """Build a detailed portrait description from character data."""
    parts = []

    # Gender/age/build/skin - combine into explicit descriptor
    gender = character.get("gender", "")
    age = character.get("age", "adult")
    build = character.get("build", "average")
    skin = character.get("skin_tone", "")

    age_map = {
        "young": "young",
        "adult": "",
        "middle-aged": "middle-aged",
        "elder": "elderly",
    }
    age_desc = age_map.get(age, "")

    # Build explicit person descriptor to anchor the generation
    # e.g., "Black man" instead of "masculine with brown skin"
    person_desc = _build_person_descriptor(gender, skin, age_desc)
    parts.append(f"{person_desc} with {build} build")

    # Hair
    hair_color = character.get("hair_color", "")
    hair_length = character.get("hair_length", "")
    hair_style = character.get("hair_style", "")

    if hair_color in ["shaved", "bald"]:
        parts.append("shaved head")
    elif hair_color:
        hair_desc = hair_color
        if hair_length and hair_length != "n/a":
            hair_desc = f"{hair_length} {hair_desc}"
        if hair_style and hair_style != "n/a":
            hair_desc = f"{hair_style} {hair_desc}"
        parts.append(f"{hair_desc} hair")

    # Eyes
    eye_color = character.get("eye_color", "")
    if eye_color:
        if eye_color == "augmented":
            parts.append("cybernetic eyes")
        else:
            parts.append(f"{eye_color} eyes")

    # Facial features
    facial = character.get("facial_features", [])
    if facial:
        parts.append(", ".join(facial))

    # Distinguishing marks
    scars = character.get("scars", "")
    if scars:
        parts.append(scars)

    augments = character.get("augmentations", "")
    if augments:
        parts.append(augments)

    tattoos = character.get("tattoos", "")
    if tattoos:
        parts.append(tattoos)

    other = character.get("other_features", "")
    if other:
        parts.append(other)

    # Expression
    expression = character.get("default_expression", "neutral")
    expression_map = {
        "neutral": "calm, alert expression",
        "wary": "guarded, watchful expression",
        "warm": "approachable expression with hint of warmth",
        "stern": "stern, serious expression",
        "tired": "tired, world-weary expression",
    }
    parts.append(expression_map.get(expression, "neutral expression"))

    return ", ".join(parts)


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Interactive character appearance creator for SENTINEL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create new character interactively
    python create_character.py

    # Load existing character and show description
    python create_character.py --load cipher.yaml

    # Save to specific path
    python create_character.py --output my_character.yaml

After creating a character, use Claude Code skills:
    /portrait cipher  - Generate portrait (Gemini NanoBanana)
    /profile cipher   - Generate NPC profile (Codex)
        """,
    )

    parser.add_argument("--load", "-l", type=Path, help="Load character from YAML file")
    parser.add_argument("--describe", "-d", action="store_true", help="Show portrait description only")
    parser.add_argument("--output", "-o", type=Path, help="Output YAML path")

    args = parser.parse_args()

    # Load or create character
    if args.load:
        if not args.load.exists():
            # Check in characters directory
            alt_path = CHARACTERS_DIR / args.load
            if alt_path.exists():
                args.load = alt_path
            else:
                print(f"Character file not found: {args.load}")
                return 1

        character = load_character(args.load)
        print(f"Loaded character: {character.get('name', 'Unknown')}")
    else:
        character = create_character_interactive()
        save_character(character, args.output)

    # Show description
    print("\n" + "=" * 50)
    print("  Portrait Description")
    print("=" * 50)
    print(build_portrait_description(character))
    name_slug = character.get("name", "").lower().replace(" ", "_")
    print(f"\nTo generate portrait: /portrait {name_slug}")
    print(f"To generate NPC profile: /profile {name_slug}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
