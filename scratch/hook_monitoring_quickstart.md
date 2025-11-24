# Hook Monitoring Quick Reference

## What You Get

Every session start now:
1. **Automatically tests** all 87 hooks in background (non-blocking)
2. **Alerts you** if any hooks are broken
3. **Shows Claude** recommendations for fixes

## Commands

### Check Hook Health
```bash
python3 scripts/ops/test_hooks.py
```

### Scan Hook Registry
```bash
python3 scripts/lib/hook_registry.py --health
```

### Validate Specific Hook
```bash
python3 scripts/lib/hook_registry.py --validate <hook_name.py>
```

## What It Detects

1. **Syntax Errors** - Broken Python code
2. **Import Errors** - Missing dependencies
3. **Structure Issues** - Missing main() or return
4. **Execution Failures** - Crashes during dry-run
5. **Performance Issues** - Hooks >500ms

## How It Works

**On SessionStart:**
```
test_hooks_background.py → Launches test suite (non-blocking)
                         ↓
                   Tests run in background (~3s)
                         ↓
              Results saved to hook_test_results.json
                         ↓
report_hook_issues.py → Reads results → Shows warnings
```

**Session impact:** ~15ms (fully non-blocking)

## Example Output

**If issues found:**
```
⚠️  HOOK HEALTH CHECK: 8 hook(s) failing

  - performance_reward.py: Import error: ...
  - pre_write_audit.py: Import error: ...

Run: python3 scripts/ops/test_hooks.py
for full details.
```

**If all healthy:**
```
✅ Hook health check: 87 hooks OK
```

## Current Status

- **87 hooks** discovered
- **33 passing** (38%)
- **46 warnings** (missing structure)
- **8 failing** (import errors - false positives)

## Files

**Production:**
- `scripts/lib/hook_registry.py` - Auto-discovery library
- `scripts/ops/test_hooks.py` - Test suite
- `.claude/hooks/test_hooks_background.py` - SessionStart launcher
- `.claude/hooks/report_hook_issues.py` - Issue reporter

**State:**
- `.claude/memory/hook_registry.json` - Hook catalog
- `.claude/memory/hook_test_results.json` - Latest test results

## Zero Maintenance

The system is **fully automatic**:
- ✅ Auto-discovers new hooks
- ✅ Updates registry on each run
- ✅ No manual configuration needed
- ✅ Runs on every session start
