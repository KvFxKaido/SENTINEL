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

    if not app.manager.current.characters:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No character loaded[/{Theme.WARNING}]"))
        return

    char = app.manager.current.characters[0]
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
                # Convert 0.0-1.0 strength to 0-5 bars
                strength_int = min(5, int(arc['strength'] * 5))
                strength_bar = "█" * strength_int + "░" * (5 - strength_int)
                log.write(Text.from_markup(f"  ◆ [bold]{arc['title']}[/bold] ({arc['arc_type']})"))
                log.write(Text.from_markup(f"    [{Theme.DIM}]{arc['description']}[/{Theme.DIM}]"))
                log.write(Text.from_markup(f"    Strength: [{Theme.ACCENT}]{strength_bar}[/{Theme.ACCENT}]"))

        if data['suggested']:
            log.write(Text.from_markup(f"\n[{Theme.WARNING}]SUGGESTED ARCS[/{Theme.WARNING}]"))
            for arc in data['suggested']:
                log.write(Text.from_markup(f"  ? [bold]{arc['title']}[/bold] ({arc['arc_type']})"))
                log.write(Text.from_markup(f"    [{Theme.DIM}]{arc['description']}[/{Theme.DIM}]"))
                log.write(Text.from_markup(f"    [{Theme.DIM}]/arc accept {arc['arc_type']} | /arc reject {arc['arc_type']}[/{Theme.DIM}]"))

        # Auto-detect new arcs if none saved yet
        if not data['accepted'] and not data['suggested']:
            # Run detection to find patterns
            candidates = detect_arcs(app.manager)
            if candidates:
                log.write(Text.from_markup(f"\n[{Theme.WARNING}]DETECTED PATTERNS[/{Theme.WARNING}]"))
                for c in candidates:
                    strength_pct = int(c['strength'] * 100)
                    log.write(Text.from_markup(f"  ? [bold]{c['title']}[/bold] ({c['arc_type']}, {strength_pct}%)"))
                    log.write(Text.from_markup(f"    [{Theme.DIM}]{c.get('description', '')}[/{Theme.DIM}]"))
                    log.write(Text.from_markup(f"    [{Theme.DIM}]/arc accept {c['arc_type']} | /arc reject {c['arc_type']}[/{Theme.DIM}]"))
            else:
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
# Ping Command (async dispatch)
# -----------------------------------------------------------------------------

