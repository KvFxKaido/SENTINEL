"""
Command-line interface for SENTINEL.

Main entry point and game loop.
Supports local backends: LM Studio and Ollama.
"""

import sys
import argparse
from pathlib import Path
from rich.panel import Panel
from rich.prompt import Prompt
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import Completer, Completion

from ..state import CampaignManager
from ..agent import SentinelAgent
from ..llm.base import Message
from ..tools.hinge_detector import detect_hinge

from .renderer import (
    console, THEME, pt_style,
    show_banner, show_backend_status, show_status, show_choices,
    status_bar,
    render_narrative_block, render_choice_block, detect_block_type,
    BlockType,
)
from .config import load_config, set_backend
from .glyphs import (
    g, format_context_meter, context_warning, estimate_conversation_tokens,
    CONTEXT_LIMITS,
)
from .choices import parse_response, ChoiceBlock
from .commands import create_commands, register_all_commands
from .command_registry import get_registry, create_completer


# Legacy: Command completer for slash commands with descriptions
# TODO: Remove once fully migrated to registry
COMMAND_META = {
    "/new": "Create a new campaign",
    "/char": "Create a character",
    "/start": "Begin the story",
    "/mission": "Get a new mission",
    "/consult": "Ask the council for advice",
    "/debrief": "End session",
    "/history": "View chronicle (filter: hinges, faction, session, search)",
    "/search": "Search campaign history",
    "/summary": "View session summary",
    "/consequences": "View pending threads",
    "/threads": "View pending threads",
    "/load": "Load campaign",
    "/save": "Save campaign",
    "/delete": "Delete campaign",
    "/list": "List campaigns",
    "/status": "Show status",
    "/backend": "Switch LLM backend",
    "/model": "Switch model",
    "/banner": "Toggle banner animation",
    "/statusbar": "Toggle status bar",
    "/lore": "Search lore",
    "/npc": "View NPC info",
    "/factions": "View faction standings",
    "/arc": "View character arcs",
    "/simulate": "Explore hypotheticals",
    "/timeline": "Search campaign memory",
    "/roll": "Roll dice",
    "/loadout": "Manage mission gear",
    "/help": "Show help",
    "/quit": "Exit",
    "/exit": "Exit",
}

# Command categories for organized display
COMMAND_CATEGORIES = {
    "Campaign": ["/new", "/load", "/save", "/list", "/delete"],
    "Character": ["/char", "/arc", "/roll"],
    "Mission": ["/start", "/mission", "/loadout", "/debrief"],
    "Social": ["/consult", "/npc", "/factions"],
    "Info": ["/status", "/history", "/summary", "/consequences", "/threads", "/timeline"],
    "Simulation": ["/simulate"],
    "Settings": ["/backend", "/model", "/banner", "/statusbar"],
    "Lore": ["/lore"],
    "System": ["/help", "/quit", "/exit"],
}

# Commands that require specific context to be shown
CONTEXT_REQUIREMENTS = {
    # Requires a campaign to be loaded
    "campaign_required": [
        "/char", "/start", "/mission", "/consult", "/debrief", "/save",
        "/status", "/history", "/summary", "/consequences", "/threads",
        "/timeline", "/npc", "/factions", "/arc", "/simulate", "/roll",
        "/loadout",
    ],
    # Requires a character to exist
    "character_required": ["/start", "/mission", "/consult", "/debrief", "/arc", "/roll"],
    # Requires an active session (session started)
    "session_required": ["/debrief"],
}


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
            # Bonus for matching at word boundaries (after /)
            if i == 0 or text[i - 1] == "/":
                score += 50
        else:
            consecutive = 0

    if pattern_idx == len(pattern):
        return True, score
    return False, 0


