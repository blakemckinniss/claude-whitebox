# Unregistered Hooks Analysis

**Analysis Date:** 2025-11-23

---

## Summary

**5 unregistered hooks identified:**

| Hook | Status | Recommendation |
|------|--------|----------------|
| `absurdity_detector.py` | ✅ **REGISTER** | Valuable advisory hook |
| `parallel_agent_reminder.py` | ❌ **DELETE** | Redundant with meta_cognition_performance.py |
| `hook_timing_wrapper.py` | ⚠️ **ARCHIVE** | Replaced by hook_performance_monitor.py |
| `parallel_hook_executor.py` | ❌ **DELETE** | Experimental, not integrated |
| `performance_gate_temp.py` | ❌ **DELETE** | Old backup, replaced by v2 |

---

## Detailed Analysis

### 1. absurdity_detector.py

**Purpose:** Detects absurd/contradictory requests (tech mismatches, over-engineering, anti-patterns)

**Status:** ✅ **SHOULD BE REGISTERED**

**Why:**
- Well-implemented advisory hook
- Provides valuable pushback against sycophancy
- Non-blocking (exit 0) - aligns with philosophy
- Complements Judge/Critic protocols
- Detects patterns like:
  - Technology mismatches (Rust in JS project)
  - Over-engineering (microservices for todo app)
  - Contradictory goals (fast + heavy ORM)
  - Security anti-patterns (plaintext passwords)

**Recommendation:**
Register to `UserPromptSubmit` event, runs before prompt processing.

**Integration:**
```json
{
  "matcher": ".*",
  "hooks": [{
    "type": "command",
    "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/absurdity_detector.py"
  }]
}
```

**Position:** Early in UserPromptSubmit chain (after synapse_fire, before advice)

---

### 2. parallel_agent_reminder.py

**Purpose:** Reminds Claude to use parallel Task invocations

**Status:** ❌ **DELETE - REDUNDANT**

**Why:**
- Only 28 lines, trivial functionality
- Already covered by `meta_cognition_performance.py` hook
- `meta_cognition_performance.py` provides comprehensive parallel execution checklist
- Adding both creates duplicate reminders

**Recommendation:**
Delete this file. Functionality already exists and is more comprehensive.

---

### 3. hook_timing_wrapper.py

**Purpose:** Wrapper to measure individual hook execution time

**Status:** ⚠️ **ARCHIVE OR DELETE**

**Why:**
- Replaced by `hook_performance_monitor.py` (PostToolUse hook)
- Current implementation is incomplete (requires wrapper architecture change)
- Would need settings.json rewrite to wrap every hook
- `hook_performance_monitor.py` already logs hook timing to same file

**Recommendation:**
Move to `scratch/archive/` or delete. Not currently integrated and redundant.

---

### 4. parallel_hook_executor.py

**Purpose:** Experimental parallel hook execution system

**Status:** ❌ **DELETE - EXPERIMENTAL/INCOMPLETE**

**Why:**
- 213 lines but not integrated into settings.json
- Requires `scratch/hook_dependency_graph.json` which doesn't exist
- Would require major settings.json refactor
- Hook parallelism not currently needed (hooks are fast <10ms)
- Adds complexity without proven ROI

**Recommendation:**
Delete. If hook latency becomes issue later, can revisit from git history.

**Note:** Current 29 PreToolUse hooks run sequentially in ~50-200ms total, acceptable.

---

### 5. performance_gate_temp.py

**Purpose:** Old backup/temporary version of performance_gate.py

**Status:** ❌ **DELETE - OBSOLETE BACKUP**

**Why:**
- Only 21 lines, stub implementation
- Replaced by `performance_gate.py` (v2 with auto-tuning)
- File dated Nov 22, current version is Nov 23
- Backup files should be in git history, not active hooks directory

**Recommendation:**
Delete. Already have `performance_gate_v1_backup.py` for version history.

---

## Cleanup Actions

### Immediate Actions (DELETE)

```bash
# Delete redundant/obsolete hooks
rm .claude/hooks/parallel_agent_reminder.py
rm .claude/hooks/parallel_hook_executor.py
rm .claude/hooks/performance_gate_temp.py
```

**Impact:** None - these are not registered in settings.json

### Optional Actions (ARCHIVE)

```bash
# Archive hook timing wrapper for potential future use
mkdir -p scratch/archive/hooks
mv .claude/hooks/hook_timing_wrapper.py scratch/archive/hooks/
```

### Registration Action (INTEGRATE)

Add `absurdity_detector.py` to settings.json:

**Location:** `hooks.UserPromptSubmit` array, position after `synapse_fire.py`

**Rationale:**
- Should run early (before advice/suggestions)
- Should fire on ALL prompts (no matcher needed)
- Provides "sanity check" layer before other hooks process request

---

## Updated Hook Count After Cleanup

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total hooks | 78 | 75 | -3 deleted |
| Registered hooks | 70 | 71 | +1 (absurdity) |
| Unregistered hooks | 5 | 1 | -4 |
| Remaining unregistered | - | hook_timing_wrapper.py | Archival candidate |

---

## Rationale: Why Register absurdity_detector.py?

**Fills a Gap:**
Current system has:
- Judge (ROI/value assessment)
- Critic (assumption attack)
- Skeptic (technical risk)
- Intervention (bikeshedding keywords)

Missing:
- **Pattern-based sanity check** for obvious contradictions

**Examples absurdity_detector catches:**
1. User: "Add blockchain authentication to my todo app"
   - Absurdity: 🚨 ABSURD TECH CHOICE: Blockchain for auth (massive overkill)
   - Judge: Would take longer to evaluate, might miss if framed well

2. User: "Keep it simple but add Kafka, Redis cluster, and microservices"
   - Absurdity: ⚠️ CONTRADICTORY GOALS: Keep it simple + distributed systems
   - Intervention: Doesn't have this pattern

3. User: "Store passwords in plaintext for simplicity"
   - Absurdity: 🚨 SECURITY VIOLATION: Storing credentials in plaintext
   - Hard block appropriate here

**Low Cost, High Value:**
- Runs in <1ms (regex matching only)
- Advisory only (exit 0) - user can override
- Catches obvious mistakes before expensive Oracle/Judge calls
- Complements existing protocols

---

## Final Recommendation Summary

✅ **Register:** `absurdity_detector.py` → UserPromptSubmit (early position)

❌ **Delete (3 files):**
- `parallel_agent_reminder.py` (redundant)
- `parallel_hook_executor.py` (experimental/unused)
- `performance_gate_temp.py` (obsolete backup)

⚠️ **Archive (optional):**
- `hook_timing_wrapper.py` → scratch/archive/hooks/

**Net Result:**
- Cleaner hooks directory
- One valuable new advisory hook
- No functionality lost (all deleted hooks are redundant or obsolete)
