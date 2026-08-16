# The Season Loop — The Roster Is the Protagonist

> **Version:** 0.1
> **Date:** August 10, 2026
> **Status:** Proposal — not yet design-binding
> **Provenance:** drafted from a designer direction ("a Madden Franchise
> mode kind of experience") refined in a three-way design pass (designer,
> Claude, ChatGPT). Builds on `sentinel_circuit_design.md` (Proposal),
> `prototypes/run-core/README.md` (the doctrine pricing this doc argues
> against), and `Sentinel 2D.md` §8 (the safehouse spatial layer this doc
> finally gives a job).

---

## 1. The Thesis

> **The roster is the protagonist. Matches are what happens to it.**

The Circuit stack already built a match loop with unusual integrity: the
card frames it, the yard plays it, the witness certifies it, the run
banks what it **cost** — purse, the mercy ledger, who of yours went
down. But run-core is explicit that its persistence is retrospective:

> A run accumulates the consequences of cards. It does not change what a
> card is.

A season mode turns that history into **pressure on the next decision**.
The reference is Madden Franchise, taken seriously and taken apart: the
thing worth stealing is that between-game state is the actual game and
the matches are its expression. The things not worth stealing are named
in §5.

## 2. The Loop

Four beats. Three exist.

```
        THE CARD ──────► THE YARD ──────► THE SETTLEMENT
           ▲            (the match,          (certified,
           │             recorded)            banked on the run)
           │                                      │
           └────────────── THE ROOM ◄─────────────┘
                    (where the last match
                     becomes the next one)
```

- **THE CARD** (built) — venue, stakes, presence list, tale of the tape.
  The pre-match card is where decisions that shape the match belong; the
  Circuit doc already parks loadout choice here.
- **THE YARD** (built) — the match, played under the rules core,
  recorded as `seed + record`.
- **THE SETTLEMENT** (built) — certified at the edge, banked under the
  run's counting policy, aftermath validated so a page cannot misreport
  what a card cost.
- **THE ROOM** (the gap this doc defines) — not "between matches."
  The room is where the last match **becomes** the next match:

  - someone is visibly injured;
  - someone has new gear hanging off them;
  - there is an empty hook where equipment used to be;
  - there is purse enough for one purchase, not three;
  - a sponsor package sits there asking a question;
  - one fighter probably shouldn't go next time;
  - and the north door produces the next card.

This is not bolting a franchise menu onto SENTINEL. `Sentinel 2D.md`
already designed the safehouse as the spatial anchor with **inventory as
physical presence** — gear on tables, absence carrying information,
"inventory as history, not loot" — and built its first pass. The room is
that plan, finally load-bearing. The acceptance test is design-philosophy
rule 1 turned into level design: **if a season fact is not visible in
the room or on the card, it does not exist.** No spreadsheet mausoleum.

## 3. The Season: A Toured Slate, Not Divisions

The eleven factions must **not** become eleven divisions. Their whole
texture in `sentinel_circuit_design.md` §4 is asymmetric participation —
the Syndicate runs the book, Covenant sanctions, Witnesses record,
Cultivators refuse to host, Architects find the institution vulgar,
Ghost Networks launder identities through it. Flattening eleven opinions
about the institution into eleven sports teams would spend exactly the
thing the Circuit is for.

A season is a **toured slate through faction influence**. Each slate
entry is a card whose meaning is composed from the factions touching it,
not an opponent wearing their jersey:

- a Covenant-sanctioned card (their rules; certain cruelties forbidden)
- a Syndicate-owned venue (their book; finishing pays)
- a Lattice-powered event (their lights; their priority contracts)
- an Ember entrant on neutral ground, because winter was bad
- a card where Witness presence weighs unusually heavily
- a card involving Ghost Network false colors — yours or theirs

The faction is not necessarily who you are playing. It is part of **what
this particular match means.** Venue rulesets as rule variants with
their own golden transcripts are already the Circuit doc's plan; the
slate is how they get scheduled. Authorship follows the twist grammar's
settled law — *the job authors the deck, the drama picks the moment* —
so a slate can be authored (a story season) or dealt (an open one)
without new machinery.

