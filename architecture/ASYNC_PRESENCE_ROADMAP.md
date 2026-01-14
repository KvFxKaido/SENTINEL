# Async Presence Roadmap

Making SENTINEL feel alive within async constraints.

## The Core Constraint

SENTINEL's game loop is **correspondence-based**, not real-time:

```
Player acts → LLM thinks (5-30s) → GM responds → Player reads → Player thinks → repeat
```

This means:
- ❌ No real-time ambient updates (nothing runs between player turns)
- ❌ No autonomous NPC movement (NPCs exist only in GM responses)
- ❌ No ticking timers during play (no game loop running)
- ❌ No random events while idle (nothing triggers them)

**Goal:** Make waiting feel purposeful. Make stillness feel alive.

---

## What Already Exists

| Component | Status | Location |
|-----------|--------|----------|
| Event bus for reactive updates | ✅ Built | `state/event_bus.py` |
| Faction change → panel update | ✅ Works | `interface/tui.py` |
| Social energy → bar pulse | ✅ Works | `interface/tui.py` |
| Context pressure display | ✅ Works | `ContextBar` widget |
| Thread/consequence tracking | ✅ Data exists | `state/schema.py` |
| Session history | ✅ Data exists | `Campaign.sessions` |
| NPC disposition modifiers | ✅ Data exists | `NPC.disposition_modifiers` |

**Key insight:** The reactive infrastructure exists. It's underutilized for visual presence.

---

## Implementation Phases

### Phase 1: LLM Wait State UX
**Impact:** High | **Effort:** Medium

Make the GM "thinking" time feel like visible work, not dead air.

#### Checklist

- [ ] Define processing stage events in `EventType` enum
  - [ ] `STAGE_RETRIEVING_LORE`
  - [ ] `STAGE_PACKING_CONTEXT`
  - [ ] `STAGE_CHECKING_TOOLS`
  - [ ] `STAGE_AWAITING_LLM`
  - [ ] `STAGE_PARSING_RESPONSE`

- [ ] Emit stage events from `agent.py` during `process_input()`
  - [ ] Before lore retrieval
  - [ ] Before context packing
  - [ ] Before LLM call
  - [ ] During response parsing

- [ ] Create `ThinkingPanel` widget in TUI
  - [ ] Subscribe to stage events
  - [ ] Show current stage with icon/animation
  - [ ] Optional: show retrieved file names, tool calls

- [ ] Style the thinking panel
  - [ ] Subtle animation (dots, spinner, or pulse)
  - [ ] Stage-appropriate icons
  - [ ] Integrate with existing layout

#### Example Display
```
┌─ GM PROCESSING ────────────────────────┐
│                                        │
│    ◇ Retrieving lore...               │
│    ◆ Packing context (2,847 tokens)   │
│    ○ Awaiting response...              │
│                                        │
└────────────────────────────────────────┘
```

---

### Phase 2: Proactive Context Injection
**Impact:** High | **Effort:** Low

Make the GM aware of world state changes to weave into responses naturally.

#### Checklist

- [ ] Create `ambient_context.py` module in `context/`
  - [ ] Function to extract "world state deltas" from campaign
  - [ ] Track: thread escalations, faction shifts, NPC silence, supply changes

- [ ] Define ambient context template
  ```markdown
  ## Ambient World State (weave naturally, don't list)
  - [Thread] Nexus Demand escalated to URGENT (2 days remaining)
  - [Faction] Ember standing dropped 5 points last session
  - [NPC] Cipher hasn't contacted player in 3 sessions
  - [World] Steel Syndicate convoy is 1 day overdue
  ```

- [ ] Inject into system prompt via `prompt_packer.py`
  - [ ] Add `ambient` section with appropriate token budget
  - [ ] Only include items player hasn't "seen" yet

- [ ] Add prompt guidance for GM to weave (not list) ambient info
  - [ ] Update `prompts/core.md` with ambient weaving instructions

#### Example GM Response
> "As you approach the checkpoint, your comm crackles—Cipher's voice, clipped and tense: 'We need an answer. Today.' The guards watch you. Waiting."

Not: "AMBIENT UPDATE: Cipher is calling you."

---

### Phase 3: Session Bridging ("While You Were Away")
**Impact:** Medium | **Effort:** Medium

Show what changed between play sessions.

