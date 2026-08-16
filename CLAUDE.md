# CLAUDE.md

Context for AI assistants working on the SENTINEL project.

## Project Structure

```
SENTINEL/
├── core/                    # Game design documents
│   └── SENTINEL Playbook — Core Rules.md
├── architecture/            # Design + decision docs (each carries a Status: line)
│   ├── sentinel_circuit_design.md    # The Circuit — sanctioned combat (Proposal)
│   ├── close_contact_design.md       # 1v1 fighting system spec (Proposal)
│   ├── flux_card_game_design.md      # Folk card game — collection + ante (Proposal)
│   ├── art_direction_gba_tactics.md  # Sprite + UI art direction (Reference)
│   ├── AGENT_ARCHITECTURE.md         # Agent design, state schema, tools
│   ├── VIDEO_GAME_REUSE_MAP.md       # What the video game reuses from this stack
│   ├── mocks/                        # HTML mocks (fighter sheet, sprite audition)
│   └── Archive/                      # Historical docs, kept for the paper trail
├── prototypes/              # Playable prototypes (see prototypes/README.md)
│   ├── tactical-core/       # Deterministic rules module — golden transcripts
│   ├── tactical/            # 2D canvas renderer
│   ├── tactical3d/          # 2.5D renderer (three.js, billboarded sprites)
│   └── close-contact/       # 1v1 fighting prototype (Godot 4.5, has own CLAUDE.md)
├── workers/
│   └── witness/             # Cloudflare Worker — certifies transcripts at the edge
├── sentinel-agent/          # The AI GM implementation
│   ├── CLAUDE.md            # Detailed dev context
│   ├── src/                 # Python source
│   │   ├── state/
│   │   │   ├── schema.py         # Pydantic models (source of truth)
│   │   │   ├── manager.py        # Campaign CRUD + delegation
│   │   │   └── event_bus.py      # Pub/sub for reactive TUI updates
│   │   ├── systems/              # Domain logic modules
│   │   │   ├── jobs.py           # Job board, templates, lifecycle
│   │   │   ├── favors.py         # NPC favor system
│   │   │   ├── endgame.py        # Readiness tracking, epilogue
│   │   │   ├── leverage.py       # Enhancement demands
│   │   │   └── arcs.py           # Character arc detection
│   │   └── interface/
│   │       ├── tui.py            # Primary Textual-based UI
│   │       ├── tui_commands.py   # TUI command handlers
│   │       └── commands.py       # CLI command handlers
│   ├── data/                # Game data files
│   │   ├── regions.json     # 11 regions with factions, adjacency
│   │   └── jobs/            # Job templates by faction
│   ├── prompts/             # Hot-reloadable prompts
│   │   └── local/           # Condensed prompts for 8B-12B models
│   └── campaigns/           # Save files
├── sentinel-campaign/       # Campaign MCP server
│   ├── src/sentinel_campaign/
│   │   ├── server.py        # MCP entry point
│   │   ├── resources/       # Lore, NPCs, operations
│   │   ├── tools/           # Standing, interactions, intel
│   │   └── data/factions/   # Faction JSON files
│   └── README.md
├── lore/                    # World-building documents (novellas)
└── wiki/                    # Reference encyclopedia (Obsidian vault)
```

## What This Is

SENTINEL is a tactical tabletop RPG about navigating political tension, ethical tradeoffs, and survival under fractured systems. The `sentinel-agent` subdirectory contains an AI Game Master that runs the game.

## Designer Context

Before diving into code, understand who you're working with:

| Resource | Location | Purpose |
|----------|----------|---------|
| Design philosophy | Condensed below | Non-negotiable design principles |
| Personal context | `.claude/personal.md` | Shawn's preferences, communication style (gitignored) |
| MCP resource | `gm://designer` | Query personal context programmatically |

### Design Philosophy (condensed)

Postmortem-driven rules, not aspirational guidelines — every one exists because something broke. Read before proposing architectural changes. (Full original: `git show a57f918^:architecture/design-philosophy.md`.)

1. **Shared state must be visible** — if you can't tell what changed, the system is hiding something
2. **Capability changes require consent** — expanding what the system can touch is an ethical event, not a UX detail
3. **Convenience never overrides clarity** — honest and awkward beats pleasant and misleading; no silent fallbacks
4. **Fewer features beat fractured coherence** — one clear way to do common things; justify complexity before building it
5. **If it feels impressive, it's probably hiding something** — boring is correct; explicit over implicit

Ship a feature only if its state is visible, its failure modes are legible, and users can tell what the system observed. Break these rules never by accident — "it's inconvenient" isn't a trade-off.

## Key Documents

