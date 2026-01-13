"""
Command Registry for SENTINEL.

Provides a single source of truth for all slash commands.
Both CLI and TUI consume from this registry.

Pattern: Self-registration with context predicates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Any, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from ..state import CampaignManager
    from ..agent import SentinelAgent


class CommandCategory(str, Enum):
    """Command categories for organized display."""
    CAMPAIGN = "Campaign"
    CHARACTER = "Character"
    MISSION = "Mission"
    SOCIAL = "Social"
    INFO = "Info"
    SIMULATION = "Simulation"
    SETTINGS = "Settings"
    LORE = "Lore"
    SYSTEM = "System"


# Type aliases
CommandHandler = Callable[["CampaignManager", "SentinelAgent", list[str]], Any]
TUICommandHandler = Callable[[Any, Any, list[str]], Any]  # (app, log, args) -> result
ContextPredicate = Callable[["CampaignManager"], bool]


# -----------------------------------------------------------------------------
# Context Predicates
# Reusable functions that check if a command should be available
# -----------------------------------------------------------------------------

def has_campaign(manager: "CampaignManager") -> bool:
    """Check if a campaign is loaded."""
    return manager.current is not None


def has_character(manager: "CampaignManager") -> bool:
    """Check if campaign has a character."""
    return manager.current is not None and bool(manager.current.characters)


def has_session(manager: "CampaignManager") -> bool:
    """Check if a session has been started."""
    if not manager.current:
        return False
    return bool(manager.current.history) or manager.current.session is not None


def always_available(manager: "CampaignManager") -> bool:
    """Command is always available."""
    return True


# -----------------------------------------------------------------------------
# Command Definition
# -----------------------------------------------------------------------------

@dataclass
class Command:
    """
    A single command definition with all metadata.

    Attributes:
        name: The command name including slash (e.g., "/new")
        description: Short description for help and completion
        category: Category for grouping in help/completion
        handler: Function to execute the command (CLI: manager, agent, args)
        tui_handler: Function to execute in TUI (app, log, args)
        available_when: Predicate function checking if command is available
        aliases: Alternative names for the command
        hidden: If True, don't show in help or completion
    """
    name: str
    description: str
    category: CommandCategory
    handler: CommandHandler | None = None
    tui_handler: TUICommandHandler | None = None
    available_when: ContextPredicate = always_available
    aliases: list[str] = field(default_factory=list)
    hidden: bool = False

    def is_available(self, manager: "CampaignManager") -> bool:
        """Check if command is available in current context."""
        try:
            return self.available_when(manager)
        except Exception:
            return True  # Fail open for safety


# -----------------------------------------------------------------------------
# Fuzzy Matching
# -----------------------------------------------------------------------------

def fuzzy_match(pattern: str, text: str) -> tuple[bool, int]:
    """
    Check if pattern fuzzy-matches text.
    Returns (matches, score) where score is higher for better matches.
    """
    pattern = pattern.lower()
    text = text.lower()

    # Exact prefix match gets highest score
    if text.startswith(pattern):
        return True, 1000 - len(text)

    # Fuzzy match: all pattern chars must appear in order
    pattern_idx = 0
    score = 0
    consecutive = 0

    for i, char in enumerate(text):
        if pattern_idx < len(pattern) and char == pattern[pattern_idx]:
            pattern_idx += 1
            consecutive += 1
            # Bonus for consecutive matches
            score += consecutive * 10
            # Bonus for matching at word boundaries
            if i == 0 or text[i - 1] in "/_-":
                score += 50
        else:
            consecutive = 0

    if pattern_idx == len(pattern):
        return True, score
    return False, 0


# -----------------------------------------------------------------------------
# Command Registry
# -----------------------------------------------------------------------------

class CommandRegistry:
    """
    Central registry for all commands.

    Commands register themselves here, and both CLI and TUI
    consume from this single source of truth.
    """

    def __init__(self):
        self._commands: dict[str, Command] = {}
        self._recent: list[str] = []
        self._max_recent = 5

    def register(self, command: Command) -> None:
        """Register a command."""
        self._commands[command.name] = command
        # Also register aliases
        for alias in command.aliases:
            self._commands[alias] = command

    def get(self, name: str) -> Command | None:
        """Get a command by name."""
        return self._commands.get(name)

    def record_usage(self, name: str) -> None:
        """Record a command as recently used."""
        if name in self._recent:
            self._recent.remove(name)
        self._recent.insert(0, name)
        self._recent = self._recent[:self._max_recent]

    def get_recent_boost(self, name: str) -> int:
        """Get score boost for recently used commands."""
        if name in self._recent:
            idx = self._recent.index(name)
            return (self._max_recent - idx) * 100
        return 0

    def all_commands(self) -> list[Command]:
        """Get all unique commands (excludes aliases)."""
        seen = set()
        result = []
        for cmd in self._commands.values():
            if cmd.name not in seen:
                seen.add(cmd.name)
                result.append(cmd)
        return result

    def available_commands(self, manager: "CampaignManager") -> list[Command]:
        """Get commands available in current context."""
        return [
            cmd for cmd in self.all_commands()
            if not cmd.hidden and cmd.is_available(manager)
        ]

    def by_category(self, manager: "CampaignManager" | None = None) -> dict[CommandCategory, list[Command]]:
        """Get commands grouped by category."""
        result: dict[CommandCategory, list[Command]] = {cat: [] for cat in CommandCategory}

        for cmd in self.all_commands():
            if cmd.hidden:
                continue
            if manager and not cmd.is_available(manager):
                continue
            result[cmd.category].append(cmd)

        # Sort each category alphabetically
        for cat in result:
            result[cat].sort(key=lambda c: c.name)

        return result

    def search(
        self,
        query: str,
        manager: "CampaignManager" | None = None,
        include_unavailable: bool = False,
    ) -> list[tuple[Command, int]]:
        """
        Search commands with fuzzy matching.

        Returns list of (command, score) tuples, sorted by score descending.
        """
        if not query:
            # No query = return all available commands
            commands = self.all_commands() if include_unavailable else (
                self.available_commands(manager) if manager else self.all_commands()
            )
            return [(cmd, self.get_recent_boost(cmd.name)) for cmd in commands if not cmd.hidden]

        results: list[tuple[Command, int]] = []
        search_pattern = query.lstrip("/").lower()

        for cmd in self.all_commands():
            if cmd.hidden:
                continue

            # Check availability
            if not include_unavailable and manager and not cmd.is_available(manager):
                continue

            # Try matching against command name (without /)
            cmd_name = cmd.name[1:] if cmd.name.startswith("/") else cmd.name
            is_match, score = fuzzy_match(search_pattern, cmd_name)

            if not is_match:
                # Also try matching against description
                is_match, score = fuzzy_match(search_pattern, cmd.description)
                if is_match:
                    score = score // 2  # Lower priority for description matches

            if is_match:
                # Add recent boost
                score += self.get_recent_boost(cmd.name)
                results.append((cmd, score))

        # Sort by score (descending), then by category order, then alphabetically
        category_order = list(CommandCategory)
        results.sort(key=lambda x: (
            -x[1],  # Score descending
            category_order.index(x[0].category),  # Category order
            x[0].name  # Alphabetical
        ))

        return results

    def autocorrect(self, cmd: str) -> tuple[str, str | None]:
        """
        Attempt to autocorrect a mistyped command.

        Returns (corrected_cmd, correction_message) or (original_cmd, None).
        """
        if cmd in self._commands:
            return cmd, None

        # Find best fuzzy match
        results = self.search(cmd, include_unavailable=True)
        if results and results[0][1] > 500:  # High confidence threshold
            corrected = results[0][0].name
            return corrected, f"Autocorrected to {corrected}"

        return cmd, None


# -----------------------------------------------------------------------------
# Global Registry Instance
# -----------------------------------------------------------------------------

_registry: CommandRegistry | None = None


def get_registry() -> CommandRegistry:
    """Get the global command registry (lazy initialization)."""
    global _registry
    if _registry is None:
        _registry = CommandRegistry()
    return _registry


def register_command(
    name: str,
    description: str,
    category: CommandCategory,
    handler: CommandHandler | None = None,
    tui_handler: TUICommandHandler | None = None,
    available_when: ContextPredicate = always_available,
    aliases: list[str] | None = None,
    hidden: bool = False,
) -> Command:
    """
    Convenience function to register a command.

    Can be used as a decorator:
        @register_command("/foo", "Do foo", CommandCategory.SYSTEM)
        def cmd_foo(manager, agent, args):
            ...

    Or directly:
        register_command("/foo", "Do foo", CommandCategory.SYSTEM, handler=my_handler)
    """
    def decorator(fn: CommandHandler) -> CommandHandler:
        cmd = Command(
            name=name,
            description=description,
            category=category,
            handler=fn,
            tui_handler=tui_handler,
            available_when=available_when,
            aliases=aliases or [],
            hidden=hidden,
        )
        get_registry().register(cmd)
        return fn

    if handler is not None:
        # Direct registration (not as decorator)
        cmd = Command(
            name=name,
            description=description,
            category=category,
            handler=handler,
            tui_handler=tui_handler,
            available_when=available_when,
            aliases=aliases or [],
            hidden=hidden,
        )
        get_registry().register(cmd)
        return cmd

    return decorator  # type: ignore


def set_tui_handler(name: str, handler: TUICommandHandler) -> None:
    """
    Set or update the TUI handler for an existing command.

    Use this to add TUI handlers after initial registration.
    """
    registry = get_registry()
    cmd = registry.get(name)
    if cmd:
        cmd.tui_handler = handler


# -----------------------------------------------------------------------------
# Prompt-Toolkit Completer Integration
# -----------------------------------------------------------------------------

def create_completer(manager_ref: Callable[[], "CampaignManager"] | None = None):
    """
    Create a prompt-toolkit Completer that uses the registry.

    Args:
        manager_ref: Callable that returns the current CampaignManager,
                    used for context-aware filtering.
    """
    from prompt_toolkit.completion import Completer, Completion

    class RegistryCompleter(Completer):
        def __init__(self):
            self.manager_ref = manager_ref

        def get_completions(self, document, complete_event):
            text = document.text_before_cursor.lstrip()

            # Only complete if starting with /
            if not text.startswith("/"):
                return

            # Get manager for context filtering
            manager = None
            if self.manager_ref:
                try:
                    manager = self.manager_ref()
                except Exception:
                    pass

            # Search for matches
            search_pattern = text[1:] if len(text) > 1 else ""
            results = get_registry().search(search_pattern, manager)

            # Group by category for display
            current_category = None
            for cmd, score in results:
                # Build display text with category prefix
                if cmd.category != current_category:
                    display = f"[{cmd.category.value}] {cmd.name}"
                    current_category = cmd.category
                else:
                    display = f"        {cmd.name}"

                yield Completion(
                    cmd.name,
                    start_position=-len(text),
                    display=display,
                    display_meta=cmd.description,
                )

    return RegistryCompleter()
