# SENTINEL Mechanics Roadmap
**Game Systems Enhancement Plan**

---

## Overview

This document covers proposed game mechanics enhancements that go beyond UI/UX polish. These are systems-level changes to how the game tracks state, relationships, and consequences.

---

## 1. Inter-Faction Dynamics

**Current:** Player-to-faction relationships tracked independently.

**Proposed:** Faction-to-faction tensions that shift based on player actions.

### Faction Relationship Matrix

```python
faction_relations = {
    ("Nexus", "Ghost Networks"): -50,      # Deep rivalry
    ("Ember Colonies", "Cultivators"): +40, # Alliance
    ("Steel Syndicate", "Architects"): -10, # Tension
    ("Covenant", "Convergence"): -30,       # Ideological opposition
    ("Lattice", "Nexus"): +20,              # Technical cooperation
    ("Wanderers", "Ember Colonies"): +25,   # Mutual survival focus
}
```

### Cascading Effects

When player helps a faction, ripple effects occur:

```
Player helps Nexus (+20)
├── Nexus: +20 (direct)
├── Ghost Networks: -5 (rivals dislike you more)
├── Lattice: +3 (allies warm to you)
└── Ember Colonies: 0 (neutral relationship)
```

### Implementation Sketch

```python
def player_helps_faction(faction_helped, magnitude, context):
    # Direct benefit
    player_standing[faction_helped] += magnitude

    # Cascade through faction relationships
    for (f1, f2), relationship in faction_relations.items():
        if f1 == faction_helped:
            if relationship < -20:  # Rivals
                player_standing[f2] -= magnitude * 0.25
            elif relationship > 30:  # Allies
                player_standing[f2] += magnitude * 0.15
```

### Design Considerations

- Cascades should be **subtle**, not overwhelming
- Players should discover relationships through play, not spreadsheets
- Some factions are truly neutral — no cascades
- Major events (betrayals, alliances) create bigger ripples

---

## 2. NPC Individual Memory

**Current:** NPC disposition tied to faction standing.

**Proposed:** NPCs remember specific interactions independently of faction.

### Example State

```
Steel Syndicate: +15 (Friendly)
├── Commander Reeves: -20 (Hostile) — Player betrayed them personally
├── Merchant Guild: +30 (Allied) — Player saved their trade route
└── Enforcers: +10 (Neutral) — Haven't interacted much
```

### Behavior Changes

NPCs check **both** faction standing AND personal memory:

```python
def get_npc_disposition(npc, player):
    faction_base = player.standing[npc.faction]
    personal_modifier = npc.personal_memory.get(player.id, 0)

    # Personal memory weighs more than faction
    effective = (faction_base * 0.4) + (personal_modifier * 0.6)
    return disposition_from_score(effective)
```

### Narrative Opportunities

- Good faction standing but burned bridges with key NPC
- Bad faction standing but one NPC owes you
- NPCs gossip — personal reputation spreads within faction

---

## 3. Consequence Visualization

**New Command:** `/consequences` or `/threads`

### Display Format

```
ACTIVE THREADS
├─ "Ember Revenge" (2 turns until activation)
│  └─ Triggered by: Refused to help Ember Colonies (Session 7)
├─ "Architect Trust" (Active - next encounter)
│  └─ Triggered by: Shared intel with Architects (Session 8)

DORMANT THREADS
└─ "Ghost Networks Watching" (Activates: visit Nexus Hub)
   └─ Triggered by: Stole Ghost Networks data (Session 5)

RESOLVED THREADS (Last 5)
├─ "Wanderer Debt" (Completed Session 9)
└─ "Syndicate Contract" (Completed Session 8)
```

### Design Philosophy

- Show **enough** to feel weight of choices
- Don't spoil specific outcomes
- Countdown creates tension without certainty
- Dormant threads show trigger conditions, not effects

---

## 4. Session Summary System

**Auto-generated after each session:**

```
SESSION 7 SUMMARY
═══════════════════════════════════════════════════════

KEY CHOICES
├─ Refused Ember Colonies' aid request
├─ Shared Nexus intel with Architects
└─ Negotiated with Steel Syndicate traders

FACTION STANDING CHANGES
├─ Ember Colonies: +15 → -5 (▼ Major loss)
├─ Architects: +10 → +25 (▲ Gained trust)
└─ Steel Syndicate: +5 → +8 (△ Minor gain)

NEW CONSEQUENCE THREADS
├─ "Ember Revenge" (Dormant, activates in 3 turns)
└─ "Architect Alliance" (Active)

RESOLVED THREADS
└─ "Ghost Networks Investigation" (Completed)

NPCs ENCOUNTERED
├─ Commander Reeves (Syndicate) — Neutral → Friendly
├─ Elder Kara (Ember) — Friendly → Hostile
└─ Agent Voss (Nexus) — Suspicious → Suspicious

POTENTIAL PATHS FORWARD
├─ Mend relationship with Ember Colonies?
├─ Leverage Architect alliance for resources
└─ Investigate Ghost Networks activity in the Ruins
```

