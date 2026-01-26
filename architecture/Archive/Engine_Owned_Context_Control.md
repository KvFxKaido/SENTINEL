# SENTINEL Implementation Plan

## Engine-Owned Context Control (Rolling Window, Compression, Memory Strain)

**Goal:** Make context behavior deterministic, portable across backends, and narratively legible.

---

## 0) Non-goals

* No reliance on LM Studio / Ollama overflow policies.
* No “magic memory.” If it isn’t in the prompt pack (or state), the model cannot know it.
* No heavy infra required for v1 (embeddings/memvid optional).

---

## 1) Core concept: Prompt Pack

Every model call builds a **Prompt Pack** from bounded sections.

### 1.1 Sections (ordered)

1. **System / Identity** (static)
2. **Rules Reference** (static, minimal)
3. **Canonical State Snapshot** (dynamic, always)
4. **Campaign Memory Digest** (dynamic, compressed)
5. **Recent Transcript Window** (dynamic, rolling)
6. **Targeted Retrieval** (dynamic, optional, budgeted)
7. **User Input** (current turn)

### 1.2 Hard budgets (token-based)

**Use token counts, not character counts.** Character caps are unreliable because:
- 6,000 chars could be 1,500 tokens (English prose) or 3,000 tokens (structured data)
- Unicode, markdown, and JSON escaping skew character counts unpredictably

**Token budgets per section:**

* System/Identity: 1,500 tokens
* Rules: 2,000 tokens
* State Snapshot: 1,500 tokens
* Digest: 2,500 tokens
* Recent Window: 3,500 tokens
* Retrieval: 2,000 tokens
* **Total budget: ~13,000 tokens** (fits comfortably in 16k context with headroom)

**Tokenizer requirement:**
- Use `tiktoken` (cl100k_base) for counting - works offline, fast, MIT licensed
- Add as dependency: `tiktoken>=0.5.0`
- Fallback: if tokenizer unavailable, use `len(text) // 4` as conservative estimate

```python
try:
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    def count_tokens(text: str) -> int:
        return len(enc.encode(text))
except ImportError:
    def count_tokens(text: str) -> int:
        return len(text) // 4  # Conservative fallback
```

---

## 2) Data structures

### 2.1 Block log (already exists)

Each GM output is stored as a structured block:

* id, timestamp
* type: NARRATIVE | INTEL | CHOICE | SYSTEM
* text
* tags: [npc:..., faction:..., hinge:..., thread:...]

### 2.2 State snapshot (already exists in campaign JSON)

A stable, human-readable summary string assembled from:

* current mission + phase
* player stats (social energy, gear highlights)
* faction standings + last deltas
* NPCs: disposition + 1–2 key memories each
* active threads: pending consequences + triggers

### 2.3 Campaign Memory Digest (new)

A single text blob stored in campaign state:

* “Hinge Index” (last N hinges: situation → choice → consequence)
* “Standing Reasons” (why each key faction is where it is)
* “NPC Memory Anchors” (only the durable stuff)
* “Open Threads” (with trigger conditions)

This is **not** the transcript. It’s the durable memory layer.

---

## 3) Rolling Window policy (engine-owned)

### 3.1 Definition

**Rolling Window = SENTINEL selects only the most recent transcript blocks to send.**
Older blocks are excluded from the Prompt Pack.

### 3.2 Default window sizing

Start with a **block-count window** (simple, predictable):

* Default: last **12** blocks
* Min: last **4** blocks
* Max: last **20** blocks

Then enforce the **Recent Window character cap** by trimming oldest blocks until within budget.

### 3.3 Priority retention inside the window

When trimming within the window, drop in this order:

1. Low-signal SYSTEM chatter
2. Long NARRATIVE blocks
3. INTEL blocks
4. CHOICE blocks (keep if possible)

> Always keep at least: last GM CHOICE (if present) + last user input.

---

## 4) Memory Strain (deterministic thresholds)

### 4.1 Strain input

Compute an estimated “pack pressure” before sending:

* `pressure = used_chars / allowed_chars` for the assembled pack.

### 4.2 Thresholds

* **< 0.70**: Normal
* **0.70–0.85**: Strain I
* **0.85–0.95**: Strain II
* **≥ 0.95**: Strain III

### 4.3 What changes by Strain tier

**Strain I**

* Reduce Recent Window target blocks (e.g., 12 → 10)
* Retrieval budget becomes `minimal` (1 lore + 1 campaign snippet)

**Strain II**

* Replace older half of Recent Window with a **Scene Recap** paragraph
* Retrieval disabled unless explicitly requested by command

**Strain III**

