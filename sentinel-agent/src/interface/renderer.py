"""
Display and rendering helpers for SENTINEL CLI.

Handles theming, banners, status displays, and visual output.
"""

import time
import random
from datetime import datetime
from enum import Enum
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text
from rich.box import ROUNDED, Box
from prompt_toolkit.styles import Style as PTStyle

from .glyphs import (
    g, energy_bar, standing_indicator,
    format_context_meter, estimate_conversation_tokens,
    CONTEXT_LIMITS, format_strain_indicator, format_strain_display,
    get_strain_info, STRAIN_TIER_INFO,
)
from ..state.schema import Campaign, Character, MissionPhase

# Import StrainTier for type hints (lazy import to avoid circular deps)
try:
    from ..context.packer import StrainTier
except ImportError:
    StrainTier = None  # type: ignore


# Shared console instance
console = Console()

# -----------------------------------------------------------------------------
# Theme: "If it looks calm, it's lying."
# From SENTINEL Visual Page Concept
# -----------------------------------------------------------------------------

THEME = {
    "primary": "steel_blue",        # cold twilight blue - loneliness, distance
    "secondary": "grey70",          # pale surgical white - sterility, control
    "warning": "dark_goldenrod",    # muted radioactive yellow - danger without melodrama
    "danger": "dark_red",           # rusted red - memory of violence
    "accent": "cyan",               # interface highlights
    "dim": "dim",                   # background text
    "text": "grey85",               # standard body text
}

# Prompt toolkit style to match theme
pt_style = PTStyle.from_dict({
    "completion-menu.completion": "bg:#1e3a5f #c0c0c0",
    "completion-menu.completion.current": "bg:#3a6a9f #ffffff bold",
    "completion-menu.meta.completion": "bg:#1e3a5f #808080",
    "completion-menu.meta.completion.current": "bg:#3a6a9f #c0c0c0",
    "scrollbar.background": "bg:#1e3a5f",
    "scrollbar.button": "bg:#3a6a9f",
})

# -----------------------------------------------------------------------------
# Faction Colors (for codec boxes)
# Each faction has a distinct visual identity
# -----------------------------------------------------------------------------

FACTION_COLORS = {
    "nexus": "steel_blue",           # Cold, data-driven
    "ember_colonies": "orange3",     # Warm, community
    "lattice": "grey70",             # Industrial, practical
    "convergence": "medium_purple",  # Enhancement, transcendence
    "covenant": "gold3",             # Traditional, formal
    "wanderers": "dark_sea_green",   # Freedom, movement
    "cultivators": "green3",         # Growth, sustainability
    "steel_syndicate": "dark_red",   # Power, leverage
    "witnesses": "cyan",             # Observation, truth
    "architects": "wheat1",          # Pre-collapse, authority
    "ghost_networks": "grey50",      # Hidden, ephemeral
}

# Disposition colors
DISPOSITION_COLORS = {
    "hostile": "red",
    "wary": "dark_orange",
    "neutral": "grey70",
    "warm": "green3",
    "loyal": "cyan",
}


# -----------------------------------------------------------------------------
# Block Types for Output Formatting
# -----------------------------------------------------------------------------

class BlockType(Enum):
    """Types of output blocks for visual differentiation."""
    NARRATIVE = "NARRATIVE"
    CHOICE = "CHOICE"
    INTEL = "INTEL"
    SYSTEM = "SYSTEM"


# Block type colors and indicators
BLOCK_STYLES = {
    BlockType.NARRATIVE: {
        "color": THEME["primary"],
        "indicator": "",
    },
    BlockType.CHOICE: {
        "color": THEME["accent"],
        "indicator": "?",
    },
    BlockType.INTEL: {
        "color": THEME["warning"],
        "indicator": "i",
    },
    BlockType.SYSTEM: {
        "color": THEME["dim"],
        "indicator": "*",
    },
}


# We use ROUNDED box for blocks (built-in, reliable)


