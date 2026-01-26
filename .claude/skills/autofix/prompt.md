# Autofix Skill

Automated validation, fixing, and push to master. Designed for mobile/async workflows where you want to trigger fixes without manual intervention.

## Workflow

1. **Run validations** (in order)
2. **Fix what's fixable**
3. **Run tests** to verify fixes don't break anything
4. **Commit and push** successful fixes
5. **Report** any remaining issues

## Step 1: Run Mechanics Check

Use the `/mechanics-check` skill or manually validate:

```bash
cd sentinel-agent && python -m pytest tests/test_schema.py tests/test_mechanics.py -v --tb=short 2>&1 | head -50
```

Check for:
- Schema drift between YAML and Pydantic models
- Invalid enum values in game data
- Missing required fields

## Step 2: Run Full Test Suite

```bash
cd sentinel-agent && python -m pytest --tb=short -q 2>&1 | tail -40
```

If tests fail:
- Read the failing test to understand what's expected
- Check if it's a simple fix (typo, missing import, schema mismatch)
- Fix if straightforward, note if complex

## Step 3: Check for Common Issues

Look for and fix:
- **Import errors** — missing dependencies, circular imports
- **Type errors** — obvious type mismatches
- **Schema drift** — YAML files out of sync with Pydantic models
- **Broken references** — files referencing deleted/moved code

## Step 4: Commit Fixes

If any fixes were made:

```bash
git status
git diff --stat
```

Stage and commit with descriptive message:

```bash
git add <specific-files>
git commit -m "$(cat <<'EOF'
Autofix: <brief description>

Fixes:
- <issue 1>
- <issue 2>

Remaining issues (manual review needed):
- <issue that couldn't be auto-fixed>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

## Step 5: Push to Master

```bash
git pull --rebase origin master && git push origin master
```

If rebase conflicts occur:
- Attempt simple resolution (accept theirs for non-critical, ours for our fixes)
- If complex, abort and report

## Step 6: Report Results

Summarize:
- What was checked
- What was fixed (with file names)
- What passed
- What still needs manual attention

## Rules

- **Never force push** — always use regular push
- **Never skip tests** — if tests fail after fixes, don't push
- **Be conservative** — when in doubt, report rather than fix
- **Atomic commits** — one commit per logical fix if possible, or one combined "autofix" commit
- **Always pull first** — rebase on latest master before pushing

## Example Output

```
## Autofix Results

### Checked
- [x] Mechanics validation (schema, enums, regions)
- [x] Test suite (454 tests)
- [x] Import health

### Fixed & Pushed
- `data/regions.json`: Fixed invalid faction enum "steel" → "steel_syndicate"
- `src/state/schema.py`: Added missing `Optional` import

### Still Passing
- All 454 tests green

### Needs Manual Review
- None

Pushed to master: abc1234
```