class SlashCommandCompleter(Completer):
    """
    Enhanced command completer with:
    - Category grouping
    - Context-aware filtering
    - Recent commands prioritized
    - Fuzzy search
    """

    def __init__(self, manager_ref=None):
        """
        Initialize completer.

        Args:
            manager_ref: Callable that returns the CampaignManager instance,
                        used for context-aware filtering.
        """
        self.manager_ref = manager_ref
        self.recent_commands: list[str] = []
        self.max_recent = 5

    def record_command(self, cmd: str):
        """Record a command as recently used."""
        # Remove if already in list
        if cmd in self.recent_commands:
            self.recent_commands.remove(cmd)
        # Add to front
        self.recent_commands.insert(0, cmd)
        # Trim to max size
        self.recent_commands = self.recent_commands[: self.max_recent]

    def _is_command_available(self, cmd: str) -> bool:
        """Check if a command is available in the current context."""
        if self.manager_ref is None:
            return True

        try:
            manager = self.manager_ref()
        except Exception:
            return True

        # Check campaign requirement
        if cmd in CONTEXT_REQUIREMENTS.get("campaign_required", []):
            if not manager.current:
                return False

        # Check character requirement
        if cmd in CONTEXT_REQUIREMENTS.get("character_required", []):
            if not manager.current or not manager.current.characters:
                return False

        # Check session requirement (session has been started)
        if cmd in CONTEXT_REQUIREMENTS.get("session_required", []):
            if not manager.current:
                return False
            # Session is started if there's history or an active session
            session_started = (
                manager.current.history
                or manager.current.session is not None
            )
            if not session_started:
                return False

        return True

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lstrip()

        # Only complete if starting with /
        if not text.startswith("/"):
            return

        # Get the search pattern (everything after /)
        search_pattern = text[1:].lower() if len(text) > 1 else ""

        # Collect all matching commands with scores
        matches: list[tuple[str, str, int, str | None]] = []  # (cmd, desc, score, category)

        # Build command to category mapping
        cmd_to_category = {}
        for category, cmds in COMMAND_CATEGORIES.items():
            for cmd in cmds:
                cmd_to_category[cmd] = category

        for cmd, description in COMMAND_META.items():
            # Skip if not available in current context
            if not self._is_command_available(cmd):
                continue

            # Check if matches (prefix or fuzzy)
            if search_pattern:
                # Try matching against command without /
                cmd_name = cmd[1:]  # Remove leading /
                is_match, score = fuzzy_match(search_pattern, cmd_name)
                if not is_match:
                    # Also try matching against description
                    is_match, score = fuzzy_match(search_pattern, description)
                    if is_match:
                        score = score // 2  # Lower priority for description matches
                if not is_match:
                    continue
            else:
                score = 0

            # Boost score for recent commands
            if cmd in self.recent_commands:
                recent_idx = self.recent_commands.index(cmd)
                score += (self.max_recent - recent_idx) * 100

            category = cmd_to_category.get(cmd)
            matches.append((cmd, description, score, category))

        # Sort by score (descending), then by category, then alphabetically
        category_order = list(COMMAND_CATEGORIES.keys())

        def sort_key(item):
            cmd, desc, score, category = item
            cat_idx = category_order.index(category) if category in category_order else 999
            return (-score, cat_idx, cmd)

        matches.sort(key=sort_key)

        # Yield completions with category display
        current_category = None
        for cmd, description, score, category in matches:
            # Build display text with category prefix if category changed
            if category and category != current_category:
                # Add category header as display
                display = f"[{category}] {cmd}"
                current_category = category
            else:
                display = f"        {cmd}"  # Indent under category

            yield Completion(
                cmd,
                start_position=-len(text),
                display=display,
                display_meta=description,
            )


# Global completer instance - will be configured with manager reference later
# Legacy: Using old SlashCommandCompleter until migration complete
command_completer = SlashCommandCompleter()

# Registry-based completer (will replace above)
registry_completer = None  # Initialized in main()


# -----------------------------------------------------------------------------
# Main Loop
# -----------------------------------------------------------------------------

