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

### Commands at a Glance

| Command | What it does |
|---------|--------------|
| `/consult <question>` | Get competing perspectives from faction advisors |
| `/factions` | View standings, relationships, cascade effects |
| `/npc [name]` | View NPC info and personal history |
| `/arc` | Manage emergent character arcs |
| `/consequences` | View pending threads and avoided situations |
| `/timeline <query>` | Search campaign memory (requires memvid) |
| `/simulate preview <action>` | Preview consequences without committing |
| `/lore quotes` | Browse faction mottos and world truths |
| `/debrief` | End session with reflection prompts |

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

* Local LLM backends (LM Studio, Ollama)
* Hot-reloadable prompts with phase-specific guidance
* Lore retrieval from novellas + campaign memory search
* `/consult` — get competing perspectives from faction advisors
* `/simulate` — preview consequences, predict NPC reactions, explore what-ifs

### NPC System

* Agendas: wants, fears, leverage, owes, lie_to_self
* Individual memory separate from faction standing
* Memory triggers react to player actions
* Disposition modifiers change behavior per level
* `/npc` command to view relationships and history

### Faction Dynamics

* 11 factions with inter-faction relationships
* Cascading effects when you help or oppose factions
* `/factions` command shows standings and relationship webs
* Faction narrative corruption (GM language shifts with standing)

### Consequence Engine

* Hinge moments (irreversible choices)
* Dormant threads (delayed consequences)
* Leverage escalation (factions call in favors with deadlines)
* `/consequences` command to view pending threads
* Avoidance tracking (not acting is also a choice)

### Character Development

* 8 emergent arc types detected from play patterns
* `/arc` command to view, accept, or reject suggested arcs
* Accepted arcs inform GM behavior and NPC recognition
* Social energy with personalized restorers/drains

### Campaign Memory (Memvid)

* Semantic search over campaign history
* `/timeline` command finds relevant past events
* Auto-captures hinges, faction shifts, NPC interactions
* Optional dependency — works without it

### Lore Integration

* 44 curated faction quotes injected into GM context
* `/lore quotes` command to browse mottos and world truths
* Unified retrieval combines static lore + campaign history

## LLM Backends

SENTINEL requires a local LLM backend.

| Backend | Setup |

|---------|-------|

| **LM Studio** | Download app, load model, start server (port 1234) |

| **Ollama** | `ollama pull llama3.2` — runs automatically (port 11434) |

The agent auto-detects available backends (LM Studio → Ollama).

### Why Local Only?

Cloud models are not officially supported.

SENTINEL's mechanics rely on predictable context limits, rolling windows, and controlled degradation. These cannot be guaranteed with hosted models.

That said, players who supply the rules, tone, and constraints to a cloud model may achieve a similar experience. Expect variance.

## Recommended Setup

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Context window** | 8K tokens | 16K+ tokens |
| **VRAM (local)** | 8GB | 16GB+ |
| **Tool calling** | See below | See below |

**Context window:** 8K is playable but limited memory and shorter scenes. 16K+ provides stable NPC memory, faction nuance, and longer missions.

**VRAM:** 8GB is functional but expect smaller models and tighter budgets. 16GB+ gives smooth pacing, better NPC consistency, and fewer compromises.

**Note:** SENTINEL prioritizes continuity and consequence over verbosity. Larger models and longer context windows improve memory, not just prose quality.

### Tool Calling Modes

| Mode | Experience |
|------|------------|
| **Without** | Narrative-only (manual rolls, tracking, consequences) |
| **With** | Full system integrity (dice, factions, hinges, simulation) |

Both modes are intentionally supported. CLI-only models work fine for pure storytelling.

### Tested Models

| Model | VRAM | Best For | Notes |
|-------|------|----------|-------|
| **Gemma 3** | ~12GB (27B) | Long-form play | Balanced, stable |
| **GPT-OSS** | ~10GB (20B) | Open-source purists | Apache 2.0 |
| **Qwen 3** | ~8GB (14B) | System-heavy play | Excellent tool calling |
| **Llama 3.2** | ~5GB (8B) | Low-end rigs | Lightweight, weaker memory |
| **Ministral 3** | ~8GB (14B) | Rules adherence | Strong instruction following |

## Development

```
cd sentinel-agent
pip install -e ".[dev]"
pytest
```

**197+ tests** covering state, mechanics, simulation, and event queue.

## Design Philosophy

> "The agent is a storyteller who knows the rules, not a rules engine that tells stories."

* NPCs are people, not obstacles
* Consequences bloom over time
* Honor player choices — no "right answers"
* Every faction is right about something
* Refusal is a meaningful choice
* Avoidance is content — the world doesn't wait
* Emergent identity — arcs recognize patterns, not prescribe paths
* Lore as texture — quotes are seasoning, not scripts

## Documentation

| Document | Purpose |
|----------|---------|
| [Project Brief](SENTINEL_PROJECT_BRIEF.md) | Full project overview |
| [Agent Architecture](architecture/AGENT_ARCHITECTURE.md) | Technical design |
| [Campaign MCP Server](sentinel-campaign/README.md) | Faction server design |
| [Agent Dev Guide](sentinel-agent/CLAUDE.md) | Contributor guide |

## License

CC BY-NC 4.0
