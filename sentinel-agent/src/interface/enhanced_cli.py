"""
SENTINEL Rich Enhancement - Enhanced CLI with Persistent Panels

Adds live status panels above the existing CLI.
Architecture:
- Wraps the existing CLI main loop
- Displays persistent status/faction panels using Rich's Live
- Adds keyboard shortcuts for common commands
- Output flows naturally below the panels
"""
import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from prompt_toolkit import PromptSession

from ..state import CampaignManager
from ..agent import SentinelAgent
from ..llm.base import Message

from .renderer import (
    console, THEME,
    show_banner, show_backend_status,
    render_narrative_block, render_choice_block,
)
from .config import load_config, set_backend
from .glyphs import (
    g, format_context_meter, context_warning, estimate_conversation_tokens,
    CONTEXT_LIMITS,
)
from .choices import parse_response, ChoiceBlock
from .commands import create_commands
from .cli import command_completer
from .panels import render_status_panel, render_faction_panel, render_button_bar


class EnhancedCLI:
    """
    Enhanced CLI wrapper with persistent panels

    Uses Rich's Live display to show:
    - Status panel (character, energy, phase, session)
    - Faction panel (top 4 factions by standing)
    - Button bar (keyboard shortcuts)

    All existing CLI functionality preserved.
    """

    def __init__(
        self,
        manager: CampaignManager,
        agent: SentinelAgent,
        prompts_dir: Path,
        lore_dir: Path | None,
        campaigns_dir: Path,
        config: dict,
    ):
        self.console = Console()
        self.manager = manager
        self.agent = agent
        self.prompts_dir = prompts_dir
        self.lore_dir = lore_dir
        self.campaigns_dir = campaigns_dir
        self.config = config

        self.session = PromptSession()
        self.running = True

        # Track whether to show panels (can toggle)
        self.panels_enabled = True

        # Game state
        self.conversation: list[Message] = []
        self.last_choices: ChoiceBlock | None = None
        self.context_limit = CONTEXT_LIMITS["default"]

        # Commands
        self.commands = create_commands(manager, agent, self.conversation)

    def print_panels(self):
        """Print status panels (called before each prompt)."""
        if not self.panels_enabled:
            return

        if not self.manager.current:
            # No campaign loaded - show minimal info
            self.console.print(Panel(
                Text.from_markup("[dim]No campaign loaded - use /new or /load[/dim]"),
                title="[bold]STATUS[/bold]",
                title_align="left",
                border_style="blue",
                padding=(0, 1)
            ))
        else:
            # Print status and faction panels
            self.console.print(render_status_panel(self.manager.current))

            # Only show factions if there are non-neutral standings
            faction_panel = render_faction_panel(self.manager.current)
            self.console.print(faction_panel)

        # Button bar
        self.console.print(render_button_bar())

    def run(self):
        """
        Main loop - simple reprint approach (no Live display).

        Flow:
        1. Print status panels
        2. Get user input
        3. Process command/action
        4. Repeat
        """
        self.console.print(f"[{THEME['dim']}]Type /help for commands, or just start playing.[/{THEME['dim']}]\n")

        while self.running:
            # Print panels before prompt
            self.print_panels()

            # Show choice-aware prompt
            if self.last_choices:
                prompt_text = "1-4 or action > "
            else:
                prompt_text = "> "

            # Get user input with autocomplete
            try:
                user_input = self.session.prompt(
                    prompt_text,
                    completer=command_completer,
                ).strip()
            except KeyboardInterrupt:
                self.console.print(f"\n[{THEME['dim']}]Use /quit or Q to exit[/{THEME['dim']}]")
                continue
            except EOFError:
                break

            if not user_input:
                continue

            # Handle numbered choice selection
            if self.last_choices and user_input.isdigit():
                choice_num = int(user_input)
                if 1 <= choice_num <= len(self.last_choices.options):
                    selected = self.last_choices.options[choice_num - 1]
                    if "something else" in selected.lower():
                        from rich.prompt import Prompt
                        user_input = Prompt.ask("[dim]What do you do?[/dim]")
                    else:
                        user_input = selected if selected.startswith("I ") else f"I {selected.lower()}"
                    self.last_choices = None

            # Handle exit
            if user_input in ['/quit', '/exit', 'quit', 'exit']:
                self.console.print("\n[cyan]Exiting SENTINEL...[/cyan]")
                break

            # Handle commands
            if user_input.startswith("/"):
                parts = user_input.split()
                cmd = parts[0].lower()
                cmd_args = parts[1:]

                if cmd in self.commands:
                    # Record command usage
                    command_completer.record_command(cmd)

                    result = self.commands[cmd](self.manager, self.agent, cmd_args)

                    # Handle backend switch
                    if cmd == "/backend" and result:
                        self.console.print(f"[dim]Switching to {result}...[/dim]")
                        set_backend(result, self.campaigns_dir)
                        self.agent = SentinelAgent(
                            self.manager,
                            prompts_dir=self.prompts_dir,
                            lore_dir=self.lore_dir if self.lore_dir and self.lore_dir.exists() else None,
                            backend=result,
                        )
                        self.commands = create_commands(self.manager, self.agent, self.conversation)
                        show_backend_status(self.agent)
                        continue

                    # Handle GM prompt (from /start, /mission, etc.)
                    if isinstance(result, tuple) and result[0] == "gm_prompt":
                        user_input = result[1]
                        # Fall through to agent processing below
                    else:
                        continue
                else:
                    self.console.print(f"[{THEME['warning']}]Unknown command: {cmd}[/{THEME['warning']}]")
                    continue

            # Regular input - send to agent
            if not self.manager.current:
                self.console.print(f"[{THEME['warning']}]Start or load a campaign first (/new or /load)[/{THEME['warning']}]")
                continue

            if not self.agent.is_available:
                self.console.print(
                    f"[{THEME['warning']}]No LLM backend available.[/{THEME['warning']}]\n"
                    f"[{THEME['dim']}]Start LM Studio or Ollama[/{THEME['dim']}]"
                )
                continue

            # Get response from agent
            self.console.print()
            with self.console.status(f"[{THEME['dim']}]...[/{THEME['dim']}]"):
                try:
                    from ..tools.hinge_detector import detect_hinge

                    # Detect potential hinge moments
                    hinge = detect_hinge(user_input)
                    if hinge:
                        self.console.print(
                            f"\n[{THEME['warning']}]{g('hinge')} HINGE MOMENT DETECTED[/{THEME['warning']}] "
                            f"[{THEME['dim']}]({hinge.category.value}, {hinge.severity})[/{THEME['dim']}]"
                        )

                    response = self.agent.respond(user_input, self.conversation)
                    self.conversation.append(Message(role="user", content=user_input))
                    self.conversation.append(Message(role="assistant", content=response))

                    # Auto-log hinge moment
                    if hinge and self.manager.current:
                        self.manager.log_hinge_moment(
                            situation=f"Player declared: {user_input[:100]}",
                            choice=hinge.matched_text,
                            reasoning=f"Category: {hinge.category.value}, Severity: {hinge.severity}",
                        )
                        self.console.print(
                            f"[{THEME['dim']}]{g('hinge')} Hinge logged to chronicle[/{THEME['dim']}]"
                        )
                except Exception as e:
                    response = f"[{THEME['danger']}]Error: {e}[/{THEME['danger']}]"
                    self.last_choices = None
                    self.console.print(Panel(response, border_style=THEME["danger"]))
                    self.console.print()
                    continue

            # Parse response for choices
            narrative, choices = parse_response(response)
            self.last_choices = choices

            # Display narrative and choices
            render_narrative_block(narrative)

            if choices:
                self.console.print()
                render_choice_block(choices)

            # Show context meter
            tokens = estimate_conversation_tokens(self.conversation)
            usage_ratio = min(tokens / self.context_limit, 1.0)
            meter = format_context_meter(self.conversation, self.context_limit)
            self.console.print(f"[{THEME['dim']}]{meter}[/{THEME['dim']}]")

            # Show warning if context is getting full
            warning = context_warning(usage_ratio)
            if warning:
                self.console.print(f"[{THEME['warning']}]{g('warning')} {warning}[/{THEME['warning']}]")

            self.console.print()