def tui_ping(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Test backend connectivity (async dispatch)."""
    import asyncio
    # Schedule the async ping method - handle_command is async so this works
    asyncio.create_task(app._ping_backend(log))


# -----------------------------------------------------------------------------
# Shop Command
# -----------------------------------------------------------------------------

# Shop inventory (mirrored from tui.py)
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
    "Vehicles": [
        ("Salvage Bike", 400, "Motorcycle. Fast, road-only, solo rider."),
        ("Rust Runner", 600, "Off-road buggy. All-terrain, 2 passengers."),
        ("Drifter's Wagon", 800, "Covered truck. Cargo capacity, slow but reliable."),
        ("Ghost Skiff", 1200, "Small boat. Water travel, stealth-capable."),
        ("Caravan Share", 200, "Wanderer caravan token. 3 uses, slow but safe."),
    ],
}

# Vehicle data for purchases (name -> attributes)
# Properties: type, terrain[], capacity, cargo, stealth, unlocks_tags[]
VEHICLE_DATA = {
    "Salvage Bike": {
        "type": "motorcycle",
        "terrain": ["road"],
        "capacity": 1,
        "cargo": False,
        "stealth": False,
        "unlocks_tags": ["delivery", "courier"],
    },
    "Rust Runner": {
        "type": "buggy",
        "terrain": ["road", "off-road"],
        "capacity": 2,
        "cargo": False,
        "stealth": False,
        "unlocks_tags": ["extraction", "patrol"],
    },
    "Drifter's Wagon": {
        "type": "truck",
        "terrain": ["road"],
        "capacity": 4,
        "cargo": True,
        "stealth": False,
        "unlocks_tags": ["cargo", "smuggling", "convoy"],
    },
    "Ghost Skiff": {
        "type": "boat",
        "terrain": ["water"],
        "capacity": 3,
        "cargo": False,
        "stealth": True,
        "unlocks_tags": ["extraction", "infiltration", "water"],
    },
    "Caravan Share": {
        "type": "caravan_token",
        "terrain": ["road", "off-road"],
        "capacity": 6,
        "cargo": True,
        "stealth": False,
        "unlocks_tags": ["trade"],
    },
}


def tui_shop(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Buy equipment (downtime only)."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
        return

    if not app.manager.current.characters:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No character loaded[/{Theme.WARNING}]"))
        return

    # Check location - shop only available at safe_house, market, or faction_hq
    from ..state.schema import Location
    loc = app.manager.current.location
    valid_locations = {Location.SAFE_HOUSE, Location.MARKET, Location.FACTION_HQ}

    if loc not in valid_locations:
        loc_display = loc.value.replace("_", " ").title()
        log.write(Text.from_markup(f"[{Theme.DANGER}]Can't shop here ({loc_display})[/{Theme.DANGER}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]Travel to safe_house, market, or faction_hq first[/{Theme.DIM}]"))
        return

    char = app.manager.current.characters[0]
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

        # Handle vehicle purchases differently
        if category == "Vehicles":
            # Check if already owned
            if any(v.name.lower() == name.lower() for v in char.vehicles):
                log.write(Text.from_markup(f"[{Theme.WARNING}]Already own: {name}[/{Theme.WARNING}]"))
                return

            # Create vehicle from data
            from ..state.schema import Vehicle
            vehicle_attrs = VEHICLE_DATA.get(name, {})
            new_vehicle = Vehicle(
                name=name,
                type=vehicle_attrs.get("type", "vehicle"),
                description=desc,
                cost=price,
                terrain=vehicle_attrs.get("terrain", []),
                capacity=vehicle_attrs.get("capacity", 1),
                cargo=vehicle_attrs.get("cargo", False),
                stealth=vehicle_attrs.get("stealth", False),
                unlocks_tags=vehicle_attrs.get("unlocks_tags", []),
            )
            char.vehicles.append(new_vehicle)
            char.credits -= price

            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Purchased: {name}[/{Theme.FRIENDLY}]"))
            log.write(Text.from_markup(f"[{Theme.DIM}]{desc}[/{Theme.DIM}]"))
            log.write(Text.from_markup(f"[{Theme.DIM}]Remaining credits: {char.credits}[/{Theme.DIM}]"))
            app.refresh_all_panels()
            return

        # Check if gear already owned
        if any(g_item.name.lower() == name.lower() for g_item in char.gear):
            log.write(Text.from_markup(f"[{Theme.WARNING}]Already own: {name}[/{Theme.WARNING}]"))
            return

        # Purchase gear
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
        app.refresh_all_panels()
        return

    log.write(Text.from_markup(f"[{Theme.DIM}]Usage: /shop or /shop buy <item name>[/{Theme.DIM}]"))


# -----------------------------------------------------------------------------
# Jobs Command
# -----------------------------------------------------------------------------

def _check_job_requirements(template, char, campaign) -> tuple[bool, list[str]]:
    """Check if player meets job requirements. Returns (eligible, missing_requirements)."""
    missing = []

    # Check vehicle requirements
    if template.requires_vehicle:
        if not char.vehicles:
            missing.append("vehicle required")
        elif template.requires_vehicle_type:
            has_type = any(v.type == template.requires_vehicle_type for v in char.vehicles)
            if not has_type:
                missing.append(f"{template.requires_vehicle_type} required")
        elif template.requires_vehicle_tags:
            player_tags = set()
            for v in char.vehicles:
                player_tags.update(v.unlocks_tags)
            missing_tags = set(template.requires_vehicle_tags) - player_tags
            if missing_tags:
                missing.append(f"vehicle with: {', '.join(missing_tags)}")

    return len(missing) == 0, missing


def tui_jobs(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """View and manage available jobs."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
        return

    from ..state.schema import Location

    campaign = app.manager.current
    location = campaign.location
    faction_hq = campaign.location_faction
    char = campaign.characters[0] if campaign.characters else None

    # Subcommand handling
    if args:
        subcmd = args[0].lower()

        if subcmd == "accept":
            if len(args) < 2:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /jobs accept <number>[/{Theme.WARNING}]"))
                return
            try:
                idx = int(args[1]) - 1
                available = campaign.jobs.available
                if idx < 0 or idx >= len(available):
                    log.write(Text.from_markup(f"[{Theme.WARNING}]Invalid job number[/{Theme.WARNING}]"))
                    return
                template_id = available[idx]

                # Check requirements before accepting
                template = app.manager.jobs.get_template(template_id)
                if template and char:
                    eligible, missing = _check_job_requirements(template, char, campaign)
                    if not eligible:
                        log.write(Text.from_markup(f"[{Theme.DANGER}]Cannot accept job: {', '.join(missing)}[/{Theme.DANGER}]"))
                        log.write(Text.from_markup(f"[{Theme.DIM}]Purchase required equipment or call in a favor[/{Theme.DIM}]"))
                        return

                    # Check buy-in affordability
                    if template.buy_in:
                        can_afford, buy_in, credits = app.manager.jobs.can_afford_buy_in(template_id)
                        if not can_afford:
                            log.write(Text.from_markup(f"[{Theme.DANGER}]Insufficient credits for buy-in[/{Theme.DANGER}]"))
                            log.write(Text.from_markup(f"[{Theme.DIM}]Need: {buy_in}c | Have: {credits}c[/{Theme.DIM}]"))
                            return

                job = app.manager.jobs.accept_job(template_id)
                if job:
                    # Show buy-in deduction if applicable
                    if job.buy_in:
                        log.write(Text.from_markup(f"[{Theme.WARNING}]Buy-in paid: -{job.buy_in}c (non-refundable)[/{Theme.WARNING}]"))

                    log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Job accepted: {job.title}[/{Theme.FRIENDLY}]"))
                    log.write(Text.from_markup(f"[{Theme.DIM}]Objectives:[/{Theme.DIM}]"))
                    for obj in job.objectives:
                        log.write(Text.from_markup(f"  [{Theme.TEXT}]{obj}[/{Theme.TEXT}]"))
                    if job.due_session:
                        log.write(Text.from_markup(f"[{Theme.WARNING}]Due by session {job.due_session}[/{Theme.WARNING}]"))
                    # Trigger LLM briefing
                    template = app.manager.jobs.get_template(template_id)
                    if template:
                        prompt = (
                            f"I've accepted a job: '{job.title}' from {job.faction.value}. "
                            f"Description: {template.description}. "
                            f"Generate a brief, atmospheric briefing. 2-3 paragraphs max."
                        )
                        app.handle_action(f"GM_PROMPT: {prompt}")
                    app.refresh_all_panels()
                else:
                    log.write(Text.from_markup(f"[{Theme.DANGER}]Failed to accept job[/{Theme.DANGER}]"))
                return
            except ValueError:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /jobs accept <number>[/{Theme.WARNING}]"))
                return

        elif subcmd == "status":
            active = app.manager.jobs.get_active_jobs()
            if not active:
                log.write(Text.from_markup(f"[{Theme.DIM}]No active jobs[/{Theme.DIM}]"))
                return

            log.write(Text.from_markup(f"[bold {Theme.TEXT}]ACTIVE JOBS[/bold {Theme.TEXT}]"))
            current_session = campaign.meta.session_count
            for i, job in enumerate(active, 1):
                status_color = Theme.ACCENT
                deadline_str = ""
                if job.due_session:
                    sessions_left = job.due_session - current_session
                    if sessions_left <= 0:
                        status_color = Theme.DANGER
                        deadline_str = " [OVERDUE]"
                    elif sessions_left == 1:
                        status_color = Theme.WARNING
                        deadline_str = " [Due next session]"
                    else:
                        deadline_str = f" [Due in {sessions_left} sessions]"

                log.write(Text.from_markup(f"[{status_color}]{i}. {job.title}[/{status_color}] ({job.faction.value}){deadline_str}"))
                log.write(Text.from_markup(f"   [{Theme.DIM}]Reward: {job.reward_credits}c[/{Theme.DIM}]"))
            return

        elif subcmd == "abandon":
            if len(args) < 2:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /jobs abandon <number>[/{Theme.WARNING}]"))
                return
            try:
                idx = int(args[1]) - 1
                active = app.manager.jobs.get_active_jobs()
                if idx < 0 or idx >= len(active):
                    log.write(Text.from_markup(f"[{Theme.WARNING}]Invalid job number[/{Theme.WARNING}]"))
                    return
                job = active[idx]
                result = app.manager.jobs.abandon_job(job.id)
                if "error" not in result:
                    log.write(Text.from_markup(f"[{Theme.WARNING}]Abandoned: {result['title']}[/{Theme.WARNING}]"))
                    log.write(Text.from_markup(f"[{Theme.DIM}]Standing with {result['faction']}: {result['standing_penalty']}[/{Theme.DIM}]"))
                    app.refresh_all_panels()
                else:
                    log.write(Text.from_markup(f"[{Theme.DANGER}]{result['error']}[/{Theme.DANGER}]"))
                return
            except ValueError:
                log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /jobs abandon <number>[/{Theme.WARNING}]"))
                return

        elif subcmd == "refresh":
            available = app.manager.jobs.refresh_board()
            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Job board refreshed: {len(available)} jobs available[/{Theme.FRIENDLY}]"))
            return

    # Default: show job board
    available = campaign.jobs.available
    if not available:
        available = app.manager.jobs.refresh_board()

    # Location-aware formatting
    if location in {Location.FIELD, Location.TRANSIT}:
        # Text message style
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]INCOMING MESSAGES[/bold {Theme.TEXT}]"))
        signal = "weak" if location == Location.TRANSIT else "moderate"
        log.write(Text.from_markup(f"[{Theme.DIM}]Signal: {signal}[/{Theme.DIM}]\n"))

        for i, template_id in enumerate(available, 1):
            template = app.manager.jobs.get_template(template_id)
            if not template:
                continue
            faction_short = template.faction.value.split()[0].upper()
            log.write(Text.from_markup(f"[{Theme.ACCENT}][{faction_short}][/{Theme.ACCENT}]"))
            log.write(Text.from_markup(f'  "{template.description}"'))
            log.write(Text.from_markup(f"  [{Theme.DIM}]{template.reward_credits}c | /jobs accept {i}[/{Theme.DIM}]\n"))
    else:
        # Terminal job board style
        title = "JOB TERMINAL"
        if location == Location.FACTION_HQ and faction_hq:
            title = f"{faction_hq.value.upper()} CONTRACTS"
        elif location == Location.MARKET:
            title = "WANDERER MARKET - JOBS"

        log.write(Text.from_markup(f"[bold {Theme.TEXT}]{title}[/bold {Theme.TEXT}]"))

        if not available:
            log.write(Text.from_markup(f"[{Theme.DIM}]No jobs available. Try /jobs refresh.[/{Theme.DIM}]"))
        else:
            import json
            from pathlib import Path

            # Load regions data for display names
            regions_file = Path(__file__).parent.parent.parent / "data" / "regions.json"
            regions_data = {}
            if regions_file.exists():
                with open(regions_file, "r", encoding="utf-8") as f:
                    regions_data = json.load(f).get("regions", {})

            for i, template_id in enumerate(available, 1):
                template = app.manager.jobs.get_template(template_id)
                if not template:
                    continue

                faction_tag = template.faction.value[:3].upper()

                # Check eligibility
                eligible = True
                missing = []
                if char:
                    eligible, missing = _check_job_requirements(template, char, campaign)

                risk_str = ""
                if template.opposing_factions:
                    risk_parts = [f.value.split()[0] for f in template.opposing_factions[:2]]
                    risk_str = f" | Risk: {', '.join(risk_parts)} -{template.opposing_penalty}"

                # Buy-in tag if applicable
                buy_in_tag = ""
                if template.buy_in:
                    buy_in_tag = f" [bold {Theme.WARNING}][BUY-IN: {template.buy_in}c][/bold {Theme.WARNING}]"

                # Title styling based on eligibility
                if eligible:
                    log.write(Text.from_markup(f"\n[{Theme.ACCENT}]{i}. [{faction_tag}] {template.title}[/{Theme.ACCENT}]{buy_in_tag}"))
                else:
                    log.write(Text.from_markup(f"\n[{Theme.DIM}]{i}. [{faction_tag}] {template.title} [LOCKED][/{Theme.DIM}]{buy_in_tag}"))

                log.write(Text.from_markup(f"   {template.description}"))
                log.write(Text.from_markup(f"   [{Theme.DIM}]Pay: {template.reward_credits}c | Est: {template.time_estimate}{risk_str}[/{Theme.DIM}]"))

                # Show region requirement
                if template.region:
                    region_info = regions_data.get(template.region.value, {})
                    region_name = region_info.get("name", template.region.value.replace("_", " ").title())
                    current_region = campaign.region
                    if template.region == current_region:
                        log.write(Text.from_markup(f"   [{Theme.FRIENDLY}]📍 {region_name} (current)[/{Theme.FRIENDLY}]"))
                    else:
                        log.write(Text.from_markup(f"   [{Theme.DIM}]📍 {region_name}[/{Theme.DIM}]"))

                # Show vehicle requirements
                if template.requires_vehicle:
                    if template.requires_vehicle_type:
                        req = f"Requires: {template.requires_vehicle_type}"
                    elif template.requires_vehicle_tags:
                        req = f"Requires: {', '.join(template.requires_vehicle_tags)}"
                    else:
                        req = "Requires: any vehicle"
                    style = Theme.DANGER if not eligible else Theme.DIM
                    log.write(Text.from_markup(f"   [{style}]🚗 {req}[/{style}]"))

        log.write(Text.from_markup(f"\n[{Theme.DIM}]Usage: /jobs accept <n> | /jobs status | /jobs refresh[/{Theme.DIM}]"))


