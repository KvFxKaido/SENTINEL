---
type: dashboard
tags:
  - dashboard
  - threads
  - consequences
---

# Thread Tracker

Track dormant consequence threads waiting to trigger.

> [!warning] Consequences Are Coming
> These threads represent delayed consequences from past choices. They will trigger when conditions are met.

---

## Active Threads

Sessions where new threads were queued.

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "[!thread]")
SORT date DESC
```

---

## By Severity

### Major Threads

> [!danger] Major
> Faction-wide consequences, permanent standing changes, or NPC death.

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "MAJOR")
SORT date DESC
```

### Moderate Threads

> [!warning] Moderate
> Significant but recoverable consequences.

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "MODERATE")
SORT date DESC
```

### Minor Threads

> [!info] Minor
> Small complications, temporary setbacks.

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "MINOR")
SORT date DESC
```

---

## Resolved Threads

Threads that have triggered or been defused.

```dataview
LIST
FROM "campaigns"
WHERE type = "session" AND contains(file.content, "## Threads Resolved")
SORT date DESC
```

---

## Thread Timeline

All sessions with thread activity.

```dataview
TABLE session, date
FROM "campaigns"
WHERE type = "session" AND (contains(file.content, "[!thread]") OR contains(file.content, "Threads Resolved"))
SORT date DESC
```

---

## See Also

- [[Campaign Hub]] — Main dashboard
- [[Timeline]] — World events
