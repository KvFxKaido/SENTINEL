# SENTINEL Wiki Canon Integrity Report

**Generated:** 2026-01-15T07:52:21.987040-06:00  
**Scope:** All 32 canon files in `C:\dev\SENTINEL\wiki\canon\`

---

## Task 1: Orphan Pages Check

**Definition:** Canon pages not linked from any of the 4 hub pages (Home.md, Factions.md, Geography.md, Timeline.md)

### Result: ✅ MOSTLY CLEAN
- **Total canon pages checked:** 28 (excluding 4 hub pages)
- **Pages linked from hubs:** 27 out of 28
- **Orphan pages found:** 1

### Orphan Page Identified
- **Dataview Queries.md** - This page exists in canon but is not referenced from any hub page

### Recommendation
Consider adding a link to [[Dataview Queries]] from an appropriate hub page, possibly under the "For Game Masters" section of [[Home]] or in a technical/tools section.

---

## Task 2: Broken Section Links Check

**Definition:** Wiki links with section anchors (`[[Page#Section]]` or `[[Page#Section|Display]]`) where either:
- The target page doesn't exist, OR
- The target page exists but the specified section heading is not found

### Result: ✅ CLEAN
- **Section links found:** 0
- **Broken section links:** 0

### Analysis
No section links were found in any of the canon files, which means there are no broken section links to report.

---

## Summary

| Check | Status | Issues Found |
|-------|--------|--------------|
| Orphan Pages | ⚠️ MINOR | 1 orphan page |
| Broken Section Links | ✅ CLEAN | 0 broken links |

### Overall Assessment
The SENTINEL wiki canon directory is in excellent structural health:
- 96% of canon pages are properly linked from hub pages
- No broken section links exist
- The single orphan page ([[Dataview Queries]]) appears to be a technical reference page that may have been intentionally left unlinked

### Files Checked
All 32 markdown files in `canon/` directory were analyzed, including:
- 4 hub pages (Home, Factions, Geography, Timeline)
- 11 faction pages
- 11 region pages  
- 6 other canon pages (events, concepts, etc.)

The wiki structure demonstrates strong internal connectivity and proper cross-referencing.