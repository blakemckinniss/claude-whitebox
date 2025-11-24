# Zero-Revisit Implementation Plan
## Strategy: Go Deep AND Go Wide

**Goal:** Build foundation (Meta-Learning + Threshold Library) WHILE applying quick wins to existing systems in parallel.

## Parallel Execution Strategy

### Track 1: Foundation (Deep) - 2 days
Build reusable infrastructure that every system can adopt.

**Deliverables:**
1. `scripts/lib/meta_learning.py` - Override tracking, pattern clustering, exception rule generation
2. `scripts/lib/auto_tuning.py` - Threshold adjustment framework (extract from scratch_enforcement)
3. `scripts/lib/telemetry_framework.py` - Standardized metrics collection

### Track 2: Quick Wins (Wide) - 1 day
Apply scratch_enforcement pattern to 3 existing systems NOW (before foundation is ready).

**Deliverables:**
1. Batching enforcement → Add auto-tuning (FP rate tracking, threshold adjustment)
2. Command prerequisites → Add adaptive windows (learn optimal timing)
3. Performance gates → Add ROI-based threshold tuning

### Track 3: Memory Hygiene - 1 day
Prevent accumulation problems.

**Deliverables:**
1. Lesson consolidation system
2. Debt auto-prioritizer
3. Telemetry archiver

### Track 4: Pattern Learning - 2 days
Auto-discovery systems.

**Deliverables:**
1. Anti-pattern auto-discovery
2. Synapse pattern auto-learner

## Implementation Order (Optimized for Parallelism)

### Phase 1: Parallel Foundation + Quick Wins (Day 1)
**Morning (Foundation):**
- Extract auto-tuning logic from scratch_enforcement.py → auto_tuning.py
- Create TelemetryFramework class (standardized state management)

**Afternoon (Quick Wins):**
- Apply auto-tuning to batching_enforcer.py
- Apply auto-tuning to command_prerequisite_gate.py

**Why parallel:** Quick wins validate the pattern while foundation is being built.

### Phase 2: Meta-Learning + More Quick Wins (Day 2)
**Morning (Foundation):**
- Build override tracking system (meta_learning.py)
- Implement pattern clustering (use sklearn or simple k-means)

**Afternoon (Quick Wins):**
- Apply auto-tuning to performance_gate.py
- Wire meta-learning into all enforcement hooks

**Why parallel:** Meta-learning integrates with quick wins as they're being built.

### Phase 3: Memory Hygiene (Day 3)
**Morning:**
- Lesson consolidation (semantic similarity via embeddings or TF-IDF)
- Debt auto-prioritizer

**Afternoon:**
- Telemetry archiver
- Hook auto-optimizer (reorder hooks by execution time)

**Why sequential:** These build on telemetry framework from Phase 1.

### Phase 4: Pattern Learning (Day 4-5)
**Day 4:**
- Anti-pattern auto-discovery (cluster failures → generate rules)
- Test anti-pattern rules (do they prevent future failures?)

**Day 5:**
- Synapse pattern auto-learner (track firing success rate)
- Integration testing across all systems

## Concrete Tasks (Broken Down)

### Task Group A: Foundation (Can run in parallel with B)

**A1. Extract Auto-Tuning Library** (2-3 hours)
```python
# scripts/lib/auto_tuning.py
class AutoTuner:
    def __init__(self, state_file, pattern_name, default_threshold):
        self.state = load_state(state_file)
        self.pattern = pattern_name

    def detect(self, history, current_turn) -> Optional[Detection]:
        # Generic pattern detection

    def should_enforce(self, prompt=None) -> Tuple[Action, Message]:
        # Phase-based enforcement (OBSERVE/WARN/ENFORCE)

    def update_metrics(self, turns_wasted, script_written, bypassed):
        # Update pattern statistics

    def auto_tune_threshold(self, turn):
        # Adjust based on FP rate + ROI

    def check_phase_transition(self, turn):
        # Auto-transition between phases
```

**A2. Build Meta-Learning System** (4-5 hours)
```python
# scripts/lib/meta_learning.py
class OverrideTracker:
    def record_override(self, hook_name, reason, context):
        # Track SUDO/MANUAL/disable events

    def cluster_patterns(self):
        # Find common override patterns
        # Return: [(pattern, frequency, example_contexts)]

    def generate_exception_rules(self):
        # Convert clusters into exception rules
        # Format: {"pattern": regex, "action": "allow", "reason": str}

    def apply_exception_rules(self, hook_name, context):
        # Check if context matches exception rule
        # Return: (should_bypass, rule_matched)
```

