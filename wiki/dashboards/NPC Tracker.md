---
type: dashboard
tags:
  - dashboard
  - npc
---

# NPC Tracker

Track NPC relationships across your campaign.

---

## Recently Encountered

NPCs you've interacted with recently, sorted by last interaction.

```dataview
TABLE faction, file.mtime AS "Last Seen"
FROM "campaigns/*/NPCs"
SORT file.mtime DESC
LIMIT 10
```

---

## By Faction

### Nexus Contacts

```dataview
LIST
FROM "campaigns/*/NPCs"
WHERE faction = "Nexus"
```

### Ember Colonies Contacts

```dataview
LIST
FROM "campaigns/*/NPCs"
WHERE faction = "Ember Colonies"
```

### Lattice Contacts

```dataview
LIST
FROM "campaigns/*/NPCs"
WHERE faction = "Lattice"
```

### Ghost Networks Contacts

```dataview
LIST
FROM "campaigns/*/NPCs"
WHERE faction = "Ghost Networks"
```

### Steel Syndicate Contacts

```dataview
LIST
FROM "campaigns/*/NPCs"
WHERE faction = "Steel Syndicate"
```

### Other Factions

```dataview
LIST
FROM "campaigns/*/NPCs"
WHERE faction != "Nexus" AND faction != "Ember Colonies" AND faction != "Lattice" AND faction != "Ghost Networks" AND faction != "Steel Syndicate"
```

---

## All NPCs

Complete list of all NPCs encountered across campaigns.

```dataview
TABLE faction, file.folder AS "Campaign"
FROM "campaigns/*/NPCs"
SORT faction ASC, file.name ASC
```

---

## See Also

- [[Campaign Hub]] — Main dashboard
- [[Faction Overview]] — Faction standings
