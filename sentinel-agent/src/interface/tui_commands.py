"""
TUI Command Handlers for SENTINEL.

Each handler takes (app, log, args) where:
- app: The SENTINELApp instance
- log: The RichLog widget to write to
- args: List of command arguments

Handlers are registered with the command registry using set_tui_handler().
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text

from .command_registry import set_tui_handler, get_registry
from .glyphs import g

if TYPE_CHECKING:
    from .tui import SENTINELApp
    from textual.widgets import RichLog


# Theme colors (imported from tui.py at runtime to avoid circular imports)
class Theme:
    """Theme colors - mirrors tui.py Theme class."""
    TEXT = "#C0C0C0"
    ACCENT = "steel_blue"
    DIM = "grey50"
    FRIENDLY = "#2ECC71"
    UNFRIENDLY = "#E67E22"
    HOSTILE = "#E74C3C"
    WARNING = "#F39C12"
    DANGER = "#E74C3C"
    NEUTRAL = "grey70"
    ALLIED = "#3498DB"


# -----------------------------------------------------------------------------
# Campaign Commands
# -----------------------------------------------------------------------------

def tui_new(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Create a new campaign."""
    if not args:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /new <campaign name>[/{Theme.WARNING}]"))
        return
    name = " ".join(args)
    campaign = app.manager.create_campaign(name)
    log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Created: {campaign.meta.name}[/{Theme.FRIENDLY}]"))
    log.write(Text.from_markup(f"[{Theme.DIM}]Use /char to create your character[/{Theme.DIM}]"))
    app.refresh_all_panels()