# -----------------------------------------------------------------------------
# Display Helpers
# -----------------------------------------------------------------------------

def show_banner(animate: bool = True):
    """Display the SENTINEL banner with optional glitch animation."""
    # Hexagon banner - ties into hinge moment glyph
    banner_lines = [
        "            /\\",
        "           /  \\",
        "          /    \\       S E N T I N E L",
        "          \\    /       T A C T I C A L   T T R P G",
        "           \\  /",
        "            \\/",
    ]

    # Glitch characters - signal noise aesthetic
    glitch_chars = "░▒▓/\\|─<>╱╲·"

    # Characters to preserve (hexagon structure)
    preserve = set("/\\ ")

    def glitch_line(line: str, reveal_chance: float) -> str:
        """Replace characters with glitch, preserving structure."""
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
        """Render a single frame of the animation."""
        text = Text()
        for i, line in enumerate(banner_lines):
            # Title lines get accent color
            if i in (2, 3):  # SENTINEL and TACTICAL lines
                if reveal > 0.6:
                    # Find where text starts (after the hexagon part)
                    text_start = line.find("S") if "S E N" in line else line.find("T A C")
                    if text_start > 0:
                        text.append(line[:text_start], style=f"bold {THEME['primary']}")
                        text.append(line[text_start:], style=f"bold {THEME['accent']}")
                    else:
                        text.append(line, style=f"bold {THEME['primary']}")
                else:
                    text.append(glitch_line(line, reveal), style=f"bold {THEME['primary']}")
            else:
                text.append(glitch_line(line, reveal), style=f"bold {THEME['primary']}")
            text.append("\n")
        return text

    if not animate:
        # Static display
        text = render_frame(1.0)
        console.print(text)
        return

    # Animated reveal
    frames = 20
    duration = 1.5  # seconds
    frame_time = duration / frames

    with Live(render_frame(0.0), console=console, refresh_per_second=20) as live:
        for i in range(frames + 1):
            # Ease-out curve for smoother reveal
            progress = i / frames
            reveal = 1 - (1 - progress) ** 2  # Quadratic ease-out
            live.update(render_frame(reveal))
            time.sleep(frame_time)

        # Final flicker effect
        for _ in range(3):
            # Brief glitch
            live.update(render_frame(0.85))
            time.sleep(0.05)
            # Back to full
            live.update(render_frame(1.0))
            time.sleep(0.1)


def show_backend_status(agent):
    """Show LLM backend status."""
    info = agent.backend_info

    if info["available"]:
        console.print(
            f"[{THEME['accent']}]Backend:[/{THEME['accent']}] {info['backend']} "
            f"[{THEME['dim']}]({info['model']})[/{THEME['dim']}]"
        )
        if info["supports_tools"]:
            console.print(f"[{THEME['dim']}]  Tool calling enabled[/{THEME['dim']}]")
        else:
            console.print(f"[{THEME['warning']}]  Tool calling not supported[/{THEME['warning']}]")
    else:
        console.print(f"[{THEME['warning']}]Backend:[/{THEME['warning']}] Not connected")
        console.print(f"[{THEME['dim']}]  Start LM Studio or Ollama[/{THEME['dim']}]")


