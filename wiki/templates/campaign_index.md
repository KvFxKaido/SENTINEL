---
type: dashboard
tags:
  - dashboard
  - hub
  - campaign
campaign: "{{campaign_id}}"
---

# {{campaign_name}} — Campaign Hub

Central dashboard for your SENTINEL campaign.

---

## Quick Navigation

| Page | Purpose |
|------|---------|
| [[_npcs\|NPCs]] | Character tracker with portraits |
| [[_threads\|Threads]] | Dormant consequences |
| [[_factions\|Factions]] | Standing overview |
| [[_events\|Timeline]] | Session-by-session history |

---

## Character

![[Characters/{{character_name}}\|{{character_name}}]]

---

## Recent Sessions

```dataview
TABLE WITHOUT ID
  file.link AS "Session",
  session AS "#",
  date AS "Date"
FROM this.file.folder + "/sessions"
WHERE type = "session"
SORT date DESC
LIMIT 5
```

---

## Active Threads

> [!warning] Consequences Waiting
> Dormant threads trigger when conditions are met.

```dataview
TABLE WITHOUT ID
  file.link AS "Thread",
  trigger AS "Trigger",
  severity AS "Severity"
FROM this.file.folder + "/threads"
WHERE type = "thread" AND status != "resolved"
SORT severity DESC
LIMIT 5
```

See [[_threads]] for full list.

---

## Recent Hinges

```dataview
TABLE WITHOUT ID
  file.link AS "Hinge",
  what_shifted AS "What Shifted"
FROM this.file.folder + "/hinges"
WHERE type = "hinge"
SORT session DESC
LIMIT 5
```

---

## Faction Standings

```dataview
TABLE WITHOUT ID
  file.link AS "Faction",
  standing AS "Standing"
FROM this.file.folder + "/factions"
WHERE type = "faction-overlay"
SORT standing DESC
```

See [[_factions]] for details.

---

## NPCs by Last Interaction

```dataview
TABLE WITHOUT ID
  file.link AS "Name",
  faction AS "Faction",
  disposition AS "Disposition"
FROM this.file.folder + "/NPCs"
SORT file.mtime DESC
LIMIT 5
```

See [[_npcs]] for full roster.

---

## See Also

- [[canon/Factions|Factions]] — Faction lore
- [[canon/Geography|Geography]] — Region reference
- [[canon/Timeline|Timeline]] — World history
