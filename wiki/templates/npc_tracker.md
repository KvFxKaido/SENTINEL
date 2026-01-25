---
type: dashboard
tags:
  - dashboard
  - npc
  - campaign
campaign: "{{campaign_id}}"
cssclasses:
  - cards
---

# NPCs — {{campaign_name}}

Character tracker for your campaign.

> [!tip] Portraits
> Generate with `/portrait <name>` in SENTINEL.
> Portraits stored in `assets/portraits/campaigns/{{campaign_id}}/`

---

## Portrait Gallery

```dataview
TABLE WITHOUT ID
  embed(link(portrait, "100")) AS Portrait,
  file.link AS Name,
  faction AS Faction,
  disposition AS Disposition
FROM this.file.folder + "/NPCs"
WHERE portrait
SORT file.mtime DESC
LIMIT 12
```

---

## Recently Encountered

```dataview
TABLE WITHOUT ID
  file.link AS "Name",
  faction AS "Faction",
  disposition AS "Disposition",
  file.mtime AS "Last Seen"
FROM this.file.folder + "/NPCs"
SORT file.mtime DESC
LIMIT 10
```

---

## By Disposition

### Loyal & Warm

> [!success] Trusted contacts

```dataview
LIST
FROM this.file.folder + "/NPCs"
WHERE disposition = "loyal" OR disposition = "warm"
SORT faction ASC
```

### Neutral

```dataview
LIST
FROM this.file.folder + "/NPCs"
WHERE disposition = "neutral"
SORT faction ASC
```

### Wary & Hostile

> [!warning] Handle with care

```dataview
LIST
FROM this.file.folder + "/NPCs"
WHERE disposition = "wary" OR disposition = "hostile"
SORT faction ASC
```

---

## By Faction

### Nexus

```dataview
LIST
FROM this.file.folder + "/NPCs"
WHERE faction = "nexus" OR faction = "Nexus"
```

### Ember Colonies

```dataview
LIST
FROM this.file.folder + "/NPCs"
WHERE faction = "ember_colonies" OR faction = "Ember Colonies"
```

### Ghost Networks

```dataview
LIST
FROM this.file.folder + "/NPCs"
WHERE faction = "ghost_networks" OR faction = "Ghost Networks"
```

### Steel Syndicate

```dataview
LIST
FROM this.file.folder + "/NPCs"
WHERE faction = "steel_syndicate" OR faction = "Steel Syndicate"
```

### Other Factions

```dataview
LIST
FROM this.file.folder + "/NPCs"
WHERE faction != "nexus" AND faction != "Nexus"
  AND faction != "ember_colonies" AND faction != "Ember Colonies"
  AND faction != "ghost_networks" AND faction != "Ghost Networks"
  AND faction != "steel_syndicate" AND faction != "Steel Syndicate"
```

---

## All NPCs

```dataview
TABLE WITHOUT ID
  file.link AS "Name",
  faction AS "Faction",
  disposition AS "Disposition",
  personal_standing AS "Personal"
FROM this.file.folder + "/NPCs"
SORT faction ASC, file.name ASC
```

---

## See Also

- [[_index|Campaign Hub]]
- [[_factions|Faction Standings]]
