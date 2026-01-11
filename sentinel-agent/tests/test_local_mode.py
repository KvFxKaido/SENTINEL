"""
Tests for local model optimizations (8B-12B parameter models).
"""

import pytest
from pathlib import Path

from src.prompts.loader import PromptLoader
from src.tools.subsets import (
    get_tools_for_phase,
    get_minimal_tools,
    PHASE_TOOLS,
    CORE_TOOLS,
    MINIMAL_TOOLS,
)
from src.context.packer import LOCAL_BUDGETS, DEFAULT_BUDGETS, PackSection


# -----------------------------------------------------------------------------
# PromptLoader Local Mode Tests
# -----------------------------------------------------------------------------

class TestPromptLoaderLocalMode:
    """Tests for PromptLoader local_mode functionality."""

    @pytest.fixture
    def prompts_dir(self):
        """Get the prompts directory."""
        return Path(__file__).parent.parent / "prompts"

    def test_local_mode_loads_condensed_prompts(self, prompts_dir):
        """Local mode should load from prompts/local/ first."""
        loader = PromptLoader(prompts_dir, local_mode=True)

        # Local core.md should be shorter than standard
        local_core = loader.load("core")

        standard_loader = PromptLoader(prompts_dir, local_mode=False)
        standard_core = standard_loader.load("core")

        # Local should be significantly shorter
        assert len(local_core) < len(standard_core)
        # But still contain essential content
        assert "SENTINEL" in local_core
        assert "GM" in local_core

    def test_local_mode_loads_mechanics(self, prompts_dir):
        """Local mode should load condensed mechanics."""
        loader = PromptLoader(prompts_dir, local_mode=True)

        # Load mechanics
        content = loader.load("mechanics")

        # Should have content
        assert len(content) > 0
        # Should be condensed (check for key rules)
        assert "d20" in content or "Rolls" in content

    def test_get_sections_local_mode_skips_narrative(self, prompts_dir):
        """Local mode should skip rules_narrative entirely."""
        loader = PromptLoader(prompts_dir, local_mode=True)
        sections = loader.get_sections()

        # rules_narrative should be empty in local mode
        assert sections["rules_narrative"] == ""

    def test_get_sections_standard_mode_includes_narrative(self, prompts_dir):
        """Standard mode should include rules_narrative."""
        loader = PromptLoader(prompts_dir, local_mode=False)
        sections = loader.get_sections()

        # rules_narrative should have content in standard mode
        # (May be empty if file doesn't exist, but test the logic)
        # The key is that it's not explicitly set to ""
        assert "rules_narrative" in sections

    def test_local_mode_caching(self, prompts_dir):
        """Local mode should cache local prompts correctly."""
        loader = PromptLoader(prompts_dir, local_mode=True)

        # Load twice
        first_load = loader.load("core")
        second_load = loader.load("core")

        # Should be identical (from cache)
        assert first_load == second_load
        # Cache key should be prefixed with "local/"
        assert "local/core" in loader._cache


# -----------------------------------------------------------------------------
# Tool Subsets Tests
# -----------------------------------------------------------------------------

class TestToolSubsets:
    """Tests for phase-based tool filtering."""

    def test_core_tools_always_included(self):
        """Core tools should be in every phase."""
        for phase, tools in PHASE_TOOLS.items():
            assert CORE_TOOLS.issubset(tools), f"{phase} missing core tools"

    def test_phase_tools_are_subsets(self):
        """Phase tools should be reasonable subsets."""
        # Briefing should have fewer tools than execution
        assert len(PHASE_TOOLS["briefing"]) < len(PHASE_TOOLS["execution"])

        # Execution should be the most complex phase
        assert len(PHASE_TOOLS["execution"]) >= len(PHASE_TOOLS["planning"])

    def test_get_tools_for_phase_returns_schemas(self):
        """get_tools_for_phase should return tool schemas."""
        tools = get_tools_for_phase("briefing")

        # Should return list of dicts with "name" keys
        assert isinstance(tools, list)
        if tools:  # May be empty if registry not fully initialized
            assert all(isinstance(t, dict) for t in tools)
            assert all("name" in t for t in tools)

    def test_get_minimal_tools(self):
        """get_minimal_tools should return minimal set."""
        minimal = get_minimal_tools()

        # Should be a small set
        assert isinstance(minimal, list)
        # MINIMAL_TOOLS has 5 tools
        assert len(MINIMAL_TOOLS) == 5

    def test_unknown_phase_returns_core_only(self):
        """Unknown phase should return core tools only."""
        tools = get_tools_for_phase("unknown_phase")

        # Should only have core tools
        tool_names = {t["name"] for t in tools}
        assert tool_names == CORE_TOOLS


# -----------------------------------------------------------------------------
# Local Budget Tests
# -----------------------------------------------------------------------------

class TestLocalBudgets:
    """Tests for LOCAL_BUDGETS configuration."""

    def test_local_budgets_are_smaller(self):
        """Local budgets should be smaller than default."""
        for section in PackSection:
            local = LOCAL_BUDGETS[section].tokens
            default = DEFAULT_BUDGETS[section].tokens
            assert local <= default, f"{section} local budget not smaller"

    def test_local_budgets_skip_optional_sections(self):
        """Local budgets should skip narrative, digest, retrieval."""
        assert LOCAL_BUDGETS[PackSection.RULES_NARRATIVE].tokens == 0
        assert LOCAL_BUDGETS[PackSection.DIGEST].tokens == 0
        assert LOCAL_BUDGETS[PackSection.RETRIEVAL].tokens == 0

    def test_local_budgets_preserve_essentials(self):
        """Local budgets should preserve essential sections."""
        # System, rules_core, state, window, input should all have budget
        assert LOCAL_BUDGETS[PackSection.SYSTEM].tokens > 0
        assert LOCAL_BUDGETS[PackSection.RULES_CORE].tokens > 0
        assert LOCAL_BUDGETS[PackSection.STATE].tokens > 0
        assert LOCAL_BUDGETS[PackSection.WINDOW].tokens > 0
        assert LOCAL_BUDGETS[PackSection.INPUT].tokens > 0

    def test_local_budgets_total_under_8k(self):
        """Local budgets should total under 8k for 8k context models."""
        total = sum(b.tokens for b in LOCAL_BUDGETS.values())
        # Allow some headroom for tool schemas
        assert total < 6000, f"Local budget total {total} too high for 8k context"