**A3. Telemetry Framework** (2-3 hours)
```python
# scripts/lib/telemetry_framework.py
class EnforcementTelemetry:
    """Standardized state management for all enforcement systems"""

    def __init__(self, system_name, state_file):
        self.system = system_name
        self.state_file = state_file

    def track_detection(self, pattern, context):
        # Record pattern detection

    def track_bypass(self, pattern, bypass_type, reason):
        # Record override (MANUAL/SUDO)

    def calculate_metrics(self):
        # Return: {fp_rate, roi, adoption_rate, ...}

    def generate_report(self, turn):
        # Auto-report every N turns
```

### Task Group B: Quick Wins (Can run in parallel with A)

**B1. Batching Enforcement Auto-Tuning** (2 hours)
- Add state tracking to native_batching_enforcer.py
- Track bypasses when "SEQUENTIAL" keyword used
- Calculate FP rate from bypasses
- Auto-adjust threshold (2→3 or 2→1) every 50 turns
- Add auto-reporting

**B2. Command Prerequisites Auto-Tuning** (2 hours)
- Track actual time between command runs
- Calculate optimal windows (e.g., if upkeep runs every 15 turns, reduce window from 20→18)
- Auto-exempt certain task types (research-only sessions)
- Add phase evolution (OBSERVE→WARN→ENFORCE)

**B3. Performance Gates Auto-Tuning** (2 hours)
- Track what gets flagged as "waste" (sequential vs parallel)
- Calculate actual ROI (time saved by parallelism)
- Auto-adjust penalty thresholds based on task type
- Add bypass tracking

### Task Group C: Memory Hygiene

**C1. Lesson Consolidation** (3-4 hours)
```python
# scripts/ops/consolidate_lessons.py
class LessonConsolidator:
    def find_duplicates(self, lessons):
        # Use TF-IDF or semantic similarity
        # Return: [(lesson1, lesson2, similarity_score)]

    def merge_lessons(self, lesson_group):
        # Keep most specific/recent version
        # Add "consolidated from X entries" metadata

    def expire_old_lessons(self, lessons, age_threshold, citation_threshold):
        # Remove lessons >6 months old + not cited in 50 turns

    def weight_lessons(self, lessons):
        # Score by: recency + citation count + specificity
```

**C2. Debt Auto-Prioritizer** (2-3 hours)
```python
# Add to scripts/ops/upkeep.py or create debt_prioritizer.py
class DebtPrioritizer:
    def score_debt_items(self, debt_ledger, git_history):
        # Score by:
        # - Frequency of area modified (from git log)
        # - Complexity (from file size/cyclomatic complexity)
        # - Age of debt item

    def auto_suggest_paydown(self, turn):
        # Every 100 turns, suggest top 3 debt items

    def auto_remove_resolved(self, debt_ledger):
        # Run verify checks, remove items that pass
```

**C3. Telemetry Archiver** (2 hours)
```python
# .claude/hooks/telemetry_archiver.py (SessionEnd hook)
class TelemetryArchiver:
    def archive_old_logs(self, log_files, age_threshold):
        # Compress logs >1 month old (gzip)

    def aggregate_to_summary(self, raw_logs):
        # Convert raw logs to summary stats
        # Keep: counts, averages, distributions
        # Discard: individual events

    def purge_ancient_data(self, archive_dir, age_threshold):
        # Delete compressed logs >6 months old
```

### Task Group D: Pattern Learning

**D1. Anti-Pattern Auto-Discovery** (4-5 hours)
```python
# scripts/ops/discover_antipatterns.py
class AntiPatternDiscoverer:
    def collect_failures(self, telemetry_logs):
        # Gather all tool failures + penalties from last 1000 turns
        # Return: [(failure_type, context, frequency)]

    def cluster_failure_patterns(self, failures):
        # Use text clustering on context
        # Return: [(cluster_id, pattern_description, examples)]

    def generate_rules(self, clusters):
        # Convert clusters into anti-pattern rules
        # Format: {
        #   "name": "sequential_read_in_loop",
        #   "pattern": regex,
        #   "detection": "3+ Read calls with similar paths",
        #   "suggestion": "Use parallel.py or scratch script"
        # }

    def test_rules(self, rules, historical_data):
        # Replay historical data, see if rules would have prevented failures
        # Calculate: precision, recall, false positive rate
        # Return: [(rule, metrics)]
```

