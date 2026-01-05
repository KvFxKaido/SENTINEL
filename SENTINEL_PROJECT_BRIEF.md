# SENTINEL Project Brief

*Last updated: January 2026*

## What This Is

SENTINEL is a **tactical tabletop RPG** with an **AI Game Master**. The game explores political tension, ethical tradeoffs, and survival in a post-collapse world where 11 factions compete for influence.

**Core loop:** Investigation → Interpretation → Choice → Consequence

**Not about:** min-max optimization, combat dominance, binary morality

**About:** navigating competing truths, sustaining integrity under pressure, relationships as resources

---

## Current Status

### Working
- CLI interface with Rich terminal UI + themed visuals
- Animated hexagon banner with glitch reveal
- Command autocomplete with descriptions
- Campaign creation, save/load (JSON persistence)
- Character creation with 7 backgrounds, personalized energy system
- 11 factions with reputation tracking
- Social energy system with **personalized restorers/drains**
- Dice mechanics (d20 + modifiers, advantage/disadvantage)
- Mission framework with 5 phases
- **Multiple-choice system** — GM always offers 2-4 options + improvisation
- **Lore retrieval (RAG)** — GM draws from canon bible + novellas
- **Council system** — consult faction advisors for competing perspectives
- **Hinge detection** — auto-detects irreversible choices in player input
- **NPC disposition modifiers** — behavior changes based on disposition level
- **NPC memory triggers** — NPCs react to tagged events (e.g., faction shifts)
- **Context meter** — visual indicator of conversation depth
- **Faction MCP server** — external faction lore + campaign tracking
- **Multi-backend LLM** — LM Studio, Ollama, Claude, OpenRouter, Gemini CLI, Codex CLI
- **Test suite** — 115 tests covering core mechanics
- **CI/CD** — GitHub Actions (Python 3.10, 3.11, 3.12)
- **Dormant thread surfacing** — keyword matching alerts GM when threads may trigger
- **Enhancement leverage** — factions call in favors with weight escalation (light/medium/heavy)
- **Phase-based GM guidance** — different prompts per mission phase (briefing, planning, execution, resolution, debrief, between)
- **Refusal reputation** — refused enhancements build titles (The Unbought, The Undaunted) that NPCs react to

### Not Yet Built
- Multi-character party support
- Web/mobile interface

---

## Architecture

```
SENTINEL/
├── lore/                         # Novellas + reference docs for RAG
│   ├── First Deployment.md
│   ├── Ghost Protocol.md
│   ├── RESET Mission Module.md   # Example mission template
│   ├── Cipher - Sample Character.md
│   └── ... (9 files total)
├── sentinel-agent/               # AI Game Master
│   ├── src/
│   │   ├── agent.py              # LLM orchestration + tool handlers + council
│   │   ├── state/
│   │   │   ├── schema.py         # Pydantic models (source of truth)
│   │   │   ├── manager.py        # Campaign CRUD
│   │   │   └── store.py          # Abstract storage interface
│   │   ├── rules/
│   │   │   └── npc.py            # Pure functions for NPC behavior
│   │   ├── llm/
│   │   │   ├── base.py           # Abstract LLM client
│   │   │   ├── lmstudio.py       # Local LLM (OpenAI-compatible)
│   │   │   ├── ollama.py         # Ollama (OpenAI-compatible)
│   │   │   ├── claude.py         # Anthropic API
│   │   │   ├── openrouter.py     # OpenRouter API
│   │   │   └── cli_wrapper.py    # Gemini/Codex CLI wrappers
│   │   ├── lore/
│   │   │   ├── chunker.py        # Parse novellas → tagged chunks
│   │   │   └── retriever.py      # Keyword matching retrieval
│   │   ├── tools/
│   │   │   ├── dice.py           # Roll mechanics
│   │   │   └── hinge_detector.py # Detect irreversible choices
│   │   └── interface/
│   │       ├── cli.py            # Terminal UI with theming
│   │       ├── glyphs.py         # Unicode/ASCII visual indicators
│   │       └── choices.py        # Choice parsing
│   ├── prompts/                  # Hot-reloadable GM instructions
│   │   ├── core.md               # Identity and principles
│   │   ├── mechanics.md          # Rules reference
│   │   ├── gm_guidance.md        # Narrative style + choice generation
│   │   └── advisors/             # Council faction perspectives
│   └── campaigns/                # JSON save files
└── sentinel-mcp/                 # Faction MCP Server
    └── src/sentinel_factions/
        ├── server.py             # MCP entry point
        ├── resources/            # Lore, NPCs, operations
        ├── tools/                # Standing, interactions, intel
        └── data/factions/        # 11 faction JSON files
```

