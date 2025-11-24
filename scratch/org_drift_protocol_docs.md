# The Organizational Drift Prevention Protocol (22nd Protocol)

## Philosophy

**Problem:** Autonomous AI systems with extensive hook systems can create catastrophic file structure issues through:
- Recursive directory structures (scripts/scripts/ops/)
- Duplicate files across production zones
- Test/debug pollution in production code
- Unbounded growth of hooks, scratch files, memory states
- Root directory pollution

**Solution:** Smart enforcement system that:
- Hard-blocks catastrophic violations (recursion, root pollution, production pollution)
- Warns on threshold violations (too many hooks/files)
- Auto-tunes thresholds to minimize false positives
- Allows SUDO overrides with tracking
- Excludes legitimate paths (projects/, node_modules/, etc.)

## Architecture

### Components

1. **Detection Library** (`scripts/lib/org_drift.py`)
   - Catastrophic pattern detection (recursion, pollution, collisions)
   - Threshold-based warnings (hook count, scratch bloat, etc.)
   - Auto-tuning framework (adjusts thresholds based on FP rate)
   - State management and reporting

2. **PreToolUse Hook** (`.claude/hooks/org_drift_gate.py`)
   - Intercepts Write/Edit operations
   - Runs drift detection BEFORE files are created
   - Hard-blocks catastrophic violations
   - Respects SUDO overrides

3. **PostToolUse Hook** (`.claude/hooks/org_drift_telemetry.py`)
   - Tracks all Write/Edit operations
   - Builds historical data for pattern analysis
   - Enables future machine learning on drift patterns

4. **Management Tool** (`scripts/ops/drift_org.py`)
   - View drift reports
   - Record false positives
   - Manually adjust thresholds
   - Reset state

## Detection Rules

### Catastrophic (Hard Blocks)

| Rule | Pattern | Example | Override |
|------|---------|---------|----------|
| **Recursion** | Directory name appears multiple times in path | `scripts/scripts/ops/` | SUDO |
| **Root Pollution** | New file in repo root outside allowlist | `/test.py` | SUDO |
| **Production Pollution** | Test/debug files in production zones | `scripts/ops/test_*.py` | SUDO |
| **Filename Collision** | Same filename in multiple production zones | `audit.py` in ops/ and lib/ | SUDO |

### Warnings (Soft Limits - Auto-Tuning)

| Rule | Initial Threshold | Auto-Tune Range | Rationale |
|------|------------------|-----------------|-----------|
| **Hook Explosion** | 30 hooks | 25-40 | Too many hooks = performance issues |
| **Scratch Bloat** | 500 files | 300-700 | Scratch is temp, not a dump |
| **Memory Fragmentation** | 100 sessions | 75-150 | Old sessions should be pruned |
| **Deep Nesting** | 6 levels | 5-8 | Excessive nesting hurts maintainability |

## Exclusions

These paths bypass ALL checks (catastrophic + warnings):

- `node_modules/`, `venv/`, `__pycache__/` (system-managed)
- `.git/` (version control)
- `scratch/archive/` (intentional archival)
- `projects/` (user owns structure)
- `.template/` (templates may mirror structures)

## Auto-Tuning Mechanism

### Goal
Keep false positive rate between 5-15%

### Algorithm
Every 100 turns:
1. Calculate FP rate per check type: `FP_rate = (FP_count / total_checks) * 100`
2. If `FP_rate > 15%`: Loosen threshold by 20%
3. If `FP_rate < 5%` AND `total_checks > 50`: Tighten by 10%
4. Report adjustments to user

### Example
```
Turn 100:
  hook_explosion: 100 checks, 20 FP (20% FP rate)
  → Threshold: 30 → 36 (loosened by 20%)

  scratch_bloat: 100 checks, 2 FP (2% FP rate)
  → Threshold: 500 → 450 (tightened by 10%)
```

## SUDO Override System

### Syntax
Include "SUDO" in your prompt to override blocks:

