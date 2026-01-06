# Frontend Sprint Orchestration

Multi-agent session plan for completing Phase 2 frontend features.

---

## Overview

**Agents:** 2-3 Claude instances + Gemini + Codex
**Goal:** Complete Q2 frontend roadmap items in parallel
**Duration:** Single session (~2-3 hours)

---

## Phase 1: Research (Parallel - Gemini + Codex)

Run these first to generate specs that Claude agents will implement.

### Gemini: Terminal Image Protocols

```
Research terminal image display protocols for SENTINEL, a terminal-based TTRPG.

Questions to answer:
1. Kitty Graphics Protocol - how does it work? What's the API?
2. Sixel - browser/terminal support, limitations?
3. iTerm2 inline images - macOS only?
4. What's the fallback detection strategy? (check $TERM, $KITTY_WINDOW_ID, etc.)
5. Python libraries that abstract this? (e.g., term-image, pixcat)

Output a spec document with:
- Protocol comparison table (support, quality, complexity)
- Recommended approach for cross-platform support
- Code snippets for detection and display
- Fallback strategy (Unicode block art → ASCII → text only)
```

### Codex: Tauri Desktop App Research

```
Research Tauri for a potential SENTINEL desktop app wrapper.

Context: SENTINEL is a Python terminal TTRPG. We want to explore wrapping it in a desktop app for:
- Native image support (NPC portraits)
- Better font rendering
- Optional sidebar panels

Questions:
1. Can Tauri wrap a Python CLI app? Or does it need a web frontend?
2. What's the minimal Tauri setup? (just a terminal emulator + image panel)
3. Alternatives: Electron, Wails, native Python (tkinter/PyQt)?
4. Effort estimate for MVP prototype?

Output a decision document with recommendation.
```

---

## Phase 2: Implementation (Parallel - 3 Claude Instances)

Start after research phase completes. Each Claude owns specific files.

### Claude A: Portrait System Architecture

**Owns:** `sentinel-agent/src/interface/portraits.py` (new), `portraits/` directory

```
Implement the portrait system foundation for SENTINEL.

Context: SENTINEL is a terminal TTRPG with NPC codec boxes. We want to add optional
portrait support for NPCs and the player character.

Requirements:
1. Create `src/interface/portraits.py` with:
   - PortraitManager class
   - Portrait dataclass (id, path, faction, npc_name)
   - get_portrait(npc_name, faction) -> Portrait | None
   - Fallback to faction glyph if no portrait

2. Create directory structure:
   portraits/
   ├── player/           # Player character portraits
   ├── factions/         # Generic faction portraits (one per faction)
   │   ├── nexus.png
   │   ├── ember.png
   │   └── ...
   └── npcs/             # Named NPC portraits
       └── .gitkeep

3. Add placeholder detection in render_codec_box():
   - If portrait exists AND terminal supports images: show image
   - Else: use existing faction glyph (current behavior)

4. Do NOT implement actual image display yet - just the data layer.

Files you may READ: renderer.py, glyphs.py, schema.py
Files you may WRITE: portraits.py (new), portraits/.gitkeep files
Do NOT modify: cli.py, renderer.py, commands.py
```

### Claude B: Terminal Image Display

**Owns:** `sentinel-agent/src/interface/images.py` (new)

**Depends on:** Gemini research output

```
Implement terminal image display for SENTINEL based on the research spec.

Requirements:
1. Create `src/interface/images.py` with:
   - detect_image_support() -> ImageProtocol enum (KITTY, SIXEL, ITERM, NONE)
   - display_image(path, width, height) -> bool (success)
   - ImageProtocol enum

2. Detection strategy:
   - Check $KITTY_WINDOW_ID for Kitty
   - Check $TERM_PROGRAM for iTerm2
   - Check $TERM for sixel support
   - Default to NONE (fallback to text)

3. Use term-image library if available, graceful fallback if not:
   ```python
   try:
       from term_image.image import from_file
       HAS_TERM_IMAGE = True
   except ImportError:
       HAS_TERM_IMAGE = False
   ```

4. Add to pyproject.toml as optional dependency:
   [project.optional-dependencies]
   images = ["term-image>=0.7.0"]

Files you may READ: renderer.py, pyproject.toml
Files you may WRITE: images.py (new), pyproject.toml (add optional dep)
Do NOT modify: cli.py, renderer.py, commands.py
```

### Claude C: Faction Visual Refinements

**Owns:** `sentinel-agent/src/interface/glyphs.py`, `sentinel-agent/src/interface/themes.py` (new)

