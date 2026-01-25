"""
Tool registry for SENTINEL agent.

Centralizes tool schemas and handlers in one place.
Agent imports the registry and delegates tool execution.
"""

from typing import Callable, Any
from ..state import get_event_bus, EventType
from ..state.schema import FactionName, LeverageWeight


# -----------------------------------------------------------------------------
# Tool Schemas
# -----------------------------------------------------------------------------

# Dice tools (also defined in dice.py, but centralized here for single source)
DICE_SCHEMAS = [
    {
        "name": "roll_check",
        "description": "Roll a d20 skill check with optional advantage/disadvantage",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill": {
                    "type": "string",
                    "description": "The skill being tested (e.g., 'Persuasion', 'Stealth')",
                },
                "dc": {
                    "type": "integer",
                    "enum": [10, 14, 18, 22],
                    "description": "Difficulty class: 10=Standard, 14=Challenging, 18=Difficult, 22=Near-Impossible",
                },
                "trained": {
                    "type": "boolean",
                    "description": "Whether the character has expertise (+5 modifier)",
                    "default": True,
                },
                "advantage": {
                    "type": "boolean",
                    "description": "Roll 2d20, take higher",
                    "default": False,
                },
                "disadvantage": {
                    "type": "boolean",
                    "description": "Roll 2d20, take lower",
                    "default": False,
                },
            },
            "required": ["skill", "dc"],
        },
    },
    {
        "name": "tactical_reset",
        "description": "Spend 10% social energy to gain advantage on next social roll",
        "input_schema": {
            "type": "object",
            "properties": {
                "current_energy": {
                    "type": "integer",
                    "description": "Current social energy percentage (0-100)",
                },
                "ritual_description": {
                    "type": "string",
                    "description": "How the character resets (e.g., 'a deep breath')",
                },
            },
            "required": ["current_energy", "ritual_description"],
        },
    },
]

# Character tools
CHARACTER_SCHEMAS = [
    {
        "name": "update_character",
        "description": "Modify character state (credits, social energy)",
        "input_schema": {
            "type": "object",
            "properties": {
                "character_id": {"type": "string"},
                "credits_delta": {"type": "integer", "default": 0},
                "social_energy_delta": {"type": "integer", "default": 0},
            },
            "required": ["character_id"],
        },
    },
    {
        "name": "invoke_restorer",
        "description": "Spend 10% social energy to gain advantage when acting in your element. Only works if the action matches one of the character's restorers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "character_id": {"type": "string"},
                "action": {
                    "type": "string",
                    "description": "What the character is doing (must align with their restorers)",
                },
            },
            "required": ["character_id", "action"],
        },
    },
    {
        "name": "declare_push",
        "description": "Player explicitly invites a consequence for advantage. Use when player accepts a Devil's Bargain. Queues a dormant thread with the consequence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "character_id": {"type": "string"},
                "goal": {
                    "type": "string",
                    "description": "What they're pushing for (e.g., 'to convince the guard')",
                },
                "consequence": {
                    "type": "string",
                    "description": "What will happen later as a result of the push",
                },
                "severity": {
                    "type": "string",
                    "enum": ["minor", "moderate", "major"],
                    "default": "moderate",
                },
            },
            "required": ["character_id", "goal", "consequence"],
        },
    },
]

# Faction tools
FACTION_SCHEMAS = [
    {
        "name": "update_faction",
        "description": "Shift faction standing",
        "input_schema": {
            "type": "object",
            "properties": {
                "faction": {
                    "type": "string",
                    "enum": [f.value for f in FactionName],
                },
                "delta": {
                    "type": "integer",
                    "enum": [-2, -1, 1],
                    "description": "-2=betray, -1=oppose, +1=help",
                },
                "reason": {"type": "string"},
            },
            "required": ["faction", "delta", "reason"],
        },
    },
]

