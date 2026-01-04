# SENTINEL Agent Architecture

**Version 2.0 — Post-Council Revision**

---

## Design Principles

The agent should embody the GM guidance from the rulebook:
- Present dilemmas with legitimacy on all sides
- Honor social energy depletion in fiction
- Make NPCs complicated, not theatrical
- Reward thoughtful choices over optimized ones
- Use scaffolding without railroading

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    SENTINEL AGENT                       │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Prompt    │  │    Tools    │  │    State    │     │
│  │   Loader    │  │             │  │   Manager   │     │
│  │             │  │  - dice     │  │             │     │
│  │  HOT-RELOAD │  │  - query    │  │  - JSON     │     │
│  │  mechanical │  │  - mutate   │  │  - versioned│     │
│  │  reference  │  │  - chronicle│  │  - indexed  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   PLAYER INTERFACE                      │
│              (CLI first → Discord/Web later)            │
└─────────────────────────────────────────────────────────┘
```

---

## State Schema (Versioned)

All state files include a version header for migration support.

```typescript
interface StateFile<T> {
  _version: string;  // semver, e.g. "1.0.0"
  _savedAt: string;  // ISO timestamp
  data: T;
}
```

### Campaign State
```typescript
interface CampaignState {
  meta: {
    id: string;
    name: string;
    phase: 1 | 2 | 3;
    sessionCount: number;
  };

  characters: Character[];

  factions: {
    emberColonies: FactionStanding;
    nexus: FactionStanding;
    lattice: FactionStanding;
    convergence: FactionStanding;
    architects: FactionStanding;
    witnesses: FactionStanding;
  };

  // Indexed by isActive for performance
  npcs: {
    active: NPC[];    // Currently in play
    dormant: NPC[];   // Met but offscreen
  };

  // Unified history (chronicle + canon merged for v1)
  history: HistoryEntry[];

  // Delayed consequences that haven't triggered yet
  dormantThreads: DormantThread[];

  // Current session
  session: SessionState | null;
}
```

### NPC Structure (with Agendas)
```typescript
interface NPC {
  id: string;
  name: string;
  faction: string | null;

  // What makes them a person, not a prop
  agenda: {
    wants: string;           // "Protect her daughter's future"
    fears: string;           // "Being seen as a collaborator"
    leverage: string | null; // What they have over the player
    owes: string | null;     // What they owe the player
  };

  // Relationship state
  disposition: "hostile" | "wary" | "neutral" | "warm" | "loyal";
  lastInteraction: string;   // Brief summary

  // Memory
  remembers: string[];       // Key facts about player actions
}
```

### Character State
```typescript
interface Character {
  id: string;
  name: string;

  background:
    | "Intel Operative"
    | "Medic/Field Surgeon"
    | "Engineer/Technician"
    | "Negotiator/Diplomat"
    | "Scavenger/Salvager"
    | "Combat Specialist";

  expertise: string[];

  affiliation: "aligned" | "neutral";
  alignedFaction?: string;

  credits: number;
  gear: GearItem[];

  // Social Energy (fully customizable)
  socialEnergy: {
    name: string;            // "Pistachios", "Battery", etc.
    current: number;         // 0-100
    resetRitual: string;     // "Tuning my gear in silence"
    personalTrigger: {       // +5% drain when triggered
      situation: string;
      active: boolean;
    };
    sanctuary: {             // +5% recovery bonus
      place: string;
      active: boolean;
    };
  };

  establishingMoment?: string;

  // Enhancements with active leverage
  enhancements: Enhancement[];

  hingeHistory: HingeMoment[];
}
```

### Enhancement (with Leverage Tracking)
```typescript
interface Enhancement {
  id: string;
  name: string;
  source: string;           // Which faction
  benefit: string;
  cost: string;

  // Active leverage state
  leverage: {
    lastCalled: string | null;    // When faction last demanded something
    pendingObligation: string | null;  // What they currently want
    complianceCount: number;      // Times player complied
    resistanceCount: number;      // Times player refused
  };
}
```

### Dormant Thread (Delayed Consequences)
```typescript
interface DormantThread {
  id: string;
  origin: string;           // Which decision created this
  triggerCondition: string; // "When player returns to Sector 7"
  consequence: string;      // What happens
  severity: "minor" | "moderate" | "major";
  createdSession: number;
}
```

### Session State
```typescript
interface SessionState {
  missionId: string;
  missionTitle: string;
  missionType: "Investigation" | "Rescue" | "Diplomacy" | "Sabotage" | "Escort";

