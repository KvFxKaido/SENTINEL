"""
Command-line interface for SENTINEL.

Main entry point and game loop.
Supports LM Studio (local) and Claude (API) backends.
"""

import sys
import argparse
from pathlib import Path
from rich.panel import Panel
from rich.prompt import Prompt
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import WordCompleter

from ..state import CampaignManager
from ..agent import SentinelAgent
from ..llm.base import Message
from ..tools.hinge_detector import detect_hinge

from .renderer import (
    console, THEME, pt_style,
    show_banner, show_backend_status, show_status, show_choices,
)
from .glyphs import (
    g, format_context_meter, context_warning, estimate_conversation_tokens,
    CONTEXT_LIMITS,
)
from .choices import parse_response, ChoiceBlock
from .commands import create_commands


# Command completer for slash commands with descriptions
COMMAND_META = {
    "/new": "Create a new campaign",
    "/char": "Create a character",
    "/start": "Begin the story",
    "/mission": "Get a new mission",
    "/consult": "Ask the council for advice",
    "/debrief": "End session",
    "/history": "View chronicle",
    "/load": "Load campaign",
    "/save": "Save campaign",
    "/list": "List campaigns",
    "/status": "Show status",
    "/backend": "Switch LLM backend",
    "/model": "Switch model",
    "/lore": "Search lore",
    "/roll": "Roll dice",
    "/help": "Show help",
    "/quit": "Exit",
    "/exit": "Exit",
}
command_completer = WordCompleter(
    list(COMMAND_META.keys()),
    ignore_case=True,
    match_middle=False,
    meta_dict=COMMAND_META,
)


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
    args = parser.parse_args()

    # Show banner (with or without animation)
    show_banner(animate=not args.no_animate)

    # Initialize
    base_dir = Path(__file__).parent.parent.parent.parent  # SENTINEL root
    prompts_dir = Path(__file__).parent.parent.parent / "prompts"
    campaigns_dir = Path("campaigns")
    lore_dir = base_dir / "lore"

    manager = CampaignManager(campaigns_dir)
    agent = SentinelAgent(
        manager,
        prompts_dir=prompts_dir,
        lore_dir=lore_dir if lore_dir.exists() else None,
        backend="auto",
    )

    # Show backend status
    show_backend_status(agent)
    if agent.lore_retriever:
        console.print(f"[{THEME['dim']}]Lore: {agent.lore_retriever.chunk_count} chunks indexed[/{THEME['dim']}]")
    console.print(f"[{THEME['dim']}]Type /help for commands, or just start playing.[/{THEME['dim']}]\n")

    # Initialize state
    conversation: list[Message] = []
    last_choices: ChoiceBlock | None = None
    context_limit = CONTEXT_LIMITS["default"]  # 16k default

    # Create commands with conversation reference
    commands = create_commands(manager, agent, conversation)

    while True:
        try:
            # Build prompt with context meter
            if conversation:
                tokens = estimate_conversation_tokens(conversation)
                usage_ratio = min(tokens / context_limit, 1.0)
                meter = format_context_meter(conversation, context_limit)
                context_display = f"[{THEME['dim']}]{meter}[/{THEME['dim']}] "
            else:
                context_display = ""
                usage_ratio = 0.0

            # Show choice-aware prompt with autocomplete
            if last_choices:
                prompt_text = "1-4 or action > "
            else:
                prompt_text = "> "

            # Use prompt_toolkit for autocomplete on slash commands
            user_input = pt_prompt(
                prompt_text,
                completer=command_completer,
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
                    result = commands[cmd](manager, agent, cmd_args)

                    # Handle backend switch
                    if cmd == "/backend" and result:
                        console.print(f"[dim]Switching to {result}...[/dim]")
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
                    f"[{THEME['dim']}]Start LM Studio or set ANTHROPIC_API_KEY[/{THEME['dim']}]"
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

            # Display narrative - cold twilight blue border
            console.print(Panel(narrative, border_style=THEME["primary"]))

            # Display choices if present
            if choices:
                console.print()
                show_choices(choices)

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
