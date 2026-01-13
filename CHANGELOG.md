# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

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