def tui_load(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Load a campaign."""
    campaigns = app.manager.list_campaigns()
    if not campaigns:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaigns found. Use /new to create one.[/{Theme.WARNING}]"))
        return

    if args:
        campaign = app.manager.load_campaign(args[0])
        if campaign:
            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Loaded: {campaign.meta.name}[/{Theme.FRIENDLY}]"))
            app.refresh_all_panels()
        else:
            log.write(Text.from_markup(f"[{Theme.DANGER}]Campaign not found[/{Theme.DANGER}]"))
    else:
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]Campaigns:[/bold {Theme.TEXT}]"))
        for i, c in enumerate(campaigns, 1):
            log.write(Text.from_markup(
                f"  [{Theme.ACCENT}]{i}[/{Theme.ACCENT}] {c['name']} "
                f"[{Theme.DIM}]({c['session_count']} sessions, {c['display_time']})[/{Theme.DIM}]"
            ))
        log.write(Text.from_markup(f"[{Theme.DIM}]Type /load <number> to load[/{Theme.DIM}]"))


def tui_save(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Save current campaign."""
    if app.manager and app.manager.current:
        app.manager.save()
        log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Campaign saved![/{Theme.FRIENDLY}]"))
    else:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign to save[/{Theme.WARNING}]"))


def tui_list(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """List all campaigns."""
    campaigns = app.manager.list_campaigns()
    if not campaigns:
        log.write(Text.from_markup(f"[{Theme.DIM}]No campaigns found[/{Theme.DIM}]"))
    else:
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]Campaigns:[/bold {Theme.TEXT}]"))
        for i, c in enumerate(campaigns, 1):
            log.write(Text.from_markup(
                f"  [{Theme.ACCENT}]{i}[/{Theme.ACCENT}] {c['name']} "
                f"[{Theme.DIM}]({c['session_count']} sessions)[/{Theme.DIM}]"
            ))


def tui_delete(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Delete a campaign."""
    if not args:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /delete <campaign name or number>[/{Theme.WARNING}]"))
        return
    identifier = " ".join(args)
    if app.manager.delete_campaign(identifier):
        log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Campaign deleted[/{Theme.FRIENDLY}]"))
    else:
        log.write(Text.from_markup(f"[{Theme.DANGER}]Campaign not found[/{Theme.DANGER}]"))


# -----------------------------------------------------------------------------
# Character Commands
# -----------------------------------------------------------------------------

def tui_char(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Character creation (not yet supported in TUI)."""
    log.write(Text.from_markup(f"[{Theme.WARNING}]Character creation requires the regular CLI.[/{Theme.WARNING}]"))
    log.write(Text.from_markup(f"[{Theme.DIM}]Run: python -m src.interface.cli[/{Theme.DIM}]"))
    log.write(Text.from_markup(f"[{Theme.DIM}]Then use /char there, and /load here after.[/{Theme.DIM}]"))


def tui_roll(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Roll dice."""
    import random
    modifier = int(args[0]) if args and args[0].lstrip('-+').isdigit() else 0
    roll = random.randint(1, 20)
    total = roll + modifier
    mod_str = f" + {modifier}" if modifier > 0 else f" - {abs(modifier)}" if modifier < 0 else ""
    log.write(Text.from_markup(
        f"[{Theme.ACCENT}]d20{mod_str} = {roll}{mod_str} = [bold]{total}[/bold][/{Theme.ACCENT}]"
    ))


# -----------------------------------------------------------------------------
# Info Commands
# -----------------------------------------------------------------------------

def tui_status(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Show campaign status."""
    from .shared import get_campaign_status
    status = get_campaign_status(app.manager)
    if status:
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]{status['name']}[/bold {Theme.TEXT}]"))
        log.write(Text.from_markup(f"  Phase: {status['phase']}"))
        log.write(Text.from_markup(f"  Sessions: {status['session_count']}"))
    else:
        log.write(Text.from_markup(f"[{Theme.DIM}]No campaign loaded[/{Theme.DIM}]"))


def tui_factions(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Show faction standings."""
    from .shared import get_faction_standings
    data = get_faction_standings(app.manager)
    if not data:
        log.write(Text.from_markup(f"[{Theme.DIM}]No campaign loaded[/{Theme.DIM}]"))
        return

    standing_values = {"Hostile": -2, "Unfriendly": -1, "Neutral": 0, "Friendly": 1, "Allied": 2}
    standing_colors = {-2: Theme.HOSTILE, -1: Theme.UNFRIENDLY, 0: Theme.NEUTRAL, 1: Theme.FRIENDLY, 2: Theme.ALLIED}

    log.write(Text.from_markup(f"[bold {Theme.TEXT}]Faction Standings:[/bold {Theme.TEXT}]"))
    for f in data['standings']:
        value = standing_values.get(f['standing'], 0)
        blocks = value + 3
        bar = g("centered") * blocks + g("frayed") * (5 - blocks)
        color = standing_colors.get(value, Theme.NEUTRAL)
        log.write(Text.from_markup(
            f"  [{Theme.TEXT}]{f['name']:<16}[/{Theme.TEXT}] [{color}]{bar} {f['standing']}[/{color}]"
        ))


def tui_threads(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """View pending threads/consequences."""
    from .shared import get_dormant_threads
    threads = get_dormant_threads(app.manager)
    if threads is None:
        log.write(Text.from_markup(f"[{Theme.DIM}]No campaign loaded[/{Theme.DIM}]"))
        return
    if not threads:
        log.write(Text.from_markup(f"[{Theme.DIM}]No pending threads[/{Theme.DIM}]"))
    else:
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]Dormant Threads:[/bold {Theme.TEXT}]"))
        for t in threads:
            sev_color = Theme.DANGER if t['severity'] == "major" else Theme.WARNING if t['severity'] == "moderate" else Theme.DIM
            log.write(Text.from_markup(
                f"  [{sev_color}]{g('thread')}[/{sev_color}] {t['origin'][:40]}..."
            ))
            log.write(Text.from_markup(f"    [{Theme.DIM}]Trigger: {t['trigger_condition']}[/{Theme.DIM}]"))


# -----------------------------------------------------------------------------
# System Commands
# -----------------------------------------------------------------------------

def tui_clear(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Clear conversation history."""
    app.conversation.clear()
    log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Conversation cleared[/{Theme.FRIENDLY}]"))
    app.refresh_all_panels()


def tui_checkpoint(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Save and relieve memory pressure."""
    if app.manager and app.manager.current:
        app.manager.save()
        log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Campaign saved[/{Theme.FRIENDLY}]"))

    old_len = len(app.conversation)
    app.conversation.clear()

    if app.agent and hasattr(app.agent, '_conversation_window'):
        app.agent._conversation_window.blocks.clear()
        app.agent._last_pack_info = None

    log.write(Text.from_markup(
        f"[{Theme.FRIENDLY}]Memory checkpoint complete[/{Theme.FRIENDLY}]  "
        f"[{Theme.DIM}]({old_len} messages archived)[/{Theme.DIM}]"
    ))
    log.write(Text.from_markup(
        f"[{Theme.DIM}]Context pressure relieved. Campaign state preserved.[/{Theme.DIM}]"
    ))
    app.refresh_all_panels()


# -----------------------------------------------------------------------------
# Mission Commands
# -----------------------------------------------------------------------------

def tui_start(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Begin the story."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Load a campaign first[/{Theme.WARNING}]"))
        return
    app.handle_action("BEGIN_SESSION")


def tui_mission(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Get a new mission."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Load a campaign first[/{Theme.WARNING}]"))
        return
    app.handle_action("REQUEST_MISSION")


def tui_consult(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Ask the council for advice."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Load a campaign first[/{Theme.WARNING}]"))
        return
    query = " ".join(args) if args else "What should I consider?"
    app.handle_action(f"CONSULT: {query}")


def tui_debrief(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """End session."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Load a campaign first[/{Theme.WARNING}]"))
        return
    app.handle_action("END_SESSION_DEBRIEF")


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

def register_tui_handlers() -> None:
    """Register all TUI command handlers with the registry."""
    # Campaign
    set_tui_handler("/new", tui_new)
    set_tui_handler("/load", tui_load)
    set_tui_handler("/save", tui_save)
    set_tui_handler("/list", tui_list)
    set_tui_handler("/delete", tui_delete)

    # Character
    set_tui_handler("/char", tui_char)
    set_tui_handler("/roll", tui_roll)

    # Info
    set_tui_handler("/status", tui_status)
    set_tui_handler("/factions", tui_factions)
    set_tui_handler("/threads", tui_threads)
    set_tui_handler("/consequences", tui_threads)  # Alias

    # System
    set_tui_handler("/clear", tui_clear)
    set_tui_handler("/checkpoint", tui_checkpoint)

    # Mission
    set_tui_handler("/start", tui_start)
    set_tui_handler("/mission", tui_mission)
    set_tui_handler("/consult", tui_consult)
    set_tui_handler("/debrief", tui_debrief)
