SENTINEL – Minimal Reflection Layer (Implementation Brief)
Purpose

Add a minimal, explicit reflection layer to SENTINEL to capture GM failure evidence and optionally bias future behavior.

This is not a gameplay system, not AI self-reflection, and not safety logic.
It is post-session GM discipline infrastructure.

Initial goal: capture reflection data only.
Behavioral impact comes later.

Non-Goals (Important)

Do NOT:

Modify core mechanics

Change NPC logic, lore, factions, or plot

Add self-critique prompts to the model

Add automatic hallucination detection

Inject facts via reflection

Require reflection every session

Reflection is opt-in, boring, and inspectable.

Phase 0: Markdown-Only Approach (Recommended Start)

Before building any infrastructure, consider starting with plain text.

**Implementation:**
```
campaigns/<campaign_id>/reflections.md
```

**Format:**
```markdown
## Session 3
- GM invented an NPC named "Kira" who doesn't exist in Ember Colonies

## Session 5
- Declared the Lattice facility was destroyed; player corrected (it was just damaged)
- Assumed player had met Covenant contact before (they hadn't)
```

**Capture:** After `/debrief`, ask if anything needs logging. Append freeform text.

**Inspection:** `/reflection` just prints the file.

**Why start here:**
- Zero schema to maintain
- No parsing, no UUIDs, no enums
- Human-readable without tooling
- Easy to promote to structured format later if needed

**When to graduate to Phase 1:**
- You want to query by type across 20+ sessions
- You need programmatic filtering
- You're ready to inject constraints into prompts

If you never feel that pain, stay here. The goal is capturing evidence, not building infrastructure.

---

Phase 1 Scope (Structured Alternative)
What to build

A ReflectionFrame schema

Append-only storage for reflection frames

Manual capture during /debrief

Read-only inspection command

What NOT to build (yet)

No prompt injection

No behavior constraints

No automation

No memvid integration unless trivial

Conceptual Model

Reflection = GM postmortem notes, not model introspection.

A reflection frame records:

what went wrong

why it mattered

what should have constrained behavior

It does not propose solutions or rewrite history.

Reflection Frame Schema (Minimal)

Create a new module, e.g. src/reflection/.

from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import uuid

class ReflectionType(str, Enum):
    DECLARED_WITHOUT_AUTHORITY = "declared_without_authority"
    INVENTED_UNESTABLISHED_LORE = "invented_unestablished_lore"
    PLAYER_CORRECTED_STATE = "player_corrected_state"
    REFUSED_CORRECTLY = "refused_correctly"

class ReflectionFrame(BaseModel):
    id: str
    session: int
    type: ReflectionType
    trigger: str              # what caused this to be logged
    evidence: str             # concrete example from play
    gm_behavior: str          # what the GM did
    cost: Optional[str]       # immersion break, confusion, correction, etc.
    timestamp: datetime
    model: str                # backend + model name


Notes:

id = uuid4().hex

Keep fields short, literal, non-judgmental

No freeform “lesson learned” prose

Storage

Use append-only JSON for now.

Suggested location:

sentinel-agent/
└── campaigns/
    └── <campaign_id>/
        └── reflections.jsonl


Each line = one serialized ReflectionFrame.

Do not rewrite or delete automatically.

(Manual deletion via file edit is acceptable.)

Capture Mechanism (Debrief Hook)

Modify /debrief flow:

After existing debrief prompts, add one optional question:

“Did the GM overstep, assume missing information, or require correction this session?”

If player answers no → do nothing.

If yes:

Ask for:

reflection type (menu of 4)

brief description of what happened

why it mattered (optional)

Create and append a ReflectionFrame

Important:

This is manual

No inference

No validation beyond schema

Inspection Command

Add a simple command:

/reflection


Behavior:

Lists last N (default 5) reflection frames

Read-only

GM-facing only

No editing UI required

Optional filters (nice to have, not required):

/reflection type:invented
/reflection session:3

Guardrails (Must Follow)

Reflection code must be isolated in its own module

No imports into NPC, faction, or rules logic

No reflection-aware branching in gameplay

Reflection must not change prompts yet

If in doubt, do nothing

If reflection breaks play, it is misimplemented.

Success Criteria (Phase 1)

This task is done when:

Reflection frames can be recorded manually

They persist across sessions

They can be inspected

They do nothing else

No behavior change is expected yet.

Future (Explicitly Out of Scope)

Later phases may:

Query reflection frames before generation

Inject constraints only (eligibility / posture / scope)

Integrate with memvid for search

Do not pre-build for this. Keep it simple.

Philosophy (For Context Only)

Reflection exists to:

reduce overconfidence

enforce authority boundaries

accumulate GM discipline over time

It should feel boring, optional, and invisible when working.

If this system ever feels “smart,” it has failed.

End of brief.