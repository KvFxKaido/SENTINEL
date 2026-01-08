"""
SENTINEL Rich Enhancement - Minimal CLI Modifications
Shows what needs to change in your existing CLI to work with enhancement
"""

# ============================================================================
# BEFORE: Your existing CLI structure (approximately)
# ============================================================================

class CLI_BEFORE:
    def __init__(self, campaign_path: str = None):
        self.campaign = self.load_or_create_campaign(campaign_path)
        # ... other setup ...
    
    def run(self):
        """Main loop - directly prints and loops"""
        while True:
            user_input = input("> ").strip()
            
            if user_input.startswith('/'):
                # Handle command
                self.handle_command(user_input)
            else:
                # Handle narrative action
                self.handle_action(user_input)
    
    def handle_command(self, user_input: str):
        """Process commands - prints directly"""
        command = user_input[1:].split()[0]
        
        if command == 'checkpoint':
            self.save_campaign()
            print("Campaign saved.")
        elif command == 'factions':
            for name, standing in self.campaign.faction_standings.items():
                print(f"{name}: {standing}")
        # ... etc


# ============================================================================
# AFTER: Modified to expose state and return output
# ============================================================================

class CLI_AFTER:
    def __init__(self, campaign_path: str = None):
        self.campaign = self.load_or_create_campaign(campaign_path)
        
        # CHANGE 1: Expose campaign state as attribute
        # This lets EnhancedCLI access state for panel rendering
        self.campaign_state = self.campaign
        
        # ... other setup ...
    
    def run(self):
        """Original run method - still works for standalone CLI"""
        while True:
            user_input = input("> ").strip()
            
            # CHANGE 2: Use process_input instead of inline handling
            output = self.process_input(user_input)
            if output:
                print(output)
    
    def process_input(self, user_input: str) -> str:
        """
        NEW METHOD: Process input and return output instead of printing
        
        This is the key change that lets EnhancedCLI work
        """
        if user_input.startswith('/'):
            return self.handle_command(user_input)
        else:
            return self.handle_action(user_input)
    
    def handle_command(self, user_input: str) -> str:
        """
        CHANGE 3: Return output instead of printing
        """
        command = user_input[1:].split()[0]
        
        if command == 'checkpoint':
            self.save_campaign()
            return "✓ Campaign saved."
        
        elif command == 'factions':
            lines = []
            for name, standing in self.campaign.faction_standings.items():
                lines.append(f"{name}: {standing}")
            return "\n".join(lines)
        
        # ... etc
        
        return f"Unknown command: {command}"
    
    def handle_action(self, user_input: str) -> str:
        """
        CHANGE 3 (continued): Return narrative output
        """
        # Process player action through agent
        response = self.agent.process(user_input)
        
        # Return formatted response instead of printing
        return self.format_response(response)


# ============================================================================
# MIGRATION CHECKLIST
# ============================================================================

"""
1. Add `self.campaign_state = self.campaign` in __init__
   └─ This exposes state for panel rendering

2. Create `process_input(text) -> str` method
   └─ Wraps your existing command/action handling
   └─ Returns output instead of printing

3. Modify command handlers to return strings
   └─ Change: print("Success")
   └─ To:     return "Success"

4. Test that BOTH interfaces work:
   └─ python -m src.interface.cli (original)
   └─ python -m src.interface.enhanced_cli (new)
"""


# ============================================================================
# EXAMPLE: Converting a command handler
# ============================================================================

def handle_factions_BEFORE(self):
    """Original - prints directly"""
    print("\n=== FACTION STANDINGS ===")
    for name, standing in self.campaign.faction_standings.items():
        mood = self.get_standing_mood(standing)
        print(f"{name:20} {standing:+4d}  [{mood}]")
    print()


def handle_factions_AFTER(self) -> str:
    """Modified - returns output"""
    lines = ["\n=== FACTION STANDINGS ==="]
    
    for name, standing in self.campaign.faction_standings.items():
        mood = self.get_standing_mood(standing)
        lines.append(f"{name:20} {standing:+4d}  [{mood}]")
    
    lines.append("")  # Blank line at end
    return "\n".join(lines)


# ============================================================================
# ROLLBACK SAFETY
# ============================================================================

"""
If something breaks, you can roll back safely:

1. Keep your original CLI.run() method
   └─ It still works standalone

2. Delete enhanced_cli.py and panels.py
   └─ No risk to core game

3. Remove the three small changes above
   └─ campaign_state attribute
   └─ process_input method
   └─ return statements in handlers

The modification is minimal and reversible.
"""
