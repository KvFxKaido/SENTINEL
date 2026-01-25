# Web UI Playtest Protocol

Visual testing checklist for SENTINEL web interface. Execute each phase in order.

## Phase 0: Environment Setup

### 0.1 Establish Browser Context
```
1. mcp__claude-in-chrome__tabs_context_mcp
2. mcp__claude-in-chrome__tabs_create_mcp (create fresh test tab)
3. Note the tabId for all subsequent operations
```

### 0.2 Navigate to UI
```
mcp__claude-in-chrome__navigate
  url: "http://localhost:4321"
  tabId: <your-tab-id>
```

### 0.3 Verify Page Load
```
mcp__claude-in-chrome__computer
  action: "screenshot"
  tabId: <your-tab-id>

mcp__claude-in-chrome__read_page
  tabId: <your-tab-id>
  filter: "interactive"
```

**Expected**:
- Header visible with SENTINEL title
- 3-column layout: SELF | NARRATIVE | WORLD
- Command input at bottom
- Status dot in header

**STOP** if you see "Bridge Not Connected" error. Ask user to start the bridge.

## Phase 1: Layout Verification

### 1.1 Three-Column Structure
Use read_page to verify:
- [ ] Left panel has class `left-panel` with `tui-panel self-panel`
- [ ] Center has class `main-content` with `narrative-log`
- [ ] Right panel has class `right-panel` with `tui-panel world-panel`

### 1.2 Panel Headers
Verify panel titles are visible:
- [ ] "SELF" title in left panel
- [ ] "WORLD" title in right panel
- [ ] Section headers: "-- STATUS --", "-- LOADOUT --", "-- STANDINGS --", etc.

### 1.3 Command Area
- [ ] Command input is visible and focusable
- [ ] Prompt character ">" is visible
- [ ] SEND button is visible
- [ ] Quick command buttons visible: status, jobs, wiki, save, help

### 1.4 Responsive Test (Optional)
```
mcp__claude-in-chrome__resize_window
  width: 900
  height: 800
  tabId: <your-tab-id>
```
- [ ] Side panels hidden at narrow width (<1000px)
- [ ] Narrative area expands to fill width
- [ ] Command input still accessible

Reset to full width after test.

## Phase 2: Command Input Interaction

### 2.1 Type in Command Input
```
mcp__claude-in-chrome__find
  query: "command input"
  tabId: <your-tab-id>

mcp__claude-in-chrome__form_input
  ref: "ref_X" (from find result for command-input)
  value: "/status"
  tabId: <your-tab-id>
```
**Verify**: Input shows "/status"

### 2.2 Submit Command
```
mcp__claude-in-chrome__find
  query: "SEND button"
  tabId: <your-tab-id>

mcp__claude-in-chrome__computer
  action: "left_click"
  ref: "ref_X" (SEND button ref)
  tabId: <your-tab-id>

mcp__claude-in-chrome__computer
  action: "wait"
  duration: 2
  tabId: <your-tab-id>
```

### 2.3 Verify Response
```
mcp__claude-in-chrome__read_page
  tabId: <your-tab-id>
```
- [ ] Command input cleared after submit
- [ ] Message appeared in narrative log
- [ ] Loading state showed (prompt character pulsed) then cleared

### 2.4 Quick Command Buttons
```
mcp__claude-in-chrome__find
  query: "jobs button"
  tabId: <your-tab-id>

mcp__claude-in-chrome__computer
  action: "left_click"
  ref: "ref_X"
  tabId: <your-tab-id>
```
- [ ] Command input populated with "/jobs"
- [ ] Can then click SEND to execute

## Phase 3: Campaign Workflow

### 3.1 Create New Campaign
```
Type: /new WebPlaytest
Click: SEND
Wait: 3 seconds
```
- [ ] No error in narrative log
- [ ] Campaign info in header updates

