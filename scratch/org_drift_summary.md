# Organizational Drift Prevention Protocol - Implementation Summary

## Overview

Implemented a comprehensive, auto-tuning enforcement system to prevent catastrophic file structure anti-patterns in autonomous AI systems with complex hook ecosystems.

## Problem Statement

Autonomous AI systems with extensive hook systems can create nightmare scenarios:
- **Recursive directories**: `scripts/scripts/ops/` breaks all tooling
- **Root pollution**: Files dumped in repository root violate constitution
- **Production pollution**: Test/debug files leak into production code
- **Unbounded growth**: Hooks/scratch files accumulate without limit
- **Duplication**: Same files exist in multiple production zones

These issues are catastrophic because:
1. They break tooling and navigation
2. They violate architectural boundaries
3. They create maintenance nightmares
4. They accumulate silently until the system is unusable

## Solution Architecture

### 1. Detection Library (`scripts/lib/org_drift.py`)

**Catastrophic Checks (Hard Blocks):**
- `detect_recursion()`: Finds repeated directory names in paths
- `detect_root_pollution()`: Catches new files in repo root
- `detect_production_pollution()`: Finds test/debug files in production zones
- `detect_filename_collision()`: Detects duplicates across zones

**Threshold Checks (Warnings with Auto-Tuning):**
- Hook Explosion: >30 hooks (range: 25-40)
- Scratch Bloat: >500 files (range: 300-700)
- Memory Fragmentation: >100 session files (range: 75-150)
- Deep Nesting: >6 levels (range: 5-8)

**Auto-Tuning Framework:**
- Runs every 100 turns
- Target: 5-15% false positive rate
- Adjustments: +20% if FP >15%, -10% if FP <5%
- Tracks SUDO overrides for pattern learning

### 2. PreToolUse Hook (`.claude/hooks/org_drift_gate.py`)

**Purpose:** Gate Write/Edit operations before they happen