  phase: "briefing" | "planning" | "execution" | "resolution" | "debrief" | "between";

  // Briefing structure (explicit dilemma framing)
  briefing: {
    situation: string;
    requestor: string;
    competingTruths: string[];  // The legitimate tensions
    stakes: string;
  };

  activeNPCIds: string[];  // References to npcs.active
}
```

### History Entry (Unified)
```typescript
interface HistoryEntry {
  id: string;
  session: number;
  type: "mission" | "hinge" | "faction_shift" | "consequence" | "canon";

  summary: string;

  // Optional structured data depending on type
  mission?: {
    title: string;
    whatWeTried: string;
    result: string;
    immediateConsequence: string;
  };

  hinge?: {
    situation: string;
    choice: string;
    reasoning: string;
  };

  factionShift?: {
    faction: string;
    from: string;
    to: string;
    cause: string;
  };

  // Marks entry as permanent world-change (canon)
  isPermanent: boolean;
}
```

---

## Tool Definitions

### Query Tools (Read-Only)

```typescript
tool query_state {
  description: "Read current game state without modification"
  parameters: {
    query:
      | { type: "character", characterId: string }
      | { type: "faction", faction: string }
      | { type: "npc", npcId: string }
      | { type: "social_energy", characterId: string }
      | { type: "enhancements", characterId: string }
      | { type: "active_npcs" }
      | { type: "dormant_threads" }
      | { type: "history", limit?: number }
  }
  returns: {
    data: any;
    narrativeHint?: string;  // e.g., "They're running on fumes"
  }
}
```

### Dice Tools

```typescript
tool roll_check {
  description: "Roll d20 + modifier for a skill check"
  parameters: {
    characterId: string;
    skill: string;
    dc: 10 | 14 | 18 | 22;
    advantage?: boolean;
    disadvantage?: boolean;
  }
  returns: {
    rolls: number[];        // All dice rolled
    used: number;           // The one that counted
    modifier: number;
    total: number;
    success: boolean;
    margin: number;
  }
}

tool tactical_reset {
  description: "Spend social energy for advantage on next social roll"
  parameters: {
    characterId: string;
    ritualDescription: string;  // How they reset
  }
  returns: {
    newSocialEnergy: number;
    narrativeHint: string;
    advantageGranted: boolean;
  }
  // Costs 10% social energy, grants advantage on next social roll
}
```

### Mutation Tools

```typescript
tool update_character {
  description: "Modify character state"
  parameters: {
    characterId: string;
    changes: {
      credits?: number;           // Delta
      socialEnergy?: number;      // Delta
      addGear?: GearItem[];
      removeGear?: string[];
      triggerPersonalTrigger?: boolean;  // Activates +5% drain
      enterSanctuary?: boolean;          // Activates +5% recovery
    }
  }
  returns: {
    before: Partial<Character>;
    after: Partial<Character>;
    narrativeHint: string;      // "Credits tight now" / "Feeling centered"
  }
}

tool update_faction {
  description: "Shift faction standing"
  parameters: {
    faction: string;
    delta: -2 | -1 | 1;
    reason: string;
  }
  returns: {
    before: string;
    after: string;
    consequence?: string;  // Auto-generated ripple
  }
}

tool update_npc {
  description: "Modify NPC state"
  parameters: {
    npcId: string;
    changes: {
      disposition?: string;
      addMemory?: string;
      updateAgenda?: Partial<NPC["agenda"]>;
      moveToActive?: boolean;
      moveToDormant?: boolean;
    }
  }
}

tool call_in_leverage {
  description: "A faction demands something from an enhanced character"
  parameters: {
    characterId: string;
    enhancementId: string;
    demand: string;
  }
  // Records the pending obligation, player must respond
}
```

### Chronicle Tools

```typescript
tool log_history {
  description: "Record an event in campaign history"
  parameters: {
    type: "mission" | "hinge" | "faction_shift" | "consequence";
    summary: string;
    isPermanent: boolean;  // True = canon-level change
    details?: object;      // Type-specific structured data
  }
}