# -----------------------------------------------------------------------------
# Travel Command
# -----------------------------------------------------------------------------

def tui_travel(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Travel to a new location."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
        return

    from ..state.schema import Location

    # Get current location
    campaign = app.manager.current
    current_loc = campaign.location
    current_display = current_loc.value.replace("_", " ").title()

    if not args:
        # Show available destinations
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]TRAVEL[/bold {Theme.TEXT}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]Current location: {current_display}[/{Theme.DIM}]\n"))
        log.write(Text.from_markup(f"[{Theme.ACCENT}]Destinations:[/{Theme.ACCENT}]"))

        for loc in Location:
            marker = "→ " if loc == current_loc else "  "
            desc = {
                Location.SAFE_HOUSE: "Your base — full access to gear, rest",
                Location.FIELD: "Mission zone — tactical mode",
                Location.FACTION_HQ: "Faction headquarters — requires faction name",
                Location.MARKET: "Wanderer market — general goods",
                Location.TRANSIT: "Traveling between locations",
            }.get(loc, "")
            style = Theme.FRIENDLY if loc == current_loc else Theme.TEXT
            log.write(Text.from_markup(f"{marker}[{style}]{loc.value}[/{style}] [{Theme.DIM}]— {desc}[/{Theme.DIM}]"))

        log.write(Text.from_markup(f"\n[{Theme.DIM}]Usage: /travel <destination> [faction][/{Theme.DIM}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]Example: /travel faction_hq nexus[/{Theme.DIM}]"))
        return

    # Parse destination
    destination = args[0].lower()
    faction = args[1] if len(args) > 1 else None

    # Call manager.travel()
    try:
        result = app.manager.travel(destination, faction)

        if "error" in result:
            log.write(Text.from_markup(f"[{Theme.DANGER}]{result['error']}[/{Theme.DANGER}]"))
        else:
            new_loc = result.get("new_location", destination).replace("_", " ").title()
            log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Traveled to {new_loc}[/{Theme.FRIENDLY}]"))

            if result.get("faction"):
                log.write(Text.from_markup(f"[{Theme.DIM}]At {result['faction'].title()} headquarters[/{Theme.DIM}]"))

            if result.get("narrative_hint"):
                log.write(Text.from_markup(f"[{Theme.DIM}]{result['narrative_hint']}[/{Theme.DIM}]"))

            app.refresh_all_panels()
    except Exception as e:
        log.write(Text.from_markup(f"[{Theme.DANGER}]Travel failed: {e}[/{Theme.DANGER}]"))


