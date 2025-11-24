# Circuit Breaker & Memory Protection - Deployment Checklist

**System Status:** ✅ Ready for Production
**Tests:** 8/8 Passing
**Critical Gaps:** 0 (All Fixed)

---

## Pre-Deployment Verification

### 1. Test Suite ✅
```bash
python3 scratch/test_circuit_breaker.py
```
**Expected:** All 8/8 tests passing
**Actual:** ✅ PASSED

### 2. Gap Analysis ✅
```bash
python3 scripts/ops/void.py scratch/circuit_breaker.py
python3 scripts/ops/void.py scratch/memory_cleanup.py
```
**Expected:** No CRITICAL gaps
**Actual:** ✅ 0 critical gaps (10 optional improvements documented)

### 3. File Inventory ✅
**Libraries** (scratch/ → scripts/lib/):
- [x] circuit_breaker.py (500 lines, file locking, error handling)
- [x] memory_cleanup.py (450 lines, archive cleanup, env var support)

**Hooks** (scratch/ → .claude/hooks/):
- [x] circuit_breaker_monitor.py (PostToolUse - tracks failures/successes)
- [x] circuit_breaker_gate.py (PreToolUse - blocks when circuit OPEN)
- [x] memory_janitor.py (SessionStart - auto-cleanup)

**Tools** (scratch/ → scripts/ops/):
- [x] circuit_status.py (status command)
- [x] reset_circuit.py (emergency reset)

**Documentation** (scratch/):
- [x] circuit_breaker_design.md (architecture)
- [x] CIRCUIT_BREAKER_SUMMARY.md (integration guide)
- [x] GAP_ANALYSIS_REPORT.md (void findings + recommendations)
- [x] test_circuit_breaker.py (8 tests, all passing)

---

## Deployment Steps

### Step 1: Move Libraries to Production
```bash
mv scratch/circuit_breaker.py scripts/lib/
mv scratch/memory_cleanup.py scripts/lib/
```

### Step 2: Move Hooks to Production
```bash
mv scratch/circuit_breaker_monitor.py .claude/hooks/
mv scratch/circuit_breaker_gate.py .claude/hooks/
mv scratch/memory_janitor.py .claude/hooks/
chmod +x .claude/hooks/circuit_breaker_*.py
chmod +x .claude/hooks/memory_janitor.py
```

### Step 3: Register Hooks in Settings
Edit `.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      ".claude/hooks/performance_telemetry_collector.py",
      ".claude/hooks/circuit_breaker_monitor.py"
    ],
    "PreToolUse": [
      ".claude/hooks/circuit_breaker_gate.py",
      ".claude/hooks/native_batching_enforcer.py"
    ],
    "SessionStart": [
      ".claude/hooks/confidence_init.py",
      ".claude/hooks/memory_janitor.py"
    ]
  }
}
```

### Step 4: Move Tools to Production
```bash
mv scratch/circuit_status.py scripts/ops/
mv scratch/reset_circuit.py scripts/ops/
chmod +x scripts/ops/circuit_status.py
chmod +x scripts/ops/reset_circuit.py
```

### Step 5: Update Tool Index
```bash
python3 scripts/ops/upkeep.py
```

### Step 6: Initialize Configuration
```bash
# Config auto-creates on first hook run, or manually:
python3 -c "
import json
from pathlib import Path

config = {
    'circuit_breakers': {
        'tool_failure': {
            'enabled': True,
            'threshold': 3,
            'window_turns': 5,
            'cooldown_base_seconds': 10
        },
        'sequential_tools': {
            'enabled': True,
            'threshold': 10,
            'window_turns': 1,
            'cooldown_base_seconds': 5
        }
    },
    'memory_limits': {
        'telemetry_max_lines': 1000,
        'telemetry_max_kb': 50,
        'telemetry_max_age_days': 7,
        'session_max_active': 10,
        'evidence_ledger_max': 100,
        'tool_history_max': 50,
        'archive_keep_count': 20
    }
}

config_file = Path('.claude/memory/circuit_breaker_config.json')
config_file.parent.mkdir(parents=True, exist_ok=True)
with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print('✅ Config initialized')
"
```

### Step 7: Test Integration
```bash
# Start new session, check hooks execute
# Look for memory janitor message (if cleanup needed)

# Check circuit status
python3 scripts/ops/circuit_status.py

# Expected output:
# 🔒 CIRCUIT BREAKER STATUS
# Active Breakers: None (all systems operational)
```

---

## Post-Deployment Verification

