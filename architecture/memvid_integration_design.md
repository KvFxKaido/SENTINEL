# Memvid Integration — SENTINEL Design Draft

> **Status:** Exploratory / Not Canon  
> **Purpose:** Evaluate whether and how memvid can be integrated into SENTINEL without violating core narrative, mechanical, or philosophical constraints.

---

## 1. Framing Principle

**Memvid is not memory.**

In SENTINEL terms, memvid represents **recorded evidence**: an immutable, lossy artifact of past events that can be queried, interpreted, distorted, or withheld.

This distinction is non-negotiable.

If memvid ever becomes a source of objective truth, authoritative recall, or perfect continuity, integration has failed.

---

## 2. Why Consider Memvid at All?

SENTINEL already behaves like an append-only world:

- Dormant threads
- Hinge moments
- Consequences that bloom later
- NPC memory shaped by perspective, not facts

Memvid aligns structurally with this model by offering:

- Immutable frames (append-only)
- Cheap, portable storage (single file)
- Fast semantic retrieval
- No database or server dependency

The question is not whether memvid fits technically, but whether it can be constrained ethically and narratively.

---

## 3. Explicit Non-Goals (Hard Constraints)

Memvid must never:

- Act as a global truth store
- Enable perfect recall for players or NPCs
- Replace ambiguity with certainty
- Allow free rewind/replay of past scenes
- Collapse factional disagreement into consensus

Any design that violates these is rejected outright.

---

## 4. Conceptual Mapping

### 4.1 Frames

| Memvid Concept | SENTINEL Mapping |
|----------------|------------------|
| Frame | Session artifact or event slice |
| Keyframe | Hinge moment |
| Frame sequence | Campaign timeline |

Frames are append-only and immutable once written.

---

### 4.2 Memory vs Evidence

- **Evidence (memvid):** what was recorded
- **Memory (NPC/Player):** what is believed, recalled, or misremembered

NPC behavior must be driven by memory, not raw evidence.

---

## 5. Approved Integration Zones

### 5.1 Internal GM / Agent Recall (Phase 1)

**Audience:** AI GM only

**Purpose:**
- Replace keyword lore retrieval
- Improve consistency without surfacing authority
- Reduce context sludge

**Rules:**
- GM queries memvid internally
- Retrieved content is summarized, filtered, and faction-colored before use
- Raw frames are never exposed

---

### 5.2 NPC Subjective Memory

Each NPC may maintain a personal memvid slice:

- Limited to events they plausibly witnessed or learned about
- Lossy by default
- Biased by faction ideology
- Corrupted by fear, loyalty, or misinformation

NPCs never query the full campaign memvid.

This directly supports:
- `lie_to_self`
- Trauma-shaped recall
- Conflicting testimonies

---

### 5.3 Hinge Moment Recording

When a hinge is detected:

1. A memvid keyframe is written
2. Frame is immutable
3. Frame is interpretable, not replayable

Later systems may reference the hinge without re-enacting it verbatim.

---

## 6. Faction-Mediated Access (Phase 2)

If memvid is ever surfaced fictionally, it must be mediated.

### Example Access Models

| Faction | Access Style |
|---------|-------------|
| **Witnesses** | Curated playback with redactions |
| **Ghost Networks** | Fragmented or corrupted frames |
| **Nexus** | Statistical summaries, not scenes |
| **Architects** | Procedural records, stripped of emotion |

Access should always:
- Cost something
- Introduce bias
- Create new consequences

---

## 7. Explicitly Rejected Uses

The following are out of scope:

- Player-accessible global search
- "What did we say about X three sessions ago" recall
- Canon verification tools
- Time-travel correction of decisions
- **Meta-Memory** (new addition):
  - Players cannot query "what NPCs remember about me"
  - No "reputation calculator" showing exact standing math
  - Memory state is discovered through interaction, not inspection

**Forgetting is a feature.**

The only way to know what someone remembers is to *ask them* or *observe their behavior*.

---

## 8. Replacement, Not Accretion

Memvid may only be integrated if it replaces existing systems.

**Potential replacements:**
- Keyword-based lore retrieval
- Ad-hoc NPC memory blobs
- Redundant session summaries

If memvid becomes "one more layer," it should be removed.

---

## 9. Open Design Questions — RESOLVED

### Q1: How lossy should NPC memvid slices be by default?

**Answer:** Faction-dependent baseline with three decay mechanisms.

