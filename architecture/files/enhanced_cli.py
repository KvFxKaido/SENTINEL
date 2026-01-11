"""
SENTINEL Rich Enhancement - Enhanced CLI Wrapper
Adds persistent panels + QoL buttons to existing CLI
"""
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
import sys
from pathlib import Path

# Import your existing CLI and the panel renderers
# Adjust these imports based on your actual structure
try:
    from src.interface.cli import CLI
    from src.interface.panels import (
        render_status_panel,
        render_faction_panel,
        render_button_bar
    )
except ImportError:
    # Fallback for testing
    print("Note: Import paths need adjustment for your project structure")
    print("Update imports in enhanced_cli.py")
    sys.exit(1)


class EnhancedCLI:
    """
    Wrapper around existing CLI that adds persistent panels
    
    Architecture:
    - Existing CLI commands work unchanged
    - Live Display shows persistent status/faction panels
    - Keyboard shortcuts trigger existing commands
    - Output still goes to console (Phase 1 simplicity)
    """
    
    def __init__(self, campaign_path: str = None):
        self.console = Console()
        self.cli = CLI(campaign_path)  # Your existing CLI
        self.session = PromptSession()
        self.running = True
        
        # Track whether to show panels (can toggle off)
        self.panels_enabled = True
    
    def create_layout(self) -> Layout:
        """
        Build the persistent display layout
        
        Structure:
        ┌─ status (3 lines)
        ├─ factions (3 lines)
        ├─ output (flexible)
        └─ buttons (1 line)
        """
        layout = Layout()
        
        layout.split_column(
            Layout(name="status", size=3),
            Layout(name="factions", size=3),
            Layout(name="spacer", size=1),  # Visual breathing room
            Layout(name="buttons", size=1)
        )
        
        return layout
    
    def update_panels(self, layout: Layout):
        """
        Refresh panels with current campaign state
        Called after every command to keep panels in sync
        """
        if not self.panels_enabled:
            return
        
        state = self.cli.campaign_state
        
        try:
            layout["status"].update(render_status_panel(state))
            layout["factions"].update(render_faction_panel(state))
            layout["buttons"].update(render_button_bar())
        except Exception as e:
            # Graceful degradation if panel rendering fails
            self.console.print(f"[dim red]Panel update error: {e}[/dim red]")
    
    def create_keybindings(self) -> KeyBindings:
        """
        Optional keyboard shortcuts
        
        Ctrl+S = /checkpoint
        Ctrl+D = /debrief
        Ctrl+X = /clear
        """
        kb = KeyBindings()
        
        @kb.add('c-s')
        def checkpoint(event):
            """Ctrl+S: Checkpoint"""
            event.app.exit(result='/checkpoint')
        
        @kb.add('c-d')
        def debrief(event):
            """Ctrl+D: Debrief"""
            event.app.exit(result='/debrief')
        
        @kb.add('c-x')
        def clear_context(event):
            """Ctrl+X: Clear context"""
            event.app.exit(result='/clear')
        
        @kb.add('c-h')
        def help_command(event):
            """Ctrl+H: Help"""
            event.app.exit(result='/help')
        
        return kb
    
    def expand_shortcuts(self, user_input: str) -> str:
        """
        Expand single-letter shortcuts to full commands
        
        c -> /checkpoint
        x -> /clear
        d -> /debrief
        h -> /help
        """
        shortcuts = {
            'c': '/checkpoint',
            'x': '/clear',
            'd': '/debrief',
            'h': '/help'
        }
        
        # Only expand if it's exactly one letter
        if len(user_input) == 1 and user_input.lower() in shortcuts:
            return shortcuts[user_input.lower()]
        
        return user_input
    
    def run(self):
        """
        Main loop with Live Display
        
        Flow:
        1. Display persistent panels
        2. Get user input (prompt stays below panels)
        3. Expand shortcuts if needed
        4. Process through existing CLI
        5. Update panels
        6. Repeat
        """
        layout = self.create_layout()
        
        self.console.print("[bold cyan]SENTINEL[/bold cyan] - Enhanced CLI")
        self.console.print("[dim]Type commands or use shortcuts: C=Checkpoint | X=Clear | D=Debrief | H=Help[/dim]\n")
        
        with Live(
            layout,
            console=self.console,
            refresh_per_second=2,  # Don't need high refresh for text
            screen=False  # Don't clear screen, allow scrollback
        ):
            while self.running:
                # Update panels with current state
                self.update_panels(layout)
                
                # Get user input
                try:
                    user_input = self.session.prompt(
                        "\n> ",
                        key_bindings=self.create_keybindings()
                    ).strip()
                except KeyboardInterrupt:
                    self.console.print("\n[dim]Use /quit to exit[/dim]")
                    continue
                except EOFError:
                    break
                
                if not user_input:
                    continue
                
                # Expand shortcuts (c -> /checkpoint, etc.)
                user_input = self.expand_shortcuts(user_input)
                
                # Handle exit
                if user_input in ['/quit', '/exit', 'quit', 'exit']:
                    self.console.print("[cyan]Exiting SENTINEL...[/cyan]")
                    break
                
                # Process through EXISTING CLI
                # This is the critical part: we don't change command handling
                try:
                    output = self.cli.process_input(user_input)
                    if output:
                        self.console.print(output)
                except Exception as e:
                    self.console.print(f"[red]Error: {e}[/red]")
                
                # Panels will auto-update on next loop


def main():
    """
    Entry point for enhanced CLI
    
    Usage:
        python -m src.interface.enhanced_cli
        python -m src.interface.enhanced_cli campaigns/my_campaign.json
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="SENTINEL Enhanced CLI")
    parser.add_argument(
        'campaign',
        nargs='?',
        default=None,
        help='Path to campaign file (optional)'
    )
    parser.add_argument(
        '--no-panels',
        action='store_true',
        help='Disable persistent panels (fallback to basic CLI)'
    )
    
    args = parser.parse_args()
    
    try:
        enhanced_cli = EnhancedCLI(args.campaign)
        enhanced_cli.panels_enabled = not args.no_panels
        enhanced_cli.run()
    except Exception as e:
        console = Console()
        console.print(f"[red]Failed to start enhanced CLI: {e}[/red]")
        console.print("\n[dim]Falling back to basic CLI...[/dim]")
        # Could fall back to regular CLI here
        raise


if __name__ == "__main__":
    main()
