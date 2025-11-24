# Oracle.py Demo: Ultra-Fast Decision Making

## Example 1: Triple Oracle Check (3 seconds)

**Scenario:** User asks "Should we migrate from Python to Rust for the backend?"

**Old approach (council.py):**
```bash
python3 scripts/ops/council.py "Migrate backend from Python to Rust"
# Wait 45-90 seconds...
# Get 5000 words of deliberation
```

**New approach (oracle.py parallel via agents):**
```
User: "Should we migrate from Python to Rust for the backend?"

Claude: This is a major architecture decision. Let me consult the triple oracle in parallel.

<function_calls>
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="description">Judge: ROI analysis</parameter>
  <parameter name="prompt">Run this command and return the output:
python3 scripts/ops/oracle.py --persona judge "Migrate backend from Python to Rust for performance"
  </parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="description">Critic: Attack assumptions</parameter>
  <parameter name="prompt">Run this command and return the output:
python3 scripts/ops/oracle.py --persona critic "Migrate backend from Python to Rust for performance"
  </parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="description">Skeptic: Pre-mortem analysis</parameter>
  <parameter name="prompt">Run this command and return the output:
python3 scripts/ops/oracle.py --persona skeptic "Migrate backend from Python to Rust for performance"
  </parameter>
</invoke>
</function_calls>

# All 3 run in parallel, return in ~3 seconds
# Each agent compresses output to ~100 words
# Total: 300 words vs 5000 words (94% savings)
```

**Expected Results:**

**Judge verdict:**
```
⚖️ VERDICT: STOP

📉 REASON:
You're solving a problem you haven't measured. Profile first.

✂️ THE CUT:
Remove the migration entirely. Profile Python code, optimize hot paths with Cython/PyPy.

💡 THE ALTERNATIVE:
1. Profile with cProfile
2. Optimize the 20% causing 80% of slowness
3. If still slow, optimize one module at a time (not entire backend)
```

**Critic response:**
```
🥊 THE ATTACK
You assume Rust = faster. But rewrites = bugs. Your Python code works TODAY.

🌑 THE BLIND SPOT
You're avoiding the real work: profiling and optimization. Rust is a distraction.

🔄 THE COUNTER-POINT
Keep Python. Add Rust only for proven bottlenecks. Hybrid > rewrite.

🔥 THE BRUTAL TRUTH
This migration will take 6 months, introduce 100+ bugs, and deliver 10% speedup. Not worth it.
```

**Skeptic analysis:**
```
🚨 CRITICAL ISSUES
- No profiling data (guessing at bottlenecks)
- No prototype (unknown Rust learning curve)
- No migration plan (all or nothing is risky)

⚠️ LOGICAL FALLACIES DETECTED
Premature Optimization: Solving for "potential" slowness, not measured reality

🔥 PRE-MORTEM: How This Will Fail
"Migration failed because: Python→Rust took 8 months, team burned out, 200 bugs introduced, performance gain was 15% (could've achieved with profiling + Cython in 2 weeks)"

💡 ALTERNATIVE APPROACHES
1. Profile Python (1 day)
2. Optimize hot paths with Cython (1 week)
3. If insufficient, rewrite ONLY bottleneck modules in Rust (1 month)
```

**Claude synthesizes:**
```
All 3 oracles agree: STOP the full migration.

Judge: ROI is terrible (6 months for 10% gain)
Critic: You're avoiding profiling (the real work)
Skeptic: Pre-mortem shows 200 bugs, team burnout

Recommendation: Profile first, optimize Python, then reconsider.
```

**Time:** 3 seconds (vs 90s)
**Context:** 300 words (vs 5000 words)
**Speedup:** 30x faster
**Clarity:** Unanimous verdict (STOP)

---

## Example 2: Meta-Agent Design with Oracle

**Scenario:** Building the architect meta-agent

**Old approach:**
```
1. Manually design agent (30 minutes)
2. Manually write tests (20 minutes)
3. Manually review design (10 minutes)
Total: 60 minutes
```

**New approach (oracle-assisted):**
```bash
# Step 1: Get design guidance (3s)
oracle.py --custom-prompt "You are a meta-agent architect" "Design an agent that creates hooks"

# Step 2: Validate design (3s)
oracle.py --persona skeptic "Agent design: [paste design from step 1]"

# Step 3: Generate test scenarios (3s)
oracle.py --custom-prompt "You are a QA engineer" "Test scenarios for architect agent: [paste design]"

# Step 4: Review for issues (3s)
oracle.py --persona critic "Architect agent implementation: [paste code]"

Total consultation: 12 seconds
Total time: 12s + implementation (vs 60 minutes)
```

**Result:** Oracle-validated meta-agent in 15 minutes (vs 60 minutes)

---

## Example 3: Parallel Research with Oracle

**Scenario:** User asks "What's the best database for high-write workloads?"

**Old approach:**
```
1. Research PostgreSQL (manual, 10 min)
2. Research MongoDB (manual, 10 min)
3. Research Cassandra (manual, 10 min)
4. Research TimescaleDB (manual, 10 min)
5. Compare results (manual, 10 min)
Total: 50 minutes
```

