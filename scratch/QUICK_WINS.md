# Threading Optimization - Quick Wins

## 🚀 30-Minute Fixes (Do Now)

### 1. Add Subprocess Timeouts
```bash
python3 scratch/add_subprocess_timeouts.py --apply
```
**Impact:** Prevents 32 potential hang points
**Risk:** Very low (adds safety)

---

### 2. Increase Parallel Workers
```bash
# File 1: best_practice_enforcer.py
sed -i 's/max_workers=10/max_workers=50/g' .claude/hooks/best_practice_enforcer.py

# File 2: detect_batch.py  
sed -i 's/max_workers=10/max_workers=50/g' .claude/hooks/detect_batch.py
```
**Impact:** 5× speedup on batch operations
**Risk:** Very low (just parameter change)

---

### 3. Validate
```bash
# Syntax check
python3 -m py_compile .claude/hooks/*.py scripts/ops/*.py scripts/lib/*.py

# Run tests
python3 -m pytest tests/ -v
```

---

## 📊 Current vs Optimized

| Metric | Before | After 30min | After Full |
|--------|--------|-------------|------------|
| Hook latency | 1050ms | 1050ms | 400ms |
| Subprocess hangs | 32 risks | 0 risks | 0 risks |
| Batch workers | 10 | 50 | 50 |
| Agent pattern | Sequential | Parallel* | Parallel* |

*Already documented in CLAUDE.md

---

## 🎯 Biggest Impact (2-4 Hours)

**Hook Consolidation:** 21 → 11 hooks = 650ms savings per prompt

See `scratch/OPTIMIZATION_ACTION_PLAN.md` for detailed guide.

---

## 📁 All Reports

- `scratch/EXEC_SUMMARY.md` - Executive summary
- `scratch/OPTIMIZATION_ACTION_PLAN.md` - Step-by-step implementation
- `scratch/threading_optimization_summary.md` - Full analysis
- `scratch/script_analysis_detailed.txt` - Per-file breakdown

---

**Total Time to 90% Optimization: ~3 hours**