### Implementation Notes

- Generated from turn-by-turn state diffs
- "Potential Paths" are AI-suggested, not prescriptive
- Exportable as markdown for player notes
- Feeds into `/history` search

---

## 5. Character Arc Detection

**Beyond backgrounds:** Personal quests that emerge organically from play.

### How It Works

1. AI identifies patterns in player choices across sessions
2. Suggests character development paths that align with behavior
3. Creates optional personal quest threads

### Example Detection

```
EMERGENT CHARACTER ARC DETECTED
"The Reluctant Diplomat"

Your character consistently chooses negotiation over confrontation.
Observed in: Sessions 3, 5, 7, 8

Potential Arc Development:
├─ NPCs begin recognizing you as a mediator
├─ Factions might request you broker deals
├─ New dialogue options emphasizing reputation
└─ Unique consequences for breaking neutrality

Accept this arc? (Optional - does not restrict choices)
> [Yes] [No] [Ask me later]
```

### Design Principles

- **Never restrict** player choices
- Arcs are **recognition**, not rails
- Players can reject or ignore
- Arcs can shift if behavior changes
- Multiple arcs can coexist

### Pattern Categories

| Pattern | Arc Type | Example |
|---------|----------|---------|
| Consistent negotiation | Diplomat | "The Reluctant Mediator" |
| Faction loyalty | Partisan | "True Believer" |
| Information gathering | Broker | "The One Who Knows" |
| Violence avoidance | Pacifist | "The Unarmed" |
| Resource accumulation | Pragmatist | "The Prepared" |
| Betrayal pattern | Survivor | "Trust No One" |

---

## 6. Enhanced `/simulate` Command

**Current:** AI vs AI testing with player personas.

**Proposed:** Interactive "what if" exploration.

### New Subcommands

```bash
/simulate whatif <session> <turn> <alternate_choice>
# Branches timeline from past decision, shows potential divergence

/simulate preview <action>
# Shows potential immediate consequences without committing

/simulate npc <npc_name> <approach>
# Predicts NPC reaction to planned interaction
```

### Example: What-If

```
> /simulate whatif 5 12 "help Ember instead of refusing"

TIMELINE DIVERGENCE ANALYSIS
═══════════════════════════════════════════════════════

Original: Refused Ember aid request
Alternate: Helped Ember Colonies

PROJECTED DIFFERENCES (Sessions 5-7):
├─ Ember standing: -5 → +20 (significant shift)
├─ "Ember Revenge" thread: Would not exist
├─ Architect intel: Would not have been shared
│  └─ Architect standing: +25 → +10
└─ NPC Elder Kara: Hostile → Warm

BUTTERFLY EFFECTS:
├─ Session 6 Syndicate encounter: Different leverage
└─ Session 7 mission: Different faction support

Note: This is speculative. Actual outcomes depend on
choices not yet made.
```

### Example: NPC Preview

```
> /simulate npc "Commander Reeves" "ask for weapons shipment"

NPC REACTION PREVIEW: Commander Reeves
═══════════════════════════════════════════════════════

Current disposition: Neutral (personal: -5, faction: +15)

LIKELY REACTIONS:
├─ 60% — Negotiates terms (wants something in return)
├─ 25% — Refuses citing past grievance
└─ 15% — Agrees if approached correctly

FACTORS IN PLAY:
├─ Personal memory: You sided against them once
├─ Faction standing: Syndicate views you favorably
└─ Current context: They need allies

SUGGESTED APPROACHES:
├─ Acknowledge past tension first
├─ Offer concrete value, not promises
└─ Avoid mentioning Nexus (sore point)
```

### Design Guardrails

- Previews are **probabilistic**, not deterministic
- Never show exact outcomes — preserve uncertainty
- What-if is **exploratory**, not save-scumming
- NPC simulation based on established personality, not omniscience

---

## 7. Lore Integration in Dialogue

**Enhancement:** AI weaves actual quotes/references from lore into NPC dialogue.

### Implementation

When retrieving lore, extract notable quotes with metadata:

```python
lore_quotes = {
    "architects_foundation": {
        "quote": "We built this world.",
        "speaker": "Architect founding doctrine",
        "context": "Core philosophy",
        "arc": "Foundations"
    },
    # ...
}
```

### Example Dialogue

```
Commander Reeves: "As the Architects say, 'We built this world.'
But we're the ones who keep it running. Remember that."

[LORE REFERENCE: Architect founding doctrine]
```

### Benefits

