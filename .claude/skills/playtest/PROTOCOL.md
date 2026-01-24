# Playtest Protocol

Systematic testing checklist for SENTINEL. Execute each section in order.

## Phase 0: Environment Check

- [ ] Bridge responds to `/health`
- [ ] Bridge state is "ready"
- [ ] Backend is "claude" (REQUIRED)

```bash
# Check health
curl -s http://localhost:3333/health | jq .

# Check state and verify backend is claude
curl -s http://localhost:3333/state | jq .

# If backend is not claude, switch it:
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/backend", "args": ["claude"]}'

# Verify switch
curl -s http://localhost:3333/state | jq -r '.sentinel.backend'
# Expected: claude
```

**STOP** if backend cannot be set to Claude. Playtesting requires Claude for consistent GM behavior.

## Phase 1: Campaign Lifecycle

### 1.1 Create Campaign
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/new", "args": ["Playtest-Unique-ID"]}'
```
**Expected**: `{"ok": true}` or campaign created message
**Verify**: `/state` shows campaign loaded

### 1.2 List Campaigns
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/list", "args": []}'
```
**Expected**: List includes newly created campaign

### 1.3 Save Campaign
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "save"}'
```
**Expected**: `{"ok": true}`

### 1.4 Load Campaign
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "load", "campaign_id": "1"}'
```
**Expected**: Campaign loads successfully

## Phase 2: Character Creation

### 2.1 Quick Character
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/char", "args": ["quick"]}'
```
**Expected**: Character created with default values
**Verify**: `campaign_state` shows character with name, background, social_energy

### 2.2 View Character
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/char", "args": []}'
```
**Expected**: Character details displayed

### 2.3 Campaign State Check
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "campaign_state"}'
```
**Verify**:
- `character.name` is set
- `character.background` is valid
- `character.social_energy.current` is 50-100
- `factions` array is populated

## Phase 3: Gameplay Commands

### 3.1 Status Command
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/status", "args": []}'
```
**Expected**: Status display without errors

### 3.2 Factions Command
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/factions", "args": []}'
```
**Expected**: All 11 factions listed with standings

### 3.3 Roll Command
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/roll", "args": ["untrained"]}'
```
**Expected**: Roll result with d20 + modifier

### 3.4 Loadout Command
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/loadout", "args": []}'
```
**Expected**: Current loadout displayed

### 3.5 Region Command
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/region", "args": []}'
```
**Expected**: Current region with faction control info

### 3.6 Jobs Command
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/jobs", "args": []}'
```
**Expected**: Job board displayed or empty message

### 3.7 Shop Command
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/shop", "args": []}'
```
**Expected**: Vehicle shop with prices

## Phase 4: Session Start (Requires LLM)

### 4.1 Start Session
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/start", "args": []}'
```
**Expected**:
- `response` field contains GM narration
- Session phase updates
- No errors

### 4.2 Player Action
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "say", "text": "I look around and assess the situation"}'
```
**Expected**: GM response in `response` field

### 4.3 State After Action
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "campaign_state"}'
```
**Verify**: State reflects any changes from GM tools

## Phase 5: Edge Cases

### 5.1 Invalid Command
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/notacommand", "args": []}'
```
**Expected**: Graceful error message, no crash

### 5.2 Missing Arguments
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "slash", "command": "/load", "args": []}'
```
**Expected**: Error message about missing campaign

### 5.3 Empty Say
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "say", "text": ""}'
```
**Expected**: Handled gracefully

### 5.4 Very Long Input
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "say", "text": "'"$(python -c "print('a' * 10000)")"'"}'
```
**Expected**: Handled without crash (may truncate)

### 5.5 Special Characters
```bash
curl -s -X POST http://localhost:3333/command \
  -H "Content-Type: application/json" \
  -d '{"cmd": "say", "text": "I say \"hello\" and use <tags> & symbols"}'
```
**Expected**: JSON escaped properly, no injection

## Phase 6: State Consistency

### 6.1 Social Energy Tracking
1. Note initial social_energy from campaign_state
2. Start session, make social action
3. Check social_energy changed appropriately

### 6.2 Faction Standing Changes
1. Note initial faction standings
2. Perform action that should affect standing
3. Verify standing updated in campaign_state

### 6.3 Save/Load Roundtrip
1. Make several state changes
2. Save campaign
3. Load a different campaign (or restart bridge)
4. Load original campaign
5. Verify all state restored correctly

## Phase 7: Stress Tests

### 7.1 Rapid Commands
```bash
for i in {1..10}; do
  curl -s -X POST http://localhost:3333/command \
    -H "Content-Type: application/json" \
    -d '{"cmd": "slash", "command": "/status", "args": []}' &
done
wait
```
**Expected**: All complete without errors (may be serialized)

### 7.2 Concurrent State Reads
```bash
for i in {1..5}; do
  curl -s -X POST http://localhost:3333/command \
    -H "Content-Type: application/json" \
    -d '{"cmd": "campaign_state"}' &
done
wait
```
**Expected**: Consistent results

## Bug Documentation Template

When you find a bug, document it as:

```markdown
### BUG-XXX: [Short Description]

**Severity**: CRITICAL | HIGH | MEDIUM | LOW

**Steps to Reproduce**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Behavior**:
[What should happen]

**Actual Behavior**:
[What actually happened]

**Error Output** (if any):
```
[paste error here]
```

**State Before**:
[relevant state]

**State After**:
[relevant state]

**Notes**:
[Any additional context]
```

## Completion Checklist

- [ ] Phase 0: Environment verified
- [ ] Phase 1: Campaign lifecycle works
- [ ] Phase 2: Character creation works
- [ ] Phase 3: Gameplay commands work
- [ ] Phase 4: Session start works (if LLM available)
- [ ] Phase 5: Edge cases handled gracefully
- [ ] Phase 6: State consistency verified
- [ ] Phase 7: Stress tests passed
- [ ] Bug report generated