```
"SUDO Create test.py in root directory"
```

### Behavior
- Violation still detected and logged
- Operation allowed despite violation
- Recorded in `sudo_overrides` array for pattern analysis
- Used to identify common false positives → auto-generate exception rules

### Use Cases
- Legitimate one-off operations
- Testing enforcement system itself
- Temporary violations during refactors

## Usage

### CLI Commands

```bash
# View drift report
python3 scripts/ops/drift_org.py report

# Record false positive
python3 scripts/ops/drift_org.py fp hook_explosion

# Manually adjust threshold
python3 scripts/ops/drift_org.py set max_hooks 40

# Reset all state (careful!)
python3 scripts/ops/drift_org.py reset
```

### Programmatic

```python
from org_drift import check_organizational_drift

allowed, errors, warnings = check_organizational_drift(
    file_path="scripts/ops/new_tool.py",
    repo_root="/path/to/repo",
    is_sudo=False
)

if not allowed:
    print("BLOCKED:", errors)
```

## Integration

### Hooks Registered

**PreToolUse:**
- Matcher: `(Write|Edit)`
- Hook: `.claude/hooks/org_drift_gate.py`
- Position: Early in chain (before other Write/Edit hooks)

**PostToolUse:**
- Hook: `.claude/hooks/org_drift_telemetry.py`
- Position: After other PostToolUse hooks

### State Files

- **State:** `.claude/memory/org_drift_state.json`
  - Thresholds, FP counts, SUDO overrides, turn count
- **Telemetry:** `.claude/memory/org_drift_telemetry.jsonl`
  - Every Write/Edit operation logged

## Testing

### Unit Tests
`scratch/test_org_drift.py` - 10 tests
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

### Integration Tests
`scratch/test_org_drift_integration.py` - 8 tests
- Recursion blocks
- Root pollution blocks
- Production pollution blocks
- Valid files allowed
- SUDO override
- Warnings don't block
- Excluded paths bypass
- Edit operations checked

All tests passing ✅

## Success Metrics

1. **Zero catastrophic violations** (recursion, root pollution) in production
2. **FP rate 5-15%** across all threshold checks
3. **Auto-convergence <100 turns** after threshold changes
4. **SUDO usage <5%** (most operations should be clean)

## Maintenance

### When to Tune
- FP rate drifts outside 5-15% range
- New organizational pattern emerges
- User frequently overrides same violation type

### When to Add Rules
- New catastrophic pattern discovered (0% tolerance)
- Performance issue traced to file structure
- User repeatedly makes same mistake

### When to Remove Rules
- Rule has >30% FP rate for >500 turns
- User always overrides (suggests rule is wrong)
- Pattern no longer applicable to project

## Philosophy

**The Constitution is Supreme Law** - This protocol enforces CLAUDE.md Hard Block #1 ("Root Pollution Ban") and prevents the hook system from creating unmaintainable complexity.

**Auto-Tuning = Zero Revisiting** - Like other enforcement protocols, this system self-adjusts to minimize false positives while maintaining protection.

**Escape Hatches Required** - SUDO overrides prevent the system from blocking legitimate operations, while tracking provides data for improving detection.

**Fail Fast, Tune Later** - Start with strict rules; loosen based on evidence. Better to block one legitimate operation than allow one catastrophic violation.

## Future Enhancements

1. **Machine Learning on Overrides** - Cluster SUDO override patterns, auto-generate exception rules
2. **Cross-File Analysis** - Detect duplicate logic (not just filenames)
3. **Dependency Graph Enforcement** - Prevent circular dependencies across zones
4. **Size-Based Rules** - Block giant files in production zones
5. **Temporal Patterns** - Detect "churn" (files created/deleted rapidly)

---

**Status:** ✅ Fully Operational
**Tests:** 18/18 passing
**Hooks:** Registered in `.claude/settings.json`
**Auto-Tuning:** Active (every 100 turns)