**Key decisions:**
- Prompts are modular and hot-reload (edit without restart)
- State is JSON files, not SQLite (MVP simplicity — council agreed)
- Lore retrieval uses lightweight keyword matching (no heavy deps)
- Tools return dicts for API serialization
- NPCs have agendas (wants, fears, leverage, owes, **lie_to_self**)
- NPC behavior logic extracted to pure functions (`rules/npc.py`) for testability

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `/new` | Create a new campaign |
| `/char` | Create character (with restorers/drains, establishing incident) |
| `/start` | Begin campaign — GM sets establishing scene |
| `/mission` | Get a new mission from the GM |
| `/consult <q>` | Ask faction advisors for competing perspectives |
| `/debrief` | End session with reflection prompts |
| `/model` | List/switch LM Studio models |
| `/lore` | Show lore status, test retrieval |
| `/roll <skill> <dc>` | Roll a skill check |
| `/save` | Save current campaign |
| `/load` | Load an existing campaign |
| `/status` | Show current status |

**Quick Start:**
```
/new → /char → /start → [play] → /debrief
```

---

## Council System

When facing difficult decisions, consult faction advisors for competing perspectives:

```
/consult Should I accept the Syndicate's offer?

◈ COUNCIL CONVENES ◈

╭─────────── NEXUS ANALYST ───────────╮
│ The probability matrix favors       │
│ acceptance. Resources gained        │
│ outweigh projected obligation       │
│ costs by 2.3x. Recommend proceeding.│
╰─────────────────────────────────────╯

╭─────────── EMBER CONTACT ───────────╮
│ They never give without taking.     │
│ Ask yourself what they'll want      │
│ when you can't say no.              │
╰─────────────────────────────────────╯

╭────────── WITNESS ARCHIVIST ────────╮
│ Syndicate enhancement acceptance    │
│ historically correlates with 73%    │
│ faction dependency. Recording.      │
╰─────────────────────────────────────╯

The council has spoken. The choice remains yours.
```

Each advisor is the same LLM with a different system prompt representing their faction's worldview. Fits the "competing truths" philosophy — three valid perspectives, none "right."

---

## Game Mechanics

### Rolls
`d20 + 5` (if trained) vs DC 10/14/18/22

### Social Energy (0-100%)
Tracks emotional bandwidth. **Personalized per character**:

```yaml
social_energy:
  name: "Pistachios"
  current: 75
  restorers: ["solo work", "quiet environments", "honest conversations"]
  drains: ["extended meetings", "ideological debates", "coercive negotiation"]
```

States:
- 51-100: Centered (normal)
- 26-50: Frayed (disadvantage on social)
- 1-25: Overloaded (disadvantage on all interpersonal)
- 0: Shutdown (complex social auto-fails)

### Factions (11 total)
Nexus, Ember Colonies, Lattice, Convergence, Covenant, Wanderers, Cultivators, Steel Syndicate, Witnesses, Architects, Ghost Networks

Standing: Hostile → Unfriendly → Neutral → Friendly → Allied

### Hinge Moments
Irreversible choices that define character. Tracks **what shifted** as a result.

### Enhancements
Faction-granted powers with strings attached. 9 factions offer them; Wanderers and Cultivators don't (philosophical). **Refused enhancements are tracked** — refusal as meaningful choice.

### NPCs
Every NPC has an agenda:
```yaml
agenda:
  wants: "Protect her daughter's future"
  fears: "Being seen as a collaborator"
  leverage: "Knows about the bunker"
  owes: "You saved her crew"
  lie_to_self: "It's temporary. We'll give power back later."
```

The `lie_to_self` field makes antagonists human — they believe they're helping.

---

## Multiple-Choice System

The GM always ends responses with options:

**Routine moments:**
```
1. Approach the guard directly
2. Look for another way around
3. Wait and observe
4. Something else...
```

**High-stakes moments:** (formal block, red panel)
```
---CHOICE---
stakes: high
context: "Accept Syndicate enhancement"
options:
- "Accept—you need the edge"
- "Refuse—you won't be owned"
- "Negotiate terms first"
- "Something else..."
---END---
```