# -----------------------------------------------------------------------------
# Region Command
# -----------------------------------------------------------------------------

def tui_region(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """View or change current world region."""
    import json
    from pathlib import Path

    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
        return

    from ..state.schema import Region

    campaign = app.manager.current
    current_region = campaign.region

    # Load regions data
    regions_file = Path(__file__).parent.parent.parent / "data" / "regions.json"
    regions_data = {}
    if regions_file.exists():
        with open(regions_file, "r", encoding="utf-8") as f:
            regions_data = json.load(f).get("regions", {})

    # Get current region info
    current_info = regions_data.get(current_region.value, {})

    if not args:
        # Show current region
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]CURRENT REGION[/bold {Theme.TEXT}]"))
        log.write(Text.from_markup(f"[{Theme.ACCENT}]{current_info.get('name', current_region.value)}[/{Theme.ACCENT}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]{current_info.get('description', '')}[/{Theme.DIM}]"))

        if current_info.get("character"):
            log.write(Text.from_markup(f"\n[{Theme.TEXT}]{current_info['character']}[/{Theme.TEXT}]"))

        # Faction influence
        primary = current_info.get("primary_faction", "")
        contested = current_info.get("contested_by", [])
        if primary:
            log.write(Text.from_markup(f"\n[{Theme.ACCENT}]Primary:[/{Theme.ACCENT}] {primary.replace('_', ' ').title()}"))
        if contested:
            contested_str = ", ".join(c.replace("_", " ").title() for c in contested)
            log.write(Text.from_markup(f"[{Theme.DIM}]Contested by:[/{Theme.DIM}] {contested_str}"))

        # Adjacent regions
        adjacent = current_info.get("adjacent", [])
        if adjacent:
            log.write(Text.from_markup(f"\n[{Theme.ACCENT}]Adjacent Regions:[/{Theme.ACCENT}]"))
            for adj in adjacent:
                adj_info = regions_data.get(adj, {})
                name = adj_info.get("name", adj.replace("_", " ").title())
                log.write(Text.from_markup(f"  [{Theme.DIM}]• {name}[/{Theme.DIM}]"))

        log.write(Text.from_markup(f"\n[{Theme.DIM}]/region list — all regions | /region <name> — travel[/{Theme.DIM}]"))
        return

    subcmd = args[0].lower()

    if subcmd == "list":
        # List all regions
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]WORLD REGIONS[/bold {Theme.TEXT}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]Post-Collapse North America[/{Theme.DIM}]\n"))

        for region in Region:
            info = regions_data.get(region.value, {})
            name = info.get("name", region.value.replace("_", " ").title())
            primary = info.get("primary_faction", "").replace("_", " ").title()

            marker = "→ " if region == current_region else "  "
            style = Theme.FRIENDLY if region == current_region else Theme.TEXT
            log.write(Text.from_markup(f"{marker}[{style}]{name}[/{style}] [{Theme.DIM}]— {primary}[/{Theme.DIM}]"))
        return

    # Travel to a region
    target_name = " ".join(args).lower().replace(" ", "_")

    # Find matching region
    target_region = None
    for region in Region:
        if target_name in region.value:
            target_region = region
            break
        # Also check by display name
        info = regions_data.get(region.value, {})
        if target_name in info.get("name", "").lower().replace(" ", "_"):
            target_region = region
            break

    if not target_region:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Unknown region: {' '.join(args)}[/{Theme.WARNING}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]Use /region list to see all regions[/{Theme.DIM}]"))
        return

    if target_region == current_region:
        log.write(Text.from_markup(f"[{Theme.DIM}]Already in {current_info.get('name', current_region.value)}[/{Theme.DIM}]"))
        return

    # Check adjacency
    adjacent = current_info.get("adjacent", [])
    target_info = regions_data.get(target_region.value, {})

    # Update region
    campaign.region = target_region
    app.manager.save_campaign()

    log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Traveled to {target_info.get('name', target_region.value)}[/{Theme.FRIENDLY}]"))
    log.write(Text.from_markup(f"[{Theme.DIM}]{target_info.get('description', '')}[/{Theme.DIM}]"))

    if target_region.value not in adjacent:
        log.write(Text.from_markup(f"\n[{Theme.WARNING}]Distant travel — may require vehicle or favor[/{Theme.WARNING}]"))

    app.refresh_all_panels()