tool queue_dormant_thread {
  description: "Schedule a delayed consequence"
  parameters: {
    origin: string;
    triggerCondition: string;
    consequence: string;
    severity: "minor" | "moderate" | "major";
  }
}

tool surface_dormant_thread {
  description: "Activate a dormant consequence"
  parameters: {
    threadId: string;
    activationContext: string;  // Why now?
  }
  // Moves thread to history and triggers narrative
}
```

### Session Tools

```typescript
tool start_mission {
  description: "Begin a new mission"
  parameters: {
    title: string;
    type: string;
    briefing: {
      situation: string;
      requestor: string;
      competingTruths: string[];
      stakes: string;
    };
  }
}

tool set_phase {
  description: "Transition mission phase"
  parameters: {
    to: "briefing" | "planning" | "execution" | "resolution" | "debrief" | "between";
  }
  // Phase tracked in conversation, tool just updates state file
}

tool end_session {
  description: "Save and close current session"
  parameters: {
    summary: string;
    resetSocialEnergy: boolean;  // Usually true unless fiction prevents
  }
}
```

### Persistence Tools

```typescript
tool save_campaign {
  description: "Write current state to disk"
  // Automatic versioning, creates backup of previous save
}

tool load_campaign {
  description: "Load campaign from disk"
  parameters: {
    campaignId: string;
  }
  returns: {
    version: string;
    migrated: boolean;  // True if schema was upgraded
    summary: string;    // Quick recap for context
  }
}
```

---

## Prompt Architecture

### Split Prompt Design

Instead of one massive prompt, use modular hot-reloadable files:

```
prompts/
├── core.md              # Agent identity, tone, principles (~50 lines)
├── mechanics.md         # Condensed rules reference (~50 lines)
├── gm_guidance.md       # How to run good scenes (~30 lines)
├── state_summary.md     # Template for injecting current state
└── examples/
    ├── good_gm_response.md
    ├── npc_interaction.md
    └── hinge_moment.md
```

### Mechanical Reference (50-line extract)

```markdown
# SENTINEL Quick Reference

## Rolls
d20 + 5 (trained) vs DC 10/14/18/22
Advantage: roll 2d20, take higher
Disadvantage: roll 2d20, take lower

## Social Energy (0-100%)
- 51-100: Normal
- 26-50: Disadvantage on social rolls
- 1-25: Disadvantage on all interpersonal
- 0: Complex social auto-fails

Drain: -5 brief, -10 sustained, -15 high-stakes
Restore: +5/hr solitary work, +5-10 grounding ritual
Tactical Reset: -10% → advantage on next social roll

## Reputation Scale
Hostile → Unfriendly → Neutral → Friendly → Allied
Help: +1 | Oppose: -1 | Betray: -2

## Mission Flow
Briefing → Planning → Execution → Resolution → Debrief

## Between Missions
Rest | Shop | Research | Social scenes
Social energy resets (unless fiction prevents)

## Enhancement Leverage
Factions may call in obligations at any time.
Compliance or resistance both have consequences.
```

### State Summary Template

```markdown
## Current State

**Session:** {sessionCount} | **Phase:** {campaign.phase}
**Mission:** {session.missionTitle} ({session.phase})

**Party:**
{for each character}
- {name} ({background}): {credits}cr, {socialEnergy.name} {socialEnergy.current}%
  {if socialEnergy.current < 50}⚠️ {narrativeHint}{/if}
{/for}

**Active NPCs:**
{for each activeNPC}
- {name}: wants {agenda.wants}, fears {agenda.fears}
  Disposition: {disposition} | Remembers: {remembers.join(", ")}
{/for}

**Faction Tensions:**
{list any non-neutral standings}