- Creates continuity between lore and gameplay
- Rewards players who read the novellas
- Makes world feel cohesive and lived-in
- NPCs feel grounded in faction ideology

---

## 8. Unified Lore + Campaign Memory Queries

**Current:** Two separate retrieval systems:
- `LoreRetriever` — Static world knowledge from `lore/*.md` (keyword matching)
- `MemvidAdapter` — Dynamic campaign events (semantic search via memvid)

**Proposed:** Unified query interface that searches both sources simultaneously.

### Use Cases

When an NPC or faction is mentioned, pull both:
1. **Lore context** — Who are they? What do they believe?
2. **Campaign history** — What has the player done with them?

### Example Query

```python
# Player asks about Nexus during dialogue
results = unified_query("Nexus", context="npc_dialogue")

# Returns:
{
    "lore": [
        {"source": "factions/nexus.md", "content": "The network that watches..."},
        {"source": "canon_bible.md", "content": "Nexus monitors all infrastructure..."}
    ],
    "campaign": [
        {"type": "faction_shift", "session": 3, "summary": "Helped Nexus analyst"},
        {"type": "npc_interaction", "npc": "Cipher", "summary": "Shared intel"}
    ]
}
```

### Implementation Sketch

```python
class UnifiedRetriever:
    """Combines static lore with dynamic campaign memory."""

    def __init__(self, lore_retriever: LoreRetriever, memvid: MemvidAdapter):
        self.lore = lore_retriever
        self.memvid = memvid

    def query(
        self,
        topic: str,
        factions: list[str] | None = None,
        npc_id: str | None = None,
        limit_lore: int = 2,
        limit_campaign: int = 5,
    ) -> dict:
        """Query both lore and campaign history."""
        results = {"lore": [], "campaign": []}

        # Static lore
        lore_hits = self.lore.retrieve(
            query=topic,
            factions=factions,
            limit=limit_lore,
        )
        results["lore"] = [
            {"source": h.chunk.source, "content": h.chunk.content}
            for h in lore_hits
        ]

        # Campaign history (if memvid enabled)
        if self.memvid and self.memvid.is_enabled:
            if npc_id:
                campaign_hits = self.memvid.get_npc_history(npc_id, limit_campaign)
            else:
                campaign_hits = self.memvid.query(topic, top_k=limit_campaign)
            results["campaign"] = campaign_hits

        return results

    def format_for_prompt(self, results: dict) -> str:
        """Format unified results for GM context."""
        lines = []

        if results["lore"]:
            lines.append("## Lore Reference")
            for hit in results["lore"]:
                lines.append(f"*From {hit['source']}:* {hit['content'][:300]}...")
            lines.append("")

        if results["campaign"]:
            lines.append("## Campaign History")
            for hit in results["campaign"]:
                frame_type = hit.get("type", "event")
                session = hit.get("session", "?")
                summary = hit.get("narrative_summary") or hit.get("choice") or str(hit)[:100]
                lines.append(f"- S{session} [{frame_type}]: {summary}")
            lines.append("")

        return "\n".join(lines)
```

### Integration Points

1. **GM Context Building** — Before generating response, query both sources
2. **NPC Dialogue** — NPC references past interactions AND faction lore
3. **`/consult` Command** — Advisors draw on both canon and campaign events
4. **`/history` Enhancement** — Show lore context alongside campaign chronicle

### Design Considerations

- **Lore is authoritative** — Campaign can't contradict canon
- **Campaign adds specificity** — "Nexus is surveillance" + "You helped them in Session 3"
- **Graceful degradation** — Works with just lore if memvid disabled
- **Performance** — Lore is local keyword match; memvid is semantic search

---

## 9. API Boundary

Before building any UI, formalize the API boundary so any frontend can connect:

```python
# sentinel-agent/src/interface/api.py
class GameAPI:
    """JSON-serializable interface for any frontend"""

    def get_scene_state() -> Dict:
        """NPCs, location, choices, current context"""
        pass

    def get_dialogue_history() -> List[Message]:
        """Conversation history for current scene"""
        pass

    def submit_choice(choice_idx: int, custom_text: str = None):
        """Player makes a choice or improvises"""
        pass

    def get_npc_data(npc_id: str) -> Dict:
        """Portrait, disposition, agenda for specific NPC"""
        pass

    def get_player_state() -> Dict:
        """Social energy, faction standings, active threads"""
        pass
```

**Benefits:**
- Keep CLI unchanged
- Build web/desktop/mobile frontends simultaneously
- Allow third-party UIs
- Testable in isolation

---

## 10. Terminal UI Mockup

Reference implementation for Warp-style terminal with SENTINEL data:

