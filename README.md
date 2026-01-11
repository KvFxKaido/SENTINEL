<p align="center">
  <img src="assets/banner.png" alt="SENTINEL Tactical TTRPG" width="600">
</p>

# SENTINEL

[![CI](https://github.com/KvFxKaido/SENTINEL/actions/workflows/ci.yml/badge.svg)](https://github.com/KvFxKaido/SENTINEL/actions/workflows/ci.yml)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC_BY--NC_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Sponsor](https://img.shields.io/badge/Sponsor-♡-pink)](https://github.com/sponsors/KvFxKaido)

A tactical, relationship-driven tabletop RPG with an AI Game Master. Navigate political tension, ethical tradeoffs, and survival in a post-collapse world where 11 factions compete for influence.

**Core loop:** Investigation → Interpretation → Choice → Consequence

## Quick Start

```bash
cd sentinel-agent
pip install -e .
sentinel                       # Textual TUI (recommended)
sentinel-cli                   # Dev CLI with simulation
```

**For 8B-12B models:** Add `--local` for optimized context budgets.

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

## Geography

Post-collapse North America, fractured along infrastructure lines.

| Region | Primary Faction | Contested By |
|--------|-----------------|--------------|
| Rust Corridor | Lattice | Steel Syndicate |
| Appalachian Hollows | Ember Colonies | Cultivators |
| Gulf Passage | Wanderers | Ghost Networks |
| Breadbasket | Cultivators | Wanderers |
| Northern Reaches | Covenant | Ember Colonies |
| Pacific Corridor | Convergence | Architects |
| Desert Sprawl | Ghost Networks | Steel Syndicate |
| Northeast Scar | Architects | Nexus |
| Sovereign South | Witnesses | Covenant |
| Texas Spine | Steel Syndicate | Lattice |
| Frozen Edge | Ember Colonies | — |

Nexus holds no territory — they hold information. Their presence is everywhere infrastructure exists.

## Character Backgrounds

Players choose one professional background. Backgrounds express capability, not destiny.

* **Intel Operative** — Systems analysis, surveillance, pattern recognition
* **Medic / Field Surgeon** — Triage, biology, crisis care
* **Engineer / Technician** — Repair, infrastructure, hacking
* **Negotiator / Diplomat** — Persuasion, mediation, languages
* **Scavenger / Salvager** — Resource location, improvisation, barter
* **Combat Specialist** — Tactics, firearms, physical conditioning

## Faction Affiliation

Players choose starting relationships, not membership. You're not "in" a faction — you have standing with them.

* **Aligned** — Start Friendly with one faction, Unfriendly with its opposite
* **Neutral** — Start Neutral with all factions; harder early, flexible long-term

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

### Campaign Memory ([Memvid](https://github.com/memvid/memvid))

* Semantic search over campaign history
* `/timeline` command finds relevant past events
* Auto-captures hinges, faction shifts, NPC interactions
* Optional dependency — works without it

### Lore Integration

* 44 curated faction quotes injected into GM context
* `/lore quotes` command to browse mottos and world truths
* Unified retrieval combines static lore + campaign history

## LLM Backends

SENTINEL supports both local and cloud backends.

| Backend | Setup |
|---------|-------|
| **LM Studio** | Download app, load model, start server (port 1234) |
| **Ollama** | `ollama pull llama3.2` — runs automatically (port 11434) |
| **Claude Code** | Install [Claude Code](https://claude.ai/code), authenticate, done |

The agent auto-detects available backends (LM Studio → Ollama → Claude Code).

### Which Backend Should I Use?

| Priority | Recommendation |
|----------|----------------|
| Best narrative quality | Claude (via Claude Code) |
| Free + private | LM Studio or Ollama with 14B+ model |
| Budget hardware | 8B model with `--local` flag |
| Offline play | Local only |
| Potato PC | Claude (offload compute to cloud) |

Local models are fully playable — the mechanics work identically. Claude shines in nuanced NPC interactions, faction politics, and long-term consequence tracking.

### Local Mode for Small Models

8B-12B models are now playable with the `--local` flag:

```bash
sentinel --local        # TUI
sentinel-cli --local    # CLI
```

Local mode reduces context from ~13K to ~5K tokens by:
- Using condensed prompts (70% smaller)
- Skipping narrative flavor, digest, and retrieval sections
- Exposing only phase-relevant tools (3-12 instead of 19)

This keeps smaller models focused and responsive. You lose some GM flavor text, but core mechanics and narrative quality remain intact.

### How Claude Code Works

We invoke the `claude` CLI in print mode (`claude -p -`), which is a documented, intended use of the tool. No OAuth tokens are extracted, no credentials are stolen, no terms of service are violated. If you're logged into Claude Code, it just works.

This is explicitly *not* an exploit. We're using the CLI the way it was designed to be used.

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

Both modes are intentionally supported. Models without tool calling work fine for pure storytelling.

### Tested Models

| Model | VRAM | Best For | Notes | Failure Mode |
|-------|------|----------|-------|--------------|
| **Gemma 3** | ~12GB (27B) | Long-form continuity, dialogue-heavy sessions | Stable tone, good narrative endurance | Plays it safe under pressure |
| **GPT-OSS** | ~10GB (20B) | Auditability, constraint experiments | Apache 2.0, predictable behavior | Flat prose, mechanical pacing |
| **Qwen 3** | ~8GB (14B) | System-heavy play | Excellent tool calling | Scaffolding becomes the game |
| **Llama 3.2** | ~5GB (8B) | Low-end rigs | Use `--local` flag; lightweight, good fallback | Forgets state without local mode |
| **Ministral 3** | ~8GB (14B) | Deterministic GM logic, trigger-heavy systems | Strong instruction following | Over-follows rules, rigid |

### The Governability Curve

Compliance with GM constraints doesn't scale linearly with model size.

| Size | Nickname | Behavior | Risk |
|------|----------|----------|------|
| <7B | Goldfish | Eager but forgets constraints as context grows | Drift |
| 8B–14B | Soldier | Follows literal instructions without "improving" them | **Ideal** |
| 20B–70B | Midwit | Detects conflict between constraints and training, invents workarounds | Disobedience |
| >70B | Academic | Can respect constraints but often requires heavy framing | Overhead |

For GM work, **obedience > reasoning**. A model that cannot stop talking cannot listen.

**8B sweet spot:** The "Soldier" tier (8B-14B) is ideal for SENTINEL because these models follow instructions precisely without trying to be clever. With `--local` mode keeping context tight, they stay focused and produce quality narrative output.

## Development

```
cd sentinel-agent
pip install -e ".[dev]"
pytest
```

**250+ tests** covering state, mechanics, simulation, local mode, and event queue.

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
