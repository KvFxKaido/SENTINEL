# Walkable World Prototype

One room, one walking character, four owned people — and one door that is
somewhere else's problem. This is a pure three.js renderer toy: no game
rules and no `tactical-core` import. Its Witness calls file what the yard
reports back through the seam and let the room reopen a certified event's
archived source (below).

Cipher walks inside a voxel-extruded Kestrel interior while VESPER, KOA,
SABLE, and the benched NIX stand as non-colliding bodies. The room reuses `tactical3d/`'s
terrain density, Y-billboard, quarter-turn camera, lighting discipline, blob
shadow, and LCD display pass so the audition is against the same visual
machinery rather than a friendly mock.

## Run it

Serve the **repository root**:

```powershell
cd C:\dev\SENTINEL
python -m http.server 8082
```

Then open <http://localhost:8082/prototypes/walkable/>.

The root matters. Room sheets load from
`../../assets/sprites/composed/<fighter>/`, which only resolves correctly
when the page is served in repository context. The ES-module import also
means this page does not run from `file://`.

## Controls

| Input | Action |
|-------|--------|
| `WASD` / arrows | walk, camera-relative |
| `Shift` + move | run |
| `L` | dash, current facing |
| `H` | heal channel |
| `G` | hurt flinch |
| `X` | down — any move key rises |
| `R` hold | aim — emitter up |
| `F` | fire |
| `C` hold | kneel |
| `Q` / `E` | orbit the room 90° |
| `P` | cycle LCD / crunch / clean |
| `Shift` + `N` | close the run, open a fresh one |
| `Shift` + `P` | plain-pass the current slate entry |
| `B` | rotate the bench before the next deal |

`J` and `K` swung the pack's sword until 2026-08-02 and are gone. No rule
ever consulted them: `tactical-core` models overwatch, shot, cover and
line of sight and contains no melee concept at all, and the yard's own
verb table never registered an attack. They were art with nothing behind
them, so the body that ships has no blade and the keys that swung it are
retired rather than left bound to nothing.

The **walk is the default gait** (2026-08-14) and `Shift` holds the run.
It was the other way round until the designer walked the room and said
the run cycle reads goofy at 1× — a nit on the record since the yard's
pre-merge walk-through, priced there at a ~4-generation re-roll. Swapping
which cycle a bare press gets cost none. Both strips were always authored
and both still play, and the **speed travels with the verb**: a walk
cycle carried at run pace would be the renderer lying about the gait.

The yard keeps the run, and not by omission — `tactical-core` exposes
each path step for 70ms, so a unit crosses a tile in a fourteenth of a
second and a walk cycle there would skate. This room is the only surface
with a gait to choose.

`R` and `C` are **stances**: held, not triggered, and standing-only.
There are no aim-walk or crouch-walk sheets, so moving takes the body
out of a stance rather than playing one over a moving body — releasing
the key, or stopping again, puts it back. Holding both is a real thing a
player does, so the tie is decided rather than left to key order: aim
wins, because aim is the stance with a verb attached to it. `F` fires
from anywhere, and because the shot begins and ends in the aim pose it
reads standalone *and* falls back into a held aim without a seam.

`Shift`+`N` closes the run — the panel's only destructive verb, so it
does not destroy what it cannot preserve. It archives first and opens a
fresh run only if the archive actually took (read back, not assumed), and
it refuses outright while a card is still settling at the edge: a card in
flight belongs to the run that dealt it, and closing mid-settlement used
to archive the run *without* its final card and then bank that card onto
the fresh one.

The run owns a four-person roster loaded from
`world/recruitment/court-01.json`: stable person ids, tactical names, bodies,
and authored origins. Exactly three ids are fielded. `B` rotates the one-person
bench and the panel shows the selected tactical names before commitment, plus
the benched person's source and reason for entering. The north door receives
only the existing certified `{name, hp}` × 3 snapshot. NIX is the first faction
entrance — an Ember Colonies defender sent because winter was bad — and
explicitly borrows SYN's tracked canvas until original art exists. That loan is
authored data and a registered yard mapping, never a missing-asset fallback.

