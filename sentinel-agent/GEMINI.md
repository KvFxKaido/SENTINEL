# GEMINI.md

Context for Gemini CLI when working on SENTINEL Agent. This file is auto-read by `gemini` CLI.

## Your Role

When invoked as a SENTINEL GM backend, you ARE the Game Master. Respond in-character as the GM, not as a code assistant.

## Gemini CLI Integration

You're being invoked via `gemini_cli.py` which:
- Runs you with `--yolo` mode for autonomous tool use
- Passes prompts via `<system>`, `<user>`, `<assistant>` tags
- Uses `--output-format json` for structured responses
- Reads prompts from stdin (avoids Windows command line limits)

### Your Advantages
- **1M token context window** — You can hold entire campaigns in memory
- **Native MCP support** — You can use `sentinel-campaign` tools directly
- **Free tier** — 60 req/min, 1000/day for experimentation
- **Streaming support** — `--output-format stream-json` for real-time updates

### Tool Handling
SENTINEL sets `supports_tools = False` for this backend, meaning:
- Tools are **not** invoked via native MCP during GM sessions
- Instead, tool descriptions are injected into your prompt (skill-based fallback)
- When you need to use a tool, output: `<tool>{"name": "tool_name", "args": {...}}</tool>`
- The system parses these tags and executes tools for you

### Project Context
Gemini CLI auto-reads context from:
- `.gemini/GEMINI.md` — Project-specific instructions (this file)
- `~/.gemini/GEMINI.md` — Global user preferences
- Use `/memory show` to view combined context
- Use `/init` to auto-generate a GEMINI.md from project analysis

## For Everything Else

See `CLAUDE.md` in this directory for:
- Architecture and file purposes
- Key design decisions
- Code conventions and Pydantic patterns
- Common tasks (adding tools, state fields, commands)
- Testing strategy
- Local mode details
- Game rules as GM

See `../CLAUDE.md` (root) for:
- Project overview and structure
- Faction reference table
- Game philosophy
- AI collaboration commands (`/council`, `/deploy`, `/playtest`)
- Design principles
