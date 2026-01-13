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
# Help and System Commands
# -----------------------------------------------------------------------------

def tui_help(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Show help text."""
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
        f"  [{Theme.ACCENT}]/wiki[/{Theme.ACCENT}] [page] - Campaign wiki/timeline\n"
        f"  [{Theme.ACCENT}]/compare[/{Theme.ACCENT}] - Cross-campaign analysis\n"
        f"\n[bold {Theme.TEXT}]System:[/bold {Theme.TEXT}]\n"
        f"  [{Theme.ACCENT}]/backend[/{Theme.ACCENT}] [name] - Switch LLM backend\n"
        f"  [{Theme.ACCENT}]/model[/{Theme.ACCENT}] [name] - Switch model\n"
        f"  [{Theme.ACCENT}]/copy[/{Theme.ACCENT}] - Copy last output\n"
        f"  [{Theme.ACCENT}]/ping[/{Theme.ACCENT}] - Test backend/model\n"
        f"  [{Theme.ACCENT}]/checkpoint[/{Theme.ACCENT}] - Save & relieve memory pressure\n"
        f"  [{Theme.ACCENT}]/compress[/{Theme.ACCENT}] - Update campaign digest\n"
        f"  [{Theme.ACCENT}]/clear[/{Theme.ACCENT}] - Clear conversation\n"
        f"  [{Theme.ACCENT}]/context[/{Theme.ACCENT}] - Show context debug info\n"
        f"  [{Theme.ACCENT}]/quit[/{Theme.ACCENT}] - Exit\n"
        f"\n[bold {Theme.TEXT}]Hotkeys:[/bold {Theme.TEXT}]\n"
        f"  [{Theme.ACCENT}]F2[/{Theme.ACCENT}] - Toggle panels | [{Theme.ACCENT}]Ctrl+Q[/{Theme.ACCENT}] - Quit | [{Theme.ACCENT}]1-9[/{Theme.ACCENT}] - Select choice"
    ))


def tui_quit(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Exit the application."""
    app.exit()


def tui_copy(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Copy last output to clipboard."""
    app._copy_last_output(log)


def tui_dock(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Toggle dock visibility."""
    app.docks_visible = not app.docks_visible
    state = "shown" if app.docks_visible else "hidden"
    log.write(Text.from_markup(f"[{Theme.DIM}]Docks {state}[/{Theme.DIM}]"))


# -----------------------------------------------------------------------------
# Inventory Commands
# -----------------------------------------------------------------------------

def tui_gear(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """View inventory."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
        return

    char = app.manager.current.player
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


# -----------------------------------------------------------------------------
# Settings Commands
# -----------------------------------------------------------------------------

def tui_backend(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Switch LLM backend."""
    from .config import set_backend
    from ..agent import SentinelAgent

    if not args:
        info = app.agent.backend_info if app.agent else {"backend": "none", "available": False}
        log.write(Text.from_markup(f"[{Theme.TEXT}]Current: {info.get('backend', 'none')}[/{Theme.TEXT}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]Usage: /backend <lmstudio|ollama|claude>[/{Theme.DIM}]"))
    else:
        backend = args[0].lower()
        log.write(Text.from_markup(f"[{Theme.DIM}]Switching to {backend}...[/{Theme.DIM}]"))
        app.agent = SentinelAgent(
            app.manager,
            prompts_dir=app.prompts_dir,
            lore_dir=app.lore_dir if app.lore_dir and app.lore_dir.exists() else None,
            backend=backend,
        )
        info = app.agent.backend_info
        if info["available"]:
            set_backend(backend, campaigns_dir=getattr(app, "campaigns_dir", "campaigns"))
            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Now using: {info['backend']} ({info['model']})[/{Theme.FRIENDLY}]"))
        else:
            log.write(Text.from_markup(f"[{Theme.DANGER}]Backend not available[/{Theme.DANGER}]"))


def tui_model(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Switch model."""
    from .config import set_model as save_model

    if not app.agent or not app.agent.client:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No LLM backend active[/{Theme.WARNING}]"))
        return

    client = app.agent.client
    backend = app.agent.backend
    has_list = hasattr(client, 'list_models')
    has_set = hasattr(client, 'set_model')

    if not args:
        log.write(Text.from_markup(f"[{Theme.TEXT}]Current model:[/{Theme.TEXT}] [{Theme.ACCENT}]{client.model_name}[/{Theme.ACCENT}]"))
        if has_list:
            try:
                models = client.list_models()
                if models:
                    log.write(Text.from_markup(f"\n[bold {Theme.TEXT}]Available models:[/bold {Theme.TEXT}]"))
                    for i, model in enumerate(models, 1):
                        current = " ← current" if model == client.model_name else ""
                        log.write(Text.from_markup(f"  [{Theme.ACCENT}]{i}.[/{Theme.ACCENT}] {model}[{Theme.DIM}]{current}[/{Theme.DIM}]"))
                    log.write(Text.from_markup(f"\n[{Theme.DIM}]Usage: /model <name or number>[/{Theme.DIM}]"))
            except Exception as e:
                log.write(Text.from_markup(f"[{Theme.DIM}]Could not list models: {e}[/{Theme.DIM}]"))
    else:
        if not has_set:
            log.write(Text.from_markup(f"[{Theme.WARNING}]Model switching not supported for {backend}[/{Theme.WARNING}]"))
            return

        model_arg = args[0]
        if model_arg.isdigit() and has_list:
            try:
                models = client.list_models()
                idx = int(model_arg) - 1
                if 0 <= idx < len(models):
                    model_arg = models[idx]
            except Exception:
                pass

        log.write(Text.from_markup(f"[{Theme.DIM}]Switching to {model_arg}...[/{Theme.DIM}]"))
        try:
            client.set_model(model_arg)
            if backend in ("lmstudio", "ollama"):
                save_model(model_arg, campaigns_dir=getattr(app, "campaigns_dir", "campaigns"))
            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Now using: {client.model_name}[/{Theme.FRIENDLY}]"))
        except Exception as e:
            log.write(Text.from_markup(f"[{Theme.DANGER}]Failed to switch model: {e}[/{Theme.DANGER}]"))


def tui_context(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Show context debug info."""
    from ..context import StrainTier

    if not app.agent or not hasattr(app.agent, '_last_pack_info'):
        log.write(Text.from_markup(f"[{Theme.DIM}]No context info yet (send a message first)[/{Theme.DIM}]"))
        return

    pack_info = app.agent._last_pack_info
    if not pack_info:
        log.write(Text.from_markup(f"[{Theme.DIM}]No context info yet[/{Theme.DIM}]"))
        return

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
    log.write(Text.from_markup(f"[{Theme.DIM}]Total: {pack_info.total_tokens:,} / {pack_info.total_budget:,} tokens[/{Theme.DIM}]"))

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

    if pack_info.warnings:
        log.write(Text.from_markup(f"\n[bold {Theme.WARNING}]Warnings:[/bold {Theme.WARNING}]"))
        for warning in pack_info.warnings:
            log.write(Text.from_markup(f"  [{Theme.WARNING}]• {warning}[/{Theme.WARNING}]"))


# -----------------------------------------------------------------------------
# Lore and NPC Commands
# -----------------------------------------------------------------------------

def tui_lore(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Search lore."""
    if not app.agent or not app.agent.lore_retriever:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No lore directory configured[/{Theme.WARNING}]"))
        return

    retriever = app.agent.lore_retriever
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


def tui_npc(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """View NPCs."""
    from .shared import get_npc_list, get_npc_details

    if not args:
        data = get_npc_list(app.manager)
        if data is None:
            log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
            return

        if not data['active'] and not data['dormant']:
            log.write(Text.from_markup(f"[{Theme.DIM}]No NPCs in this campaign yet[/{Theme.DIM}]"))
            return

        log.write(Text.from_markup(f"[bold {Theme.TEXT}]NPCs[/bold {Theme.TEXT}]"))
        if data['active']:
            log.write(Text.from_markup(f"\n[{Theme.ACCENT}]ACTIVE[/{Theme.ACCENT}]"))
            for npc in data['active']:
                faction = npc['faction'] or "unknown"
                disp = npc['disposition']
                log.write(Text.from_markup(f"  • {npc['name']} [{Theme.DIM}]{faction}, {disp}[/{Theme.DIM}]"))
        if data['dormant']:
            log.write(Text.from_markup(f"\n[{Theme.DIM}]DORMANT[/{Theme.DIM}]"))
            for npc in data['dormant']:
                log.write(Text.from_markup(f"  [{Theme.DIM}]• {npc['name']}[/{Theme.DIM}]"))
    else:
        npc = get_npc_details(app.manager, args[0])
        if not npc:
            log.write(Text.from_markup(f"[{Theme.WARNING}]No NPC found matching '{args[0]}'[/{Theme.WARNING}]"))
            return

        log.write(Text.from_markup(f"\n[bold {Theme.ACCENT}]{npc['name']}[/bold {Theme.ACCENT}]"))
        if npc.get('faction'):
            log.write(Text.from_markup(f"  [{Theme.DIM}]Faction:[/{Theme.DIM}] {npc['faction']}"))
        if npc.get('role'):
            log.write(Text.from_markup(f"  [{Theme.DIM}]Role:[/{Theme.DIM}] {npc['role']}"))
        if npc.get('disposition'):
            log.write(Text.from_markup(f"  [{Theme.DIM}]Disposition:[/{Theme.DIM}] {npc['disposition']}"))
        if npc.get('wants'):
            log.write(Text.from_markup(f"  [{Theme.TEXT}]Wants:[/{Theme.TEXT}] {npc['wants']}"))
        if npc.get('fears'):
            log.write(Text.from_markup(f"  [{Theme.TEXT}]Fears:[/{Theme.TEXT}] {npc['fears']}"))


def tui_arc(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """View character arcs."""
    from .shared import get_character_arcs, detect_arcs, accept_arc, reject_arc

    if not args:
        data = get_character_arcs(app.manager)
        if data is None:
            log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign or character loaded[/{Theme.WARNING}]"))
            return

        log.write(Text.from_markup(f"[bold {Theme.TEXT}]Character Arcs[/bold {Theme.TEXT}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]{data['character_name']}'s emergent identity patterns[/{Theme.DIM}]"))

        if data['accepted']:
            log.write(Text.from_markup(f"\n[{Theme.ACCENT}]ACTIVE ARCS[/{Theme.ACCENT}]"))
            for arc in data['accepted']:
                strength_bar = "█" * min(5, arc['strength']) + "░" * (5 - min(5, arc['strength']))
                log.write(Text.from_markup(f"  ◆ [bold]{arc['title']}[/bold] ({arc['arc_type']})"))
                log.write(Text.from_markup(f"    [{Theme.DIM}]{arc['description']}[/{Theme.DIM}]"))
                log.write(Text.from_markup(f"    Strength: [{Theme.ACCENT}]{strength_bar}[/{Theme.ACCENT}]"))

        if data['suggested']:
            log.write(Text.from_markup(f"\n[{Theme.WARNING}]SUGGESTED ARCS[/{Theme.WARNING}]"))
            for arc in data['suggested']:
                log.write(Text.from_markup(f"  ? [bold]{arc['title']}[/bold] ({arc['arc_type']})"))
                log.write(Text.from_markup(f"    [{Theme.DIM}]{arc['description']}[/{Theme.DIM}]"))
                log.write(Text.from_markup(f"    [{Theme.DIM}]/arc accept {arc['arc_type']} | /arc reject {arc['arc_type']}[/{Theme.DIM}]"))

        if not data['accepted'] and not data['suggested']:
            log.write(Text.from_markup(f"\n[{Theme.DIM}]No arcs detected yet. Play more to develop patterns.[/{Theme.DIM}]"))
    elif args[0].lower() == "detect":
        candidates = detect_arcs(app.manager)
        if candidates:
            log.write(Text.from_markup(f"[bold {Theme.TEXT}]Detected Patterns[/bold {Theme.TEXT}]"))
            for c in candidates:
                log.write(Text.from_markup(f"  ◆ {c['title']} ({c['arc_type']})"))
        else:
            log.write(Text.from_markup(f"[{Theme.DIM}]No strong patterns detected yet[/{Theme.DIM}]"))
    elif args[0].lower() == "accept" and len(args) > 1:
        result = accept_arc(app.manager, args[1])
        if result.success:
            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]{result.message}[/{Theme.FRIENDLY}]"))
        else:
            log.write(Text.from_markup(f"[{Theme.WARNING}]{result.message}[/{Theme.WARNING}]"))
    elif args[0].lower() == "reject" and len(args) > 1:
        result = reject_arc(app.manager, args[1])
        if result.success:
            log.write(Text.from_markup(f"[{Theme.DIM}]{result.message}[/{Theme.DIM}]"))
        else:
            log.write(Text.from_markup(f"[{Theme.WARNING}]{result.message}[/{Theme.WARNING}]"))
    else:
        log.write(Text.from_markup(f"[{Theme.DIM}]Usage: /arc | /arc detect | /arc accept <type> | /arc reject <type>[/{Theme.DIM}]"))


# -----------------------------------------------------------------------------
# History Commands
# -----------------------------------------------------------------------------

def tui_history(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """View campaign chronicle."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.DIM}]No campaign loaded[/{Theme.DIM}]"))
        return

    history = list(app.manager.current.history)
    if not history:
        log.write(Text.from_markup(f"[{Theme.DIM}]No chronicle entries yet[/{Theme.DIM}]"))
        return

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

    filtered = history
    if filter_type:
        filtered = [h for h in history if h.type.value == filter_type]
    if session_filter:
        filtered = [h for h in history if h.session == session_filter]
    if search_term:
        filtered = [h for h in history if search_term in h.summary.lower()]

    log.write(Text.from_markup(f"[bold {Theme.TEXT}]Campaign Chronicle[/bold {Theme.TEXT}]"))
    if not filtered:
        log.write(Text.from_markup(f"[{Theme.DIM}]No matching entries[/{Theme.DIM}]"))
    else:
        for entry in filtered[-15:]:
            etype = entry.type.value
            if etype == "hinge":
                icon = f"[{Theme.DANGER}]{g('hinge')}[/{Theme.DANGER}]"
            elif etype == "faction_shift":
                icon = f"[{Theme.WARNING}]{g('triggered')}[/{Theme.WARNING}]"
            else:
                icon = f"[{Theme.DIM}]•[/{Theme.DIM}]"
            log.write(Text.from_markup(f"  {icon} S{entry.session}: {entry.summary[:60]}..."))


def tui_search(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Search campaign history."""
    if not args:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /search <term>[/{Theme.WARNING}]"))
        return
    tui_history(app, log, ["search"] + args)


def tui_summary(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """View session summary."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
        return

    session_num = app.manager.current.meta.session_count
    if args and args[0].isdigit():
        session_num = int(args[0])

    summary_data = app.manager.generate_session_summary(session_num)
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


def tui_timeline(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Search campaign memory (memvid)."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
        return

    from ..state import MEMVID_AVAILABLE
    if not MEMVID_AVAILABLE:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Memvid not installed. Run: pip install memvid-sdk[/{Theme.WARNING}]"))
        return

    if not app.manager.memvid or not app.manager.memvid.is_enabled:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Memvid not enabled for this campaign[/{Theme.WARNING}]"))
        return

    memvid = app.manager.memvid

    if not args:
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]Campaign Timeline[/bold {Theme.TEXT}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]Sessions: {app.manager.current.meta.session_count}[/{Theme.DIM}]"))

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


# -----------------------------------------------------------------------------
# Wiki Commands
# -----------------------------------------------------------------------------

def tui_wiki(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """View campaign wiki."""
    from .shared import get_wiki_timeline, get_wiki_page_overlay
    from .glyphs import sanitize_for_terminal

    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
        return

    wiki_dir = getattr(app.manager, '_wiki_dir', 'wiki')

    if not args:
        result = get_wiki_timeline(app.manager, wiki_dir=str(wiki_dir))
        if not result:
            log.write(Text.from_markup(f"[{Theme.WARNING}]Could not load wiki timeline[/{Theme.WARNING}]"))
            return

        log.write(Text.from_markup(f"[bold {Theme.TEXT}]Campaign Wiki[/bold {Theme.TEXT}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]{result['campaign_name']}[/{Theme.DIM}]"))

        if not result['events']:
            log.write(Text.from_markup(f"\n[{Theme.DIM}]{result.get('message', 'No events recorded yet.')}[/{Theme.DIM}]"))
            log.write(Text.from_markup(f"[{Theme.DIM}]Events are auto-logged during play.[/{Theme.DIM}]"))
            return

        log.write(Text.from_markup(f"\n[{Theme.ACCENT}]Timeline ({result['event_count']} events)[/{Theme.ACCENT}]"))

        for event in result['events'][-15:]:
            if "[HINGE]" in event:
                color = Theme.DANGER
                icon = g('hinge')
            elif "[FACTION]" in event:
                color = Theme.ACCENT
                icon = g('faction')
            elif "[THREAD]" in event:
                color = Theme.WARNING
                icon = g('thread')
            elif "[MISSION]" in event:
                color = Theme.TEXT
                icon = g('mission')
            else:
                color = Theme.DIM
                icon = g('bullet')

            event_text = sanitize_for_terminal(event)
            log.write(Text.from_markup(f"  [{color}]{icon}[/{color}] {event_text}"))

        log.write(Text.from_markup(f"\n[{Theme.DIM}]/wiki <page> for specific page overlay[/{Theme.DIM}]"))
    else:
        page = " ".join(args)
        result = get_wiki_page_overlay(app.manager, page, wiki_dir=str(wiki_dir))

        if not result or not result['exists']:
            log.write(Text.from_markup(f"[{Theme.DIM}]No campaign overlay for '{page}'[/{Theme.DIM}]"))
            return

        log.write(Text.from_markup(f"[bold {Theme.TEXT}]Wiki Overlay: {page}[/bold {Theme.TEXT}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]Campaign-specific additions[/{Theme.DIM}]\n"))

        content = sanitize_for_terminal(result['content'])
        lines = content.split('\n')
        for line in lines[:30]:
            log.write(Text.from_markup(f"  {line}"))


def tui_compress(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Update campaign digest."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
        return

    from pathlib import Path
    from ..context import DigestManager

    campaign = app.manager.current
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
    digest_manager.save(campaign.meta.id, digest)
    log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Digest updated[/{Theme.FRIENDLY}]"))

    if digest.hinge_index:
        log.write(Text.from_markup(f"  [{Theme.ACCENT}]{len(digest.hinge_index)}[/{Theme.ACCENT}] hinge moments"))
    if digest.standing_reasons:
        log.write(Text.from_markup(f"  [{Theme.ACCENT}]{len(digest.standing_reasons)}[/{Theme.ACCENT}] faction standings"))
    if digest.npc_anchors:
        log.write(Text.from_markup(f"  [{Theme.ACCENT}]{len(digest.npc_anchors)}[/{Theme.ACCENT}] NPC memories"))


def tui_simulate(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Explore hypotheticals."""
    if not args:
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]Simulation Modes[/bold {Theme.TEXT}]"))
        log.write(Text.from_markup(f"\n[{Theme.ACCENT}]/simulate preview <action>[/{Theme.ACCENT}]"))
        log.write(Text.from_markup(f"  [{Theme.DIM}]Preview consequences without committing[/{Theme.DIM}]"))
        log.write(Text.from_markup(f"\n[{Theme.ACCENT}]/simulate npc <name> <approach>[/{Theme.ACCENT}]"))
        log.write(Text.from_markup(f"  [{Theme.DIM}]Predict NPC reaction[/{Theme.DIM}]"))
        log.write(Text.from_markup(f"\n[{Theme.ACCENT}]/simulate whatif <query>[/{Theme.ACCENT}]"))
        log.write(Text.from_markup(f"  [{Theme.DIM}]Explore how past choices might have gone differently[/{Theme.DIM}]"))
        return

    subcommand = args[0].lower()
    sub_args = args[1:]

    if subcommand == "preview":
        if not sub_args:
            log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /simulate preview <action>[/{Theme.WARNING}]"))
            return
        app._simulate_preview(sub_args)
    elif subcommand == "npc":
        if len(sub_args) < 2:
            log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /simulate npc <name> <approach>[/{Theme.WARNING}]"))
            return
        app._simulate_npc(sub_args)
    elif subcommand == "whatif":
        if not sub_args:
            log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /simulate whatif <query>[/{Theme.WARNING}]"))
            return
        app._simulate_whatif(sub_args)
    else:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Unknown simulate subcommand: {subcommand}[/{Theme.WARNING}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]Use: preview, npc, or whatif[/{Theme.DIM}]"))


def tui_loadout(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Manage mission gear."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
        return

    if not app.manager.current.characters:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Create a character first[/{Theme.WARNING}]"))
        return

    char = app.manager.current.characters[0]
    session = app.manager.current.session

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
            app.manager.save()
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
            app.manager.save()
            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Removed {item.name}[/{Theme.FRIENDLY}]"))
        else:
            log.write(Text.from_markup(f"[{Theme.WARNING}]Item not in loadout: {item_query}[/{Theme.WARNING}]"))
    elif subcommand == "clear":
        count = len(session.loadout)
        session.loadout.clear()
        app.manager.save()
        log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Cleared {count} items[/{Theme.FRIENDLY}]"))
    else:
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
    set_tui_handler("/gear", tui_gear)
    set_tui_handler("/loadout", tui_loadout)
    set_tui_handler("/arc", tui_arc)

    # Info
    set_tui_handler("/status", tui_status)
    set_tui_handler("/factions", tui_factions)
    set_tui_handler("/threads", tui_threads)
    set_tui_handler("/consequences", tui_threads)  # Alias
    set_tui_handler("/npc", tui_npc)
    set_tui_handler("/lore", tui_lore)

    # History
    set_tui_handler("/history", tui_history)
    set_tui_handler("/search", tui_search)
    set_tui_handler("/summary", tui_summary)
    set_tui_handler("/timeline", tui_timeline)

    # Wiki
    set_tui_handler("/wiki", tui_wiki)
    set_tui_handler("/compress", tui_compress)

    # Simulation
    set_tui_handler("/simulate", tui_simulate)

    # System
    set_tui_handler("/clear", tui_clear)
    set_tui_handler("/checkpoint", tui_checkpoint)
    set_tui_handler("/help", tui_help)
    set_tui_handler("/quit", tui_quit)
    set_tui_handler("/exit", tui_quit)  # Alias
    set_tui_handler("/copy", tui_copy)
    set_tui_handler("/dock", tui_dock)

    # Settings
    set_tui_handler("/backend", tui_backend)
    set_tui_handler("/model", tui_model)
    set_tui_handler("/context", tui_context)

    # Mission
    set_tui_handler("/start", tui_start)
    set_tui_handler("/mission", tui_mission)
    set_tui_handler("/consult", tui_consult)
    set_tui_handler("/debrief", tui_debrief)