**D2. Synapse Pattern Auto-Learner** (3-4 hours)
```python
# scripts/ops/learn_synapses.py
class SynapsePatternLearner:
    def track_firing_success(self, synapse_fire_logs):
        # For each synapse pattern that fired:
        # - Did user act on the suggestion?
        # - Was the retrieved context relevant?
        # Return: [(pattern_id, success_rate, usefulness_score)]

    def prune_ineffective_patterns(self, patterns, threshold=0.2):
        # Remove patterns with <20% success rate

    def cluster_user_prompts(self, prompt_history):
        # Find common prompt types not covered by existing patterns
        # Return: [(cluster, representative_prompts)]

    def suggest_new_patterns(self, clusters):
        # Generate regex patterns for uncovered clusters
        # Return: [(proposed_pattern, rationale, example_matches)]
```

## Success Metrics (Track From Day 1)

### Foundation Metrics
1. **Reusability Score:** # of systems using auto_tuning.py / # of enforcement systems
   - Target: >80% by end of Week 2

2. **Override Clustering Success:** % of overrides that become exception rules
   - Target: >50% within 100 turns

### Quick Win Metrics
3. **Threshold Convergence Time:** Turns until thresholds stabilize
   - Target: <100 turns per system

4. **False Positive Rate:** % of enforcements that are bypassed
   - Target: 5-15% band (stable over time)

### Memory Hygiene Metrics
5. **Lesson Quality Score:** % of top-5 lessons that are cited in last 50 turns
   - Target: >80%

6. **Debt Paydown Rate:** # of debt items resolved / # added
   - Target: >1.0 (net reduction)

### Pattern Learning Metrics
7. **Anti-Pattern Coverage:** % of failures prevented by auto-discovered rules
   - Target: >60% within 500 turns

8. **Synapse Hit Rate:** % of synapse fires that lead to user action
   - Target: >40%

## Risk Mitigation

### Risk 1: Foundation Takes Too Long
**Mitigation:** Quick wins are independent - can ship without foundation
**Fallback:** If foundation blocked, complete all quick wins first

### Risk 2: Auto-Tuning Causes Instability
**Mitigation:** All systems start in OBSERVE phase (passive data collection)
**Fallback:** Emergency disable via SUDO keyword, auto-backtrack if FP >15%

### Risk 3: Memory Consolidation Loses Important Data
**Mitigation:** Keep backups before consolidation, dry-run mode first
**Fallback:** Restore from backup if consolidation removes critical lessons

### Risk 4: Pattern Discovery Generates Too Many Rules
**Mitigation:** Require >10 occurrences + >70% confidence before creating rule
**Fallback:** Auto-prune rules with >20% FP rate after 100 turn trial

## Deliverable Checklist

### Week 1: Foundation + Quick Wins
- [ ] auto_tuning.py (extract from scratch_enforcement)
- [ ] meta_learning.py (override tracking + clustering)
- [ ] telemetry_framework.py (standardized state management)
- [ ] Batching enforcement auto-tuning
- [ ] Command prerequisites auto-tuning
- [ ] Performance gates auto-tuning

### Week 2: Memory Hygiene + Pattern Learning
- [ ] Lesson consolidation system
- [ ] Debt auto-prioritizer
- [ ] Telemetry archiver
- [ ] Hook auto-optimizer
- [ ] Anti-pattern auto-discovery
- [ ] Synapse pattern auto-learner

### Week 3: Integration + Testing
- [ ] All systems use telemetry_framework
- [ ] All enforcement systems use auto_tuning
- [ ] Meta-learning integrated into all hooks
- [ ] End-to-end testing (1000 turn simulation)
- [ ] Documentation update (CLAUDE.md)
- [ ] Success metrics dashboard

## Next Immediate Action

**Start with parallel execution:**
1. Create auto_tuning.py (extract pattern from scratch_enforcement)
2. WHILE that's building, apply quick win to batching_enforcer.py

Both can happen in same session via parallel work streams.