# NPC tools
NPC_SCHEMAS = [
    {
        "name": "update_npc",
        "description": "Update NPC disposition or add memory",
        "input_schema": {
            "type": "object",
            "properties": {
                "npc_id": {"type": "string"},
                "disposition": {
                    "type": "string",
                    "enum": ["hostile", "wary", "neutral", "warm", "loyal"],
                },
                "memory": {
                    "type": "string",
                    "description": "New memory to add (what the NPC now remembers)",
                },
            },
            "required": ["npc_id"],
        },
    },
    {
        "name": "trigger_npc_memory",
        "description": "Fire NPC memory triggers based on event tags",
        "input_schema": {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Event tags like 'helped_ember', 'betrayed_lattice'",
                },
            },
            "required": ["tags"],
        },
    },
    {
        "name": "describe_npc_appearance",
        "description": "Record an NPC's physical appearance for portrait generation. Call this when first describing an NPC or when asked about their appearance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "NPC's full name",
                },
                "faction": {
                    "type": "string",
                    "description": "Faction affiliation",
                },
                "gender": {
                    "type": "string",
                    "enum": ["masculine", "feminine", "androgynous"],
                },
                "age": {
                    "type": "string",
                    "enum": ["young", "adult", "middle-aged", "elder"],
                },
                "skin_tone": {
                    "type": "string",
                    "description": "e.g., pale, fair, medium, olive, brown, dark",
                },
                "build": {
                    "type": "string",
                    "enum": ["slight", "lean", "average", "athletic", "stocky", "heavy"],
                },
                "hair_color": {"type": "string"},
                "hair_length": {
                    "type": "string",
                    "enum": ["bald", "short", "medium", "long"],
                },
                "hair_style": {
                    "type": "string",
                    "description": "e.g., straight, curly, braided, mohawk, dreadlocks",
                },
                "eye_color": {"type": "string"},
                "facial_features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Distinctive facial features like 'sharp jawline', 'high cheekbones'",
                },
                "augmentations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Visible cybernetic enhancements",
                },
                "scars": {"type": "string", "description": "Notable scars"},
                "tattoos": {"type": "string", "description": "Visible tattoos"},
                "other_features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Clothing, accessories, distinctive items always present",
                },
                "default_expression": {
                    "type": "string",
                    "description": "Typical expression: wary, stern, warm, amused, neutral",
                },
            },
            "required": ["name", "gender", "age", "skin_tone", "build", "hair_color", "eye_color"],
        },
    },
    {
        "name": "acquire_leverage",
        "description": "Record that the player has discovered compromising information about an NPC. This creates leverage that can be used for coercive persuasion.",
        "input_schema": {
            "type": "object",
            "properties": {
                "npc_id": {"type": "string"},
                "leverage_type": {
                    "type": "string",
                    "enum": ["financial", "personal", "professional", "faction", "criminal"],
                    "description": "Category of compromising info",
                },
                "description": {
                    "type": "string",
                    "description": "What the player discovered (e.g., 'Embezzled 2000 credits from Lattice')",
                },
            },
            "required": ["npc_id", "leverage_type", "description"],
        },
    },
    {
        "name": "use_leverage",
        "description": "Use leverage the player holds over an NPC. Costs social energy and may create consequences.",
        "input_schema": {
            "type": "object",
            "properties": {
                "npc_id": {"type": "string"},
                "action": {
                    "type": "string",
                    "enum": ["threaten", "deploy", "burn"],
                    "description": "threaten=implicit pressure (-10 energy), deploy=explicit use (-15 energy, resentment), burn=public exposure (-20 energy, NPC ruined/hostile)",
                },
            },
            "required": ["npc_id", "action"],
        },
    },
]

# Hinge and thread tools
CONSEQUENCE_SCHEMAS = [
    {
        "name": "log_hinge_moment",
        "description": "Record an irreversible choice",
        "input_schema": {
            "type": "object",
            "properties": {
                "situation": {"type": "string"},
                "choice": {"type": "string"},
                "reasoning": {"type": "string"},
            },
            "required": ["situation", "choice", "reasoning"],
        },
    },
    {
        "name": "queue_dormant_thread",
        "description": "Schedule a delayed consequence",
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {"type": "string"},
                "trigger_condition": {"type": "string"},
                "consequence": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["minor", "moderate", "major"],
                    "default": "moderate",
                },
            },
            "required": ["origin", "trigger_condition", "consequence"],
        },
    },
    {
        "name": "surface_dormant_thread",
        "description": "Activate a dormant thread when its trigger condition is met.",
        "input_schema": {
            "type": "object",
            "properties": {
                "thread_id": {"type": "string"},
                "activation_context": {
                    "type": "string",
                    "description": "What player action triggered this consequence",
                },
            },
            "required": ["thread_id", "activation_context"],
        },
    },
    {
        "name": "log_avoidance",
        "description": "Record when a player chooses not to engage with a significant situation. Non-action is content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "situation": {"type": "string"},
                "what_was_at_stake": {"type": "string"},
                "potential_consequence": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["minor", "moderate", "major"],
                    "default": "moderate",
                },
            },
            "required": ["situation", "what_was_at_stake", "potential_consequence"],
        },
    },
    {
        "name": "surface_avoidance",
        "description": "Mark an avoidance as surfaced when its consequences come due.",
        "input_schema": {
            "type": "object",
            "properties": {
                "avoidance_id": {"type": "string"},
                "what_happened": {"type": "string"},
            },
            "required": ["avoidance_id", "what_happened"],
        },
    },
]

