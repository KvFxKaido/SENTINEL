"""
SENTINEL Textual TUI - Three-column layout with collapsible docks.

Main stream in center, SELF dock (left) and WORLD dock (right) toggle with [ and ].
"""
import asyncio
import random
import subprocess
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Input, RichLog, LoadingIndicator, Button
from textual.screen import Screen, ModalScreen
from textual.binding import Binding
from textual.reactive import reactive
from textual import work
from rich.text import Text
from rich.panel import Panel
from rich.padding import Padding
from rich.console import Console, RenderableType

from textual.events import Key

from ..state import CampaignManager, get_event_bus, EventType, GameEvent
from ..state.schema import Campaign, Standing, Character, DormantThread
from ..agent import SentinelAgent
from ..context import StrainTier, format_strain_notice
from ..llm import CLI_BACKENDS
from ..llm.base import Message
from ..tools.hinge_detector import detect_hinge
from .choices import parse_response, ChoiceBlock
from .config import load_config, set_backend, set_model as save_model
from .glyphs import g, energy_bar
from .command_registry import get_registry
from .commands import register_all_commands
from .tui_commands import register_tui_handlers
from .codec import render_codec_frame, NPCDisplay, Disposition, FACTION_COLORS


def center_renderable(renderable: RenderableType, content_width: int, container_width: int) -> Padding:
    """Center a renderable by adding left padding."""
    if container_width <= content_width:
        return Padding(renderable, (0, 0))
    left_pad = (container_width - content_width) // 2
    return Padding(renderable, (0, 0, 0, left_pad))


# =============================================================================
# Command Autocorrect
# =============================================================================

# Cache for valid commands (populated lazily from registry)
_valid_commands_cache: list[str] | None = None


def get_valid_commands() -> list[str]:
    """
    Get all valid command names from the registry.

    Lazily populates from the command registry on first call,
    so new commands are automatically available for autocomplete.
    """
    global _valid_commands_cache
    if _valid_commands_cache is None:
        registry = get_registry()
        # Get all command names (includes aliases like /exit → /quit)
        _valid_commands_cache = sorted(registry._commands.keys())
    return _valid_commands_cache


def invalidate_command_cache() -> None:
    """Clear the command cache (call after registering new commands)."""
    global _valid_commands_cache
    _valid_commands_cache = None

class ChoiceButtons(Static):
    """Displays clickable choice buttons when GM presents options."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._choices: list[str] = []
        self._callback = None

    def set_choices(self, choices: list[str], callback):
        """Set choices and callback for selection."""
        self._choices = choices
        self._callback = callback
        self._render_buttons()

    def clear_choices(self):
        """Clear all choices."""
        self._choices = []
        self._callback = None
        self.update("")

    def _render_buttons(self):
        """Render choice buttons."""
        if not self._choices:
            self.update("")
            return

        lines = [f"[{Theme.DIM}]Press 1-{len(self._choices[:9])} to select:[/{Theme.DIM}]"]
        for i, choice in enumerate(self._choices[:9], 1):  # Max 9 choices
            # Truncate long choices
            display = choice[:55] + "..." if len(choice) > 55 else choice
            lines.append(f"  [{Theme.ACCENT}][{i}][/{Theme.ACCENT}] {display}")

        self.update(Text.from_markup("\n".join(lines)))

    def select(self, num: int):
        """Select a choice by number."""
        if 1 <= num <= len(self._choices) and self._callback:
            self._callback(num)


class SuggestionDisplay(Static):
    """Shows command suggestions as user types."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._suggestions: list[str] = []
        self._selected: int = 0

    def update_suggestions(self, prefix: str):
        """Update suggestions based on input prefix."""
        if not prefix.startswith("/"):
            self._suggestions = []
            self.update("")
            return

        cmd_part = prefix.split(" ", 1)[0].lower()
        self._suggestions = [c for c in get_valid_commands() if c.startswith(cmd_part) and c != cmd_part]
        self._selected = 0

        if self._suggestions:
            display = " ".join(f"[{Theme.ACCENT}]{s}[/{Theme.ACCENT}]" for s in self._suggestions[:5])
            if len(self._suggestions) > 5:
                display += f" [dim]+{len(self._suggestions) - 5} more[/dim]"
            self.update(Text.from_markup(f"[dim]Tab:[/dim] {display}"))
        else:
            self.update("")

    def get_selected(self) -> str | None:
        """Get currently selected suggestion."""
        if self._suggestions:
            return self._suggestions[self._selected]
        return None

    def next_suggestion(self):
        """Cycle to next suggestion."""
        if self._suggestions:
            self._selected = (self._selected + 1) % len(self._suggestions)