**Faction Fidelity Profiles:**

| Faction | High Fidelity | Degraded | Notes |
|---------|--------------|----------|-------|
| **Nexus** | Data, metrics, patterns | Emotional context, names | Remembers numbers, forgets people |
| **Ember** | Relationships, trust networks | Logistics, exact counts | Remembers who helped, forgets supply details |
| **Witnesses** | Events, timestamps | Interpretation, motive | Records what happened, not why |
| **Ghost Networks** | Operational security gaps | Intentionally corrupted | Memory practice, not malfunction |
| **Covenant** | Doctrine, ritual | Dissent, contradiction | Faith-shaped recall |
| **Lattice** | Technical specs | Human nuance | Enhanced recall, augmented gaps |

**Decay Rates:**
- **Non-critical details:** 5% per session
- **Hinges + witnessed trauma:** 0% (permanent)
- **Contradictory evidence:** Faster decay if conflicts with faction worldview

---

### Q2: Should corruption be probabilistic or faction-driven?

**Answer:** Both, layered in three stages.

**Corruption Model:**

1. **Structural Bias (faction-driven):** Constant, predictable filtering
   - Ember NPC viewing Nexus surveillance = "threat" framing
   - Nexus analyst viewing Ember autonomy = "inefficiency" framing
   
2. **Traumatic Corruption (event-driven):** Fear reshapes memory around specific incidents
   - Witnessed violence creates gaps or exaggerations
   - Betrayal experiences color future similar interactions
   
3. **Decay Noise (probabilistic):** Natural degradation over time
   - Small details drift
   - Exact wording becomes paraphrase
   - Timing becomes approximate

**Example Cascade:**
- Ember NPC witnesses Nexus surveillance
- Structural bias: "threat"
- Trauma: "betrayal" (if trusted Nexus before)
- Decay: Uncertainty about specific technical details over sessions

---

### Q3: Do hinge frames ever decay, or only interpretations?

**Answer:** Hinges never decay. Interpretations always shift.

**Immutable:** The fact that you refused the enhancement.

**Fluid:** The meaning of that refusal evolves:
- **Session 1:** "I value autonomy"
- **Session 10:** "I was naive"
- **Session 20:** "I should have taken the power when I could"

**Implementation:**
- Hinge keyframes stored with zero decay
- Interpretation metadata stored separately with drift enabled
- NPCs can reference same hinge with contradictory meanings

This is critical: the world remembers your choices forever, but understanding of those choices is fluid.

---

### Q4: What does it cost to access evidence in-world?

**Answer:** Tiered costs based on access method.

#### Personal Recall (NPC asking themselves)
- **Recent events:** Free
- **Traumatic memories:** Social energy cost
- **Distant memories:** Time passage makes recall harder, disadvantage on related checks

#### Asking Someone Else
- **Cost:** Reputation (mild) + social energy for both parties
- **Risk:** Distorted account, NPC may lie or misremember
- **Consequence:** They remember you asked

#### Faction Archives (Witnesses, Architects)
- **Cost:** Formal request (reputation hit if denied) + time delay (1-3 sessions)
- **Result:** Heavily redacted/interpreted, faction-colored
- **Consequence:** Creates paper trail, others may know you inquired

#### Illegal Access (Ghost Networks, hacking)
- **Cost:** Resources + time + skill check
- **Risk:** Discovery creates new enemies, triggers dormant threads
- **Result:** Incomplete/corrupted data
- **Consequence:** Permanent relationship damage if caught

**Design Principle:** More accurate information costs more and creates more consequences.

---

## 10. Provisional Verdict

Memvid is philosophically compatible but narratively dangerous.

It is acceptable only if treated as:

> **Evidence without authority**

Integration should proceed, if at all, cautiously, internally first, and with explicit safeguards against truth collapse.

---

## 11. Integration Roadmap (If Approved)

### Phase 1: Internal Only (Q1 Implementation)
**Goal:** Replace keyword lore retrieval, zero player visibility

- GM queries memvid for semantic lore retrieval
- Results filtered through faction lens before use
- No player-facing changes
- Backwards compatible with existing campaign files

**Success Metric:** GM consistency improves, context sludge reduces

---

### Phase 2: NPC Memory (Q2 Implementation)
**Goal:** Each NPC gets personal memvid slice

- Bounded by plausible knowledge (what they could witness/learn)
- Corruption rules applied per faction profiles
- Drives NPC behavior, not exposed to players
- Still no player access to raw data

