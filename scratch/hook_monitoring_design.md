# Hook Monitoring System Design

## Problem Statement
Hook system has grown to 24+ hooks across multiple event types. Need automated health monitoring to detect:
- Broken hooks (import errors, syntax errors)
- Poorly performing hooks (timeouts, exceptions)
- Hook conflicts (multiple hooks modifying same state)

## Requirements
1. **Registry**: Central catalog of all hooks with metadata
2. **Test Suite**: Automated tests that run on SessionStart (background, non-blocking)
3. **Issue Reporting**: Surface problems to both Claude and user
4. **Zero Maintenance**: Self-updating registry, auto-discovery

## Architecture

### 1. Hook Registry (`scripts/lib/hook_registry.py`)
Auto-discovers hooks by scanning `.claude/hooks/` directory.

**Registry Schema:**
```json
{
  "hooks": {
    "auto_documentarian.py": {
      "path": ".claude/hooks/auto_documentarian.py",
      "event_type": "SessionEnd",
      "last_scan": "2025-11-23T21:00:00",
      "health": {
        "syntax_valid": true,
        "imports_valid": true,
        "has_main": true,
        "estimated_duration_ms": 150
      }
    }
  },
  "event_types": {
    "SessionStart": ["startup_whitebox.py", "epistemological_init.py"],
    "UserPromptSubmit": ["synapses.py", "scratch_enforcer.py", ...],
    "PostToolUse": ["org_drift_telemetry.py", "batching_analyzer.py", ...],
    "PreToolUse": ["org_drift_gate.py", "tier_gate.py", ...],
    "SessionEnd": ["auto_documentarian.py", "upkeep_auto.py"]
  }
}
```

**Registry Functions:**
- `scan_hooks()`: Auto-discover all hook files
- `validate_hook(path)`: Check syntax, imports, structure
- `categorize_by_event(hooks)`: Group by event type
- `save_registry()`: Persist to `.claude/memory/hook_registry.json`

### 2. Hook Test Suite (`scripts/ops/test_hooks.py`)
Runs comprehensive tests on all hooks.

**Test Categories:**
1. **Syntax Tests**: `python3 -m py_compile <hook>`
2. **Import Tests**: `python3 -c "import sys; sys.path.insert(0, '.claude/hooks'); import <module>"`
3. **Structure Tests**: Has `main()`, returns proper hookSpecificOutput
4. **Dry-Run Tests**: Execute with test event, check for crashes
5. **Performance Tests**: Measure execution time, flag if >500ms

**Output Format:**
```
🧪 HOOK TEST RESULTS (24 hooks scanned)
✅ 22 passing
⚠️  1 warning (slow)
❌ 1 failing

FAILURES:
  ❌ org_drift_gate.py - ImportError: No module named 'org_drift'

WARNINGS:
  ⚠️  auto_documentarian.py - Slow execution (850ms)

RECOMMENDATIONS:
  - Fix import path in org_drift_gate.py
  - Consider caching in auto_documentarian.py
```

### 3. SessionStart Integration
Add to `.claude/hooks/test_hooks_background.py`:

```python
#!/usr/bin/env python3
"""
SessionStart hook: Run hook tests in background, non-blocking.
Surfaces critical issues to user via system reminder.
"""
import subprocess
import sys

def main(event):
    # Launch test suite in background (non-blocking)
    subprocess.Popen(
        ["python3", "scripts/ops/test_hooks.py", "--quiet"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True  # Detach from parent
    )

    # Return immediately (non-blocking)
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "🧪 Hook test suite running in background..."
        }
    }
```

**Issue Surfacing:**
- Write results to `.claude/memory/hook_test_results.json`
- If failures detected, another SessionStart hook reads this and adds to system reminders
- User sees: "⚠️ 1 hook failing: org_drift_gate.py (ImportError)"

### 4. Continuous Monitoring
**File Watcher** (optional future enhancement):
- Watch `.claude/hooks/` for changes
- Auto-run tests when hook modified
- Update registry in real-time

## Implementation Plan
1. ✅ Design architecture (this doc)
2. Implement `scripts/lib/hook_registry.py` (auto-discovery, validation)
3. Implement `scripts/ops/test_hooks.py` (test suite)
4. Add `.claude/hooks/test_hooks_background.py` (SessionStart integration)
5. Add `.claude/hooks/report_hook_issues.py` (surfaces failures to user)
6. Test with intentionally broken hook
7. Document in CLAUDE.md

## Success Criteria
- [ ] Auto-discovery finds all 24+ hooks
- [ ] Syntax/import tests catch broken hooks
- [ ] SessionStart execution is non-blocking (<50ms)
- [ ] User sees warnings for failing hooks
- [ ] Claude sees recommendations in system reminders
- [ ] Zero manual maintenance required
