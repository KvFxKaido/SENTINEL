"""
Command-line interface for SENTINEL.

Provides the main game loop and command handling.
Supports LM Studio (local) and Claude (API) backends.
"""

import sys
import time
import random
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style as PTStyle

from ..state import CampaignManager, Campaign, Character, Background
from ..state.schema import (
    SessionState, MissionBriefing, MissionType, MissionPhase,
    SessionReflection, HistoryType,
)
from ..agent import SentinelAgent
from ..llm.base import Message
from .choices import parse_response, ChoiceBlock
from .glyphs import (
    g, energy_bar, standing_indicator,
    format_context_meter, context_warning, estimate_conversation_tokens,
    CONTEXT_LIMITS,
)
from ..tools.hinge_detector import detect_hinge


console = Console()

# Command completer for slash commands with descriptions
COMMAND_META = {
    "/new": "Create a new campaign",
    "/char": "Create a character",
    "/start": "Begin the story",
    "/mission": "Get a new mission",
    "/consult": "Ask the council for advice",
    "/debrief": "End session",
    "/history": "View chronicle",
    "/load": "Load campaign",
    "/save": "Save campaign",
    "/list": "List campaigns",
    "/status": "Show status",
    "/backend": "Switch LLM backend",
    "/model": "Switch model",
    "/lore": "Search lore",
    "/roll": "Roll dice",
    "/help": "Show help",
    "/quit": "Exit",
    "/exit": "Exit",
}
command_completer = WordCompleter(
    list(COMMAND_META.keys()),
    ignore_case=True,
    match_middle=False,
    meta_dict=COMMAND_META,
)

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


def show_backend_status(agent: SentinelAgent):
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
    manager: CampaignManager,
    agent: SentinelAgent | None = None,
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
| `/load` | Load an existing campaign |
| `/save` | Save current campaign |
| `/list` | List all campaigns |
| `/status` | Show current status |
| `/backend` | Show/change LLM backend |
| `/model` | List/switch LM Studio models |
| `/lore` | Show lore status, test retrieval |
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


def show_choices(choices: ChoiceBlock):
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


# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------