**Success Metric:** NPCs remember consistently but incorrectly, creating conflicting testimonies

---

### Phase 3: Faction Archives (Q3 Implementation)
**Goal:** Limited, mediated player access

- Only through faction-specific interfaces
- Always costs something (reputation, time, resources)
- Always introduces bias
- Creates new consequences

**Success Metric:** Players use archives strategically, not reflexively

---

### Never Implement:
- Global truth store
- Player meta-tools ("show me what X remembers")
- Perfect recall mechanics
- Rewind/replay functionality
- Consensus verification

---

## 12. Next Steps (If Proceeding)

**Before any code:**
1. Draft data flow diagram (conceptual only)
2. Write corruption/bias rules as prose
3. Identify exact systems to replace (not add to)
4. Prototype internal-only retrieval in isolated branch

**Kill Criteria:**
- If it becomes "one more system" instead of replacement
- If players start treating it as objective truth
- If NPC behavior becomes too predictable
- If forgetting stops being a feature

---

## 13. Final Note

This document is exploratory. Nothing here is canon until explicitly promoted.

The question is not "Can we integrate memvid?" but "Should we?"

And if the answer is yes, the next question is: "How do we keep it from becoming what we're building against?"

---

## Appendix A: Implementation Sketches

> **Note:** These are reference implementations, not production code. Actual implementation should follow SENTINEL's existing patterns.

### A.1 Core State Adapter

```python
# sentinel-agent/src/state/memvid_adapter.py
from memvid_sdk import Memvid, PutOptions, SearchRequest
from datetime import datetime

class MemvidGameState:
    def __init__(self, campaign_file="campaign.mv2"):
        self.mv = Memvid.create(campaign_file)

    def save_turn(self, game_state, choices, npcs_affected):
        """Save complete turn state as Smart Frame"""
        frame_data = {
            "turn": game_state.turn_number,
            "session": game_state.session_number,
            "player_state": game_state.player.__dict__,
            "faction_standings": game_state.faction_standings,
            "choices_made": choices,
            "npc_changes": npcs_affected,
            "active_threads": game_state.consequence_threads,
        }

        opts = PutOptions.builder() \
            .title(f"Turn {game_state.turn_number}") \
            .tag("session", str(game_state.session_number)) \
            .tag("type", "turn_state") \
            .build()

        self.mv.put_json(frame_data, opts)
        self.mv.commit()

    def save_hinge_moment(self, choice, immediate_effects, dormant_threads):
        """Tag major decisions for easy retrieval"""
        frame_data = {
            "choice": choice,
            "immediate": immediate_effects,
            "dormant": dormant_threads,
            "timestamp": datetime.now().isoformat(),
        }

        opts = PutOptions.builder() \
            .title(f"HINGE: {choice['description']}") \
            .tag("type", "hinge_moment") \
            .tag("severity", "high") \
            .build()

        self.mv.put_json(frame_data, opts)
        self.mv.commit()

    def query_timeline(self, query):
        """Search campaign history"""
        request = SearchRequest(
            query=query,
            top_k=10,
            snippet_chars=200
        )
        return self.mv.search(request)
```

### A.2 NPC Memory System

```python
# sentinel-agent/src/memory/memvid_npc.py

class MemvidNPCMemory:
    def __init__(self, memvid_instance):
        self.mv = memvid_instance

    def record_interaction(self, npc_name, player_action, npc_reaction,
                          disposition_change, context):
        """Store NPC memory as frame"""
        frame_data = {
            "npc": npc_name,
            "action": player_action,
            "reaction": npc_reaction,
            "disposition_delta": disposition_change,
            "context": context,
        }

        opts = PutOptions.builder() \
            .title(f"Interaction: {npc_name}") \
            .tag("npc", npc_name) \
            .tag("type", "npc_memory") \
            .build()

        self.mv.put_json(frame_data, opts)

    def get_npc_history(self, npc_name):
        """Retrieve all interactions with specific NPC"""
        results = self.mv.search(SearchRequest(
            query=f"npc:{npc_name}",
            top_k=50
        ))
        return [hit.json_data for hit in results.hits]

    def npc_remembers(self, npc_name, topic):
        """Check if NPC remembers something - returns (bool, hits)"""
        results = self.mv.search(SearchRequest(
            query=f"npc:{npc_name} {topic}",
            top_k=5
        ))
        return len(results.hits) > 0, results.hits
```

