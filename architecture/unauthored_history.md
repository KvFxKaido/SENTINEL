# "I Got This Hood From A Random NPC One Day"

> **Version:** 0.1
> **Date:** August 15, 2026
> **Status:** Proposal — an authoring pipeline, argued before anything is built
> **Provenance:** designer, after a long detour through forever-games, Bethesda
> modularity and Fallout: London. The detour's conclusion was not "go 3D." It
> was that the thing worth optimizing is the **pipeline for making content**,
> and the thing worth making is **agency that nobody authored**.
> **Related:** `sentinel_circuit_design.md` §6 (trophies, personal tokens),
> `circuit_season_loop.md` (the roster is the protagonist),
> `munder_difflin_notes.md` (the append-only log open item)

---

## 1. The Sentence

> *"I got this hood from a random NPC one day."*

That is the whole design target. Not a feature list — a sentence a player
should be able to say truthfully, about an object they own, in a run nobody
scripted for them.

It is worth stating why that sentence is hard, because it looks easy. Every
part of it is load-bearing:

| fragment | what it demands |
|---|---|
| *this hood* | the object persists, and is **this** one — not a stack count |
| *from a random NPC* | **nobody authored** the hood-for-you. It was contingent |
| *one day* | the object remembers **when**, and the when is retrievable |
| *I got* | the player was there. It happened **to them**, not to a save file |

## 2. What This Is Not

**It is not branching.** A branch authors the outcomes and lets the player pick
one; the space of stories is exactly as large as somebody typed. That is the
opposite of the sentence. Nobody should have written the hood.

**It is not radiant filler either.** Bethesda's radiant quests are contingent
and produce almost no attachment, because the output is interchangeable —
*a* raider camp, *a* fetch. Contingency alone is noise. What separates the two
is whether the result carries **a record of the specific circumstances that
produced it**, and whether the game can hand that record back.

So the axis is not authored-vs-emergent. It is:

```
authored outcome            <- branching, expensive, finite
authored CONDITIONS         <- what we want
authored nothing            <- radiant noise
```

We author **actors, needs, rules, and stakes**. The outcome is whatever falls
out, and it is stamped with what fell.

## 3. Four Properties, All Required

An object, event or relationship earns the sentence only with all four:

1. **Contingent** — it could have not happened, and its shape depends on state
   the player influenced.
2. **Provenanced** — it carries a pointer to the moment that produced it, not a
   prose summary of it.
3. **Persistent** — it survives the session, the run, and ideally the campaign.
4. **Legible** — the player can get the story back out, in the room or on the
   card. (This is the season doc's acceptance law, unchanged: *a fact not
   visible in the room or on the card does not exist.*)

Three out of four is a feature nobody notices. Persistence without provenance
is inventory. Provenance without legibility is a database.

## 4. What Already Exists

More than expected, which is why this is a pipeline proposal and not an engine
proposal.

**The doctrine is already written.** `sentinel_circuit_design.md` §6 says
trophies have provenance *in grades* — a trophy from a recorded match is
certified, "the jacket is *from the night you refused the yield at the drained
reservoir*, and anyone can rewatch what it cost." And personal tokens are
already specified as **player-authored insignia**: "nobody designs them, play
makes them mean something." The sentence above is that section, restated by the
designer from memory two months later. It was always the target.

**The provenance mechanism exists and is half-applied.**
`HistoryEntry` (`sentinel-agent/src/state/schemas/campaign.py:81`) carries
`event_id: str | None` plus typed sub-records — `mission`, `hinge`,
`faction_shift`. Of those:

- `event_id` is populated in exactly one place, `manager.py:714`, under the
  comment `# Provenance: links to MCP event`
- `mission=` (`manager.py:888`) and `hinge=` (`manager.py:1730`) are populated
- `faction_shift=` is **never** passed — the typed field exists and the call
  site sends only a formatted string

So the pattern is in the codebase, named, and used inconsistently. This is a
much cheaper starting point than the append-only log
(`munder_difflin_notes.md`) it was previously framed as needing: **finish the
pattern first, and find out whether the log is still necessary afterwards.**

**The item side already stamps.** `run-core`'s purchase record carries
`{id, name, slot, color, who, cost, at}` plus the slate stamp
`{idx, venue, host, sanction}` — where on the tour it was bought. That is
provenance in the weak form: it remembers a *position*, not a *moment*. One
field (`event_id`) upgrades it.

**The witness archive is the strong form, already built.** Every filed match is
content-addressed on `{rules, seed, roster, record}` and replayable from
`/matches/{id}`. An object that carries a match id can have its origin *watched*,
not merely described. Nothing else in this stack can make that claim.

