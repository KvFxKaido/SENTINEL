# prototypes

Playable prototypes of the universe's combat layers.

The squad layer: one tactical encounter — Kestrel Yard — that feels good
enough to replay twice. One rules layer, two renderers, one test suite.

```
tactical-core/   rules: rng, LOS, cover, firing solutions, movement, AI
                 no DOM — runs under `node --test`, guarded in CI
run-core/        the run: what survives the door. Banks what a card COST
                 — purse, mercy, wounds — and never what a card IS.
                 No DOM, no rules import; `node --test`, guarded in CI
tactical/        2D canvas renderer (immediate-mode, pixel sprites)
tactical3d/      three.js renderer (retained-mode, 2:1 isometric)
walkable/        walkable interior (COURT 01): one room, one body, and a
                 north door that hands the feed to tactical3d and takes
                 the outcome back — the seam
```

Three modules, three walls. `tactical-core` is trustworthy because it has
no host; `run-core` is safe because it holds no rules; `walkable` stays
honest because it can still not compute an outcome. The renderers are the
only things that know about all of it.

## The seam

`walkable/` and `tactical3d/` meet at a door, not a shared state. Crossing
the walkable room's north door loads tactical3d in an iframe with a seed
AND a roster the room dealt (`?seam=1&seed=…&roster=VESPER:10,…` — since
the doctrine change, `seed + roster + record IS the match`); when the
player walks out, the yard posts back `{seed, roster, record, result,
rating, purse, ledger, down, fingerprint}` and the iframe is torn down.
The overworld never watches combat happen — and it
does not trust what it is told: the returned seed AND squad must match
what was dealt, malformed payloads are refused, and the witness Worker's replay of
the record settles the run (certified / disputed-and-struck /
unreachable-but-labeled). The aftermath rides home beside the outcome
because the run banks what a card *cost*: `ledger` is the same
walked/finished/lost the certificate carries, so the edge checks it, and
`down` names your dead — the yard's own word, agreeing with its own count.
Both ends of that are on a deadline: the cut
holds until the yard proves it booted, with a timeout and ESC abort, and
the certify request has its own, so an edge that accepts and never answers
is *unreachable* too rather than a ledger stuck mid-settlement. Neither a
dead far side nor a dead witness traps the room. One crossing buys
exactly one card:
in seam mode the yard's own re-deal verbs (R / shift+R) are disabled,
because dealing is the world's move.

## The run

What survives the door, and the reason to cross it twice. The room's
session ledger became a **run** (2026-08-04): purse, the mercy ledger, and
who went down now outlive the tab, in `localStorage`, under
[`run-core/`](run-core/).

The run banks what a card **cost**. It now also owns four stable people,
their authored recruitment origins, and the three-person lineup chosen from
them; the selected three still fight at full strength. That used to be
forced to the canonical trio: `seed + record IS the match` was what let the
witness certify anything at all. Since the doctrine change
(`architecture/roster_in_the_match.md`, 2026-08-13) the law is **seed +
roster + record**, the squad crosses the door as a certified input, and
since the faction door (2026-08-16) the run may substitute its authored
fourth person before the deal. Stable ids and origins remain in the room;
the yard still receives only `{name, hp}` times three. Carrying a wound into
the next card remains a design decision rather than an impossibility.

Nothing is silently migrated or dropped: a stored run this schema cannot
read is *moved aside*, a fresh one opens, and the panel says so. A room
that cannot persist at all still plays, and says the run will not survive
the page. `Shift`+`N` closes a run and archives it — refusing if it cannot
archive, and refusing while a card is still settling at the edge, because
a card in flight belongs to the run that dealt it.

Since the front office (2026-08-11) a fresh run opens on the **house
slate** and is a season (`architecture/circuit_season_loop.md`, Tier 1):
an authored tour with faction framing, wounds as recovery clocks counted
in slate positions, and passing — `Shift`+`P` — always legal precisely
because the clocks gate the deal. The panel says where the tour stands,
what the next entry means, and why the door would refuse to deal; the
cut card frames each crossing from the run's **own** slate. Nothing that
a replay would notice crosses the seam — the yard is dealt exactly the
match it was always dealt. A stored plain run stays plain; a stored
season keeps its own slate even if the house slate has since changed.

And since the venue lens (2026-08-16) a season crossing also deals its
entry's **venue name** (`&venue=THE COLD COURT`) — the one deliberately
inert input. The yard dresses for it out of `world/venues.json`: light
color, weather in the air, the card's venue lines — and nothing else.
The certificate cannot see a venue (there is no field for one), and the
harness replays the same seed at two venues and asserts the certified
text is byte-identical while the stages visibly are not
(`test_yard_venue.mjs`). The asymmetry with `?roster=` is the law in
miniature: a malformed roster **faults** because fielding a guessed
squad would certify a match nobody dealt, while a venue the atlas has
never heard of gets the house look and *says so* — a lens must never
decide whether the match exists. A typo'd venue in the authored house
slate still faults, but in the ROOM at boot, where authoring mistakes
belong. A plain run deals no venue and the yard is its own ground.

