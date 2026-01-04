# GEMINI.md

Context and guidelines for Gemini models working on the SENTINEL project.

## Project Overview

SENTINEL is an AI-driven tabletop RPG engine focusing on political tension, ethical tradeoffs, and survival.
The system is composed of a Python-based CLI agent (`sentinel-agent`) and a Model Context Protocol server (`sentinel-mcp`) that manages world state and faction dynamics.

## System Architecture

### Core Components
*   **`sentinel-agent/`**: The primary executable and Orchestrator.
    *   **`src/agent.py`**: The main game loop (Input -> Retrieve -> Decide -> Render).
    *   **`src/state/`**: Pydantic models defining the game state. **Critical**: This is the single source of truth for runtime data.
    *   **`src/llm/`**: Abstraction layer for LLM providers (Claude, OpenAI, Local).
    *   **`src/interface/`**: Handles CLI rendering, glyphs, and user input.
*   **`sentinel-mcp/`**: A specialized MCP server.
    *   Serves faction data, relationships, and dynamic world updates as tools to the Agent.
    *   Maintains the simulation of the "living world" outside player view.
*   **`core/` & `lore/`**: Static data and narrative constraints.

## Architectural Focus Areas

When analyzing or modifying this codebase, prioritize:

1.  **State Management Integrity**:
    *   The `state/` module ensures game continuity. Changes here must include migrations or backward compatibility.
    *   Verify that `schema.py` accurately reflects the rules definitions in `core/`.
2.  **Separation of Concerns**:
    *   **Narrative vs. Simulation**: The Agent handles narrative flow; the MCP server handles faction simulation. Keep these logic streams distinct.
    *   **Display vs. Logic**: All visual formatting should remain in `interface/`. Logic should return structured data.
3.  **Tool Abstraction**:
    *   The agent interacts with the world via Tools (Dice, Hinge Detector, MCP Factions). Ensure tool interfaces remain standardized in `sentinel-agent/src/tools`.

## Development Guidelines

### Design Patterns
*   **Type Safety**: Use Pydantic models for all data exchange interfaces.
*   **Asynchronous I/O**: The system relies on `asyncio` for fluid LLM streaming and MCP communication.
*   **Modular Prompts**: Prompts in `sentinel-agent/prompts/` are hot-reloadable. Prefer editing these over hardcoding strings in Python.

### Best Practices
1.  **Context Efficiency**: When retrieving lore, prefer smart chunking (`lore/chunker.py`) over dumping raw text files into the context window.
2.  **Error Handling**: The CLI must remain stable. Wrap LLM calls and Tool executions in robust error handlers that provide narrative fallback (e.g., "The signal is static...").
3.  **Testing**: Verify changes using the `tests/` directory.

## Game Philosophy (Architectural Implications)

*   **"Consequences Bloom"**: Architecture must support delayed effects (Dormant Threads). Ensure the State Manager can serialize and deserialize pending events.
*   **"Social Energy"**: This is a constrained resource. Code that triggers interactions must correctly debit this value in the state.
*   **"Relationships as Resources"**: NPC disposition is a structured data point, not just narrative flavor. Treat it as a variable affecting logic flow.

## Gemini-Specific Tips

*   **Big Picture**: Use your large context window to ingest `architecture/AGENT_ARCHITECTURE.md` and `core/SENTINEL Playbook — Core Rules.md` simultaneously to ensure code changes align with game design.
*   **Pattern Matching**: Look for discrepancies between `sentinel-mcp` tool definitions and `sentinel-agent` tool usage—this is a common drift point.
*   **Refactoring**: Identify opportunities to move hardcoded logic from `agent.py` into data-driven structures in `sentinel-mcp`.
