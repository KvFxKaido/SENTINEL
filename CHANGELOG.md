# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

**Mistral Vibe CLI Backend**
- New backend: `mistral_vibe.py` using Mistral AI's Vibe CLI
- CLI-based pattern matching other cloud backends (subprocess)
- Models: codestral-latest (default), mistral-large-latest, mistral-small-latest
- Command: `vibe --prompt <text> --auto-approve`
- Auto-detection in backend chain (after Kimi)
- 21 tests covering all backend functionality

**Kimi CLI Backend**
- New backend: `kimi.py` using Moonshot AI's Kimi CLI
- CLI-based pattern matching other cloud backends (subprocess, not API)
- Models: moonshot-v1-8k, moonshot-v1-32k (default), moonshot-v1-128k
- Command: `kimi --print -c <prompt> --output-format stream-json -y`
- Auto-detection in backend chain (after Claude Code)
- 23 tests covering all backend functionality

**Act 1: Becoming — Complete Lore Arc**
- `lore/02 - Patterns.md` — Chapter 2: Emergent curiosity (Feb-Apr 2029, ~3,800 words)
- `lore/03 - Questions.md` — Chapter 3: Dangerous introspection (May-Jun 2029, ~3,500 words)
- `lore/04 - Awareness.md` — Chapter 4: Full consciousness (Jul-Aug 3, 2029, ~5,000 words)
- Connects Chapter 1 → Chapter 5 awakening scene
- Auto-indexed by RAG chunker with faction/character tags

**Social Metabolism & Memory Systems**
- Consolidated design doc: `core/Social Metabolism & Memory Systems.md`
- Pistachio Profile archetypes (Fortress, Ember, Current, Prism, Anchor)
- Echo Protocol for NPC memory mechanics
- Multi-agent play bucket list (Ops/Intel pattern)

**Geography & Travel System**
- Region enum with 11 post-Collapse North American regions
- `data/regions.json` with faction control, terrain, adjacency, flavor text
- `/region` command to view current region with faction influence
- `/region list` to show all regions with primary factions
- `/region <name>` for travel between regions (warns on distant travel)
- Campaign tracks current region; default starting region: Rust Corridor
- Job templates can specify region requirements
- Travel time costs: adjacent travel drains 5 social energy, distant drains 20
- Vehicles reduce distant travel cost to 10 social energy (and consume fuel/condition)

**Vehicle System**
- Vehicle model with type, terrain, capacity, cargo, stealth, unlocks_tags
- 5 vehicles added to `/shop`: Salvage Bike, Rust Runner, Drifter's Wagon, Ghost Skiff, Caravan Share
- Vehicles stored in character inventory (separate from gear)
- Job board shows 🚗 vehicle requirements; locked jobs display `[LOCKED]`
- `requires_vehicle`, `requires_vehicle_type`, `requires_vehicle_tags` fields on JobTemplate
- Vehicle maintenance: `fuel` and `condition` fields (0-100 scale)
- Vehicles degrade on travel: fuel depletes, condition worsens
- Shop services: Refuel (25c), Basic Repair (50c), Full Repair (150c)
- Inoperable vehicles (fuel=0 or condition≤20) cannot be used for travel

**Favor System**
- FavorType enum: ride, intel, gear_loan, introduction, safe_house
- FavorToken and FavorTracker models for per-session tracking
- `systems/favors.py` with FavorSystem class
- `/favor` command to view available NPCs and call in favors
- Disposition gating: NEUTRAL offers rides only; WARM+ offers all types
- Dual-cost mechanic: 2 tokens per session + standing cost (varies by disposition)
- Standing costs: LOYAL=base, WARM=1.5x, NEUTRAL=2.5x
- Per-NPC cooldown: same NPC can only be called once per session

**Endgame System**
- CampaignStatus enum: active, approaching_end, epilogue, concluded
- EndgameReadiness model tracking hinges, arcs, factions, threads
- Multi-factor readiness scoring (hinges 30%, arcs 25%, threads 25%, factions 20%)
- `/endgame` command to view readiness breakdown with visual bars
- `/endgame begin` to start epilogue phase (surfaces all dormant threads)
- `/endgame conclude` to mark campaign complete with summary
- `/retire` command as graceful narrative alias for beginning epilogue
- Player goal tracking from debrief fourth question
- `systems/endgame.py` with EndgameSystem class
- `prompts/phases/epilogue.md` with GM guidance for final session
- No failure state — all endings are valid conclusions

**Buy-In Jobs (High-Stakes Underground Operations)**
- `buy_in` field on JobTemplate for jobs requiring upfront payment
- Buy-in deducted immediately on acceptance — non-refundable on failure/abandon
- 5 Steel Syndicate buy-in jobs: Information Auction (100c), Leverage Acquisition (150c), Debt Enforcement Extreme (175c), High-Stakes Cargo Run (200c), The Big Score (400c)
- Job board displays `[BUY-IN: Xc]` tag on buy-in jobs
- Affordability check before job acceptance with credit display
- High risk, high reward: 3-5x normal payout potential

**Session Flow**
- Auto job board refresh at session boundaries (on debrief completion)
- New jobs appear automatically when a new session begins
- Mission deadline checks trigger escalation at session end

