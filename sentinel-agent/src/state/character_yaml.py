"""
Character YAML and portrait management with campaign isolation.

Each campaign has its own character appearances and portraits:
- Character YAML: assets/characters/campaigns/{campaign_id}/{name}.yaml
- Portraits: sentinel-ui/public/assets/portraits/campaigns/{campaign_id}/{name}.png

This enables fully emergent playthroughs where the same NPC name
can have different appearances across campaigns.
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


def _get_project_root() -> Path:
    """Get the SENTINEL project root directory."""
    # Navigate from this file: src/state/ -> sentinel-agent/ -> SENTINEL/
    return Path(__file__).parent.parent.parent.parent


def get_characters_dir(campaign_id: str | None = None) -> Path:
    """
    Get the characters directory path.

    Args:
        campaign_id: If provided, returns campaign-specific directory.
                    If None, returns legacy global directory for backward compat.
    """
    base = _get_project_root() / "assets" / "characters"
    if campaign_id:
        return base / "campaigns" / campaign_id
    return base


def get_portraits_dir(campaign_id: str | None = None) -> Path:
    """
    Get the portraits directory path for web UI.

    Args:
        campaign_id: If provided, returns campaign-specific directory.
                    If None, returns legacy global directory.
    """
    base = _get_project_root() / "sentinel-ui" / "public" / "assets" / "portraits"
    if campaign_id:
        return base / "campaigns" / campaign_id
    return base / "npcs"


def get_wiki_portraits_dir(campaign_id: str | None = None) -> Path:
    """
    Get the wiki portraits directory path.

    Args:
        campaign_id: If provided, returns campaign-specific directory.
    """
    base = _get_project_root() / "wiki" / "assets" / "portraits"
    if campaign_id:
        return base / "campaigns" / campaign_id
    return base / "npcs"


def yaml_exists(name: str, campaign_id: str | None = None) -> bool:
    """
    Check if a character YAML file exists for the given name.

    Args:
        name: Character/NPC name
        campaign_id: Campaign ID for campaign-specific lookup.
                    If None, checks legacy global directory.

    Returns:
        True if YAML file exists
    """
    characters_dir = get_characters_dir(campaign_id)
    slug = slugify(name)
    yaml_path = characters_dir / f"{slug}.yaml"

    # Check campaign-specific first
    if yaml_path.exists():
        return True

    # Fall back to global directory for backward compatibility
    if campaign_id:
        global_dir = get_characters_dir(None)
        global_path = global_dir / f"{slug}.yaml"
        return global_path.exists()

    return False


def load_character_yaml(name: str, campaign_id: str | None = None) -> dict | None:
    """
    Load character YAML data.

    Args:
        name: Character/NPC name
        campaign_id: Campaign ID for campaign-specific lookup

    Returns:
        Character data dict or None if not found
    """
    slug = slugify(name)

    # Check campaign-specific first
    if campaign_id:
        campaign_dir = get_characters_dir(campaign_id)
        campaign_path = campaign_dir / f"{slug}.yaml"
        if campaign_path.exists():
            with open(campaign_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

    # Fall back to global directory
    global_dir = get_characters_dir(None)
    global_path = global_dir / f"{slug}.yaml"
    if global_path.exists():
        with open(global_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    return None


def save_character_yaml(
    name: str,
    data: dict,
    campaign_id: str | None = None,
) -> Path:
    """
    Save character YAML data.

    Args:
        name: Character/NPC name
        data: Character data to save
        campaign_id: Campaign ID for campaign-specific save

    Returns:
        Path to saved file
    """
    characters_dir = get_characters_dir(campaign_id)
    characters_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(name)
    yaml_path = characters_dir / f"{slug}.yaml"

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


def generate_stub_yaml(
    name: str,
    faction: str | None = None,
    role: str | None = None,
    campaign_id: str | None = None,
) -> Path | None:
    """
    Generate a stub YAML file for an NPC if one doesn't exist.

    Args:
        name: NPC name
        faction: Faction affiliation (optional)
        role: NPC role like "contact", "merchant" (optional)
        campaign_id: Campaign ID for campaign-specific save

    Returns:
        Path to created file, or None if file already exists
    """
    # Check if already exists (campaign-specific or global)
    if yaml_exists(name, campaign_id):
        return None

    # Build the YAML content
    data = YAML_TEMPLATE.copy()
    data["name"] = name
    data["faction"] = faction or "unknown"
    if role:
        data["role"] = role

    return save_character_yaml(name, data, campaign_id)


def generate_stubs_for_campaign(
    npcs: list,
    campaign_id: str | None = None,
) -> list[Path]:
    """
    Generate YAML stubs for all NPCs in a campaign that don't have them.

    Args:
        npcs: List of NPC objects (must have .name and .faction attributes)
        campaign_id: Campaign ID for campaign-specific saves

    Returns:
        List of paths to newly created YAML files
    """
    created = []

    for npc in npcs:
        # Extract role from agenda if available
        role = None
        if hasattr(npc, "agenda") and npc.agenda:
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
            campaign_id=campaign_id,
        )

        if path:
            created.append(path)

    return created


def portrait_exists(name: str, campaign_id: str | None = None) -> bool:
    """
    Check if a portrait exists for the given name.

    Args:
        name: Character/NPC name
        campaign_id: Campaign ID for campaign-specific lookup

    Returns:
        True if portrait file exists
    """
    slug = slugify(name)

    # Check campaign-specific first
    if campaign_id:
        campaign_dir = get_portraits_dir(campaign_id)
        if (campaign_dir / f"{slug}.png").exists():
            return True

    # Fall back to global directory
    global_dir = get_portraits_dir(None)
    return (global_dir / f"{slug}.png").exists()


def get_portrait_path(name: str, campaign_id: str | None = None) -> Path | None:
    """
    Get the path to a portrait file, checking campaign-specific first.

    Args:
        name: Character/NPC name
        campaign_id: Campaign ID for campaign-specific lookup

    Returns:
        Path to portrait or None if not found
    """
    slug = slugify(name)

    # Check campaign-specific first
    if campaign_id:
        campaign_dir = get_portraits_dir(campaign_id)
        campaign_path = campaign_dir / f"{slug}.png"
        if campaign_path.exists():
            return campaign_path

    # Fall back to global directory
    global_dir = get_portraits_dir(None)
    global_path = global_dir / f"{slug}.png"
    if global_path.exists():
        return global_path

    return None


def get_portrait_web_path(name: str, campaign_id: str | None = None) -> str:
    """
    Get the web URL path for a portrait.

    Args:
        name: Character/NPC name
        campaign_id: Campaign ID for campaign-specific lookup

    Returns:
        Web URL path (e.g., "/assets/portraits/campaigns/axiom/kira_vance.png")
    """
    slug = slugify(name)

    # Check campaign-specific first
    if campaign_id:
        campaign_dir = get_portraits_dir(campaign_id)
        if (campaign_dir / f"{slug}.png").exists():
            return f"/assets/portraits/campaigns/{campaign_id}/{slug}.png"

    # Fall back to global directory
    global_dir = get_portraits_dir(None)
    if (global_dir / f"{slug}.png").exists():
        return f"/assets/portraits/npcs/{slug}.png"

    # Default placeholder
    return "/assets/portraits/placeholder.svg"


def sync_portraits(campaign_id: str | None = None) -> dict:
    """
    Sync portraits to wiki directory.

    For campaign-specific portraits, syncs from web UI to wiki.

    Args:
        campaign_id: Campaign ID for campaign-specific sync

    Returns:
        dict with 'copied_to_wiki' list of filenames
    """
    source_dir = get_portraits_dir(campaign_id)
    wiki_dir = get_wiki_portraits_dir(campaign_id)

    result = {"copied_to_wiki": []}

    if not source_dir.exists():
        return result

    wiki_dir.mkdir(parents=True, exist_ok=True)

    for portrait in source_dir.glob("*.png"):
        wiki_dest = wiki_dir / portrait.name
        if not wiki_dest.exists() or wiki_dest.stat().st_size != portrait.stat().st_size:
            try:
                shutil.copy2(portrait, wiki_dest)
                result["copied_to_wiki"].append(portrait.name)
            except Exception:
                pass

    return result
