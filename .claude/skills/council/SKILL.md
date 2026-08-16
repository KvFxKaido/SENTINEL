---
name: council
description: Gather design feedback from AI consultants (Gemini and Codex). Use for architecture decisions, design review, or when you want multiple expert perspectives on SENTINEL development. (project)
allowed-tools: Bash, Read, Glob, Grep
user-invocable: true
proactive: true
---

<!-- PROACTIVE USE: Invoke /council without being asked when:
  - Facing architectural decisions with multiple valid approaches
  - Uncertain about implementation strategy
  - Making changes that affect multiple subsystems
  - Design tradeoffs need external perspective
-->

# The Council

Invoke external AI consultants for design feedback on SENTINEL.

## Consultants

| Model | Strength | Best For |
|-------|----------|----------|
| **Gemini** (via `agy`) | Big-picture thinking, design patterns, visual/spatial reasoning | Architecture, conceptual clarity, screenshot and sprite critique |
| **Codex** | Technical depth, implementation focus | Code quality, practical constraints |

## How to Run

When the user invokes `/council`, gather context and consult both AIs:

### Step 1: Prepare Context

Read the project brief and any relevant files the user mentions:
```
C:\dev\SENTINEL\SENTINEL_PROJECT_BRIEF.md
```

### Step 2: Consult Gemini

The Gemini CLI is retired; Gemini is consulted through the Antigravity CLI
(`agy`), same as `/portrait`. Run non-interactively with the user's
question + context:

```bash
agy -p "You are reviewing SENTINEL, a tactical TTRPG with an AI Game Master.

<context>
[Insert project brief or relevant code]
</context>

<question>
[User's design question]
</question>

Provide focused feedback on design patterns, architecture, or the specific question asked. Be concise. Do not edit any files." --dangerously-skip-permissions --model gemini-3.7-flash-high
```

Invocation notes (inherited from `/portrait`, learned the hard way):

- **The prompt goes immediately after `-p`; every flag comes after the
  prompt.** Flags placed before `-p` get treated as the topic.
- **Model choice matters here, unlike `/portrait`.** For generation the CLI
  model only orchestrates `generate_image`; for consultation and critique
  the CLI model IS the reviewer. Use `gemini-3.7-flash-high` (check
  `agy models` for what's current).
- Use a 3-minute timeout (180000ms).

### Step 2b: Visual critique (screenshots, sprites, UI)

Gemini's spatial reasoning is the reason it holds this seat. `agy` has no
image flag, but the agent can **view image files it can reach** — grant the
directory with `--add-dir` and tell it to view the file (verified
2026-08-16: it read text and colors out of a probe PNG accurately).

```bash
agy -p "You are reviewing visual assets for SENTINEL, a tactical game with a
CRT-broadcast aesthetic. View the image file(s) named [FILES] in the
workspace directory, then answer:

<question>
[e.g. Does this walk cycle read as deliberate movement or as jank at a
glance? Is anything on this card unreadable at arm's length on a phone?]
</question>

Give a perceptual read, not a pixel measurement. Do not write or run
scripts; view the images directly. Do not edit any files." --add-dir "[DIR_CONTAINING_IMAGES]" --dangerously-skip-permissions --model gemini-3.7-flash-high
```

Aim it at **gestalt questions the deterministic checks cannot see** —
"does this read", "is this legible", "can a player find X on this screen".
Frame-to-frame mechanics (displacement, seams, anchoring) stay with the
pipeline's own pixel checks, which measure better than any eyeball. The
harness audition captures (`prototypes/walkable/test/audition-*/`) are
ready-made inputs.

### Step 3: Consult Codex

Run non-interactively:
```bash
codex exec "You are reviewing SENTINEL, a tactical TTRPG with an AI Game Master.

<context>
[Insert project brief or relevant code]
</context>

<question>
[User's design question]
</question>

Provide focused feedback on implementation, code quality, or the specific question asked. Be concise."
```

### Step 4: Synthesize

Present both perspectives, noting:
- Where they agree (strong signal)
- Where they differ (worth investigating)
- Actionable recommendations

## Example Usage

User: `/council` Should we use SQLite instead of JSON for campaign persistence?

Then:
1. Read `SENTINEL_PROJECT_BRIEF.md` and `src/state/schema.py`
2. Ask Gemini about data model evolution and query patterns
3. Ask Codex about migration complexity and performance
4. Synthesize into recommendation

## Tips

- Keep prompts focused on one question at a time
- Include relevant code snippets, not entire files
- The consultants don't have project context — you must provide it
- Use when genuinely uncertain, not for validation
- A consultant's report is a claim, not a record — premise-check any
  factual assertion about the tree before building scope on it
