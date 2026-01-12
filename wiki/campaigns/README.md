# Campaign Wiki Overlays

Each campaign can have its own wiki overlay that extends or overrides canon pages.

## Directory Structure

```
campaigns/
└── {campaign_id}/
    ├── _events.md           # Campaign timeline (auto-generated)
    ├── Nexus.md             # Override or extend canon Nexus page
    └── NPCs/
        └── Marcus_Cole.md   # Campaign-specific NPC
```

## Page Types

### Override Pages

A page with the same name as a canon page completely replaces it for this campaign.

### Extend Pages

Use `extends:` frontmatter to append sections to a canon page:

```markdown
---
extends: Nexus
append_to: "## History"
---

### Campaign Events

- **Session 3:** Player exposed surveillance operation
- **Session 7:** Standing dropped to Unfriendly
```

### New Pages

Pages that don't exist in canon are campaign-specific additions.

## Auto-Generated Content

The `_events.md` file is automatically updated when the GM logs wiki events.
It contains a chronological list of campaign-specific happenings.
