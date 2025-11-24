# Zero-Revisit Principle: Gap Analysis

## The Ideal
"The system will NEVER be abandoned because it requires ZERO revisiting"

## Current State Analysis

### ✅ Systems That Already Achieve This

1. **Scratch-First Enforcement** (just implemented)
   - Auto-tunes thresholds based on FP rate
   - Auto-transitions phases based on ROI
   - Auto-backtracks if too aggressive
   - Auto-reports every 50 turns
   - **Why it works:** Self-correcting feedback loop with quantitative metrics

2. **Epistemological Protocol** (confidence tracking)
   - Auto-tracks evidence gathering
   - Auto-updates confidence based on actions
   - Auto-enforces tier gates
   - **Why it works:** Passive accumulation, no human input needed

3. **Background Execution Telemetry**
   - Auto-tracks usage ratio
   - Auto-reports underutilization
   - Auto-calculates time savings
   - **Why it works:** Pure telemetry, no decisions needed

### ⚠️ Systems That PARTIALLY Achieve This

1. **Batching Enforcement**
   - ✅ Auto-detects sequential tool use
   - ✅ Auto-blocks violations
   - ❌ NO auto-tuning of thresholds
   - ❌ NO phase evolution (always enforcing)
   - ❌ NO false positive tracking
   - **Gap:** Static rules → will be too aggressive or too passive over time

2. **Command Prerequisites**
   - ✅ Auto-tracks command runs
   - ✅ Auto-blocks violations
   - ❌ NO adaptation to workflow changes
   - ❌ NO learning from bypasses
   - **Gap:** Fixed windows (20 turns for upkeep, 3 for verify) may not fit all tasks

3. **Performance Rewards/Penalties**
   - ✅ Auto-rewards parallel execution
   - ✅ Auto-penalizes sequential waste
   - ❌ NO threshold tuning for "what counts as waste"
   - ❌ NO adaptation to different task types
   - **Gap:** One-size-fits-all scoring

### ❌ Systems That REQUIRE Manual Revisiting

1. **Anti-Patterns Registry** (.claude/memory/anti_patterns.md)
   - Static list of patterns
   - No auto-detection of new anti-patterns from failures
   - No auto-removal of false positives
   - **Problem:** Becomes stale over time

2. **Synapses (Associative Memory)**
   - Static regex patterns in synapses.json
   - No learning from successful/failed associations
   - No auto-addition of new patterns from user interactions
   - **Problem:** Coverage gaps appear as new tasks emerge

3. **Hook Performance Monitoring**
   - Tracks hook execution times
   - Reports slow hooks
   - ❌ NO auto-disabling of expensive hooks
   - ❌ NO auto-reordering for efficiency
   - **Problem:** Generates alerts but requires human action

4. **Debt Ledger**
   - Tracks technical debt items
   - ❌ NO auto-prioritization based on impact
   - ❌ NO auto-scheduling of debt paydown
   - ❌ NO auto-removal of resolved items
   - **Problem:** Accumulates without resolution

5. **Lessons Learned**
   - Auto-captures lessons on session end
   - ❌ NO auto-weighting by relevance
   - ❌ NO auto-consolidation of duplicates
   - ❌ NO auto-expiration of outdated lessons
   - **Problem:** Signal-to-noise ratio degrades

## Root Causes of "Requires Revisiting"

### Cause 1: Static Thresholds Without Feedback
**Examples:**
- Batching enforcer: "2+ sequential reads = violation" (always)
- Command prerequisites: "upkeep must run within 20 turns" (always)
- Hook performance: "hooks >500ms = slow" (always)

**Solution Pattern:** Add telemetry → calculate actual distributions → auto-adjust thresholds

### Cause 2: No Learning from Bypasses
**Examples:**
- User uses "SUDO" to override → system doesn't learn why
- User uses "MANUAL" → no analysis of whether rule was wrong
- User disables hook → no tracking of why

**Solution Pattern:** Track bypass reasons → cluster common patterns → auto-loosen rules for those patterns

### Cause 3: Accumulation Without Pruning
**Examples:**
- Lessons.md grows forever (currently 50+ entries)
- Debt ledger accumulates (no auto-paydown)
- Telemetry logs grow unbounded

**Solution Pattern:** Auto-prune based on age + relevance scores + duplication detection

### Cause 4: Detection Without Action
**Examples:**
- Hook performance monitor detects slow hooks → just reports
- Debt tracker identifies debt → just logs
- Fallacy detector finds anti-patterns → just warns

**Solution Pattern:** Detection + Auto-remediation (or auto-scheduling of remediation)

## Optimization Opportunities (Ranked by Impact)

### 🔥 CRITICAL (High Impact, Enables Everything Else)

1. **Meta-Learning System** (Foundation for all other optimizations)
   - Track ALL user overrides/bypasses (SUDO, MANUAL, hook disable, etc.)
   - Cluster common override patterns
   - Auto-generate "exception rules" from clusters
   - Auto-loosen enforcement for high-FP patterns
   - Auto-tighten enforcement for zero-FP patterns
   - **Impact:** Every enforcement system becomes self-tuning

