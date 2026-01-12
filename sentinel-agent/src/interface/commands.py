"""
Command handlers for SENTINEL CLI.

Each command function takes (manager, agent, args) and returns:
- None for normal completion
- ("gm_prompt", prompt) to trigger GM response
- backend_name string for /backend command
"""

import sys
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from ..state import CampaignManager, Character, Background
from ..state.schema import SessionReflection, HistoryType
from ..agent import SentinelAgent
from ..lore.quotes import (
    get_quotes_by_faction, get_quotes_by_category, get_all_mottos,
    format_quote_for_dialogue, QuoteCategory, LORE_QUOTES,
)
from .renderer import (
    console, THEME, show_status, show_backend_status, show_help,
    render_codec_box, FACTION_COLORS, DISPOSITION_COLORS, status_bar,
)
from .config import (
    set_model as save_model_config, set_animate_banner, set_show_status_bar,
    load_config,
)
from .glyphs import g


# -----------------------------------------------------------------------------
# Campaign Commands
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
        status_bar.reset_tracking()  # Reset delta tracking for fresh campaign
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


def cmd_save(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Save current campaign."""
    manager.save_campaign()
    console.print(f"[{THEME['accent']}]Saved[/{THEME['accent']}]")


def cmd_delete(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Delete a campaign."""
    if not args:
        # Show list and prompt
        campaigns = manager.list_campaigns()
        if not campaigns:
            console.print("[yellow]No campaigns to delete.[/yellow]")
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
        selection = Prompt.ask("Delete campaign #")
        args = [selection]

    # Confirm deletion
    campaign_id = args[0]
    campaigns = manager.list_campaigns()

    # Resolve numeric index to get name for confirmation
    if campaign_id.isdigit():
        idx = int(campaign_id) - 1
        if 0 <= idx < len(campaigns):
            campaign_name = campaigns[idx]["name"]
            campaign_id = campaigns[idx]["id"]
        else:
            console.print("[red]Invalid selection[/red]")
            return
    else:
        # Find by ID
        campaign_name = next((c["name"] for c in campaigns if c["id"] == campaign_id), campaign_id)

    confirm = Prompt.ask(
        f"[{THEME['danger']}]Delete '{campaign_name}'? This cannot be undone[/{THEME['danger']}]",
        choices=["y", "n"],
        default="n"
    )

    if confirm != "y":
        console.print("[dim]Cancelled[/dim]")
        return

    deleted_id = manager.delete_campaign(campaign_id)
    if deleted_id:
        console.print(f"[{THEME['accent']}]Deleted campaign: {campaign_name}[/{THEME['accent']}]")
    else:
        console.print("[red]Campaign not found[/red]")


# -----------------------------------------------------------------------------
# Backend Commands
# -----------------------------------------------------------------------------

def cmd_backend(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Show or change backend."""
    valid_backends = ["lmstudio", "ollama", "claude", "auto"]

    if not args:
        show_backend_status(agent)
        console.print(f"\n[{THEME['dim']}]Available backends:[/{THEME['dim']}]")
        console.print(f"  [{THEME['accent']}]lmstudio[/{THEME['accent']}]   - Local LLM (free, requires LM Studio)")
        console.print(f"  [{THEME['accent']}]ollama[/{THEME['accent']}]     - Local LLM (free, requires Ollama)")
        console.print(f"  [{THEME['accent']}]claude[/{THEME['accent']}]     - Claude via Claude Code CLI (uses existing auth)")
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


def cmd_model(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """List or switch models for the current backend."""
    if not agent.client:
        console.print("[yellow]No LLM backend active[/yellow]")
        return

    # Get client and list models
    client = agent.client
    if not hasattr(client, "list_models"):
        console.print("[yellow]Model listing not supported[/yellow]")
        return

    models = client.list_models()
    if not models:
        console.print(f"[yellow]No models available (is {agent.backend} running?)[/yellow]")
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

    if not hasattr(client, "set_model"):
        console.print(f"[yellow]Model switching not supported for {agent.backend}[/yellow]")
        return

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
    save_model_config(selection)  # Save preference
    console.print(f"[green]Switched to:[/green] {selection}")
    console.print("[dim]  (Saved as default)[/dim]")

    # Check tool support
    if client.supports_tools:
        console.print("[dim]  Tool calling supported[/dim]")
    else:
        console.print("[yellow]  Tool calling not supported by this model[/yellow]")


def cmd_ping(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Lightweight backend/model connectivity check."""
    if not agent.client:
        console.print("[yellow]No LLM backend active[/yellow]")
        return

    backend = agent.backend
    model = agent.client.model_name
    console.print(f"[dim]Pinging {backend} ({model})...[/dim]")
    try:
        response = agent.client.chat(
            messages=[Message(role="user", content="Reply with exactly: pong")],
            system="Reply with exactly: pong",
            tools=None,
            temperature=0.0,
            max_tokens=5,
        )
        text = response.content.strip()
        console.print("[green]pong ✓[/green]")
        if text.lower() != "pong" and text:
            console.print(f"[dim]Got: {text}[/dim]")
    except Exception as e:
        console.print(f"[red]Ping failed: {e}[/red]")

def cmd_banner(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Toggle banner animation on startup."""
    config = load_config()
    current = config.get("animate_banner", True)

    if args:
        # Set explicitly: /banner on, /banner off
        arg = args[0].lower()
        if arg in ("on", "true", "1", "yes"):
            new_value = True
        elif arg in ("off", "false", "0", "no"):
            new_value = False
        else:
            console.print(f"[yellow]Unknown option: {arg}[/yellow]")
            console.print("[dim]Use: /banner on, /banner off, or just /banner to toggle[/dim]")
            return
    else:
        # Toggle
        new_value = not current

    set_animate_banner(new_value)
    status = "[green]on[/green]" if new_value else "[dim]off[/dim]"
    console.print(f"Banner animation: {status}")
    console.print("[dim]  (Saved for future sessions)[/dim]")


def cmd_statusbar(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Toggle persistent status bar."""
    config = load_config()
    current = config.get("show_status_bar", True)

    if args:
        # Set explicitly: /statusbar on, /statusbar off
        arg = args[0].lower()
        if arg in ("on", "true", "1", "yes"):
            new_value = True
        elif arg in ("off", "false", "0", "no"):
            new_value = False
        else:
            console.print(f"[yellow]Unknown option: {arg}[/yellow]")
            console.print("[dim]Use: /statusbar on, /statusbar off, or just /statusbar to toggle[/dim]")
            return
    else:
        # Toggle
        new_value = not current

    # Update both config and runtime state
    set_show_status_bar(new_value)
    status_bar.enabled = new_value

    status = "[green]on[/green]" if new_value else "[dim]off[/dim]"
    console.print(f"Status bar: {status}")
    console.print("[dim]  (Saved for future sessions)[/dim]")


# -----------------------------------------------------------------------------
# Lore Quotes
# -----------------------------------------------------------------------------

FACTION_IDS = [
    "nexus", "ember_colonies", "lattice", "convergence", "covenant",
    "wanderers", "cultivators", "steel_syndicate", "witnesses",
    "architects", "ghost_networks",
]


def _show_lore_quotes(args: list[str]):
    """Show lore quotes, optionally filtered by faction."""
    # Parse args for faction filter
    faction_filter = None
    show_mottos = False

    if args:
        arg = args[0].lower()
        if arg == "mottos":
            show_mottos = True
        else:
            # Match faction (flexible matching)
            for faction_id in FACTION_IDS:
                if faction_id.startswith(arg) or faction_id.replace("_", "").startswith(arg):
                    faction_filter = faction_id
                    break

            if not faction_filter and arg not in ("all", "help"):
                console.print(f"[yellow]Unknown faction: {args[0]}[/yellow]")
                console.print(f"[dim]Available: {', '.join(FACTION_IDS)}[/dim]")
                return

    # Show mottos summary
    if show_mottos:
        console.print(f"\n[bold {THEME['primary']}]◈ FACTION MOTTOS ◈[/bold {THEME['primary']}]")
        console.print()
        mottos = get_all_mottos()
        for faction_id, motto in mottos.items():
            name = faction_id.replace("_", " ").title()
            console.print(f"  [{THEME['accent']}]{name}[/{THEME['accent']}]")
            console.print(f"    \"{motto}\"")
            console.print()
        return

    # Show help if no args
    if not args or (args and args[0].lower() == "help"):
        console.print(f"\n[bold]Lore Quotes[/bold]")
        console.print(f"  [dim]Curated quotes for NPC dialogue and world-building[/dim]")
        console.print()
        console.print(f"  /lore quotes mottos     — Show all faction mottos")
        console.print(f"  /lore quotes <faction>  — Show quotes for a faction")
        console.print(f"  /lore quotes all        — Show all quotes")
        console.print()
        console.print(f"  [dim]Total quotes: {len(LORE_QUOTES)}[/dim]")
        console.print()

        # Quick summary
        console.print(f"  [bold]Categories:[/bold]")
        for cat in QuoteCategory:
            count = len(get_quotes_by_category(cat))
            console.print(f"    {cat.value}: {count}")
        return

    # Show all or faction-specific quotes
    if faction_filter:
        quotes = get_quotes_by_faction(faction_filter)
        title = faction_filter.replace("_", " ").title()
        console.print(f"\n[bold {THEME['primary']}]◈ {title.upper()} QUOTES ◈[/bold {THEME['primary']}]")
    else:
        quotes = LORE_QUOTES
        console.print(f"\n[bold {THEME['primary']}]◈ ALL LORE QUOTES ◈[/bold {THEME['primary']}]")

    if not quotes:
        console.print(f"[dim]No quotes found for {faction_filter}[/dim]")
        return

    console.print()

    # Group by category
    by_category: dict[QuoteCategory, list] = {}
    for quote in quotes:
        by_category.setdefault(quote.category, []).append(quote)

    for category in QuoteCategory:
        cat_quotes = by_category.get(category, [])
        if not cat_quotes:
            continue

        # Category header
        cat_label = category.value.replace("_", " ").upper()
        console.print(f"[bold {THEME['secondary']}]{cat_label}[/bold {THEME['secondary']}]")

        for quote in cat_quotes:
            # Quote text
            console.print(f"  \"{quote.text}\"")
            console.print(f"    [{THEME['dim']}]— {quote.speaker}[/{THEME['dim']}]")
            if quote.context:
                console.print(f"    [{THEME['dim']}]({quote.context})[/{THEME['dim']}]")
            console.print()

        console.print()


def cmd_lore(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Show lore status and test retrieval. Use /lore <faction> to filter by perspective."""
    # Handle /lore quotes subcommand
    if args and args[0].lower() == "quotes":
        _show_lore_quotes(args[1:])
        return

    if not agent.lore_retriever:
        console.print("[yellow]No lore directory configured[/yellow]")
        return

    retriever = agent.lore_retriever

    # Check if first arg is a faction name (for filtering)
    index = retriever.index
    known_factions = set(index.get("by_faction", {}).keys())
    faction_filter = None
    query_args = args

    if args:
        # Check if first arg matches a faction (case-insensitive)
        first_arg_lower = args[0].lower()
        for faction in known_factions:
            if faction.lower() == first_arg_lower or faction.lower().startswith(first_arg_lower):
                faction_filter = faction
                query_args = args[1:]  # Rest is the query
                break

    # Show lore status
    console.print(f"\n[bold]Lore System[/bold]")
    console.print(f"  Directory: {retriever.lore_dir}")
    console.print(f"  Chunks indexed: {retriever.chunk_count}")

    if known_factions:
        factions_list = ", ".join(sorted(known_factions))
        console.print(f"  Factions tagged: {factions_list}")

    if index["by_theme"]:
        themes = ", ".join(sorted(index["by_theme"].keys()))
        console.print(f"  Themes tagged: {themes}")

    # Show faction filter notice
    if faction_filter:
        console.print(f"\n[bold {THEME['accent']}]◈ Viewing through {faction_filter.upper()} perspective ◈[/bold {THEME['accent']}]")
        console.print(f"[dim]Results filtered and weighted toward {faction_filter} sources.[/dim]")
        console.print(f"[dim]Remember: Every faction believes they're telling the truth.[/dim]")

    # Test retrieval if query provided (or faction filter with optional query)
    if args:
        query = " ".join(query_args) if query_args else ""
        if query:
            console.print(f"\n[dim]Searching for: {query}[/dim]")

        # Use unified retriever's query_active() for strain-bypassing retrieval
        # This is "active" retrieval - player explicitly requested it via command
        factions_arg = [faction_filter] if faction_filter else None

        if agent.unified_retriever:
            # Active retrieval via unified retriever (ignores strain tier)
            unified_result = agent.unified_retriever.query_active(
                topic=query or (faction_filter or ""),
                factions=factions_arg,
            )
            _display_lore_results(unified_result.lore, limit=3 if faction_filter else 2)

            # Also show campaign history if available
            if unified_result.has_campaign:
                console.print(f"\n[bold {THEME['secondary']}]Campaign History[/bold {THEME['secondary']}]")
                for hit in unified_result.campaign[:3]:
                    frame_type = hit.get("type", "event")
                    session = hit.get("session", "?")
                    summary = _format_campaign_hit(hit)
                    console.print(f"  [{THEME['dim']}]S{session}[/{THEME['dim']}] [{THEME['accent']}]{frame_type}[/{THEME['accent']}]: {summary}")
        else:
            # Fallback to raw lore retriever
            results = retriever.retrieve(query=query, factions=factions_arg, limit=3 if faction_filter else 2)
            _display_lore_retrieval_results(results)
    else:
        console.print(f"\n[dim]Use /lore <query> to search, or /lore <faction> to filter by perspective[/dim]")
        console.print(f"[dim]Example: /lore lattice infrastructure[/dim]")


def _display_lore_results(lore_hits: list[dict], limit: int = 2):
    """Display lore results from UnifiedResult format."""
    import re

    if not lore_hits:
        console.print("[dim]No lore matches found[/dim]")
        return

    # Source type labels
    source_labels = {
        "canon": "CANON",
        "case_file": "CASE FILE",
        "character": "CHARACTER",
        "session": "SESSION",
        "default": "LORE",
    }

    for hit in lore_hits[:limit]:
        source = hit.get("source", "unknown")
        title = hit.get("title", "")
        section = hit.get("section", "")
        content = hit.get("content", "")
        match_reasons = hit.get("match_reasons", [])
        score = hit.get("score", 0)

        # Determine source type from source name
        source_type = "default"
        source_lower = source.lower()
        if "canon" in source_lower or "bible" in source_lower:
            source_type = "canon"
        elif "case" in source_lower:
            source_type = "case_file"
        elif "character" in source_lower:
            source_type = "character"
        elif "session" in source_lower:
            source_type = "session"

        source_label = source_labels.get(source_type, "LORE")

        # Relevance indicator based on score
        if score >= 5.0:
            level = 5
        elif score >= 3.5:
            level = 4
        elif score >= 2.0:
            level = 3
        elif score >= 1.0:
            level = 2
        else:
            level = 1
        relevance_indicator = "●" * level + "○" * (5 - level)

        console.print(
            f"\n[{THEME['accent']}]{relevance_indicator}[/{THEME['accent']}] "
            f"[dim]{source_label}[/dim] — "
            f"[cyan]{title}[/cyan]"
        )

        if section:
            console.print(f"  [{THEME['secondary']}]§ {section}[/{THEME['secondary']}]")

        if match_reasons:
            console.print(f"  [{THEME['dim']}]{', '.join(match_reasons)}[/{THEME['dim']}]")

        # Content snippet
        preview = re.sub(r'\s+', ' ', content[:180]).strip()
        if len(content) > 180:
            last_space = preview.rfind(' ')
            if last_space > 120:
                preview = preview[:last_space]
            preview += "..."
        console.print(f"  [italic]{preview}[/italic]")


def _display_lore_retrieval_results(results):
    """Display lore results from raw LoreRetriever format."""
    import re

    if not results:
        console.print("[dim]No matches found[/dim]")
        return

    source_labels = {
        "canon": "CANON",
        "case_file": "CASE FILE",
        "character": "CHARACTER",
        "session": "SESSION",
        "default": "LORE",
    }

    for r in results:
        source_label = source_labels.get(r.source_type, "LORE")
        console.print(
            f"\n[{THEME['accent']}]{r.relevance_indicator}[/{THEME['accent']}] "
            f"[dim]{source_label}[/dim] — "
            f"[cyan]{r.chunk.title}[/cyan]"
        )

        if r.chunk.section:
            console.print(f"  [{THEME['secondary']}]§ {r.chunk.section}[/{THEME['secondary']}]")

        meta_parts = []
        if r.chunk.arc:
            meta_parts.append(r.chunk.arc)
        if r.chunk.date:
            meta_parts.append(r.chunk.date)
        if r.chunk.location:
            meta_parts.append(r.chunk.location)
        if meta_parts:
            console.print(f"  [{THEME['dim']}]{' · '.join(meta_parts)}[/{THEME['dim']}]")

        if r.match_reasons:
            console.print(f"  [{THEME['dim']}]{', '.join(r.match_reasons)}[/{THEME['dim']}]")

        snippet = r.get_keyword_snippet(max_len=180)
        if not snippet:
            preview = re.sub(r'\s+', ' ', r.chunk.content[:180]).strip()
            if len(r.chunk.content) > 180:
                last_space = preview.rfind(' ')
                if last_space > 120:
                    preview = preview[:last_space]
                preview += "..."
            snippet = preview

        console.print(f"  [italic]{snippet}[/italic]")


def _format_campaign_hit(hit: dict) -> str:
    """Format a campaign history hit for display."""
    frame_type = hit.get("type", "event")

    if frame_type == "turn_state":
        return hit.get("narrative_summary", "Turn state recorded")[:60]
    elif frame_type == "hinge_moment":
        return hit.get("choice", "Hinge moment")[:60]
    elif frame_type == "npc_interaction":
        npc = hit.get("npc_name", "Unknown")
        action = hit.get("player_action", "")[:40]
        return f"{npc}: {action}"
    elif frame_type == "faction_shift":
        faction = hit.get("faction", "Unknown")
        from_s = hit.get("from_standing", "?")
        to_s = hit.get("to_standing", "?")
        return f"{faction}: {from_s} -> {to_s}"
    elif frame_type == "dormant_thread":
        return f"Thread: {hit.get('origin', 'Unknown')[:50]}"
    else:
        return str(hit)[:60]


# -----------------------------------------------------------------------------
# Character Commands
# -----------------------------------------------------------------------------

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


def cmd_npc(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """View NPC information including personal standing and interactions.

    Usage:
        /npc                  - List all active NPCs
        /npc <name>           - Show details for an NPC
        /npc <name> history   - Show full interaction history
    """
    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    # List all NPCs
    if not args:
        active = manager.current.npcs.active
        dormant = manager.current.npcs.dormant

        if not active and not dormant:
            console.print(f"[{THEME['dim']}]No NPCs in this campaign yet.[/{THEME['dim']}]")
            return

        console.print(f"\n[bold {THEME['primary']}]◈ NPCs ◈[/bold {THEME['primary']}]")

        if active:
            console.print(f"\n[bold {THEME['secondary']}]ACTIVE[/bold {THEME['secondary']}]")
            for npc in active:
                _display_npc_summary(npc, manager)

        if dormant:
            console.print(f"\n[bold {THEME['secondary']}]DORMANT[/bold {THEME['secondary']}]")
            for npc in dormant:
                _display_npc_summary(npc, manager, dim=True)

        return

    # Find NPC by name
    name_query = args[0].lower()
    show_history = len(args) > 1 and args[1].lower() == "history"

    npc = None
    for n in manager.current.npcs.active + manager.current.npcs.dormant:
        if name_query in n.name.lower():
            npc = n
            break

    if not npc:
        console.print(f"[{THEME['warning']}]No NPC found matching '{args[0]}'[/{THEME['warning']}]")
        return

    # Get comprehensive status
    status = manager.get_npc_status(npc.id)
    if not status:
        console.print(f"[{THEME['warning']}]Could not retrieve NPC status[/{THEME['warning']}]")
        return

    # Display NPC in codec box style
    eff_disp = status["effective_disposition"]
    faction_id = npc.faction.value if npc.faction else "unknown"
    greeting = _generate_npc_greeting(npc, eff_disp)

    # Check if NPC has relevant memories to show memory tag
    memory_tag = None
    if status["remembers"]:
        memory_tag = "MEMORY"

    console.print()  # Spacing before codec box
    render_codec_box(
        npc_name=npc.name,
        faction=faction_id,
        dialogue=greeting,
        role=getattr(npc, 'role', None),
        disposition=eff_disp,
        memory_tag=memory_tag,
    )

    # Additional stats below codec box

    # Standing breakdown
    console.print(f"\n[bold {THEME['secondary']}]RELATIONSHIP[/bold {THEME['secondary']}]")

    # Personal standing with visual bar
    ps = status["personal_standing"]
    bar = _standing_bar(ps)
    console.print(f"  [{THEME['dim']}]Personal:[/{THEME['dim']}] {bar} ({ps:+d})")

    # Faction standing if applicable
    if status["faction_standing"]:
        console.print(f"  [{THEME['dim']}]Faction:[/{THEME['dim']}] {status['faction_standing']}")

    # Effective disposition
    eff_disp = status["effective_disposition"]
    disp_color = _disposition_color(eff_disp)
    console.print(f"  [{THEME['dim']}]Effective:[/{THEME['dim']}] [{disp_color}]{eff_disp.upper()}[/{disp_color}]")

    # Agenda
    agenda = status["agenda"]
    console.print(f"\n[bold {THEME['secondary']}]AGENDA[/bold {THEME['secondary']}]")
    console.print(f"  [{THEME['dim']}]Wants:[/{THEME['dim']}] {agenda['wants']}")
    console.print(f"  [{THEME['dim']}]Fears:[/{THEME['dim']}] {agenda['fears']}")
    if agenda.get("leverage"):
        console.print(f"  [{THEME['warning']}]Leverage:[/{THEME['warning']}] {agenda['leverage']}")
    if agenda.get("owes"):
        console.print(f"  [{THEME['accent']}]Owes you:[/{THEME['accent']}] {agenda['owes']}")

    # Memories
    if status["remembers"]:
        console.print(f"\n[bold {THEME['secondary']}]REMEMBERS[/bold {THEME['secondary']}]")
        for mem in status["remembers"]:
            console.print(f"  [{THEME['dim']}]•[/{THEME['dim']}] {mem}")

    # Recent interactions
    interactions = status["interactions"]
    if interactions:
        console.print(f"\n[bold {THEME['secondary']}]RECENT INTERACTIONS[/bold {THEME['secondary']}]")
        for inter in interactions:
            change = inter["standing_change"]
            if change > 0:
                change_str = f"[{THEME['accent']}]+{change}[/{THEME['accent']}]"
            elif change < 0:
                change_str = f"[{THEME['danger']}]{change}[/{THEME['danger']}]"
            else:
                change_str = ""

            console.print(
                f"  [{THEME['dim']}]S{inter['session']}[/{THEME['dim']}] "
                f"{inter['action'][:40]}{'...' if len(inter['action']) > 40 else ''} {change_str}"
            )

    # Full history if requested
    if show_history and npc.interactions:
        console.print(f"\n[bold {THEME['secondary']}]FULL HISTORY[/bold {THEME['secondary']}]")
        for inter in npc.interactions:
            change = inter.standing_change
            if change > 0:
                change_str = f"[{THEME['accent']}]+{change}[/{THEME['accent']}]"
            elif change < 0:
                change_str = f"[{THEME['danger']}]{change}[/{THEME['danger']}]"
            else:
                change_str = ""

            console.print(
                f"\n  [{THEME['dim']}]Session {inter.session}[/{THEME['dim']}] {change_str}"
            )
            console.print(f"  [{THEME['secondary']}]Action:[/{THEME['secondary']}] {inter.action}")
            console.print(f"  [{THEME['secondary']}]Outcome:[/{THEME['secondary']}] {inter.outcome}")

    return None


def _generate_npc_greeting(npc, disposition: str) -> str:
    """Generate a contextual greeting based on NPC disposition and agenda."""
    # Disposition-based greeting templates
    greetings = {
        "hostile": [
            f"What do you want? I've got nothing to say to you.",
            f"You've got nerve showing your face here.",
            f"We're done talking.",
        ],
        "wary": [
            f"...Make it quick. I'm watching you.",
            f"I don't trust you. Not yet.",
            f"Speak. But choose your words carefully.",
        ],
        "neutral": [
            f"Can I help you with something?",
            f"You need something?",
            f"What brings you here?",
        ],
        "warm": [
            f"Good to see you. What can I do for you?",
            f"Ah, it's you. Come in, come in.",
            f"I was hoping you'd stop by.",
        ],
        "loyal": [
            f"My friend. Whatever you need, I'm here.",
            f"You know I've got your back. What's going on?",
            f"Say the word. I'm with you.",
        ],
    }

    import random
    templates = greetings.get(disposition.lower(), greetings["neutral"])
    return random.choice(templates)


def _display_npc_summary(npc, manager: CampaignManager, dim: bool = False):
    """Display a single NPC in summary format."""
    style = THEME["dim"] if dim else THEME["secondary"]

    # Get faction standing for effective disposition
    faction_standing = None
    if npc.faction and manager.current:
        faction_standing = manager.current.factions.get(npc.faction).standing

    eff_disp = npc.get_effective_disposition(faction_standing)
    disp_color = _disposition_color(eff_disp.value) if not dim else THEME["dim"]

    faction_str = f" [{THEME['dim']}]{npc.faction.value}[/{THEME['dim']}]" if npc.faction else ""
    standing_str = f" ({npc.personal_standing:+d})" if npc.personal_standing != 0 else ""

    console.print(
        f"  [{style}]{g('npc')}[/{style}] "
        f"[{style}]{npc.name}[/{style}]{faction_str} — "
        f"[{disp_color}]{eff_disp.value}[/{disp_color}]{standing_str}"
    )


def _standing_bar(standing: int) -> str:
    """Create a visual bar for standing (-100 to +100)."""
    # Normalize to 0-10 scale
    normalized = (standing + 100) / 20  # 0-10
    filled = int(normalized)
    empty = 10 - filled

    if standing < -30:
        color = "red"
    elif standing < 0:
        color = "yellow"
    elif standing < 30:
        color = "white"
    else:
        color = "green"

    return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"


def _disposition_color(disposition: str) -> str:
    """Get color for a disposition level."""
    colors = {
        "hostile": THEME["danger"],
        "wary": THEME["warning"],
        "neutral": THEME["dim"],
        "warm": THEME["secondary"],
        "loyal": THEME["accent"],
    }
    return colors.get(disposition.lower(), THEME["dim"])


# -----------------------------------------------------------------------------
# Faction Commands
# -----------------------------------------------------------------------------

def cmd_factions(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """View faction standings and inter-faction relationships.

    Usage:
        /factions              - List all factions with player standing
        /factions <name>       - Show a faction's relationship web
    """
    from ..state.schema import FactionName, get_faction_relation

    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    # Get all faction standings
    factions = manager.current.factions

    # If no args, show all factions
    if not args:
        console.print(f"\n[bold {THEME['primary']}]◈ FACTION STANDINGS ◈[/bold {THEME['primary']}]")
        console.print(f"[{THEME['dim']}]Your reputation with each faction[/{THEME['dim']}]\n")

        # Group by standing level
        standings_order = ["Allied", "Friendly", "Neutral", "Unfriendly", "Hostile"]
        grouped = {s: [] for s in standings_order}

        for faction_enum in FactionName:
            faction_state = factions.get(faction_enum)
            standing = faction_state.standing.value
            grouped[standing].append(faction_enum.value)

        for standing in standings_order:
            if grouped[standing]:
                color = _standing_color(standing)
                console.print(f"[bold {color}]{standing.upper()}[/bold {color}]")
                for name in grouped[standing]:
                    console.print(f"  [{THEME['secondary']}]{g('faction')}[/{THEME['secondary']}] {name}")
                console.print()

        console.print(f"[{THEME['dim']}]Use /factions <name> to see a faction's relationship web[/{THEME['dim']}]")
        return

    # Find faction by name (case-insensitive partial match)
    query = args[0].lower()
    matched_faction = None
    for faction_enum in FactionName:
        if query in faction_enum.value.lower():
            matched_faction = faction_enum
            break

    if not matched_faction:
        console.print(f"[{THEME['warning']}]No faction found matching '{args[0]}'[/{THEME['warning']}]")
        console.print(f"[{THEME['dim']}]Available: {', '.join(f.value for f in FactionName)}[/{THEME['dim']}]")
        return

    # Show faction relationship web
    web = manager.get_faction_web(matched_faction)
    player_standing = factions.get(matched_faction).standing.value

    console.print(f"\n[bold {THEME['primary']}]◈ {matched_faction.value.upper()} ◈[/bold {THEME['primary']}]")
    standing_color = _standing_color(player_standing)
    console.print(f"[{THEME['dim']}]Your standing:[/{THEME['dim']}] [{standing_color}]{player_standing}[/{standing_color}]\n")

    # Allies
    if web["allies"]:
        console.print(f"[bold {THEME['accent']}]ALLIES[/bold {THEME['accent']}]")
        for ally in web["allies"]:
            relation_bar = _relation_bar(ally["relation"])
            your_standing = _standing_color(ally["player_standing"])
            console.print(
                f"  [{THEME['accent']}]+[/{THEME['accent']}] {ally['faction']} "
                f"[{THEME['dim']}]{relation_bar}[/{THEME['dim']}] "
                f"[{your_standing}](you: {ally['player_standing']})[/{your_standing}]"
            )
        console.print()

    # Rivals
    if web["rivals"]:
        console.print(f"[bold {THEME['danger']}]RIVALS[/bold {THEME['danger']}]")
        for rival in web["rivals"]:
            relation_bar = _relation_bar(rival["relation"])
            your_standing = _standing_color(rival["player_standing"])
            console.print(
                f"  [{THEME['danger']}]−[/{THEME['danger']}] {rival['faction']} "
                f"[{THEME['dim']}]{relation_bar}[/{THEME['dim']}] "
                f"[{your_standing}](you: {rival['player_standing']})[/{your_standing}]"
            )
        console.print()

    # Neutral (if any significant ones)
    if web["neutral"]:
        console.print(f"[bold {THEME['dim']}]NEUTRAL[/bold {THEME['dim']}]")
        for neu in web["neutral"]:
            your_standing = _standing_color(neu["player_standing"])
            console.print(
                f"  [{THEME['dim']}]○[/{THEME['dim']}] {neu['faction']} "
                f"[{your_standing}](you: {neu['player_standing']})[/{your_standing}]"
            )
        console.print()

    # Cascade warning
    console.print(f"[{THEME['dim']}]─────────────────────────────────────[/{THEME['dim']}]")
    if web["allies"]:
        ally_names = [a["faction"] for a in web["allies"][:2]]
        console.print(
            f"[{THEME['dim']}]Help {matched_faction.value} → "
            f"{', '.join(ally_names)} may warm to you[/{THEME['dim']}]"
        )
    if web["rivals"]:
        rival_names = [r["faction"] for r in web["rivals"][:2]]
        console.print(
            f"[{THEME['dim']}]Help {matched_faction.value} → "
            f"{', '.join(rival_names)} may cool toward you[/{THEME['dim']}]"
        )

    return None


def _standing_color(standing: str) -> str:
    """Get color for a faction standing level."""
    colors = {
        "Allied": THEME["accent"],
        "Friendly": "green",
        "Neutral": THEME["dim"],
        "Unfriendly": THEME["warning"],
        "Hostile": THEME["danger"],
    }
    return colors.get(standing, THEME["dim"])


def _relation_bar(relation: int) -> str:
    """Create a small visual bar for faction-to-faction relation (-50 to +50)."""
    abs_rel = abs(relation)
    if abs_rel >= 40:
        return "████"
    elif abs_rel >= 30:
        return "███░"
    elif abs_rel >= 20:
        return "██░░"
    else:
        return "█░░░"


# -----------------------------------------------------------------------------
# Character Arc Commands
# -----------------------------------------------------------------------------

def cmd_arc(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """View and manage character arcs.

    Usage:
        /arc                - Show current arcs and any suggestions
        /arc detect         - Analyze history for new arc patterns
        /arc accept <type>  - Accept a suggested arc
        /arc reject <type>  - Reject a suggested arc
        /arc list           - List all arc types

    Arcs are recognition of play patterns, not restrictions.
    They provide narrative flavor and GM context.
    """
    from ..state.schema import ArcType, ArcStatus, ARC_PATTERNS

    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    if not manager.current.characters:
        console.print(f"[{THEME['warning']}]No character in campaign[/{THEME['warning']}]")
        return

    char = manager.current.characters[0]

    # No args: show current arcs and check for suggestions
    if not args:
        _show_arcs_status(manager, char)
        return

    subcommand = args[0].lower()

    if subcommand == "detect":
        _detect_arcs(manager, char)
    elif subcommand == "accept" and len(args) > 1:
        _accept_arc(manager, char, args[1])
    elif subcommand == "reject" and len(args) > 1:
        _reject_arc(manager, char, args[1])
    elif subcommand == "list":
        _list_arc_types()
    else:
        console.print(f"[{THEME['warning']}]Unknown subcommand: {subcommand}[/{THEME['warning']}]")
        console.print(f"[{THEME['dim']}]Use: /arc, /arc detect, /arc accept <type>, /arc reject <type>, /arc list[/{THEME['dim']}]")


def _show_arcs_status(manager: CampaignManager, char):
    """Show current arcs and any pending suggestions."""
    from ..state.schema import ArcStatus

    console.print(f"\n[bold {THEME['primary']}]◈ CHARACTER ARCS ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['dim']}]{char.name}'s emergent identity patterns[/{THEME['dim']}]\n")

    # Show accepted arcs
    accepted = [a for a in char.arcs if a.status == ArcStatus.ACCEPTED]
    if accepted:
        console.print(f"[bold {THEME['accent']}]ACTIVE ARCS[/bold {THEME['accent']}]")
        for arc in accepted:
            strength_bar = _arc_strength_bar(arc.strength)
            console.print(f"\n  [{THEME['accent']}]◆[/{THEME['accent']}] [bold]{arc.title}[/bold] ({arc.arc_type.value})")
            console.print(f"    [{THEME['dim']}]{arc.description}[/{THEME['dim']}]")
            console.print(f"    Strength: {strength_bar} [{THEME['dim']}]Reinforced {arc.times_reinforced}x[/{THEME['dim']}]")
            if arc.effects:
                console.print(f"    [{THEME['secondary']}]Effects:[/{THEME['secondary']}]")
                for effect in arc.effects[:2]:
                    console.print(f"      [{THEME['dim']}]• {effect}[/{THEME['dim']}]")
        console.print()

    # Show suggested arcs (detected but not accepted/rejected)
    suggested = [a for a in char.arcs if a.status == ArcStatus.SUGGESTED]
    if suggested:
        console.print(f"[bold {THEME['warning']}]SUGGESTED ARCS[/bold {THEME['warning']}]")
        for arc in suggested:
            strength_bar = _arc_strength_bar(arc.strength)
            console.print(f"\n  [{THEME['warning']}]?[/{THEME['warning']}] [bold]{arc.title}[/bold] ({arc.arc_type.value})")
            console.print(f"    [{THEME['dim']}]{arc.description}[/{THEME['dim']}]")
            console.print(f"    Strength: {strength_bar}")
            console.print(f"    [{THEME['dim']}]Use /arc accept {arc.arc_type.value} or /arc reject {arc.arc_type.value}[/{THEME['dim']}]")
        console.print()

    # Check for new suggestions
    suggestion = manager.suggest_arc()
    if suggestion and suggestion["arc_type"] not in [a.arc_type.value for a in char.arcs]:
        console.print(f"[bold {THEME['accent']}]NEW ARC DETECTED[/bold {THEME['accent']}]")
        _display_arc_suggestion(suggestion)

    if not accepted and not suggested and not suggestion:
        console.print(f"[{THEME['dim']}]No arcs detected yet.[/{THEME['dim']}]")
        console.print(f"[{THEME['dim']}]Play more sessions to develop patterns, or use /arc detect to analyze history.[/{THEME['dim']}]")


def _detect_arcs(manager: CampaignManager, char):
    """Run arc detection and show results."""
    console.print(f"\n[bold {THEME['primary']}]◈ ARC DETECTION ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['dim']}]Analyzing campaign history for patterns...[/{THEME['dim']}]\n")

    candidates = manager.detect_arcs()

    if not candidates:
        console.print(f"[{THEME['dim']}]No strong patterns detected yet.[/{THEME['dim']}]")
        console.print(f"[{THEME['dim']}]Keep making choices — arcs emerge from consistent behavior.[/{THEME['dim']}]")
        return

    # Filter out already-processed arcs
    existing_types = {a.arc_type.value for a in char.arcs}
    new_candidates = [c for c in candidates if c["arc_type"] not in existing_types]

    if new_candidates:
        console.print(f"[bold {THEME['accent']}]DETECTED PATTERNS[/bold {THEME['accent']}]\n")
        for candidate in sorted(new_candidates, key=lambda x: x["strength"], reverse=True):
            _display_arc_suggestion(candidate)

        console.print(f"[{THEME['dim']}]Use /arc accept <type> to embrace an arc[/{THEME['dim']}]")
        console.print(f"[{THEME['dim']}]Use /arc reject <type> to decline (won't suggest again)[/{THEME['dim']}]")
    else:
        console.print(f"[{THEME['dim']}]No new patterns detected.[/{THEME['dim']}]")
        console.print(f"[{THEME['dim']}]All detected arcs have been processed.[/{THEME['dim']}]")


def _display_arc_suggestion(suggestion: dict):
    """Display a single arc suggestion."""
    strength_bar = _arc_strength_bar(suggestion["strength"])

    console.print(f"  [{THEME['accent']}]◆[/{THEME['accent']}] [bold]{suggestion['title']}[/bold] ({suggestion['arc_type']})")
    console.print(f"    [{THEME['dim']}]{suggestion['description']}[/{THEME['dim']}]")
    console.print(f"    Strength: {strength_bar}")

    if suggestion.get("evidence"):
        console.print(f"    [{THEME['secondary']}]Evidence:[/{THEME['secondary']}]")
        for ev in suggestion["evidence"][:3]:
            console.print(f"      [{THEME['dim']}]• {ev[:60]}...[/{THEME['dim']}]" if len(ev) > 60 else f"      [{THEME['dim']}]• {ev}[/{THEME['dim']}]")

    if suggestion.get("effects"):
        console.print(f"    [{THEME['secondary']}]If accepted:[/{THEME['secondary']}]")
        for effect in suggestion["effects"][:2]:
            console.print(f"      [{THEME['dim']}]• {effect}[/{THEME['dim']}]")

    console.print()


def _accept_arc(manager: CampaignManager, char, arc_type: str):
    """Accept a detected arc."""
    from ..state.schema import ArcType

    # Validate arc type
    try:
        ArcType(arc_type)
    except ValueError:
        console.print(f"[{THEME['warning']}]Unknown arc type: {arc_type}[/{THEME['warning']}]")
        console.print(f"[{THEME['dim']}]Use /arc list to see available types[/{THEME['dim']}]")
        return

    arc = manager.accept_arc(char.id, arc_type)

    if arc:
        console.print(f"\n[bold {THEME['accent']}]◆ ARC ACCEPTED ◆[/bold {THEME['accent']}]")
        console.print(f"[bold]{arc.title}[/bold] ({arc.arc_type.value})")
        console.print(f"[{THEME['dim']}]{arc.description}[/{THEME['dim']}]\n")

        if arc.effects:
            console.print(f"[{THEME['secondary']}]This arc means:[/{THEME['secondary']}]")
            for effect in arc.effects:
                console.print(f"  [{THEME['dim']}]• {effect}[/{THEME['dim']}]")

        console.print(f"\n[{THEME['dim']}]The GM will weave this into your story.[/{THEME['dim']}]")
        console.print(f"[{THEME['dim']}]Your choices still define you — arcs recognize, not restrict.[/{THEME['dim']}]")
    else:
        console.print(f"[{THEME['warning']}]Could not accept arc: {arc_type}[/{THEME['warning']}]")


def _reject_arc(manager: CampaignManager, char, arc_type: str):
    """Reject a suggested arc."""
    from ..state.schema import ArcType

    # Validate arc type
    try:
        ArcType(arc_type)
    except ValueError:
        console.print(f"[{THEME['warning']}]Unknown arc type: {arc_type}[/{THEME['warning']}]")
        console.print(f"[{THEME['dim']}]Use /arc list to see available types[/{THEME['dim']}]")
        return

    success = manager.reject_arc(char.id, arc_type)

    if success:
        console.print(f"\n[{THEME['dim']}]Arc rejected: {arc_type}[/{THEME['dim']}]")
        console.print(f"[{THEME['dim']}]This pattern won't be suggested again.[/{THEME['dim']}]")
        console.print(f"[{THEME['dim']}]Your character's story remains unwritten.[/{THEME['dim']}]")
    else:
        console.print(f"[{THEME['warning']}]Could not reject arc: {arc_type}[/{THEME['warning']}]")


def _list_arc_types():
    """List all available arc types."""
    from ..state.schema import ArcType, ARC_PATTERNS

    console.print(f"\n[bold {THEME['primary']}]◈ ARC TYPES ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['dim']}]Patterns that can emerge from play[/{THEME['dim']}]\n")

    for arc_type in ArcType:
        pattern = ARC_PATTERNS.get(arc_type, {})
        title = pattern.get("title_templates", [arc_type.value])[0]
        desc = pattern.get("description", "")

        console.print(f"  [{THEME['accent']}]{arc_type.value}[/{THEME['accent']}] — {title}")
        console.print(f"    [{THEME['dim']}]{desc[:80]}...[/{THEME['dim']}]" if len(desc) > 80 else f"    [{THEME['dim']}]{desc}[/{THEME['dim']}]")
        console.print()


def _arc_strength_bar(strength: float) -> str:
    """Create a visual bar for arc strength (0.0-1.0)."""
    filled = int(strength * 5)
    empty = 5 - filled

    if strength >= 0.7:
        color = THEME["accent"]
    elif strength >= 0.5:
        color = THEME["secondary"]
    else:
        color = THEME["dim"]

    return f"[{color}]{'●' * filled}{'○' * empty}[/{color}]"


# -----------------------------------------------------------------------------
# Gameplay Commands
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# Session Commands
# -----------------------------------------------------------------------------

def cmd_debrief(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """End session with reflection prompts and summary."""
    from pathlib import Path

    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    session_num = manager.current.meta.session_count

    console.print(f"\n[bold {THEME['primary']}]◈ SESSION {session_num} DEBRIEF ◈[/bold {THEME['primary']}]")

    # Generate session summary BEFORE incrementing session count
    summary_data = manager.generate_session_summary(session_num)

    # Display session summary
    _display_session_summary(summary_data)

    # Reflection prompts
    console.print(f"\n[bold {THEME['secondary']}]REFLECTIONS[/bold {THEME['secondary']}]")
    console.print(f"[{THEME['dim']}]Answer what feels relevant. Skip with Enter.[/{THEME['dim']}]\n")

    cost = Prompt.ask(f"[{THEME['secondary']}]What did this cost you?[/{THEME['secondary']}]", default="")
    learned = Prompt.ask(f"[{THEME['secondary']}]What did you learn?[/{THEME['secondary']}]", default="")
    refuse = Prompt.ask(f"[{THEME['secondary']}]What would you refuse to do again?[/{THEME['secondary']}]", default="")

    # Build reflections object for storage
    reflections_obj = SessionReflection(
        cost=cost,
        learned=learned,
        would_refuse=refuse,
    )

    # Build summary text
    reflection_lines = []
    if cost:
        reflection_lines.append(f"Cost: {cost}")
    if learned:
        reflection_lines.append(f"Learned: {learned}")
    if refuse:
        reflection_lines.append(f"Would refuse: {refuse}")

    if reflection_lines:
        console.print(f"\n[{THEME['dim']}]Reflections noted.[/{THEME['dim']}]")
    summary_text = "; ".join(reflection_lines) if reflection_lines else "Session concluded"

    # Increment session count BEFORE end_session (so it logs correctly)
    manager.current.meta.session_count += 1

    # End session with proper logging
    entry = manager.end_session(
        summary=summary_text,
        reflections=reflections_obj if reflection_lines else None,
        reset_social_energy=True,
    )

    console.print(f"\n[{THEME['accent']}]Session {session_num} complete.[/{THEME['accent']}]")
    console.print(f"[{THEME['dim']}]Social energy reset. Chronicle updated. Campaign saved.[/{THEME['dim']}]")

    # Auto-save to wiki as daily note
    if manager.wiki and manager.wiki.is_enabled:
        reflections_dict = None
        if reflection_lines:
            reflections_dict = {
                "cost": cost,
                "learned": learned,
                "would_refuse": refuse,
            }
        wiki_path = manager.wiki.save_session_summary(summary_data, reflections_dict)
        if wiki_path:
            console.print(f"[{THEME['dim']}]Wiki daily note: {wiki_path.name}[/{THEME['dim']}]")

    # Offer to export summary
    export = Prompt.ask(f"\n[{THEME['dim']}]Export summary to markdown?[/{THEME['dim']}]", choices=["y", "n"], default="n")
    if export == "y":
        # Add reflections to summary for export
        if reflection_lines:
            summary_data["reflections"] = {
                "cost": cost,
                "learned": learned,
                "would_refuse": refuse,
            }

        markdown = manager.format_session_summary_markdown(summary_data)

        # Add reflections section to markdown
        if reflection_lines:
            markdown += "\n## PLAYER REFLECTIONS\n"
            if cost:
                markdown += f"- **Cost:** {cost}\n"
            if learned:
                markdown += f"- **Learned:** {learned}\n"
            if refuse:
                markdown += f"- **Would refuse:** {refuse}\n"

        # Save to file
        export_dir = Path("campaigns") / "summaries"
        export_dir.mkdir(parents=True, exist_ok=True)
        filename = f"session_{session_num}_{manager.current.meta.name.replace(' ', '_')}.md"
        filepath = export_dir / filename
        filepath.write_text(markdown, encoding="utf-8")
        console.print(f"[{THEME['accent']}]Saved:[/{THEME['accent']}] {filepath}")

    # Offer to wrap up with GM
    if agent.is_available and reflection_lines:
        wrap = Prompt.ask(f"\n[{THEME['dim']}]Ask the GM to narrate the aftermath?[/{THEME['dim']}]", choices=["y", "n"], default="n")
        if wrap == "y":
            prompt = (
                f"The session is ending. Here are the player's reflections:\n"
                f"{chr(10).join(reflection_lines)}\n\n"
                f"Provide a brief narrative wrap-up (2-3 paragraphs) that honors these reflections "
                f"and sets up threads for next session."
            )
            return ("gm_prompt", prompt)

    return None


def _display_session_summary(summary: dict):
    """Display session summary in terminal."""
    has_content = False

    # Key Choices / Hinges
    if summary.get("hinges"):
        has_content = True
        console.print(f"\n[bold {THEME['secondary']}]KEY CHOICES[/bold {THEME['secondary']}]")
        for hinge in summary["hinges"]:
            console.print(f"  [{THEME['danger']}]{g('hinge')}[/{THEME['danger']}] {hinge['choice']}")
            if hinge.get("what_shifted"):
                console.print(f"    [{THEME['dim']}]Shifted: {hinge['what_shifted']}[/{THEME['dim']}]")

    # Faction Changes
    if summary.get("faction_changes"):
        has_content = True
        console.print(f"\n[bold {THEME['secondary']}]FACTION STANDING CHANGES[/bold {THEME['secondary']}]")
        for change in summary["faction_changes"]:
            marker = f" [{THEME['accent']}]★[/{THEME['accent']}]" if change.get("is_permanent") else ""
            console.print(f"  [{THEME['warning']}]{g('faction')}[/{THEME['warning']}] {change['summary']}{marker}")

    # Threads Created
    if summary.get("threads_created"):
        has_content = True
        console.print(f"\n[bold {THEME['secondary']}]NEW CONSEQUENCE THREADS[/bold {THEME['secondary']}]")
        severity_style = {
            "major": THEME["danger"],
            "moderate": THEME["warning"],
            "minor": THEME["dim"],
        }
        for thread in summary["threads_created"]:
            sev = thread["severity"]
            color = severity_style.get(sev, THEME["dim"])
            console.print(f"  [{color}]{g('thread')}[/{color}] {thread['origin']}")
            console.print(f"    [{THEME['dim']}]Trigger: {thread['trigger']}[/{THEME['dim']}]")

    # Threads Resolved
    if summary.get("threads_resolved"):
        has_content = True
        console.print(f"\n[bold {THEME['secondary']}]RESOLVED THREADS[/bold {THEME['secondary']}]")
        for thread in summary["threads_resolved"]:
            console.print(f"  [{THEME['accent']}]{g('success')}[/{THEME['accent']}] {thread['summary']}")

    # NPCs Encountered
    if summary.get("npcs_encountered"):
        has_content = True
        console.print(f"\n[bold {THEME['secondary']}]NPCs ENCOUNTERED[/bold {THEME['secondary']}]")
        for npc in summary["npcs_encountered"]:
            disp = npc.get("disposition_change", 0)
            if disp > 0:
                change = f" [{THEME['accent']}]+{disp}[/{THEME['accent']}]"
            elif disp < 0:
                change = f" [{THEME['danger']}]{disp}[/{THEME['danger']}]"
            else:
                change = ""
            faction = f" [{THEME['dim']}]{npc['faction']}[/{THEME['dim']}]" if npc.get("faction") else ""
            console.print(f"  [{THEME['secondary']}]{g('npc')}[/{THEME['secondary']}] {npc['name']}{faction}{change}")

    if not has_content:
        console.print(f"\n[{THEME['dim']}]No significant events recorded this session.[/{THEME['dim']}]")


def cmd_summary(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """View summary of a session.

    Usage:
        /summary          - Summary of current/last session
        /summary <n>      - Summary of session n
        /summary export   - Export current session to markdown
    """
    from pathlib import Path

    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    # Parse arguments
    session_num = manager.current.meta.session_count
    export_mode = False

    for arg in args:
        if arg.lower() == "export":
            export_mode = True
        elif arg.isdigit():
            session_num = int(arg)

    # Generate summary
    summary_data = manager.generate_session_summary(session_num)

    if "error" in summary_data:
        console.print(f"[{THEME['warning']}]{summary_data['error']}[/{THEME['warning']}]")
        return

    console.print(f"\n[bold {THEME['primary']}]◈ SESSION {session_num} SUMMARY ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['dim']}]Campaign: {summary_data['campaign']}[/{THEME['dim']}]")

    _display_session_summary(summary_data)

    # Export if requested
    if export_mode:
        markdown = manager.format_session_summary_markdown(summary_data)
        export_dir = Path("campaigns") / "summaries"
        export_dir.mkdir(parents=True, exist_ok=True)
        filename = f"session_{session_num}_{manager.current.meta.name.replace(' ', '_')}.md"
        filepath = export_dir / filename
        filepath.write_text(markdown, encoding="utf-8")
        console.print(f"\n[{THEME['accent']}]Exported:[/{THEME['accent']}] {filepath}")

    return None


def cmd_history(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """View campaign chronicle with filtering and search.

    Usage:
        /history              - Show all (last 20 entries)
        /history hinges       - Filter to hinge moments only
        /history faction      - Filter to faction shifts only
        /history missions     - Filter to mission completions
        /history session 3    - Filter to specific session
        /history search <term> - Keyword search in summaries
    """
    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    history = list(manager.current.history)
    if not history:
        console.print(f"[{THEME['dim']}]No chronicle entries yet.[/{THEME['dim']}]")
        return

    # Type glyphs and colors - using existing glyphs from glyphs.py
    type_style = {
        HistoryType.MISSION: (g("briefing"), THEME["accent"], "MISSION"),
        HistoryType.HINGE: (g("hinge"), THEME["danger"], "HINGE"),
        HistoryType.FACTION_SHIFT: (g("triggered"), THEME["warning"], "FACTION"),
        HistoryType.CONSEQUENCE: (g("thread"), THEME["secondary"], "CONSEQUENCE"),
        HistoryType.CANON: (g("canon"), THEME["primary"], "CANON"),
    }

    # Type filter mapping (allow plural forms)
    type_map = {
        "mission": HistoryType.MISSION,
        "missions": HistoryType.MISSION,
        "hinge": HistoryType.HINGE,
        "hinges": HistoryType.HINGE,
        "faction": HistoryType.FACTION_SHIFT,
        "factions": HistoryType.FACTION_SHIFT,
        "consequence": HistoryType.CONSEQUENCE,
        "consequences": HistoryType.CONSEQUENCE,
        "canon": HistoryType.CANON,
    }

    # Parse arguments
    filter_type = None
    filter_session = None
    search_term = None
    title_suffix = ""

    if args:
        first_arg = args[0].lower()

        # Handle session filter: /history session 3
        if first_arg == "session" and len(args) >= 2:
            try:
                filter_session = int(args[1])
                title_suffix = f" - Session {filter_session}"
            except ValueError:
                console.print(f"[{THEME['warning']}]Invalid session number: {args[1]}[/{THEME['warning']}]")
                return

        # Handle search: /history search <term>
        elif first_arg == "search":
            if len(args) < 2:
                console.print(f"[{THEME['warning']}]Usage: /history search <term>[/{THEME['warning']}]")
                return
            search_term = " ".join(args[1:]).lower()
            title_suffix = f" - Search: '{search_term}'"

        # Handle type filter: /history hinges, /history faction, etc.
        elif first_arg in type_map:
            filter_type = type_map[first_arg]
            title_suffix = f" - {first_arg.title()}"

        else:
            # Unknown filter - show help
            console.print(f"[{THEME['warning']}]Unknown filter: {first_arg}[/{THEME['warning']}]")
            console.print()
            console.print(f"[{THEME['dim']}]Usage:[/{THEME['dim']}]")
            console.print(f"  /history              [{THEME['dim']}]Show all (last 20)[/{THEME['dim']}]")
            console.print(f"  /history hinges       [{THEME['dim']}]Filter to hinge moments[/{THEME['dim']}]")
            console.print(f"  /history faction      [{THEME['dim']}]Filter to faction shifts[/{THEME['dim']}]")
            console.print(f"  /history missions     [{THEME['dim']}]Filter to mission completions[/{THEME['dim']}]")
            console.print(f"  /history session 3    [{THEME['dim']}]Filter to specific session[/{THEME['dim']}]")
            console.print(f"  /history search <term> [{THEME['dim']}]Keyword search[/{THEME['dim']}]")
            return

    # Apply filters
    if filter_type:
        history = [h for h in history if h.type == filter_type]
    if filter_session is not None:
        history = [h for h in history if h.session == filter_session]
    if search_term:
        history = [h for h in history if search_term in h.summary.lower()]

    if not history:
        console.print(f"[{THEME['dim']}]No matching entries found.[/{THEME['dim']}]")
        return

    # Header
    console.print(f"\n[bold {THEME['primary']}]{g('briefing')} CAMPAIGN HISTORY{title_suffix.upper()} {g('briefing')}[/bold {THEME['primary']}]")
    console.print()

    # Group entries by session (most recent sessions first)
    from collections import defaultdict
    by_session: dict[int, list] = defaultdict(list)
    for entry in history:
        by_session[entry.session].append(entry)

    # Sort sessions descending, limit to last 20 entries total
    sorted_sessions = sorted(by_session.keys(), reverse=True)
    entries_shown = 0
    max_entries = 20

    for session_num in sorted_sessions:
        if entries_shown >= max_entries:
            break

        session_entries = by_session[session_num]
        # Sort entries within session by timestamp (oldest first within session)
        session_entries.sort(key=lambda e: e.timestamp)

        # Session header
        console.print(f"[bold {THEME['secondary']}]Session {session_num}[/bold {THEME['secondary']}]")

        for entry in session_entries:
            if entries_shown >= max_entries:
                break

            glyph, color, type_label = type_style.get(
                entry.type, (g("bullet"), THEME["dim"], "EVENT")
            )
            permanent_mark = " [bold]★[/bold]" if entry.is_permanent else ""

            # Entry line with glyph, type label, and summary
            console.print(
                f"  [{color}]{glyph}[/{color}] "
                f"[{THEME['dim']}][{type_label}][/{THEME['dim']}] "
                f"{entry.summary}{permanent_mark}"
            )

            # Show extra details for certain types
            if entry.type == HistoryType.HINGE and entry.hinge:
                console.print(f"    [{THEME['dim']}]Choice: {entry.hinge.choice}[/{THEME['dim']}]")
                if entry.hinge.what_shifted:
                    console.print(f"    [{THEME['dim']}]Shifted: {entry.hinge.what_shifted}[/{THEME['dim']}]")

            if entry.type == HistoryType.FACTION_SHIFT and entry.faction_shift:
                fs = entry.faction_shift
                console.print(
                    f"    [{THEME['dim']}]{fs.faction.value}: "
                    f"{fs.from_standing.value} {g('arrow')} {fs.to_standing.value}[/{THEME['dim']}]"
                )

            if entry.type == HistoryType.MISSION and entry.mission and entry.mission.reflections:
                r = entry.mission.reflections
                if r.cost:
                    console.print(f"    [{THEME['dim']}]Cost: {r.cost}[/{THEME['dim']}]")
                if r.learned:
                    console.print(f"    [{THEME['dim']}]Learned: {r.learned}[/{THEME['dim']}]")

            entries_shown += 1

        console.print()  # Blank line between sessions

    # Footer with counts and usage hints
    total = len(manager.current.history)
    filtered_total = len(history)

    if filtered_total > max_entries:
        console.print(
            f"[{THEME['dim']}]Showing {entries_shown} of {filtered_total} matching entries "
            f"(total: {total})[/{THEME['dim']}]"
        )
    elif filter_type or filter_session is not None or search_term:
        console.print(f"[{THEME['dim']}]Found {filtered_total} matching entries (total: {total})[/{THEME['dim']}]")

    console.print(f"[{THEME['dim']}]Filters: hinges, faction, missions, session <n>, search <term>[/{THEME['dim']}]")
    return None


def cmd_search(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Search campaign history for a term.

    Alias for /history search <term>
    """
    if not args:
        console.print(f"[{THEME['warning']}]Usage: /search <term>[/{THEME['warning']}]")
        console.print(f"[{THEME['dim']}]Example: /search Nexus[/{THEME['dim']}]")
        return

    # Delegate to cmd_history with search prefix
    return cmd_history(manager, agent, ["search"] + args)


def cmd_consequences(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """View pending consequences and dormant threads.

    Shows:
    - Active dormant threads waiting to trigger
    - Avoided situations that may come back
    - Recently resolved consequences
    """
    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    console.print(f"\n[bold {THEME['primary']}]◈ CONSEQUENCE THREADS ◈[/bold {THEME['primary']}]")

    current_session = manager.current.meta.session_count
    has_content = False

    # Severity styling
    severity_style = {
        "major": (THEME["danger"], "▲▲▲"),
        "moderate": (THEME["warning"], "▲▲○"),
        "minor": (THEME["dim"], "▲○○"),
    }

    # -------------------------------------------------------------------------
    # Active Dormant Threads
    # -------------------------------------------------------------------------
    threads = manager.current.dormant_threads
    if threads:
        has_content = True
        console.print(f"\n[bold {THEME['secondary']}]DORMANT THREADS[/bold {THEME['secondary']}]")
        console.print(f"[{THEME['dim']}]Consequences waiting to surface[/{THEME['dim']}]\n")

        for thread in threads:
            sev = thread.severity.value if hasattr(thread.severity, 'value') else thread.severity
            color, indicator = severity_style.get(sev, (THEME["dim"], "▲○○"))

            # Calculate age
            age = current_session - thread.created_session
            if age == 0:
                age_text = "this session"
            elif age == 1:
                age_text = "1 session ago"
            else:
                age_text = f"{age} sessions ago"

            console.print(f"[{color}]{indicator}[/{color}] [{THEME['accent']}]{thread.origin}[/{THEME['accent']}]")
            console.print(f"  [{THEME['dim']}]Created:[/{THEME['dim']}] {age_text} (S{thread.created_session})")
            console.print(f"  [{THEME['secondary']}]Trigger:[/{THEME['secondary']}] {thread.trigger_condition}")
            console.print(f"  [{color}]Consequence:[/{color}] {thread.consequence}")
            console.print()

    # -------------------------------------------------------------------------
    # Avoided Situations
    # -------------------------------------------------------------------------
    avoided = manager.current.avoided_situations
    unsurfaced = [a for a in avoided if not a.surfaced]
    if unsurfaced:
        has_content = True
        console.print(f"[bold {THEME['secondary']}]AVOIDED SITUATIONS[/bold {THEME['secondary']}]")
        console.print(f"[{THEME['dim']}]What you chose not to engage with[/{THEME['dim']}]\n")

        for situation in unsurfaced[:5]:  # Show up to 5
            sev = situation.severity.value if hasattr(situation.severity, 'value') else situation.severity
            color, indicator = severity_style.get(sev, (THEME["dim"], "▲○○"))

            age = current_session - situation.created_session
            age_text = f"S{situation.created_session}" if age > 0 else "this session"

            console.print(f"[{color}]{indicator}[/{color}] [{THEME['warning']}]{situation.situation}[/{THEME['warning']}]")
            console.print(f"  [{THEME['dim']}]At stake:[/{THEME['dim']}] {situation.what_was_at_stake}")
            console.print(f"  [{color}]May cause:[/{color}] {situation.potential_consequence}")
            console.print()

    # -------------------------------------------------------------------------
    # Recently Resolved (from history)
    # -------------------------------------------------------------------------
    resolved = [
        h for h in manager.current.history
        if h.type == HistoryType.CONSEQUENCE
    ]
    if resolved:
        has_content = True
        console.print(f"[bold {THEME['secondary']}]RESOLVED THREADS[/bold {THEME['secondary']}]")
        console.print(f"[{THEME['dim']}]Consequences that have surfaced[/{THEME['dim']}]\n")

        for entry in reversed(resolved[-5:]):  # Last 5
            ts = entry.timestamp.strftime("%Y-%m-%d")
            console.print(
                f"[{THEME['accent']}]{g('success')}[/{THEME['accent']}] "
                f"[{THEME['dim']}]S{entry.session} {ts}[/{THEME['dim']}] — "
                f"{entry.summary}"
            )

        if len(resolved) > 5:
            console.print(f"\n[{THEME['dim']}]...and {len(resolved) - 5} more. Use /history consequence to see all.[/{THEME['dim']}]")
        console.print()

    # -------------------------------------------------------------------------
    # Empty State
    # -------------------------------------------------------------------------
    if not has_content:
        console.print(f"\n[{THEME['dim']}]No pending consequences.[/{THEME['dim']}]")
        console.print(f"[{THEME['dim']}]Threads are created when choices have delayed effects.[/{THEME['dim']}]")

    # Summary stats
    thread_count = len(threads) if threads else 0
    avoided_count = len(unsurfaced) if unsurfaced else 0
    if thread_count or avoided_count:
        console.print(f"[{THEME['dim']}]─────────────────────────────────────[/{THEME['dim']}]")
        console.print(
            f"[{THEME['dim']}]Dormant: {thread_count} | "
            f"Avoided: {avoided_count}[/{THEME['dim']}]"
        )

    return None


# -----------------------------------------------------------------------------
# Context Debug Commands
# -----------------------------------------------------------------------------

def cmd_context(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Show context status.

    Usage:
        /context         - Show current context usage and strain tier
        /context debug   - Show detailed breakdown of all sections
    """
    from ..context import (
        PromptPacker, PackSection, PackInfo, SectionBudget, DEFAULT_BUDGETS,
    )
    from ..context.packer import StrainTier, format_strain_notice

    # Check if we have context info from agent
    pack_info = getattr(agent, "_last_pack_info", None)

    if "debug" in args:
        _show_context_debug(manager, agent, pack_info)
    else:
        _show_context_simple(manager, agent, pack_info)


def _show_context_simple(manager: CampaignManager, agent: SentinelAgent, pack_info: "PackInfo | None"):
    """Show simple context status view."""
    from ..context import DEFAULT_BUDGETS
    from ..context.packer import StrainTier, format_strain_notice

    console.print(f"\n[bold {THEME['primary']}]CONTEXT STATUS[/bold {THEME['primary']}]")

    if pack_info is None:
        # No pack info yet - show estimated usage
        console.print(f"[{THEME['dim']}]No context pack yet. Start a session to see usage.[/{THEME['dim']}]")
        console.print()

        # Show budget overview
        total_budget = sum(b.tokens for b in DEFAULT_BUDGETS.values())
        console.print(f"[{THEME['secondary']}]Total Budget:[/{THEME['secondary']}] {total_budget:,} tokens")
        console.print()
        console.print(f"[{THEME['dim']}]Use /context debug to see section budgets.[/{THEME['dim']}]")
        return

    # Context bar visualization
    bar = _format_context_bar(pack_info.pressure)
    strain_color = _get_strain_color(pack_info.strain_tier)

    console.print()
    console.print(f"  {bar}")
    console.print()
    console.print(
        f"  [{THEME['secondary']}]Tokens:[/{THEME['secondary']}] "
        f"{pack_info.total_tokens:,} / {pack_info.total_budget:,} "
        f"[{THEME['dim']}]({pack_info.pressure:.0%})[/{THEME['dim']}]"
    )

    # Strain tier indicator
    tier_name = pack_info.strain_tier.value.replace("_", " ").upper()
    console.print(
        f"  [{THEME['secondary']}]Strain:[/{THEME['secondary']}] "
        f"[{strain_color}]{tier_name}[/{strain_color}]"
    )

    # Strain explanation
    explanation = _get_strain_explanation(pack_info.strain_tier)
    console.print(f"  [{THEME['dim']}]{explanation}[/{THEME['dim']}]")

    # Warnings
    if pack_info.warnings:
        console.print()
        console.print(f"  [{THEME['warning']}]Warnings:[/{THEME['warning']}]")
        for warning in pack_info.warnings[:3]:  # Show up to 3
            console.print(f"    [{THEME['dim']}]- {warning}[/{THEME['dim']}]")

    # Recommendation for high strain
    if pack_info.strain_tier in (StrainTier.STRAIN_II, StrainTier.STRAIN_III):
        console.print()
        console.print(
            f"  [{THEME['accent']}]Tip:[/{THEME['accent']}] "
            f"Consider /debrief to consolidate and start fresh."
        )

    console.print()
    console.print(f"[{THEME['dim']}]Use /context debug for detailed breakdown.[/{THEME['dim']}]")


def _show_context_debug(manager: CampaignManager, agent: SentinelAgent, pack_info: "PackInfo | None"):
    """Show detailed context debug view."""
    from ..context import PackSection, DEFAULT_BUDGETS, SectionBudget
    from ..context.packer import StrainTier, format_strain_notice

    console.print(f"\n[bold {THEME['primary']}]CONTEXT DEBUG[/bold {THEME['primary']}]")

    # Section breakdown table
    table = Table(title="Section Breakdown", box=None)
    table.add_column("Section", style="cyan")
    table.add_column("Tokens", justify="right")
    table.add_column("Budget", justify="right")
    table.add_column("Usage", justify="right")
    table.add_column("Status")

    if pack_info:
        # Show actual pack info
        for section_content in pack_info.sections:
            section = section_content.section
            budget = DEFAULT_BUDGETS.get(section, SectionBudget(tokens=0))
            tokens = section_content.token_count
            budget_tokens = budget.tokens

            # Calculate usage percentage
            usage_pct = (tokens / budget_tokens * 100) if budget_tokens > 0 else 0

            # Determine status
            if section_content.truncated:
                orig = section_content.original_tokens or tokens
                status = f"[{THEME['warning']}]TRIMMED ({orig} -> {tokens})[/{THEME['warning']}]"
            elif usage_pct > 100:
                status = f"[{THEME['danger']}]OVER BUDGET[/{THEME['danger']}]"
            elif usage_pct > 80:
                status = f"[{THEME['warning']}]HIGH[/{THEME['warning']}]"
            elif tokens == 0:
                status = f"[{THEME['dim']}]EMPTY[/{THEME['dim']}]"
            else:
                status = f"[{THEME['accent']}]OK[/{THEME['accent']}]"

            table.add_row(
                section.value,
                f"{tokens:,}",
                f"{budget_tokens:,}",
                f"{usage_pct:.0f}%",
                status,
            )

        console.print(table)

        # Totals
        console.print()
        bar = _format_context_bar(pack_info.pressure)
        console.print(f"[bold]Total:[/bold] {bar}")
        console.print(
            f"  {pack_info.total_tokens:,} / {pack_info.total_budget:,} tokens "
            f"({pack_info.pressure:.1%})"
        )

        # Trimmed blocks info
        if pack_info.trimmed_blocks > 0:
            console.print()
            console.print(
                f"[{THEME['warning']}]Window blocks trimmed:[/{THEME['warning']}] "
                f"{pack_info.trimmed_blocks}"
            )

        # Scene recap if present
        if pack_info.scene_recap:
            console.print()
            console.print(f"[bold {THEME['secondary']}]Scene Recap Active:[/bold {THEME['secondary']}]")
            console.print(f"  [{THEME['dim']}]{pack_info.scene_recap[:100]}...[/{THEME['dim']}]")

    else:
        # Show budget defaults when no pack info
        for section in PackSection:
            budget = DEFAULT_BUDGETS.get(section, SectionBudget(tokens=0))
            required = "Required" if budget.required else "Optional"
            truncatable = "Yes" if budget.can_truncate else "No"
            table.add_row(
                section.value,
                "-",
                f"{budget.tokens:,}",
                "-",
                f"[{THEME['dim']}]{required}[/{THEME['dim']}]",
            )

        console.print(table)
        console.print()
        console.print(f"[{THEME['dim']}]No active context pack. Showing default budgets.[/{THEME['dim']}]")

    # Strain tier explanation
    console.print()
    console.print(f"[bold {THEME['secondary']}]Strain Tiers:[/bold {THEME['secondary']}]")

    current_tier = pack_info.strain_tier if pack_info else None

    for tier in StrainTier:
        tier_name = tier.value.replace("_", " ").upper()
        explanation = _get_strain_explanation(tier)
        thresholds = _get_strain_thresholds(tier)

        # Highlight current tier
        if tier == current_tier:
            marker = f"[{THEME['accent']}]>[/{THEME['accent']}]"
            style = THEME['accent']
        else:
            marker = " "
            style = THEME['dim']

        console.print(f"  {marker} [{style}]{tier_name}[/{style}] ({thresholds})")
        console.print(f"      [{THEME['dim']}]{explanation}[/{THEME['dim']}]")

    # Warnings
    if pack_info and pack_info.warnings:
        console.print()
        console.print(f"[bold {THEME['warning']}]Warnings:[/bold {THEME['warning']}]")
        for warning in pack_info.warnings:
            console.print(f"  [{THEME['dim']}]- {warning}[/{THEME['dim']}]")

    # Recommendations
    console.print()
    console.print(f"[bold {THEME['secondary']}]Recommendations:[/bold {THEME['secondary']}]")

    if pack_info is None:
        console.print(f"  [{THEME['dim']}]- Start a session with /start to generate context[/{THEME['dim']}]")
    elif pack_info.strain_tier == StrainTier.NORMAL:
        console.print(f"  [{THEME['accent']}]- Context healthy. Full features available.[/{THEME['accent']}]")
    elif pack_info.strain_tier == StrainTier.STRAIN_I:
        console.print(f"  [{THEME['dim']}]- Context under light strain. Consider natural pauses.[/{THEME['dim']}]")
        console.print(f"  [{THEME['dim']}]- Retrieval budget reduced automatically.[/{THEME['dim']}]")
    elif pack_info.strain_tier == StrainTier.STRAIN_II:
        console.print(f"  [{THEME['warning']}]- Consider /debrief soon to consolidate memory.[/{THEME['warning']}]")
        console.print(f"  [{THEME['dim']}]- Auto-retrieval disabled to preserve space.[/{THEME['dim']}]")
    else:  # STRAIN_III
        console.print(f"  [{THEME['danger']}]- /debrief strongly recommended![/{THEME['danger']}]")
        console.print(f"  [{THEME['dim']}]- Working from minimal context only.[/{THEME['dim']}]")


def _format_context_bar(pressure: float, width: int = 30) -> str:
    """Create a visual bar for context pressure."""
    filled = int(pressure * width)
    filled = min(filled, width)  # Cap at 100%
    empty = width - filled

    # Color based on pressure
    if pressure < 0.70:
        color = THEME['accent']
    elif pressure < 0.85:
        color = THEME['warning']
    else:
        color = THEME['danger']

    bar_char = "█"
    empty_char = "░"

    return f"[{color}]{bar_char * filled}[/{color}][{THEME['dim']}]{empty_char * empty}[/{THEME['dim']}]"


def _get_strain_color(tier: "StrainTier") -> str:
    """Get color for a strain tier."""
    from ..context.packer import StrainTier

    colors = {
        StrainTier.NORMAL: THEME['accent'],
        StrainTier.STRAIN_I: THEME['secondary'],
        StrainTier.STRAIN_II: THEME['warning'],
        StrainTier.STRAIN_III: THEME['danger'],
    }
    return colors.get(tier, THEME['dim'])


def _get_strain_explanation(tier: "StrainTier") -> str:
    """Get explanation for a strain tier."""
    from ..context.packer import StrainTier

    explanations = {
        StrainTier.NORMAL: "Full context available. No compression needed.",
        StrainTier.STRAIN_I: "Context reduced. Older blocks condensed, minimal retrieval.",
        StrainTier.STRAIN_II: "Working from scene recap. No auto-retrieval.",
        StrainTier.STRAIN_III: "Context critical. Consider /debrief to consolidate.",
    }
    return explanations.get(tier, "Unknown strain level.")


def _get_strain_thresholds(tier: "StrainTier") -> str:
    """Get threshold description for a strain tier."""
    from ..context.packer import StrainTier

    thresholds = {
        StrainTier.NORMAL: "<70%",
        StrainTier.STRAIN_I: "70-85%",
        StrainTier.STRAIN_II: "85-95%",
        StrainTier.STRAIN_III: ">95%",
    }
    return thresholds.get(tier, "?")


# -----------------------------------------------------------------------------
# Memory / Timeline Commands
# -----------------------------------------------------------------------------

def cmd_timeline(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Search campaign memory via memvid.

    Usage:
        /timeline              - Show recent turns and hinges
        /timeline <query>      - Semantic search across history
        /timeline hinges       - Show all hinge moments
        /timeline session <n>  - Show events from session n
        /timeline npc <name>   - Show interactions with an NPC

    Note: This is "active" retrieval - player explicitly requested it.
    Results bypass strain tier restrictions (not auto-injected into prompt).
    """
    from ..state import MEMVID_AVAILABLE

    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    if not MEMVID_AVAILABLE:
        console.print(f"[{THEME['warning']}]Memvid not installed. Run: pip install memvid-sdk[/{THEME['warning']}]")
        return

    if not manager.memvid or not manager.memvid.is_enabled:
        console.print(f"[{THEME['warning']}]Memvid not enabled for this campaign[/{THEME['warning']}]")
        return

    memvid = manager.memvid

    # Parse subcommands
    # All /timeline queries are "active" retrieval - player explicitly requested
    # them, so they bypass strain tier restrictions
    if not args:
        # Default: show recent activity
        _show_timeline_overview(manager, memvid)
        return

    subcommand = args[0].lower()

    if subcommand == "hinges":
        _show_hinges(memvid)
    elif subcommand == "session" and len(args) > 1:
        try:
            session_num = int(args[1])
            _show_session_timeline(memvid, session_num)
        except ValueError:
            console.print(f"[{THEME['danger']}]Session number must be an integer[/{THEME['danger']}]")
    elif subcommand == "npc" and len(args) > 1:
        npc_name = " ".join(args[1:])
        _show_npc_memory(manager, memvid, npc_name)
    else:
        # Treat as semantic search query
        # Use unified retriever's query_active() when available for combined results
        query = " ".join(args)
        if agent.unified_retriever:
            # Active retrieval via unified retriever (ignores strain tier)
            _search_timeline_unified(agent, query)
        else:
            # Fallback to direct memvid search
            _search_timeline(memvid, query)


def _show_timeline_overview(manager: CampaignManager, memvid):
    """Show overview of recent campaign activity."""
    console.print(f"\n[bold {THEME['primary']}]◈ CAMPAIGN TIMELINE ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['dim']}]Campaign: {manager.current.meta.name}[/{THEME['dim']}]")
    console.print(f"[{THEME['dim']}]Sessions: {manager.current.meta.session_count}[/{THEME['dim']}]\n")

    # Show recent hinges
    hinges = memvid.get_hinges(limit=5)
    if hinges:
        console.print(f"[bold {THEME['secondary']}]Recent Hinge Moments[/bold {THEME['secondary']}]")
        for h in hinges:
            session = h.get("session", "?")
            choice = h.get("choice", "Unknown choice")[:60]
            console.print(f"  [{THEME['danger']}]{g('hinge')}[/{THEME['danger']}] S{session}: {choice}...")
        console.print()

    # Show active threads
    threads = memvid.get_active_threads()
    if threads:
        console.print(f"[bold {THEME['secondary']}]Dormant Threads[/bold {THEME['secondary']}]")
        for t in threads[:5]:
            severity = t.get("severity", "moderate")
            origin = t.get("origin", "Unknown")[:50]
            severity_color = {
                "major": THEME['danger'],
                "moderate": THEME['warning'],
                "minor": THEME['dim'],
            }.get(severity, THEME['dim'])
            console.print(f"  [{severity_color}]{g('thread')}[/{severity_color}] {origin}...")
        console.print()

    # Show usage hints
    console.print(f"[{THEME['dim']}]Commands:[/{THEME['dim']}]")
    console.print(f"  [{THEME['accent']}]/timeline <query>[/{THEME['accent']}]      - Search history")
    console.print(f"  [{THEME['accent']}]/timeline hinges[/{THEME['accent']}]       - All hinge moments")
    console.print(f"  [{THEME['accent']}]/timeline session <n>[/{THEME['accent']}]  - Events from session n")
    console.print(f"  [{THEME['accent']}]/timeline npc <name>[/{THEME['accent']}]   - NPC interactions")


def _show_hinges(memvid):
    """Show all hinge moments."""
    console.print(f"\n[bold {THEME['primary']}]◈ HINGE MOMENTS ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['dim']}]Irreversible choices that shaped this story[/{THEME['dim']}]\n")

    hinges = memvid.get_hinges(limit=20)
    if not hinges:
        console.print(f"[{THEME['dim']}]No hinge moments recorded yet.[/{THEME['dim']}]")
        return

    for h in hinges:
        session = h.get("session", "?")
        situation = h.get("situation", "")[:80]
        choice = h.get("choice", "Unknown")
        reasoning = h.get("reasoning", "")
        what_shifted = h.get("what_shifted", "")

        console.print(f"[bold {THEME['danger']}]{g('hinge')} Session {session}[/bold {THEME['danger']}]")
        if situation:
            console.print(f"  [{THEME['dim']}]Situation:[/{THEME['dim']}] {situation}...")
        console.print(f"  [{THEME['secondary']}]Choice:[/{THEME['secondary']}] {choice}")
        if reasoning:
            console.print(f"  [{THEME['dim']}]Reasoning:[/{THEME['dim']}] {reasoning[:100]}...")
        if what_shifted:
            console.print(f"  [{THEME['accent']}]Shifted:[/{THEME['accent']}] {what_shifted}")
        console.print()


def _show_session_timeline(memvid, session_num: int):
    """Show all events from a specific session."""
    console.print(f"\n[bold {THEME['primary']}]◈ SESSION {session_num} TIMELINE ◈[/bold {THEME['primary']}]\n")

    frames = memvid.get_session_timeline(session_num)
    if not frames:
        console.print(f"[{THEME['dim']}]No events found for session {session_num}.[/{THEME['dim']}]")
        return

    # Group by type
    type_icons = {
        "turn_state": g("phase"),
        "hinge_moment": g("hinge"),
        "npc_interaction": g("npc"),
        "faction_shift": g("faction"),
        "dormant_thread": g("thread"),
    }

    for frame in frames:
        frame_type = frame.get("type", "unknown")
        icon = type_icons.get(frame_type, "•")
        timestamp = frame.get("timestamp", "")[:10]

        if frame_type == "turn_state":
            turn = frame.get("turn", "?")
            summary = frame.get("narrative_summary", "")[:60]
            console.print(f"  [{THEME['secondary']}]{icon}[/{THEME['secondary']}] Turn {turn}: {summary or '[no summary]'}")

        elif frame_type == "hinge_moment":
            choice = frame.get("choice", "")[:60]
            console.print(f"  [{THEME['danger']}]{icon}[/{THEME['danger']}] HINGE: {choice}...")

        elif frame_type == "npc_interaction":
            npc = frame.get("npc_name", "Unknown")
            action = frame.get("player_action", "")[:40]
            console.print(f"  [{THEME['accent']}]{icon}[/{THEME['accent']}] {npc}: {action}...")

        elif frame_type == "faction_shift":
            faction = frame.get("faction", "Unknown")
            from_s = frame.get("from_standing", "")
            to_s = frame.get("to_standing", "")
            console.print(f"  [{THEME['warning']}]{icon}[/{THEME['warning']}] {faction}: {from_s} → {to_s}")

        elif frame_type == "dormant_thread":
            origin = frame.get("origin", "")[:50]
            console.print(f"  [{THEME['dim']}]{icon}[/{THEME['dim']}] Thread queued: {origin}...")


def _show_npc_memory(manager: CampaignManager, memvid, npc_name: str):
    """Show interactions with a specific NPC."""
    console.print(f"\n[bold {THEME['primary']}]◈ NPC MEMORY: {npc_name.upper()} ◈[/bold {THEME['primary']}]\n")

    # First, try to find NPC by name in current campaign to get ID
    npc = None
    npc_id = None
    if manager.current:
        for n in manager.current.npcs.active + manager.current.npcs.dormant:
            if npc_name.lower() in n.name.lower():
                npc = n
                npc_id = n.id
                break

    if npc:
        console.print(f"[{THEME['dim']}]NPC: {npc.name}[/{THEME['dim']}]")
        if npc.faction:
            console.print(f"[{THEME['dim']}]Faction: {npc.faction.value}[/{THEME['dim']}]")
        console.print(f"[{THEME['dim']}]Disposition: {npc.disposition.value}[/{THEME['dim']}]\n")

        interactions = memvid.get_npc_history(npc_id, limit=15)
    else:
        # Search by name in memvid
        console.print(f"[{THEME['dim']}]Searching for interactions with '{npc_name}'...[/{THEME['dim']}]\n")
        interactions = memvid.query(f"npc_name:{npc_name}", top_k=15)

    if not interactions:
        console.print(f"[{THEME['dim']}]No recorded interactions found.[/{THEME['dim']}]")
        return

    for inter in interactions:
        session = inter.get("session", "?")
        action = inter.get("player_action", "")
        reaction = inter.get("npc_reaction", "")
        disp_change = inter.get("disposition_change", 0)

        console.print(f"[bold {THEME['secondary']}]Session {session}[/bold {THEME['secondary']}]")
        if action:
            console.print(f"  [{THEME['dim']}]You:[/{THEME['dim']}] {action[:80]}...")
        if reaction:
            console.print(f"  [{THEME['accent']}]They:[/{THEME['accent']}] {reaction[:80]}...")
        if disp_change != 0:
            sign = "+" if disp_change > 0 else ""
            color = THEME['accent'] if disp_change > 0 else THEME['danger']
            console.print(f"  [{color}]Disposition: {sign}{disp_change}[/{color}]")
        console.print()


def _search_timeline(memvid, query: str):
    """Semantic search across campaign history."""
    console.print(f"\n[bold {THEME['primary']}]◈ TIMELINE SEARCH ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['dim']}]Query: {query}[/{THEME['dim']}]\n")

    results = memvid.query(query, top_k=10)
    if not results:
        console.print(f"[{THEME['dim']}]No matches found.[/{THEME['dim']}]")
        return

    type_icons = {
        "turn_state": (g("phase"), THEME['secondary']),
        "hinge_moment": (g("hinge"), THEME['danger']),
        "npc_interaction": (g("npc"), THEME['accent']),
        "faction_shift": (g("faction"), THEME['warning']),
        "dormant_thread": (g("thread"), THEME['dim']),
    }

    for result in results:
        frame_type = result.get("type", "unknown")
        icon, color = type_icons.get(frame_type, ("•", THEME['dim']))
        session = result.get("session", "?")

        # Build summary based on type
        if frame_type == "turn_state":
            summary = result.get("narrative_summary", "Turn state")
        elif frame_type == "hinge_moment":
            summary = result.get("choice", "Hinge moment")
        elif frame_type == "npc_interaction":
            npc = result.get("npc_name", "Unknown")
            action = result.get("player_action", "")[:40]
            summary = f"{npc}: {action}"
        elif frame_type == "faction_shift":
            faction = result.get("faction", "Unknown")
            summary = f"{faction} standing changed"
        elif frame_type == "dormant_thread":
            summary = result.get("origin", "Thread")[:50]
        else:
            summary = str(result)[:60]

        console.print(f"  [{color}]{icon}[/{color}] S{session}: {summary}...")

    console.print(f"\n[{THEME['dim']}]Found {len(results)} results.[/{THEME['dim']}]")


def _search_timeline_unified(agent: SentinelAgent, query: str):
    """
    Semantic search using unified retriever's query_active().

    This is "active" retrieval - player explicitly requested it via /timeline.
    Bypasses strain tier restrictions and shows both lore and campaign results.
    """
    console.print(f"\n[bold {THEME['primary']}]◈ TIMELINE SEARCH ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['dim']}]Query: {query}[/{THEME['dim']}]\n")

    # Use query_active() to bypass strain restrictions
    unified_result = agent.unified_retriever.query_active(topic=query)

    has_results = False

    # Show campaign history (primary for /timeline)
    if unified_result.has_campaign:
        has_results = True
        console.print(f"[bold {THEME['secondary']}]Campaign History[/bold {THEME['secondary']}]")

        type_icons = {
            "turn_state": (g("phase"), THEME['secondary']),
            "hinge_moment": (g("hinge"), THEME['danger']),
            "npc_interaction": (g("npc"), THEME['accent']),
            "faction_shift": (g("faction"), THEME['warning']),
            "dormant_thread": (g("thread"), THEME['dim']),
        }

        for result in unified_result.campaign[:10]:
            frame_type = result.get("type", "unknown")
            icon, color = type_icons.get(frame_type, ("•", THEME['dim']))
            session = result.get("session", "?")

            # Build summary based on type
            if frame_type == "turn_state":
                summary = result.get("narrative_summary", "Turn state")
            elif frame_type == "hinge_moment":
                summary = result.get("choice", "Hinge moment")
            elif frame_type == "npc_interaction":
                npc = result.get("npc_name", "Unknown")
                action = result.get("player_action", "")[:40]
                summary = f"{npc}: {action}"
            elif frame_type == "faction_shift":
                faction = result.get("faction", "Unknown")
                summary = f"{faction} standing changed"
            elif frame_type == "dormant_thread":
                summary = result.get("origin", "Thread")[:50]
            else:
                summary = str(result)[:60]

            console.print(f"  [{color}]{icon}[/{color}] S{session}: {summary}...")

        console.print(f"\n[{THEME['dim']}]Found {len(unified_result.campaign)} campaign results.[/{THEME['dim']}]")

    # Show relevant lore (bonus for unified search)
    if unified_result.has_lore:
        has_results = True
        console.print(f"\n[bold {THEME['secondary']}]Related Lore[/bold {THEME['secondary']}]")
        for hit in unified_result.lore[:2]:
            title = hit.get("title", "Unknown")
            section = hit.get("section", "")
            content = hit.get("content", "")[:80]
            console.print(f"  [{THEME['accent']}]►[/{THEME['accent']}] {title}")
            if section:
                console.print(f"    [{THEME['dim']}]§ {section}[/{THEME['dim']}]")
            console.print(f"    [italic]{content}...[/italic]")

    if not has_results:
        console.print(f"[{THEME['dim']}]No matches found.[/{THEME['dim']}]")


# -----------------------------------------------------------------------------
# Wiki Commands
# -----------------------------------------------------------------------------

def cmd_wiki(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """View campaign wiki timeline and page overlays.

    Usage:
        /wiki              - Show campaign event timeline
        /wiki <page>       - Show overlay for a specific page (e.g., Nexus)

    The wiki timeline shows significant campaign events:
    - Hinge moments (irreversible choices)
    - Faction standing changes
    - Dormant threads created

    Events are auto-logged during play and persist across sessions.
    """
    from .shared import get_wiki_timeline, get_wiki_page_overlay

    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    # Determine wiki_dir from manager if available
    wiki_dir = getattr(manager, '_wiki_dir', 'wiki')

    if not args:
        # Show timeline
        result = get_wiki_timeline(manager, wiki_dir=str(wiki_dir))

        if not result:
            console.print(f"[{THEME['warning']}]Could not load wiki timeline[/{THEME['warning']}]")
            return

        console.print(f"\n[bold {THEME['primary']}]◈ CAMPAIGN WIKI ◈[/bold {THEME['primary']}]")
        console.print(f"[{THEME['dim']}]{result['campaign_name']} ({result['campaign_id'][:8]})[/{THEME['dim']}]\n")

        if not result['events']:
            console.print(f"[{THEME['dim']}]{result.get('message', 'No events recorded yet.')}[/{THEME['dim']}]")
            console.print(f"\n[{THEME['dim']}]Events are auto-logged during play:[/{THEME['dim']}]")
            console.print(f"  [{THEME['secondary']}]{g('bullet')}[/{THEME['secondary']}] Hinge moments (irreversible choices)")
            console.print(f"  [{THEME['secondary']}]{g('bullet')}[/{THEME['secondary']}] Faction standing changes")
            console.print(f"  [{THEME['secondary']}]{g('bullet')}[/{THEME['secondary']}] Dormant threads queued")
            return

        # Show events grouped by type
        console.print(f"[bold {THEME['accent']}]Timeline ({result['event_count']} events)[/bold {THEME['accent']}]\n")

        for event in result['events']:
            # Color-code by type
            if "[HINGE]" in event:
                color = THEME['danger']
                icon = g('hinge')
            elif "[FACTION]" in event:
                color = THEME['accent']
                icon = g('faction')
            elif "[THREAD]" in event:
                color = THEME['warning']
                icon = g('thread')
            elif "[NPC]" in event:
                color = THEME['secondary']
                icon = g('npc')
            else:
                color = THEME['text']
                icon = g('bullet')

            console.print(f"  [{color}]{icon}[/{color}] {event}")

        console.print(f"\n[{THEME['dim']}]Use /wiki <page> to see campaign changes to a specific page[/{THEME['dim']}]")
        return

    # Show specific page overlay
    page = " ".join(args)
    result = get_wiki_page_overlay(manager, page, wiki_dir=str(wiki_dir))

    if not result:
        console.print(f"[{THEME['warning']}]Could not load wiki page[/{THEME['warning']}]")
        return

    if not result['exists']:
        console.print(f"[{THEME['dim']}]No campaign overlay exists for '{page}'[/{THEME['dim']}]")
        console.print(f"[{THEME['dim']}]Overlays are created when campaign events affect a page.[/{THEME['dim']}]")
        return

    console.print(f"\n[bold {THEME['primary']}]◈ WIKI OVERLAY: {page} ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['dim']}]Campaign-specific additions to canon[/{THEME['dim']}]\n")

    # Display content with markdown-like formatting
    from rich.markdown import Markdown
    from rich.panel import Panel

    md = Markdown(result['content'])
    console.print(Panel(md, border_style=THEME['dim']))


# -----------------------------------------------------------------------------
# Simulation Commands
# -----------------------------------------------------------------------------

def cmd_simulate(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Run simulations and explore hypothetical scenarios.

    Usage:
        /simulate [turns] [persona]     - Run AI vs AI simulation
        /simulate preview <action>      - Preview consequences of an action
        /simulate npc <name> <approach> - Predict NPC reaction
        /simulate whatif <query>        - Explore alternate past choices

    Personas: cautious, opportunist, principled, chaotic
    """
    if not args:
        _show_simulate_help()
        return

    subcommand = args[0].lower()

    # Route to subcommand handlers
    if subcommand == "preview":
        return _simulate_preview(manager, agent, args[1:])
    elif subcommand == "npc":
        return _simulate_npc(manager, agent, args[1:])
    elif subcommand == "whatif":
        return _simulate_whatif(manager, agent, args[1:])
    else:
        # Default: run AI vs AI simulation
        return _simulate_run(manager, agent, args)


def _show_simulate_help():
    """Show simulate command help."""
    console.print(f"\n[bold {THEME['primary']}]◈ SIMULATION MODES ◈[/bold {THEME['primary']}]\n")

    console.print(f"[bold {THEME['accent']}]/simulate [turns] [persona][/bold {THEME['accent']}]")
    console.print(f"  [{THEME['dim']}]Run AI vs AI simulation for testing[/{THEME['dim']}]")
    console.print(f"  [{THEME['dim']}]Personas: cautious, opportunist, principled, chaotic[/{THEME['dim']}]\n")

    console.print(f"[bold {THEME['accent']}]/simulate preview <action>[/bold {THEME['accent']}]")
    console.print(f"  [{THEME['dim']}]Preview potential consequences without committing[/{THEME['dim']}]")
    console.print(f"  [{THEME['dim']}]Example: /simulate preview I betray the Syndicate contact[/{THEME['dim']}]\n")

    console.print(f"[bold {THEME['accent']}]/simulate npc <name> <approach>[/bold {THEME['accent']}]")
    console.print(f"  [{THEME['dim']}]Predict how an NPC will react to an approach[/{THEME['dim']}]")
    console.print(f"  [{THEME['dim']}]Example: /simulate npc Reeves ask for weapons[/{THEME['dim']}]\n")

    console.print(f"[bold {THEME['accent']}]/simulate whatif <query>[/bold {THEME['accent']}]")
    console.print(f"  [{THEME['dim']}]Explore how past choices might have gone differently[/{THEME['dim']}]")
    console.print(f"  [{THEME['dim']}]Example: /simulate whatif helped Ember instead[/{THEME['dim']}]\n")


def _simulate_run(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Run AI vs AI simulation (original behavior)."""
    from pathlib import Path
    from ..simulation import AIPlayer, PERSONAS, run_simulation, SimulationTranscript
    from ..simulation.runner import create_simulation_character

    # Parse arguments
    turns = 5  # default
    persona = "cautious"  # default

    for arg in args:
        if arg.isdigit():
            turns = int(arg)
        elif arg in PERSONAS:
            persona = arg

    # Validate backend
    if not agent.client:
        console.print("[red]No LLM backend available. Cannot run simulation.[/red]")
        return

    # Ensure campaign exists
    if not manager.current:
        console.print(f"[{THEME['secondary']}]Creating simulation campaign...[/{THEME['secondary']}]")
        manager.create_campaign(f"Simulation ({persona})")

    # Ensure character exists
    if not manager.current.characters:
        console.print(f"[{THEME['secondary']}]Creating simulation character...[/{THEME['secondary']}]")
        character = create_simulation_character(manager, persona)
    else:
        character = manager.current.characters[0]

    # Show simulation header
    console.print()
    console.print(Panel(
        f"[{THEME['accent']}]{g('moment')} SIMULATION[/{THEME['accent']}]: "
        f"{turns} turns, persona: [bold]{persona}[/bold]\n"
        f"Character: {character.name} ({character.background.value})",
        border_style=THEME['primary'],
    ))
    console.print()

    # Create AI player
    player = AIPlayer(agent.client, persona=persona, character=character)

    # Run simulation with progress display
    console.print(f"[{THEME['secondary']}]Running simulation...[/{THEME['secondary']}]")
    console.print()

    try:
        transcript = run_simulation(agent, player, turns, manager)
    except Exception as e:
        console.print(f"[red]Simulation error: {e}[/red]")
        return

    # Display transcript
    _display_simulation_transcript(transcript)

    # Save transcript
    simulations_dir = Path("simulations")
    filepath = transcript.save(simulations_dir)
    console.print(f"\n[{THEME['secondary']}]Transcript saved: {filepath}[/{THEME['secondary']}]")

    # Save campaign state
    manager.save_campaign()


def _simulate_preview(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Preview consequences of a proposed action without committing."""
    from .shared import simulate_preview

    if not args:
        console.print(f"[{THEME['warning']}]Usage: /simulate preview <action>[/{THEME['warning']}]")
        console.print(f"[{THEME['dim']}]Example: /simulate preview I betray the Syndicate contact[/{THEME['dim']}]")
        return

    if not agent.client:
        console.print(f"[{THEME['warning']}]No LLM backend available[/{THEME['warning']}]")
        return

    action = " ".join(args)

    console.print(f"\n[bold {THEME['primary']}]◈ ACTION PREVIEW ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['dim']}]Proposed action:[/{THEME['dim']}] {action}\n")

    with console.status(f"[{THEME['dim']}]Analyzing potential consequences...[/{THEME['dim']}]"):
        result = simulate_preview(manager, agent.client, action)

    if not result.success:
        console.print(f"[{THEME['warning']}]{result.error}[/{THEME['warning']}]")
        return

    console.print(Panel(
        result.analysis,
        title=f"[bold {THEME['warning']}]CONSEQUENCE PREVIEW[/bold {THEME['warning']}]",
        border_style=THEME['warning'],
    ))

    console.print(f"\n[{THEME['dim']}]This is speculative. Actual outcomes depend on dice and GM narration.[/{THEME['dim']}]")
    console.print(f"[{THEME['dim']}]No changes have been made to your campaign.[/{THEME['dim']}]")


def _simulate_npc(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Predict how an NPC will react to a proposed approach."""
    from .shared import simulate_npc, get_npc_details

    if len(args) < 2:
        console.print(f"[{THEME['warning']}]Usage: /simulate npc <name> <approach>[/{THEME['warning']}]")
        console.print(f"[{THEME['dim']}]Example: /simulate npc Reeves ask for weapons shipment[/{THEME['dim']}]")
        return

    if not agent.client:
        console.print(f"[{THEME['warning']}]No LLM backend available[/{THEME['warning']}]")
        return

    npc_query = args[0]
    approach = " ".join(args[1:])

    # Get NPC details for header display
    npc_info = get_npc_details(manager, npc_query)
    if not npc_info:
        console.print(f"[{THEME['warning']}]No NPC found matching '{npc_query}'[/{THEME['warning']}]")
        return

    # Show header
    console.print(f"\n[bold {THEME['primary']}]◈ NPC REACTION PREVIEW ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['secondary']}]NPC:[/{THEME['secondary']}] {npc_info['name']}")
    if npc_info.get('faction'):
        console.print(f"[{THEME['secondary']}]Faction:[/{THEME['secondary']}] {npc_info['faction']}")
    console.print(f"[{THEME['secondary']}]Disposition:[/{THEME['secondary']}] {npc_info['disposition']}")
    console.print(f"[{THEME['secondary']}]Personal standing:[/{THEME['secondary']}] {npc_info['personal_standing']:+d}")
    console.print(f"\n[{THEME['dim']}]Proposed approach:[/{THEME['dim']}] {approach}\n")

    with console.status(f"[{THEME['dim']}]Predicting {npc_info['name']}'s reaction...[/{THEME['dim']}]"):
        result = simulate_npc(manager, agent.client, npc_query, approach)

    if not result.success:
        console.print(f"[{THEME['warning']}]{result.error}[/{THEME['warning']}]")
        return

    console.print(Panel(
        result.analysis,
        title=f"[bold {THEME['accent']}]{npc_info['name'].upper()} — REACTION PREDICTION[/bold {THEME['accent']}]",
        border_style=THEME['accent'],
    ))

    console.print(f"\n[{THEME['dim']}]This is speculative based on established NPC traits.[/{THEME['dim']}]")
    console.print(f"[{THEME['dim']}]Actual reactions depend on approach, dice, and GM interpretation.[/{THEME['dim']}]")


def _simulate_whatif(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Explore how past choices might have gone differently."""
    from .shared import simulate_whatif

    if not args:
        console.print(f"[{THEME['warning']}]Usage: /simulate whatif <query>[/{THEME['warning']}]")
        console.print(f"[{THEME['dim']}]Example: /simulate whatif helped Ember instead of refusing[/{THEME['dim']}]")
        console.print(f"[{THEME['dim']}]Example: /simulate whatif accepted the enhancement[/{THEME['dim']}]")
        return

    if not agent.client:
        console.print(f"[{THEME['warning']}]No LLM backend available[/{THEME['warning']}]")
        return

    query = " ".join(args)

    console.print(f"\n[bold {THEME['primary']}]◈ WHAT-IF ANALYSIS ◈[/bold {THEME['primary']}]")
    console.print(f"[{THEME['dim']}]Query:[/{THEME['dim']}] {query}\n")

    with console.status(f"[{THEME['dim']}]Analyzing alternate timeline...[/{THEME['dim']}]"):
        result = simulate_whatif(manager, agent.client, query)

    if not result.success:
        console.print(f"[{THEME['warning']}]{result.error}[/{THEME['warning']}]")
        return

    console.print(Panel(
        result.analysis,
        title=f"[bold {THEME['warning']}]TIMELINE DIVERGENCE[/bold {THEME['warning']}]",
        border_style=THEME['warning'],
    ))

    console.print(f"\n[{THEME['dim']}]This is speculative. The road not taken remains unknown.[/{THEME['dim']}]")
    console.print(f"[{THEME['dim']}]Your actual choices have shaped who you are.[/{THEME['dim']}]")


def _display_simulation_transcript(transcript: "SimulationTranscript"):
    """Display simulation transcript in terminal."""
    from rich.rule import Rule
    from rich.markdown import Markdown

    current_turn = 0

    for turn in transcript.turns:
        if turn.role == "gm":
            current_turn = turn.turn_number
            console.print(Rule(f"Turn {current_turn}", style=THEME['secondary']))
            console.print()
            console.print(f"[bold {THEME['primary']}][GM][/bold {THEME['primary']}]")
            console.print(turn.content)
            console.print()

            if turn.choices_presented:
                for i, choice in enumerate(turn.choices_presented, 1):
                    console.print(f"  [{THEME['secondary']}]{i}.[/{THEME['secondary']}] {choice}")
                console.print()

        else:  # player
            console.print(
                f"[bold {THEME['accent']}][PLAYER ({transcript.persona})][/bold {THEME['accent']}]"
            )
            console.print(turn.content)
            console.print()

    # Summary panel
    stats = transcript.player_stats
    summary_lines = [
        f"Turns: {len([t for t in transcript.turns if t.role == 'gm'])}",
        f"Improvisations: {stats.get('improvisations', 0)}",
        f"Enhancements accepted: {stats.get('enhancements_accepted', 0)}",
        f"Offers refused: {stats.get('offers_refused', 0)}",
    ]

    console.print(Panel(
        f"[{THEME['accent']}]{g('moment')} SIMULATION COMPLETE[/{THEME['accent']}]\n" +
        " | ".join(summary_lines),
        border_style=THEME['primary'],
    ))


# -----------------------------------------------------------------------------
# Context Control Commands
# -----------------------------------------------------------------------------

def cmd_checkpoint(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Save campaign state and compress memory. Use when context is strained.

    This command:
    1. Generates/updates the campaign digest (compressed memory)
    2. Exports a session summary
    3. Prunes old transcript blocks (archives to disk)
    4. Resets strain state

    Usage:
        /checkpoint         - Full checkpoint with archive
        /checkpoint quick   - Update digest without archiving
    """
    from pathlib import Path
    from datetime import datetime
    from ..context import DigestManager

    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    quick_mode = args and args[0].lower() == "quick"
    campaign = manager.current
    campaign_id = campaign.meta.id

    console.print(f"\n[bold {THEME['primary']}]{'QUICK' if quick_mode else 'FULL'} CHECKPOINT[/bold {THEME['primary']}]")

    # Step 1: Generate/update digest
    console.print(f"[{THEME['secondary']}]Generating digest...[/{THEME['secondary']}]")
    digest_manager = DigestManager(Path("campaigns"))
    digest = digest_manager.generate(campaign)
    digest_path = digest_manager.save(campaign_id, digest)

    console.print(f"  [{THEME['accent']}]{g('success')}[/{THEME['accent']}] Digest saved: {digest_path.name}")
    console.print(f"    [{THEME['dim']}]Hinges: {len(digest.hinge_index)} | "
                  f"Factions: {len(digest.standing_reasons)} | "
                  f"NPCs: {len(digest.npc_anchors)} | "
                  f"Threads: {len(digest.open_threads)}[/{THEME['dim']}]")

    # Step 2: Export session summary
    session_num = campaign.meta.session_count
    console.print(f"[{THEME['secondary']}]Exporting session {session_num} summary...[/{THEME['secondary']}]")
    summary_md = digest_manager.export_session_summary(campaign, session_num)

    summaries_dir = Path("campaigns") / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summaries_dir / f"session_{session_num}_{campaign.meta.name.replace(' ', '_')}.md"
    summary_path.write_text(summary_md, encoding="utf-8")
    console.print(f"  [{THEME['accent']}]{g('success')}[/{THEME['accent']}] Summary: {summary_path.name}")

    if not quick_mode:
        # Step 3: Archive old transcript blocks (mark in history)
        # Note: Actual block pruning is handled by RollingWindow
        # We just mark this checkpoint in history
        from ..state.schema import HistoryEntry, HistoryType

        checkpoint_entry = HistoryEntry(
            session=session_num,
            type=HistoryType.CANON,
            summary=f"Checkpoint: digest updated, session {session_num} archived",
            is_permanent=True,
        )
        campaign.history.append(checkpoint_entry)
        console.print(f"  [{THEME['accent']}]{g('success')}[/{THEME['accent']}] Checkpoint logged to history")

    # Step 4: Save campaign
    manager.save_campaign()
    console.print(f"  [{THEME['accent']}]{g('success')}[/{THEME['accent']}] Campaign saved")

    console.print(f"\n[{THEME['accent']}]Checkpoint complete.[/{THEME['accent']}]")
    console.print(f"[{THEME['dim']}]Context memory compressed. Safe to continue.[/{THEME['dim']}]")


def cmd_compress(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Update campaign digest without pruning transcript.

    This is a lighter-weight operation than /checkpoint that just
    updates the compressed memory (digest) from current campaign state.

    Usage:
        /compress           - Update digest from current state
        /compress show      - Show current digest contents
    """
    from pathlib import Path
    from ..context import DigestManager

    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    campaign = manager.current
    campaign_id = campaign.meta.id
    digest_manager = DigestManager(Path("campaigns"))

    # Check for show mode
    if args and args[0].lower() == "show":
        existing = digest_manager.load(campaign_id)
        if existing:
            console.print(f"\n[bold {THEME['primary']}]CURRENT DIGEST[/bold {THEME['primary']}]")
            console.print(f"[{THEME['dim']}]Last updated: {existing.last_updated.strftime('%Y-%m-%d %H:%M')}[/{THEME['dim']}]")
            console.print(f"[{THEME['dim']}]Session count: {existing.session_count}[/{THEME['dim']}]\n")
            console.print(existing.to_prompt_text())
        else:
            console.print(f"[{THEME['dim']}]No digest exists yet. Run /compress to create one.[/{THEME['dim']}]")
        return

    console.print(f"\n[bold {THEME['primary']}]COMPRESSING MEMORY[/bold {THEME['primary']}]")

    # Generate and save digest
    digest = digest_manager.generate(campaign)
    digest_path = digest_manager.save(campaign_id, digest)

    console.print(f"[{THEME['accent']}]{g('success')}[/{THEME['accent']}] Digest updated")
    console.print(f"  [{THEME['dim']}]File: {digest_path.name}[/{THEME['dim']}]")

    # Show summary of what was captured
    console.print(f"\n[bold {THEME['secondary']}]DIGEST CONTENTS[/bold {THEME['secondary']}]")

    if digest.hinge_index:
        console.print(f"  [{THEME['accent']}]{len(digest.hinge_index)}[/{THEME['accent']}] hinge moments")
        for h in digest.hinge_index[-3:]:  # Show last 3
            console.print(f"    [{THEME['dim']}]S{h.session}:[/{THEME['dim']}] {h.choice[:50]}...")

    if digest.standing_reasons:
        console.print(f"  [{THEME['accent']}]{len(digest.standing_reasons)}[/{THEME['accent']}] faction standings explained")

    if digest.npc_anchors:
        console.print(f"  [{THEME['accent']}]{len(digest.npc_anchors)}[/{THEME['accent']}] NPCs with memories")

    if digest.open_threads:
        console.print(f"  [{THEME['accent']}]{len(digest.open_threads)}[/{THEME['accent']}] open consequence threads")

    console.print(f"\n[{THEME['dim']}]Use /compress show to view full digest content.[/{THEME['dim']}]")


def cmd_clear(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Clear transcript beyond minimum window (no digest update).

    WARNING: This clears conversation context without updating the digest.
    Use /checkpoint instead for a safe context reset.

    This is useful when:
    - You want to start fresh within a session
    - Context is bloated with irrelevant exchanges
    - You explicitly don't want to persist recent events

    Usage:
        /clear              - Clear with confirmation
        /clear force        - Clear without confirmation
    """
    from ..state.schema import HistoryEntry, HistoryType

    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    force = args and args[0].lower() == "force"

    if not force:
        console.print(f"\n[bold {THEME['warning']}]CLEAR TRANSCRIPT[/bold {THEME['warning']}]")
        console.print(f"[{THEME['dim']}]This will clear recent conversation context.[/{THEME['dim']}]")
        console.print(f"[{THEME['warning']}]WARNING: Digest will NOT be updated. Use /checkpoint instead for safe context reset.[/{THEME['warning']}]")

        confirm = Prompt.ask(
            f"[{THEME['danger']}]Clear without checkpoint?[/{THEME['danger']}]",
            choices=["y", "n"],
            default="n"
        )
        if confirm != "y":
            console.print(f"[{THEME['dim']}]Cancelled. Consider using /checkpoint instead.[/{THEME['dim']}]")
            return

    # Mark in history that we cleared without checkpoint
    session_num = manager.current.meta.session_count
    clear_entry = HistoryEntry(
        session=session_num,
        type=HistoryType.CANON,
        summary="Context cleared without checkpoint",
        is_permanent=False,
    )
    manager.current.history.append(clear_entry)

    # Save campaign
    manager.save_campaign()

    console.print(f"\n[{THEME['accent']}]{g('success')}[/{THEME['accent']}] Transcript cleared")
    console.print(f"[{THEME['dim']}]History marked: cleared_without_checkpoint[/{THEME['dim']}]")
    console.print(f"[{THEME['dim']}]Consider running /compress to update digest with recent events.[/{THEME['dim']}]")


# -----------------------------------------------------------------------------
# Loadout Commands
# -----------------------------------------------------------------------------

def cmd_loadout(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """
    Manage mission loadout.

    Usage:
        /loadout            Show current loadout and available gear
        /loadout add <item> Add item to loadout (by name or ID)
        /loadout remove <item>  Remove item from loadout
        /loadout clear      Clear all items from loadout
    """
    from ..state.schema import MissionPhase

    if not manager.current:
        console.print(f"[{THEME['warning']}]No campaign loaded[/{THEME['warning']}]")
        return

    if not manager.current.characters:
        console.print(f"[{THEME['warning']}]Create a character first (/char)[/{THEME['warning']}]")
        return

    char = manager.current.characters[0]
    session = manager.current.session

    # Check if we have an active session
    if not session:
        console.print(f"[{THEME['warning']}]No active mission. Use /mission to start one.[/{THEME['warning']}]")
        return

    # Subcommand parsing
    subcommand = args[0].lower() if args else "show"
    item_query = " ".join(args[1:]) if len(args) > 1 else ""

    # Check if loadout is locked (execution phase or later)
    locked_phases = {MissionPhase.EXECUTION, MissionPhase.RESOLUTION}
    is_locked = session.phase in locked_phases

    if subcommand in ("add", "remove", "clear") and is_locked:
        console.print(f"[{THEME['danger']}]Loadout is locked during {session.phase.value} phase[/{THEME['danger']}]")
        console.print(f"[{THEME['dim']}]Gear must be selected during planning. Work with what you brought.[/{THEME['dim']}]")
        return

    # Build gear lookup by ID and name
    gear_by_id = {g.id: g for g in char.gear}
    gear_by_name = {g.name.lower(): g for g in char.gear}

    # Get current loadout items
    loadout_items = [gear_by_id[gid] for gid in session.loadout if gid in gear_by_id]

    if subcommand == "add":
        if not item_query:
            console.print(f"[{THEME['warning']}]Specify item to add: /loadout add <item>[/{THEME['warning']}]")
            return

        # Find the item
        item = None
        query_lower = item_query.lower()

        # Try exact ID match
        if query_lower in gear_by_id:
            item = gear_by_id[query_lower]
        # Try name match (case-insensitive)
        elif query_lower in gear_by_name:
            item = gear_by_name[query_lower]
        # Try partial name match
        else:
            matches = [g for g in char.gear if query_lower in g.name.lower()]
            if len(matches) == 1:
                item = matches[0]
            elif len(matches) > 1:
                console.print(f"[{THEME['warning']}]Multiple matches:[/{THEME['warning']}]")
                for m in matches:
                    console.print(f"  • {m.name} [{THEME['dim']}]{m.id}[/{THEME['dim']}]")
                return

        if not item:
            console.print(f"[{THEME['warning']}]Item not found: {item_query}[/{THEME['warning']}]")
            console.print(f"[{THEME['dim']}]Use /loadout to see available gear[/{THEME['dim']}]")
            return

        if item.id in session.loadout:
            console.print(f"[{THEME['dim']}]{item.name} is already in loadout[/{THEME['dim']}]")
            return

        # Add to loadout
        session.loadout.append(item.id)
        manager.save_campaign()

        use_note = " (single-use)" if item.single_use else ""
        console.print(f"[{THEME['accent']}]{g('success')}[/{THEME['accent']}] Added {item.name}{use_note} to loadout")

        # Soft limit warning
        if len(session.loadout) > 5:
            console.print(f"[{THEME['warning']}]Note: {len(session.loadout)} items. Travel light to move fast.[/{THEME['warning']}]")

        return

    elif subcommand == "remove":
        if not item_query:
            console.print(f"[{THEME['warning']}]Specify item to remove: /loadout remove <item>[/{THEME['warning']}]")
            return

        # Find the item in loadout
        item = None
        query_lower = item_query.lower()

        for loaded_item in loadout_items:
            if loaded_item.id == query_lower or loaded_item.name.lower() == query_lower:
                item = loaded_item
                break
            elif query_lower in loaded_item.name.lower():
                item = loaded_item
                break

        if not item:
            console.print(f"[{THEME['warning']}]Item not in loadout: {item_query}[/{THEME['warning']}]")
            return

        session.loadout.remove(item.id)
        manager.save_campaign()
        console.print(f"[{THEME['accent']}]{g('success')}[/{THEME['accent']}] Removed {item.name} from loadout")
        return

    elif subcommand == "clear":
        if not session.loadout:
            console.print(f"[{THEME['dim']}]Loadout is already empty[/{THEME['dim']}]")
            return

        count = len(session.loadout)
        session.loadout.clear()
        manager.save_campaign()
        console.print(f"[{THEME['accent']}]{g('success')}[/{THEME['accent']}] Cleared {count} item(s) from loadout")
        return

    # Default: show loadout and available gear
    console.print(f"\n[bold {THEME['primary']}]MISSION LOADOUT[/bold {THEME['primary']}]")

    # Phase indicator
    phase_color = THEME['accent'] if session.phase == MissionPhase.PLANNING else THEME['dim']
    lock_status = f"[{THEME['danger']}]LOCKED[/{THEME['danger']}]" if is_locked else f"[{THEME['accent']}]OPEN[/{THEME['accent']}]"
    console.print(f"[{THEME['dim']}]Phase:[/{THEME['dim']}] [{phase_color}]{session.phase.value.upper()}[/{phase_color}] | {lock_status}")

    # Current loadout
    if loadout_items:
        console.print(f"\n[bold {THEME['secondary']}]Packed ({len(loadout_items)} items)[/bold {THEME['secondary']}]")
        for item in loadout_items:
            use_tag = f" [{THEME['warning']}]ONE-USE[/{THEME['warning']}]" if item.single_use else ""
            used_tag = f" [{THEME['danger']}]SPENT[/{THEME['danger']}]" if item.used else ""
            console.print(f"  {g('bullet')} {item.name}{use_tag}{used_tag}")
            if item.description:
                console.print(f"      [{THEME['dim']}]{item.description}[/{THEME['dim']}]")
    else:
        console.print(f"\n[{THEME['dim']}]Loadout empty — nothing packed[/{THEME['dim']}]")

    # Available gear (not in loadout)
    available = [g_item for g_item in char.gear if g_item.id not in session.loadout]
    if available:
        console.print(f"\n[bold {THEME['secondary']}]Available at Base ({len(available)} items)[/bold {THEME['secondary']}]")

        # Group by category
        by_category: dict[str, list] = {}
        for item in available:
            cat = item.category or "General"
            by_category.setdefault(cat, []).append(item)

        for category, items in sorted(by_category.items()):
            console.print(f"  [{THEME['accent']}]{category}[/{THEME['accent']}]")
            for item in items:
                use_tag = f" [{THEME['warning']}]one-use[/{THEME['warning']}]" if item.single_use else ""
                console.print(f"    {g('bullet')} {item.name}{use_tag}")

    # Help text
    if not is_locked:
        console.print(f"\n[{THEME['dim']}]Commands: /loadout add <item> | remove <item> | clear[/{THEME['dim']}]")
        console.print(f"[{THEME['dim']}]Tip: Pack light (3-5 items). What's not packed stays at base.[/{THEME['dim']}]")


# Command Registry
# -----------------------------------------------------------------------------

def create_commands(manager: CampaignManager, agent: SentinelAgent, conversation: list | None = None):
    """Create command handlers with proper closures."""
    return {
        "/new": cmd_new,
        "/load": cmd_load,
        "/list": cmd_list,
        "/save": cmd_save,
        "/delete": cmd_delete,
        "/status": lambda m, a, args: show_status(m, a, conversation),
        "/backend": cmd_backend,
        "/model": cmd_model,
        "/ping": cmd_ping,
        "/banner": cmd_banner,
        "/statusbar": cmd_statusbar,
        "/lore": cmd_lore,
        "/char": cmd_char,
        "/npc": cmd_npc,
        "/factions": cmd_factions,
        "/arc": cmd_arc,
        "/roll": cmd_roll,
        "/loadout": cmd_loadout,
        "/start": cmd_start,
        "/mission": cmd_mission,
        "/consult": cmd_consult,
        "/debrief": cmd_debrief,
        "/history": cmd_history,
        "/search": cmd_search,
        "/summary": cmd_summary,
        "/consequences": cmd_consequences,
        "/threads": cmd_consequences,  # Alias
        "/simulate": cmd_simulate,
        "/timeline": cmd_timeline,
        "/wiki": cmd_wiki,
        "/context": cmd_context,
        # Context control commands
        "/checkpoint": cmd_checkpoint,
        "/compress": cmd_compress,
        "/clear": cmd_clear,
        "/help": lambda m, a, args: show_help(),
        "/quit": lambda m, a, args: sys.exit(0),
        "/exit": lambda m, a, args: sys.exit(0),
    }
