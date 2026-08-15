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

**The provenance mechanism exists, is half-applied, and points at nothing.**
`HistoryEntry` (`sentinel-agent/src/state/schemas/campaign.py:81`) carries
`event_id: str | None` plus typed sub-records — `mission`, `hinge`,
`faction_shift`. Of those:

- `mission=` (`manager.py:888`) and `hinge=` (`manager.py:1730`) are populated
- `faction_shift=` is not passed on any **live recording path** — the three
  `FACTION_SHIFT` call sites (`manager.py:711`, `1485`, `1622`) send a
  formatted string and leave the typed field `None`. The seed importer
  (`sentinel-agent/scripts/import_cipher.py:161`) does construct one, which
  makes this a runtime inconsistency rather than an unused field.
- `event_id` is populated in exactly one place, `manager.py:714`, under the
  comment `# Provenance: links to MCP event`

**And that pointer already dangles.** `_process_pending_events()` marks each
event processed and then calls `clear_processed()`, which is
`self.events = [e for e in self.events if not e.processed]`
(`schemas/campaign.py:229`) — the payload is *deleted by design* moments after
the id is recorded. There is no lookup-by-id anywhere, and memvid keeps the id
only inside a prose `cause`. So the one field in this codebase actually
commented "Provenance" points at something that no longer exists (caught in
review).

This reverses the first draft's conclusion, which said to finish the pattern
and decide about the append-only log afterwards. **A durable event record is a
prerequisite, not a follow-up.** `event_id` is not a provenance mechanism until
its target survives, and every pointer minted before then is another dangling
reference. It also means the append-only structured log
(`munder_difflin_notes.md`, open item) is now justified by a consumer that
exists rather than by analogy to another project: without it, the sentence at
the top of this doc cannot be delivered at all.

The first draft made exactly the error this doc warns about. It verified that
the pointer existed and was populated, and never checked whether the pointee
survived — the untested boundary, one layer in.

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
| thing | `world/things/<id>.json` | `thingValid` (new) | kit, shops, drops |
| offer | `world/offers/<id>.json` | `offerValid` | encounters |

`run-core`'s `itemValid` is **not** this validator and should not be stretched
into one: it checks a flair item's fixed shape (`id`, `name`, `slot`, `cost`,
`color`) and enforces the Tier 1 slot law, which is a narrower job than
describing an arbitrary world thing. A world thing that happens to be wearable
should *reduce* to a flair item at the boundary where the run banks it, and be
refused by that same check if it cannot (caught in review).

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

Ordered, because the first draft had the order backwards and the dependency is
real:

1. **A durable target, first.** Provenance needs something that survives.
   Either the append-only structured log, or — cheaper — stop deleting: retain
   processed events, or copy the payload into history before `clear_processed()`
   runs. Nothing below works without this, and every `event_id` written before
   it is a dangling pointer.
2. **Populate the typed sub-records at the sites that know the answer.** Not at
   the MCP logging site: `log_faction_event` also carries `mission`, `contact`
   and `negotiate` events, and its payload has neither `from_standing` nor
   `to_standing`, so constructing a `FactionShiftRecord` there would fabricate
   standings or mislabel non-shifts. The right sites are `shift_faction()` and
   the cascade path, where `before` and `after` are both in scope. General
   faction events want their own record type rather than being forced into a
   shift shape (caught in review).
3. **Give things an `origin`** — an event id, once (1) makes ids resolvable, and
   where one exists a match id from the witness archive. A hood that knows the
   night is a hood that can be asked about it.
4. **Make the origin legible** — one line in the room, one line on the card.
   Where a match id exists, a link that replays it.

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