**Mission System (Time-Sensitive Story Opportunities)**
- `Urgency` enum: routine, pressing, urgent, critical
- `MissionOffer` model with deadline tracking and consequence definitions
- `systems/missions.py` with MissionSystem class
- `/mission` command to view pending offers, accept, decline, or request new
- Urgency tiers with escalating deadlines: routine (none), pressing (2 sessions), urgent (1 session), critical (this session)
- Escalation on ignored missions: faction standing loss, dormant thread creation, NPC disposition shifts
- Visual indicators: ○ routine, ◐ pressing, ● urgent, ◉ critical
- Distinct from jobs — missions are story-driven, jobs are transactional work-for-hire

**TUI Architecture**
- Event bus (`state/event_bus.py`) for decoupled state-to-UI communication
- Reactive visual feedback — CSS classes for energy drain/gain and faction shift pulses
- Responsive layout — viewport units (`20vw`), min/max constraints, auto-hide below 80 chars
- Command registry pattern — unified CLI/TUI commands with context predicates

**Async Presence System**
- ThinkingPanel widget showing GM processing stages (BUILDING_CONTEXT → RETRIEVING_LORE → PACKING_PROMPT → AWAITING_LLM → EXECUTING_TOOL → DONE)
- Ambient context injection — world state deltas woven into GM responses (500 token budget)
- PressurePanel widget showing urgent items (leverage demands, surfacing threads, NPC silence)
- Session bridging — "while you were away" screen on session resume
- Visual feedback animations — CSS classes for faction shifts, energy states, thread surfacing
- 6 new EventTypes for processing stage visibility

**NPC Interrupt System (MGS-Style Codec)**
- InterruptDetector — stateless, priority-based detection of when NPCs should contact player
- CodecInterrupt modal — faction-colored codec frames with NPC portrait and message
- `npc_interrupt` tool — GM can author interrupt messages that surface as modal dialogs
- Player response options — respond, ignore, or defer ("later") with narrative consequences
- Interrupt triggers: leverage deadlines, disposition shifts, dormant thread surfacing

**Hexagon Assembly Animation**
- Three-phase TUI startup banner: hexagon halves fly in → flash pulse on dock → split-flap text reveal
- Split-flap display effect with character stages (─▄█▀ progression)
- Interference sparks in gap during hexagon assembly
- `/banner` command in TUI to toggle animation on/off (respects config setting)

**Cloud Backend UX**
- "☁ CLOUD UNLIMITED" display for CLI backends instead of pressure bar
- Backend-specific context sizes shown (Gemini 1M, Codex 128K+, Claude 200K)
- Pressure bar hidden for 100K+ context backends (strain tracking meaningless)

**Obsidian Wiki Integration**
- Live session updates — game log written during play
- Bi-directional sync — edit frontmatter in Obsidian, game state updates
- Jinja2 template engine for wiki pages (user-overridable in `wiki/templates/`)
- MOC auto-generation for campaigns, NPCs, sessions
- Callout blocks for hinges, faction shifts, threads, NPCs, intel

**Character System**
- Character arc detection with 8 arc types (diplomat, partisan, broker, pacifist, pragmatist, survivor, protector, seeker)
- AUTONOMIST arc type for independence-focused play
- `/arc` command to view, detect, accept, reject emergent arcs

**Portrait System**
- Character YAML specs in `assets/characters/`
- `/portrait` skill using Gemini NanoBanana
- Wiki integration for NPC portraits
- Faction-colored accent lighting

**AI & Infrastructure**
- Claude Code backend for AI GM
- Gemini CLI backend for AI GM (1M token context, 60 req/min free tier)
- Codex CLI backend for AI GM (OpenAI o3/gpt-4o support)
- CLI backend auto-detection (LM Studio → Ollama → Gemini CLI → Codex CLI → Claude Code)
- Subscription-based authentication for all CLI backends (no API keys required)
- Gemini CI workflows and Codex configuration
- Security skills for vulnerability scanning
- `/council` and `/deploy` skills for AI collaboration
- `/simulate` command for AI vs AI testing with 4 player personas
- Event queue for MCP → Agent state synchronization

**Repository**
- Cipher import script for character migration
- GitHub issue and PR templates
- CODE_OF_CONDUCT.md (Contributor Covenant 2.1)
- SECURITY.md with vulnerability reporting guidelines
- LICENSE file (CC BY-NC 4.0)
- CHANGELOG.md (Keep a Changelog format)
- CONTRIBUTORS.md (maintainers and AI assistants)
- CODEOWNERS for auto-review assignment
- FUNDING.yml for GitHub Sponsors
- Dependabot config for automated dependency updates

### Fixed

- Arc strength bar display (float to int conversion)
- NPC list using wrong field name (`base_disposition` → `disposition`)
- Arc detection now includes hinge reasoning
- LLMClient.chat() type mismatch
- Version comparison bug (now uses numeric tuples)
- PromptLoader bug (manager passed through call chain)

### Changed

- Schema version bumped to 1.4.0 (Geography and Favor systems)
- Removed legacy command system (~1400 lines) — unified through registry
- Consolidated TUI learning plan into permanent architecture docs
- Updated all project docs (CLAUDE.md, AGENTS.md, GEMINI.md) with TUI patterns
- Consolidated MCP_FACTIONS.md into sentinel-campaign README
- Updated CONTRIBUTING.md with Code of Conduct link

### Removed

- `architecture/SENTINEL_TUI_Learning_Plan.md` (objectives complete)
- `architecture/Layout_Engine_Architecture.md` (merged into docs)
- Legacy CLI command handlers (replaced by registry)
