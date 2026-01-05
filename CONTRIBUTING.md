# Contributing to SENTINEL

Thank you for your interest in contributing to SENTINEL.

SENTINEL is a tactical tabletop RPG with an AI Game Master, focused on player agency, ethical ambiguity, and long-term consequence in a fractured post-collapse world. Contributions are welcome, but this is a values-driven project. Technical quality matters, and so does philosophical alignment.

This document exists to help you decide how to contribute and whether a contribution is a good fit.

---

## Design Philosophy (Read First)

SENTINEL prioritizes:

- Player agency over optimization
- Ethical tradeoffs over binary morality
- Consequences over spectacle
- Clarity over cleverness
- Narrative integrity over mechanical efficiency

Contributions that do any of the following will not be accepted, even if they are technically impressive:

- Reduce meaningful player choice
- Imply or enforce a "correct" moral outcome
- Optimize away uncertainty, discomfort, or ambiguity
- Turn NPCs into puzzles, rewards, or obstacles to be solved
- Steer players toward preferred decisions or outcomes

If you are unsure whether a change aligns with these principles, open an issue for discussion before submitting a pull request.

---

## Code of Conduct

This project and everyone participating in it are governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold it. Please report unacceptable behavior to the project maintainers.

---

## Ways to Contribute

### Good First Contributions

These are high-impact, low-risk ways to get involved:

- Documentation improvements and clarifications
- Bug fixes with regression tests
- Test coverage expansion
- UX and CLI polish that does not alter decision structure
- Refactoring for readability and maintainability
- New LLM backend adapters that follow existing abstractions

### Medium-Scope Contributions

- Prompt tuning in `prompts/` (hot-reloadable, no restart needed)
- AI GM behavior refinements that improve clarity or neutrality
- Faction advisor perspectives in `prompts/advisors/`
- Additional tooling or developer ergonomics
- Performance or reliability improvements

### Major Contributions (Proposal Required)

The following require prior discussion via an issue or proposal:

- Changes to core mechanics
- New or altered factions
- Canon or lore modifications
- Structural changes to the agent architecture
- New enhancement systems or leverage mechanics

Do not submit a pull request for these without prior alignment.

---

## Development Setup

```bash
# Clone and install
git clone https://github.com/YOUR_USERNAME/SENTINEL.git
cd SENTINEL/sentinel-agent
pip install -e ".[dev]"

# Run tests (197 should pass)
pytest

# Run the CLI
python -m src.interface.cli
```

For detailed guidance on architecture, file purposes, and code conventions, see [`sentinel-agent/CLAUDE.md`](sentinel-agent/CLAUDE.md).

### Key Directories

| Directory | Purpose |
|-----------|---------|
| `sentinel-agent/src/` | Core agent code |
| `sentinel-agent/prompts/` | Hot-reloadable GM prompts |
| `sentinel-agent/tests/` | Test suite |
| `sentinel-campaign/` | Faction MCP server |
| `lore/` | Canon novellas for RAG |

---

## Code & Quality Standards

### Code Style

- Follow existing project style and conventions
- Write clear, readable code with meaningful names
- Keep functions focused and modular
- Comment complex or non-obvious logic

### Testing

- New features should include tests when practical
- Bug fixes must include regression coverage
- All existing tests must pass
- Exploratory or experimental work may omit tests if clearly marked

CI must pass for a pull request to be considered.

---

## Reporting Bugs

When reporting a bug, please include:

- **Title:** Clear and descriptive
- **Description:** What is happening
- **Steps to Reproduce:** Minimal, repeatable steps
- **Expected Behavior**
- **Actual Behavior**
- **Environment:** OS, Python version, LLM backend
- **Logs or Screenshots:** If applicable

---

## Suggesting Enhancements

Enhancement suggestions are welcome. Please include:

- A clear description of the current behavior
- The proposed change
- Concrete examples
- Why this improves player agency, clarity, or consequence

Avoid suggestions framed primarily around optimization, balance for efficiency, or power scaling.

---

## Pull Request Process

1. Fork the repository
2. Create a feature branch from `master`
3. Implement your changes
4. Ensure tests pass locally (`pytest`)
5. Push your branch to your fork
6. Open a pull request

Your PR description should include:

- A clear summary of changes
- References to related issues (if any)
- Testing performed
- Notes on any breaking changes

Be responsive to review feedback. Discussion is part of the process.

---

## Pull Request Checklist

- [ ] Code follows project style guidelines
- [ ] Relevant documentation updated
- [ ] Tests added or updated where appropriate
- [ ] All tests pass locally
- [ ] No reduction in player agency or narrative integrity
- [ ] Commit messages are clear and descriptive

---

## License

By contributing to SENTINEL, you agree that your contributions will be licensed under the project's existing license (CC BY-NC 4.0).

---

## Questions

If you're unsure where a contribution fits or want feedback before building:

- Open an issue for discussion
- Review existing issues and discussions
- See [SENTINEL_PROJECT_BRIEF.md](SENTINEL_PROJECT_BRIEF.md) for project context

Thoughtful questions are welcome. Careless changes are not.