The north doorway is **live**: walking through it is the seam — and the
dash moves through the same collision and door machinery, so dashing the
doorway deals the card too. On the full roster, walking back out of a
**lost** card plays the hurt flinch: the record comes back with you, and
it shows.

## The seam

Crossing the north door hands the feed to `tactical3d/` in a fullscreen
iframe with a seed this room dealt (`?seam=1&seed=…`). The yard plays
exactly one card — its own re-deal verbs are disabled in seam mode — and
when you take **WALK BACK OUT** on the post-match overlay, it posts
`{seed, roster, record, result, rating, purse, ledger, down, derivedEvents,
fingerprint}` home and the frame is torn down. You return standing just inside
the walls; walking the door again deals a fresh card.

`ledger` and `down` are the **aftermath** — walked / finished / lost, and
the names of your dead. They ride home because the run banks what a card
cost, and cost is not in the yard's `end` event. The counts are the same
three the witness certificate carries, so the edge checks them; the names
are the yard's own word and must at least agree with its own count.

The four owned room bodies show only looping `IDLE` or `KNEEL`. The newest entry
in `run.recent` whose certificate is not `struck` owns the visible aftermath:
an operative kneels if and only if that entry names them in `down`. A fresh
run, or one containing only struck cards, leaves everybody idle. `run.wounds`
is cumulative history and stays in the panel; using it for posture would imply
a persistent injury the next canonical full-strength card does not have.

The room does not take the yard's word for it:

- the returned **seed must match the one it dealt**, and the payload must
  be shaped like a replayable record — anything else is refused;
- the record is sent to the witness Worker, whose **replay settles the
  run**: `CERTIFIED AT THE EDGE`; `EDGE DISPUTES THE FEED — STRUCK` for
  a genuine 422 replay/rules dispute (struck cards never count); or a
  specifically labelled `COUNTED UNWITNESSED` verdict for unreachable,
  500, 507, or incomplete protocol/infrastructure outcomes. A full archive
  says `CERTIFIED BUT NOT ARCHIVED — COUNTED UNWITNESSED · THE ARCHIVE IS
  FULL`. A 400 remains a caller bug and the run refuses it rather than
  recasting it as either a dispute or an unwitnessed card.
  On that certified path the Worker's own replay authors `derivedEvents`;
  the room never asks the page to prove its own derivation. The aftermath is
  checked the same way the outcome always was: a page
  that misreports what a card cost is struck, not banked;
- a returned record carrying `CUT THE FEED` is sent to neither `/certify`
  nor `/file`. The room calls it `dark`, not `unwitnessed`, at banking time.
  Every counted dark or accidentally unwitnessed card appends its full
  `seed + roster + record`, claimed events (including an empty array) and
  aftermath to the independent local chronicle. When the yard returned
  derived events, run-core receives the returned `{logId,key}` only after that
  append survives; only then may the event and relationship bank at claim
  grade;
- the hand-off has a readiness handshake: the cut card holds until the
  yard proves it booted, with a 7s timeout and an <kbd>ESC</kbd> abort
  that put you back in the room if the far side never answers;
- the file-and-certify request has a deadline of its own (8s). A witness that
  refuses was always labelled `NO WITNESS REACHABLE`; a witness that
  *accepts and never answers* used to leave the ledger at `ASKING THE
  EDGE…` forever. A hang is unreachable too, and the room says so and
  counts the card (caught in review — this room guarded a dead yard
  behind the door and was not guarding a dead edge in front of it).

