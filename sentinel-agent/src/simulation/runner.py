"""Simulation runner and transcript management."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from ..llm.base import Message
from ..state.schema import Character, Background
from ..state.manager import CampaignManager
from .player import AIPlayer


@dataclass
class SimulationTurn:
    """A single turn in the simulation."""

    turn_number: int
    role: Literal["gm", "player"]
    content: str
    choices_presented: list[str] = field(default_factory=list)


@dataclass
class SimulationTranscript:
    """Complete transcript of a simulation run."""

    persona: str = "cautious"
    character_name: str = "Unknown"
    character_background: str = "Unknown"
    started_at: datetime = field(default_factory=datetime.now)
    turns: list[SimulationTurn] = field(default_factory=list)
    player_stats: dict = field(default_factory=dict)

    def add_turn(
        self,
        role: Literal["gm", "player"],
        content: str,
        choices: list[str] | None = None,
    ) -> None:
        """Add a turn to the transcript."""
        turn_num = len([t for t in self.turns if t.role == "gm"])
        if role == "gm":
            turn_num += 1
        self.turns.append(SimulationTurn(
            turn_number=turn_num,
            role=role,
            content=content,
            choices_presented=choices or [],
        ))

    def to_markdown(self) -> str:
        """Convert transcript to markdown format."""
        lines = [
            "# Simulation Transcript",
            "",
            f"- **Date:** {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Persona:** {self.persona}",
            f"- **Character:** {self.character_name} ({self.character_background})",
            f"- **Turns:** {len([t for t in self.turns if t.role == 'gm'])}",
            "",
            "---",
            "",
        ]

        current_turn = 0
        for turn in self.turns:
            if turn.role == "gm":
                current_turn = turn.turn_number
                lines.append(f"## Turn {current_turn}")
                lines.append("")
                lines.append("**GM:**")
                lines.append("")
                lines.append(turn.content)
                lines.append("")

                if turn.choices_presented:
                    lines.append("*Choices:*")
                    for i, choice in enumerate(turn.choices_presented, 1):
                        lines.append(f"{i}. {choice}")
                    lines.append("")

            else:  # player
                lines.append(f"**Player ({self.persona}):**")
                lines.append("")
                lines.append(turn.content)
                lines.append("")
                lines.append("---")
                lines.append("")

        # Add summary
        lines.append("## Summary")
        lines.append("")
        if self.player_stats:
            lines.append(f"- **Total decisions:** {self.player_stats.get('total_decisions', 0)}")
            lines.append(f"- **Improvisations:** {self.player_stats.get('improvisations', 0)}")
            lines.append(f"- **Enhancements accepted:** {self.player_stats.get('enhancements_accepted', 0)}")
            lines.append(f"- **Offers refused:** {self.player_stats.get('offers_refused', 0)}")
        lines.append("")

        return "\n".join(lines)

    def save(self, simulations_dir: Path) -> Path:
        """Save transcript to file. Returns the file path."""
        simulations_dir.mkdir(parents=True, exist_ok=True)

        timestamp = self.started_at.strftime("%Y-%m-%d_%H%M%S")
        filename = f"sim_{timestamp}_{self.persona}.md"
        filepath = simulations_dir / filename

        filepath.write_text(self.to_markdown(), encoding="utf-8")
        return filepath


def extract_choices(gm_text: str) -> list[str]:
    """Extract numbered choices from GM response."""
    choices = []

    # Pattern 1: Numbered list (1. Choice text)
    numbered = re.findall(r"^\s*(\d+)\.\s+(.+)$", gm_text, re.MULTILINE)
    if numbered:
        choices = [text.strip() for _, text in numbered]

    # Pattern 2: Formal choice block
    if "---CHOICE---" in gm_text:
        match = re.search(r"options:\s*\n((?:- .+\n?)+)", gm_text)
        if match:
            choices = [
                line.strip("- ").strip()
                for line in match.group(1).strip().split("\n")
                if line.strip().startswith("-")
            ]

    return choices


def run_simulation(
    agent,  # SentinelAgent - avoiding circular import
    player: AIPlayer,
    turns: int,
    manager: CampaignManager,
    verbose: bool = False,
) -> SimulationTranscript:
    """
    Run the simulation loop.

    Args:
        agent: The SentinelAgent (GM)
        player: The AIPlayer
        turns: Number of GM↔Player exchanges
        manager: Campaign manager
        verbose: Show detailed progress

    Returns:
        SimulationTranscript with all turns
    """
    # Initialize transcript
    character = player.character
    transcript = SimulationTranscript(
        persona=player.persona_name,
        character_name=character.name if character else "Unknown",
        character_background=character.background.value if character else "Unknown",
    )

    conversation: list[Message] = []

    # Initial prompt to start the scene
    char_info = ""
    if character:
        char_info = f"The player character is {character.name}, a {character.background.value}. "

    initial_prompt = (
        f"{char_info}"
        "Begin the campaign. Set an establishing scene that puts the character "
        "in an interesting situation with a choice to make."
    )

    # Get initial GM response
    gm_response = agent.respond(initial_prompt, conversation)

    # Extract choices and add to transcript
    choices = extract_choices(gm_response)
    transcript.add_turn("gm", gm_response, choices)

    # Update conversation
    conversation.append(Message(role="user", content=initial_prompt))
    conversation.append(Message(role="assistant", content=gm_response))

    # Run the simulation loop
    for turn_num in range(turns):
        # AI player responds
        player_action = player.respond(gm_response, choices)
        transcript.add_turn("player", player_action)

        # Update conversation with player action
        conversation.append(Message(role="user", content=player_action))

        # GM responds
        gm_response = agent.respond(player_action, conversation)

        # Extract new choices
        choices = extract_choices(gm_response)
        transcript.add_turn("gm", gm_response, choices)

        # Update conversation
        conversation.append(Message(role="assistant", content=gm_response))

    # Capture player stats
    transcript.player_stats = player.get_stats()

    return transcript


def create_simulation_character(manager: CampaignManager, persona: str) -> Character:
    """Create a character suited to the persona for simulation."""
    from ..state.schema import SocialEnergy

    # Pick background based on persona
    background_map = {
        "cautious": Background.WITNESS,
        "opportunist": Background.OPERATIVE,
        "principled": Background.PILGRIM,
        "chaotic": Background.GHOST,
    }

    background = background_map.get(persona, Background.SURVIVOR)

    # Create character with appropriate name
    name_map = {
        "cautious": "Val",
        "opportunist": "Kade",
        "principled": "Seren",
        "chaotic": "Glitch",
    }

    name = name_map.get(persona, "Cipher")

    character = Character(
        name=name,
        background=background,
        social_energy=SocialEnergy(current=75),
    )

    manager.add_character(character)
    return character
