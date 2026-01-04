# Contributing to SENTINEL

Welcome to SENTINEL. We're building something that respects player agency, embraces moral complexity, and prioritizes narrative integrity. This document outlines how you can contribute to our vision.

## Our Design Philosophy

SENTINEL is built on three core pillars:

### Player Agency
We believe players should make meaningful choices with real consequences. Every decision point should offer genuine alternatives that affect the narrative trajectory, character relationships, and world state. Agency means players aren't following a predetermined path—they're authoring their own story within our framework.

### Ethical Ambiguity
The world doesn't operate in binaries. We reject simplistic good-vs-evil narratives. Characters have conflicting motivations. Factions have valid points and fatal flaws. Moral choices should feel weighty precisely because reasonable people could disagree on the right answer. We explore the grey spaces where ethics get complicated.

### Narrative Integrity
Story coherence matters. Every quest, dialogue, and environmental detail should reinforce the world's internal logic. Contradictions must be intentional. Character arcs should earn their emotional beats. We prioritize meaningful storytelling over spectacle, and depth over breadth.

---

## Contribution Tiers

We recognize contributions at multiple levels. All tiers are valued and necessary for SENTINEL's success.

### Tier 1: Community Member
**Getting started with feedback and ideas**

- Playtesting and bug reporting
- Suggesting narrative improvements or world-building ideas
- Participating in design discussions
- Creating issues that document problems or opportunities
- No technical setup required

### Tier 2: Active Contributor
**Taking on defined tasks**

- Writing dialogue, quest text, or item descriptions
- Creating or refining environmental narratives
- Contributing code fixes for documented issues
- Improving documentation and guides
- Requires forking and opening pull requests

### Tier 3: Specialist Contributor
**Deep expertise in specific domains**

- Leading narrative arcs or character development
- Designing complex quest systems or branching logic
- Architecting major code systems or refactors
- Mentoring other contributors in their specialty
- Requires demonstrated expertise and sustained contributions

### Tier 4: Maintainer
**Strategic stewardship of the project**

- Merging pull requests and managing releases
- Setting long-term vision alongside the core team
- Resolving design conflicts and architectural decisions
- Onboarding new high-level contributors
- By invitation only, after significant sustained contributions

---

## What Will NOT Be Accepted

Before you start, understand these hard boundaries:

### Narrative & Design
- **Grimdark edgeliness for its own sake** — Dark themes are fine; nihilistic "nothing matters" messaging isn't aligned with our philosophy
- **Exploitative content involving minors** — This is non-negotiable. No exceptions
- **Crude stereotypes or reductive representation** — Complex, nuanced characterization of all groups required
- **Plots that undermine player agency** — "Gotcha" moments where players are forced into paths aren't allowed
- **Narratively inconsistent retcons** — Changes to established lore must make logical sense in-world
- **Generic fantasy/sci-fi clichés without a twist** — We push genre conventions, not reinforce them
- **Contradictions to established design pillars** — New content must support player agency, ethical complexity, and narrative integrity

### Code
- **Spaghetti code without documentation** — All code must be readable and maintainable
- **External dependencies without justification** — Minimize bloat; justify what you add
- **Code that breaks existing tests** — New submissions must pass all tests
- **Hardcoded values instead of configurable systems** — Use data-driven design
- **Security vulnerabilities** — Any known exploits, input validation issues, or authentication bypasses are rejected

### Community
- **Discrimination, harassment, or hate speech** — We maintain a respectful environment
- **Commercial content disguised as contributions** — This is a creative collaboration, not an advertising platform
- **Contributions violating open-source licenses** — Respect intellectual property

---

## Getting Started

### Step 1: Explore the Project
- Read this guide thoroughly
- Review our **Code of Conduct** and **Design Pillars** documentation
- Play the game or read existing content to understand tone and world
- Check the issue tracker for areas marked "good first contribution"

### Step 2: Set Up Your Environment
```bash
# Clone the repository
git clone https://github.com/KvFxKaido/SENTINEL.git
cd SENTINEL

# Create your feature branch
git checkout -b your-feature-name

# Install dependencies (varies by component)
# See SETUP.md for detailed instructions
```

### Step 3: Make Your Changes
- Keep commits focused and atomic
- Write clear commit messages explaining the *why*, not just the *what*
- Test your changes thoroughly (see Code Style Guide below)
- Reference relevant issues: "Fixes #123" or "Related to #456"

### Step 4: Open a Pull Request
- Fill out the PR template completely
- Link to any related issues
- Provide context: what problem does this solve? why this approach?
- Be prepared for thoughtful feedback

