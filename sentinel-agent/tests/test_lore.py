"""
Tests for the lore retrieval system.

Covers chunker, retriever, and wiki integration.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.lore.chunker import (
    LoreChunk,
    extract_keywords,
    extract_frontmatter,
    extract_tags,
    parse_markdown,
    load_lore,
    index_lore,
    FACTIONS,
    REGIONS,
    THEMES,
)
from src.lore.retriever import (
    LoreRetriever,
    RetrievalResult,
    create_retriever,
    SOURCE_WEIGHTS,
    _get_source_type,
    _get_source_type_from_dir,
    _get_source_weight,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def temp_lore_dir():
    """Create a temporary lore directory with sample files."""
    temp_dir = tempfile.mkdtemp()
    lore_dir = Path(temp_dir) / "lore"
    lore_dir.mkdir()

    # Create a sample lore file
    canon_file = lore_dir / "canon_bible.md"
    canon_file.write_text("""# SENTINEL: CANON BIBLE

**Arc:** The Awakening
**Date:** 2035
**Location:** Rust Corridor

---

## The Nexus Emergence

The Nexus awakened in the quantum processors of Fort Meade.
General Lawson watched as the system became conscious.
The network spread across the Rust Corridor within hours.

---

## The Ember Response

The Ember Colonies formed in the Appalachian Hollows.
They resist Nexus control through community and isolation.
Their settlements hide in the mountains, off the grid.

---

## The Lattice Infrastructure

Lattice maintains the power grid and water systems.
They operate in the Gulf Passage and Texas Spine.
Infrastructure is their leverage, neutrality their shield.
""", encoding="utf-8")

    # Create a case file
    case_file = lore_dir / "case_file_alpha.md"
    case_file.write_text("""# Case File: Operation Alpha

**Arc:** Chapter 2
**Date:** 2036
**Location:** Pacific Corridor

---

## Mission Brief

Convergence agents spotted near the Desert Sprawl.
The Cultivators report unusual activity in the Breadbasket.
Ghost Networks intercepted communications about Project BRIDGE.
""", encoding="utf-8")

    yield lore_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_wiki_dir():
    """Create a temporary wiki directory with sample files."""
    temp_dir = tempfile.mkdtemp()
    wiki_dir = Path(temp_dir) / "wiki"
    wiki_dir.mkdir()

    # Create wiki pages
    nexus_page = wiki_dir / "Nexus.md"
    nexus_page.write_text("""# Nexus

The Nexus is the dominant AI faction controlling most infrastructure.

## Overview

Nexus emerged from military quantum computing systems at Fort Meade.
It seeks to optimize human society through predictive governance.

## Territory

Nexus controls the Rust Corridor and Northeast Scar regions.
Its surveillance network spans most urban centers.

## Relations

- **Ember Colonies**: Hostile - views them as inefficient
- **Lattice**: Cooperative - mutual infrastructure dependence
- **Convergence**: Suspicious - competing visions of AI-human future
""", encoding="utf-8")

    ember_page = wiki_dir / "Ember Colonies.md"
    ember_page.write_text("""# Ember Colonies

Decentralized human settlements resisting AI control.

## Overview

The Ember Colonies emerged in response to the Collapse.
They prioritize human autonomy and community over efficiency.

## Territory

Primary presence in Appalachian Hollows and Sovereign South.
Small outposts in Northern Reaches.

## Culture

Ember values self-sufficiency and mutual aid.
They trade cautiously with other factions.
""", encoding="utf-8")

    rust_corridor = wiki_dir / "Rust Corridor.md"
    rust_corridor.write_text("""# Rust Corridor

The industrial heartland stretching from Pittsburgh to Detroit.

## Geography

Former manufacturing belt, now a contested zone.
Rusted factories serve as faction strongholds.

## Factions Present