def show_status(
    manager,
    agent=None,
    conversation: list | None = None,
):
    """Show current campaign and backend status."""
    if agent:
        show_backend_status(agent)
        console.print()

    if not manager.current:
        console.print(f"[{THEME['dim']}]No campaign loaded[/{THEME['dim']}]")
        return

    c = manager.current

    # Campaign info
    table = Table(
        title=f"[bold {THEME['primary']}]{c.meta.name}[/bold {THEME['primary']}]",
        show_header=False,
        box=None
    )
    table.add_column("Key", style=THEME["dim"])
    table.add_column("Value", style=THEME["secondary"])

    table.add_row("Phase", f"{c.meta.phase}")
    table.add_row("Sessions", f"{c.meta.session_count}")
    table.add_row("Characters", f"{len(c.characters)}")
    table.add_row("Active NPCs", f"{len(c.npcs.active)}")
    thread_glyph = g("thread") if c.dormant_threads else ""
    table.add_row("Dormant Threads", f"{thread_glyph} {len(c.dormant_threads)}")

    console.print(table)

    # Character summary
    if c.characters:
        console.print()
        for char in c.characters:
            energy = char.social_energy
            # Theme-aware energy colors
            if energy.current >= 51:
                energy_color = THEME["accent"]
            elif energy.current >= 26:
                energy_color = THEME["warning"]
            else:
                energy_color = THEME["danger"]

            # Energy bar visualization
            bar = energy_bar(energy.current, width=10)

            display_name = f"{char.name} ({char.callsign})" if char.callsign else char.name
            console.print(
                f"  [bold {THEME['secondary']}]{display_name}[/bold {THEME['secondary']}] "
                f"[{THEME['dim']}]{char.background.value}[/{THEME['dim']}]"
            )
            console.print(
                f"    [{energy_color}]{energy.name}: {bar} {energy.current}%[/{energy_color}] "
                f"[{THEME['dim']}]| {char.credits} cr[/{THEME['dim']}]"
            )

    # Current mission
    if c.session:
        console.print()
        console.print(
            f"[bold {THEME['primary']}]Mission:[/bold {THEME['primary']}] {c.session.mission_title} "
            f"[{THEME['dim']}]({c.session.phase.value})[/{THEME['dim']}]"
        )

    # Context meter
    if conversation:
        console.print()
        context_limit = CONTEXT_LIMITS["default"]
        meter = format_context_meter(conversation, context_limit)
        tokens = estimate_conversation_tokens(conversation)
        console.print(
            f"[{THEME['dim']}]Context:[/{THEME['dim']}] {meter} "
            f"[{THEME['dim']}](~{tokens:,} tokens)[/{THEME['dim']}]"
        )


def show_help():
    """Show available commands."""
    help_text = """
## Commands

| Command | Description |
|---------|-------------|
| `/new` | Create a new campaign |
| `/char` | Create a character |
| `/start` | Begin the campaign (GM sets the scene) |
| `/mission` | Get a new mission from the GM |
| `/loadout` | Manage mission gear (add/remove/clear) |
| `/consult <q>` | Ask faction advisors for perspectives |
| `/debrief` | End session with reflection prompts |
| `/history [filter]` | View chronicle (hinges, faction, missions, session N) |
| `/search <term>` | Search campaign history for keywords |
| `/summary [n]` | View session summary (n = session number) |
| `/consequences` | View pending threads and avoided situations |
| `/timeline` | Search campaign memory (memvid) |
| `/factions` | View faction standings and relationships |
| `/load` | Load an existing campaign |
| `/save` | Save current campaign |
| `/list` | List all campaigns |
| `/status` | Show current status |
| `/backend` | Show/change LLM backend |
| `/model` | List/switch LM Studio models |
| `/banner` | Toggle banner animation on startup |
| `/statusbar` | Toggle persistent status bar |
| `/context` | Show context usage (`/context debug` for breakdown) |
| `/checkpoint` | Save state + compress memory |
| `/compress` | Update digest without pruning |
| `/clear` | Clear transcript beyond minimum window |
| `/lore` | Show lore status, test retrieval (`/lore quotes` for faction quotes) |
| `/npc [name]` | View NPC info and personal standing |
| `/arc` | View and manage emergent character arcs |
| `/simulate` | Explore hypotheticals (preview, npc, whatif) |
| `/roll <skill> <dc>` | Roll a skill check |
| `/quit` | Exit the game |

## Quick Start

1. `/new` — Create a campaign
2. `/char` — Create your character
3. `/start` — Jump into the story

## During Play

Just type what you want to do, or pick a numbered option.

Examples:
- "I approach the checkpoint guard."
- "I try to convince her to let me through."
- Type `2` to select option 2

## Backend Options

By default, the agent auto-detects in this order:
1. **LM Studio** — Free, runs locally (localhost:1234)
2. **Ollama** — Free, runs locally (localhost:11434)

Use `/backend <name>` to switch (lmstudio, ollama, auto).
"""
    console.print(Markdown(help_text))


