"""Resource handlers for factions."""

import json
from pathlib import Path


def _load_faction_data(data_dir: Path, faction_id: str) -> dict:
    """Load faction JSON file."""
    faction_file = data_dir / "factions" / f"{faction_id}.json"
    if faction_file.exists():
        return json.loads(faction_file.read_text())
    return {}


def get_faction_lore(data_dir: Path, faction_id: str) -> dict:
    """Get faction lore/history."""
    data = _load_faction_data(data_dir, faction_id)
    return {
        "id": faction_id,
        "name": data.get("name", faction_id.replace("_", " ").title()),
        "tagline": data.get("tagline", ""),
        "ideology": data.get("ideology", ""),
        "history": data.get("history", ""),
        "structure": data.get("structure", ""),
        "symbols": data.get("symbols", []),
        "aesthetic": data.get("aesthetic", ""),
        "key_events": data.get("key_events", []),
    }


def get_faction_npcs(data_dir: Path, faction_id: str) -> dict:
    """Get faction NPC archetypes."""
    data = _load_faction_data(data_dir, faction_id)
    return {
        "faction": faction_id,
        "archetypes": data.get("archetypes", []),
    }


def get_faction_operations(data_dir: Path, faction_id: str) -> dict:
    """Get faction operations/goals."""
    data = _load_faction_data(data_dir, faction_id)
    return {
        "faction": faction_id,
        "goals": data.get("goals", []),
        "methods": data.get("methods", []),
        "current_tensions": data.get("current_tensions", []),
    }


def get_relationships(data_dir: Path) -> dict:
    """Get inter-faction relationships."""
    rel_file = data_dir / "relationships.json"
    if rel_file.exists():
        return json.loads(rel_file.read_text())
    return {"relationships": []}