### A.3 Consequence Timeline

```python
# sentinel-agent/src/consequences/memvid_threads.py

class ConsequenceTimeline:
    def __init__(self, memvid_instance):
        self.mv = memvid_instance

    def create_thread(self, thread_id, trigger_choice, effects,
                     activation_condition, current_turn):
        """Create new consequence thread"""
        frame_data = {
            "thread_id": thread_id,
            "status": "dormant",
            "triggered_by": trigger_choice,
            "effects": effects,
            "activation": activation_condition,
            "created_turn": current_turn,
        }

        opts = PutOptions.builder() \
            .title(f"Thread: {thread_id}") \
            .tag("type", "consequence_thread") \
            .tag("status", "dormant") \
            .build()

        self.mv.put_json(frame_data, opts)

    def get_active_threads(self):
        """Get all currently active consequence threads"""
        results = self.mv.search(SearchRequest(
            query="type:consequence_thread status:active",
            top_k=20
        ))
        return [hit.json_data for hit in results.hits]

    def get_dormant_threads(self):
        """Get all dormant consequence threads"""
        results = self.mv.search(SearchRequest(
            query="type:consequence_thread status:dormant",
            top_k=20
        ))
        return [hit.json_data for hit in results.hits]
```

### A.4 CLI Commands

```python
# Add to sentinel-agent/src/interface/cli.py

@command
def timeline(args):
    """View campaign timeline"""
    if args.query:
        results = memvid_state.query_timeline(args.query)
        display_timeline_results(results)
    else:
        recent = memvid_state.query_timeline("type:turn_state")
        display_timeline(recent[:10])

@command
def rewind(session_num, turn_num):
    """Load earlier campaign state (requires confirmation)"""
    confirm = input(f"Rewind to Session {session_num}, Turn {turn_num}? (yes/no): ")
    if confirm.lower() == "yes":
        memvid_state.rewind_to_turn(turn_num)
        print("Campaign state restored.")

@command
def consequences():
    """Display consequence threads"""
    timeline = ConsequenceTimeline(memvid_state.mv)

    active = timeline.get_active_threads()
    dormant = timeline.get_dormant_threads()

    print("\nACTIVE THREADS")
    for thread in active:
        print(f"├─ {thread['thread_id']}")
        print(f"│  └─ Triggered by: {thread['triggered_by']}")

    print("\nDORMANT THREADS")
    for thread in dormant:
        print(f"└─ {thread['thread_id']} ({thread['activation']})")
        print(f"   └─ Triggered by: {thread['triggered_by']}")
```

### A.5 Frontend Bridge (TypeScript)

```typescript
// sentinel-ui/src/bridge/memvid_reader.ts
import { Memvid } from '@memvid/sdk';

export class CampaignReader {
    private mv: Memvid;

    constructor(campaignPath: string) {
        this.mv = Memvid.open(campaignPath);
    }

    async getRecentTurns(count: number = 10) {
        const results = await this.mv.search({
            query: "type:turn_state",
            topK: count
        });
        return results.hits.map(hit => hit.jsonData);
    }

    async getNPCInteractions(npcName: string) {
        const results = await this.mv.search({
            query: `npc:${npcName}`,
            topK: 50
        });
        return results.hits.map(hit => hit.jsonData);
    }

    async getConsequenceThreads() {
        const results = await this.mv.search({
            query: "type:consequence_thread",
            topK: 20
        });
        return results.hits.map(hit => hit.jsonData);
    }
}
```

---

## Appendix B: Migration Checklist

1. **Install SDK:** `pip install memvid-sdk`
2. **Create adapter:** Implement `MemvidGameState` class
3. **Parallel write:** Keep existing JSON saves, also write to `.mv2`
4. **Verify integrity:** Compare JSON and memvid outputs
5. **Add commands:** `/timeline`, `/consequences`
6. **Test with existing campaigns**
7. **(Optional) Build frontend** — only after CLI integration solid

---

## Feedback Sources

This document incorporates suggestions from:
- ChatGPT
- Claude (Chrome Extension)
- Claude Code
- Deepseek
- Kimi

---

**Version:** 1.1 - Implementation Sketches Added
**Contributors:** Shawn Montgomery (framework), Claude (question resolution, roadmap, code sketches)
**Status:** Awaiting decision on Phase 1 prototype
