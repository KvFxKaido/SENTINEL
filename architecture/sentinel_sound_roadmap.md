# SENTINEL — Tactical Sound Roadmap

> **Design principle:** Sound is a comms channel, not a soundtrack.
> It reacts to world state, never to player input directly.

---

## Phase 0 — Guardrails (Do This First)

**Non‑negotiables**
- Sound subscribes only to existing domain events (event bus)
- No new game logic introduced for audio
- All playback is async and non‑blocking
- Sound can be disabled globally at runtime
- Silence is a valid and respected state

**Out of scope (explicitly)**
- Music tracks
- Per‑character voice acting
- Real‑time spatial audio
- Input click sounds

---

## Phase 1 — Presence & Latency (MVP)

**Goal:** Make the system feel alive without adding spectacle.

### Events → Sounds

| Domain Event | Sound Intent | Notes |
|-------------|--------------|-------|
| GM_THINKING_START | Low ambient loop | Masks latency, very quiet |
| GM_THINKING_END | Soft release | Ends loop cleanly |
| CHOICE_PRESENTED | Neutral cue | Signals agency |
| CHOICE_CONFIRMED | Firmer click | Commitment moment |
| HINGE_DETECTED | Heavy impact | Brief silence before hit |

**Asset Count:** ~5 sounds total

**Acceptance Criteria**
- No sound fires on raw input
- Sounds never overlap chaotically
- Latency feels intentional, not frozen

---

## Phase 2 — System Telemetry

**Goal:** Let players *feel* state changes before reading them.

### Events → Sounds

| Domain Event | Sound Intent | Notes |
|-------------|--------------|-------|
| FACTION_CHANGED (+) | Subtle rising tone | No celebration |
| FACTION_CHANGED (–) | Subtle falling tone | No drama |
| THREAD_SURFACED | Radio crackle | Short, dry |
| CONSEQUENCE_ESCALATED | Low pulse | Signals pressure |
| NPC_INTERRUPT | Comms ping | Human, not alarm |

**Asset Count:** +4–5 sounds

**Acceptance Criteria**
- Players can identify faction shifts without UI
- Urgency is conveyed without panic

---

## Phase 3 — Strain & Pressure (Optional)

**Goal:** Encode psychological pressure into ambience.

### Events → Sounds

| Domain Event | Sound Intent | Notes |
|-------------|--------------|-------|
| STRAIN_TIER_I | Light interference | Barely perceptible |
| STRAIN_TIER_II | Rhythmic pressure | Low frequency |
| STRAIN_TIER_III | Distortion layer | Never loud |
| SOCIAL_ENERGY_CRITICAL | Slow pulse | Fatigue, not danger |

**Asset Count:** +3–4 sounds

**Acceptance Criteria**
- Players notice strain emotionally before numerically
- No sound induces anxiety spikes

---

## Phase 4 — Faction Identity (Deferred)

**Goal:** Reinforce faction personality through sound texture.

**Examples**
- Nexus: clean digital pings
- Ember Colonies: fire crackle, wind
- Lattice: electrical hum
- Ghost Networks: reversed/glitched audio
- Witnesses: tape hiss, analog noise

**Rules**
- Applied as filters or alternates, not layered stacks
- Never override core Phase 1 sounds

---

## Phase 5 — Polish & Control

**Optional Enhancements**
- Volume control (global only)
- Sound test command
- Per‑campaign sound enable flag
- Asset hot‑swap support

**Still Out of Scope**
- Adaptive music
- Voice synthesis
- Competitive audio cues

---

## Minimal Asset List (Recommended)

Start with exactly these:
1. gm_thinking_loop.wav
2. gm_thinking_end.wav
3. choice_present.wav
4. choice_confirm.wav
5. hinge_hit.wav
6. faction_up.wav
7. faction_down.wav
8. npc_interrupt.wav

If more are added before Phase 2 is complete, stop and reassess.

---

## Final Rule

If removing a sound makes the system clearer,
that sound did not belong.

Sound exists to clarify meaning, not decorate it.

