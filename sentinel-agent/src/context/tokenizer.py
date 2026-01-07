"""
Token counting with tiktoken + fallback.

Uses cl100k_base encoding (Claude/GPT-4 compatible) when tiktoken is available,
falls back to conservative character-based estimation when not.
"""

from typing import Protocol, runtime_checkable

# Try to import tiktoken, fall back gracefully
_tiktoken_encoder = None
_HAS_TIKTOKEN = False

try:
    import tiktoken
    _tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
    _HAS_TIKTOKEN = True
except ImportError:
    pass


# Conservative estimate: ~4 chars per token for English prose
# This is intentionally conservative to avoid overflow
CHARS_PER_TOKEN_FALLBACK = 4


def count_tokens(text: str) -> int:
    """
    Count tokens in text.

    Uses tiktoken (cl100k_base) if available, otherwise falls back to
    conservative character-based estimation (len(text) // 4).

    Args:
        text: The text to count tokens for

    Returns:
        Token count (integer)
    """
    if not text:
        return 0

    if _HAS_TIKTOKEN and _tiktoken_encoder is not None:
        return len(_tiktoken_encoder.encode(text))

    # Conservative fallback
    return len(text) // CHARS_PER_TOKEN_FALLBACK


def has_tiktoken() -> bool:
    """Check if tiktoken is available."""
    return _HAS_TIKTOKEN


@runtime_checkable
class TokenCounter(Protocol):
    """Protocol for token counting implementations."""

    def count(self, text: str) -> int:
        """Count tokens in text."""
        ...

    def truncate_to_budget(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token budget."""
        ...


class TiktokenCounter:
    """Token counter using tiktoken (accurate)."""

    def __init__(self, encoding_name: str = "cl100k_base"):
        if not _HAS_TIKTOKEN:
            raise ImportError("tiktoken is required for TiktokenCounter")
        self._encoder = tiktoken.get_encoding(encoding_name)

    def count(self, text: str) -> int:
        """Count tokens using tiktoken."""
        if not text:
            return 0
        return len(self._encoder.encode(text))

    def truncate_to_budget(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token budget (preserves token boundaries)."""
        if not text:
            return ""

        tokens = self._encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text

        # Truncate and decode
        truncated_tokens = tokens[:max_tokens]
        return self._encoder.decode(truncated_tokens)


class FallbackCounter:
    """Token counter using character estimation (conservative)."""

    def __init__(self, chars_per_token: int = CHARS_PER_TOKEN_FALLBACK):
        self._chars_per_token = chars_per_token

    def count(self, text: str) -> int:
        """Estimate tokens using character count."""
        if not text:
            return 0
        return len(text) // self._chars_per_token

    def truncate_to_budget(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within estimated token budget."""
        if not text:
            return ""

        max_chars = max_tokens * self._chars_per_token
        if len(text) <= max_chars:
            return text

        # Try to truncate at word boundary
        truncated = text[:max_chars]
        last_space = truncated.rfind(' ')
        if last_space > max_chars * 0.8:  # Only if we're not losing too much
            truncated = truncated[:last_space]

        return truncated


def get_counter() -> TokenCounter:
    """
    Get the best available token counter.

    Returns TiktokenCounter if tiktoken is installed, FallbackCounter otherwise.
    """
    if _HAS_TIKTOKEN:
        return TiktokenCounter()
    return FallbackCounter()


# Convenience: default counter instance
_default_counter = None


def get_default_counter() -> TokenCounter:
    """Get or create the default counter instance."""
    global _default_counter
    if _default_counter is None:
        _default_counter = get_counter()
    return _default_counter


def truncate_to_budget(text: str, max_tokens: int) -> str:
    """
    Truncate text to fit within token budget.

    Uses the default counter.
    """
    return get_default_counter().truncate_to_budget(text, max_tokens)
