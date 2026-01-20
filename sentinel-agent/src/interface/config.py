"""
User configuration persistence.

Stores settings like preferred backend and model in a JSON file.
"""

import json
from pathlib import Path
from typing import TypedDict


class Config(TypedDict, total=False):
    """User configuration."""
    backend: str  # lmstudio, claude, openrouter, etc.
    model: str | None  # Model name for LM Studio/Ollama
    animate_banner: bool  # Show animated banner on startup
    show_status_bar: bool  # Show persistent status bar


DEFAULT_CONFIG: Config = {
    "backend": "claude",  # Default to Claude for best experience
    "model": None,
    "animate_banner": True,
    "show_status_bar": True,
}


def get_config_path(campaigns_dir: Path | str = "campaigns") -> Path:
    """Get path to config file."""
    return Path(campaigns_dir) / ".sentinel_config.json"


def load_config(campaigns_dir: Path | str = "campaigns") -> Config:
    """Load config from file, or return defaults if not found."""
    path = get_config_path(campaigns_dir)

    if not path.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with open(path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        # Merge with defaults to handle missing keys
        config = DEFAULT_CONFIG.copy()
        config.update(saved)
        return config
    except (json.JSONDecodeError, IOError):
        return DEFAULT_CONFIG.copy()


def save_config(config: Config, campaigns_dir: Path | str = "campaigns") -> bool:
    """Save config to file. Returns True on success."""
    path = get_config_path(campaigns_dir)

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except IOError:
        return False


def set_backend(backend: str, campaigns_dir: Path | str = "campaigns") -> None:
    """Save backend preference."""
    config = load_config(campaigns_dir)
    config["backend"] = backend
    save_config(config, campaigns_dir)


def set_model(model: str | None, campaigns_dir: Path | str = "campaigns") -> None:
    """Save model preference."""
    config = load_config(campaigns_dir)
    config["model"] = model
    save_config(config, campaigns_dir)


def set_animate_banner(animate: bool, campaigns_dir: Path | str = "campaigns") -> None:
    """Save banner animation preference."""
    config = load_config(campaigns_dir)
    config["animate_banner"] = animate
    save_config(config, campaigns_dir)


def set_show_status_bar(show: bool, campaigns_dir: Path | str = "campaigns") -> None:
    """Save status bar visibility preference."""
    config = load_config(campaigns_dir)
    config["show_status_bar"] = show
    save_config(config, campaigns_dir)
