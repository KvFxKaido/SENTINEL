# SENTINEL Wiki

Obsidian vault containing the SENTINEL reference encyclopedia.

## Structure

```
wiki/
├── canon/              # Base lore (shared across campaigns)
│   ├── Home.md         # Landing page
│   ├── Factions.md     # Hub: all 11 factions
│   ├── Geography.md    # Hub: all 11 regions
│   ├── Timeline.md     # Hub: chronological history
│   ├── [Faction].md    # Individual faction pages
│   └── [Region].md     # Individual region pages
└── campaigns/          # Per-campaign overlays
    └── {campaign_id}/  # Campaign-specific additions
        ├── _events.md  # Session timeline
        └── *.md        # Page overlays (extend canon)
```

## Conventions

### Callout Types

Use Obsidian callouts to visually distinguish content types:

| Callout | Use For | Example |
|---------|---------|---------|
| `[!quote]` | Character quotes, canon citations | Dialogue, philosophy |
| `[!info]` | Statistics, data, neutral facts | Day One stats |
| `[!danger]` | Critical events, irreversible moments | Judgment Hour |
| `[!important]` | Key concepts, realizations | Mutual Fear |
| `[!abstract]` | Core philosophy summaries | Faction overviews |
| `[!warning]` | Cautions, pending consequences | Dormant threads |

**Campaign-specific callouts:**

| Callout | Use For |
|---------|---------|
| `[!hinge]` | Irreversible player choices |
| `[!faction]` | Faction standing changes |
| `[!thread]` | Dormant threads queued |
| `[!npc]` | NPC interactions, disposition changes |

**Example:**
```markdown
> [!hinge] Betrayed Nexus Contact
> Standing: Neutral → Unfriendly (-20)
> Thread queued: Nexus Retaliation
```

### Mermaid Diagrams

Faction relationship diagrams use consistent notation:

```markdown
```mermaid
graph LR
    FactionA ===|"cooperative"| FactionB    %% Solid = friendly
    FactionA -.-|"tense"| FactionC          %% Dashed = strained
    FactionA ---|"hostile"| FactionD        %% Line = hostile
```
```

### Frontmatter

All pages should include typed frontmatter:

```yaml
---
type: faction | region | event | hub | npc
tags:
  - relevant-tags
aliases:
  - Alternate Names
---
```

### Wikilinks

- Use `[[Page Name]]` for internal links
- Use `[[Page Name|Display Text]]` for custom display
- Prefer exact page names over aliases

### Campaign Overlays

Campaign-specific content lives in `campaigns/{id}/`:

- **Extend canon:** Use `extends: Canon_Page` in frontmatter
- **Override sections:** Same heading replaces canon heading
- **Add sections:** New headings append to canon

**Example overlay:**
```markdown
---
extends: Nexus
campaign: iron_winter
---

## Campaign Status

> [!faction] Standing Changed (Session 3)
> Neutral → Unfriendly after surveillance betrayal
```

## Integration

The wiki integrates with the SENTINEL agent:

- **Retrieval:** Wiki pages indexed alongside lore (1.8x weight)
- **MCP Resources:** `wiki://{page}` exposes pages via MCP
- **MCP Tools:** `search_wiki` for keyword queries
- **Regions:** Geographic queries match wiki region pages

## Plugins (Optional)

These Obsidian plugins enhance the experience:

| Plugin | Purpose |
|--------|---------|
| **Dataview** | Dynamic queries across pages |
| **Mermaid** | Relationship diagrams (built-in) |
| **Calendar** | Session timeline navigation |

The wiki works without plugins—they're purely additive.
