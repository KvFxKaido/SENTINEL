"""
SENTINEL Rich Enhancement - Panel Rendering
Persistent status displays for CLI wrapper
"""
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.console import RenderableType


def render_status_panel(campaign_state) -> Panel:
    """
    Persistent status bar showing:
    - Character name + background
    - Social energy
    - Context pressure + strain tier
    - Current phase
    """
    char = campaign_state.player
    
    # Get context metrics (from your context control)
    pressure = getattr(campaign_state, 'context_pressure', 0.0)
    strain = get_strain_indicator(pressure)
    
    # Get current mission phase
    phase = campaign_state.mission.phase if campaign_state.mission else "FREE ROAM"
    
    # Build status line with separators
    parts = [
        f"[bold cyan]{char.name}[/bold cyan]",
        f"[{char.background}]",
        f"Energy: [green]{char.social_energy}%[/green]",
        f"Context: [yellow]{int(pressure * 100)}%[/yellow] {strain}",
        f"Phase: [magenta]{phase}[/magenta]"
    ]
    
    status_text = Text(" │ ".join(parts))
    
    return Panel(
        status_text,
        style="on #001100",
        border_style="blue",
        padding=(0, 1)
    )


def render_faction_panel(campaign_state, limit: int = 4) -> Panel:
    """
    Show top N factions by relevance with visual bars
    """
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="left")
    table.add_column(justify="left")
    table.add_column(justify="left")
    
    # Get visible factions (prioritize recent interactions or high standing)
    visible_factions = get_visible_factions(campaign_state, limit)
    
    for faction_name, standing in visible_factions:
        # Visual bar
        bar = create_standing_bar(standing)
        
        # Standing mood
        mood = get_standing_mood(standing)
        mood_color = get_mood_color(standing)
        
        table.add_row(
            f"[cyan]{faction_name}[/cyan]",
            bar,
            f"[{mood_color}]{mood}[/{mood_color}]"
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
        "[cyan]X[/cyan]=Clear",
        "[cyan]D[/cyan]=Debrief",
        "[cyan]H[/cyan]=Help"
    ]
    
    return Text(" │ ".join(shortcuts), style="dim")


# --- Helper Functions ---

def get_strain_indicator(pressure: float) -> str:
    """
    Visual indicator for context strain tier
    Matches your Memory Strain thresholds
    """
    if pressure < 0.70:
        return "[green]Normal[/green]"
    elif pressure < 0.85:
        return "[yellow]⚠ Strain I[/yellow]"
    elif pressure < 0.95:
        return "[red]⚠⚠ Strain II[/red]"
    else:
        return "[bold red]⚠⚠⚠ Strain III[/bold red]"


def create_standing_bar(standing: int, width: int = 10) -> str:
    """
    Visual bar for faction standing
    Standing ranges from -100 (hostile) to +100 (trusted)
    """
    # Normalize to 0..width
    normalized = int((standing + 100) / 200 * width)
    normalized = max(0, min(width, normalized))  # Clamp
    
    filled = "▰" * normalized
    empty = "▱" * (width - normalized)
    
    # Color based on standing
    if standing >= 40:
        color = "green"
    elif standing >= -20:
        color = "white"
    else:
        color = "red"
    
    return f"[{color}]{filled}{empty}[/{color}]"


def get_standing_mood(standing: int) -> str:
    """
    Text label for faction standing
    Matches SENTINEL's faction relationship system
    """
    if standing >= 60:
        return "Trusted"
    elif standing >= 20:
        return "Friendly"
    elif standing >= -20:
        return "Neutral"
    elif standing >= -60:
        return "Wary"
    else:
        return "Hostile"


def get_mood_color(standing: int) -> str:
    """Color coding for mood labels"""
    if standing >= 40:
        return "green"
    elif standing >= -20:
        return "white"
    else:
        return "red"


def get_visible_factions(campaign_state, limit: int = 4) -> list[tuple[str, int]]:
    """
    Return top N factions by relevance
    Priority: recent interactions > high standing > alphabetical
    """
    standings = campaign_state.faction_standings
    
    # Simple version for Phase 1: sort by absolute standing
    # Phase 2: weight by recent interaction count
    sorted_factions = sorted(
        standings.items(),
        key=lambda x: abs(x[1]),  # Sort by magnitude of standing
        reverse=True
    )
    
    return sorted_factions[:limit]