def cmd_new(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Create a new campaign."""
    name = " ".join(args) if args else Prompt.ask("Campaign name")
    campaign = manager.create_campaign(name)
    console.print(f"[green]Created campaign:[/green] {campaign.meta.name}")
    console.print("[dim]Use /char to create your character[/dim]")


def cmd_load(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Load a campaign."""
    if not args:
        # Show list and prompt
        campaigns = manager.list_campaigns()
        if not campaigns:
            console.print("[yellow]No campaigns found. Use /new to create one.[/yellow]")
            return

        table = Table(title="Campaigns")
        table.add_column("#", style="dim")
        table.add_column("Name")
        table.add_column("Sessions")
        table.add_column("Last Played")

        for i, c in enumerate(campaigns, 1):
            table.add_row(
                str(i),
                c["name"],
                str(c["session_count"]),
                c["display_time"],
            )

        console.print(table)
        selection = Prompt.ask("Load campaign #")
        args = [selection]

    campaign = manager.load_campaign(args[0])
    if campaign:
        console.print(f"[green]Loaded:[/green] {campaign.meta.name}")
        show_status(manager)
    else:
        console.print("[red]Campaign not found[/red]")


def cmd_list(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """List all campaigns."""
    campaigns = manager.list_campaigns()

    if not campaigns:
        console.print("[dim]No campaigns found[/dim]")
        return

    table = Table(title="Campaigns")
    table.add_column("#", style="dim")
    table.add_column("Name")
    table.add_column("Phase")
    table.add_column("Sessions")
    table.add_column("Last Played")

    for i, c in enumerate(campaigns, 1):
        table.add_row(
            str(i),
            c["name"],
            str(c["phase"]),
            str(c["session_count"]),
            c["display_time"],
        )

    console.print(table)


def cmd_backend(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Show or change backend."""
    valid_backends = ["lmstudio", "claude", "openrouter", "gemini", "codex", "auto"]

    if not args:
        show_backend_status(agent)
        console.print(f"\n[{THEME['dim']}]Available backends:[/{THEME['dim']}]")
        console.print(f"  [{THEME['accent']}]lmstudio[/{THEME['accent']}]   - Local LLM (free, requires LM Studio)")
        console.print(f"  [{THEME['accent']}]claude[/{THEME['accent']}]     - Anthropic API (requires ANTHROPIC_API_KEY)")
        console.print(f"  [{THEME['accent']}]openrouter[/{THEME['accent']}] - Multi-model API (requires OPENROUTER_API_KEY)")
        console.print(f"  [{THEME['accent']}]gemini[/{THEME['accent']}]     - Google CLI (requires gemini installed)")
        console.print(f"  [{THEME['accent']}]codex[/{THEME['accent']}]      - OpenAI CLI (requires codex installed)")
        console.print(f"  [{THEME['accent']}]auto[/{THEME['accent']}]       - Auto-detect best available")
        console.print(f"\n[{THEME['dim']}]Use /backend <name> to switch[/{THEME['dim']}]")
        return

    backend = args[0].lower()
    if backend not in valid_backends:
        console.print(f"[{THEME['danger']}]Unknown backend: {backend}[/{THEME['danger']}]")
        console.print(f"[{THEME['dim']}]Valid options: {', '.join(valid_backends)}[/{THEME['dim']}]")
        return

    # Return new backend choice - will be handled by main loop
    return backend


def cmd_lore(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Show lore status and test retrieval."""
    if not agent.lore_retriever:
        console.print("[yellow]No lore directory configured[/yellow]")
        return

    retriever = agent.lore_retriever
    console.print(f"\n[bold]Lore System[/bold]")
    console.print(f"  Directory: {retriever.lore_dir}")
    console.print(f"  Chunks indexed: {retriever.chunk_count}")

    # Show what's in the index
    index = retriever.index
    if index["by_faction"]:
        factions = ", ".join(sorted(index["by_faction"].keys()))
        console.print(f"  Factions tagged: {factions}")

    if index["by_theme"]:
        themes = ", ".join(sorted(index["by_theme"].keys()))
        console.print(f"  Themes tagged: {themes}")

    # Test retrieval if query provided
    if args:
        query = " ".join(args)
        console.print(f"\n[dim]Searching for: {query}[/dim]")
        results = retriever.retrieve(query=query, limit=2)
        if results:
            for r in results:
                console.print(f"\n[cyan]{r.chunk.title}[/cyan] ({r.chunk.source})")
                console.print(f"  Score: {r.score:.1f} — {', '.join(r.match_reasons)}")
                preview = r.chunk.content[:200].replace('\n', ' ')
                console.print(f"  [dim]{preview}...[/dim]")
        else:
            console.print("[dim]No matches found[/dim]")
    else:
        console.print("\n[dim]Use /lore <query> to test retrieval[/dim]")


def cmd_model(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """List or switch LM Studio models."""
    if agent.backend != "lmstudio":
        console.print("[yellow]Model switching only available for LM Studio backend[/yellow]")
        return

    # Get client and list models
    client = agent.client
    if not hasattr(client, "list_models"):
        console.print("[yellow]Model listing not supported[/yellow]")
        return

    models = client.list_models()
    if not models:
        console.print("[yellow]No models available (is LM Studio running?)[/yellow]")
        return

    current = client.model_name

    if not args:
        # Show available models
        console.print("\n[bold]Available Models:[/bold]")
        for i, model in enumerate(models, 1):
            marker = "[cyan]>[/cyan] " if model == current else "  "
            console.print(f"  {marker}{i}. {model}")
        console.print("\n[dim]Use /model <number> or /model <name> to switch[/dim]")
        return

    # Switch model
    selection = args[0]

    # Handle numeric selection
    if selection.isdigit():
        idx = int(selection) - 1
        if 0 <= idx < len(models):
            selection = models[idx]
        else:
            console.print(f"[red]Invalid selection. Choose 1-{len(models)}[/red]")
            return

    # Set the model
    client.set_model(selection)
    console.print(f"[green]Switched to:[/green] {selection}")

    # Check tool support
    if client.supports_tools:
        console.print("[dim]  Tool calling supported[/dim]")
    else:
        console.print("[yellow]  Tool calling not supported by this model[/yellow]")


def cmd_char(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Create a character."""
    from ..state.schema import SocialEnergy, EstablishingIncident

    if not manager.current:
        console.print("[yellow]Load or create a campaign first[/yellow]")
        return

    # Identity
    console.print(f"\n[bold {THEME['primary']}]◈ SUBJECT FILE ◈[/bold {THEME['primary']}]")

    name = Prompt.ask("Legal name")
    callsign = Prompt.ask("Callsign (optional)", default="")
    pronouns = Prompt.ask("Pronouns (optional)", default="")
    age = Prompt.ask("Age (optional, e.g. 'early 30s', 'weathered')", default="")

    # Background with descriptions
    console.print(f"\n[bold]Background:[/bold]")
    bg_descriptions = {
        "Caretaker": "Healer, protector — the one who keeps others alive",
        "Survivor": "Endured the worst, still standing",
        "Operative": "Trained for missions, intel, shadows",
        "Technician": "Keeps the machines running",
        "Pilgrim": "Seeker, wanderer, searching for meaning",
        "Witness": "Observer, recorder, keeper of truth",
        "Ghost": "Erased, forgotten, never officially existed",
    }
    backgrounds = list(Background)
    for i, bg in enumerate(backgrounds, 1):
        desc = bg_descriptions.get(bg.value, "")
        console.print(f"  [{THEME['accent']}]{i}.[/{THEME['accent']}] {bg.value} [{THEME['dim']}]— {desc}[/{THEME['dim']}]")

    bg_choice = Prompt.ask("Choose background (1-7)")
    background = backgrounds[int(bg_choice) - 1]

    # Appearance
    console.print(f"\n[{THEME['dim']}]Visible details: scars, posture, clothing, devices (optional)[/{THEME['dim']}]")
    appearance = Prompt.ask("Appearance", default="")

    # Survival note
    console.print(f"\n[{THEME['dim']}]Why is this person still alive? (optional)[/{THEME['dim']}]")
    survival_note = Prompt.ask("Survival", default="")

    # Social energy customization
    console.print(f"\n[bold]Social Energy[/bold]")
    energy_name = Prompt.ask(
        "Name your energy track",
        default="Pistachios"
    )

    console.print(f"[{THEME['dim']}]What restores your energy? (comma-separated, or skip)[/{THEME['dim']}]")
    restorers_input = Prompt.ask("Restorers", default="")
    restorers = [r.strip() for r in restorers_input.split(",") if r.strip()]

    console.print(f"[{THEME['dim']}]What drains your energy? (comma-separated, or skip)[/{THEME['dim']}]")
    drains_input = Prompt.ask("Drains", default="")
    drains = [d.strip() for d in drains_input.split(",") if d.strip()]

    # Establishing incident
    console.print(f"\n[bold]Establishing Incident[/bold]")
    console.print(f"[{THEME['dim']}]What pulled you into this life? (1-2 sentences, or skip)[/{THEME['dim']}]")
    incident_summary = Prompt.ask("Incident", default="")

    establishing = None
    if incident_summary:
        establishing = EstablishingIncident(summary=incident_summary)

    # Build character
    character = Character(
        name=name,
        callsign=callsign,
        pronouns=pronouns,
        age=age,
        appearance=appearance,
        survival_note=survival_note,
        background=background,
        social_energy=SocialEnergy(
            name=energy_name,
            restorers=restorers,
            drains=drains,
        ),
        establishing_incident=establishing,
    )

    manager.add_character(character)

    # Display
    display_name = f"{name} ({callsign})" if callsign else name
    console.print(f"\n[{THEME['accent']}]Created:[/{THEME['accent']}] [{THEME['secondary']}]{display_name}[/{THEME['secondary']}]")
    if pronouns:
        console.print(f"  [{THEME['dim']}]Pronouns:[/{THEME['dim']}] {pronouns}")
    console.print(f"  [{THEME['dim']}]Background:[/{THEME['dim']}] {background.value}")
    console.print(f"  [{THEME['dim']}]Expertise:[/{THEME['dim']}] {', '.join(character.expertise)}")
    if appearance:
        console.print(f"  [{THEME['dim']}]Appearance:[/{THEME['dim']}] {appearance[:60]}{'...' if len(appearance) > 60 else ''}")
    if survival_note:
        console.print(f"  [{THEME['dim']}]Still alive because:[/{THEME['dim']}] {survival_note[:60]}{'...' if len(survival_note) > 60 else ''}")
    console.print(f"  [{THEME['dim']}]{energy_name}:[/{THEME['dim']}] [{THEME['accent']}]{character.social_energy.current}%[/{THEME['accent']}]")
    if restorers:
        console.print(f"  [{THEME['dim']}]Restores:[/{THEME['dim']}] {', '.join(restorers)}")
    if drains:
        console.print(f"  [{THEME['dim']}]Drains:[/{THEME['dim']}] {', '.join(drains)}")
    if establishing:
        console.print(f"  [{THEME['dim']}]Origin:[/{THEME['dim']}] \"{incident_summary[:60]}{'...' if len(incident_summary) > 60 else ''}\"")
    console.print(f"\n[{THEME['dim']}]Type /start to begin your story[/{THEME['dim']}]")


def cmd_roll(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Roll a skill check."""
    from ..tools.dice import roll_check

    if len(args) < 2:
        console.print("[yellow]Usage: /roll <skill> <dc>[/yellow]")
        console.print("  Example: /roll Persuasion 14")
        return

    skill = args[0]
    try:
        dc = int(args[1])
    except ValueError:
        console.print("[red]DC must be a number (10, 14, 18, or 22)[/red]")
        return

    # Check for advantage/disadvantage flags
    advantage = "--adv" in args or "-a" in args
    disadvantage = "--dis" in args or "-d" in args

    result = roll_check(
        skill=skill,
        dc=dc,
        trained=True,
        advantage=advantage,
        disadvantage=disadvantage,
    )

    # Format output
    rolls_str = ", ".join(str(r) for r in result.rolls)
    if len(result.rolls) > 1:
        adv_glyph = g("advantage") if advantage else g("disadvantage")
        rolls_str = f"{adv_glyph} [{rolls_str}] {g('arrow')} {result.used}"

    result_glyph = g("success") if result.success else g("failure")
    color = THEME["accent"] if result.success else THEME["danger"]
    console.print(
        f"[{THEME['dim']}]{g('roll')}[/{THEME['dim']}] "
        f"[bold {THEME['secondary']}]{skill}[/bold {THEME['secondary']}] vs DC {dc}: "
        f"[{color}]{rolls_str} + {result.modifier} = {result.total}[/{color}] "
        f"[{color}]{result_glyph} {result.narrative}[/{color}]"
    )


def cmd_debrief(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """End session with reflection prompts."""
    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    console.print(f"\n[bold {THEME['primary']}]◈ SESSION DEBRIEF ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['dim']}]Answer what feels relevant. Skip with Enter.[/{THEME['dim']}]\n")

    # Reflection prompts from the Cipher sheet
    cost = Prompt.ask(f"[{THEME['secondary']}]What did this cost you?[/{THEME['secondary']}]", default="")
    learned = Prompt.ask(f"[{THEME['secondary']}]What did you learn?[/{THEME['secondary']}]", default="")
    refuse = Prompt.ask(f"[{THEME['secondary']}]What would you refuse to do again?[/{THEME['secondary']}]", default="")

    # Build reflections object for storage
    reflections_obj = SessionReflection(
        cost=cost,
        learned=learned,
        would_refuse=refuse,
    )

    # Build summary for display
    reflection_lines = []
    if cost:
        reflection_lines.append(f"Cost: {cost}")
    if learned:
        reflection_lines.append(f"Learned: {learned}")
    if refuse:
        reflection_lines.append(f"Would refuse: {refuse}")

    if not reflection_lines:
        console.print(f"[{THEME['dim']}]No reflections recorded.[/{THEME['dim']}]")
        summary = "Session concluded"
    else:
        console.print(f"\n[{THEME['dim']}]Reflections noted.[/{THEME['dim']}]")
        summary = "; ".join(reflection_lines)

    # Increment session count BEFORE end_session (so it logs correctly)
    manager.current.meta.session_count += 1

    # End session with proper logging
    entry = manager.end_session(
        summary=summary,
        reflections=reflections_obj if reflection_lines else None,
        reset_social_energy=True,
    )

    console.print(f"\n[{THEME['accent']}]Session {manager.current.meta.session_count} complete.[/{THEME['accent']}]")
    console.print(f"[{THEME['dim']}]Social energy reset. Chronicle updated. Campaign saved.[/{THEME['dim']}]")

    # Offer to wrap up with GM
    if agent.is_available and reflection_lines:
        wrap = Prompt.ask("\nAsk the GM to narrate the aftermath?", choices=["y", "n"], default="n")
        if wrap == "y":
            prompt = (
                f"The session is ending. Here are the player's reflections:\n"
                f"{chr(10).join(reflection_lines)}\n\n"
                f"Provide a brief narrative wrap-up (2-3 paragraphs) that honors these reflections "
                f"and sets up threads for next session."
            )
            return ("gm_prompt", prompt)

    return None


def cmd_history(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """View campaign chronicle."""
    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    history = manager.current.history
    if not history:
        console.print(f"[{THEME['dim']}]No chronicle entries yet.[/{THEME['dim']}]")
        return

    # Optional filter by type
    filter_type = args[0].lower() if args else None
    type_map = {
        "mission": HistoryType.MISSION,
        "hinge": HistoryType.HINGE,
        "faction": HistoryType.FACTION_SHIFT,
        "consequence": HistoryType.CONSEQUENCE,
        "canon": HistoryType.CANON,
    }

    if filter_type and filter_type in type_map:
        history = [h for h in history if h.type == type_map[filter_type]]
        if not history:
            console.print(f"[{THEME['dim']}]No {filter_type} entries found.[/{THEME['dim']}]")
            return

    console.print(f"\n[bold {THEME['primary']}]◈ CHRONICLE ◈[/bold {THEME['primary']}]")
    if filter_type:
        console.print(f"[{THEME['dim']}]Filtered by: {filter_type}[/{THEME['dim']}]\n")

    # Type glyphs and colors
    type_style = {
        HistoryType.MISSION: (g("phase"), THEME["accent"]),
        HistoryType.HINGE: (g("hinge"), THEME["danger"]),
        HistoryType.FACTION_SHIFT: (g("faction"), THEME["warning"]),
        HistoryType.CONSEQUENCE: (g("thread"), THEME["secondary"]),
        HistoryType.CANON: (g("success"), THEME["primary"]),
    }

    # Display entries (most recent first)
    for entry in reversed(history[-20:]):  # Show last 20
        glyph, color = type_style.get(entry.type, ("•", THEME["dim"]))
        permanent_mark = " [bold]★[/bold]" if entry.is_permanent else ""

        # Format timestamp
        ts = entry.timestamp.strftime("%Y-%m-%d")

        console.print(
            f"[{THEME['dim']}]S{entry.session} {ts}[/{THEME['dim']}] "
            f"[{color}]{glyph}[/{color}] {entry.summary}{permanent_mark}"
        )

        # Show extra details for certain types
        if entry.type == HistoryType.HINGE and entry.hinge:
            console.print(f"  [{THEME['dim']}]Choice: {entry.hinge.choice}[/{THEME['dim']}]")
            if entry.hinge.what_shifted:
                console.print(f"  [{THEME['dim']}]Shifted: {entry.hinge.what_shifted}[/{THEME['dim']}]")

        if entry.type == HistoryType.MISSION and entry.mission and entry.mission.reflections:
            r = entry.mission.reflections
            if r.cost:
                console.print(f"  [{THEME['dim']}]Cost: {r.cost}[/{THEME['dim']}]")
            if r.learned:
                console.print(f"  [{THEME['dim']}]Learned: {r.learned}[/{THEME['dim']}]")

    # Show count
    total = len(manager.current.history)
    shown = min(20, len(history))
    if total > 20:
        console.print(f"\n[{THEME['dim']}]Showing {shown} of {total} entries. Filter with: /history <type>[/{THEME['dim']}]")

    console.print(f"\n[{THEME['dim']}]Types: mission, hinge, faction, consequence, canon[/{THEME['dim']}]")
    return None


def cmd_consult(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Consult the council of advisors."""
    if not args:
        console.print(f"[{THEME['warning']}]Usage: /consult <question>[/{THEME['warning']}]")
        console.print(f"[{THEME['dim']}]Example: /consult Should I accept the Syndicate's offer?[/{THEME['dim']}]")
        return None

    if not agent.is_available:
        console.print(f"[{THEME['warning']}]No LLM backend available[/{THEME['warning']}]")
        return None

    question = " ".join(args)

    console.print(f"\n[bold {THEME['primary']}]◈ COUNCIL CONVENES ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['dim']}]Query: {question}[/{THEME['dim']}]\n")

    # Query all advisors in parallel
    with console.status(f"[{THEME['dim']}]Consulting advisors...[/{THEME['dim']}]"):
        responses = agent.consult(question)

    # Display each advisor's response
    advisor_colors = {
        "nexus": "cyan",
        "ember": "dark_goldenrod",
        "witness": "grey70",
    }

    for resp in responses:
        color = advisor_colors.get(resp.advisor, THEME["secondary"])

        if resp.error:
            console.print(Panel(
                f"[{THEME['danger']}]{resp.error}[/{THEME['danger']}]",
                title=f"[bold {color}]{resp.title}[/bold {color}]",
                border_style=color,
            ))
        else:
            console.print(Panel(
                resp.response,
                title=f"[bold {color}]{resp.title}[/bold {color}]",
                border_style=color,
            ))
        console.print()

    console.print(f"[{THEME['dim']}]The council has spoken. The choice remains yours.[/{THEME['dim']}]\n")
    return None


def cmd_mission(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Get a new mission from the GM."""
    if not manager.current:
        console.print("[yellow]Load or create a campaign first[/yellow]")
        return None

    if not manager.current.characters:
        console.print("[yellow]Create a character first (/char)[/yellow]")
        return None

    if not agent.is_available:
        console.print("[yellow]No LLM backend available[/yellow]")
        return None

    # Optional: let player specify a faction or type preference
    hint = " ".join(args) if args else ""

    prompt = (
        "Generate a mission briefing for me. Consider my current faction standings "
        "and any dormant threads that might be relevant. Present the situation, "
        "who's asking, what's at stake, and the competing truths involved."
    )
    if hint:
        prompt += f" I'm particularly interested in: {hint}"

    return ("gm_prompt", prompt)


def cmd_start(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Start the campaign with an establishing scene."""
    if not manager.current:
        console.print("[yellow]Create a campaign first (/new)[/yellow]")
        return None

    if not manager.current.characters:
        console.print("[yellow]Create a character first (/char)[/yellow]")
        return None

    if not agent.is_available:
        console.print("[yellow]No LLM backend available[/yellow]")
        return None

    char = manager.current.characters[0]

    prompt = (
        f"Begin the campaign. I'm playing {char.name}, a {char.background.value}. "
        f"Set an establishing scene that introduces the world and leads naturally "
        f"toward a situation where my skills might be needed. Start in motion — "
        f"don't over-explain, just drop me into the fiction."
    )

    return ("gm_prompt", prompt)


# -----------------------------------------------------------------------------
# Main Loop
# -----------------------------------------------------------------------------

def create_commands(
    manager: CampaignManager,
    agent: SentinelAgent,
    conversation: list | None = None,
):
    """Create command handlers with proper closures."""
    return {
        "/new": cmd_new,
        "/load": cmd_load,
        "/list": cmd_list,
        "/save": lambda m, a, args: (m.save_campaign(), console.print(f"[{THEME['accent']}]Saved[/{THEME['accent']}]")),
        "/status": lambda m, a, args: show_status(m, a, conversation),
        "/backend": cmd_backend,
        "/model": cmd_model,
        "/lore": cmd_lore,
        "/char": cmd_char,
        "/roll": cmd_roll,
        "/start": cmd_start,
        "/mission": cmd_mission,
        "/consult": cmd_consult,
        "/debrief": cmd_debrief,
        "/history": cmd_history,
        "/help": lambda m, a, args: show_help(),
        "/quit": lambda m, a, args: sys.exit(0),
        "/exit": lambda m, a, args: sys.exit(0),
    }


def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="SENTINEL - AI Game Master")
    parser.add_argument(
        "--no-animate", "-q",
        action="store_true",
        help="Skip banner animation"
    )
    args = parser.parse_args()

    # Show banner (with or without animation)
    show_banner(animate=not args.no_animate)

    # Initialize
    base_dir = Path(__file__).parent.parent.parent.parent  # SENTINEL root
    prompts_dir = Path(__file__).parent.parent.parent / "prompts"
    campaigns_dir = Path("campaigns")
    lore_dir = base_dir / "lore"

    manager = CampaignManager(campaigns_dir)
    agent = SentinelAgent(
        manager,
        prompts_dir=prompts_dir,
        lore_dir=lore_dir if lore_dir.exists() else None,
        backend="auto",
    )

    # Show backend status
    show_backend_status(agent)
    if agent.lore_retriever:
        console.print(f"[{THEME['dim']}]Lore: {agent.lore_retriever.chunk_count} chunks indexed[/{THEME['dim']}]")
    console.print(f"[{THEME['dim']}]Type /help for commands, or just start playing.[/{THEME['dim']}]\n")

    # Initialize state
    conversation: list[Message] = []
    last_choices: ChoiceBlock | None = None
    context_limit = CONTEXT_LIMITS["default"]  # 16k default

    # Create commands with conversation reference
    commands = create_commands(manager, agent, conversation)

    while True:
        try:
            # Build prompt with context meter
            if conversation:
                tokens = estimate_conversation_tokens(conversation)
                usage_ratio = min(tokens / context_limit, 1.0)
                meter = format_context_meter(conversation, context_limit)
                context_display = f"[{THEME['dim']}]{meter}[/{THEME['dim']}] "
            else:
                context_display = ""
                usage_ratio = 0.0

            # Show choice-aware prompt with autocomplete
            if last_choices:
                prompt_text = "1-4 or action > "
            else:
                prompt_text = "> "

            # Use prompt_toolkit for autocomplete on slash commands
            user_input = pt_prompt(
                prompt_text,
                completer=command_completer,
                style=pt_style,
                complete_while_typing=True,
            ).strip()

            if not user_input:
                continue

            # Handle numbered choice selection
            if last_choices and user_input.isdigit():
                choice_num = int(user_input)
                if 1 <= choice_num <= len(last_choices.options):
                    selected = last_choices.options[choice_num - 1]
                    # "Something else..." prompts for custom input
                    if "something else" in selected.lower():
                        user_input = Prompt.ask("[dim]What do you do?[/dim]")
                    else:
                        # Convert choice to action statement
                        user_input = selected if selected.startswith("I ") else f"I {selected.lower()}"
                    last_choices = None

            # Handle commands
            if user_input.startswith("/"):
                parts = user_input.split()
                cmd = parts[0].lower()
                args = parts[1:]

                if cmd in commands:
                    result = commands[cmd](manager, agent, args)

                    # Handle backend switch
                    if cmd == "/backend" and result:
                        console.print(f"[dim]Switching to {result}...[/dim]")
                        agent = SentinelAgent(
                            manager,
                            prompts_dir=prompts_dir,
                            lore_dir=lore_dir if lore_dir.exists() else None,
                            backend=result,
                        )
                        commands = create_commands(manager, agent, conversation)
                        show_backend_status(agent)
                        continue

                    # Handle GM prompt (from /start, /mission, etc.)
                    if isinstance(result, tuple) and result[0] == "gm_prompt":
                        user_input = result[1]
                        # Fall through to agent processing below
                    else:
                        continue
                else:
                    console.print(f"[{THEME['warning']}]Unknown command: {cmd}[/{THEME['warning']}]")
                    continue

            # Regular input - send to agent
            if not manager.current:
                console.print(f"[{THEME['warning']}]Start or load a campaign first (/new or /load)[/{THEME['warning']}]")
                continue

            if not agent.is_available:
                console.print(
                    f"[{THEME['warning']}]No LLM backend available.[/{THEME['warning']}]\n"
                    f"[{THEME['dim']}]Start LM Studio or set ANTHROPIC_API_KEY[/{THEME['dim']}]"
                )
                continue

            # Detect potential hinge moments before sending
            hinge = detect_hinge(user_input)
            if hinge:
                console.print(
                    f"\n[{THEME['warning']}]{g('hinge')} HINGE MOMENT DETECTED[/{THEME['warning']}] "
                    f"[{THEME['dim']}]({hinge.category.value}, {hinge.severity})[/{THEME['dim']}]"
                )

            # Get response from agent
            console.print()
            with console.status(f"[{THEME['dim']}]...[/{THEME['dim']}]"):
                try:
                    response = agent.respond(user_input, conversation)
                    conversation.append(Message(role="user", content=user_input))
                    conversation.append(Message(role="assistant", content=response))

                    # Auto-log hinge moment after GM confirms the action
                    if hinge and manager.current:
                        manager.log_hinge_moment(
                            situation=f"Player declared: {user_input[:100]}",
                            choice=hinge.matched_text,
                            reasoning=f"Category: {hinge.category.value}, Severity: {hinge.severity}",
                        )
                        console.print(
                            f"[{THEME['dim']}]{g('hinge')} Hinge logged to chronicle[/{THEME['dim']}]"
                        )
                except Exception as e:
                    response = f"[{THEME['danger']}]Error: {e}[/{THEME['danger']}]"
                    last_choices = None
                    console.print(Panel(response, border_style=THEME["danger"]))
                    console.print()
                    continue

            # Parse response for choices
            narrative, choices = parse_response(response)
            last_choices = choices

            # Display narrative - cold twilight blue border
            console.print(Panel(narrative, border_style=THEME["primary"]))

            # Display choices if present
            if choices:
                console.print()
                show_choices(choices)

            # Show context meter and warning after response
            tokens = estimate_conversation_tokens(conversation)
            usage_ratio = min(tokens / context_limit, 1.0)
            meter = format_context_meter(conversation, context_limit)
            console.print(f"[{THEME['dim']}]{meter}[/{THEME['dim']}]")

            # Show warning if context is getting full
            warning = context_warning(usage_ratio)
            if warning:
                console.print(f"[{THEME['warning']}]{g('warning')} {warning}[/{THEME['warning']}]")

            console.print()

        except KeyboardInterrupt:
            console.print(f"\n[{THEME['dim']}]Use /quit to exit[/{THEME['dim']}]")
        except EOFError:
            break


if __name__ == "__main__":
    main()
