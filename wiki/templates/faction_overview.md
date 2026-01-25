---
type: dashboard
tags:
  - dashboard
  - factions
  - campaign
campaign: "{{campaign_id}}"
---

# Factions — {{campaign_name}}

Track faction standings and relationships.

---

## Current Standings

```dataview
TABLE WITHOUT ID
  file.link AS "Faction",
  standing AS "Standing",
  recent_change AS "Recent Change"
FROM this.file.folder
WHERE type = "faction-overlay"
SORT standing DESC
```

---

## Standing History

Sessions where faction standings changed.

```dataview
LIST WITHOUT ID choice + " — " + what_shifted
FROM this.file.folder
WHERE type = "hinge" AND contains(tags, "faction")
SORT session DESC
LIMIT 10
```

---

## By Standing Level

### Allied

> [!success] Strong Allies

```dataview
LIST
FROM this.file.folder
WHERE type = "faction-overlay" AND standing = "Allied"
```

### Friendly

```dataview
LIST
FROM this.file.folder
WHERE type = "faction-overlay" AND standing = "Friendly"
```

### Neutral

```dataview
LIST
FROM this.file.folder
WHERE type = "faction-overlay" AND standing = "Neutral"
```

### Unfriendly

> [!warning] Strained Relations

```dataview
LIST
FROM this.file.folder
WHERE type = "faction-overlay" AND standing = "Unfriendly"
```

### Hostile

> [!danger] Active Opposition

```dataview
LIST
FROM this.file.folder
WHERE type = "faction-overlay" AND standing = "Hostile"
```

---

## Faction NPCs

NPCs grouped by faction affiliation.

```dataview
TABLE WITHOUT ID
  faction AS "Faction",
  rows.file.link AS "Contacts"
FROM this.file.folder + "/NPCs"
GROUP BY faction
SORT faction ASC
```

---

## Relationship Quick Reference

| Relationship | Factions |
|--------------|----------|
| **Deep Rivalry** | [[canon/Nexus\|Nexus]] ↔ [[canon/Ghost Networks\|Ghost Networks]] |
| **Ideological War** | [[canon/Ember Colonies\|Ember]] ↔ [[canon/Convergence\|Convergence]] |
| **Records Dispute** | [[canon/Witnesses\|Witnesses]] ↔ [[canon/Architects\|Architects]] |
| **Mutual Dependency** | [[canon/Nexus\|Nexus]] ↔ [[canon/Lattice\|Lattice]] |
| **Trust & Stories** | [[canon/Ember Colonies\|Ember]] ↔ [[canon/Witnesses\|Witnesses]] |

See [[canon/Factions#Relationship Web]] for full diagram.

---

## See Also

- [[_index|Campaign Hub]]
- [[_npcs|NPC Tracker]]
- [[canon/Factions|Faction Lore]]
- [[canon/Geography|Territorial Control]]