def show_choices(choices):
    """Display choice panel for player options (legacy - use render_choice_block for new style)."""
    if choices.stakes == "high":
        # Rusted red for danger/hinge moments
        title = f"[bold {THEME['danger']}]DECISION[/bold {THEME['danger']}]"
        if choices.context:
            title += f" [{THEME['secondary']}]{choices.context}[/{THEME['secondary']}]"
        box_style = THEME["danger"]
    else:
        title = None
        box_style = THEME["primary"]

    choice_text = "\n".join(
        f"[{THEME['accent']}]{i}.[/{THEME['accent']}] {opt}"
        for i, opt in enumerate(choices.options, 1)
    )

    if title:
        console.print(Panel(choice_text, title=title, border_style=box_style))
    else:
        console.print(Panel(choice_text, border_style=box_style, padding=(0, 1)))


# -----------------------------------------------------------------------------
# Block-Based Output (Phase 1.1)
# -----------------------------------------------------------------------------

def _format_block_title(block_type: BlockType, timestamp: datetime | None = None) -> str:
    """
    Format a block title with timestamp and type indicator.

    Returns a string like: "[14:32] NARRATIVE"
    """
    style = BLOCK_STYLES[block_type]
    color = style["color"]

    # Format timestamp
    if timestamp is None:
        timestamp = datetime.now()
    time_str = timestamp.strftime("%H:%M")

    return f"[{time_str}] {block_type.value}"


def detect_block_type(content: str) -> BlockType:
    """
    Detect the type of content block based on its contents.

    Intel indicators: faction intel, data, reports, coordinates
    Narrative: everything else (default)

    Args:
        content: The text content to analyze

    Returns:
        BlockType enum value
    """
    content_lower = content.lower()

    # Intel indicators
    intel_keywords = [
        "intel:", "report:", "data:", "coordinates:",
        "faction intel", "intelligence report",
        "surveillance", "decoded message",
        "transmission", "intercepted",
        "classified", "dossier",
    ]

    for keyword in intel_keywords:
        if keyword in content_lower:
            return BlockType.INTEL

    # Default to narrative
    return BlockType.NARRATIVE


def render_block(
    content: str,
    block_type: BlockType | None = None,
    timestamp: datetime | None = None,
    high_stakes: bool = False,
    context: str | None = None,
) -> None:
    """
    Render content as a discrete, timestamped block.

    Args:
        content: The text content to display
        block_type: Type of block (auto-detected if None)
        timestamp: Timestamp to display (uses current time if None)
        high_stakes: Whether this is a high-stakes moment (affects styling)
        context: Optional context string for the block title
    """
    if block_type is None:
        block_type = detect_block_type(content)

    if timestamp is None:
        timestamp = datetime.now()

    style = BLOCK_STYLES[block_type]
    color = style["color"]

    # High stakes overrides color
    if high_stakes:
        color = THEME["danger"]

    # Build title
    title = _format_block_title(block_type, timestamp)
    if context:
        title += f" - {context}"

    # Create panel with block styling
    console.print(Panel(
        content,
        title=f"[bold {color}]{title}[/bold {color}]",
        title_align="left",
        border_style=color,
        box=ROUNDED,
        padding=(0, 1),
    ))


def render_narrative_block(
    content: str,
    timestamp: datetime | None = None,
) -> None:
    """
    Render GM narrative in a timestamped block.

    Args:
        content: The narrative text
        timestamp: Optional timestamp (uses current time if None)
    """
    render_block(
        content=content,
        block_type=BlockType.NARRATIVE,
        timestamp=timestamp,
    )