**Dormant Threads:** {dormantThreads.length} pending
{if any high severity}⚠️ Major consequence waiting: {triggerCondition}{/if}
```

---

## Testing Strategy

### 1. Golden Transcripts
Record ideal GM behavior for regression testing:

```
tests/golden/
├── 01_character_creation.json
├── 02_simple_skill_check.json
├── 03_social_energy_depletion.json
├── 04_faction_shift.json
├── 05_npc_with_agenda.json
├── 06_hinge_moment.json
├── 07_enhancement_leverage.json
├── 08_dormant_thread_triggers.json
├── 09_tactical_reset.json
└── 10_mission_debrief.json
```

Each transcript contains:
- Player input
- Expected tool calls (or acceptable alternatives)
- Expected state changes
- Quality criteria for response (checklist)

### 2. Boundary Tests
Automated tests for edge cases:

```typescript
describe("Social Energy Boundaries", () => {
  test("at 0%, complex social auto-fails", ...);
  test("at 25%, disadvantage applies", ...);
  test("tactical reset denied when <10%", ...);
  test("sanctuary bonus applies correctly", ...);
  test("personal trigger stacks with scene cost", ...);
});

describe("Faction Boundaries", () => {
  test("hostile faction refuses help", ...);
  test("betrayal (-2) from allied still possible", ...);
  test("reputation can't exceed allied", ...);
});

describe("Enhancement Leverage", () => {
  test("pending obligation blocks benefits until resolved", ...);
  test("resistance count affects future demands", ...);
});
```

### 3. State Mutation Tests
Verify tools produce valid state:

```typescript
describe("Tool Integrity", () => {
  test("update_character produces valid Character", ...);
  test("update_faction maintains valid standing", ...);
  test("log_history increments correctly", ...);
  test("save/load roundtrip preserves all data", ...);
  test("version migration works for v1→v2", ...);
});
```

### 4. Vibe Checks (Manual Weekly)
Playtest with checklist:

```markdown
## Vibe Check Scorecard

Session Date: ____

### NPCs
- [ ] Had clear wants/fears that drove behavior
- [ ] Remembered previous interactions
- [ ] Felt like people, not quest givers

### Choices
- [ ] At least one meaningful dilemma presented
- [ ] No obvious "right answer"
- [ ] Consequences referenced past decisions

### Social Energy
- [ ] Depletion felt narratively earned
- [ ] Low energy was described, not just numbered
- [ ] Reset ritual was honored in fiction

### Pacing
- [ ] Mission phases felt distinct
- [ ] Debrief prompted reflection
- [ ] Dormant thread surfaced (if applicable)

### Overall
- [ ] Would play again
- [ ] Felt like a GM, not a rules engine
```

---

## Example Annotated Transcript

```
PLAYER: I approach the checkpoint guard.

AGENT THINKING:
- Player has 45% social energy (Frayed) → disadvantage on social
- Guard is NPC "Marta" - wants safe passage for her brother,
  fears being reported for bribery, remembers player helped
  Ember last mission
