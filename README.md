# SENTINEL

[![CI](https://github.com/KvFxKaido/SENTINEL/actions/workflows/ci.yml/badge.svg)](https://github.com/KvFxKaido/SENTINEL/actions/workflows/ci.yml)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC_BY--NC_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Sponsor](https://img.shields.io/badge/Sponsor-♡-pink)](https://github.com/sponsors/KvFxKaido)

A tactical, relationship-driven tabletop RPG with an AI Game Master. Navigate political tension, ethical tradeoffs, and survival in a post-collapse world where 11 factions compete for influence.

**Core loop:** Investigation → Interpretation → Choice → Consequence

## Quick Start

```
cd sentinel-agent
pip install -e .
python -m src.interface.cli
```

Then: `/new` → `/char` → `/start` → play

## Project Structure

```
SENTINEL/
├── sentinel-agent/     # AI Game Master
├── sentinel-campaign/  # Faction MCP Server
├── core/               # Game rules document
├── lore/               # Novellas and world-building
└── architecture/       # Design documents
```

| Component | Description |

|-----------|-------------|

| [sentinel-agent](sentinel-agent/) | Python CLI that runs the AI GM |

| [sentinel-campaign](sentinel-campaign/) | MCP server providing faction knowledge |

| [Core Rules](core/) | Complete game rules |

| [Lore](lore/) | Canon novellas for RAG retrieval |

## The Eleven Factions

| Faction | Philosophy |

|---------|------------|

| **Nexus** | The network that watches |

| **Ember Colonies** | We survived. We endure. |

| **Lattice** | We keep the lights on |

| **Convergence** | Become what you were meant to be |

| **Covenant** | We hold the line |

| **Wanderers** | The road remembers |

| **Cultivators** | From the soil, we rise |

| **Steel Syndicate** | Everything has a price |

| **Witnesses** | We remember so you don't have to lie |

| **Architects** | We built this world |

| **Ghost Networks** | We were never here |

## Character Backgrounds

Players choose one professional background. Backgrounds express capability, not destiny.

* **Intel Operative** — Systems analysis, surveillance, pattern recognition
* **Medic / Field Surgeon** — Triage, biology, crisis care
* **Engineer / Technician** — Repair, infrastructure, hacking
* **Negotiator / Diplomat** — Persuasion, mediation, languages
* **Scavenger / Salvager** — Resource location, improvisation, barter
* **Combat Specialist** — Tactics, firearms, physical conditioning

## Key Features

### AI Game Master

* Multiple LLM backends (LM Studio, Ollama, Claude, OpenRouter, Gemini, Codex)
* Hot-reloadable prompts
* Lore retrieval from novellas
* `/consult` — get competing perspectives from faction advisors
* `/simulate` — AI vs AI testing with 4 player personas

### NPC System

* Agendas: wants, fears, leverage, owes, lie_to_self
* Memory triggers react to player actions
* Disposition modifiers change behavior

### Consequence Engine

* Hinge moments (irreversible choices)
* Dormant threads (delayed consequences)
* Leverage escalation (factions call in favors)
* Faction standing affects NPC behavior

### Choice System

* GM always offers 2-4 options plus improvisation
* High-stakes moments use formal choice blocks
* Choices extracted and tracked for AI simulation

### Social Energy

* Tracks emotional bandwidth (0-100%)
* Personalized restorers and drains
* Affects social roll modifiers

## LLM Backends

| Backend | Setup |

|---------|-------|

| **LM Studio** | Download app, load model, start server (port 1234) |

| **Ollama** | `ollama pull llama3.2` — runs automatically (port 11434) |

| **Claude** | `pip install -e ".[claude]"` + API key |

| **OpenRouter** | Set `OPENROUTER_API_KEY` |

| **Gemini CLI** | Install `gemini` command |

| **Codex CLI** | Install `codex` command |

The agent auto-detects available backends (prefers local: LM Studio > Ollama).

## Recommended Setup

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Context window** | 8K tokens | 16K+ tokens |
| **VRAM (local)** | 8GB | 16GB+ |
| **Tool calling** | Optional | Required for full experience |

### Tested Models

| Model | Size | Notes |
|-------|------|-------|
| **Qwen 2.5** | 32B | Excellent tool calling, good roleplay |
| **Mistral Large** | 123B | Strong narrative, needs beefy GPU |
| **Llama 3.1** | 70B | Solid all-around |
| **Claude Sonnet** | API | Best quality, requires API key |

CLI-only backends (Gemini, Codex) work but skip tool calling — dice rolls, faction tracking, and hinge detection happen manually.

## Development

```
cd sentinel-agent
pip install -e ".[dev]"
pytest
```

**197 tests** covering state, mechanics, simulation, and event queue.

## Design Philosophy

> "The agent is a storyteller who knows the rules, not a rules engine that tells stories."

* NPCs are people, not obstacles
* Consequences bloom over time
* Honor player choices — no "right answers"
* Every faction is right about something

## Documentation

| Document | Purpose |

|----------|---------|

| [Project Brief](SENTINEL_PROJECT_BRIEF.md) | Full project overview |

| [Agent Architecture](architecture/AGENT_ARCHITECTURE.md) | Technical design |

| [Campaign MCP Server](sentinel-campaign/README.md) | Faction server design |

| [Agent Dev Guide](sentinel-agent/CLAUDE.md) | Contributor guide |

## License

CC BY-NC 4.0