class ThinkingPanel(Static):
    """Shows GM processing stages during response generation."""

    # Stage icons and labels
    STAGES = {
        EventType.STAGE_BUILDING_CONTEXT: ("◇", "Building context"),
        EventType.STAGE_RETRIEVING_LORE: ("◇", "Retrieving lore"),
        EventType.STAGE_PACKING_PROMPT: ("◇", "Packing prompt"),
        EventType.STAGE_AWAITING_LLM: ("◆", "Awaiting response"),
        EventType.STAGE_EXECUTING_TOOL: ("⚡", "Executing tool"),
        EventType.STAGE_PROCESSING_DONE: ("✓", "Complete"),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_stage: EventType | None = None
        self._detail: str = ""
        self._completed_stages: list[EventType] = []
        self._visible: bool = False

    def show_stage(self, stage: EventType, detail: str = "", **extra):
        """Update to show a processing stage."""
        # Track completed stages
        if self._current_stage and self._current_stage != stage:
            if self._current_stage not in self._completed_stages:
                self._completed_stages.append(self._current_stage)

        self._current_stage = stage
        self._detail = detail
        self._visible = True
        self.add_class("visible")
        self.refresh_display()

    def hide(self):
        """Hide the thinking panel."""
        self._visible = False
        self._current_stage = None
        self._completed_stages = []
        self.remove_class("visible")
        self.update("")

    def refresh_display(self):
        """Render the current thinking state."""
        if not self._visible or not self._current_stage:
            return

        display = Text()
        display.append("┌─ GM PROCESSING ", style=Theme.BORDER)
        display.append("─" * 40, style=Theme.BORDER)
        display.append("┐\n", style=Theme.BORDER)
        display.append("│ ", style=Theme.BORDER)

        # Show completed stages
        for completed in self._completed_stages[-3:]:  # Last 3 completed
            icon, label = self.STAGES.get(completed, ("○", "Unknown"))
            display.append(f"  {icon} ", style=Theme.DIM)
            display.append(f"{label}", style=Theme.DIM)

        # Show current stage
        if self._current_stage:
            icon, label = self.STAGES.get(self._current_stage, ("◆", "Processing"))
            display.append(f"  {icon} ", style=f"bold {Theme.ACCENT}")
            display.append(f"{label}", style=f"bold {Theme.ACCENT}")
            if self._detail:
                display.append(f" — {self._detail}", style=Theme.TEXT)

        # Pad and close
        display.append(" " * 10, style=Theme.BG)
        display.append("│\n", style=Theme.BORDER)
        display.append("└", style=Theme.BORDER)
        display.append("─" * 56, style=Theme.BORDER)
        display.append("┘", style=Theme.BORDER)

        self.update(display)


class CommandInput(Input):
    """Custom Input that handles Tab completion and history."""

    BINDINGS = [
        Binding("ctrl+i", "complete", "Complete", show=False, priority=True),
        Binding("up", "history_back", "History Back", show=False, priority=True),
        Binding("down", "history_forward", "History Forward", show=False, priority=True),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tab_matches: list[str] = []
        self._tab_index: int = 0
        self._tab_prefix: str = ""
        self._history: list[str] = []
        self._history_index: int = -1
        self._history_buffer: str = ""
        self._suggestion_display: SuggestionDisplay | None = None

    def set_suggestion_display(self, display: SuggestionDisplay):
        """Link to suggestion display widget."""
        self._suggestion_display = display

    def set_history(self, history: list[str]):
        """Set the command history."""
        self._history = history

    def add_to_history(self, cmd: str):
        """Add command to history."""
        if cmd and (not self._history or self._history[-1] != cmd):
            self._history.append(cmd)
        self._history_index = -1
        self._history_buffer = ""

    def watch_value(self, value: str) -> None:
        """Called when input value changes - update suggestions."""
        if self._suggestion_display:
            self._suggestion_display.update_suggestions(value)

    def action_complete(self) -> None:
        """Tab completion action."""
        self._do_tab_completion()

    def action_history_back(self) -> None:
        """Navigate back in history."""
        self._history_back()

    def action_history_forward(self) -> None:
        """Navigate forward in history."""
        self._history_forward()

    def _on_key(self, event: Key) -> None:
        """Intercept keys before Input processes them."""
        if event.key == "tab":
            event.prevent_default()
            event.stop()
            self._do_tab_completion()
            return
        if event.key == "up":
            event.prevent_default()
            event.stop()
            self._history_back()
            return
        if event.key == "down":
            event.prevent_default()
            event.stop()
            self._history_forward()
            return
        # Number keys for choice selection (when input is empty)
        if event.key in "123456789" and not self.value:
            # Check if app has choices available
            app = self.app
            if hasattr(app, 'last_choices') and app.last_choices:
                event.prevent_default()
                event.stop()
                num = int(event.key)
                if hasattr(app, '_select_choice'):
                    app._select_choice(num)
                return
        # Reset tab state on other keys
        self._tab_matches = []
        self._tab_index = 0
        self._tab_prefix = ""
        # Let parent handle the key
        super()._on_key(event)

    def _do_tab_completion(self):
        """Perform tab completion for commands."""
        current = self.value

        if not current.startswith("/"):
            return

        parts = current.split(" ", 1)
        cmd_part = parts[0].lower()
        args_part = " " + parts[1] if len(parts) > 1 else ""

        if cmd_part == self._tab_prefix and self._tab_matches:
            self._tab_index = (self._tab_index + 1) % len(self._tab_matches)
            completed = self._tab_matches[self._tab_index]
        else:
            self._tab_prefix = cmd_part
            self._tab_matches = [c for c in get_valid_commands() if c.startswith(cmd_part)]
            if not self._tab_matches:
                return
            self._tab_index = 0
            completed = self._tab_matches[0]

        self.value = completed + args_part
        self.cursor_position = len(completed)

    def _history_back(self):
        """Navigate back in history."""
        if not self._history:
            return
        if self._history_index == -1:
            self._history_buffer = self.value
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.value = self._history[-(self._history_index + 1)]
            self.cursor_position = len(self.value)

    def _history_forward(self):
        """Navigate forward in history."""
        if self._history_index == -1:
            return
        self._history_index -= 1
        if self._history_index == -1:
            self.value = self._history_buffer
        else:
            self.value = self._history[-(self._history_index + 1)]
        self.cursor_position = len(self.value)


def autocorrect_command(cmd: str) -> tuple[str, str | None]:
    """
    Autocorrect a mistyped command using the command registry.

    Returns (corrected_cmd, suggestion_message) where suggestion_message
    is None if no correction was needed.
    """
    registry = get_registry()

    # Check if command exists in registry
    if registry.get(cmd):
        return cmd, None

    # Use registry's autocorrect (fuzzy matching)
    corrected, msg = registry.autocorrect(cmd)
    if corrected != cmd:
        return corrected, f"Autocorrected '{cmd}' → '{corrected}'"

    # Check for exact match
    if cmd in get_valid_commands():
        return cmd, None

    # Fallback to difflib fuzzy matching
    matches = get_close_matches(cmd, get_valid_commands(), n=1, cutoff=0.6)
    if matches:
        corrected = matches[0]
        return corrected, f"Autocorrected '{cmd}' → '{corrected}'"

    return cmd, None


# =============================================================================
# Theme: AMOLED black + clinical white
# =============================================================================

class Theme:
    """Color theme constants."""
    BG = "#000000"              # AMOLED black
    BORDER = "#b3b3b3"          # Pale surgical white (grey70)
    TEXT = "#e5e5e5"            # Soft white (grey90)
    ACCENT = "#5f8787"          # Muted cyan
    WARNING = "#af8700"         # Muted amber
    DANGER = "#870000"          # Rusted red
    DIM = "#5f5f87"             # Grey-blue

    # Standing colors
    HOSTILE = "#870000"
    UNFRIENDLY = "#af5f00"
    NEUTRAL = "#b3b3b3"
    FRIENDLY = "#5f875f"
    ALLIED = "#5f8787"


# =============================================================================
# Widgets: Context Bar (Strain Tracker)
# =============================================================================

class ContextBar(Static):
    """HUD-style context pressure display below header."""

    # Map StrainTier to display info
    TIER_DISPLAY = {
        StrainTier.NORMAL: ("NOMINAL", Theme.FRIENDLY),
        StrainTier.STRAIN_I: ("STRAIN I", Theme.WARNING),
        StrainTier.STRAIN_II: ("STRAIN II", Theme.DANGER),
        StrainTier.STRAIN_III: ("STRAIN III", Theme.HOSTILE),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pressure: float = 0.0
        self.tokens_used: int = 0
        self.tokens_max: int = 13000  # Default pack budget
        self.strain_tier: StrainTier = StrainTier.NORMAL
        self.section_info: str = ""
        self.backend: str | None = None  # Track current backend for cloud detection

    def set_backend(self, backend: str | None):
        """Set the current backend (affects display mode)."""
        self.backend = backend
        self.refresh_display()

    def update_from_pack_info(self, pack_info):
        """Update from agent's PackInfo object."""
        if pack_info is None:
            self.pressure = 0.0
            self.tokens_used = 0
            self.strain_tier = StrainTier.NORMAL
            self.section_info = ""
        else:
            self.pressure = pack_info.pressure
            self.tokens_used = pack_info.total_tokens
            self.tokens_max = pack_info.total_budget
            self.strain_tier = pack_info.strain_tier
            # Build section summary
            sections = []
            for s in pack_info.sections:
                if s.token_count > 0:
                    mark = "✓" if not s.truncated else "…"
                    sections.append(f"{s.section.value}:{mark}")
            self.section_info = " ".join(sections[:4])  # Show first 4
        self.refresh_display()

    def update_pressure(self, pressure: float, tokens_used: int = 0, tokens_max: int = 13000):
        """Manual update (fallback when no pack info available)."""
        self.pressure = pressure
        self.tokens_used = tokens_used
        self.tokens_max = tokens_max
        self.strain_tier = StrainTier.from_pressure(pressure)
        self.section_info = ""
        self.refresh_display()

    def refresh_display(self):
        # Cloud backends (Gemini, Codex, Claude) have massive context — no pressure tracking
        if self.backend and self.backend in CLI_BACKENDS:
            display = Text()
            display.append("CONTEXT ", style=Theme.DIM)
            display.append("[", style=Theme.ACCENT)
            display.append("☁ CLOUD", style=f"bold {Theme.ACCENT}")
            display.append("]", style=Theme.ACCENT)
            display.append(" ∞ ", style=Theme.ACCENT)
            display.append("UNLIMITED", style=f"bold {Theme.FRIENDLY}")
            # Show backend name
            backend_display = self.backend.upper()
            if self.backend == "gemini":
                backend_display = "GEMINI (1M ctx)"
            elif self.backend == "codex":
                backend_display = "CODEX (128K+ ctx)"
            elif self.backend == "claude":
                backend_display = "CLAUDE (200K ctx)"
            display.append(f"  │ {backend_display}", style=Theme.DIM)
            self.update(display)
            return

        # Local backends — show pressure bar and strain tracking
        tier_name, tier_color = self.TIER_DISPLAY.get(
            self.strain_tier, ("NOMINAL", Theme.FRIENDLY)
        )

        # Visual bar (20 chars wide)
        bar_width = 20
        filled = int(min(1.0, self.pressure) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Percentage
        pct = int(self.pressure * 100)

        # Build display
        display = Text()
        display.append("CONTEXT ", style=Theme.DIM)
        display.append(f"[{bar}]", style=tier_color)
        display.append(f" {pct}% ", style=tier_color)
        display.append(tier_name, style=f"bold {tier_color}")

        if self.tokens_used > 0:
            display.append(f"  {self.tokens_used:,}/{self.tokens_max:,} tokens", style=Theme.DIM)

        if self.section_info:
            display.append(f"  │ {self.section_info}", style=Theme.DIM)

        self.update(display)


# =============================================================================
# Widgets: Header Bar
# =============================================================================

class HeaderBar(Static):
    """Top header: SENTINEL + Campaign + Seed + Character + Phase + Clock."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.campaign: Campaign | None = None

    def update_campaign(self, campaign: Campaign | None):
        self.campaign = campaign
        self.refresh_display()

    def refresh_display(self):
        # Clock
        now = datetime.now()
        clock = now.strftime("%H:%M")

        # Build header text
        header = Text()
        header.append("◈ ", style=f"bold {Theme.ACCENT}")
        header.append("SENTINEL", style=f"bold {Theme.ACCENT}")
        header.append(f"  {g('bullet')}  ", style=Theme.DIM)
        header.append(clock, style=Theme.TEXT)

        if self.campaign:
            seed = self.campaign.meta.id[:4].upper()
            header.append(f"  {g('bullet')}  ", style=Theme.DIM)
            header.append(self.campaign.meta.name, style=Theme.TEXT)
            header.append(f"  {g('bullet')}  Seed {seed}", style=Theme.DIM)

            # Session count
            session = self.campaign.meta.session_count
            header.append(f"  {g('bullet')}  ", style=Theme.DIM)
            header.append(f"S{session:02d}", style=Theme.TEXT)

            if self.campaign.characters:
                char = self.campaign.characters[0]
                name = char.callsign if char.callsign else char.name
                phase = self.campaign.session.phase.value.upper() if self.campaign.session else "FREE ROAM"
                header.append("  |  ", style=Theme.DIM)
                header.append(name, style=f"bold {Theme.ACCENT}")
                header.append(f"  {g('bullet')}  ", style=Theme.DIM)
                header.append(phase, style=Theme.TEXT)

        self.update(header)


# =============================================================================
# Widgets: SELF Dock (Left)
# =============================================================================

class SelfDock(Static):
    """Left dock: Character details, loadout, enhancements."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.campaign: Campaign | None = None

    def update_campaign(self, campaign: Campaign | None):
        self.campaign = campaign
        self.refresh_display()

    def refresh_display(self):
        if not self.campaign or not self.campaign.characters:
            self.update(Panel(
                Text.from_markup(f"[{Theme.DIM}]No character[/{Theme.DIM}]"),
                title=f"[bold {Theme.TEXT}]SELF[/bold {Theme.TEXT}]",
                border_style=Theme.BORDER,
                style=f"on {Theme.BG}",
            ))
            return

        char = self.campaign.characters[0]
        name = char.callsign if char.callsign else char.name
        background = char.background.value

        # Energy
        energy = char.social_energy.current
        if energy > 50:
            e_color = Theme.FRIENDLY
        elif energy > 25:
            e_color = Theme.WARNING
        else:
            e_color = Theme.DANGER
        bar = energy_bar(energy, width=8)

        lines = [
            f"[bold {Theme.ACCENT}]{name}[/bold {Theme.ACCENT}]",
            f"[{Theme.DIM}][{background}][/{Theme.DIM}]",
            f"[{Theme.TEXT}]-- STATUS --[/{Theme.TEXT}]",
            f"[{Theme.DIM}]Pistachios[/{Theme.DIM}]",
            f"[{e_color}]{bar} {energy}%[/{e_color}]",
        ]

        # Loadout
        lines.append(f"[{Theme.TEXT}]-- LOADOUT --[/{Theme.TEXT}]")
        gear_items = []
        if self.campaign.session and self.campaign.session.loadout:
            for gear_id in self.campaign.session.loadout[:4]:
                gear_item = next((gi for gi in char.gear if gi.id == gear_id), None)
                if gear_item:
                    gear_items.append(gear_item)
        elif char.gear:
            gear_items = char.gear[:4]

        if gear_items:
            for gear_item in gear_items:
                mark = "x" if not gear_item.used else " "
                lines.append(f"[{mark}] {gear_item.name[:18]}")
        else:
            lines.append(f"[{Theme.DIM}](none)[/{Theme.DIM}]")

        # Enhancements
        lines.append(f"[{Theme.TEXT}]-- ENHANCEMENTS --[/{Theme.TEXT}]")
        if char.enhancements:
            for enh in char.enhancements[:2]:
                lines.append(f"[{Theme.ACCENT}]{enh.name[:18]}[/{Theme.ACCENT}]")
        elif char.refused_enhancements:
            for ref in char.refused_enhancements[:2]:
                lines.append(f"[{Theme.DIM}][Refused][/{Theme.DIM}]")
                lines.append(f"[{Theme.DIM}]{ref.name[:18]}[/{Theme.DIM}]")
        else:
            lines.append(f"[{Theme.DIM}](none)[/{Theme.DIM}]")

        self.update(Panel(
            Text.from_markup("\n".join(lines)),
            title=f"[bold {Theme.TEXT}]SELF[/bold {Theme.TEXT}]",
            border_style=Theme.BORDER,
            style=f"on {Theme.BG}",
            padding=(0, 1),
        ))


# =============================================================================
# Widgets: WORLD Dock (Right)
# =============================================================================

class WorldDock(Static):
    """Right dock: Faction standings, pending threads."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.campaign: Campaign | None = None

    def update_campaign(self, campaign: Campaign | None):
        self.campaign = campaign
        self.refresh_display()

    def refresh_display(self):
        if not self.campaign:
            self.update(Panel(
                Text.from_markup(f"[{Theme.DIM}]No campaign[/{Theme.DIM}]"),
                title=f"[bold {Theme.TEXT}]WORLD[/bold {Theme.TEXT}]",
                border_style=Theme.BORDER,
                style=f"on {Theme.BG}",
            ))
            return

        standing_values = {
            "Hostile": -2, "Unfriendly": -1, "Neutral": 0,
            "Friendly": 1, "Allied": 2,
        }
        standing_colors = {
            -2: Theme.HOSTILE, -1: Theme.UNFRIENDLY, 0: Theme.NEUTRAL,
            1: Theme.FRIENDLY, 2: Theme.ALLIED,
        }
        standing_labels = {
            -2: "Hostile", -1: "Unfriendly", 0: "Neutral",
            1: "Friendly", 2: "Allied"
        }

        lines = [f"[{Theme.TEXT}]-- STANDINGS --[/{Theme.TEXT}]"]

        factions_data = []
        for faction_field in ['nexus', 'ember_colonies', 'lattice', 'convergence',
                              'covenant', 'wanderers', 'cultivators', 'steel_syndicate',
                              'witnesses', 'architects', 'ghost_networks']:
            faction_data = getattr(self.campaign.factions, faction_field, None)
            if faction_data:
                name = faction_field.replace('_', ' ').title()
                if len(name) > 12:
                    name = name[:11] + "."
                value = standing_values.get(faction_data.standing.value, 0)
                factions_data.append((name, value))

        # Sort by absolute value, show non-neutral first
        factions_data.sort(key=lambda x: (x[1] == 0, -abs(x[1])))

        shown = 0
        for name, value in factions_data:
            if shown >= 5:
                break
            if value != 0 or shown < 3:  # Show non-neutral + up to 3 neutral
                blocks = value + 3
                bar = g("centered") * blocks + g("frayed") * (5 - blocks)
                color = standing_colors.get(value, Theme.NEUTRAL)
                label = standing_labels.get(value, "Neutral")
                lines.append(f"[{Theme.TEXT}]{name}[/{Theme.TEXT}]")
                lines.append(f"[{color}]{bar} {label}[/{color}]")
                shown += 1

        # Threads
        lines.append(f"[{Theme.TEXT}]-- THREADS --[/{Theme.TEXT}]")
        if self.campaign.dormant_threads:
            for thread in self.campaign.dormant_threads[:3]:
                sev = thread.severity.value
                if sev == "major":
                    icon = f"[{Theme.DANGER}]{g('warning')}[/{Theme.DANGER}]"
                elif sev == "moderate":
                    icon = f"[{Theme.WARNING}]{g('warning')}[/{Theme.WARNING}]"
                else:
                    icon = f"[{Theme.DIM}]{g('thread')}[/{Theme.DIM}]"
                lines.append(f"{icon} {thread.origin[:14]}...")
        else:
            lines.append(f"[{Theme.DIM}](none)[/{Theme.DIM}]")

        self.update(Panel(
            Text.from_markup("\n".join(lines)),
            title=f"[bold {Theme.TEXT}]WORLD[/bold {Theme.TEXT}]",
            border_style=Theme.BORDER,
            style=f"on {Theme.BG}",
            padding=(0, 1),
        ))


class PressurePanel(Static):
    """Footer panel showing urgent world pressure."""

    URGENCY_STYLE = {
        "urgent": (Theme.DANGER, "🔴"),
        "soon": (Theme.WARNING, "🟡"),
        "later": (Theme.DIM, "🟢"),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._items: list[dict] = []
        self._session: int = 0

    def update_items(self, items: list[dict], session: int) -> None:
        self._items = items
        self._session = session
        self.refresh_display()

    def refresh_display(self) -> None:
        lines = [f"[{Theme.TEXT}]-- PRESSURE --[/{Theme.TEXT}]"]

        if not self._items:
            lines.append(f"[{Theme.DIM}](clear)[/{Theme.DIM}]")
        else:
            for item in self._items:
                urgency = item.get("urgency", "later")
                color, dot = self.URGENCY_STYLE.get(urgency, (Theme.DIM, "🟢"))
                label = item.get("label", "")
                countdown = item.get("countdown", "")
                lines.append(f"[{color}]{dot} {label}{countdown}[/{color}]")

        self.update(Panel(
            Text.from_markup("\n".join(lines)),
            title=f"[bold {Theme.TEXT}]PRESSURE[/bold {Theme.TEXT}]",
            border_style=Theme.BORDER,
            style=f"on {Theme.BG}",
            padding=(0, 1),
        ))


class SessionBridgeScreen(ModalScreen):
    """Screen showing changes since last session."""

    CSS = f"""
    SessionBridgeScreen {{
        align: center middle;
        background: {Theme.BG} 80%;
    }}

    #bridge-dialog {{
        width: 60;
        height: auto;
        max-height: 80%;
        background: {Theme.BG};
        border: tall {Theme.BORDER};
        padding: 1 2;
    }}

    #bridge-title {{
        text-align: center;
        color: {Theme.ACCENT};
        text-style: bold;
        border-bottom: solid {Theme.DIM};
        margin-bottom: 1;
    }}

    .bridge-item {{
        padding: 0 1;
        color: {Theme.TEXT};
    }}

    #bridge-continue {{
        width: 100%;
        margin-top: 2;
    }}
    """

    def __init__(self, changes: list[dict]):
        super().__init__()
        self.changes = changes

    def compose(self) -> ComposeResult:
        yield Container(
            Static("WHILE YOU WERE AWAY", id="bridge-title"),
            Vertical(id="bridge-list"),
            Button("Access Terminal", variant="primary", id="bridge-continue"),
            id="bridge-dialog"
        )

    def on_mount(self):
        container = self.query_one("#bridge-list")
        if not self.changes:
            container.mount(Static("No significant changes detected.", classes="bridge-item"))
            return

        for change in self.changes:
            # Determine icon/color based on type
            icon = "•"
            color = Theme.TEXT

            if change.get("category") == "faction":
                icon = g("faction")
                color = Theme.WARNING
            elif change.get("category") == "npc":
                icon = g("npc_active")
                color = Theme.ACCENT
            elif change.get("category") == "thread":
                icon = g("warning")
                color = Theme.DANGER

            text = Text()
            text.append(f"{icon} ", style=color)
            text.append(change["text"])

            container.mount(Static(text, classes="bridge-item"))

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "bridge-continue":
            self.dismiss()


class CodecInterrupt(ModalScreen):
    """MGS-style NPC interrupt modal."""

    CSS = f"""
    CodecInterrupt {{
        align: center middle;
        background: {Theme.BG} 90%;
    }}

    #interrupt-dialog {{
        width: 70;
        height: auto;
        max-height: 80%;
        background: {Theme.BG};
        border: heavy {Theme.ACCENT};
        padding: 1 2;
    }}

    #interrupt-header {{
        text-align: center;
        color: {Theme.WARNING};
        text-style: bold;
        margin-bottom: 1;
    }}

    #codec-frame {{
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }}

    #interrupt-message {{
        padding: 1;
        background: #1a1a1a;
        border: solid {Theme.DIM};
        margin-bottom: 1;
    }}

    #interrupt-buttons {{
        width: 100%;
        height: 3;
        align: center middle;
    }}

    #interrupt-buttons Button {{
        margin: 0 1;
    }}
    """

    BINDINGS = [
        Binding("r", "respond", "Respond"),
        Binding("i", "ignore", "Ignore"),
        Binding("l", "later", "Later"),
        Binding("escape", "later", "Later"),
    ]

    def __init__(
        self,
        npc_name: str,
        faction: str,
        message: str,
        urgency: str = "medium",
        disposition: str = "neutral",
    ):
        super().__init__()
        self.npc_name = npc_name
        self.faction = faction
        self.message = message
        self.urgency = urgency
        self.disposition = disposition

    def compose(self) -> ComposeResult:
        # Build codec frame for NPC
        try:
            disp_enum = Disposition(self.disposition.lower())
        except ValueError:
            disp_enum = Disposition.NEUTRAL

        npc_display = NPCDisplay(
            name=self.npc_name,
            faction=self.faction,
            disposition=disp_enum,
        )
        codec_art = render_codec_frame(npc_display, width=40, scanlines=False)

        # Urgency header styling
        urgency_color = {
            "critical": Theme.DANGER,
            "high": Theme.WARNING,
            "medium": Theme.ACCENT,
        }.get(self.urgency, Theme.ACCENT)

        yield Container(
            Static(f"[{urgency_color}]:: INCOMING TRANSMISSION ::[/{urgency_color}]", id="interrupt-header"),
            Static(codec_art, id="codec-frame"),
            Static(f'"{self.message}"', id="interrupt-message"),
            Horizontal(
                Button("Respond [R]", variant="primary", id="btn-respond"),
                Button("Ignore [I]", variant="warning", id="btn-ignore"),
                Button("Later [L]", variant="default", id="btn-later"),
                id="interrupt-buttons",
            ),
            id="interrupt-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-respond":
            self.dismiss("respond")
        elif button_id == "btn-ignore":
            self.dismiss("ignore")
        elif button_id == "btn-later":
            self.dismiss("later")

    def action_respond(self) -> None:
        self.dismiss("respond")

    def action_ignore(self) -> None:
        self.dismiss("ignore")

    def action_later(self) -> None:
        self.dismiss("later")


# =============================================================================
# Main Application
# =============================================================================

class SentinelTUI(App):
    """SENTINEL TUI with collapsible SELF/WORLD docks."""

    CSS = f"""
    Screen {{
        background: {Theme.BG};
        layout: grid;
        grid-size: 1;
        grid-rows: 2 1 1fr;
    }}

    #header {{
        height: 2;
        padding: 0 1;
        background: {Theme.BG};
        border-bottom: solid {Theme.DIM};
    }}

    #context-bar {{
        height: 1;
        padding: 0 1;
        background: {Theme.BG};
        text-align: center;
    }}

    #main-container {{
        width: 100%;
        height: 100%;
    }}

    #self-dock {{
        width: 20vw;
        min-width: 24;
        max-width: 32;
        height: 100%;
        padding: 0;
    }}

    #self-dock.hidden {{
        display: none;
    }}

    /* Reactive visual feedback for state changes */
    #self-dock.energy-drain {{
        background: {Theme.DANGER} 15%;
    }}

    #self-dock.energy-gain {{
        background: {Theme.FRIENDLY} 15%;
    }}

    #self-dock.energy-critical {{
        background: {Theme.DANGER} 20%;
        border: solid {Theme.DANGER};
    }}

    #world-dock.faction-shift {{
        background: {Theme.WARNING} 15%;
        border: solid {Theme.WARNING};
    }}

    #world-dock.thread-surfaced {{
        background: {Theme.WARNING} 12%;
        border: solid {Theme.WARNING};
    }}

    #pressure-panel.consequence-urgent {{
        background: {Theme.DANGER} 12%;
        border: solid {Theme.DANGER};
    }}

    #center-column {{
        width: 1fr;
        min-width: 40;
        height: 100%;
        align: center top;
    }}

    #console-wrapper {{
        width: 100%;
        max-width: 120;
        height: 100%;
    }}

    #output-log {{
        height: 1fr;
        width: 100%;
        background: {Theme.BG};
        border: solid {Theme.BORDER};
    }}

    #thinking-panel {{
        height: auto;
        max-height: 5;
        width: 100%;
        background: {Theme.BG};
        color: {Theme.ACCENT};
        display: none;
        padding: 0 1;
        margin-bottom: 1;
    }}

    #thinking-panel.visible {{
        display: block;
    }}

    #thinking-indicator {{
        height: 1;
        width: 100%;
        background: {Theme.BG};
        color: {Theme.ACCENT};
        display: none;
    }}

    #thinking-indicator.visible {{
        display: block;
    }}

    #choice-buttons {{
        width: 100%;
        height: auto;
        max-height: 12;
        background: {Theme.BG};
        padding: 0 1;
        margin-bottom: 1;
    }}

    #suggestions {{
        height: 1;
        width: 100%;
        background: {Theme.BG};
        padding: 0 1;
    }}

    #input-row {{
        height: 3;
        width: 100%;
        layout: horizontal;
    }}

    #input-container {{
        width: 1fr;
        height: 3;
        background: {Theme.BG};
        border: round {Theme.DIM};
    }}

    #button-bar {{
        width: auto;
        height: 3;
        layout: horizontal;
        margin-left: 1;
    }}

    .action-btn {{
        min-width: 6;
        height: 3;
        margin: 0 0 0 1;
        background: {Theme.BG};
        color: {Theme.ACCENT};
        border: tall {Theme.DIM};
    }}

    .action-btn:hover {{
        background: #1a1a1a;
        color: {Theme.TEXT};
    }}

    .action-btn:focus {{
        border: tall {Theme.ACCENT};
    }}

    #world-column {{
        width: 20vw;
        min-width: 24;
        max-width: 32;
        height: 100%;
        layout: vertical;
    }}

    #world-column.hidden {{
        display: none;
    }}

    #world-dock {{
        height: 1fr;
        padding: 0;
    }}

    #pressure-panel {{
        height: auto;
        max-height: 10;
        padding: 0;
        margin-top: 1;
    }}

    /* Input styling */
    #main-input {{
        background: {Theme.BG};
        color: white;
        border: none;
        height: 1;
        width: 100%;
    }}

    #main-input:focus {{
        background: {Theme.BG};
        color: white;
    }}

    /* RichLog styling */
    #output-log {{
        background: {Theme.BG};
        scrollbar-color: {Theme.DIM};
        scrollbar-color-hover: {Theme.ACCENT};
        scrollbar-color-active: {Theme.ACCENT};
    }}

    #center-column {{
        align: center top;
    }}
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("f2", "toggle_docks", "F2 Panels", show=True),
        # Number keys for choice selection
        Binding("1", "select_choice_1", "Choice 1", show=False),
        Binding("2", "select_choice_2", "Choice 2", show=False),
        Binding("3", "select_choice_3", "Choice 3", show=False),
        Binding("4", "select_choice_4", "Choice 4", show=False),
        Binding("5", "select_choice_5", "Choice 5", show=False),
        Binding("6", "select_choice_6", "Choice 6", show=False),
        Binding("7", "select_choice_7", "Choice 7", show=False),
        Binding("8", "select_choice_8", "Choice 8", show=False),
        Binding("9", "select_choice_9", "Choice 9", show=False),
    ]

    # Reactive dock visibility
    docks_visible = reactive(True)

    # Threshold for auto-hiding docks (chars)
    NARROW_THRESHOLD = 80

    def __init__(self, local_mode: bool = False):
        self._user_wants_docks = True  # User's explicit preference
        self._auto_hidden = False      # Whether we auto-hid due to narrow terminal
        super().__init__()
        self.manager: CampaignManager | None = None
        self.agent: SentinelAgent | None = None
        self.conversation: list[Message] = []
        self.last_choices: ChoiceBlock | None = None
        self.prompts_dir: Path | None = None
        self.lore_dir: Path | None = None
        self.local_mode = local_mode
        # Command history (for persistence)
        self._history: list[str] = []
        self._history_file = Path("campaigns") / ".tui_history"
        self._history_max = 500  # Max entries to keep
        self._load_history()

    def _load_history(self):
        """Load command history from file."""
        try:
            if self._history_file.exists():
                self._history = self._history_file.read_text().strip().split("\n")
                # Filter empty lines
                self._history = [h for h in self._history if h.strip()]
        except Exception:
            self._history = []

    def _save_history(self):
        """Save command history to file."""
        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
            # Keep only last N entries
            to_save = self._history[-self._history_max:]
            self._history_file.write_text("\n".join(to_save))
        except Exception:
            pass  # Silently fail if we can't save

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield HeaderBar(id="header")
        yield ContextBar(id="context-bar")

        with Horizontal(id="main-container"):
            yield SelfDock(id="self-dock")
            with Container(id="center-column"):
                with Vertical(id="console-wrapper"):
                    yield RichLog(id="output-log", highlight=True, markup=True)
                    yield ThinkingPanel(id="thinking-panel")
                    yield LoadingIndicator(id="thinking-indicator")
                    yield ChoiceButtons(id="choice-buttons")
                    yield SuggestionDisplay(id="suggestions")
                    with Horizontal(id="input-row"):
                        with Container(id="input-container"):
                            yield CommandInput(placeholder="> What do you do?", id="main-input")
                        with Container(id="button-bar"):
                            yield Button("Save", id="btn-save", classes="action-btn")
                            yield Button("Clear", id="btn-clear", classes="action-btn")
                            yield Button("Copy", id="btn-copy", classes="action-btn")
            with Container(id="world-column"):
                yield WorldDock(id="world-dock")
                yield PressurePanel(id="pressure-panel")

    def on_mount(self):
        """Initialize when app mounts."""
        self.initialize_game()
        self.refresh_all_panels()

        # Start clock timer (update every 30 seconds)
        self.set_interval(30, self._update_clock)

        # Subscribe to game events for reactive UI updates
        bus = get_event_bus()
        bus.on(EventType.FACTION_CHANGED, self._on_faction_changed)
        bus.on(EventType.NPC_ADDED, self._on_npc_changed)
        bus.on(EventType.NPC_DISPOSITION_CHANGED, self._on_npc_changed)
        bus.on(EventType.THREAD_QUEUED, self._on_thread_queued)
        bus.on(EventType.THREAD_SURFACED, self._on_thread_surfaced)
        bus.on(EventType.ENHANCEMENT_CALLED, self._on_enhancement_called)
        bus.on(EventType.CAMPAIGN_LOADED, self._on_campaign_loaded)
        bus.on(EventType.SOCIAL_ENERGY_CHANGED, self._on_energy_changed)

        # Processing stage events (for thinking panel)
        bus.on(EventType.STAGE_BUILDING_CONTEXT, self._on_processing_stage)
        bus.on(EventType.STAGE_RETRIEVING_LORE, self._on_processing_stage)
        bus.on(EventType.STAGE_PACKING_PROMPT, self._on_processing_stage)
        bus.on(EventType.STAGE_AWAITING_LLM, self._on_processing_stage)
        bus.on(EventType.STAGE_EXECUTING_TOOL, self._on_processing_stage)
        bus.on(EventType.STAGE_PROCESSING_DONE, self._on_processing_done)

        # Pass history and suggestion display to command input
        cmd_input = self.query_one("#main-input", CommandInput)
        cmd_input.set_history(self._history)
        cmd_input.set_suggestion_display(self.query_one("#suggestions", SuggestionDisplay))
        cmd_input.focus()

        # Show startup animation (runs as worker to avoid blocking)
        self._run_startup_animation()

    def _update_clock(self):
        """Update the header clock."""
        self.query_one("#header", HeaderBar).refresh_display()

    @work
    async def _run_startup_animation(self):
        """Run startup animation as async worker."""
        # Wait for layout to compute
        await asyncio.sleep(0.1)

        # Check if animation is enabled
        config = load_config(self.campaigns_dir)
        animate = config.get("animate_banner", True)

        log = self.query_one("#output-log", RichLog)
        wrapper = self.query_one("#console-wrapper")
        # Try wrapper width, fall back to log, subtract for borders
        raw_width = wrapper.size.width or log.size.width or 80
        log_width = raw_width - 4

        # Hexagon structure: (left_margin, left_char, inner_gap, right_char, text)
        # The hexagon halves will slide together during assembly
        hex_parts = [
            (12, "/",  0, "\\", ""),
            (11, "/",  2, "\\", ""),
            (10, "/",  4, "\\", "       S E N T I N E L"),
            (10, "\\", 4, "/",  "       T A C T I C A L   T T R P G"),
            (11, "\\", 2, "/",  ""),
            (12, "\\", 0, "/",  ""),
        ]

        # Glitch characters for interference effect
        glitch_chars = "░▒▓│┃╎╏"

        def render_assembly_frame(offset: int, text_reveal: float = 0.0) -> Text:
            """Render hexagon with both halves offset from center.

            offset > 0: halves are apart (left char shifted left, right char shifted right)
            offset = 0: halves are docked at final position
            """
            text = Text()
            # We need enough width to hold the spread-out hexagon
            line_width = 55 + (offset * 2)

            for left_margin, left_char, inner_gap, right_char, label in hex_parts:
                # Build line as character array for precise positioning
                line_chars = [' '] * line_width

                # Left char: starts further left, moves right as offset decreases
                left_pos = max(0, left_margin - offset)
                # Right char: starts further right, moves left as offset decreases
                right_pos = left_margin + 1 + inner_gap + offset

                if left_pos < line_width:
                    line_chars[left_pos] = left_char
                if right_pos < line_width:
                    line_chars[right_pos] = right_char

                # Add interference sparks in the gap during assembly
                if offset > 0:
                    gap_center = (left_pos + right_pos) // 2
                    for spark_offset in range(-2, 3):
                        spark_pos = gap_center + spark_offset
                        if 0 < spark_pos < line_width - 1 and random.random() < 0.15:
                            line_chars[spark_pos] = random.choice(glitch_chars)

                line = ''.join(line_chars).rstrip()
                text.append(line, style=f"bold {Theme.ACCENT}")

                # Add text label with typewriter reveal
                if label and text_reveal > 0:
                    chars_to_show = int(len(label) * text_reveal)
                    visible = label[:chars_to_show]
                    text.append(visible, style=f"bold {Theme.TEXT}")

                text.append("\n")
            return text

        def render_final() -> Text:
            """Render final static banner."""
            text = Text()
            for left_margin, left_char, inner_gap, right_char, label in hex_parts:
                line = " " * left_margin + left_char + " " * inner_gap + right_char
                text.append(line, style=f"bold {Theme.ACCENT}")
                if label:
                    text.append(label, style=f"bold {Theme.TEXT}")
                text.append("\n")
            return text

        # Banner width (widest line)
        banner_width = 55

        if animate:
            # Phase 1: Hexagon assembly (halves slide together from opposite sides)
            max_offset = 12  # How far each half starts from final position
            assembly_frames = 12
            for i in range(assembly_frames + 1):
                progress = i / assembly_frames
                # Ease-out with slight bounce for satisfying "dock" feel
                eased = 1 - (1 - progress) ** 2.5
                offset = int(max_offset * (1 - eased))
                log.clear()
                # Width expands when halves are apart
                frame_width = banner_width + (offset * 2)
                log.write(center_renderable(render_assembly_frame(offset), frame_width, log_width))
                await asyncio.sleep(0.055)

            # Phase 2: Lock-in flash (brief bright pulse when pieces dock)
            for color in [Theme.TEXT, Theme.ACCENT]:
                log.clear()
                flash_text = Text()
                for left_margin, left_char, inner_gap, right_char, _ in hex_parts:
                    line = " " * left_margin + left_char + " " * inner_gap + right_char
                    flash_text.append(line + "\n", style=f"bold {color}")
                log.write(center_renderable(flash_text, banner_width, log_width))
                await asyncio.sleep(0.04)

            # Phase 3: Split-flap text reveal (like old departure boards)
            # Each character "flips" through stages: ─ → ▄ → █ → ▀ → final
            flip_stages = ['─', '▄', '█', '▀']

            def render_flip_frame(wave_progress: float) -> Text:
                """Render hexagon with split-flap text animation."""
                text = Text()
                for left_margin, left_char, inner_gap, right_char, label in hex_parts:
                    # Hexagon part (fully assembled)
                    line = " " * left_margin + left_char + " " * inner_gap + right_char
                    text.append(line, style=f"bold {Theme.ACCENT}")

                    # Split-flap text reveal
                    if label:
                        flip_text = []
                        for i, char in enumerate(label):
                            if char == ' ':
                                flip_text.append(' ')
                                continue

                            # Wave effect: each char starts flipping at staggered time
                            # wave_progress 0→1 overall, char_start staggers by position
                            char_start = i * 0.03  # Delay per character
                            char_progress = (wave_progress - char_start) / 0.15  # Duration per flip
                            char_progress = max(0.0, min(1.0, char_progress))

                            if char_progress >= 1.0:
                                # Fully revealed
                                flip_text.append(char)
                            elif char_progress <= 0.0:
                                # Not started yet
                                flip_text.append(' ')
                            else:
                                # Mid-flip: show intermediate stage
                                stage_idx = int(char_progress * len(flip_stages))
                                stage_idx = min(stage_idx, len(flip_stages) - 1)
                                flip_text.append(flip_stages[stage_idx])

                        text.append(''.join(flip_text), style=f"bold {Theme.TEXT}")

                    text.append("\n")
                return text

            # Run the flip animation
            flip_frames = 20
            for i in range(flip_frames + 1):
                wave_progress = i / flip_frames
                # Slight ease-out for satisfying settle
                wave_progress = 1 - (1 - wave_progress) ** 1.5
                log.clear()
                log.write(center_renderable(render_flip_frame(wave_progress), banner_width, log_width))
                await asyncio.sleep(0.035)

            # Brief pause then show final clean render
            await asyncio.sleep(0.08)
            log.clear()
            log.write(center_renderable(render_final(), banner_width, log_width))

        # Clear and show welcome
        log.clear()
        log.write(center_renderable(render_final(), banner_width, log_width))
        log.write("")
        log.write(Text.from_markup(
            f"[{Theme.DIM}]Type /help for commands, or /new to start.[/{Theme.DIM}]"
        ))
        log.write(Text.from_markup(
            f"[{Theme.DIM}]Press F2 to toggle side panels.[/{Theme.DIM}]"
        ))
        log.write("")

        if self.agent:
            info = self.agent.backend_info
            if info["available"]:
                log.write(Text.from_markup(
                    f"[{Theme.ACCENT}]Backend:[/{Theme.ACCENT}] {info['backend']} "
                    f"[{Theme.DIM}]({info['model']})[/{Theme.DIM}]"
                ))
            else:
                log.write(Text.from_markup(
                    f"[{Theme.WARNING}]No LLM backend available[/{Theme.WARNING}]"
                ))

    def initialize_game(self):
        """Initialize game systems."""
        base_dir = Path(__file__).parent.parent.parent.parent
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"
        campaigns_dir = Path("campaigns")
        self.campaigns_dir = campaigns_dir
        self.lore_dir = base_dir / "lore"

        config = load_config(campaigns_dir)
        saved_backend = config.get("backend", "auto")
        saved_model = config.get("model")

        self.manager = CampaignManager(campaigns_dir)

        # Initialize command registry with CLI and TUI handlers
        register_all_commands()
        register_tui_handlers()
        self.agent = SentinelAgent(
            self.manager,
            prompts_dir=self.prompts_dir,
            lore_dir=self.lore_dir if self.lore_dir.exists() else None,
            backend=saved_backend,
            local_mode=self.local_mode,
        )

        if saved_model and self.agent and self.agent.client and self.agent.backend in ("lmstudio", "ollama"):
            if hasattr(self.agent.client, "set_model"):
                try:
                    self.agent.client.set_model(saved_model)
                except Exception:
                    pass

    def refresh_all_panels(self):
        """Refresh all panels with current campaign state."""
        campaign = self.manager.current if self.manager else None

        self.query_one("#header", HeaderBar).update_campaign(campaign)
        self.query_one("#self-dock", SelfDock).update_campaign(campaign)
        self.query_one("#world-dock", WorldDock).update_campaign(campaign)
        self._refresh_pressure_panel()

        # Update context bar from agent's pack info (real token counts)
        context_bar = self.query_one("#context-bar", ContextBar)
        # Set backend for cloud detection (affects display mode)
        if self.agent:
            context_bar.set_backend(self.agent.backend)
        if self.agent and hasattr(self.agent, '_last_pack_info'):
            context_bar.update_from_pack_info(self.agent._last_pack_info)
        else:
            context_bar.update_pressure(0.0)

    def _trim_pressure_text(self, text: str, limit: int = 26) -> str:
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "..."

    def _build_pressure_items(self) -> list[dict]:
        if not self.manager or not self.manager.current:
            return []

        campaign = self.manager.current
        current_session = campaign.meta.session_count
        items: list[dict] = []

        def add_item(label: str, urgency: str, score: int, countdown: str = "") -> None:
            items.append({
                "label": label,
                "urgency": urgency,
                "countdown": countdown,
                "score": score,
            })

        # Leverage demands
        for demand in self.manager.get_pending_demands():
            urgency = demand.get("urgency", "pending")
            weight = demand.get("weight", "medium")
            tier = "urgent" if urgency in ("critical", "urgent") else "soon"
            if urgency == "pending" and weight in ("light",):
                tier = "later"

            countdown = ""
            deadline_session = demand.get("deadline_session")
            if deadline_session is not None:
                if current_session > deadline_session:
                    countdown = " OVERDUE"
                    score = 500
                elif current_session == deadline_session:
                    countdown = " DUE"
                    score = 450
                else:
                    remaining = deadline_session - current_session
                    countdown = f" T-{remaining}"
                    score = 300 + max(0, 20 - remaining)
            else:
                score = 260 if tier == "urgent" else 200 if tier == "soon" else 140

            label = f"Demand: {demand.get('faction', '?')} - {self._trim_pressure_text(demand.get('demand', ''))}"
            add_item(label, tier, score, countdown)

        # Dormant threads
        for thread in campaign.dormant_threads:
            age = max(0, current_session - thread.created_session)
            if thread.severity.value == "major" or age >= 4:
                tier = "urgent"
                score = 240 + age
            elif thread.severity.value == "moderate" or age >= 2:
                tier = "soon"
                score = 180 + age
            else:
                tier = "later"
                score = 120 + age

            label = f"Thread: {self._trim_pressure_text(thread.origin)}"
            add_item(label, tier, score)

        # NPC silence
        for npc in campaign.npcs.active:
            if not npc.interactions:
                continue
            silence = current_session - npc.interactions[-1].session
            if silence < 2:
                continue
            if silence >= 4:
                tier = "urgent"
                score = 220 + silence
            else:
                tier = "soon"
                score = 170 + silence
            label = f"NPC: {self._trim_pressure_text(npc.name, 18)} quiet {silence}s"
            add_item(label, tier, score)

        items.sort(key=lambda item: item["score"], reverse=True)
        for item in items:
            item.pop("score", None)
        return items[:5]

    def _refresh_pressure_panel(self) -> bool:
        panel = self.query_one("#pressure-panel", PressurePanel)
        if not self.manager or not self.manager.current:
            panel.update_items([], 0)
            return False

        items = self._build_pressure_items()
        panel.update_items(items, self.manager.current.meta.session_count)
        return any(item.get("urgency") == "urgent" for item in items)

    def watch_docks_visible(self, visible: bool):
        """React to dock visibility changes."""
        self_dock = self.query_one("#self-dock")
        world_dock = self.query_one("#world-column")
        if visible:
            self_dock.remove_class("hidden")
            world_dock.remove_class("hidden")
        else:
            self_dock.add_class("hidden")
            world_dock.add_class("hidden")

    def action_toggle_docks(self):
        """Toggle both docks visibility (user preference)."""
        self._user_wants_docks = not self._user_wants_docks
        # Only actually show if terminal is wide enough
        if self._user_wants_docks and not self._auto_hidden:
            self.docks_visible = True
        else:
            self.docks_visible = False

    def on_resize(self, event) -> None:
        """Handle terminal resize - auto-hide docks on narrow terminals."""
        width = event.size.width

        if width < self.NARROW_THRESHOLD:
            # Terminal too narrow - auto-hide docks
            if not self._auto_hidden:
                self._auto_hidden = True
                self.docks_visible = False
                # Notify user (only on transition to narrow)
                try:
                    log = self.query_one("#output-log", RichLog)
                    log.write(Text.from_markup(
                        f"[{Theme.DIM}][ Panels hidden - terminal narrow ({width} chars) ][/{Theme.DIM}]"
                    ))
                except Exception:
                    pass
        else:
            # Terminal wide enough - restore if user wants them
            if self._auto_hidden:
                self._auto_hidden = False
                if self._user_wants_docks:
                    self.docks_visible = True

    # -------------------------------------------------------------------------
    # Event Bus Handlers (reactive UI updates)
    # -------------------------------------------------------------------------

    def _on_faction_changed(self, event: GameEvent) -> None:
        """Handle faction standing changes - update WORLD dock with visual feedback."""
        # Use call_from_thread since events may fire from worker threads
        def update():
            try:
                world_dock = self.query_one("#world-dock", WorldDock)
                world_dock.update_campaign(self.manager.current if self.manager else None)
                world_dock.refresh_display()

                # Visual feedback - highlight the dock briefly
                world_dock.add_class("faction-shift")
                self.set_timer(1.5, lambda: world_dock.remove_class("faction-shift"))

                # Log the change to output
                log = self.query_one("#output-log", RichLog)
                faction = event.data.get("faction", "?")
                before = event.data.get("before", "?")
                after = event.data.get("after", "?")
                log.write(Text.from_markup(
                    f"[{Theme.WARNING}][ {faction}: {before} → {after} ][/{Theme.WARNING}]"
                ))
            except Exception:
                pass

        self.call_from_thread(update)

    def _on_npc_changed(self, event: GameEvent) -> None:
        """Handle NPC changes - update WORLD dock."""
        def update():
            try:
                world_dock = self.query_one("#world-dock", WorldDock)
                world_dock.update_campaign(self.manager.current if self.manager else None)
                world_dock.refresh_display()
                self._refresh_pressure_panel()
            except Exception:
                pass

        self.call_from_thread(update)

    def _on_thread_queued(self, event: GameEvent) -> None:
        """Handle new dormant thread - update WORLD dock."""
        def update():
            try:
                world_dock = self.query_one("#world-dock", WorldDock)
                world_dock.update_campaign(self.manager.current if self.manager else None)
                world_dock.refresh_display()
                self._refresh_pressure_panel()

                # Notify in output
                log = self.query_one("#output-log", RichLog)
                severity = event.data.get("severity", "moderate")
                log.write(Text.from_markup(
                    f"[{Theme.WARNING}][ Thread queued ({severity}) ][/{Theme.WARNING}]"
                ))
            except Exception:
                pass

        self.call_from_thread(update)

    def _on_thread_surfaced(self, event: GameEvent) -> None:
        """Handle a surfaced thread - update WORLD dock with visual feedback."""
        def update():
            try:
                world_dock = self.query_one("#world-dock", WorldDock)
                world_dock.update_campaign(self.manager.current if self.manager else None)
                world_dock.refresh_display()

                world_dock.add_class("thread-surfaced")
                self.set_timer(1.0, lambda: world_dock.remove_class("thread-surfaced"))

                pressure_panel = self.query_one("#pressure-panel", PressurePanel)
                has_urgent = self._refresh_pressure_panel()
                if has_urgent:
                    pressure_panel.add_class("consequence-urgent")
                    self.set_timer(1.0, lambda: pressure_panel.remove_class("consequence-urgent"))

                log = self.query_one("#output-log", RichLog)
                severity = event.data.get("severity", "moderate")
                log.write(Text.from_markup(
                    f"[{Theme.WARNING}][ Thread surfaced ({severity}) ][/{Theme.WARNING}]"
                ))
            except Exception:
                pass

        self.call_from_thread(update)

    def _on_campaign_loaded(self, event: GameEvent) -> None:
        """Handle campaign load - refresh all panels."""
        def update():
            try:
                self.refresh_all_panels()

                # Check for session changes (bridge)
                if self.manager:
                    changes = self.manager.get_session_changes()
                    if changes:
                        self.push_screen(SessionBridgeScreen(changes))

            except Exception:
                pass

        self.call_from_thread(update)

    def _on_energy_changed(self, event: GameEvent) -> None:
        """Handle social energy changes - update SELF dock with visual feedback."""
        def update():
            try:
                self_dock = self.query_one("#self-dock", SelfDock)
                self_dock.update_campaign(self.manager.current if self.manager else None)

                # Visual feedback - highlight based on gain/drain
                delta = event.data.get("delta", 0)
                before = event.data.get("before", 0)
                after = event.data.get("after", 0)

                if delta < 0:
                    # Energy drained - red highlight
                    self_dock.add_class("energy-drain")
                    self.set_timer(1.5, lambda: self_dock.remove_class("energy-drain"))
                elif delta > 0:
                    # Energy gained - green highlight
                    self_dock.add_class("energy-gain")
                    self.set_timer(1.5, lambda: self_dock.remove_class("energy-gain"))

                if after <= 25 and delta != 0:
                    self_dock.add_class("energy-critical")
                    self.set_timer(1.0, lambda: self_dock.remove_class("energy-critical"))

                # Log the change
                log = self.query_one("#output-log", RichLog)
                color = Theme.FRIENDLY if delta > 0 else Theme.DANGER
                direction = "+" if delta > 0 else ""
                log.write(Text.from_markup(
                    f"[{color}][ Energy: {before}% → {after}% ({direction}{delta}) ][/{color}]"
                ))
            except Exception:
                pass

        self.call_from_thread(update)

    def _on_enhancement_called(self, event: GameEvent) -> None:
        """Handle leverage calls - refresh pressure panel with urgency pulse."""
        def update():
            try:
                pressure_panel = self.query_one("#pressure-panel", PressurePanel)
                has_urgent = self._refresh_pressure_panel()
                if has_urgent:
                    pressure_panel.add_class("consequence-urgent")
                    self.set_timer(1.0, lambda: pressure_panel.remove_class("consequence-urgent"))

                log = self.query_one("#output-log", RichLog)
                faction = event.data.get("faction", "?")
                demand = self._trim_pressure_text(event.data.get("demand", ""), 32)
                log.write(Text.from_markup(
                    f"[{Theme.DANGER}][ Leverage called by {faction}: {demand} ][/{Theme.DANGER}]"
                ))
            except Exception:
                pass

        self.call_from_thread(update)

    def _on_processing_stage(self, event: GameEvent) -> None:
        """Handle processing stage updates - update thinking panel."""
        def update():
            try:
                panel = self.query_one("#thinking-panel", ThinkingPanel)
                panel.show_stage(
                    event.type,
                    detail=event.data.get("detail", ""),
                    **event.data
                )
            except Exception:
                pass

        self.call_from_thread(update)

    def _on_processing_done(self, event: GameEvent) -> None:
        """Handle processing complete - hide thinking panel."""
        def update():
            try:
                panel = self.query_one("#thinking-panel", ThinkingPanel)
                # Brief delay to show "Complete" before hiding
                self.set_timer(0.5, panel.hide)
            except Exception:
                pass

        self.call_from_thread(update)

    # -------------------------------------------------------------------------
    # Codec Interrupt System
    # -------------------------------------------------------------------------

    async def show_codec_interrupt(
        self,
        npc_name: str,
        faction: str,
        message: str,
        urgency: str = "medium",
        disposition: str = "neutral",
    ) -> str:
        """Show codec interrupt modal and return player's choice."""
        result = await self.push_screen_wait(
            CodecInterrupt(
                npc_name=npc_name,
                faction=faction,
                message=message,
                urgency=urgency,
                disposition=disposition,
            )
        )
        return result  # "respond", "ignore", or "later"

    def _handle_tool_result(self, tool_name: str, result: dict) -> None:
        """Handle tool execution result, checking for interrupt signals."""
        # Check if this is an interrupt signal
        if result.get("interrupt"):
            # Schedule showing the interrupt modal
            self.call_later(self._show_pending_interrupt, result)
            return

        # Other tool result handling can be added here as needed

    async def _show_pending_interrupt(self, interrupt_data: dict) -> None:
        """Show the codec interrupt modal."""
        npc_name = interrupt_data.get("npc_name", "Unknown")
        message = interrupt_data.get("message", "...")
        urgency = interrupt_data.get("urgency", "medium")

        # Get NPC details if available
        faction = "unknown"
        disposition = "neutral"
        if self.manager and self.manager.current:
            for npc in self.manager.current.npcs.active:
                if npc.name.lower() == npc_name.lower():
                    faction = npc.faction.value if hasattr(npc.faction, 'value') else str(npc.faction)
                    disposition = npc.disposition.value if hasattr(npc.disposition, 'value') else str(npc.disposition)
                    break

        response = await self.show_codec_interrupt(
            npc_name=npc_name,
            faction=faction,
            message=message,
            urgency=urgency,
            disposition=disposition,
        )

        # Handle the response
        await self._handle_interrupt_response(response, npc_name)

    async def _handle_interrupt_response(self, response: str, npc_name: str) -> None:
        """Handle player's response to interrupt."""
        log = self.query_one("#output-log", RichLog)

        if response == "respond":
            log.write(Text.from_markup(
                f"[{Theme.ACCENT}]You open the channel to {npc_name}...[/{Theme.ACCENT}]"
            ))
            # The GM will continue the conversation naturally

        elif response == "ignore":
            log.write(Text.from_markup(
                f"[{Theme.WARNING}]You ignore {npc_name}'s transmission.[/{Theme.WARNING}]"
            ))
            # Add memory trigger to NPC
            if self.manager and self.manager.current:
                for npc in self.manager.current.npcs.active:
                    if npc.name.lower() == npc_name.lower():
                        # Add to NPC's memory triggers
                        if not hasattr(npc, 'memory_triggers'):
                            npc.memory_triggers = []
                        npc.memory_triggers.append({
                            "tag": "ignored_interrupt",
                            "session": self.manager.current.meta.session_count,
                        })
                        self.manager.save_campaign()
                        break

        elif response == "later":
            log.write(Text.from_markup(
                f"[{Theme.DIM}]You'll deal with {npc_name} later...[/{Theme.DIM}]"
            ))

    # Number key actions for choice selection
    def action_select_choice_1(self):
        """Select choice 1."""
        self._select_choice(1)

    def action_select_choice_2(self):
        """Select choice 2."""
        self._select_choice(2)

    def action_select_choice_3(self):
        """Select choice 3."""
        self._select_choice(3)

    def action_select_choice_4(self):
        """Select choice 4."""
        self._select_choice(4)

    def action_select_choice_5(self):
        """Select choice 5."""
        self._select_choice(5)

    def action_select_choice_6(self):
        """Select choice 6."""
        self._select_choice(6)

    def action_select_choice_7(self):
        """Select choice 7."""
        self._select_choice(7)

    def action_select_choice_8(self):
        """Select choice 8."""
        self._select_choice(8)

    def action_select_choice_9(self):
        """Select choice 9."""
        self._select_choice(9)

    def _select_choice(self, num: int):
        """Handle choice selection by number key."""
        # Only select if input is not focused (so typing numbers still works)
        input_widget = self.query_one("#main-input", CommandInput)
        if input_widget.has_focus and input_widget.value:
            return  # Let user type numbers in input

        if self.last_choices and 1 <= num <= len(self.last_choices.options):
            asyncio.create_task(self.handle_choice(num))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id
        log = self.query_one("#output-log", RichLog)

        if button_id == "btn-save":
            if self.manager and self.manager.current:
                self.manager.save_campaign()
                log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Campaign saved[/{Theme.FRIENDLY}]"))
            else:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))

        elif button_id == "btn-clear":
            self.conversation.clear()
            if self.agent and hasattr(self.agent, '_conversation_window'):
                self.agent._conversation_window.blocks.clear()
                self.agent._last_pack_info = None
            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Conversation cleared[/{Theme.FRIENDLY}]"))
            self.refresh_all_panels()

        elif button_id == "btn-copy":
            self._copy_last_output(log)

        # Refocus input after button click
        self.query_one("#main-input", CommandInput).focus()

    def _copy_last_output(self, log: RichLog, *, tail_lines: int = 200) -> None:
        """Copy the last chunk of output log to the clipboard."""
        lines = getattr(log, "lines", None)
        if not lines:
            log.write(Text.from_markup(f"[{Theme.WARNING}]Nothing to copy[/{Theme.WARNING}]"))
            return

        tail = lines[-tail_lines:]
        text = "\n".join(line.text.rstrip() for line in tail).rstrip()
        if not text:
            log.write(Text.from_markup(f"[{Theme.WARNING}]Nothing to copy[/{Theme.WARNING}]"))
            return

        try:
            subprocess.run(["clip"], input=text.encode("utf-8"), check=True)
            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Copied last output[/{Theme.FRIENDLY}]"))
        except Exception as e:
            log.write(Text.from_markup(f"[{Theme.DANGER}]Copy failed: {e}[/{Theme.DANGER}]"))

    async def _ping_backend(self, log: RichLog) -> None:
        """Send a tiny request to verify backend/model connectivity."""
        if not self.agent or not self.agent.client:
            log.write(Text.from_markup(f"[{Theme.WARNING}]No LLM backend active[/{Theme.WARNING}]"))
            return

        backend = self.agent.backend
        model = getattr(self.agent.client, "model_name", "unknown")
        log.write(Text.from_markup(f"[{Theme.DIM}]Pinging {backend} ({model})...[/{Theme.DIM}]"))

        try:
            # Keep it tiny to avoid confusing context-length issues with connectivity.
            response = await asyncio.to_thread(
                self.agent.client.chat_with_tools,
                messages=[Message(role="user", content="Reply with exactly: pong")],
                system="Reply with exactly: pong",
                tools=None,
                tool_executor=lambda n, a: {},
                max_iterations=1,
                temperature=0.0,
                max_tokens=5,
            )
            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]pong ✓[/{Theme.FRIENDLY}]"))
            if response and response.strip().lower() != "pong":
                log.write(Text.from_markup(f"[{Theme.DIM}]Got: {response.strip()}[/{Theme.DIM}]"))
        except Exception as e:
            log.write(Text.from_markup(f"[{Theme.DANGER}]Ping failed: {e}[/{Theme.DANGER}]"))

    def exit(self, *args, **kwargs):
        """Save history before exiting."""
        self._save_history()
        super().exit(*args, **kwargs)

    async def on_input_submitted(self, event: Input.Submitted):
        """Handle input submission."""
        user_input = event.value.strip()
        event.input.value = ""

        if not user_input:
            return

        # Add to history via CommandInput
        cmd_input = self.query_one("#main-input", CommandInput)
        cmd_input.add_to_history(user_input)
        # Also keep in app for persistence
        if not self._history or self._history[-1] != user_input:
            self._history.append(user_input)

        log = self.query_one("#output-log", RichLog)

        # Echo input
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]>[/bold {Theme.TEXT}] {user_input}"))

        # Handle commands
        if user_input.startswith("/"):
            await self.handle_command(user_input)
        elif user_input.isdigit() and self.last_choices:
            await self.handle_choice(int(user_input))
        else:
            self.handle_action(user_input)  # @work decorator, don't await

        self.refresh_all_panels()

    async def handle_command(self, cmd_input: str):
        """Handle slash commands."""
        log = self.query_one("#output-log", RichLog)
        parts = cmd_input.split()
        cmd = parts[0].lower()
        args = parts[1:]

        # Autocorrect typos
        corrected_cmd, correction_msg = autocorrect_command(cmd)
        if correction_msg:
            log.write(Text.from_markup(f"[{Theme.DIM}]{correction_msg}[/{Theme.DIM}]"))
            cmd = corrected_cmd

        # Try registry dispatch first
        registry = get_registry()
        cmd_obj = registry.get(cmd)
        if cmd_obj and cmd_obj.tui_handler:
            registry.record_usage(cmd)
            cmd_obj.tui_handler(self, log, args)
            return

        # Unknown command fallback
        log.write(Text.from_markup(f"[{Theme.WARNING}]Unknown command: {cmd}[/{Theme.WARNING}]"))

    async def handle_choice(self, choice_num: int):
        """Handle numbered choice selection."""
        if not self.last_choices:
            return

        if 1 <= choice_num <= len(self.last_choices.options):
            selected = self.last_choices.options[choice_num - 1]
            if "something else" in selected.lower():
                return
            action = selected if selected.startswith("I ") else f"I {selected.lower()}"
            self.last_choices = None
            self._clear_choice_buttons()  # Clear the choice buttons widget
            self.handle_action(action)  # @work decorator, don't await

    def _update_choice_buttons(self, options: list[str]):
        """Update the choice buttons widget with current options."""
        choice_buttons = self.query_one("#choice-buttons", ChoiceButtons)
        choice_buttons.set_choices(options, lambda num: asyncio.create_task(self.handle_choice(num)))

    def _clear_choice_buttons(self):
        """Clear the choice buttons widget."""
        choice_buttons = self.query_one("#choice-buttons", ChoiceButtons)
        choice_buttons.clear_choices()

    @work(thread=True)
    async def handle_action(self, user_input: str):
        """Handle regular action input (runs in thread)."""
        log = self.query_one("#output-log", RichLog)
        # Get content width (subtract borders/padding)
        log_width = (log.size.width or 80) - 4

        if not self.manager or not self.manager.current:
            self.call_from_thread(log.write, Text.from_markup(
                f"[{Theme.WARNING}]Start or load a campaign first[/{Theme.WARNING}]"
            ))
            return

        if not self.agent or not self.agent.is_available:
            self.call_from_thread(log.write, Text.from_markup(
                f"[{Theme.WARNING}]No LLM backend available[/{Theme.WARNING}]"
            ))
            return

        # Show thinking indicator
        indicator = self.query_one("#thinking-indicator", LoadingIndicator)
        self.call_from_thread(indicator.add_class, "visible")

        try:
            # Detect hinge
            hinge = detect_hinge(user_input)
            if hinge:
                self.call_from_thread(log.write, Text.from_markup(
                    f"[{Theme.WARNING}]{g('hinge')} HINGE MOMENT[/{Theme.WARNING}]"
                ))

            # Get response
            response = self.agent.respond(user_input, self.conversation)
            self.conversation.append(Message(role="user", content=user_input))
            self.conversation.append(Message(role="assistant", content=response))

            # Log hinge
            if hinge:
                self.manager.log_hinge_moment(
                    situation=f"Player: {user_input[:100]}",
                    choice=hinge.matched_text,
                    reasoning=f"{hinge.category.value}, {hinge.severity}",
                )

            # Parse and display
            narrative, choices = parse_response(response)
            self.last_choices = choices

            # Display narrative in a centered panel
            panel_width = 70
            narrative_panel = Panel(
                narrative,
                border_style=Theme.BORDER,
                style=f"on {Theme.BG}",
                padding=(0, 1),
                width=panel_width,
            )
            self.call_from_thread(log.write, "")
            self.call_from_thread(log.write, center_renderable(narrative_panel, panel_width, log_width))

            # Display choices
            if choices:
                choice_lines = "\n".join(
                    f"[{Theme.ACCENT}]{i}.[/{Theme.ACCENT}] {opt}"
                    for i, opt in enumerate(choices.options, 1)
                )
                choice_panel = Panel(
                    Text.from_markup(choice_lines),
                    title=f"[bold {Theme.TEXT}]CHOICE[/bold {Theme.TEXT}]",
                    border_style=Theme.ACCENT,
                    style=f"on {Theme.BG}",
                    padding=(0, 1),
                    width=panel_width,
                )
                self.call_from_thread(log.write, center_renderable(choice_panel, panel_width, log_width))

                # Update choice buttons widget
                self.call_from_thread(self._update_choice_buttons, choices.options)
            else:
                # Clear choice buttons if no choices
                self.call_from_thread(self._clear_choice_buttons)

            self.call_from_thread(log.write, "")

        except Exception as e:
            self.call_from_thread(log.write, Text.from_markup(
                f"[{Theme.DANGER}]Error: {e}[/{Theme.DANGER}]"
            ))
        finally:
            # Hide thinking indicator
            self.call_from_thread(indicator.remove_class, "visible")

        # Refresh panels on main thread
        self.call_from_thread(self.refresh_all_panels)

    @work(thread=True)
    async def _simulate_preview(self, args: list[str]):
        """Preview consequences of a proposed action without committing."""
        from .shared import simulate_preview

        log = self.query_one("#output-log", RichLog)
        log_width = (log.size.width or 80) - 4
        indicator = self.query_one("#thinking-indicator", LoadingIndicator)

        if not self.agent or not self.agent.client:
            self.call_from_thread(log.write, Text.from_markup(
                f"[{Theme.WARNING}]No LLM backend available[/{Theme.WARNING}]"
            ))
            return

        action = " ".join(args)

        # Show header
        self.call_from_thread(log.write, Text.from_markup(
            f"\n[bold {Theme.PRIMARY}]◈ ACTION PREVIEW ◈[/bold {Theme.PRIMARY}]"
        ))
        self.call_from_thread(log.write, Text.from_markup(
            f"[{Theme.DIM}]Proposed action:[/{Theme.DIM}] {action}\n"
        ))

        # Show thinking indicator
        self.call_from_thread(indicator.add_class, "visible")

        try:
            result = simulate_preview(self.manager, self.agent.client, action)

            if not result.success:
                self.call_from_thread(log.write, Text.from_markup(
                    f"[{Theme.WARNING}]{result.error}[/{Theme.WARNING}]"
                ))
                return

            # Display analysis in panel
            panel_width = 70
            analysis_panel = Panel(
                result.analysis,
                title=f"[bold {Theme.WARNING}]CONSEQUENCE PREVIEW[/bold {Theme.WARNING}]",
                border_style=Theme.WARNING,
                style=f"on {Theme.BG}",
                padding=(0, 1),
                width=panel_width,
            )
            self.call_from_thread(log.write, center_renderable(analysis_panel, panel_width, log_width))

            self.call_from_thread(log.write, Text.from_markup(
                f"\n[{Theme.DIM}]This is speculative. Actual outcomes depend on dice and GM narration.[/{Theme.DIM}]"
            ))
            self.call_from_thread(log.write, Text.from_markup(
                f"[{Theme.DIM}]No changes have been made to your campaign.[/{Theme.DIM}]"
            ))

        finally:
            self.call_from_thread(indicator.remove_class, "visible")

    @work(thread=True)
    async def _simulate_npc(self, args: list[str]):
        """Predict how an NPC will react to a proposed approach."""
        from .shared import simulate_npc, get_npc_details

        log = self.query_one("#output-log", RichLog)
        log_width = (log.size.width or 80) - 4
        indicator = self.query_one("#thinking-indicator", LoadingIndicator)

        if not self.agent or not self.agent.client:
            self.call_from_thread(log.write, Text.from_markup(
                f"[{Theme.WARNING}]No LLM backend available[/{Theme.WARNING}]"
            ))
            return

        npc_query = args[0]
        approach = " ".join(args[1:])

        # Get NPC details for header display
        npc_info = get_npc_details(self.manager, npc_query)
        if not npc_info:
            self.call_from_thread(log.write, Text.from_markup(
                f"[{Theme.WARNING}]No NPC found matching '{npc_query}'[/{Theme.WARNING}]"
            ))
            return

        # Show header
        self.call_from_thread(log.write, Text.from_markup(
            f"\n[bold {Theme.PRIMARY}]◈ NPC REACTION PREVIEW ◈[/bold {Theme.PRIMARY}]"
        ))
        self.call_from_thread(log.write, Text.from_markup(
            f"[{Theme.SECONDARY}]NPC:[/{Theme.SECONDARY}] {npc_info['name']}"
        ))
        if npc_info.get('faction'):
            self.call_from_thread(log.write, Text.from_markup(
                f"[{Theme.SECONDARY}]Faction:[/{Theme.SECONDARY}] {npc_info['faction']}"
            ))
        self.call_from_thread(log.write, Text.from_markup(
            f"[{Theme.SECONDARY}]Disposition:[/{Theme.SECONDARY}] {npc_info['disposition']}"
        ))
        self.call_from_thread(log.write, Text.from_markup(
            f"[{Theme.SECONDARY}]Personal standing:[/{Theme.SECONDARY}] {npc_info['personal_standing']:+d}"
        ))
        self.call_from_thread(log.write, Text.from_markup(
            f"\n[{Theme.DIM}]Proposed approach:[/{Theme.DIM}] {approach}\n"
        ))

        # Show thinking indicator
        self.call_from_thread(indicator.add_class, "visible")

        try:
            result = simulate_npc(self.manager, self.agent.client, npc_query, approach)

            if not result.success:
                self.call_from_thread(log.write, Text.from_markup(
                    f"[{Theme.WARNING}]{result.error}[/{Theme.WARNING}]"
                ))
                return

            # Display prediction in panel
            panel_width = 70
            prediction_panel = Panel(
                result.analysis,
                title=f"[bold {Theme.ACCENT}]{npc_info['name'].upper()} — REACTION PREDICTION[/bold {Theme.ACCENT}]",
                border_style=Theme.ACCENT,
                style=f"on {Theme.BG}",
                padding=(0, 1),
                width=panel_width,
            )
            self.call_from_thread(log.write, center_renderable(prediction_panel, panel_width, log_width))

            self.call_from_thread(log.write, Text.from_markup(
                f"\n[{Theme.DIM}]This is speculative based on established NPC traits.[/{Theme.DIM}]"
            ))
            self.call_from_thread(log.write, Text.from_markup(
                f"[{Theme.DIM}]Actual reactions depend on approach, dice, and GM interpretation.[/{Theme.DIM}]"
            ))

        finally:
            self.call_from_thread(indicator.remove_class, "visible")

    @work(thread=True)
    async def _simulate_whatif(self, args: list[str]):
        """Explore how past choices might have gone differently."""
        from .shared import simulate_whatif

        log = self.query_one("#output-log", RichLog)
        log_width = (log.size.width or 80) - 4
        indicator = self.query_one("#thinking-indicator", LoadingIndicator)

        if not self.agent or not self.agent.client:
            self.call_from_thread(log.write, Text.from_markup(
                f"[{Theme.WARNING}]No LLM backend available[/{Theme.WARNING}]"
            ))
            return

        query = " ".join(args)

        # Show header
        self.call_from_thread(log.write, Text.from_markup(
            f"\n[bold {Theme.PRIMARY}]◈ WHAT-IF ANALYSIS ◈[/bold {Theme.PRIMARY}]"
        ))
        self.call_from_thread(log.write, Text.from_markup(
            f"[{Theme.DIM}]Query:[/{Theme.DIM}] {query}\n"
        ))

        # Show thinking indicator
        self.call_from_thread(indicator.add_class, "visible")

        try:
            result = simulate_whatif(self.manager, self.agent.client, query)

            if not result.success:
                self.call_from_thread(log.write, Text.from_markup(
                    f"[{Theme.WARNING}]{result.error}[/{Theme.WARNING}]"
                ))
                return

            # Display analysis in panel
            panel_width = 70
            analysis_panel = Panel(
                result.analysis,
                title=f"[bold {Theme.WARNING}]TIMELINE DIVERGENCE[/bold {Theme.WARNING}]",
                border_style=Theme.WARNING,
                style=f"on {Theme.BG}",
                padding=(0, 1),
                width=panel_width,
            )
            self.call_from_thread(log.write, center_renderable(analysis_panel, panel_width, log_width))

            self.call_from_thread(log.write, Text.from_markup(
                f"\n[{Theme.DIM}]This is speculative. The road not taken remains unknown.[/{Theme.DIM}]"
            ))
            self.call_from_thread(log.write, Text.from_markup(
                f"[{Theme.DIM}]Your actual choices have shaped who you are.[/{Theme.DIM}]"
            ))

        finally:
            self.call_from_thread(indicator.remove_class, "visible")


def main():
    """Entry point for Textual TUI."""
    import argparse
    parser = argparse.ArgumentParser(description="SENTINEL - AI Game Master (TUI)")
    parser.add_argument(
        "--local", "-l",
        action="store_true",
        help="Use local mode (optimized for 8B-12B models)"
    )
    args = parser.parse_args()

    app = SentinelTUI(local_mode=args.local)
    app.run()


if __name__ == "__main__":
    main()
