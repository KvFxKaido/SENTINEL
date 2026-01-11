# SENTINEL Rich Enhancement Implementation

## Goal
Add persistent status displays + QoL buttons WITHOUT breaking existing CLI commands.

## What We're Building

```
┌─ STATUS ────────────────────────────────────────────────────┐
│ CIPHER [Ghost Networks] │ Energy: 85% │ Context: 23% Normal │
└─────────────────────────────────────────────────────────────┘
┌─ FACTIONS ──────────────────────────────────────────────────┐
│ Nexus ▰▰▰▱▱ Wary │ Ember ▰▰▱▱▱ Hostile │ Ghost ▰▰▰▰▱ Trusted │
└─────────────────────────────────────────────────────────────┘

[10:45:32] NARRATIVE
The checkpoint looms ahead...

> /consult "how does Nexus see this?"

[Buttons: C=Checkpoint | X=Clear | D=Debrief | H=Help]
```

## Architecture

**Principle: CLI commands stay unchanged, we just add a display layer**

```
cli.py (existing)
  ├─ parse_command() ← stays exactly the same
  ├─ handle_input() ← stays exactly the same
  └─ main_loop() ← gets wrapped with Rich Live Display

NEW: panels.py
  ├─ StatusPanel(campaign_state) → Rich panel
  ├─ FactionPanel(campaign_state) → Rich panel
  └─ ButtonBar() → Rich text with shortcuts

NEW: enhanced_cli.py
  └─ wraps existing CLI with Live Display
```

## Implementation Steps

### Step 1: Create Panel Rendering Module

```python
# src/interface/panels.py
from rich.panel import Panel
from rich.text import Text
from rich.console import RenderableType
from rich.table import Table

def render_status_panel(campaign_state) -> Panel:
    """Persistent status display"""
    char = campaign_state.player
    context = campaign_state.context_pressure  # From your context control
    
    # Build status text
    status_line = (
        f"{char.name} [{char.background}] │ "
        f"Energy: {char.social_energy}% │ "
        f"Context: {int(context * 100)}% {get_strain_indicator(context)}"
    )
    
    return Panel(
        Text(status_line, style="cyan"),
        style="on #001100",
        border_style="blue"
    )

def render_faction_panel(campaign_state) -> Panel:
    """Faction standings at a glance"""
    table = Table.grid(padding=(0, 2))
    
    # Get top 3-4 factions by interaction frequency or standing
    top_factions = get_visible_factions(campaign_state, limit=4)
    
    for faction_name, standing in top_factions:
        bar = create_standing_bar(standing)
        mood = get_standing_mood(standing)
        table.add_column()
        table.add_row(f"{faction_name} {bar} {mood}")
    
    return Panel(
        table,
        title="FACTIONS",
        style="on #001100",
        border_style="blue"
    )

def render_button_bar() -> Text:
    """QoL shortcuts at bottom"""
    return Text(
        "[C]heckpoint | [X]Clear Context | [D]ebrief | [H]elp",
        style="dim cyan"
    )

# Helper functions

def get_strain_indicator(pressure: float) -> str:
    """Visual indicator for context strain"""
    if pressure < 0.70:
        return "Normal"
    elif pressure < 0.85:
        return "⚠ Strain I"
    elif pressure < 0.95:
        return "⚠⚠ Strain II"
    else:
        return "⚠⚠⚠ Strain III"

def create_standing_bar(standing: int) -> str:
    """Visual bar for faction standing (-100 to 100)"""
    # Map -100..100 to 0..10 blocks
    blocks = int((standing + 100) / 20)
    filled = "▰" * blocks
    empty = "▱" * (10 - blocks)
    return filled + empty

def get_standing_mood(standing: int) -> str:
    """Text label for standing"""
    if standing >= 60:
        return "Trusted"
    elif standing >= 20:
        return "Friendly"
    elif standing >= -20:
        return "Neutral"
    elif standing >= -60:
        return "Wary"
    else:
        return "Hostile"

def get_visible_factions(campaign_state, limit=4):
    """Return top N factions by relevance"""
    # Priority: recent interactions > high standing > alphabetical
    factions = campaign_state.faction_standings.items()
    
    # Simple version: just sort by standing
    sorted_factions = sorted(factions, key=lambda x: x[1], reverse=True)
    return sorted_factions[:limit]
```

### Step 2: Wrap Existing CLI with Live Display

