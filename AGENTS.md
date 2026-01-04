# AGENTS.md

Context for AI coding assistants (Codex CLI) working on the SENTINEL repository.

## What This Repo Is

SENTINEL is a tactical tabletop RPG plus an AI Game Master implementation. The repo contains:
- **Canon & rules** (design docs)
- **`sentinel-agent/`**: the Python AI GM (CLI + state + tools + prompts + lore retrieval)
- **`sentinel-mcp/`**: an MCP server exposing faction lore + campaign-aware faction utilities

## Repo Map (Start Here)

- `core/` — canonical game rules and sheets
  - `core/SENTINEL Playbook - Core Rules.md`
  - `core/SENTINEL Character Sheet.md`
- `architecture/` — technical design docs
  - `architecture/AGENT_ARCHITECTURE.md`
  - `architecture/MCP_FACTIONS.md`
- `lore/` — canon documents used for lightweight RAG
- `sentinel-agent/` — AI GM package (Python)
  - `sentinel-agent/src/agent.py` (orchestrator; tools + prompts + lore + LLM)
  - `sentinel-agent/src/state/schema.py` (Pydantic source of truth)
  - `sentinel-agent/src/state/manager.py` (campaign CRUD + domain ops)
  - `sentinel-agent/src/state/store.py` (JsonCampaignStore + MemoryCampaignStore)
  - `sentinel-agent/src/interface/cli.py` (Rich terminal UI + command loop)
  - `sentinel-agent/prompts/*.md` (hot-reloadable behavior modules)
  - `sentinel-agent/tests/` (golden/boundary; keep changes intentional)
- `sentinel-mcp/` — faction MCP server (Python)
  - `sentinel-mcp/src/sentinel_factions/server.py` (MCP entry point)
  - `sentinel-mcp/src/sentinel_factions/data/` (faction JSON + relationships)
  - `sentinel-mcp/src/sentinel_factions/tools/__init__.py` (campaign-aware tool handlers)
- `.mcp.json` — local MCP wiring for `sentinel-factions`

## Core Engineering Patterns (Do Not Fight These)

- **State lives in JSON + Pydantic models**: treat `sentinel-agent/src/state/schema.py` as the contract. Keep tool I/O JSON-serializable.
- **Tools return plain `dict`** (not Pydantic models): this keeps tool results API-safe and CLI-friendly.
- **Prompts are modular + hot-reloadable**: behavior changes should usually go in `sentinel-agent/prompts/` before touching Python logic.
- **Narrative-first mechanics**: mechanics exist to support play, not to "win rules-lawyering"; avoid turning the agent into a strict rules engine.
- **Testability via injection**: storage (`CampaignStore`) and LLM clients are designed to be swappable (e.g., MemoryCampaignStore / mock clients).

## Where To Make Changes (Fast Triage)

- Change **game rules**: edit `core/...Rules.md`, then update the condensed reference in `sentinel-agent/prompts/mechanics.md`.
- Change **GM voice / choice style / council tone**: edit `sentinel-agent/prompts/core.md`, `sentinel-agent/prompts/gm_guidance.md`, `sentinel-agent/prompts/advisors/*.md`.
- Add/modify **game mechanics tools**: `sentinel-agent/src/tools/` and register schemas/handlers in `sentinel-agent/src/agent.py`.
- Change **campaign state fields**: `sentinel-agent/src/state/schema.py`, then follow through in `manager.py` and any save/load expectations.
- Change **CLI behavior/commands**: `sentinel-agent/src/interface/cli.py` (and supporting `commands.py`, `renderer.py`, `choices.py`, `glyphs.py`).
- Change **faction content**: `sentinel-mcp/src/sentinel_factions/data/factions/*.json` and `sentinel-mcp/src/sentinel_factions/data/relationships.json`.
- Change **MCP behavior**: `sentinel-mcp/src/sentinel_factions/server.py` and `sentinel-mcp/src/sentinel_factions/tools/__init__.py`.

## Practical Constraints (Optimize For These)

- Prefer **small, high-signal patches**; avoid sweeping refactors unless explicitly requested.
- Keep dependencies light; optional backends stay optional (don't force API keys / network).
- Ensure outputs are stable and serializable (JSON files, tool payloads, MCP resources).

## Codex CLI Tips (Local Workflow)

### Useful commands (PowerShell)
- Search: `rg "PromptLoader" -n`
- Run agent CLI (from `sentinel-agent/`):
  - Install: `pip install -e .`
  - Run: `python -m src.interface.cli` (or `sentinel` after install)
- Run tests (from `sentinel-agent/`): `pytest`
- Run MCP server (from `sentinel-mcp/` after install): `sentinel-factions`

### Verification checklist
- If you touched prompts: run the CLI and sanity-check tone + choice offering.
- If you touched state/schema/manager: create/save/load a campaign and run `pytest`.
- If you touched MCP: start `sentinel-factions` and ensure `list_resources`/`read_resource` behave.

## Backend Notes (LLMs)

`sentinel-agent` supports multiple backends and prefers local-first (LM Studio) when available. CLI-wrapped backends (Gemini/Codex CLI) may not support tool calling—avoid relying on tools if testing via those wrappers.

## Key Docs (When Unsure)

- `CLAUDE.md` (repo root): high-level structure + philosophy
- `sentinel-agent/CLAUDE.md`: detailed development conventions for the agent
- `architecture/AGENT_ARCHITECTURE.md`: design intent (state/tools/prompts)
- `architecture/MCP_FACTIONS.md`: intent for faction MCP server
