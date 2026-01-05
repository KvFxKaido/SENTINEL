# AI Feedback Consolidation

*Ideas gathered from ChatGPT, Kimi, Deepseek — January 2026*

---

## Current State (What's Already Built)

Before evaluating suggestions, here's what SENTINEL already has:

| Feature | Status | Notes |
|---------|--------|-------|
| Dormant thread surfacing | ✅ Built | Keyword matching, `[DORMANT THREAD ALERT]` injection, GM discretion |
| Enhancement leverage | ✅ Built | Hint injection, weight escalation (light/medium/heavy), faction pressure styles |
| Hinge detection | ✅ Built | Pattern matching in player input, logging |
| NPC memory triggers | ✅ Built | Tag-based reactions, disposition shifts |
| Council system | ✅ Built | Parallel advisor queries with faction voices |
| Test coverage | ✅ 107 tests | Core mechanics covered |

---

## Source 1: TTRPG Creator Buddy (ChatGPT CustomGPT)

### Key Points

1. **Dormant threads are the keystone** — "This is the moment SENTINEL crosses from impressive to unforgettable"
   - *Status: Already built*

2. **Phase-based GM guidance** — Different prompts per mission phase (briefing vs execution vs debrief)
   - *Status: Not yet built, low code effort*

3. **Enhancement leverage should be story-triggered, never random**
   - "Factions call favors when refusal would contradict the reason you accepted"
   - *Status: Built with this philosophy*

4. **Player-facing "Push" mechanic** — Let players explicitly invite consequence
   - Costs: social energy, faction standing, permanent flag
   - *Status: New idea, worth considering*

5. **Multiplayer/Web UI** — Defer until core systems solid
   - *Status: Agreed, already deprioritized*

### Proposed Thread Schema (Their Suggestion)

```yaml
dormant_thread:
  trigger_type: time | faction | npc | location | energy
  trigger_condition: "Faction standing <= Unfriendly"
  tension: 1-5
```

### Claude's Take

The rigid `trigger_type` enum is more mechanical than our keyword-matching approach. Our implementation keeps GM discretion central — threads surface when *narrative* matches, not when variables trip. Prefer our current approach.

---

## Source 2: TTRPG Plot Advice

### Key Points

1. **Leverage Clock model** — Hidden segments (3-6), specific triggers (+1/+2), clock fills = faction must call
   - *Status: Disagree — too gamey, removes GM discretion*

2. **Dormant threads surface by resonance, not time**
   - Three conditions: Thematic Echo, Factional Proximity, Identity Stress
   - *Status: Aligns with our keyword approach*

3. **Consequence Scheduler** — Unified system evaluating all consequence sources
   - *Status: We have this implicitly via `respond()` checks. Could formalize later if GM gets overwhelmed.*

4. **Multiplayer model** — Sequential spotlight, shared consequence pool
   - *Status: Good framework for later*

### Claude's Take

The Leverage Clock feels like a board game mechanic. SENTINEL's philosophy is "pressure without scripts" — the GM should decide when to call leverage based on narrative conditions, not segment counts. Our hint → judgment → call flow is better.

"Identity Stress" (social energy threshold linked to past choice) is clever but adds tracking complexity that could get brittle.

---

## Source 3: Infinite Imagination TTRPG Helper

### Key Points

1. **Non-action as hinge** — "What happens when the player tries to disengage?"
   - Avoidance is also a choice
   - Track consecutive disengagements, surface consequences for *not* engaging
   - *Status: New idea, philosophically strong, worth building*

2. **Factions as long-term corruption** — Faction exposure changes player *thinking*, not just standing
   - "Nexus advisors start finishing your sentences"
   - "Syndicate language infects your dialogue"
   - *Status: Prompt/narrative guidance, not system. Achievable.*

3. **The guilt question** — "When a campaign ends, what do you want the player to feel guilty about?"
   - Design north star for hinge framing, debrief prompts, consequences
   - *Status: Philosophical anchor, not a feature*

4. **Missing end state** — No win condition is correct, but players need emotional anchors
   - Suggestion: Help players ask "What would 'enough' look like?"
   - *Status: Could add to debrief prompts*

### Claude's Take

This is the strongest feedback philosophically. Non-action as hinge is genuinely novel and fits SENTINEL's "refusal is meaningful" philosophy. The faction corruption idea is achievable through GM guidance. The guilt question should inform design decisions.

---

## Source 4: Kimi

### Key Points

1. **Refusal reputation space** — Refused enhancements should grant a *title* ("The Undaunted") that NPCs react to
   - "No power, but reputation space opens up that can't be bought any other way"
   - *Status: We track refused enhancements but don't give them narrative weight yet. Good idea.*

2. **Social energy needs a carrot, not just stick** — Currently only disadvantage at low energy
   - Suggestion: Spend 10% energy to invoke a restorer mid-scene for advantage on one social check
   - "Players learn to *spend* the meter as a resource, not just hoard it"
   - *Status: New mechanic idea, worth considering*

3. **Enhancement leverage via d6 roll** — After mission, 4-5 = small obligation, 6 = two factions clash
   - *Status: Disagree with random trigger. We built hint-based system with GM discretion.*

4. **Dormant threads pressure counter** — `/quiet` command increments hidden counter, when ≥3 next mission must weave in a thread
   - *Status: Disagree — prefer GM discretion over forced weaving*

5. **Multiplayer via priority drafting** — Players secretly draft priority (1-4), GM resolves the spread
   - *Status: Interesting framework for later*