* Recent Window becomes last 4–6 blocks only
* Digest becomes more prominent (ensure it fits; trim transcript first)
* GM instructed to acknowledge uncertainty and offer “/checkpoint”

> Optional: tie fiction/UI to tier: “Memory Strain active” banner + consequences.

---

## 5) Compression + checkpointing

### 5.1 Commands

* `/checkpoint`:

  * Generate/update Digest
  * Optionally export session summary
  * Prune transcript blocks older than N (archive to disk)
  * Clear “strain” state to Normal

* `/compress`:

  * Update Digest only (no pruning)

* `/clear` (no save):

  * Drop transcript beyond minimum window
  * Do **not** update Digest
  * Mark in history: `cleared_without_checkpoint: true`
  * **Narrative rule:** GM may reference the gap only when Strain II+ is active (never as a “gotcha”)

### 5.2 Digest generation strategy

Start simple: LLM-generated digest with strict schema.

* Provide current digest + last session summary + last K blocks
* Ask model to output updated digest in sections

Then validate:

* length caps
* required headings present

**Fallback (must not fail):**
If digest generation or schema validation fails, use deterministic template-based append:

* always preserve Hinge Index
* always preserve faction standings + reasons
* always preserve active threads + triggers

---

## 6) Retrieval integration (optional, budgeted)

### 6.1 Retrieval budget presets

* `minimal`: 1 lore + 1 campaign memory
* `standard`: 2 lore + 2 campaign memory
* `deep`: 3 lore + 5 campaign memory

### 6.2 Passive vs active retrieval (strain-aware)

* **Passive retrieval** (auto-injected): obey strain rules strictly.
* **Active retrieval** (via `/timeline`, `/lore`, `/search`): always attempt and return results out-of-band.

  * Injection of results into the next Prompt Pack is optional.
  * If injecting would raise strain tier, warn and suggest `/checkpoint` or proceeding without injection.

### 6.3 Rules

* Retrieval content must fit within Retrieval cap.
* Retrieval is the first thing to shrink during strain.

---

## 7) Backend interface

### 7.1 Unified LLM request payload

Create one “messages builder” that outputs OpenAI-style chat messages:

* system: identity + rules
* developer/system optional: state + digest + retrieval
* user: recent window + current input (or as separate messages)

### 7.2 Compatibility

* LM Studio (OpenAI-compatible)
* Ollama (OpenAI-compatible)
* Claude/OpenRouter/Gemini wrappers can use the same pack content.

---

## 8) UI/Telemetry

### 8.1 Context meter should reflect engine reality

* Show: `used_chars / allowed_chars` and strain tier
* Show which components are currently included:

  * Rules ✓ | State ✓ | Digest ✓ | Recent: 10 blocks | Retrieval: minimal

### 8.2 Debug command

* `/context debug`:

  * prints sizes per section
  * prints strain tier
  * prints what got trimmed and why

---

## 9) Testing plan

### 9.1 Unit tests

* Prompt packer respects per-section caps
* Rolling window retains required blocks
* Strain tier transitions are deterministic
* `/clear` does not update digest
* `/checkpoint` updates digest and prunes transcript

### 9.2 Golden tests

* Fixed campaign state + transcript produces identical pack output

### 9.3 Budget stress tests (add)

* If a single section exceeds its cap (especially State Snapshot), behavior is deterministic:

  * truncate with warning
  * log truncation
  * surface in `/context debug`

---

## 10) Milestones

### M1: Prompt packer (core)

* Implement section caps + pack assembly
* Implement rolling window trimming
* Add **anchor retention**: include hinge-tagged blocks even if older than window (trim non-hinges first)

### M2: Strain tiers + UI

* Compute pressure, expose tier
* Adjust budgets per tier

### M3: Digest + checkpoint commands

* Implement digest storage
* Implement `/checkpoint`, `/compress`, `/clear`
* Add digest fallback path

### M4: Retrieval budget enforcement

* Tie existing retrieval to budget + caps
* Implement passive vs active retrieval behavior

### M5: Polish

* “Memory Strain” fiction/UI hooks
* `/context debug`

---

## 11) Implementation notes (practical)

* **Use token counts from the start** - character counts are unreliable across content types.
* Always trim transcript before digest. Digest is the "memory contract."
* Define pressure against the **sum of section budgets**, not the backend's advertised context.
* Keep the pack assembly deterministic and logged. If it's surprising, it's a bug.
* **Hinge quotas** - enforce max hinged blocks per window + TTL to prevent hinge abuse.
* **Engine-inserted strain text** - don't rely on model to "acknowledge uncertainty"; inject it.