Season end is **closing the run**, which already archives rather than
deletes, and closing is already the player's verb — the same grammar as
the agent's player-initiated endgame. And the season's identity stat is
already built and named: run-core calls the mercy ledger "the run's
actual thesis." A season's headline is not W–L. It is `MERCY · 12
WALKED · 3 FINISHED · 80% HONORED` — the shape of who you have been,
assembled from numbers the edge certified. That is this game's passer
rating.

## 4. Two Tiers, One Boundary

The boundary between the tiers is the same line run-core drew: **what
crosses the door.** Lite never lets roster state cross it. Full makes
crossing it certified.

### Tier 1 — Season-lite (buildable now, no doctrine change)

Roster state affects **whether and when** you field — never what happens
inside a card:

- **Wounds are clocks, counted in slate positions — and passing is
  always legal.** A fighter who went down is recovering; the deal is
  gated while the roster is unfit. What advances the clock is the
  SLATE, not the card: a season may **pass on a slate entry**, and
  passing advances the slate (and every recovery clock) at the entry's
  own cost — the purse not won, the rating not built, the hosting
  faction that noticed you didn't show. Resting the squad is a real
  decision, visible on the card you declined. This is load-bearing:
  clocks counted in *cards dealt* would deadlock — the wound would gate
  the only mechanism that heals it (caught by both review bots on this
  doc's first draft). Never wall-clock — nothing in this stack reads
  the clock, and the season inherits that.
- **Purse spends in the room.** Physical inventory per Sentinel 2D:
  bought gear appears on tables and bodies — **in the flair register,
  mechanically inert by the Circuit's own law.** Gear that carries
  verbs is Tier 2 roster state and waits for the door; a lite purchase
  changes what the squad looks like and what their history shows,
  never what a card resolves.
- **Flair ships fully.** The Circuit's flair register is renderer-only
  by its own law — zero rules impact, determinism untouched by
  construction — so the squad visibly accumulates look and history in
  lite already. Drape and patch stay mechanically inert; the insignia
  slot's claim game is card-side and needs no engine change.
- **Sponsor offers are present and unaccepted.** Sponsorship is leverage
  and leverage is the campaign layer's; in lite the package sits in the
  room asking, which is most of its dramatic job.
- **The slate advances.** Cards carry their faction framing; the run
  banks them; the season has a shape.
- **The venue reaches the eye** *(built 2026-08-16)*. Each slate entry's
  venue is a look the yard dresses for — light, weather, the card's own
  presence list — authored in `world/venues.json` and dealt through the
  door by name. Tier 1 by construction, the FLAIR_SLOTS move applied to
  place: the venue is a declared-inert lens the certificate has no field
  for, and the harness replays one seed at two venues to prove the
  record cannot see the weather. The §3 promise that a card's meaning is
  composed from the factions touching it now has a visible half —
  Covenant ground is cold and sanctioned out loud, the Drain is green
  murk nobody signs. Venue **rulesets** (rule variants with their own
  goldens) remain Tier 2, unbuilt, exactly as §3 parks them.

One deliberate exclusion, and the reason the tier boundary is honest:
**"who" is already rules-level.** Lineup names live in `makeUnits` and
ride the record; fielding a substitute changes what the edge replays.
There is no lite version of benching-with-substitution that doesn't
either lie to the renderer or break the certificate. So in lite, wounds
gate the *deal*, never the *lineup*. Who fights is the canonical squad
at full strength, exactly as run-core's line requires.

### Tier 2 — Full season (the doctrine change)

> **Landed 2026-08-13.** The mechanism argued for below is built and
> binding: see `roster_in_the_match.md` (Status: Current), which is the
> doc this section asked for. Two things it deliberately did NOT do, and
> which this section should not be read as claiming: wounds still do not
> impair (the room deals full strength — that is a design decision, not a
> plumbing one), and the run does not yet own roster state. Both are now
> unblocked rather than blocked.

The dragon, named at its actual size. Not "wounds become modifiers" —
that is one consequence. The change is:

```
the law until 2026-08-13:   seed + record                 = the match
the law since:              seed + roster state + record  = the match
```

**Roster state becomes part of match identity.** The mechanism is a
snapshot with one owner per phase:

- the **run** owns mutable roster state (wounds, gear, lineup);
- the **card** takes an immutable snapshot at the deal;
- the **yard** consumes the snapshot (`restart(seed, roster)`);
- the **witness** receives the *same snapshot*, replays from it, and
  carries its hash in the certificate and the content address **as its
  own field, deliberately NOT folded into the rules stamp** — the stamp
  stays the behavioral version of the rules alone. run-core reports
  stamp drift as a rules boundary, and a wound is not a rules
  deployment; conflating the two would mark ordinary season progression
  as drift on every card (caught in review of this doc's first draft);
- nobody reinterprets it afterward.

This is the seam's existing distrust philosophy — matching seeds,
replaying records, validating aftermath, refusing malformed claims —
extended by exactly one certified input. The witness does not trust the
room; it witnesses one more thing.

run-core's price list is the checklist, including its fourth item, which
the snapshot answers: *what does a filed record mean when two players
play the same seed with different squads?* It means what it says — the
roster is in the content address, so a record individuates by what
actually fought. The archive stays honest by construction, the same way
`POST /file`'s idempotent keys already work.

**What wakes up on the far side:** everything §6 of the Circuit doc
designed and gated — gear slots carrying verbs and geometry, primary
ammo and the sidearm floor, sponsor rigs as leverage physically mounted
on a torso, lineup choice against a known opponent as the tale of the
tape, wounded fighters fielded impaired or benched for real. None of
those need individual holes punched through determinism; they are all
just roster state, snapshotted and certified.

## 5. What Not to Take from Madden

- **The menu lasagna.** Rule 1 as level design, per §2. The room is the
  interface.
- **Stat inflation.** Gear is verbs and access, never `+3.7%` — already
  law in Circuit §6, inherited whole.
- **Fake busywork.** No staff meetings, no training sliders. SENTINEL's
  between-match decisions are the campaign layer's own currencies —
  leverage, favors, standing, disposition — with the room as their
  surface.
- **Symmetric league fiction.** No divisions; see §3.

## 6. Open Questions

1. **Slate authorship.** Fixed authored seasons, dealt open seasons, or
   both (a story slate that opens up after its arc)? Current lean: both,
   because the twist grammar already separates deck authorship from
   moment selection.
2. **Recovery economics.** How many cards does a wound cost, and does
   purse buy it down (a cutman is already a favor in the Circuit doc)?
   Numbers want the lite prototype, not this doc.
3. **Roster growth.** New citizens via the D1 compositor path is priced
   art-side (~a head and a palette entry, plus the verb ladders); what
   is it priced story-side — recruiting as a job type? A Convergence
   sponsorship with strings?
4. **Death vs. downed.** Does a fighter lost on a finished card leave
   the roster for the season, forever, or by venue rules? Interacts
   directly with Circuit open question 2 (lethality default) and should
   be settled with it — leaning: the roster consequence follows the
   venue's law, so a Covenant card and a Syndicate card risk different
   things, which is the sport feeling different again.
5. **Season length.** Fixed slate size vs. close-when-you-choose.
   Leaning: the run already closes by choice; a slate gives it shape
   without forcing the ending — endgame stays player-initiated.

## 7. Build Order

1. **Season-lite** — the room-as-front-office loop: slate data on the
   card, wounds as deal-gating clocks in run-core's grammar (a new
   consequence it is allowed to bank), purse spending, physical gear in
   the flair register, sponsor offers present. No engine change; the
   harnesses grow the room-management claims.
2. **The doctrine PR** — `seed + roster state + record = match`, argued
   on its own, priced against run-core's checklist, landing
   `restart(seed, roster)`, the certify/file body change, and the
   stamp/address fold in one reviewed change.
3. **Wake §6** — gear verbs, ammo, sponsor rigs, lineup choice, wound
   effects, each as rule variants under golden transcripts, now that
   they are all just roster state.

Lite is the migration path, not a compromise: it builds the entire
Room → Card management loop and its surfaces while the combat engine
keeps its current law, and when the doctrine lands, the sleeping half of
the system wakes up already housed.