6. **Banner UX** — Hex glitch fires every command, gets old. Add `/quiet-banner` toggle or cache after first load.
   - *Status: Valid UX feedback, easy fix*

7. **Lore retrieval exposure** — `/lore lattice` returns faction-tagged chunks so players see corpus bias
   - *Status: Good idea, reinforces "competing truths"*

8. **Council hallucination test** — Assert advisors don't give identical answers (<60% string overlap)
   - *Status: Good testing idea*

9. **Highest-impact** — Enhancement leverage (faction callbacks)
   - *Status: Already built*

### Claude's Take

Strong practical feedback. The "refusal grants title" idea is excellent — it gives narrative weight to saying no without adding mechanical power. The social energy carrot (spend to gain advantage) is worth exploring.

Disagree with the random d6 leverage trigger and forced dormant thread weaving. Both remove GM discretion in favor of mechanical triggers. SENTINEL's philosophy is "tools inform, GM decides."

The banner UX note is valid — easy quality-of-life fix.

---

## Source 5: Deepseek

### Key Points

1. **Enhancement leverage** — Story-triggered, tied to hinge detection
   - Example: Using Syndicate enhancement to bypass security → later Syndicate calls favor during moral dilemma
   - *Status: Already built with this philosophy*

2. **Dormant thread surfacing** — Tie to faction standing thresholds or social energy states
   - *Status: We use keyword matching instead. This is more mechanical than our approach.*

3. **Multiplayer** — Round-robin consultation, players represent different factions/backgrounds
   - *Status: Interesting framework for later*

4. **Web interface** — Yes but not yet. WebSocket frontend connecting to CLI backend as first step.
   - *Status: Agrees with deferral, good migration path*

5. **Priorities** — Enhancement leverage → Dormant threads → Phase-based GM guidance
   - *Status: First two already built, third is on our list*

6. **"Tactical" definition question** — "How do you define 'tactical' in a game that's not about combat dominance?"
   - Is it social maneuvering? Resource allocation? Narrative positioning?
   - *Status: Good clarifying question worth answering*

### Claude's Take

Most aligned with what we've already built. The "tactical" question is worth answering — SENTINEL is tactical in the sense of *resource positioning* (social energy, faction standing, information) and *consequence management* (dormant threads, leverage). Combat is incidental; the tactics are in relationship navigation.

WebSocket frontend as migration path is a practical suggestion if we ever go web.

---

## Synthesis: What To Build Next

### High Priority (Strong Consensus + Fits Philosophy)

| Idea | Source | Effort | Notes |
|------|--------|--------|-------|
| Phase-based GM guidance | ChatGPT, Deepseek | Low | Mostly prompt work |
| Non-action as hinge | Infinite Imagination | Medium | Track disengagement, surface consequences |
| Refusal grants title/reputation | Kimi | Low | NPCs react to refused enhancements |
| Faction narrative corruption | Infinite Imagination | Low | GM guidance update |
| Debrief enhancement | Infinite Imagination | Low | Add "What would enough look like?" |

### Worth Considering (Good Ideas, Lower Priority)

| Idea | Source | Effort | Notes |
|------|--------|--------|-------|
| Social energy carrot | Kimi | Medium | Spend 10% for advantage when invoking restorer |
| Player "Push" mechanic | ChatGPT | Medium | Player invites consequence explicitly |
| Banner UX toggle | Kimi | Low | `/quiet-banner` or cache after first load |
| Lore faction filtering | Kimi | Low | `/lore lattice` shows bias explicitly |
| Council hallucination test | Kimi | Low | Assert advisors don't give identical answers |

### Rejected or Deferred

| Idea | Source | Reason |
|------|--------|--------|
| Leverage Clock model | TTRPG Plot Advice | Too mechanical, removes GM discretion |
| d6 random leverage trigger | Kimi | Random undermines narrative weight |
| Dormant thread pressure counter | Kimi | Forced weaving removes GM discretion |
| Rigid trigger_type enum | ChatGPT | Keyword matching is more flexible |
| Faction standing triggers | Deepseek | Too mechanical for thread surfacing |
| Multiplayer | All | Defer until core solid |
| Web UI | All | CLI is curation, not limitation |

---

## Design North Stars (From This Feedback)

1. **"Consequences bloom over time"** — Already our philosophy, validated
2. **"Refusal is content"** — Extend to non-action/avoidance
3. **"Pressure without scripts"** — GM discretion over mechanical triggers
4. **"The guilt question"** — What should players feel guilty about when it ends?

---

## Open Questions

1. How do we track "non-action" without being punitive? (Avoidance should have consequences, but not feel like the game is punishing passivity)

2. How does faction corruption manifest in prompts? (Specific language patterns per faction?)

3. Should "Push" be a player-initiated command, or GM-offered choice?

4. What does "tactical" mean for SENTINEL? (Social maneuvering? Resource positioning? Consequence management?)

5. What should players feel guilty about when a campaign ends? (Design north star for hinges and debrief)

---

## Multiplayer Frameworks (For Later)

Several sources proposed multiplayer approaches worth capturing:

| Source | Model | Notes |
|--------|-------|-------|
| ChatGPT | Sequential spotlight, shared consequence pool | One speaker, others interject at energy cost |
| Kimi | Priority drafting (1-4) | Players secretly rank choices, GM resolves spread |
| Deepseek | Round-robin consultation | Players represent different factions/backgrounds |

Common thread: Avoid simultaneous input. Use the council concept to make everyone feel heard.

---

*Last updated: January 2026*
