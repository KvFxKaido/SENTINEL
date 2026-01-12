---
type: dashboard
tags:
  - dashboard
  - npc
cssclasses:
  - cards
---

# NPC Tracker

Track NPC relationships across your campaign.

> [!tip] Portraits
> Generate portraits with: `python scripts/generate_portrait.py npc "Name" --campaign your_campaign`
> Portraits are stored in `assets/portraits/npcs/` (gitignored).

---

## Portrait Gallery

NPCs with generated portraits displayed as cards.

```dataview
TABLE WITHOUT ID
  embed(link("assets/portraits/" + portrait, "100")) AS Portrait,
  file.link AS Name,
  faction AS Faction
FROM "campaigns/*/NPCs"
WHERE portrait
SORT file.mtime DESC
LIMIT 12
```

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
