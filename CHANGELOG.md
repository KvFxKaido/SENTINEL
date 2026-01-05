# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `/simulate` command for AI vs AI testing with 4 player personas
- Event queue for MCP → Agent state synchronization
- Cipher import script for character migration
- GitHub issue and PR templates
- CODE_OF_CONDUCT.md (Contributor Covenant 2.1)
- SECURITY.md with vulnerability reporting guidelines
- LICENSE file (CC BY-NC 4.0)
- License badge in README

### Fixed

- LLMClient.chat() type mismatch
- Version comparison bug (now uses numeric tuples)
- PromptLoader bug (manager passed through call chain)

### Changed

- Consolidated MCP_FACTIONS.md into sentinel-campaign README
- Updated CONTRIBUTING.md with Code of Conduct link
