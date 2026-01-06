"""
Display and rendering helpers for SENTINEL CLI.

Handles theming, banners, status displays, and visual output.
"""

import time
import random
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text
from prompt_toolkit.styles import Style as PTStyle

from .glyphs import (
    g, energy_bar,
    format_context_meter, estimate_conversation_tokens,
    CONTEXT_LIMITS,
)


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
        console.print(f"[{THEME['dim']}]  Start LM Studio or set ANTHROPIC_API_KEY[/{THEME['dim']}]")


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
| `/consult <q>` | Ask faction advisors for perspectives |
| `/debrief` | End session with reflection prompts |
| `/history` | View campaign chronicle |
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
| `/lore` | Show lore status, test retrieval |
| `/npc [name]` | View NPC info and personal standing |
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
2. **Claude API** — Requires ANTHROPIC_API_KEY
3. **OpenRouter** — Multi-model API, requires OPENROUTER_API_KEY
4. **Gemini CLI** — Google AI, requires `gemini` installed
5. **Codex CLI** — OpenAI, requires `codex` installed

Use `/backend <name>` to switch (lmstudio, claude, openrouter, gemini, codex).
"""
    console.print(Markdown(help_text))


def show_choices(choices):
    """Display choice panel for player options."""
    if choices.stakes == "high":
        # Rusted red for danger/hinge moments
        title = f"[bold {THEME['danger']}]◈ DECISION ◈[/bold {THEME['danger']}]"
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
