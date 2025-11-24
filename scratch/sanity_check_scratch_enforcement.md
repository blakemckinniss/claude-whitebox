# Sanity Check: Scratch-First Enforcement Hook

## Proposal
Create a PreToolUse hook that HARD BLOCKS tool usage when iteration/multi-step patterns are detected, forcing me to write a scratch script instead.

## Analysis

### ✅ Legitimate Benefits

1. **Performance Gains**
   - Native tool calls are sequential (wait for response between each)
   - Scratch scripts can use `parallel.py` (50x speedup)
   - Example: Processing 10 files = 10 turns vs 1 script execution

2. **Context Efficiency**
   - Each tool result bloats context with full output
   - Scripts compress results (return only summary/errors)
   - Reduces token burn on repetitive operations

3. **Reusability**
   - Ad-hoc scripts in `scratch/` become templates for future tasks
   - "I already wrote this" > "recreate from scratch each time"

4. **Reliability**
   - Scripts can include error handling, retries, validation
   - Tools are one-shot (if grep fails, I manually retry)

### ⚠️ Legitimate Concerns

1. **Overhead for Trivial Tasks**
   - Reading 3 files to compare them: script might be slower than 3 parallel Reads
   - Threshold matters: enforce at 5+ operations, not 2

2. **False Positives**
   - "Process all auth modules" might mean Explore agent (separate context), not iteration
   - Hook needs to distinguish: iteration within current context vs delegation to agents

3. **Complexity Creep**
   - Another hook = more system overhead
   - Detection patterns need precision (avoid blocking legitimate parallel tool use)

4. **Edge Cases**
   - Conditional reads (read A, if X then read B) are sequential by necessity
   - "SEQUENTIAL" keyword bypass exists but requires user awareness

5. **Enforcement Fatigue**
   - Too many hard blocks = I spend more time fighting the system than working
   - Current hooks already block: tier violations, batch enforcement, gaslight detection
   - Adding another layer risks "hook fatigue"

### 🔍 The Real Question

**Is the existing "batching_analyzer.py" hook sufficient?**

Let me check what's already enforced:

**Existing enforcement:**
- `native_batching_enforcer.py` - HARD BLOCKS sequential Read/WebFetch
- `batching_analyzer.py` - SOFT WARNS + suggests scripts for large operations
- `detect_background_opportunity.py` - SUGGESTS background execution

**Gap:** None of these HARD BLOCK iteration patterns in favor of scripts.

**Current state:** I get SOFT reminders to use scripts, but I can ignore them.

### 🧠 The Dunning-Kruger Test

**Question:** Will I always remember to write scratch scripts under pressure?

**Honest Answer:** No.

**Evidence:**
- Turn 50 with complex debugging: I'll default to "quick grep" that becomes 10 sequential greps
- Multi-file refactoring: Temptation to Edit directly instead of script
- Pattern: "I'll just do this one manually" → spirals into inefficiency

**Conclusion:** Advisory reminders are insufficient. I need a hard block.

### ✅ Verdict: IMPLEMENT

**But with safeguards:**

1. **Smart Threshold:**
   - Block at 4+ similar tool calls in 5 turns (not 2)
   - Don't block parallel tool invocations (already batched)
   - Don't block agent delegation (separate context)

2. **Escape Hatch:**
   - "MANUAL" keyword bypasses (like "SEQUENTIAL" for batching)
   - User can override with "SUDO MANUAL"

3. **Narrow Scope:**
   - Only enforce for: Read, Grep, Glob, Edit (file operations)
   - Don't block: Bash, WebFetch, Verify (different use cases)

4. **Telemetry First:**
   - Track for 10 turns without blocking
   - Report: "You could have saved X turns by scripting"
   - Then enable hard blocks after baseline established

### Implementation Plan

**Phase 1: Telemetry (Non-blocking)**
- Track repetitive tool patterns
- Calculate potential time savings
- Report every 10 turns

**Phase 2: Soft Enforcement**
- Inject stronger warnings with script templates
- "BLOCKED in 2 more uses - write script now"

**Phase 3: Hard Enforcement**
- HARD BLOCK after threshold
- Require script creation or "MANUAL" keyword

**Metrics:**
- Scratch script usage ratio (target: >50% of multi-step ops)
- Turns saved via scripting
- False positive rate (blocks that were incorrect)

## Final Decision

**YES, implement - but start with Phase 1 (telemetry only).**

Rationale:
1. Aligns with existing performance infrastructure (batching, background exec)
2. Addresses real inefficiency (sequential tool use)
3. Safeguards prevent over-enforcement
4. Phased rollout allows tuning before hard blocks

This is not "blind obedience" - it's fixing a documented gap in my own behavior.