**The world data exists.** 11 regions with adjacency and control, 11 factions
with NPCs and operations, job templates, favors, a disposition ladder, dormant
threads, 108 wiki pages. The simulation substrate is not the bottleneck.

## 5. The Pipeline — The Actual Proposal

The bottleneck is **how fast a new thing gets into the world**. The design
constraint follows from one property: *content that is diffable text can be
authored by the designer, by an assistant, or by a script, and reviewed like
code. Content that lives in a GUI can only be authored by clicking.*

Everything below is a file. Nothing below is a tool.

### 5.1 One file per thing, validated at a boundary, faulting loudly

The repo already has this idiom and should generalize it rather than invent a
new one: `slateValid`, `stockValid`, `rosterValid`, `cardValid` — authored data
checked at the edge, refusing rather than defaulting, throwing at boot. Every
content type below gets the same treatment.

| content type | file | validated by | consumed by |
|---|---|---|---|
| place | `world/places/<id>.json` | `placeValid` | the room / overworld |
| person | `world/people/<id>.json` | `personValid` | schedules, encounters |
| thing | `world/things/<id>.json` | `itemValid` (exists) | kit, shops, drops |
| offer | `world/offers/<id>.json` | `offerValid` | encounters |

An **offer** is the unit that produces the sentence. Not a quest — a quest
authors an outcome. An offer authors a *condition*: who, where, what they want,
what they will part with, and what makes them willing. The hood is not written
into a reward table; it is a thing that person owns, which becomes yours if the
conditions land.

### 5.2 The authoring loop, and its target time

The measurable design target, worth writing down because it is the whole point:

> **From "I want a fence in The Drain who trades gear for information about
> Covenant patrols" to walking up to him: under one hour.**

If that is an hour, there is a pipeline. If it is a day, there is a tool problem
wearing a content problem's clothes. The loop:

1. write `world/people/fence-drain.json` — a person, an inventory, a want
2. `python scripts/world_check.py` — validation, ids resolve, no dangling refs
3. reload — no rebuild, no editor, no binary

Steps 2 and 3 are the deliverable. Step 1 is the part an assistant can do.

### 5.3 Ids are the contract

Every authored thing has a stable string id, and every reference is by id.
This is the boring decision that makes everything else possible: diffs stay
readable, an assistant can write references without seeing the whole world, and
provenance pointers survive a save-game migration. `world_check.py` refuses
dangling ids the way `sane()` refuses a run whose books do not balance.

### 5.4 What is NOT text, and the honest cost

Art. Meshes if it ever goes volumetric; sprites today. This is the one layer no
authoring pipeline fixes, and it is why the 2.5D diorama direction is worth
keeping: it buys spatial inhabitation at the cost of an art pipeline that
already exists (`roster_mold.py`, PixelLab, acceptance checks) rather than one
that does not.

## 6. What This Asks Of The Engine

Small, and mostly finishing:

1. **Populate `faction_shift=`** at its call site. One argument. Closes the
   inconsistency and makes the pattern uniform.
2. **Give things an `origin`** — an `event_id`, and where one exists, a match id
   from the witness archive. A hood that knows the night is a hood that can be
   asked about it.
3. **Make the origin legible** — one line in the room, one line on the card.
   Where a match id exists, a link that replays it.
4. **Then** ask whether the append-only structured log is needed. It probably is,
   for resumability. But it should be justified by a consumer that exists, not
   by analogy to another project's architecture.

## 7. What Not To Build

- **Dialogue trees.** They author outcomes, cost enormously, and are the exact
  shape this doc rejects.
- **Quest markers.** A bounty target at work is the design; an arrow over their
  head is its deletion.
- **Uniqueness by authorship.** No "legendary" table. An object is special
  because of what happened, not because a designer flagged it.
- **A framework for N fantasies.** Build this one. The framework is what falls
  out of building the second thing, never what precedes the first.

## 8. Open Questions

1. **Where do people live — campaign layer or room?** The campaign has NPCs as
   data and no bodies; the room has bodies and no people. The seam between them
   is unbuilt and is probably the first real work.
2. **Does the Circuit host this, or is it a sibling?** The Circuit is one venue
   inside the campaign by its own doc. A fence in The Drain is not a card. That
   may mean the room grows a second door.
3. **How much contingency before it reads as noise?** Radiant quests are the
   warning. The answer is likely that provenance is the difference, but it wants
   a played test, not an argument.
4. **What is the day-three test?** Leave, come back, and see whether the world
   reached a state you did not predict and can still explain. That is the
   acceptance test for this entire direction, and it cannot be run until at
   least two systems interact without the player.
