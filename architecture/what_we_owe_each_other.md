# What We Owe Each Other

> **Version:** 0.1
> **Date:** August 16, 2026
> **Status:** Proposal — pairwise history and its boundaries, argued before
> implementation
> **Provenance:** designer discussion prompted by *Star Wars Zero Company*'s
> squad-bond and utility-role systems, corrected against the live SENTINEL
> stack in a three-way pass (designer, Claude, Codex)
> **Related:** `circuit_season_loop.md` (the roster is the protagonist),
> `roster_in_the_match.md` (the current certified-input law),
> `unauthored_history.md` (the provenance test),
> `sentinel_circuit_design.md` §6 (verbs, access and provenance grades),
> `munder_difflin_notes.md` (the durable-event prerequisite)

---

## 1. The Thesis

> **A relationship is a sentence about what two people have done for each
> other, with a source the player can inspect. It changes what they may ask of
> each other, not their stats.**

The Circuit already knows who fought, what shape they were in, what commands
they committed, what the Witness could replay, and what the run banked. It does
not yet know what one fighter has become to another.

The obvious implementation is a bond meter: field two people together, fill a
bar, unlock passive bonuses. That would be legible and persistent, but neither
contingent nor meaningfully provenanced. Time served together is not trust, and
`+10 aim while adjacent` is not a relationship. It is a formation bonus wearing
a friendship label.

SENTINEL's version begins with an event:

```text
authored person
  -> fielded pair
  -> explicit utility verb
  -> replayed moment
  -> durable origin
  -> named relationship
  -> visible permission or obligation in the room
  -> someday, if earned, a paired verb in the yard
```

The order is the design. Verbs come before relationships because a relationship
must point at the moment that produced it. Room consequences come before paired
combat techniques because most relationship state can matter without changing
what a match is.

## 2. Three Different Things Called A Bond

These layers are related. They are not interchangeable.

| Layer | Question it answers | Owner | Certified match input? |
|---|---|---|---|
| **relationship history** | What happened between these two people? | the run, pointing at a durable origin | no |
| **permission or obligation** | What will they now do, refuse, risk or ask outside the yard? | the run; enforced visibly by the room | no |
| **paired tactical verb** | What can this exact pair do inside this match? | an immutable snapshot consumed by the yard | yes |

Examples make the boundary clearer:

- `WON'T GO WITHOUT KOA` may constrain a lineup before the card is dealt. It is
  the same *shape* as `fitness(run)`: the room and the door ask whether the deal
  is legal, and the yard need never know why it was not opened.
- `OWES A LIFE` may alter a recovery, pass or settlement decision. Those are
  run economics. The certified match remains unchanged.
- `LINKED OVERWATCH` changes a legal action or reaction inside the yard. The
  Witness must receive the fact that made it legal, replay from it, and include
  it in the content address. That is a doctrine change, undertaken only for a
  specific verb that has already justified the cost.

This corrects an easy sequencing mistake: relationship state does **not** enter
the match merely because it exists. It enters only when the match consults it.

## 3. The Bench Is A Faction Door

Lineup choice is not a picker built over interchangeable bodies. Before the
run can own a bench, it must answer where fighters come from.

The answer is the same authored-condition pipeline proposed in
`unauthored_history.md`:

- a Convergence sponsor offers a fighter carrying an enhancement package and
  the leverage attached to it;
- the Ember Colonies quietly enter somebody because winter was bad;
- the Covenant vouches for a fighter whose participation is itself an oath;
- the Ghost Networks delivers a recruit whose identity may be a product;
- a person already in `world/people/` becomes available because an offer's
  conditions landed.

A body may be procedurally composed. An entrance is authored. Every recruit has
a stable person, a source, a reason they are here, and someone whose account of
that reason may be false.

This matters immediately for relationships. The tactical roster currently
uses a fighter's uppercase name as its identity in the transcript. That is
sufficient for the current three-slot wire contract. It is not a durable key
for a pairwise history once aliases, false colors, renamed recruits or identity
laundering exist.

The future run-owned roster therefore needs a stable person id outside the
yard. The room may deal a tactical name, but a relationship belongs to the
people behind the names. This proposal does not change the current
`{name, hp}` match input or decide how that mapping crosses the door. It names
the identity question before a bond ledger accidentally makes display names
permanent.

## 4. Verbs Before Bonds

Today's record vocabulary is deliberately small: move, shoot, finish,
overwatch, spare, end, and the house's twist. It can reproduce the match, but
it cannot honestly produce a sentence like:

> Sable dragged Koa out under fire.