And since the kit table (2026-08-13) the purse **spends**. A prop against
the south wall — the opposite pole from the north door — sells flair, and
only flair: run-core's `FLAIR_SLOTS` is drape and patch, the two slots the
Circuit's gear table calls mechanically inert, so the shop cannot stock a
verb even by accident. Standing at the table opens it (`1`–`4` buy, `Z`
chooses who wears it); walking away closes it. Purchases are permanent,
one slot per fighter, and each one is stamped with where on the tour it
happened — unless the tour is already over, when there is nothing left to
stamp it with. Purse stays what the season *won* and the balance is what is
left of it, because one number cannot honestly say both. The rack on the
table is the physical half — one hook per fighter per slot, in the
panel's stated order — and the empty hooks are the point: absence carries
information. What the room does **not** do is put the hood on the body;
drape and patch become sprite layers when the gear pipeline says so, and
tinting a composed sheet to fake one would be the renderer claiming a
pixel nobody authored. Nothing bought crosses the seam — the round-trip
harness deals a card from a dressed room and asserts the yard's URL is
byte-identical to the bare room's.

And since the people layer (2026-08-15) the room has **someone in it**.
`world/people/<id>.json` declares a person: a name, a place to stand, a
body to wear, and — the part that makes it a seam rather than more set
dressing — a **faction and an archetype the campaign already authors**.
The archetype is resolved out of
`sentinel-campaign/.../factions/<faction>.json` at boot, not copied, so
editing the Syndicate's Broker edits who keeps the kit table. A person
claiming a role the faction does not have is a boot fault naming the
roles it does have; so is an unknown faction, an undrawable body, or a
file that disagrees with the index. VANCE keeps the table, and the shop
says so in the campaign's own words. This is
`architecture/unauthored_history.md`'s first seam: the campaign had NPCs
with no bodies and the room had bodies with no people.

Since the convergence (2026-08-01) the same **body** crosses too. Both
surfaces load the molded pack sheets from `assets/sprites/<fighter>/`, so
a fighter does not change species at the door — which is also why the
yard now serves from the repo root and faults explicitly rather than
falling back when a sheet is missing. `test_seam_round_trip.mjs` walks
the whole thing with both surfaces alive at once.

And the 1v1 layer: `close-contact/` — the SENTINEL: Close Contact
fighting prototype (Godot 4.5, limb-mapped inputs, active defense). See
its own README; the rest of this file is about the tactical slice.

## Run it

The yard now consumes molded fighter sheets from `assets/`, and the walkable
room crosses directly into it. Serve both from the **repo root** so the shared
rules, sheets, and seam all resolve under one origin:

```sh
python -m http.server 8080
```

- 2D → <http://localhost:8080/prototypes/tactical/>
- 3D → <http://localhost:8080/prototypes/tactical3d/>
- walkable seam → <http://localhost:8080/prototypes/walkable/>

Or double-click `tactical3d/serve.cmd`, which does both and opens a browser.

Append `?seed=deadbeef` to pin a specific encounter.

Both world surfaces load regenerated sheets from `assets/` (see
`scripts/roster_mold.py`). A second port is optional, not a different serving
contract:

```sh
python -m http.server 8082          # at the repo root
```

then <http://localhost:8082/prototypes/walkable/>. Append `?deal=6` to pin
the seed its door deals; `?witness=…` passes through to the yard.

## Run the tests

```sh
cd prototypes/tactical-core && node --test        # the rules, with goldens

cd prototypes/walkable/test                       # the room
npm install && npx playwright install chromium
node test_walkable_verbs.mjs
python test_roster_sweep.py

cd prototypes/tactical3d/test                     # the yard, and the door
npm install
node test_yard_bodies.mjs
node test_seam_round_trip.mjs
node test_witness_deadline.mjs
```

All of it runs in CI. The browser suites drive **synthetic sheets** at the
pack's real geometry from one shared generator, so no licensed pack is
needed and the two surfaces cannot drift onto different fixtures — they
field the same bodies now, and the fixtures say so.

## Why two renderers

Not indecision. Two renderers over one rules module is the cheapest ongoing
proof that the rules really are renderer-agnostic — if a rule ever leaks into
a renderer, the other one breaks and says so. They also make the immediate-mode
vs retained-mode contrast concrete, which is the whole reason the 3D port was
worth doing as a learning exercise.

If one of them stops earning its keep, delete it. Do not let them drift.

## Neither of these is the game

No campaign, no classes, no research tree, no soldier whose death ruins your
evening. This is a recognizable genre chassis to argue with. The questions
that would make it SENTINEL rather than XCOM-flavoured come after the chassis
proves itself:

- What if turns are simultaneous?
- What if cover degrades?
- What if missed shots alter the map?
- What if **social energy** is the morale system — depletion, not death, ends fights?
- What if positioning creates team abilities instead of aim bonuses?
- ~~What if hostiles surrender, and what you do next is a **hinge moment**?~~
  **Built.** Hostiles yield on morale, and the spare/finish call is the
  match's last move (Circuit roadmap step 1 — see `tactical-core/`).

That one was where this stopped being a clone. Depletion-not-death now exists
for hostiles; whether it becomes **social energy** on the player's side is
still open.
