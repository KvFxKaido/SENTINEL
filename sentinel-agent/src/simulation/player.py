"""AI Player for simulation mode."""

from ..llm.base import LLMClient, Message, LLMResponse
from ..state.schema import Character
from .personas import PERSONAS, get_persona_system_prompt


class AIPlayer:
    """AI that plays SENTINEL as a character."""

    def __init__(
        self,
        client: LLMClient,
        persona: str = "cautious",
        character: Character | None = None,
    ):
        """
        Initialize AI player.

        Args:
            client: LLM client to use for responses
            persona: One of: cautious, opportunist, principled, chaotic
            character: Character being played (for name/background context)
        """
        self.client = client
        self.persona_name = persona
        self.persona = PERSONAS.get(persona, PERSONAS["cautious"])
        self.character = character
        self.decisions: list[str] = []  # Track key decisions made

    @property
    def character_name(self) -> str:
        """Get character name for prompts."""
        if self.character:
            return self.character.name
        return "the character"

    def respond(self, gm_text: str, choices: list[str] | None = None) -> str:
        """
        Generate player response to GM narration.

        Args:
            gm_text: The GM's narration/description
            choices: Optional list of presented choices

        Returns:
            Player action/dialogue as a string
        """
        # Build the user message with GM text and choices
        user_content = f"**GM says:**\n{gm_text}"

        if choices:
            user_content += "\n\n**Your options:**\n"
            for i, choice in enumerate(choices, 1):
                user_content += f"{i}. {choice}\n"
            user_content += "\nWhat do you do?"
        else:
            user_content += "\n\nWhat do you do?"

        # Get system prompt for persona
        system_prompt = get_persona_system_prompt(
            self.persona_name,
            self.character_name,
        )

        # Call LLM
        messages = [Message(role="user", content=user_content)]

        response = self.client.chat(
            messages=messages,
            system=system_prompt,
            temperature=0.8,  # Slightly higher for variety
            max_tokens=256,  # Keep responses concise
        )

        # Extract content from response
        if isinstance(response, LLMResponse):
            action = response.content.strip()
        else:
            action = str(response).strip()

        # Track significant decisions
        self._track_decision(action, choices)

        return action

    def _track_decision(self, action: str, choices: list[str] | None) -> None:
        """Track key decisions for summary stats."""
        action_lower = action.lower()

        # Track enhancement decisions
        if "accept" in action_lower and "enhancement" in action_lower:
            self.decisions.append("accepted_enhancement")
        elif "refuse" in action_lower or "decline" in action_lower:
            self.decisions.append("refused_offer")

        # Track if they picked a numbered choice or improvised
        if choices:
            picked_choice = any(
                action_lower.startswith(str(i)) or f"option {i}" in action_lower
                for i in range(1, len(choices) + 1)
            )
            if not picked_choice:
                self.decisions.append("improvised")

    def get_stats(self) -> dict:
        """Get summary statistics about player decisions."""
        return {
            "total_decisions": len(self.decisions),
            "improvisations": self.decisions.count("improvised"),
            "enhancements_accepted": self.decisions.count("accepted_enhancement"),
            "offers_refused": self.decisions.count("refused_offer"),
        }
