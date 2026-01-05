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
from .renderer import console, THEME, show_status, show_backend_status, show_help
from .config import set_model as save_model_config, set_animate_banner, load_config
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
    save_model_config(selection)  # Save preference
    console.print(f"[green]Switched to:[/green] {selection}")
    console.print("[dim]  (Saved as default)[/dim]")

    # Check tool support
    if client.supports_tools:
        console.print("[dim]  Tool calling supported[/dim]")
    else:
        console.print("[yellow]  Tool calling not supported by this model[/yellow]")


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


def cmd_lore(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Show lore status and test retrieval. Use /lore <faction> to filter by perspective."""
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

        # Retrieve with faction filter if specified
        factions_arg = [faction_filter] if faction_filter else None
        results = retriever.retrieve(query=query, factions=factions_arg, limit=3 if faction_filter else 2)

        if results:
            for r in results:
                console.print(f"\n[cyan]{r.chunk.title}[/cyan] ({r.chunk.source})")
                console.print(f"  Score: {r.score:.1f} — {', '.join(r.match_reasons)}")

                # Show perspective/bias prominently
                if r.chunk.factions:
                    faction_tags = ", ".join(r.chunk.factions)
                    console.print(f"  [{THEME['warning']}]Perspective: {faction_tags}[/{THEME['warning']}]")

                preview = r.chunk.content[:200].replace('\n', ' ')
                console.print(f"  [dim]{preview}...[/dim]")
        else:
            console.print("[dim]No matches found[/dim]")
    else:
        console.print(f"\n[dim]Use /lore <query> to search, or /lore <faction> to filter by perspective[/dim]")
        console.print(f"[dim]Example: /lore lattice infrastructure[/dim]")


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


# -----------------------------------------------------------------------------
# Simulation Commands
# -----------------------------------------------------------------------------

def cmd_simulate(manager: CampaignManager, agent: SentinelAgent, args: list[str]):
    """Run AI vs AI simulation for testing.

    Usage: /simulate [turns] [persona]

    Personas: cautious, opportunist, principled, chaotic
    """
    from pathlib import Path
    from rich.live import Live
    from rich.spinner import Spinner
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
        "/banner": cmd_banner,
        "/lore": cmd_lore,
        "/char": cmd_char,
        "/roll": cmd_roll,
        "/start": cmd_start,
        "/mission": cmd_mission,
        "/consult": cmd_consult,
        "/debrief": cmd_debrief,
        "/history": cmd_history,
        "/simulate": cmd_simulate,
        "/help": lambda m, a, args: show_help(),
        "/quit": lambda m, a, args: sys.exit(0),
        "/exit": lambda m, a, args: sys.exit(0),
    }