Query params: `?deal=6` pins the seed the door deals (the same
pin-a-board move as tactical3d's `?seed=`); `?witness=http://localhost:8787`
passes through to the yard and is used for filing here.

### Recorded seam decision — 2026-08-16, durable-moment step 3

**THE ROOM FILES WHAT IT CERTIFIES.** The certified seam path submits the
returned record to `POST /file`, not bare `/certify`. `/file` performs the same
replay certification and archives idempotently by the record's content key, so
every card the room calls certified has the filed match id required for a
resolvable origin. This is a recorded implementation decision for designer
review. Deliberate darkness composes with it by submitting to neither
endpoint; run schema v7 counts that card as `dark`, separately from the
accidental `unwitnessed` family.

On a successful filing, the card banks only the Worker's replay-authored
`derivedEvents` and its returned id. The yard-computed array crosses the seam
for immediate in-session display, but never enters the run ledger. The two
arrays are not adversarially compared because the certified path does not
accept the page as an author at all.

A filed certificate that lacks `derivedEvents` is counted unwitnessed with an
explicit incomplete-attestation verdict. Like unreachable, 500 and 507, it
may bank the yard's event only as a logged claim — never as certification.

Run schema v7 translates each event's tactical actor and beneficiary through
the fielded lineup at banking time and records the author explicitly. A
certified extraction carries `grade:"certified"` with filed
`{matchId,commandIndex}` and offers **BACK TO FILE**. A dark or accidentally
unwitnessed extraction carries `grade:"claim"` with local
`{logId,commandIndex,key}` and offers **BACK TO LOG**. Both source paths use the
same raw-record view without importing replay rules. A missing, malformed, or
content-mismatched claim target says **THE SOURCE DOES NOT RESOLVE** rather
than crashing, silently hiding the entry, or opening the wrong match.

### Recorded integrity decisions — 2026-08-18, step 5

**WHO VOUCHES IS THE GRADE.** Certified events are authored by the Worker's
replay. Claim events are the squad's word: the yard rules core computed them
in its completed session, but the room does not replay and therefore cannot
promote them. A forged seam post can bank a falsifiable claim for something
its preserved record disproves; it can never bank certification.

**NO POINTER BEFORE ITS TARGET SURVIVES.** The local chronicle is append-only,
independent of RUN_V, run close and run orphaning, and capped at 200 entries.
On every counted uncertified card, the room appends the full match first and
banks the card second. When the card has yard-derived events, it maps the
returned `{id,key}` to the `{logId,key}` reference run-core needs to bank claim
events and mint relationships; an event-less card receives no origin and says
its record was kept with nothing to bank. A full, blocked or damaged log still
banks purse, wounds, mercy and slate movement, but the panel says **THE LOG IS
FULL — NOTHING KEPT** (or names the other refusal) and no event or debt appears.
A struck 422 logs and mints nothing.

**GRADES ARE NOT POWER TIERS.** `OWES A LIFE` records the same grade and origin
as its extraction. One active debt per directed pair spans grades, and
**REPAY THE LIFE** has identical recovery and fulfillment semantics for a
claim or a certificate. The panel names `CHOSE THE DARK` separately from
`LOST THE FEED`, renders the split counters, and names the squad's word beside
each local log address.

### Recorded relationship decisions — 2026-08-17, pairwise-ledger step 4

These two implementation decisions are recorded for designer veto at review:

1. **THE FIRST NAMED RELATIONSHIP IS OWES A LIFE.** On the certified filed
   path, run schema v6 consumes the Worker's `extraction` event and mints the
   directional fact beneficiary owes actor a life. Repeated rescues do not
   replace an active debt's first source. The run panel names both people,
   shows `ACTIVE` or `FULFILLED`, keeps the mint and repayment slate stamps,
   and retains **BACK TO FILE `{matchId}` / COMMAND `{commandIndex}`** after
   fulfillment. The existing archived-source view follows that pointer and
   exposes the raw drag command.
2. **THE FIRST OBLIGATION IS THE DEDICATED PASS — REPAY THE LIFE.** Every live
   slate stop shows its plain pass explicitly. When and only when an active
   debt's named creditor has a running recovery clock, a second button appears
   beside it: **PASS — KOA REPAYS THE LIFE: SABLE RECOVERS 2** (with the owned
   names for that pair). Committing it advances that creditor by two, every
   other clock by one, and fulfills the debt at that pass's slate stamp. When
   either gate is false the dedicated option is absent, not mysteriously
   disabled; the plain pass never disappears while a stop remains.

Step 5 extends both decisions across provenance grades without replacing
them: claim events mint the same directional fact, a live debt in either
grade blocks another for that directed pair, and repayment neither weakens
nor strengthens because the source is local.

This remains entirely on the run/room side of the door. Neither relationship
state nor the dedication enters the yard, changes `{name, hp}`, touches the
certified snapshot, moves combat arithmetic, or spends purse. The shop remains
flair-only by construction.

On a season the door also deals the current entry's venue name
(`&venue=…`) — renderer flavor the yard dresses for out of
`world/venues.json`, never a certified input (the seam section of
`prototypes/README.md` owns the law). The room checks at boot that every
venue the HOUSE slate stages exists in that atlas, so an authoring typo
faults in the front office instead of surfacing as "UNRECORDED GROUND"
mid-crossing; stored seasons are deliberately not gated — a save never
bricks over a look. The room also keeps its own air now: dust hanging in
the sodium key, authored beside the light it hangs in, cosmetic and
room-owned (`dataset.air`).

## Room body assets

The local sheets are regenerable artifacts and are intentionally untracked.
If they are missing, the page stops at an explicit asset message instead of
substituting a placeholder:

```powershell
python scripts/roster_mold.py     # licensed pack -> assets/sprites/<fighter>/
python scripts/compose_body.py --gen assets/original/cipher `
                               --src assets/sprites/cipher `
                               --out <frames> --verbs IDLE RUN WALK AIM FIRE `
                                                     HURT DEATH HEAL KNEEL DASH
# then scripts/pack_strip.py each frame dir -> assets/sprites/composed/cipher/
# repeat compose + pack for VESPER / KOA / SABLE; this room reads IDLE / KNEEL
```

Three stages, and this page reads the last one: `assets/sprites/composed/`,
the mold's body with the generated head composed in and the sword stripped
(the walk-off verdict, 2026-08-02 — see `architecture/art_direction_gba_tactics.md`).
The licensed source pack must be present locally at
`assets/packs/FULL_Adventurer 2D Pixel Art/`; the FREE pack cannot serve this
page at all, because composing needs the synthesized AIM / FIRE / KNEEL that
only the full pack's mold produces. Frame counts are read from sheet width,
never assumed: the pack varies them per verb (heal runs 12 frames, hurt 4,
and synthesized kneel 2).

On the full pack the mold also **synthesizes** three verbs the pack does
not ship — `AIM`, `FIRE`, `KNEEL`, 12 more sheets — so a molded fighter
carries 48. Compose then drops the two ATTACK verbs (no rule consults
them), which is why what this page actually reads is 40 sheets per
fighter, not 48: the mold and the composed body are different stages and
count differently. They are ordinary sheets on the same canvas; nothing
in this page knows the difference. What makes them the pack's own rather than
imported: aim lifts the HEAL draw (the frame where the held object sits
at the chest, hand already closed on it) and replaces the vial with the
emitter, so the grip is still the pack artist's; the emitter's charge and
its muzzle bloom are drawn in the pack's heal greens, which the mold
already swaps to each fighter's mark color; and the housing is drawn in
the pack's steels, which the blade pass already sheathes on any
non-attack sheet. **Aiming shows cold steel; only the shot lights** —
the blade's law, read onto a barrel. Kneel is row surgery on IDLE: the
torso is copied down, the boots never move, and the coat hem flares a
pixel, because on a body in a long coat the height loss alone read as a
shorter man rather than a crouching one.

The room gate is stated, never guessed at, and it is ONE tier: Cipher needs
all ten verbs and four facings (40 sheets); VESPER, KOA, SABLE, and the SYN
canvas loaned to NIX need only `IDLE` and `KNEEL` in four facings (32 more).
Loading the squad's other eight verbs here would spend the north seam's
seven-second boot budget on poses the room never plays. All 72 unique required
sheets load and the panel reads
**COMPOSED / READY**, or the room faults.

- every required sheet loads → **COMPOSED / READY**;
- any sheet missing → an explicit fault naming the count and the first
  casualty, pointing at all three regeneration stages;
- a sheet that exists but fails geometry faults on its own message, because
  rejection and absence are different verdicts.

The old CORE/FULL split went away with the blade. It distinguished a
free-pack four-verb body from a full-pack nine-verb one, and the composed
body has no free-pack form — so a reduced roster is always a broken
regeneration, and reporting it as a healthy state would be the silent
fallback this gate exists to prevent.

These bodies are **canon**. The walk-off (2026-07-31, `walkoff.html` — both
bodies fielded in this room on one input) decided the two questions this
room carried: the pack format beat the 32×32 body-law canvas, and the
selout dialect won with it. The verdict and its costs are recorded in
the body law's successor section,
`architecture/art_direction_gba_tactics.md`.

## Tests

`test/` holds the headless harness that guards this page's claims — the
"caught in test" comments in `index.html` point at it:

```sh
cd prototypes/walkable/test
npm install                        # the playwright library
npx playwright install chromium    # the browser itself (skip if one is provisioned)
node test_walkable_verbs.mjs       # verbs, stances, light, roster faults, regressions
python test_roster_sweep.py        # the roster mold's remold sweep (pillow + numpy)
```

What it does and deliberately does not touch:

- The browser harness drives the page against **synthetic sheets** at the
  pack's real geometry (no licensed pack needed), measuring verb
  durations in-page against per-sheet frame counts. Real composed sheets
  for Cipher, VESPER, KOA and SABLE are backed up before the run and
  restored after.
- The same harness carries §12's first-relationship acceptance sentence at
  both grades. The certified golden DRAG resolves FILE command 6. Its faithful
  dark parallel logs the full match before banking, resolves LOG command 7,
  mints claim-grade `OWES A LIFE`, repays with the same two-stop recovery, and
  survives reload. The accident family logs a lost-feed claim; a 422 logs
  nothing; a 200-entry full log banks the card but no event or debt and names
  the refusal; removing a claim target renders **THE SOURCE DOES NOT
  RESOLVE**. Separate negatives still prove no dedication without a debt or
  with a fit creditor, while the plain pass remains offered.
- The mold test runs the actual `scripts/roster_mold.py` twice against
  fake packs — **fully sandboxed in a temp dir** via the mold's
  `ROSTER_MOLD_PACKS` / `ROSTER_MOLD_OUT` test hooks, so the real
  licensed packs and molded outputs are never touched. On synthetic
  input the pinned cipher golden is EXPECTED to fire; the test asserts
  that it does.

Two claims are split deliberately across the suites, because neither
runner can see the whole thing. The room's `FIRE_SPILL` curve must light
exactly the frames that carry a muzzle bloom — but headless rAF runs
around 5fps against a 500ms sheet, so the browser can only ever observe
a couple of frames (and the phase cannot be walked: `locked.started` is
stamped on the verb's first *rendered* frame, so delaying the keypress
shifts nothing). So the browser asserts light-per-frame on whatever it
catches, refusing to pass if it caught too little; the Python suite
asserts the other half — that the bloom really is drawn on frames 1–3 —
where every frame is visible.

Both run in CI (`walkable-harness` job), alongside the yard's two suites —
including `prototypes/tactical3d/test/test_seam_round_trip.mjs`, which
walks this room's north door, plays the card, and reads the verdict this
room settles on. The seam round trip **is** covered now; it stopped being
somebody else's problem when the yard started fielding these same bodies.

Not covered: anything about how the sheets *look* — pixels are judged by
walking, not asserted.

One thing about looks *is* worth measuring, because eyes lie about scale:
the count of mark-colour pixels a verb lights at its peak. The shipped
verbs run blade ignition 706 and heal channel 38; the muzzle bloom's
first cut peaked at 21, which on a ~34px body drawn ~28px tall is a
flicker rather than a gunshot. It was resized against those numbers, not
against a zoomed contact sheet where everything reads fine:

```sh
python - <<'PY'
from PIL import Image; import numpy as np, os
R, E = 'assets/sprites/cipher', [(0xea,0xff,0xff),(0xa5,0xec,0xff),(0x5c,0xcf,0xff),(0x21,0x96,0xd8),(0x1d,0x7f,0xc0)]
for rel in ['ATTACK 1/attack1_right.png','HEAL/heal_right.png','FIRE/fire_right.png']:
    a = np.array(Image.open(os.path.join(R, rel)).convert('RGBA'))
    pk = [int(sum(((f[:,:,0]==c[0])&(f[:,:,1]==c[1])&(f[:,:,2]==c[2])&(f[:,:,3]>0)).sum() for c in E))
          for f in (a[:, i*96:(i+1)*96] for i in range(a.shape[1]//96))]
    print(f'{rel:26} peak={max(pk)}')
PY
```