| Document | Purpose |
|----------|---------|
| `core/SENTINEL Playbook — Core Rules.md` | The complete game rules |
| `architecture/sentinel_circuit_design.md` | The Circuit — combat as an institution (Proposal) |
| `architecture/close_contact_design.md` | Close Contact — the 1v1 fighting spec (Proposal) |
| `architecture/flux_card_game_design.md` | FLUX — the folk card game (Proposal) |
| `architecture/art_direction_gba_tactics.md` | Sprite + UI art direction (Reference) |
| `architecture/AGENT_ARCHITECTURE.md` | Agent design, state schema, tools |
| `prototypes/tactical-core/README.md` | Deterministic rules module + the golden-transcript discipline |
| `workers/witness/README.md` | Edge certification of match transcripts (live Worker) |
| `sentinel-agent/CLAUDE.md` | Dev guide for Claude assistants |
| `sentinel-campaign/README.md` | Campaign MCP server (factions, history, tools) |

### Decision-doc Status lifecycle

Every doc in `architecture/` carries a `Status:` line in its header (borrowed
from Push's decision docs). The states:

- **Proposal** — a design being argued; cite it in PRs as intent, not law.
- **Reference** — steers taste and future work; not binding as a whole, but may
  contain individually **decided** items, marked inline with their decision date.
- **Current (date)** — binding until superseded; changing it takes a PR that says so.
- **Historical — superseded by `<doc>`** — kept for the paper trail; do not build
  against it. Docs in `architecture/Archive/` are Historical by location.

If a doc has no Status line, add one before extending the doc.

## Game Philosophy

**Not about:** min-max optimization, combat dominance, binary morality

**About:** navigating competing truths, sustaining integrity under pressure, relationships as resources, choosing consequences you can live with

**Core loop:** Investigation → Interpretation → Choice → Consequence

## The Eleven Factions

| Faction | Tagline | Intel Domains |
|---------|---------|---------------|
| Nexus | The network that watches | Infrastructure, population, predictions |
| Ember Colonies | We survived. We endure. | Survival, safe routes, trust networks |
| Lattice | We keep the lights on | Infrastructure, supply chains, logistics |
| Convergence | Become what you were meant to be | Enhancement tech, integration research |
| Covenant | We hold the line | Oaths, sanctuary, ethics |
| Wanderers | The road remembers | Trade routes, news, safe passages |
| Cultivators | From the soil, we rise | Food production, seed stocks, land |
| Steel Syndicate | Everything has a price | Resources, leverage, smuggling |
| Witnesses | We remember so you don't have to lie | History, records, contradictions |
| Architects | We built this world | Pre-collapse records, credentials |
| Ghost Networks | We were never here | Escape routes, identities, hiding |

Full faction data available via MCP: `faction://{id}/lore`, `faction://{id}/npcs`, `faction://{id}/operations`

## Unique Mechanics

See `core/SENTINEL Playbook — Core Rules.md` for complete rules. Summary:

| Mechanic | Purpose |
|----------|---------|
| **Social Energy** | Emotional bandwidth; depletes on interaction, at zero complex social auto-fails |
| **Hinge Moments** | Irreversible choices with narrative gravity; always log and reference later |
| **Enhancements** | Faction-granted power; accepting creates leverage they can call in |
| **Dormant Threads** | Delayed consequences; queue with trigger, surface when conditions met |
| **NPC Disposition** | hostile→wary→neutral→warm→loyal; each level has tone/reveals/withholds |
| **Geography** | 11 regions with faction control; `/region` to travel |
| **Vehicles** | Transport that unlocks certain jobs; buy via `/shop` |
| **Favors** | Call in favors from allied NPCs; disposition-gated |
| **Job Board** | Faction-specific jobs by location/standing; `/jobs` to browse |
| **Endgame** | Player-initiated conclusion; readiness tracks hinges/arcs/threads/factions |
| **Memvid** | Optional semantic search over campaign history; `/timeline` |
| **Wiki** | Reference encyclopedia (Obsidian vault), read by lore retrieval and the campaign MCP server |

Character appearances and portraits are campaign-isolated: `assets/characters/campaigns/{id}/{name}.yaml`

## MCP Server: sentinel-campaign

Provides faction tools, wiki resources, and campaign state. See `sentinel-campaign/README.md` for full details.

**Resources:** `faction://{id}/lore`, `faction://{id}/npcs`, `faction://{id}/operations`, `wiki://{page}`

**Key tools:** `get_faction_standing`, `get_faction_intel`, `query_faction_npcs`, `search_wiki`, `log_wiki_event`

**Setup:** `cd sentinel-campaign && pip install -e .` — configured in `.mcp.json`

---

## Working on This Project

### To modify game rules
Edit `core/SENTINEL Playbook — Core Rules.md`. Then update `sentinel-agent/prompts/mechanics.md` with the condensed reference.

### To modify agent behavior
See `sentinel-agent/CLAUDE.md` for detailed guidance. Key files:
- `prompts/*.md` — GM personality and guidance (hot-reloadable)
- `src/agent.py` — Tool definitions and API orchestration
- `src/state/schema.py` — Data models

### To modify faction data
Edit JSON files in `sentinel-campaign/src/sentinel_campaign/data/factions/`.

### To modify regions or jobs
- **Regions:** Edit `sentinel-agent/data/regions.json` (faction control, adjacency, terrain)
- **Job templates:** Edit JSON files in `sentinel-agent/data/jobs/` (one file per faction)
- **Job requirements:** Add `region`, `requires_vehicle`, `requires_vehicle_type`, or `requires_vehicle_tags` to templates

### To modify vehicles or shop
Edit `SHOP_INVENTORY` and `VEHICLE_DATA` in `sentinel-agent/src/interface/tui_commands.py`.

### To modify favor system
Edit `sentinel-agent/src/systems/favors.py` for costs, disposition rules, or favor types.

### To run the agent
```bash
cd sentinel-agent
pip install -e .
sentinel                  # Textual TUI (recommended)
sentinel-cli              # Dev CLI with simulation
sentinel --local          # For 8B-12B models (reduced context)
```

## Execute the Claim

Borrowed from Push, paid for twice here: **before asserting something is
verified, run the exact thing that would fail if the assertion were false.**
Inspecting code, narrating arithmetic, or grepping for the convenient form of a
pattern is not verification — it is a claim wearing verification's clothes.

The failure classes this repo has already bought:

- **Narrated arithmetic.** "350×223 is exactly half of 445" shipped in a fix
  description. 445 is odd. Review bots caught it; the author didn't, because the
  claim was written down instead of computed. If the claim is a number, compute
  the number.
- **The convenient grep.** A removal sweep matched `_wiki_dir` and declared
  victory; a bare `wiki_dir=` kwarg survived and broke every TUI launch. The
  smoke test imported the module but never reached the failing call. Search for
  the form that would falsify you, and execute the code path — not the import.
- **The untested boundary.** `addRating` claimed consumers could sum its event
  deltas; at the clamp bounds it emitted the *requested* delta, not the
  *applied* one, so sums drifted. If the claim is "consumers can rely on X,"
  write the test at the edge of X, where X breaks.

The golden-transcript discipline (`prototypes/tactical-core/README.md`) is this
rule institutionalized: rules changes have landed with the goldens untouched
because "this change cannot alter the transcript" was executed via `node --test`,
not argued in prose.

## AI Collaboration

This project has access to multiple AI agents. **Use them proactively** — don't wait to be asked.

> **Staleness note (2026-08):** the Gemini CLI is retired; Google's replacement
> is Antigravity (`agy`). `/portrait` and `/council` have been re-plumbed onto
> `agy`; council's Gemini seat can also view image files granted via
> `--add-dir` (verified 2026-08-16). The Gemini halves of `/deploy` and
> `/security` have not been re-plumbed and will fail until they get the same
> treatment. The Codex halves still work.

### `/council` — Get External Perspectives
Consults Gemini and Codex for design feedback. Use when:
- Facing architectural decisions with multiple valid approaches
- Uncertain about implementation strategy
- Making changes that affect multiple subsystems
- Design tradeoffs need external perspective

### `/deploy` — Delegate Implementation
Deploys Codex or Gemini as working agents. Use when:
- Task has independent subtasks that can be parallelized
- Well-scoped implementation work can be delegated
- Bulk file operations or repetitive changes needed
- You want a different implementation approach to compare

**Philosophy:** These aren't just tools for the user to invoke — they're force multipliers. If consulting would improve a decision or deploying would speed up work, do it.

---

## Design Principles

1. **Narrative over mechanics** — The agent is a storyteller, not a rules engine
2. **Consequences bloom over time** — Plant seeds, let them grow
3. **NPCs are people** — Every NPC has wants, fears, and memory
4. **Honor player choices** — No "right answers," no punishment for creativity
5. **Validate limits** — Social energy depletion should feel humane, not punitive

## Test Campaigns

| Campaign | Owner | Purpose |
|----------|-------|---------|
| `cipher` | Shawn | Primary playtest campaign |
| `axiom` | Claude | AI assistant testing save (do not delete) |

The `axiom` campaign is used by Claude for testing new features, command flows, and UI changes. It has a Ghost background character named "Axiom" and serves as a safe sandbox for development testing.

## License

CC BY-NC 4.0
