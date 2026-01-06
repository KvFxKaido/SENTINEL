#!/usr/bin/env python3
"""
SENTINEL NPC Codec System - MGS-Inspired Terminal Dialogue
Prototype for enhanced faction glyphs + styled frames
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.box import DOUBLE
from typing import Literal

console = Console()

# Faction glyphs and color schemes
FACTION_IDENTITY = {
    "nexus": {
        "glyph": "◈",
        "color": "#5B9BD5",  # Cold blue
        "style": "clinical"
    },
    "ember": {
        "glyph": "◆",
        "color": "#E67E22",  # Warm orange
        "style": "warm"
    },
    "lattice": {
        "glyph": "⬡",
        "color": "#7D3C98",  # Purple
        "style": "enhanced"
    },
    "convergence": {
        "glyph": "◉",
        "color": "#00BCD4",  # Cyan
        "style": "transcendent"
    },
    "covenant": {
        "glyph": "✦",
        "color": "#C0C0C0",  # Silver
        "style": "traditional"
    },
    "wanderers": {
        "glyph": "◇",
        "color": "#8B4513",  # Earth brown
        "style": "nomadic"
    },
    "cultivators": {
        "glyph": "❋",
        "color": "#2ECC71",  # Green
        "style": "organic"
    },
    "syndicate": {
        "glyph": "◼",
        "color": "#95A5A6",  # Industrial gray
        "style": "utilitarian"
    },
    "witnesses": {
        "glyph": "◎",
        "color": "#F39C12",  # Archive gold
        "style": "observant"
    },
    "architects": {
        "glyph": "▣",
        "color": "#34495E",  # Structural blue-gray
        "style": "ordered"
    },
    "ghost": {
        "glyph": "◌",
        "color": "#7F8C8D",  # Ephemeral gray
        "style": "glitchy"
    }
}

# Disposition colors
DISPOSITION_COLORS = {
    "hostile": "#E74C3C",      # Red
    "unfriendly": "#E67E22",   # Orange
    "neutral": "#95A5A6",      # Gray
    "friendly": "#3498DB",     # Blue
    "allied": "#2ECC71"        # Green
}

def show_npc_dialogue(
    name: str,
    faction: str,
    role: str,
    disposition: Literal["hostile", "unfriendly", "neutral", "friendly", "allied"],
    dialogue: str
):
    """Display NPC dialogue in MGS codec style"""
    
    faction_info = FACTION_IDENTITY.get(faction.lower(), FACTION_IDENTITY["nexus"])
    glyph = faction_info["glyph"]
    faction_color = faction_info["color"]
    disposition_color = DISPOSITION_COLORS[disposition]
    
    # Build the header
    header = Text()
    header.append(f"  {glyph}  ", style=f"bold {faction_color}")
    header.append(name.upper(), style=f"bold {faction_color}")
    header.append("\n")
    header.append(f"  [{faction.upper()} - {role.upper()}]", style=f"dim {faction_color}")
    header.append("\n")
    header.append(f"  [Disposition: {disposition.capitalize()}]", style=f"{disposition_color}")
    
    # Build the dialogue section with Rich's built-in wrapping
    dialogue_text = Text()
    dialogue_text.append("\n")
    dialogue_text.append(f"  {dialogue}\n", style=faction_color)
    
    # Combine header and dialogue
    content = Text()
    content.append(header)
    content.append(dialogue_text)
    
    # Create the panel with faction-appropriate styling
    panel = Panel(
        content,
        border_style=faction_color,
        box=DOUBLE,
        padding=(0, 1),
        width=55
    )
    
    console.print(panel)
    console.print()  # Spacing


def demo():
    """Run a demo showing different NPCs and factions"""
    
    console.print("\n[bold white]SENTINEL NPC Codec System - Demo[/bold white]\n")
    
    # Nexus Analyst - Neutral
    show_npc_dialogue(
        name="Dr. Helena Voss",
        faction="nexus",
        role="Analyst",
        disposition="neutral",
        dialogue="The probability matrix favors acceptance. Resources gained outweigh projected obligation costs by 2.3x. Recommend proceeding with caution."
    )
    
    # Ember Contact - Friendly
    show_npc_dialogue(
        name="Marcus Webb",
        faction="ember",
        role="Cell Leader",
        disposition="friendly",
        dialogue="They never give without taking. Ask yourself what they'll want when you can't say no. We've seen this pattern before."
    )
    
    # Witness Archivist - Allied
    show_npc_dialogue(
        name="Yuki Tanaka",
        faction="witnesses",
        role="Archivist",
        disposition="allied",
        dialogue="Syndicate enhancement acceptance historically correlates with 73% faction dependency within 18 months. Recording for future reference."
    )
    
    # Ghost Network Operator - Unfriendly
    show_npc_dialogue(
        name="Cipher",
        faction="ghost",
        role="Operative",
        disposition="unfriendly",
        dialogue="You're asking the wrong questions. The problem isn't what they're offering. It's why they're offering it to you specifically."
    )
    
    # Covenant Priest - Neutral
    show_npc_dialogue(
        name="Father Elias",
        faction="covenant",
        role="Spiritual Advisor",
        disposition="neutral",
        dialogue="Every gift carries obligation. The question is whether you're accepting a burden or embracing a calling. Only you can discern the difference."
    )
    
    # Lattice Technician - Friendly
    show_npc_dialogue(
        name="Dr. Sarah Chen",
        faction="lattice",
        role="Enhancement Specialist",
        disposition="friendly",
        dialogue="The augmentation is reversible within the first 72 hours. After that, neural integration becomes permanent. Your choice matters now."
    )
    
    # Steel Syndicate Broker - Hostile
    show_npc_dialogue(
        name="Kovac",
        faction="syndicate",
        role="Resource Broker",
        disposition="hostile",
        dialogue="You walk in here with nothing to offer and expect favors? That's not how this works. Come back when you've got something worth my time."
    )

    console.print("[dim]Press Enter to see conversation flow demo...[/dim]")
    input()
    
    # Simulate a conversation sequence
    console.print("\n[bold white]CONVERSATION FLOW EXAMPLE[/bold white]\n")
    
    console.print("[italic white]> You approach the guard at the checkpoint.[/italic white]\n")
    
    show_npc_dialogue(
        name="Guard Station 7",
        faction="architects",
        role="Security",
        disposition="neutral",
        dialogue="Credentials. Now."
    )
    
    console.print("[italic white]> You present your transit papers.[/italic white]\n")
    
    show_npc_dialogue(
        name="Guard Station 7",
        faction="architects",
        role="Security",
        disposition="unfriendly",
        dialogue="These are dated. You should have renewed them last week. I could turn you away right now."
    )
    
    console.print("[dim italic]1. Apologize and offer to pay the late fee")
    console.print("2. Point out the papers are technically still valid")
    console.print("3. Ask if there's another way through")
    console.print("4. Something else...[/dim italic]\n")


if __name__ == "__main__":
    demo()