# -----------------------------------------------------------------------------
# Favor Command
# -----------------------------------------------------------------------------

def tui_favor(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Call in a favor from an allied NPC."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
        return

    from ..systems.favors import FavorSystem
    from ..state.schema import FavorType, Disposition

    favors = FavorSystem(app.manager)

    if not args:
        # Show available NPCs and tokens remaining
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]FAVORS[/bold {Theme.TEXT}]"))
        tokens = favors.tokens_remaining()
        log.write(Text.from_markup(f"[{Theme.ACCENT}]Tokens remaining:[/{Theme.ACCENT}] {tokens}/2 this session\n"))

        available = favors.get_available_npcs()

        if not available:
            log.write(Text.from_markup(f"[{Theme.DIM}]No allied NPCs available for favors[/{Theme.DIM}]"))
            log.write(Text.from_markup(f"[{Theme.DIM}]Build standing with NPCs to unlock favors[/{Theme.DIM}]"))
            return

        log.write(Text.from_markup(f"[{Theme.ACCENT}]Available NPCs:[/{Theme.ACCENT}]"))
        for npc in available:
            # Get faction standing
            faction_standing = None
            if npc.faction:
                faction_standing = app.manager.current.factions.get_standing(npc.faction)
            disposition = npc.get_effective_disposition(faction_standing)

            options = favors.get_npc_favor_options(npc)
            favor_list = ", ".join(f"{ft.value} (-{cost})" for ft, cost in options)

            log.write(Text.from_markup(f"\n  [{Theme.TEXT}]{npc.name}[/{Theme.TEXT}] [{Theme.DIM}]({disposition.value})[/{Theme.DIM}]"))
            log.write(Text.from_markup(f"  [{Theme.DIM}]Standing: {npc.personal_standing} | {favor_list}[/{Theme.DIM}]"))

        log.write(Text.from_markup(f"\n[{Theme.DIM}]/favor <npc> <type> [details][/{Theme.DIM}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]Types: ride, intel, gear_loan, introduction, safe_house[/{Theme.DIM}]"))
        return

    if len(args) < 2:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Usage: /favor <npc name> <favor type> [details][/{Theme.WARNING}]"))
        return

    # Parse NPC name and favor type
    npc_query = args[0]
    favor_type_str = args[1].lower()
    details = " ".join(args[2:]) if len(args) > 2 else ""

    # Find NPC
    npc = favors.find_npc_by_name(npc_query)
    if not npc:
        log.write(Text.from_markup(f"[{Theme.WARNING}]NPC not found: {npc_query}[/{Theme.WARNING}]"))
        return

    # Parse favor type
    try:
        favor_type = FavorType(favor_type_str)
    except ValueError:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Unknown favor type: {favor_type_str}[/{Theme.WARNING}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]Types: ride, intel, gear_loan, introduction, safe_house[/{Theme.DIM}]"))
        return

    # Check if we can afford it
    can_afford, reason = favors.can_afford_favor(npc, favor_type)
    if not can_afford:
        log.write(Text.from_markup(f"[{Theme.DANGER}]{reason}[/{Theme.DANGER}]"))
        return

    # Call the favor
    result = favors.call_favor(npc, favor_type, details)

    if "error" in result:
        log.write(Text.from_markup(f"[{Theme.DANGER}]{result['error']}[/{Theme.DANGER}]"))
        return

    log.write(Text.from_markup(f"[{Theme.FRIENDLY}]Favor granted from {result['npc_name']}[/{Theme.FRIENDLY}]"))
    log.write(Text.from_markup(f"[{Theme.DIM}]Type: {result['favor_type']} | Cost: -{result['standing_cost']} standing[/{Theme.DIM}]"))
    log.write(Text.from_markup(f"[{Theme.DIM}]Standing with {result['npc_name']}: {result['old_standing']} → {result['new_standing']}[/{Theme.DIM}]"))
    log.write(Text.from_markup(f"[{Theme.DIM}]Tokens remaining: {result['tokens_remaining']}/2[/{Theme.DIM}]"))

    if result.get("narrative_hint"):
        log.write(Text.from_markup(f"\n[{Theme.TEXT}]{result['narrative_hint']}[/{Theme.TEXT}]"))

    app.refresh_all_panels()