def render_intel_block(
    content: str,
    timestamp: datetime | None = None,
    source: str | None = None,
) -> None:
    """
    Render intelligence/data in a timestamped block.

    Args:
        content: The intel text
        timestamp: Optional timestamp (uses current time if None)
        source: Optional source identifier (e.g., faction name)
    """
    render_block(
        content=content,
        block_type=BlockType.INTEL,
        timestamp=timestamp,
        context=source,
    )


def render_choice_block(
    choices,
    timestamp: datetime | None = None,
) -> None:
    """
    Render player choices in a timestamped block.

    Args:
        choices: ChoiceBlock object with options and stakes
        timestamp: Optional timestamp (uses current time if None)
    """
    if timestamp is None:
        timestamp = datetime.now()

    # Determine styling based on stakes
    if choices.stakes == "high":
        color = THEME["danger"]
        title_prefix = "DECISION"
    else:
        color = BLOCK_STYLES[BlockType.CHOICE]["color"]
        title_prefix = "CHOICE"

    # Build title
    time_str = timestamp.strftime("%H:%M")
    title = f"[{time_str}] {title_prefix}"
    if choices.context:
        title += f" - {choices.context}"

    # Format choices
    choice_text = "\n".join(
        f"[{THEME['accent']}]{i}.[/{THEME['accent']}] {opt}"
        for i, opt in enumerate(choices.options, 1)
    )

    console.print(Panel(
        choice_text,
        title=f"[bold {color}]{title}[/bold {color}]",
        title_align="left",
        border_style=color,
        box=ROUNDED,
        padding=(0, 1),
    ))


def render_system_block(
    content: str,
    timestamp: datetime | None = None,
    context: str | None = None,
) -> None:
    """
    Render system messages in a timestamped block.

    Args:
        content: The system message text
        timestamp: Optional timestamp (uses current time if None)
        context: Optional context string
    """
    render_block(
        content=content,
        block_type=BlockType.SYSTEM,
        timestamp=timestamp,
        context=context,
    )


# -----------------------------------------------------------------------------
# Persistent Status Bar
# -----------------------------------------------------------------------------

