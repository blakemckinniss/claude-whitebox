# Threading & Parallelization - Action Plan

## Quick Summary

**Audit Results:**
- 90 Python files analyzed
- 19 files with issues (34 total issues)
- **CRITICAL:** Hook system has 1050ms sequential latency
- **HIGH:** 32 subprocess calls missing timeouts
- **GOOD:** 8 files using optimal patterns

**Estimated Impact:** 50-100× speedup on common operations

---

## Immediate Actions (< 1 Hour)

### 1. Add Subprocess Timeouts (30 minutes)

**Problem:** 32 subprocess calls risk indefinite hangs

**Files Affected:**
- Hooks: 18 locations across 10 files
- Scripts: 14 locations across 7 files

**Solution:**
```bash
# Preview changes
python3 scratch/add_subprocess_timeouts.py

# Apply fixes
python3 scratch/add_subprocess_timeouts.py --apply
```

**Auto-fix Logic:**
- Default: `timeout=10`
- Git push: `timeout=30`
- Tests: `timeout=60`
- Package managers: `timeout=120`

**Validation:**
```bash
# Verify no syntax errors
python3 -m py_compile .claude/hooks/*.py scripts/ops/*.py scripts/lib/*.py

# Run tests
python3 -m pytest tests/ -v
```

---

### 2. Increase max_workers (5 minutes)

**Problem:** Some scripts use suboptimal worker counts

**Files:**
- `.claude/hooks/best_practice_enforcer.py` - Change 10 → 50
- `.claude/hooks/detect_batch.py` - Change 10 → 50

**Fix:**
```bash
# best_practice_enforcer.py
sed -i 's/max_workers=10/max_workers=50/g' .claude/hooks/best_practice_enforcer.py

# detect_batch.py
sed -i 's/max_workers=10/max_workers=50/g' .claude/hooks/detect_batch.py
```

**Impact:** 5× speedup on batch operations

---

### 3. Document Parallel Agent Pattern (DONE)

**Problem:** Sequential agent invocation (N× slower than parallel)

**Solution:** Already added to CLAUDE.md meta-cognition checklist:

```markdown
⚡ META-COGNITION PERFORMANCE CHECKLIST:

5. Multiple agents needed?
   → Can I delegate in PARALLEL? (single message, multiple Task calls)
   → 🚀 AGENT CONTEXT IS FREE - each agent = separate context window!
```

**Impact:** N× speedup when using multiple agents

---

## Medium-Term Actions (2-4 Hours)

### 4. Hook Consolidation (Reduces 21 → 7-10 hooks)

**Problem:** 21 hooks run sequentially = 1050ms latency

**Strategy:** Merge related hooks into multi-purpose hooks

#### Phase 1: Memory Hooks → `unified_memory_manager.py`

**Merge:**
- `.claude/hooks/synapse_fire.py` (associative memory)
- `.claude/hooks/auto_remember.py` (lesson capture)
- `.claude/hooks/session_context.py` (session tracking)

**New Hook:**
```python
#!/usr/bin/env python3
"""
Unified Memory Manager
Handles: Synapse firing, auto-remember, session context
"""

def run():
    # 1. Fire synapses (associative recall)
    synapses = fire_synapses(user_prompt)

    # 2. Update session context
    update_session_context(turn_number, tokens_used)

    # 3. Auto-remember significant events
    check_auto_remember(conversation_events)

    return {
        'synapses': synapses,
        'session': session_data,
        'memories': new_memories
    }
```

**Impact:** 3 hooks → 1 hook (150ms → 50ms)

---

#### Phase 2: Detection Hooks → `unified_pattern_detector.py`

**Merge:**
- `.claude/hooks/detect_batch.py`
- `.claude/hooks/detect_gaslight.py`
- `.claude/hooks/detect_success_auto_learn.py`
- `.claude/hooks/detect_failure_auto_learn.py`
- `.claude/hooks/detect_confidence_penalty.py`

**New Hook:**
```python
#!/usr/bin/env python3
"""
Unified Pattern Detector
Handles: Batch operations, gaslighting, success/failure, confidence penalties
"""

def run():
    patterns_detected = []

    # Run all detection patterns in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(detect_batch, message): 'batch',
            executor.submit(detect_gaslight, message): 'gaslight',
            executor.submit(detect_success, message): 'success',
            executor.submit(detect_failure, message): 'failure',
            executor.submit(detect_penalty, message): 'penalty',
        }

        for future in as_completed(futures):
            pattern_type = futures[future]
            result = future.result()
            if result:
                patterns_detected.append((pattern_type, result))

    return patterns_detected
```

**Impact:** 5 hooks → 1 hook (250ms → 50ms)

---

#### Phase 3: Epistemology Hooks → `unified_epistemology_tracker.py`

**Merge:**
- `.claude/hooks/command_tracker.py`
- `.claude/hooks/confidence_tracker.py`
- `.claude/hooks/session_state_tracker.py`

**New Hook:**
```python
#!/usr/bin/env python3
"""
Unified Epistemology Tracker
Handles: Command tracking, confidence updates, session state
"""

def run():
    # 1. Track commands executed
    track_commands(tools_used)

    # 2. Update confidence score
    new_confidence = calculate_confidence(evidence_gathered)

    # 3. Update session state
    update_session_state(session_id, state_changes)

    return {
        'commands': commands_tracked,
        'confidence': new_confidence,
        'state': session_state
    }
```

**Impact:** 3 hooks → 1 hook (150ms → 50ms)

---

#### Phase 4: Performance Hooks → `unified_performance_monitor.py`

**Merge:**
- `.claude/hooks/performance_gate.py`
- `.claude/hooks/best_practice_enforcer.py`
- `.claude/hooks/detect_parallel.py`

