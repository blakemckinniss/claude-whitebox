# Hook System Performance Audit Report

**Date:** 2025-11-24
**Total Hooks:** 90 files, 15,311 lines of code
**Registered Hooks:** 97 registrations across 6 lifecycle events

---

## Executive Summary

The hook system has **critical performance bottlenecks** causing **~5.2 seconds of latency per interaction**. Primary issues:

1. **Hook explosion** - 97 hooks registered, many redundant
2. **No parallelization** - Hooks execute sequentially
3. **Repeated state loading** - 35 hooks independently read session state
4. **Expensive subprocess calls** - Hooks spawn `git`, `python3` subprocesses
5. **Duplicate functionality** - Multiple hooks checking same things

---

## Bottleneck Analysis

### Per-Lifecycle Overhead

| Lifecycle Event | Hook Count | Est. Time | Impact |
|----------------|-----------|-----------|--------|
| PreToolUse:Write | 15 | ~1387ms | Every file write |
| PreToolUse:Bash | 13 | ~1198ms | Every command |
| UserPromptSubmit | 21 | ~1770ms | Every user message |
| PostToolUse | 21 | ~2076ms | Every tool completion |
| Stop | 7 | ~1500ms | Every response end |
| SessionEnd | 4 | ~1100ms | Session termination |

### Slowest Individual Hooks

| Hook | Time (ms) | Root Cause |
|------|-----------|------------|
| auto_commit_on_end.py | 1007 | Runs `upkeep.py` + multiple git commands |
| auto_commit_threshold.py | 525 | Also runs `upkeep.py` + git commands |
| tier_gate_v1_backup.py | 130 | Should not be registered (backup file!) |
| command_prerequisite_gate_v1_backup.py | 128 | Should not be registered (backup!) |
| file_operation_gate.py | 128 | JSON parsing + state loading |
| org_drift_gate.py | 127 | Filesystem scanning |
| tier_gate.py | 125 | State loading + JSON parsing |

---

## Critical Issues

### 1. Backup Files Registered as Active Hooks
```
tier_gate_v1_backup.py - 130ms WASTED per invocation
command_prerequisite_gate_v1_backup.py - 128ms WASTED per invocation
native_batching_enforcer_v1_backup.py - registered but unused
```
**Fix:** Remove `*_v1_backup.py` from settings.json

### 2. Duplicate auto_commit Hooks
Both `auto_commit_threshold.py` (Stop) and `auto_commit_on_end.py` (SessionEnd) do the same thing. They both run `upkeep.py` subprocess.

**Impact:** ~1.5 seconds wasted on duplicate commit logic

### 3. 35 Hooks Load Session State Independently
Each hook does:
```python
state_file = Path(".claude/memory/session_state.json")
with open(state_file) as f:
    state = json.load(f)
```
**Impact:** Same JSON file parsed 35 times per session

### 4. Hook Chain Redundancy

**Write Operation Chain (15 hooks):**
```
file_operation_gate.py        → path validation
hook_documentation_enforcer.py → path validation (again)
assumption_firewall.py        → confidence check
org_drift_gate.py            → path validation (again)
constitutional_guard.py       → path validation (again)
root_pollution_gate.py        → path validation (again)
scratch_flat_enforcer.py      → scratch path check
block_main_write.py           → path validation (again)
command_prerequisite_gate.py  → confidence + prerequisites
tier_gate.py                  → tier check
pre_write_audit.py            → audit check
ban_stubs.py                  → content check
enforce_reasoning_rigor.py    → reasoning check
confidence_gate.py            → confidence check (again)
trigger_skeptic.py            → skeptic trigger
```

**6 hooks do path validation, 3 check confidence, 2 check tier** - all separately!

---

## Consolidation Recommendations

### High Priority (Immediate ~60% improvement)

#### 1. Remove Backup Files from Registration
```json
// REMOVE from settings.json - these are backups, not active hooks:
tier_gate_v1_backup.py
command_prerequisite_gate_v1_backup.py
native_batching_enforcer_v1_backup.py
performance_gate_v1_backup.py
```
**Savings:** ~400ms per turn

#### 2. Merge Auto-Commit Hooks
Consolidate `auto_commit_on_end.py` + `auto_commit_threshold.py` into ONE hook.
**Savings:** ~500-1000ms at session end

#### 3. Create Unified State Loader
```python
# lib/state_loader.py - singleton pattern
_cached_state = None

def get_session_state():
    global _cached_state
    if _cached_state is None:
        _cached_state = load_from_disk()
    return _cached_state
```
**Savings:** ~300ms (35 loads → 1 load per event)

### Medium Priority (Additional ~25% improvement)

#### 4. Merge Path Validation Hooks
Combine into ONE `unified_path_gate.py`:
- file_operation_gate.py
- org_drift_gate.py
- root_pollution_gate.py
- scratch_flat_enforcer.py
- block_main_write.py
- constitutional_guard.py

**Savings:** ~600ms per Write operation

#### 5. Merge Confidence/Tier Hooks
Combine into ONE `unified_confidence_gate.py`:
- confidence_gate.py
- tier_gate.py
- confidence_init.py
- detect_low_confidence.py

**Savings:** ~300ms per turn

#### 6. Consolidate Telemetry
Merge 6 telemetry hooks into ONE `unified_telemetry.py`:
- batching_telemetry.py
- background_telemetry.py
- performance_telemetry_collector.py
- command_tracker.py
- evidence_tracker.py
- token_tracker.py

**Savings:** ~400ms per PostToolUse

### Low Priority (Architectural)

#### 7. Lazy Loading for Expensive Hooks
Make `auto_commit_*` hooks only trigger on actual commit intent, not every Stop event.

#### 8. Hook Parallelization
Claude Code runs hooks sequentially. If hooks could run in parallel within a lifecycle event, we'd see massive gains.

---

## Projected Impact

| Scenario | Current | Optimized | Improvement |
|----------|---------|-----------|-------------|
| Per-Turn Overhead | 5233ms | 2100ms | 60% |
| Write Operation | 1387ms | 400ms | 71% |
| Session End | 2600ms | 600ms | 77% |

---

## Implementation Roadmap

### Phase 1: Quick Wins (10 min work, 40% gain)
1. Remove 4 backup file registrations from settings.json
2. Remove duplicate auto_commit hook
3. Add caching to state loading

### Phase 2: Consolidation (2-4 hours, +20% gain)
1. Create unified_path_gate.py
2. Create unified_confidence_gate.py
3. Create unified_telemetry.py

### Phase 3: Architecture (future)
1. Investigate hook parallelization
2. Implement lazy loading patterns
3. Add hook performance budgets

---

## Appendix: Error Hooks (14 hooks failing silently)

These hooks have non-zero exit codes during dry-run:
- detect_tool_failure.py
- post_tool_command_suggester.py
- performance_reward.py
- (11 others)

Should investigate whether these are expected failures (missing stdin) or actual bugs.
