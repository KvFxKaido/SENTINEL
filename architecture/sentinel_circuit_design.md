# The Circuit — Sanctioned Combat in SENTINEL

> **Version:** 0.2 (Design exploration)
> **Date:** July 27, 2026
> **Status:** Proposal — not yet design-binding
> **Prototype:** `prototypes/tactical/` + `prototypes/tactical3d/` over the
> shared `prototypes/tactical-core/` rules module (#56/#57, #60)
> **Changes in 0.2:** adds §6 — loot, cosmetics, and false colors

---

## 1. The Problem

SENTINEL is a game about choices, consequences, and integrity under pressure.
The tactical prototype is a game about shooting three hostiles in a rail yard.
Both are good. They do not obviously belong to the same game.

If tactical combat becomes a core loop the naive way — the world is dangerous,
missions are firefights — it corrodes everything the rest of the repo is built
on. A world where every job resolves at gunpoint is a world where avoidance,
leverage, disposition, and hinge moments are decoration. Combat would not just
sit beside the choice systems; it would out-compete them.

The reconciliation is not to nerf combat. It is to give combat an **address**.

## 2. The Thesis

> Combat in SENTINEL is an institution, not a state of the world.

The Circuit is sanctioned, witnessed, wagered-on combat: a formalized way for
factions to settle disputes, for the desperate to convert risk into standing,
and for a fractured world to keep its violence somewhere it can see it.
Nobody can afford a real war. The Circuit is the pressure valve — half
bloodsport economy, half diplomatic institution, streamed over salvaged
networks to anyone with a working screen.

It is barbaric, and it is the thing preventing something worse. Both are true.
The game never tells you which truth wins. That is the SENTINEL move.

### Tone: institution, not satire

The obvious reference (Showgunners, The Running Man) is broadcast-death-show
satire: garish, winking, primetime. That register fights the project's
commitments — *reflection over spectacle, aftermath over action* (see
`Sentinel 2D.md`). The Circuit is the darker, quieter version:

- Not a glittering arena — a cleared rail yard, a drained reservoir, a
  pre-collapse mall with the storefronts welded shut
- Not celebrity hosts — Witness recorders on tripods and a Syndicate
  oddsmaker with a ledger
- Not a cheering audience — people watching a flickering feed because the
  outcome decides their water rights
- The spectacle exists, but the game's camera stays interested in what it
  costs the people inside it

## 3. What the Frame Resolves (for free)

| Prototype artifact | Naive reading | Circuit reading |
|---|---|---|
| Win / lose / restart | Gamey abstraction | Rematches, brackets, seasons |
| Replay same seed | Debug feature | Rewatching the episode; disputing a ruling |
| Visible hit %, firing solutions | HUD | Broadcast overlay — what the audience sees |
| CRT / scanline aesthetic | Style choice | You are literally watching the feed |
| AI GM narrating combat | Voice from nowhere | The **showrunner** — an entity that wants drama, plays favorites, injects twists |
| Death | Squad-wipe = reload | Elimination is the norm; *lethality is a choice with witnesses* |

The last two rows are the important ones. The showrunner gives the AI GM a
diegetic seat at the table during tactical play. And containing death inside
an institution means killing is never mechanically required — it is always a
decision someone watched you make.

## 4. Eleven Factions, Eleven Opinions

The Circuit is a competing-truths engine. Nobody is neutral about it:

| Faction | Reads the Circuit as | Involvement |
|---|---|---|
| Steel Syndicate | A market | Runs the book, brokers matches, owns venues |
| Nexus | A dataset | Ratings, prediction markets, audience metrics |
| Witnesses | A record | Official recorders; their footage is the legal truth of a match |
| Covenant | An oath-bound dueling law | Sanctions matches, enforces terms, forbids certain cruelties |
| Convergence | A recruiting floor | Sponsors fighters with enhancement packages |
| Lattice | Logistics | Powers venues, moves crowds; paid in priority contracts |
| Wanderers | News | Carry results and legends between regions |
| Cultivators | A tragedy with useful side effects | Refuse to host; sell to the crowds anyway |
| Ember Colonies | Proof the world hasn't healed | Condemn it; quietly enter fighters when winter is bad |
| Architects | A degraded copy of pre-collapse sport | Hold the archives that prove it; find it vulgar |
| Ghost Networks | An identity laundry | A dead fighter is a clean exit; a masked one is anyone |

A match is never just a match. It is a Syndicate revenue event, a Nexus data
harvest, a Covenant legal proceeding, and a Witness historical record — at the
same time, about the same six people in a rail yard.

## 5. Mechanical Hooks (mapped to existing systems)

Every hook below plugs into a system that already exists in the agent. The
Circuit adds no new currencies — it adds a **spotlight** to the existing ones.

| Existing system | Circuit hook |
|---|---|
| **Enhancements / Leverage** (`sentinel-agent/src/systems/leverage.py`) | Sponsorship. Accepting sponsor gear mid-season is accepting leverage; the call-in comes at the worst possible bracket |
| **Hinge Moments** | The arena manufactures them on camera: the downed opponent who yields, the twist the showrunner offers you live |
| **NPC Disposition** | Opponents are NPCs with memory. The fighter you spared meets you again — in the bracket or outside it |
| **Dormant Threads** | "The crowd remembers the yield you refused" — queue it, surface it seasons later |
| **Favors** (`sentinel-agent/src/systems/favors.py`) | Corner crew: calling in a favor gets you a cutman, a scout report on your opponent, a venue map |
| **Job Board** (`sentinel-agent/src/systems/jobs.py`) | Matches are a job type. Stakes vary: purse, safe passage, debt clearance, a faction dropping a grudge |
| **Social Energy** | The interview is the second fight. Post-match obligations drain the same pool the match did |
| **Regions / Vehicles** | The Circuit tours. Venues have regional character and hosting factions; getting there is the existing travel game |
| **Witnesses MCP data** | Match records are wiki events (`log_wiki_event`) — the campaign wiki grows a fight history organically |

### The first organ swap: ratings as a resource

Under the Circuit frame, the tactical prototype's first real divergence from
XCOM is not cover degradation — it is **audience**:

- Flashy, risky plays (long shots, flanking sprints, fighting from the open)
  build rating. Safe plays (hunkering, overwatch turtling) bleed it.
- Rating converts to purse money, sponsor interest, and faction attention —
  all things the campaign layer already knows how to spend.
- Playing to the crowd versus keeping your people safe is the
  integrity-under-pressure loop, running *inside* the tactical layer.

This is deliberately the opposite of XCOM's incentive structure, where optimal
play is maximum caution. The Circuit pays you to be worth watching, and makes
you decide what that costs.

### The second: surrender, on camera

Hostiles can yield when the match is lost (morale, not just HP). What you do
next is a hinge moment with an audience: the Covenant referee is watching, the
Witness feed is live, the Syndicate odds assumed a finish. Every option is
legible to a different faction as the right one.

## 6. Loot, Cosmetics, and False Colors

Nothing in the Circuit drops `+3.7%`. Gear changes what a fighter can
**do**, faction rewards change where a fighter can **go**, and cosmetics
change what the world **believes**. The numbers stay on the broadcast
overlay where they belong.

### Loot is verbs and access, never stats

Two acquisition channels, both priced by systems that already exist:

- **Sponsor gear** changes a unit's verbs or geometry — a shotgun that
  displaces, a drone that reads intent one turn further, a shield that
  becomes temporary cover. Accepting it is accepting leverage
  (`leverage.py`); the call-in arrives at the worst possible bracket.
  Gear is never strictly better, only differently committed.
- **Faction rewards** are access: venues, card types, objective contracts,
  a corner crew, a referee who owes you. Access is **standing-gated, not
  unlocked** — "unlock" implies permanence, and nothing here is permanent.
  Go hostile with Covenant and their venues close again, their protections
  lapse, their colors on your shoulders change meaning. A reputation web,
  not a tech tree. (The gates already exist: standing in `jobs.py`,
  disposition in `favors.py`.)

The completionist failure mode — grind all eleven factions, collect
everything, owe nobody — is structurally impossible when access tracks
*current* standing. That is intended. An account you finish is not a
squad you answer for.

### Cosmetics come in three registers

| Register | What it is | What the world does |
|---|---|---|
| **Flair** | A really good hood. A cape. Wear, scars, trophies | Nothing. It is yours, and the world ignores it |
| **Colors, worn honestly** | Faction insignia backed by real standing | Reads it and reacts: disposition, odds, crowd, referee |
| **Colors, worn falsely** | Insignia you have no right to | Reads it exactly the same — until someone present can check |

Most items are flair, on purpose. The squad you dress is the squad you
protect, and that attachment needs no mechanical subsidy.

### The insignia slot

One slot the world reads; everything else the world ignores. The slot is
a **claim, not a credential** — the game renders what you wear with
perfect honesty, and whether it is true is your problem. This keeps the
dress-up layer free while giving every fighter exactly one channel for
saying something with their body on camera.

Because the slot is always read, **there is no neutral content**:

| In the slot | What it says |
|---|---|
| Faction colors, backed | Allegiance — the world reacts accordingly |
| Faction colors, unbacked | Fraud (see below) |
| Nothing | "No colors." Eleven factions read an empty patch eleven ways — Convergence sees recruitable, Covenant sees unsworn, the Syndicate sees unpriced |
| A personal token | A pressed flower, a length of chain, a child's ribbon. The crowd interprets — and repetition turns it into a persona. Wear it through a famous run and you become *the one with the chain* |
| A trophy | Memorial to your crew, taunt to the crew it came from. Depends entirely on who is watching, and the game never rules on which |

Personal tokens are **player-authored insignia**: nobody designs them,
play makes them mean something. Recognition accrues through existing
systems only — NPC memory triggers key on the token, Witness records
log the matches it was worn in, crowd recognition rides rating. No new
currency. Two consequences follow and both are features: a legend is
transferable (a retiring fighter hands the token to a rookie, and the
recognition arrives with suspicion attached), and a legend is
counterfeitable (Ghost Networks will launder anything, including you).
A mask plus a personal token is a persona with no name at all — the
token *is* the identity.

### False colors

Wearing colors without the standing behind them is fraud, and fraud is a
play, not a menu error. Exposure must be **legible, never a lottery**
(design philosophy rule 1): the pre-match card lists who is present that
could read you — a Witness recorder, a hosting-faction official, an NPC
who remembers you (`check_triggers`). Walking in anyway is a decision
made with open eyes.

| Faction | Response to being impersonated |
|---|---|
| Covenant | Oath-breaking. Standing drops hard; sanctioned cards close |
| Steel Syndicate | Respects the hustle, bills the hustle — a fine, then a license offer |
| Witnesses | Never punish. Simply publish. The record is the punishment |
| Ghost Networks | The vendor. Laundered kit is a product line; exposure risk priced in |
| Nexus | Flags the anomaly; your odds move strangely on the next card |

A mask plus false colors is the complete identity laundry — which is a
Ghost Networks service, purchasable, with strings.

### Trophies have provenance

Every match has a seed and a Witness record. A trophy cosmetic references
both: the jacket is *from the night you refused the yield at the drained
reservoir*, and anyone can rewatch what it cost (`log_wiki_event`,
memvid). The squad's look accumulates history the way their dossiers do —
cosmetics as a legible record of what they survived and what they chose.

### Prototype implications

- Flair is renderer-only — palette and material variants on the current
  primitives, sprite layers later. Zero rules impact; determinism is
  untouched by construction.
- Venue rulesets (a Covenant card forbids finishing downed fighters; a
  Syndicate card pays for it) are rule variants in `tactical-core` with
  their own golden transcripts.
- The insignia declaration is one line on the pre-match card (roadmap
  step 3), declared before the match and resolved by the same visible
  rules as everything else.

If the game is ever sold, flair is the only purchasable register. Colors
and access stay play-gated, or the allegiance layer is dead on arrival.

## 7. What This Is Not

- **Not the whole game.** The Circuit is one venue inside the campaign — a
  place jobs, debts, and disputes sometimes route through. The wasteland
  still exists; unsanctioned violence still exists and stays as costly and
  ugly as the rest of the repo assumes.
- **Not a metaplot obligation.** A campaign can ignore the Circuit entirely.
  It is infrastructure, like regions and vehicles.
- **Not settled canon.** This doc is a proposal. Names, Covenant rules,
  season structure, and the ratings math are all open.

## 8. Open Questions

1. **Name.** "The Circuit" (touring, regional, ties to travel systems) vs.
   "The Sanction" (legalistic, Covenant-flavored) vs. something diegetic that
   different factions refuse to share (Syndicate: "the card"; Covenant: "the
   proceedings"; crowds: "the show").
2. **Lethality default.** Are matches nonlethal-by-rule with lethality as a
   scandal, or lethal-by-default with mercy as the scandal? (Current lean:
   varies by venue and hosting faction — a Covenant card and a Syndicate
   card should feel like different sports.)
3. **Player entry fiction.** Why does a courier/fixer character step into a
   bracket? Debt is the obvious hook; are there others worth systemizing?
4. **Ratings math.** What behaviors are "worth watching" mechanically, and
   how do we keep the incentive legible without a hidden crowd-mood model?
   (Design philosophy rule 1: shared state must be visible.)
5. **Showrunner authority.** How much may the GM-as-showrunner interfere
   mid-match before it violates turn authority and determinism
   (`Sentinel 2D.md` §4)? Current lean: twists are declared between rounds,
   resolved by the same pure-function pipeline — never silent mid-turn edits.
6. **Exposure model for false colors.** Event-driven (a reader must be
   physically present) or threshold-based? How much of the presence list is
   visible pre-match? Current lean: fully visible — the risk is a decision,
   never a dice roll the player didn't know they were making.
7. **Does flair stay pure forever?** Is there ever a crowd-mood bonus for
   showing up dressed well? Current lean: no. The moment flair has a
   number, every hood is a stat stick and the register collapses into
   colors.
8. **Personal-token recognition.** How does a token legibly accrue meaning —
   match count worn, notoriety of the matches, or only what NPCs and
   Witnesses actually recorded? Current lean: only the recorded — a token
   means exactly what the record says happened while wearing it, so its
   meaning is auditable like everything else.

## 9. Prototype Roadmap

Building on `prototypes/tactical/` in order of leverage:

1. **Yield states** — hostiles surrender below a morale threshold; add the
   spare/finish choice and log it (hinge moment plumbing can come later)
2. **Rating meter** — visible, simple, rule-based; pays out at match end
3. **Match framing** — pre-match card (stakes, sponsor offer, venue,
   hosting faction) and post-match consequence summary
4. **Showrunner twists** — between-round events drawn from a small deck,
   announced on the feed before they resolve
5. **Campaign wiring** — matches as a job type; results into wiki events,
   disposition changes, and dormant threads

Steps 1–2 are weekend-sized against the existing prototype. Step 5 is where
the Circuit stops being a prototype and becomes SENTINEL.