class StatusBar:
    """
    Persistent status bar showing character, mission, energy state, and context strain.

    Tracks previous values to show deltas (e.g., "68% -> 53%").
    Now includes strain tier indicator for context pressure visualization.
    """

    def __init__(self):
        self._prev_energy: int | None = None
        self._prev_credits: int | None = None
        self._enabled: bool = True
        self._current_strain_tier: "StrainTier | None" = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    def toggle(self) -> bool:
        """Toggle status bar on/off. Returns new state."""
        self._enabled = not self._enabled
        return self._enabled

    def set_strain_tier(self, tier: "StrainTier | None") -> None:
        """Update the current strain tier for display."""
        self._current_strain_tier = tier

    def format(
        self,
        campaign: Campaign | None,
        strain_tier: "StrainTier | None" = None,
    ) -> Text | None:
        """
        Format the status bar for display.

        Args:
            campaign: Current campaign state
            strain_tier: Optional strain tier (uses stored value if None)

        Returns None if disabled or no campaign loaded.
        """
        if not self._enabled or not campaign:
            return None

        # Use provided tier or fall back to stored value
        tier = strain_tier if strain_tier is not None else self._current_strain_tier

        text = Text()

        # Character info
        if campaign.characters:
            char = campaign.characters[0]
            display_name = char.callsign if char.callsign else char.name
            text.append(f" {display_name}", style=f"bold {THEME['secondary']}")
        else:
            text.append(" No Character", style=f"{THEME['dim']}")

        text.append(" | ", style=THEME["dim"])

        # Mission info
        if campaign.session:
            mission_title = campaign.session.mission_title
            if len(mission_title) > 20:
                mission_title = mission_title[:18] + "..."
            phase = campaign.session.phase.value.title()
            text.append(f"{mission_title}", style=THEME["primary"])
            text.append(f" ({phase})", style=THEME["dim"])
        else:
            text.append("No Mission", style=THEME["dim"])

        text.append(" | ", style=THEME["dim"])

        # Location
        from ..state.schema import Location
        loc = campaign.location
        loc_short = {
            Location.SAFE_HOUSE: "Safe",
            Location.FIELD: "Field",
            Location.FACTION_HQ: "HQ",
            Location.MARKET: "Mkt",
            Location.TRANSIT: "Transit",
        }.get(loc, loc.value[:5])
        if loc == Location.FACTION_HQ and campaign.location_faction:
            faction_abbrev = campaign.location_faction.value[:3].upper()
            text.append(f"@{loc_short}:{faction_abbrev}", style=THEME["secondary"])
        else:
            text.append(f"@{loc_short}", style=THEME["secondary"])

        text.append(" | ", style=THEME["dim"])

        # Social energy with delta
        if campaign.characters:
            char = campaign.characters[0]
            energy = char.social_energy
            current = energy.current

            # Energy color based on state
            if current >= 51:
                energy_color = THEME["accent"]
            elif current >= 26:
                energy_color = THEME["warning"]
            else:
                energy_color = THEME["danger"]

            # Short name (max 12 chars)
            energy_name = energy.name[:12] if len(energy.name) > 12 else energy.name

            # Show delta if we have previous value
            if self._prev_energy is not None and self._prev_energy != current:
                delta = current - self._prev_energy
                if delta > 0:
                    delta_str = f" +{delta}"
                    delta_style = THEME["accent"]
                else:
                    delta_str = f" {delta}"
                    delta_style = THEME["danger"]
                text.append(f"{energy_name}: {current}%", style=energy_color)
                text.append(delta_str, style=f"bold {delta_style}")
            else:
                text.append(f"{energy_name}: {current}%", style=energy_color)

            # Update tracked value
            self._prev_energy = current

        text.append(" | ", style=THEME["dim"])

        # Strain tier indicator (context pressure)
        if tier is not None and StrainTier is not None:
            glyph, color, description = get_strain_info(tier.value)
            text.append(glyph, style=f"bold {color}")
            # Show tier name only for non-normal tiers
            if tier.value != "normal":
                tier_label = tier.value.upper().replace("_", " ")
                text.append(f" {tier_label}", style=color)
            text.append(" | ", style=THEME["dim"])

        # Session count
        text.append(f"Session {campaign.meta.session_count}", style=THEME["dim"])
        text.append(" ", style="")

        return text

    def render(
        self,
        campaign: Campaign | None,
        strain_tier: "StrainTier | None" = None,
    ) -> None:
        """
        Render the status bar to console.

        Args:
            campaign: Current campaign state
            strain_tier: Optional strain tier for context pressure display
        """
        content = self.format(campaign, strain_tier=strain_tier)
        if content:
            console.print(Panel(
                content,
                box=ROUNDED,
                padding=(0, 0),
                style=THEME["dim"],
            ))

    def reset_tracking(self) -> None:
        """Reset delta tracking (call on campaign load)."""
        self._prev_energy = None
        self._prev_credits = None
        self._current_strain_tier = None




# Shared status bar instance
status_bar = StatusBar()


# -----------------------------------------------------------------------------
# NPC Codec Boxes (MGS-style dialogue frames)
# -----------------------------------------------------------------------------