**Behavior:**
- Runs drift detection on target file path
- Hard-blocks catastrophic violations
- Shows warnings for threshold violations (doesn't block)
- Respects "SUDO" keyword overrides
- Logs overrides for analysis

**Integration:**
- Matcher: `(Write|Edit)`
- Position: Early in hook chain
- Error handling: On failure, allows operation (fail-open)

### 3. PostToolUse Hook (`.claude/hooks/org_drift_telemetry.py`)

**Purpose:** Track all file operations for pattern analysis

**Data Collected:**
- Timestamp, tool name, file path, directory, depth
- Success/failure status

**Storage:** `.claude/memory/org_drift_telemetry.jsonl`

**Future Use:**
- Machine learning on drift patterns
- Predictive detection
- Pattern clustering for auto-rules

### 4. Management Tool (`scripts/ops/drift_org.py`)

**Commands:**

```bash
# View current state and statistics
drift_org report

# Record a false positive (for auto-tuning)
drift_org fp <violation_type>

# Manually adjust threshold
drift_org set <threshold_name> <value>

# Reset all state (nuclear option)
drift_org reset
```

## Key Features

### Smart Exclusions

The following paths bypass ALL checks:
- `node_modules/`, `venv/`, `__pycache__/` (system-managed)
- `.git/` (version control)
- `scratch/archive/` (intentional archival)
- `projects/` (user owns structure)
- `.template/` (templates may mirror structures)

**Rationale:** Don't block the system or user-controlled zones

### SUDO Override System

**Syntax:** Include "SUDO" in prompt
**Effect:** Allows operation despite violations
**Tracking:** Logs to `sudo_overrides` array with type, path, timestamp

**Philosophy:**
- Provide escape hatch for legitimate operations
- Track what users override → identify false positive patterns
- Enable future auto-rule generation from common overrides

### Auto-Tuning Mechanism

**Algorithm:**
1. Every 100 turns, calculate FP rate: `FP_rate = (FP_count / total_checks) * 100`
2. If `FP_rate > 15%`: Increase threshold by 20% (too strict)
3. If `FP_rate < 5%` AND `total_checks > 50`: Decrease by 10% (too loose)
4. Report adjustments transparently

**Example Output:**
```
🔧 Auto-tuned thresholds (Turn 100):
   • hook_explosion: 30 → 36 (FP rate 20.0%)
   • scratch_bloat: 500 → 450 (FP rate 2.0%)
```

**Goal:** Zero-maintenance system that adapts to actual usage patterns

## Testing

### Unit Tests (`scratch/test_org_drift.py`)

10 tests covering:
- Recursion detection
- Root pollution detection
- Production pollution detection
- Depth calculation
- Exclusion patterns
- Filename collision detection
- Full drift check (catastrophic)
- Auto-tuning logic
- Warnings vs errors
- Exclusion bypass

**Result:** 10/10 passing ✅

### Integration Tests (`scratch/test_org_drift_integration.py`)

8 tests covering:
- Recursion blocks via hook
- Root pollution blocks via hook
- Production pollution blocks via hook
- Valid files allowed
- SUDO override behavior
- Warnings don't block
- Excluded paths bypass
- Edit operations checked

**Result:** 8/8 passing ✅

## State Management

### State File (`.claude/memory/org_drift_state.json`)

```json
{
  "thresholds": {
    "max_hooks": 30,
    "max_scratch_files": 500,
    "max_memory_sessions": 100,
    "max_depth": 6,
    "max_root_files": 0
  },
  "false_positives": {
    "hook_explosion": 0,
    "scratch_bloat": 0
  },
  "total_checks": {
    "recursion": 3,
    "root_pollution": 5
  },
  "last_tuning": "2025-11-23T...",
  "turn_count": 17,
  "sudo_overrides": [
    {
      "type": "root_pollution",
      "path": "/path/to/file",
      "timestamp": "2025-11-23T..."
    }
  ]
}
```

### Telemetry File (`.claude/memory/org_drift_telemetry.jsonl`)

```jsonl
{"timestamp": "2025-11-23T...", "tool": "Write", "file_path": "...", "depth": 3, "success": true}
{"timestamp": "2025-11-23T...", "tool": "Edit", "file_path": "...", "depth": 2, "success": true}
```

## Documentation

### User-Facing
- **CLAUDE.md**: Protocol overview, rules, commands
- **scratch/org_drift_protocol_docs.md**: Comprehensive technical docs

### Developer-Facing
- **scripts/lib/org_drift.py**: Inline docstrings
- **scratch/org_drift_analysis.md**: Design rationale

## Success Metrics

1. **Zero catastrophic violations** in production (recursion, root pollution)
2. **FP rate 5-15%** across all threshold checks
3. **Auto-convergence <100 turns** after system changes
4. **SUDO usage <5%** (most operations should be clean)

## Current Status

✅ **All components operational**
- Library: 400+ lines, fully tested
- Hooks: Registered and active
- Tool: CLI ready
- Tests: 18/18 passing
- Documentation: Complete

📊 **Initial State** (Turn 17)
- 17 checks performed
- 0 false positives
- 2 SUDO overrides (both root pollution in tests)
- All thresholds at default values

## Philosophy

**Constitutional Enforcement:** This protocol enforces CLAUDE.md Hard Block #1 ("Root Pollution Ban") and prevents the hook system from creating unmaintainable complexity.

**Zero-Revisit Infrastructure:** Like the Scratch-First and Command Prerequisite protocols, this system auto-tunes to minimize false positives, requiring zero manual intervention.

**Fail Fast, Tune Later:** Better to block one legitimate operation than allow one catastrophic violation. The system starts strict and loosens based on evidence.

**Escape Hatches Required:** SUDO overrides prevent gridlock while providing data for improving detection rules over time.

## Future Enhancements

1. **Machine Learning on Overrides**
   - Cluster SUDO override patterns (>10 occurrences, >70% confidence)
   - Auto-generate exception rules
   - Update exclusion patterns

2. **Cross-File Analysis**
   - Detect duplicate logic (not just filenames)
   - Use AST comparison or hash-based similarity

3. **Dependency Graph Enforcement**
   - Track import relationships
   - Prevent circular dependencies across zones

4. **Size-Based Rules**
   - Block files >1000 lines in production zones
   - Encourage modularization

5. **Temporal Patterns**
   - Detect "churn" (files created/deleted rapidly)
   - Flag unstable areas of codebase

## Integration Checklist

- [x] Detection library implemented
- [x] PreToolUse hook created
- [x] PostToolUse hook created
- [x] Management tool created
- [x] Hooks registered in settings.json
- [x] Unit tests written and passing
- [x] Integration tests written and passing
- [x] Documentation added to CLAUDE.md
- [x] Active context updated
- [x] Tool added to CLI shortcuts
- [x] State files initialized

## Files Modified/Created

**Created:**
- `scripts/lib/org_drift.py` (400+ lines)
- `.claude/hooks/org_drift_gate.py`
- `.claude/hooks/org_drift_telemetry.py`
- `scripts/ops/drift_org.py`
- `scratch/test_org_drift.py`
- `scratch/test_org_drift_integration.py`
- `scratch/org_drift_analysis.md`
- `scratch/org_drift_protocol_docs.md`
- `scratch/org_drift_summary.md`

**Modified:**
- `.claude/settings.json` (added hooks)
- `CLAUDE.md` (added protocol section + CLI shortcut)
- `.claude/memory/active_context.md` (added session entry)

**State Files (Auto-Generated):**
- `.claude/memory/org_drift_state.json`
- `.claude/memory/org_drift_telemetry.jsonl`

---

**Total Lines of Code:** ~1500+ (library + hooks + tests + tools)
**Testing Coverage:** 18/18 tests passing
**Status:** ✅ Production Ready