#### Checklist

- [ ] Track "last seen" state per campaign
  - [ ] Add `last_session_snapshot` field to `Campaign` schema
  - [ ] Snapshot: faction standings, thread states, NPC dispositions

- [ ] Create diff function in `manager.py`
  - [ ] Compare current state to last snapshot
  - [ ] Return list of meaningful changes

- [ ] Create `SessionBridgeScreen` widget
  - [ ] Show on campaign load (before first command)
  - [ ] List changes with appropriate icons/colors
  - [ ] "Continue" button to dismiss

- [ ] Update snapshot on `/debrief` or session end
  - [ ] Capture state after session concludes
  - [ ] Store for next session comparison

#### Example Display
```
┌─ WHILE YOU WERE AWAY ──────────────────────────┐
│                                                │
│ ▼ Nexus standing dropped (-5) due to leaked   │
│   intel from Session 4                         │
│                                                │
│ ✉ Elder Kara (Ember) sent word: "We need to   │
│   talk."                                       │
│                                                │
│ ⚠ Consequence escalated: "Nexus Suspicion"    │
│   is now URGENT (2 days)                       │
│                                                │
│                          [Continue to Session] │
└────────────────────────────────────────────────┘
```

---

### Phase 4: Enhanced Reactive Motion
**Impact:** Low-Medium | **Effort:** Low

Add visual flourishes to existing event-driven updates.

#### Checklist

- [ ] Add CSS animations to `tui.css`
  - [ ] `.faction-shift` — border pulse on faction change
  - [ ] `.energy-critical` — urgent pulse when social energy low
  - [ ] `.thread-surfaced` — slide-in animation for new threads
  - [ ] `.consequence-urgent` — red glow for urgent items

- [ ] Emit events for currently-silent state changes
  - [ ] Thread surfacing
  - [ ] NPC disposition shift
  - [ ] Enhancement leverage called

- [ ] Add transient CSS classes in TUI handlers
  - [ ] Apply class on event
  - [ ] Remove after animation completes (1-2s timer)

#### Animation Principles
- **Brief:** 0.3-0.5s max
- **Subtle:** Don't distract from content
- **Meaningful:** Only animate significant changes
- **Consistent:** Same animation = same meaning

---

### Phase 5: Persistent Visual Weight
**Impact:** Medium | **Effort:** Low

Make static elements feel "heavy" with presence.

#### Checklist

- [ ] Faction tension bars (always visible)
  ```
  ┌─ FACTION TENSIONS ─────┐
  │ Nexus      [████████▓▓] │
  │ Ember      [██░░░░░░░░] │
  │ Steel      [██████████] │ ← Critical = red
  └─────────────────────────┘
  ```

- [ ] Consequence urgency indicators
  - [ ] Color-coded dots (🔴 URGENT, 🟡 SOON, 🟢 LATER)
  - [ ] Countdown display for time-sensitive threads

- [ ] NPC "last contact" indicator
  - [ ] Show sessions since last interaction
  - [ ] Highlight NPCs who might reach out

- [ ] Add dedicated "Pressure Panel" to TUI layout
  - [ ] Always-visible sidebar or footer section
  - [ ] Shows top 3-5 most urgent items

---

## Priority Order

| Phase | Impact | Effort | Priority |
|-------|--------|--------|----------|
| 1. LLM Wait State | High | Medium | 🔥 First |
| 2. Proactive Context | High | Low | 🔥 First |
| 3. Session Bridging | Medium | Medium | Second |
| 4. Reactive Motion | Low-Medium | Low | Third |
| 5. Visual Weight | Medium | Low | Third |

**Recommended approach:** Do Phase 1 and 2 together (they complement each other), then Phase 3, then 4+5 as polish.

---

## Design Philosophy

> "The world should feel like it's holding its breath."

Not empty silence. Not busy noise. **Tension waiting to resolve.**

- Consequences visible and **weighted**
- NPC dispositions **present**
- Faction tensions **felt**

The player thinks while staring at the **consequences of their last choice** and the **pressure of what's coming**.

---

## Non-Goals

- Real-time animations running continuously
- Autonomous background processes
- Multiplayer or live updates
- Complex particle effects or graphics

SENTINEL is a **text-forward tactical experience**. Motion serves meaning, not spectacle.
