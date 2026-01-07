"""
Rolling window management for transcript blocks.

Handles:
- Block priority retention (CHOICE > INTEL > NARRATIVE > SYSTEM)
- Anchor retention for hinge-tagged blocks
- Token-budget-aware trimming
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Literal


class BlockPriority(IntEnum):
    """
    Priority for block retention (higher = keep longer).

    Drop order: SYSTEM (0) → NARRATIVE (1) → INTEL (2) → CHOICE (3)
    """
    SYSTEM = 0      # Low-signal system chatter - drop first
    NARRATIVE = 1   # Long narrative blocks
    INTEL = 2       # Information blocks
    CHOICE = 3      # Player choice blocks - keep if possible

    @classmethod
    def from_block_type(cls, block_type: str) -> "BlockPriority":
        """Convert block type string to priority."""
        # Normalize to uppercase for standard block types
        normalized = block_type.upper()
        mapping = {
            "SYSTEM": cls.SYSTEM,
            "NARRATIVE": cls.NARRATIVE,
            "INTEL": cls.INTEL,
            "CHOICE": cls.CHOICE,
            # History types (also uppercase for lookup)
            "HINGE": cls.CHOICE,  # Hinges are high priority
            "MISSION": cls.INTEL,
            "FACTION_SHIFT": cls.INTEL,
            "CONSEQUENCE": cls.NARRATIVE,
            "CANON": cls.NARRATIVE,
        }
        return mapping.get(normalized, cls.NARRATIVE)


@dataclass
class TranscriptBlock:
    """
    A single block in the transcript.

    Represents one GM output or player input for context management.
    """
    id: str
    timestamp: datetime
    role: Literal["user", "assistant", "system"]
    content: str
    block_type: str = "NARRATIVE"  # NARRATIVE | INTEL | CHOICE | SYSTEM
    tags: list[str] = field(default_factory=list)
    token_count: int | None = None  # Cached token count

    @property
    def priority(self) -> BlockPriority:
        """Get retention priority for this block."""
        return BlockPriority.from_block_type(self.block_type)

    @property
    def is_anchor(self) -> bool:
        """Check if this block is an anchor (should be retained longer)."""
        # Hinge-tagged blocks are anchors
        return any(tag.startswith("hinge:") for tag in self.tags)

    @property
    def is_user_input(self) -> bool:
        """Check if this is a user input block."""
        return self.role == "user"


@dataclass
class WindowConfig:
    """Configuration for rolling window behavior."""
    # Block count limits
    default_blocks: int = 12
    min_blocks: int = 4
    max_blocks: int = 20

    # Anchor management
    max_anchors: int = 5      # Max hinge-tagged blocks to retain
    anchor_ttl_sessions: int = 3  # Sessions before anchor expires

    # Token budget (for recent window section)
    token_budget: int = 3500

    @classmethod
    def minimal(cls) -> "WindowConfig":
        """Minimal window for strain situations."""
        return cls(
            default_blocks=6,
            min_blocks=4,
            max_blocks=8,
            max_anchors=2,
            token_budget=2000,
        )

    @classmethod
    def standard(cls) -> "WindowConfig":
        """Standard window for normal operation."""
        return cls()

    @classmethod
    def expanded(cls) -> "WindowConfig":
        """Expanded window for deep context."""
        return cls(
            default_blocks=16,
            min_blocks=8,
            max_blocks=24,
            max_anchors=8,
            token_budget=5000,
        )


class RollingWindow:
    """
    Manages the rolling window of recent transcript blocks.

    Implements:
    - Token-budget-aware windowing
    - Priority-based retention (CHOICE > INTEL > NARRATIVE > SYSTEM)
    - Anchor retention for hinge-tagged blocks
    """

    def __init__(
        self,
        blocks: list[TranscriptBlock] | None = None,
        config: WindowConfig | None = None,
    ):
        self._blocks: list[TranscriptBlock] = blocks or []
        self.config = config or WindowConfig.standard()
        self._token_counter = None  # Lazy load

    @property
    def _counter(self):
        """Lazy-load token counter."""
        if self._token_counter is None:
            from .tokenizer import get_default_counter
            self._token_counter = get_default_counter()
        return self._token_counter

    def add_block(self, block: TranscriptBlock) -> None:
        """Add a block to the window."""
        # Calculate token count if not set
        if block.token_count is None:
            block.token_count = self._counter.count(block.content)
        self._blocks.append(block)

    def get_window(self, budget_override: int | None = None) -> list[TranscriptBlock]:
        """
        Get blocks that fit within the token budget.

        Returns blocks in chronological order, prioritizing:
        1. Always: last user input + last assistant response
        2. Anchors (hinge-tagged blocks) within anchor limit
        3. Higher priority blocks (CHOICE > INTEL > NARRATIVE > SYSTEM)
        4. More recent blocks

        Args:
            budget_override: Override token budget (uses config default if None)

        Returns:
            List of blocks that fit within budget, in chronological order
        """
        if not self._blocks:
            return []

        budget = budget_override or self.config.token_budget

        # Step 1: Identify must-keep blocks
        must_keep = self._get_must_keep_blocks()

        # Step 2: Get anchors (up to limit)
        anchors = self._get_anchor_blocks(exclude=must_keep)

        # Step 3: Get recent blocks up to default count
        recent = self._get_recent_blocks(
            count=self.config.default_blocks,
            exclude=must_keep | anchors,
        )

        # Step 4: Combine and fit within budget
        candidates = must_keep | anchors | recent
        return self._fit_to_budget(candidates, budget, must_keep)

    def _get_must_keep_blocks(self) -> set[str]:
        """Get IDs of blocks that must always be kept."""
        ids = set()
        if not self._blocks:
            return ids

        # Always keep last user input
        for block in reversed(self._blocks):
            if block.is_user_input:
                ids.add(block.id)
                break

        # Always keep last assistant response (if present after last user input)
        found_user = False
        for block in reversed(self._blocks):
            if block.is_user_input:
                found_user = True
            elif found_user and block.role == "assistant":
                ids.add(block.id)
                break

        # Always keep last CHOICE block if present
        for block in reversed(self._blocks):
            if block.block_type == "CHOICE":
                ids.add(block.id)
                break

        return ids

    def _get_anchor_blocks(self, exclude: set[str]) -> set[str]:
        """Get IDs of anchor blocks (hinge-tagged) up to limit."""
        anchors = []
        for block in reversed(self._blocks):
            if block.id not in exclude and block.is_anchor:
                anchors.append(block.id)
                if len(anchors) >= self.config.max_anchors:
                    break
        return set(anchors)

    def _get_recent_blocks(self, count: int, exclude: set[str]) -> set[str]:
        """Get IDs of most recent blocks not in exclude set."""
        recent = []
        for block in reversed(self._blocks):
            if block.id not in exclude:
                recent.append(block.id)
                if len(recent) >= count:
                    break
        return set(recent)

    def _fit_to_budget(
        self,
        candidate_ids: set[str],
        budget: int,
        must_keep: set[str],
    ) -> list[TranscriptBlock]:
        """
        Fit candidate blocks within token budget.

        Trims lowest-priority blocks first until budget is met.
        """
        # Get candidate blocks
        candidates = [b for b in self._blocks if b.id in candidate_ids]

        # Calculate total tokens
        total_tokens = sum(b.token_count or 0 for b in candidates)

        if total_tokens <= budget:
            return candidates  # Already fits

        # Need to trim - sort by priority (lowest first) then by recency (oldest first)
        # But never remove must_keep blocks
        removable = [b for b in candidates if b.id not in must_keep]
        removable.sort(key=lambda b: (b.priority, b.timestamp))

        # Remove blocks until within budget
        while total_tokens > budget and removable:
            removed = removable.pop(0)
            total_tokens -= removed.token_count or 0
            candidate_ids.discard(removed.id)

        # Return remaining blocks in chronological order
        result = [b for b in self._blocks if b.id in candidate_ids]
        return result

    def get_trimmed_summary(self) -> str | None:
        """
        Generate a summary of trimmed content (for Strain II+).

        Returns a "Scene Recap" paragraph summarizing trimmed blocks.
        """
        window_ids = {b.id for b in self.get_window()}
        trimmed = [b for b in self._blocks if b.id not in window_ids]

        if not trimmed:
            return None

        # Simple summary: count blocks by type
        by_type: dict[str, int] = {}
        for block in trimmed:
            by_type[block.block_type] = by_type.get(block.block_type, 0) + 1

        parts = []
        if by_type.get("NARRATIVE", 0):
            parts.append(f"{by_type['NARRATIVE']} narrative exchanges")
        if by_type.get("INTEL", 0):
            parts.append(f"{by_type['INTEL']} intel updates")
        if by_type.get("CHOICE", 0):
            parts.append(f"{by_type['CHOICE']} decision points")

        if not parts:
            return None

        return f"[Scene recap: {', '.join(parts)} earlier this session]"

    def clear(self) -> None:
        """Clear all blocks from the window."""
        self._blocks = []

    def __len__(self) -> int:
        return len(self._blocks)

    @property
    def total_tokens(self) -> int:
        """Get total token count of all blocks."""
        return sum(b.token_count or 0 for b in self._blocks)

    @property
    def blocks(self) -> list[TranscriptBlock]:
        """Get all blocks (read-only copy)."""
        return list(self._blocks)