# -----------------------------------------------------------------------------
# Endgame Command
# -----------------------------------------------------------------------------

def tui_endgame(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """View endgame readiness and manage campaign conclusion."""
    if not app.manager or not app.manager.current:
        log.write(Text.from_markup(f"[{Theme.WARNING}]No campaign loaded[/{Theme.WARNING}]"))
        return

    from ..state.schema import CampaignStatus

    campaign = app.manager.current
    readiness = app.manager.get_endgame_readiness()

    if "error" in readiness:
        log.write(Text.from_markup(f"[{Theme.WARNING}]{readiness['error']}[/{Theme.WARNING}]"))
        return

    if not args:
        # Show readiness breakdown
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]ENDGAME READINESS[/bold {Theme.TEXT}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]{readiness['readiness_message']}[/{Theme.DIM}]\n"))

        # Status
        status = readiness["status"]
        status_color = {
            "active": Theme.TEXT,
            "approaching_end": Theme.WARNING,
            "epilogue": Theme.ACCENT,
            "concluded": Theme.FRIENDLY,
        }.get(status, Theme.TEXT)
        log.write(Text.from_markup(f"[{Theme.DIM}]Status:[/{Theme.DIM}] [{status_color}]{status.upper()}[/{status_color}]\n"))

        # Readiness scores with visual bars
        for key, data in readiness["scores"].items():
            score = data["score"]
            bar_filled = int(score * 10)
            bar_empty = 10 - bar_filled
            bar = "█" * bar_filled + "░" * bar_empty
            pct = int(score * 100)
            log.write(Text.from_markup(
                f"  [{Theme.ACCENT}]{data['label']:10}[/{Theme.ACCENT}] [{Theme.TEXT}]{bar}[/{Theme.TEXT}] {pct:3}%  [{Theme.DIM}]{data['description']}[/{Theme.DIM}]"
            ))

        # Overall readiness
        overall = readiness["overall_score"]
        overall_pct = int(overall * 100)
        level = readiness["readiness_level"].upper()
        log.write(Text.from_markup(f"\n[bold {Theme.ACCENT}]Overall: {level} ({overall_pct}%)[/bold {Theme.ACCENT}]"))

        # Player goals
        if readiness["player_goals"]:
            log.write(Text.from_markup(f"\n[{Theme.TEXT}]Your stated goals:[/{Theme.TEXT}]"))
            for goal in readiness["player_goals"]:
                log.write(Text.from_markup(f"  [{Theme.DIM}]• {goal}[/{Theme.DIM}]"))

        # Instructions
        if readiness["can_begin_epilogue"]:
            if status == "active" or status == "approaching_end":
                log.write(Text.from_markup(f"\n[{Theme.FRIENDLY}]Ready for conclusion. Use /endgame begin to start epilogue.[/{Theme.FRIENDLY}]"))
            elif status == "epilogue":
                log.write(Text.from_markup(f"\n[{Theme.WARNING}]Epilogue in progress. Use /endgame conclude when finished.[/{Theme.WARNING}]"))
        else:
            log.write(Text.from_markup(f"\n[{Theme.DIM}]Continue playing to accumulate more narrative weight.[/{Theme.DIM}]"))

        return

    subcommand = args[0].lower()

    if subcommand == "begin":
        # Start epilogue
        result = app.manager.begin_epilogue()

        if "error" in result:
            log.write(Text.from_markup(f"[{Theme.DANGER}]{result['error']}[/{Theme.DANGER}]"))
            if "suggestion" in result:
                log.write(Text.from_markup(f"[{Theme.DIM}]{result['suggestion']}[/{Theme.DIM}]"))
            return

        log.write(Text.from_markup(f"[bold {Theme.ACCENT}]EPILOGUE BEGINS[/bold {Theme.ACCENT}]"))
        log.write(Text.from_markup(f"[{Theme.TEXT}]Your story reaches its conclusion. All threads surface now.[/{Theme.TEXT}]\n"))

        # Show threads that will surface
        threads = result.get("threads_to_surface", [])
        if threads:
            log.write(Text.from_markup(f"[{Theme.WARNING}]Dormant threads surfacing:[/{Theme.WARNING}]"))
            for thread in threads:
                severity_color = {
                    "minor": Theme.DIM,
                    "moderate": Theme.WARNING,
                    "major": Theme.DANGER,
                }.get(thread["severity"], Theme.TEXT)
                log.write(Text.from_markup(
                    f"  [{severity_color}]• {thread['description']} (Session {thread['created_session']})[/{severity_color}]"
                ))

        # Show player goals for the epilogue
        goals = result.get("player_goals", [])
        if goals:
            log.write(Text.from_markup(f"\n[{Theme.TEXT}]Your goals to resolve:[/{Theme.TEXT}]"))
            for goal in goals:
                log.write(Text.from_markup(f"  [{Theme.DIM}]• {goal}[/{Theme.DIM}]"))

        log.write(Text.from_markup(f"\n[{Theme.FRIENDLY}]When your story is complete: /endgame conclude[/{Theme.FRIENDLY}]"))
        app.refresh_all_panels()

    elif subcommand == "cancel":
        # Cancel epilogue
        result = app.manager.cancel_epilogue()

        if "error" in result:
            log.write(Text.from_markup(f"[{Theme.DANGER}]{result['error']}[/{Theme.DANGER}]"))
            return

        log.write(Text.from_markup(f"[{Theme.WARNING}]Epilogue cancelled. Returning to active play.[/{Theme.WARNING}]"))
        app.refresh_all_panels()

    elif subcommand == "conclude":
        # Conclude campaign
        result = app.manager.conclude_campaign()

        if "error" in result:
            log.write(Text.from_markup(f"[{Theme.DANGER}]{result['error']}[/{Theme.DANGER}]"))
            return

        log.write(Text.from_markup(f"[bold {Theme.ACCENT}]═══ CAMPAIGN CONCLUDED ═══[/bold {Theme.ACCENT}]\n"))

        # Campaign summary
        log.write(Text.from_markup(f"[bold {Theme.TEXT}]{result['campaign_name']}[/bold {Theme.TEXT}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]{result['session_count']} sessions played[/{Theme.DIM}]\n"))

        # Character summary
        char = result.get("character", {})
        log.write(Text.from_markup(f"[{Theme.TEXT}]{char.get('name', 'Unknown')}[/{Theme.TEXT}]"))
        if char.get("background"):
            log.write(Text.from_markup(f"[{Theme.DIM}]{char['background']}[/{Theme.DIM}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]{char.get('hinge_count', 0)} defining choices made[/{Theme.DIM}]\n"))

        # Primary arc
        arc = result.get("primary_arc", {})
        if arc.get("type"):
            log.write(Text.from_markup(f"[{Theme.ACCENT}]Arc: {arc['title']} ({arc['type']})[/{Theme.ACCENT}]"))
            log.write(Text.from_markup(f"[{Theme.DIM}]Reinforced {arc['times_reinforced']} times[/{Theme.DIM}]\n"))

        # Final faction standings
        standings = result.get("faction_standings", {})
        if standings:
            log.write(Text.from_markup(f"[{Theme.TEXT}]Faction Legacy:[/{Theme.TEXT}]"))
            for faction, data in list(standings.items())[:5]:  # Top 5
                level = data.get("level", "neutral")
                level_color = {
                    "hostile": Theme.HOSTILE,
                    "unfriendly": Theme.UNFRIENDLY,
                    "neutral": Theme.NEUTRAL,
                    "friendly": Theme.FRIENDLY,
                    "allied": Theme.ALLIED,
                }.get(level, Theme.TEXT)
                log.write(Text.from_markup(f"  [{level_color}]{faction}: {level.upper()}[/{level_color}]"))

        log.write(Text.from_markup(f"\n[{Theme.FRIENDLY}]Your story is complete. Thank you for playing.[/{Theme.FRIENDLY}]"))
        app.refresh_all_panels()

    else:
        log.write(Text.from_markup(f"[{Theme.WARNING}]Unknown subcommand: {subcommand}[/{Theme.WARNING}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]Usage: /endgame [begin|cancel|conclude][/{Theme.DIM}]"))