```python
# src/interface/enhanced_cli.py
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
import sys

from .cli import CLI  # Your existing CLI class
from .panels import (
    render_status_panel,
    render_faction_panel,
    render_button_bar
)

class EnhancedCLI:
    """Wraps existing CLI with persistent panels"""
    
    def __init__(self, campaign_path: str):
        self.console = Console()
        self.cli = CLI(campaign_path)  # Your existing CLI
        self.session = PromptSession()
        self.running = True
        
    def create_layout(self) -> Layout:
        """Build the persistent display layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="status", size=3),
            Layout(name="factions", size=3),
            Layout(name="output", ratio=1),
            Layout(name="buttons", size=1)
        )
        
        return layout
    
    def update_layout(self, layout: Layout):
        """Refresh panels with current state"""
        state = self.cli.campaign_state
        
        layout["status"].update(render_status_panel(state))
        layout["factions"].update(render_faction_panel(state))
        layout["buttons"].update(render_button_bar())
        # output area is handled separately
    
    def run(self):
        """Main loop with Live Display"""
        layout = self.create_layout()
        
        with Live(layout, console=self.console, refresh_per_second=4):
            while self.running:
                # Update panels
                self.update_layout(layout)
                
                # Get user input (this doesn't block the Live display)
                try:
                    user_input = self.session.prompt(
                        "> ",
                        key_bindings=self.create_keybindings()
                    )
                except (EOFError, KeyboardInterrupt):
                    break
                
                # Handle shortcuts
                if user_input.lower() == 'c':
                    user_input = '/checkpoint'
                elif user_input.lower() == 'x':
                    user_input = '/clear'
                elif user_input.lower() == 'd':
                    user_input = '/debrief'
                elif user_input.lower() == 'h':
                    user_input = '/help'
                
                # Process through EXISTING CLI
                # This is the key: we don't change how commands work
                output = self.cli.process_input(user_input)
                
                # Display output in the output area
                self.display_output(output)
                
                # Panels will auto-update on next loop
    
    def create_keybindings(self):
        """Optional: Add keyboard shortcuts"""
        kb = KeyBindings()
        
        @kb.add('c-s')  # Ctrl+S
        def _(event):
            event.app.exit(result='/checkpoint')
        
        @kb.add('c-d')  # Ctrl+D  
        def _(event):
            event.app.exit(result='/debrief')
            
        return kb
    
    def display_output(self, output: str):
        """Show CLI output (narrative, choices, etc.)"""
        # For now, just print - in Phase 2 we can capture to layout
        self.console.print(output)

def main():
    """Entry point"""
    import sys
    
    campaign_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    enhanced_cli = EnhancedCLI(campaign_path)
    enhanced_cli.run()

if __name__ == "__main__":
    main()
```

### Step 3: Modify Existing CLI (Minimal Changes)

You need to expose two things from your existing CLI:

```python
# In src/interface/cli.py

class CLI:
    def __init__(self, campaign_path: str):
        # ... existing init ...
        self.campaign_state = None  # Make this accessible
        
    def process_input(self, user_input: str) -> str:
        """
        Extract your command handling into a function that returns output
        instead of printing directly
        """
        # Parse command
        if user_input.startswith('/'):
            command, *args = user_input[1:].split()
            return self.handle_command(command, args)
        else:
            # Regular narrative input
            return self.handle_action(user_input)
    
    def handle_command(self, command: str, args: list) -> str:
        """
        Your existing command handling, but return output instead of printing
        """
        if command == 'checkpoint':
            # ... existing logic ...
            return "Campaign saved."
        elif command == 'factions':
            # ... existing logic ...
            return faction_display
        # ... etc
```

## Phase 1 Checklist

- [ ] Create `src/interface/panels.py` with rendering functions
- [ ] Create `src/interface/enhanced_cli.py` with Live wrapper
- [ ] Modify existing CLI to expose:
  - [ ] `campaign_state` as attribute
  - [ ] `process_input(text) -> output` method
- [ ] Test that existing commands work unchanged
- [ ] Test that panels update when state changes

## Phase 2: Polish (Optional)

Once Phase 1 works:

- Add scrollback to output area (capture in layout instead of printing)
- Add color coding to strain indicators
- Add animations (pulse on hinge, flash on strain tier change)
- Add tooltips to button shortcuts
- Make faction panel collapsible

## Testing Strategy

**Test existing CLI still works:**
```bash
python -m src.interface.cli campaigns/test.json
```

**Test enhanced CLI:**
```bash
python -m src.interface.enhanced_cli campaigns/test.json
```

Both should handle commands identically.

## Rollback Plan

If something breaks:
- Enhanced CLI is a separate file - delete it
- Minimal changes to existing CLI can be reverted
- No risk to core game logic

## Next Steps After Implementation

1. Ship it and play a session
2. Note what actually matters (do you use the shortcuts?)
3. Note what's missing (wish list)
4. Decide if Textual migration is worth it later

---

**This gets you "tastefully polished" without architectural risk.**
