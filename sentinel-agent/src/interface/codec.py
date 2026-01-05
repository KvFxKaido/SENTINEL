"""
MGS-style codec frame renderer for NPC portraits.

Displays character portraits in a bordered frame with faction styling,
disposition indicators, and optional visual effects.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Disposition(Enum):
    HOSTILE = "hostile"
    WARY = "wary"
    NEUTRAL = "neutral"
    WARM = "warm"
    LOYAL = "loyal"


# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Faction colors
    NEXUS = "\033[38;5;39m"       # Blue
    EMBER = "\033[38;5;208m"      # Orange
    LATTICE = "\033[38;5;220m"    # Yellow
    CONVERGENCE = "\033[38;5;129m" # Purple
    COVENANT = "\033[38;5;255m"   # White
    WANDERERS = "\033[38;5;101m"  # Tan/brown
    CULTIVATORS = "\033[38;5;34m" # Green
    STEEL = "\033[38;5;240m"      # Gray
    WITNESSES = "\033[38;5;52m"   # Dark red
    ARCHITECTS = "\033[38;5;24m"  # Steel blue
    GHOST = "\033[38;5;236m"      # Dark gray

    # Disposition colors
    HOSTILE_COLOR = "\033[38;5;196m"  # Red
    WARY_COLOR = "\033[38;5;208m"     # Orange
    NEUTRAL_COLOR = "\033[38;5;247m"  # Gray
    WARM_COLOR = "\033[38;5;77m"      # Green
    LOYAL_COLOR = "\033[38;5;39m"     # Blue

    # Scanline effect
    SCANLINE = "\033[38;5;236m"


FACTION_COLORS = {
    "nexus": Colors.NEXUS,
    "ember": Colors.EMBER,
    "ember_colonies": Colors.EMBER,
    "lattice": Colors.LATTICE,
    "convergence": Colors.CONVERGENCE,
    "covenant": Colors.COVENANT,
    "wanderers": Colors.WANDERERS,
    "cultivators": Colors.CULTIVATORS,
    "steel": Colors.STEEL,
    "steel_syndicate": Colors.STEEL,
    "witnesses": Colors.WITNESSES,
    "architects": Colors.ARCHITECTS,
    "ghost": Colors.GHOST,
    "ghost_networks": Colors.GHOST,
}

DISPOSITION_COLORS = {
    Disposition.HOSTILE: Colors.HOSTILE_COLOR,
    Disposition.WARY: Colors.WARY_COLOR,
    Disposition.NEUTRAL: Colors.NEUTRAL_COLOR,
    Disposition.WARM: Colors.WARM_COLOR,
    Disposition.LOYAL: Colors.LOYAL_COLOR,
}

DISPOSITION_ICONS = {
    Disposition.HOSTILE: "■",
    Disposition.WARY: "◆",
    Disposition.NEUTRAL: "●",
    Disposition.WARM: "♦",
    Disposition.LOYAL: "★",
}


# ASCII portrait templates by archetype
PORTRAITS = {
    "default": [
        "   ╭─────╮   ",
        "   │ ◠ ◠ │   ",
        "   │  ▽  │   ",
        "   ╰─────╯   ",
        "    ╱███╲    ",
    ],
    "scout": [
        "   ╭─────╮   ",
        "   │ ◠ ◠ │   ",
        "   │  ◡  │   ",
        "   ╰─────╯   ",
        "   ╱░░█░░╲   ",
    ],
    "soldier": [
        "  ┌┬─────┬┐  ",
        "   │ ▬ ▬ │   ",
        "   │  ▲  │   ",
        "   ╰─────╯   ",
        "   ╱█████╲   ",
    ],
    "elder": [
        "   ╭─────╮   ",
        "   │ ─ ─ │   ",
        "  ╱│  ∩  │╲  ",
        "   ╰─────╯   ",
        "    ╱▓▓▓╲    ",
    ],
    "merchant": [
        "   ╭─────╮   ",
        "   │ $ $ │   ",
        "   │  ◡  │   ",
        "   ╰──┬──╯   ",
        "    ╱▒▒▒╲    ",
    ],
    "mystic": [
        "  ╭──◊──╮    ",
        "   │ ◉ ◉ │   ",
        "   │  ○  │   ",
        "   ╰─────╯   ",
        "   ╱░▓░▓░╲   ",
    ],
    "hacker": [
        "   ╭─────╮   ",
        "   │ 0 0 │   ",
        "   │  =  │   ",
        "   ╰─────╯   ",
        "    ╱▓█▓╲    ",
    ],
    "medic": [
        "   ╭──┼──╮   ",
        "   │ ◠ ◠ │   ",
        "   │  ◡  │   ",
        "   ╰─────╯   ",
        "    ╱░+░╲    ",
    ],
    "hostile": [
        "   ╭─────╮   ",
        "   │ ▼ ▼ │   ",
        "   │  ▲  │   ",
        "   ╰─────╯   ",
        "   ╱█▓█▓█╲   ",
    ],
}


@dataclass
class NPCDisplay:
    """Data for displaying an NPC in codec style."""
    name: str
    faction: str
    disposition: Disposition = Disposition.NEUTRAL
    archetype: str = "default"
    title: Optional[str] = None


def get_faction_color(faction: str) -> str:
    """Get the ANSI color code for a faction."""
    return FACTION_COLORS.get(faction.lower(), Colors.RESET)


def get_disposition_display(disposition: Disposition) -> tuple[str, str]:
    """Get the color and icon for a disposition."""
    color = DISPOSITION_COLORS.get(disposition, Colors.NEUTRAL_COLOR)
    icon = DISPOSITION_ICONS.get(disposition, "●")
    return color, icon


def render_codec_frame(
    npc: NPCDisplay,
    scanlines: bool = True,
    width: int = 32,
) -> str:
    """
    Render an MGS-style codec frame for an NPC.

    Args:
        npc: The NPC to display
        scanlines: Whether to add scanline effect
        width: Frame width

    Returns:
        Rendered frame as a string
    """
    faction_color = get_faction_color(npc.faction)
    disp_color, disp_icon = get_disposition_display(npc.disposition)
    portrait = PORTRAITS.get(npc.archetype, PORTRAITS["default"])

    lines = []
    reset = Colors.RESET
    dim = Colors.DIM
    bold = Colors.BOLD

    # Top border
    lines.append(f"{faction_color}╔{'═' * (width - 2)}╗{reset}")

    # Faction header
    faction_display = npc.faction.upper().replace("_", " ")
    header = f" {faction_display} "
    padding = width - 4 - len(header)
    left_pad = padding // 2
    right_pad = padding - left_pad
    lines.append(f"{faction_color}║{reset}{dim}{'░' * left_pad}{reset}{faction_color}{bold}{header}{reset}{dim}{'░' * right_pad}{reset}{faction_color}║{reset}")

    # Separator
    lines.append(f"{faction_color}╟{'─' * (width - 2)}╢{reset}")

    # Portrait area
    portrait_width = 13  # Width of portrait art
    portrait_padding = (width - 2 - portrait_width) // 2

    for i, portrait_line in enumerate(portrait):
        # Add scanline effect on alternating lines
        if scanlines and i % 2 == 1:
            styled_portrait = f"{Colors.SCANLINE}{portrait_line}{reset}"
        else:
            styled_portrait = f"{faction_color}{portrait_line}{reset}"

        line = f"{faction_color}║{reset}{' ' * portrait_padding}{styled_portrait}{' ' * portrait_padding}{faction_color}║{reset}"
        lines.append(line)

    # Separator
    lines.append(f"{faction_color}╟{'─' * (width - 2)}╢{reset}")

    # Name and disposition
    name_display = npc.name.upper()
    disp_display = f"[{npc.disposition.value.upper()}]"

    # Calculate spacing
    name_section = f" {name_display}"
    disp_section = f"{disp_display} {disp_icon} "
    middle_space = width - 2 - len(name_section) - len(disp_section)

    info_line = f"{faction_color}║{reset}{bold}{name_section}{reset}{' ' * middle_space}{disp_color}{disp_section}{reset}{faction_color}║{reset}"
    lines.append(info_line)

    # Title line (optional)
    if npc.title:
        title_display = npc.title
        title_padding = width - 4 - len(title_display)
        lines.append(f"{faction_color}║{reset}{dim} {title_display}{' ' * title_padding}{reset}{faction_color}║{reset}")

    # Bottom border
    lines.append(f"{faction_color}╚{'═' * (width - 2)}╝{reset}")

    return "\n".join(lines)


def render_calling_animation(npc: NPCDisplay, frame: int = 0) -> str:
    """Render a 'calling' animation frame."""
    faction_color = get_faction_color(npc.faction)
    reset = Colors.RESET

    dots = "." * ((frame % 3) + 1)
    padding = " " * (3 - len(dots))

    return f"{faction_color}╔════════════════════════════╗\n║  INCOMING TRANSMISSION{dots}{padding} ║\n╚════════════════════════════╝{reset}"


def demo():
    """Demo the codec frame renderer."""
    import sys

    # Enable UTF-8 on Windows
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')

    # Show calling animation
    npc = NPCDisplay(
        name="Kira",
        faction="ember_colonies",
        disposition=Disposition.WARM,
        archetype="scout",
        title="Ember Scout, Eastern Sector",
    )

    print("\n" + "=" * 40)
    print("  SENTINEL CODEC - NPC Portrait Demo")
    print("=" * 40 + "\n")

    # Show the codec frame
    print(render_codec_frame(npc))
    print()

    # Show different dispositions
    print("\n--- Disposition Examples ---\n")

    for disposition in Disposition:
        test_npc = NPCDisplay(
            name="Test",
            faction="nexus",
            disposition=disposition,
            archetype="default",
        )
        disp_color, disp_icon = get_disposition_display(disposition)
        print(f"{disp_color}[{disposition.value.upper():^8}] {disp_icon}{Colors.RESET}")

    # Show different archetypes
    print("\n--- Archetype Portraits ---\n")

    archetypes = [
        ("Kira", "ember", "scout", "Scout"),
        ("Marcus", "steel_syndicate", "merchant", "Fence"),
        ("The Oracle", "nexus", "mystic", "Seer"),
        ("Vex", "ghost_networks", "hacker", "Infiltrator"),
        ("Commander Thresh", "covenant", "soldier", "Enforcer"),
        ("Elder Moss", "cultivators", "elder", "Grove Keeper"),
    ]

    for name, faction, archetype, title in archetypes:
        test_npc = NPCDisplay(
            name=name,
            faction=faction,
            disposition=Disposition.NEUTRAL,
            archetype=archetype,
            title=title,
        )
        print(render_codec_frame(test_npc, width=32))
        print()


if __name__ == "__main__":
    demo()
