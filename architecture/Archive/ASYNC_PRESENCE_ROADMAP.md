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

### Phase 1: LLM Wait State UX ✅ COMPLETE
**Impact:** High | **Effort:** Medium

Make the GM "thinking" time feel like visible work, not dead air.

#### Checklist

- [x] Define processing stage events in `EventType` enum
  - [x] `STAGE_BUILDING_CONTEXT`
  - [x] `STAGE_RETRIEVING_LORE`
  - [x] `STAGE_PACKING_PROMPT`
  - [x] `STAGE_AWAITING_LLM`
  - [x] `STAGE_EXECUTING_TOOL`
  - [x] `STAGE_PROCESSING_DONE`

- [x] Emit stage events from `agent.py` during `respond()`
  - [x] Before building context
  - [x] Before lore retrieval
  - [x] Before context packing
  - [x] Before LLM call (with model name + token count)
  - [x] During tool execution (with tool name)
  - [x] After response complete

- [x] Create `ThinkingPanel` widget in TUI
  - [x] Subscribe to stage events
  - [x] Show current stage with icon (◆) and completed stages (◇)
  - [x] Show detail text (model name, tool name, etc.)

- [x] Style the thinking panel
  - [x] Box border with "GM PROCESSING" header
  - [x] Stage-appropriate icons
  - [x] Integrated into console wrapper layout

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

### Phase 2: Proactive Context Injection ✅ COMPLETE
**Impact:** High | **Effort:** Low

Make the GM aware of world state changes to weave into responses naturally.

#### Checklist

- [x] Create `ambient_context.py` module in `context/`
  - [x] Function to extract "world state deltas" from campaign
  - [x] Track: thread escalations, faction shifts, NPC silence, supply changes

- [x] Define ambient context template
  ```markdown
  ## Ambient World State (weave naturally, don't list)
  - [Thread] Nexus Demand escalated to URGENT (2 days remaining)
  - [Faction] Ember standing dropped 5 points last session
  - [NPC] Cipher hasn't contacted player in 3 sessions
  - [World] Steel Syndicate convoy is 1 day overdue
  ```

- [x] Inject into system prompt via `prompt_packer.py`
  - [x] Add `AMBIENT` section with 500 token budget
  - [x] Session-based "seen" tracking to avoid repeating items

- [x] Add prompt guidance for GM to weave (not list) ambient info
  - [x] Update `prompts/core.md` with ambient weaving instructions

#### Example GM Response
> "As you approach the checkpoint, your comm crackles—Cipher's voice, clipped and tense: 'We need an answer. Today.' The guards watch you. Waiting."

Not: "AMBIENT UPDATE: Cipher is calling you."

---

### Phase 3: Session Bridging ("While You Were Away") ✅ COMPLETE
**Impact:** Medium | **Effort:** Medium

Show what changed between play sessions.

#### Checklist

- [x] Track "last seen" state per campaign
  - [x] Add `CampaignSnapshot` model and `last_session_snapshot` field to schema
  - [x] Snapshot: faction standings, thread states, NPC dispositions

- [x] Create diff function in `manager.py`
  - [x] `get_session_changes()` compares current to snapshot
  - [x] Returns list of changes with icons and types

- [x] Create `SessionBridgeScreen` widget
  - [x] Modal screen with "WHILE YOU WERE AWAY" header
  - [x] Shows changes with icons and colors
  - [x] "Access Terminal" button to dismiss

- [x] Update snapshot on `/debrief` or session end
  - [x] `_create_snapshot()` captures state in `end_session()`
  - [x] Migration creates initial snapshot for existing campaigns

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

### Phase 4: Enhanced Reactive Motion ✅ COMPLETE
**Impact:** Low-Medium | **Effort:** Low

Add visual flourishes to existing event-driven updates.

#### Checklist

- [x] Add CSS animations to `tui.py` (inline CSS)
  - [x] `.faction-shift` — border pulse with 0.4s keyframe animation
  - [x] `.energy-critical` — urgent pulse when social energy ≤25
  - [x] `.thread-surfaced` — animation for surfaced threads
  - [x] `.consequence-urgent` — red glow for urgent items

- [x] Emit events for currently-silent state changes
  - [x] `THREAD_SURFACED` event in `surface_dormant_thread()`
  - [x] `ENHANCEMENT_CALLED` event in `call_leverage()`

- [x] Add transient CSS classes in TUI handlers
  - [x] `_on_thread_surfaced()` and `_on_enhancement_called()` handlers
  - [x] `set_timer(1.0, ...)` removes animation classes

#### Animation Principles
- **Brief:** 0.3-0.5s max
- **Subtle:** Don't distract from content
- **Meaningful:** Only animate significant changes
- **Consistent:** Same animation = same meaning

---

### Phase 5: Persistent Visual Weight ✅ COMPLETE
**Impact:** Medium | **Effort:** Low

Make static elements feel "heavy" with presence.

#### Checklist

- [x] Consequence urgency indicators
  - [x] Color-coded dots (🔴 URGENT, 🟡 SOON, 🟢 LATER)
  - [x] Countdown display for time-sensitive demands (T-N, DUE, OVERDUE)

- [x] NPC "last contact" indicator
  - [x] Shows sessions since last interaction in Pressure Panel
  - [x] Highlights NPCs who have been quiet 2+ sessions

- [x] Add dedicated "Pressure Panel" to TUI layout
  - [x] `PressurePanel` widget in world-column
  - [x] Shows top 5 most urgent items (scored and sorted)
  - [x] Includes: demands, threads, NPC silence

- [ ] Faction tension bars (deferred)
  - Note: Would duplicate existing WorldDock faction display

---

## Priority Order

| Phase | Impact | Effort | Status |
|-------|--------|--------|--------|
| 1. LLM Wait State | High | Medium | ✅ Complete |
| 2. Proactive Context | High | Low | ✅ Complete |
| 3. Session Bridging | Medium | Medium | ✅ Complete |
| 4. Reactive Motion | Low-Medium | Low | ✅ Complete |
| 5. Visual Weight | Medium | Low | ✅ Complete |

**All phases implemented!** The SENTINEL TUI now has full async presence features.

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
