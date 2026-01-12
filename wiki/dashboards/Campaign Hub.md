---
type: dashboard
tags:
  - dashboard
  - hub
---

# Campaign Hub

Central dashboard for tracking your SENTINEL campaign.

> [!info] Dataview Required
> This dashboard uses live Dataview queries. Install the [Dataview plugin](https://github.com/blacksmithgu/obsidian-dataview) to see dynamic content.

---

## Quick Links

| Dashboard | Purpose |
|-----------|---------|
| [[NPC Tracker]] | Recent NPC interactions and dispositions |
| [[Thread Tracker]] | Active consequence threads by urgency |
| [[Faction Overview]] | Faction standings and relationships |

---

## Recent Sessions

```dataview
TABLE session, date
FROM "campaigns"
WHERE type = "session"
SORT date DESC
LIMIT 5
```

---

## Active Threads

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "[!thread]")
SORT date DESC
LIMIT 5
```

---

## Recent Hinges

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "[!hinge]")
SORT date DESC
LIMIT 5
```

---

## NPCs by Last Interaction

```dataview
TABLE faction
FROM "campaigns/*/NPCs"
SORT file.mtime DESC
LIMIT 5
```

---

## See Also

- [[Factions]] — Faction reference
- [[Geography]] — Region reference
- [[Timeline]] — World history
- [[Dataview Queries]] — Query examples
