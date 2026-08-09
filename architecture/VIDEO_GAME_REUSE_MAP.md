# SENTINEL → Video Game Reuse Map

> **Status:** Repo structure map — what's live, what's reference, what transfers
> **Date:** July 2026
> **Context:** This repo is being **restructured in place**, not retired. Active
> tabletop-tool development has wound down, but the repo stays live as the
> pre-production corpus for the SENTINEL video game: source IP plus a runnable
> reference implementation. This document maps what transfers, in what form, and
> what is kept as reference rather than ported.

---

## The Short Version

By code volume, roughly 40% of the Python here is disposable. But close to **100% of the
design, lore, content data, and systems logic survives the pivot.** The presentation layer
(Textual TUI, wiki sync) was built for the tabletop-tool era and does not transfer — and
that layer is also what made spatial embodiment painful to build, which is where momentum
stalled.

Notably, the video game design phase already happened in this repo:
`architecture/Sentinel 2D.md` (v3.0, January 2026) is a design-binding spatial embodiment
plan, with supporting isometric sprite/animation rules and sound/visual roadmaps. The pivot
is a resumption, not a restart.

---

## Tier 1 — Transfers As-Is (the actual IP)

Zero translation needed. This is the material that would take a year to recreate.

| Asset | Location | Role in the video game |
|---|---|---|
| Core rules (3 docs, ~1,100 lines) | `core/` | The systems design spec: Playbook, Character Sheet, Social Metabolism & Memory |
| Lore corpus (~3,500 lines) | `lore/` | Setting bible: 10-chapter novella arc, Canon Bible, geography. Tone reference and backstory source |
| Canon wiki pages | `wiki/canon/` | In-game codex content, nearly verbatim |
| Faction database (11 factions) | `sentinel-campaign/src/sentinel_campaign/data/factions/` | Content database — engine-agnostic JSON: NPCs, operations, lore per faction |
| Region data | `sentinel-agent/data/regions.json` | World map data: 11 regions, adjacency, faction control, terrain |
| Job templates | `sentinel-agent/data/jobs/` | Mission/contract content seeds, keyed by faction |
| **Game design doc** | `architecture/Sentinel 2D.md` | The GDD. Council-reviewed, design-binding. Commitment gate, safehouse anchor, map-as-proposal turn loop, hybrid combat |
| Art direction | `architecture/Isometric Sprite System.md`, `Isometric Animation Rules.md`, `Mobile Sprite Sketching Checklist.md`, `sentinel_visual_roadmap.md` | Sprite and animation production rules |
| Audio direction | `architecture/sentinel_sound_roadmap.md` | Sound design plan |
| Design invariants | `CLAUDE.md` § Design Philosophy (condensed) | Postmortem-driven principles; the full original doc was retired in May 2026, the condensed version is the living one |
| Character appearance specs | `assets/characters/` — **now tracked** | ✅ Promoted from gitignored local-only to tracked source IP during the restructure. Safe in git history |
| Original body art + generation records | `assets/original/`, `scripts/pixellab_*.json`, `architecture/original_body_pipeline.md` | The shipping sprite path: license-clean generated art (locked appearance, verb sheets, 96×80 re-frames), the input records that document its provenance, and the migration doc (Current since the slice passed 2026-08-09). The PNGs are the source of truth — tracked precisely because the records cannot regenerate them (null seeds, provider CDN links; "a CDN is not provenance"). Replaces the pack-derived path, which could never ship from this CC BY-NC repo |
| Character portraits + generator | `assets/portraits/` — **now tracked** | ✅ 14 curated PNGs + `generate_all.py`, committed directly (~20MB, archive-safe, no LFS dependency). Only lossily reproducible, so kept verbatim |

## Tier 2 — Transfers as Blueprint (port the logic, not the code)

`sentinel-agent/src/systems/` (~4,500 lines) is pure domain logic with no UI entanglement:

- `leverage.py` — enhancement debt and demand mechanics
- `cascades.py` — cross-faction consequence propagation
- `favors.py` — disposition-gated favor economy
- `arcs.py` — character arc detection
- `endgame.py` — readiness scoring and epilogue assembly
- `turns.py`, `travel.py`, `interrupts.py`, `missions.py`, `jobs.py` — turn authority, movement, event injection, job lifecycle

These are deterministic rules. In an engine-native rewrite (Godot/GDScript, C#, etc.), the
Python serves as the **reference implementation** and its tests as the spec. Porting against
a working reference is dramatically cheaper than designing these systems again.

Likewise `sentinel-agent/src/state/schemas/` (character, npc, world, campaign, action, event, turn_result):
these Pydantic models are the save-game schema, translatable to any serialization format.

## Tier 3 — Transfers Only If NPCs Stay AI-Driven

`Sentinel 2D.md`'s turn loop ("map as proposal, GM as authority") assumes an AI GM layer.
If the video game keeps LLM-driven NPC dialogue and consequence narration:

- `sentinel-agent/prompts/` — GM personality, mechanics reference, condensed local-model variants
- `sentinel-agent/src/agent.py` — tool definitions and orchestration patterns
- `sentinel-campaign/` MCP server — faction tools, standing, intel; MCP is client-agnostic, so this transfers close to intact
- `sentinel-agent/src/interface/codec.py` — codec-style NPC conversation implementation (design notes in `architecture/sentinel_visual_roadmap.md`)

If dialogue goes fully scripted instead, this tier is sunk cost — but the *content* inside
the prompts (faction voice, disposition tone rules) still feeds the writing.

## Tier 4 — Does Not Transfer (and that's fine)

Presentation layer built for the terminal-tool era:

- `sentinel-agent/src/interface/tui.py`, `tui_commands.py` — Textual TUI
- `sentinel-agent/src/state/wiki_watcher.py`, `wiki_adapter.py` — Obsidian bi-directional sync
- `sentinel-agent/src/state/event_bus.py` — TUI reactivity wiring
- `sentinel-agent/src/interface/commands.py` — CLI

This layer did its job: it let the systems and content get playtested without an engine.

---

## Recommended Path

1. **Source IP is preserved in git** ✅ *(done)* — `assets/characters/` and
   `assets/portraits/` were promoted from gitignored local-only files to tracked
   source IP. Archiving or cloning the repo now captures the full corpus. The
   dependency-bump noise was stopped by removing `.github/dependabot.yml`.
2. **Keep this repo live, restructured in place** — *not* archived. A read-only
   archive would break step 5 (the Tier 2 reference implementation must stay
   runnable to port against). One repo, one history: reference and rewrite side
   by side. Retired presentation-layer code stays in git history, not deleted.
3. **Add the engine-native project as a top-level sibling** here (e.g. `game/`)
   when it starts — a new directory in this repo, not a fresh repo.
4. **Founding documents** for the game: `architecture/Sentinel 2D.md`, `core/`,
   the faction and region JSON data, and the condensed design philosophy in
   `CLAUDE.md`.
5. **Port Tier 2 systems** against the Python reference implementations, tests
   first. The repo staying live is what keeps this reference executable.
6. **Decide Tier 3 early** — AI-driven NPC dialogue is an architectural fork, not a
   feature flag. The MCP server is ready if the answer is yes.