```
Refine faction visual language in SENTINEL.

Requirements:
1. Enhance glyphs.py:
   - Add FACTION_FRAMES dict with box-drawing characters per faction
   - Nexus: clean double-line (╔═╗)
   - Ember: warm rounded (╭─╮)
   - Ghost: glitchy/broken (┌╌┐ with occasional gaps)
   - Each faction gets unique frame style

2. Create themes.py:
   - Extract THEME dict from renderer.py to dedicated file
   - Add per-faction color schemes:
     FACTION_THEMES = {
         "nexus": {"primary": "bright_blue", "accent": "cyan", ...},
         "ember": {"primary": "orange", "accent": "yellow", ...},
     }
   - Add get_faction_theme(faction_name) -> dict

3. Update renderer.py imports to use themes.py (minimal change)

Files you may READ: renderer.py, glyphs.py
Files you may WRITE: glyphs.py, themes.py (new)
Files you may EDIT (import only): renderer.py (just update imports)
Do NOT modify: cli.py, commands.py
```

---

## Phase 3: Integration (Single Claude)

After parallel implementation, one Claude integrates everything.

### Claude Integrator

```
Integrate the portrait and image systems into SENTINEL's codec boxes.

Context: Three parallel agents created:
- portraits.py: Portrait data management
- images.py: Terminal image display
- themes.py + glyphs.py updates: Faction visual refinements

Your job:
1. Update render_codec_box() in renderer.py to:
   - Import from portraits, images, themes
   - Check for portrait, display if terminal supports
   - Apply faction-specific frame from glyphs.py
   - Use faction theme colors

2. Add /portrait command to commands.py:
   - /portrait - show current character portrait
   - /portrait set <path> - set custom portrait
   - /portrait clear - remove custom portrait

3. Run tests, fix any integration issues

4. Update renderer.py THEME to import from themes.py

Files you may READ/WRITE: renderer.py, commands.py, cli.py
Coordinate with: portraits.py, images.py, themes.py, glyphs.py
```

---

## File Ownership Matrix

| File | Claude A | Claude B | Claude C | Integrator |
|------|----------|----------|----------|------------|
| portraits.py (new) | WRITE | - | - | READ |
| images.py (new) | - | WRITE | - | READ |
| themes.py (new) | - | - | WRITE | READ |
| glyphs.py | READ | - | WRITE | READ |
| renderer.py | READ | READ | EDIT imports | WRITE |
| commands.py | - | - | - | WRITE |
| cli.py | - | - | - | EDIT |
| pyproject.toml | - | EDIT | - | - |

---

## Sequencing

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: Research (15-20 min)                               │
│                                                             │
│   Gemini ──────────┐                                        │
│   (image protocols)│                                        │
│                    ├──► Research specs ready                │
│   Codex ──────────┘                                        │
│   (Tauri research)                                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: Implementation (30-45 min)                         │
│                                                             │
│   Claude A ─────────┐                                       │
│   (portraits.py)    │                                       │
│                     │                                       │
│   Claude B ─────────┼──► All modules complete               │
│   (images.py)       │                                       │
│                     │                                       │
│   Claude C ─────────┘                                       │
│   (themes + glyphs)                                         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: Integration (20-30 min)                            │
│                                                             │
│   Claude Integrator ──► codec boxes + /portrait command     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: Test & Polish (15 min)                             │
│                                                             │
│   Human review + final fixes                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Startup Commands

### Phase 1 (run in parallel terminals)

**Gemini:**
```bash
gemini < architecture/prompts/gemini_image_research.md
```

**Codex:**
```bash
codex exec < architecture/prompts/codex_tauri_research.md
```

### Phase 2 (after research, run in parallel)

```bash
# Terminal 1
claude --prompt "$(cat architecture/prompts/claude_a_portraits.md)"

# Terminal 2
claude --prompt "$(cat architecture/prompts/claude_b_images.md)"

# Terminal 3
claude --prompt "$(cat architecture/prompts/claude_c_themes.md)"
```

### Phase 3 (after implementation)

```bash
claude --prompt "$(cat architecture/prompts/claude_integrator.md)"
```

---

## Success Criteria

- [ ] `portraits.py` exists with PortraitManager class
- [ ] `images.py` exists with terminal detection
- [ ] `themes.py` exists with faction color schemes
- [ ] `glyphs.py` has FACTION_FRAMES
- [ ] `render_codec_box()` uses new systems
- [ ] `/portrait` command works
- [ ] All 197+ tests pass
- [ ] Manual test: codec box displays with faction styling

---

## Rollback Plan

If integration fails, each module is isolated:
- Delete new files (portraits.py, images.py, themes.py)
- Revert renderer.py, glyphs.py, commands.py
- System returns to current working state

---

## Notes

- Keep prompts focused - one clear deliverable per agent
- Agents should NOT run tests mid-work (avoids conflicts)
- Integrator runs full test suite at the end
- Human approves before any git commits
