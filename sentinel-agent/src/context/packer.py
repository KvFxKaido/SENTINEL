"""
Prompt Pack builder for SENTINEL.

Assembles bounded sections into a single prompt pack with deterministic
token budgets and strain-aware trimming.

Sections (ordered):
1. System / Identity (static)
2. Rules Reference (static, minimal)
3. Canonical State Snapshot (dynamic, always)
4. Campaign Memory Digest (dynamic, compressed)
5. Recent Transcript Window (dynamic, rolling)
6. Targeted Retrieval (dynamic, optional, budgeted)
7. User Input (current turn)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .tokenizer import count_tokens, truncate_to_budget, get_default_counter
from .window import RollingWindow, TranscriptBlock, WindowConfig


class PackSection(str, Enum):
    """Sections of the prompt pack, in order."""
    SYSTEM = "system"           # GM identity and philosophy
    RULES = "rules"             # Game mechanics reference
    STATE = "state"             # Current campaign state snapshot
    DIGEST = "digest"           # Campaign memory digest (compressed history)
    WINDOW = "window"           # Recent transcript blocks
    RETRIEVAL = "retrieval"     # Lore/history retrieval
    INPUT = "input"             # Current user input


@dataclass
class SectionBudget:
    """Token budget for a section."""
    tokens: int
    required: bool = True       # If True, section must be included
    can_truncate: bool = True   # If True, can be truncated to fit


# Default token budgets per section (~13,000 total for 16k context)
DEFAULT_BUDGETS: dict[PackSection, SectionBudget] = {
    PackSection.SYSTEM: SectionBudget(tokens=1500, required=True, can_truncate=False),
    PackSection.RULES: SectionBudget(tokens=2000, required=True, can_truncate=True),
    PackSection.STATE: SectionBudget(tokens=1500, required=True, can_truncate=True),
    PackSection.DIGEST: SectionBudget(tokens=2500, required=False, can_truncate=True),
    PackSection.WINDOW: SectionBudget(tokens=3500, required=True, can_truncate=True),
    PackSection.RETRIEVAL: SectionBudget(tokens=2000, required=False, can_truncate=True),
    PackSection.INPUT: SectionBudget(tokens=500, required=True, can_truncate=False),
}


class StrainTier(Enum):
    """Memory strain tiers based on context pressure."""
    NORMAL = "normal"       # < 0.70 - Full context available
    STRAIN_I = "strain_i"   # 0.70-0.85 - Reduced window, minimal retrieval
    STRAIN_II = "strain_ii"  # 0.85-0.95 - Scene recap, no retrieval
    STRAIN_III = "strain_iii"  # >= 0.95 - Minimal window, offer checkpoint

    @classmethod
    def from_pressure(cls, pressure: float) -> "StrainTier":
        """Determine strain tier from pressure ratio."""
        if pressure < 0.70:
            return cls.NORMAL
        elif pressure < 0.85:
            return cls.STRAIN_I
        elif pressure < 0.95:
            return cls.STRAIN_II
        else:
            return cls.STRAIN_III


@dataclass
class SectionContent:
    """Content for a single section."""
    section: PackSection
    content: str
    token_count: int
    truncated: bool = False
    original_tokens: int | None = None


@dataclass
class PackInfo:
    """Information about a packed prompt."""
    sections: list[SectionContent]
    total_tokens: int
    total_budget: int
    pressure: float
    strain_tier: StrainTier
    warnings: list[str] = field(default_factory=list)
    trimmed_blocks: int = 0
    scene_recap: str | None = None

    @property
    def is_over_budget(self) -> bool:
        return self.total_tokens > self.total_budget

    def get_section(self, section: PackSection) -> SectionContent | None:
        """Get content for a specific section."""
        for s in self.sections:
            if s.section == section:
                return s
        return None


class PromptPacker:
    """
    Builds prompt packs with deterministic token budgets.

    The packer assembles content from various sources into a single
    prompt pack that fits within context limits while preserving
    the most important information.
    """

    def __init__(
        self,
        budgets: dict[PackSection, SectionBudget] | None = None,
        total_budget: int = 13000,
    ):
        self.budgets = budgets or DEFAULT_BUDGETS.copy()
        self.total_budget = total_budget
        self._counter = get_default_counter()

    def pack(
        self,
        system: str = "",
        rules: str = "",
        state: str = "",
        digest: str = "",
        window: RollingWindow | None = None,
        retrieval: str = "",
        user_input: str = "",
    ) -> tuple[str, PackInfo]:
        """
        Pack content into a prompt with budget enforcement.

        Args:
            system: GM identity and philosophy
            rules: Game mechanics reference
            state: Current campaign state snapshot
            digest: Campaign memory digest
            window: Rolling window of transcript blocks
            retrieval: Lore/history retrieval content
            user_input: Current user input

        Returns:
            Tuple of (packed_prompt, pack_info)
        """
        sections: list[SectionContent] = []
        warnings: list[str] = []

        # Process each section in order
        section_contents = [
            (PackSection.SYSTEM, system),
            (PackSection.RULES, rules),
            (PackSection.STATE, state),
            (PackSection.DIGEST, digest),
            (PackSection.RETRIEVAL, retrieval),
            (PackSection.INPUT, user_input),
        ]

        for section, content in section_contents:
            if not content and not self.budgets[section].required:
                continue

            budget = self.budgets[section]
            token_count = self._counter.count(content)
            truncated = False
            original_tokens = None

            if token_count > budget.tokens:
                if budget.can_truncate:
                    original_tokens = token_count
                    content = self._counter.truncate_to_budget(content, budget.tokens)
                    token_count = self._counter.count(content)
                    truncated = True
                    warnings.append(
                        f"{section.value} truncated: {original_tokens} → {token_count} tokens"
                    )
                else:
                    warnings.append(
                        f"{section.value} over budget: {token_count} > {budget.tokens} tokens"
                    )

            sections.append(SectionContent(
                section=section,
                content=content,
                token_count=token_count,
                truncated=truncated,
                original_tokens=original_tokens,
            ))

        # Process window separately (it has special handling)
        window_content = ""
        trimmed_blocks = 0
        scene_recap = None

        if window:
            # Get strain tier to adjust window config
            current_total = sum(s.token_count for s in sections)
            preliminary_pressure = current_total / self.total_budget

            # Adjust window config based on strain
            if preliminary_pressure >= 0.70:
                window_config = WindowConfig.minimal()
            else:
                window_config = WindowConfig.standard()

            # Override window's config
            window.config = window_config
            window_budget = self.budgets[PackSection.WINDOW].tokens

            # Get window blocks
            window_blocks = window.get_window(budget_override=window_budget)
            trimmed_blocks = len(window.blocks) - len(window_blocks)

            # Format blocks as conversation
            window_content = self._format_window_blocks(window_blocks)
            window_tokens = self._counter.count(window_content)

            # Get scene recap if we trimmed blocks and are at strain II+
            if trimmed_blocks > 0 and preliminary_pressure >= 0.85:
                scene_recap = window.get_trimmed_summary()

            sections.append(SectionContent(
                section=PackSection.WINDOW,
                content=window_content,
                token_count=window_tokens,
                truncated=trimmed_blocks > 0,
            ))

        # Calculate totals
        total_tokens = sum(s.token_count for s in sections)
        pressure = total_tokens / self.total_budget
        strain_tier = StrainTier.from_pressure(pressure)

        # Build pack info
        pack_info = PackInfo(
            sections=sections,
            total_tokens=total_tokens,
            total_budget=self.total_budget,
            pressure=pressure,
            strain_tier=strain_tier,
            warnings=warnings,
            trimmed_blocks=trimmed_blocks,
            scene_recap=scene_recap,
        )

        # Assemble final prompt
        packed_prompt = self._assemble_prompt(sections, scene_recap)

        return packed_prompt, pack_info

    def _format_window_blocks(self, blocks: list[TranscriptBlock]) -> str:
        """Format transcript blocks as conversation history."""
        if not blocks:
            return ""

        lines = []
        for block in blocks:
            role_prefix = {
                "user": "PLAYER",
                "assistant": "GM",
                "system": "SYSTEM",
            }.get(block.role, "UNKNOWN")

            lines.append(f"[{role_prefix}]: {block.content}")

        return "\n\n".join(lines)

    def _assemble_prompt(
        self,
        sections: list[SectionContent],
        scene_recap: str | None = None,
    ) -> str:
        """Assemble sections into final prompt."""
        parts = []

        for section in sections:
            if not section.content:
                continue

            # Add section header for clarity
            header = self._section_header(section.section)
            if header:
                parts.append(f"## {header}\n\n{section.content}")
            else:
                parts.append(section.content)

        # Insert scene recap before window if present
        if scene_recap:
            # Find window section and insert recap before it
            for i, part in enumerate(parts):
                if "## Recent Conversation" in part or "## Conversation History" in part:
                    parts.insert(i, f"[{scene_recap}]")
                    break

        return "\n\n---\n\n".join(parts)

    def _section_header(self, section: PackSection) -> str | None:
        """Get display header for section."""
        headers = {
            PackSection.SYSTEM: None,  # System goes first without header
            PackSection.RULES: "Game Rules Reference",
            PackSection.STATE: "Current State",
            PackSection.DIGEST: "Campaign Memory",
            PackSection.WINDOW: "Recent Conversation",
            PackSection.RETRIEVAL: "Relevant Context",
            PackSection.INPUT: None,  # Input goes last without header
        }
        return headers.get(section)

    def adjust_for_strain(
        self,
        strain_tier: StrainTier,
    ) -> dict[PackSection, SectionBudget]:
        """
        Get adjusted budgets for a strain tier.

        Strain I: Reduced window, minimal retrieval
        Strain II: Scene recap instead of old window, no retrieval
        Strain III: Minimal window only, digest prominent
        """
        adjusted = self.budgets.copy()

        if strain_tier == StrainTier.STRAIN_I:
            # Reduce window, cut retrieval
            adjusted[PackSection.WINDOW] = SectionBudget(
                tokens=2500, required=True, can_truncate=True
            )
            adjusted[PackSection.RETRIEVAL] = SectionBudget(
                tokens=500, required=False, can_truncate=True
            )

        elif strain_tier == StrainTier.STRAIN_II:
            # Minimal window, no retrieval
            adjusted[PackSection.WINDOW] = SectionBudget(
                tokens=1500, required=True, can_truncate=True
            )
            adjusted[PackSection.RETRIEVAL] = SectionBudget(
                tokens=0, required=False, can_truncate=True
            )

        elif strain_tier == StrainTier.STRAIN_III:
            # Bare minimum window, digest gets more space
            adjusted[PackSection.WINDOW] = SectionBudget(
                tokens=1000, required=True, can_truncate=True
            )
            adjusted[PackSection.RETRIEVAL] = SectionBudget(
                tokens=0, required=False, can_truncate=True
            )
            adjusted[PackSection.DIGEST] = SectionBudget(
                tokens=3500, required=True, can_truncate=True
            )

        return adjusted

    def get_pressure(self, **kwargs: Any) -> float:
        """Calculate pressure without full packing."""
        total = 0
        for section, content in kwargs.items():
            if content:
                total += self._counter.count(str(content))
        return total / self.total_budget


def format_strain_notice(tier: StrainTier) -> str | None:
    """
    Get narrative text for strain tier.

    Returns text to be engine-inserted (not relying on model).
    """
    notices = {
        StrainTier.NORMAL: None,
        StrainTier.STRAIN_I: (
            "[Memory strain active — some earlier context condensed]"
        ),
        StrainTier.STRAIN_II: (
            "[Memory strain elevated — "
            "working from scene recap and key anchors only]"
        ),
        StrainTier.STRAIN_III: (
            "[Memory critical — context fragmenting. "
            "Consider /checkpoint to consolidate memory.]"
        ),
    }
    return notices.get(tier)
