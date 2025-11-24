# Hook Unification Recommendation
**Date:** 2025-11-22
**Current State:** 19 UserPromptSubmit hooks (known-good, stable)
**Goal:** Reduce hook count WITHOUT losing functionality

---

## Executive Summary

After analyzing all 19 hooks:
- **18 are read-only** (inject context but don't write state)
- **1 writes state** (confidence_init)
- All follow similar pattern: detect trigger → inject context

**Conservative Recommendation:** Merge **2-4 hooks** maximum
**Expected Reduction:** 19 → 17 or 19 → 15 hooks
**Risk Level:** LOW (if done carefully)

---

## Merge Candidates (Ranked by Safety)

### ✅ TIER 1: VERY SAFE (Recommended)

#### 1. Pattern Detectors → `unified_pattern_detector.py`
**Merge:** `detect_gaslight.py` + `detect_batch.py`

**Similarity:**
- Both are simple regex pattern matchers
- Both inject warning when pattern matches
- Zero state writes, zero dependencies
- ~150 lines each, mostly pattern lists

**Implementation:**
```python
patterns = {
    'gaslighting': {
        'triggers': ['you said', 'still not working', 'stop lying', ...],
        'message': '🚨 GASLIGHTING PROTOCOL ACTIVE...'
    },
    'batch_operation': {
        'triggers': ['batch', 'bulk', 'all files', ...],
        'message': '⚠️ BATCH OPERATION DETECTED...'
    }
}
```

**Savings:** 1 hook
**Risk:** VERY LOW
**Effort:** 30 minutes

---

### ⚠️ TIER 2: SAFE (Conditional)

#### 2. Behavioral Controls → `unified_behavioral_controls.py`
**Merge:** `intervention.py` + `anti_sycophant.py`

**Similarity:**
- Both detect problematic conversation patterns
- `intervention`: bikeshedding keywords
- `anti_sycophant`: opinion requests
- Both inject "think twice" warnings

**Risk Assessment:**
- Need to READ hooks first to verify no complex logic
- If both are simple pattern matchers → SAFE
- If either has state management → DO NOT MERGE

**Savings:** 1 hook
**Risk:** LOW (if verified)
**Effort:** 1 hour (includes verification)

---

### ⚠️ TIER 3: MEDIUM RISK (Research Required)

#### 3. Advisor Consolidation → `unified_advisor.py`
**Merge:** `pre_advice.py` + `command_suggester.py` + `best_practice_enforcer.py`

**Complexity:**
- All provide guidance, but at different phases
- May have different trigger conditions
- Risk of instruction conflicts if merged incorrectly

**Approach:**
1. Read all three hooks fully
2. Map trigger conditions
3. Design multi-phase advisor (pre → suggest → enforce)
4. Test extensively before deploying

**Savings:** 2 hooks
**Risk:** MEDIUM
**Effort:** 2-3 hours

---

## DO NOT MERGE (Unique Functions)

These hooks have unique, non-overlapping functionality:

| Hook | Reason |
|------|--------|
| `confidence_init` | State initializer - MUST run first, writes state |
| `synapse_fire` | Associative memory - complex algorithm |
| `force_playwright` | Browser automation trigger |
| `auto_commit_on_complete` | Completion detector |
| `prerequisite_checker` | Complex prerequisite validation (175 lines) |
| `sanity_check` | Logic validation |
| `check_knowledge` | Knowledge gap detection |
| `intent_classifier` | Intent analysis |
| `ecosystem_mapper` | Workflow mapping |
| `enforce_workflow` | Workflow enforcement |
| `detect_low_confidence` | Confidence warnings (different from penalty) |
| `detect_confidence_penalty` | Applies penalties via subprocess |

---

## Recommended Phased Approach

### Phase 1: Pattern Detectors Only (Week 1)
**Action:** Merge `detect_gaslight` + `detect_batch` → `unified_pattern_detector.py`

**Steps:**
1. Create `scratch/unified_pattern_detector.py`
2. Test side-by-side with originals
3. Backup `settings.json`
4. Update hook configuration
5. Monitor for 1 week

**Success Criteria:**
- All warnings still fire correctly
- No context pollution increase
- Latency improves by ~50-100ms

**If stable** → Proceed to Phase 2
**If unstable** → Rollback, keep 19 hooks

---

### Phase 2: Behavioral Controls (Week 2)
**Action:** Merge `intervention` + `anti_sycophant` → `unified_behavioral_controls.py`

**Prerequisites:**
- Phase 1 stable for 1 week
- Read both hooks to verify no hidden complexity

**Steps:**
1. Verify both are simple pattern matchers
2. Create unified hook in `scratch/`
3. Test, backup, deploy
4. Monitor for 1 week

**Success Criteria:**
- All behavioral warnings intact
- No new instruction conflicts

---

### Phase 3: Evaluation (Week 3)
**Decision Point:** Continue consolidation or stop?

**If 19 → 17 is stable:**
- Consider Phase 4 (Advisor consolidation)
- Evaluate if 2-hook reduction is sufficient

**If any instability:**
- STOP consolidation
- Document what works, what doesn't
- Keep current stable state

---

## Risk Mitigation

### Before ANY Merge:
```bash
# Backup
cp .claude/settings.json .claude/settings.json.backup_$(date +%Y%m%d)

# Create rollback script
cat > rollback.sh <<'EOF'
#!/bin/bash
cp .claude/settings.json.backup_XXXXXXXX .claude/settings.json
echo "Rolled back to previous configuration"
EOF
chmod +x rollback.sh
```

### Testing Checklist:
- [ ] Compare outputs: old hook vs new hook on same inputs
- [ ] Verify all trigger patterns still fire
- [ ] Check context injection size (should not increase)
- [ ] Measure latency (should decrease or stay same)
- [ ] Monitor for 7 days before next merge

### Rollback Triggers:
- Context pollution increases (>30 system-reminder tags per response)
- Warnings/suggestions stop firing
- New instruction conflicts appear
- Latency increases
- User reports unexpected behavior

---

## Expected Outcomes

### Conservative (Phase 1 + 2 only):
- **Current:** 19 hooks
- **New:** 17 hooks
- **Latency:** -100-200ms
- **Risk:** VERY LOW

### Moderate (Phase 1 + 2 + 3):
- **Current:** 19 hooks
- **New:** 15 hooks
- **Latency:** -300-500ms
- **Risk:** LOW-MEDIUM

### Aggressive (All merges):
- **Current:** 19 hooks
- **New:** 12 hooks
- **Latency:** -700-1000ms
- **Risk:** MEDIUM-HIGH
- **Recommendation:** DO NOT ATTEMPT

---

## Conclusion

**START SMALL:** Merge pattern detectors only (Phase 1)

**Rationale:**
- 19 hooks is at stability threshold, not catastrophic
- Context pollution is the real risk, not hook count
- 2-4 hook reduction provides meaningful latency improvement
- Low risk of breaking working system

**Philosophy:** Don't fix what isn't broken. Optimize incrementally.

---

## Next Steps

1. **Review this recommendation**
2. **Choose approach:** Conservative (Phase 1 only) or Moderate (Phase 1+2)
3. **If approved:** Create `unified_pattern_detector.py` in `scratch/`
4. **Test thoroughly** before deploying
5. **Monitor for 1 week** minimum
6. **Document results** for future reference

---

## Appendix: Hook Analysis Summary

```
UserPromptSubmit Hooks (19 total):

Read-Only Pattern Matchers (SAFE TO MERGE):
  • detect_gaslight      - Frustration detection
  • detect_batch         - Batch operation detection
  • intervention         - Bikeshedding detection
  • anti_sycophant       - Opinion request blocker

Advisory/Suggestion (MEDIUM RISK):
  • pre_advice           - General advice
  • command_suggester    - Command suggestions
  • best_practice_enforcer - Anti-pattern warnings

Complex Validators (DO NOT MERGE):
  • prerequisite_checker - 175 lines, complex logic
  • sanity_check         - Logic validation
  • check_knowledge      - Knowledge gap detection

Unique Functions (DO NOT MERGE):
  • confidence_init      - State initializer
  • synapse_fire         - Associative memory
  • force_playwright     - Browser automation
  • auto_commit_on_complete - Completion detector
  • intent_classifier    - Intent analysis
  • ecosystem_mapper     - Workflow mapping
  • enforce_workflow     - Workflow enforcement

Confidence System (KEEP SEPARATE):
  • detect_low_confidence - Warning injection
  • detect_confidence_penalty - Penalty application
```

**Total Mergeable (Conservative):** 4 hooks → 2 unified hooks
**Total Mergeable (Moderate):** 7 hooks → 3 unified hooks
**Total Unique (Keep Separate):** 12 hooks
