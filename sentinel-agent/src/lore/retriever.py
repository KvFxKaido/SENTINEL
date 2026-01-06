"""
Lore retriever for SENTINEL.

Finds relevant lore chunks based on current game context.
Uses lightweight keyword matching - no external dependencies.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from .chunker import LoreChunk, index_lore, extract_keywords


# Source type weights - prioritize canon lore over character sheets
SOURCE_WEIGHTS = {
    "canon": 2.0,      # Canon Bible, core lore documents
    "case_file": 1.0,  # Example timelines, case studies
    "character": 0.3,  # Character sheets, sample characters
    "session": 0.5,    # Session logs
    "default": 1.0,
}

# Patterns to identify source types
SOURCE_PATTERNS = [
    (r"canon.*bible|unified.*lore", "canon"),
    (r"case.*file|timeline", "case_file"),
    (r"character|sample.*char|subject.*file", "character"),
    (r"session.*log|session.*\d", "session"),
]


def _get_source_type(source: str, title: str) -> str:
    """Determine source type from filename and title."""
    combined = f"{source} {title}".lower()
    for pattern, source_type in SOURCE_PATTERNS:
        if re.search(pattern, combined):
            return source_type
    return "default"


def _get_source_weight(source: str, title: str) -> float:
    """Get weight multiplier for a source type."""
    source_type = _get_source_type(source, title)
    return SOURCE_WEIGHTS.get(source_type, SOURCE_WEIGHTS["default"])


def _find_keyword_snippet(content: str, keywords: set[str], max_len: int = 150) -> str:
    """Find a snippet of content containing matched keywords."""
    if not keywords:
        return ""

    content_lower = content.lower()

    # Find first keyword match position
    best_pos = len(content)
    best_keyword = None
    for kw in keywords:
        pos = content_lower.find(kw)
        if pos != -1 and pos < best_pos:
            best_pos = pos
            best_keyword = kw

    if best_keyword is None:
        return ""

    # Extract context around the match
    start = max(0, best_pos - 40)
    end = min(len(content), best_pos + len(best_keyword) + max_len - 40)

    # Adjust to word boundaries
    if start > 0:
        # Find start of word
        while start > 0 and content[start - 1] not in " \n\t":
            start -= 1
        prefix = "..."
    else:
        prefix = ""

    if end < len(content):
        # Find end of word
        while end < len(content) and content[end] not in " \n\t":
            end += 1
        suffix = "..."
    else:
        suffix = ""

    snippet = content[start:end].strip()
    # Clean up newlines
    snippet = re.sub(r'\s+', ' ', snippet)

    return f"{prefix}{snippet}{suffix}"


def _truncate_clean(text: str, max_len: int) -> str:
    """Truncate text at word boundary."""
    if len(text) <= max_len:
        return text

    # Find last space before max_len
    truncated = text[:max_len]
    last_space = truncated.rfind(' ')
    if last_space > max_len * 0.7:  # Don't cut too much
        truncated = truncated[:last_space]

    return truncated.rstrip() + "..."


@dataclass
class RetrievalResult:
    """A retrieved lore chunk with relevance score."""
    chunk: LoreChunk
    score: float
    match_reasons: list[str]
    matched_keywords: set[str] = field(default_factory=set)
    source_type: str = "default"

    @property
    def relevance_level(self) -> int:
        """Convert score to 1-5 relevance level."""
        if self.score >= 5.0:
            return 5
        elif self.score >= 3.5:
            return 4
        elif self.score >= 2.0:
            return 3
        elif self.score >= 1.0:
            return 2
        else:
            return 1

    @property
    def relevance_indicator(self) -> str:
        """Visual relevance indicator."""
        level = self.relevance_level
        filled = "●" * level
        empty = "○" * (5 - level)
        return filled + empty

    def get_keyword_snippet(self, max_len: int = 150) -> str:
        """Get snippet containing matched keywords."""
        return _find_keyword_snippet(self.chunk.content, self.matched_keywords, max_len)


class LoreRetriever:
    """
    Retrieves relevant lore based on game context.

    Matches on:
    - Factions mentioned in current game state
    - Keywords in player input or mission context
    - Themes relevant to current situation
    """

    def __init__(self, lore_dir: Path | str):
        self.lore_dir = Path(lore_dir)
        self._index: dict | None = None

    @property
    def index(self) -> dict:
        """Lazy-load the lore index."""
        if self._index is None:
            self._index = index_lore(self.lore_dir)
        return self._index

    def reload(self) -> None:
        """Force reload of lore index."""
        self._index = None

    @property
    def chunk_count(self) -> int:
        """Number of chunks in the index."""
        return len(self.index["chunks"])

    def retrieve(
        self,
        query: str = "",
        factions: list[str] | None = None,
        themes: list[str] | None = None,
        limit: int = 2,
    ) -> list[RetrievalResult]:
        """
        Retrieve relevant lore chunks.

        Args:
            query: Free text to match against (player input, mission description)
            factions: Factions to prioritize (from current game state)
            themes: Themes to prioritize
            limit: Max chunks to return

        Returns:
            List of RetrievalResult sorted by relevance
        """
        if not self.index["chunks"]:
            return []

        factions = [f.lower() for f in (factions or [])]
        themes = themes or []
        query_keywords = extract_keywords(query) if query else set()

        # Track scores and metadata per chunk
        scores: dict[str, tuple[float, list[str], set[str], str]] = {}

        for chunk_id, chunk in self.index["chunks"].items():
            score = 0.0
            reasons = []
            matched_kw = set()

            # Source type weight multiplier
            source_type = _get_source_type(chunk.source, chunk.title)
            source_weight = _get_source_weight(chunk.source, chunk.title)

            # Faction match (high weight)
            faction_matches = set(f.lower() for f in chunk.factions) & set(factions)
            if faction_matches:
                score += 3.0 * len(faction_matches)
                reasons.append(f"factions: {', '.join(faction_matches)}")

            # Theme match (medium weight)
            theme_matches = set(chunk.themes) & set(themes)
            if theme_matches:
                score += 2.0 * len(theme_matches)
                reasons.append(f"themes: {', '.join(theme_matches)}")

            # Keyword match (lower weight, but accumulates)
            keyword_matches = chunk.keywords & query_keywords
            if keyword_matches:
                score += 0.5 * len(keyword_matches)
                matched_kw = keyword_matches
                if len(keyword_matches) <= 3:
                    reasons.append(f"matches: {', '.join(list(keyword_matches)[:3])}")
                else:
                    reasons.append(f"{len(keyword_matches)} keyword matches")

            # Apply source type multiplier
            if score > 0:
                score *= source_weight
                scores[chunk_id] = (score, reasons, matched_kw, source_type)

        # Sort by score descending
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x][0], reverse=True)

        results = []
        for chunk_id in sorted_ids[:limit]:
            chunk = self.index["chunks"][chunk_id]
            score, reasons, matched_kw, source_type = scores[chunk_id]
            results.append(RetrievalResult(
                chunk=chunk,
                score=score,
                match_reasons=reasons,
                matched_keywords=matched_kw,
                source_type=source_type,
            ))

        return results

    def retrieve_for_context(
        self,
        player_input: str,
        active_factions: list[str] | None = None,
        mission_type: str | None = None,
        limit: int = 2,
    ) -> list[RetrievalResult]:
        """
        Convenience method for retrieving based on game context.

        Maps mission types to themes automatically.
        """
        # Map mission types to themes
        theme_map = {
            "Investigation": ["technology", "ethics"],
            "Rescue": ["military", "resistance"],
            "Diplomacy": ["ethics"],
            "Sabotage": ["resistance", "technology"],
            "Escort": ["military"],
        }
        themes = theme_map.get(mission_type, []) if mission_type else []

        return self.retrieve(
            query=player_input,
            factions=active_factions,
            themes=themes,
            limit=limit,
        )

    def format_for_prompt(self, results: list[RetrievalResult]) -> str:
        """Format retrieved chunks for inclusion in system prompt."""
        if not results:
            return ""

        lines = ["## Lore Reference", ""]
        for result in results:
            chunk = result.chunk
            lines.append(f"**From {chunk.title}**")
            if chunk.section:
                lines.append(f"*{chunk.section}*")
            lines.append("")
            # Truncate very long chunks
            content = chunk.content
            if len(content) > 800:
                content = content[:800] + "..."
            lines.append(content)
            lines.append("")

        return "\n".join(lines)


def create_retriever(lore_dir: Path | str = "lore") -> LoreRetriever:
    """Create a lore retriever instance."""
    return LoreRetriever(lore_dir)
