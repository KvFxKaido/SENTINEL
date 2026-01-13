# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

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

- Removed legacy command system (~1400 lines) — unified through registry
- Consolidated TUI learning plan into permanent architecture docs
- Updated all project docs (CLAUDE.md, AGENTS.md, GEMINI.md) with TUI patterns
- Consolidated MCP_FACTIONS.md into sentinel-campaign README
- Updated CONTRIBUTING.md with Code of Conduct link

### Removed

- `architecture/SENTINEL_TUI_Learning_Plan.md` (objectives complete)
- `architecture/Layout_Engine_Architecture.md` (merged into docs)
- Legacy CLI command handlers (replaced by registry)