def render_codec_box(
    npc_name: str,
    faction: str,
    dialogue: str,
    role: str | None = None,
    disposition: str = "neutral",
    memory_tag: str | None = None,
    show_disposition: bool = True,
) -> None:
    """
    Render an MGS codec-style dialogue box for NPC speech.

    Args:
        npc_name: NPC's display name
        faction: Faction ID (e.g., 'nexus', 'ember_colonies')
        dialogue: The NPC's speech text
        role: Optional role/title (e.g., 'Analyst', 'Cell Leader')
        disposition: Current disposition toward player
        memory_tag: Optional tag if NPC is referencing stored memory
        show_disposition: Whether to show disposition indicator
    """
    # Normalize faction ID
    faction_key = faction.lower().replace(" ", "_")
    faction_color = FACTION_COLORS.get(faction_key, THEME["secondary"])
    faction_glyph = g(faction_key) if faction_key in FACTION_COLORS else "◈"

    # Build header line
    header = Text()
    header.append(f"  {faction_glyph}  ", style=f"bold {faction_color}")
    header.append(npc_name.upper(), style=f"bold {THEME['secondary']}")

    # Build subtitle (faction + role + disposition)
    subtitle_parts = []

    # Faction display name
    faction_display = faction.replace("_", " ").title()
    if role:
        subtitle_parts.append(f"[{faction_display} — {role}]")
    else:
        subtitle_parts.append(f"[{faction_display}]")

    # Disposition indicator
    if show_disposition:
        disp_color = DISPOSITION_COLORS.get(disposition.lower(), "grey70")
        disp_indicator = _disposition_bar(disposition)
        subtitle_parts.append(f"[Disposition: {disposition.title()} {disp_indicator}]")

    subtitle = Text()
    subtitle.append("  ", style="dim")
    subtitle.append("  ".join(subtitle_parts), style=f"{THEME['dim']}")

    # Format dialogue with proper indentation
    dialogue_text = Text()
    dialogue_text.append("\n")

    # Wrap dialogue in quotes, indent
    lines = dialogue.split("\n")
    for i, line in enumerate(lines):
        if i == 0:
            dialogue_text.append(f'  "{line}', style=THEME["secondary"])
        else:
            dialogue_text.append(f"\n   {line}", style=THEME["secondary"])
    dialogue_text.append('"', style=THEME["secondary"])

    # Memory tag if present
    if memory_tag:
        dialogue_text.append(f"\n{'':>40}", style="dim")
        dialogue_text.append(f"[⚡ {memory_tag}]", style=f"italic {THEME['warning']}")

    # Combine all parts
    content = Text()
    content.append_text(header)
    content.append("\n")
    content.append_text(subtitle)
    content.append_text(dialogue_text)

    # Render the panel with faction-colored border
    console.print(Panel(
        content,
        border_style=faction_color,
        box=CODEC_BOX,
        padding=(0, 1),
    ))


def _disposition_bar(disposition: str, width: int = 5) -> str:
    """Generate a visual disposition indicator."""
    levels = ["hostile", "wary", "neutral", "warm", "loyal"]
    try:
        level_idx = levels.index(disposition.lower())
    except ValueError:
        level_idx = 2  # Default to neutral

    filled = level_idx + 1
    return "▰" * filled + "▱" * (width - filled)


# Custom box style for codec boxes (double-line border)
from rich.box import Box, DOUBLE

# Use Rich's built-in DOUBLE box for codec frames
CODEC_BOX = DOUBLE


def render_codec_dialogue(
    npc_name: str,
    faction: str,
    exchanges: list[dict],
    role: str | None = None,
    disposition: str = "neutral",
) -> None:
    """
    Render a multi-turn codec dialogue sequence.

    Args:
        npc_name: NPC's display name
        faction: Faction ID
        exchanges: List of dicts with 'speaker' and 'text' keys
        role: Optional role/title
        disposition: Current disposition
    """
    for exchange in exchanges:
        speaker = exchange.get("speaker", "npc")
        text = exchange.get("text", "")
        memory = exchange.get("memory_tag")

        if speaker == "npc":
            render_codec_box(
                npc_name=npc_name,
                faction=faction,
                dialogue=text,
                role=role,
                disposition=disposition,
                memory_tag=memory,
            )
        else:
            # Player speech - simpler box
            console.print(Panel(
                f'[{THEME["accent"]}]> {text}[/{THEME["accent"]}]',
                border_style=THEME["primary"],
                padding=(0, 1),
            ))
        console.print()  # Spacing between exchanges