Trying to infer that sentence from nearby movement and subsequent survival
would create a hidden authorship system. A pathfinder's geometry is not an
expression of intent, and the player could not know which incidental patterns
the relationship engine was scoring.

The record needs explicit utility verbs first. Candidate families include:

- assistance — one fighter commits tempo to another's declared action;
- protection — one fighter takes responsibility for a visible lane or threat;
- extraction — stabilize, carry or drag somebody who cannot leave alone;
- displacement — create an opening another fighter may use;
- interference — alter cover, doors, lights, machinery or the feed.

This is not a verb catalogue and none of those names are settled. The first
verb should prove four properties:

1. **Explicit intent.** The player chose a two-person act; the engine did not
   infer friendship from incidental geometry.
2. **Real cost.** Somebody spends AP, position, safety, ammunition or another
   visible resource. An assist is not a free-action fountain.
3. **Canonical recording.** The committed input names actor and beneficiary,
   and replay reaches the same result.
4. **Legible resolution.** The board and feed say what was attempted and what
   happened.

The relationship is then derived from replayed facts, never awarded because a
client asserted `bond += 1`. The derivation may name the command index and a
predicate over replayed state — who acted, for whom, under what danger, and
whether the act mattered. The exact predicate belongs beside the verb in the
rules and its tests, not in prose interpreted differently by every caller —
and it belongs *there* because only the rules core can replay. Derivation
next to the verb is what keeps relationship-minting deterministic and
testable; the run consumes derived events and never computes them, which is
the line that leaves `bond += 1` with no place to live.

Simply sharing a card is not a relationship-producing verb.

## 5. A Pairwise Mercy Ledger

The run's mercy ledger is the model: a sentence about who the squad has been,
assembled from outcomes the edge replayed. Relationships are the pairwise
form of the same idea.

A relationship entry must carry enough information to answer:

- **who** the two people are, by stable identity;
- **what** named fact now holds between them;
- **where** it came from;
- **which grade** of provenance supports it;
- **whether** it is active, fulfilled, broken or superseded;
- **how** the room makes it visible.

This proposal deliberately does not freeze a JSON schema. A premature shape is
how an implementation detail becomes doctrine before the first real verb has
tested it. The invariant is that the source resolves.

### Certified grade

`POST /certify` proves that a record replayed under the current rules. It does
not make the record durable. For the durable-moment slice the live room uses
`POST /file` on its certified path, so the same replay that certifies the card
also gives it an archived origin. This is the recorded 2026-08-16 step-3
decision **THE ROOM FILES WHAT IT CERTIFIES**, subject to designer veto at
review; the yard's separate **FILE THE RECORD** action remains another route
to the same idempotent endpoint. A future deliberate feed cut submits to
neither endpoint, so it does not conflict with this choice.

A relationship called **certified** therefore needs a filed match id (and, when
one match contains several candidate moments, the command or derived-event
position inside it). A certificate fingerprint that disappears with the page
is not an origin.

### Claim grade

An unwitnessed moment may still matter. The Circuit already says an unrecorded
trophy is a claim rather than nothing. A relationship born there is likewise a
claim, clearly labelled and backed by a durable local event rather than prose
that merely says it happened.

The append-only event target argued in `munder_difflin_notes.md` and
`unauthored_history.md` is therefore a prerequisite for claim-grade bonds. No
pointer is minted before its target survives.

Certified and claim are not power tiers. They are statements about what can be
shown. A claimed debt may be more socially explosive than a certified one.

## 6. Permissions And Obligations Live In The Room

The first useful relationships should change the next decision without
changing the next match's rules.

Possible shapes include:

- a lineup condition visible before the card is accepted;
- a recovery choice one fighter can make for another;
- a pass whose social or recovery cost changes because of a promise;
- a settlement option available only because somebody will vouch for the
  choice;
- an obligation that makes a sponsor, faction or teammate ask for repayment.

These are examples, not settled content. Their shared constraints are:

- **The effect is visible before commitment.** Nobody silently edits a lineup,
  spends purse or refuses a card after the player crosses the door.
- **The run owns the fact.** The room renders and enforces it; the yard does
  not receive state it cannot use.
- **The relationship changes choices, not arithmetic.** No passive aim,
  damage, defense or experience bonus.
- **No repetition treadmill.** A relationship changes because a sourced event
  changed it, not because two names appeared together five times.
- **No universal upward ladder.** Trust, debt, dependence, resentment and
  refusal are different facts, not positive and negative positions on one
  meter.

This is Tier 1 relationship play: consequential, persistent and legible, with
zero change to `seed + roster + record = the match`.

## 7. When The Pair Enters The Match

Only a concrete paired verb can justify this step.

