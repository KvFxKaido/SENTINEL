"""
Lore retriever for SENTINEL.

Finds relevant lore chunks based on current game context.
Uses lightweight keyword matching - no external dependencies.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .chunker import LoreChunk, index_lore, extract_keywords


@dataclass
class RetrievalResult:
    """A retrieved lore chunk with relevance score."""
    chunk: LoreChunk
    score: float
    match_reasons: list[str]


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

        scores: dict[str, tuple[float, list[str]]] = {}

        for chunk_id, chunk in self.index["chunks"].items():
            score = 0.0
            reasons = []

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
                if len(keyword_matches) <= 5:
                    reasons.append(f"keywords: {', '.join(list(keyword_matches)[:5])}")
                else:
                    reasons.append(f"keywords: {len(keyword_matches)} matches")

            if score > 0:
                scores[chunk_id] = (score, reasons)

        # Sort by score descending
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x][0], reverse=True)

        results = []
        for chunk_id in sorted_ids[:limit]:
            chunk = self.index["chunks"][chunk_id]
            score, reasons = scores[chunk_id]
            results.append(RetrievalResult(
                chunk=chunk,
                score=score,
                match_reasons=reasons,
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
