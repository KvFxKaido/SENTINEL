# Design Philosophy

**Author:** Shawn Montgomery
**Purpose:** Constraints that keep software from lying to its users
**Lineage:** Extracted from Sovwren Friction Spec (2024–2025)

---

## What This Is

These are the patterns that actually work. Not "best practices" I read somewhere — patterns I've validated across terminal UIs, web automation, and AI tools by watching them fail when ignored.

If a feature violates these principles, it doesn't ship. I don't care how impressive it is.

Every rule here exists because something broke. This is postmortem, not theory.

---

## Core Invariants

### 1. Visibility Over Convenience

Users need to see what the system sees and does. Period.

**Things that violate this:**
- Background operations with no indication
- "Smart" behavior that guesses what you meant
- State changes that happen silently
- Capability escalation without telling you

**What this looks like in practice:**
- File trees distinguish "loaded" from "available"
- Event logs for anything with side effects
- Mode indicators you can actually see
- No silent fallbacks to different behavior

**The test:** If you can't tell what changed, the system is hiding something.

---

### 2. Capability Changes Require Consent

When the system can suddenly do *more*, that's an ethical event. Not a UX detail.

**Things that violate this:**
- Auto-enabling features "for your convenience"
- Silent permission escalation
- Inferring authorization from past behavior
- "Smart defaults" that expand what the system can touch

**What this looks like in practice:**
- Web access behind an explicit gate
- Browser actions need escalation + stated reason
- Cloud API calls need preview and confirmation
- Destructive operations need two-step confirmation

**The test:** Can you identify the moment the blast radius expanded?

---

### 3. Truth Over Smoothness

Honest and awkward beats pleasant and misleading. Every time.

**Things that violate this:**
- Hiding errors to keep the flow smooth
- Pretending to remember when you don't
- Faking continuity across resets
- Polishing failures into "partial success"

**What this looks like in practice:**
- Return observations, not success/failure
- Say what you don't know
- Surface limits instead of papering over them
- Errors stop execution — they don't get buried

**The test:** Does it feel polished because it's *correct*, or because it's *concealing*?

---

### 4. Fewer Features > More Coherence

Every feature is a maintenance burden and a cognitive cost. Act accordingly.

**Things that violate this:**
- Feature bloat driven by novelty
- Overlapping capabilities with different behavior
- Special cases that fracture the mental model
- Tools that don't compose predictably

**What this looks like in practice:**
- One clear way to do common things
- Remove features that contradict core principles
- Justify complexity before building it
- Defer functionality until patterns stabilize

**The test:** Can someone explain the whole system in five minutes?

---

### 5. Explicit State, Always

If state affects behavior, it has to be visible. No exceptions.

**Things that violate this:**
- Hidden modes that change interpretation
- Implicit context that alters responses
- Ambient state users can't inspect
- Config that lives "somewhere else"

**What this looks like in practice:**
- Mode indicators in the UI
- Context load meters
- Session state visible on demand
- Settings rendered, not just stored

**The test:** Can you reconstruct *why* the system did that?

---

### 6. Boring Is Correct

Predictable, explicit, verbose behavior is a feature. Not a flaw.

**Things that violate this:**
- Clever abstractions that hide mechanism
- Magic that works until it catastrophically doesn't
- Convenience shortcuts that break mental models
- Automatic behavior users can't predict

**What this looks like in practice:**
- Commands do exactly one thing
- No context-dependent behavior shifts
- Explicit over implicit
- Manual transmission, not automatic

**The test:** Would a new user understand what just happened?

---

### 7. Seams Must Be Explicit

Users need to know which component is acting. Always.

**Things that violate this:**
- AI "helping" by executing on your behalf
- Shell commands auto-running from suggestions
- Integrations that blur responsibility
- Actions taken "because you probably wanted to"

**What this looks like in practice:**
- Shell is law — AI never executes implicitly
- Confirmation before external side effects
- Clear attribution of who did what
- Preview before commit

**The test:** If something fails, can you identify which component failed?

---

### 8. Performance Is a Feature, Safety Is Non-Negotiable

Fast is nice. Safe is required.

**Things that violate this:**
- Skipping validation for speed
- Optimistic updates without rollback
- Background ops you can't inspect
- Blind trust in caches

**What this looks like in practice:**
- Log intent before execution
- Graceful degradation with explicit indication
- Stale data clearly marked
- Cache hits distinguished from fresh data

**The test:** Can you audit what happened, even when it was fast?

---

## The Short Version

These are non-negotiable:

1. Shared state must be visible
2. Capability changes require consent
3. Convenience never overrides clarity
4. Fewer features beat fractured coherence
5. If it feels impressive, it's probably hiding something

---

## Context-Specific Notes

### AI / LLM Interfaces
- Memory asymmetry is structural — don't fake continuity
- Context limits are real — show them
- Mode changes affect behavior — make them visible
- External access is capability escalation — gate it

### Terminal Tools
- Shell is ground truth — never execute implicitly
- Local-first by default — cloud is opt-in
- Boring is correct — predictable over clever
- Explicit seams — users know which component acts

### Web Automation
- Observation precedes action
- Escalation requires justification and permanent logs
- Return observations, not success states
- Event logs exist for audit, not analytics

---

## When Can You Ship a Feature?

Only if:

1. Its state is visible
2. Its failure modes are legible
3. It doesn't reintroduce solved problems
4. Users can tell what the system observed
5. It doesn't hide complexity behind convenience

If any of these fail, defer it.

---

## When to Break These Rules

Never by accident.

**Valid reasons:**
- Safety (preventing user harm)
- Legal compliance (when there's no alternative)
- Physical constraints (when visibility is literally impossible)

**Invalid reasons:**
- "Users expect this"
- "Competitors do it"
- "It feels more elegant"
- "We can hide the complexity later"

---

## Final Thought

Good software is boring. Great software is boring *and* honest.

If a rule stops serving the work, change it deliberately and document the trade-off. But "it's inconvenient" isn't a trade-off — it's a skill issue.

---

**Version:** 1.2
**Last Updated:** 2026-01-16
**Source:** Extracted from Sovwren Friction Spec; validated across Vigil, Sentinel, and Browser Instrumentation MCP