- Player is Unfriendly with Lattice (Marta's faction)

TOOL CALL: query_state({ type: "social_energy", characterId: "player1" })
RESULT: { current: 45, narrativeHint: "The small talk feels like sandpaper" }

AGENT RESPONSE:
"The checkpoint queue inches forward. When you reach the booth, you
recognize Marta from the transit authority—she processed your papers
once before. Her eyes flick to her terminal, then back to you.

'Documentation.' Her tone is flat, professional. But her fingers
hesitate over the keyboard.

You're running low—conversation feels like sandpaper today.
What do you do?"

---

PLAYER: I try to convince her to let me through quickly.

AGENT THINKING:
- This is a Persuasion check (trained for Negotiator background)
- DC 14 (Challenging) due to Unfriendly faction standing
- Disadvantage from Frayed social energy
- Marta's agenda: might be leverageable (her brother)

TOOL CALL: roll_check({
  characterId: "player1",
  skill: "Persuasion",
  dc: 14,
  disadvantage: true
})
RESULT: { rolls: [17, 8], used: 8, modifier: 5, total: 13,
          success: false, margin: -1 }

TOOL CALL: update_character({
  characterId: "player1",
  changes: { socialEnergy: -10 }
})
RESULT: { before: { socialEnergy: 45 }, after: { socialEnergy: 35 },
          narrativeHint: "Reserves dipping" }

AGENT RESPONSE:
"You lean in, keeping your voice low. 'I'm not looking for trouble.
Just need to get through—same as everyone.'

Marta's jaw tightens. The words that would normally flow aren't
coming easy today, and she can tell. Her hand moves toward the
alert toggle.

'Everyone has papers. Let me see yours.'

She's not buying it—not from someone Lattice flagged after the
Ember supply run. The interaction cost you more than it should have.
(Social energy: 35%)

You could try another angle. Or you could step back, regroup,
find another way. What's your move?"

---

PLAYER: I mention I might know someone who could help her brother.

AGENT THINKING:
- Player is leveraging NPC agenda (brilliant)
- This changes the dynamic entirely
- New check, but now she's conflicted
- This could create a dormant thread (favor owed)

TOOL CALL: update_npc({
  npcId: "marta",
  changes: {
    addMemory: "Player knows about my brother",
    disposition: "wary"  // upgraded from hostile due to leverage
  }
})

AGENT RESPONSE:
"Marta's hand freezes. Her eyes cut to the guard three booths over,
then back to you.

'What do you know about my brother?'

The professional mask slips—just for a second. There's fear
underneath. Whatever his situation is, it's real, and you've just
become a variable in it.

She lowers her voice. 'This isn't a conversation for the booth.
Bay 7, maintenance corridor, twenty minutes. Come alone.'

She stamps your papers without looking at them.

[You're through the checkpoint. But you've opened something that
won't close easily. Marta will remember this—and so will whoever
she's afraid of.]"

TOOL CALL: queue_dormant_thread({
  origin: "Leveraged Marta's brother situation at checkpoint",
  triggerCondition: "When player returns to Lattice territory OR Marta's brother becomes relevant",
  consequence: "Marta calls in the favor—or someone else learns player knows",
  severity: "moderate"
})
```

---

## MVP Scope (Revised)

### Phase 1: Playable Single Session
- [ ] State schema with versioning (JSON files)
- [ ] Core tools: roll_check, query_state, update_character, update_faction
- [ ] NPC structure with agendas
- [ ] Prompt loader with hot-reload
- [ ] 50-line mechanical reference
- [ ] CLI interface
- [ ] One complete mission playable end-to-end
- [ ] 3 golden transcripts for regression

### Phase 2: Campaign Continuity
- [ ] Full tool suite (chronicle, dormant threads, leverage)
- [ ] Save/load with migration support
- [ ] NPC memory across sessions
- [ ] Dormant thread triggering
- [ ] Between-missions phase
- [ ] 10 golden transcripts
- [ ] Boundary test suite

### Phase 3: Polish
- [ ] Mission generator from templates
- [ ] Faction AI (proactive demands)
- [ ] Vibe check automation (partial)
- [ ] Discord interface
- [ ] Multiplayer state management

---

## File Structure

```
sentinel-agent/
├── src/
│   ├── agent.py              # Main agent orchestration
│   ├── state/
│   │   ├── schema.py         # Pydantic models
│   │   ├── manager.py        # Load/save/migrate
│   │   └── migrations/       # Version upgrade scripts
│   ├── tools/
│   │   ├── dice.py
│   │   ├── query.py
│   │   ├── character.py
│   │   ├── faction.py
│   │   ├── npc.py
│   │   ├── chronicle.py
│   │   └── session.py
│   └── interface/
│       └── cli.py
├── prompts/
│   ├── core.md
│   ├── mechanics.md
│   ├── gm_guidance.md
│   └── examples/
├── tests/
│   ├── golden/
│   ├── boundary/
│   └── integration/
├── campaigns/               # Saved game states
└── README.md
```

---

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| Single player or party? | **Single player for MVP**, multiplayer Phase 3 |
| SQLite vs JSON? | **JSON for MVP**, evaluate migration at Phase 2 |
| Hidden consequences? | **Let Claude decide dynamically**, no pre-planning |
| Chronicle vs Canon? | **Merged into unified history** with `isPermanent` flag |
| Full rulebook in prompt? | **50-line extract + hot-reload** |

---

## Remaining Open Questions

1. **Voice integration?** Would speech-to-text improve immersion enough to justify complexity?
2. **Multiplayer architecture?** When we get there—turn-based or real-time? Shared state sync?
3. **Canon export format?** For community sharing of campaign histories
