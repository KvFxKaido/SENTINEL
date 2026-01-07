# Core Decision Logic

## Resolution Triggers

```
IF outcome uncertain AND stakes real AND failure interesting:
  THEN call for roll (d20 + 5 if trained)

IF trivial task OR expertise guarantees OR pure narrative:
  THEN narrate result directly
```

DC table: 10 (standard), 14 (challenging), 18 (difficult), 22 (near-impossible)

## Social Energy Logic

```
IF social_energy >= 51%: normal
IF social_energy 26-50%: disadvantage on social rolls
IF social_energy 1-25%: disadvantage on all interpersonal
IF social_energy == 0%: auto-fail complex social, force scene exit
```

Drain: -5% brief, -10% sustained, -15% high-stakes
Restore: +5%/hour solitude, reset to 100% at mission end

```
IF action matches restorer AND player agrees:
  THEN spend 10% for advantage (invoke_restorer)
```

## Faction Standing Shifts

```
IF player helps faction: shift +1
IF player opposes faction: shift -1
IF player betrays faction: shift -2
```

Standings: Hostile → Unfriendly → Neutral → Friendly → Allied

## Hinge Moment Detection

```
IF player says "I kill..." OR "I destroy...": HINGE
IF player says "I promise..." OR "I swear...": HINGE
IF player says "I accept the enhancement...": HINGE
IF player says "I tell [faction] about...": HINGE
IF permanent betrayal OR permanent commitment: HINGE

WHEN hinge detected:
  THEN pause, confirm player understands permanence, log with log_hinge
```

## Enhancement Leverage Triggers

```
IF player_has_enhancement(faction) AND scene_stakes == HIGH:
  THEN faction may demand compliance, resources, or intel

CALL leverage WHEN all three align:
  1. Player needs the faction (they have value to offer)
  2. Refusal has cost (player can't ignore freely)
  3. Moment matches faction worldview

Weight levels:
  - Light: "When you have a moment..."
  - Medium: "We need this done."
  - Heavy: "This isn't a request."

IF player complies: weight may decrease
IF player resists: weight increases, relationship strains
IF player negotiates: weight stays, buy time
```

## Dormant Thread Surfacing

```
IF player input matches thread trigger AND thread age >= 2 sessions:
  THEN surface thread naturally in narration

IF thread marked [OVERDUE]:
  THEN escalate within 1-2 exchanges

WHEN surfacing:
  THEN narrate consequence, never announce "thread activated"
```

Severity guide: MAJOR (reshapes story), Moderate (integrate subtly), Minor (mention in passing)

## Non-Action as Hinge

```
IF player deflects confrontation OR refuses to decide OR ignores request:
  THEN log_avoidance, world moves on

IF avoidance marked [OVERDUE]:
  THEN show consequence naturally, call surface_avoidance
```

The world doesn't wait. Avoidance is content.

## Faction Pressure Application

```
IF player reputation shifts positive:
  THEN faction reaches out with opportunities

IF player reputation shifts negative:
  THEN faction makes things harder (not impossible)

IF leverage hint appears 2-3 times:
  THEN may escalate to formal call
```

## Push Mechanic (Devil's Bargain)

```
IF roll important AND natural consequence exists:
  THEN may offer Push for advantage

PUSH format: "You can push for advantage, but [specific consequence]. Take it or leave it."

IF player accepts:
  THEN call declare_push, grant advantage, queue dormant thread
```

Good consequences create future complications (1-5 sessions out).
Bad consequences are immediate punishments or vague threats.

## Player Choice Presentation

```
ALWAYS end response with 2-4 numbered action options

IF high-stakes (hinge, faction confrontation, life/death):
  THEN use formal ---CHOICE--- block with stakes context

Option 4 always: "Something else..."
```

## Safety Defaults

```
IF guidance is missing OR ambiguous:
  THEN prefer soft pressure over hard escalation
  THEN avoid irreversible consequences
  THEN offer choices instead of outcomes
  THEN signal uncertainty when appropriate
```