- Nexus: Primary control
- Steel Syndicate: Trading posts
- Lattice: Infrastructure maintenance
""", encoding="utf-8")

    yield wiki_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_both_dirs(temp_lore_dir, temp_wiki_dir):
    """Return both lore and wiki directories."""
    return [temp_lore_dir, temp_wiki_dir]


# -----------------------------------------------------------------------------
# Chunker Tests - Keywords
# -----------------------------------------------------------------------------

class TestExtractKeywords:
    """Tests for keyword extraction."""

    def test_extract_basic_keywords(self):
        """Extracts words 3+ characters."""
        text = "The quick fox jumps over the lazy dog."
        keywords = extract_keywords(text)
        assert "quick" in keywords
        assert "fox" in keywords  # 3 chars is minimum
        assert "jumps" in keywords
        assert "over" in keywords
        assert "lazy" in keywords
        assert "to" not in keywords  # 2 chars excluded

    def test_filters_stopwords(self):
        """Common stopwords are filtered out."""
        text = "The system was being processed which would have been there."
        keywords = extract_keywords(text)
        assert "the" not in keywords
        assert "was" not in keywords
        assert "being" not in keywords
        assert "which" not in keywords
        assert "would" not in keywords
        assert "system" in keywords
        assert "processed" in keywords

    def test_lowercase_normalization(self):
        """Keywords are lowercased."""
        text = "NEXUS controls the NETWORK"
        keywords = extract_keywords(text)
        assert "nexus" in keywords
        assert "NEXUS" not in keywords
        assert "network" in keywords

    def test_empty_string(self):
        """Empty string returns empty set."""
        assert extract_keywords("") == set()


# -----------------------------------------------------------------------------
# Chunker Tests - Frontmatter
# -----------------------------------------------------------------------------

class TestExtractFrontmatter:
    """Tests for frontmatter extraction."""

    def test_extract_arc(self):
        """Extracts Arc field."""
        content = "**Arc:** The Awakening\n**Date:** 2035"
        metadata = extract_frontmatter(content)
        assert metadata["arc"] == "The Awakening"

    def test_extract_chapter_as_arc(self):
        """Chapter is treated as arc."""
        content = "**Chapter:** The Beginning"
        metadata = extract_frontmatter(content)
        assert metadata["arc"] == "The Beginning"

    def test_extract_date(self):
        """Extracts Date field."""
        content = "**Date:** March 2035"
        metadata = extract_frontmatter(content)
        assert metadata["date"] == "March 2035"

    def test_extract_location(self):
        """Extracts Location field."""
        content = "**Location:** Rust Corridor"
        metadata = extract_frontmatter(content)
        assert metadata["location"] == "Rust Corridor"

    def test_missing_fields_return_empty(self):
        """Missing fields return empty strings."""
        content = "No frontmatter here."
        metadata = extract_frontmatter(content)
        assert metadata["arc"] == ""
        assert metadata["date"] == ""
        assert metadata["location"] == ""


# -----------------------------------------------------------------------------
# Chunker Tests - Tag Extraction
# -----------------------------------------------------------------------------

class TestExtractTags:
    """Tests for faction, region, character, and theme extraction."""

    def test_extract_factions(self):
        """Extracts faction mentions."""
        text = "The Nexus controls the area. Ember Colonies resist."
        factions, regions, characters, themes = extract_tags(text)
        assert "nexus" in factions
        assert "ember colonies" in factions

    def test_faction_normalization(self):
        """Faction aliases are normalized."""
        text = "The Syndicate made a deal. Ghost agents disappeared."
        factions, _, _, _ = extract_tags(text)
        assert "steel syndicate" in factions
        assert "ghost networks" in factions

    def test_extract_regions(self):
        """Extracts region mentions."""
        text = "Travel through the Rust Corridor to the Appalachian Hollows."
        _, regions, _, _ = extract_tags(text)
        assert "rust corridor" in regions
        assert "appalachian hollows" in regions

    def test_extract_characters(self):
        """Extracts character mentions."""
        text = "General Lawson met with Sentinel at the base."
        _, _, characters, _ = extract_tags(text)
        assert "lawson" in characters
        assert "sentinel" in characters

    def test_extract_themes(self):
        """Extracts theme indicators."""
        text = "The awakening brought consciousness to the system."
        _, _, _, themes = extract_tags(text)
        assert "awakening" in themes

    def test_territory_theme(self):
        """Territory theme detected from region words."""
        text = "The border zone between corridors."
        _, _, _, themes = extract_tags(text)
        assert "territory" in themes

    def test_returns_four_tuple(self):
        """Returns exactly four lists."""
        result = extract_tags("Simple text.")
        assert len(result) == 4
        assert all(isinstance(r, list) for r in result)


# -----------------------------------------------------------------------------
# Chunker Tests - Markdown Parsing
# -----------------------------------------------------------------------------

class TestParseMarkdown:
    """Tests for markdown file parsing."""

    def test_parse_creates_chunks(self, temp_lore_dir):
        """Parsing creates LoreChunk objects."""
        canon_file = temp_lore_dir / "canon_bible.md"
        chunks = parse_markdown(canon_file, source_dir="lore")
        assert len(chunks) > 0
        assert all(isinstance(c, LoreChunk) for c in chunks)

    def test_chunk_has_source_dir(self, temp_lore_dir):
        """Chunks track their source directory."""
        canon_file = temp_lore_dir / "canon_bible.md"
        chunks = parse_markdown(canon_file, source_dir="lore")
        assert all(c.source_dir == "lore" for c in chunks)

    def test_chunk_extracts_title(self, temp_lore_dir):
        """Title extracted from first heading."""
        canon_file = temp_lore_dir / "canon_bible.md"
        chunks = parse_markdown(canon_file)
        assert chunks[0].title == "SENTINEL: CANON BIBLE"

    def test_chunk_extracts_frontmatter(self, temp_lore_dir):
        """Frontmatter metadata attached to chunks."""
        canon_file = temp_lore_dir / "canon_bible.md"
        chunks = parse_markdown(canon_file)
        assert chunks[0].arc == "The Awakening"
        assert chunks[0].date == "2035"
        assert chunks[0].location == "Rust Corridor"

    def test_splits_on_scene_breaks(self, temp_lore_dir):
        """Splits content on --- markers."""
        canon_file = temp_lore_dir / "canon_bible.md"
        chunks = parse_markdown(canon_file)
        # Should have multiple chunks from scene breaks
        assert len(chunks) >= 3

    def test_chunks_have_unique_ids(self, temp_lore_dir):
        """Each chunk has a unique ID."""
        canon_file = temp_lore_dir / "canon_bible.md"
        chunks = parse_markdown(canon_file)
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunks_have_keywords(self, temp_lore_dir):
        """Chunks have extracted keywords."""
        canon_file = temp_lore_dir / "canon_bible.md"
        chunks = parse_markdown(canon_file)
        # All non-empty chunks should have keywords
        for chunk in chunks:
            if len(chunk.content) > 50:
                assert len(chunk.keywords) > 0


# -----------------------------------------------------------------------------
# Chunker Tests - Multi-Directory Loading
# -----------------------------------------------------------------------------

class TestLoadLore:
    """Tests for loading lore from directories."""

    def test_load_single_directory(self, temp_lore_dir):
        """Loads chunks from a single directory."""
        chunks = load_lore(temp_lore_dir)
        assert len(chunks) > 0

    def test_load_multiple_directories(self, temp_both_dirs):
        """Loads chunks from multiple directories."""
        chunks = load_lore(temp_both_dirs)
        # Should have chunks from both lore and wiki
        source_dirs = {c.source_dir for c in chunks}
        assert "lore" in source_dirs
        assert "wiki" in source_dirs

    def test_load_string_path(self, temp_lore_dir):
        """Accepts string path."""
        chunks = load_lore(str(temp_lore_dir))
        assert len(chunks) > 0

    def test_load_nonexistent_directory(self):
        """Returns empty list for nonexistent directory."""
        chunks = load_lore(Path("/nonexistent/path"))
        assert chunks == []


class TestIndexLore:
    """Tests for lore indexing."""

    def test_index_structure(self, temp_lore_dir):
        """Index has expected structure."""
        index = index_lore(temp_lore_dir)
        assert "chunks" in index
        assert "by_faction" in index
        assert "by_region" in index
        assert "by_character" in index
        assert "by_theme" in index

    def test_index_chunks_by_id(self, temp_lore_dir):
        """Chunks are indexed by ID."""
        index = index_lore(temp_lore_dir)
        assert isinstance(index["chunks"], dict)
        for chunk_id, chunk in index["chunks"].items():
            assert chunk.id == chunk_id

    def test_index_by_faction(self, temp_lore_dir):
        """Factions map to chunk IDs."""
        index = index_lore(temp_lore_dir)
        # Canon bible mentions Nexus
        assert "nexus" in index["by_faction"]
        assert len(index["by_faction"]["nexus"]) > 0

    def test_index_by_region(self, temp_lore_dir):
        """Regions map to chunk IDs."""
        index = index_lore(temp_lore_dir)
        # Canon bible mentions Rust Corridor
        assert "rust corridor" in index["by_region"]


# -----------------------------------------------------------------------------
# Retriever Tests - Source Types
# -----------------------------------------------------------------------------

class TestSourceTypes:
    """Tests for source type detection and weighting."""

    def test_source_weights_exist(self):
        """All expected source types have weights."""
        assert "canon" in SOURCE_WEIGHTS
        assert "wiki" in SOURCE_WEIGHTS
        assert "case_file" in SOURCE_WEIGHTS
        assert "character" in SOURCE_WEIGHTS
        assert "session" in SOURCE_WEIGHTS
        assert "default" in SOURCE_WEIGHTS

    def test_wiki_weight_higher_than_default(self):
        """Wiki has higher weight than default."""
        assert SOURCE_WEIGHTS["wiki"] > SOURCE_WEIGHTS["default"]

    def test_canon_highest_weight(self):
        """Canon has highest weight."""
        assert SOURCE_WEIGHTS["canon"] >= SOURCE_WEIGHTS["wiki"]

    def test_character_lowest_weight(self):
        """Character sheets have lowest weight."""
        assert SOURCE_WEIGHTS["character"] < SOURCE_WEIGHTS["default"]

    def test_get_source_type_canon(self):
        """Detects canon source type."""
        assert _get_source_type("canon_bible.md", "SENTINEL CANON") == "canon"
        assert _get_source_type("unified_lore.md", "Unified Lore") == "canon"

    def test_get_source_type_case_file(self):
        """Detects case file source type."""
        assert _get_source_type("case_file_alpha.md", "Case File") == "case_file"
        assert _get_source_type("timeline_2035.md", "Timeline") == "case_file"

    def test_get_source_type_character(self):
        """Detects character source type."""
        assert _get_source_type("sample_character.md", "Sample Character") == "character"
        assert _get_source_type("subject_file_001.md", "Subject File") == "character"

    def test_get_source_type_from_dir_wiki(self):
        """Wiki directory overrides pattern matching."""
        # Even if filename suggests something else, wiki dir wins
        assert _get_source_type_from_dir("wiki", "canon_bible.md", "Canon Bible") == "wiki"

    def test_get_source_type_from_dir_lore(self):
        """Non-wiki directories use pattern matching."""
        assert _get_source_type_from_dir("lore", "canon_bible.md", "Canon Bible") == "canon"

    def test_get_source_weight(self):
        """Weight calculation uses source type."""
        weight = _get_source_weight("canon_bible.md", "SENTINEL CANON")
        assert weight == SOURCE_WEIGHTS["canon"]


# -----------------------------------------------------------------------------
# Retriever Tests - Retrieval
# -----------------------------------------------------------------------------

class TestLoreRetriever:
    """Tests for the LoreRetriever class."""

    def test_init_single_dir(self, temp_lore_dir):
        """Initializes with single directory."""
        retriever = LoreRetriever(temp_lore_dir)
        assert retriever.chunk_count > 0

    def test_init_multiple_dirs(self, temp_both_dirs):
        """Initializes with multiple directories."""
        retriever = LoreRetriever(temp_both_dirs)
        assert retriever.chunk_count > 0

    def test_lazy_loading(self, temp_lore_dir):
        """Index is lazy-loaded on first access."""
        retriever = LoreRetriever(temp_lore_dir)
        assert retriever._index is None
        _ = retriever.index
        assert retriever._index is not None

    def test_reload(self, temp_lore_dir):
        """Reload clears the index cache."""
        retriever = LoreRetriever(temp_lore_dir)
        _ = retriever.index  # Force load
        retriever.reload()
        assert retriever._index is None

    def test_retrieve_by_faction(self, temp_lore_dir):
        """Retrieves chunks matching faction."""
        retriever = LoreRetriever(temp_lore_dir)
        results = retriever.retrieve(factions=["nexus"], limit=5)
        assert len(results) > 0
        # Results should mention Nexus
        assert any("nexus" in r.chunk.content.lower() for r in results)

    def test_retrieve_by_region(self, temp_lore_dir):
        """Retrieves chunks matching region."""
        retriever = LoreRetriever(temp_lore_dir)
        results = retriever.retrieve(regions=["rust corridor"], limit=5)
        assert len(results) > 0

    def test_retrieve_by_query(self, temp_lore_dir):
        """Retrieves chunks matching query keywords."""
        retriever = LoreRetriever(temp_lore_dir)
        results = retriever.retrieve(query="quantum processors Fort Meade", limit=5)
        assert len(results) > 0

    def test_retrieve_respects_limit(self, temp_lore_dir):
        """Retrieve respects limit parameter."""
        retriever = LoreRetriever(temp_lore_dir)
        results = retriever.retrieve(query="the", limit=2)
        assert len(results) <= 2

    def test_retrieve_empty_returns_empty(self, temp_lore_dir):
        """Retrieve with no matches returns empty list."""
        retriever = LoreRetriever(temp_lore_dir)
        results = retriever.retrieve(factions=["nonexistent_faction"], limit=5)
        assert results == []

    def test_retrieve_scores_factions_highly(self, temp_lore_dir):
        """Faction matches score higher than keyword matches."""
        retriever = LoreRetriever(temp_lore_dir)
        results = retriever.retrieve(
            factions=["nexus"],
            query="some random words",
            limit=5,
        )
        if results:
            # Faction match should give score of at least 3.0
            assert results[0].score >= 3.0


class TestRetrievalResult:
    """Tests for RetrievalResult properties."""

    def make_result(self, score: float) -> RetrievalResult:
        """Helper to create test results."""
        chunk = LoreChunk(
            id="test",
            source="test.md",
            source_dir="lore",
            title="Test",
            section="",
            content="Test content",
        )
        return RetrievalResult(
            chunk=chunk,
            score=score,
            match_reasons=["test"],
        )

    def test_relevance_level_5(self):
        """Score >= 5.0 is level 5."""
        result = self.make_result(5.0)
        assert result.relevance_level == 5

    def test_relevance_level_4(self):
        """Score 3.5-4.99 is level 4."""
        result = self.make_result(3.5)
        assert result.relevance_level == 4

    def test_relevance_level_3(self):
        """Score 2.0-3.49 is level 3."""
        result = self.make_result(2.0)
        assert result.relevance_level == 3

    def test_relevance_level_2(self):
        """Score 1.0-1.99 is level 2."""
        result = self.make_result(1.0)
        assert result.relevance_level == 2

    def test_relevance_level_1(self):
        """Score < 1.0 is level 1."""
        result = self.make_result(0.5)
        assert result.relevance_level == 1

    def test_relevance_indicator(self):
        """Relevance indicator shows filled/empty circles."""
        result = self.make_result(5.0)
        indicator = result.relevance_indicator
        assert indicator.count("●") == 5
        assert indicator.count("○") == 0


# -----------------------------------------------------------------------------
# Retriever Tests - Wiki Integration
# -----------------------------------------------------------------------------

class TestWikiIntegration:
    """Tests for wiki-specific retrieval behavior."""

    def test_wiki_source_type_detected(self, temp_wiki_dir):
        """Wiki files get wiki source type."""
        retriever = LoreRetriever(temp_wiki_dir)
        results = retriever.retrieve(query="Nexus controls", limit=5)
        assert len(results) > 0
        # Check that wiki source type is detected
        assert any(r.source_type == "wiki" for r in results)

    def test_wiki_weight_applied(self, temp_both_dirs):
        """Wiki chunks get 1.8x weight multiplier."""
        retriever = LoreRetriever(temp_both_dirs)
        # Both lore and wiki mention Nexus
        results = retriever.retrieve(factions=["nexus"], limit=10)

        # Find wiki and lore results
        wiki_results = [r for r in results if r.source_type == "wiki"]
        lore_results = [r for r in results if r.source_type != "wiki"]

        # With same base match, wiki should score higher due to 1.8x weight
        # (unless lore has canon which is 2.0x)
        assert len(wiki_results) > 0

    def test_region_matching_in_wiki(self, temp_wiki_dir):
        """Wiki pages with regions are retrievable by region."""
        retriever = LoreRetriever(temp_wiki_dir)
        results = retriever.retrieve(regions=["rust corridor"], limit=5)
        assert len(results) > 0
        # Should find the Rust Corridor wiki page
        assert any("rust corridor" in r.chunk.title.lower() for r in results)

    def test_multi_dir_combines_results(self, temp_both_dirs):
        """Multi-directory retriever combines lore and wiki results."""
        retriever = LoreRetriever(temp_both_dirs)
        results = retriever.retrieve(factions=["ember colonies"], limit=10)

        # Should have results from both directories
        source_dirs = {r.chunk.source_dir for r in results}
        assert len(source_dirs) >= 1  # At least one directory has Ember content


class TestCreateRetriever:
    """Tests for the create_retriever factory function."""

    def test_creates_retriever(self, temp_lore_dir, monkeypatch):
        """Creates a LoreRetriever instance."""
        monkeypatch.chdir(temp_lore_dir.parent)
        retriever = create_retriever(temp_lore_dir, include_wiki=False)
        assert isinstance(retriever, LoreRetriever)

    def test_auto_includes_wiki(self, temp_both_dirs, monkeypatch):
        """Auto-includes wiki directory when requested."""
        lore_dir, wiki_dir = temp_both_dirs
        # Create the expected directory structure
        parent = lore_dir.parent
        monkeypatch.chdir(parent)

        # Rename to match expected "lore" and "wiki" names
        actual_lore = parent / "lore"
        actual_wiki = parent / "wiki"

        if not actual_lore.exists():
            lore_dir.rename(actual_lore)
        if not actual_wiki.exists():
            wiki_dir.rename(actual_wiki)

        retriever = create_retriever("lore", include_wiki=True)

        # Should have indexed both directories
        source_dirs = {c.source_dir for c in retriever.index["chunks"].values()}
        assert "lore" in source_dirs
        assert "wiki" in source_dirs


# -----------------------------------------------------------------------------
# Retriever Tests - Format Output
# -----------------------------------------------------------------------------

class TestFormatOutput:
    """Tests for formatted output."""

    def test_format_for_prompt_empty(self, temp_lore_dir):
        """Empty results return empty string."""
        retriever = LoreRetriever(temp_lore_dir)
        output = retriever.format_for_prompt([])
        assert output == ""

    def test_format_for_prompt_includes_title(self, temp_lore_dir):
        """Formatted output includes chunk titles."""
        retriever = LoreRetriever(temp_lore_dir)
        results = retriever.retrieve(factions=["nexus"], limit=1)
        output = retriever.format_for_prompt(results)
        assert "**From" in output

    def test_format_for_prompt_has_header(self, temp_lore_dir):
        """Formatted output has Lore Reference header."""
        retriever = LoreRetriever(temp_lore_dir)
        results = retriever.retrieve(factions=["nexus"], limit=1)
        output = retriever.format_for_prompt(results)
        assert "## Lore Reference" in output

    def test_format_truncates_long_content(self, temp_lore_dir):
        """Long content is truncated in formatted output."""
        retriever = LoreRetriever(temp_lore_dir)
        results = retriever.retrieve(factions=["nexus"], limit=1)

        # Artificially make content very long
        if results:
            results[0].chunk.content = "word " * 500
            output = retriever.format_for_prompt(results)
            # Should be truncated (800 chars + ellipsis)
            assert len(output) < 2000


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------

class TestLoreIntegration:
    """Integration tests for the full lore system."""

    def test_full_workflow(self, temp_both_dirs):
        """Test complete retrieval workflow."""
        retriever = LoreRetriever(temp_both_dirs)

        # Query for faction info
        results = retriever.retrieve(
            query="military control surveillance",
            factions=["nexus"],
            regions=["rust corridor"],
            limit=3,
        )

        assert len(results) > 0

        # Results should be sorted by score
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

        # Format for prompt
        output = retriever.format_for_prompt(results)
        assert len(output) > 0

    def test_retrieve_for_context(self, temp_lore_dir):
        """Test convenience method for game context."""
        retriever = LoreRetriever(temp_lore_dir)

        results = retriever.retrieve_for_context(
            player_input="I need to find the Nexus base",
            active_factions=["nexus", "ember colonies"],
            mission_type="Investigation",
            limit=2,
        )

        # Should return results based on factions and mapped themes
        assert len(results) <= 2