### 3.2 Create Character
```
Type: /char quick
Click: SEND
Wait: 2 seconds
```
- [ ] Character name appears in SELF panel (#char-name)
- [ ] Background appears (#char-background)
- [ ] Energy bar has non-zero width

### 3.3 Verify State Display Sync
```
mcp__claude-in-chrome__javascript_tool
  action: "javascript_exec"
  text: "JSON.stringify(window.__campaignState?.character || {})"
  tabId: <your-tab-id>
```

Compare JavaScript result to displayed values:
- [ ] Name matches #char-name
- [ ] Background matches #char-background
- [ ] Credits match #credits-value
- [ ] Energy percentage matches #energy-value

### 3.4 Start Session
```
Type: /start
Click: SEND
Wait: 5 seconds (GM response takes time)
```
- [ ] GM response appears in narrative log
- [ ] Codec frame styling applied (portrait, disposition bar)
- [ ] No JavaScript errors

### 3.5 Send Player Action
```
Type: I look around carefully
Click: SEND
Wait: 5 seconds
```
- [ ] User message appears in narrative
- [ ] GM response appears
- [ ] State may have updated (check energy bar)

## Phase 4: State Panel Updates

### 4.1 Faction Standings Display
```
mcp__claude-in-chrome__javascript_tool
  action: "javascript_exec"
  text: "document.querySelectorAll('.standing-row').length"
  tabId: <your-tab-id>
```
- [ ] 11 factions displayed (one row per faction)
- [ ] Each has name, progress bar, standing label
- [ ] Colors match standing level (hostile=red, friendly=green, etc.)

### 4.2 Standing Bar Verification
For each visible standing:
- [ ] Progress bar width corresponds to standing level
- [ ] CSS class matches standing (hostile, unfriendly, neutral, friendly, allied)
- [ ] Label text matches class

### 4.3 Thread Display
If threads exist:
- [ ] Thread items visible in WORLD panel
- [ ] Thread icon (!) present
- [ ] Thread text not truncated inappropriately

### 4.4 Event Log
- [ ] Events appear as they happen
- [ ] Event type highlighted in cyan
- [ ] Log scrolls and caps at 15 entries

## Phase 5: Codec Frame Styling

### 5.1 Player Message Style
When user sends a message:
- [ ] Codec frame appears
- [ ] Character name shown (or "YOU")
- [ ] Portrait placeholder visible
- [ ] Disposition bar segments filled appropriately

### 5.2 GM/NPC Message Style
When GM responds:
- [ ] Codec frame has different color (faction-based)
- [ ] NPC name parsed from "Name: dialogue" format
- [ ] State indicator shows "SECURE CONNECTION"
- [ ] Scanlines effect on portrait

### 5.3 Choice Options
If GM presents numbered options:
- [ ] Options rendered as choice-item divs
- [ ] Choice index numbers visible
- [ ] Choices are distinct and readable

### 5.4 System Messages
For command output (not GM):
- [ ] System message style (centered, muted)
- [ ] No Codec frame
- [ ] Clear distinction from GM dialogue

## Phase 6: Edge Cases

### 6.1 Empty States
Before character creation:
- [ ] Character name shows "—"
- [ ] Background shows "[No character]"
- [ ] Loadout shows "[Empty]"
- [ ] Threads show "[No active threads]"

### 6.2 Error Handling
```
Type: /notarealcommand
Click: SEND
Wait: 1 second
```
- [ ] Error message appears (red styling)
- [ ] App doesn't crash
- [ ] Can continue using other commands

### 6.3 Long Content
```
Type: I want to write a very long message that goes on and on describing my character's elaborate plan to infiltrate the Nexus compound by disguising as a maintenance worker...
Click: SEND
Wait: 3 seconds
```
- [ ] Message wraps properly
- [ ] No horizontal overflow
- [ ] Narrative log scrolls to show new content

### 6.4 Special Characters
```
Type: I say "Hello" and use <brackets> & symbols!
Click: SEND
Wait: 2 seconds
```
- [ ] Characters escaped properly
- [ ] No XSS issues
- [ ] Display looks correct

## Phase 7: Cross-Reference with API

### 7.1 State Consistency Check
After making changes, verify UI matches API:
```
mcp__claude-in-chrome__javascript_tool
  action: "javascript_exec"
  text: `
    const s = window.__campaignState;
    JSON.stringify({
      char_name: s?.character?.name,
      energy_current: s?.character?.social_energy?.current,
      energy_max: s?.character?.social_energy?.max,
      credits: s?.character?.credits,
      faction_count: s?.factions?.length,
      thread_count: s?.threads?.length
    })
  `
  tabId: <your-tab-id>
```

Read displayed values and compare:
- [ ] #char-name matches char_name
- [ ] #energy-value percentage = (energy_current / energy_max) * 100
- [ ] #credits-value matches credits + "c"
- [ ] Faction rows = faction_count
- [ ] Thread items = thread_count

## Bug Documentation Template

```markdown
### WEBUI-XXX: [Short Description]

**Severity**: CRITICAL | HIGH | MEDIUM | LOW

**Screenshot**: [Take screenshot with computer tool]

**Steps to Reproduce**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected UI**:
[What should be displayed]

**Actual UI**:
[What is displayed]

**Internal State** (if relevant):
```javascript
window.__campaignState.someField = value
```

**DOM Structure** (if relevant):
[read_page output snippet]

**Notes**:
[Any additional context]
```

## Completion Checklist

- [ ] Phase 0: Environment setup complete
- [ ] Phase 1: Layout verified
- [ ] Phase 2: Command input works
- [ ] Phase 3: Campaign workflow complete
- [ ] Phase 4: State panels update correctly
- [ ] Phase 5: Codec frames styled correctly
- [ ] Phase 6: Edge cases handled
- [ ] Phase 7: State consistency verified
- [ ] Screenshots captured for all issues
- [ ] Bug report generated
