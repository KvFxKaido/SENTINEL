# SENTINEL Wiki

Obsidian vault containing the SENTINEL reference encyclopedia.

## Structure

```
wiki/
├── canon/                  # Base lore (shared across campaigns)
│   ├── Home.md             # Landing page
│   ├── Factions.md         # Hub: all 11 factions
│   ├── Geography.md        # Hub: all 11 regions
│   ├── Timeline.md         # Hub: chronological history
│   ├── [Faction].md        # Individual faction pages
│   └── [Region].md         # Individual region pages
├── templates/              # Dashboard templates (auto-copied to campaigns)
│   ├── campaign_index.md   # → _index.md (campaign hub)
│   ├── npc_tracker.md      # → _npcs.md (NPC gallery)
│   ├── thread_tracker.md   # → _threads.md (dormant threads)
│   └── faction_overview.md # → _factions.md (standings)
└── campaigns/              # Per-campaign overlays
    └── {campaign_id}/      # Campaign-specific content
        ├── _index.md       # Campaign hub (folder note)
        ├── _events.md      # Session timeline
        ├── _npcs.md        # NPC tracker dashboard
        ├── _threads.md     # Thread tracker dashboard
        ├── _factions.md    # Faction standings dashboard
        ├── Characters/     # Player characters
        │   └── {name}.md
        ├── NPCs/           # NPC overlay pages
        │   ├── _index.md   # NPC index by faction
        │   └── {name}.md
        ├── sessions/       # Session summaries
        │   └── {date}/
        │       ├── {date}.md
        │       └── _game_log.md
        ├── threads/        # Individual thread notes (Dataview)
        ├── hinges/         # Individual hinge notes (Dataview)
        └── factions/       # Faction overlay notes (Dataview)
```

## Dashboard Templates

Dashboard templates in `wiki/templates/` are automatically copied to new campaigns on first load. They use Dataview queries with `this.file.folder` for campaign isolation.

**Templates:**

| Template | Destination | Purpose |
|----------|-------------|---------|
| `campaign_index.md` | `_index.md` | Campaign hub with navigation and status |
| `npc_tracker.md` | `_npcs.md` | NPC gallery with portraits and dispositions |
| `thread_tracker.md` | `_threads.md` | Dormant threads by severity |
| `faction_overview.md` | `_factions.md` | Faction standings and relationships |

**Placeholders replaced on copy:**
- `{{campaign_id}}` → Campaign ID
- `{{campaign_name}}` → Campaign name (title case)
- `{{character_name}}` → Player character name (set on first `/char wiki`)

## Individual Notes

For Dataview queries to work, events are stored as individual notes with typed frontmatter:

**Thread notes** (`threads/{slug}.md`):
```yaml
---
type: thread
status: active | resolved
severity: minor | moderate | major
origin: "What caused this"
trigger: "When it fires"
consequence: "What happens"
created_session: 3
---
```

**Hinge notes** (`hinges/{slug}.md`):
```yaml
---
type: hinge
session: 2
label: "Decision Name"
what_shifted: "Consequences"
---
```

**Faction overlays** (`factions/{slug}.md`):
```yaml
---
type: faction-overlay
faction: "Faction Name"
standing: Allied | Friendly | Neutral | Unfriendly | Hostile
---
```

## Conventions

### Callout Types

Use Obsidian callouts to visually distinguish content types:

| Callout | Use For | Example |
|---------|---------|---------|
| `[!quote]` | Character quotes, canon citations | Dialogue, philosophy |
| `[!info]` | Statistics, data, neutral facts | Day One stats |
| `[!danger]` | Critical events, irreversible moments | Zero Hour |
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
type: faction | region | event | hub | npc | character | thread | hinge
tags:
  - relevant-tags
campaign: campaign_id  # For campaign-specific pages
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

- **Auto-generation:** Dashboards created on campaign init
- **Live updates:** NPCs, hinges, threads logged during play
- **Bi-directional sync:** Edit frontmatter in Obsidian → game state updates
- **Retrieval:** Wiki pages indexed alongside lore (1.8x weight)
- **MCP Resources:** `wiki://{page}` exposes pages via MCP
- **MCP Tools:** `search_wiki` for keyword queries

## Commands

| Command | Effect |
|---------|--------|
| `/wiki` | Show campaign timeline |
| `/wiki <page>` | Show page with campaign overlay |
| `/char wiki` | Regenerate character wiki page |
| `/compare` | Cross-campaign faction analysis |

## Plugins (Recommended)

These Obsidian plugins enhance the experience:

| Plugin | Purpose |
|--------|---------|
| **Dataview** | Dynamic queries for threads, hinges, NPCs |
| **Mermaid** | Relationship diagrams (built-in) |
| **Calendar** | Session timeline navigation |

The wiki works without plugins—Dataview queries will just show as code blocks.