---

## Code Style Guide

### General Principles
- **Clarity over cleverness** — Code is read more than written
- **Self-documenting code** — Names should reveal intent
- **Single Responsibility** — Functions do one thing well
- **DRY (Don't Repeat Yourself)** — Extract common patterns

### Specific Standards
```
[Include your language-specific standards here]

Examples:
- Naming: snake_case for functions/variables, CamelCase for classes
- Line length: Maximum 100 characters
- Indentation: 4 spaces (never tabs)
- Comments: Explain *why*, not *what*
- Testing: Aim for >80% coverage on new code
```

### Documentation
- Comment non-obvious logic
- Document function signatures with purpose and parameters
- Include examples for complex functionality
- Update relevant documentation files when changing behavior

---

## Narrative Style Guide

### Dialogue
- **Voice consistency** — Characters should sound distinct and consistent with their background
- **Subtext** — What characters don't say is as important as what they do
- **Avoid exposition dumps** — Weave worldbuilding naturally into conversation
- **Player agency in dialogue** — Dialogue options should represent genuine choices, not cosmetic variants

### Quest Design
- **Meaningful consequences** — Different choices should lead to different outcomes
- **Multiple valid approaches** — Quests should be solvable in 2+ ways
- **Ethical complexity** — At least one quest outcome involves genuine moral tension
- **Narrative payoff** — Quests should affect character relationships or world state, not just inventory

### World-Building
- **Internal consistency** — Lore must align with established world rules
- **Show, don't tell** — Let environments and characters reveal the world
- **Texture and detail** — Rich sensory description, but purposeful (no padding)
- **Cultural specificity** — Avoid generic "fantasy medieval" when designing cultures/factions

### Example Standards
```
GOOD: "The merchant's eyes dart to the side. She knows something."
WEAK: "The merchant is nervous because she is hiding secrets."

GOOD: Give the player three quest solutions with different moral implications.
WEAK: Make all paths lead to the same outcome; just change the flavor text.
```

---

## Review Process

### What Happens After You Open a PR

1. **Automated Checks** (within hours)
   - Tests must pass
   - Code style validation
   - Linting checks

2. **Community Review** (24-72 hours)
   - Design feedback on narrative/gameplay changes
   - Code review for technical contributions
   - Constructive suggestions for improvement

3. **Maintainer Review** (2-5 business days)
   - Final approval or detailed feedback
   - Merge decision or request for revisions

### Providing Feedback
- **Be specific** — "This doesn't work" is unhelpful. "This breaks agency because the player can't choose X" is useful
- **Offer alternatives** — If you critique, suggest solutions
- **Assume good faith** — We're all here to make SENTINEL better
- **Focus on the work, not the person** — Critique ideas, not contributors

### Revising Your PR
- Respond to feedback directly in the conversation
- Update your code/content based on suggestions
- Push new commits (don't force-push; let the history show revision)
- Re-request review once ready

### When to Close Without Merging
- The contribution doesn't align with design pillars
- Security vulnerabilities aren't addressed
- Code quality or narrative consistency issues can't be resolved
- Contributor unresponsive after 30 days (with warning)

---

## Recognition Guidelines

Contributors are recognized based on impact and commitment:

### In-Game Credits
- Tier 2+ contributors on content are credited in the game itself
- Format: [Contributor Name] — [Role/Contribution]
- Example: "Jane Smith — Quest Design, Dialogue"

### In Documentation
- All contributors listed in CONTRIBUTORS.md with their specialization
- Linked to GitHub profiles for discoverability

### Special Recognition
- Major features or arcs named after lead contributors (with permission)
- Shoutouts in release notes for significant contributions
- Invitation to core team socials/retrospectives

### Compensation
- SENTINEL is a passion project; currently, contributions are volunteer
- If commercialization happens, early contributors will be consulted on fair models

---

## Questions?

- **General questions:** Open a Discussion in the repository
- **Specific issues:** Comment on the relevant issue thread
- **Design philosophy:** Start a Discussion tagged with "design-debate"
- **Direct contact:** Reach out to maintainers via GitHub (response within 5 business days)

---

## Final Thoughts

Contributing to SENTINEL means helping build a game that respects its players. We're creating a space where difficult choices matter, where morality isn't simple, and where every narrative moment serves the story. 

Whether you're writing a single piece of dialogue, fixing a critical bug, or designing an entire faction, you're part of something meaningful.

Thank you for being here.

---

*Last updated: 2026-01-04*
*Maintained by: KvFxKaido*
