# Hook System Performance Audit

**Date:** 2024-11-24
**Auditor:** Claude (Opus 4.5)
**Verdict:** ⚠️ MODERATE ISSUES - Optimization Recommended

---

## Executive Summary

The hook system has **performance bottlenecks** due to:
1. **Hook explosion** - 70+ hooks across all events
2. **Session state file leak** - 45 orphaned files
3. **Duplicate registrations** - Same hooks running multiple times
4. **Epistemology I/O contention** - 22 hooks reading same state file

---

## 🔴 Critical Issues

### 1. Session State File Leak
**Severity:** HIGH
**Location:** `.claude/memory/session_*.json`
**Count:** 45 orphaned session files (336KB)

**Problem:** Session state files are never cleaned up. Each session creates a new file but `session_cleanup.py` isn't removing old ones.

**Fix:** Add retention policy to `session_cleanup.py`:
```python
# Delete session files older than 7 days
find .claude/memory -name "session_*_state.json" -mtime +7 -delete
```

---

### 2. Hook Count Explosion

| Event | Hook Count | Overhead (est.) |
|-------|-----------|-----------------|
| UserPromptSubmit | **21** | ~315ms |
| PostToolUse | **21** | ~315ms |
| PreToolUse (Write) | **13** | ~195ms |
| PreToolUse (Bash) | **12** | ~180ms |

**Total overhead per turn:** ~1.7 seconds
**25-turn session overhead:** ~43 seconds

---

### 3. Duplicate Hook Registrations

These hooks run **multiple times** per tool call:

| Hook | Registrations | Wasted Executions |
|------|---------------|-------------------|
| `tier_gate.py` | 3x | 2 redundant |
| `command_prerequisite_gate.py` | 3x | 2 redundant |
| `root_pollution_gate.py` | 2x | 1 redundant |
| `scratch_flat_enforcer.py` | 2x | 1 redundant |
| `auto_commit_threshold.py` | 2x (Stop+SessionEnd) | Intentional? |

**Fix:** Consolidate matchers. Instead of:
```json
{"matcher": "(Write|Edit)", "hooks": [tier_gate]},
{"matcher": "Bash", "hooks": [tier_gate]},
{"matcher": "Task", "hooks": [tier_gate]}
```
Use:
```json
{"matcher": "(Write|Edit|Bash|Task)", "hooks": [tier_gate]}
```

---

### 4. Epistemology I/O Contention

**22 hooks** read from `epistemology.py` state, causing:
- File I/O on every hook execution
- JSON parsing overhead
- Potential race conditions

**Affected hooks:**
- `tier_gate.py`, `confidence_gate.py`, `evidence_tracker.py`
- `command_prerequisite_gate.py`, `file_operation_gate.py`
- `batching_telemetry.py`, `performance_reward.py`
- ... and 15 more

**Fix:** Implement in-memory state caching with dirty flag:
```python
# In epistemology.py
_state_cache = None
_cache_mtime = 0

def get_session_state():
    global _state_cache, _cache_mtime
    file_mtime = os.path.getmtime(STATE_FILE)
    if _state_cache and file_mtime == _cache_mtime:
        return _state_cache  # Cache hit
    # Cache miss - reload
    _state_cache = json.load(open(STATE_FILE))
    _cache_mtime = file_mtime
    return _state_cache
```

---

## 🟡 Moderate Issues

### 5. Subprocess-Spawning Hooks

12 hooks spawn subprocesses (expensive):

| Hook | Subprocess Calls |
|------|------------------|
| `auto_commit_threshold.py` | 7 |
| `session_digest.py` | 4 |
| `auto_void.py` | 4 |
| `auto_playwright_setup.py` | 4 |
| `test_hooks_background.py` | 4 |
| `synapse_fire.py` | 3 |

**Recommendation:** Review if subprocess calls are necessary. Consider:
- Using Python stdlib instead of shell commands
- Lazy evaluation (only spawn when needed)
- Caching results

---

### 6. Orphan Hook Files

**91 hook files** exist but only **~50 are registered**.

Orphan files (not in settings.json):
- `*_v1_backup.py` files (3)
- Various unused detectors
- Test files in production directory

**Fix:** Move unused hooks to `.claude/hooks/archive/` or delete.

---

## 🟢 What's Working Well

1. **Individual hook speed** - Each hook runs in ~15-25ms
2. **Matcher-based filtering** - Hooks only run for relevant tools
3. **Exit code handling** - Hooks fail gracefully
4. **JSON output format** - Consistent structure

---

## Recommendations (Priority Order)

### P0 - Do Now
1. **Fix session state leak** - Add cleanup to `session_cleanup.py`
2. **Consolidate duplicate registrations** - Merge matchers for tier_gate, command_prerequisite_gate

### P1 - This Week
3. **Implement epistemology caching** - Reduce file I/O
4. **Archive orphan hooks** - Clean up `.claude/hooks/`

### P2 - Later
5. **Review subprocess hooks** - Optimize or lazy-evaluate
6. **Consider hook batching** - Run multiple hooks in single Python process

---

## Estimated Impact

| Fix | Time Saved per Turn |
|-----|---------------------|
| Consolidate duplicates | ~90ms |
| Epistemology caching | ~50ms |
| Reduce UserPromptSubmit hooks | ~150ms |

**Total potential savings:** ~300ms per turn (~7.5s per 25-turn session)

---

## Appendix: Full Hook Count

```
PreToolUse: 33 total registrations (with overlaps)
  - mcp__.*: 1
  - (Read|Write|Edit): 1
  - (Write|Edit): 7
  - Write: 6
  - Bash: 12
  - Task: 3
  - (Bash|Write|Edit): 1
  - (Read|Grep|Glob|WebFetch|WebSearch): 1
  - (Read|Grep|Glob|Edit): 1

UserPromptSubmit: 21 hooks (all run on every prompt)
PostToolUse: 21 hooks (all run after every tool)
SessionStart: 6 hooks
Stop: 7 hooks
SessionEnd: 4 hooks
```