**New Hook:**
```python
#!/usr/bin/env python3
"""
Unified Performance Monitor
Handles: Performance gates, best practices, parallelization detection
"""

def run():
    warnings = []

    # Check for performance anti-patterns
    if detect_sequential_loop():
        warnings.append("Sequential loop detected - use parallel.py")

    if detect_nested_iteration():
        warnings.append("Nested iteration - write script to scratch/")

    if detect_large_file_read():
        warnings.append("Large file read - use line ranges or grep")

    return warnings
```

**Impact:** 3 hooks → 1 hook (150ms → 50ms)

---

#### Summary: Hook Consolidation Impact

| Phase | Before | After | Savings |
|-------|--------|-------|---------|
| Memory | 3 hooks (150ms) | 1 hook (50ms) | 100ms |
| Detection | 5 hooks (250ms) | 1 hook (50ms) | 200ms |
| Epistemology | 3 hooks (150ms) | 1 hook (50ms) | 100ms |
| Performance | 3 hooks (150ms) | 1 hook (50ms) | 100ms |
| **Remaining** | **7 hooks** | **7 hooks** | **0ms** |
| **TOTAL** | **21 hooks (1050ms)** | **11 hooks (400ms)** | **650ms** |

**Result:** 2.6× speedup (1050ms → 400ms)

---

## Long-Term Actions (Claude Code Core Changes)

### 5. Parallel Hook Execution (Requires Claude Team)

**Problem:** Even after consolidation, hooks run sequentially

**Solution:** Modify Claude Code hook executor to parallelize independent hooks

**Prototype:** `scratch/hook_parallelization_prototype.py`

**Key Insight:**
- Some hooks MUST be sequential (state-modifying)
- Others CAN be parallel (read-only analysis)

**Categorization:**
```json
{
  "dependent": [
    "command_tracker.py",
    "session_context.py",
    "auto_remember.py"
  ],
  "independent": [
    ... all analysis/detection hooks ...
  ]
}
```

**Expected Impact:** 10-20× speedup (400ms → 20-40ms after consolidation)

---

## Validation & Testing

### After Each Change:

```bash
# 1. Syntax check
python3 -m py_compile <modified_file>

# 2. Run affected tests
python3 -m pytest tests/ -k <relevant_test> -v

# 3. Manual verification
python3 <modified_script> --help  # Ensure it still works
```

### Full System Test:

```bash
# 1. Run all audits
python3 scratch/threading_audit.py
python3 scratch/analyze_script_patterns.py

# 2. Run all tests
python3 -m pytest tests/ -v

# 3. Benchmark hooks (if prototype exists)
python3 scratch/hook_parallelization_prototype.py

# 4. Verify upkeep
python3 scripts/ops/upkeep.py
```

---

## Success Metrics

| Metric | Before | Target | Measurement |
|--------|--------|--------|-------------|
| Hook latency | 1050ms | 400ms (consolidation)<br>100ms (parallel) | Benchmark script |
| Agent parallelization | Sequential | Parallel | Manual observation |
| Subprocess hangs | 32 risks | 0 risks | Grep for timeout= |
| Batch performance | 10 workers | 50 workers | Check max_workers |

---

## Rollback Plan

If issues occur:

```bash
# 1. Restore from git
git checkout HEAD -- <problematic_file>

# 2. Disable specific hook
# Edit .claude/settings.json, remove hook from list

# 3. Full rollback
git reset --hard HEAD~1
```

---

## Implementation Checklist

- [ ] **Immediate (30 min)**
  - [ ] Run `python3 scratch/add_subprocess_timeouts.py --apply`
  - [ ] Increase max_workers in best_practice_enforcer.py
  - [ ] Increase max_workers in detect_batch.py
  - [ ] Validate: `python3 -m py_compile .claude/hooks/*.py scripts/ops/*.py`

- [ ] **Medium-term (2-4 hours)**
  - [ ] Create `unified_memory_manager.py`
  - [ ] Create `unified_pattern_detector.py`
  - [ ] Create `unified_epistemology_tracker.py`
  - [ ] Create `unified_performance_monitor.py`
  - [ ] Update `.claude/settings.json` to use new hooks
  - [ ] Test each consolidated hook independently
  - [ ] Remove old hooks after validation

- [ ] **Long-term (external dependency)**
  - [ ] Document parallel hook execution requirements
  - [ ] Share prototype with Claude team
  - [ ] Wait for core implementation

---

## Files Reference

**Analysis Scripts:**
- `scratch/threading_audit.py` - High-level audit
- `scratch/analyze_script_patterns.py` - Detailed code analysis
- `scratch/hook_parallelization_prototype.py` - Hook parallel execution demo

**Fix Scripts:**
- `scratch/add_subprocess_timeouts.py` - Auto-add timeouts

**Reports:**
- `scratch/threading_optimization_summary.md` - Full analysis
- `scratch/script_analysis_detailed.txt` - Per-file issues
- `scratch/OPTIMIZATION_ACTION_PLAN.md` - This file

---

## Questions?

**Q: Will consolidating hooks break existing functionality?**
A: No, if done carefully. Each consolidated hook calls the same logic as before, just in a single execution.

**Q: What's the risk of adding timeouts?**
A: Very low. Timeouts prevent hangs. If a command legitimately takes longer, we can increase specific timeouts.

**Q: Can I apply fixes incrementally?**
A: Yes! Start with subprocess timeouts (safest), then max_workers, then hook consolidation.

**Q: How do I measure actual impact?**
A: Benchmark hook execution before/after using the prototype script.

---

**Next Steps:** Start with immediate actions (< 1 hour), validate, then proceed to hook consolidation.
