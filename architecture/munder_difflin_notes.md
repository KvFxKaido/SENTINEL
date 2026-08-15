# External Reference — Munder Difflin (multi-agent harness)

**Status:** Reference, v0.1 — steers future work on the agent/event layer and on
UI state visibility; not binding. Decided items, if any, are marked inline with
their decision date.
**Source:** [`chaitanyagiri/munder-difflin`](https://github.com/chaitanyagiri/munder-difflin)
(MIT source; bundled pixel art non-commercial), read at commit-of-record
2026-08-14. Design docs `HIVE.md`, `SPEC.md`, `DESIGN.md` in the repo root.
Marketing site + blog at `munderdiffl.in`.
**Related:** `AGENT_ARCHITECTURE.md` (our agent + state layer),
`art_direction_gba_tactics.md` (state-visibility-as-pixels),
`sentinel-agent/src/state/event_bus.py` (our pub/sub)

## Why this reference

Munder Difflin is a local harness that wraps terminal agent CLIs (Claude Code,
Codex, Antigravity, Grok, Kimi, Qwen, OpenCode, Copilot CLI) into a coordinated
"office": each agent is a real pty process with a mailbox and a long-term memory
file, drawn as a 24×24 sprite walking around a Pixi.js office floor, with a
"GOD agent" routing work and escalating to the human.

It is not a game and we are not building a harness. It earns a reference doc for
two narrower reasons:

1. It solved the *durable event plane* problem we have punted on, and its
   solution is boring in the way our design philosophy asks for.
2. Its design doc states its taste constraints as **falsifiable tests** rather
   than adjectives, which is a technique worth copying independent of the
   content.

Read `HIVE.md` first; it is better written than the README.

---

## What transfers

### 1. Two planes, and never parsing the transcript for state

Munder Difflin keeps a hard separation:

- **Terminal plane** — raw pty bytes, tailed to a log, rendered verbatim by
  xterm.js. Never parsed.
- **Event plane** — structured lifecycle events arriving *out of band* via
  provider hooks (`UserPromptSubmit`, `PreToolUse`, `PostToolUse`,
  `Notification`, `Stop`), POSTed to a Unix socket owned by the main process.

The renderer learns what an agent did from the event plane, never by scraping
the terminal. Their stated fallback if hook schemas break is text parsing —
named explicitly as the degraded path, not the design.

**For us:** this validates the shape of `event_bus.py`. Narrative stream and
state change are different planes, and the TUI should keep learning about state
from the second one. It is also an argument against any future temptation to
infer campaign state by re-reading GM prose.

### 2. Durable append-only log with per-consumer cursors — *the useful idea*

Their `log.jsonl` is append-only. Consumers track their own cursor position,
which decouples production from consumption and buys replay for free. Per-agent
`cursor.json` prevents reprocessing; handled messages are archived to
`inbox/.done/` for audit rather than deleted.

**Gap this exposes in SENTINEL — stated narrowly, because the obvious version
of the claim is false.** State transitions *are* persisted: `apply_faction_shift`
calls `log_history()`, which appends a `HistoryEntry` and calls
`save_campaign()` before the event is ever emitted
(`sentinel-agent/src/state/manager.py:1483`). `EventBus` additionally retains
its last 100 events (`event_bus.py:139-140`) with a `get_history()` accessor.
So a faction shift with no subscriber attached is *not* lost, and the audit
trail is not empty.

What is actually missing is narrower:

- **The event payload is richer than what persists.** `FACTION_CHANGED` carries
  structured `before`/`after`, `cascades`, `campaign_id`, and `session`; the
  `HistoryEntry` that reaches disk carries a formatted summary *string*. A
  consumer reconstructing history from the campaign file has to parse prose to
  recover what the event already had in fields.
- **Replay does not survive restart.** `EventBus._history` is in-process and
  capped at 100. Reattaching after a restart cannot recover events, and there is
  no per-consumer cursor, so a subscriber cannot resume from where it left off —
  only from "now."

An append-only, structured campaign event log would close both: full payloads on
disk, resumable by cursor across restarts, and plausibly the thing memvid /
`/timeline` indexes instead of a parallel structure over the same history. That
is a real gap, but it is a gap in *fidelity and resumability*, not in whether
anything is recorded at all.

This is the highest-value idea in the repo for us.

### 3. The speech-act message schema

Messages carry seven semantic fields, but three do the load-bearing work:

- `action ∈ {request, inform, propose, query, agree, refuse, done}`
- a **reply-obligation** flag
- a **hop counter** with a cap

The rule that makes it work, quoted: *"Only `request`/`query`/`propose` obligate
a reply (pure `inform`/`done` are terminal)."* That single line is what stops
agent ping-pong. The hop cap catches whatever slips past it and escalates rather
than looping.

**Where this maps for us: NPC ↔ player ↔ faction interactions.** A typed
vocabulary with an explicit "does this demand a response" bit is a better model
of social pressure than free-form exchange, and it composes with social energy —
an unanswered obligation becomes a legible cost rather than an implicit one.

**Where it explicitly does *not* map: our multi-agent skills.** `/council` is a
one-shot fan-out — consult Gemini, consult Codex, synthesize — with no
agent-to-agent messaging and no follow-up round
(`.claude/skills/council/SKILL.md`). There is no cycle for a hop cap or a
reply-obligation flag to guard, and adding one would be defending against a
failure mode we do not have. The guard becomes relevant only if a council flow
ever feeds one consultant's output back to another; until then this is a note
about NPC modelling, not about tooling.

### 4. Memory posture — including the part they haven't solved

Markdown-first (`memory.md` per agent), read at task start, appended as
knowledge accumulates. A semantic index (their "MemPalace") is mined *on top*,
with **graceful degradation** when the index is unavailable. This is the same
posture as memvid being optional in SENTINEL, arrived at independently.

Worth recording honestly: their condensation/summarization pass to bound memory
growth is **Phase 3 and still unvalidated end-to-end**. They ship the memory
layer with unbounded growth as a known open failure mode, listed as such in
their own failure table. Our campaign saves carry the same risk, and we should
not assume the problem is solved anywhere just because the retrieval half works.

### 5. State visible through several channels at once, never colour alone

Their avatars communicate status through **position** (at desk = idle, walking
to station = thinking, at station = working) **+ badge chip + 8×8 overlay icon
+ UI chrome tint**, simultaneously. Explicitly never colour alone.

**For us:** directly applicable to `art_direction_gba_tactics.md` and the TUI.
The redundancy is an accessibility argument and a legibility argument at the
same time, and it is the same discipline the SRW stat sheet enforces.

### 6. Taste constraints stated as tests

Their design doc's governing constraint is: *"If a component could exist on iOS
17, it's wrong."* That is a rule you can **fail**, applied to a specific target
(1995–2005 Nintendo, not "retro"). Compare with the adjective-based version —
"chunky, nostalgic, characterful" — which cannot be failed and therefore cannot
review anything.

`art_direction_gba_tactics.md` would benefit from an equivalent one-liner at the
top: a single sentence a reviewer can hold a mock against and say *no*.

---

## Two cautions that land on our own principles

**Capability blast radius.** Their hook install writes into
`.claude/settings.local.json`, and they recommend per-project rather than global
scope specifically "to limit blast radius." That is design philosophy rule #2
(capability changes require consent) learned the same way we learned it —
worth noting that the convergence is independent.

**Asset provenance.** Their source is MIT, but the bundled pixel art derives
from LimeZu's tilesets under a **non-commercial-use-only** licence: commercial
deployment requires replacing the art or buying a separate licence. They
document this up front in the README rather than burying it.

We are CC BY-NC 4.0, so the immediate conflict is smaller — but the practice is
the one to copy. Sprite and tileset provenance for `prototypes/tactical3d/` and
any future sprite work should be stated as plainly as they state theirs, at the
point where someone would otherwise assume it was ours.

---

## What not to take

**The GOD-agent orchestrator.** A single LLM ("Michael") adjudicates routine
requests autonomously and decides which ones a human sees. Its escalation policy
lives in a system prompt — which means it is neither visible, nor diffable, nor
testable, and the human cannot tell what was decided on their behalf. By design
philosophy rule #5 (*if it feels impressive, it's probably hiding something*),
this is the part to be suspicious of. It is also the part the marketing leads
with.

The contrast inside the same codebase is instructive. Their mechanical layer is
boring and correct:

| Failure | Their defence |
|---------|---------------|
| Git index corruption | Single committer; retry + backoff; stale-lock cleanup |
| Concurrent mailbox writes | One JSON file per message, temp-file + atomic `rename` |
| Infinite Stop-hook loops | `stop_hook_active` guard, hop cap, block cap |
| Agent ping-pong | Reply obligation only on request/query/propose |
| Message reprocessing | Per-agent cursor; processed messages archived |
| Unbounded memory growth | *(unsolved — Phase 3)* |

Every row except the last is a small, legible mechanism. That layer is the one
worth reading. The orchestration on top of it is a demo.

**The office-floor visualisation, as a model for us.** They make it work by
pairing it with the multi-channel state rules above, but a spatial metaphor is a
representation that can drift from what it represents. We would be adopting the
risk without their reason for taking it.

---

## Disambiguation

Searching "Munder Difflin" also surfaces a **Munder Difflin Paper Company**
multi-agent project — a Udacity Agentic AI nanodegree course assignment, no
relation to the harness described here. Both borrow the name from *The Office*.

## Open items

- [ ] Append-only campaign event log with consumer cursors — worth a Proposal
      doc of its own; would supersede or wrap `event_bus.py`, and should be
      designed alongside memvid/`/timeline` rather than beside it.
- [ ] Reply-obligation flag on NPC interactions — smaller; sketch against the
      existing disposition + social-energy model before committing to a schema.
- [ ] One falsifiable taste constraint at the top of
      `art_direction_gba_tactics.md`.
- [ ] Asset provenance statement for `prototypes/tactical3d/` sprites.