The current roster is exactly three `{name, hp}` entries. Extras are refused,
the roster is hashed independently, and the content address includes its
canonical form. A relationship-gated yard action must not arrive as an ignored
extra field or a renderer convention.

Before such a verb ships, a doctrine change must answer:

1. Is pair state part of each fighter, a separate edge list between fielded
   fighters, or another certified input beside the roster?
2. What is its one canonical form?
3. Which component owns the mutable source before the card snapshots it?
4. How do the room, yard, Witness and archive agree on the same snapshot?
5. How does the rules stamp exercise pair handling, rather than merely hashing
   inert data?
6. What does an old record mean when pair state is absent?

Until those are answered in a binding amendment, relationships may gate the
door and bend the run, but they may not change a legal move, shot, reaction or
outcome inside the yard.

## 8. The Opening — A Candidate, Not A Meter

One candidate paired grammar is an **Opening**:

- created by an explicit recorded utility verb;
- consumable only by a different operative;
- at most one active;
- visible on the board and spoken on the feed;
- expired at round end;
- never generated by ordinary damage;
- no points, levels or banked meter.

If a player action creates it, that action is already the warning and the
recorded cause. A second showrunner-style input and a one-resolution delay are
not automatically required. The house's warning rule protects turn authority
when an outside actor inserts an effect; a fighter deliberately creating an
opening is already acting inside turn authority.

If the director, house or another external actor creates an Opening, the
settled twist grammar applies: recorded input, announced one resolution-moment
before it lands, rules-enforced budget.

The announcer remains useful either way. `SABLE LEFT THE GATE OPEN` is both
tone and the free legibility channel required by design-philosophy rule 1.

This proposal does not settle what consuming an Opening does. That answer
belongs to the first verb prototype, where its cost and geometry can be played
rather than admired in a document.

## 9. Cutting The Feed

Interference with the Witness is the utility idea most specific to SENTINEL.
The tactical benefit is purchased with the credibility of the squad's own
history.

The desired shape is compelling:

- a fighter deliberately cuts or jams the broadcast;
- the act creates a visible tactical advantage;
- the match returns labelled unwitnessed rather than pretending it was
  certified;
- public purse, sponsor attention or faction response changes because nobody
  received the show;
- relationships produced in the dark carry claim-grade provenance;
- the choice may itself become discoverable later.

None of those consequences is automatic today.

The rules core computes purse from rating at match end whether a Witness is
reachable or not. `run-core` counts an unwitnessed card and banks its reported
purse. The room calls an unreachable edge `unwitnessed`, but calls a reachable
edge that refuses an incomplete or divergent record `struck`. And if a
`cut-feed` command remains in a complete submitted record, the Witness can
simply replay and certify it.

So feed-cutting is a vertical seam change, not one clever button. A prototype
must decide explicitly:

1. Does the local canonical record continue after the public feed is cut?
2. Is the record intentionally withheld from the Witness — on **every**
   submission path? Darkness must be a property of the card, not of one
   surface: the yard's own **FILE THE RECORD** action posts directly to
   `/file` (`tactical3d/index.html`), so a darkness enforced only in the
   room's submit logic is one button away from the public archive, which
   defeats claim-grade provenance and the later-exposure premise at once
   (caught in review).