# Enhancement tools
ENHANCEMENT_SCHEMAS = [
    {
        "name": "grant_enhancement",
        "description": "Grant a faction enhancement to a character. Creates leverage tracking. Wanderers and Cultivators don't offer enhancements.",
        "input_schema": {
            "type": "object",
            "properties": {
                "character_id": {"type": "string"},
                "name": {"type": "string"},
                "source": {
                    "type": "string",
                    "enum": [f.value for f in FactionName if f not in (
                        FactionName.WANDERERS, FactionName.CULTIVATORS
                    )],
                },
                "benefit": {"type": "string"},
                "cost": {"type": "string"},
            },
            "required": ["character_id", "name", "source", "benefit", "cost"],
        },
    },
    {
        "name": "refuse_enhancement",
        "description": "Record when a character refuses an enhancement offer. Refusal builds reputation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "character_id": {"type": "string"},
                "name": {"type": "string"},
                "source": {
                    "type": "string",
                    "enum": [f.value for f in FactionName],
                },
                "benefit": {"type": "string"},
                "reason_refused": {"type": "string"},
            },
            "required": ["character_id", "name", "source", "benefit", "reason_refused"],
        },
    },
]

# Leverage tools
LEVERAGE_SCHEMAS = [
    {
        "name": "call_leverage",
        "description": "A faction calls in leverage on an enhancement they granted. Creates a formal demand.",
        "input_schema": {
            "type": "object",
            "properties": {
                "character_id": {"type": "string"},
                "enhancement_id": {"type": "string"},
                "demand": {"type": "string"},
                "weight": {
                    "type": "string",
                    "enum": ["light", "medium", "heavy"],
                    "default": "medium",
                },
                "threat_basis": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Why the faction has leverage",
                },
                "deadline": {"type": "string"},
                "deadline_sessions": {"type": "integer"},
                "consequences": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["character_id", "enhancement_id", "demand"],
        },
    },
    {
        "name": "escalate_demand",
        "description": "Escalate an unresolved leverage demand.",
        "input_schema": {
            "type": "object",
            "properties": {
                "character_id": {"type": "string"},
                "enhancement_id": {"type": "string"},
                "escalation_type": {
                    "type": "string",
                    "enum": ["queue_consequence", "increase_weight", "faction_action"],
                },
                "narrative": {"type": "string"},
            },
            "required": ["character_id", "enhancement_id", "escalation_type"],
        },
    },
    {
        "name": "resolve_leverage",
        "description": "Record player's response to a leverage call.",
        "input_schema": {
            "type": "object",
            "properties": {
                "character_id": {"type": "string"},
                "enhancement_id": {"type": "string"},
                "response": {
                    "type": "string",
                    "enum": ["comply", "resist", "negotiate"],
                },
                "outcome": {"type": "string"},
            },
            "required": ["character_id", "enhancement_id", "response", "outcome"],
        },
    },
]

# Session tools
SESSION_SCHEMAS = [
    {
        "name": "set_phase",
        "description": "Advance the mission phase. Each phase changes GM guidance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "enum": ["briefing", "planning", "execution", "resolution", "debrief", "between"],
                },
            },
            "required": ["phase"],
        },
    },
]