def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="SENTINEL - AI Game Master")
    parser.add_argument(
        "--no-animate", "-q",
        action="store_true",
        help="Skip banner animation"
    )
    parser.add_argument(
        "--local", "-l",
        action="store_true",
        help="Use local mode (optimized for 8B-12B models)"
    )
    args = parser.parse_args()

    # Initialize paths
    base_dir = Path(__file__).parent.parent.parent.parent  # SENTINEL root
    prompts_dir = Path(__file__).parent.parent.parent / "prompts"
    campaigns_dir = Path("campaigns")
    lore_dir = base_dir / "lore"

    # Load saved config (backend, model, banner preference, status bar)
    config = load_config(campaigns_dir)
    saved_backend = config.get("backend", "auto")
    saved_model = config.get("model")
    animate_banner = config.get("animate_banner", True)
    show_status_bar = config.get("show_status_bar", True)

    # Initialize status bar from config
    status_bar.enabled = show_status_bar

    # Command line --no-animate overrides config
    if args.no_animate:
        animate_banner = False

    # Show banner
    show_banner(animate=animate_banner)

    manager = CampaignManager(campaigns_dir)

    # Initialize command registry
    register_all_commands()
    global registry_completer
    registry_completer = create_completer(lambda: manager)

    # Configure the command completer with manager reference for context-aware filtering
    # Legacy: Still using old completer until migration complete
    command_completer.manager_ref = lambda: manager

    agent = SentinelAgent(
        manager,
        prompts_dir=prompts_dir,
        lore_dir=lore_dir if lore_dir.exists() else None,
        backend=saved_backend,
        local_mode=args.local,
    )

    # Restore saved model if using LM Studio/Ollama
    if saved_model and agent.backend in ("lmstudio", "ollama"):
        if hasattr(agent.client, "set_model"):
            try:
                agent.client.set_model(saved_model)
            except Exception:
                pass  # Model might not be available anymore

    # Show backend status
    show_backend_status(agent)
    if agent.local_mode:
        console.print(f"[{THEME['highlight']}]Local mode enabled[/{THEME['highlight']}] (condensed prompts, reduced budgets)")
    if agent.lore_retriever:
        lore_status = f"Lore: {agent.lore_retriever.chunk_count} chunks"
        if agent.unified_retriever and agent.unified_retriever.memvid:
            memvid_status = "enabled" if agent.unified_retriever.memvid.is_enabled else "disabled"
            lore_status += f" | Memvid: {memvid_status}"
        console.print(f"[{THEME['dim']}]{lore_status}[/{THEME['dim']}]")
    console.print(f"[{THEME['dim']}]Type /help for commands, or just start playing.[/{THEME['dim']}]\n")

    # Initialize state
    conversation: list[Message] = []
    last_choices: ChoiceBlock | None = None
    context_limit = CONTEXT_LIMITS["default"]  # 16k default

    # Create commands with conversation reference
    commands = create_commands(manager, agent, conversation)

    while True:
        try:
            # Poll for MCP events at start of each loop
            # This ensures faction events are processed immediately, not just on load
            events_processed = manager.poll_events()
            if events_processed > 0:
                console.print(f"[{THEME['dim']}]Processed {events_processed} pending event(s)[/{THEME['dim']}]")

            # Build prompt with context meter
            if conversation:
                tokens = estimate_conversation_tokens(conversation)
                usage_ratio = min(tokens / context_limit, 1.0)
                meter = format_context_meter(conversation, context_limit)
                context_display = f"[{THEME['dim']}]{meter}[/{THEME['dim']}] "
            else:
                context_display = ""
                usage_ratio = 0.0

            # Show status bar if enabled and campaign loaded
            if status_bar.enabled and manager.current:
                status_bar.render(manager.current)

            # Show choice-aware prompt with autocomplete
            if last_choices:
                prompt_text = "1-4 or action > "
            else:
                prompt_text = "> "

            # Use prompt_toolkit for autocomplete on slash commands
            user_input = pt_prompt(
                prompt_text,
                completer=registry_completer,  # Using registry-based completer
                style=pt_style,
                complete_while_typing=True,
            ).strip()

            if not user_input:
                continue

            # Handle numbered choice selection
            if last_choices and user_input.isdigit():
                choice_num = int(user_input)
                if 1 <= choice_num <= len(last_choices.options):
                    selected = last_choices.options[choice_num - 1]
                    # "Something else..." prompts for custom input
                    if "something else" in selected.lower():
                        user_input = Prompt.ask("[dim]What do you do?[/dim]")
                    else:
                        # Convert choice to action statement
                        user_input = selected if selected.startswith("I ") else f"I {selected.lower()}"
                    last_choices = None

            # Handle commands
            if user_input.startswith("/"):
                parts = user_input.split()
                cmd = parts[0].lower()
                cmd_args = parts[1:]

                if cmd in commands:
                    # Record command usage for recent commands feature
                    get_registry().record_usage(cmd)

                    result = commands[cmd](manager, agent, cmd_args)

                    # Handle backend switch
                    if cmd == "/backend" and result:
                        console.print(f"[dim]Switching to {result}...[/dim]")
                        set_backend(result, campaigns_dir)  # Save preference
                        agent = SentinelAgent(
                            manager,
                            prompts_dir=prompts_dir,
                            lore_dir=lore_dir if lore_dir.exists() else None,
                            backend=result,
                        )
                        commands = create_commands(manager, agent, conversation)
                        show_backend_status(agent)
                        continue

                    # Handle GM prompt (from /start, /mission, etc.)
                    if isinstance(result, tuple) and result[0] == "gm_prompt":
                        user_input = result[1]
                        # Fall through to agent processing below
                    else:
                        continue
                else:
                    console.print(f"[{THEME['warning']}]Unknown command: {cmd}[/{THEME['warning']}]")
                    continue

            # Regular input - send to agent
            if not manager.current:
                console.print(f"[{THEME['warning']}]Start or load a campaign first (/new or /load)[/{THEME['warning']}]")
                continue

            if not agent.is_available:
                console.print(
                    f"[{THEME['warning']}]No LLM backend available.[/{THEME['warning']}]\n"
                    f"[{THEME['dim']}]Start LM Studio or Ollama[/{THEME['dim']}]"
                )
                continue

            # Detect potential hinge moments before sending
            hinge = detect_hinge(user_input)
            if hinge:
                console.print(
                    f"\n[{THEME['warning']}]{g('hinge')} HINGE MOMENT DETECTED[/{THEME['warning']}] "
                    f"[{THEME['dim']}]({hinge.category.value}, {hinge.severity})[/{THEME['dim']}]"
                )

            # Get response from agent
            console.print()
            with console.status(f"[{THEME['dim']}]...[/{THEME['dim']}]"):
                try:
                    response = agent.respond(user_input, conversation)
                    conversation.append(Message(role="user", content=user_input))
                    conversation.append(Message(role="assistant", content=response))

                    # Auto-log hinge moment after GM confirms the action
                    if hinge and manager.current:
                        manager.log_hinge_moment(
                            situation=f"Player declared: {user_input[:100]}",
                            choice=hinge.matched_text,
                            reasoning=f"Category: {hinge.category.value}, Severity: {hinge.severity}",
                        )
                        console.print(
                            f"[{THEME['dim']}]{g('hinge')} Hinge logged to chronicle[/{THEME['dim']}]"
                        )
                except Exception as e:
                    response = f"[{THEME['danger']}]Error: {e}[/{THEME['danger']}]"
                    last_choices = None
                    console.print(Panel(response, border_style=THEME["danger"]))
                    console.print()
                    continue

            # Parse response for choices
            narrative, choices = parse_response(response)
            last_choices = choices

            # Display narrative using block-based output
            # Auto-detect block type (NARRATIVE vs INTEL) based on content
            render_narrative_block(narrative)

            # Display choices if present using block-based output
            if choices:
                console.print()
                render_choice_block(choices)

            # Show context meter and warning after response
            tokens = estimate_conversation_tokens(conversation)
            usage_ratio = min(tokens / context_limit, 1.0)
            meter = format_context_meter(conversation, context_limit)
            console.print(f"[{THEME['dim']}]{meter}[/{THEME['dim']}]")

            # Show warning if context is getting full
            warning = context_warning(usage_ratio)
            if warning:
                console.print(f"[{THEME['warning']}]{g('warning')} {warning}[/{THEME['warning']}]")

            console.print()

        except KeyboardInterrupt:
            console.print(f"\n[{THEME['dim']}]Use /quit to exit[/{THEME['dim']}]")
        except EOFError:
            break


if __name__ == "__main__":
    main()