### Day 1 Checks
```bash
# 1. Check config created
ls -lh .claude/memory/circuit_breaker_config.json

# 2. Check state initialized
ls -lh .claude/memory/circuit_breaker_state.json

# 3. Check incident log created (may not exist yet - only on trips)
ls -lh .claude/memory/circuit_breaker_incidents.jsonl 2>/dev/null || echo "No incidents yet (good)"

# 4. Check status
python3 scripts/ops/circuit_status.py
```

### Week 1 Monitoring
```bash
# Check memory growth
du -sh .claude/memory/

# Check state file size
ls -lh .claude/memory/circuit_breaker_state.json

# Check incident count
wc -l .claude/memory/circuit_breaker_incidents.jsonl 2>/dev/null || echo 0

# Check active circuits
python3 scripts/ops/circuit_status.py --json | jq '.circuits | length'
```

**Expected Metrics:**
- Memory total: <1MB
- State file: <20KB
- Incident count: 0-10
- Active circuits: 2-5

---

## Rollback Plan

If issues detected, rollback is simple:

```bash
# 1. Remove hooks from settings.json
#    (delete circuit_breaker_* entries)

# 2. Restart session
#    (hooks won't load)

# 3. Optionally remove files
rm .claude/hooks/circuit_breaker_*.py
rm .claude/hooks/memory_janitor.py
rm scripts/lib/circuit_breaker.py
rm scripts/lib/memory_cleanup.py
rm scripts/ops/circuit_status.py
rm scripts/ops/reset_circuit.py

# 4. Remove state files
rm .claude/memory/circuit_breaker_*.json*
rm -rf .claude/memory/archives/
```

**System returns to pre-deployment state.**

---

## Troubleshooting

### Circuit Breaker Stuck OPEN
```bash
# Check status
python3 scripts/ops/circuit_status.py

# If legitimately stuck, reset
python3 scripts/ops/reset_circuit.py --circuit tool_failure

# Or reset all
python3 scripts/ops/reset_circuit.py --all
```

### Memory Cleanup Not Running
```bash
# Check SessionStart hook registered
grep -A 5 "SessionStart" .claude/settings.json

# Manually trigger cleanup
python3 -c "
from scripts.lib.memory_cleanup import auto_cleanup_on_startup
print(auto_cleanup_on_startup())
"
```

### Hooks Crashing
```bash
# Check stderr logs
# Hooks log to stderr with prefix [circuit_breaker] or [memory_cleanup]

# Test hook directly
echo '{"tool_name":"Bash","tool_result":{"isError":false},"session_id":"test","turn_count":1}' | \
  python3 .claude/hooks/circuit_breaker_monitor.py
```

### High Memory Usage
```bash
# Check memory stats
python3 scripts/ops/circuit_status.py --memory

# If telemetry huge, manually rotate
python3 -c "
from scripts.lib.memory_cleanup import rotate_all_telemetry
print('\n'.join(rotate_all_telemetry()))
"
```

---

## Success Criteria

**After 1 week, system is successful if:**
- ✅ No crashes or errors in stderr logs
- ✅ Memory usage <1MB
- ✅ State file <50KB
- ✅ No false positive circuit trips
- ✅ Memory cleanup runs automatically on session start
- ✅ Tests still passing (8/8)

**If any criteria fail:** Investigate, tune config, or consider rollback.

---

## Documentation Update

After deployment, update CLAUDE.md:

```markdown
## 🔒 Circuit Breaker Protocol (22nd Protocol)

**Purpose:** Prevent runaway loops and memory leaks.

**Commands:**
- `/circuit-status` - Show circuit breaker and memory status
- `/reset-circuit --all` - Reset all circuit breakers (admin override)

**Bypass:** Include "SUDO BYPASS" keyword to override circuit breaker.

**Automatic Protection:**
- Tool failures (3 in 5 turns) → Circuit trips
- Sequential tool abuse (>10 same tool in 1 turn) → Warning
- Memory auto-cleanup on session start (telemetry rotation, session pruning)

**Status Indicators:**
- 🚨 Circuit OPEN - Operation blocked, cooldown active
- ⚠️ Circuit HALF_OPEN - Probing after cooldown
- ✅ Circuit CLOSED - Normal operation

See `scripts/lib/circuit_breaker.py` for implementation.
```

---

## Deployment Sign-Off

**Prerequisites Met:**
- [x] All tests passing (8/8)
- [x] Critical gaps fixed (0 remaining)
- [x] Documentation complete
- [x] Rollback plan defined

**Deployment Status:** 🟢 READY

**Approved By:** [Your approval]
**Date:** 2025-11-23

**Proceed with deployment.**
