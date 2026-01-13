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
from textual.binding import Binding
from textual.reactive import reactive
from textual import work
from rich.text import Text
from rich.panel import Panel
from rich.padding import Padding
from rich.console import Console, RenderableType

from textual.events import Key

from ..state import CampaignManager
from ..state.schema import Campaign, Standing, Character, DormantThread
from ..agent import SentinelAgent
from ..context import StrainTier, format_strain_notice
from ..llm.base import Message
from ..tools.hinge_detector import detect_hinge
from .choices import parse_response, ChoiceBlock
from .config import load_config, set_backend, set_model as save_model
from .glyphs import g, energy_bar
from .command_registry import get_registry
from .commands import register_all_commands
from .tui_commands import register_tui_handlers


def center_renderable(renderable: RenderableType, content_width: int, container_width: int) -> Padding:
    """Center a renderable by adding left padding."""
    if container_width <= content_width:
        return Padding(renderable, (0, 0))
    left_pad = (container_width - content_width) // 2
    return Padding(renderable, (0, 0, 0, left_pad))


# =============================================================================
# Command Autocorrect
# =============================================================================

VALID_COMMANDS = [
    "/new", "/load", "/save", "/list", "/delete",
    "/char", "/roll", "/gear", "/shop", "/loadout",
    "/start", "/mission", "/consult", "/debrief",
    "/status", "/factions", "/threads", "/consequences", "/history",
    "/npc", "/arc", "/lore", "/search", "/summary", "/timeline", "/simulate",
    "/wiki", "/compare",
    "/backend", "/model", "/clear", "/checkpoint", "/compress", "/context", "/dock",
    "/copy",
    "/ping",
    "/help", "/quit", "/exit",
]

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
        self._suggestions = [c for c in VALID_COMMANDS if c.startswith(cmd_part) and c != cmd_part]
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
            self._tab_matches = [c for c in VALID_COMMANDS if c.startswith(cmd_part)]
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

    # Fallback to legacy VALID_COMMANDS for any not yet in registry
    if cmd in VALID_COMMANDS:
        return cmd, None

    matches = get_close_matches(cmd, VALID_COMMANDS, n=1, cutoff=0.6)
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

    #world-dock {{
        width: 20vw;
        min-width: 24;
        max-width: 32;
        height: 100%;
        padding: 0;
    }}

    #world-dock.hidden {{
        display: none;
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
            yield WorldDock(id="world-dock")

    def on_mount(self):
        """Initialize when app mounts."""
        self.initialize_game()
        self.refresh_all_panels()

        # Start clock timer (update every 30 seconds)
        self.set_interval(30, self._update_clock)

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

        log = self.query_one("#output-log", RichLog)
        wrapper = self.query_one("#console-wrapper")
        # Try wrapper width, fall back to log, subtract for borders
        raw_width = wrapper.size.width or log.size.width or 80
        log_width = raw_width - 4

        # Hexagon banner
        banner_lines = [
            "            /\\",
            "           /  \\",
            "          /    \\       S E N T I N E L",
            "          \\    /       T A C T I C A L   T T R P G",
            "           \\  /",
            "            \\/",
        ]

        # Glitch characters
        glitch_chars = "░▒▓/\\|─<>╱╲·"
        preserve = set("/\\ ")

        def glitch_line(line: str, reveal_chance: float) -> str:
            result = []
            for char in line:
                if char in preserve:
                    result.append(char)
                elif random.random() < reveal_chance:
                    result.append(char)
                else:
                    result.append(random.choice(glitch_chars))
            return "".join(result)

        def render_frame(reveal: float) -> Text:
            text = Text()
            for i, line in enumerate(banner_lines):
                if i in (2, 3):  # Title lines
                    if reveal > 0.6:
                        text_start = line.find("S") if "S E N" in line else line.find("T A C")
                        if text_start > 0:
                            text.append(line[:text_start], style=f"bold {Theme.ACCENT}")
                            text.append(line[text_start:], style=f"bold {Theme.TEXT}")
                        else:
                            text.append(line, style=f"bold {Theme.ACCENT}")
                    else:
                        text.append(glitch_line(line, reveal), style=f"bold {Theme.ACCENT}")
                else:
                    text.append(glitch_line(line, reveal), style=f"bold {Theme.ACCENT}")
                text.append("\n")
            return text

        # Banner width (widest line)
        banner_width = 55

        # Animate with async sleep
        frames = 12
        for i in range(frames + 1):
            progress = i / frames
            reveal = 1 - (1 - progress) ** 2  # Ease-out
            log.clear()
            log.write(center_renderable(render_frame(reveal), banner_width, log_width))
            await asyncio.sleep(0.08)

        # Final flicker
        for _ in range(2):
            log.clear()
            log.write(center_renderable(render_frame(0.85), banner_width, log_width))
            await asyncio.sleep(0.04)
            log.clear()
            log.write(center_renderable(render_frame(1.0), banner_width, log_width))
            await asyncio.sleep(0.08)

        # Clear and show welcome
        log.clear()
        log.write(center_renderable(render_frame(1.0), banner_width, log_width))
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

        # Update context bar from agent's pack info (real token counts)
        context_bar = self.query_one("#context-bar", ContextBar)
        if self.agent and hasattr(self.agent, '_last_pack_info'):
            context_bar.update_from_pack_info(self.agent._last_pack_info)
        else:
            context_bar.update_pressure(0.0)

    def watch_docks_visible(self, visible: bool):
        """React to dock visibility changes."""
        self_dock = self.query_one("#self-dock")
        world_dock = self.query_one("#world-dock")
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
                self.manager.save()
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
