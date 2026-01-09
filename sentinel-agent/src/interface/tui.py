"""
SENTINEL Textual TUI - Three-column layout with collapsible docks.

Main stream in center, SELF dock (left) and WORLD dock (right) toggle with [ and ].
"""
import asyncio
import random
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
from .config import load_config, set_backend
from .glyphs import g, energy_bar


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
    "/backend", "/model", "/clear", "/checkpoint", "/compress", "/context", "/dock",
    "/help", "/quit", "/exit",
]

# Shop inventory based on playbook prices
SHOP_INVENTORY = {
    "Surveillance": [
        ("Tactical Drone", 300, "Remote recon"),
        ("A/V Recorder", 100, "Hidden camera/mic"),
        ("Motion Tracker", 150, "Detect movement through walls"),
    ],
    "Hacking": [
        ("Encryption Breaker", 400, "Single-use, advantage vs high-security"),
        ("Ghost Protocol Suite", 300, "Scrubs logs and traces"),
        ("Network Mapper", 200, "Visual map of vulnerabilities"),
    ],
    "Infiltration": [
        ("Lockpick Set", 100, "Advantage vs mechanical locks"),
        ("Climbing Rig", 200, "Vertical access"),
        ("Disguise Module", 300, "Temp identity, advantage on deception"),
    ],
    "Combat": [
        ("EMP Device", 500, "Disables electronics in radius"),
        ("Neural Disruptor", 400, "Close-range incapacitation"),
        ("Stun Grenade", 50, "Flashbang, crowd control"),
    ],
    "Medical": [
        ("Trauma Kit", 200, "Stabilize critical injury, single-use"),
        ("Diagnostic Scanner", 350, "Detect injury, toxins, implants"),
        ("Stimulant Dose", 100, "One-time boost, addiction risk"),
    ],
    "Comms": [
        ("Encrypted Comms", 250, "Secure voice/text"),
        ("Long-Range Transmitter", 400, "Remote contact"),
        ("Translator Module", 150, "Real-time language bridge"),
    ],
}


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
    Autocorrect a mistyped command.

    Returns (corrected_cmd, suggestion_message) where suggestion_message
    is None if no correction was needed.
    """
    if cmd in VALID_COMMANDS:
        return cmd, None

    # Find close matches (cutoff=0.6 means 60% similarity required)
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
# Widgets: Bottom Dock
# =============================================================================

class BottomDock(Static):
    """Persistent bottom dock: Pistachios | Strain | Session."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.campaign: Campaign | None = None

    def update_campaign(self, campaign: Campaign | None):
        self.campaign = campaign
        self.refresh_display()

    def refresh_display(self):
        if not self.campaign or not self.campaign.characters:
            self.update(Text.from_markup(
                f"[{Theme.DIM}]No campaign loaded[/{Theme.DIM}]"
            ))
            return

        char = self.campaign.characters[0]
        energy = char.social_energy.current

        # Energy bar with color
        if energy > 50:
            e_color = Theme.FRIENDLY
        elif energy > 25:
            e_color = Theme.WARNING
        else:
            e_color = Theme.DANGER

        bar = energy_bar(energy, width=5)

        # Strain indicator (placeholder - would come from context packer)
        strain = "LOW"
        strain_bar = g("energy_full") * 1 + g("energy_empty") * 2

        # Session count
        session = self.campaign.meta.session_count

        parts = [
            f"[{Theme.TEXT}]Pistachios[/{Theme.TEXT}] [{e_color}]{bar} {energy}%[/{e_color}]",
            f"[{Theme.DIM}]|[/{Theme.DIM}]",
            f"[{Theme.TEXT}]Strain[/{Theme.TEXT}] [{Theme.ACCENT}]{strain_bar} {strain}[/{Theme.ACCENT}]",
            f"[{Theme.DIM}]|[/{Theme.DIM}]",
            f"[{Theme.DIM}]Session {session:02d}[/{Theme.DIM}]",
        ]

        self.update(Text.from_markup("  " + "   ".join(parts)))


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
        grid-rows: 2 1 1fr 1;
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
        width: 26;
        height: 100%;
        padding: 0;
    }}

    #self-dock.hidden {{
        display: none;
    }}

    #center-column {{
        width: 1fr;
        height: 100%;
        align: center top;
    }}

    #console-wrapper {{
        width: 90%;
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
        width: 26;
        height: 100%;
        padding: 0;
    }}

    #world-dock.hidden {{
        display: none;
    }}

    #bottom-dock {{
        height: 1;
        background: {Theme.BG};
        border-top: dashed {Theme.DIM};
        padding: 0 1;
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

    def __init__(self):
        super().__init__()
        self.manager: CampaignManager | None = None
        self.agent: SentinelAgent | None = None
        self.conversation: list[Message] = []
        self.last_choices: ChoiceBlock | None = None
        self.prompts_dir: Path | None = None
        self.lore_dir: Path | None = None
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
            yield WorldDock(id="world-dock")

        yield BottomDock(id="bottom-dock")

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
        self.lore_dir = base_dir / "lore"

        config = load_config(campaigns_dir)
        saved_backend = config.get("backend", "auto")

        self.manager = CampaignManager(campaigns_dir)
        self.agent = SentinelAgent(
            self.manager,
            prompts_dir=self.prompts_dir,
            lore_dir=self.lore_dir if self.lore_dir.exists() else None,
            backend=saved_backend,
        )

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

        self.query_one("#bottom-dock", BottomDock).update_campaign(campaign)

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
        """Toggle both docks visibility."""
        self.docks_visible = not self.docks_visible

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

        # Refocus input after button click
        self.query_one("#main-input", CommandInput).focus()

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

        if cmd in ["/quit", "/exit"]:
            self.exit()
            return

        if cmd == "/help":
            log.write(Text.from_markup(
                f"[bold {Theme.TEXT}]Campaign:[/bold {Theme.TEXT}]\n"
                f"  [{Theme.ACCENT}]/new[/{Theme.ACCENT}] <name> - Create campaign\n"
                f"  [{Theme.ACCENT}]/load[/{Theme.ACCENT}] [n] - Load campaign\n"
                f"  [{Theme.ACCENT}]/save[/{Theme.ACCENT}] - Save campaign\n"
                f"  [{Theme.ACCENT}]/list[/{Theme.ACCENT}] - List campaigns\n"
                f"  [{Theme.ACCENT}]/delete[/{Theme.ACCENT}] <name> - Delete campaign\n"
                f"\n[bold {Theme.TEXT}]Character:[/bold {Theme.TEXT}]\n"
                f"  [{Theme.ACCENT}]/char[/{Theme.ACCENT}] - Create character (use regular CLI)\n"
                f"  [{Theme.ACCENT}]/roll[/{Theme.ACCENT}] [mod] - Roll d20\n"
                f"  [{Theme.ACCENT}]/gear[/{Theme.ACCENT}] - View inventory\n"
                f"  [{Theme.ACCENT}]/shop[/{Theme.ACCENT}] - Buy equipment (downtime only)\n"
                f"  [{Theme.ACCENT}]/loadout[/{Theme.ACCENT}] - Manage mission gear\n"
                f"  [{Theme.ACCENT}]/arc[/{Theme.ACCENT}] - View character arcs\n"
                f"\n[bold {Theme.TEXT}]Session:[/bold {Theme.TEXT}]\n"
                f"  [{Theme.ACCENT}]/start[/{Theme.ACCENT}] - Begin story\n"
                f"  [{Theme.ACCENT}]/mission[/{Theme.ACCENT}] - Request mission\n"
                f"  [{Theme.ACCENT}]/consult[/{Theme.ACCENT}] [topic] - Ask for advice\n"
                f"  [{Theme.ACCENT}]/debrief[/{Theme.ACCENT}] - End session\n"
                f"\n[bold {Theme.TEXT}]Info:[/bold {Theme.TEXT}]\n"
                f"  [{Theme.ACCENT}]/status[/{Theme.ACCENT}] - Show status\n"
                f"  [{Theme.ACCENT}]/factions[/{Theme.ACCENT}] - Show standings\n"
                f"  [{Theme.ACCENT}]/npc[/{Theme.ACCENT}] [name] - View NPCs\n"
                f"  [{Theme.ACCENT}]/threads[/{Theme.ACCENT}] - View pending consequences\n"
                f"  [{Theme.ACCENT}]/history[/{Theme.ACCENT}] [filter] - View chronicle\n"
                f"  [{Theme.ACCENT}]/search[/{Theme.ACCENT}] <term> - Search history\n"
                f"  [{Theme.ACCENT}]/summary[/{Theme.ACCENT}] [n] - Session summary\n"
                f"  [{Theme.ACCENT}]/timeline[/{Theme.ACCENT}] [query] - Campaign memory (memvid)\n"
                f"  [{Theme.ACCENT}]/lore[/{Theme.ACCENT}] [query] - Search lore\n"
                f"  [{Theme.ACCENT}]/simulate[/{Theme.ACCENT}] - Explore hypotheticals\n"
                f"\n[bold {Theme.TEXT}]System:[/bold {Theme.TEXT}]\n"
                f"  [{Theme.ACCENT}]/backend[/{Theme.ACCENT}] [name] - Switch LLM backend\n"
                f"  [{Theme.ACCENT}]/model[/{Theme.ACCENT}] [name] - Switch model\n"
                f"  [{Theme.ACCENT}]/checkpoint[/{Theme.ACCENT}] - Save & relieve memory pressure\n"
                f"  [{Theme.ACCENT}]/compress[/{Theme.ACCENT}] - Update campaign digest\n"
                f"  [{Theme.ACCENT}]/clear[/{Theme.ACCENT}] - Clear conversation\n"
                f"  [{Theme.ACCENT}]/context[/{Theme.ACCENT}] - Show context debug info\n"
                f"  [{Theme.ACCENT}]/quit[/{Theme.ACCENT}] - Exit\n"
                f"\n[bold {Theme.TEXT}]Hotkeys:[/bold {Theme.TEXT}]\n"
                f"  [{Theme.ACCENT}]F2[/{Theme.ACCENT}] - Toggle panels | [{Theme.ACCENT}]Ctrl+Q[/{Theme.ACCENT}] - Quit | [{Theme.ACCENT}]1-9[/{Theme.ACCENT}] - Select choice"
            ))
            return

        if cmd == "/dock":
            # Toggle both docks
            self.docks_visible = not self.docks_visible
            state = "shown" if self.docks_visible else "hidden"
            log.write(Text.from_markup(f"[{Theme.DIM}]Docks {state}[/{Theme.DIM}]"))
            return

        if cmd == "/new":
            if not args:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /new <campaign name>[/{Theme.WARNING}]"))
                return
            name = " ".join(args)
            campaign = self.manager.create_campaign(name)
            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Created: {campaign.meta.name}[/{Theme.FRIENDLY}]"))
            log.write(Text.from_markup(f"[{Theme.DIM}]Use /char to create your character[/{Theme.DIM}]"))
            self.refresh_all_panels()
            return

        if cmd == "/char":
            # Character creation is an interactive wizard - not supported in TUI yet
            log.write(Text.from_markup(f"[{Theme.WARNING}]Character creation requires the regular CLI.[/{Theme.WARNING}]"))
            log.write(Text.from_markup(f"[{Theme.DIM}]Run: python -m src.interface.cli[/{Theme.DIM}]"))
            log.write(Text.from_markup(f"[{Theme.DIM}]Then use /char there, and /load here after.[/{Theme.DIM}]"))
            return

        if cmd == "/load":
            campaigns = self.manager.list_campaigns()
            if not campaigns:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No campaigns found. Use /new to create one.[/{Theme.WARNING}]"))
                return

            if args:
                # Direct load by number or name
                campaign = self.manager.load_campaign(args[0])
                if campaign:
                    log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Loaded: {campaign.meta.name}[/{Theme.FRIENDLY}]"))
                    self.refresh_all_panels()
                else:
                    log.write(Text.from_markup(f"[{Theme.DANGER}]Campaign not found[/{Theme.DANGER}]"))
            else:
                # Show list
                log.write(Text.from_markup(f"[bold {Theme.TEXT}]Campaigns:[/bold {Theme.TEXT}]"))
                for i, c in enumerate(campaigns, 1):
                    log.write(Text.from_markup(
                        f"  [{Theme.ACCENT}]{i}[/{Theme.ACCENT}] {c['name']} "
                        f"[{Theme.DIM}]({c['session_count']} sessions, {c['display_time']})[/{Theme.DIM}]"
                    ))
                log.write(Text.from_markup(f"[{Theme.DIM}]Type /load <number> to load[/{Theme.DIM}]"))
            return

        if cmd == "/save":
            if self.manager and self.manager.current:
                self.manager.save()
                log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Campaign saved![/{Theme.FRIENDLY}]"))
            else:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign to save[/{Theme.WARNING}]"))
            return

        if cmd == "/status":
            if self.manager and self.manager.current:
                c = self.manager.current
                log.write(Text.from_markup(f"[bold {Theme.TEXT}]{c.meta.name}[/bold {Theme.TEXT}]"))
                log.write(Text.from_markup(f"  Phase: {c.meta.phase}"))
                log.write(Text.from_markup(f"  Sessions: {c.meta.session_count}"))
            else:
                log.write(Text.from_markup(f"[{Theme.DIM}]No campaign loaded[/{Theme.DIM}]"))
            return

        if cmd == "/factions":
            if self.manager and self.manager.current:
                self._show_all_factions(log)
            else:
                log.write(Text.from_markup(f"[{Theme.DIM}]No campaign loaded[/{Theme.DIM}]"))
            return

        if cmd == "/start":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Load a campaign first[/{Theme.WARNING}]"))
                return
            self.handle_action("BEGIN_SESSION")  # @work decorator, don't await
            return

        if cmd == "/list":
            campaigns = self.manager.list_campaigns()
            if not campaigns:
                log.write(Text.from_markup(f"[{Theme.DIM}]No campaigns found[/{Theme.DIM}]"))
            else:
                log.write(Text.from_markup(f"[bold {Theme.TEXT}]Campaigns:[/bold {Theme.TEXT}]"))
                for i, c in enumerate(campaigns, 1):
                    log.write(Text.from_markup(
                        f"  [{Theme.ACCENT}]{i}[/{Theme.ACCENT}] {c['name']} "
                        f"[{Theme.DIM}]({c['session_count']} sessions)[/{Theme.DIM}]"
                    ))
            return

        if cmd == "/delete":
            if not args:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /delete <campaign name or number>[/{Theme.WARNING}]"))
                return
            identifier = " ".join(args)
            if self.manager.delete_campaign(identifier):
                log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Campaign deleted[/{Theme.FRIENDLY}]"))
            else:
                log.write(Text.from_markup(f"[{Theme.DANGER}]Campaign not found[/{Theme.DANGER}]"))
            return

        if cmd == "/mission":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Load a campaign first[/{Theme.WARNING}]"))
                return
            self.handle_action("REQUEST_MISSION")
            return

        if cmd == "/consult":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Load a campaign first[/{Theme.WARNING}]"))
                return
            query = " ".join(args) if args else "What should I consider?"
            self.handle_action(f"CONSULT: {query}")
            return

        if cmd == "/debrief":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Load a campaign first[/{Theme.WARNING}]"))
                return
            self.handle_action("END_SESSION_DEBRIEF")
            return

        if cmd in ["/threads", "/consequences"]:
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.DIM}]No campaign loaded[/{Theme.DIM}]"))
                return
            threads = self.manager.current.dormant_threads
            if not threads:
                log.write(Text.from_markup(f"[{Theme.DIM}]No pending threads[/{Theme.DIM}]"))
            else:
                log.write(Text.from_markup(f"[bold {Theme.TEXT}]Dormant Threads:[/bold {Theme.TEXT}]"))
                for t in threads:
                    sev_color = Theme.DANGER if t.severity.value == "major" else Theme.WARNING if t.severity.value == "moderate" else Theme.DIM
                    log.write(Text.from_markup(
                        f"  [{sev_color}]{g('thread')}[/{sev_color}] {t.origin[:40]}..."
                    ))
                    log.write(Text.from_markup(f"    [{Theme.DIM}]Trigger: {t.trigger_condition}[/{Theme.DIM}]"))
            return

        if cmd == "/history":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.DIM}]No campaign loaded[/{Theme.DIM}]"))
                return
            history = self.manager.current.history
            hinges = [h for h in history if h.entry_type.value == "hinge"]
            if not hinges:
                log.write(Text.from_markup(f"[{Theme.DIM}]No hinge moments recorded[/{Theme.DIM}]"))
            else:
                log.write(Text.from_markup(f"[bold {Theme.TEXT}]Hinge Moments:[/bold {Theme.TEXT}]"))
                for h in hinges[-5:]:  # Last 5
                    log.write(Text.from_markup(f"  [{Theme.ACCENT}]{g('hinge')}[/{Theme.ACCENT}] {h.content[:60]}..."))
            return

        if cmd == "/roll":
            import random
            modifier = int(args[0]) if args and args[0].lstrip('-+').isdigit() else 0
            roll = random.randint(1, 20)
            total = roll + modifier
            mod_str = f" + {modifier}" if modifier > 0 else f" - {abs(modifier)}" if modifier < 0 else ""
            log.write(Text.from_markup(
                f"[{Theme.ACCENT}]d20{mod_str} = {roll}{mod_str} = [bold]{total}[/bold][/{Theme.ACCENT}]"
            ))
            return

        if cmd == "/gear":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
                return

            char = self.manager.current.player
            if not char.gear:
                log.write(Text.from_markup(f"[{Theme.DIM}]No gear in inventory[/{Theme.DIM}]"))
                log.write(Text.from_markup(f"[{Theme.DIM}]Credits: {char.credits}[/{Theme.DIM}]"))
                return

            log.write(Text.from_markup(f"[bold {Theme.TEXT}]INVENTORY[/bold {Theme.TEXT}]  [{Theme.DIM}]{char.credits} credits[/{Theme.DIM}]"))

            # Group by category
            by_category: dict[str, list] = {}
            for item in char.gear:
                cat = item.category or "Other"
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(item)

            for category, items in sorted(by_category.items()):
                log.write(Text.from_markup(f"\n[{Theme.ACCENT}]{category}[/{Theme.ACCENT}]"))
                for item in items:
                    status = ""
                    if item.single_use:
                        status = f" [{Theme.WARNING}](single-use)[/{Theme.WARNING}]" if not item.used else f" [{Theme.DIM}](USED)[/{Theme.DIM}]"
                    log.write(Text.from_markup(
                        f"  • {item.name}{status}"
                        + (f" [{Theme.DIM}]— {item.description}[/{Theme.DIM}]" if item.description else "")
                    ))
            return

        if cmd == "/shop":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
                return

            # Check if in mission
            session = self.manager.current.session
            if session and session.mission:
                from ..state.schema import MissionPhase
                phase = session.mission.phase
                if phase not in (MissionPhase.BETWEEN, MissionPhase.PLANNING):
                    log.write(Text.from_markup(f"[{Theme.WARNING}]Can't shop during a mission[/{Theme.WARNING}]"))
                    log.write(Text.from_markup(f"[{Theme.DIM}]Complete or abort the mission first[/{Theme.DIM}]"))
                    return

            char = self.manager.current.player
            credits = char.credits

            if not args:
                # Show shop categories
                log.write(Text.from_markup(f"[bold {Theme.TEXT}]SHOP[/bold {Theme.TEXT}]  [{Theme.ACCENT}]{credits} credits[/{Theme.ACCENT}]"))
                log.write(Text.from_markup(f"[{Theme.DIM}]Usage: /shop <category> or /shop buy <item>[/{Theme.DIM}]\n"))

                for category, items in SHOP_INVENTORY.items():
                    log.write(Text.from_markup(f"[{Theme.ACCENT}]{category}[/{Theme.ACCENT}]"))
                    for name, price, desc in items:
                        affordable = "[bold]" if credits >= price else f"[{Theme.DIM}]"
                        end = "[/bold]" if credits >= price else f"[/{Theme.DIM}]"
                        log.write(Text.from_markup(f"  {affordable}• {name} ({price}c){end} [{Theme.DIM}]— {desc}[/{Theme.DIM}]"))
                    log.write(Text.from_markup(""))
                return

            # Handle /shop buy <item name>
            if args[0].lower() == "buy" and len(args) > 1:
                item_name = " ".join(args[1:]).lower()

                # Find the item
                found = None
                for category, items in SHOP_INVENTORY.items():
                    for name, price, desc in items:
                        if name.lower() == item_name or name.lower().startswith(item_name):
                            found = (name, price, desc, category)
                            break
                    if found:
                        break

                if not found:
                    log.write(Text.from_markup(f"[{Theme.WARNING}]Item not found: {item_name}[/{Theme.WARNING}]"))
                    return

                name, price, desc, category = found

                if credits < price:
                    log.write(Text.from_markup(f"[{Theme.DANGER}]Not enough credits[/{Theme.DANGER}]"))
                    log.write(Text.from_markup(f"[{Theme.DIM}]Need {price}, have {credits}[/{Theme.DIM}]"))
                    return

                # Check if already owned
                if any(g.name.lower() == name.lower() for g in char.gear):
                    log.write(Text.from_markup(f"[{Theme.WARNING}]Already own: {name}[/{Theme.WARNING}]"))
                    return

                # Purchase
                from ..state.schema import GearItem
                single_use = "single-use" in desc.lower()
                new_item = GearItem(
                    name=name,
                    category=category,
                    description=desc,
                    cost=price,
                    single_use=single_use,
                )
                char.gear.append(new_item)
                char.credits -= price

                log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Purchased: {name}[/{Theme.FRIENDLY}]"))
                log.write(Text.from_markup(f"[{Theme.DIM}]Remaining credits: {char.credits}[/{Theme.DIM}]"))
                self.refresh_all_panels()
                return

            log.write(Text.from_markup(f"[{Theme.DIM}]Usage: /shop or /shop buy <item name>[/{Theme.DIM}]"))
            return

        if cmd == "/backend":
            if not args:
                info = self.agent.backend_info if self.agent else {"backend": "none", "available": False}
                log.write(Text.from_markup(
                    f"[{Theme.TEXT}]Current: {info.get('backend', 'none')}[/{Theme.TEXT}]"
                ))
                log.write(Text.from_markup(f"[{Theme.DIM}]Usage: /backend <lmstudio|ollama|claude|gemini|codex>[/{Theme.DIM}]"))
            else:
                backend = args[0].lower()
                log.write(Text.from_markup(f"[{Theme.DIM}]Switching to {backend}...[/{Theme.DIM}]"))
                # Reinitialize agent with new backend
                self.agent = SentinelAgent(
                    self.manager,
                    prompts_dir=self.prompts_dir,
                    lore_dir=self.lore_dir if self.lore_dir and self.lore_dir.exists() else None,
                    backend=backend,
                )
                info = self.agent.backend_info
                if info["available"]:
                    log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Now using: {info['backend']} ({info['model']})[/{Theme.FRIENDLY}]"))
                else:
                    log.write(Text.from_markup(f"[{Theme.DANGER}]Backend not available[/{Theme.DANGER}]"))
            return

        if cmd == "/model":
            if not self.agent or not self.agent.client:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No LLM backend active[/{Theme.WARNING}]"))
                return

            client = self.agent.client
            backend = self.agent.backend
            has_list = hasattr(client, 'list_models')
            has_set = hasattr(client, 'set_model')

            if not args:
                # Show current model and list available
                log.write(Text.from_markup(
                    f"[{Theme.TEXT}]Current model:[/{Theme.TEXT}] [{Theme.ACCENT}]{client.model_name}[/{Theme.ACCENT}]"
                ))
                if has_list:
                    try:
                        models = client.list_models()
                        if models:
                            log.write(Text.from_markup(f"\n[bold {Theme.TEXT}]Available models:[/bold {Theme.TEXT}]"))
                            for i, model in enumerate(models, 1):
                                current = " ← current" if model == client.model_name else ""
                                log.write(Text.from_markup(
                                    f"  [{Theme.ACCENT}]{i}.[/{Theme.ACCENT}] {model}[{Theme.DIM}]{current}[/{Theme.DIM}]"
                                ))
                            log.write(Text.from_markup(f"\n[{Theme.DIM}]Usage: /model <name or number>[/{Theme.DIM}]"))
                        else:
                            log.write(Text.from_markup(f"[{Theme.DIM}]No other models available[/{Theme.DIM}]"))
                    except Exception as e:
                        log.write(Text.from_markup(f"[{Theme.DIM}]Could not list models: {e}[/{Theme.DIM}]"))
                else:
                    log.write(Text.from_markup(
                        f"[{Theme.DIM}]Model listing not supported for {backend}[/{Theme.DIM}]"
                    ))
            else:
                # Switch model
                if not has_set:
                    log.write(Text.from_markup(
                        f"[{Theme.WARNING}]Model switching not supported for {backend}[/{Theme.WARNING}]"
                    ))
                    return

                model_arg = args[0]

                # Check if it's a number (index into list)
                if model_arg.isdigit() and has_list:
                    try:
                        models = client.list_models()
                        idx = int(model_arg) - 1
                        if 0 <= idx < len(models):
                            model_arg = models[idx]
                        else:
                            log.write(Text.from_markup(f"[{Theme.WARNING}]Invalid model number[/{Theme.WARNING}]"))
                            return
                    except Exception:
                        pass

                # Verify model exists before switching
                if has_list:
                    try:
                        models = client.list_models()
                        if model_arg not in models:
                            log.write(Text.from_markup(
                                f"[{Theme.WARNING}]Model '{model_arg}' not found[/{Theme.WARNING}]"
                            ))
                            log.write(Text.from_markup(
                                f"[{Theme.DIM}]Available: {', '.join(models[:5])}{'...' if len(models) > 5 else ''}[/{Theme.DIM}]"
                            ))
                            return
                    except Exception:
                        pass

                log.write(Text.from_markup(f"[{Theme.DIM}]Switching to {model_arg}...[/{Theme.DIM}]"))
                try:
                    client.set_model(model_arg)
                    log.write(Text.from_markup(
                        f"[{Theme.FRIENDLY}]Now using: {client.model_name}[/{Theme.FRIENDLY}]"
                    ))
                except Exception as e:
                    log.write(Text.from_markup(f"[{Theme.DANGER}]Failed to switch model: {e}[/{Theme.DANGER}]"))
            return

        if cmd == "/clear":
            self.conversation.clear()
            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Conversation cleared[/{Theme.FRIENDLY}]"))
            self.refresh_all_panels()
            return

        if cmd == "/checkpoint":
            # Save campaign and clear conversation to relieve memory pressure
            if self.manager and self.manager.current:
                self.manager.save()
                log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Campaign saved[/{Theme.FRIENDLY}]"))

            # Clear conversation
            old_len = len(self.conversation)
            self.conversation.clear()

            # Reset agent's conversation window
            if self.agent and hasattr(self.agent, '_conversation_window'):
                self.agent._conversation_window.blocks.clear()
                self.agent._last_pack_info = None

            log.write(Text.from_markup(
                f"[{Theme.FRIENDLY}]Memory checkpoint complete[/{Theme.FRIENDLY}]  "
                f"[{Theme.DIM}]({old_len} messages archived)[/{Theme.DIM}]"
            ))
            log.write(Text.from_markup(
                f"[{Theme.DIM}]Context pressure relieved. Campaign state preserved.[/{Theme.DIM}]"
            ))
            self.refresh_all_panels()
            return

        if cmd == "/context":
            # Show detailed context debug info
            if not self.agent or not hasattr(self.agent, '_last_pack_info'):
                log.write(Text.from_markup(f"[{Theme.DIM}]No context info yet (send a message first)[/{Theme.DIM}]"))
                return

            pack_info = self.agent._last_pack_info
            if not pack_info:
                log.write(Text.from_markup(f"[{Theme.DIM}]No context info yet[/{Theme.DIM}]"))
                return

            # Header
            tier_colors = {
                StrainTier.NORMAL: Theme.FRIENDLY,
                StrainTier.STRAIN_I: Theme.WARNING,
                StrainTier.STRAIN_II: Theme.DANGER,
                StrainTier.STRAIN_III: Theme.HOSTILE,
            }
            tier_color = tier_colors.get(pack_info.strain_tier, Theme.TEXT)
            log.write(Text.from_markup(
                f"[bold {Theme.TEXT}]Context Debug[/bold {Theme.TEXT}]  "
                f"[{tier_color}]{pack_info.strain_tier.value.upper()}[/{tier_color}]  "
                f"{int(pack_info.pressure * 100)}% pressure"
            ))
            log.write(Text.from_markup(
                f"[{Theme.DIM}]Total: {pack_info.total_tokens:,} / {pack_info.total_budget:,} tokens[/{Theme.DIM}]"
            ))

            # Sections
            log.write(Text.from_markup(f"\n[bold {Theme.TEXT}]Sections:[/bold {Theme.TEXT}]"))
            for section in pack_info.sections:
                if section.token_count == 0:
                    continue
                status = ""
                if section.truncated:
                    status = f" [{Theme.WARNING}](truncated from {section.original_tokens})[/{Theme.WARNING}]"
                log.write(Text.from_markup(
                    f"  [{Theme.ACCENT}]{section.section.value:<16}[/{Theme.ACCENT}] "
                    f"{section.token_count:>5,} tokens{status}"
                ))

            # Warnings
            if pack_info.warnings:
                log.write(Text.from_markup(f"\n[bold {Theme.WARNING}]Warnings:[/bold {Theme.WARNING}]"))
                for warning in pack_info.warnings:
                    log.write(Text.from_markup(f"  [{Theme.WARNING}]• {warning}[/{Theme.WARNING}]"))

            # Trimmed blocks
            if pack_info.trimmed_blocks > 0:
                log.write(Text.from_markup(
                    f"\n[{Theme.DIM}]{pack_info.trimmed_blocks} conversation blocks trimmed from window[/{Theme.DIM}]"
                ))

            # Scene recap
            if pack_info.scene_recap:
                log.write(Text.from_markup(f"\n[bold {Theme.TEXT}]Scene Recap:[/bold {Theme.TEXT}]"))
                log.write(Text.from_markup(f"[{Theme.DIM}]{pack_info.scene_recap}[/{Theme.DIM}]"))

            return

        if cmd == "/lore":
            if not self.agent or not self.agent.lore_retriever:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No lore directory configured[/{Theme.WARNING}]"))
                return

            retriever = self.agent.lore_retriever
            log.write(Text.from_markup(f"[bold {Theme.TEXT}]Lore System[/bold {Theme.TEXT}]"))
            log.write(Text.from_markup(f"  [{Theme.DIM}]Directory: {retriever.lore_dir}[/{Theme.DIM}]"))
            log.write(Text.from_markup(f"  [{Theme.DIM}]Chunks indexed: {retriever.chunk_count}[/{Theme.DIM}]"))

            if args:
                query = " ".join(args)
                log.write(Text.from_markup(f"\n[{Theme.DIM}]Searching: {query}[/{Theme.DIM}]"))
                results = retriever.retrieve(query=query, limit=3)
                if results:
                    for r in results:
                        source = r.get("source", "unknown")[:30]
                        text = r.get("text", "")[:100]
                        log.write(Text.from_markup(f"\n  [{Theme.ACCENT}]{source}[/{Theme.ACCENT}]"))
                        log.write(Text.from_markup(f"  [{Theme.DIM}]{text}...[/{Theme.DIM}]"))
                else:
                    log.write(Text.from_markup(f"[{Theme.DIM}]No matches found[/{Theme.DIM}]"))
            else:
                log.write(Text.from_markup(f"\n[{Theme.DIM}]Usage: /lore <query>[/{Theme.DIM}]"))
            return

        if cmd == "/npc":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
                return

            npcs = self.manager.current.npcs
            active = npcs.active if npcs else []
            dormant = npcs.dormant if npcs else []

            if not args:
                # List all NPCs
                if not active and not dormant:
                    log.write(Text.from_markup(f"[{Theme.DIM}]No NPCs in this campaign yet[/{Theme.DIM}]"))
                    return

                log.write(Text.from_markup(f"[bold {Theme.TEXT}]NPCs[/bold {Theme.TEXT}]"))
                if active:
                    log.write(Text.from_markup(f"\n[{Theme.ACCENT}]ACTIVE[/{Theme.ACCENT}]"))
                    for npc in active:
                        faction = npc.faction.value if npc.faction else "unknown"
                        disp = npc.base_disposition.value if npc.base_disposition else "neutral"
                        log.write(Text.from_markup(f"  • {npc.name} [{Theme.DIM}]{faction}, {disp}[/{Theme.DIM}]"))
                if dormant:
                    log.write(Text.from_markup(f"\n[{Theme.DIM}]DORMANT[/{Theme.DIM}]"))
                    for npc in dormant:
                        log.write(Text.from_markup(f"  [{Theme.DIM}]• {npc.name}[/{Theme.DIM}]"))
            else:
                # Find specific NPC
                name_query = args[0].lower()
                npc = None
                for n in active + dormant:
                    if name_query in n.name.lower():
                        npc = n
                        break
                if not npc:
                    log.write(Text.from_markup(f"[{Theme.WARNING}]No NPC found matching '{args[0]}'[/{Theme.WARNING}]"))
                    return

                # Show NPC details
                log.write(Text.from_markup(f"\n[bold {Theme.ACCENT}]{npc.name}[/bold {Theme.ACCENT}]"))
                if npc.faction:
                    log.write(Text.from_markup(f"  [{Theme.DIM}]Faction:[/{Theme.DIM}] {npc.faction.value}"))
                if npc.role:
                    log.write(Text.from_markup(f"  [{Theme.DIM}]Role:[/{Theme.DIM}] {npc.role}"))
                if npc.base_disposition:
                    log.write(Text.from_markup(f"  [{Theme.DIM}]Disposition:[/{Theme.DIM}] {npc.base_disposition.value}"))
                if npc.wants:
                    log.write(Text.from_markup(f"  [{Theme.TEXT}]Wants:[/{Theme.TEXT}] {npc.wants}"))
                if npc.fears:
                    log.write(Text.from_markup(f"  [{Theme.TEXT}]Fears:[/{Theme.TEXT}] {npc.fears}"))
                if npc.leverage:
                    log.write(Text.from_markup(f"  [{Theme.WARNING}]Leverage:[/{Theme.WARNING}] {npc.leverage}"))
                if npc.owes:
                    log.write(Text.from_markup(f"  [{Theme.ACCENT}]Owes:[/{Theme.ACCENT}] {npc.owes}"))
            return

        if cmd == "/arc":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
                return

            if not self.manager.current.characters:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No character in campaign[/{Theme.WARNING}]"))
                return

            char = self.manager.current.characters[0]
            from ..state.schema import ArcStatus

            if not args:
                # Show current arcs
                log.write(Text.from_markup(f"[bold {Theme.TEXT}]Character Arcs[/bold {Theme.TEXT}]"))
                log.write(Text.from_markup(f"[{Theme.DIM}]{char.name}'s emergent identity patterns[/{Theme.DIM}]"))

                accepted = [a for a in char.arcs if a.status == ArcStatus.ACCEPTED]
                suggested = [a for a in char.arcs if a.status == ArcStatus.SUGGESTED]

                if accepted:
                    log.write(Text.from_markup(f"\n[{Theme.ACCENT}]ACTIVE ARCS[/{Theme.ACCENT}]"))
                    for arc in accepted:
                        strength_bar = "█" * min(5, arc.strength) + "░" * (5 - min(5, arc.strength))
                        log.write(Text.from_markup(f"  ◆ [bold]{arc.title}[/bold] ({arc.arc_type.value})"))
                        log.write(Text.from_markup(f"    [{Theme.DIM}]{arc.description}[/{Theme.DIM}]"))
                        log.write(Text.from_markup(f"    Strength: [{Theme.ACCENT}]{strength_bar}[/{Theme.ACCENT}]"))

                if suggested:
                    log.write(Text.from_markup(f"\n[{Theme.WARNING}]SUGGESTED ARCS[/{Theme.WARNING}]"))
                    for arc in suggested:
                        log.write(Text.from_markup(f"  ? [bold]{arc.title}[/bold] ({arc.arc_type.value})"))
                        log.write(Text.from_markup(f"    [{Theme.DIM}]{arc.description}[/{Theme.DIM}]"))
                        log.write(Text.from_markup(f"    [{Theme.DIM}]/arc accept {arc.arc_type.value} | /arc reject {arc.arc_type.value}[/{Theme.DIM}]"))

                if not accepted and not suggested:
                    log.write(Text.from_markup(f"\n[{Theme.DIM}]No arcs detected yet. Play more to develop patterns.[/{Theme.DIM}]"))
            elif args[0].lower() == "detect":
                candidates = self.manager.detect_arcs()
                if candidates:
                    log.write(Text.from_markup(f"[bold {Theme.TEXT}]Detected Patterns[/bold {Theme.TEXT}]"))
                    for c in candidates:
                        log.write(Text.from_markup(f"  ◆ {c['title']} ({c['arc_type']})"))
                else:
                    log.write(Text.from_markup(f"[{Theme.DIM}]No strong patterns detected yet[/{Theme.DIM}]"))
            elif args[0].lower() == "accept" and len(args) > 1:
                result = self.manager.accept_arc(args[1])
                if result:
                    log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Arc accepted: {args[1]}[/{Theme.FRIENDLY}]"))
                else:
                    log.write(Text.from_markup(f"[{Theme.WARNING}]Could not accept arc: {args[1]}[/{Theme.WARNING}]"))
            elif args[0].lower() == "reject" and len(args) > 1:
                result = self.manager.reject_arc(args[1])
                if result:
                    log.write(Text.from_markup(f"[{Theme.DIM}]Arc rejected: {args[1]}[/{Theme.DIM}]"))
                else:
                    log.write(Text.from_markup(f"[{Theme.WARNING}]Could not reject arc: {args[1]}[/{Theme.WARNING}]"))
            else:
                log.write(Text.from_markup(f"[{Theme.DIM}]Usage: /arc | /arc detect | /arc accept <type> | /arc reject <type>[/{Theme.DIM}]"))
            return

        if cmd == "/loadout":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
                return

            if not self.manager.current.characters:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Create a character first[/{Theme.WARNING}]"))
                return

            char = self.manager.current.characters[0]
            session = self.manager.current.session

            if not session:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No active session. Use /mission first.[/{Theme.WARNING}]"))
                return

            from ..state.schema import MissionPhase
            is_locked = session.phase in {MissionPhase.EXECUTION, MissionPhase.RESOLUTION}

            gear_by_id = {g_item.id: g_item for g_item in char.gear}
            loadout_items = [gear_by_id[gid] for gid in session.loadout if gid in gear_by_id]

            subcommand = args[0].lower() if args else "show"
            item_query = " ".join(args[1:]) if len(args) > 1 else ""

            if subcommand in ("add", "remove", "clear") and is_locked:
                log.write(Text.from_markup(f"[{Theme.DANGER}]Loadout locked during {session.phase.value}[/{Theme.DANGER}]"))
                return

            if subcommand == "add" and item_query:
                item = None
                for g_item in char.gear:
                    if item_query.lower() in g_item.name.lower():
                        item = g_item
                        break
                if item and item.id not in session.loadout:
                    session.loadout.append(item.id)
                    self.manager.save()
                    log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Added {item.name} to loadout[/{Theme.FRIENDLY}]"))
                elif item:
                    log.write(Text.from_markup(f"[{Theme.DIM}]{item.name} already in loadout[/{Theme.DIM}]"))
                else:
                    log.write(Text.from_markup(f"[{Theme.WARNING}]Item not found: {item_query}[/{Theme.WARNING}]"))
            elif subcommand == "remove" and item_query:
                item = None
                for loaded in loadout_items:
                    if item_query.lower() in loaded.name.lower():
                        item = loaded
                        break
                if item:
                    session.loadout.remove(item.id)
                    self.manager.save()
                    log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Removed {item.name}[/{Theme.FRIENDLY}]"))
                else:
                    log.write(Text.from_markup(f"[{Theme.WARNING}]Item not in loadout: {item_query}[/{Theme.WARNING}]"))
            elif subcommand == "clear":
                count = len(session.loadout)
                session.loadout.clear()
                self.manager.save()
                log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Cleared {count} items[/{Theme.FRIENDLY}]"))
            else:
                # Show loadout
                log.write(Text.from_markup(f"[bold {Theme.TEXT}]MISSION LOADOUT[/bold {Theme.TEXT}]"))
                lock_status = f"[{Theme.DANGER}]LOCKED[/{Theme.DANGER}]" if is_locked else f"[{Theme.ACCENT}]OPEN[/{Theme.ACCENT}]"
                log.write(Text.from_markup(f"[{Theme.DIM}]Phase: {session.phase.value.upper()}[/{Theme.DIM}] | {lock_status}"))

                if loadout_items:
                    log.write(Text.from_markup(f"\n[{Theme.ACCENT}]Packed ({len(loadout_items)})[/{Theme.ACCENT}]"))
                    for item in loadout_items:
                        use_tag = f" [{Theme.WARNING}]ONE-USE[/{Theme.WARNING}]" if item.single_use else ""
                        log.write(Text.from_markup(f"  • {item.name}{use_tag}"))
                else:
                    log.write(Text.from_markup(f"\n[{Theme.DIM}]Loadout empty[/{Theme.DIM}]"))

                available = [g_item for g_item in char.gear if g_item.id not in session.loadout]
                if available:
                    log.write(Text.from_markup(f"\n[{Theme.DIM}]Available ({len(available)})[/{Theme.DIM}]"))
                    for item in available[:5]:
                        log.write(Text.from_markup(f"  [{Theme.DIM}]• {item.name}[/{Theme.DIM}]"))
                    if len(available) > 5:
                        log.write(Text.from_markup(f"  [{Theme.DIM}]...and {len(available) - 5} more[/{Theme.DIM}]"))

                if not is_locked:
                    log.write(Text.from_markup(f"\n[{Theme.DIM}]/loadout add <item> | remove <item> | clear[/{Theme.DIM}]"))
            return

        if cmd == "/search":
            if not args:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /search <term>[/{Theme.WARNING}]"))
                return
            # Delegate to history with search
            args = ["search"] + args
            cmd = "/history"
            # Fall through to history handler below

        if cmd == "/history":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.DIM}]No campaign loaded[/{Theme.DIM}]"))
                return

            history = list(self.manager.current.history)
            if not history:
                log.write(Text.from_markup(f"[{Theme.DIM}]No chronicle entries yet[/{Theme.DIM}]"))
                return

            # Filter by type if specified
            filter_type = None
            search_term = None
            session_filter = None

            if args:
                arg = args[0].lower()
                if arg in ("hinge", "hinges"):
                    filter_type = "hinge"
                elif arg in ("faction", "factions"):
                    filter_type = "faction_shift"
                elif arg in ("mission", "missions"):
                    filter_type = "mission"
                elif arg == "session" and len(args) > 1:
                    session_filter = int(args[1]) if args[1].isdigit() else None
                elif arg == "search" and len(args) > 1:
                    search_term = " ".join(args[1:]).lower()

            # Apply filters
            filtered = history
            if filter_type:
                filtered = [h for h in history if h.entry_type.value == filter_type]
            if session_filter:
                filtered = [h for h in history if h.session == session_filter]
            if search_term:
                filtered = [h for h in history if search_term in h.content.lower()]

            log.write(Text.from_markup(f"[bold {Theme.TEXT}]Campaign Chronicle[/bold {Theme.TEXT}]"))
            if not filtered:
                log.write(Text.from_markup(f"[{Theme.DIM}]No matching entries[/{Theme.DIM}]"))
            else:
                for entry in filtered[-15:]:  # Last 15
                    etype = entry.entry_type.value
                    if etype == "hinge":
                        icon = f"[{Theme.DANGER}]{g('hinge')}[/{Theme.DANGER}]"
                    elif etype == "faction_shift":
                        icon = f"[{Theme.WARNING}]{g('triggered')}[/{Theme.WARNING}]"
                    else:
                        icon = f"[{Theme.DIM}]•[/{Theme.DIM}]"
                    log.write(Text.from_markup(f"  {icon} S{entry.session}: {entry.content[:60]}..."))
            return

        if cmd == "/summary":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
                return

            session_num = self.manager.current.meta.session_count
            if args and args[0].isdigit():
                session_num = int(args[0])

            summary_data = self.manager.generate_session_summary(session_num)
            if "error" in summary_data:
                log.write(Text.from_markup(f"[{Theme.WARNING}]{summary_data['error']}[/{Theme.WARNING}]"))
                return

            log.write(Text.from_markup(f"[bold {Theme.TEXT}]Session {session_num} Summary[/bold {Theme.TEXT}]"))
            log.write(Text.from_markup(f"[{Theme.DIM}]Campaign: {summary_data.get('campaign', 'Unknown')}[/{Theme.DIM}]"))

            if summary_data.get("hinges"):
                log.write(Text.from_markup(f"\n[{Theme.ACCENT}]Hinge Moments[/{Theme.ACCENT}]"))
                for h in summary_data["hinges"]:
                    log.write(Text.from_markup(f"  [{Theme.DANGER}]{g('hinge')}[/{Theme.DANGER}] {h.get('choice', '')[:50]}"))

            if summary_data.get("faction_shifts"):
                log.write(Text.from_markup(f"\n[{Theme.ACCENT}]Faction Changes[/{Theme.ACCENT}]"))
                for f in summary_data["faction_shifts"]:
                    log.write(Text.from_markup(f"  {g('triggered')} {f}"))

            if summary_data.get("threads_created"):
                log.write(Text.from_markup(f"\n[{Theme.WARNING}]New Threads[/{Theme.WARNING}]"))
                for t in summary_data["threads_created"]:
                    log.write(Text.from_markup(f"  {g('thread')} {t[:50]}"))
            return

        if cmd == "/timeline":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
                return

            from ..state import MEMVID_AVAILABLE
            if not MEMVID_AVAILABLE:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Memvid not installed. Run: pip install memvid-sdk[/{Theme.WARNING}]"))
                return

            if not self.manager.memvid or not self.manager.memvid.is_enabled:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Memvid not enabled for this campaign[/{Theme.WARNING}]"))
                return

            memvid = self.manager.memvid

            if not args:
                log.write(Text.from_markup(f"[bold {Theme.TEXT}]Campaign Timeline[/bold {Theme.TEXT}]"))
                log.write(Text.from_markup(f"[{Theme.DIM}]Sessions: {self.manager.current.meta.session_count}[/{Theme.DIM}]"))

                hinges = memvid.get_hinges(limit=5)
                if hinges:
                    log.write(Text.from_markup(f"\n[{Theme.ACCENT}]Recent Hinges[/{Theme.ACCENT}]"))
                    for h in hinges:
                        choice = h.get("choice", "")[:50]
                        log.write(Text.from_markup(f"  [{Theme.DANGER}]{g('hinge')}[/{Theme.DANGER}] {choice}..."))

                log.write(Text.from_markup(f"\n[{Theme.DIM}]/timeline <query> | hinges | session <n> | npc <name>[/{Theme.DIM}]"))
            elif args[0].lower() == "hinges":
                hinges = memvid.get_hinges(limit=10)
                log.write(Text.from_markup(f"[bold {Theme.TEXT}]All Hinge Moments[/bold {Theme.TEXT}]"))
                for h in hinges:
                    session = h.get("session", "?")
                    choice = h.get("choice", "")[:60]
                    log.write(Text.from_markup(f"  S{session}: {choice}"))
            else:
                query = " ".join(args)
                log.write(Text.from_markup(f"[{Theme.DIM}]Searching: {query}[/{Theme.DIM}]"))
                results = memvid.search(query, limit=5)
                if results:
                    for r in results:
                        log.write(Text.from_markup(f"  • {r.get('summary', r.get('text', ''))[:60]}..."))
                else:
                    log.write(Text.from_markup(f"[{Theme.DIM}]No matches found[/{Theme.DIM}]"))
            return

        if cmd == "/simulate":
            log.write(Text.from_markup(f"[bold {Theme.TEXT}]Simulation Modes[/bold {Theme.TEXT}]"))
            log.write(Text.from_markup(f"\n[{Theme.ACCENT}]/simulate [turns] [persona][/{Theme.ACCENT}]"))
            log.write(Text.from_markup(f"  [{Theme.DIM}]AI vs AI testing (cautious, opportunist, principled, chaotic)[/{Theme.DIM}]"))
            log.write(Text.from_markup(f"\n[{Theme.ACCENT}]/simulate preview <action>[/{Theme.ACCENT}]"))
            log.write(Text.from_markup(f"  [{Theme.DIM}]Preview consequences without committing[/{Theme.DIM}]"))
            log.write(Text.from_markup(f"\n[{Theme.ACCENT}]/simulate npc <name> <approach>[/{Theme.ACCENT}]"))
            log.write(Text.from_markup(f"  [{Theme.DIM}]Predict NPC reaction[/{Theme.DIM}]"))
            log.write(Text.from_markup(f"\n[{Theme.WARNING}]Note: Full simulation requires the regular CLI[/{Theme.WARNING}]"))
            return

        if cmd == "/compress":
            if not self.manager or not self.manager.current:
                log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
                return

            from pathlib import Path
            from ..context import DigestManager

            campaign = self.manager.current
            digest_manager = DigestManager(Path("campaigns"))

            if args and args[0].lower() == "show":
                existing = digest_manager.load(campaign.meta.id)
                if existing:
                    log.write(Text.from_markup(f"[bold {Theme.TEXT}]Current Digest[/bold {Theme.TEXT}]"))
                    log.write(Text.from_markup(f"[{Theme.DIM}]Last updated: {existing.last_updated.strftime('%Y-%m-%d %H:%M')}[/{Theme.DIM}]"))
                    log.write(Text.from_markup(f"\n{existing.to_prompt_text()[:500]}..."))
                else:
                    log.write(Text.from_markup(f"[{Theme.DIM}]No digest exists. Run /compress to create one.[/{Theme.DIM}]"))
                return

            log.write(Text.from_markup(f"[bold {Theme.TEXT}]Compressing Memory[/bold {Theme.TEXT}]"))
            digest = digest_manager.generate(campaign)
            digest_path = digest_manager.save(campaign.meta.id, digest)
            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Digest updated[/{Theme.FRIENDLY}]"))

            if digest.hinge_index:
                log.write(Text.from_markup(f"  [{Theme.ACCENT}]{len(digest.hinge_index)}[/{Theme.ACCENT}] hinge moments"))
            if digest.standing_reasons:
                log.write(Text.from_markup(f"  [{Theme.ACCENT}]{len(digest.standing_reasons)}[/{Theme.ACCENT}] faction standings"))
            if digest.npc_anchors:
                log.write(Text.from_markup(f"  [{Theme.ACCENT}]{len(digest.npc_anchors)}[/{Theme.ACCENT}] NPC memories"))
            return

        log.write(Text.from_markup(f"[{Theme.WARNING}]Unknown command: {cmd}[/{Theme.WARNING}]"))

    def _show_all_factions(self, log: RichLog):
        """Display all faction standings."""
        standing_values = {
            "Hostile": -2, "Unfriendly": -1, "Neutral": 0,
            "Friendly": 1, "Allied": 2,
        }
        standing_colors = {
            -2: Theme.HOSTILE, -1: Theme.UNFRIENDLY, 0: Theme.NEUTRAL,
            1: Theme.FRIENDLY, 2: Theme.ALLIED,
        }

        log.write(Text.from_markup(f"[bold {Theme.TEXT}]Faction Standings:[/bold {Theme.TEXT}]"))

        for faction_field in ['nexus', 'ember_colonies', 'lattice', 'convergence',
                              'covenant', 'wanderers', 'cultivators', 'steel_syndicate',
                              'witnesses', 'architects', 'ghost_networks']:
            faction_data = getattr(self.manager.current.factions, faction_field, None)
            if faction_data:
                name = faction_field.replace('_', ' ').title()
                value = standing_values.get(faction_data.standing.value, 0)
                blocks = value + 3
                bar = g("centered") * blocks + g("frayed") * (5 - blocks)
                color = standing_colors.get(value, Theme.NEUTRAL)
                standing = faction_data.standing.value
                log.write(Text.from_markup(
                    f"  [{Theme.TEXT}]{name:<16}[/{Theme.TEXT}] [{color}]{bar} {standing}[/{color}]"
                ))

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


def main():
    """Entry point for Textual TUI."""
    app = SentinelTUI()
    app.run()


if __name__ == "__main__":
    main()
