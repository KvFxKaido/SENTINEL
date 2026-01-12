---
type: reference
tags:
  - meta
  - dataview
  - queries
---

# Dataview Queries

Example queries for the SENTINEL wiki. Requires the [Dataview plugin](https://github.com/blacksmithgu/obsidian-dataview).

> [!info] Plugin Required
> These queries only work with the Dataview plugin installed in Obsidian.

---

## Faction Queries

### All Factions

```dataview
TABLE philosophy, status
FROM "canon"
WHERE type = "faction"
SORT file.name ASC
```

### Factions by Tag

```dataview
LIST
FROM "canon"
WHERE type = "faction" AND contains(tags, "resistance")
```

---

## Region Queries

### All Regions with Control

```dataview
TABLE primary AS "Primary Faction", contested AS "Contested By", location
FROM "canon"
WHERE type = "region"
SORT file.name ASC
```

### Regions by Faction

```dataview
LIST
FROM "canon"
WHERE type = "region" AND primary = "Ember Colonies"
```

---

## Session Queries

### Recent Sessions

```dataview
TABLE session, date
FROM "campaigns"
WHERE type = "session"
SORT date DESC
LIMIT 10
```

### Sessions with Hinges

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "[!hinge]")
SORT date DESC
```

---

## NPC Queries

### NPCs by Faction

```dataview
TABLE faction, file.folder AS "Campaign"
FROM "campaigns"
WHERE type = "npc"
SORT faction ASC
```

### NPCs Encountered Recently

```dataview
TABLE faction
FROM "campaigns/*/NPCs"
SORT file.mtime DESC
LIMIT 10
```

---

## Cross-Campaign Analysis

### All Hinges Across Campaigns

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "[!hinge]")
GROUP BY file.folder
```

### Faction Standing Changes

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "[!faction]")
SORT date DESC
```

---

## See Also

- [[Factions]] — Faction overview
- [[Geography]] — Region overview
- [[Timeline]] — Chronological history