# Interrupt tools
INTERRUPT_SCHEMAS = [
    {
        "name": "npc_interrupt",
        "description": "Deliver an NPC interrupt to the player. Use when prompted that an NPC wants to interrupt. The message should be in the NPC's voice.",
        "input_schema": {
            "type": "object",
            "properties": {
                "npc_name": {
                    "type": "string",
                    "description": "Name of the interrupting NPC",
                },
                "message": {
                    "type": "string",
                    "description": "What the NPC says (in character, 1-3 sentences)",
                },
                "urgency": {
                    "type": "string",
                    "enum": ["medium", "high", "critical"],
                    "description": "How urgent this interrupt feels",
                    "default": "medium",
                },
            },
            "required": ["npc_name", "message"],
        },
    },
]


def get_all_schemas() -> list[dict]:
    """Get all tool schemas as a flat list."""
    return (
        DICE_SCHEMAS +
        CHARACTER_SCHEMAS +
        FACTION_SCHEMAS +
        NPC_SCHEMAS +
        CONSEQUENCE_SCHEMAS +
        ENHANCEMENT_SCHEMAS +
        LEVERAGE_SCHEMAS +
        SESSION_SCHEMAS +
        INTERRUPT_SCHEMAS
    )


# -----------------------------------------------------------------------------
# Tool Registry
# -----------------------------------------------------------------------------

class ToolRegistry:
    """
    Registry for tool handlers.

    Decouples tool execution from the agent. The agent registers handlers,
    and the registry handles dispatch.
    """

    def __init__(self):
        self._handlers: dict[str, Callable[..., dict]] = {}

    def register(self, name: str, handler: Callable[..., dict]) -> None:
        """Register a tool handler."""
        self._handlers[name] = handler

    def register_all(self, handlers: dict[str, Callable[..., dict]]) -> None:
        """Register multiple handlers at once."""
        self._handlers.update(handlers)

    def execute(self, name: str, arguments: dict) -> dict:
        """Execute a tool by name."""
        if name not in self._handlers:
            return {"error": f"Unknown tool: {name}"}

        try:
            return self._handlers[name](**arguments)
        except Exception as e:
            return {"error": str(e)}

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._handlers

    @property
    def tool_names(self) -> list[str]:
        """List all registered tool names."""
        return list(self._handlers.keys())

    def get_schemas(self) -> list[dict]:
        """Get schemas for all registered tools."""
        all_schemas = get_all_schemas()
        return [s for s in all_schemas if s["name"] in self._handlers]


