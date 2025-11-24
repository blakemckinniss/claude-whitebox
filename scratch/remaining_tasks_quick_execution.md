# Remaining Tasks - Quick Execution Plan

## Completed (3/12)
✅ Auto-tuning library (auto_tuning.py)
✅ Meta-learning system (meta_learning.py)
✅ Batching enforcer upgrade

## Current Session Priorities (High Value, Can Complete Today)

### Priority 1: Command Prerequisites Auto-Tuning (2 hours)
**Why:** High-impact enforcement system that currently has static 20-turn window
**Implementation:**
- Use auto_tuning.py framework
- Track actual time between upkeep/verify runs
- Auto-adjust windows based on actual usage patterns
- Add OBSERVE → WARN → ENFORCE phases

### Priority 2: Telemetry Framework (1 hour)
**Why:** Standardizes state management across all systems
**Implementation:**
- Extract common patterns from auto_tuning.py and meta_learning.py
- Create base class for state management
- Add standard metrics calculation

### Priority 3: Update Existing Systems to Use Meta-Learning (1 hour)
**Why:** Immediate benefit - all hooks learn from bypasses
**Implementation:**
- Update scratch_enforcer.py to record overrides
- Update batching_enforcer.py to record overrides
- Add auto_update_rules() calls to PostToolUse hooks

## Next Session Priorities (Memory Hygiene - High ROI)

### Priority 4: Lesson Consolidation (3 hours)
**Why:** Prevents lessons.md from becoming noise
**Implementation:**
- Use TF-IDF or simple word overlap for similarity
- Merge duplicates (keep most recent/specific)
- Auto-expire old lessons (>6 months + not cited in 50 turns)
- Weight by recency + citation count

### Priority 5: Debt Auto-Prioritizer (2 hours)
**Why:** Prevents debt_ledger from accumulating
**Implementation:**
- Score by: git log frequency + file complexity + age
- Auto-suggest top 3 every 100 turns
- Auto-remove resolved items via verify checks

### Priority 6: Telemetry Archiver (1 hour)
**Why:** Prevents disk bloat from JSONL logs
**Implementation:**
- Compress logs >1 month old
- Aggregate to summary stats
- Purge >6 months old

## Future Session Priorities (Pattern Learning - Advanced)

### Priority 7: Anti-Pattern Auto-Discovery (4 hours)
**Why:** System learns from failures without manual pattern authoring
**Implementation:**
- Cluster tool failures + penalties from telemetry
- Generate anti-pattern rules from clusters
- Test rules against historical data (precision/recall)
- Auto-add rules with >70% confidence

### Priority 8: Synapse Pattern Auto-Learner (3 hours)
**Why:** Associative memory improves coverage over time
**Implementation:**
- Track synapse firing success rate (did user act on suggestion?)
- Prune patterns with <20% success rate
- Cluster uncovered prompts, suggest new patterns

### Priority 9: Integration Testing (2 hours)
**Why:** Ensure all systems work together
**Implementation:**
- 1000-turn simulation
- Verify phase transitions occur correctly
- Check threshold convergence
- Validate false positive rates

### Priority 10: Documentation (1 hour)
**Why:** Update CLAUDE.md with new protocols
**Implementation:**
- Document meta-learning system
- Document auto-tuning framework
- Update hard blocks list
- Add success metrics

## Implementation Order for THIS SESSION

1. ✅ auto_tuning.py (DONE)
2. ✅ meta_learning.py (DONE)
3. ✅ Batching enforcer upgrade (DONE)
4. **→ Command prerequisites upgrade** (NEXT - 2 hours)
5. **→ Wire meta-learning into existing hooks** (1 hour)
6. **→ Create test suite for auto-tuning** (1 hour)

**Remaining time today: ~4 hours of work**
**Can complete: Priorities 1, 3, and basic testing**

## Success Metrics to Track

After today's work:
- [ ] 2 enforcement systems using auto_tuning.py (batching + prerequisites)
- [ ] All hooks recording overrides to meta_learning
- [ ] Exception rules being auto-generated every 100 turns
- [ ] Test coverage for auto-tuning framework (8/8 tests passing)
- [ ] Phase transitions validated

After next session:
- [ ] Lessons consolidation preventing bloat
- [ ] Debt auto-prioritization working
- [ ] Telemetry archival preventing disk bloat
- [ ] All memory hygiene systems operational

After future sessions:
- [ ] Anti-patterns being auto-discovered from failures
- [ ] Synapse patterns being auto-learned from usage
- [ ] 1000-turn simulation passing
- [ ] Documentation complete