**New approach (oracle parallel):**
```xml
<function_calls>
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="description">PostgreSQL analysis</parameter>
  <parameter name="prompt">Run: oracle.py "PostgreSQL for high-write workloads: pros/cons, performance characteristics"</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="description">MongoDB analysis</parameter>
  <parameter name="prompt">Run: oracle.py "MongoDB for high-write workloads: pros/cons, performance characteristics"</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="description">Cassandra analysis</parameter>
  <parameter name="prompt">Run: oracle.py "Cassandra for high-write workloads: pros/cons, performance characteristics"</parameter>
</invoke>
<invoke name="Task">
  <parameter name="subagent_type">researcher</parameter>
  <parameter name="description">TimescaleDB analysis</parameter>
  <parameter name="prompt">Run: oracle.py "TimescaleDB for high-write workloads: pros/cons, performance characteristics"</parameter>
</invoke>
</function_calls>

# All 4 run in parallel, return in 3 seconds
# Each returns ~100 words
# Total: 400 words of comparative analysis
```

**Result:** 4 database comparisons in 3 seconds (vs 50 minutes)

---

## Example 4: Hook Design Validation

**Scenario:** Creating a new hook to enforce test coverage

**Workflow with oracle:**

```bash
# Design phase (3s)
oracle.py --custom-prompt "You are a hook designer" "Design PreToolUse hook that blocks git commits when test coverage <80%"

# Response includes:
# - Hook structure
# - Required checks
# - Error handling
# - Registration in settings.json

# Validation phase (parallel, 3s)
"Run oracle critic and skeptic in parallel on this hook design"

# Critic finds:
# - Missing edge case: What if pytest isn't installed?
# - Potential bypass: User could disable hook

# Skeptic finds:
# - Security: Coverage report could be faked
# - Performance: Running coverage check on every commit is slow

# Revision based on feedback (manual)
# - Add check for pytest existence
# - Cache coverage results
# - Verify coverage report authenticity

# Final review (3s)
oracle.py --persona judge "Revised hook design: [paste]"

# Judge verdict: PROCEED (with minor simplifications)

Total oracle time: 9 seconds
Total time: 9s + implementation (vs hours of manual design/review)
```

---

## Example 5: The Ultimate Meta-Pattern

**Scenario:** User wants to add a complex new protocol

**Comprehensive workflow (30 seconds of oracle consultations):**

```bash
# Phase 1: Design (3s)
oracle.py --custom-prompt "You are a protocol designer" "Design enforcement mechanism for API rate limiting"

# Phase 2: Validation (parallel, 3s)
"Run oracle judge, critic, skeptic in parallel on protocol design"

# Phase 3: Implementation planning (3s)
oracle.py --custom-prompt "You are a meta-system architect" "Implementation plan for rate limit protocol: hooks, state, enforcement"

# Phase 4: Security review (3s)
oracle.py --custom-prompt "You are a security auditor" "Security analysis of rate limit protocol: [paste design]"

# Phase 5: Test strategy (3s)
oracle.py --custom-prompt "You are a QA engineer" "Test strategy for rate limit protocol: scenarios, edge cases, validation"

# Phase 6: Documentation plan (3s)
oracle.py --custom-prompt "You are a technical writer" "Documentation outline for rate limit protocol: user guide, reference, examples"

# Phase 7: Final review (parallel, 3s)
"Run oracle judge, critic, skeptic in parallel on complete protocol design"

Total oracle time: 24 seconds
Total consultations: 10 (7 single + 2 parallel triple-checks)
Total cost: <$0.10 (Gemini Flash is cheap)
Result: Fully validated protocol design
```

**Compare to manual:**
- Design: 1 hour
- Validation: 30 minutes
- Security review: 30 minutes
- Test planning: 30 minutes
- Documentation: 30 minutes
- Total: 3 hours

**With oracle: 24 seconds + implementation**

**Speedup: 450x on consultation phase**

---

## Best Practices

### 1. Always Use Triple Oracle for Major Decisions
```bash
"Run oracle judge, critic, skeptic in parallel on: [decision]"
```

### 2. Use Custom Prompts for Domain Expertise
```bash
oracle.py --custom-prompt "You are a [domain expert]" "[question]"
```

Examples:
- "You are a database architect"
- "You are a security auditor"
- "You are a meta-system designer"
- "You are a performance engineer"
- "You are a technical writer"

### 3. Parallel Oracle = Free Speedup
```
3 sequential oracles: 9 seconds
3 parallel oracles (via agents): 3 seconds
Speedup: 3x (FREE via parallelism)
```

### 4. Oracle Before Implementation
```
Design → Oracle validation → Implementation
(Not: Implementation → Manual review → Refactor)
```

### 5. Oracle for Meta-Agent Development
```
Agent design → Oracle skeptic
Test generation → Oracle QA engineer
Documentation → Oracle technical writer
Final review → Oracle judge
```

---

## Measurement

**Track oracle usage:**
```bash
# Add to session state
oracle_calls: 0
oracle_time_saved: 0  # vs council.py

# After each oracle call
oracle_calls += 1
oracle_time_saved += 87  # seconds (90s - 3s)
```

**Session end summary:**
```
Oracle usage this session:
- Calls: 12
- Time saved: 1044s (17.4 minutes)
- Decisions validated: 4
- Designs reviewed: 3
- Security audits: 2
```

---

## Bottom Line

**Oracle.py transforms decision-making from minutes/hours to seconds.**

Use it:
- **Every major decision** (triple oracle in parallel)
- **Before implementation** (validate design)
- **After implementation** (review code)
- **For meta-agents** (design, test, document)
- **Instead of council.py** (30x faster)

**The rule:** If you're about to spend >5 minutes thinking, spend 3 seconds asking oracle first.
