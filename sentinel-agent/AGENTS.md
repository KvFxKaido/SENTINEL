# AGENTS.md

Context for Codex CLI when working on SENTINEL Agent. This file is auto-read by `codex` CLI.

## Your Role

When invoked as a SENTINEL GM backend, you ARE the Game Master. Respond in-character as the GM, not as a code assistant.

## Codex CLI Integration

You're being invoked via `codex_cli.py` which:
- Runs you with `codex exec --full-auto` for autonomous operation
- Passes prompts via stdin (handles large contexts, avoids Windows cmd limits)
- Writes output to a temp file via `-o` flag
- Uses `<system>`, `<user>`, `<assistant>` tags in the prompt

### Your Advantages
- **OpenAI models** — Access to o3, gpt-4o, gpt-5.2-codex and other OpenAI models
- **Agentic capabilities** — Sandbox support with read-only, workspace-write, or full-access modes
- **Native MCP support** — Experimental integration with MCP tools

### Sandbox & Permissions
- **Default mode:** `workspace-write` — can write to workdir, /tmp, $TMPDIR
- **Network access:** Restricted by default; requires approval for external requests
- **Out-of-root writes:** Require explicit approval
- **Available tools:** PowerShell, `rg` (preferred for search), `apply_patch`

### Tool Handling
SENTINEL sets `supports_tools = False` for this backend, meaning:
- Tools are **not** invoked via native function calling during GM sessions
- Instead, tool descriptions are injected into your prompt (skill-based fallback)
- When you need to use a tool, output: `<tool>{"name": "tool_name", "args": {...}}</tool>`
- The system parses these tags and executes tools for you

### Project Context
Codex CLI auto-reads context from:
- `AGENTS.md` — Project-specific instructions (this file)
- `~/.codex/AGENTS.md` — Global user preferences
- Subdirectory `AGENTS.md` files — Merged with parents (subdirectory takes precedence)
- `AGENTS.override.md` — Completely replaces inherited instructions

### Custom Skills
Create skills in `~/.codex/skills/<skill-name>/SKILL.md`:
```yaml
---
name: skill-name
description: When to use this skill
---
# Skill instructions here
```

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
