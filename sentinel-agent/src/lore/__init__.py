"""Lore retrieval system for SENTINEL."""

from .chunker import LoreChunk, load_lore, index_lore
from .retriever import LoreRetriever, RetrievalResult, create_retriever
from .unified import (
    UnifiedRetriever,
    UnifiedResult,
    RetrievalBudget,
    DEFAULT_BUDGET,
    create_unified_retriever,
    extract_faction_state,
)

__all__ = [
    # Chunker
    "LoreChunk",
    "load_lore",
    "index_lore",
    # Retriever
    "LoreRetriever",
    "RetrievalResult",
    "create_retriever",
    # Unified
    "UnifiedRetriever",
    "UnifiedResult",
    "RetrievalBudget",
    "DEFAULT_BUDGET",
    "create_unified_retriever",
    "extract_faction_state",
]
