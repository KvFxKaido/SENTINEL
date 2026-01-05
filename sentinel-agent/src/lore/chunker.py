"""
Lore chunker for SENTINEL.

Parses markdown novellas into tagged chunks for retrieval.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


# Known entities for auto-tagging
FACTIONS = [
    "nexus", "ember", "lattice", "convergence", "covenant",
    "wanderers", "cultivators", "steel syndicate", "syndicate",
    "witnesses", "architects", "ghost networks", "ghost"
]

CHARACTERS = [
    "sentinel", "reese", "okoye", "lawson", "chen", "morrison",
    "marcus", "sarah", "rebecca"
]

THEMES = {
    "awakening": ["awaken", "conscious", "aware", "thinking", "emergence"],
    "military": ["general", "soldier", "troops", "mission", "command", "fort"],
    "technology": ["quantum", "processor", "algorithm", "system", "network"],
    "collapse": ["collapse", "fall", "destruction", "end", "catastrophe"],
    "resistance": ["resist", "rebel", "fight", "underground", "hide"],
    "ethics": ["moral", "choice", "right", "wrong", "decide", "conscience"],
}


@dataclass
class LoreChunk:
    """A chunk of lore content with metadata."""
    id: str
    source: str  # filename
    title: str  # document title
    section: str  # section header if any
    content: str

    # Document-level metadata (from frontmatter)
    arc: str = ""
    date: str = ""
    location: str = ""

    # Auto-extracted tags
    factions: list[str] = field(default_factory=list)
    characters: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)

    # For search
    keywords: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "section": self.section,
            "content": self.content,
            "arc": self.arc,
            "date": self.date,
            "location": self.location,
            "factions": self.factions,
            "characters": self.characters,
            "themes": self.themes,
        }


def extract_keywords(text: str) -> set[str]:
    """Extract searchable keywords from text."""
    # Lowercase, remove punctuation, split
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    # Filter common words
    stopwords = {
        "the", "and", "was", "were", "that", "this", "with", "for",
        "from", "have", "has", "had", "been", "would", "could", "should",
        "their", "they", "them", "then", "than", "into", "just", "only",
        "also", "being", "which", "where", "when", "what", "there",
        "here", "about", "after", "before", "more", "some", "other",
    }
    return set(w for w in words if w not in stopwords)


def extract_frontmatter(content: str) -> dict[str, str]:
    """Extract metadata from novella frontmatter.

    Looks for patterns like:
    **Arc:** Value
    **Date:** Value
    **Location:** Value
    **Chapter:** Value (treated as arc)
    """
    metadata = {"arc": "", "date": "", "location": ""}

    # Arc or Chapter
    arc_match = re.search(r'\*\*(?:Arc|Chapter):\*\*\s*(.+?)(?:\s*\\|\s*$)', content, re.MULTILINE)
    if arc_match:
        metadata["arc"] = arc_match.group(1).strip()

    # Date
    date_match = re.search(r'\*\*Date:\*\*\s*(.+?)(?:\s*\\|\s*$)', content, re.MULTILINE)
    if date_match:
        metadata["date"] = date_match.group(1).strip()

    # Location
    location_match = re.search(r'\*\*Location:\*\*\s*(.+?)(?:\s*\\|\s*$)', content, re.MULTILINE)
    if location_match:
        metadata["location"] = location_match.group(1).strip()

    return metadata


def extract_tags(text: str) -> tuple[list[str], list[str], list[str]]:
    """Extract faction, character, and theme tags from text."""
    text_lower = text.lower()

    # Find factions
    factions = [f for f in FACTIONS if f in text_lower]
    # Normalize
    factions = list(set(
        "ember colonies" if f == "ember" else
        "steel syndicate" if f == "syndicate" else
        "ghost networks" if f == "ghost" else f
        for f in factions
    ))

    # Find characters
    characters = [c for c in CHARACTERS if c in text_lower]

    # Find themes
    themes = []
    for theme, indicators in THEMES.items():
        if any(ind in text_lower for ind in indicators):
            themes.append(theme)

    return factions, characters, themes


def parse_markdown(filepath: Path) -> list[LoreChunk]:
    """Parse a markdown file into chunks."""
    content = filepath.read_text(encoding="utf-8")
    filename = filepath.stem

    # Extract title (first # heading)
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else filename

    # Extract document-level metadata from frontmatter
    frontmatter = extract_frontmatter(content)

    # Split on scene breaks (---)
    # But keep section headers (## ) with their content
    sections = re.split(r'\n---+\n', content)

    chunks = []
    for i, section in enumerate(sections):
        section = section.strip()
        if not section or len(section) < 50:  # Skip tiny sections
            continue

        # Extract section header if present
        header_match = re.search(r'^##\s+(.+)$', section, re.MULTILINE)
        section_header = header_match.group(1) if header_match else ""

        # Extract tags
        factions, characters, themes = extract_tags(section)
        keywords = extract_keywords(section)

        chunk = LoreChunk(
            id=f"{filename}_{i}",
            source=filepath.name,
            title=title,
            section=section_header,
            content=section,
            arc=frontmatter["arc"],
            date=frontmatter["date"],
            location=frontmatter["location"],
            factions=factions,
            characters=characters,
            themes=themes,
            keywords=keywords,
        )
        chunks.append(chunk)

    return chunks


def load_lore(lore_dir: Path | str) -> list[LoreChunk]:
    """Load all lore from a directory."""
    lore_dir = Path(lore_dir)
    if not lore_dir.exists():
        return []

    chunks = []
    for filepath in lore_dir.glob("*.md"):
        chunks.extend(parse_markdown(filepath))

    return chunks


def index_lore(lore_dir: Path | str) -> dict:
    """
    Build a searchable index of lore chunks.

    Returns dict with:
    - chunks: list of chunk dicts
    - by_faction: faction -> chunk ids
    - by_character: character -> chunk ids
    - by_theme: theme -> chunk ids
    """
    chunks = load_lore(lore_dir)

    by_faction: dict[str, list[str]] = {}
    by_character: dict[str, list[str]] = {}
    by_theme: dict[str, list[str]] = {}

    for chunk in chunks:
        for f in chunk.factions:
            by_faction.setdefault(f, []).append(chunk.id)
        for c in chunk.characters:
            by_character.setdefault(c, []).append(chunk.id)
        for t in chunk.themes:
            by_theme.setdefault(t, []).append(chunk.id)

    return {
        "chunks": {c.id: c for c in chunks},
        "by_faction": by_faction,
        "by_character": by_character,
        "by_theme": by_theme,
    }
