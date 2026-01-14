"""
Engine-owned context control for SENTINEL.

Handles prompt packing, rolling windows, memory strain, and token budgets.
"""

from .tokenizer import count_tokens, TokenCounter
from .packer import (
    PromptPacker,
    PackSection,
    PackInfo,
    SectionBudget,
    StrainTier,
    DEFAULT_BUDGETS,
    LOCAL_BUDGETS,
    format_strain_notice,
)
from .window import (
    RollingWindow,
    TranscriptBlock,
    BlockPriority,
    WindowConfig,
)
from .digest import (
    DigestManager,
    CampaignDigest,
    HingeEntry,
    ThreadEntry,
    DigestSection,
)
from .ambient_context import extract_ambient_context

__all__ = [
    # Tokenizer
    "count_tokens",
    "TokenCounter",
    # Packer
    "PromptPacker",
    "PackSection",
    "PackInfo",
    "SectionBudget",
    "StrainTier",
    "DEFAULT_BUDGETS",
    "LOCAL_BUDGETS",
    "format_strain_notice",
    # Window
    "RollingWindow",
    "TranscriptBlock",
    "BlockPriority",
    "WindowConfig",
    # Digest
    "DigestManager",
    "CampaignDigest",
    "HingeEntry",
    "ThreadEntry",
    "DigestSection",
    # Ambient context
    "extract_ambient_context",
]
