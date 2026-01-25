---
type: dashboard
tags:
  - dashboard
  - threads
  - consequences
  - campaign
campaign: "{{campaign_id}}"
---

# Threads — {{campaign_name}}

Dormant consequence threads waiting to trigger.

> [!warning] Consequences Are Coming
> These threads represent delayed consequences from past choices. They will trigger when conditions are met.

---

## Active Threads

```dataview
TABLE WITHOUT ID
  origin AS "Origin",
  trigger AS "Trigger Condition",
  consequence AS "Consequence",
  severity AS "Severity",
  created_session AS "Since"
FROM this.file.folder
WHERE type = "thread" AND status != "resolved"
SORT severity DESC
```

---

## By Severity

### Major

> [!danger] Major Consequences
> Faction-wide effects, permanent standing changes, or NPC death.

```dataview
LIST WITHOUT ID origin + " — " + consequence
FROM this.file.folder
WHERE type = "thread" AND severity = "major" AND status != "resolved"
```

### Moderate

> [!warning] Moderate Consequences
> Significant but recoverable effects.

```dataview
LIST WITHOUT ID origin + " — " + consequence
FROM this.file.folder
WHERE type = "thread" AND severity = "moderate" AND status != "resolved"
```

### Minor

> [!info] Minor Consequences
> Small complications, temporary setbacks.

```dataview
LIST WITHOUT ID origin + " — " + consequence
FROM this.file.folder
WHERE type = "thread" AND severity = "minor" AND status != "resolved"
```

---

## Thread Timeline

When threads were created.

```dataview
TABLE WITHOUT ID
  origin AS "Origin",
  severity AS "Severity",
  created_session AS "Session"
FROM this.file.folder
WHERE type = "thread"
SORT created_session DESC
```

---

## Resolved Threads

Threads that have triggered or been defused.

```dataview
TABLE WITHOUT ID
  origin AS "Origin",
  consequence AS "What Happened",
  resolved_session AS "Resolved"
FROM this.file.folder
WHERE type = "thread" AND status = "resolved"
SORT resolved_session DESC
```

---

## See Also

- [[_index|Campaign Hub]]
- [[_events|Timeline]]
- [[canon/Dormant Threads|Thread Mechanics]]