```
SENTINEL Terminal v1.0
─────────────────────────────────────

NPC: Cipher (Nexus Analyst)
Disposition: Friendly [+12]
Location: Archive Terminal 7A
─────────────────────────────────────

[You approach the terminal. Cipher looks up from her screens.]

CIPHER: "The data doesn't match. Nexus records
show the shipment arrived, but Witness archives
say otherwise. Someone's rewriting history."

─────────────────────────────────────
Choices detected:
[1] 🔍 Ask about the discrepancy (Investigation)
    DC: 14, Energy: -10%

[2] 🤝 Suggest collaborating with Witnesses (Diplomacy)
    Faction: Nexus -2, Witnesses +1

[3] ⚡ Push for immediate action (Combat Specialist)
    Triggers: Leverage escalation with Steel Syndicate

[4] 💭 Something else...
─────────────────────────────────────
> _
```

**Warp Features to Steal:**
- Inline command preview — hover over choices to see consequences
- Smart autocomplete — `/consult faction:` shows all 11 factions
- Inline dice results — `🎲 17 + 5 = 22 (Success!)`
- Session branching — like Warp's command tree, but for narrative
- Inline lore tooltips — hover over faction names for quick info

---

## 11. Event-Driven UI Architecture

**Principle:** The frontend should **never interpret meaning** — only display state.

### Mental Model

```
AI produces narrative + tags
         ↓
Event normalization layer
         ↓
Frontend renders based on event type
```

This keeps: determinism, testability, replay/debug ability.

### Event Schema

Every GM output becomes a typed event:

```json
{
  "type": "npc_dialogue",
  "npc": "Archivist Hale",
  "faction": "Witnesses",
  "visual_state": "fractured",
  "stakes": "high",
  "disposition": "wary",
  "memory_triggered": true,
  "text": "We remember so you don't have to lie."
}
```

```json
{
  "type": "choice_block",
  "stakes": "hinge",
  "options": [
    {"id": 1, "text": "Accept the enhancement", "risk_hint": "faction_debt"},
    {"id": 2, "text": "Refuse", "risk_hint": "opportunity_cost"},
    {"id": 3, "text": "Negotiate terms", "risk_hint": "time_pressure"},
    {"id": 4, "text": "Something else...", "risk_hint": null}
  ]
}
```

```json
{
  "type": "state_change",
  "changes": [
    {"field": "faction_standing.ember", "old": 15, "new": -5},
    {"field": "social_energy", "old": 68, "new": 53}
  ]
}
```

### Benefits

- Backend owns all game logic
- Frontend is a pure renderer
- Events can be logged, replayed, tested
- Multiple frontends (CLI, desktop, web) consume same event stream

---

## Development Sequence

### Near-Term (Core Improvements)

1. ~~**Consequence Visualization**~~ — DONE
   - [x] `/consequences` command
   - [x] Thread status display
   - [x] Dormant thread countdown

2. ~~**Session Summaries**~~ — DONE
   - [x] Auto-generation on session end (`/debrief`)
   - [x] Export to markdown
   - [x] Standalone `/summary` command for any session

3. **NPC Individual Memory** — 1-2 weeks
   - Separate NPC reputation from faction
   - Personal interaction history
   - Dialogue references to memories

### Mid-Term (System Expansion)

4. **Inter-Faction Dynamics** — 2 weeks
   - Faction relationship matrix
   - Cascading effects system
   - Surface relationships through NPC dialogue

5. **Enhanced `/simulate`** — 2 weeks
   - What-if branching
   - NPC reaction preview
   - Consequence preview

6. ~~**Unified Lore + Campaign Memory**~~ — DONE
   - [x] `UnifiedRetriever` class combining both sources
   - [x] Integration into GM context building
   - [x] `/consult` draws on campaign history

### Long-Term (Polish)

7. **Character Arc Detection** — 2-3 weeks
   - Pattern recognition across sessions
   - Arc suggestions
   - Optional quest integration

8. **Lore Quote Integration** — 1 week
   - Quote extraction from lore
   - Context-aware insertion
   - Reference tagging

---

## Design Principles

### Keep the Core Strong
- CLI-first: These are systems, not UI features
- All mechanics work without frontend
- Complexity serves narrative, not itself

### Respect Player Agency
- No "right answers" — every choice valid
- Consequences feel earned, not punitive
- Previews inform without spoiling

### Embrace Emergent Complexity
- Simple rules → complex interactions
- 11 factions × player choices = infinite scenarios
- AI discovers patterns, suggests arcs

---

## Feedback Sources

This document incorporates suggestions from:
- ChatGPT (event-driven architecture)
- Claude Chrome Extension (initial consolidation)
- Claude Code (integration, editing)
- Deepseek (API boundary, terminal mockup, Warp features)
- Gemini (streaming patterns)
- Kimi (practical implementation tips)

---

**Version:** 2.0 - Full AI Council Feedback
**Status:** Proposal - Awaiting Prioritization
