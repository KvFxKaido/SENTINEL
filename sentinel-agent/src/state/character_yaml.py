"""
Character YAML stub generation and portrait sync for portrait workflow.

When campaigns are saved, this module:
1. Checks for NPCs without character YAML files and generates stubs
2. Syncs portraits from the source directory to web UI and wiki

Portrait workflow for players:
1. Drop portrait in assets/portraits/npcs/{name}.png (e.g., kira_vance.png)
2. Run /save - portraits auto-sync to web UI and wiki
"""

from pathlib import Path
import shutil
import yaml


# Template for character YAML stubs
# Uses None/unknown values that signal "needs editing"
YAML_TEMPLATE = {
    "name": "",
    "faction": "",
    "role": "unknown",  # contact, merchant, enforcer, etc.
    "gender": "unknown",  # masculine, feminine, androgynous
    "age": "adult",  # child, young, adult, middle-aged, elder
    "skin_tone": "unknown",  # pale, fair, medium, olive, brown, dark
    "build": "unknown",  # slight, lean, average, athletic, stocky, heavy
    "hair_color": "unknown",
    "hair_length": "unknown",  # bald, short, medium, long
    "hair_style": "unknown",  # straight, wavy, curly, braided, etc.
    "eye_color": "unknown",
    "facial_features": [],  # sharp, soft, angular, round, etc.
    "augmentations": [],  # visible cybernetics
    "scars": None,
    "tattoos": None,
    "other_features": [],  # clothing, accessories, always-present items
    "default_expression": "neutral",  # wary, stern, warm, amused, etc.
    "notes": "Auto-generated stub. Edit appearance fields for portrait generation.",
}


def slugify(name: str) -> str:
    """Convert NPC name to filename slug."""
    return name.strip().lower().replace(" ", "_").replace("'", "").replace("-", "_")


def get_characters_dir() -> Path:
    """Get the characters directory path."""
    # Navigate from this file: src/state/ -> sentinel-agent/ -> SENTINEL/assets/characters/
    return Path(__file__).parent.parent.parent.parent / "assets" / "characters"


def yaml_exists(name: str, characters_dir: Path | None = None) -> bool:
    """Check if a character YAML file exists for the given NPC name."""
    if characters_dir is None:
        characters_dir = get_characters_dir()

    slug = slugify(name)
    yaml_path = characters_dir / f"{slug}.yaml"
    return yaml_path.exists()


def generate_stub_yaml(
    name: str,
    faction: str | None = None,
    role: str | None = None,
    characters_dir: Path | None = None,
) -> Path | None:
    """
    Generate a stub YAML file for an NPC if one doesn't exist.

    Args:
        name: NPC name
        faction: Faction affiliation (optional)
        role: NPC role like "contact", "merchant" (optional)
        characters_dir: Override characters directory (for testing)

    Returns:
        Path to created file, or None if file already exists
    """
    if characters_dir is None:
        characters_dir = get_characters_dir()

    # Ensure directory exists
    characters_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(name)
    yaml_path = characters_dir / f"{slug}.yaml"

    # Don't overwrite existing files
    if yaml_path.exists():
        return None

    # Build the YAML content
    data = YAML_TEMPLATE.copy()
    data["name"] = name
    data["faction"] = faction or "unknown"
    if role:
        data["role"] = role

    # Write with nice formatting
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=80,
        )

    return yaml_path


def generate_stubs_for_campaign(npcs: list, characters_dir: Path | None = None) -> list[Path]:
    """
    Generate YAML stubs for all NPCs in a campaign that don't have them.

    Args:
        npcs: List of NPC objects (must have .name and .faction attributes)
        characters_dir: Override characters directory (for testing)

    Returns:
        List of paths to newly created YAML files
    """
    created = []

    for npc in npcs:
        # Extract role from agenda if available
        role = None
        if hasattr(npc, "agenda") and npc.agenda:
            # Agenda might hint at role based on wants/fears
            agenda = npc.agenda
            if hasattr(agenda, "wants"):
                wants = agenda.wants.lower() if agenda.wants else ""
                if "trade" in wants or "deal" in wants:
                    role = "merchant"
                elif "information" in wants or "intel" in wants:
                    role = "informant"
                elif "power" in wants or "control" in wants:
                    role = "leader"

        # Get faction name as string
        faction_str = None
        if hasattr(npc, "faction") and npc.faction:
            faction_str = npc.faction.value if hasattr(npc.faction, "value") else str(npc.faction)

        path = generate_stub_yaml(
            name=npc.name,
            faction=faction_str,
            role=role,
            characters_dir=characters_dir,
        )

        if path:
            created.append(path)

    return created


def get_portraits_dir() -> Path:
    """Get the source portraits directory path (assets/portraits/npcs/)."""
    return Path(__file__).parent.parent.parent.parent / "assets" / "portraits" / "npcs"


def get_webui_portraits_dir() -> Path:
    """Get the web UI portraits directory path."""
    return Path(__file__).parent.parent.parent.parent / "sentinel-ui" / "public" / "assets" / "portraits" / "npcs"


def get_wiki_portraits_dir() -> Path:
    """Get the wiki portraits directory path."""
    return Path(__file__).parent.parent.parent.parent / "wiki" / "assets" / "portraits" / "npcs"


def sync_portraits() -> dict:
    """
    Sync portraits from source directory to web UI and wiki.

    Source: assets/portraits/npcs/
    Destinations:
      - sentinel-ui/public/assets/portraits/npcs/ (web UI)
      - wiki/assets/portraits/npcs/ (Obsidian)

    Returns:
        dict with 'copied_to_webui' and 'copied_to_wiki' lists of filenames
    """
    source_dir = get_portraits_dir()
    webui_dir = get_webui_portraits_dir()
    wiki_dir = get_wiki_portraits_dir()

    result = {
        "copied_to_webui": [],
        "copied_to_wiki": [],
    }

    # Skip if source doesn't exist
    if not source_dir.exists():
        return result

    # Ensure destination directories exist
    webui_dir.mkdir(parents=True, exist_ok=True)
    wiki_dir.mkdir(parents=True, exist_ok=True)

    # Sync each portrait
    for portrait in source_dir.glob("*.png"):
        # Copy to web UI if missing or different size
        webui_dest = webui_dir / portrait.name
        if not webui_dest.exists() or webui_dest.stat().st_size != portrait.stat().st_size:
            try:
                shutil.copy2(portrait, webui_dest)
                result["copied_to_webui"].append(portrait.name)
            except Exception:
                pass  # Best effort

        # Copy to wiki if missing or different size
        wiki_dest = wiki_dir / portrait.name
        if not wiki_dest.exists() or wiki_dest.stat().st_size != portrait.stat().st_size:
            try:
                shutil.copy2(portrait, wiki_dest)
                result["copied_to_wiki"].append(portrait.name)
            except Exception:
                pass  # Best effort

    return result
