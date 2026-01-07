"""
Tests for the context management module (prompt packing, rolling window, tokenizer).
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.context.tokenizer import (
    count_tokens,
    has_tiktoken,
    FallbackCounter,
    get_counter,
    truncate_to_budget,
)
from src.context.window import (
    RollingWindow,
    TranscriptBlock,
    BlockPriority,
    WindowConfig,
)
from src.context.packer import (
    PromptPacker,
    PackSection,
    SectionBudget,
    StrainTier,
    DEFAULT_BUDGETS,
    format_strain_notice,
)


# -----------------------------------------------------------------------------
# Tokenizer Tests
# -----------------------------------------------------------------------------

class TestTokenizer:
    """Tests for token counting."""

    def test_count_tokens_empty(self):
        """Empty string returns 0 tokens."""
        assert count_tokens("") == 0

    def test_count_tokens_basic(self):
        """Basic string returns non-zero tokens."""
        result = count_tokens("Hello, world!")
        assert result > 0
        assert result < 10  # Reasonable for short string

    def test_count_tokens_consistency(self):
        """Same string returns same count."""
        text = "The quick brown fox jumps over the lazy dog."
        assert count_tokens(text) == count_tokens(text)

    def test_fallback_counter(self):
        """Fallback counter uses character estimation."""
        counter = FallbackCounter(chars_per_token=4)
        # 40 chars / 4 = 10 tokens
        assert counter.count("a" * 40) == 10

    def test_truncate_to_budget(self):
        """Truncation respects token budget."""
        text = "word " * 1000  # Long text
        truncated = truncate_to_budget(text, max_tokens=50)
        assert count_tokens(truncated) <= 50

    def test_truncate_short_text(self):
        """Short text is not truncated."""
        text = "Hello"
        truncated = truncate_to_budget(text, max_tokens=100)
        assert truncated == text

    def test_get_counter_returns_protocol(self):
        """get_counter returns a valid TokenCounter."""
        counter = get_counter()
        assert hasattr(counter, "count")
        assert hasattr(counter, "truncate_to_budget")


# -----------------------------------------------------------------------------
# Block Priority Tests
# -----------------------------------------------------------------------------

class TestBlockPriority:
    """Tests for block priority system."""

    def test_priority_ordering(self):
        """Priorities are correctly ordered for trimming."""
        # SYSTEM should be lowest (trim first)
        assert BlockPriority.SYSTEM < BlockPriority.NARRATIVE
        assert BlockPriority.NARRATIVE < BlockPriority.INTEL
        assert BlockPriority.INTEL < BlockPriority.CHOICE

    def test_from_block_type_mapping(self):
        """Block types map to correct priorities."""
        assert BlockPriority.from_block_type("SYSTEM") == BlockPriority.SYSTEM
        assert BlockPriority.from_block_type("NARRATIVE") == BlockPriority.NARRATIVE
        assert BlockPriority.from_block_type("INTEL") == BlockPriority.INTEL
        assert BlockPriority.from_block_type("CHOICE") == BlockPriority.CHOICE

    def test_from_block_type_case_insensitive(self):
        """Block type lookup is case-insensitive for uppercase."""
        assert BlockPriority.from_block_type("narrative") == BlockPriority.NARRATIVE

    def test_from_block_type_history_types(self):
        """History types map to priorities."""
        assert BlockPriority.from_block_type("hinge") == BlockPriority.CHOICE
        assert BlockPriority.from_block_type("mission") == BlockPriority.INTEL
        assert BlockPriority.from_block_type("consequence") == BlockPriority.NARRATIVE


# -----------------------------------------------------------------------------
# TranscriptBlock Tests
# -----------------------------------------------------------------------------

class TestTranscriptBlock:
    """Tests for transcript block dataclass."""

    def make_block(
        self,
        role: str = "assistant",
        content: str = "Test content",
        block_type: str = "NARRATIVE",
        tags: list[str] | None = None,
    ) -> TranscriptBlock:
        """Helper to create test blocks."""
        return TranscriptBlock(
            id=str(uuid4()),
            timestamp=datetime.now(),
            role=role,
            content=content,
            block_type=block_type,
            tags=tags or [],
        )

    def test_priority_property(self):
        """Block returns correct priority."""
        block = self.make_block(block_type="CHOICE")
        assert block.priority == BlockPriority.CHOICE

    def test_is_anchor_with_hinge_tag(self):
        """Block with hinge tag is an anchor."""
        block = self.make_block(tags=["hinge:betrayal", "faction:nexus"])
        assert block.is_anchor is True

    def test_is_anchor_without_hinge_tag(self):
        """Block without hinge tag is not an anchor."""
        block = self.make_block(tags=["faction:nexus"])
        assert block.is_anchor is False

    def test_is_user_input(self):
        """User role blocks are identified correctly."""
        user_block = self.make_block(role="user")
        gm_block = self.make_block(role="assistant")
        assert user_block.is_user_input is True
        assert gm_block.is_user_input is False


# -----------------------------------------------------------------------------
# Rolling Window Tests
# -----------------------------------------------------------------------------

class TestRollingWindow:
    """Tests for rolling window behavior."""

    def make_blocks(self, count: int, with_anchors: bool = False) -> list[TranscriptBlock]:
        """Create a sequence of test blocks."""
        blocks = []
        for i in range(count):
            role = "user" if i % 2 == 0 else "assistant"
            tags = []
            if with_anchors and i == 5:
                tags = ["hinge:test_hinge"]
            blocks.append(TranscriptBlock(
                id=f"block_{i}",
                timestamp=datetime.now() + timedelta(minutes=i),
                role=role,
                content=f"Test content for block {i}. " * 10,
                block_type="NARRATIVE" if role == "assistant" else "CHOICE",
                tags=tags,
            ))
        return blocks

    def test_empty_window(self):
        """Empty window returns empty list."""
        window = RollingWindow()
        assert window.get_window() == []

    def test_add_block(self):
        """Adding blocks increases window size."""
        window = RollingWindow()
        blocks = self.make_blocks(5)
        for block in blocks:
            window.add_block(block)
        assert len(window) == 5

    def test_get_window_respects_config(self):
        """Window returns blocks up to config limit."""
        config = WindowConfig(default_blocks=5, token_budget=10000)
        blocks = self.make_blocks(20)
        window = RollingWindow(blocks=blocks, config=config)
        result = window.get_window()
        # Should get around 5 blocks (may vary based on must-keep)
        assert len(result) <= 10

    def test_must_keep_last_user_input(self):
        """Last user input is always kept."""
        blocks = self.make_blocks(10)
        # Last user input is block_8 (even index)
        window = RollingWindow(blocks=blocks, config=WindowConfig(default_blocks=3))
        result = window.get_window()
        result_ids = {b.id for b in result}
        assert "block_8" in result_ids

    def test_anchor_retention(self):
        """Anchor blocks are retained even if older."""
        blocks = self.make_blocks(20, with_anchors=True)
        config = WindowConfig(default_blocks=5, max_anchors=3, token_budget=5000)
        window = RollingWindow(blocks=blocks, config=config)
        result = window.get_window()
        result_ids = {b.id for b in result}
        # Block 5 has hinge tag, should be retained
        assert "block_5" in result_ids

    def test_chronological_order(self):
        """Returned blocks are in chronological order."""
        blocks = self.make_blocks(10)
        window = RollingWindow(blocks=blocks)
        result = window.get_window()
        timestamps = [b.timestamp for b in result]
        assert timestamps == sorted(timestamps)

    def test_trimmed_summary(self):
        """Trimmed summary describes dropped content."""
        blocks = self.make_blocks(50)
        config = WindowConfig(default_blocks=5, token_budget=1000)
        window = RollingWindow(blocks=blocks, config=config)
        summary = window.get_trimmed_summary()
        # Should have a summary since we're trimming a lot
        assert summary is not None or len(window.get_window()) == len(blocks)

    def test_clear(self):
        """Clear removes all blocks."""
        blocks = self.make_blocks(10)
        window = RollingWindow(blocks=blocks)
        window.clear()
        assert len(window) == 0


# -----------------------------------------------------------------------------
# Strain Tier Tests
# -----------------------------------------------------------------------------

class TestStrainTier:
    """Tests for memory strain tiers."""

    def test_normal_tier(self):
        """Low pressure is NORMAL tier."""
        assert StrainTier.from_pressure(0.50) == StrainTier.NORMAL
        assert StrainTier.from_pressure(0.69) == StrainTier.NORMAL

    def test_strain_i_tier(self):
        """70-85% pressure is STRAIN_I."""
        assert StrainTier.from_pressure(0.70) == StrainTier.STRAIN_I
        assert StrainTier.from_pressure(0.84) == StrainTier.STRAIN_I

    def test_strain_ii_tier(self):
        """85-95% pressure is STRAIN_II."""
        assert StrainTier.from_pressure(0.85) == StrainTier.STRAIN_II
        assert StrainTier.from_pressure(0.94) == StrainTier.STRAIN_II

    def test_strain_iii_tier(self):
        """95%+ pressure is STRAIN_III."""
        assert StrainTier.from_pressure(0.95) == StrainTier.STRAIN_III
        assert StrainTier.from_pressure(1.0) == StrainTier.STRAIN_III

    def test_strain_notices(self):
        """Each strain tier has appropriate notice."""
        assert format_strain_notice(StrainTier.NORMAL) is None
        assert "condensed" in format_strain_notice(StrainTier.STRAIN_I)
        assert "recap" in format_strain_notice(StrainTier.STRAIN_II)
        assert "checkpoint" in format_strain_notice(StrainTier.STRAIN_III)


# -----------------------------------------------------------------------------
# Prompt Packer Tests
# -----------------------------------------------------------------------------

class TestPromptPacker:
    """Tests for prompt packing."""

    def test_pack_empty(self):
        """Packing empty content succeeds."""
        packer = PromptPacker()
        prompt, info = packer.pack()
        assert info.total_tokens == 0
        assert info.pressure == 0

    def test_pack_basic_sections(self):
        """Basic sections are included in pack."""
        packer = PromptPacker()
        prompt, info = packer.pack(
            system="You are the GM.",
            rules="Roll d20.",
            state="Current mission: Test.",
            user_input="What happens next?",
        )
        assert "You are the GM" in prompt
        assert "Roll d20" in prompt
        assert "Current mission: Test" in prompt
        assert info.total_tokens > 0

    def test_pack_respects_budgets(self):
        """Pack respects section budgets."""
        # Create packer with small rules budget
        custom_budgets = DEFAULT_BUDGETS.copy()
        custom_budgets[PackSection.RULES] = SectionBudget(
            tokens=50, required=True, can_truncate=True
        )
        packer = PromptPacker(budgets=custom_budgets, total_budget=1000)
        # Create content that exceeds the small budget
        long_rules = "rule " * 500  # Much more than 50 tokens
        prompt, info = packer.pack(rules=long_rules)
        # Should have truncation warning
        assert any("truncated" in w for w in info.warnings)

    def test_pack_calculates_pressure(self):
        """Pack correctly calculates pressure."""
        packer = PromptPacker(total_budget=1000)
        prompt, info = packer.pack(
            system="Short system prompt.",
        )
        expected_pressure = info.total_tokens / 1000
        assert abs(info.pressure - expected_pressure) < 0.01

    def test_pack_determines_strain_tier(self):
        """Pack determines correct strain tier."""
        packer = PromptPacker(total_budget=100)
        # Create content that will cause high pressure
        prompt, info = packer.pack(
            system="system " * 50,
            rules="rules " * 50,
        )
        # Should be high strain with this much content in small budget
        assert info.strain_tier in [StrainTier.STRAIN_II, StrainTier.STRAIN_III]

    def test_adjust_for_strain(self):
        """Budget adjustments for strain tiers."""
        packer = PromptPacker()

        normal = packer.adjust_for_strain(StrainTier.NORMAL)
        strain_i = packer.adjust_for_strain(StrainTier.STRAIN_I)
        strain_iii = packer.adjust_for_strain(StrainTier.STRAIN_III)

        # Strain I should have smaller window
        assert strain_i[PackSection.WINDOW].tokens < normal[PackSection.WINDOW].tokens
        # Strain III should have no retrieval
        assert strain_iii[PackSection.RETRIEVAL].tokens == 0

    def test_pack_with_window(self):
        """Pack includes window content."""
        packer = PromptPacker()
        window = RollingWindow()
        window.add_block(TranscriptBlock(
            id="test",
            timestamp=datetime.now(),
            role="user",
            content="What do I see?",
            block_type="CHOICE",
        ))
        window.add_block(TranscriptBlock(
            id="test2",
            timestamp=datetime.now(),
            role="assistant",
            content="You see a vast corridor.",
            block_type="NARRATIVE",
        ))

        prompt, info = packer.pack(window=window)
        assert "PLAYER" in prompt or "What do I see" in prompt
        assert "GM" in prompt or "vast corridor" in prompt

    def test_default_budgets_sum(self):
        """Default budgets fit in 16k context."""
        total = sum(b.tokens for b in DEFAULT_BUDGETS.values())
        assert total <= 14000  # Leave headroom for 16k context

    def test_pack_info_get_section(self):
        """PackInfo can retrieve specific sections."""
        packer = PromptPacker()
        prompt, info = packer.pack(
            system="System content",
            rules="Rules content",
        )
        system_section = info.get_section(PackSection.SYSTEM)
        assert system_section is not None
        assert "System content" in system_section.content


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------

class TestContextIntegration:
    """Integration tests for context module."""

    def test_full_pack_workflow(self):
        """Test complete packing workflow."""
        # Setup
        packer = PromptPacker(total_budget=8000)
        window = RollingWindow()

        # Add some conversation
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            window.add_block(TranscriptBlock(
                id=f"block_{i}",
                timestamp=datetime.now() + timedelta(minutes=i),
                role=role,
                content=f"Message {i} content. " * 5,
                block_type="CHOICE" if role == "user" else "NARRATIVE",
            ))

        # Pack
        prompt, info = packer.pack(
            system="You are the GM for SENTINEL.",
            rules="Players roll d20 for checks.",
            state="Mission: Investigation. Party: 2 operatives.",
            digest="Previous session: Met with Nexus contact.",
            window=window,
            retrieval="Lore: Nexus controls the network.",
            user_input="I approach the guard.",
        )

        # Verify
        assert info.total_tokens > 0
        assert info.pressure > 0
        assert info.strain_tier in StrainTier
        assert "GM" in prompt
        assert "SENTINEL" in prompt

    def test_strain_progression(self):
        """Test that strain tiers progress correctly as content grows."""
        packer = PromptPacker(total_budget=500)

        # Start with low content
        _, info1 = packer.pack(system="Short")
        assert info1.strain_tier == StrainTier.NORMAL

        # Add more content
        _, info2 = packer.pack(
            system="Short",
            rules="Rules " * 50,
        )
        # Should be higher strain now
        assert info2.strain_tier.value >= info1.strain_tier.value