def main():
    """
    Entry point for enhanced CLI

    Usage:
        python -m src.interface.enhanced_cli
        python -m src.interface.enhanced_cli --no-animate
    """
    # Parse arguments
    parser = argparse.ArgumentParser(description="SENTINEL - Enhanced CLI with Panels")
    parser.add_argument(
        "--no-animate", "-q",
        action="store_true",
        help="Skip banner animation"
    )
    parser.add_argument(
        "--no-panels",
        action="store_true",
        help="Disable persistent panels (fallback to basic CLI)"
    )
    args = parser.parse_args()

    # Initialize paths
    base_dir = Path(__file__).parent.parent.parent.parent  # SENTINEL root
    prompts_dir = Path(__file__).parent.parent.parent / "prompts"
    campaigns_dir = Path("campaigns")
    lore_dir = base_dir / "lore"

    # Load config
    config = load_config(campaigns_dir)
    saved_backend = config.get("backend", "auto")
    saved_model = config.get("model")
    animate_banner = config.get("animate_banner", True)

    # Command line overrides
    if args.no_animate:
        animate_banner = False

    # Show banner
    show_banner(animate=animate_banner)

    # Initialize manager and agent
    manager = CampaignManager(campaigns_dir)

    # Configure command completer
    command_completer.manager_ref = lambda: manager

    agent = SentinelAgent(
        manager,
        prompts_dir=prompts_dir,
        lore_dir=lore_dir if lore_dir.exists() else None,
        backend=saved_backend,
    )

    # Restore saved model
    if saved_model and agent.backend in ("lmstudio", "ollama"):
        if hasattr(agent.client, "set_model"):
            try:
                agent.client.set_model(saved_model)
            except Exception:
                pass

    # Show backend status
    show_backend_status(agent)
    if agent.lore_retriever:
        lore_status = f"Lore: {agent.lore_retriever.chunk_count} chunks"
        if agent.unified_retriever and agent.unified_retriever.memvid:
            memvid_status = "enabled" if agent.unified_retriever.memvid.is_enabled else "disabled"
            lore_status += f" | Memvid: {memvid_status}"
        console.print(f"[{THEME['dim']}]{lore_status}[/{THEME['dim']}]")
    console.print(f"[{THEME['dim']}]Type /help for commands, or just start playing.[/{THEME['dim']}]\n")

    # Run enhanced CLI or fall back to basic
    if args.no_panels:
        console.print(f"[{THEME['dim']}]Running in basic mode (panels disabled)[/{THEME['dim']}]\n")
        # Import and run standard CLI
        from .cli import main as cli_main
        cli_main()
    else:
        try:
            enhanced_cli = EnhancedCLI(
                manager=manager,
                agent=agent,
                prompts_dir=prompts_dir,
                lore_dir=lore_dir,
                campaigns_dir=campaigns_dir,
                config=config,
            )
            enhanced_cli.panels_enabled = True
            enhanced_cli.run()
        except Exception as e:
            console.print(f"[red]Failed to start enhanced CLI: {e}[/red]")
            console.print(f"\n[{THEME['dim']}]Falling back to basic CLI...[/{THEME['dim']}]")
            raise


if __name__ == "__main__":
    main()