Player types 1-4 to select, or types freely to improvise.

---

## Lore Retrieval System

The GM draws from your novellas for narrative inspiration:

- **9 documents** chunked into tagged segments
- Auto-tagged with factions, characters, themes
- Retrieved based on current faction standings + player input
- Injected into GM context (up to 2 chunks per response)

Includes:
- 6 original novellas
- Cipher sample character sheet
- Cipher case file (example timeline)
- RESET mission module (template)

Test with: `/lore sentinel` or `/lore awakening`

---

## Faction MCP Server

External MCP server providing faction knowledge and campaign tracking:

### Resources
| URI | Returns |
|-----|---------|
| `faction://{id}/lore` | History, ideology, structure |
| `faction://{id}/npcs` | NPC archetypes with wants/fears/speech |
| `faction://{id}/operations` | Goals, methods, tensions |
| `faction://relationships` | Inter-faction dynamics |

### Tools
| Tool | Purpose |
|------|---------|
| `get_faction_standing` | Player's standing + history |
| `get_faction_interactions` | Past encounters this campaign |
| `log_faction_event` | Record faction-related event |
| `get_faction_intel` | What does faction know about topic? |
| `query_faction_npcs` | NPCs by faction in campaign |

### Intel Domains
Each faction knows different things:
- **Nexus:** Infrastructure, population, predictions
- **Ember Colonies:** Survival, safe routes, trust networks
- **Witnesses:** History, records, contradictions
- **Steel Syndicate:** Resources, leverage, smuggling
- **Ghost Networks:** Escape routes, identities, hiding

Example: `/consult "What does Nexus know about infrastructure?"` returns grid status, population flows, prediction models.

---

## Visual Theme

Based on design concept: *"If it looks calm, it's lying."*

| Color | Meaning |
|-------|---------|
| Cold twilight blue | Loneliness, distance, the void |
| Pale surgical white | Sterility, control, clinical precision |
| Muted radioactive yellow | Danger without melodrama |
| Rusted red | Memory of violence, high-stakes decisions |

Applied throughout CLI: banners, panels, status displays, choice blocks.

---

## Tech Stack

- **Python 3.10+**
- **Pydantic** — State validation
- **Rich** — Terminal UI with theming
- **prompt-toolkit** — Command autocomplete
- **LM Studio** — Local LLM (free, OpenAI-compatible API at port 1234)
- **Ollama** — Local LLM alternative (OpenAI-compatible API at port 11434)
- **Anthropic SDK** — Claude API (optional)
- **pytest** — Test framework with 115 tests
- **GitHub Actions** — CI/CD pipeline

No heavy ML dependencies — lore retrieval uses keyword matching.

---

## Open Questions / Areas for Feedback

1. **Multiplayer** — How would multiple players work? Turn-based? Simultaneous input?

2. **Web interface** — Worth building, or is CLI sufficient for the audience?

3. **Phase-based prompts** — Should the GM get different guidance during briefing vs execution vs debrief?

---

## Design Philosophy

> "The agent is a storyteller who knows the rules, not a rules engine that tells stories."

- NPCs are people, not obstacles
- Consequences bloom over time (dormant threads)
- Honor player choices — no "right answers"
- Social energy depletion should feel humane, not punitive
- Every faction is right about something, dangerous when taken too far
- **Refusal is a meaningful choice** — what you don't accept matters
- **Competing truths** — the council shows multiple valid perspectives

---

## Sample Documents

| Document | Purpose |
|----------|---------|
| `lore/Cipher - Sample Character.md` | Complete character sheet example |
| `lore/Cipher Case File — Example Timeline.md` | Mission log + relationship map |
| `lore/RESET Mission Module.md` | Mission template with hinge structure |

---

## Links

- Game rules: `core/SENTINEL Playbook — Core Rules.md`
- Architecture doc: `architecture/AGENT_ARCHITECTURE.md`
- MCP design: `architecture/MCP_FACTIONS.md`
- Dev guide: `sentinel-agent/CLAUDE.md`
- MCP server: `sentinel-mcp/README.md`

---

## How to Help

When brainstorming, consider:
- Does this serve the narrative-first philosophy?
- Does this add complexity without depth?
- Would this feel good at the table (or terminal)?
- Is this solving a real problem or an imagined one?

I'm building this solo, so prioritization matters. What's the highest-impact next step?
