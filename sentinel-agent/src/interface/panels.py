"""
SENTINEL Rich Enhancement - Panel Rendering
Persistent status displays for enhanced CLI wrapper
"""
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from ..state.schema import Campaign, Standing, MissionPhase


def render_status_panel(campaign: Campaign) -> Panel:
    """
    Persistent status bar showing:
    - Character name + background
    - Social energy
    - Current mission phase
    - Session number
    """
    if not campaign.characters:
        # No character created yet
        status_text = Text(
            f"[bold cyan]{campaign.meta.name}[/bold cyan] │ "
            f"Session: {campaign.meta.session_count} │ "
            f"[dim]No character yet - use /char to create[/dim]"
        )
    else:
        char = campaign.characters[0]

        # Get current mission phase
        if campaign.session and campaign.session.phase:
            phase = campaign.session.phase.value.upper()
            phase_color = {
                "briefing": "cyan",
                "planning": "yellow",
                "execution": "red",
                "resolution": "magenta",
                "debrief": "green",
                "between": "dim",
            }.get(campaign.session.phase.value, "white")
            phase_display = f"[{phase_color}]{phase}[/{phase_color}]"
        else:
            phase_display = "[dim]FREE ROAM[/dim]"

        # Get social energy with color coding
        energy = char.social_energy.current
        energy_color = "green" if energy > 60 else "yellow" if energy > 30 else "red"

        # Build status line with separators
        parts = [
            f"[bold cyan]{char.name}[/bold cyan]",
            f"[dim]{char.background.value if char.background else 'Unknown'}[/dim]",
            f"Energy: [{energy_color}]{energy}[/{energy_color}]",
            f"Session: {campaign.meta.session_count}",
            f"Phase: {phase_display}"
        ]

        status_text = Text(" │ ".join(parts))

    return Panel(
        status_text,
        style="on #001100",
        border_style="blue",
        padding=(0, 1)
    )


def render_faction_panel(campaign: Campaign, limit: int = 4) -> Panel:
    """
    Show top N factions by relevance with visual bars
    """
    if not campaign.factions:
        return Panel(
            Text("[dim]No faction standings yet[/dim]"),
            title="[bold]FACTIONS[/bold]",
            title_align="left",
            style="on #001100",
            border_style="blue",
            padding=(0, 1)
        )

    table = Table.grid(padding=(0, 2))
    table.add_column(justify="left", width=20)
    table.add_column(justify="left", width=12)
    table.add_column(justify="left")

    # Get visible factions (prioritize by absolute standing value)
    visible_factions = get_visible_factions(campaign, limit)

    for faction_name, standing in visible_factions:
        # Standing is a Standing enum (HOSTILE, UNFRIENDLY, NEUTRAL, FRIENDLY, ALLIED)
        # Convert to a numeric value for the bar (-100 to +100 scale)
        standing_value = standing_to_numeric(standing)

        # Visual bar
        bar = create_standing_bar(standing_value)

        # Standing mood with color
        mood_color = get_mood_color(standing)

        table.add_row(
            f"[cyan]{faction_name}[/cyan]",
            bar,
            f"[{mood_color}]{standing.value}[/{mood_color}]"
        )

    return Panel(
        table,
        title="[bold]FACTIONS[/bold]",
        title_align="left",
        style="on #001100",
        border_style="blue",
        padding=(0, 1)
    )


def render_button_bar() -> Text:
    """
    QoL shortcuts displayed at bottom
    Shows available keyboard shortcuts
    """
    shortcuts = [
        "[cyan]C[/cyan]=Checkpoint",
        "[cyan]S[/cyan]=Status",
        "[cyan]F[/cyan]=Factions",
        "[cyan]H[/cyan]=Help",
        "[cyan]Q[/cyan]=Quit"
    ]

    return Text(" │ ".join(shortcuts), style="dim")


# --- Helper Functions ---

def standing_to_numeric(standing: Standing) -> int:
    """
    Convert Standing enum to numeric value for visualization
    HOSTILE = -80, UNFRIENDLY = -40, NEUTRAL = 0, FRIENDLY = +40, ALLIED = +80
    """
    mapping = {
        Standing.HOSTILE: -80,
        Standing.UNFRIENDLY: -40,
        Standing.NEUTRAL: 0,
        Standing.FRIENDLY: 40,
        Standing.ALLIED: 80,
    }
    return mapping.get(standing, 0)


def create_standing_bar(standing_value: int, width: int = 10) -> str:
    """
    Visual bar for faction standing
    Standing ranges from -100 (hostile) to +100 (allied)
    """
    # Normalize to 0..width
    normalized = int((standing_value + 100) / 200 * width)
    normalized = max(0, min(width, normalized))  # Clamp

    filled = "▰" * normalized
    empty = "▱" * (width - normalized)

    # Color based on standing value
    if standing_value >= 40:
        color = "green"
    elif standing_value >= -20:
        color = "white"
    else:
        color = "red"

    return f"[{color}]{filled}{empty}[/{color}]"


def get_mood_color(standing: Standing) -> str:
    """Color coding for faction standing"""
    mapping = {
        Standing.HOSTILE: "red",
        Standing.UNFRIENDLY: "yellow",
        Standing.NEUTRAL: "white",
        Standing.FRIENDLY: "green",
        Standing.ALLIED: "bright_green",
    }
    return mapping.get(standing, "white")


def get_visible_factions(campaign: Campaign, limit: int = 4) -> list[tuple[str, Standing]]:
    """
    Return top N factions by relevance
    Priority: highest absolute standing (most extreme relationships shown first)
    """
    if not campaign.factions:
        return []

    # Build list of (faction_name, standing, numeric_value) tuples
    faction_list = []

    # FactionRegistry has fields for each faction
    for faction_field in ['nexus', 'ember_colonies', 'lattice', 'convergence',
                          'covenant', 'wanderers', 'cultivators', 'steel_syndicate',
                          'witnesses', 'architects', 'ghost_networks']:
        faction_data = getattr(campaign.factions, faction_field, None)
        if faction_data:
            # Get friendly name from field name
            faction_name = faction_field.replace('_', ' ').title()
            numeric = standing_to_numeric(faction_data.standing)
            faction_list.append((faction_name, faction_data.standing, abs(numeric)))

    # Sort by absolute standing value (most extreme first)
    faction_list.sort(key=lambda x: x[2], reverse=True)

    # Return top N as (name, standing) tuples
    return [(name, standing) for name, standing, _ in faction_list[:limit]]