def create_default_registry(manager: "CampaignManager") -> ToolRegistry:
    """
    Create a registry with all default tool handlers.

    Args:
        manager: The campaign manager for state operations

    Returns:
        Configured ToolRegistry with all handlers
    """
    from .dice import roll_check, tactical_reset

    registry = ToolRegistry()

    # Dice handlers
    def handle_roll_check(**kwargs) -> dict:
        result = roll_check(**kwargs)
        return {
            "rolls": result.rolls,
            "used": result.used,
            "modifier": result.modifier,
            "total": result.total,
            "dc": result.dc,
            "success": result.success,
            "margin": result.margin,
            "narrative": result.narrative,
        }

    def handle_tactical_reset(**kwargs) -> dict:
        result = tactical_reset(**kwargs)
        return {
            "old_energy": result.old_energy,
            "new_energy": result.new_energy,
            "advantage_granted": result.advantage_granted,
            "narrative_hint": result.narrative_hint,
        }

    # Character handlers
    def handle_update_character(**kwargs) -> dict:
        result = manager.update_character(
            character_id=kwargs["character_id"],
            credits_delta=kwargs.get("credits_delta", 0),
            social_energy_delta=kwargs.get("social_energy_delta", 0),
        )
        return result or {"error": "Character not found"}

    def handle_invoke_restorer(**kwargs) -> dict:
        return manager.invoke_restorer(
            character_id=kwargs["character_id"],
            action=kwargs["action"],
        )

    def handle_declare_push(**kwargs) -> dict:
        return manager.declare_push(
            character_id=kwargs["character_id"],
            goal=kwargs["goal"],
            consequence=kwargs["consequence"],
            severity=kwargs.get("severity", "moderate"),
        )

    # Faction handlers
    def handle_update_faction(**kwargs) -> dict:
        faction = FactionName(kwargs["faction"])
        return manager.shift_faction(
            faction=faction,
            delta=kwargs["delta"],
            reason=kwargs["reason"],
        )

    # NPC handlers
    def handle_update_npc(**kwargs) -> dict:
        npc_id = kwargs["npc_id"]
        results = {}

        if "disposition" in kwargs:
            disp_result = manager.update_npc_disposition(
                npc_id=npc_id,
                disposition=kwargs["disposition"],
            )
            if disp_result:
                results["disposition"] = disp_result
            else:
                return {"error": f"NPC not found: {npc_id}"}

        if "memory" in kwargs:
            success = manager.update_npc_memory(npc_id, kwargs["memory"])
            results["memory_added"] = success

        if not results:
            return {"error": "No updates specified"}

        return results

    def handle_trigger_memory(**kwargs) -> dict:
        tags = kwargs["tags"]
        triggered = manager.check_npc_triggers(tags)
        return {
            "tags_checked": tags,
            "triggered_count": len(triggered),
            "reactions": triggered,
        }

    def handle_describe_npc_appearance(**kwargs) -> dict:
        """Save NPC appearance to campaign-specific character YAML for portrait generation."""
        from ..state.character_yaml import save_character_yaml

        name = kwargs["name"]

        # Get campaign ID for campaign-specific storage
        campaign_id = None
        if manager.current:
            campaign_id = manager.current.meta.id

        # Build appearance data from kwargs
        data = {
            "name": name,
            "faction": kwargs.get("faction", "unknown"),
            "role": kwargs.get("role", "contact"),
            "gender": kwargs.get("gender", "unknown"),
            "age": kwargs.get("age", "adult"),
            "skin_tone": kwargs.get("skin_tone", "unknown"),
            "build": kwargs.get("build", "average"),
            "hair_color": kwargs.get("hair_color", "unknown"),
            "hair_length": kwargs.get("hair_length", "unknown"),
            "hair_style": kwargs.get("hair_style", "unknown"),
            "eye_color": kwargs.get("eye_color", "unknown"),
            "facial_features": kwargs.get("facial_features", []),
            "augmentations": kwargs.get("augmentations", []),
            "scars": kwargs.get("scars"),
            "tattoos": kwargs.get("tattoos"),
            "other_features": kwargs.get("other_features", []),
            "default_expression": kwargs.get("default_expression", "neutral"),
        }

        # Save to campaign-specific directory
        yaml_path = save_character_yaml(name, data, campaign_id)

        return {
            "saved": True,
            "path": str(yaml_path.name),
            "campaign_id": campaign_id,
            "name": name,
            "narrative_hint": f"Appearance recorded for {name}. Portrait can be generated with /portrait.",
        }

    def handle_acquire_leverage(**kwargs) -> dict:
        """Record player discovering compromising info about an NPC."""
        from ..state.schema import PlayerLeverage, LeverageType

        npc_id = kwargs["npc_id"]
        leverage_type = kwargs["leverage_type"]
        description = kwargs["description"]

        # Find the NPC
        npc = manager.get_npc(npc_id)
        if not npc:
            return {"error": f"NPC not found: {npc_id}"}

        # Check if already has leverage
        if npc.player_leverage:
            return {
                "error": "Already hold leverage over this NPC",
                "existing": npc.player_leverage.description,
            }

        # Get current session
        session = manager.current.meta.session_count if manager.current else 1

        # Create the leverage record
        npc.player_leverage = PlayerLeverage(
            type=LeverageType(leverage_type),
            description=description,
            acquired_session=session,
        )

        # Save the campaign
        manager.save()

        return {
            "acquired": True,
            "npc": npc.name,
            "leverage_type": leverage_type,
            "description": description,
            "narrative_hint": f"You now hold leverage over {npc.name}. This can be used for coercive persuasion, but comes with costs.",
        }

    def handle_use_leverage(**kwargs) -> dict:
        """Use leverage the player holds over an NPC."""
        npc_id = kwargs["npc_id"]
        action = kwargs["action"]

        # Find the NPC
        npc = manager.get_npc(npc_id)
        if not npc:
            return {"error": f"NPC not found: {npc_id}"}

        # Get current session
        session = manager.current.meta.session_count if manager.current else 1

        # Use the leverage
        result = npc.use_leverage(action, session)

        if not result["success"]:
            return result

        # Apply social energy cost
        char = manager.current.characters[0] if manager.current and manager.current.characters else None
        if char and char.social_energy:
            char.social_energy.current = max(0, char.social_energy.current - result["social_cost"])

        # Create dormant thread if needed
        if result["creates_thread"]:
            manager.queue_dormant_thread(
                origin=f"{npc.name} coerced via leverage",
                trigger_condition=f"{npc.name} finds opportunity for retaliation",
                consequence=f"{npc.name} attempts to expose or harm the player",
                severity="moderate" if action == "deploy" else "major",
            )

        # Save the campaign
        manager.save()

        return {
            "success": True,
            "npc": npc.name,
            "action": action,
            "social_cost": result["social_cost"],
            "npc_coerced": npc.coerced,
            "npc_resentful": npc.resentment,
            "thread_created": result["creates_thread"],
            "narrative_hint": _leverage_narrative(action, npc.name),
        }

    def _leverage_narrative(action: str, npc_name: str) -> str:
        """Generate narrative hint for leverage use."""
        if action == "threaten":
            return f"{npc_name} cooperates, but you see the calculation in their eyes. They're weighing options."
        elif action == "deploy":
            return f"{npc_name} has no choice but to comply. The resentment is palpable. They will remember this."
        else:  # burn
            return f"{npc_name}'s reputation is destroyed. Whatever relationship existed is gone. They have nothing left to lose."

    # Consequence handlers
    def handle_log_hinge(**kwargs) -> dict:
        entry = manager.log_hinge_moment(
            situation=kwargs["situation"],
            choice=kwargs["choice"],
            reasoning=kwargs["reasoning"],
        )
        return {"id": entry.id, "logged": True}

    def handle_queue_thread(**kwargs) -> dict:
        thread = manager.queue_dormant_thread(
            origin=kwargs["origin"],
            trigger_condition=kwargs["trigger_condition"],
            consequence=kwargs["consequence"],
            severity=kwargs.get("severity", "moderate"),
        )
        return {"id": thread.id, "queued": True}

    def handle_surface_thread(**kwargs) -> dict:
        thread = manager.surface_dormant_thread(
            thread_id=kwargs["thread_id"],
            activation_context=kwargs["activation_context"],
        )
        if thread:
            return {
                "surfaced": True,
                "consequence": thread.consequence,
                "severity": thread.severity.value,
                "origin": thread.origin,
            }
        return {"error": f"Thread not found: {kwargs['thread_id']}"}

    def handle_log_avoidance(**kwargs) -> dict:
        avoided = manager.log_avoidance(
            situation=kwargs["situation"],
            what_was_at_stake=kwargs["what_was_at_stake"],
            potential_consequence=kwargs["potential_consequence"],
            severity=kwargs.get("severity", "moderate"),
        )
        return {
            "id": avoided.id,
            "situation": avoided.situation,
            "severity": avoided.severity.value,
            "narrative_hint": "The world moves on. This may resurface.",
        }

    def handle_surface_avoidance(**kwargs) -> dict:
        avoided = manager.surface_avoidance(
            avoidance_id=kwargs["avoidance_id"],
            what_happened=kwargs["what_happened"],
        )
        if avoided:
            return {
                "id": avoided.id,
                "situation": avoided.situation,
                "what_happened": kwargs["what_happened"],
                "severity": avoided.severity.value,
            }
        return {"error": "Avoidance not found or already surfaced"}

    # Enhancement handlers
    def handle_grant_enhancement(**kwargs) -> dict:
        try:
            source = FactionName(kwargs["source"])
            enhancement = manager.grant_enhancement(
                character_id=kwargs["character_id"],
                name=kwargs["name"],
                source=source,
                benefit=kwargs["benefit"],
                cost=kwargs["cost"],
            )
            return {
                "id": enhancement.id,
                "name": enhancement.name,
                "source": enhancement.source.value,
                "benefit": enhancement.benefit,
                "cost": enhancement.cost,
                "granted": True,
                "narrative_hint": f"Accepted {source.value} enhancement. They won't forget.",
            }
        except ValueError as e:
            return {"error": str(e)}

    def handle_refuse_enhancement(**kwargs) -> dict:
        try:
            source = FactionName(kwargs["source"])
            refusal = manager.refuse_enhancement(
                character_id=kwargs["character_id"],
                name=kwargs["name"],
                source=source,
                benefit=kwargs["benefit"],
                reason_refused=kwargs["reason_refused"],
            )

            rep = manager.get_refusal_reputation(kwargs["character_id"])

            result = {
                "id": refusal.id,
                "name": refusal.name,
                "source": refusal.source.value,
                "refused": True,
                "reason": refusal.reason_refused,
            }

            if rep:
                result["reputation"] = rep

            return result
        except ValueError as e:
            return {"error": str(e)}

    # Leverage handlers
    def handle_call_leverage(**kwargs) -> dict:
        return manager.call_leverage(
            character_id=kwargs["character_id"],
            enhancement_id=kwargs["enhancement_id"],
            demand=kwargs["demand"],
            weight=kwargs.get("weight", "medium"),
            threat_basis=kwargs.get("threat_basis"),
            deadline=kwargs.get("deadline"),
            deadline_sessions=kwargs.get("deadline_sessions"),
            consequences=kwargs.get("consequences"),
        )

    def handle_escalate_demand(**kwargs) -> dict:
        return manager.escalate_demand(
            character_id=kwargs["character_id"],
            enhancement_id=kwargs["enhancement_id"],
            escalation_type=kwargs["escalation_type"],
            narrative=kwargs.get("narrative", ""),
        )

    def handle_resolve_leverage(**kwargs) -> dict:
        return manager.resolve_leverage(
            character_id=kwargs["character_id"],
            enhancement_id=kwargs["enhancement_id"],
            response=kwargs["response"],
            outcome=kwargs["outcome"],
        )

    # Session handlers
    def handle_set_phase(**kwargs) -> dict:
        return manager.set_phase(phase=kwargs["phase"])

    # Interrupt handlers
    def handle_npc_interrupt(
        npc_name: str, message: str, urgency: str = "medium", **kwargs
    ) -> dict:
        """Signal TUI to show codec interrupt modal."""
        npc_id = None
        faction = None
        disposition = None
        if manager.current:
            target = npc_name.strip().lower()
            candidates = manager.current.npcs.active + manager.current.npcs.dormant
            for npc in candidates:
                if npc.name.strip().lower() == target:
                    npc_id = npc.id
                    faction = npc.faction.value if npc.faction else None
                    faction_standing = None
                    if npc.faction:
                        faction_standing = manager.current.factions.get(npc.faction).standing
                    disposition = npc.get_effective_disposition(faction_standing).value
                    break

        if manager.current:
            get_event_bus().emit(
                EventType.NPC_INTERRUPT,
                campaign_id=manager.current.meta.id,
                session=manager.current.meta.session_count,
                npc_id=npc_id,
                npc_name=npc_name,
                faction=faction,
                disposition=disposition,
                message=message,
                urgency=urgency,
                state="incoming",
            )

        return {
            "interrupt": True,
            "npc_name": npc_name,
            "message": message,
            "urgency": urgency,
        }

    # Register all handlers
    registry.register_all({
        "roll_check": handle_roll_check,
        "tactical_reset": handle_tactical_reset,
        "update_character": handle_update_character,
        "invoke_restorer": handle_invoke_restorer,
        "declare_push": handle_declare_push,
        "update_faction": handle_update_faction,
        "update_npc": handle_update_npc,
        "trigger_npc_memory": handle_trigger_memory,
        "describe_npc_appearance": handle_describe_npc_appearance,
        "acquire_leverage": handle_acquire_leverage,
        "use_leverage": handle_use_leverage,
        "log_hinge_moment": handle_log_hinge,
        "queue_dormant_thread": handle_queue_thread,
        "surface_dormant_thread": handle_surface_thread,
        "log_avoidance": handle_log_avoidance,
        "surface_avoidance": handle_surface_avoidance,
        "grant_enhancement": handle_grant_enhancement,
        "refuse_enhancement": handle_refuse_enhancement,
        "call_leverage": handle_call_leverage,
        "escalate_demand": handle_escalate_demand,
        "resolve_leverage": handle_resolve_leverage,
        "set_phase": handle_set_phase,
        "npc_interrupt": handle_npc_interrupt,
    })

    return registry
