---
type: dashboard
tags:
  - dashboard
  - factions
---

# Faction Overview

Track faction standings and relationships across your campaign.

---

## The Eleven Factions

```dataview
TABLE philosophy, status
FROM "canon"
WHERE type = "faction"
SORT file.name ASC
```

---

## Faction Standing Changes

Sessions where faction standings changed.

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "[!faction]")
SORT date DESC
```

---

## By Faction

### Nexus

> [!abstract] Assistance through integration

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "Nexus")
SORT date DESC
LIMIT 5
```

### Ember Colonies

> [!abstract] Autonomy at any cost

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "Ember")
SORT date DESC
LIMIT 5
```

### Lattice

> [!abstract] Enhance humanity beyond weakness

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "Lattice")
SORT date DESC
LIMIT 5
```

### Ghost Networks

> [!abstract] Invisible resistance and sabotage

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "Ghost")
SORT date DESC
LIMIT 5
```

---

## Territorial Control

Regions and their controlling factions.

```dataview
TABLE primary AS "Primary", contested AS "Contested", location
FROM "canon"
WHERE type = "region"
SORT file.name ASC
```

---

## Relationship Quick Reference

| Relationship | Factions |
|--------------|----------|
| **Deep Rivalry** | [[Nexus]] ↔ [[Ghost Networks]] |
| **Ideological War** | [[Ember Colonies]] ↔ [[Convergence]] |
| **Records Dispute** | [[Witnesses]] ↔ [[Architects]] |
| **Mutual Dependency** | [[Nexus]] ↔ [[Lattice]] |
| **Trust & Stories** | [[Ember Colonies]] ↔ [[Witnesses]] |
| **Escape & Sanctuary** | [[Ghost Networks]] ↔ [[Ember Colonies]] |

See [[Factions#Relationship Web]] for the full diagram.

---

## See Also

- [[Campaign Hub]] — Main dashboard
- [[Factions]] — Full faction reference
- [[Geography]] — Territorial control
