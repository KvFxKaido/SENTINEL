# Wiki Agent Context

Instructions for AI agents working with the SENTINEL wiki.

## Structure Overview

```
wiki/
├── canon/              # Base lore (source of truth, never modify during checks)
│   ├── Home.md         # Landing page, primary index
│   ├── Factions.md     # Hub: links to all 11 factions
│   ├── Geography.md    # Hub: links to all 11 regions
│   ├── Timeline.md     # Hub: chronological events
│   ├── {Faction}.md    # One per faction (11 total)
│   └── {Region}.md     # One per region (11 total)
├── campaigns/          # Per-campaign overlays (auto-generated)
│   ├── _meta/          # Cross-campaign analysis
│   └── {campaign_id}/  # Campaign-specific additions
├── dashboards/         # Dataview query pages
└── templates/          # Jinja2 templates (if present)
```

## The 11 Factions

Every faction must have a canon page:
- Nexus, Ember Colonies, Lattice, Convergence, Covenant
- Wanderers, Cultivators, Steel Syndicate, Witnesses, Architects, Ghost Networks

## The 11 Regions

Every region must have a canon page:
- Rust Corridor, Appalachian Hollows, Gulf Passage, The Breadbasket
- Northern Reaches, Pacific Corridor, Desert Sprawl, Northeast Scar
- Sovereign South, Texas Spine, Frozen Edge

## Required Frontmatter

All pages MUST have frontmatter with at minimum:

```yaml
---
type: faction | region | event | hub | npc | index
tags:
  - at-least-one-tag
---
```

Optional but encouraged:
```yaml
aliases:
  - Alternate Name
  - Short Name
```

## Wikilink Conventions

### Valid Link Formats
- `[[Page Name]]` — Standard link
- `[[Page Name|Display Text]]` — Aliased display
- `[[Page Name#Section]]` — Section anchor
- `[[Page Name#Section|Display]]` — Section with alias

### Link Resolution Rules
1. Exact page name match (case-sensitive filename, but Obsidian is case-insensitive)
2. Alias match from frontmatter
3. Links ARE BROKEN if neither exists

### Common Aliases to Check
These aliases are defined in frontmatter and should resolve:
- `Awakening` → `The Awakening`
- `Geography` → `Geography.md`
- `SENTINEL Wiki` → `Home.md`

## Callout Syntax

Valid callout blocks:
```markdown
> [!type] Optional Title
> Content line 1
> Content line 2
```

### Standard Types (Obsidian built-in)
`quote`, `info`, `danger`, `important`, `abstract`, `warning`, `note`, `tip`, `example`

### Campaign-Specific Types
`hinge`, `faction`, `thread`, `npc`

## Mermaid Diagrams

All faction pages should have relationship diagrams using this notation:
```
graph LR
    A ===|"cooperative"| B    %% Solid thick = friendly
    A -.-|"tense"| C          %% Dashed = strained
    A ---|"hostile"| D        %% Solid thin = hostile
```

## Integrity Checks to Perform

### Critical (Must Pass)
1. **Broken wikilinks** — Links to pages that don't exist and aren't aliases
2. **Missing frontmatter** — Pages without `type` field
3. **Missing factions** — Any of the 11 factions without a canon page
4. **Missing regions** — Any of the 11 regions without a canon page

### Important (Should Pass)
5. **Orphan pages** — Pages not linked from any hub (Home, Factions, Geography, Timeline)
6. **Empty aliases** — Frontmatter with `aliases:` but no entries
7. **Broken section links** — `[[Page#Section]]` where section doesn't exist

### Advisory (Nice to Fix)
8. **Inconsistent casing** — `[[nexus]]` vs `[[Nexus]]`
9. **Missing mermaid diagrams** — Faction pages without relationship graphs
10. **Callout syntax errors** — Malformed `[!type]` blocks

## Lore Cross-Reference

The `lore/` directory contains source novellas and reference documents. Wiki pages that reference story content should match lore filenames.

### Lore Naming Convention
Lore files use chapter prefixes:
```
lore/
├── 00 - The Contingency.md
├── 01 - First Deployment.md
├── 02 - Patterns.md
├── ...
├── 08 - Reese's Awakening.md
├── Cipher - Sample Character.md      # No prefix (reference doc)
└── SENTINEL Canon Bible — Unified Lore Edition.md
```

### Wiki-Lore Title Matching Rules
1. Wiki page title should match lore title **after stripping chapter prefix**
2. Strip pattern: `^\d+\s*-\s*` (digits, optional space, hyphen, space)
3. Case must match exactly (Obsidian is case-insensitive but consistency matters)

### Examples
| Wiki Reference | Expected Lore File | Status |
|----------------|-------------------|--------|
| `[[First Deployment]]` | `01 - First Deployment.md` | OK (prefix stripped) |
| `[[The Awakening]]` | `05 - The Awakening.md` | OK |
| `[[Ghost in The Machine]]` | `06 - Ghost in the Machine.md` | MISMATCH (case: "The" vs "the") |

### Cross-Reference Checks
1. **Missing lore source** — Wiki references a story that doesn't exist in `lore/`
2. **Title drift** — Wiki title doesn't match lore title (after prefix strip)
3. **Orphan lore** — Lore file exists but no wiki page references it

### Resolution Priority
When titles mismatch, prefer **lore filename as source of truth** — update wiki to match.

## Overlay Rules

Campaign overlays in `campaigns/{id}/`:
- EXTEND canon, never replace it
- Use `extends: Canon_Page` in frontmatter
- Same heading = override that section
- New heading = append to canon

## Report Format

When reporting issues, use this format:

```markdown
## Wiki Integrity Report

### Critical Issues (X found)
- [ ] `Page.md:15` — Broken link: `[[Nonexistent Page]]`

### Important Issues (X found)
- [ ] `Page.md` — Missing frontmatter `type` field

### Advisory (X found)
- [ ] `Page.md:42` — Inconsistent casing: `[[nexus]]` should be `[[Nexus]]`

### Summary
- Canon pages: X/Y valid
- Total wikilinks: X checked, Y broken
- Frontmatter: X pages missing required fields
```