def tui_retire(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Gracefully retire your character and end the campaign."""
    log.write(Text.from_markup(f"[{Theme.TEXT}]Your character steps back from the life. One final reckoning awaits.[/{Theme.TEXT}]\n"))
    # Delegate to endgame begin
    tui_endgame(app, log, ["begin"])


# -----------------------------------------------------------------------------
# Compare Command
# -----------------------------------------------------------------------------

def tui_compare(app: "SENTINELApp", log: "RichLog", args: list[str]) -> None:
    """Cross-campaign comparison."""
    from pathlib import Path
    import sys

    wiki_dir = Path(getattr(app.manager, '_wiki_dir', 'wiki')) if app.manager else Path('wiki')

    # Try to import and run the comparison script
    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    if scripts_dir.exists():
        sys.path.insert(0, str(scripts_dir))

    try:
        from compare_campaigns import discover_campaigns, generate_report

        log.write(Text.from_markup(f"[{Theme.DIM}]Scanning campaigns...[/{Theme.DIM}]"))

        campaigns = discover_campaigns(wiki_dir)

        if not campaigns:
            log.write(Text.from_markup(f"[{Theme.WARNING}]No campaigns with events found[/{Theme.WARNING}]"))
            log.write(Text.from_markup(f"[{Theme.DIM}]Play some sessions to generate wiki events[/{Theme.DIM}]"))
            return

        log.write(Text.from_markup(f"[bold {Theme.TEXT}]Cross-Campaign Analysis[/bold {Theme.TEXT}]"))
        log.write(Text.from_markup(f"[{Theme.DIM}]{len(campaigns)} campaign(s) analyzed[/{Theme.DIM}]\n"))

        # Campaign overview
        log.write(Text.from_markup(f"[{Theme.ACCENT}]Campaigns:[/{Theme.ACCENT}]"))
        for c in sorted(campaigns, key=lambda x: x.sessions, reverse=True):
            log.write(Text.from_markup(
                f"  [{Theme.TEXT}]{c.id}[/{Theme.TEXT}]: "
                f"{c.sessions} sessions, {len(c.hinges)} hinges, {len(c.faction_shifts)} shifts"
            ))

        # Faction standings comparison
        all_factions: set[str] = set()
        for c in campaigns:
            for shift in c.faction_shifts:
                all_factions.add(shift.faction)

        if all_factions and len(campaigns) > 1:
            log.write(Text.from_markup(f"\n[{Theme.ACCENT}]Faction Divergence:[/{Theme.ACCENT}]"))

            for faction in sorted(all_factions):
                standings = []
                for c in campaigns:
                    standing = c.final_standings.get(faction, "Neutral")
                    standings.append(f"{c.id}:{standing}")

                unique = set(s.split(":")[1] for s in standings)
                if len(unique) == 1:
                    icon = f"[{Theme.WARNING}]![/{Theme.WARNING}]"  # Convergent
                else:
                    icon = f"[{Theme.FRIENDLY}]~[/{Theme.FRIENDLY}]"  # Divergent

                log.write(Text.from_markup(f"  {icon} [{Theme.TEXT}]{faction}[/{Theme.TEXT}]: {', '.join(standings)}"))

        elif all_factions:
            log.write(Text.from_markup(f"\n[{Theme.ACCENT}]Final Standings:[/{Theme.ACCENT}]"))
            c = campaigns[0]
            for faction in sorted(all_factions):
                standing = c.final_standings.get(faction, "Neutral")
                log.write(Text.from_markup(f"  [{Theme.TEXT}]{faction}[/{Theme.TEXT}]: {standing}"))

        # Write full report
        meta_dir = wiki_dir / "campaigns" / "_meta"
        meta_dir.mkdir(exist_ok=True)
        report = generate_report(campaigns, wiki_dir)
        report_path = meta_dir / "comparison_report.md"
        report_path.write_text(report, encoding="utf-8")

        log.write(Text.from_markup(f"\n[{Theme.DIM}]Full report: {report_path}[/{Theme.DIM}]"))

    except ImportError as e:
        log.write(Text.from_markup(f"[{Theme.DANGER}]Could not load comparison script: {e}[/{Theme.DANGER}]"))
    except Exception as e:
        log.write(Text.from_markup(f"[{Theme.DANGER}]Comparison failed: {e}[/{Theme.DANGER}]"))


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
    set_tui_handler("/shop", tui_shop)
    set_tui_handler("/jobs", tui_jobs)
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
    set_tui_handler("/compare", tui_compare)

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
    set_tui_handler("/ping", tui_ping)

    # Settings
    set_tui_handler("/backend", tui_backend)
    set_tui_handler("/model", tui_model)
    set_tui_handler("/context", tui_context)

    # Mission
    set_tui_handler("/start", tui_start)
    set_tui_handler("/mission", tui_mission)
    set_tui_handler("/consult", tui_consult)
    set_tui_handler("/debrief", tui_debrief)
    set_tui_handler("/travel", tui_travel)

    # Geography & Favors
    set_tui_handler("/region", tui_region)
    set_tui_handler("/favor", tui_favor)

    # Endgame
    set_tui_handler("/endgame", tui_endgame)
    set_tui_handler("/retire", tui_retire)