2. **Threshold Auto-Tuning Library** (Generalize scratch_enforcement pattern)
   - Extract auto-tuning logic into reusable lib
   - Apply to: batching, prerequisites, performance gates, etc.
   - Each system tracks: detections, bypasses, ROI, FP rate
   - Each system auto-adjusts thresholds every N turns
   - **Impact:** 10+ systems become self-tuning overnight

3. **Lesson Consolidation System** (Prevent memory bloat)
   - Auto-detect duplicate lessons (semantic similarity)
   - Auto-merge similar lessons (keep most specific)
   - Auto-expire lessons (>6 months old + not referenced in 50 turns)
   - Auto-weight lessons by recency + citation count
   - **Impact:** Lessons stay relevant, signal-to-noise stays high

### 🟡 HIGH IMPACT (Force Multipliers)

4. **Hook Auto-Optimizer**
   - Track hook execution time per invocation
   - Auto-reorder hooks (fastest first, expensive last)
   - Auto-disable hooks that fail >10 times consecutively
   - Auto-suggest hook consolidation (if 3+ hooks do similar checks)
   - **Impact:** System gets faster over time, not slower

5. **Debt Auto-Prioritizer**
   - Score debt by: frequency of area modified + complexity + age
   - Auto-suggest debt paydown every 100 turns (top 3 items)
   - Auto-remove debt if verification shows it no longer applies
   - **Impact:** Debt doesn't accumulate indefinitely

6. **Anti-Pattern Auto-Discovery**
   - Track all tool failures + penalties
   - Cluster common failure patterns
   - Auto-generate new anti-pattern rules from clusters
   - Auto-test anti-pattern rules (do they prevent future failures?)
   - **Impact:** System learns from mistakes without manual pattern authoring

### 🟢 MEDIUM IMPACT (Quality of Life)

7. **Command Prerequisite Auto-Tuner**
   - Track actual time between command runs
   - Auto-adjust windows (e.g., if upkeep always runs at 15 turns, reduce window to 18)
   - Auto-exempt certain task types (e.g., research-only sessions don't need commit prereqs)
   - **Impact:** Prerequisites stay relevant, fewer false positives

8. **Synapse Pattern Auto-Learner**
   - Track which synapse patterns fire + are useful (user acts on suggestion)
   - Auto-remove patterns that never fire or are ignored
   - Auto-suggest new patterns from user prompt clusters
   - **Impact:** Associative memory improves coverage over time

9. **Telemetry Auto-Archiver**
   - Auto-compress telemetry logs >1 month old
   - Auto-aggregate old data into summary stats
   - Auto-purge raw logs >6 months old
   - **Impact:** Disk usage stays bounded

### 🔵 LOW IMPACT (Nice to Have)

10. **Hook Dependency Auto-Detector**
    - Analyze which hooks depend on outputs of other hooks
    - Auto-optimize execution order based on dependencies
    - Auto-parallelize independent hooks
    - **Impact:** Marginal speed improvement

## Implementation Strategy

### Phase 1: Foundation (Week 1)
Build the **Meta-Learning System** and **Threshold Auto-Tuning Library**.

These are force multipliers - once built, every other system can adopt them.

### Phase 2: Quick Wins (Week 2)
Apply auto-tuning to:
- Batching enforcement
- Command prerequisites
- Performance gates

### Phase 3: Memory Hygiene (Week 3)
Implement:
- Lesson consolidation
- Debt auto-prioritizer
- Telemetry archiver

### Phase 4: Pattern Learning (Week 4)
Implement:
- Anti-pattern auto-discovery
- Synapse pattern auto-learner

### Phase 5: Hook Optimization (Week 5)
Implement:
- Hook auto-optimizer
- Hook dependency detector

## Success Metrics

**How to measure "Zero Revisit" achievement:**

1. **Manual Intervention Ratio**
   - Track: User explicitly disables/modifies enforcement rules
   - Target: <1% of sessions require manual intervention
   - Current: Unknown (not tracked)

2. **Threshold Drift Over Time**
   - Track: How much thresholds change from defaults
   - Target: Converge to stable values within 100 turns
   - Current: Scratch enforcement achieves this ✅

3. **False Positive Rate Stability**
   - Track: FP rate variance over time
   - Target: FP rate stays within 5-15% band
   - Current: Scratch enforcement tracks this ✅

4. **Override Clustering Success**
   - Track: % of overrides that lead to auto-generated exception rules
   - Target: >50% of override patterns become auto-rules
   - Current: 0% (not implemented)

5. **Signal-to-Noise Ratio**
   - Track: % of lessons/debt/alerts that are acted upon
   - Target: >80% of top-5 items are relevant
   - Current: Unknown (not tracked)

## The North Star

**Every enforcement system should:**
1. Start passive (observe phase)
2. Auto-tune based on outcomes
3. Self-correct when wrong
4. Report progress transparently
5. Learn from user overrides
6. Prune stale data automatically

**If a system doesn't do these 6 things, it WILL be abandoned.**