3. How is deliberate darkness distinguished from infrastructure failure?
   `unwitnessed` today means the edge was unreachable — an accident. A
   chosen cut banked under the same label is true but misleading, so the
   likely seat of the answer is the run's verdict surface: `CHOSE THE
   DARK` and `LOST THE FEED` distinguished at banking time, not only
   forensically via the surviving record.
4. Which economic outputs disappear, shrink or move elsewhere?
5. What durable source supports a claim-grade relationship from the dark?
6. Can a hidden record be exposed and certified later, and who gains leverage
   by doing so?

The current lean is that the local record continues — determinism should not
be destroyed to express secrecy — while the record is submitted to neither
`/certify` nor `/file` by any surface that holds it. That preserves the
possibility of later exposure without pretending the match was publicly
witnessed when it happened. This is a lean, not settled law.

Feed-cutting should follow the first ordinary utility verb. Otherwise one
prototype would be asked to invent utility actions, intentional witness loss,
graded provenance and altered settlement economics at once.

## 10. Build Order

### 1. The faction door

Give the run ownership of a roster larger than the fielded three: stable person
ids, authored recruitment origins, and a visible lineup decision. Do not add
relationships yet. This is where the eleven factions enter the season as
people rather than jerseys.

> **Landed 2026-08-16.** `run-core` schema v4 owns four people and a lineup of
> three stable ids. Court 01 loads its authored entrances from
> `world/recruitment/court-01.json`; NIX enters through the Ember Colonies, and
> the room exposes the one-person bench before reducing the choice to the
> unchanged certified `{name, hp}` snapshot. No relationship state was added.

### 2. The record vocabulary

Add one explicit two-person utility verb with a real cost, deterministic
replay, readable events and a golden that exercises it. No bond effect is
required for the verb to be worthwhile.

> **Landed 2026-08-16.** `tactical-core` records DRAG as
> `["drag", actorId, bodyId, x, y]`: an adjacent down operative moves one
> tile behind an actor spending a full activation at half mobility, with
> overwatch checked on every shared step. It pays +2 rating once per body,
> heals nothing, and names both people plus the body's movement on the feed.
> The seed-1 golden pins SABLE dragging KOA under SYN-3 reaction fire at
> fingerprint `e9e0a018`; `tactical3d` commits the same verb by selecting
> actor, body, then destination, and slides the existing DEATH pose.

### 3. The durable moment

Derive one pairwise event from replay and give it a surviving target: a filed
match id for certified grade or an append-only local event for claim grade.
The room must be able to take the player back to the source.

> **Landed 2026-08-16.** A completed DRAG deterministically derives
> `{kind:"extraction", actor, beneficiary, commandIndex, underFire, reached:true}`
> beside the verb in `tactical-core`; interrupted drags derive nothing. The
> Witness is the author on the certified path: its own replay returns the
> `derivedEvents` certificate field, and `/file` supplies the content-derived
> match id. Run schema v5 translates tactical names through the fielded lineup
> at bank time and stores the event under stable person ids only with certified
> `{matchId, commandIndex}` provenance. The room renders that grade and **BACK
> TO FILE** opens `GET /matches/{id}` with the pointed command visible.
> Unwitnessed cards and cards certified but not archived still count, while
> banking no derived event; the yard's account remains visible only for the
> current session. Claim grade is deferred because the append-only local event
> log named in §5 does not exist yet, and the twelve-card recent buffer cannot
> be the surviving target a claim pointer requires. This is event provenance
> only: no relationship, permission, obligation, bond name or bond ledger
> landed in this step.

### 4. The pairwise ledger

Bank one named relationship on the run and render it in the room. Give it one
room-layer permission or obligation. Prove save, restore, provenance and the
visible gate. The yard remains unchanged.

### 5. The integrity verb

Prototype feed-cutting as its own seam slice: deliberate unwitnessed status,
explicit economics and claim-grade relationship origins.

### 6. The doctrine change

Only after a relationship-gated tactical verb survives play should pair state
cross the door. Amend the certified-input law, content address, Worker,
goldens and seam harness together.

The first four steps are the on-ramp. Step 6 is not their prerequisite.

The order is dependency, not schedule. Steps 1 and 2 do not depend on each
other — the verb needs no bench and the bench needs no verb — so the two
largest fronts can proceed in parallel rather than the pipeline stalling
behind recruitment authoring. What is genuinely serial: step 3 needs step
2's verb to derive from, and step 4 needs step 1's identities and step 3's
sources before a ledger has anything true to bank.

## 11. What Not To Build

- **Bond XP.** Shared deployments and repeated heals do not fill a friendship
  bar.
- **Passive stat bonuses.** A relationship changes permissions, obligations or
  verbs, not aim percentages.
- **A second combat meter.** Rating already prices spectacle, and ammo is the
  planned logistics answer to overwatch. Advantage mana would dilute both.
- **Three AP or refund chains.** The current two-AP economy and
  activation-ending attacks stay until an actual verb proves they cannot
  carry the design.
- **A commander exception.** The roster is the protagonist. No mandatory
  Hawks-shaped anchor receives privileged orders or free tempo.
- **A fourth field slot.** Utility earns a place by changing what a turn can
  mean, not by expanding the squad until support becomes affordable.
- **Hidden chemistry.** If a relationship affects a card, the room or card says
  how before the player commits.
- **A generated-person vending machine.** Visual generation is welcome;
  context-free replacement bodies are not.
- **Semantic guesswork over generic commands.** If the record cannot name the
  act, it cannot mint the relationship.

## 12. Acceptance Test For The First Relationship

The first slice is complete when all of this can be demonstrated in one line of
play:

> A named fighter deliberately helps another through an explicit recorded
> verb; the Witness replays that act; a durable source identifies the moment;
> the run banks one named relationship; and the room visibly changes the next
> decision without changing what the yard is allowed to do.

If the source cannot be reopened, it is not provenance. If the next decision
does not change, it is a journal entry. If the yard changes before receiving a
certified snapshot, it is a lie at the door.
